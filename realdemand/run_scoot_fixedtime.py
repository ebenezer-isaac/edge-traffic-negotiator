"""Fixed-time arm for the real-demand Euston sweep, on the exact demand files of scoot_sweep_v2.json.

Each cell's route file is regenerated with the same subsample(frac, seed=7) call the sweep used,
from the frac stored in the MaxPressure cell. A determinism check re-runs a few MaxPressure cells
first and refuses to continue unless they reproduce the stored delay exactly. Writes
scoot_fixedtime.json; does not touch scoot_sweep_v2.json.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

REPO = os.environ.get("EDGE_NEGOTIATOR_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "src"))
os.chdir(REPO)

from calibrate_demand import subsample  # noqa: E402
from experiment_fixedtime import _run_fixedtime  # noqa: E402
from experiment_traffic import NullAgent, run_arm  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SWEEP = json.load(open(os.path.join(HERE, "results", "scoot_sweep_v2.json"), encoding="utf-8"))
OUT = os.path.join(HERE, "results", "scoot_fixedtime.json")
NET = os.path.join(REPO, "sumo", "euston", "euston_spine.net.xml")
BASE = os.path.join(REPO, "sumo", "euston", "base_hourly.rou.xml")
END = SWEEP["meta"]["end"]
TMP = tempfile.mkdtemp(prefix="scoot_ft_")


def routes_for(cell) -> str:
    p = os.path.join(TMP, f"{cell['day'][-2:]}_{cell['hour']:02d}.rou.xml")
    if not os.path.exists(p):
        subsample(BASE, p, cell["frac"], seed=7)
    return p


def main() -> int:
    mp = {k.split("|", 1)[1]: c for k, c in SWEEP["cells"].items() if k.startswith("maxpressure|")}
    for key in ("2026-05-12|06", "2026-05-13|13", "2026-05-14|22"):
        c = mp[key]
        r = run_arm(f"ftcheck_{key.replace('|', '_')}", NullAgent(), seed=1, end=END, net=NET, routes=routes_for(c))
        got = round(r["metrics"]["mean_network_delay_s"], 2)
        print(f"determinism {key}: stored {c['delay_s']} reproduced {got}", flush=True)
        if got != c["delay_s"]:
            print("ABORT: MaxPressure cell did not reproduce; demand files differ from the sweep")
            return 1
    out = {"meta": {"source": "scoot_sweep_v2.json demand files", "end": END, "seed": 1,
                    "controller": "SUMO default fixed-time programs"}, "cells": {}}
    for key, c in sorted(mp.items()):
        t0 = time.time()
        m = _run_fixedtime(f"scoot_{key.replace('|', '_')}", NET, routes_for(c), 1, END, TMP)
        out["cells"][f"fixedtime|{key}"] = {
            "day": c["day"], "hour": c["hour"], "frac": c["frac"],
            "delay_s": round(m["mean_network_delay_s"], 2), "completed": m["completed"],
            "departed": m["departed"], "teleports": m["teleports"], "runtime_s": round(time.time() - t0, 1)}
        json.dump(out, open(OUT, "w", encoding="utf-8"), indent=2)
        print(key, out["cells"][f"fixedtime|{key}"]["delay_s"], flush=True)
    print("DONE", len(out["cells"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
