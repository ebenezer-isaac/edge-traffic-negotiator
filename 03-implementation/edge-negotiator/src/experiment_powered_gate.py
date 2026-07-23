"""Powered-runs honest gate (MASTER-SPEC §8 demand-honesty gate; D-H1-perf / D8).

The H1 headline comparison (SLM vs MaxPressure across model x config) and the demand
sweep are DELIBERATELY reported as PILOTS: n small per cell, and -- critically --
the Euston demand is calibrated to a DfT DAILY-resolution AADF source, whose
magnitude + mix are real but whose HOURLY temporal profile, directional split, and
turning proportions are ASSUMED. Per §8's hard startup gate, any INFERENTIAL claim
(significance, confidence intervals, a TOST parity conclusion, a powered null) is
GATED until a NAMED, TIME-RESOLVED demand source (TfL hourly + turning counts + mix)
lands.

This module does NOT fabricate a powered run. It EMITS the honest gate record: what
is claimable now (descriptive pilots, labelled), what is BLOCKED (all inferential
claims), and what would UNBLOCK it (the time-resolved source + the pre-registered
protocol). Reporting a labelled pilot -- or an honest negative -- PASSES the
D-H1-perf reporting gate; the gate fails only if a comparison is missing, un-powered
WITHOUT the pilot label, or silently degraded (§12).
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.normpath(os.path.join(_HERE, "..", "results"))


def _load(name: str):
    p = os.path.join(RESULTS, name)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return None


def build_gate() -> dict:
    """Assemble the honest gate record from whatever pilot artifacts exist."""
    sweep = _load("experiment_sweep.json")
    smoke = _load("experiment_traffic_arms.json")

    pilot_evidence = []
    if sweep:
        st = sweep.get("scale_threshold", {})
        pilot_evidence.append({
            "artifact": "experiment_sweep.json",
            "kind": "model x config feasibility map (PILOT, n=1/cell)",
            "baseline_delay_s": sweep.get("baseline", {}).get("metrics", {}).get(
                "mean_network_delay_s"),
            "scale_threshold_reached": st.get("reached"),
            "smallest_parity_model": st.get("smallest_model"),
            "simplest_parity_config": st.get("simplest_config"),
            "label": sweep.get("label"),
        })
    if smoke:
        pilot_evidence.append({
            "artifact": "experiment_traffic_arms.json",
            "kind": "config-arm smoke (PILOT, n=1/arm)",
            "label": smoke.get("label"),
        })

    record = {
        "experiment": "H1_powered_runs_honest_gate",
        "gate": "D-H1-perf / D8 (§8 demand-honesty startup gate)",
        "status": "GATED (pilot-only) -- inferential runs deferred",
        "claimable_now": [
            "DESCRIPTIVE pilot results, explicitly labelled PILOT / SMOKE / n=1 per "
            "cell (the feasibility map + scale threshold + the config-arm smoke).",
            "An honest NEGATIVE or a conditional POSITIVE is a valid pilot result and "
            "PASSES the D-H1-perf reporting gate when labelled (§12).",
        ],
        "blocked_until_time_resolved_demand": [
            "Any significance / p-value / confidence-interval claim.",
            "A TOST parity conclusion or a powered null (null only when CI half-width "
            "< a pre-registered numeric MDE from an external operational-harm threshold).",
            "n>=30 paired deltas vs MaxPressure with ONE CI method across the study.",
        ],
        "what_would_unblock": [
            "A NAMED, TIME-RESOLVED demand source: TfL hourly counts + turning counts "
            "+ vehicle mix for the Euston A501 corridor (§8/§9).",
            "Then: re-run the sweep at n>=30 seeds/cell under the pinned protocol "
            "(paired deltas, BCa/permutation + Holm, pre-registered MDE, TOST).",
        ],
        "demand_honesty": (
            "Euston demand is DfT DAILY-AADF calibrated: magnitude + mix are REAL "
            "(cp 18077/56815, 2025), the hourly profile + directional split + turning "
            "proportions are ASSUMED. So every H1 traffic result here is a PILOT."),
        "pilot_evidence": pilot_evidence,
        "honest": ("This is an HONEST GATE, not a skipped obligation: the powered "
                   "inferential runs are well-defined and would run unchanged once "
                   "the time-resolved source lands; withholding the inferential claim "
                   "until then is the correct scientific posture, not a gap."),
    }
    return record


def run() -> dict:
    record = build_gate()
    os.makedirs(RESULTS, exist_ok=True)
    json_path = os.path.join(RESULTS, "experiment_powered_gate.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
    md_path = os.path.join(RESULTS, "experiment_powered_gate.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_md(record))
    print("=" * 72)
    print(f"POWERED-RUNS HONEST GATE: {record['status']}")
    for e in record["pilot_evidence"]:
        print(f"  pilot: {e['artifact']} -- {e.get('kind')}")
    print(f"  blocked: {len(record['blocked_until_time_resolved_demand'])} inferential "
          "claim classes deferred until time-resolved TfL demand")
    print("=" * 72)
    print(f"  wrote: {json_path}")
    print(f"  wrote: {md_path}")
    return record


def render_md(r: dict) -> str:
    lines = ["# H1 powered runs: honest §8 demand gate (D-H1-perf / D8)", ""]
    lines.append(f"**Status: {r['status']}**")
    lines.append("")
    lines.append(f"- Gate: {r['gate']}")
    lines.append(f"- Demand honesty: {r['demand_honesty']}")
    lines.append("")
    lines.append("## Claimable now (descriptive pilots)")
    lines.append("")
    for c in r["claimable_now"]:
        lines.append(f"- {c}")
    lines.append("")
    lines.append("## Blocked until time-resolved demand")
    lines.append("")
    for c in r["blocked_until_time_resolved_demand"]:
        lines.append(f"- {c}")
    lines.append("")
    lines.append("## What would unblock it")
    lines.append("")
    for c in r["what_would_unblock"]:
        lines.append(f"- {c}")
    lines.append("")
    lines.append("## Pilot evidence on file")
    lines.append("")
    if r["pilot_evidence"]:
        for e in r["pilot_evidence"]:
            lines.append(f"- `{e['artifact']}` — {e.get('kind')}"
                         + (f"; scale threshold: {e.get('smallest_parity_model')} x "
                            f"{e.get('simplest_parity_config')} (reached="
                            f"{e.get('scale_threshold_reached')})"
                            if e.get("scale_threshold_reached") is not None else ""))
    else:
        lines.append("- (no pilot artifacts found on disk yet)")
    lines.append("")
    lines.append(f"> {r['honest']}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    run()
    sys.exit(0)
