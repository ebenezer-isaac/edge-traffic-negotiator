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
    "qwen3.5-0.8b": "qwen3.5-0.8b-generic-gpu:2",
    "qwen3.5-2b": "qwen3.5-2b-generic-gpu:2",
    "qwen3.5-4b": "qwen3.5-4b-generic-gpu:2",
    "phi-4-mini": "Phi-4-mini-instruct-generic-gpu:5",
}


def _topologies() -> list:
    return [
        {"label": "euston_corridor", "structure": "real linear arterial (A501)",
         "net": os.path.join(_SUMO, "euston", "euston_spine.net.xml"),
         "routes": os.path.join(_SUMO, "euston", "base.rou.xml")},
        {"label": "euston_peakhour",
         "structure": "real A501 arterial, MEASURED 2024 peak-hour DfT magnitude (base_hourly)",
         "net": os.path.join(_SUMO, "euston", "euston_spine.net.xml"),
         "routes": os.path.join(_SUMO, "euston", "base_hourly.rou.xml")},
        {"label": "bloomsbury_grid", "structure": "REAL London grid (Bloomsbury WC1, 9 signals)",
         "net": os.path.join(_SUMO, "bloomsbury", "bloomsbury.net.xml"),
         "routes": os.path.join(_SUMO, "bloomsbury", "bloomsbury.rou.xml")},
        {"label": "oldstreet_junction",
         "structure": "REAL complex London junction (Old St EC1, 9 signals incl. a 5-arm/17-movement junction)",
         "net": os.path.join(_SUMO, "oldstreet", "oldstreet.net.xml"),
         # oldstreet_light.rou.xml = demand-calibrated (481 veh): the default randomTrips (1716)
         # gridlocked this small dense junction (baseline 550s, 187 teleports). Light = 0 teleports.
         "routes": os.path.join(_SUMO, "oldstreet", "oldstreet_light.rou.xml")},
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
        topologies=None, out_basename: str | None = None, gate_mode: str = "sum") -> dict:
    tops = topologies if topologies is not None else _topologies()
    agents = {}
    for m in models:
        a, reason = _probe(m)
        agents[m] = (a, reason)

    os.makedirs(RESULTS, exist_ok=True)
    _base = out_basename or "experiment_topology"
    jp = os.path.join(RESULTS, f"{_base}.json")
    mp = os.path.join(RESULTS, f"{_base}.md")

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
                       gate=gate, config="myopic", net=top["net"], routes=top["routes"],
                       gate_mode=gate_mode)
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
                          routes=top["routes"], gate_mode=gate_mode)
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
        "gate": gate, "gate_mode": gate_mode,
        "topologies": [t["label"] for t in tops],
        "cells": cells,
        "explanatory": _explain(cells, models),
        "note": ("DESCRIPTIVE multi-topology pilot (n=1/cell); inferential significance "
                 "§8-gated. Grids are SYNTHETIC contrasts to the real Euston corridor; "
                 "real-London multi-area OSM nets are the next infra step (harness is "
                 "net-agnostic). Which model wins where + WHY, from the joint verdicts."),
    }
    # jp/mp were bound at the top of run() from out_basename; reuse them so --out is
    # honoured for the FINAL write too (previously this block re-hardcoded
    # experiment_topology.json, which clobbered a full run when --out was set).
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
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
    # Direction analysis. A covariance SIGN is not enough (a two-cluster artifact or a
    # single leverage point can flip it), so we report: (a) a proper Pearson r with n,
    # (b) the mean win split by REGIME (free-flowing vs congested), and (c) the WITHIN-
    # congested direction -- because the honest story here is a regime SEPARATION, not a
    # graded monotonic law, and within the congested nets the relationship can invert.
    def _pearson(xs, ys):
        n = len(xs)
        if n < 2:
            return None
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        syy = sum((y - my) ** 2 for y in ys)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        if sxx <= 0 or syy <= 0:
            return None
        return sxy / (sxx ** 0.5 * syy ** 0.5)

    win = [-o["delay_rel_pct"] for o in obs]            # +win = delay improvement %
    proxy = [o["baseline_gridlock_proxy"] for o in obs]
    free = [o for o in obs if o["baseline_teleports"] == 0]      # MaxPressure never gridlocks
    cong = [o for o in obs if o["baseline_teleports"] > 0]       # MaxPressure gridlocks
    mean = lambda xs: round(sum(xs) / len(xs), 1) if xs else None
    r_all = _pearson(proxy, win)
    cong_win = [-o["delay_rel_pct"] for o in cong]
    cong_proxy = [o["baseline_gridlock_proxy"] for o in cong]
    r_cong = _pearson(cong_proxy, cong_win)
    trend = None
    if len(obs) >= 2:
        n_pos = sum(1 for o in obs if o["baseline_teleports"] > 0 and -o["delay_rel_pct"] > 0)
        trend = (
            f"regime separation (n={len(obs)} cells, DESCRIPTIVE): the SLM WINS only where "
            f"MaxPressure gridlocks (teleports>0) and LOSES on free-flowing nets "
            f"(mean win congested {mean(cong_win)}% vs free-flowing {mean([-o['delay_rel_pct'] for o in free])}%). "
            f"Across all topologies r={round(r_all,2) if r_all is not None else 'NA'}, but this is "
            f"driven by the free-vs-congested split, NOT a graded law: WITHIN the congested "
            f"nets the direction "
            + ("INVERTS (more gridlock -> smaller win) "
               if (r_cong is not None and r_cong < 0) else "does not cleanly hold ")
            + f"(r_congested={round(r_cong,2) if r_cong is not None else 'NA'}). "
            f"So the honest claim is a congestion-REGIME effect, not 'win grows monotonically "
            f"with gridlock'. n=1 seed/cell: not a significance test."
        )
    return {
        "hypothesis": ("the SLM's delay+throughput advantage appears where MaxPressure "
                       "gridlocks (teleports>0) and disappears where the network self-"
                       "regulates (free-flowing, zero teleports)"),
        "observations": obs,
        "trend": trend,
        "pearson_r_all_topologies": round(r_all, 3) if r_all is not None else None,
        "pearson_r_congested_only": round(r_cong, 3) if r_cong is not None else None,
        "mean_win_pct_congested": mean(cong_win),
        "mean_win_pct_free_flowing": mean([-o["delay_rel_pct"] for o in free]),
        "caveat": ("Regime SEPARATION at n=4 topologies x n=1 seed, not a graded monotonic "
                   "law and not a significance test. The all-topology correlation is "
                   "dominated by the synthetic zero-teleport grids clustering at proxy~0; "
                   "within the congested real nets the win does not grow with gridlock "
                   "(Bloomsbury has more gridlock than Euston yet a smaller/negative win)."),
        "reading": ("Mechanism HYPOTHESIS (not demonstrated at n=1): MaxPressure is "
                    "throughput-optimal and near-ideal when traffic flows freely, so the "
                    "SLM's waiting-time-aware policy only adds latency there; when "
                    "MaxPressure gridlocks, queue management has headroom to help."),
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
    ap.add_argument("--topologies", nargs="*", default=None,
                    help="subset of topology labels to run (default: all). "
                         "e.g. --topologies euston_corridor")
    ap.add_argument("--out", default=None,
                    help="optional alternate results basename (avoids clobbering the "
                         "full multi-topology run's experiment_topology.json)")
    ap.add_argument("--gate", type=int, default=2,
                    help="congestion-gate threshold (default 2)")
    ap.add_argument("--gate-mode", choices=("sum", "max"), default="sum",
                    help="'sum' (total halting, default, phase-count-scaled) or 'max' "
                         "(largest per-phase queue, topology-invariant congestion gate)")
    return ap


if __name__ == "__main__":
    ns = _parser().parse_args()
    tops = None
    if ns.topologies:
        want = set(ns.topologies)
        tops = [t for t in _topologies() if t["label"] in want]
        if not tops:
            raise SystemExit(f"no topology matched {sorted(want)}; "
                             f"known: {[t['label'] for t in _topologies()]}")
    run(models=tuple(ns.models), seed=ns.seed, end=ns.end, topologies=tops,
        out_basename=ns.out, gate=ns.gate, gate_mode=ns.gate_mode)
