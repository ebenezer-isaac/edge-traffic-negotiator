#!/usr/bin/env python3
"""Build the Euston Road (A501) spine SUMO demand: base.rou.xml + smoke.rou.xml.

Substrate  : euston_spine.net.xml (the 4-TLS eastern A501 stretch, UTM-projected).
Demand pipe: SUMO randomTrips.py (candidate pool) -> routeSampler.py (calibrate to
             REAL DfT edge counts) -> assemble a routes file that assigns every
             vehicle a type sampled from a DfT-anchored vTypeDistribution.

=======================  DEMAND SOURCE + HONESTY (MASTER-SPEC §8)  ============
SOURCE      : DfT Road Traffic Statistics, AADF count-point data
              (dft_traffic_counts_aadf.csv), A501 count points, YEAR 2025. REAL,
              NAMED, public. https://roadtraffic.dft.gov.uk / dft.gov.uk.
MAGNITUDE   : aadf_to_edgedata.py snaps A501 count points onto net edges and
              converts AADF -> peak-hour per-direction flow. On-net anchors:
              cp 18077 / cp 56815 (A501, AADF=38863, 2025) -> 1652 veh/h/dir,
              plus side-road cp 37293 (A5202). routeSampler matches these to
              GEH<5 at 100% of counting locations. This describes the
              OFFLINE routeSampler route-SELECTION fit, NOT the live SUMO run
              (see RUN BEHAVIOUR below).
VEHICLE MIX : REAL DfT proportions from the on-net A501 anchor cp 18077 (2025):
              cars_and_taxis 27848 / two_wheeled 2257 / buses 1669 / LGVs 6147 /
              HGVs 942 (all_motor_vehicles 38863). Encoded as A501_MIX below.
RESOLUTION  : DAILY (Annual Average Daily Flow). NOT hourly. The peak-hour
              fraction (0.085), the AM/PM temporal profile, the directional
              split, and the junction TURNING proportions are ASSUMED, not
              measured (randomTrips draws origins/destinations stochastically).
RUN BEHAVIOUR: verified from sumo/euston/tripinfo_euston.xml (scale 1.0, NO
              active controller, random base routing): of 3154 loaded
              vehicles, completed (vaporized=="")=774 (24.5%), stranded at sim
              end (vaporized=="end")=2330, teleported (vaporized=="teleport")=
              50. The PLAIN run GRIDLOCKS at scale 1.0; it does NOT complete
              3154/3154 with 0 teleports. Count from tripinfo as
              completed=count(vaporized=="") and
              teleports=count(vaporized=="teleport"); NEVER len(tripinfo):
              euston.sumocfg sets write-unfinished/write-undeparted, so every
              LOADED vehicle gets a row regardless of outcome. src/metrics.py
              already counts this correctly (Trip.completed / RunRecord.
              completed_trips). The GEH<5 fit above therefore licenses the
              demand's MAGNITUDE only: the calibrated demand is usable ONLY
              WITH an active signal controller (per sweep_results.json,
              MaxPressure at scale 1.0 = 96.8% completion, 1 teleport).
GATE (§8)   : Because the temporal profile is NOT a real time-resolved (hourly)
              source, §8's hard startup gate applies -> INFERENTIAL claims from
              Euston runs are GATED: PILOT ONLY. The demand anchors a realistic
              MAGNITUDE + MIX; it does not license a "measured demand" claim.
              A "structural zero" coordination term is inert regardless (§8/§9).
================================================================================

Usage:
    ../../.venv/Scripts/python.exe build_demand.py            # build both files
    ../../.venv/Scripts/python.exe build_demand.py --keep-tmp # keep intermediates
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(os.environ.get("SUMO_HOME", ""), "tools")
NET = os.path.join(HERE, "euston_spine.net.xml")
EDGEDATA = os.path.join(HERE, "aadf_counts.edgedata.xml")

# --- REAL DfT A501 vehicle mix (cp 18077, 2025); fractions of all_motor_vehicles.
# car+taxi / two-wheel-motor / bus+coach / LGV / HGV. Sums to 1.0.
DFT_MIX = {
    "car":        ("passenger",  4.3, 27848),
    "motorcycle": ("motorcycle", 2.2,  2257),
    "bus":        ("bus",       12.0,  1669),
    "lgv":        ("delivery",   6.5,  6147),
    "hgv":        ("truck",     12.0,   942),
}
_TOTAL = sum(v[2] for v in DFT_MIX.values())  # 38863

BEGIN, END = 0, 3600          # base: 1-hour demand run
SMOKE_END = 600               # smoke: short horizon
SMOKE_PERIOD = 3.0            # smoke: sparse insertion (~1 veh / 3 s)
CAND_PERIOD = 0.3             # candidate pool density for routeSampler
FRINGE_FACTOR = 10            # bias trip origins/destinations to net fringe
SEED = 42


def _run(cmd: list[str]) -> None:
    print("  $", " ".join(os.path.basename(c) if c.endswith(".py") else c
                           for c in cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=HERE)


def _vtype_distribution() -> str:
    """The DfT-anchored vTypeDistribution block (real 2025 A501 proportions)."""
    lines = ['  <vTypeDistribution id="A501_MIX">']
    for name, (vclass, length, count) in DFT_MIX.items():
        prob = count / _TOTAL
        lines.append(
            f'    <vType id="{name}" vClass="{vclass}" length="{length}" '
            f'probability="{prob:.4f}"/>  <!-- DfT cp18077 2025: {count} -->')
    lines.append("  </vTypeDistribution>")
    return "\n".join(lines)


_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<!-- Euston Road (A501) spine demand, generated by build_demand.py.
     Substrate : euston_spine.net.xml (4-TLS eastern A501 stretch).
     Source    : DfT AADF count points, A501, YEAR 2025 (REAL, NAMED).
     Calibrated: routeSampler to real per-edge peak-hour flow (GEH<5 on the
                 OFFLINE route-selection fit, NOT the live SUMO run: the plain
                 run gridlocks at scale 1.0, 774/3154 (24.5%) completed, 50
                 teleports, see tripinfo_euston.xml + build_demand.py header.
                 Usable ONLY with an active controller, e.g. MaxPressure at
                 scale 1.0 = 96.8% completion, 1 teleport (sweep_results.json)).
     Mix       : REAL DfT cp18077 2025 proportions (vTypeDistribution A501_MIX).
     Resolution: DAILY AADF; hourly profile + turning + direction ASSUMED.
     GATE (§8) : temporal profile NOT time-resolved -> INFERENTIAL claims GATED,
                 PILOT ONLY. This is a realistic magnitude+mix, not measured
                 time-resolved demand. -->
"""


