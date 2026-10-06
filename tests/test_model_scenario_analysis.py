"""Tests for the model x scenario differentiation analysis (src/model_scenario_analysis.py).

Pins the methodology math (Pearson/Spearman/rank, rank-reversal detection, win rate) and the
key committed findings (disordinal interaction present; Simpson's paradox: pooled-all positive
but pooled-congested negative). Pure functions -> no SUMO/Foundry."""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import model_scenario_analysis as msa  # noqa: E402


def test_pearson_and_spearman_basics():
    assert round(msa._pearson([1, 2, 3], [1, 2, 3]), 3) == 1.0
    assert round(msa._pearson([1, 2, 3], [3, 2, 1]), 3) == -1.0
    assert msa._pearson([1, 1, 1], [1, 2, 3]) is None      # zero variance -> None
    # Spearman is rank-based: monotone-but-nonlinear -> 1.0 where Pearson < 1
    assert round(msa._spearman([1, 2, 3], [1, 4, 9]), 3) == 1.0


def test_rank_handles_ties():
    assert msa._rank([10, 20, 20, 40]) == [1.0, 2.5, 2.5, 4.0]


def test_leave_one_out_exposes_leverage():
    # a single high-leverage point props up an otherwise weak correlation
    xs = [0, 0, 0, 10]
    ys = [0, 1, 0, 10]
    loo = msa._leave_one_out_pearson(xs, ys)
    assert len(loo) == 4
    assert loo[3] is None or abs(loo[3]) < abs(msa._pearson(xs, ys))  # dropping the leverage pt weakens r


def test_interaction_detects_rank_reversal():
    # model A wins scenario s1, model B wins s2 -> disordinal interaction
    matrix = {"A": {"s1": {"delay_rel_pct": -20, "joint_verdict": "clean_win"},
                    "s2": {"delay_rel_pct": +5, "joint_verdict": "regression"}},
              "B": {"s1": {"delay_rel_pct": -10, "joint_verdict": "clean_win"},
                    "s2": {"delay_rel_pct": -3, "joint_verdict": "clean_win"}}}
    inter = msa._interaction(matrix, ["s1", "s2"])
    assert len(inter["rank_reversals"]) == 1
    rr = inter["rank_reversals"][0]
    assert rr["winner_1"] == "A" and rr["winner_2"] == "B"
    assert inter["eta_squared_descriptive"] is not None


def test_analyse_committed_findings():
    r = msa.analyse()
    # the headline interaction: qwen2.5-0.5b wins Euston, qwen3-0.6b wins the grids
    reversals = r["interaction"]["rank_reversals"]
    assert any(rr["scenario_1"] == "euston_corridor" and rr["winner_1"] == "qwen2.5-0.5b"
               and rr["winner_2"] == "qwen3-0.6b" for rr in reversals)
    # Simpson's paradox: pooled ALL positive, pooled CONGESTED negative
    pooled = r["simpson"]["_pooled"]
    assert pooled["pearson_all"] > 0
    assert pooled["pearson_congested_only"] < 0
    # eta-squared: scenario dominates the variance (substrate matters most)
    eta = r["interaction"]["eta_squared_descriptive"]
    assert eta["scenario"] > eta["model"] and eta["scenario"] > eta["interaction"]
    # win rates present for both topology models
    assert r["win_rates"]["qwen2.5-0.5b"]["topology"]["n"] == 4
    assert r["win_rates"]["qwen3-0.6b"]["topology"]["wins"] == 2
