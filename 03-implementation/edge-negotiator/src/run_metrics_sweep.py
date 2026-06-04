"""Honest throughput-controlled coordination sweep (the survivorship-bias-free redo).

WHY THIS EXISTS
---------------
The Milestone-2 sweep headlined ``avg_travel_time_s`` averaged over *completed trips
only*. On the oversaturated 2x2 grid that statistic is survivorship-biased: a
controller that strands the slow, congested vehicles unfinished at the horizon drops
those slow trips from the denominator and can post a spuriously *lower* mean travel
time -- the WRONG SIGN. (See src/metrics.py module docstring and the sibling agent's
finding.)

This runner re-runs the four controller modes (and, for ``coordinated``, a
coord_weight / lambda sweep) and scores every run with the *throughput-controlled*
metrics in src/metrics.py:

    throughput            completed count                       (cannot be gamed by stranding)
    completion_rate       completed / departed                  (needs write-unfinished)
    mean_network_delay    total time-in-network / departed      (needs write-unfinished;
                                                                  stranded vehicles still count)
    total_network_delay   sum of time-in-network over departed
    matched_diff          same-vehicle paired travel-time diff  (two tripinfo files)

To make metrics.py's denominators honest, SUMO MUST emit tripinfo for the WHOLE
vehicle population, not just survivors. We start SUMO with:

    --tripinfo-output <path>
    --tripinfo-output.write-unfinished     (running-at-horizon vehicles, arrival=-1)
    --tripinfo-output.write-undeparted     (loaded-but-blocked vehicles, depart=-1)

REPRODUCIBILITY / SPEED
-----------------------
The SLM is replaced by the deterministic :class:`StubAgent` (injected; NO Foundry
Local). Every (mode, lambda, seed) writes its tripinfo to a UNIQUE path under
results/tripinfo_metrics/ so parallel/repeated runs never collide.

OWNERSHIP
---------
This file is NEW and self-contained. It IMPORTS (never edits) the controllers,
coordination plumbing, CFG/HERE, metrics.py and stats.py. It does NOT call
run_coordinated.run() because that helper hardcodes a shared tripinfo path and omits
the write-unfinished/-undeparted flags; we need our own SUMO invocation. The
controller-wiring here is a faithful copy of run_coordinated.run()'s wiring.

    python src/run_metrics_sweep.py                 # full sweep -> results/coord_throughput.md
    python src/run_metrics_sweep.py --seeds 0 1 2    # quick smaller sweep
    python src/run_metrics_sweep.py --smoke          # 2 seeds, end=200 (sanity)
"""
from __future__ import annotations

import argparse
import json
import os

import traci
from sumolib import checkBinary

import metrics as M
import stats as S
from controllers import FixedTimeController, MaxPressureController
from coordinated_controller import CoordinatedController, StubAgent
from hybrid_controller import HybridController
from run_baseline import CFG, HERE

# Reuse the SAME grid adjacency the production runner uses.
from run_coordinated import ADJACENCY, _build_coordination

# Honest headline metrics we run the full inferential stack on.
HEADLINE_METRICS = ("mean_network_delay", "completion_rate", "throughput")
# Lambda (coord_weight) values swept for the coordinated mode (0.0 == clean ablation
# that reproduces the uncoordinated shield choice exactly).
COORD_WEIGHTS = (0.0, 0.5, 1.0, 2.0, 4.0)
NONCOORD_MODES = ("fixed", "maxpressure", "uncoordinated")
DEFAULT_SEEDS = tuple(range(15))  # 0..14 (>= 15 seeds as required)
DEFAULT_END = 1000

TRIPINFO_DIR = os.path.join(HERE, "..", "results", "tripinfo_metrics")
RESULTS_MD = os.path.join(HERE, "..", "results", "coord_throughput.md")
RESULTS_JSON = os.path.join(HERE, "..", "results", "coord_throughput_raw.json")


