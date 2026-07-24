"""H2 trust axis IN the traffic sim: does the trust mechanism protect the corridor when a
neighbour LIES about how much traffic it is sending?

For each map we designate the busiest-adjacency junction as a potential liar and run the
coordination arm under three honesty scenarios:
  * honest  -- all neighbours truthful (control).
  * blatant -- the liar grossly inflates its release claim every tick.
  * stealth -- the liar inflates a little, intermittently.

Per (map, scenario, seed) we record: delay vs the same-seed MaxPressure baseline, the number of
lies actually injected (bus lie_log), and -- by replaying the controller's conservation
Detections through a TrustLedger (local sensing = ground truth) -- each source's final trust,
lies caught, and whether a caught liar can still corroborate a preemption. The claim to test:
truth-telling holds trust high, a caught lie collapses it (asymmetric) and bounds the liar, and
delay is not wrecked by the lie because local sensing overrides the false claim.

Uses one fixed fast SLM (qwen2.5-0.5b) so the honesty scenario is the only variable. GPU (coord
needs the SLM). DfT daily-resolution demand (§8): descriptive mechanism demonstration.
"""
from __future__ import annotations

import argparse
import json
import os

_SRC = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(_SRC), "results")
RAW = os.path.join(RESULTS, "trust_traffic_raw")

from experiment_topology import _probe, _topologies  # noqa: E402
from experiment_traffic import NullAgent, TimingAgent, build_coordination, run_arm  # noqa: E402
from trust_injection import replay_trust  # noqa: E402

SCENARIOS = ("honest", "blatant", "stealth")


def _liar_for(label, net):
    """Pick the junction with the most neighbours (most claims -> most testable) as the liar."""
    import traci
    from sumolib import checkBinary
    # tls list needs a live net; read adjacency via build_coordination (sumolib only).
    binary = checkBinary("sumo")
    traci.start([binary, "-n", net, "--begin", "0", "--end", "1", "--no-step-log", "true",
                 "--no-warnings", "true"])
    try:
        tls = list(traci.trafficlight.getIDList())
    finally:
        traci.close()
    coord = build_coordination(tls, net_path=net)
    adj = coord["adjacency"]
    if not any(adj.values()):
        return None, tls
    liar = max(tls, key=lambda j: len(adj.get(j, ())))
    return (liar if adj.get(liar) else None), tls


def run(model="qwen2.5-0.5b", seeds=(42, 7, 123), end=1200, gate=2):
    os.makedirs(RAW, exist_ok=True)
    agent_probe, reason = _probe(model)
    if agent_probe is None:
        print(f"model {model} not servable: {reason}")
        return {"error": reason}
    tops = [t for t in _topologies() if os.path.exists(t["net"]) and os.path.exists(t["routes"])]
    cells = []
    for t in tops:
        label, net, routes = t["label"], t["net"], t["routes"]
        liar, _tls = _liar_for(label, net)
        if liar is None:
            cells.append({"topology": label, "skipped": "no neighbour adjacency (coordination inert)"})
            print(f"  {label}: SKIP (no adjacency)", flush=True)
            continue
        print(f"  {label}: liar junction = {liar}", flush=True)
        for scenario in SCENARIOS:
            for s in seeds:
                rawp = os.path.join(RAW, f"{label}__{scenario}__s{s}.json")
                if os.path.exists(rawp):
                    print(f"    {scenario:8s} s{s} SKIP", flush=True)
                    continue
                base = run_arm(f"tt_{label}_mp_s{s}", NullAgent(), seed=s, end=end, gate=gate,
                               config="myopic", net=net, routes=routes)
                base_delay = base["metrics"]["mean_network_delay_s"]
                liars = None if scenario == "honest" else {liar: scenario}
                timing = TimingAgent(agent_probe, forward_note=True)
                r = run_arm(f"tt_{label}_{scenario}_s{s}", timing, seed=s, end=end, gate=gate,
                            config="coordination", net=net, routes=routes, liars=liars)
                d = r["metrics"]["mean_network_delay_s"]
                trust = replay_trust(r.get("events", []), liars or {})
                rec = {"topology": label, "scenario": scenario, "seed": s, "liar": liar,
                       "delay_s": d, "baseline_delay_s": base_delay,
                       "delay_rel_pct": round((d - base_delay) / base_delay * 100.0, 4) if base_delay else None,
                       "n_lies_injected": len(r.get("lie_log", [])),
                       "trust_summary": trust,
                       "liar_trust": (trust.get(liar) or {}).get("final_trust"),
                       "liar_lies_caught": (trust.get(liar) or {}).get("lies_caught"),
                       "liar_can_corroborate": (trust.get(liar) or {}).get("can_corroborate")}
                with open(rawp, "w", encoding="utf-8") as fh:
                    json.dump(rec, fh, indent=2)
                cells.append(rec)
                print(f"    {scenario:8s} s{s} delay_rel={rec['delay_rel_pct']}% "
                      f"lies={rec['n_lies_injected']} liar_trust={rec['liar_trust']} "
                      f"caught={rec['liar_lies_caught']} corrob={rec['liar_can_corroborate']}", flush=True)
    aggregate()
    return {"cells": cells}


def aggregate():
    if not os.path.isdir(RAW):
        return
    rows = []
    for fn in sorted(os.listdir(RAW)):
        if fn.endswith(".json"):
            with open(os.path.join(RAW, fn), encoding="utf-8") as fh:
                rows.append(json.load(fh))
    # group by (topology, scenario): mean delay_rel + mean liar trust
    agg = {}
    for r in rows:
        if "delay_rel_pct" not in r:
            continue
        k = (r["topology"], r["scenario"])
        a = agg.setdefault(k, {"rel": [], "trust": [], "caught": [], "lies": []})
        a["rel"].append(r["delay_rel_pct"])
        if r.get("liar_trust") is not None:
            a["trust"].append(r["liar_trust"])
        if r.get("liar_lies_caught") is not None:
            a["caught"].append(r["liar_lies_caught"])
        a["lies"].append(r.get("n_lies_injected", 0))
    out = {"experiment": "H2_trust_traffic", "scenarios": list(SCENARIOS), "cells": {}}
    for (top, sc), a in sorted(agg.items()):
        mean = lambda xs: round(sum(xs) / len(xs), 3) if xs else None  # noqa: E731
        out["cells"][f"{top}::{sc}"] = {
            "mean_delay_rel_pct": mean(a["rel"]), "n": len(a["rel"]),
            "mean_liar_final_trust": mean(a["trust"]), "mean_lies_caught": mean(a["caught"]),
            "mean_lies_injected": mean(a["lies"])}
    jp = os.path.join(RESULTS, "experiment_trust_traffic.json")
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"aggregated -> {jp}", flush=True)
    for k, v in out["cells"].items():
        print(f"  {k:34s} delay_rel={v['mean_delay_rel_pct']}% liar_trust={v['mean_liar_final_trust']} "
              f"caught={v['mean_lies_caught']}/{v['mean_lies_injected']}", flush=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="H2 trust axis in the traffic sim (honest/blatant/stealth).")
    ap.add_argument("--model", default="qwen2.5-0.5b")
    ap.add_argument("--seeds", nargs="*", type=int, default=[42, 7, 123])
    ap.add_argument("--end", type=int, default=1200)
    ap.add_argument("--aggregate", action="store_true")
    ns = ap.parse_args()
    if ns.aggregate:
        aggregate()
    else:
        run(model=ns.model, seeds=tuple(ns.seeds), end=ns.end)
