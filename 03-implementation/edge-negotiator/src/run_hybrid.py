"""Run the hybrid SLM + MaxPressure controller over the 2x2 grid.

    python src/run_hybrid.py                # all 4 junctions SLM-controlled
    python src/run_hybrid.py --slm A0       # only A0 uses the SLM; rest = MaxPressure

Requires a model loaded in Foundry Local (see slm_agent.py). Reports traffic metrics
plus a summary of the SLM decision log (how often the shield had to override).
"""
from __future__ import annotations

import argparse
import os

import traci
from sumolib import checkBinary

from run_baseline import CFG, HERE, parse_metrics
from hybrid_controller import HybridController
from slm_agent import SLMAgent


def run(slm_junctions=None, gui: bool = False, seed: int = 42, end: int = 1000) -> dict:
    binary = checkBinary("sumo-gui" if gui else "sumo")
    tripinfo = os.path.join(HERE, "..", "sumo", "tripinfo_hybrid.xml")
    traci.start([binary, "-c", CFG, "--tripinfo-output", tripinfo,
                 "--seed", str(seed), "--no-warnings", "true"])
    tls = traci.trafficlight.getIDList()
    agent = SLMAgent()
    ctrl = HybridController(traci, tls, agent, slm_junctions=slm_junctions or list(tls))

    step = 0
    while traci.simulation.getMinExpectedNumber() > 0 and step < end:
        traci.simulationStep()
        ctrl.step()
        step += 1
    traci.close()

    metrics = parse_metrics(tripinfo)
    ev = ctrl.events
    metrics.update({
        "controller": "hybrid",
        "slm_model": agent.model,
        "slm_junctions": sorted(ctrl.slm),
        "slm_decisions": len(ev),
        "shield_overrode_none": sum(1 for e in ev if e["slm_phase"] is None),
        "slm_differed_from_shield": sum(
            1 for e in ev if e["slm_phase"] is not None and e["slm_phase"] != e["shield_phase"]),
    })
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--slm", nargs="*", default=None, help="junction IDs the SLM controls (default: all)")
    ap.add_argument("--gui", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    result = run(slm_junctions=args.slm, gui=args.gui, seed=args.seed)
    print("\n=== hybrid result ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