# --------------------------------------------------------------------------- #
# One simulation run -> (RunRecord, run-level dict).
# --------------------------------------------------------------------------- #
def _tripinfo_path(mode: str, coord_weight: float | None, seed: int) -> str:
    """Unique per-run tripinfo path so concurrent sims never collide."""
    lam = "na" if coord_weight is None else f"{coord_weight:g}"
    name = f"tripinfo_{mode}_lam{lam}_seed{seed}.xml"
    return os.path.join(TRIPINFO_DIR, name)


def run_one(mode: str, seed: int, end: int = DEFAULT_END,
            coord_weight: float = 1.0) -> dict:
    """Run ONE simulation with StubAgent injected and the full-population tripinfo
    flags, parse it with metrics.py, and return a flat dict of honest metrics +
    coordination provenance + the tripinfo path (for matched-set comparisons).

    No Foundry: the SLM modes always use the deterministic StubAgent.
    """
    if mode not in (*NONCOORD_MODES, "coordinated"):
        raise ValueError(f"unknown mode {mode!r}")

    os.makedirs(TRIPINFO_DIR, exist_ok=True)
    tripinfo = _tripinfo_path(mode, coord_weight if mode == "coordinated" else None, seed)

    binary = checkBinary("sumo")
    # The THREE flags metrics.py requires to see the whole vehicle population.
    traci.start([
        binary, "-c", CFG,
        "--tripinfo-output", tripinfo,
        "--tripinfo-output.write-unfinished",
        "--tripinfo-output.write-undeparted",
        "--seed", str(seed), "--no-warnings", "true",
    ])
    coordination = None
    try:
        tls = list(traci.trafficlight.getIDList())
        agent = StubAgent()  # deterministic, injected: NO Foundry Local

        if mode == "fixed":
            ctrl = FixedTimeController()
        elif mode == "maxpressure":
            ctrl = MaxPressureController(traci, tls)
        elif mode == "uncoordinated":
            ctrl = HybridController(traci, tls, agent, slm_junctions=tls)
        else:  # coordinated
            identities, registry, bus, checker = _build_coordination(tls)
            coordination = {"registry": registry, "bus": bus}
            ctrl = CoordinatedController(
                traci, tls, agent, identities=identities, registry=registry,
                bus=bus, adjacency=ADJACENCY, checker=checker, slm_junctions=tls,
                coord_weight=coord_weight,
            )

        step = 0
        while traci.simulation.getMinExpectedNumber() > 0 and step < end:
            traci.simulationStep()
            ctrl.step()
            step += 1
    finally:
        traci.close()

    # ----- score with the throughput-controlled metrics (metrics.py) -----
    record = M.parse_tripinfo(tripinfo)
    summ = M.summary(record)

    # Sanity: the write flags must have taken effect, otherwise completion_rate
    # collapses to a meaningless 1.0 and mean_network_delay loses stranded vehicles.
    # On an oversaturated grid we EXPECT unfinished/undeparted vehicles; warn loudly
    # if neither flag produced any (would indicate the flags silently failed).
    if not (record.has_unfinished or record.has_undeparted):
        print(f"[WARN] {os.path.basename(tripinfo)}: no unfinished/undeparted vehicles "
              f"present -- completion_rate/mean_network_delay may be untrustworthy "
              f"(write flags may not have applied).")

    row: dict = {
        "mode": mode,
        "seed": seed,
        "coord_weight": coord_weight if mode == "coordinated" else None,
        "sim_steps": step,
        "tripinfo": tripinfo,
        # honest metrics:
        "throughput": summ["throughput"],
        "completion_rate": summ["completion_rate"],
        "mean_network_delay": summ["mean_network_delay"],
        "total_network_delay": summ["total_network_delay"],
        # population provenance:
        "loaded": summ["loaded"],
        "departed": summ["departed"],
        "running_at_end": summ["running_at_end"],
        "undeparted": summ["undeparted"],
        "write_unfinished_present": summ["write_unfinished_present"],
        "write_undeparted_present": summ["write_undeparted_present"],
        # the OLD biased metric, kept for the side-by-side honesty contrast:
        "avg_travel_time_completed": summ["avg_travel_time_completed"],
    }

    # Coordination causal-pathway provenance (coordinated mode only).
    if mode == "coordinated":
        row["coord_adjusted_decisions"] = ctrl.coord_adjusted_decisions
        row["coord_changed_events"] = sum(1 for e in ctrl.events if e.get("coord_changed"))
        row["verified_messages"] = sum(
            len(e.get("received", [])) for e in ctrl.events
            if isinstance(e.get("received"), list))
        row["rejected_messages"] = len(coordination["bus"].rejected)
        row["flagged_detections"] = sum(1 for d in ctrl.detections if d.flagged)
    return row


