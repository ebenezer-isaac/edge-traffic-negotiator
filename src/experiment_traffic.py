"""H1 HEADLINE experiment harness (MASTER-SPEC §3 H1 + §8): the on-device SLM
traffic-signal controller vs the MaxPressure baseline on the REAL Euston Road
(A501) corridor, with the tamper-evident audit layer LIVE on BOTH arms.

This module is the harness (+ a SMOKE entrypoint), NOT the powered sweep. It runs
ONE demand + ONE seed under two controllers and produces a first REAL, honestly
labelled PILOT/SMOKE data point. The full model x config sweep (§3, §8) reuses
this harness later with a longer horizon and n>=30 seeds.

The two arms (SAME net + SAME demand + SAME seed; ONLY the agent differs)
------------------------------------------------------------------------
  * ``maxpressure`` -- the deterministic baseline. Driven through the EXISTING
    ``HybridController`` wiring with a NULL agent that never proposes, so the
    MaxPressure shield stands on every decision interval: this IS MaxPressure
    (Varaiya 2013), run on identical machinery to the SLM arm so the comparison
    is apples-to-apples (only the proposal source changes).
  * ``slm_myopic`` -- the on-device SLM controller (Phi-4-mini via Foundry Local),
    MYOPIC: it sees only its OWN per-junction green-phase queues (no neighbour
    note, no coordination term). It PROPOSES a phase via ``choose_phase``; the
    deterministic MaxPressure shield inside ``HybridController`` VALIDATES it and
    falls back to the MaxPressure choice on any invalid/None proposal. The shield
    is NEVER bypassed and NEVER reimplemented here.

Metrics (via ``metrics.py`` -- survivorship-robust, never ``len(tripinfo)``)
--------------------------------------------------------------------------
completed = trips with arrival>=0 (``throughput``); mean delay = ``mean_network_delay``
(over ALL departed, so a controller cannot win by stranding slow trips); the biased
completed-only mean + the completed median are reported alongside for context;
teleports counted live from ``traci.simulation.getStartingTeleportNumber`` (the
gridlock signal). SLM per-decision ``choose_phase`` latency is profiled via
``slm_latency.summarize_latency`` (FLPerformance nearest-rank, warmup>=1).

Audit LIVE on both arms
-----------------------
A fresh ``AuditLog`` is injected per arm; every controller decision is mirrored in
as a signed, hash-chained ``kind:"decision"`` record (issuer = the deciding
junction's Ed25519 identity). After each run we ASSERT ``verify_chain()`` and a
Merkle inclusion proof for a sampled decision, and record the decision-record
count -- the accountability layer runs on the real controller, not a mock.

Foundry precondition
--------------------
``probe_foundry_determinism`` runs FIRST. If Foundry Local is down or non-
deterministic at temp 0 the SLM arm is SKIPPED-WITH-A-RECORD (never fabricated);
the MaxPressure baseline still runs (it needs no model).

PILOT/SMOKE caveats (§8): Euston demand is DfT-daily-AADF calibrated (magnitude +
mix real, temporal profile assumed), so this is PILOT-gated -- and a SMOKE run is
n=1 at a short horizon, so NO significance/inferential claim is made.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from time import perf_counter

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from audit_log import AuditLog, verify_inclusion  # noqa: E402
from hybrid_controller import HybridController  # noqa: E402
from identity import JunctionIdentity  # noqa: E402
from metrics import (  # noqa: E402
    avg_travel_time_completed,
    mean_network_delay,
    parse_tripinfo,
    throughput,
)
from slm_latency import summarize_latency  # noqa: E402

RESULTS = os.path.normpath(os.path.join(_HERE, "..", "results"))
_SUMO_EUSTON = os.path.normpath(os.path.join(_HERE, "..", "sumo", "euston"))
NET = os.path.join(_SUMO_EUSTON, "euston_spine.net.xml")
# Default demand = base.rou.xml (DfT-daily-AADF, assumed peak fraction). Set
# EUSTON_ROUTES=base_hourly.rou.xml to run against the MEASURED peak-hour magnitude
# (DfT raw survey; still a §8 PILOT). Default unchanged, so committed runs are stable.
ROUTES = os.environ.get("EUSTON_ROUTES") or os.path.join(_SUMO_EUSTON, "base.rou.xml")

# The event-gated decision interval the SLM must keep up with (§3: "~10 s"). This
# equals HybridController's min_green, so it is the cadence choose_phase runs at.
DECISION_INTERVAL_S = 10


# --------------------------------------------------------------------------- #
# Agents. Both expose the SLMAgent.choose_phase signature so HybridController is
# agnostic to which arm it is driving.
# --------------------------------------------------------------------------- #
class NullAgent:
    """Baseline agent: never proposes, so the MaxPressure shield always stands.

    HybridController.decide returns the MaxPressure choice whenever the proposal
    is None -- so a NullAgent turns HybridController into pure MaxPressure while
    keeping the audit/decision-logging path identical to the SLM arm.
    """

    model = "maxpressure(null-agent-shield)"

    def choose_phase(self, junction_id, num_phases, halting_per_phase,
                     neighbor_note: str = "", phase_context=None):  # noqa: ARG002
        return None


class TimingAgent:
    """Wrap a real agent, timing every ``choose_phase`` call (per-decision latency).

    ``forward_note`` controls the config arm (MASTER-SPEC §3 {myopic, +coordination,
    +prediction}):
      * ``False`` (DEFAULT, MYOPIC) -- the neighbour note is DROPPED, so the SLM
        sees only its own per-junction queues (the H1 myopic config).
      * ``True`` (+coordination / +prediction) -- the note IS forwarded, so the SLM
        sees the coordination/prediction context the CoordinatedController assembled.
    Records per-call wall-clock so ``slm_latency.summarize_latency`` can profile
    choose_phase against the decision interval, identically across all arms.
    """

    def __init__(self, inner, *, forward_note: bool = False):
        self.inner = inner
        self.model = getattr(inner, "model", "unknown")
        self.forward_note = bool(forward_note)
        self.latencies_s: list[float] = []
        self.calls = 0
        self.none_returns = 0
        self.notes_forwarded = 0

    def choose_phase(self, junction_id, num_phases, halting_per_phase,
                     neighbor_note: str = "", phase_context=None):
        self.calls += 1
        t0 = perf_counter()
        if phase_context is not None:
            # SOTA delay-aware myopic mode: forward the per-phase delay context (the
            # note channel is independent and unused here).
            out = self.inner.choose_phase(junction_id, num_phases, halting_per_phase,
                                          phase_context=phase_context)
        elif self.forward_note:
            if neighbor_note:
                self.notes_forwarded += 1
            out = self.inner.choose_phase(junction_id, num_phases, halting_per_phase,
                                          neighbor_note=neighbor_note)
        else:  # myopic: the note is NOT forwarded to the inner agent
            out = self.inner.choose_phase(junction_id, num_phases, halting_per_phase)
        self.latencies_s.append(perf_counter() - t0)
        if out is None:
            self.none_returns += 1
        return out


# --------------------------------------------------------------------------- #
# Harness building blocks (pure / testable without SUMO or Foundry).
# --------------------------------------------------------------------------- #
# The config arms (MASTER-SPEC §3 {myopic, +coordination, +prediction}). The
# baseline (myopic MaxPressure) is ALWAYS the myopic reference; the arm names below
# vary only what the SLM controller may use ON TOP of the same MaxPressure shield.
CONFIGS = ("myopic", "coordination", "prediction")
# Coordination reference weight (Channel B) and the actual-flow window (s). 1.0
# means the incoming-release term counts at parity with local halting; the window
# is the sliding actual-flow reconciliation horizon used by run_coordinated too.
COORD_WEIGHT = 1.0
FLOW_WINDOW_S = 30.0
# +prediction weight: approaching (in-motion) vehicles count at parity with queued
# ones in the deterministic reference. 0.0 for myopic/coordination arms.
PREDICT_WEIGHT = 1.0


def build_coordination(tls_ids, net_path: str = NET, bus_factory=None):
    """Build the coordination scaffolding for a real net (identities + registry +
    signed bus + checker + derived adjacency/edge_map).

    ``bus_factory`` (opt-in): callable (registry, adjacency) -> bus. Defaults to the honest
    MessageBus. The H2 trust axis passes a LyingBus factory to inject insider-liar claims;
    default None keeps behaviour byte-identical.

    Adjacency and the explicit ``(src,dst)->edge_id`` map are DERIVED from the real
    net via ``edge_map_from_net`` (chain mode: two TLS are neighbours iff a path of
    non-signalised interior nodes joins them). This is what makes coordination work
    on the OSM Euston net whose edge ids are not junction-id concatenations. Returns
    a dict consumed by ``build_controller``. Reads the net via sumolib (no traci).
    """
    import sumolib
    from coordinated_controller import edge_map_from_net
    from message_bus import MessageBus
    from registry import Registry

    net = sumolib.net.readNet(net_path)
    adjacency, edge_map = edge_map_from_net(net, mode="chain")
    identities = {jid: JunctionIdentity(jid) for jid in tls_ids}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    # The bus needs an adjacency for EVERY signalised junction (default empty).
    bus_adjacency = {jid: list(adjacency.get(jid, ())) for jid in tls_ids}
    bus = bus_factory(registry, bus_adjacency) if bus_factory else MessageBus(registry, bus_adjacency)
    return {
        "identities": identities,
        "registry": registry,
        "bus": bus,
        "adjacency": bus_adjacency,
        "edge_map": edge_map,
    }


def build_controller(conn, tls_ids, agent, *, config: str = "myopic", gate: int = 2,
                     min_green: int = DECISION_INTERVAL_S, yellow: int = 3,
                     coordination: dict | None = None, gate_mode: str = "sum"):
    """Build the shield-gated controller for one arm at a given config.

    ALL arms share the MaxPressure shield (SLM proposes, shield disposes,
    event-gated); the config only widens what the SLM may use on top:
      * ``myopic``       -- HybridController: per-junction queues only.
      * ``coordination`` -- CoordinatedController with a live signed neighbour
        exchange (coord_weight>0) feeding a neighbour note + a coordination-adjusted
        deterministic reference. Requires ``coordination`` (from build_coordination).
      * ``prediction``   -- coordination PLUS the +prediction lever (predict_weight>0):
        approaching in-motion vehicles are anticipated in the reference + the note.
    Reusing one shield keeps the arms apples-to-apples: only the SLM's information
    (and the deterministic fallback reference) changes, never the safety floor.
    """
    if config not in CONFIGS and config != "sota":
        raise ValueError(f"config must be one of {CONFIGS + ('sota',)}, got {config!r}")
    if config == "myopic":
        return HybridController(conn, tls_ids, agent, gate=gate,
                                min_green=min_green, yellow=yellow, gate_mode=gate_mode)
    if config == "sota":
        # SOTA delay-aware MYOPIC (own-junction only): the queue-only myopic shield
        # plus the delay-aware agent context (waiting-time priority + switching
        # hysteresis). No coordination / no neighbour note.
        return HybridController(conn, tls_ids, agent, gate=gate,
                                min_green=min_green, yellow=yellow, delay_aware=True,
                                gate_mode=gate_mode)
    if coordination is None:
        raise ValueError(f"config {config!r} requires coordination scaffolding "
                         "(call build_coordination first)")
    from coordinated_controller import CoordinatedController
    predict_weight = PREDICT_WEIGHT if config == "prediction" else 0.0
    return CoordinatedController(
        conn, tls_ids, agent,
        identities=coordination["identities"], registry=coordination["registry"],
        bus=coordination["bus"], adjacency=coordination["adjacency"],
        edge_map=coordination["edge_map"], gate=gate, min_green=min_green,
        yellow=yellow, coord_weight=COORD_WEIGHT, flow_window=FLOW_WINDOW_S,
        predict_weight=predict_weight)


def mirror_new_events(audit: AuditLog, identities: dict, events, already: int) -> int:
    """Append controller decision events ``events[already:]`` to the signed chain.

    Each HybridController event becomes a ``kind:"decision"`` audit record signed by
    the deciding junction's Ed25519 identity, so the accountability layer records
    the REAL controller decisions inline as they happen. Returns the new high-water
    mark (len(events)). Uses only the AuditLog public API -- no producer-wiring is
    reimplemented here.
    """
    for ev in events[already:]:
        jid = ev.get("tls")
        # ``executed`` is the phase ACTUALLY served (post anti-starvation), so the
        # hash-chained record reconstructs the true served phase (MASTER-SPEC §4 H2).
        # ``proposal`` (the pre-override decision) + slm_phase + shield_phase are
        # kept as provenance; ``served_by`` names who authored the served phase.
        served = ev.get("served", ev.get("used"))
        record = {
            "kind": "decision",
            "junction": jid,
            "halting": [int(h) for h in ev.get("halting", [])],
            "slm_phase": ev.get("slm_phase"),
            "shield_phase": ev.get("shield_phase"),
            "proposal": ev.get("used"),
            "executed": served,
            "served_by": ev.get("served_by"),
            "overridden": bool(ev.get("overridden")),
        }
        audit.append(record, issuer=identities.get(jid))
    return len(events)


def _served_by(e) -> str:
    """The event's ``served_by`` label, derived from fields if absent (an event
    from a directly-driven decide() has no override, so served == used)."""
    sb = e.get("served_by")
    if sb:
        return sb
    served = e.get("served", e.get("used"))
    if served != e.get("used"):
        return "anti_starvation"
    if e.get("slm_phase") is not None and e.get("slm_phase") == served:
        return "slm"
    return "shield"


def decision_stats(events) -> dict:
    """Characterise the arm's decisions HONESTLY from the controller event log.

    Every decision is bucketed by WHO authored the phase actually served (``served_by``):
      * ``anti_starvation`` -- the fairness shield overrode the decision's choice.
        This interval is NEITHER the SLM proposal NOR the shield's argmax, so it is
        NOT counted as "SLM agreed/used" (the bug this fixes: overridden intervals
        were mislabelled as SLM authorship).
      * ``slm``    -- a valid SLM proposal was served.
      * ``shield`` -- the MaxPressure shield choice was served.
    The SLM-authorship counts (agreed/diverged) are taken ONLY over intervals the
    SLM actually authored, so they cannot double-count an override. Still
    distinguishes a genuine SLM run from a DEGRADED all-fallback run (§8 / D-H1-perf).
    For the baseline (NullAgent) every proposal is None -> all shield.
    """
    total = len(events)
    labels = [_served_by(e) for e in events]
    anti = sum(1 for x in labels if x == "anti_starvation")
    slm_served = sum(1 for x in labels if x == "slm")
    shield_served = sum(1 for x in labels if x == "shield")

    # The SLM SPOKE (valid proposal) here, regardless of whether the shield later
    # overrode it -- a participation count, kept distinct from authorship.
    proposed = [e for e in events if e.get("slm_phase") is not None]
    # SLM AUTHORSHIP: only intervals actually served by a valid SLM proposal.
    slm_events = [e for e, x in zip(events, labels) if x == "slm"]
    agreed = sum(1 for e in slm_events if e["slm_phase"] == e.get("shield_phase"))
    diverged_served = sum(1 for e in slm_events
                          if e["slm_phase"] != e.get("shield_phase"))
    # Shield fell back to MaxPressure because the SLM was silent/invalid (None).
    fallbacks = sum(1 for e, x in zip(events, labels)
                    if x == "shield" and e.get("slm_phase") is None)
    return {
        "decisions": total,
        "served_by": {"slm": slm_served, "shield": shield_served,
                      "anti_starvation": anti},
        "slm_valid_proposals": len(proposed),
        "slm_proposal_served": slm_served,
        "slm_agreed_with_shield": agreed,
        "slm_diverged_and_served": diverged_served,
        "shield_fallbacks_none": fallbacks,
        "anti_starvation_overrides": anti,
    }


def audit_bundle(audit: AuditLog, public_keys: dict) -> dict:
    """verify_chain + verify_signatures + Merkle root + a sample inclusion proof.

    Raises RuntimeError if chain verification or the sampled inclusion proof fails
    -- the audit layer must not silently degrade to a green result (§10 golden rule).
    """
    n = len(audit)
    decision_entries = sum(1 for e in audit.entries()
                           if e["event"].get("kind") == "decision")
    bundle: dict = {
        "enabled": True,
        "entries": n,
        "decision_entries": decision_entries,
        "verify_chain": audit.verify_chain(),
        "verify_signatures": audit.verify_signatures(public_keys),
    }
    if not bundle["verify_chain"]:
        raise RuntimeError("AUDIT INTEGRITY FAILURE: verify_chain() returned False")
    if n == 0:
        bundle["merkle_root"] = None
        bundle["inclusion_proof_valid"] = None
        return bundle
    root = audit.merkle_root(0, n)
    idx = n - 1
    entry_hash = audit.entries()[idx]["hash"]
    branch = audit.inclusion_proof(idx, 0, n)
    ok = verify_inclusion(entry_hash, branch, root)
    if not ok:
        raise RuntimeError("AUDIT INTEGRITY FAILURE: Merkle inclusion proof invalid")
    bundle["merkle_root"] = root
    bundle["inclusion_sample_index"] = idx
    bundle["inclusion_branch_len"] = len(branch)
    bundle["inclusion_proof_valid"] = ok
    return bundle


def metrics_from_tripinfo(tripinfo_path: str, teleports: int, sim_steps: int) -> dict:
    """Survivorship-robust metrics for one arm (pure function of the tripinfo file).

    completed = arrival>=0 (metrics.throughput), NEVER len(tripinfo). mean delay =
    mean_network_delay over ALL departed vehicles; the biased completed-only mean +
    completed median are reported alongside for context only.
    """
    run = parse_tripinfo(tripinfo_path)
    completed_durs = sorted(t.duration for t in run.completed_trips)
    return {
        "loaded": len(run.trips),
        "departed": len(run.departed_trips),
        "completed": throughput(run),
        "running_at_end": len(run.running_trips),
        "undeparted": len(run.undeparted_trips),
        "mean_network_delay_s": mean_network_delay(run),
        "avg_travel_time_completed_s": avg_travel_time_completed(run),
        "median_travel_time_completed_s": (
            statistics.median(completed_durs) if completed_durs else None),
        "teleports": teleports,
        "sim_steps": sim_steps,
        "write_unfinished_present": run.has_unfinished,
        "write_undeparted_present": run.has_undeparted,
    }


# --------------------------------------------------------------------------- #
# The live SUMO run of one arm.
# --------------------------------------------------------------------------- #
def coordination_stats(ctrl) -> dict | None:
    """Coordination/prediction liveness + causality for a coordinated arm.

    Separates WIRING-LIVE (signed messages actually published + verified over the
    real derived adjacency) from CAUSAL EFFECT (decisions the adjusted reference /
    the prediction term actually moved). A structural zero on this substrate is a
    HONEST finding (§3), reported as such -- distinct from an inert/unwired term.
    Returns None for the myopic arm (no coordination layer).
    """
    if not hasattr(ctrl, "coord_adjusted_decisions"):
        return None
    ev = ctrl.events
    published = sum(1 for e in ev if isinstance(e.get("published"), dict)
                    and "error" not in e.get("published", {}))
    verified = sum(len(e.get("received", [])) for e in ev
                   if isinstance(e.get("received"), list)
                   and not any("error" in r for r in e.get("received", [])
                               if isinstance(r, dict)))
    return {
        "coord_weight": ctrl.coord_weight,
        "predict_weight": getattr(ctrl, "predict_weight", 0.0),
        "flow_window_s": ctrl.flow_window_s,
        "messages_published": published,
        "verified_messages_received": verified,
        "rejected_messages": len(ctrl.bus.rejected),
        "coord_adjusted_decisions": ctrl.coord_adjusted_decisions,
        "pred_adjusted_decisions": getattr(ctrl, "pred_adjusted_decisions", 0),
        "coord_changed_events": sum(1 for e in ev if e.get("coord_changed")),
        "pred_changed_events": sum(1 for e in ev if e.get("pred_changed")),
        "detections": len(ctrl.detections),
        "flagged_detections": sum(1 for d in ctrl.detections if d.flagged),
    }


def run_arm(arm: str, agent, *, seed: int, end: int, gate: int = 2,
            config: str = "myopic", net: str | None = None,
            routes: str | None = None, gate_mode: str = "sum",
            liars: dict | None = None) -> dict:
    """Run ONE controller arm end-to-end on a SUMO net; return its result dict.

    Live-gated on SUMO (imports traci/sumolib inside). Builds the config-appropriate
    controller (myopic HybridController, or a CoordinatedController for the
    +coordination / +prediction arms), injects a fresh AuditLog and mirrors every
    controller decision into it, then asserts audit integrity. For coordinated arms
    the audit is signed by the SAME per-junction identities the controller uses.

    ``net``/``routes`` override the default Euston net/demand (default = the module
    NET/ROUTES), so the SAME controller + audit can run on ANY topology (the multi-
    topology study). The controller is built from the net's own TLS list, so it is
    topology-agnostic; ``config != "myopic"`` on a non-Euston net would need the
    coordination scaffolding derived from that net (myopic needs none).
    """
    import traci
    from sumolib import checkBinary

    net = net or NET
    routes = routes or ROUTES
    binary = checkBinary("sumo")
    tripinfo = os.path.join(_SUMO_EUSTON, f"tripinfo_h1_{arm}_s{seed}.xml")
    # write-unfinished + write-undeparted so metrics.py sees the WHOLE population
    # (departed/running/undeparted), not just survivors. time-to-teleport 300 so
    # gridlock surfaces honestly as teleports (matches sumo/euston/euston.sumocfg).
    traci.start([binary, "-n", net, "-r", routes,
                 "--tripinfo-output", tripinfo,
                 "--tripinfo-output.write-unfinished", "true",
                 "--tripinfo-output.write-undeparted", "true",
                 "--begin", "0", "--end", str(end),
                 "--time-to-teleport", "300",
                 "--seed", str(seed),
                 "--no-step-log", "true", "--no-warnings", "true"])

    teleports = 0
    step = 0
    audit = AuditLog()
    identities: dict[str, JunctionIdentity] = {}
    logged = 0
    tls: list[str] = []
    ctrl = None
    coordination = None
    try:
        tls = list(traci.trafficlight.getIDList())
        if config in ("myopic", "sota"):
            # Myopic + SOTA delay-aware are own-junction only: no coordination layer.
            identities = {tl: JunctionIdentity(tl) for tl in tls}
        else:
            # Coordinated arms sign the audit with the controller's OWN identities.
            # Derive adjacency from the ACTUAL net being simulated (net, not the default
            # Euston NET) -- otherwise coordination/prediction on any other topology would
            # use Euston's neighbour graph, which is wrong.
            bus_factory = None
            if liars:
                from trust_injection import LyingBus
                bus_factory = lambda r, a: LyingBus(r, a, liars=liars)  # noqa: E731
            coordination = build_coordination(tls, net_path=net, bus_factory=bus_factory)
            identities = coordination["identities"]
        ctrl = build_controller(traci, tls, agent, config=config, gate=gate,
                                coordination=coordination, gate_mode=gate_mode)
        while traci.simulation.getMinExpectedNumber() > 0 and step < end:
            traci.simulationStep()
            ctrl.step()
            logged = mirror_new_events(audit, identities, ctrl.events, logged)
            teleports += traci.simulation.getStartingTeleportNumber()
            step += 1
    finally:
        try:
            traci.close()
        except Exception:
            pass

    public_keys = {jid: ident.public_key for jid, ident in identities.items()}
    events = ctrl.events if ctrl is not None else []
    result = {
        "arm": arm,
        "config": config,
        "controller_model": getattr(agent, "model", "unknown"),
        "controlled_tls": tls,
        "metrics": metrics_from_tripinfo(tripinfo, teleports, step),
        "decision_stats": decision_stats(events),
        "coordination": coordination_stats(ctrl),
        "audit": audit_bundle(audit, public_keys),
        "tripinfo": tripinfo,
    }
    if liars:
        # H2 trust axis: expose the raw detection events (for offline TrustLedger replay) and
        # the bus's lie-injection log so the caller can quantify caught-vs-uncaught insider lies.
        result["events"] = events
        bus_obj = coordination.get("bus") if coordination else None
        result["lie_log"] = list(getattr(bus_obj, "lie_log", []))
    return result


# --------------------------------------------------------------------------- #
# Foundry probe (SKIP-with-record; never fabricate).
# --------------------------------------------------------------------------- #
def probe_foundry():
    """Return (SLMAgent, None) if the real-model precondition holds, else (None, reason)."""
    try:
        from slm_agent import probe_foundry_determinism
    except Exception as exc:  # noqa: BLE001
        return None, f"import failed: {type(exc).__name__}: {exc}"
    return probe_foundry_determinism()


# --------------------------------------------------------------------------- #
# Verdict + reporting.
# --------------------------------------------------------------------------- #
def _num(x):
    return x if isinstance(x, (int, float)) else None


def _bml(slm_val, base_val, *, lower_is_better: bool, band: float = 0.02):
    """Classify SLM vs baseline as slm_beats / match / slm_loses on one metric.

    ``band`` is the relative tie-window (2%). Returns (status, relative_change) where
    relative_change = (slm - base)/base. For a lower-is-better metric (delay) a
    negative change is good; for higher-is-better (throughput) a positive change is
    good. A tie inside the band is 'match'."""
    if slm_val is None or base_val is None:
        return "indeterminate", None
    rel = (slm_val - base_val) / base_val if base_val else float("inf")
    if abs(rel) <= band:
        return "match", rel
    better = (slm_val < base_val) if lower_is_better else (slm_val > base_val)
    return ("slm_beats" if better else "slm_loses"), rel


def _joint_verdict(delay_status: str, thru_status: str) -> str:
    """Combine the delay + throughput verdicts into an honest joint outcome.

    MaxPressure is throughput-OPTIMAL by design, so the key question (Akin) is whether
    a delay win quietly SACRIFICES throughput. Labels:
      * clean_win  -- at least one metric beats and NEITHER loses (wins without a cost);
      * trade_off  -- one metric beats but the other loses (an honest trade);
      * match      -- both within the tie band;
      * regression -- at least one loses and neither beats.
    """
    if "indeterminate" in (delay_status, thru_status):
        return "indeterminate"
    s = {delay_status, thru_status}
    if "slm_beats" in s and "slm_loses" not in s:
        return "clean_win"
    if "slm_beats" in s and "slm_loses" in s:
        return "trade_off"
    if delay_status == "match" and thru_status == "match":
        return "match"
    return "regression"


def verdict(baseline: dict, slm: dict | None) -> dict:
    """Honest joint verdict on DELAY and THROUGHPUT at this config (no significance).

    ``status`` remains the DELAY verdict (slm_beats/match/slm_loses) for backward
    compatibility with the sweep/sota consumers. Added: ``throughput_status`` (on
    completed vehicles, higher is better) and ``joint_verdict`` (clean_win / trade_off
    / match / regression) -- so a delay win is never reported without checking it did
    not cost throughput (MaxPressure is throughput-optimal by design)."""
    if slm is None or slm.get("skipped"):
        return {"status": "no_comparison",
                "reason": "SLM arm skipped (Foundry precondition unmet); baseline only"}
    b = baseline["metrics"]
    s = slm["metrics"]
    bd, sd = _num(b.get("mean_network_delay_s")), _num(s.get("mean_network_delay_s"))
    if bd is None or sd is None:
        return {"status": "indeterminate", "reason": "a mean_network_delay is undefined (nobody departed?)"}
    delay_status, rel = _bml(sd, bd, lower_is_better=True)
    # Throughput = completed vehicles (arrival>=0); higher is better. Same net+demand+
    # seed, so absolute completed counts are directly comparable.
    bc, sc = _num(b.get("completed")), _num(s.get("completed"))
    thru_status, thru_rel = _bml(sc, bc, lower_is_better=False)
    return {
        "status": delay_status,               # DELAY verdict (unchanged contract)
        "metric": "mean_network_delay_s (lower is better)",
        "baseline_delay_s": bd,
        "slm_delay_s": sd,
        "slm_minus_baseline_s": sd - bd,
        "slm_relative_delay": rel,
        "baseline_completed": bc,
        "slm_completed": sc,
        "throughput_status": thru_status,      # on completed vehicles (higher is better)
        "throughput_relative": thru_rel,
        "throughput_completed_delta": (sc - bc) if (sc is not None and bc is not None) else None,
        "joint_verdict": _joint_verdict(delay_status, thru_status),
        "note": ("SMOKE / PILOT: n=1, short horizon, DfT-daily-AADF demand -- "
                 "descriptive only, NO significance/inferential claim (§8). Delay AND "
                 "throughput both reported; MaxPressure is throughput-optimal by design."),
    }


def latency_viability(lat: dict | None) -> dict:
    """Is choose_phase fast enough for the ~10 s event-gated interval (H1 real-time)?"""
    if not lat or not lat.get("n"):
        return {"viable": None, "reason": "no measurable choose_phase samples"}
    p95 = lat.get("p95")
    p99 = lat.get("p99")
    return {
        "decision_interval_s": DECISION_INTERVAL_S,
        "p50_s": lat.get("p50"),
        "p95_s": p95,
        "p99_s": p99,
        "p99_within_interval": (p99 is not None and p99 <= DECISION_INTERVAL_S),
        "p95_within_interval": (p95 is not None and p95 <= DECISION_INTERVAL_S),
    }


def run(seed: int = 42, end: int = 300, gate: int = 2) -> dict:
    result: dict = {
        "experiment": "H1_slm_vs_maxpressure_traffic",
        "label": "PILOT / SMOKE",
        "config": "myopic (per-junction queues; no coordination; no neighbour note)",
        "corridor": "Euston Road A501 spine (euston_spine.net.xml, 4 TLS)",
        "demand": "base.rou.xml (DfT-AADF-calibrated, daily resolution)",
        "seed": seed,
        "end": end,
        "gate": gate,
        "decision_interval_s": DECISION_INTERVAL_S,
        "caveats": [
            "PILOT: demand is DfT daily-AADF magnitude+mix; temporal profile assumed "
            "-> inferential claims GATED until time-resolved TfL counts land (§8).",
            "SMOKE: n=1, short horizon -> descriptive only, NO significance claim.",
            "Audit layer LIVE on both arms (signed hash-chain + Merkle inclusion proof).",
        ],
    }

    # Baseline first -- no Foundry needed.
    result["baseline"] = run_arm("maxpressure", NullAgent(), seed=seed, end=end, gate=gate)

    # SLM arm -- gated on the Foundry determinism probe.
    agent, reason = probe_foundry()
    if agent is None:
        result["slm"] = {"skipped": True, "reason": reason}
    else:
        timing = TimingAgent(agent)
        slm = run_arm("slm_myopic", timing, seed=seed, end=end, gate=gate)
        slm["model"] = agent.model
        slm["slm_calls"] = timing.calls
        slm["slm_none_returns"] = timing.none_returns
        slm["latency"] = summarize_latency(timing.latencies_s, warmup=1)
        result["slm"] = slm

    result["verdict"] = verdict(result["baseline"],
                                result.get("slm") if not result.get("slm", {}).get("skipped") else result["slm"])
    slm_lat = (result["slm"].get("latency")
               if isinstance(result.get("slm"), dict) and not result["slm"].get("skipped")
               else None)
    result["latency_viability"] = latency_viability(slm_lat)

    os.makedirs(RESULTS, exist_ok=True)
    json_path = os.path.join(RESULTS, "experiment_traffic.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    md_path = os.path.join(RESULTS, "experiment_traffic.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_md(result))
    _print_summary(result, json_path, md_path)
    return result


_CONFIG_DESC = {
    "myopic": "per-junction queues only; no coordination; no neighbour note",
    "coordination": "signed neighbour exchange feeds a coordination note + a "
                    "coordination-adjusted deterministic reference (coord_weight>0)",
    "prediction": "coordination PLUS the +prediction lever: approaching in-motion "
                  "vehicles anticipated in the reference + the note (predict_weight>0)",
}


def _stub_agent():
    """Deterministic argmax-over-queue stand-in (no Foundry). Used ONLY by the
    wiring-validation path so the config-arm machinery can be proven live on the
    real net when Foundry is unavailable -- NEVER a stand-in for the SLM in a
    feasibility claim."""
    from coordinated_controller import StubAgent
    return StubAgent()


def run_configs(seed: int = 42, end: int = 300, gate: int = 2,
                configs=CONFIGS, *, stub: bool = False) -> dict:
    """Run the myopic MaxPressure baseline ONCE, then a controller across the config
    arms {myopic, +coordination, +prediction}, on the real Euston corridor.

    ``stub=False`` (DEFAULT): the SLM controller (phi-4-mini via Foundry Local),
    gated on the Foundry determinism probe -- the H1 feasibility measurement. Arms
    SKIP-with-record if the probe fails (never a fabricated green).

    ``stub=True``: the deterministic StubAgent (argmax-over-queue, no Foundry) --
    a WIRING / CAUSALITY validation of the config-arm machinery on the real net
    (signed neighbour exchange live, coordination/prediction terms causal, served-
    phase audit correct). This is NOT an SLM feasibility result and is written to a
    DISTINCT file so it can never be mistaken for one.

    One shared baseline (myopic MaxPressure, Varaiya -- the fixed reference every
    config is asked to match-or-beat), the config arms, one verdict + coordination
    liveness per arm. PILOT/SMOKE, n=1: descriptive only.
    """
    mode = "STUB_WIRING_VALIDATION" if stub else "SLM_FEASIBILITY"
    result: dict = {
        "experiment": ("H1_config_arms_WIRING_VALIDATION" if stub
                       else "H1_config_arms_slm_vs_maxpressure"),
        "mode": mode,
        "label": "PILOT / SMOKE",
        "controller_under_test": (
            "StubAgent (deterministic argmax-over-queue; NOT the SLM) -- config-arm "
            "WIRING/CAUSALITY validation only" if stub
            else "on-device SLM (phi-4-mini via Foundry Local)"),
        "corridor": "Euston Road A501 spine (euston_spine.net.xml, 4 TLS)",
        "demand": "base.rou.xml (DfT-AADF-calibrated, daily resolution)",
        "baseline_controller": "myopic MaxPressure (Varaiya) -- fixed reference",
        "seed": seed,
        "end": end,
        "gate": gate,
        "decision_interval_s": DECISION_INTERVAL_S,
        "configs": list(configs),
        "config_descriptions": {c: _CONFIG_DESC[c] for c in configs},
        "caveats": [
            "PILOT: demand is DfT daily-AADF magnitude+mix; temporal profile assumed "
            "-> inferential claims GATED until time-resolved TfL counts land (§8).",
            "SMOKE: n=1, short horizon -> descriptive only, NO significance claim.",
            "Audit layer LIVE on every arm (signed hash-chain + Merkle inclusion proof).",
            "Baseline is myopic MaxPressure; the config arms vary only the controller's "
            "information, never the MaxPressure safety floor.",
        ],
    }
    if stub:
        result["caveats"].insert(0,
            "WIRING VALIDATION ONLY: the controller is the deterministic StubAgent, "
            "NOT the SLM. This run proves the config-arm machinery is live + causal "
            "on the real net; it is NOT an SLM feasibility result (D-H1-perf).")

    # ONE baseline: myopic MaxPressure. Every config arm compares against it.
    result["baseline"] = run_arm("maxpressure", NullAgent(), seed=seed, end=end,
                                 gate=gate, config="myopic")

    if stub:
        agent, reason = _stub_agent(), None
    else:
        agent, reason = probe_foundry()
    arms: dict = {}
    if agent is None:
        for config in configs:
            arms[config] = {"skipped": True, "reason": reason}
    else:
        for config in configs:
            # Fresh TimingAgent per arm (accumulates its own latency samples). The
            # note is forwarded for coordination/prediction, dropped for myopic.
            timing = TimingAgent(agent, forward_note=(config != "myopic"))
            slm = run_arm(f"{'stub' if stub else 'slm'}_{config}", timing,
                          seed=seed, end=end, gate=gate, config=config)
            slm["model"] = agent.model
            slm["slm_calls"] = timing.calls
            slm["slm_none_returns"] = timing.none_returns
            slm["notes_forwarded"] = timing.notes_forwarded
            slm["latency"] = summarize_latency(timing.latencies_s, warmup=1)
            slm["verdict"] = verdict(result["baseline"], slm)
            slm["latency_viability"] = latency_viability(slm["latency"])
            arms[config] = slm
    result["arms"] = arms
    result["scale_summary"] = _scale_summary(result["baseline"], arms, configs)

    os.makedirs(RESULTS, exist_ok=True)
    stem = "experiment_traffic_arms_stub" if stub else "experiment_traffic_arms"
    json_path = os.path.join(RESULTS, f"{stem}.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    md_path = os.path.join(RESULTS, f"{stem}.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_configs_md(result))
    _print_configs_summary(result, json_path, md_path)
    return result


def _scale_summary(baseline: dict, arms: dict, configs) -> dict:
    """The simplest config reaching parity-or-better (proto scale-threshold, §3).

    Ordered myopic -> coordination -> prediction (simplest first). Reports the
    FIRST config that matches-or-beats the baseline on delay, or an honest negative.
    n=1 SMOKE, so this is descriptive framing for the eventual feasibility map, NOT
    an inferential threshold claim.
    """
    order = [c for c in ("myopic", "coordination", "prediction") if c in configs]
    ran = {c: arms[c] for c in order
           if isinstance(arms.get(c), dict) and not arms[c].get("skipped")}
    if not ran:
        return {"status": "no_arm_ran",
                "reason": "SLM arms skipped (Foundry precondition unmet)"}
    parity_or_better = [
        c for c in order
        if c in ran and ran[c]["verdict"].get("status") in ("match", "slm_beats")
    ]
    simplest = parity_or_better[0] if parity_or_better else None
    return {
        "simplest_parity_or_better_config": simplest,
        "per_config_status": {c: ran[c]["verdict"].get("status") for c in order
                              if c in ran},
        "note": ("SMOKE n=1: descriptive only. The powered feasibility MAP over "
                 "{model} x {config} + a real scale threshold is phase 2, gated on "
                 "time-resolved demand (§8)."),
    }


# --------------------------------------------------------------------------- #
# Markdown report.
# --------------------------------------------------------------------------- #
def _fmt(v, nd: int = 2) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def render_md(r: dict) -> str:
    b = r["baseline"]["metrics"]
    ba = r["baseline"]["audit"]
    slm = r.get("slm", {})
    slm_ran = isinstance(slm, dict) and not slm.get("skipped")
    lines = []
    lines.append("# H1 headline: on-device SLM controller vs MaxPressure (Euston A501)")
    lines.append("")
    lines.append("**PILOT / SMOKE** -- n=1, myopic config. NOT the powered sweep, NOT a "
                 "significance claim.")
    lines.append("")
    lines.append(f"- Corridor: {r['corridor']}")
    lines.append(f"- Demand: {r['demand']}")
    lines.append(f"- Seed: {r['seed']}  |  horizon (sim end): {r['end']} s  |  "
                 f"event-gate: {r['gate']}  |  decision interval: {r['decision_interval_s']} s")
    lines.append("")
    lines.append("## Head-to-head")
    lines.append("")
    lines.append("| Metric | MaxPressure (baseline) | SLM (phi-4-mini, myopic) |")
    lines.append("|---|---|---|")
    if slm_ran:
        s = slm["metrics"]
        sa = slm["audit"]

        def row(label, key, nd=2):
            return f"| {label} | {_fmt(b.get(key), nd)} | {_fmt(s.get(key), nd)} |"
        lines.append(row("completed (arrival>=0)", "completed", 0))
        lines.append(row("departed", "departed", 0))
        lines.append(row("running at end", "running_at_end", 0))
        lines.append(row("mean network delay (s)", "mean_network_delay_s"))
        lines.append(row("median completed travel time (s)", "median_travel_time_completed_s"))
        lines.append(row("avg completed travel time (s, biased)", "avg_travel_time_completed_s"))
        lines.append(row("teleports", "teleports", 0))
        lat = slm.get("latency", {})
        lines.append(f"| SLM choose_phase P50 / P99 (s) | -- | "
                     f"{_fmt(lat.get('p50'), 3)} / {_fmt(lat.get('p99'), 3)} |")
        lines.append(f"| audit verify_chain | {_fmt(ba.get('verify_chain'))} | "
                     f"{_fmt(sa.get('verify_chain'))} |")
        lines.append(f"| audit decision records | {_fmt(ba.get('decision_entries'), 0)} | "
                     f"{_fmt(sa.get('decision_entries'), 0)} |")
        lines.append(f"| Merkle inclusion proof | {_fmt(ba.get('inclusion_proof_valid'))} | "
                     f"{_fmt(sa.get('inclusion_proof_valid'))} |")
    else:
        lines.append(f"| completed (arrival>=0) | {_fmt(b.get('completed'), 0)} | SKIPPED |")
        lines.append(f"| mean network delay (s) | {_fmt(b.get('mean_network_delay_s'))} | SKIPPED |")
        lines.append(f"| teleports | {_fmt(b.get('teleports'), 0)} | SKIPPED |")
        lines.append(f"| audit verify_chain | {_fmt(ba.get('verify_chain'))} | SKIPPED |")
    lines.append("")

    v = r["verdict"]
    lines.append("## Verdict (delay, this config)")
    lines.append("")
    if not slm_ran:
        lines.append(f"- **SLM arm SKIPPED**: {slm.get('reason')}")
        lines.append("- No head-to-head verdict possible; MaxPressure baseline recorded above.")
    else:
        lines.append(f"- **{v.get('status')}** on {v.get('metric')}")
        lines.append(f"- baseline delay {_fmt(v.get('baseline_delay_s'))} s vs SLM "
                     f"{_fmt(v.get('slm_delay_s'))} s "
                     f"(SLM - baseline = {_fmt(v.get('slm_minus_baseline_s'))} s, "
                     f"{_fmt((v.get('slm_relative_delay') or 0) * 100, 1)}%)")
        lv = r["latency_viability"]
        lines.append(f"- **Real-time viability**: choose_phase P50={_fmt(lv.get('p50_s'), 3)} s, "
                     f"P95={_fmt(lv.get('p95_s'), 3)} s, P99={_fmt(lv.get('p99_s'), 3)} s "
                     f"vs {lv.get('decision_interval_s')} s interval -- "
                     f"P99 within interval: {_fmt(lv.get('p99_within_interval'))}")
        lines.append(f"- SLM calls: {slm.get('slm_calls')} "
                     f"(None/invalid -> shield fallback: {slm.get('slm_none_returns')})")
        ds = slm.get("decision_stats", {})
        sb = ds.get("served_by", {})
        lines.append(
            f"- Served-by breakdown ({ds.get('decisions')} decisions): "
            f"{sb.get('slm', 0)} served by a valid SLM proposal "
            f"({ds.get('slm_agreed_with_shield')} agreed with the MaxPressure shield, "
            f"{ds.get('slm_diverged_and_served')} diverged from it), "
            f"{sb.get('shield', 0)} served by the MaxPressure shield "
            f"({ds.get('shield_fallbacks_none')} of which were SLM None/invalid fallbacks), "
            f"{sb.get('anti_starvation', 0)} FORCED by the anti-starvation fairness "
            "shield (NOT SLM-authored -- the fairness override, neither the SLM "
            "proposal nor MaxPressure's argmax).")
        lines.append(
            f"- The SLM issued {ds.get('slm_valid_proposals')} valid proposals in "
            f"total (participation); authorship of the SERVED phase is the "
            f"served-by breakdown above. An anti-starvation override interval is "
            "attributed to the shield, never to the SLM.")
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    for c in r["caveats"]:
        lines.append(f"- {c}")
    lines.append("")
    return "\n".join(lines)


def _print_summary(r: dict, json_path: str, md_path: str) -> None:
    print("=" * 72)
    print("H1 PILOT/SMOKE: SLM (phi-4-mini, myopic) vs MaxPressure on Euston A501")
    b = r["baseline"]["metrics"]
    print(f"  baseline: completed={b['completed']} departed={b['departed']} "
          f"mean_delay={_fmt(b['mean_network_delay_s'])}s teleports={b['teleports']}")
    slm = r.get("slm", {})
    if slm.get("skipped"):
        print(f"  SLM: SKIPPED -- {slm.get('reason')}")
    else:
        s = slm["metrics"]
        lat = slm.get("latency", {})
        print(f"  SLM:      completed={s['completed']} departed={s['departed']} "
              f"mean_delay={_fmt(s['mean_network_delay_s'])}s teleports={s['teleports']}")
        print(f"  SLM choose_phase latency (n={lat.get('n')}, W={lat.get('warmup_discarded')}): "
              f"P50={_fmt(lat.get('p50'), 3)}s P95={_fmt(lat.get('p95'), 3)}s "
              f"P99={_fmt(lat.get('p99'), 3)}s")
        ds = slm.get("decision_stats", {})
        sb = ds.get("served_by", {})
        print(f"  served-by: slm={sb.get('slm', 0)} "
              f"(agreed={ds.get('slm_agreed_with_shield')} "
              f"diverged={ds.get('slm_diverged_and_served')}), "
              f"shield={sb.get('shield', 0)} "
              f"(none-fallbacks={ds.get('shield_fallbacks_none')}), "
              f"anti_starvation={sb.get('anti_starvation', 0)}")
        print(f"  verdict: {r['verdict'].get('status')}")
    print(f"  audit both arms verify_chain: baseline={r['baseline']['audit']['verify_chain']}"
          + ("" if slm.get("skipped") else f" slm={slm['audit']['verify_chain']}"))
    print("=" * 72)
    print(f"  wrote: {json_path}")
    print(f"  wrote: {md_path}")


def render_configs_md(r: dict) -> str:
    """Feasibility-style report: baseline + one column per SLM config arm."""
    b = r["baseline"]["metrics"]
    ba = r["baseline"]["audit"]
    configs = r["configs"]
    arms = r["arms"]
    ran = {c: arms[c] for c in configs
           if isinstance(arms.get(c), dict) and not arms[c].get("skipped")}
    stub = r.get("mode") == "STUB_WIRING_VALIDATION"
    col = "Stub" if stub else "SLM"
    title = ("H1 config arms: WIRING VALIDATION (StubAgent, NOT the SLM) vs myopic "
             "MaxPressure (Euston A501)" if stub else
             "H1 config arms: SLM controller vs myopic MaxPressure (Euston A501)")
    lines = [f"# {title}", ""]
    lines.append(f"- Controller under test: {r['controller_under_test']}")
    lines.append("")
    lines.append("**PILOT / SMOKE** -- n=1 per arm. Config-arm validation (each arm "
                 "runs live + is genuinely wired/causal), NOT the powered sweep.")
    if stub:
        lines.append("")
        lines.append("> WIRING VALIDATION ONLY -- the controller is the deterministic "
                     "StubAgent, NOT the SLM. Proves the config-arm machinery is live "
                     "and causal on the real net; NOT an SLM feasibility result.")
    lines.append("")
    lines.append(f"- Corridor: {r['corridor']}")
    lines.append(f"- Demand: {r['demand']}")
    lines.append(f"- Baseline: {r['baseline_controller']}")
    lines.append(f"- Seed: {r['seed']}  |  horizon: {r['end']} s  |  event-gate: "
                 f"{r['gate']}  |  decision interval: {r['decision_interval_s']} s")
    lines.append("")
    for c in configs:
        lines.append(f"- **{c}**: {r['config_descriptions'][c]}")
    lines.append("")

    # Head-to-head table: baseline column + one column per config that ran.
    ran_cfgs = [c for c in configs if c in ran]
    header = "| Metric | MaxPressure |" + "".join(f" {col} {c} |" for c in ran_cfgs)
    sep = "|---|---|" + "---|" * len(ran_cfgs)
    lines.append("## Head-to-head")
    lines.append("")
    if not ran_cfgs:
        skip = next((arms[c] for c in configs
                     if isinstance(arms.get(c), dict) and arms[c].get("skipped")), {})
        lines.append(f"All SLM arms SKIPPED: {skip.get('reason')}")
        lines.append(f"Baseline recorded: completed={_fmt(b.get('completed'), 0)}, "
                     f"mean delay={_fmt(b.get('mean_network_delay_s'))} s, "
                     f"teleports={_fmt(b.get('teleports'), 0)}, "
                     f"audit verify_chain={_fmt(ba.get('verify_chain'))}.")
        lines.append("")
    else:
        lines.append(header)
        lines.append(sep)

        def mrow(label, key, nd=2):
            cells = "".join(f" {_fmt(ran[c]['metrics'].get(key), nd)} |" for c in ran_cfgs)
            return f"| {label} | {_fmt(b.get(key), nd)} |" + cells
        lines.append(mrow("completed (arrival>=0)", "completed", 0))
        lines.append(mrow("departed", "departed", 0))
        lines.append(mrow("running at end", "running_at_end", 0))
        lines.append(mrow("mean network delay (s)", "mean_network_delay_s"))
        lines.append(mrow("median completed travel (s)", "median_travel_time_completed_s"))
        lines.append(mrow("teleports", "teleports", 0))
        p99row = "".join(
            f" {_fmt(ran[c].get('latency', {}).get('p99'), 3)} |" for c in ran_cfgs)
        lines.append("| SLM choose_phase P99 (s) | -- |" + p99row)
        vchain = "".join(f" {_fmt(ran[c]['audit'].get('verify_chain'))} |" for c in ran_cfgs)
        lines.append(f"| audit verify_chain | {_fmt(ba.get('verify_chain'))} |" + vchain)
        lines.append("")

        # Verdict + wiring/causality per config.
        lines.append("## Per-config verdict + coordination liveness")
        lines.append("")
        for c in ran_cfgs:
            arm = ran[c]
            v = arm["verdict"]
            lines.append(f"### {c}")
            lines.append(f"- **{v.get('status')}** on delay: baseline "
                         f"{_fmt(v.get('baseline_delay_s'))} s vs SLM "
                         f"{_fmt(v.get('slm_delay_s'))} s "
                         f"(delta {_fmt(v.get('slm_minus_baseline_s'))} s, "
                         f"{_fmt((v.get('slm_relative_delay') or 0) * 100, 1)}%)")
            lat = arm.get("latency", {})
            lines.append(f"- choose_phase latency P50/P95/P99 = "
                         f"{_fmt(lat.get('p50'), 3)}/{_fmt(lat.get('p95'), 3)}/"
                         f"{_fmt(lat.get('p99'), 3)} s (n={lat.get('n')})")
            ds = arm.get("decision_stats", {})
            sb = ds.get("served_by", {})
            lines.append(f"- served-by: slm={sb.get('slm', 0)}, shield={sb.get('shield', 0)}, "
                         f"anti_starvation={sb.get('anti_starvation', 0)}; "
                         f"SLM valid proposals={ds.get('slm_valid_proposals')}, "
                         f"notes forwarded={arm.get('notes_forwarded', 0)}")
            co = arm.get("coordination")
            if co is None:
                lines.append("- coordination: n/a (myopic arm, no coordination layer)")
            else:
                lines.append(
                    f"- coordination WIRING: {co['messages_published']} signed messages "
                    f"published, {co['verified_messages_received']} verified received, "
                    f"{co['rejected_messages']} rejected (window {_fmt(co['flow_window_s'], 0)} s)")
                lines.append(
                    f"- coordination CAUSAL: coord_weight={_fmt(co['coord_weight'], 1)}, "
                    f"adjusted-reference changed {co['coord_adjusted_decisions']} decisions; "
                    f"prediction (predict_weight={_fmt(co['predict_weight'], 1)}) changed "
                    f"{co['pred_adjusted_decisions']} decisions"
                    + (" -- STRUCTURAL ZERO on this substrate (honest §3 finding)"
                       if co['coord_adjusted_decisions'] == 0 and co['pred_adjusted_decisions'] == 0
                       else ""))
            lines.append("")

    # Proto scale-threshold framing.
    ss = r["scale_summary"]
    lines.append("## Simplest config reaching parity-or-better (proto scale-threshold)")
    lines.append("")
    if ss.get("status") == "no_arm_ran":
        lines.append(f"- No SLM arm ran: {ss.get('reason')}")
    else:
        simplest = ss.get("simplest_parity_or_better_config")
        lines.append(f"- Simplest config at parity-or-better: "
                     f"**{simplest if simplest else 'NONE in this smoke'}**")
        lines.append(f"- Per-config status: {ss.get('per_config_status')}")
    lines.append(f"- {ss.get('note', '')}")
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    for c in r["caveats"]:
        lines.append(f"- {c}")
    lines.append("")
    return "\n".join(lines)


def _print_configs_summary(r: dict, json_path: str, md_path: str) -> None:
    print("=" * 72)
    print("H1 CONFIG ARMS (PILOT/SMOKE): SLM vs myopic MaxPressure on Euston A501")
    b = r["baseline"]["metrics"]
    print(f"  baseline (myopic MaxPressure): completed={b['completed']} "
          f"mean_delay={_fmt(b['mean_network_delay_s'])}s teleports={b['teleports']}")
    for c in r["configs"]:
        arm = r["arms"].get(c, {})
        if arm.get("skipped"):
            print(f"  [{c}] SKIPPED -- {arm.get('reason')}")
            continue
        s = arm["metrics"]
        v = arm["verdict"]
        lat = arm.get("latency", {})
        co = arm.get("coordination")
        line = (f"  [{c}] completed={s['completed']} "
                f"mean_delay={_fmt(s['mean_network_delay_s'])}s "
                f"teleports={s['teleports']} verdict={v.get('status')} "
                f"P99={_fmt(lat.get('p99'), 3)}s")
        if co is not None:
            line += (f" | coord_changed={co['coord_adjusted_decisions']} "
                     f"pred_changed={co['pred_adjusted_decisions']} "
                     f"msgs={co['messages_published']}/{co['verified_messages_received']}")
        print(line)
        print(f"       audit verify_chain={arm['audit']['verify_chain']} "
              f"decision_records={arm['audit'].get('decision_entries')}")
    ss = r["scale_summary"]
    print(f"  simplest parity-or-better: {ss.get('simplest_parity_or_better_config')}")
    print("=" * 72)
    print(f"  wrote: {json_path}")
    print(f"  wrote: {md_path}")


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="H1 headline: on-device SLM controller vs MaxPressure on Euston A501 "
                    "(PILOT/SMOKE harness; reused by the powered sweep).")
    ap.add_argument("--end", type=int, default=300,
                    help="sim horizon in seconds (SHORT for smoke; default 300)")
    ap.add_argument("--seed", type=int, default=42, help="SUMO seed (default 42)")
    ap.add_argument("--gate", type=int, default=2,
                    help="event-gate: skip the SLM when total halting < gate (default 2)")
    ap.add_argument("--configs", action="store_true",
                    help="run the {myopic,+coordination,+prediction} config arms "
                         "(one shared baseline + 3 SLM arms) instead of the single "
                         "myopic smoke")
    ap.add_argument("--stub", action="store_true",
                    help="config arms with the deterministic StubAgent (no Foundry): "
                         "a WIRING/CAUSALITY validation of the arm machinery on the "
                         "real net, NOT an SLM feasibility result. Implies --configs.")
    return ap


if __name__ == "__main__":
    args = _build_parser().parse_args()
    if args.configs or args.stub:
        run_configs(seed=args.seed, end=args.end, gate=args.gate, stub=args.stub)
    else:
        run(seed=args.seed, end=args.end, gate=args.gate)
