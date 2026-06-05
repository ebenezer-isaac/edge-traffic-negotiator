"""End-to-end tests for the MQTT-transport coordinated control loop.

``src/run_mqtt_coord.py`` swaps the in-process ``MessageBus`` for a real broker
*without touching* ``CoordinatedController``: each junction's signed publications
flow through an :class:`MqttBusAdapter` -> :class:`MqttTransport` -> broker, and
its inbox is fed from MQTT-verified deliveries. These tests assert the swap is
TRANSPARENT (identical decision-affecting semantics to the in-process run), that
the security gate is unchanged end-to-end (tampered / revoked / non-neighbour
still rejected over the wire), and that a broker-down condition degrades
gracefully with a clear status.

Live-broker tests are gated on broker availability and SKIP cleanly when no
broker is reachable (like ``test_mqtt_transport.py``), so the suite is never red
merely because the spike's container is down. Set EDGE_MQTT_HOST / EDGE_MQTT_PORT
to point at the broker (defaults 127.0.0.1:1883).

``src/`` is inserted on ``sys.path`` so the bare ``import`` style used across the
project's tests works under ``python -m pytest tests``.
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
    serialize,
    topic_for,
)
import paho.mqtt.client as mqtt  # noqa: E402

import run_mqtt_coord as rmc  # noqa: E402
from run_mqtt_coord import MqttBusAdapter, broker_reachable, run  # noqa: E402

HOST = os.environ.get("EDGE_MQTT_HOST", "127.0.0.1")
PORT = int(os.environ.get("EDGE_MQTT_PORT", "1883"))

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


_BROKER = _broker_up(HOST, PORT)
live = pytest.mark.skipif(
    not _BROKER,
    reason=f"no MQTT broker reachable at {HOST}:{PORT} (start eclipse-mosquitto)",
)


# A StubAgent local to the tests so a Foundry-less, deterministic agent drives
# the run (mirrors coordinated_controller.StubAgent, imported to stay in lockstep).
from coordinated_controller import StubAgent  # noqa: E402


def _raw_publish(topic: str, frame: bytes, qos: int = 1):
    """Publish a frame to a topic with a throwaway client (an external producer)."""
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    c.connect(HOST, PORT, keepalive=30)
    c.loop_start()
    try:
        info = c.publish(topic, frame, qos=qos)
        info.wait_for_publish(timeout=5.0)
    finally:
        c.disconnect()
        c.loop_stop()


def _fresh_registry():
    registry = Registry()
    idents = {jid: JunctionIdentity(jid) for jid in ("A0", "A1", "B0", "B1")}
    for jid, ident in idents.items():
        registry.register(jid, ident.public_key)
    return registry, idents


def _drain_reasons(transport, predicate, deadline_s=2.0):
    """Poll a transport's verified queue until timeout (side effect: feeds bus)."""
    end = time.time() + deadline_s
    while time.time() < end:
        transport.poll(timeout=0.2)


# --------------------------------------------------------------------------- #
# broker-down: explicit + graceful (no broker needed for this one).
# --------------------------------------------------------------------------- #


def test_broker_reachable_false_on_dead_port():
    # Port 1 is reserved/closed: the pre-flight must report it down, not hang.
    assert broker_reachable(HOST, 1, timeout=1.0) is False


def test_run_requires_broker_raises_when_down():
    # require_broker=True (default) must raise a clear MqttTransportError before
    # any sim is started, rather than silently running fully degraded.
    with pytest.raises(MqttTransportError):
        run(seed=42, end=10, agent=StubAgent(), port=1, require_broker=True)


def test_run_broker_down_degrades_gracefully_with_status():
    # require_broker=False: a missing broker is reported as a clear status, not a
    # crash. This is the spike's degradation contract (missing report = no update).
    m = run(seed=42, end=10, agent=StubAgent(), port=1, require_broker=False)
    assert m["broker_up"] is False
    assert m["transport"] == "mqtt"
    assert m["verified_messages"] == 0
    assert "status" in m and isinstance(m["status"], str) and m["status"]


# --------------------------------------------------------------------------- #
# adapter unit: bus-shaped seam routes publish/inbox over the transport.
# --------------------------------------------------------------------------- #


def test_adapter_rejects_non_transport():
    with pytest.raises(TypeError):
        MqttBusAdapter(object())


