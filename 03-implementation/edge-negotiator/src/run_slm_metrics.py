"""HONEST coordination effect with the REAL Phi-4-mini SLM (throughput-controlled).

WHY THIS EXISTS
---------------
The deterministic-StubAgent sweep (results/coord_throughput.md) proved that, under
throughput-controlled metrics, Channel-B (the deterministic coordination-adjusted
reference choice) has NO measurable effect on the 2x2 grid: a valid SLM/Stub proposal
always wins, so the adjusted-pressure term is inert on travel time. But that sweep is
BLIND to the dissertation's PRIMARY coordination pathway, Channel-A -- the per-phase
neighbour-note injected into the SLM prompt. A deterministic StubAgent ignores the
note entirely (see coordinated_controller.StubAgent.choose_phase: `neighbor_note`
unused), so the only way to measure the Channel-A coordination effect is to run the
REAL SLM, where the note can actually change the model's phase choice.

This runner therefore runs ONLY the two SLM modes with the REAL SLMAgent:

    uncoordinated   HybridController (SLM proposes, MaxPressure shield disposes),
                    NO neighbour note -> the SLM never sees coordination info.
    coordinated     CoordinatedController, coord_weight=1.0 -> the SLM DOES receive
                    the per-phase neighbour note (Channel A) AND the Channel-B
                    adjusted reference is live as the fallback.

Both arms use the SAME real SLMAgent; the ONLY difference is whether coordination
information reaches the model. So a coordinated-vs-uncoordinated difference here is
attributable to coordination (chiefly Channel A) and nothing else.

METRICS / SUMO FLAGS
--------------------
Every run is scored with the throughput-controlled metrics in src/metrics.py
(throughput, completion_rate, mean_network_delay, total_network_delay, matched_diff).
Those metrics require the WHOLE vehicle population, so SUMO is started WITH:

    --tripinfo-output <unique path under results/tripinfo_slm/>
    --tripinfo-output.write-unfinished     (running-at-horizon, arrival=-1)
    --tripinfo-output.write-undeparted     (loaded-but-blocked, depart=-1)

NOTE: run_coordinated.run() omits those two flags AND hardcodes a shared tripinfo
path, so we compose our own traci.start() that mirrors its controller wiring but adds
the flags + a unique path. We IMPORT (never edit) the controllers, coordination
plumbing, CFG/HERE, metrics.py and stats.py.

SCOPE / SPEED
-------------
Real SLM calls are ~0.5s each and serialised, so scope is MODEST: end=500, seeds
[0,1,2,3] by default (4 seeds). With ~4 SLM junctions event-gated this is hundreds of
serialised calls; the sweep takes a while. Honesty: n=4 is almost certainly
underpowered; the report says so explicitly.

    .venv/Scripts/python src/run_slm_metrics.py                 # default 4 seeds, end=500
    .venv/Scripts/python src/run_slm_metrics.py --seeds 0 1 2 3 4 5
    .venv/Scripts/python src/run_slm_metrics.py --smoke         # 1 seed, end=120 (sanity)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time

import traci
from sumolib import checkBinary

import metrics as M
import stats as S
from coordinated_controller import CoordinatedController
from hybrid_controller import HybridController
from run_baseline import CFG, HERE
from run_coordinated import ADJACENCY, _build_coordination

# The two REAL-SLM arms we compare. coordinated uses coord_weight=1.0 so BOTH
# Channel A (the prompt note) and Channel B (the adjusted reference) are live.
MODES = ("uncoordinated", "coordinated")
COORD_WEIGHT = 1.0
# Honest headline metrics we run the full inferential stack on (plus matched_diff).
HEADLINE_METRICS = ("mean_network_delay", "completion_rate", "throughput")
DEFAULT_SEEDS = (0, 1, 2, 3)
DEFAULT_END = 500

TRIPINFO_DIR = os.path.join(HERE, "..", "results", "tripinfo_slm")
RESULTS_MD = os.path.join(HERE, "..", "results", "coord_slm_honest.md")
RESULTS_JSON = os.path.join(HERE, "..", "results", "coord_slm_honest_raw.json")
PROGRESS = os.path.join(HERE, "..", "results", "coord_slm_progress.txt")


def _log(msg: str) -> None:
    """Print AND append to a progress file so a background run is pollable."""
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(PROGRESS), exist_ok=True)
        with open(PROGRESS, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _real_agent():
    """Construct the real SLMAgent (deferred import: needs Foundry Local)."""
    from slm_agent import SLMAgent
    return SLMAgent()


def _tripinfo_path(mode: str, seed: int) -> str:
    """Unique per-run tripinfo path so repeated/concurrent sims never collide."""
    return os.path.join(TRIPINFO_DIR, f"tripinfo_slm_{mode}_seed{seed}.xml")


def run_one(mode: str, seed: int, agent, end: int = DEFAULT_END) -> dict:
    """Run ONE simulation in ``mode`` with the REAL ``agent`` and the full-population
    tripinfo flags, score it with metrics.py, return a flat dict of honest metrics +
    coordination provenance + the tripinfo path (for matched-set comparisons).
    """
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")

    os.makedirs(TRIPINFO_DIR, exist_ok=True)
    tripinfo = _tripinfo_path(mode, seed)

    binary = checkBinary("sumo")
    # The THREE flags metrics.py requires to see the whole vehicle population --
    # which run_coordinated.run() does NOT pass. This is the crux of owning our own
    # traci.start(): same wiring, honest tripinfo.
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
        if mode == "uncoordinated":
            ctrl = HybridController(traci, tls, agent, slm_junctions=tls)
        else:  # coordinated
            identities, registry, bus, checker = _build_coordination(tls)
            coordination = {"bus": bus}
            ctrl = CoordinatedController(
                traci, tls, agent, identities=identities, registry=registry,
                bus=bus, adjacency=ADJACENCY, checker=checker, slm_junctions=tls,
                coord_weight=COORD_WEIGHT,
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
    if not (record.has_unfinished or record.has_undeparted):
        _log(f"[WARN] {os.path.basename(tripinfo)}: no unfinished/undeparted vehicles "
             f"-- completion_rate/mean_network_delay may be untrustworthy.")

    ev = ctrl.events
    slm_decisions = len(ev)
    slm_differed = sum(1 for e in ev
                       if e["slm_phase"] is not None and e["slm_phase"] != e["shield_phase"])
    slm_none = sum(1 for e in ev if e["slm_phase"] is None)

    row: dict = {
        "mode": mode,
        "seed": seed,
        "coord_weight": COORD_WEIGHT if mode == "coordinated" else None,
        "sim_steps": step,
        "tripinfo": tripinfo,
        "slm_model": getattr(ctrl.agent, "model", "unknown"),
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
        # SLM-loop provenance (proves the real model was actually in the loop):
        "slm_decisions": slm_decisions,
        "slm_differed_from_shield": slm_differed,
        "slm_returned_none": slm_none,
    }

    if mode == "coordinated":
        row["coord_adjusted_decisions"] = ctrl.coord_adjusted_decisions
        row["coord_changed_events"] = sum(1 for e in ev if e.get("coord_changed"))
        row["notes_sent"] = sum(1 for e in ev if e.get("neighbor_note"))
        row["verified_messages"] = sum(
            len(e.get("received", [])) for e in ev if isinstance(e.get("received"), list))
        row["rejected_messages"] = len(coordination["bus"].rejected)
    return row


# --------------------------------------------------------------------------- #
# Sweep orchestration.
# --------------------------------------------------------------------------- #
def run_sweep(seeds, end: int = DEFAULT_END) -> list[dict]:
    """Run every (mode, seed) cell with ONE shared real SLMAgent; return run rows."""
    agent = _real_agent()
    _log(f"SLMAgent constructed: model={getattr(agent, 'model', '?')}")
    rows: list[dict] = []
    total = len(MODES) * len(seeds)
    done = 0
    for mode in MODES:
        for seed in seeds:
            t0 = time.time()
            r = run_one(mode, seed, agent, end=end)
            rows.append(r)
            done += 1
            dt = time.time() - t0
            extra = ""
            if mode == "coordinated":
                extra = (f" coord_adj={r['coord_adjusted_decisions']} "
                         f"notes={r['notes_sent']}")
            _log(f"[done {done}/{total}] mode={mode:13s} seed={seed} "
                 f"thru={r['throughput']:.0f} comp_rate={r['completion_rate']:.3f} "
                 f"mnd={r['mean_network_delay']:.1f} "
                 f"slm_dec={r['slm_decisions']} slm_diff={r['slm_differed_from_shield']}"
                 f"{extra} ({dt:.0f}s)")
    return rows


# --------------------------------------------------------------------------- #
# Inference helpers.
# --------------------------------------------------------------------------- #
def _compare(rows: list[dict], metric: str) -> "object":
    """summarize_sweep: coordinated vs uncoordinated (baseline) on one metric.

    The family here is a single comparison (coordinated vs uncoordinated), so Holm
    reduces to the raw permutation p; we still route through summarize_sweep for the
    paired BCa diff CI + permutation p in one place.
    """
    sub = [r for r in rows
           if isinstance(r.get(metric), (int, float))
           and not (isinstance(r[metric], float) and math.isnan(r[metric]))]
    return S.summarize_sweep(
        sub, metric=metric, group_key="mode", seed_key="seed",
        baseline="uncoordinated", n_boot=10000, n_perm=10000, seed=0,
    )


def _matched_diff_summary(rows: list[dict]) -> dict:
    """Paired same-vehicle travel-time diff: coordinated - uncoordinated, over seeds.

    For each seed present in BOTH arms, parse both tripinfo files and compute
    metrics.matched_diff (avg travel time over vehicles that completed in BOTH runs).
    diff_a_minus_b with A=coordinated, B=uncoordinated; negative => coordination is
    faster on shared trips. Reports BCa CI + paired-vs-zero permutation p over seeds.
    """
    import numpy as np
    a_by_seed = {r["seed"]: r for r in rows if r["mode"] == "coordinated"}
    b_by_seed = {r["seed"]: r for r in rows if r["mode"] == "uncoordinated"}
    shared = sorted(set(a_by_seed) & set(b_by_seed))
    diffs, per_seed, n_matched, only_a, only_b = [], [], 0, 0, 0
    for s in shared:
        ra = M.parse_tripinfo(a_by_seed[s]["tripinfo"])
        rb = M.parse_tripinfo(b_by_seed[s]["tripinfo"])
        md = M.matched_diff(ra, rb)
        if md["n_matched"] > 0:
            diffs.append(md["diff_a_minus_b"])
            per_seed.append({"seed": s, "diff": md["diff_a_minus_b"],
                             "n_matched": int(md["n_matched"])})
            n_matched += int(md["n_matched"])
            only_a += int(md["n_only_a"])
            only_b += int(md["n_only_b"])
    if not diffs:
        return {"n_seeds": 0, "mean_diff": float("nan"),
                "ci": (float("nan"), float("nan")), "excludes_zero": False,
                "perm_p": float("nan"), "total_n_matched": 0,
                "only_coord": only_a, "only_uncoord": only_b, "per_seed": per_seed}
    arr = np.array(diffs, dtype=float)
    pt, lo, hi = S.bca_bootstrap(arr, n_boot=10000, seed=0)
    p = S.permutation_test(arr, np.zeros_like(arr), n_perm=10000, seed=0)
    return {
        "n_seeds": len(diffs), "mean_diff": pt, "ci": (lo, hi),
        "excludes_zero": (lo > 0.0) or (hi < 0.0), "perm_p": p,
        "total_n_matched": n_matched, "only_coord": only_a, "only_uncoord": only_b,
        "per_seed": per_seed,
    }


# --------------------------------------------------------------------------- #
# Report rendering.
# --------------------------------------------------------------------------- #
def _fmt(v, nd=3):
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return "NaN" if v != v else f"{v:.{nd}f}"
    return str(v)


def _mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))
          and not (isinstance(x, float) and x != x)]
    return sum(xs) / len(xs) if xs else float("nan")


def _mode_table(rows: list[dict]) -> str:
    hdr = ("| mode | n | throughput | completion_rate | mean_network_delay | "
           "total_network_delay | avg_tt_completed (biased) | slm_decisions | "
           "slm_differed_from_shield |")
    sep = "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    lines = [hdr, sep]
    for mode in MODES:
        sub = [r for r in rows if r["mode"] == mode]
        if not sub:
            continue
        lines.append(
            f"| {mode} | {len(sub)} | {_mean([r['throughput'] for r in sub]):.1f} | "
            f"{_mean([r['completion_rate'] for r in sub]):.3f} | "
            f"{_mean([r['mean_network_delay'] for r in sub]):.1f} | "
            f"{_mean([r['total_network_delay'] for r in sub]):.0f} | "
            f"{_mean([r['avg_travel_time_completed'] for r in sub]):.1f} | "
            f"{_mean([r['slm_decisions'] for r in sub]):.0f} | "
            f"{_mean([r['slm_differed_from_shield'] for r in sub]):.1f} |")
    return "\n".join(lines)


def _stats_table(df, metric: str, lower_is_better: bool) -> str:
    dir_word = "lower=better" if lower_is_better else "higher=better"
    hdr = ("| group | n | mean | 95% BCa CI | diff vs uncoord | diff 95% BCa CI | "
           "excl 0 | perm p | Holm thr | Holm reject |")
    sep = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    lines = [f"**Metric: {metric} ({dir_word})**", "", hdr, sep]
    for _, r in df.iterrows():
        base = " (baseline)" if r["is_baseline"] else ""
        if r["is_baseline"]:
            diff = diffci = excl = pp = ht = hr = "-"
        else:
            diff = _fmt(r["diff_vs_baseline"], 3)
            diffci = f"[{_fmt(r['diff_ci_lo'], 3)}, {_fmt(r['diff_ci_hi'], 3)}]"
            excl = "YES" if r["diff_excludes_zero"] else "no"
            pp = _fmt(r["perm_p"], 4)
            ht = _fmt(r["holm_threshold"], 4)
            hr = "REJECT" if r["holm_reject"] else "fail-to-reject"
        lines.append(
            f"| {r['group']}{base} | {int(r['n'])} | {_fmt(r['mean'], 3)} | "
            f"[{_fmt(r['ci_lo'], 3)}, {_fmt(r['ci_hi'], 3)}] | {diff} | {diffci} | "
            f"{excl} | {pp} | {ht} | {hr} |")
    return "\n".join(lines)


def _verdict(rows: list[dict], md: dict) -> tuple[str, list[str]]:
    """Honest help/hurt/neutral verdict, coordinated vs uncoordinated (real SLM).

    A metric where coordinated significantly (CI excludes 0) beats uncoordinated in
    the beneficial direction -> HELPS; significantly worse -> HURTS; nothing
    significant on any headline metric or matched_diff -> NEUTRAL.
    """
    notes: list[str] = []
    metric_dir = {"mean_network_delay": True, "completion_rate": False,
                  "throughput": False}
    help_, hurt = False, False
    for metric, lower_better in metric_dir.items():
        df = _compare(rows, metric)
        di = df.set_index("group")
        if "coordinated" not in di.index:
            continue
        r = di.loc["coordinated"]
        diff = r["diff_vs_baseline"]
        sig = bool(r["diff_excludes_zero"])
        improved = (diff < 0) if lower_better else (diff > 0)
        tag = "(CI excludes 0)" if sig else "(CI includes 0; n.s.)"
        verb = "improved" if improved else "worsened"
        notes.append(f"{metric}: coordinated {verb} by diff={diff:+.3f} vs uncoordinated, "
                     f"perm p={_fmt(r['perm_p'], 4)} {tag}")
        if sig:
            (help_, hurt) = (True, hurt) if improved else (help_, True)
    # matched-set same-vehicle travel time
    if md["n_seeds"] > 0:
        sig = md["excludes_zero"]
        improved = md["mean_diff"] < 0  # coord faster on shared trips
        tag = "(CI excludes 0)" if sig else "(CI includes 0; n.s.)"
        notes.append(f"matched_diff (same-vehicle travel time, coord - uncoord): "
                     f"{md['mean_diff']:+.2f}s, perm p={_fmt(md['perm_p'], 4)} {tag}")
        if sig:
            (help_, hurt) = (True, hurt) if improved else (help_, True)

    if help_ and not hurt:
        return "HELPS", notes
    if hurt and not help_:
        return "HURTS", notes
    if help_ and hurt:
        return "MIXED", notes
    return "NO SIGNIFICANT EFFECT (NEUTRAL)", notes


def build_report(rows: list[dict]) -> str:
    n_seeds = len({r["seed"] for r in rows})
    seeds = sorted({r["seed"] for r in rows})
    end = rows[0]["sim_steps"] if rows else "n/a"
    model = next((r.get("slm_model") for r in rows if r.get("slm_model")), "unknown")
    md = _matched_diff_summary(rows)

    # coordination provenance totals (proves Channel A/B were live)
    coord_rows = [r for r in rows if r["mode"] == "coordinated"]
    tot_coord_adj = sum(r.get("coord_adjusted_decisions", 0) for r in coord_rows)
    tot_coord_changed = sum(r.get("coord_changed_events", 0) for r in coord_rows)
    tot_notes = sum(r.get("notes_sent", 0) for r in coord_rows)
    tot_verified = sum(r.get("verified_messages", 0) for r in coord_rows)

    headline, notes = _verdict(rows, md)
    underpowered = n_seeds < 8

    p: list[str] = []
    p.append("# Honest coordination effect with the REAL Phi-4-mini SLM "
             "(throughput-controlled, 2x2 grid)")
    p.append("")
    p.append(
        "Generated by `src/run_slm_metrics.py`. Both arms use the **real SLMAgent** "
        f"(`{model}` via Foundry Local); the ONLY difference is whether coordination "
        "information reaches the model. `uncoordinated` runs the event-gated hybrid "
        "(SLM proposes, MaxPressure shield disposes) with NO neighbour note; "
        "`coordinated` (coord_weight=1.0) additionally injects the per-phase "
        "neighbour-note into the SLM prompt (**Channel A**) and makes the "
        "coordination-adjusted deterministic reference live as the shield fallback "
        "(**Channel B**).")
    p.append("")
    p.append(
        "WHY THE REAL SLM IS REQUIRED: coordination enters chiefly via Channel A, the "
        "neighbour-note in the SLM prompt. The deterministic StubAgent ignores that "
        "note (proven in `results/coord_throughput.md`), so the Channel-A effect can "
        "ONLY be measured with the real model -- which is exactly this run.")
    p.append("")
    p.append("Every run is scored with the throughput-controlled metrics in "
             "`src/metrics.py`, parsed from a tripinfo emitted WITH "
             "`--tripinfo-output.write-unfinished --tripinfo-output.write-undeparted` "
             "(unique path per run under `results/tripinfo_slm/`), so the whole "
             "vehicle population (completed + stranded-at-horizon + never-departed) "
             "is counted and the Milestone-2 survivorship bias cannot recur.")
    p.append("")
    p.append(f"- Seeds: n={n_seeds} ({seeds})")
    p.append(f"- Horizon: end={end} steps (per run, capped)")
    p.append(f"- SLM model: `{model}` (real, serialised ~0.5s/call)")
    p.append(f"- Coordinated mode: coord_weight={COORD_WEIGHT:g} "
             "(Channel A note + Channel B adjusted reference both live)")
    p.append("")

    p.append("## Headline verdict")
    p.append("")
    p.append(f"**With the REAL SLM and throughput-controlled metrics, Channel-A/B "
             f"coordination shows: {headline}** (coordinated vs uncoordinated, paired "
             f"on seed).")
    p.append("")
    for nt in notes:
        p.append(f"- {nt}")
    p.append("")
    if underpowered:
        p.append(f"> **POWER CAVEAT (honest):** n={n_seeds} seeds is small. With so "
                 f"few paired observations the permutation test has very low power "
                 f"and the BCa CIs are wide, so a 'NO SIGNIFICANT EFFECT' result is "
                 f"**likely underpowered** -- it means *not detected at n={n_seeds}*, "
                 f"NOT *proven absent*. A larger seed count would be needed to "
                 f"resolve a small true effect.")
        p.append("")

    p.append("## Coordination pathway provenance (proves the channels were live)")
    p.append("")
    p.append("These confirm coordination was actually exercised in the coordinated "
             "arm; without them a null result could merely mean 'coordination never "
             "fired'.")
    p.append("")
    p.append(f"- Channel-A neighbour-notes injected into SLM prompts: **{tot_notes}** "
             f"(across {len(coord_rows)} coordinated runs)")
    p.append(f"- Verified neighbour messages received: **{tot_verified}**")
    p.append(f"- `coord_adjusted_decisions` (Channel-B adjusted choice differed from "
             f"plain MaxPressure): **{tot_coord_adj}**")
    p.append(f"- `coord_changed_events` (per-event cross-check of the above): "
             f"**{tot_coord_changed}**")
    p.append("")

    p.append("## Per-mode honest metrics (mean over seeds)")
    p.append("")
    p.append("`slm_decisions` = event-gated SLM consultations; "
             "`slm_differed_from_shield` = times the SLM's phase differed from the "
             "MaxPressure shield's (proves the real model was in the loop and active).")
    p.append("")
    p.append(_mode_table(rows))
    p.append("")

    p.append("## Inferential comparison: coordinated vs uncoordinated "
             "(BCa 95% CI + paired permutation)")
    p.append("")
    p.append("Paired on seed. The family is a single comparison per metric, so Holm "
             "reduces to the raw permutation p.")
    p.append("")
    for metric in HEADLINE_METRICS:
        lower = metric == "mean_network_delay"
        df = _compare(rows, metric)
        p.append(_stats_table(df, metric, lower))
        p.append("")

    p.append("## Matched-set (same-vehicle) travel-time comparison")
    p.append("")
    p.append("`matched_diff` averages travel time over ONLY the vehicles that "
             "completed in BOTH arms (apples-to-apples; the survivorship-bias "
             "antidote for travel time). diff = coordinated - uncoordinated; negative "
             "=> coordination is faster on shared trips. BCa CI + paired-vs-zero "
             "permutation p over seeds.")
    p.append("")
    md_hdr = ("| comparison | seeds | mean diff (coord - uncoord) | 95% BCa CI | "
              "excl 0 | perm p | total matched veh | only coord | only uncoord |")
    md_sep = "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    md_lines = [md_hdr, md_sep,
                (f"| coordinated vs uncoordinated | {md['n_seeds']} | "
                 f"{_fmt(md['mean_diff'], 2)} | "
                 f"[{_fmt(md['ci'][0], 2)}, {_fmt(md['ci'][1], 2)}] | "
                 f"{'YES' if md['excludes_zero'] else 'no'} | "
                 f"{_fmt(md['perm_p'], 4)} | {md['total_n_matched']} | "
                 f"{md['only_coord']} | {md['only_uncoord']} |")]
    p.append("\n".join(md_lines))
    p.append("")
    if md.get("per_seed"):
        p.append("Per-seed matched diffs: " + ", ".join(
            f"seed {d['seed']}: {d['diff']:+.2f}s (n={d['n_matched']})"
            for d in md["per_seed"]))
        p.append("")

    p.append("## Method notes")
    p.append("")
    p.append("- BOTH arms use the SAME real SLMAgent; the only manipulated variable "
             "is whether coordination info reaches the model. A difference is "
             "therefore attributable to coordination (chiefly Channel A).")
    p.append("- `throughput` is a count and cannot be gamed by stranding slow "
             "vehicles. `mean_network_delay` divides total time-in-network by ALL "
             "departed vehicles (stranded ones keep their accrued time), so a "
             "'completes fewer but faster' controller earns no spurious win.")
    p.append("- The biased `avg_tt_completed` column is shown only for contrast; it "
             "is NOT the headline.")
    p.append("- Comparisons are paired on seed; permutation p uses the +1 "
             "small-sample correction (so p is never exactly 0).")
    p.append(f"- n={n_seeds} seeds. Significance is reported honestly: at this seed "
             f"count the test is {'likely UNDERPOWERED' if underpowered else 'better powered'}.")
    return "\n".join(p)


def write_report(rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(RESULTS_JSON), exist_ok=True)
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    _log(f"[wrote] {RESULTS_JSON}")
    report = build_report(rows)
    with open(RESULTS_MD, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    _log(f"[wrote] {RESULTS_MD}")


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Real-SLM honest coordination sweep.")
    ap.add_argument("--seeds", nargs="*", type=int, default=list(DEFAULT_SEEDS))
    ap.add_argument("--end", type=int, default=DEFAULT_END)
    ap.add_argument("--smoke", action="store_true",
                    help="quick sanity sweep: 1 seed, end=120")
    args = ap.parse_args()

    seeds, end = args.seeds, args.end
    if args.smoke:
        seeds, end = [0], 120

    # Fresh progress file each invocation so polling sees only this run.
    try:
        os.makedirs(os.path.dirname(PROGRESS), exist_ok=True)
        with open(PROGRESS, "w", encoding="utf-8") as f:
            f.write("")
    except Exception:
        pass

    _log(f"=== REAL-SLM metrics sweep START: seeds={seeds} end={end} "
         f"modes={MODES} coord_weight={COORD_WEIGHT} ===")
    t0 = time.time()
    rows = run_sweep(seeds, end=end)
    write_report(rows)
    _log(f"=== SWEEP COMPLETE in {time.time() - t0:.0f}s "
         f"({len(rows)} runs, {len(seeds)} seeds) -> {os.path.basename(RESULTS_MD)} ===")


if __name__ == "__main__":
    main()
