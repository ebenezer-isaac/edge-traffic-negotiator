"""Round-trip + adversarial tests for src/mqtt_transport.py over a REAL broker.

The MQTT transport is the de-risk spike for the brief's fast control path
(signed messages over MQTT). The whole point of the spike is that the broker
adds *transport only* and the trust guarantees stay byte-identical to the
in-process ``MessageBus``. These tests assert exactly that against a live
``eclipse-mosquitto`` broker:

  * a signed neighbour message published over MQTT is received AND verifies,
    with payload intact (happy path);
  * a payload tampered on the wire is REJECTED with ``bad_signature``;
  * a non-neighbour sender is REJECTED with ``not_neighbour``;
  * a revoked sender is REJECTED with ``revoked``;
  * an unknown (never-registered) sender is REJECTED with ``unknown_sender``;
  * a duplicate frame (QoS-1 redelivery) is REJECTED with ``replay``.

If no broker is reachable on the configured host/port the whole module is
skipped with a clear reason (so the suite is never red merely because the
spike's container is not up). Set EDGE_MQTT_HOST / EDGE_MQTT_PORT to point at
the broker (defaults 127.0.0.1:1883).

src/ is inserted on sys.path so ``import mqtt_transport`` works when run as
``python -m pytest tests`` from the project root, matching the other tests.
"""
import os
import socket
import sys
import time

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from identity import JunctionIdentity  # noqa: E402
from message_bus import MessageBus, NeighborMessage  # noqa: E402
from registry import Registry  # noqa: E402
from mqtt_transport import (  # noqa: E402
    MqttTransport,
    MqttTransportError,
    deserialize,
    serialize,
    topic_for,
    verify_received,
)

import paho.mqtt.client as mqtt  # noqa: E402

HOST = os.environ.get("EDGE_MQTT_HOST", "127.0.0.1")
PORT = int(os.environ.get("EDGE_MQTT_PORT", "1883"))

# 2x2 grid topology from the project brief (same as test_message_bus.py).
ADJACENCY = {
    "A0": ["A1", "B0"],
    "A1": ["A0", "B1"],
    "B0": ["A0", "B1"],
    "B1": ["A1", "B0"],
}


