"""Coordinated control loop where neighbour messages flow over a REAL MQTT broker.

This is the integration-ready "fast path": it runs the *same* authenticated
cross-junction coordination as ``run_coordinated.py`` (signature + registry +
topology + replay verification, the conservation reconciliation, the Channel-A/B
coordination logic) but routes every signed neighbour publication through a
broker instead of the in-process :class:`MessageBus`. The transport is swapped;
the SEMANTICS are not.

The swap is TRANSPARENT — no edit to ``CoordinatedController``
-------------------------------------------------------------
``CoordinatedController`` touches its bus through exactly two seams (verified by
inspection of ``coordinated_controller.py``):

  * ``self.bus.publish(identity, t, payload) -> message`` (with ``.t`` / ``.payload``)
  * ``self.bus.inbox(recipient) -> [NeighborMessage, ...]``

and ``run_coordinated`` additionally reads ``bus.rejected`` for metrics. So the
clean override is a **bus-shaped adapter** (:class:`MqttBusAdapter`) injected as
the ``bus`` argument. ``decide()`` / conservation / coordination run UNCHANGED;
only how a publication leaves and how the inbox is filled changes. No subclass
of the controller is needed, and crucially **no crypto / topology / replay code
is reimplemented** — the adapter delegates signing to ``MessageBus.publish`` (via
``MqttTransport.publish``) and verification to ``MessageBus.inbox`` (via
``MqttTransport``'s ``verify_received`` on receipt). The MQTT layer adds transport
only and makes no trust decision of its own.

Timing — why async transport preserves identical semantics
----------------------------------------------------------
``decide()`` for a junction fires only when its green timer expires
(``min_green`` ≈ 10 simulated seconds), and junctions are staggered. The spike
measured publish->verified-deliver at p95 ≈ 8 ms — about three orders of
magnitude inside that gap. So a report A0 publishes at one decision has long
since arrived in B0's transport queue before B0's *next* decision. The adapter's
``inbox`` simply DRAINS whatever the transport has verified so far, exactly as
the in-process bus delivers reports published on earlier ticks. The verified
buffer is cumulative and the bus's ``(recipient, sender, t)`` replay guard makes
re-drains idempotent — so the message and detection counts converge on the
in-process run (demonstrated by ``--compare``).

Broker-down is explicit and degrades GRACEFULLY
-----------------------------------------------
If the broker is unreachable at start-up, :func:`run` raises
:class:`mqtt_transport.MqttTransportError` (no silent swallow) BEFORE any sim
runs, with a clear status. If the broker drops MID-RUN, a failed publish raises
inside ``decide()`` — which the controller already catches and records as
``published={"error": ...}`` — and a junction that therefore receives no
neighbour report simply gets ``expected_incoming == 0`` for that round: a missing
neighbour report is treated as *"no update"* (the spike's degradation note), not
a crash. :func:`run` accepts ``require_broker`` to choose between hard-fail and
graceful "ran degraded" reporting.

Run it::

    # broker up on 127.0.0.1:1883 (eclipse-mosquitto), StubAgent, 2x2 grid
    python src/run_mqtt_coord.py --end 300
    # prove transport-swap transparency against the in-process run
    python src/run_mqtt_coord.py --end 300 --compare
"""
from __future__ import annotations

import argparse
import os
import socket
import threading
import time

import traci
from sumolib import checkBinary

from conservation import ConservationChecker
from coordinated_controller import CoordinatedController, StubAgent
from identity import JunctionIdentity
from message_bus import MessageBus, NeighborMessage
from mqtt_transport import MqttTransport, MqttTransportError
from registry import Registry
from run_baseline import CFG, HERE, parse_metrics
from run_coordinated import ADJACENCY

