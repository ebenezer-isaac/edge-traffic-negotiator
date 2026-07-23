"""Tests for the measured DfT hourly-demand parser (src/hourly_demand.py).

Written to FAIL if the parser fabricates or mis-derives the measured profile, or drops
the honesty caveats that keep it a pilot (single survey day, no turning counts).
"""
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import hourly_demand as hd  # noqa: E402


def test_measured_profile_from_real_csv():
    p = hd.measured_profile()
    assert p["year"] == "2024"                       # latest survey year on file
    assert 7 <= p["peak_hour"] <= 18                  # within the 07-19 survey window
    assert p["peak_hour_total_veh"] > 0
    # per-direction peak sums to the peak-hour total (E + W).
    assert sum(p["peak_hour_per_direction_veh"].values()) == p["peak_hour_total_veh"]
    assert p["measured_not_assumed"] is True


def test_hourly_share_sums_to_one():
    p = hd.measured_profile()
    assert sum(p["hourly_share"].values()) == pytest.approx(1.0, abs=1e-6)


def test_directional_split_and_mix_normalised():
    p = hd.measured_profile()
    assert sum(p["directional_split"].values()) == pytest.approx(1.0, abs=1e-6)
    assert sum(p["vehicle_mix"].values()) == pytest.approx(1.0, abs=1e-6)
    assert p["vehicle_mix"]["car"] > 0.5              # cars dominate the A501 mix


def test_caveats_keep_it_a_pilot():
    p = hd.measured_profile()
    joined = " ".join(p["caveats"]).lower()
    assert "single weekday" in joined or "n=1" in joined
    assert "turning" in joined                        # turning still assumed
    assert "§8" in " ".join(p["caveats"]) or "inferential" in joined


def test_fail_loud_on_missing_file(tmp_path):
    with pytest.raises((FileNotFoundError, ValueError)):
        hd.measured_profile(csv_path=str(tmp_path / "nope.csv"))


def test_fail_loud_on_unknown_count_points():
    with pytest.raises(ValueError):
        hd.measured_profile(count_points=("99999",))
