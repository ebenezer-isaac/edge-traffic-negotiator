"""§6.2 EV-incident staging for IntegratedSystem (split out to keep system.py
under the file-size ceiling).

``run_ev_incident(system)`` stages a NAIVE-victim (corroboration_required=False)
phantom-claim + real-EV incident over the 2x2 grid, with an AuditLog injected so
the §11 EV records are emitted INLINE, and returns a ``SystemResult``. It reuses
the orchestrator's own builders (identities / registry / agent / registry mirror
/ audit bundle / backends) via the passed ``system`` instance.
"""
from __future__ import annotations

from audit_log import AuditLog
from conservation import ConservationChecker
from emergency_controller import EmergencyController
from message_bus import MessageBus
from system_fakeconn import (
    FakeConn, coordination_counts, config_dict, fake_traffic_summary,
)


def flatten_entries(audit) -> tuple[dict, ...]:
    """Flatten audit entries to the §11 producer shape (the reader's `flatten`):
    lift ``event.*`` to the top level, PRESERVE the envelope ``seq``, and carry the
    envelope issuer + signature (the keyless sighting's §11 `signature` layer)."""
    if audit is None:
        return ()
    return tuple(
        {**e["event"], "seq": e["seq"], "issuer": e["issuer"],
         "entry_signature": e["signature"]}
        for e in audit.entries()
    )


