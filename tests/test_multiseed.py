"""Tests for the multi-seed robustness aggregation (src/experiment_multiseed.py).

The live run needs Foundry+SUMO; these pin the PURE aggregation/robustness logic so a
multi-seed summary can never misreport the spread or the win-rate."""
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import experiment_multiseed as ms  # noqa: E402


def test_agg_mean_std_min_max():
    g = ms._agg([10.0, 20.0, 30.0])
    assert g["n"] == 3
    assert g["mean"] == pytest.approx(20.0)
    assert g["min"] == 10.0 and g["max"] == 30.0
    assert g["std"] > 0


def test_agg_empty_and_nonnumeric():
    assert ms._agg([])["n"] == 0
    assert ms._agg([None, "x"])["n"] == 0


def test_agg_single_value_zero_std():
    g = ms._agg([42.0])
    assert g["n"] == 1 and g["std"] == 0.0


def test_robust_verdict_reports_means_and_clean_win_count():
    # SLM lower delay + higher completed on every seed -> robust clean win.
    db, ds = [314.0, 315.0, 313.0], [235.0, 240.0, 230.0]
    cb, cs = [361, 360, 362], [472, 470, 474]
    joint = {"clean_win": 3, "trade_off": 0, "match": 0, "regression": 0}
    txt = ms._robust(db, ds, cb, cs, joint, 3)
    assert "3/3" in txt and "clean win" in txt.lower()
    assert "Robust across seeds" in txt


def test_robust_verdict_flags_non_robust():
    db, ds = [314.0, 315.0], [235.0, 400.0]      # one seed loses badly
    cb, cs = [361, 360], [472, 300]
    joint = {"clean_win": 1, "trade_off": 0, "match": 0, "regression": 1}
    txt = ms._robust(db, ds, cb, cs, joint, 2)
    assert "1/2" in txt
    assert "Robust across seeds" not in txt        # not all seeds win -> not "robust"


def test_robust_verdict_gated_when_no_slm():
    assert "gated" in ms._robust([314.0], [], [361], [], {}, 0).lower()


def test_model_map_has_winner():
    assert ms._MODEL_IDS["qwen2.5-0.5b"].startswith("qwen2.5-0.5b")
