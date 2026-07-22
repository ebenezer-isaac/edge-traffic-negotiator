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
ROUTES = os.path.join(_SUMO_EUSTON, "base.rou.xml")

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
                     neighbor_note: str = ""):  # noqa: ARG002 - myopic, note unused
        return None


class TimingAgent:
    """Wrap a real agent, timing every ``choose_phase`` call (per-decision latency).

    Calls the inner agent MYOPICALLY (no neighbour note is forwarded), matching the
    H1 myopic config. Records per-call wall-clock so ``slm_latency.summarize_latency``
    can profile choose_phase against the decision interval.
    """

    def __init__(self, inner):
        self.inner = inner
        self.model = getattr(inner, "model", "unknown")
        self.latencies_s: list[float] = []
        self.calls = 0
        self.none_returns = 0

    def choose_phase(self, junction_id, num_phases, halting_per_phase,
                     neighbor_note: str = ""):  # noqa: ARG002 - myopic: note dropped
        self.calls += 1
        t0 = perf_counter()
        out = self.inner.choose_phase(junction_id, num_phases, halting_per_phase)
        self.latencies_s.append(perf_counter() - t0)
        if out is None:
            self.none_returns += 1
        return out


# --------------------------------------------------------------------------- #
# Harness building blocks (pure / testable without SUMO or Foundry).
# --------------------------------------------------------------------------- #
def build_controller(conn, tls_ids, agent, *, gate: int = 2,
                     min_green: int = DECISION_INTERVAL_S, yellow: int = 3):
    """Build the SHARED shield-gated wiring for one arm.

    Both arms use HybridController (SLM proposes, MaxPressure shield disposes,
    event-gated). The baseline passes a NullAgent; the SLM arm passes a TimingAgent
    wrapping the live SLMAgent. Reusing one controller class keeps the arms
    apples-to-apples: only the proposal source changes.
    """
    return HybridController(conn, tls_ids, agent, gate=gate,
                            min_green=min_green, yellow=yellow)


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
def run_arm(arm: str, agent, *, seed: int, end: int, gate: int = 2) -> dict:
    """Run ONE controller arm end-to-end on the Euston net; return its result dict.

    Live-gated on SUMO (imports traci/sumolib inside). Injects a fresh AuditLog and
    mirrors every controller decision into it, then asserts audit integrity.
    """
    import traci
    from sumolib import checkBinary

    binary = checkBinary("sumo")
    tripinfo = os.path.join(_SUMO_EUSTON, f"tripinfo_h1_{arm}_s{seed}.xml")
    # write-unfinished + write-undeparted so metrics.py sees the WHOLE population
    # (departed/running/undeparted), not just survivors. time-to-teleport 300 so
    # gridlock surfaces honestly as teleports (matches sumo/euston/euston.sumocfg).
    traci.start([binary, "-n", NET, "-r", ROUTES,
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
    try:
        tls = list(traci.trafficlight.getIDList())
        identities = {tl: JunctionIdentity(tl) for tl in tls}
        ctrl = build_controller(traci, tls, agent, gate=gate)
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
    return {
        "arm": arm,
        "controller_model": getattr(agent, "model", "unknown"),
        "controlled_tls": tls,
        "metrics": metrics_from_tripinfo(tripinfo, teleports, step),
        "decision_stats": decision_stats(events),
        "audit": audit_bundle(audit, public_keys),
        "tripinfo": tripinfo,
    }


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


def verdict(baseline: dict, slm: dict | None) -> dict:
    """Honest match/beat/lose on delay at THIS config (no significance claim)."""
    if slm is None or slm.get("skipped"):
        return {"status": "no_comparison",
                "reason": "SLM arm skipped (Foundry precondition unmet); baseline only"}
    b = baseline["metrics"]
    s = slm["metrics"]
    bd, sd = _num(b.get("mean_network_delay_s")), _num(s.get("mean_network_delay_s"))
    if bd is None or sd is None:
        return {"status": "indeterminate", "reason": "a mean_network_delay is undefined (nobody departed?)"}
    # Lower delay is better. 2% band = "match"; else beat/lose.
    rel = (sd - bd) / bd if bd else float("inf")
    if abs(rel) <= 0.02:
        status = "match"
    elif sd < bd:
        status = "slm_beats"
    else:
        status = "slm_loses"
    return {
        "status": status,
        "metric": "mean_network_delay_s (lower is better)",
        "baseline_delay_s": bd,
        "slm_delay_s": sd,
        "slm_minus_baseline_s": sd - bd,
        "slm_relative_delay": rel,
        "baseline_completed": b.get("completed"),
        "slm_completed": s.get("completed"),
        "note": ("SMOKE / PILOT: n=1, short horizon, DfT-daily-AADF demand -- "
                 "descriptive only, NO significance/inferential claim (§8)."),
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


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="H1 headline: on-device SLM controller vs MaxPressure on Euston A501 "
                    "(PILOT/SMOKE harness; reused by the powered sweep).")
    ap.add_argument("--end", type=int, default=300,
                    help="sim horizon in seconds (SHORT for smoke; default 300)")
    ap.add_argument("--seed", type=int, default=42, help="SUMO seed (default 42)")
    ap.add_argument("--gate", type=int, default=2,
                    help="event-gate: skip the SLM when total halting < gate (default 2)")
    return ap


if __name__ == "__main__":
    args = _build_parser().parse_args()
    run(seed=args.seed, end=args.end, gate=args.gate)
