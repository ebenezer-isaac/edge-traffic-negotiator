"""De-risk runner for the REAL Euston Road (A501) spine corridor.

PENDING ARTIFACT: this runner targets ``euston_spine.net.xml``, which does NOT
exist yet -- it must be built with SUMO ``netconvert`` from an OSM extract of
the Euston Road corridor (out of scope for this change; requires SUMO on the
target machine). Until that net is built, this runner is PENDING and cannot
execute end-to-end. The legacy ``lambeth_*.net.xml`` files left in this
directory are the PRIOR corridor's build artifacts, kept for reference only;
they are NOT the Euston substrate and must not be pointed at by ``NET`` below.

Drives the UNMODIFIED src/ controller stack (FixedTimeController,
MaxPressureController) over euston_spine.net.xml end-to-end via TraCI, and runs
a demand sweep (via SUMO's --scale knob over base.rou.xml) to locate the clean
operating band and the gridlock tipping point.

Does NOT edit src/. It imports the controllers as-is to prove (or break) their
compatibility with real irregular junction topology. teleports == gridlock signal.

    .venv/Scripts/python sumo/euston/run_euston.py --controller maxpressure --scale 1.0
    .venv/Scripts/python sumo/euston/run_euston.py --sweep
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
import xml.etree.ElementTree as ET

import traci
from sumolib import checkBinary

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "..", "src"))
sys.path.insert(0, SRC)

from controllers import MaxPressureController, FixedTimeController  # noqa: E402

# PENDING: euston_spine.net.xml does not exist yet (needs netconvert on the
# target machine, out of scope here). This runner cannot execute until it is
# built.
NET = os.path.join(HERE, "euston_spine.net.xml")
ROUTES = os.path.join(HERE, "base.rou.xml")


def parse_metrics(tripinfo_path: str) -> dict:
    if not os.path.exists(tripinfo_path):
        return {"completed": 0}
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


def run(controller: str, scale: float = 1.0, seed: int = 42, end: int = 3600,
        gui: bool = False) -> dict:
    """Run one controller at one demand scale. Captures teleports + insertion stats.

    Returns a result dict. On controller construction/step failure, captures the
    verbatim error rather than crashing the whole sweep (that error IS the data).
    """
    binary = checkBinary("sumo-gui" if gui else "sumo")
    tag = f"{controller}_s{scale:g}"
    tripinfo = os.path.join(HERE, f"tripinfo_euston_{tag}.xml")
    # time-to-teleport 300: gridlock surfaces honestly as teleports.
    traci.start([binary, "-n", NET, "-r", ROUTES,
                 "--tripinfo-output", tripinfo,
                 "--scale", str(scale),
                 "--begin", "0", "--end", str(end),
                 "--time-to-teleport", "300",
                 "--seed", str(seed),
                 "--no-step-log", "true", "--no-warnings", "true"])

    result: dict = {"controller": controller, "scale": scale, "seed": seed}
    err = None
    teleports = 0
    loaded = inserted = 0
    try:
        tls = traci.trafficlight.getIDList()
        result["controlled_tls"] = list(tls)
        if controller == "maxpressure":
            ctrl = MaxPressureController(traci, tls)
        else:
            ctrl = FixedTimeController()

        step = 0
        while traci.simulation.getMinExpectedNumber() > 0 and step < end:
            traci.simulationStep()
            ctrl.step()
            teleports += traci.simulation.getStartingTeleportNumber()
            # accumulate per-step counts (these are per-step deltas, not cumulative)
            loaded += traci.simulation.getLoadedNumber()
            inserted += traci.simulation.getDepartedNumber()
            step += 1
        result["sim_steps"] = step
    except traci.TraCIException as e:
        err = f"TraCIException: {e}"
        result["error"] = err
        result["error_trace"] = traceback.format_exc()
    except Exception as e:  # noqa: BLE001 - we want to capture ANY breakage verbatim
        err = f"{type(e).__name__}: {e}"
        result["error"] = err
        result["error_trace"] = traceback.format_exc()
    finally:
        try:
            traci.close()
        except Exception:
            pass

    result["teleports"] = teleports
    result["loaded"] = loaded
    result["departed_inserted"] = inserted
    result.update(parse_metrics(tripinfo))
    if "completed" in result and loaded:
        result["completion_pct"] = round(100.0 * result["completed"] / loaded, 1)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--controller", choices=["maxpressure", "fixed"], default="maxpressure")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--end", type=int, default=3600)
    ap.add_argument("--gui", action="store_true")
    ap.add_argument("--sweep", action="store_true",
                    help="run the full demand sweep for both controllers")
    args = ap.parse_args()

    if args.sweep:
        scales = [0.3, 0.5, 0.7, 1.0, 1.3]
        controllers = ["fixed", "maxpressure"]
        rows = []
        for ctl in controllers:
            for sc in scales:
                print(f"--- running {ctl} @ scale {sc} ---", flush=True)
                r = run(ctl, scale=sc, seed=args.seed, end=args.end)
                # keep result compact for the JSON dump
                r.pop("error_trace", None)
                r.pop("controlled_tls", None)
                rows.append(r)
                print(json.dumps(r), flush=True)
        out = os.path.join(HERE, "sweep_results.json")
        with open(out, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"\nwrote {out}")
        return

    result = run(args.controller, scale=args.scale, seed=args.seed,
                 end=args.end, gui=args.gui)
    print("\n=== result ===")
    for k, v in result.items():
        if k == "error_trace":
            continue
        print(f"  {k}: {v}")
    if result.get("error_trace"):
        print("\n=== error trace ===\n" + result["error_trace"])


if __name__ == "__main__":
    main()