# --------------------------------------------------------------------------- #
# Sweep orchestration.
# --------------------------------------------------------------------------- #
def run_sweep(seeds, end: int = DEFAULT_END) -> list[dict]:
    """Run every (mode[, lambda], seed) cell and return the flat list of run rows."""
    rows: list[dict] = []
    for mode in NONCOORD_MODES:
        for seed in seeds:
            r = run_one(mode, seed, end=end)
            rows.append(r)
            print(f"[done] mode={mode:13s} seed={seed:2d} "
                  f"thru={r['throughput']:.0f} comp_rate={r['completion_rate']:.3f} "
                  f"mnd={r['mean_network_delay']:.1f}")
    for lam in COORD_WEIGHTS:
        for seed in seeds:
            r = run_one("coordinated", seed, end=end, coord_weight=lam)
            rows.append(r)
            print(f"[done] mode=coordinated  lam={lam:<4g} seed={seed:2d} "
                  f"thru={r['throughput']:.0f} comp_rate={r['completion_rate']:.3f} "
                  f"mnd={r['mean_network_delay']:.1f} "
                  f"coord_adj={r['coord_adjusted_decisions']}")
    return rows


# --------------------------------------------------------------------------- #
# Inference: build per-comparison stats rows.
# --------------------------------------------------------------------------- #
def _label_rows(rows: list[dict]) -> list[dict]:
    """Give each coordinated-lambda its own group label for summarize_sweep.

    summarize_sweep groups on a single key. We synthesise a ``group`` per run:
    non-coordinated modes keep their name; coordinated runs become
    ``coord_lam<lambda>``. This lets one summarize_sweep call compare every
    coordinated-lambda AND uncoordinated against a chosen baseline in one family.
    """
    out = []
    for r in rows:
        if r["mode"] == "coordinated":
            grp = f"coord_lam{r['coord_weight']:g}"
        else:
            grp = r["mode"]
        out.append({**r, "group": grp})
    return out


def _compare(labelled: list[dict], metric: str, baseline: str, groups_keep) -> "object":
    """Run summarize_sweep on a subset of groups vs one baseline, for one metric.

    Filters to ``groups_keep`` (plus the baseline), drops rows with non-finite
    metric values (e.g. completion_rate NaN if nobody departed -- shouldn't happen
    on this grid but we guard), then calls stats.summarize_sweep which gives
    per-group BCa CIs, paired BCa diff vs baseline, permutation p, and Holm.
    """
    import math
    keep = set(groups_keep) | {baseline}
    sub = [r for r in labelled
           if r["group"] in keep and isinstance(r.get(metric), (int, float))
           and not (isinstance(r[metric], float) and math.isnan(r[metric]))]
    return S.summarize_sweep(
        sub, metric=metric, group_key="group", seed_key="seed",
        baseline=baseline, n_boot=10000, n_perm=10000, seed=0,
    )