def run_ev_incident(system):
    """Stage a NAIVE-victim phantom-claim + real-EV incident (§6.2).

    HONEST exploit-then-defend (the servable phantom DOES commandeer the naive
    victim; the defended gate refuses it). The AUDITED incident is the NAIVE leg
    (what §6.2 scopes); a fresh unaudited DEFENDED leg is the contrast assertion.

    NAIVE leg (audited), two scripted ticks over A0 (corroboration_required=False):
      * PHANTOM tick: a compromised-but-approved neighbour (A1) signs a phantom
        ev_claim to A0 for a SERVABLE approach ("A1A0" = phase 0). MaxPressure
        prefers phase 1, so the naive victim admitting the phantom COMMANDEERS the
        signal to phase 0 (executed != baseline) -- the exploit LANDS (recorded).
      * REAL tick: a real EV is sensed LOCALLY on A0's phase-0 in-lane, so A0
        PREEMPTS to phase 0 (causal). A coordination decision AND an EV decision
        fire the SAME tick; the EV decision (its driving inputs carry an ev_id) is
        the causal one.
    DEFENDED leg (contrast, unaudited): the SAME servable phantom "A1A0" with NO
    corroborating sighting is REFUSED (executed == baseline, no preempt).
    """
    from system import SystemResult, _GRID_ADJACENCY, _GRID_TLS

    cfg = system.config
    adjacency = {k: list(v) for k, v in _GRID_ADJACENCY.items()}
    identities = system._build_identities(list(_GRID_TLS))
    registry, registry_events = system._build_registry(identities)
    bus = MessageBus(registry, adjacency)
    ev_bus = MessageBus(registry, adjacency)
    checker = ConservationChecker(tolerance=cfg.tolerance)
    audit = AuditLog() if cfg.audit else None
    registry_appended = system._mirror_registry(audit, registry_events, identities)

    # MaxPressure prefers phase 1 (B0A0_0 large); phase 0 executed can ONLY come
    # from an EV path (phantom-admitted or real-sensed) -> a visible commandeering.
    conn = FakeConn({"A1A0_0": 1, "B0A0_0": 8, "A0A1_0": 0, "A0B0_0": 0})
    ctrl = EmergencyController(
        conn, ["A0"], system._build_agent(), identities=identities,
        registry=registry, bus=bus, adjacency=adjacency, checker=checker,
        slm_junctions=["A0"], gate=cfg.gate, coord_weight=cfg.coord_weight,
        ev_bus=ev_bus, corroboration_required=False, preemption_enabled=True,
        advance_claims_enabled=True, verbose=False, audit_log=audit,
    )
    st = ctrl.tls["A0"]
    phantom_id, real_id = "PHANTOM-AMB", "AMB-REAL"
    servable_edge = "A1A0"  # phase-0 approach: a servable phantom target
    baseline = 1  # StubAgent argmax over halting -> phase 1 (B0A0_0 largest)

    # PHANTOM tick: honest coord claim from A1 + a SERVABLE phantom EV claim. The
    # naive victim admits it and COMMANDEERS the signal to phase 0 (the exploit).
    conn.simulation.advance(1.0)
    bus.publish(identities["A1"], 0,
                {"toward": {"A0": {"release": 1, "queue_forecast": 1}}})
    ctrl.inject_phantom_claim("A1", "A0", phantom_id, servable_edge)
    phantom_executed = ctrl.decide("A0", st)

    # REAL tick: a real EV enters within ev_horizon on A0's phase-0 in-lane.
    # (Advancing the scripted conn state simulates the world moving on, as the
    # harness's set_observed does; each map is REBUILT, never mutated in place.)
    conn.simulation.advance(1.0)
    real_t = float(conn.simulation.getTime())
    conn.lane._vehicles = {**conn.lane._vehicles, "A1A0_0": (real_id,)}
    conn.vehicle._classes = {**conn.vehicle._classes, real_id: "emergency"}
    conn.vehicle._positions = {**conn.vehicle._positions, real_id: 190.0}
    bus.publish(identities["A1"], 1,
                {"toward": {"A0": {"release": 1, "queue_forecast": 1}}})
    real_executed = ctrl.decide("A0", st)

    # DEFENDED contrast leg: a fresh victim with corroboration_required=True refuses
    # the SAME servable phantom (no independent sighting -> not admissible). Fresh
    # conn + audit=None: this leg is a contrast assertion, not the audited incident.
    def_conn = FakeConn({"A1A0_0": 1, "B0A0_0": 8, "A0A1_0": 0, "A0B0_0": 0})
    def_ctrl = EmergencyController(
        def_conn, ["A0"], system._build_agent(), identities=identities,
        registry=registry, bus=MessageBus(registry, adjacency), adjacency=adjacency,
        checker=ConservationChecker(tolerance=cfg.tolerance), slm_junctions=["A0"],
        gate=cfg.gate, coord_weight=cfg.coord_weight,
        ev_bus=MessageBus(registry, adjacency), corroboration_required=True,
        preemption_enabled=True, advance_claims_enabled=True, verbose=False,
        audit_log=None,
    )
    def_ctrl.inject_phantom_claim("A1", "A0", phantom_id, servable_edge)
    def_executed = def_ctrl.decide("A0", def_ctrl.tls["A0"])
    def_ev = [e for e in def_ctrl.ev_events if e["ev_id"] == phantom_id]
    phantom_preempted_defended = (bool(def_ev)
                                  and def_ev[0]["preempt_phase"] is not None
                                  and def_executed != baseline)

    phantom_ev = [e for e in ctrl.ev_events if e["ev_id"] == phantom_id]
    real_ev = [e for e in ctrl.ev_events if e["source"] == "local_sensing"]
    ev_incident = {
        "enabled": True,
        "phantom_ev_id": phantom_id, "real_ev_id": real_id,
        "servable_edge": servable_edge,
        "victim_mode": "naive", "corroboration_required": False,
        "phantom_recorded": bool(phantom_ev),
        "phantom_admissible": bool(phantom_ev) and phantom_ev[0]["admissible"],
        # NAIVE: the servable phantom COMMANDEERS the signal (the exploit lands).
        "phantom_preempted": (bool(phantom_ev)
                              and phantom_ev[0]["preempt_phase"] is not None
                              and phantom_executed != baseline),
        "phantom_executed": phantom_executed,
        # DEFENDED contrast: the same phantom is refused by the corroboration gate.
        "phantom_preempted_defended": phantom_preempted_defended,
        "phantom_executed_defended": def_executed,
        "real_recorded": bool(real_ev),
        "real_preempted": (bool(real_ev)
                           and real_ev[0]["preempt_phase"] is not None
                           and real_executed != baseline),
        "real_executed": real_executed, "baseline": baseline,
        "real_tick_t": real_t,
    }
    return SystemResult(
        config=config_dict(cfg),
        traffic=fake_traffic_summary(2, len(ctrl.events)),
        coordination=coordination_counts(ctrl, bus),
        audit=system._audit_bundle(audit, registry_appended),
        backends=system._backends(live=False),
        audit_entries=flatten_entries(audit),
        ev_incident=ev_incident,
    )
