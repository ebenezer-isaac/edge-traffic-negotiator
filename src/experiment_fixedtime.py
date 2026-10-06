"""Fixed-time (SUMO default TLS program) baseline FLOOR across all topologies.

The thesis compares the SLM against MaxPressure (a strong, throughput-optimal adaptive baseline).
An examiner will rightly ask: how far above the NAIVE floor is that? This runs each net under its
own default fixed-time signal programs (no adaptive controller at all -- FixedTimeController is a
no-op, so SUMO just runs the built-in cyclic timings) and measures mean network delay per
(topology, seed). Combined with the MaxPressure BASELINE files already in results/frontier_raw/,
this gives the ordering fixed-time -> MaxPressure -> best-SLM, so we can state how much of the
gain is 'any adaptive control' vs the SLM specifically.

Pure SUMO (no Foundry/SLM), so it is fast and can be run any time. Same SUMO invocation as
run_arm (identical tripinfo/teleport flags) so the delay numbers are directly comparable.
"""
from __future__ import annotations

import json
import os

_SRC = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(_SRC), "results")

from experiment_topology import _topologies  # noqa: E402
from experiment_traffic import metrics_from_tripinfo  # noqa: E402


def _run_fixedtime(label, net, routes, seed, end, gate_dir):
    """Run one net under its default fixed-time TLS programs; return mean network delay."""
    import traci
    from sumolib import checkBinary
    binary = checkBinary("sumo")
    tripinfo = os.path.join(gate_dir, f"tripinfo_ft_{label}_s{seed}.xml")
    teleports = 0
    step = 0
    traci.start([binary, "-n", net, "-r", routes,
                 "--tripinfo-output", tripinfo,
                 "--tripinfo-output.write-unfinished", "true",
                 "--tripinfo-output.write-undeparted", "true",
                 "--begin", "0", "--end", str(end),
                 "--time-to-teleport", "300",
                 "--seed", str(seed),
                 "--no-step-log", "true", "--no-warnings", "true"])
    try:
        while traci.simulation.getMinExpectedNumber() > 0 and step < end:
            traci.simulationStep()          # FixedTimeController is a no-op: default programs run
            teleports += traci.simulation.getStartingTeleportNumber()
            step += 1
    finally:
        try:
            traci.close()
        except Exception:
            pass
    return metrics_from_tripinfo(tripinfo, teleports, step)


def run(seeds=(42, 7, 123), end=1200):
    gate_dir = os.path.join(_SRC, "..", "sumo", "euston")  # scratch for tripinfo files
    os.makedirs(gate_dir, exist_ok=True)
    tops = [t for t in _topologies() if os.path.exists(t["net"]) and os.path.exists(t["routes"])]
    out = {"experiment": "fixed_time_floor", "seeds": list(seeds), "end": end, "cells": []}
    for t in tops:
        for s in seeds:
            m = _run_fixedtime(t["label"], t["net"], t["routes"], s, end, gate_dir)
            rec = {"topology": t["label"], "seed": s,
                   "fixedtime_delay_s": m["mean_network_delay_s"],
                   "teleports": m.get("teleports"), "completed": m.get("completed"),
                   "loaded": m.get("loaded")}
            out["cells"].append(rec)
            print(f"  {t['label']:20s} s{s} fixed-time delay={m['mean_network_delay_s']:.1f}s "
                  f"teleports={m.get('teleports')} completed={m.get('completed')}", flush=True)
    jp = os.path.join(RESULTS, "experiment_fixedtime.json")
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"wrote {jp}", flush=True)
    return out


def compare():
    """Order fixed-time vs MaxPressure (from frontier BASELINE files), per (topology, seed)."""
    import glob
    ft = {}
    p = os.path.join(RESULTS, "experiment_fixedtime.json")
    if os.path.exists(p):
        for c in json.load(open(p))["cells"]:
            ft[(c["topology"], c["seed"])] = c["fixedtime_delay_s"]
    mp = {}
    for f in glob.glob(os.path.join(RESULTS, "frontier_raw", "BASELINE__*.json")):
        d = json.load(open(f))
        mp[(d["topology"], d["seed"])] = d["mean_network_delay_s"]
    print("topology / seed        fixed-time   MaxPressure   MP vs FT")
    for k in sorted(set(ft) & set(mp)):
        f, m = ft[k], mp[k]
        print(f"  {k[0]:20s} s{k[1]:<4d} {f:8.1f}s    {m:8.1f}s    {(m-f)/f*100:+.1f}%")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Fixed-time (SUMO default) baseline floor.")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--seeds", nargs="*", type=int, default=[42, 7, 123])
    ap.add_argument("--end", type=int, default=1200)
    ns = ap.parse_args()
    if ns.compare:
        compare()
    else:
        run(seeds=tuple(ns.seeds), end=ns.end)
        compare()