@live
def test_adapter_publish_then_inbox_roundtrips_verified():
    # A0 receives; A1 (its neighbour) publishes via its own adapter. A0's inbox
    # (drained from MQTT-verified deliveries) must surface A1's signed report.
    registry, idents = _fresh_registry()
    recv_tr = MqttTransport("A0", MessageBus(registry, ADJACENCY),
                            host=HOST, port=PORT, client_id="t-recvA0")
    send_tr = MqttTransport("A1", MessageBus(registry, ADJACENCY),
                            host=HOST, port=PORT, client_id="t-sendA1")
    with recv_tr, send_tr:
        recv = MqttBusAdapter(recv_tr)
        send = MqttBusAdapter(send_tr)
        send.publish(idents["A1"], t=5, payload={"toward": {"A0": {"release": 4}}})
        # Let the report round-trip + verify, then drain A0's inbox.
        got = []
        end = time.time() + 5.0
        while time.time() < end and not got:
            got = recv.inbox("A0")
            if not got:
                time.sleep(0.05)
        assert got, "A1's signed report never surfaced on A0's MQTT-fed inbox"
        msg = got[0]
        assert isinstance(msg, NeighborMessage)
        assert msg.sender == "A1" and msg.t == 5
        assert msg.payload == {"toward": {"A0": {"release": 4}}}


# --------------------------------------------------------------------------- #
# end-to-end: a coordinated run over the broker carries >0 verified messages
# and is TRANSPARENT vs the in-process run (identical decision-affecting counts).
# --------------------------------------------------------------------------- #


@live
def test_coordinated_run_over_broker_carries_verified_messages():
    m = run(seed=42, end=300, agent=StubAgent(), host=HOST, port=PORT)
    assert m["broker_up"] is True
    assert m["transport"] == "mqtt"
    assert m["slm_decisions"] > 0
    assert m["verified_messages"] > 0, "no neighbour messages verified over MQTT"
    # The adapter retries a transient NO_CONN (lossy-link blip) before giving up,
    # so with the broker up publish errors should be rare. We allow a tiny bound
    # (not strictly zero) because a momentary keepalive blip under contention is a
    # realistic roadside condition the fast path must tolerate gracefully — and a
    # blipped publish is recorded as published={"error":...}, NOT a crash.
    assert m["publish_errors"] <= 2, (
        f"too many publish failures with broker up: {m['publish_errors']}")


@live
def test_transport_swap_is_transparent_vs_in_process():
    # The proof the broker adds transport only: a coordinated run over MQTT must
    # reproduce the in-process run's decision-affecting counts. slm_decisions is
    # deterministic (sim-driven) -> exact. The message/detection counts depend on
    # async delivery timing, so we require them to land within a small tolerance
    # of the in-process baseline AND to be strictly positive (transport works).
    import run_coordinated as rc

    mqttm = run(seed=42, end=300, agent=StubAgent(), host=HOST, port=PORT,
                settle_s=0.02)
    inproc = rc.run("coordinated", seed=42, end=300, agent=StubAgent())

    # Sim-driven, transport-independent: must match exactly.
    assert mqttm["slm_decisions"] == inproc["slm_decisions"]

    # Transport-carried counts: positive and close to the in-process baseline.
    assert mqttm["verified_messages"] > 0
    assert inproc["verified_messages"] > 0
    assert abs(mqttm["verified_messages"] - inproc["verified_messages"]) <= 4, (
        f"verified messages diverged too far: mqtt={mqttm['verified_messages']} "
        f"inproc={inproc['verified_messages']}")
    # Detections are downstream of which decision saw which report; allow a small
    # timing-driven band but require the same order of magnitude.
    assert mqttm["detections"] > 0
    assert abs(mqttm["detections"] - inproc["detections"]) <= 10, (
        f"detections diverged too far: mqtt={mqttm['detections']} "
        f"inproc={inproc['detections']}")


# --------------------------------------------------------------------------- #
# security end-to-end: the SAME rejection reasons reach the receiver-side bus
# over the wire (transport makes no trust decision of its own).
# --------------------------------------------------------------------------- #


