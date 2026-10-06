"""Unattended real-demand sweep: Euston A501, 24h x 3 days, MaxPressure baseline
(+ SLM arm when --slm and Foundry Local is up). Drives the model with the REAL
measured SCOOT hourly profile (3 anchor junctions on the spine), by subsampling
base_hourly.rou.xml to each (day,hour)'s measured fraction of the reference peak.

Resumable: skips (arm,day,hour) cells already in the output JSON. Incremental write
after every cell. Run from the repo edge-negotiator dir with its .venv python.

  python run_scoot_sweep.py                 # MaxPressure baseline, all 72 cells
  python run_scoot_sweep.py --slm MODEL     # add SLM arm (needs Foundry Local)
"""
from __future__ import annotations
import argparse, csv, json, os, sys, time, traceback

REPO = os.environ.get("EDGE_NEGOTIATOR_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, "src")
sys.path.insert(0, SRC)
os.chdir(REPO)

SCRATCH = os.environ.get("SWEEP_DIR", os.path.join(REPO, "realdemand", "results"))
SCOOT_CSV = os.environ.get("SCOOT_CSV", "1453-2627 Scoot Data.csv")  # TfL data supplied under the Environmental Information Regulations (ref. 1453-2627), not redistributed
OUT_JSON = os.path.join(SCRATCH, os.environ.get("SWEEP_OUT", "scoot_sweep_results.json"))
LOG = os.path.join(SCRATCH, os.environ.get("SWEEP_LOG", "scoot_sweep.log"))
REFSCALE = float(os.environ.get("SWEEP_REFSCALE", "1.0"))  # busiest-hour -> REFSCALE*base_hourly
TMPROUTES = os.path.join(SCRATCH, "sweep_routes")
os.makedirs(TMPROUTES, exist_ok=True)

NET = os.path.join(REPO, "sumo", "euston", "euston_spine.net.xml")
BASE_ROUTES = os.path.join(REPO, "sumo", "euston", "base_hourly.rou.xml")
ANCHORS = ("N02/015", "N02/064", "N02/144")  # on-spine, SCOOT-counted
DAYS = ("2026-05-12", "2026-05-13", "2026-05-14")
END = int(os.environ.get("SWEEP_END", "1200"))  # thesis-validated Euston window (end=1200)

from experiment_traffic import NullAgent, run_arm  # noqa: E402
from calibrate_demand import subsample  # noqa: E402


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def corridor_vph():
    """Per-(day,hour) summed inflow across anchor junctions + 3-day mean. Robust int parse."""
    perday = {d: {h: 0 for h in range(24)} for d in DAYS}
    with open(SCOOT_CSV, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            det = r["ScootDetectorId"]
            if not any(det.startswith(a) for a in ANCHORS):
                continue
            d = r["Date"]
            if d not in perday:
                continue
            h = int(r["Hour"])
            v = int(str(r["VehicleCount"]).replace(",", "").strip() or 0)
            perday[d][h] += v
    mean = {h: sum(perday[d][h] for d in DAYS) / len(DAYS) for h in range(24)}
    return perday, mean


def load_results():
    if os.path.exists(OUT_JSON):
        try:
            return json.load(open(OUT_JSON, encoding="utf-8"))
        except Exception:
            pass
    return {"meta": {}, "cells": {}}


def save(res):
    tmp = OUT_JSON + ".tmp"
    json.dump(res, open(tmp, "w", encoding="utf-8"), indent=2)
    os.replace(tmp, OUT_JSON)


def main(slm_model):
    perday, mean = corridor_vph()
    peak_ref = max(mean.values())  # 3-day-mean busiest hour = fraction 1.0 reference
    res = load_results()
    res["meta"] = {"anchors": list(ANCHORS), "days": list(DAYS), "end": END,
                   "peak_ref_vph": round(peak_ref), "refscale": REFSCALE, "net": "euston_spine",
                   "base_routes": "base_hourly.rou.xml",
                   "profile_perday_vph": {d: {str(h): perday[d][h] for h in range(24)} for d in DAYS}}
    arms = [("maxpressure", None)]
    if slm_model:
        arms.append((f"slm:{slm_model}", slm_model))
    total = len(arms) * len(DAYS) * 24
    done = 0
    log(f"START sweep: arms={[a for a,_ in arms]} cells={total} peak_ref={peak_ref:.0f} vph")

    for arm_name, model in arms:
        agent_factory = None
        if model:
            from experiment_traffic import TimingAgent  # noqa
            from experiment_topology import _probe  # noqa
            a, reason = _probe(model)
            if a is None:
                log(f"SKIP arm {arm_name}: Foundry/model unavailable ({reason})")
                continue
            agent_factory = lambda: TimingAgent(a, forward_note=False)
        for d in DAYS:
            for h in range(24):
                key = f"{arm_name}|{d}|{h:02d}"
                done += 1
                if key in res["cells"]:
                    continue
                frac = min(1.0, max(0.02, (perday[d][h] / peak_ref) * REFSCALE))
                rpath = os.path.join(TMPROUTES, f"d{d[-2:]}_h{h:02d}_f{int(frac*100)}.rou.xml")
                try:
                    n = subsample(BASE_ROUTES, rpath, frac, seed=7)
                    agent = agent_factory() if agent_factory else NullAgent()
                    t0 = time.time()
                    r = run_arm(f"scoot_{arm_name}_{d[-2:]}_{h:02d}", agent, seed=1,
                                end=END, net=NET, routes=rpath)
                    m = r["metrics"]
                    cell = {"arm": arm_name, "day": d, "hour": h, "frac": round(frac, 4),
                            "demand_vph": perday[d][h], "trips": n,
                            "delay_s": round(m["mean_network_delay_s"], 2),
                            "completed": m["completed"], "departed": m["departed"],
                            "teleports": m["teleports"], "runtime_s": round(time.time() - t0, 1)}
                    res["cells"][key] = cell
                    save(res)
                    log(f"[{done}/{total}] {key} vph={perday[d][h]} frac={frac:.2f} "
                        f"delay={cell['delay_s']}s completed={cell['completed']} ({cell['runtime_s']}s)")
                except Exception as e:
                    log(f"[{done}/{total}] {key} ERROR {e}\n{traceback.format_exc()}")
                    res["cells"][key] = {"arm": arm_name, "day": d, "hour": h, "error": str(e)}
                    save(res)
    log(f"DONE sweep. cells written: {len(res['cells'])}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--slm", default=None, help="SLM model id (needs Foundry Local)")
    ns = ap.parse_args()
    main(ns.slm)
