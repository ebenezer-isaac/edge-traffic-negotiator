"""Delay AND throughput joint analysis of the committed H1 sweep (Akin's point).

MaxPressure is throughput-OPTIMAL by design, so beating it on delay is only a clean
result if it does NOT quietly sacrifice throughput. This re-analyses the ALREADY
COMMITTED sweep (results/experiment_sweep.json -- which records completed vehicles and
delay per cell) and reports, per model x config, the joint verdict:
  * clean_win  -- beats on at least one of {delay, throughput} and loses on neither;
  * trade_off  -- wins one, sacrifices the other;
  * match / regression otherwise.
Throughput = completed vehicles (arrival>=0) over the horizon; higher is better. Same
net + demand + seed, so absolute completed counts are directly comparable. Completion
rate (completed/departed) is reported alongside for transparency. No re-run, no new
numbers -- this is a lens on existing measured data.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from experiment_traffic import _bml, _joint_verdict  # noqa: E402

RESULTS = os.path.normpath(os.path.join(_HERE, "..", "results"))


def analyse(sweep: dict) -> dict:
    b = sweep["baseline"]["metrics"]
    b_delay, b_comp, b_dep = (b.get("mean_network_delay_s"), b.get("completed"),
                              b.get("departed"))
    rows = []
    for model, cfgs in sweep.get("cells", {}).items():
        for config, cell in cfgs.items():
            if cell.get("skipped"):
                rows.append({"model": model, "config": config, "status": "skipped",
                             "reason": cell.get("reason", "")[:60]})
                continue
            m = cell["metrics"]
            d, c, dep = m.get("mean_network_delay_s"), m.get("completed"), m.get("departed")
            d_stat, d_rel = _bml(d, b_delay, lower_is_better=True)
            t_stat, t_rel = _bml(c, b_comp, lower_is_better=False)
            rows.append({
                "model": model, "config": config,
                "delay_s": d, "delay_status": d_stat, "delay_rel": d_rel,
                "completed": c, "throughput_status": t_stat, "throughput_rel": t_rel,
                "completed_delta": (c - b_comp) if (c is not None and b_comp) else None,
                "departed": dep,
                "completion_rate": (c / dep) if (c is not None and dep) else None,
                "joint_verdict": _joint_verdict(d_stat, t_stat),
                "slm_authored": cell.get("slm_proposal_served"),
                "slm_calls": cell.get("slm_calls"),
            })
    # Flag inert-coordination duplicates: on this substrate +coordination changes zero
    # decisions, so a coordination cell that is byte-identical (delay AND completed) to
    # its myopic sibling is the SAME run, not a second independent win. Counting it
    # again would inflate the clean-win tally, so we dedupe for the DISTINCT count.
    myopic_by_model = {r["model"]: r for r in rows
                       if r.get("config") == "myopic" and "delay_s" in r}
    for r in rows:
        sib = myopic_by_model.get(r.get("model"))
        r["duplicate_of_myopic"] = bool(
            r.get("config") == "coordination" and sib is not None
            and r.get("delay_s") == sib.get("delay_s")
            and r.get("completed") == sib.get("completed"))
    clean = [r for r in rows if r.get("joint_verdict") == "clean_win"]
    trades = [r for r in rows if r.get("joint_verdict") == "trade_off"]
    distinct_clean = [r for r in clean if not r.get("duplicate_of_myopic")]
    return {
        "experiment": "H1_delay_and_throughput_joint",
        "question": ("does the SLM's delay win sacrifice throughput? (MaxPressure is "
                     "throughput-optimal by design, Akin)"),
        "baseline": {"delay_s": b_delay, "completed": b_comp, "departed": b_dep,
                     "completion_rate": (b_comp / b_dep) if b_dep else None},
        "rows": rows,
        "n_clean_win_cells": len(clean),
        "n_clean_win_distinct_configs": len(distinct_clean),
        "n_inert_coordination_duplicates": len(clean) - len(distinct_clean),
        "n_trade_off": len(trades),
        "headline": _headline(rows, b_comp),
        "note": ("Descriptive PILOT lens on committed data (n=1/cell); no significance "
                 "claim. Completion counts comparable (same net+demand+seed)."),
    }


def _headline(rows, b_comp) -> str:
    ran = [r for r in rows if "joint_verdict" in r]
    cw = [r for r in ran if r["joint_verdict"] == "clean_win"]
    if cw:
        best = min(cw, key=lambda r: r["delay_s"])
        return (f"{best['model']} x {best['config']} is a CLEAN WIN: delay "
                f"{best['delay_s']:.1f}s ({best['delay_rel']*100:+.1f}%) AND throughput "
                f"{best['completed']} completed ({best['completed_delta']:+d} vs baseline "
                f"{b_comp}, {best['throughput_rel']*100:+.1f}%). The delay win does NOT "
                "cost throughput -- it improves both.")
    trades = [r for r in ran if r["joint_verdict"] == "trade_off"]
    if trades:
        return ("No clean win: the delay gains come with a throughput trade-off (see "
                "rows). Honest trade, still publishable.")
    return "No delay win at this horizon; see rows."


def run() -> dict:
    sweep_path = os.path.join(RESULTS, "experiment_sweep.json")
    with open(sweep_path, encoding="utf-8") as fh:
        sweep = json.load(fh)
    result = analyse(sweep)
    os.makedirs(RESULTS, exist_ok=True)
    jp = os.path.join(RESULTS, "experiment_throughput.json")
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    mp = os.path.join(RESULTS, "experiment_throughput.md")
    with open(mp, "w", encoding="utf-8") as fh:
        fh.write(render_md(result))
    _print(result, jp, mp)
    return result


def _fmt(v, nd=1):
    return f"{v:.{nd}f}" if isinstance(v, float) else ("n/a" if v is None else str(v))


def render_md(r: dict) -> str:
    b = r["baseline"]
    lines = ["# H1: delay AND throughput (does the delay win cost throughput?)", ""]
    lines.append(f"**{r['headline']}**")
    lines.append("")
    lines.append(f"- Question: {r['question']}")
    lines.append(f"- Baseline MaxPressure: delay {_fmt(b['delay_s'])} s, completed "
                 f"{b['completed']} (throughput), departed {b['departed']}, completion "
                 f"rate {_fmt(b['completion_rate'],3)}")
    lines.append("")
    lines.append("| Model x config | Delay (s) | Delay | Completed | Throughput | Joint |")
    lines.append("|---|---|---|---|---|---|")
    for row in r["rows"]:
        if row.get("status") == "skipped":
            lines.append(f"| {row['model']} x {row['config']} | -- | SKIP | -- | -- | -- |")
            continue
        dr = f"{row['delay_rel']*100:+.1f}%"
        tr = f"{row['throughput_rel']*100:+.1f}%"
        jv = row["joint_verdict"].replace("_", " ")
        lines.append(f"| {row['model']} x {row['config']} | {_fmt(row['delay_s'])} | "
                     f"{row['delay_status'].replace('slm_','')} {dr} | "
                     f"{row['completed']} ({row['completed_delta']:+d}) | "
                     f"{row['throughput_status'].replace('slm_','')} {tr} | **{jv}** |")
    lines.append("")
    lines.append(f"- Clean wins: **{r['n_clean_win_distinct_configs']} distinct configs** "
                 f"({r['n_clean_win_cells']} cells incl. "
                 f"{r['n_inert_coordination_duplicates']} inert-coordination duplicates "
                 f"of myopic)   |   trade-offs: {r['n_trade_off']}")
    lines.append(f"- {r['note']}")
    lines.append("")
    return "\n".join(lines)


def _print(r, jp, mp):
    print("=" * 68)
    print("DELAY + THROUGHPUT JOINT ANALYSIS")
    print("  " + r["headline"])
    print(f"  clean wins: {r['n_clean_win_distinct_configs']} distinct configs "
          f"({r['n_clean_win_cells']} cells, {r['n_inert_coordination_duplicates']} "
          f"inert-coord duplicates)  trade-offs: {r['n_trade_off']}")
    print("=" * 68)
    print(f"  wrote: {jp}\n  wrote: {mp}")


if __name__ == "__main__":
    run()
