"""High-N deterministic baseline sweep: fixed-time vs MaxPressure on the 2x2 grid.

Purpose (de-risking the Wk9-10 evaluation methodology)
------------------------------------------------------
1. POWER. Milestone-2 used n=3 seeds; the paired permutation test could not reject
   even a real effect (min two-sided p at n=3 is 1/(2^3+1)... and the Monte-Carlo
   floor sat at ~0.244). This sweep uses n=30 deterministic seeds, instant (no Foundry
   Local), so the stats+sim pipeline gets a fair chance to detect a real effect.

2. SURVIVORSHIP BIAS. We emit tripinfo with --write-unfinished and --write-undeparted
   so src/metrics.py can compute throughput-controlled metrics (completion_rate,
   total/mean network delay, matched-set diff) ALONGSIDE the old completed-only
   average. The report shows whether the picture changes.

3. PIPELINE VALIDATION (positive control). MaxPressure is throughput-optimal and is
   expected to beat fixed-time. If the n=30 pipeline does NOT detect this, that is a
   real finding about sim/metric sensitivity -- we report it honestly rather than
   tuning until it passes.

This module OWNS its own SUMO invocation (it must pass the --write-* flags that
run_baseline.run does not), but reuses CFG/HERE from run_baseline and the stats API.

    .venv/Scripts/python src/sweep_baselines.py            # 30 seeds, writes report
    .venv/Scripts/python src/sweep_baselines.py --seeds 5  # quick smoke
"""
from __future__ import annotations

import argparse
import os
from typing import Dict, List

import traci
from sumolib import checkBinary

import metrics as M
import stats
from controllers import FixedTimeController, MaxPressureController
from run_baseline import CFG, HERE

MODES = ("fixed", "maxpressure")
DEFAULT_SEEDS = list(range(1, 31))  # 30 deterministic seeds
END = 1000  # match the sumocfg horizon


