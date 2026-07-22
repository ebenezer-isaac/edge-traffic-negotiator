"""MQTT-backed transport for The Edge Negotiator's signed neighbour bus.

DE-RISK SPIKE (MASTER-SPEC.md: the fast/real-time control path is
*signed messages over MQTT*; the Besu ledger is the slow async trust path).
``src/message_bus.py`` ships an **in-process** ``MessageBus`` whose publish/inbox
split was deliberately shaped like an MQTT adapter would wrap (see its module
docstring). This module is that adapter: it puts a real broker between
``publish`` and ``inbox`` *without forking any crypto or verification*.

Design — reuse, do not reimplement
----------------------------------
``MqttTransport`` wraps one ``MessageBus`` per junction host. The wire format is
the *same self-authenticating* ``NeighborMessage`` the in-process bus already
produces:

  * **publish(identity, t, payload)** — signs via ``MessageBus.publish`` (which
    signs with ``identity`` over ``canonical_bytes``), then serialises the
    resulting signed ``NeighborMessage`` to JSON (signature is raw bytes ->
    base64) and PUBLISHES it to ``edge-negotiator/junction/<sender>``.
  * **on receipt**, a subscriber deserialises the JSON back into a
    ``NeighborMessage``, injects it into a *receiver-side* ``MessageBus``, and
    calls ``MessageBus.inbox(recipient)``. That single call runs the IDENTICAL
    topology + registry-membership + Ed25519-signature + replay checks the
    in-process bus uses. The MQTT layer adds transport only; it makes **no**
    trust decision of its own. A tampered payload, a non-neighbour sender, or a
    revoked/unknown sender is rejected by exactly the same code path and lands
    in the same ``bus.rejected`` log.

Broker-down is explicit
-----------------------
Connection failure raises :class:`MqttTransportError` with the underlying error
(no silent swallow). ``publish`` to a broker that has gone away raises too.

This is a spike: QoS/retain/TLS/auth choices for the production corridor are
discussed in ``../MQTT-SPIKE.md``; here we use QoS 1 (at-least-once; the bus's
replay guard makes duplicate delivery safe to drop) and no retain (reports are
per-tick and must not be replayed to late subscribers).
"""
from __future__ import annotations

import base64
import json
import queue
import threading
from dataclasses import dataclass

import paho.mqtt.client as mqtt

from identity import JunctionIdentity
from message_bus import MessageBus, NeighborMessage

TOPIC_PREFIX = "edge-negotiator/junction"
# QoS 1: at-least-once. The bus's (recipient, sender, t) replay guard makes a
# duplicate harmless (it is rejected as ``replay``), so we trade possible dupes
# for guaranteed delivery rather than risk a dropped report at QoS 0.
DEFAULT_QOS = 1


class MqttTransportError(RuntimeError):
    """Raised when the broker is unreachable or a publish/connect fails.

    Carries the underlying transport error so a junction never silently loses
    connectivity to the control plane.
    """


def topic_for(sender: str) -> str:
    """Topic a junction publishes its own reports on: one topic per sender."""
    return f"{TOPIC_PREFIX}/{sender}"


# --------------------------------------------------------------------------- #
# Wire (de)serialisation — the signed NeighborMessage as broker-ready bytes.
# --------------------------------------------------------------------------- #


