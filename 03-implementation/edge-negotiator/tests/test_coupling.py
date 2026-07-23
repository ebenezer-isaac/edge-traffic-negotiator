"""Fault-finding tests for Experiment D, the coupling boundary (src/experiment_coupling.py).

Written to FAIL if: the CUSUM threshold is not calibrated to its FP budget, the
coverage-escape model does not exhibit the phase-lock coupling, the lemma does not hold
under dense coverage, or the severe inferential contrast is ever reported as a PASSED
control (it must stay PROTOCOL-gated).
"""
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import experiment_coupling as cp  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. CUSUM threshold is independently calibrated to its FP budget.
# --------------------------------------------------------------------------- #
def test_cusum_threshold_matches_fp_budget():
    cal = cp.calibrate_cusum_threshold(fp_budget=0.05, n=20000)
    assert cal["tau"] > 0
    assert cal["realised_fp_rate"] == pytest.approx(0.05, abs=0.01)


def test_cusum_threshold_tighter_budget_raises_tau():
    lax = cp.calibrate_cusum_threshold(fp_budget=0.10, n=20000)["tau"]
    strict = cp.calibrate_cusum_threshold(fp_budget=0.01, n=20000)["tau"]
    assert strict > lax   # a tighter FP budget demands a higher threshold


# --------------------------------------------------------------------------- #
# 2. The coupling: phase-lock lowers effective coverage and raises escape.
# --------------------------------------------------------------------------- #
def test_effective_coverage_collapses_under_phaselock():
    assert cp._effective_coverage(0.8, 0.0) == pytest.approx(0.8)   # well-mixed
    assert cp._effective_coverage(0.8, 1.0) == pytest.approx(0.0)   # coverage desert


def test_wellmixed_escape_tracks_one_minus_coverage():
    tau = cp.calibrate_cusum_threshold()["tau"]
    # phaselock=0 -> escape ~ (1 - coverage)
    out = cp.escape_proportion(0.7, 0.0, tau)
    mean = sum(out) / len(out)
    assert mean == pytest.approx(0.30, abs=0.05)


def test_phaselock_escape_exceeds_wellmixed_at_matched_coverage():
    tau = cp.calibrate_cusum_threshold()["tau"]
    mixed = sum(cp.escape_proportion(0.5, 0.0, tau)) / cp.MC_TRIALS
    locked = sum(cp.escape_proportion(0.5, 1.0, tau)) / cp.MC_TRIALS
    assert locked > mixed + 0.2   # the phase-locked pocket escapes far more


# --------------------------------------------------------------------------- #
# 3. The conditional lemma holds under dense coverage.
# --------------------------------------------------------------------------- #
def test_lemma_holds_under_dense_coverage():
    tau = cp.calibrate_cusum_threshold()["tau"]
    lem = cp.lemma_check(tau)
    assert lem["lemma_holds_numerically"] is True
    assert lem["dense_wellmixed_escape_mean"] < 0.15   # escape -> 0 as coverage -> 1
    assert len(lem["hypotheses"]) == 4


# --------------------------------------------------------------------------- #
# 4. The severe contrast is DESCRIPTIVE and stays PROTOCOL-gated (never a pass).
# --------------------------------------------------------------------------- #
def test_severe_contrast_is_protocol_gated_not_passed():
    r = cp.run()
    sc = r["severe_contrast"]
    assert sc["inferential_decision"] == "NOT_RUN"
    assert sc["status"] == "PROTOCOL_NOT_A_PASSED_CONTROL"
    assert sc["direction_as_predicted"] is True          # descriptive direction holds
    assert len(sc["why_gated"]) >= 3                     # honest reasons recorded


def test_all_surface_cells_tagged_modelled():
    r = cp.run()
    cells = r["coverage_escape_surface"]["cells"]
    assert cells and all(c["cell_provenance"] == "MODELLED" for c in cells)


def test_geometry_is_n1_case_study():
    r = cp.run()
    assert "n=1" in r["geometry"]
    assert "corridors in general" in r["geometry"].lower()  # the negative claim is stated


# --------------------------------------------------------------------------- #
# 5. Determinism: seeded -> identical results across runs (no seed-manufactured sig).
# --------------------------------------------------------------------------- #
def test_deterministic_across_runs():
    tau = cp.calibrate_cusum_threshold()["tau"]
    a = cp.escape_proportion(0.5, 1.0, tau)
    b = cp.escape_proportion(0.5, 1.0, tau)
    assert a == b
