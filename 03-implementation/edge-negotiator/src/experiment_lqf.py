"""Longest-Queue-First (LQF) classical baseline.

Raised by the academic supervisor in the 2026-08-06 supervision meeting ("have you
ever noticed any approach using the longest queue first?"). MaxPressure and LQF are
NOT the same rule: MaxPressure scores a phase by *pressure*, the upstream queue minus
the downstream queue it would discharge into, so it declines to serve a long queue
whose exit is blocked; LQF is greedy on the upstream queue alone and has no
downstream term. On short-link networks, where exits block often, the two can
disagree substantially.

This runs LQF as a third classical baseline so the distinction is answered with a
measurement rather than an assertion. The controller subclasses MaxPressureController
and overrides ONLY `decide`, so min-green, yellow clearance, the anti-starvation floor
and the step loop are byte-identical between the two arms: the comparison isolates the
phase-selection rule and nothing else.

Pure SUMO, no SLM, no GPU.
"""
from __future__ import annotations

import json
import os
import sys

_SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SRC)
RESULTS = os.path.join(os.path.dirname(_SRC), "results")

from controllers import MaxPressureController  # noqa: E402
from experiment_topology import _topologies  # noqa: E402
from experiment_traffic import metrics_from_tripinfo  # noqa: E402

DISJOINT = [1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
            23, 24, 25, 26, 27, 28, 30, 31, 32, 33, 34]
TARGETS = ["euston_peakhour", "bloomsbury_grid", "oldstreet_junction",
           "bloomsbury_calibrated", "euston_peakhour_calibrated"]


class LongestQueueFirstController(MaxPressureController):
    """Greedy on upstream halting count; no downstream term. Everything else inherited."""

    def decide(self, tl: str, st: dict) -> int:
        return max(range(len(st["green"])), key=lambda gi: self.green_halting(st, gi))


def _run_lqf(label, net, routes, seed, end, gate_dir):
    import traci
    from sumolib import checkBinary
    binary = checkBinary("sumo")
    tripinfo = os.path.join(gate_dir, f"tripinfo_lqf_{label}_s{seed}.xml")
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
        tls = list(traci.trafficlight.getIDList())
        ctrl = LongestQueueFirstController(traci, tls)
        while traci.simulation.getMinExpectedNumber() > 0 and step < end:
            traci.simulationStep()
            ctrl.step()
            teleports += traci.simulation.getStartingTeleportNumber()
            step += 1
    finally:
        try:
            traci.close()
        except Exception:
            pass
    return metrics_from_tripinfo(tripinfo, teleports, step)


def main():
    gate_dir = os.path.join(_SRC, "..", "sumo", "euston")
    os.makedirs(gate_dir, exist_ok=True)
    tops = {t["label"]: t for t in _topologies()}
    out = {"experiment": "longest_queue_first_baseline",
           "note": "LQF = greedy on upstream halting count. Subclasses MaxPressure and "
                   "overrides decide() only, so shield/min-green/yellow/anti-starvation "
                   "are identical between the two arms.",
           "seeds": DISJOINT, "end": 1200, "cells": []}
    path = os.path.join(RESULTS, "experiment_lqf.json")
    # Resumable: keep any cells already on disk and skip them, so a killed run
    # (or a machine restart) costs at most the cell in flight.
    done = set()
    if os.path.exists(path):
        try:
            prev = json.load(open(path, encoding="utf-8"))
            out["cells"] = prev.get("cells", [])
            done = {(c["topology"], c["seed"]) for c in out["cells"]}
            print(f"  resuming: {len(done)} cells already on disk", flush=True)
        except Exception:
            pass
    for lab in TARGETS:
        if lab not in tops:
            print(f"  SKIP {lab} (not registered)", flush=True)
            continue
        t = tops[lab]
        for s in DISJOINT:
            if (lab, s) in done:
                continue
            m = _run_lqf(t["label"], t["net"], t["routes"], s, 1200, gate_dir)
            out["cells"].append({
                "topology": lab, "seed": s,
                "lqf_delay_s": m["mean_network_delay_s"],
                "teleports": m.get("teleports"), "completed": m.get("completed"),
                "loaded": m.get("loaded"), "undeparted": m.get("undeparted")})
            print("  %-28s s%-3d delay=%8.2f tel=%s compl=%s/%s" % (
                lab, s, m["mean_network_delay_s"], m.get("teleports"),
                m.get("completed"), m.get("loaded")), flush=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(out, fh, indent=2)
    print("DONE ->", path, flush=True)


if __name__ == "__main__":
    main()
