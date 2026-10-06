"""Fixed-time floor with full guard metrics on the three original maps,
over the 30 training-disjoint evaluation seeds."""
import json, os, sys
_SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SRC)
RESULTS = os.path.join(os.path.dirname(_SRC), "results")
from experiment_topology import _topologies
from experiment_fixedtime import _run_fixedtime

DIS = [1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,
       24, 25, 26, 27, 28, 30, 31, 32, 33, 34]
TARGETS = ["euston_peakhour", "bloomsbury_grid", "oldstreet_junction"]
gate_dir = os.path.join(_SRC, "..", "sumo", "euston")
os.makedirs(gate_dir, exist_ok=True)
tops = {t["label"]: t for t in _topologies()}
out = {"experiment": "fixed_time_guards_disjoint30", "seeds": DIS, "end": 1200, "cells": []}
for lab in TARGETS:
    t = tops[lab]
    for s in DIS:
        m = _run_fixedtime(t["label"], t["net"], t["routes"], s, 1200, gate_dir)
        out["cells"].append({"topology": lab, "seed": s,
                             "fixedtime_delay_s": m["mean_network_delay_s"],
                             "teleports": m.get("teleports"),
                             "completed": m.get("completed"),
                             "loaded": m.get("loaded"),
                             "undeparted": m.get("undeparted")})
        print("  %-20s s%-3d delay=%8.2f tel=%s compl=%s/%s" % (
            lab, s, m["mean_network_delay_s"], m.get("teleports"),
            m.get("completed"), m.get("loaded")), flush=True)
        with open(os.path.join(RESULTS, "experiment_fixedtime_guards.json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)
print("DONE", flush=True)
