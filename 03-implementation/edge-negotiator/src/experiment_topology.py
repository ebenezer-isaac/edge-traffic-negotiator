"""Multi-topology H1 study + explanatory analysis (full-scale phase; req 5 + 6).

The pilot beat MaxPressure on ONE straight corridor (Euston A501). This runs the SAME
controller across MULTIPLE topologies -- the real Euston corridor plus synthetic grids
of increasing size/connectivity -- for one or more models, and asks WHICH model wins
under WHICH topology, and WHY the advantage varies.

Topology is the experimental variable MaxPressure's known weakness lives in: its eager,
myopic, memoryless switching causes the most lost time under SATURATION on a CONSTRAINED
topology (few alternate routes), and less where the network self-regulates. So the
explanatory hypothesis is: the SLM's delay+throughput advantage is LARGEST where
MaxPressure gridlocks hardest (high teleports / low completion), and NARROWS toward a
match where the topology absorbs the demand. Each cell reports delay + throughput + the
joint verdict; the analysis correlates the win magnitude with per-topology gridlock.

Reuses run_arm on each net (topology-agnostic controller). SLM is Foundry-probe-gated
per model (SKIP-with-record). Real-London MULTI-AREA nets (extra OSM extractions) are
the next infra step; the harness is net-agnostic so they drop straight in.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from experiment_traffic import (  # noqa: E402
    NullAgent, TimingAgent, run_arm, summarize_latency, verdict,
)

RESULTS = os.path.normpath(os.path.join(_HERE, "..", "results"))
_SUMO = os.path.normpath(os.path.join(_HERE, "..", "sumo"))
_MODEL_IDS = {
    "qwen2.5-0.5b": "qwen2.5-0.5b-instruct-generic-gpu:4",
    "qwen3-0.6b": "qwen3-0.6b-generic-gpu:2",
    "phi-4-mini": "Phi-4-mini-instruct-generic-gpu:5",
}


def _topologies() -> list:
    return [
        {"label": "euston_corridor", "structure": "real linear arterial (A501)",
         "net": os.path.join(_SUMO, "euston", "euston_spine.net.xml"),
         "routes": os.path.join(_SUMO, "euston", "base.rou.xml")},
        {"label": "bloomsbury_grid", "structure": "REAL London grid (Bloomsbury WC1, 9 signals)",
         "net": os.path.join(_SUMO, "bloomsbury", "bloomsbury.net.xml"),
         "routes": os.path.join(_SUMO, "bloomsbury", "bloomsbury.rou.xml")},
        {"label": "grid3x3", "structure": "synthetic 3x3 grid (more routes)",
         "net": os.path.join(_SUMO, "grid3x3", "grid3x3.net.xml"),
         "routes": os.path.join(_SUMO, "grid3x3", "grid3x3.rou.xml")},
        {"label": "grid4x4", "structure": "synthetic 4x4 grid (most routes)",
         "net": os.path.join(_SUMO, "grid4x4", "grid4x4.net.xml"),
         "routes": os.path.join(_SUMO, "grid4x4", "grid4x4.rou.xml")},
    ]


def _probe(alias: str):
    from slm_agent import SLMAgent, discover_endpoint
    mid = _MODEL_IDS.get(alias, alias)
    base, _ = discover_endpoint()
    a = SLMAgent(base_url=base, model=mid)
    try:
        a.client.models.list()
        if a.choose_phase("PROBE", 2, [8, 0]) is None:
            return None, f"{mid} did not answer a well-formed decision"
    except Exception as exc:  # noqa: BLE001
        return None, f"Foundry not reachable for {mid} ({type(exc).__name__})"
    return a, None


def _tls_count(net_path: str) -> int:
    try:
        import sumolib
        return len(sumolib.net.readNet(net_path).getTrafficLights())
    except Exception:
        return -1


def run(models=("qwen2.5-0.5b",), seed: int = 42, end: int = 1200, gate: int = 2,
        topologies=None) -> dict:
    tops = topologies if topologies is not None else _topologies()
    agents = {}
    for m in models:
        a, reason = _probe(m)
        agents[m] = (a, reason)

    os.makedirs(RESULTS, exist_ok=True)
    jp = os.path.join(RESULTS, "experiment_topology.json")
    mp = os.path.join(RESULTS, "experiment_topology.md")

    def _flush(cells_so_far):
        # Incremental write after each topology so a long multi-topology run preserves
        # progress if interrupted (grids have many signals -> many slow SLM calls).
        partial = {"experiment": "H1_multi_topology", "models": list(models),
                   "seed": seed, "end": end, "topologies": [t["label"] for t in tops],
                   "cells": cells_so_far, "explanatory": _explain(cells_so_far, models),
                   "note": "partial (in progress)"}
        with open(jp, "w", encoding="utf-8") as fh:
            json.dump(partial, fh, indent=2)

    cells = []
    for top in tops:
        if not (os.path.exists(top["net"]) and os.path.exists(top["routes"])):
            cells.append({"topology": top["label"], "skipped": True,
                          "reason": "net or routes file missing"})
            continue
        n_tls = _tls_count(top["net"])
        base = run_arm(f"top_{top['label']}_mp", NullAgent(), seed=seed, end=end,
                       gate=gate, config="myopic", net=top["net"], routes=top["routes"])
        bm = base["metrics"]
        row = {"topology": top["label"], "structure": top["structure"], "tls": n_tls,
               "baseline": {"delay_s": bm["mean_network_delay_s"],
                            "completed": bm["completed"], "departed": bm["departed"],
                            "teleports": bm["teleports"]},
               "models": {}}
        for m in models:
            agent, reason = agents[m]
            if agent is None:
                row["models"][m] = {"skipped": True, "reason": reason}
                continue
            timing = TimingAgent(agent, forward_note=False)
            slm = run_arm(f"top_{top['label']}_{m}", timing, seed=seed, end=end,
                          gate=gate, config="myopic", net=top["net"],
                          routes=top["routes"])
            v = verdict(base, slm)
            sm = slm["metrics"]
            row["models"][m] = {
                "delay_s": sm["mean_network_delay_s"], "completed": sm["completed"],
                "teleports": sm["teleports"],
                "delay_status": v["status"], "throughput_status": v["throughput_status"],
                "joint_verdict": v["joint_verdict"],
                "delay_rel": v["slm_relative_delay"],
                "slm_authored": slm["decision_stats"]["slm_proposal_served"],
                "slm_calls": timing.calls,
                "latency_p99": summarize_latency(timing.latencies_s, warmup=1).get("p99"),
            }
        cells.append(row)
        _flush(cells)   # persist after each topology (long-run resilience)

    result = {
        "experiment": "H1_multi_topology",
        "models": list(models), "seed": seed, "end": end,
        "topologies": [t["label"] for t in tops],
        "cells": cells,
        "explanatory": _explain(cells, models),
        "note": ("DESCRIPTIVE multi-topology pilot (n=1/cell); inferential significance "
                 "§8-gated. Grids are SYNTHETIC contrasts to the real Euston corridor; "
                 "real-London multi-area OSM nets are the next infra step (harness is "
                 "net-agnostic). Which model wins where + WHY, from the joint verdicts."),
    }
    os.makedirs(RESULTS, exist_ok=True)
    jp = os.path.join(RESULTS, "experiment_topology.json")
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    mp = os.path.join(RESULTS, "experiment_topology.md")
    with open(mp, "w", encoding="utf-8") as fh:
        fh.write(render_md(result))
    _print(result, jp, mp)
    return result


def _explain(cells, models) -> dict:
    """Correlate the SLM's win magnitude with each topology's MaxPressure gridlock
    (teleports + un-completed demand): the hypothesis is the win is largest where
    MaxPressure gridlocks hardest, narrowing where the network self-regulates."""
    obs = []
    for c in cells:
        if c.get("skipped"):
            continue
        b = c["baseline"]
        # baseline gridlock proxy: teleports + fraction of departed that did NOT complete.
        stranded = (b["departed"] - b["completed"]) / b["departed"] if b["departed"] else 0.0
        gridlock = b["teleports"] + 100.0 * stranded
        for m in models:
            mc = c["models"].get(m, {})
            if mc.get("skipped"):
                continue
            obs.append({"topology": c["topology"], "model": m, "tls": c["tls"],
                        "baseline_gridlock_proxy": round(gridlock, 1),
                        "baseline_teleports": b["teleports"],
                        "baseline_stranded_frac": round(stranded, 3),
                        "delay_rel_pct": round((mc["delay_rel"] or 0) * 100, 1),
                        "joint": mc["joint_verdict"]})
    # direction: does a larger baseline gridlock proxy go with a larger delay win?
    pairs = [(o["baseline_gridlock_proxy"], -o["delay_rel_pct"]) for o in obs]  # -rel = win size
    trend = None
    if len(pairs) >= 2:
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        cov = sum((x - mx) * (y - my) for x, y in pairs)
        trend = ("win grows with baseline gridlock (hypothesis supported)" if cov > 0
                 else "win does NOT grow with baseline gridlock (hypothesis not supported)"
                 if cov < 0 else "flat")
    return {
        "hypothesis": ("the SLM's delay+throughput advantage is largest where MaxPressure "
                       "gridlocks hardest (constrained/saturated topology) and narrows "
                       "where the network self-regulates"),
        "observations": obs,
        "trend": trend,
        "reading": ("Compare each row's baseline gridlock proxy (teleports + stranded%) "
                    "to the delay-win size. The mechanism: MaxPressure's eager myopic "
                    "switching wastes the most time exactly where gridlock compounds, so "
                    "the steadier SLM controller gains most there."),
    }


def _fmt(v, nd=1):
    return f"{v:.{nd}f}" if isinstance(v, float) else ("n/a" if v is None else str(v))


def render_md(r: dict) -> str:
    lines = ["# H1 multi-topology: which model wins where, and why", ""]
    lines.append(f"Models: {r['models']}  |  seed {r['seed']}  |  horizon {r['end']}s  |  "
                 f"topologies: {r['topologies']}")
    lines.append("")
    for c in r["cells"]:
        if c.get("skipped"):
            lines.append(f"## {c['topology']} -- SKIPPED ({c['reason']})")
            continue
        b = c["baseline"]
        lines.append(f"## {c['topology']} ({c['structure']}, {c['tls']} signals)")
        lines.append(f"- MaxPressure baseline: delay {_fmt(b['delay_s'])}s, completed "
                     f"{b['completed']}/{b['departed']}, teleports {b['teleports']}")
        lines.append("")
        lines.append("| Model | Delay (s) | Delay | Completed | Throughput | Joint | P99 |")
        lines.append("|---|---|---|---|---|---|---|")
        for m, mc in c["models"].items():
            if mc.get("skipped"):
                lines.append(f"| {m} | SKIP | -- | -- | -- | -- | -- |")
                continue
            lines.append(f"| {m} | {_fmt(mc['delay_s'])} | "
                         f"{mc['delay_status'].replace('slm_','')} "
                         f"{_fmt((mc['delay_rel'] or 0)*100)}% | {mc['completed']} | "
                         f"{mc['throughput_status'].replace('slm_','')} | "
                         f"**{mc['joint_verdict']}** | {_fmt(mc['latency_p99'],2)} |")
        lines.append("")
    ex = r["explanatory"]
    lines.append("## Explanatory analysis (WHY the advantage varies)")
    lines.append("")
    lines.append(f"- Hypothesis: {ex['hypothesis']}")
    lines.append(f"- Trend across cells: **{ex['trend']}**")
    lines.append("")
    lines.append("| Topology | Model | Baseline gridlock proxy | Delay win % | Joint |")
    lines.append("|---|---|---|---|---|")
    for o in ex["observations"]:
        lines.append(f"| {o['topology']} | {o['model']} | {o['baseline_gridlock_proxy']} "
                     f"(tp {o['baseline_teleports']}, stranded {o['baseline_stranded_frac']}) "
                     f"| {-o['delay_rel_pct']:+.1f} | {o['joint']} |")
    lines.append("")
    lines.append(f"- {ex['reading']}")
    lines.append("")
    lines.append(f"> {r['note']}")
    lines.append("")
    return "\n".join(lines)


def _print(r, jp, mp):
    print("=" * 68)
    print(f"MULTI-TOPOLOGY: models {r['models']} across {r['topologies']}")
    for c in r["cells"]:
        if c.get("skipped"):
            print(f"  {c['topology']}: SKIP ({c['reason']})"); continue
        for m, mc in c["models"].items():
            if mc.get("skipped"):
                print(f"  {c['topology']:<16} {m:<14} SKIP"); continue
            print(f"  {c['topology']:<16} {m:<14} {mc['joint_verdict']:<11} "
                  f"delay={_fmt(mc['delay_s'])}s ({_fmt((mc['delay_rel'] or 0)*100)}%)")
    print(f"  trend: {r['explanatory']['trend']}")
    print("=" * 68)
    print(f"  wrote: {jp}\n  wrote: {mp}")


def _parser():
    ap = argparse.ArgumentParser(description="Multi-topology H1 study + explanatory analysis.")
    ap.add_argument("--models", nargs="*", default=["qwen2.5-0.5b"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--end", type=int, default=1200)
    return ap


if __name__ == "__main__":
    ns = _parser().parse_args()
    run(models=tuple(ns.models), seed=ns.seed, end=ns.end)