def _assemble(sampled_path: str, out_path: str, title: str) -> int:
    """Wrap routeSampler/duarouter vehicles with the DfT vType distribution."""
    tree = ET.parse(sampled_path)
    vehicles = tree.getroot().findall("vehicle")
    vehicles.sort(key=lambda v: float(v.get("depart", "0")))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(_HEADER)
        f.write(f"<!-- {title}: {len(vehicles)} vehicles -->\n")
        f.write('<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                'xsi:noNamespaceSchemaLocation='
                '"http://sumo.dlr.de/xsd/routes_file.xsd">\n')
        f.write(_vtype_distribution() + "\n")
        for i, veh in enumerate(vehicles):
            route = veh.find("route")
            edges = route.get("edges")
            depart = veh.get("depart", "0")
            f.write(f'  <vehicle id="{i}" type="A501_MIX" depart="{depart}">\n')
            f.write(f'    <route edges="{edges}"/>\n')
            f.write("  </vehicle>\n")
        f.write("</routes>\n")
    return len(vehicles)


def build_base(keep_tmp: bool) -> int:
    cand = os.path.join(HERE, "_cand.rou.xml")
    sampled = os.path.join(HERE, "_sampled.rou.xml")
    print("[base] candidate pool via randomTrips + duarouter")
    _run([sys.executable, os.path.join(TOOLS, "randomTrips.py"),
          "-n", NET, "-o", os.path.join(HERE, "_cand.trips.xml"),
          "-r", cand, "-b", str(BEGIN), "-e", str(END), "-p", str(CAND_PERIOD),
          "--fringe-factor", str(FRINGE_FACTOR), "--seed", str(SEED),
          "--validate", "--vehicle-class", "passenger"])
    print("[base] calibrate to real DfT counts via routeSampler")
    _run([sys.executable, os.path.join(TOOLS, "routeSampler.py"),
          "-r", cand, "--edgedata-files", EDGEDATA,
          "--edgedata-attribute", "entered", "-o", sampled, "--seed", str(SEED)])
    n = _assemble(sampled, os.path.join(HERE, "base.rou.xml"),
                  "base demand (~1 h, DfT-calibrated)")
    if not keep_tmp:
        for p in (cand, sampled, os.path.join(HERE, "_cand.trips.xml")):
            if os.path.exists(p):
                os.remove(p)
    return n


def build_smoke(keep_tmp: bool) -> int:
    trips = os.path.join(HERE, "_smoke.trips.xml")
    routes = os.path.join(HERE, "_smoke.rou.xml")
    print("[smoke] sparse short-horizon pool via randomTrips + duarouter")
    _run([sys.executable, os.path.join(TOOLS, "randomTrips.py"),
          "-n", NET, "-o", trips, "-r", routes,
          "-b", "0", "-e", str(SMOKE_END), "-p", str(SMOKE_PERIOD),
          "--fringe-factor", str(FRINGE_FACTOR), "--seed", str(SEED),
          "--validate", "--vehicle-class", "passenger"])
    n = _assemble(routes, os.path.join(HERE, "smoke.rou.xml"),
                  "smoke demand (600 s, low volume)")
    if not keep_tmp:
        for p in (trips, routes):
            if os.path.exists(p):
                os.remove(p)
    return n


