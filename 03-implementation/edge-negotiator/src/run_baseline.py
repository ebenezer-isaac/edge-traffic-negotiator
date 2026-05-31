"""Run a deterministic baseline controller over the 2x2 grid and report metrics.

Wk 1-2 pipeline milestone: proves SUMO + TraCI + a controller loop end-to-end.

    python src/run_baseline.py --controller maxpressure
    python src/run_baseline.py --controller fixed --gui
"""
from __future__ import annotations

import argparse
import os
import xml.etree.ElementTree as ET

import traci
from sumolib import checkBinary

from controllers import MaxPressureController, FixedTimeController

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "..", "sumo", "grid2x2.sumocfg")


def parse_metrics(tripinfo_path: str) -> dict:
    trips = ET.parse(tripinfo_path).getroot().findall("tripinfo")
    n = len(trips)
    if n == 0:
        return {"completed": 0}
    avg = lambda attr: sum(float(t.get(attr)) for t in trips) / n
    return {
        "completed": n,
        "avg_travel_time_s": round(avg("duration"), 2),
        "avg_waiting_time_s": round(avg("waitingTime"), 2),
        "avg_time_loss_s": round(avg("timeLoss"), 2),
    }


def run(controller: str, gui: bool = False, seed: int = 42, end: int = 1000) -> dict:
    binary = checkBinary("sumo-gui" if gui else "sumo")
    tripinfo = os.path.join(HERE, "..", "sumo", f"tripinfo_{controller}.xml")
    traci.start([binary, "-c", CFG, "--tripinfo-output", tripinfo,
                 "--seed", str(seed), "--no-warnings", "true"])
    tls = traci.trafficlight.getIDList()
    ctrl = MaxPressureController(traci, tls) if controller == "maxpressure" else FixedTimeController()

    step = 0
    while traci.simulation.getMinExpectedNumber() > 0 and step < end:
        traci.simulationStep()
        ctrl.step()
        step += 1
    traci.close()

    metrics = parse_metrics(tripinfo)
    metrics["controller"] = controller
    metrics["sim_steps"] = step
    metrics["controlled_tls"] = list(tls)
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--controller", choices=["maxpressure", "fixed"], default="maxpressure")
    ap.add_argument("--gui", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    result = run(args.controller, gui=args.gui, seed=args.seed)
    print("\n=== result ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
