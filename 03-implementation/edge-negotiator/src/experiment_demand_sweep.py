"""Experiment 2: demand sweep with system-level trade-offs (Lee + Akin).

Runs the corridor across a demand range (SUMO --scale) for each controller mode,
paired on seed, and reports the system-level metrics the supervisors asked for:
throughput, network delay, fairness across junctions (all four ideologies), and
worst-case delay, plus the emergency and attack effects. Headline deltas carry
BCa bootstrap 95% CIs (the same stats stack as the main harness), so "no harm to
normal traffic" is shown, not asserted, and the effects are located across the
demand range rather than at one operating point.

  python src/experiment_demand_sweep.py                       # full sweep (heavy)
  python src/experiment_demand_sweep.py --seeds 5 --scales 0.7,1.0,1.3
  python src/experiment_demand_sweep.py --seeds 2 --scales 1.0 --modes defended,nopreempt  # smoke

The full sweep (8 scales x 4 modes x 30 seeds) is ~960 headless SUMO runs; run it
in the background. Metrics come from SUMO tripinfo, parsed independently of the
controller.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ET

import demo_emergency as dm
import emergency_metrics as em
import stats
from measure_emergency import ATTACK_T, ATTACK_END, AMBULANCE_T

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.normpath(os.path.join(HERE, "..", "results"))

SCALES = (0.3, 0.5, 0.7, 1.0, 1.3, 1.5, 2.0, 3.0)
MODES = ("nopreempt", "maxpressure_preempt", "defended", "naive")
STEPS = 400
_CROSS = re.compile(r"^cross_(?:ns|sn)(\d+)\.")


def _f(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def parse_run(path: str) -> dict:
    """Per-run metrics from a SUMO tripinfo file, grouped for fairness."""
    per_junction: dict[str, list[float]] = {}
    network: list[float] = []
    completed = 0
    amb_dur = None
    root = ET.parse(path).getroot()
    for tr in root.findall("tripinfo"):
        vid = tr.get("id", "")
        tl = _f(tr.get("timeLoss"))
        if tr.get("arrival") not in (None, "", "-1"):
            completed += 1
        if vid == dm.REAL_AMB:
            amb_dur = _f(tr.get("duration"))
            continue
        network.append(tl)
        m = _CROSS.match(vid)
        if m:
            per_junction.setdefault(f"J{m.group(1)}", []).append(tl)

    groups = {j: v for j, v in per_junction.items() if v}
    fair = em.fairness_report(groups) if groups else {
        "jain": None, "gini": None, "rawlsian_worst_group": None,
        "utilitarian_mean_group": None, "n_groups": 0}
    wc = em.worst_case_report(network) if network else {"max": None, "p95": None, "n": 0}
    # Attack harm is TARGETED at J2's cross street, so the worst case there is the
    # attack-relevant number; the network-wide worst case dilutes it (a targeted
    # attack is near-invisible in the aggregate, which is itself a finding).
    j2 = per_junction.get("J2", [])
    return {
        "throughput": completed,
        "net_mean_timeloss": round(em.utilitarian_mean(network), 3) if network else None,
        "amb_duration": amb_dur,
        "jain": fair["jain"], "gini": fair["gini"],
        "rawlsian_worst_junction": fair["rawlsian_worst_group"],
        "worst_max": wc["max"], "worst_p95": wc["p95"],
        "worst_max_j2": round(max(j2), 3) if j2 else None,
    }


def _bca(deltas, seed=0):
    vals = [d for d in deltas if d is not None]
    if len(vals) < 2:
        return {"n": len(vals), "mean": (round(vals[0], 3) if vals else None),
                "ci95": [None, None]}
    point, lo, hi = stats.bca_bootstrap(vals, seed=seed)
    return {"n": len(vals), "mean": round(point, 3), "ci95": [round(lo, 3), round(hi, 3)]}


def _paired(rows, scale, mode, key):
    """Per-seed values for (scale, mode), ordered by seed, for pairing."""
    sub = {r["seed"]: r[key] for r in rows if r["scale"] == scale and r["mode"] == mode}
    return [sub[s] for s in sorted(sub)]


def _delta(rows, scale, a, b, key):
    """Paired a-minus-b deltas across seeds (None if a seed missing either)."""
    ka = {r["seed"]: r[key] for r in rows if r["scale"] == scale and r["mode"] == a}
    kb = {r["seed"]: r[key] for r in rows if r["scale"] == scale and r["mode"] == b}
    out = []
    for s in sorted(set(ka) & set(kb)):
        if ka[s] is None or kb[s] is None:
            continue
        out.append(ka[s] - kb[s])
    return out


def run(seeds=30, scales=SCALES, modes=MODES, steps=STEPS) -> dict:
    rows = []
    with tempfile.TemporaryDirectory() as td:
        for scale in scales:
            for mode in modes:
                for seed in range(seeds):
                    tp = os.path.join(td, f"t_{mode}_{scale}_{seed}.xml")
                    dm.run(gui=False, delay=0.0, seed=seed, end=steps, scale=scale,
                           attack_t=ATTACK_T, attack_end=ATTACK_END,
                           ambulance_t=AMBULANCE_T, verbose=False, mode=mode,
                           tripinfo_path=tp)
                    m = parse_run(tp)
                    m.update(scale=scale, mode=mode, seed=seed)
                    rows.append(m)

    # Per (scale, mode) means of each metric.
    means = {}
    metric_keys = ("throughput", "net_mean_timeloss", "amb_duration", "jain",
                   "gini", "rawlsian_worst_junction", "worst_max", "worst_p95",
                   "worst_max_j2")
    for scale in scales:
        for mode in modes:
            vals = {k: [r[k] for r in rows if r["scale"] == scale and r["mode"] == mode
                        and r[k] is not None] for k in metric_keys}
            means[f"{scale}|{mode}"] = {
                k: (round(sum(v) / len(v), 3) if v else None) for k, v in vals.items()}

    # Headline deltas per scale, paired on seed, with BCa CIs.
    have = set(modes)
    deltas = {}
    for scale in scales:
        d = {}
        if {"nopreempt", "defended"} <= have:
            d["ev_benefit_s (nopreempt-defended amb)"] = _bca(
                _delta(rows, scale, "nopreempt", "defended", "amb_duration"))
        if {"maxpressure_preempt", "defended"} <= have:
            d["coordination_gain_s (mpp-defended amb)"] = _bca(
                _delta(rows, scale, "maxpressure_preempt", "defended", "amb_duration"))
            d["no_harm_netdelay_s (defended-mpp)"] = _bca(
                _delta(rows, scale, "defended", "maxpressure_preempt", "net_mean_timeloss"))
        if {"naive", "defended"} <= have:
            d["attack_worstcase_avoided_s (naive-defended, J2)"] = _bca(
                _delta(rows, scale, "naive", "defended", "worst_max_j2"))
            d["fairness_gain_jain (defended-naive)"] = _bca(
                _delta(rows, scale, "defended", "naive", "jain"))
        deltas[str(scale)] = d

    out = {"experiment": "demand_sweep", "seeds": seeds,
           "scales": list(scales), "modes": list(modes), "steps": steps,
           "per_scale_mode_means": means, "headline_deltas_by_scale": deltas}

    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "experiment2_demand_sweep.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    _write_md(out)
    print(json.dumps({"scales": out["scales"], "modes": out["modes"],
                      "seeds": seeds, "n_runs": len(rows)}, indent=2))
    print(f"written: {os.path.join(RESULTS, 'experiment2_demand_sweep.json')}")
    return out


def _write_md(out: dict) -> None:
    lines = ["# Experiment 2: demand sweep (system-level trade-offs)", "",
             f"Seeds={out['seeds']} (paired), steps={out['steps']}, "
             f"modes={', '.join(out['modes'])}. Metrics from SUMO tripinfo; "
             "headline deltas carry BCa 95% CIs.", "",
             "## Per-scale headline deltas (paired on seed)", ""]
    for scale, d in out["headline_deltas_by_scale"].items():
        lines.append(f"### scale = {scale}")
        lines.append("| effect | mean | 95% CI |")
        lines.append("|---|---|---|")
        for name, s in d.items():
            lines.append(f"| {name} | {s['mean']} | [{s['ci95'][0]}, {s['ci95'][1]}] |")
        lines.append("")
    with open(os.path.join(RESULTS, "experiment2_demand_sweep.md"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Experiment 2: demand sweep.")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--scales", type=str, default=None,
                    help="comma list, e.g. 0.7,1.0,1.3 (default: full sweep)")
    ap.add_argument("--modes", type=str, default=None,
                    help="comma list (default: nopreempt,maxpressure_preempt,defended,naive)")
    ap.add_argument("--steps", type=int, default=STEPS)
    return ap


if __name__ == "__main__":
    args = _build_parser().parse_args()
    sc = tuple(float(x) for x in args.scales.split(",")) if args.scales else SCALES
    md = tuple(x.strip() for x in args.modes.split(",")) if args.modes else MODES
    run(seeds=args.seeds, scales=sc, modes=md, steps=args.steps)
