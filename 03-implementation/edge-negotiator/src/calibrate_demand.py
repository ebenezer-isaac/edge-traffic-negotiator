"""Demand-calibrate a topology by subsampling its route file (SUMO XML).

Mirrors the Old Street treatment: the default randomTrips output oversaturates
some real maps, so the network never clears within the horizon and mean delay
becomes a gridlock-regime artefact rather than a comparable quantity. This
subsamples vehicles (keeping vType declarations) and reports the completion
rate and teleport count per demand fraction, so a fraction can be chosen on
evidence.

Usage: python src/calibrate_demand.py --topology bloomsbury_grid \
           --fracs 0.25 0.4 0.55 --seeds 1 2 4
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
RESULTS = os.path.normpath(os.path.join(_HERE, "..", "results"))

from experiment_topology import _topologies  # noqa: E402
from experiment_traffic import NullAgent, run_arm  # noqa: E402


def subsample(src: str, dst: str, frac: float, seed: int = 7) -> int:
    """Write dst keeping every non-vehicle child (vType, route defs) and a
    deterministic `frac` sample of vehicles/trips, preserving document order."""
    tree = ET.parse(src)
    root = tree.getroot()
    veh = [c for c in root if c.tag in ("vehicle", "trip")]
    other = [c for c in root if c.tag not in ("vehicle", "trip")]
    rng = random.Random(seed)
    keep = set(rng.sample(range(len(veh)), int(len(veh) * frac)))
    kept = [v for i, v in enumerate(veh) if i in keep]
    for c in list(root):
        root.remove(c)
    for c in other:
        root.append(c)
    for v in kept:
        root.append(v)
    tree.write(dst, encoding="UTF-8", xml_declaration=True)
    return len(kept)


def main(topology, fracs, seeds, end, gate):
    t = next(x for x in _topologies() if x["label"] == topology)
    src = t["routes"]
    base = os.path.dirname(src)
    out = []
    for frac in fracs:
        dst = os.path.join(base, f"_cal_{int(frac * 100)}.rou.xml")
        n = subsample(src, dst, frac)
        rows = []
        for s in seeds:
            r = run_arm(f"cal{frac}_s{s}", NullAgent(), seed=s, end=end, gate=gate,
                        config="myopic", net=t["net"], routes=dst)
            m = r["metrics"]
            rows.append(m)
        ld = sum(m["loaded"] for m in rows) / len(rows)
        cp = sum(m["completed"] for m in rows) / len(rows)
        tp = sum(m["teleports"] for m in rows) / len(rows)
        dl = sum(m["mean_network_delay_s"] for m in rows) / len(rows)
        pct = cp / ld * 100 if ld else 0.0
        print(f"frac={frac:.2f} trips={n} loaded={ld:.0f} completion={pct:.1f}% "
              f"teleports={tp:.1f} delay={dl:.1f}s", flush=True)
        out.append({"frac": frac, "trips": n, "loaded": round(ld), "completed": round(cp),
                    "completion_pct": round(pct, 1), "teleports": round(tp, 1),
                    "delay_s": round(dl, 1), "file": dst})
    p = os.path.join(RESULTS, f"calibration_{topology}.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"topology": topology, "source": src, "seeds": seeds,
                   "end": end, "cells": out}, fh, indent=2)
    print(f"wrote {p}", flush=True)
    print("CALIBRATION DONE", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Subsample demand and report clearance.")
    ap.add_argument("--topology", required=True)
    ap.add_argument("--fracs", nargs="*", type=float, default=[0.25, 0.4, 0.55])
    ap.add_argument("--seeds", nargs="*", type=int, default=[1, 2, 4])
    ap.add_argument("--end", type=int, default=1200)
    ap.add_argument("--gate", type=int, default=2)
    ns = ap.parse_args()
    main(ns.topology, ns.fracs, ns.seeds, ns.end, ns.gate)
