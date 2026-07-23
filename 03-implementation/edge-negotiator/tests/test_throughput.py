"""Tests for the delay+throughput joint verdict (Akin's methodological point).

Written to FAIL if a delay win is ever reported without checking throughput, if the
joint verdict mislabels a trade-off as a clean win, or if the throughput direction
(higher completed = better) is inverted.
"""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import experiment_traffic as ex  # noqa: E402
import throughput_analysis as ta  # noqa: E402


# --------------------------------------------------------------------------- #
# _bml: direction-aware beats/match/loses.
# --------------------------------------------------------------------------- #
def test_bml_delay_lower_is_better():
    assert ex._bml(235.0, 314.55, lower_is_better=True)[0] == "slm_beats"
    assert ex._bml(400.0, 314.55, lower_is_better=True)[0] == "slm_loses"
    assert ex._bml(315.0, 314.55, lower_is_better=True)[0] == "match"   # within 2%


def test_bml_throughput_higher_is_better():
    assert ex._bml(472, 361, lower_is_better=False)[0] == "slm_beats"   # more completed
    assert ex._bml(300, 361, lower_is_better=False)[0] == "slm_loses"
    assert ex._bml(361, 361, lower_is_better=False)[0] == "match"


# --------------------------------------------------------------------------- #
# _joint_verdict: the trade-off logic.
# --------------------------------------------------------------------------- #
def test_joint_clean_win_needs_no_loss():
    assert ex._joint_verdict("slm_beats", "slm_beats") == "clean_win"
    assert ex._joint_verdict("slm_beats", "match") == "clean_win"
    assert ex._joint_verdict("match", "slm_beats") == "clean_win"


def test_joint_trade_off_is_win_one_lose_other():
    assert ex._joint_verdict("slm_beats", "slm_loses") == "trade_off"
    assert ex._joint_verdict("slm_loses", "slm_beats") == "trade_off"


def test_joint_match_and_regression():
    assert ex._joint_verdict("match", "match") == "match"
    assert ex._joint_verdict("slm_loses", "match") == "regression"
    assert ex._joint_verdict("slm_loses", "slm_loses") == "regression"


# --------------------------------------------------------------------------- #
# verdict(): throughput now reported alongside delay; status contract preserved.
# --------------------------------------------------------------------------- #
def _arm(delay, completed):
    return {"metrics": {"mean_network_delay_s": delay, "completed": completed,
                        "departed": 700}}


def test_verdict_reports_throughput_and_joint():
    v = ex.verdict(_arm(314.55, 361), _arm(235.0, 472))
    assert v["status"] == "slm_beats"            # delay verdict (unchanged contract)
    assert v["throughput_status"] == "slm_beats"  # more vehicles completed
    assert v["throughput_completed_delta"] == 111
    assert v["joint_verdict"] == "clean_win"


def test_verdict_flags_a_real_trade_off():
    # Wins delay but completes FEWER vehicles -> honest trade-off, not a clean win.
    v = ex.verdict(_arm(314.55, 361), _arm(250.0, 300))
    assert v["status"] == "slm_beats"
    assert v["throughput_status"] == "slm_loses"
    assert v["joint_verdict"] == "trade_off"


def test_verdict_status_key_still_delay_for_consumers():
    # The sweep/sota consumers read verdict["status"] as the DELAY verdict.
    v = ex.verdict(_arm(314.55, 361), _arm(235.0, 472))
    assert v["status"] in ("slm_beats", "match", "slm_loses")


# --------------------------------------------------------------------------- #
# analyse(): the committed sweep is all clean wins, no trade-offs.
# --------------------------------------------------------------------------- #
def test_analysis_of_committed_sweep_has_no_trade_offs():
    import json
    p = os.path.join(ta.RESULTS, "experiment_sweep.json")
    with open(p, encoding="utf-8") as fh:
        sweep = json.load(fh)
    r = ta.analyse(sweep)
    assert r["n_trade_off"] == 0            # no delay win came at a throughput cost
    assert r["n_clean_win"] >= 1
    # the winning cell improves BOTH delay and throughput
    win = next(row for row in r["rows"]
               if row.get("model") == "qwen2.5-0.5b" and row.get("config") == "myopic")
    assert win["joint_verdict"] == "clean_win"
    assert win["completed_delta"] > 0        # more vehicles completed, not fewer