def _broker_up(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# Skip the entire module (cleanly, with a reason) if the broker is not up.
pytestmark = pytest.mark.skipif(
    not _broker_up(HOST, PORT),
    reason=f"no MQTT broker reachable at {HOST}:{PORT} (start eclipse-mosquitto)",
)


def _fresh_registry():
    """Registry + identities for A0, A1, B0, B1, all registered & approved."""
    registry = Registry()
    idents = {jid: JunctionIdentity(jid) for jid in ("A0", "A1", "B0", "B1")}
    for jid, ident in idents.items():
        registry.register(jid, ident.public_key)
    return registry, idents


def _make_transport(recipient, registry, **kw):
    bus = MessageBus(registry, ADJACENCY)
    kw.setdefault("host", HOST)
    kw.setdefault("port", PORT)
    return MqttTransport(recipient, bus, **kw)


def _drain_until(transport, predicate, deadline_s=5.0):
    """Poll the transport until ``predicate(delivery)`` or timeout."""
    end = time.time() + deadline_s
    while time.time() < end:
        d = transport.poll(timeout=0.5)
        if d is not None and predicate(d):
            return d
    return None


# --------------------------------------------------------------------------- #
# Pure (de)serialisation — no broker needed, but guards the wire contract.
# --------------------------------------------------------------------------- #


def test_serialize_roundtrip_preserves_signed_fields():
    registry, idents = _fresh_registry()
    bus = MessageBus(registry, ADJACENCY)
    msg = bus.publish(idents["A1"], t=7, payload={"phase": 2, "q": [1, 0, 3]})

    restored = deserialize(serialize(msg))
    assert restored.sender == msg.sender
    assert restored.t == msg.t
    assert restored.payload == msg.payload
    assert restored.signature == msg.signature  # raw bytes survive base64


@pytest.mark.parametrize(
    "raw",
    [
        b"not json",
        b"[]",
        b"{}",
        b'{"sender":"","t":1,"payload":{},"sig_b64":"AA=="}',
        b'{"sender":"A1","t":true,"payload":{},"sig_b64":"AA=="}',
        b'{"sender":"A1","t":1,"payload":[],"sig_b64":"AA=="}',
        b'{"sender":"A1","t":1,"payload":{},"sig_b64":"!!!not-base64"}',
    ],
)
def test_deserialize_rejects_malformed_frames(raw):
    with pytest.raises(ValueError):
        deserialize(raw)


# --------------------------------------------------------------------------- #
# Real broker: happy-path round-trip verifies with payload intact.
# --------------------------------------------------------------------------- #


def test_roundtrip_signed_message_verifies():
    registry, idents = _fresh_registry()
    # A0 is the receiver; A1 is its neighbour and the sender.
    receiver = _make_transport("A0", registry, client_id="recv-A0-rt")
    sender_bus = MessageBus(registry, ADJACENCY)
    sender = MqttTransport("A1", sender_bus, host=HOST, port=PORT, client_id="send-A1-rt")
    with receiver, sender:
        payload = {"phase": 2, "predicted_outflow": 17, "queue": [3, 0, 1]}
        sent = sender.publish(idents["A1"], t=5, payload=payload)

        got = _drain_until(receiver, lambda d: d.ok and d.message.t == 5)
        assert got is not None, "neighbour message was never delivered/verified"
        assert got.message.sender == "A1"
        assert got.message.payload == payload   # intact across the broker
        assert got.message.signature == sent.signature
        # Nothing should have been rejected for this delivery.
        assert all(r["reason"] != "bad_signature" for r in receiver.bus.rejected)


# --------------------------------------------------------------------------- #
# Real broker: tampered payload on the wire is rejected (bad_signature).
# --------------------------------------------------------------------------- #


def test_tampered_payload_rejected_over_broker():
    registry, idents = _fresh_registry()
    receiver = _make_transport("A0", registry, client_id="recv-A0-tamper")
    with receiver:
        # Build a genuine signed message from neighbour A1, then tamper the
        # payload AFTER signing and publish the forged frame on A1's topic
        # using a raw paho client (an attacker who can write to the topic).
        signer_bus = MessageBus(registry, ADJACENCY)
        msg = signer_bus.publish(idents["A1"], t=9, payload={"phase": 1})
        forged = NeighborMessage(
            sender=msg.sender,
            t=msg.t,
            payload={"phase": 99},          # changed -> signature no longer matches
            signature=msg.signature,
        )
        _raw_publish(topic_for("A1"), serialize(forged))

        # It must NOT be delivered; the bus must log bad_signature.
        delivered = _drain_until(receiver, lambda d: d.ok and d.message.t == 9, deadline_s=2.0)
        assert delivered is None, "tampered payload was wrongly delivered"
        time.sleep(0.3)  # let the reject land
        reasons = [
            r["reason"] for r in receiver.bus.rejected
            if r["sender"] == "A1" and r["t"] == 9
        ]
        assert "bad_signature" in reasons


# --------------------------------------------------------------------------- #
# Real broker: non-neighbour sender rejected (not_neighbour).
# --------------------------------------------------------------------------- #


def test_non_neighbour_rejected_over_broker():
    registry, idents = _fresh_registry()
    # A0's neighbours are A1 and B0. B1 is approved+registered but NOT adjacent.
    receiver = _make_transport("A0", registry, client_id="recv-A0-nonadj")
    with receiver:
        signer_bus = MessageBus(registry, ADJACENCY)
        msg = signer_bus.publish(idents["B1"], t=3, payload={"phase": 1})
        _raw_publish(topic_for("B1"), serialize(msg))

        delivered = _drain_until(receiver, lambda d: d.ok and d.message.t == 3, deadline_s=2.0)
        assert delivered is None
        time.sleep(0.3)
        reasons = [
            r["reason"] for r in receiver.bus.rejected
            if r["sender"] == "B1" and r["t"] == 3
        ]
        assert "not_neighbour" in reasons


# --------------------------------------------------------------------------- #
# Real broker: revoked sender rejected (revoked).
# --------------------------------------------------------------------------- #


def test_revoked_sender_rejected_over_broker():
    registry, idents = _fresh_registry()
    receiver = _make_transport("A0", registry, client_id="recv-A0-revoked")
    with receiver:
        # A1 is a neighbour and was registered; revoke it before delivery.
        signer_bus = MessageBus(registry, ADJACENCY)
        msg = signer_bus.publish(idents["A1"], t=11, payload={"phase": 1})
        registry.revoke("A1")
        _raw_publish(topic_for("A1"), serialize(msg))

        delivered = _drain_until(receiver, lambda d: d.ok and d.message.t == 11, deadline_s=2.0)
        assert delivered is None
        time.sleep(0.3)
        reasons = [
            r["reason"] for r in receiver.bus.rejected
            if r["sender"] == "A1" and r["t"] == 11
        ]
        assert "revoked" in reasons


# --------------------------------------------------------------------------- #
# Real broker: unknown (never-registered) sender rejected (unknown_sender).
# --------------------------------------------------------------------------- #


def test_unknown_sender_rejected_over_broker():
    registry, idents = _fresh_registry()
    receiver = _make_transport("A0", registry, client_id="recv-A0-unknown")
    with receiver:
        # "A0" thinks A1 is a neighbour. Use a NEW identity that claims to be A1
        # but is not in the registry under that... actually A1 IS registered, so
        # to get unknown_sender we need an adjacency entry to a never-registered
        # junction. Add a synthetic neighbour to a throwaway receiver.
        adj = {**ADJACENCY, "A0": ["A1", "B0", "GHOST"]}
        ghost_bus = MessageBus(registry, adj)
        ghost_receiver = MqttTransport(
            "A0", ghost_bus, host=HOST, port=PORT, client_id="recv-A0-ghost"
        )
        with ghost_receiver:
            ghost = JunctionIdentity("GHOST")  # never registered
            signer_bus = MessageBus(registry, adj)
            # GHOST is not in registry, so signer_bus.publish still signs fine
            # (publish does not check membership).
            msg = signer_bus.publish(ghost, t=13, payload={"phase": 1})
            _raw_publish(topic_for("GHOST"), serialize(msg))

            delivered = _drain_until(
                ghost_receiver, lambda d: d.ok and d.message.t == 13, deadline_s=2.0
            )
            assert delivered is None
            time.sleep(0.3)
            reasons = [
                r["reason"] for r in ghost_receiver.bus.rejected
                if r["sender"] == "GHOST" and r["t"] == 13
            ]
            assert "unknown_sender" in reasons


# --------------------------------------------------------------------------- #
# Real broker: duplicate (QoS-1 redelivery) rejected as replay.
# --------------------------------------------------------------------------- #


def test_duplicate_frame_rejected_as_replay():
    registry, idents = _fresh_registry()
    receiver = _make_transport("A0", registry, client_id="recv-A0-replay")
    with receiver:
        signer_bus = MessageBus(registry, ADJACENCY)
        msg = signer_bus.publish(idents["A1"], t=21, payload={"phase": 2})
        frame = serialize(msg)
        _raw_publish(topic_for("A1"), frame)
        # First delivery must verify.
        first = _drain_until(receiver, lambda d: d.ok and d.message.t == 21)
        assert first is not None
        # Re-send the identical frame: replay guard must reject the second.
        _raw_publish(topic_for("A1"), frame)
        time.sleep(0.5)
        replays = [
            r for r in receiver.bus.rejected
            if r["sender"] == "A1" and r["t"] == 21 and r["reason"] == "replay"
        ]
        assert replays, "duplicate frame was not rejected as replay"


# --------------------------------------------------------------------------- #
# Broker-down is explicit (no swallow).
# --------------------------------------------------------------------------- #


def test_connect_to_dead_broker_raises():
    registry, _ = _fresh_registry()
    # Port 1 is reserved/closed; connect must raise, not hang or swallow.
    t = _make_transport("A0", registry, port=1, connect_timeout=2.0)
    with pytest.raises(MqttTransportError):
        t.connect()


# --------------------------------------------------------------------------- #
# verify_received contract directly (no broker) — pins the reuse semantics.
# --------------------------------------------------------------------------- #


def test_verify_received_uses_bus_logic_directly():
    registry, idents = _fresh_registry()
    bus = MessageBus(registry, ADJACENCY)
    msg = MessageBus(registry, ADJACENCY).publish(idents["A1"], t=2, payload={"x": 1})
    ok = verify_received(bus, "A0", msg)
    assert ok.ok and ok.message.sender == "A1"
    # Second time -> replay via the same bus's guard.
    again = verify_received(bus, "A0", msg)
    assert not again.ok and again.reason == "replay"


# --------------------------------------------------------------------------- #
# Raw publish helper (an "attacker" / external producer on a topic).
# --------------------------------------------------------------------------- #


def _raw_publish(topic: str, frame: bytes, qos: int = 1):
    """Publish ``frame`` to ``topic`` with a throwaway client; wait for ack."""
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    c.connect(HOST, PORT, keepalive=30)
    c.loop_start()
    try:
        info = c.publish(topic, frame, qos=qos)
        info.wait_for_publish(timeout=5.0)
    finally:
        c.disconnect()
        c.loop_stop()