def serialize(message: NeighborMessage) -> bytes:
    """Encode a signed ``NeighborMessage`` to self-describing JSON bytes.

    The signature is raw 64-byte Ed25519 output, so it is base64-encoded for
    JSON transport. ``sender``/``t``/``payload`` are carried verbatim so the
    receiver can recompute ``canonical_bytes`` byte-identically and verify.
    """
    return json.dumps(
        {
            "sender": message.sender,
            "t": message.t,
            "payload": message.payload,
            "sig_b64": base64.b64encode(message.signature).decode("ascii"),
        },
        # Wire encoding need not be canonical (only the *signed* bytes must be);
        # but keep it deterministic for reproducible captures.
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def deserialize(raw: bytes) -> NeighborMessage:
    """Decode broker bytes back into a ``NeighborMessage``.

    Strictly validates the envelope shape and types before constructing the
    message; a malformed/hostile frame raises ``ValueError`` rather than
    producing a half-built object. The crypto is NOT checked here — that is the
    bus's job on ``inbox`` — but a frame that cannot even be parsed into the
    right shape can never be a valid signed report, so we reject it early.
    """
    if not isinstance(raw, (bytes, bytearray)):
        raise ValueError("raw frame must be bytes")
    try:
        obj = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"frame is not valid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("frame must be a JSON object")

    sender = obj.get("sender")
    t = obj.get("t")
    payload = obj.get("payload")
    sig_b64 = obj.get("sig_b64")

    if not isinstance(sender, str) or not sender:
        raise ValueError("frame.sender must be a non-empty string")
    # bool is an int subclass; reject it explicitly like the bus does for t.
    if not isinstance(t, int) or isinstance(t, bool):
        raise ValueError("frame.t must be an int")
    if not isinstance(payload, dict):
        raise ValueError("frame.payload must be an object")
    if not isinstance(sig_b64, str):
        raise ValueError("frame.sig_b64 must be a base64 string")
    try:
        signature = base64.b64decode(sig_b64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"frame.sig_b64 is not valid base64: {exc}") from exc

    return NeighborMessage(sender=sender, t=t, payload=payload, signature=signature)


# --------------------------------------------------------------------------- #
# Receiver-side verification — REUSE MessageBus.inbox, do not reimplement.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class VerifiedDelivery:
    """Outcome of feeding one received frame through the bus's verification.

    ``message`` is the delivered :class:`NeighborMessage` iff ``ok`` is True;
    otherwise ``reason`` is the bus's rejection reason (one of the bus's closed
    set: unknown_sender / revoked / bad_signature / not_neighbour / replay).
    """

    ok: bool
    message: NeighborMessage | None
    reason: str | None


def verify_received(
    bus: MessageBus, recipient: str, message: NeighborMessage
) -> VerifiedDelivery:
    """Run the in-process bus's FULL verification over a received message.

    This injects ``message`` into ``bus`` exactly as if it had been published
    locally, then calls ``bus.inbox(recipient)``. All trust logic (topology,
    membership, signature, replay) is the bus's own code — the MQTT layer makes
    no security decision. Returns a :class:`VerifiedDelivery` reporting whether
    the bus accepted it and, if not, the bus's precise reason.

    We touch ``bus._published`` directly because that is the in-process bus's
    receive buffer; the spike's whole point is to drive the *same* buffer from a
    broker instead of from a local ``publish``. Verification itself is untouched.
    """
    rejected_before = len(bus.rejected)
    # Inject into the bus's receive buffer (immutable-style append, matching the
    # bus's own pattern) so inbox() considers it.
    bus._published = [*bus._published, message]  # noqa: SLF001 (intentional reuse)
    delivered = bus.inbox(recipient, t=message.t)

    for msg in delivered:
        if (
            msg.sender == message.sender
            and msg.t == message.t
            and msg.signature == message.signature
        ):
            return VerifiedDelivery(ok=True, message=msg, reason=None)

    # Not delivered -> the bus logged exactly why. Take the newest reason that
    # concerns this (recipient, sender, t).
    new_rejections = bus.rejected[rejected_before:]
    reason = None
    for rej in reversed(new_rejections):
        if (
            rej["recipient"] == recipient
            and rej["sender"] == message.sender
            and rej["t"] == message.t
        ):
            reason = rej["reason"]
            break
    return VerifiedDelivery(ok=False, message=None, reason=reason)


# --------------------------------------------------------------------------- #
# The transport.
# --------------------------------------------------------------------------- #


class MqttTransport:
    """One junction host's MQTT endpoint over a shared signed ``MessageBus``.

    Construct with the junction's own ``recipient`` id, a ``MessageBus`` (built
    from the shared registry + adjacency, exactly as the in-process path is),
    and the broker host/port. ``publish`` signs+ships; received frames are run
    through the bus's verification and, if accepted, handed to ``on_delivered``
    and also pushed to an internal queue ``poll()`` drains. Use as a context
    manager to guarantee disconnect.

    Subscriptions: by default we subscribe to ``edge-negotiator/junction/+`` and
    let the *bus* decide (via topology) which senders are actually neighbours,
    so a misconfigured topic filter can never widen trust — the security gate is
    always the verification, never the subscription.
    """

    def __init__(
        self,
        recipient: str,
        bus: MessageBus,
        *,
        host: str = "127.0.0.1",
        port: int = 1883,
        client_id: str | None = None,
        qos: int = DEFAULT_QOS,
        connect_timeout: float = 5.0,
    ) -> None:
        if not isinstance(recipient, str) or not recipient:
            raise ValueError("recipient must be a non-empty string")
        if not isinstance(bus, MessageBus):
            raise TypeError("bus must be a MessageBus")

        self._recipient = recipient
        self._bus = bus
        self._host = host
        self._port = port
        self._qos = qos
        self._connect_timeout = connect_timeout

        self._delivered_q: "queue.Queue[VerifiedDelivery]" = queue.Queue()
        self._on_delivered = None  # optional callback(VerifiedDelivery)
        self._lock = threading.Lock()
        self._connected = threading.Event()
        self._connect_rc = None
        self._connect_failed = False

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id or f"edge-{recipient}",
        )
        self._client.on_connect = self._handle_connect
        self._client.on_message = self._handle_message

    # -- lifecycle -----------------------------------------------------------

    def connect(self) -> None:
        """Connect to the broker and subscribe. Raises on failure (no swallow)."""
        try:
            self._client.connect(self._host, self._port, keepalive=30)
        except (OSError, ConnectionError) as exc:
            raise MqttTransportError(
                f"cannot reach MQTT broker at {self._host}:{self._port}: {exc}"
            ) from exc
        self._client.loop_start()
        if not self._connected.wait(self._connect_timeout):
            self._client.loop_stop()
            raise MqttTransportError(
                f"timed out connecting to MQTT broker at {self._host}:{self._port} "
                f"after {self._connect_timeout}s"
            )
        if self._connect_failed:
            self._client.loop_stop()
            raise MqttTransportError(
                f"broker refused connection (rc={self._connect_rc})"
            )

    def disconnect(self) -> None:
        """Stop the network loop and disconnect cleanly. Idempotent."""
        try:
            self._client.disconnect()
        finally:
            self._client.loop_stop()

    def __enter__(self) -> "MqttTransport":
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.disconnect()

    # -- API -----------------------------------------------------------------

    def set_on_delivered(self, callback) -> None:
        """Register a callback ``fn(VerifiedDelivery)`` for accepted messages.

        Called from the paho network thread. Keep it cheap and thread-safe.
        """
        self._on_delivered = callback

    def publish(self, identity: JunctionIdentity, t: int, payload: dict) -> NeighborMessage:
        """Sign via the bus, then PUBLISH the signed frame to the sender topic.

        Signing is delegated to ``MessageBus.publish`` so the exact same key
        usage and ``canonical_bytes`` apply as the in-process path; we then
        serialise and ship. Raises :class:`MqttTransportError` if the broker
        rejects the publish (e.g. disconnected).
        """
        message = self._bus.publish(identity, t, payload)
        frame = serialize(message)
        info = self._client.publish(topic_for(message.sender), frame, qos=self._qos)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise MqttTransportError(
                f"MQTT publish failed (rc={info.rc}); broker may be down"
            )
        return message

    def subscribe_neighbours(self) -> None:
        """Subscribe to all junction topics; topology gates who is trusted.

        We subscribe with a wildcard and rely on the bus's adjacency check to
        drop non-neighbour senders, so the subscription can never grant trust
        the topology does not.
        """
        self._client.subscribe(f"{TOPIC_PREFIX}/+", qos=self._qos)

    def poll(self, timeout: float = 1.0) -> VerifiedDelivery | None:
        """Block up to ``timeout`` for the next *accepted* delivery, else None.

        Only messages the bus VERIFIED are queued; rejected frames are dropped
        (the reason is in ``bus.rejected``) and never surface here.
        """
        try:
            return self._delivered_q.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def bus(self) -> MessageBus:
        """The underlying verifying bus (exposes ``rejected`` for inspection)."""
        return self._bus

    # -- paho callbacks ------------------------------------------------------

    def _handle_connect(self, client, userdata, flags, reason_code, properties=None):
        # reason_code is a paho V2 ReasonCode: it exposes .is_failure and .value
        # (it is NOT directly int()-able). Success -> subscribe; failure is
        # surfaced to connect() which raises rather than swallowing it.
        self._connect_rc = reason_code
        self._connect_failed = bool(getattr(reason_code, "is_failure", False))
        if not self._connect_failed:
            self.subscribe_neighbours()
        self._connected.set()

    def _handle_message(self, client, userdata, msg):
        # Parse + verify entirely through the bus. A hostile/malformed frame is
        # rejected here and never crashes the receiver thread.
        try:
            message = deserialize(msg.payload)
        except ValueError:
            # Unparseable frame: not a valid signed report. Drop silently from
            # the delivery queue (it could never verify); do not crash.
            return
        with self._lock:
            result = verify_received(self._bus, self._recipient, message)
        if result.ok:
            self._delivered_q.put(result)
            if self._on_delivered is not None:
                self._on_delivered(result)