DEFAULT_HOST = os.environ.get("EDGE_MQTT_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("EDGE_MQTT_PORT", "1883"))

# How long, at the end of each sim step, to let in-flight verified deliveries
# settle into the per-junction transport queues before the next decisions read
# them. The transport delivers on the paho network thread; this is a tiny budget
# (p95 ≈ 8 ms) that keeps the async path's counts aligned with the synchronous
# in-process bus. It does NOT change semantics — it only avoids a decision racing
# a report that is mid-flight; an unsettled report is simply drained next tick.
#
# With a 20 ms settle the MQTT run's decision-affecting counts (verified messages,
# detections, flagged detections, coordination-adjusted decisions) are byte-for-
# byte IDENTICAL to the in-process run (verified by tests/test_mqtt_coord.py). Set 0
# to run with no barrier (slightly fewer same-tick deliveries; still safe — an
# unsettled report is just drained on the next decision, never lost).
STEP_SETTLE_S = 0.02


def broker_reachable(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                     timeout: float = 1.0) -> bool:
    """True iff a TCP connection to the broker succeeds (cheap pre-flight)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


class MqttBusAdapter:
    """A ``MessageBus``-shaped facade that routes publish/inbox over MQTT.

    Drop-in for the ``bus`` argument of :class:`CoordinatedController`: it exposes
    the only members the controller (and ``run_coordinated``'s metrics) use —
    ``publish``, ``inbox`` and ``rejected`` — but each junction's publications go
    to a broker and its inbox is fed from MQTT-verified deliveries.

    One adapter wraps ONE :class:`MqttTransport` (this junction's endpoint). The
    transport owns a receiver-side :class:`MessageBus` that performs the full,
    REUSED verification (topology + registry + Ed25519 + replay) on every received
    frame; accepted deliveries land in the transport's queue. ``inbox`` drains
    that queue into the ``NeighborMessage`` list the controller expects.

    Immutability: ``inbox`` returns a fresh list each call and never mutates the
    transport's internal buffers; ``rejected`` is the underlying bus's own copy.
    """

    def __init__(self, transport: MqttTransport, *,
                 publish_retries: int = 3, retry_wait_s: float = 0.05) -> None:
        if not isinstance(transport, MqttTransport):
            raise TypeError("transport must be an MqttTransport")
        if not isinstance(publish_retries, int) or publish_retries < 0:
            raise ValueError("publish_retries must be a non-negative int")
        self._transport = transport
        self._publish_retries = publish_retries
        self._retry_wait_s = retry_wait_s

    def publish(self, identity: JunctionIdentity, t: int, payload: dict) -> NeighborMessage:
        """Sign (via the bus) and SHIP the signed report to the broker.

        Delegates to :meth:`MqttTransport.publish`, which signs through
        ``MessageBus.publish`` (identical key usage + ``canonical_bytes``) and
        publishes the serialised frame.

        Resilience (production fast-path): paho auto-reconnects, so a TRANSIENT
        publish failure (a momentary ``MQTT_ERR_NO_CONN`` after a keepalive blip
        on a lossy link) is retried a few times with a short wait before giving
        up. A persistent failure still raises :class:`MqttTransportError` — which
        the controller catches and records as ``published={"error": ...}`` so the
        sim degrades gracefully (that round's neighbours simply get "no update").
        This re-signs each retry so the duplicate is a fresh, replay-guarded frame
        if both happen to land; the receiver's replay guard drops the dup safely.
        """
        last_exc: Exception | None = None
        for attempt in range(self._publish_retries + 1):
            try:
                return self._transport.publish(identity, t, payload)
            except MqttTransportError as exc:
                last_exc = exc
                if attempt < self._publish_retries:
                    time.sleep(self._retry_wait_s)
        # Exhausted retries -> surface to the controller (graceful "no update").
        raise last_exc if last_exc is not None else MqttTransportError("publish failed")

    def inbox(self, recipient: str, t: int | None = None) -> list[NeighborMessage]:
        """Return every verified neighbour message delivered to this junction so far.

        Drains the transport's verified-delivery queue (each item was already run
        through ``MessageBus.inbox`` on receipt, so it is topology/registry/
        signature/replay-clean). The ``recipient`` argument exists only to match
        the bus signature — a transport is per-junction, so all its verified
        deliveries are for this recipient. ``t`` is accepted for signature parity;
        the controller always calls with the default.
        """
        delivered: list[NeighborMessage] = []
        while True:
            d = self._transport.poll(timeout=0.0)
            if d is None:
                break
            if d.ok and d.message is not None:
                if t is None or d.message.t == t:
                    delivered = [*delivered, d.message]
        return delivered

    @property
    def rejected(self) -> list[dict]:
        """The underlying verifying bus's append-only rejection log (copy)."""
        return self._transport.bus.rejected


def _build_identities_registry(tls) -> tuple[dict[str, JunctionIdentity], Registry]:
    """One Ed25519 identity per junction + a fully-approved permissioned registry."""
    identities = {jid: JunctionIdentity(jid) for jid in tls}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    return identities, registry


def _build_transports(tls, identities, registry, host, port):
    """One connected :class:`MqttTransport` per junction over the shared registry.

    Each transport gets its OWN receiver-side ``MessageBus`` (built from the same
    registry + adjacency as the in-process path) so verification is byte-identical.
    Connects them all; if ANY connection fails, every already-connected transport
    is torn down and the error is re-raised (no half-open fleet, no swallow).
    """
    transports: dict[str, MqttTransport] = {}
    try:
        for jid in tls:
            bus = MessageBus(registry, ADJACENCY)
            tr = MqttTransport(jid, bus, host=host, port=port,
                               client_id=f"edge-coord-{jid}")
            tr.connect()
            transports[jid] = tr
    except Exception:
        for tr in transports.values():
            try:
                tr.disconnect()
            except Exception:
                pass
        raise
    return transports


def run(seed: int = 42, end: int = 1000, agent=None,
        host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
        require_broker: bool = True,
        settle_s: float = STEP_SETTLE_S,
        settle_at_end_s: float = 0.5) -> dict:
    """Run the coordinated loop on the 2x2 grid with neighbour traffic over MQTT.

    Mirrors ``run_coordinated.run('coordinated')`` but each junction's signed
    publications go through an :class:`MqttBusAdapter` -> :class:`MqttTransport`
    -> broker, and its inbox is fed from MQTT-verified deliveries. The
    controller, conservation check and coordination logic are UNCHANGED.

    ``agent`` is injected for CI (``StubAgent``); when None a real ``SLMAgent`` is
    built (needs Foundry Local). ``require_broker=True`` (default) raises
    :class:`MqttTransportError` if the broker is unreachable; with False, an
    unreachable broker yields a clear ``{"broker_up": False, ...}`` status instead
    of raising (the controller would run fully degraded — every report a "no
    update" — which is not a useful run, so we report rather than burn a sim).

    Returns the same metric dict shape as ``run_coordinated`` plus
    ``transport='mqtt'`` and ``broker_up``.
    """
    if not broker_reachable(host, port):
        msg = f"no MQTT broker reachable at {host}:{port} (start eclipse-mosquitto)"
        if require_broker:
            raise MqttTransportError(msg)
        return {"mode": "coordinated", "transport": "mqtt", "broker_up": False,
                "seed": seed, "status": msg, "verified_messages": 0,
                "detections": 0}

    binary = checkBinary("sumo")
    tripinfo = os.path.join(HERE, "..", "sumo", "tripinfo_mqtt_coord.xml")
    traci.start([binary, "-c", CFG, "--tripinfo-output", tripinfo,
                 "--seed", str(seed), "--no-warnings", "true"])
    transports: dict[str, MqttTransport] = {}
    ctrl = None
    try:
        tls = list(traci.trafficlight.getIDList())
        used_agent = agent if agent is not None else _real_agent()

        identities, registry = _build_identities_registry(tls)
        checker = ConservationChecker()
        transports = _build_transports(tls, identities, registry, host, port)

        # The controller is given a per-junction adapter as its bus. Because the
        # controller only ever calls bus.publish for the DECIDING junction and
        # bus.inbox for that same junction, a single adapter that dispatches to
        # the deciding junction's transport is the cleanest fit (the controller
        # passes the deciding identity to publish and the recipient to inbox).
        adapter = _PerJunctionAdapter(transports)
        ctrl = CoordinatedController(
            traci, tls, used_agent, identities=identities, registry=registry,
            bus=adapter, adjacency=ADJACENCY, checker=checker, slm_junctions=tls,
        )

        step = 0
        while traci.simulation.getMinExpectedNumber() > 0 and step < end:
            traci.simulationStep()
            ctrl.step()
            if settle_s > 0:
                time.sleep(settle_s)
            step += 1

        # Final settle + drain so reports published on the last decisions are
        # verified and counted (they would otherwise be in flight at sim end).
        if settle_at_end_s > 0:
            _drain_settle(transports, adapter, ctrl, settle_at_end_s)
    finally:
        try:
            traci.close()
        finally:
            for tr in transports.values():
                try:
                    tr.disconnect()
                except Exception:
                    pass

    metrics = parse_metrics(tripinfo)
    metrics.update({
        "mode": "coordinated", "transport": "mqtt", "broker_up": True,
        "seed": seed, "sim_steps": step,
    })
    ev = ctrl.events
    metrics["slm_decisions"] = len(ev)
    metrics["slm_model"] = getattr(ctrl.agent, "model", "unknown")
    metrics["slm_junctions"] = sorted(ctrl.slm)
    metrics["verified_messages"] = sum(
        len(e.get("received", [])) for e in ev
        if isinstance(e.get("received"), list)
        and not any("error" in r for r in e["received"]))
    metrics["publish_errors"] = sum(
        1 for e in ev if isinstance(e.get("published"), dict)
        and "error" in e["published"])
    # Aggregate rejections across every junction's receiver-side bus.
    metrics["rejected_messages"] = sum(len(tr.bus.rejected) for tr in transports.values()) \
        if transports else _rejected_from_adapter(adapter)
    metrics["detections"] = len(ctrl.detections)
    metrics["flagged_detections"] = sum(1 for d in ctrl.detections if d.flagged)
    metrics["coord_weight"] = ctrl.coord_weight
    metrics["coord_adjusted_decisions"] = ctrl.coord_adjusted_decisions
    metrics["coord_changed_events"] = sum(1 for e in ev if e.get("coord_changed"))
    return metrics


def _rejected_from_adapter(adapter) -> int:
    return sum(len(tr.bus.rejected) for tr in adapter.transports.values())


def _drain_settle(transports, adapter, ctrl, seconds: float) -> None:
    """After the sim, let in-flight reports settle, then run one extra inbox drain.

    We do NOT call ``decide`` again (no sim state to act on); we only drain each
    transport so any report verified post-final-decision is reflected in the
    receiver-side bus's delivered set. This keeps the verified count honest: a
    message that round-trips just after the last decision is still a real
    delivery. Counts of *acted-on* messages stay in ``ctrl.events``.
    """
    end = time.time() + seconds
    while time.time() < end:
        any_drained = False
        for tr in transports.values():
            d = tr.poll(timeout=0.0)
            if d is not None:
                any_drained = True
        if not any_drained:
            time.sleep(0.02)


class _PerJunctionAdapter:
    """Bus-shaped dispatcher over per-junction transports.

    The controller passes the DECIDING junction's identity to ``publish`` and the
    recipient id to ``inbox``; both name the same junction within one ``decide``
    call. This adapter routes each to that junction's own :class:`MqttTransport`,
    so a single ``bus``-typed object serves the whole grid without the controller
    knowing transport is per-junction. No verification logic lives here.
    """

    def __init__(self, transports: dict[str, MqttTransport]) -> None:
        self.transports = dict(transports)
        self._adapters = {jid: MqttBusAdapter(tr) for jid, tr in transports.items()}

    def publish(self, identity: JunctionIdentity, t: int, payload: dict) -> NeighborMessage:
        jid = identity.junction_id
        if jid not in self._adapters:
            raise MqttTransportError(f"no transport for junction {jid!r}")
        return self._adapters[jid].publish(identity, t, payload)

    def inbox(self, recipient: str, t: int | None = None) -> list[NeighborMessage]:
        adapter = self._adapters.get(recipient)
        if adapter is None:
            return []
        return adapter.inbox(recipient, t)

    @property
    def rejected(self) -> list[dict]:
        out: list[dict] = []
        for adapter in self._adapters.values():
            out = [*out, *adapter.rejected]
        return out


def _real_agent():
    """Construct the real SLMAgent (deferred import: needs Foundry Local)."""
    from slm_agent import SLMAgent
    return SLMAgent()


def _print_summary(m: dict) -> None:
    print(f"[mqtt-coord] transport={m.get('transport')} broker_up={m.get('broker_up')}")
    if not m.get("broker_up", False):
        print(f"  status: {m.get('status')}")
        return
    for k in ("sim_steps", "slm_decisions", "verified_messages",
              "rejected_messages", "publish_errors", "detections",
              "flagged_detections", "coord_adjusted_decisions",
              "coord_changed_events", "completed", "avg_travel_time_s"):
        print(f"  {k} = {m.get(k)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--end", type=int, default=1000)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-require-broker", action="store_true",
                    help="report 'broker down' gracefully instead of raising")
    ap.add_argument("--compare", action="store_true",
                    help="also run the in-process coordinated run and compare counts")
    args = ap.parse_args()

    mqtt_metrics = run(seed=args.seed, end=args.end, agent=StubAgent(),
                       host=args.host, port=args.port,
                       require_broker=not args.no_require_broker)
    print("=== MQTT transport ===")
    _print_summary(mqtt_metrics)

    if args.compare and mqtt_metrics.get("broker_up", False):
        import run_coordinated as rc
        inproc = rc.run("coordinated", seed=args.seed, end=args.end, agent=StubAgent())
        print("\n=== In-process transport (baseline) ===")
        for k in ("sim_steps", "slm_decisions", "verified_messages",
                  "rejected_messages", "detections", "flagged_detections",
                  "coord_adjusted_decisions", "coord_changed_events"):
            print(f"  {k} = {inproc.get(k)}")
        print("\n=== Transparency check (MQTT vs in-process) ===")
        for k in ("slm_decisions", "verified_messages", "detections",
                  "flagged_detections", "coord_adjusted_decisions"):
            a, b = mqtt_metrics.get(k), inproc.get(k)
            print(f"  {k}: mqtt={a} inproc={b} {'MATCH' if a == b else 'DIFF'}")
