"""Measured hourly demand profile from the DfT raw manual counts (MASTER-SPEC §8).

Reads the filtered DfT raw-count rows for the Euston A501 count points
(`sumo/euston/a501_raw_hourly_counts.csv`, from the DfT raw-counts release, the SAME
NAMED source family as the AADF magnitude already used) and derives the MEASURED
temporal profile that the demand builder otherwise ASSUMES:

  * the hourly flow profile (07:00-19:00, the manual-survey window),
  * the directional split (E/W), and
  * the vehicle mix per hour.

This upgrades the §8 demand-honesty posture from "temporal profile ASSUMED
(peak-hour fraction 0.085)" to "temporal profile MEASURED from the DfT raw survey"
for the peak-hour MAGNITUDE + directional split. It does NOT unlock an inferential
claim: the survey is a SINGLE weekday (n=1 day, 07:00-19:00 only) and carries no
junction turning proportions, so H1 inferential claims stay §8-gated until a
time-resolved TfL source (hourly + turning + mix) lands. Pure stdlib; no SUMO.
"""
from __future__ import annotations

import csv
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.normpath(
    os.path.join(_HERE, "..", "sumo", "euston", "a501_raw_hourly_counts.csv"))

# The A501 corridor count points already used for the AADF magnitude (§8).
A501_COUNT_POINTS = ("18077", "56815")
# DfT raw-count per-vehicle-type columns -> the demand vType families.
_MIX_COLUMNS = {
    "cars_and_taxis": "car",
    "two_wheeled_motor_vehicles": "motorcycle",
    "buses_and_coaches": "bus",
    "LGVs": "lgv",
    "all_HGVs": "hgv",
}


def load_rows(csv_path: str | None = None) -> list[dict]:
    """Load the filtered raw-count rows (fail-loud if the file/columns are absent)."""
    path = csv_path or DEFAULT_CSV
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"no rows in {path}")
    required = {"count_point_id", "direction_of_travel", "year", "hour",
                "all_motor_vehicles"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"raw-count CSV missing columns: {sorted(missing)}")
    return rows


def measured_profile(csv_path: str | None = None, count_points=A501_COUNT_POINTS,
                     year: str | None = None) -> dict:
    """Derive the measured hourly profile for the given count points + survey year.

    Aggregates over the count points and both directions. Returns the per-hour totals,
    the normalised hourly SHARE profile, the peak hour + its per-direction flow (veh/h),
    the directional split, and the vehicle mix (fractions). Uses the latest survey year
    present unless ``year`` is given. Fail-loud on empty selection."""
    rows = load_rows(csv_path)
    sel0 = [r for r in rows if r["count_point_id"] in set(count_points)]
    if not sel0:
        raise ValueError(f"no rows for count points {count_points}")
    yr = year or str(max(int(r["year"]) for r in sel0))
    sel = [r for r in sel0 if r["year"] == yr]
    if not sel:
        raise ValueError(f"no rows for year {yr}")

    hours: dict[int, int] = {}
    by_dir: dict[str, int] = {}
    by_dir_hour: dict[tuple, int] = {}
    mix: dict[str, int] = {}
    for r in sel:
        h = int(r["hour"])
        v = int(r["all_motor_vehicles"])
        d = r["direction_of_travel"]
        hours[h] = hours.get(h, 0) + v
        by_dir[d] = by_dir.get(d, 0) + v
        by_dir_hour[(h, d)] = by_dir_hour.get((h, d), 0) + v
        for col, fam in _MIX_COLUMNS.items():
            try:
                mix[fam] = mix.get(fam, 0) + int(r.get(col, 0) or 0)
            except ValueError:
                continue

    total = sum(hours.values())
    peak_hour = max(hours, key=lambda h: hours[h])
    peak_total = hours[peak_hour]
    per_dir_peak = {d: by_dir_hour.get((peak_hour, d), 0)
                    for d in sorted(by_dir)}
    mix_total = sum(mix.values()) or 1
    return {
        "source": "DfT raw manual counts (07:00-19:00 survey window)",
        "count_points": list(count_points),
        "year": yr,
        "count_dates": sorted({r["count_date"] for r in sel if r.get("count_date")}),
        "hours": dict(sorted(hours.items())),
        "hourly_share": {h: hours[h] / total for h in sorted(hours)} if total else {},
        "peak_hour": peak_hour,
        "peak_hour_total_veh": peak_total,
        "peak_hour_per_direction_veh": per_dir_peak,
        "directional_split": {d: by_dir[d] / sum(by_dir.values())
                              for d in sorted(by_dir)} if by_dir else {},
        "vehicle_mix": {fam: mix.get(fam, 0) / mix_total for fam in
                        sorted(set(_MIX_COLUMNS.values()))},
        "twelve_hour_total_veh": total,
        "measured_not_assumed": True,
        "caveats": [
            "Single weekday survey (n=1 day), 07:00-19:00 only (no overnight).",
            "No junction turning proportions -> turning still assumed.",
            "Removes the assumed peak-hour fraction; does NOT unlock an inferential "
            "claim (H1 inferential stays §8-gated until time-resolved TfL data).",
        ],
    }
