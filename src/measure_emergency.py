"""Measurement harness for the exploit-then-defend demo.

Runs the corridor scenario headless in three modes with identical seed/traffic
and SUMO tripinfo output, then extracts the metrics an academic write-up needs:

  * defended  -- the corroboration gate (our system)
  * naive     -- trust-everything victim (honours the signed phantom claim)
  * nopreempt -- plain MaxPressure (ignores all EV triggers); the counterfactual
                 "what would have happened without our emergency layer"

The three runs differ ONLY in the controller's trust/preemption policy, so any
metric delta is attributable to the policy, not to traffic noise. Metrics come
from SUMO's own per-trip output (tripinfo), not from anything the controller
self-reports -- an independent measurement.

    python src/measure_emergency.py            # prints a metrics table (JSON)
"""
from __future__ import annotations

import json
import os
import statistics
import tempfile
import xml.etree.ElementTree as ET

import demo_emergency as dm

MODES = ("defended", "naive", "nopreempt")
SEED = 42
SCALE = 1.0
STEPS = 400
ATTACK_T = 40
ATTACK_END = 100
AMBULANCE_T = 120


def _f(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _classify(veh_id: str) -> str:
    """Map a SUMO vehicle id to a measurement bucket."""
    if veh_id == dm.REAL_AMB:
        return "ambulance"
    if veh_id.startswith("cross_ns2.") or veh_id.startswith("cross_sn2."):
        return "cross_J2"          # the attack target's cross street
    if veh_id.startswith("cross_"):
        return "cross_other"
    if veh_id.startswith("art_"):
        return "arterial"
    return "other"


def parse_tripinfo(path: str) -> dict:
    """Extract per-bucket delay metrics from a SUMO tripinfo file."""
    buckets: dict[str, list[dict]] = {}
    amb: dict | None = None
    root = ET.parse(path).getroot()
    for tr in root.findall("tripinfo"):
        vid = tr.get("id", "")
        rec = {
            "duration": _f(tr.get("duration")),
            "timeLoss": _f(tr.get("timeLoss")),
            "waitingTime": _f(tr.get("waitingTime")),
            "routeLength": _f(tr.get("routeLength")),
            "arrival": _f(tr.get("arrival")),
        }
        b = _classify(vid)
        if b == "ambulance":
            amb = rec
        buckets.setdefault(b, []).append(rec)

    def agg(recs, key):
        vals = [r[key] for r in recs]
        return {
            "n": len(vals),
            "mean": round(statistics.mean(vals), 2) if vals else None,
            "max": round(max(vals), 2) if vals else None,
            "total": round(sum(vals), 2) if vals else 0.0,
        }

    return {
        "ambulance": ({"duration": amb["duration"], "timeLoss": amb["timeLoss"],
                       "waitingTime": amb["waitingTime"]} if amb else None),
        "cross_J2_timeLoss": agg(buckets.get("cross_J2", []), "timeLoss"),
        "cross_J2_waitingTime": agg(buckets.get("cross_J2", []), "waitingTime"),
        "arterial_timeLoss": agg(buckets.get("arterial", []), "timeLoss"),
        "network_timeLoss": agg(
            [r for b, recs in buckets.items() for r in recs
             if b != "ambulance"], "timeLoss"),
        "network_completed": sum(
            len(recs) for b, recs in buckets.items() if b != "ambulance"),
    }


def _bootstrap_ci(values, reps=5000, alpha=0.05, rng=None):
    """Percentile bootstrap 95% CI for the mean of ``values`` (paired deltas)."""
    import random
    if not values:
        return (None, None)
    rng = rng or random.Random(12345)
    n = len(values)
    means = []
    for _ in range(reps):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int((alpha / 2) * reps)]
    hi = means[int((1 - alpha / 2) * reps) - 1]
    return (round(lo, 2), round(hi, 2))


def _scalars(parsed: dict) -> dict:
    """Pull the scalar metrics we compare from one parsed tripinfo dict."""
    amb = parsed["ambulance"]
    return {
        "amb_dur": amb["duration"] if amb else None,
        "crossJ2_mean": parsed["cross_J2_timeLoss"]["mean"] or 0.0,
        "crossJ2_max": parsed["cross_J2_timeLoss"]["max"] or 0.0,
        "net_mean": parsed["network_timeLoss"]["mean"] or 0.0,
    }