# --------------------------------------------------------------------------- #
# Matched-set (same-vehicle) paired comparison.
# --------------------------------------------------------------------------- #
def _matched_diff_summary(rows: list[dict], group_a_filter, group_b_filter,
                          label_a: str, label_b: str) -> dict:
    """Average metrics.matched_diff over seeds present in BOTH arms.

    ``group_*_filter`` is a predicate(row)->bool selecting that arm's runs. We pair
    by seed, parse both tripinfo files, and compute matched_diff (avg travel time
    over vehicles completed in BOTH runs). Reports the mean over seeds of
    diff_a_minus_b (negative => arm A faster on shared trips) plus the total
    matched n.
    """
    import numpy as np
    a_by_seed = {r["seed"]: r for r in rows if group_a_filter(r)}
    b_by_seed = {r["seed"]: r for r in rows if group_b_filter(r)}
    shared = sorted(set(a_by_seed) & set(b_by_seed))
    diffs, n_matched, only_a, only_b = [], 0, 0, 0
    for s in shared:
        ra = M.parse_tripinfo(a_by_seed[s]["tripinfo"])
        rb = M.parse_tripinfo(b_by_seed[s]["tripinfo"])
        md = M.matched_diff(ra, rb)
        if md["n_matched"] > 0:
            diffs.append(md["diff_a_minus_b"])
            n_matched += int(md["n_matched"])
            only_a += int(md["n_only_a"])
            only_b += int(md["n_only_b"])
    if not diffs:
        return {"label_a": label_a, "label_b": label_b, "n_seeds": 0,
                "mean_diff_a_minus_b": float("nan"), "ci": (float("nan"), float("nan")),
                "excludes_zero": False, "perm_p": float("nan"),
                "total_n_matched": 0, "only_a": only_a, "only_b": only_b}
    arr = np.array(diffs, dtype=float)
    pt, lo, hi = S.bca_bootstrap(arr, n_boot=10000, seed=0)
    # one-sample-vs-zero permutation: pair each diff against a zero vector
    p = S.permutation_test(arr, np.zeros_like(arr), n_perm=10000, seed=0)
    return {
        "label_a": label_a, "label_b": label_b, "n_seeds": len(diffs),
        "mean_diff_a_minus_b": pt, "ci": (lo, hi),
        "excludes_zero": (lo > 0.0) or (hi < 0.0), "perm_p": p,
        "total_n_matched": n_matched, "only_a": only_a, "only_b": only_b,
    }


# --------------------------------------------------------------------------- #
# Report rendering.
# --------------------------------------------------------------------------- #
def _fmt(v, nd=3):
    if v is None:
        return "n/a"
    if isinstance(v, float):
        if v != v:
            return "NaN"
        return f"{v:.{nd}f}"
    return str(v)


def _mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float)) and not (isinstance(x, float) and x != x)]
    return sum(xs) / len(xs) if xs else float("nan")


def _lambda_table(rows: list[dict]) -> str:
    """Per-lambda mean of every honest metric + coord_adjusted_decisions."""
    hdr = ("| lambda | n | coord_adj_decisions | throughput | completion_rate | "
           "mean_network_delay | total_network_delay | avg_tt_completed (biased) |")
    sep = "| --- | --- | --- | --- | --- | --- | --- | --- |"
    lines = [hdr, sep]
    for lam in COORD_WEIGHTS:
        sub = [r for r in rows if r["mode"] == "coordinated" and r["coord_weight"] == lam]
        if not sub:
            continue
        lines.append(
            f"| {lam:g} | {len(sub)} | {_mean([r['coord_adjusted_decisions'] for r in sub]):.1f} | "
            f"{_mean([r['throughput'] for r in sub]):.1f} | "
            f"{_mean([r['completion_rate'] for r in sub]):.3f} | "
            f"{_mean([r['mean_network_delay'] for r in sub]):.1f} | "
            f"{_mean([r['total_network_delay'] for r in sub]):.0f} | "
            f"{_mean([r['avg_travel_time_completed'] for r in sub]):.1f} |")
    return "\n".join(lines)


