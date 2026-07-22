#!/usr/bin/env python3
"""Anchor SUMO demand to DfT AADF link counts, for the Euston Road (A501)
corridor.

Pipeline role (corridor demand-calibration extraction):
  AADF (vehicles/day, all directions) -> hourly peak flow (veh/h on a SUMO edge)
  -> SUMO edgeData <interval> file -> routeSampler count calibrator.

Steps performed here:
  1. Read the DfT AADF CSV (dft_traffic_counts_aadf.csv, inside aadf.zip).
  2. Keep count points inside the corridor bbox, latest year per count point.
  3. Snap each count point (lat/lon) to the nearest SUMO edge in the network
     using sumolib (requires a geo-referenced .net.xml, i.e. built with
     --proj.utm; we convert lon/lat -> net XY with net.convertLonLat2XY).
  4. Convert AADF -> directional peak-hour flow:
        peak_hour = AADF * PEAK_FRACTION       (AADF is both directions)
        per_direction = peak_hour / 2          (corridor edges are one-way pairs)
     PEAK_FRACTION default 0.085 (~8.5% of daily flow in the AM/PM peak hour) is
     the assumed-profile parameter the brief calls out; tune per scenario.
  5. Write a SUMO edgeData file (<meandata>) with `entered` counts per edge,
     consumable by routeSampler.py -d.

NOTE: convertLonLat2XY needs pyproj. If pyproj is absent, install it into the
venv (pip install pyproj) OR snap using easting/northing columns from the AADF
CSV against the net's UTM offset. This script tries pyproj first and prints a
clear message if it is missing (do NOT silently mis-snap).
"""
from __future__ import annotations
import argparse, csv, io, sys, zipfile
from xml.sax.saxutils import quoteattr

import sumolib  # type: ignore

# Corridor bbox W,S,E,N (must match extract_corridor.ps1).
# PENDING: this bbox is the PRIOR (Lambeth) corridor's bounds, kept only so the
# script remains runnable pending the Euston Road (A501) net build; it must be
# re-derived to the real Euston Road corridor bbox before this pipeline is run
# against euston_spine.net.xml.
BBOX = (-0.1190, 51.4600, -0.0930, 51.4980)
PEAK_FRACTION_DEFAULT = 0.085  # assumed peak-hour share of AADF (tune per scenario)
SNAP_RADIUS_M = 60.0           # max distance count-point -> edge to accept a match


def latest_corridor_points(aadf_zip: str) -> list[dict]:
    w, s, e, n = BBOX
    z = zipfile.ZipFile(aadf_zip)
    name = next(f for f in z.namelist() if f.endswith(".csv"))
    latest: dict[str, dict] = {}
    with z.open(name) as fh:
        rdr = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig"))
        for row in rdr:
            try:
                lat = float(row["latitude"]); lon = float(row["longitude"])
            except (ValueError, KeyError):
                continue
            if not (w <= lon <= e and s <= lat <= n):
                continue
            cp = row["count_point_id"]
            if cp not in latest or int(row["year"]) > int(latest[cp]["year"]):
                latest[cp] = row
    return list(latest.values())


def snap_to_edge(net, lon: float, lat: float):
    """Return (edge, dist_m) of nearest drivable edge, or (None, inf)."""
    try:
        x, y = net.convertLonLat2XY(lon, lat)
    except ImportError:
        print("ERROR: pyproj not installed; cannot convert lon/lat -> net XY.\n"
              "       Run: .venv\\Scripts\\python -m pip install pyproj", file=sys.stderr)
        sys.exit(2)
    candidates = net.getNeighboringEdges(x, y, r=SNAP_RADIUS_M)
    if not candidates:
        return None, float("inf")
    edge, dist = min(candidates, key=lambda ed: ed[1])
    # only keep car-drivable edges
    if not edge.allows("passenger"):
        drivable = [(ed, d) for ed, d in candidates if ed.allows("passenger")]
        if not drivable:
            return None, float("inf")
        edge, dist = min(drivable, key=lambda ed: ed[1])
    return edge, dist


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--net", required=True, help="geo-referenced .net.xml (built with --proj.utm)")
    ap.add_argument("--aadf-zip", default="aadf.zip", help="DfT AADF zip")
    ap.add_argument("--out", default="aadf_counts.edgedata.xml", help="output edgeData file")
    ap.add_argument("--peak-fraction", type=float, default=PEAK_FRACTION_DEFAULT)
    ap.add_argument("--begin", type=int, default=0)
    ap.add_argument("--end", type=int, default=3600, help="interval length seconds (1 h peak)")
    args = ap.parse_args()

    net = sumolib.net.readNet(args.net)
    pts = latest_corridor_points(args.aadf_zip)
    print(f"corridor count points (latest year): {len(pts)}")

    matched, intervals = [], []
    for row in pts:
        try:
            aadf = float(row["all_motor_vehicles"])
        except (ValueError, KeyError):
            continue
        edge, dist = snap_to_edge(net, float(row["longitude"]), float(row["latitude"]))
        if edge is None or dist > SNAP_RADIUS_M:
            continue
        per_dir_peak = aadf * args.peak_fraction / 2.0  # veh/h, single direction
        matched.append((edge.getID(), int(round(per_dir_peak)), row, dist))

    # de-duplicate: if two count points snap to one edge, keep the larger AADF
    best: dict[str, tuple] = {}
    for eid, cnt, row, dist in matched:
        if eid not in best or cnt > best[eid][0]:
            best[eid] = (cnt, row, dist)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("<meandata>\n")
        f.write(f'  <interval id="aadf_peak" begin="{args.begin}" end="{args.end}">\n')
        for eid, (cnt, row, dist) in sorted(best.items()):
            f.write(f'    <edge id={quoteattr(eid)} entered="{cnt}"/>  '
                    f'<!-- cp {row["count_point_id"]} {row["road_name"]} '
                    f'AADF={row["all_motor_vehicles"]} {row["year"]} snap={dist:.0f}m -->\n')
        f.write("  </interval>\n")
        f.write("</meandata>\n")

    print(f"wrote {len(best)} edge count anchors -> {args.out}")
    print("routeSampler usage:")
    print(f"  python routeSampler.py -r candidate.rou.xml -d {args.out} "
          f"-o calibrated.rou.xml --total-count -1 --optimize full")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
