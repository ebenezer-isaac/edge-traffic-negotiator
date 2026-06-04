"""Milestone-2 results collector: run all four modes across seeds, dump full
metrics (incl. the coordination/security fields), and compute BCa CIs + paired
permutation tests via stats.py. Writes JSON + a markdown report under results/.

Deterministic modes (fixed, maxpressure) are cheap; the SLM modes
(uncoordinated, coordinated) call Foundry Local and dominate wall-clock, so they
run on a smaller seed set. Run from the project root:

    .venv/Scripts/python src/collect_results.py
"""
from __future__ import annotations

import json
import os

import run_coordinated as rc
import stats
from run_baseline import HERE

# Common seeds so coordinated-vs-uncoordinated and SLM-vs-baseline pair cleanly.
SLM_SEEDS = [42, 7, 13]
DET_SEEDS = [42, 7, 13]
END = 500

RESULTS_DIR = os.path.join(HERE, "..", "results")


def _coord_summary(m: dict) -> str:
    if m.get("mode") != "coordinated":
        return ""
    return (f"  [coord] verified_msgs={m.get('verified_messages')} "
            f"rejected={m.get('rejected_messages')} "
            f"detections={m.get('detections')} flagged={m.get('flagged_detections')}")


def main() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    rows: list[dict] = []

    plan = [("fixed", DET_SEEDS), ("maxpressure", DET_SEEDS),
            ("uncoordinated", SLM_SEEDS), ("coordinated", SLM_SEEDS)]

    for mode, seeds in plan:
        for seed in seeds:
            m = rc.run(mode, seed=seed, end=END)
            rows.append(m)
            line = (f"[done] mode={mode:13s} seed={seed:<3d} "
                    f"completed={m.get('completed')} "
                    f"att={m.get('avg_travel_time_s')} "
                    f"wait={m.get('avg_waiting_time_s')}")
            print(line)
            cs = _coord_summary(m)
            if cs:
                print(cs)

    with open(os.path.join(RESULTS_DIR, "milestone2_raw.json"), "w") as f:
        json.dump(rows, f, indent=2, default=str)

    # Stats: per-mode mean + BCa CI, paired diff vs maxpressure (shared seeds),
    # permutation p, Holm-corrected. Travel time and waiting time.
    report = ["# Milestone-2 results (2x2 grid)\n",
              f"END={END} sim-steps. SLM seeds={SLM_SEEDS}, det seeds={DET_SEEDS}.",
              f"SLM model: {next((r.get('slm_model') for r in rows if r.get('slm_model')), 'n/a')}\n"]

    for metric in ("avg_travel_time_s", "avg_waiting_time_s"):
        report.append(f"\n## {metric} (baseline = maxpressure)\n")
        try:
            df = stats.summarize_sweep(rows, metric=metric, group_key="mode",
                                       seed_key="seed", baseline="maxpressure")
            report.append(df.to_markdown(index=False))
        except Exception as exc:  # never lose the raw rows to a stats error
            report.append(f"_stats failed: {type(exc).__name__}: {exc}_")

    # Throughput (completed trips) per mode — guards against reading the
    # completed-trips-only travel-time means as a clean win (survivorship bias).
    report.append("\n## Throughput (completed trips, mean over seeds)\n")
    for mode in ("fixed", "maxpressure", "uncoordinated", "coordinated"):
        comp = [r["completed"] for r in rows if r.get("mode") == mode and "completed" in r]
        if comp:
            report.append(f"- {mode}: {sum(comp) / len(comp):.1f}")
    report.append(
        "\n> Caveat: avg_travel_time_s / avg_waiting_time_s are averaged over "
        "*completed* trips only. If a mode completes fewer trips, lower travel-time "
        "means may reflect survivorship bias (slow trips unfinished, hence excluded), "
        "not a genuine speed-up. Compare throughput before claiming a delay improvement.")

    # Coordination-mechanism proof (live run evidence).
    coord = [r for r in rows if r.get("mode") == "coordinated"]
    if coord:
        vm = sum(int(r.get("verified_messages", 0)) for r in coord)
        rj = sum(int(r.get("rejected_messages", 0)) for r in coord)
        det = sum(int(r.get("detections", 0)) for r in coord)
        report.append("\n## Coordination mechanism (live, summed over coordinated seeds)\n")
        report.append(f"- verified signed neighbour messages consumed: **{vm}**")
        report.append(f"- rejected messages (bad sig / revoked / replay / non-neighbour): **{rj}**")
        report.append(f"- conservation reconciliations performed: **{det}**")

    out = "\n".join(report) + "\n"
    with open(os.path.join(RESULTS_DIR, "milestone2_report.md"), "w") as f:
        f.write(out)
    print("\n" + out)


if __name__ == "__main__":
    main()