def _mode_table(rows: list[dict]) -> str:
    hdr = ("| mode | n | throughput | completion_rate | mean_network_delay | "
           "total_network_delay | avg_tt_completed (biased) |")
    sep = "| --- | --- | --- | --- | --- | --- | --- |"
    lines = [hdr, sep]
    for mode in NONCOORD_MODES:
        sub = [r for r in rows if r["mode"] == mode]
        if not sub:
            continue
        lines.append(
            f"| {mode} | {len(sub)} | {_mean([r['throughput'] for r in sub]):.1f} | "
            f"{_mean([r['completion_rate'] for r in sub]):.3f} | "
            f"{_mean([r['mean_network_delay'] for r in sub]):.1f} | "
            f"{_mean([r['total_network_delay'] for r in sub]):.0f} | "
            f"{_mean([r['avg_travel_time_completed'] for r in sub]):.1f} |")
    return "\n".join(lines)


def _stats_table(df, metric: str, lower_is_better: bool) -> str:
    """Render a summarize_sweep DataFrame into a markdown table."""
    dir_word = "lower=better" if lower_is_better else "higher=better"
    hdr = (f"| group | n | mean | 95% BCa CI | diff vs base | diff 95% BCa CI | "
           f"excl 0 | perm p | Holm thr | Holm reject |")
    sep = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    lines = [f"**Metric: {metric} ({dir_word})**", "", hdr, sep]
    for _, r in df.iterrows():
        base = " (baseline)" if r["is_baseline"] else ""
        if r["is_baseline"]:
            diff = diffci = excl = pp = ht = hr = "-"
        else:
            diff = _fmt(r["diff_vs_baseline"], 3)
            diffci = f"[{_fmt(r['diff_ci_lo'],3)}, {_fmt(r['diff_ci_hi'],3)}]"
            excl = "YES" if r["diff_excludes_zero"] else "no"
            pp = _fmt(r["perm_p"], 4)
            ht = _fmt(r["holm_threshold"], 4)
            hr = "REJECT" if r["holm_reject"] else "fail-to-reject"
        lines.append(
            f"| {r['group']}{base} | {int(r['n'])} | {_fmt(r['mean'],3)} | "
            f"[{_fmt(r['ci_lo'],3)}, {_fmt(r['ci_hi'],3)}] | {diff} | {diffci} | "
            f"{excl} | {pp} | {ht} | {hr} |")
    return "\n".join(lines)


def _verdict(rows, labelled) -> tuple[str, list[str]]:
    """Derive the honest help/hurt/neutral verdict from the stats.

    Compares coordinated (each lambda) vs uncoordinated on all three headline
    metrics. A lambda HELPS iff it significantly (Holm-reject) improves a metric
    in the beneficial direction; HURTS iff it significantly worsens one; NEUTRAL
    if no headline metric reaches significance.
    """
    notes: list[str] = []
    coord_groups = [f"coord_lam{l:g}" for l in COORD_WEIGHTS]
    # metric -> (lower_is_better)
    metric_dir = {"mean_network_delay": True, "completion_rate": False, "throughput": False}
    significant_help = significant_hurt = False
    best_lambda = None
    best_mnd = float("inf")
    for metric, lower_better in metric_dir.items():
        df = _compare(labelled, metric, baseline="uncoordinated", groups_keep=coord_groups)
        di = df.set_index("group")
        for g in coord_groups:
            if g not in di.index:
                continue
            row = di.loc[g]
            if not bool(row["holm_reject"]):
                continue
            diff = row["diff_vs_baseline"]  # coord - uncoordinated
            improved = (diff < 0) if lower_better else (diff > 0)
            verb = "HELPS" if improved else "HURTS"
            if improved:
                significant_help = True
            else:
                significant_hurt = True
            notes.append(f"{g} vs uncoordinated on {metric}: diff={diff:+.3f} "
                         f"(perm p={row['perm_p']:.4g}, Holm-reject) -> {verb}")
    # best lambda by mean mean_network_delay (lower better), informational
    for lam in COORD_WEIGHTS:
        sub = [r for r in rows if r["mode"] == "coordinated" and r["coord_weight"] == lam]
        mnd = _mean([r["mean_network_delay"] for r in sub])
        if mnd == mnd and mnd < best_mnd:
            best_mnd, best_lambda = mnd, lam

    if significant_help and not significant_hurt:
        headline = "HELPS"
    elif significant_hurt and not significant_help:
        headline = "HURTS"
    elif significant_help and significant_hurt:
        headline = "MIXED"
    else:
        headline = "NO SIGNIFICANT EFFECT (NEUTRAL)"
    notes.append(f"best lambda by mean_network_delay = {best_lambda:g} "
                 f"(mnd={best_mnd:.1f}) -- informational only, "
                 f"{'' if significant_help or significant_hurt else 'NOT statistically distinguished'}")
    return headline, notes