def _measured_scale() -> tuple[float, dict]:
    """Ratio (measured-peak / assumed-peak) for the A501 corridor, from the DfT raw
    manual survey (src/hourly_demand.py). The current base demand is calibrated to the
    ASSUMED peak-hour flow (AADF x PEAK_FRACTION); the measured survey gives the REAL
    peak-hour magnitude, so this ratio rescales the demand to the measured level."""
    src = os.path.normpath(os.path.join(HERE, "..", "..", "src"))
    if src not in sys.path:
        sys.path.insert(0, src)
    from hourly_demand import measured_profile
    p = measured_profile()
    measured_per_dir = p["peak_hour_total_veh"] / 2.0
    # The assumption base.rou.xml was built under: A501 AADF 38863 x 0.085 / 2.
    assumed_per_dir = 38863 * 0.085 / 2.0
    return measured_per_dir / assumed_per_dir, p


def build_hourly(keep_tmp: bool) -> int:
    """Build base_hourly.rou.xml: base.rou.xml rescaled to the MEASURED peak-hour
    magnitude from the DfT raw survey. Deterministic subsample (seeded) of the
    calibrated base vehicles by the measured/assumed ratio -- preserves the route,
    vehicle-mix, and departure-time distributions of the calibrated demand while
    setting the ABSOLUTE magnitude to the measured level. No SUMO tools needed.

    Honest scope: this upgrades the peak-hour MAGNITUDE + temporal basis from ASSUMED
    (peak fraction 0.085) to MEASURED (DfT raw survey); it does NOT unlock an
    inferential claim (single survey day, no turning counts; §8 gate stands)."""
    scale, prof = _measured_scale()
    base = os.path.join(HERE, "base.rou.xml")
    out = os.path.join(HERE, "base_hourly.rou.xml")
    tree = ET.parse(base)
    root = tree.getroot()
    vehicles = root.findall("vehicle")
    # Deterministic subsample: keep a vehicle iff a seeded hash-uniform < scale. Stable
    # across runs (no RNG state), so the measured demand is reproducible.
    import hashlib
    kept = []
    for v in vehicles:
        h = hashlib.sha256(f"{SEED}:{v.get('id')}".encode()).digest()
        u = int.from_bytes(h[:8], "big") / float(1 << 64)  # uniform [0,1)
        if u < scale:
            kept.append(v)
    vtypes = _vtype_distribution()
    with open(out, "w", encoding="utf-8") as f:
        f.write(_HEADER)
        f.write(f"<!-- base_hourly: base.rou.xml rescaled to the MEASURED peak-hour "
                f"magnitude (DfT raw survey {prof['year']}, peak hour {prof['peak_hour']}:00, "
                f"{prof['peak_hour_total_veh']} veh/h both-dir); scale={scale:.3f} vs the "
                f"assumed peak-fraction demand; {len(kept)}/{len(vehicles)} vehicles. "
                f"MEASURED magnitude, still PILOT (n=1 survey day, section 8 gate). -->\n")
        f.write('<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                'xsi:noNamespaceSchemaLocation='
                '"http://sumo.dlr.de/xsd/routes_file.xsd">\n')
        f.write(vtypes + "\n")
        for i, veh in enumerate(kept):
            route = veh.find("route")
            f.write(f'  <vehicle id="{i}" type="A501_MIX" depart="{veh.get("depart","0")}">\n')
            f.write(f'    <route edges="{route.get("edges")}"/>\n')
            f.write("  </vehicle>\n")
        f.write("</routes>\n")
    print(f"wrote base_hourly.rou.xml ({len(kept)} vehicles, scale={scale:.3f} to the "
          f"measured peak {prof['peak_hour_total_veh']} veh/h at {prof['peak_hour']}:00)")
    return len(kept)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keep-tmp", action="store_true",
                    help="keep intermediate _cand/_sampled files")
    ap.add_argument("--hourly", action="store_true",
                    help="build base_hourly.rou.xml (base rescaled to the MEASURED "
                         "DfT peak-hour magnitude) instead of the full pipeline")
    args = ap.parse_args()
    if args.hourly:
        n = build_hourly(args.keep_tmp)
        print(f"MEASURED-hourly demand: {n} vehicles (peak-hour magnitude from the DfT "
              "raw survey; section-8 PILOT -- single survey day, turning still assumed).")
        return 0
    if not TOOLS or not os.path.isdir(TOOLS):
        print("ERROR: SUMO_HOME/tools not found; set SUMO_HOME.", file=sys.stderr)
        return 2
    if not os.path.exists(EDGEDATA):
        print(f"ERROR: {EDGEDATA} missing; run aadf_to_edgedata.py first.",
              file=sys.stderr)
        return 2
    nb = build_base(args.keep_tmp)
    ns = build_smoke(args.keep_tmp)
    print(f"\nwrote base.rou.xml ({nb} vehicles) + smoke.rou.xml ({ns} vehicles)")
    print("DEMAND IS DfT-MAGNITUDE-CALIBRATED, DAILY-RESOLUTION -> "
          "inferential claims GATED (pilot only), per MASTER-SPEC §8.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