def _run_one(mode: str, seed: int, end: int = END) -> M.RunRecord:
    """Run one (mode, seed) sim and parse the FULL-population tripinfo.

    Emits tripinfo with write-unfinished + write-undeparted so the parsed RunRecord
    describes loaded/departed/completed/running, not just survivors.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    binary = checkBinary("sumo")
    tripinfo = os.path.join(HERE, "..", "sumo", f"tripinfo_sweep_{mode}_{seed}.xml")
    traci.start([
        binary, "-c", CFG,
        "--tripinfo-output", tripinfo,
        "--tripinfo-output.write-unfinished",
        "--tripinfo-output.write-undeparted",
        "--seed", str(seed),
        "--no-warnings", "true",
        "--end", str(end),
    ])
    try:
        tls = list(traci.trafficlight.getIDList())
        ctrl = MaxPressureController(traci, tls) if mode == "maxpressure" else FixedTimeController()
        step = 0
        while traci.simulation.getMinExpectedNumber() > 0 and step < end:
            traci.simulationStep()
            ctrl.step()
            step += 1
    finally:
        traci.close()
    return M.parse_tripinfo(tripinfo)


def sweep(seeds: List[int]) -> List[Dict]:
    """Run every (mode, seed) pair; return one flat metric dict per run.

    Each row carries the stats grouping keys (mode, seed) plus every scalar from
    metrics.summary(), so it can be fed straight into stats.summarize_sweep on any
    metric column.
    """
    rows: List[Dict] = []
    runs: Dict[tuple, M.RunRecord] = {}
    for seed in seeds:
        for mode in MODES:
            run = _run_one(mode, seed)
            runs[(mode, seed)] = run
            row = {"mode": mode, "seed": seed}
            row.update(M.summary(run))
            rows.append(row)
            print(f"[done] mode={mode:11s} seed={seed:2d} "
                  f"thru={int(row['throughput']):3d} "
                  f"compl_rate={row['completion_rate']:.3f} "
                  f"old_avg_tt={row['avg_travel_time_completed']:.2f} "
                  f"mean_net_delay={row['mean_network_delay']:.2f}")
    # Stash the parsed runs for the matched-set analysis.
    sweep.runs = runs  # type: ignore[attr-defined]
    return rows


def _matched_set_rows(runs: Dict[tuple, M.RunRecord], seeds: List[int]) -> List[Dict]:
    """Per-seed apples-to-apples matched-set diff (maxpressure - fixed).

    Restricts to vehicles that completed in BOTH controllers for that seed, so a
    controller cannot win by completing a different (slower) subset.
    """
    out: List[Dict] = []
    for seed in seeds:
        mp = runs[("maxpressure", seed)]
        fx = runs[("fixed", seed)]
        md = M.matched_diff(mp, fx)
        out.append({"seed": seed, **md})
    return out


def _fmt(x, nd=3):
    try:
        import math
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return "nan"
    except Exception:
        pass
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def _summary_table(rows: List[Dict], metric: str, baseline: str) -> str:
    df = stats.summarize_sweep(
        rows, metric=metric, group_key="mode", seed_key="seed",
        baseline=baseline, n_boot=10000, n_perm=10000, seed=0,
        alternative="two-sided",
    )
    cols = ["group", "n", "mean", "ci_lo", "ci_hi", "diff_vs_baseline",
            "diff_ci_lo", "diff_ci_hi", "diff_excludes_zero", "perm_p",
            "holm_threshold", "holm_reject"]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    lines = [header, sep]
    for _, r in df.iterrows():
        vals = [
            r["group"], int(r["n"]), _fmt(r["mean"], 2), _fmt(r["ci_lo"], 2),
            _fmt(r["ci_hi"], 2), _fmt(r["diff_vs_baseline"], 3),
            _fmt(r["diff_ci_lo"], 3), _fmt(r["diff_ci_hi"], 3),
            bool(r["diff_excludes_zero"]), _fmt(r["perm_p"], 5),
            _fmt(r["holm_threshold"], 5), bool(r["holm_reject"]),
        ]
        lines.append("| " + " | ".join(str(v) for v in vals) + " |")
    return "\n".join(lines), df


def write_report(rows: List[Dict], runs: Dict[tuple, M.RunRecord],
                 seeds: List[int], path: str) -> None:
    """Render results/baselines_highN.md with old + new metrics and the verdict."""
    import numpy as np

    n = len(seeds)
    # Metrics to summarise: the OLD biased one, then the throughput-controlled ones.
    metric_blocks = [
        ("avg_travel_time_completed",
         "OLD metric -- mean travel time over COMPLETED trips only (survivorship-biased)"),
        ("throughput", "Throughput -- completed-trip count (cannot be gamed by stranding)"),
        ("completion_rate", "Completion rate -- completed / departed"),
        ("mean_network_delay",
         "NEW metric -- mean time-in-network over ALL departed vehicles (robust)"),
        ("total_network_delay",
         "NEW metric -- total outstanding network delay (completed + still-running)"),
    ]

    parts: List[str] = []
    parts.append("# High-N baseline sweep: fixed-time vs MaxPressure (2x2 grid)\n")
    parts.append(
        f"Deterministic sweep, **n={n} seeds** (seeds {seeds[0]}..{seeds[-1]}), "
        f"END={END} sim-steps, no Foundry Local. Baseline = **fixed**; positive "
        f"direction = MaxPressure should beat fixed-time.\n")
    parts.append(
        "Tripinfo emitted with `--tripinfo-output.write-unfinished "
        "--tripinfo-output.write-undeparted`, so metrics see the WHOLE vehicle "
        "population (loaded/departed/completed/running), not just survivors. "
        "Stats: BCa 95% CIs + paired permutation (10k) + Holm across the family.\n")

    verdicts: Dict[str, Dict] = {}
    for metric, title in metric_blocks:
        # higher-is-better for throughput & completion_rate; lower-is-better otherwise.
        table, df = _summary_table(rows, metric, baseline="fixed")
        parts.append(f"## {title}\n")
        parts.append(f"`metric = {metric}`\n")
        parts.append(table + "\n")
        mp = df.set_index("group").loc["maxpressure"]
        verdicts[metric] = {
            "diff": float(mp["diff_vs_baseline"]),
            "perm_p": float(mp["perm_p"]),
            "holm_reject": bool(mp["holm_reject"]),
            "excludes_zero": bool(mp["diff_excludes_zero"]),
        }

    # Matched-set apples-to-apples block.
    msrows = _matched_set_rows(runs, seeds)
    diffs = np.array([r["diff_a_minus_b"] for r in msrows
                      if not (isinstance(r["diff_a_minus_b"], float)
                              and np.isnan(r["diff_a_minus_b"]))])
    n_matched_tot = sum(int(r["n_matched"]) for r in msrows)
    parts.append("## Matched-set comparison (apples-to-apples)\n")
    parts.append(
        "Per seed, restrict to vehicles that completed under BOTH controllers, then "
        "take MaxPressure_avg - fixed_avg over that shared set. A controller cannot "
        "win here by completing a different (faster) subset. Paired over seeds:\n")
    if diffs.size >= 2:
        pt, lo, hi = stats.bca_bootstrap(diffs, n_boot=10000, seed=0)
        # paired permutation of the per-seed matched diffs against zero
        p = stats.permutation_test(diffs, np.zeros_like(diffs), n_perm=10000, seed=0)
        parts.append(
            f"- matched vehicles (summed over seeds): **{n_matched_tot}**\n"
            f"- mean per-seed matched diff (MaxPressure - fixed): "
            f"**{pt:.3f} s** (BCa 95% CI {lo:.3f}..{hi:.3f})\n"
            f"- paired permutation p (diff != 0): **{p:.5f}**, "
            f"excludes_zero={'yes' if (lo>0 or hi<0) else 'no'}\n")
        verdicts["matched_diff"] = {"diff": float(pt), "perm_p": float(p),
                                    "excludes_zero": bool(lo > 0 or hi < 0)}
    else:
        parts.append("- too few non-empty matched seeds for inference\n")

    # ----- VERDICT -----
    parts.append("## Verdict\n")
    thru = verdicts["throughput"]
    mnd = verdicts["mean_network_delay"]
    old = verdicts["avg_travel_time_completed"]

    detected = thru["holm_reject"] or mnd["holm_reject"]
    parts.append(
        "**Does the n=30 pipeline detect a real effect?** "
        + ("YES -- " if detected else "NO -- ")
        + f"throughput diff (MP-fixed) = {thru['diff']:+.2f} trips "
          f"(perm_p={thru['perm_p']:.4g}, Holm reject={thru['holm_reject']}); "
          f"mean_network_delay diff = {mnd['diff']:+.2f} s "
          f"(perm_p={mnd['perm_p']:.4g}, Holm reject={mnd['holm_reject']}).\n")
    parts.append(
        "**Survivorship bias check.** "
        f"Old completed-only avg-travel-time diff = {old['diff']:+.2f} s "
        f"(perm_p={old['perm_p']:.4g}). "
        "Compare its SIGN/significance to mean_network_delay above: if they disagree, "
        "the old metric was being driven by which trips completed, not by genuinely "
        "faster travel -- exactly the Milestone-2 confound.\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print(f"\n[report] wrote {path}")
    return verdicts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=30,
                    help="number of deterministic seeds (1..N)")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "results",
                                                   "baselines_highN.md"))
    args = ap.parse_args()
    seeds = list(range(1, args.seeds + 1))
    rows = sweep(seeds)
    runs = sweep.runs  # type: ignore[attr-defined]
    write_report(rows, runs, seeds, args.out)


if __name__ == "__main__":
    main()