@live
def test_tampered_payload_rejected_end_to_end():
    registry, idents = _fresh_registry()
    recv_tr = MqttTransport("A0", MessageBus(registry, ADJACENCY),
                            host=HOST, port=PORT, client_id="t-tamper-A0")
    with recv_tr:
        signer = MessageBus(registry, ADJACENCY)
        msg = signer.publish(idents["A1"], t=9, payload={"toward": {"A0": {"release": 1}}})
        forged = NeighborMessage(sender=msg.sender, t=msg.t,
                                 payload={"toward": {"A0": {"release": 999}}},
                                 signature=msg.signature)  # signature no longer matches
        _raw_publish(topic_for("A1"), serialize(forged))
        _drain_reasons(recv_tr, None, deadline_s=2.0)
        reasons = [r["reason"] for r in recv_tr.bus.rejected
                   if r["sender"] == "A1" and r["t"] == 9]
        assert "bad_signature" in reasons


@live
def test_revoked_sender_rejected_end_to_end():
    registry, idents = _fresh_registry()
    recv_tr = MqttTransport("A0", MessageBus(registry, ADJACENCY),
                            host=HOST, port=PORT, client_id="t-revoke-A0")
    with recv_tr:
        signer = MessageBus(registry, ADJACENCY)
        msg = signer.publish(idents["A1"], t=11, payload={"toward": {"A0": {"release": 1}}})
        registry.revoke("A1")  # approved at sign time, revoked before delivery
        _raw_publish(topic_for("A1"), serialize(msg))
        _drain_reasons(recv_tr, None, deadline_s=2.0)
        reasons = [r["reason"] for r in recv_tr.bus.rejected
                   if r["sender"] == "A1" and r["t"] == 11]
        assert "revoked" in reasons


@live
def test_non_neighbour_rejected_end_to_end():
    registry, idents = _fresh_registry()
    # A0's neighbours are A1, B0. B1 is approved+registered but NOT adjacent.
    recv_tr = MqttTransport("A0", MessageBus(registry, ADJACENCY),
                            host=HOST, port=PORT, client_id="t-nonadj-A0")
    with recv_tr:
        signer = MessageBus(registry, ADJACENCY)
        msg = signer.publish(idents["B1"], t=3, payload={"toward": {"A0": {"release": 1}}})
        _raw_publish(topic_for("B1"), serialize(msg))
        _drain_reasons(recv_tr, None, deadline_s=2.0)
        reasons = [r["reason"] for r in recv_tr.bus.rejected
                   if r["sender"] == "B1" and r["t"] == 3]
        assert "not_neighbour" in reasons


@live
def test_unknown_sender_rejected_end_to_end():
    registry, _ = _fresh_registry()
    # Add a synthetic, never-registered neighbour GHOST to A0's adjacency.
    adj = {**ADJACENCY, "A0": ["A1", "B0", "GHOST"]}
    recv_tr = MqttTransport("A0", MessageBus(registry, adj),
                            host=HOST, port=PORT, client_id="t-ghost-A0")
    with recv_tr:
        ghost = JunctionIdentity("GHOST")  # never registered
        signer = MessageBus(registry, adj)
        msg = signer.publish(ghost, t=13, payload={"toward": {"A0": {"release": 1}}})
        _raw_publish(topic_for("GHOST"), serialize(msg))
        _drain_reasons(recv_tr, None, deadline_s=2.0)
        reasons = [r["reason"] for r in recv_tr.bus.rejected
                   if r["sender"] == "GHOST" and r["t"] == 13]
        assert "unknown_sender" in reasons


@live
def test_duplicate_frame_rejected_as_replay_end_to_end():
    registry, idents = _fresh_registry()
    recv_tr = MqttTransport("A0", MessageBus(registry, ADJACENCY),
                            host=HOST, port=PORT, client_id="t-replay-A0")
    with recv_tr:
        signer = MessageBus(registry, ADJACENCY)
        msg = signer.publish(idents["A1"], t=21, payload={"toward": {"A0": {"release": 2}}})
        frame = serialize(msg)
        _raw_publish(topic_for("A1"), frame)
        # first delivery verifies
        end = time.time() + 5.0
        first = None
        while time.time() < end and first is None:
            first = recv_tr.poll(timeout=0.2)
        assert first is not None and first.ok
        # identical frame again -> replay guard rejects the second
        _raw_publish(topic_for("A1"), frame)
        _drain_reasons(recv_tr, None, deadline_s=2.0)
        replays = [r for r in recv_tr.bus.rejected
                   if r["sender"] == "A1" and r["t"] == 21 and r["reason"] == "replay"]
        assert replays, "duplicate frame was not rejected as replay over MQTT"