def multi(n_seeds: int = 30, scale: float = SCALE, steps: int = STEPS) -> dict:
    """Powered comparison: run all 3 modes across ``n_seeds`` seeds (paired on
    seed) and report each delta's mean + 95% bootstrap CI."""
    import statistics
    deltas = {"ev_benefit_s": [], "gate_cost_s": [],
              "attack_harm_avoided_s": [], "attack_worstcase_avoided_s": []}
    with tempfile.TemporaryDirectory() as td:
        for seed in range(n_seeds):
            s = {}
            for mode in MODES:
                tp = os.path.join(td, f"t_{mode}_{seed}.xml")
                dm.run(gui=False, delay=0.0, seed=seed, end=steps, scale=scale,
                       attack_t=ATTACK_T, attack_end=ATTACK_END,
                       ambulance_t=AMBULANCE_T, verbose=False, mode=mode,
                       tripinfo_path=tp)
                s[mode] = _scalars(parse_tripinfo(tp))
            if (s["nopreempt"]["amb_dur"] is not None
                    and s["defended"]["amb_dur"] is not None
                    and s["naive"]["amb_dur"] is not None):
                deltas["ev_benefit_s"].append(
                    s["nopreempt"]["amb_dur"] - s["defended"]["amb_dur"])
                deltas["gate_cost_s"].append(
                    s["defended"]["amb_dur"] - s["naive"]["amb_dur"])
            deltas["attack_harm_avoided_s"].append(
                s["naive"]["crossJ2_mean"] - s["defended"]["crossJ2_mean"])
            deltas["attack_worstcase_avoided_s"].append(
                s["naive"]["crossJ2_max"] - s["defended"]["crossJ2_max"])

    summary = {"n_seeds": n_seeds, "scale": scale}
    for k, vals in deltas.items():
        summary[k] = {
            "n": len(vals),
            "mean": round(statistics.mean(vals), 2) if vals else None,
            "sd": round(statistics.pstdev(vals), 2) if len(vals) > 1 else None,
            "ci95": _bootstrap_ci(vals),
        }
    print(json.dumps(summary, indent=2))
    return summary


def main() -> dict:
    out: dict[str, dict] = {}
    with tempfile.TemporaryDirectory() as td:
        for mode in MODES:
            tp = os.path.join(td, f"tripinfo_{mode}.xml")
            dm.run(gui=False, delay=0.0, seed=SEED, end=STEPS, scale=SCALE,
                   attack_t=ATTACK_T, attack_end=ATTACK_END,
                   ambulance_t=AMBULANCE_T, verbose=False, mode=mode,
                   tripinfo_path=tp)
            out[mode] = parse_tripinfo(tp)

    # Derived comparisons the report leans on.
    def amb_dur(m):
        a = out[m]["ambulance"]
        return a["duration"] if a else None
    def crossj2(m):
        return out[m]["cross_J2_timeLoss"]["mean"]
    derived = {
        "ambulance_duration_s": {m: amb_dur(m) for m in MODES},
        "ev_preemption_benefit_s (nopreempt - defended)": (
            round(amb_dur("nopreempt") - amb_dur("defended"), 2)
            if amb_dur("nopreempt") is not None and amb_dur("defended") is not None
            else None),
        "cross_J2_mean_timeLoss_s": {m: crossj2(m) for m in MODES},
        "attack_harm_avoided_s (naive - defended, cross_J2 mean timeLoss)": (
            round((crossj2("naive") or 0) - (crossj2("defended") or 0), 2)),
    }
    result = {"config": {"seed": SEED, "scale": SCALE, "steps": STEPS,
                         "attack_window": [ATTACK_T, ATTACK_END],
                         "ambulance_t": AMBULANCE_T},
              "per_mode": out, "derived": derived}
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    import sys
    if "--multi" in sys.argv:
        n = 30
        for a in sys.argv:
            if a.startswith("--seeds="):
                n = int(a.split("=", 1)[1])
        sc = SCALE
        for a in sys.argv:
            if a.startswith("--scale="):
                sc = float(a.split("=", 1)[1])
        multi(n_seeds=n, scale=sc)
    else:
        main()
