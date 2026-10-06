"""Multi-seed robustness for the H1 headline (Akin: no more n=1).

Runs the MaxPressure baseline AND a chosen SLM config across MANY seeds on Euston, and
reports, per seed, delay + throughput + the joint verdict, plus the AGGREGATE: mean and
spread (std/min/max) of each metric, and the WIN-RATE -- the fraction of seeds where the
SLM beats MaxPressure on delay, on throughput, and jointly (clean_win). This upgrades
the pilot from a single seed to a robustness picture: a win that holds across seeds is
far stronger than one lucky draw.

Still §8-gated for INFERENTIAL significance (demand is DfT daily-resolution), so this is
DESCRIPTIVE multi-seed robustness, not a powered n>=30 significance test -- reported as
such. Reuses experiment_traffic.run_arm verbatim (same battery-verified controller).
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from experiment_traffic import (  # noqa: E402
    NullAgent, TimingAgent, run_arm, summarize_latency, verdict,
)

RESULTS = os.path.normpath(os.path.join(_HERE, "..", "results"))
_MODEL_IDS = {
    "qwen2.5-0.5b": "qwen2.5-0.5b-instruct-generic-gpu:4",
    "qwen2.5-1.5b": "qwen2.5-1.5b-instruct-generic-gpu:4",
    "qwen3-0.6b": "qwen3-0.6b-generic-gpu:2",
    "qwen3-1.7b": "qwen3-1.7b-generic-gpu:2",
    "qwen3.5-0.8b": "qwen3.5-0.8b-generic-gpu:2",
    "qwen3.5-2b": "qwen3.5-2b-generic-gpu:2",
    "qwen3.5-4b": "qwen3.5-4b-generic-gpu:2",
    "phi-4-mini": "Phi-4-mini-instruct-generic-gpu:5",
}


def _agg(values: list) -> dict:
    xs = [v for v in values if isinstance(v, (int, float))]
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "mean": statistics.mean(xs),
            "std": statistics.pstdev(xs) if len(xs) > 1 else 0.0,
            "min": min(xs), "max": max(xs)}


def _probe(model_alias: str):
    from slm_agent import SLMAgent, discover_endpoint
    mid = _MODEL_IDS.get(model_alias, model_alias)
    base, _ = discover_endpoint()
    a = SLMAgent(base_url=base, model=mid)
    try:
        a.client.models.list()
        seen = {a.choose_phase("PROBE", 2, [8, 0]) for _ in range(3)}
        if None in seen:
            return None, f"{mid} did not answer a well-formed decision"
        if len(seen) != 1:
            return None, f"{mid} non-deterministic at temp 0: {sorted(seen)}"
    except Exception as exc:  # noqa: BLE001
        return None, f"Foundry not reachable for {mid} ({type(exc).__name__})"
    return a, None


def run(model: str = "qwen2.5-0.5b", config: str = "myopic",
        seeds=(42, 1, 2, 3, 7), end: int = 1200, gate: int = 2) -> dict:
    agent, reason = _probe(model)
    slm_gated = agent is None
    per_seed = []
    delays_b, delays_s, comp_b, comp_s = [], [], [], []
    joint_counts = {"clean_win": 0, "trade_off": 0, "match": 0, "regression": 0}
    delay_wins = thru_wins = 0
    for seed in seeds:
        base = run_arm(f"mp_s{seed}", NullAgent(), seed=seed, end=end, gate=gate,
                       config="myopic")
        row = {"seed": seed,
               "baseline_delay_s": base["metrics"]["mean_network_delay_s"],
               "baseline_completed": base["metrics"]["completed"]}
        delays_b.append(row["baseline_delay_s"])
        comp_b.append(row["baseline_completed"])
        if slm_gated:
            row["slm"] = {"skipped": True, "reason": reason}
        else:
            timing = TimingAgent(agent, forward_note=(config != "myopic"))
            slm = run_arm(f"slm_{model}_s{seed}", timing, seed=seed, end=end, gate=gate,
                          config=config)
            v = verdict(base, slm)
            row["slm_delay_s"] = slm["metrics"]["mean_network_delay_s"]
            row["slm_completed"] = slm["metrics"]["completed"]
            row["delay_status"] = v["status"]
            row["throughput_status"] = v["throughput_status"]
            row["joint_verdict"] = v["joint_verdict"]
            row["slm_authored"] = slm["decision_stats"]["slm_proposal_served"]
            row["slm_calls"] = timing.calls
            row["latency_p99"] = summarize_latency(timing.latencies_s, warmup=1).get("p99")
            delays_s.append(row["slm_delay_s"])
            comp_s.append(row["slm_completed"])
            joint_counts[row["joint_verdict"]] = joint_counts.get(row["joint_verdict"], 0) + 1
            delay_wins += int(v["status"] == "slm_beats")
            thru_wins += int(v["throughput_status"] == "slm_beats")
        per_seed.append(row)

    n = len([r for r in per_seed if not r.get("slm", {}).get("skipped")])
    result = {
        "experiment": "H1_multiseed_robustness",
        "model": model, "config": config, "seeds": list(seeds), "end": end,
        "slm_gated": slm_gated,
        "per_seed": per_seed,
        "aggregate": {
            "baseline_delay_s": _agg(delays_b), "slm_delay_s": _agg(delays_s),
            "baseline_completed": _agg(comp_b), "slm_completed": _agg(comp_s),
        },
        "win_rate": {
            "n_seeds": n,
            "delay_beats": f"{delay_wins}/{n}" if n else "0/0",
            "throughput_beats": f"{thru_wins}/{n}" if n else "0/0",
            "joint": joint_counts,
        },
        "robustness_verdict": _robust(delays_b, delays_s, comp_b, comp_s, joint_counts, n),
        "note": ("DESCRIPTIVE multi-seed robustness (Akin), NOT a powered n>=30 "
                 "significance test -- demand is DfT daily-resolution so inferential "
                 "significance stays §8-gated until time-resolved TfL counts. A win that "
                 "holds across seeds is far stronger than a single draw."),
    }
    os.makedirs(RESULTS, exist_ok=True)
    jp = os.path.join(RESULTS, "experiment_multiseed.json")
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    mp = os.path.join(RESULTS, "experiment_multiseed.md")
    with open(mp, "w", encoding="utf-8") as fh:
        fh.write(render_md(result))
    _print(result, jp, mp)
    return result


def _robust(db, ds, cb, cs, joint, n) -> str:
    if not ds or not n:
        return "SLM arm gated (Foundry unavailable); baseline seeds recorded only."
    dmean_b, dmean_s = statistics.mean(db), statistics.mean(ds)
    cmean_b, cmean_s = statistics.mean(cb), statistics.mean(cs)
    cw = joint.get("clean_win", 0)
    return (f"Across {n} seeds: mean delay {dmean_s:.1f}s vs {dmean_b:.1f}s baseline "
            f"({(dmean_s-dmean_b)/dmean_b*100:+.1f}%); mean throughput {cmean_s:.0f} vs "
            f"{cmean_b:.0f} completed ({(cmean_s-cmean_b)/cmean_b*100:+.1f}%); "
            f"{cw}/{n} seeds a clean win on both. "
            + ("Robust across seeds." if cw == n else
               "Mixed across seeds (see per-seed)." if cw else "Does not hold across seeds."))


def _fmt(v, nd=1):
    return f"{v:.{nd}f}" if isinstance(v, float) else ("n/a" if v is None else str(v))


def render_md(r: dict) -> str:
    a = r["aggregate"]
    w = r["win_rate"]
    lines = [f"# H1 multi-seed robustness: {r['model']} x {r['config']}", ""]
    lines.append(f"**{r['robustness_verdict']}**")
    lines.append("")
    lines.append(f"- Seeds: {r['seeds']}  |  horizon {r['end']}s")
    lines.append(f"- Delay wins: {w['delay_beats']}  |  throughput wins: "
                 f"{w['throughput_beats']}  |  joint: {w['joint']}")
    lines.append("")
    lines.append("## Per seed")
    lines.append("")
    lines.append("| Seed | Baseline delay | SLM delay | Baseline compl | SLM compl | Joint |")
    lines.append("|---|---|---|---|---|---|")
    for row in r["per_seed"]:
        if row.get("slm", {}).get("skipped"):
            lines.append(f"| {row['seed']} | {_fmt(row['baseline_delay_s'])} | SKIP | "
                         f"{row['baseline_completed']} | SKIP | -- |")
            continue
        lines.append(f"| {row['seed']} | {_fmt(row['baseline_delay_s'])} | "
                     f"{_fmt(row['slm_delay_s'])} | {row['baseline_completed']} | "
                     f"{row['slm_completed']} | {row.get('joint_verdict','')} |")
    lines.append("")
    lines.append("## Aggregate (mean +/- std)")
    lines.append("")
    for k in ("baseline_delay_s", "slm_delay_s", "baseline_completed", "slm_completed"):
        g = a[k]
        if g.get("n"):
            lines.append(f"- {k}: {_fmt(g['mean'])} +/- {_fmt(g['std'])} "
                         f"(min {_fmt(g['min'])}, max {_fmt(g['max'])}, n={g['n']})")
    lines.append("")
    lines.append(f"> {r['note']}")
    lines.append("")
    return "\n".join(lines)


def _print(r, jp, mp):
    print("=" * 66)
    print(f"MULTI-SEED ROBUSTNESS: {r['model']} x {r['config']}")
    print("  " + r["robustness_verdict"])
    print(f"  delay wins {r['win_rate']['delay_beats']}, throughput wins "
          f"{r['win_rate']['throughput_beats']}, joint {r['win_rate']['joint']}")
    print("=" * 66)
    print(f"  wrote: {jp}\n  wrote: {mp}")


def _parser():
    ap = argparse.ArgumentParser(description="Multi-seed robustness for the H1 headline.")
    ap.add_argument("--model", default="qwen2.5-0.5b")
    ap.add_argument("--config", default="myopic")
    ap.add_argument("--seeds", nargs="*", type=int, default=[42, 1, 2, 3, 7])
    ap.add_argument("--end", type=int, default=1200)
    return ap


if __name__ == "__main__":
    ns = _parser().parse_args()
    run(model=ns.model, config=ns.config, seeds=tuple(ns.seeds), end=ns.end)