def build_report(rows: list[dict]) -> str:
    labelled = _label_rows(rows)
    coord_groups = [f"coord_lam{l:g}" for l in COORD_WEIGHTS]
    n_seeds = len({r["seed"] for r in rows})

    parts: list[str] = []
    parts.append("# Honest coordination numbers: throughput-controlled metrics (2x2 grid)")
    parts.append("")
    parts.append(
        "Generated by `src/run_metrics_sweep.py`. The SLM is replaced by the "
        "deterministic `StubAgent` (no Foundry Local). Every run scores the "
        "**throughput-controlled** metrics from `src/metrics.py`, parsed from a "
        "tripinfo emitted with `--tripinfo-output.write-unfinished "
        "--tripinfo-output.write-undeparted` so the whole vehicle population "
        "(completed + stranded-at-horizon + never-departed) is counted. This "
        "resolves the Milestone-2 survivorship bias where avg-travel-time over "
        "*completed trips only* could flip sign.")
    parts.append("")
    parts.append(f"- Seeds: {n_seeds} ({sorted({r['seed'] for r in rows})})")
    parts.append(f"- Horizon: end={rows[0]['sim_steps'] if rows else 'n/a'} steps (per run, capped)")
    parts.append(f"- Lambda (coord_weight) values: {', '.join(f'{l:g}' for l in COORD_WEIGHTS)}")
    parts.append("- Honest headline metrics: throughput (higher=better), "
                 "completion_rate (higher=better), mean_network_delay (lower=better).")
    parts.append("")

    # ---- Verdict (computed first so it can headline) ----
    headline, notes = _verdict(rows, labelled)
    parts.append("## Headline verdict")
    parts.append("")
    parts.append(f"**On throughput-controlled metrics, R2 coordination shows: {headline}** "
                 f"(coordinated vs uncoordinated, Holm-corrected across the lambda family).")
    parts.append("")
    for nt in notes:
        parts.append(f"- {nt}")
    parts.append("")

    # ---- Lambda-sensitivity table ----
    parts.append("## Lambda-sensitivity curve (coordinated mode)")
    parts.append("")
    parts.append("`coord_adj_decisions` = decisions where the coordination-adjusted "
                 "deterministic choice differed from plain MaxPressure (proves the "
                 "pathway is causally live). Each metric is the mean over seeds.")
    parts.append("")
    parts.append(_lambda_table(rows))
    parts.append("")

    # ---- Per-mode honest metrics ----
    parts.append("## Per-mode honest metrics (non-coordinated baselines)")
    parts.append("")
    parts.append(_mode_table(rows))
    parts.append("")

    # ---- Inferential comparisons ----
    parts.append("## Inferential comparisons (BCa 95% CI + paired permutation + Holm)")
    parts.append("")
    parts.append("### A) coordinated(lambda) vs uncoordinated")
    parts.append("")
    for metric in HEADLINE_METRICS:
        lower = metric == "mean_network_delay"
        df = _compare(labelled, metric, baseline="uncoordinated", groups_keep=coord_groups)
        parts.append(_stats_table(df, metric, lower))
        parts.append("")
    parts.append("### B) coordinated(lambda) and uncoordinated vs maxpressure")
    parts.append("")
    for metric in HEADLINE_METRICS:
        lower = metric == "mean_network_delay"
        df = _compare(labelled, metric, baseline="maxpressure",
                      groups_keep=[*coord_groups, "uncoordinated"])
        parts.append(_stats_table(df, metric, lower))
        parts.append("")

    # ---- Matched-set same-vehicle comparison ----
    parts.append("## Matched-set (same-vehicle) travel-time comparison")
    parts.append("")
    parts.append("`matched_diff` averages travel time over ONLY the vehicles that "
                 "completed in BOTH arms (apples-to-apples; the survivorship-bias "
                 "antidote for travel time). diff = A - B; negative => A faster on "
                 "shared trips. CI is BCa over seeds; perm p is paired-vs-zero.")
    parts.append("")
    md_hdr = ("| comparison (A vs B) | seeds | mean diff (A-B) | 95% BCa CI | "
              "excl 0 | perm p | total matched veh | only A | only B |")
    md_sep = "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    md_lines = [md_hdr, md_sep]
    # best lambda by mnd for the matched comparison; default to 1.0 if absent
    best_lam = 1.0
    best_mnd = float("inf")
    for lam in COORD_WEIGHTS:
        sub = [r for r in rows if r["mode"] == "coordinated" and r["coord_weight"] == lam]
        mnd = _mean([r["mean_network_delay"] for r in sub])
        if mnd == mnd and mnd < best_mnd:
            best_mnd, best_lam = mnd, lam
    comparisons = [
        (lambda r, lam=best_lam: r["mode"] == "coordinated" and r["coord_weight"] == lam,
         lambda r: r["mode"] == "uncoordinated",
         f"coord(lam={best_lam:g})", "uncoordinated"),
        (lambda r, lam=best_lam: r["mode"] == "coordinated" and r["coord_weight"] == lam,
         lambda r: r["mode"] == "maxpressure",
         f"coord(lam={best_lam:g})", "maxpressure"),
        (lambda r: r["mode"] == "uncoordinated",
         lambda r: r["mode"] == "maxpressure",
         "uncoordinated", "maxpressure"),
    ]
    for fa, fb, la, lb in comparisons:
        md = _matched_diff_summary(rows, fa, fb, la, lb)
        md_lines.append(
            f"| {md['label_a']} vs {md['label_b']} | {md['n_seeds']} | "
            f"{_fmt(md['mean_diff_a_minus_b'],2)} | "
            f"[{_fmt(md['ci'][0],2)}, {_fmt(md['ci'][1],2)}] | "
            f"{'YES' if md['excludes_zero'] else 'no'} | {_fmt(md['perm_p'],4)} | "
            f"{md['total_n_matched']} | {md['only_a']} | {md['only_b']} |")
    parts.append("\n".join(md_lines))
    parts.append("")

    parts.append("## Method notes")
    parts.append("")
    parts.append("- `throughput` is a count and cannot be gamed by stranding slow "
                 "vehicles. `mean_network_delay` divides total time-in-network by "
                 "ALL departed vehicles (stranded ones keep their accrued time), so "
                 "a 'completes fewer but faster' controller earns no spurious win.")
    parts.append("- The biased `avg_tt_completed` column is shown only for contrast; "
                 "it is NOT the headline.")
    parts.append("- All comparisons are paired on seed; permutation p-values are "
                 "Holm-corrected across each family (the lambda set, plus "
                 "uncoordinated where applicable).")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", nargs="*", type=int, default=list(DEFAULT_SEEDS))
    ap.add_argument("--end", type=int, default=DEFAULT_END)
    ap.add_argument("--smoke", action="store_true",
                    help="quick sanity sweep: 2 seeds, end=200")
    args = ap.parse_args()

    seeds = args.seeds
    end = args.end
    if args.smoke:
        seeds, end = [0, 1], 200

    print(f"=== metrics sweep: seeds={seeds} end={end} ===")
    rows = run_sweep(seeds, end=end)

    os.makedirs(os.path.dirname(RESULTS_JSON), exist_ok=True)
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    print(f"[wrote] {RESULTS_JSON}")

    report = build_report(rows)
    with open(RESULTS_MD, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(f"[wrote] {RESULTS_MD}")


if __name__ == "__main__":
    main()
