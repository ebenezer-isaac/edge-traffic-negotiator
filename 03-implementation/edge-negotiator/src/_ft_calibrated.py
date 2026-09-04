"""Fixed-time floor on the calibrated topologies (pure SUMO, no SLM)."""
import json, os, sys
_SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SRC)
RESULTS = os.path.join(os.path.dirname(_SRC), "results")
from experiment_topology import _topologies
from experiment_fixedtime import _run_fixedtime

TARGETS = ["bloomsbury_calibrated", "euston_peakhour_calibrated"]
SEEDS = [31, 32, 33, 34]
gate_dir = os.path.join(_SRC, "..", "sumo", "euston")
os.makedirs(gate_dir, exist_ok=True)
tops = {t["label"]: t for t in _topologies()}
out = {"experiment": "fixed_time_floor_calibrated", "seeds": SEEDS, "end": 1200, "cells": []}
for lab in TARGETS:
    t = tops[lab]
    for s in SEEDS:
        m = _run_fixedtime(t["label"], t["net"], t["routes"], s, 1200, gate_dir)
        out["cells"].append({"topology": lab, "seed": s,
                             "fixedtime_delay_s": m["mean_network_delay_s"],
                             "teleports": m.get("teleports"), "completed": m.get("completed"),
                             "loaded": m.get("loaded")})
        print(f"  {lab:28s} s{s:<3d} delay={m['mean_network_delay_s']:8.2f}s "
              f"tel={m.get('teleports')} compl={m.get('completed')}/{m.get('loaded')}", flush=True)
        with open(os.path.join(RESULTS, "experiment_fixedtime_calibrated_ext.json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)
print("DONE", flush=True)
