"""Tests for the powered-runs honest gate (src/experiment_powered_gate.py).

The gate must be an HONEST record: it must never claim an inferential result, must
list the blocked claim classes + the unblock condition, and must surface whatever
pilot artifacts exist without upgrading them to powered claims.
"""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import experiment_powered_gate as pg  # noqa: E402


def test_gate_is_gated_not_a_powered_claim():
    r = pg.build_gate()
    assert "GATED" in r["status"]
    # It must NOT assert significance / CI / TOST anywhere in claimable_now.
    joined = " ".join(r["claimable_now"]).lower()
    for banned in ("significance", "p-value", "confidence interval", "tost"):
        assert banned not in joined


def test_gate_lists_blocked_classes_and_unblock():
    r = pg.build_gate()
    assert len(r["blocked_until_time_resolved_demand"]) >= 3
    unblock = " ".join(r["what_would_unblock"]).lower()
    assert "time-resolved" in unblock and "tfl" in unblock
    assert "n>=30" in " ".join(r["blocked_until_time_resolved_demand"]).lower()


def test_gate_demand_honesty_names_daily_resolution():
    r = pg.build_gate()
    assert "DAILY" in r["demand_honesty"] and "ASSUMED" in r["demand_honesty"]


def test_gate_pilot_evidence_is_labelled_pilot():
    # Any surfaced pilot artifact must carry a PILOT label, never a powered claim.
    r = pg.build_gate()
    for e in r["pilot_evidence"]:
        assert "PILOT" in e["kind"] or "pilot" in e["kind"].lower()
