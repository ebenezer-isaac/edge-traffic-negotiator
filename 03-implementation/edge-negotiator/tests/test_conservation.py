"""Tests for the vehicle-conservation plausibility check (src/conservation.py).

Run from the project root with the venv interpreter:
    .venv/Scripts/python -m pytest tests/test_conservation.py -v

These tests are written to BREAK the checker: happy path is minimal; the bulk
covers boundary values, missing-data faults, asymmetric mismatches, ordering
determinism, immutability, and adversarial / malformed input at the boundary.
"""

import os
import sys

import pytest

# src/ is not installed; put it on the path so `import conservation` resolves.
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from conservation import ConservationChecker, Detection  # noqa: E402


# --------------------------------------------------------------------------- #
# Happy path                                                                   #
# --------------------------------------------------------------------------- #


def test_matching_within_tolerance_not_flagged():
    checker = ConservationChecker(tolerance=2)
    claims = {("A0", "A1"): 10}
    observed = {("A0", "A1"): 9}  # delta = 1, within tolerance
    result = checker.evaluate(claims, observed)

    assert len(result) == 1
    det = result[0]
    assert det == Detection("A0", "A1", 10, 9, 1, False, "ok")


def test_exact_match_zero_delta_ok():
    checker = ConservationChecker(tolerance=2)
    result = checker.evaluate({("A0", "B0"): 7}, {("A0", "B0"): 7})
    assert result[0].reason == "ok"
    assert result[0].flagged is False
    assert result[0].delta == 0


# --------------------------------------------------------------------------- #
# Spoof / fault detection                                                      #
# --------------------------------------------------------------------------- #


def test_inflation_spoof_flagged():
    checker = ConservationChecker(tolerance=2)
    result = checker.evaluate({("A0", "A1"): 20}, {("A0", "A1"): 5})
    det = result[0]
    assert det.flagged is True
    assert det.reason == "inflated"
    assert det.delta == 15


def test_under_report_flagged():
    # observed >> claimed : the negative-delta branch (fault or selective hiding)
    checker = ConservationChecker(tolerance=2)
    result = checker.evaluate({("A0", "A1"): 3}, {("A0", "A1"): 18})
    det = result[0]
    assert det.flagged is True
    assert det.reason == "under_reported"
    assert det.delta == -15


def test_missing_claim_flagged():
    # claimed absent (treated as 0) but observed 8 -> B saw traffic A denies.
    checker = ConservationChecker(tolerance=2)
    result = checker.evaluate({}, {("B0", "B1"): 8})
    det = result[0]
    assert det.flagged is True
    assert det.reason == "missing_claim"
    assert det.claimed == 0
    assert det.observed == 8
    assert det.delta == -8


def test_missing_claim_when_explicit_zero_still_balances():
    # An explicit claim of 0 is a *present* claim; with observed 0 -> ok,
    # NOT missing_claim. Distinguishes "said zero" from "said nothing".
    checker = ConservationChecker(tolerance=2)
    result = checker.evaluate({("B0", "B1"): 0}, {("B0", "B1"): 0})
    assert result[0].reason == "ok"
    assert result[0].flagged is False


def test_missing_observation_flagged():
    # claimed 8 but observed absent -> A says it sent traffic B never saw.
    checker = ConservationChecker(tolerance=2)
    result = checker.evaluate({("A1", "B1"): 8}, {})
    det = result[0]
    assert det.flagged is True
    assert det.reason == "missing_observation"
    assert det.claimed == 8
    assert det.observed == 0
    assert det.delta == 8


# --------------------------------------------------------------------------- #
# Boundary values                                                              #
# --------------------------------------------------------------------------- #


def test_boundary_delta_equals_tolerance_not_flagged():
    checker = ConservationChecker(tolerance=2)
    result = checker.evaluate({("A0", "A1"): 7}, {("A0", "A1"): 5})  # delta == 2
    assert result[0].delta == 2
    assert result[0].flagged is False
    assert result[0].reason == "ok"


def test_boundary_delta_one_over_tolerance_flagged():
    checker = ConservationChecker(tolerance=2)
    result = checker.evaluate({("A0", "A1"): 8}, {("A0", "A1"): 5})  # delta == 3
    assert result[0].delta == 3
    assert result[0].flagged is True
    assert result[0].reason == "inflated"


def test_boundary_negative_delta_equals_tolerance_not_flagged():
    checker = ConservationChecker(tolerance=2)
    result = checker.evaluate({("A0", "A1"): 5}, {("A0", "A1"): 7})  # delta == -2
    assert result[0].flagged is False
    assert result[0].reason == "ok"


def test_boundary_negative_delta_one_over_tolerance_flagged():
    checker = ConservationChecker(tolerance=2)
    result = checker.evaluate({("A0", "A1"): 5}, {("A0", "A1"): 8})  # delta == -3
    assert result[0].flagged is True
    assert result[0].reason == "under_reported"


def test_zero_tolerance_any_mismatch_flagged():
    checker = ConservationChecker(tolerance=0)
    ok = checker.evaluate({("A0", "A1"): 4}, {("A0", "A1"): 4})
    bad = checker.evaluate({("A0", "A1"): 4}, {("A0", "A1"): 5})
    assert ok[0].flagged is False
    assert bad[0].flagged is True
    assert bad[0].reason == "under_reported"


# --------------------------------------------------------------------------- #
# Empty / multi-edge / ordering                                                #
# --------------------------------------------------------------------------- #


def test_empty_inputs_empty_list():
    checker = ConservationChecker()
    assert checker.evaluate({}, {}) == []


def test_multiple_edges_deterministic_sorted_order():
    checker = ConservationChecker(tolerance=2)
    claims = {("B1", "B0"): 4, ("A0", "A1"): 20, ("A1", "B1"): 9}
    observed = {("A0", "A1"): 5, ("B1", "B0"): 4, ("B0", "A0"): 6}
    result = checker.evaluate(claims, observed)

    keys = [(d.src, d.dst) for d in result]
    assert keys == sorted(keys)
    assert keys == [
        ("A0", "A1"),
        ("A1", "B1"),
        ("B0", "A0"),
        ("B1", "B0"),
    ]

    by_key = {(d.src, d.dst): d for d in result}
    assert by_key[("A0", "A1")].reason == "inflated"        # 20 vs 5
    assert by_key[("A1", "B1")].reason == "missing_observation"  # claim only
    assert by_key[("B0", "A0")].reason == "missing_claim"   # obs only
    assert by_key[("B1", "B0")].reason == "ok"              # 4 vs 4


def test_one_detection_per_edge_no_duplicates():
    checker = ConservationChecker(tolerance=2)
    claims = {("A0", "A1"): 5, ("A1", "A0"): 5}
    observed = {("A0", "A1"): 5, ("A1", "A0"): 5}
    result = checker.evaluate(claims, observed)
    keys = [(d.src, d.dst) for d in result]
    assert len(keys) == len(set(keys)) == 2


# --------------------------------------------------------------------------- #
# Immutability                                                                 #
# --------------------------------------------------------------------------- #


def test_inputs_not_mutated():
    checker = ConservationChecker(tolerance=2)
    claims = {("A0", "A1"): 20}
    observed = {("A0", "B0"): 8}
    claims_snapshot = dict(claims)
    observed_snapshot = dict(observed)

    checker.evaluate(claims, observed)

    assert claims == claims_snapshot
    assert observed == observed_snapshot


def test_detection_is_frozen():
    det = Detection("A0", "A1", 1, 1, 0, False, "ok")
    with pytest.raises((AttributeError, TypeError)):  # frozen dataclass
        det.flagged = True  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Adversarial / malformed input at the boundary                               #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("bad", [-1, -100])
def test_negative_tolerance_rejected(bad):
    with pytest.raises(ValueError):
        ConservationChecker(tolerance=bad)


@pytest.mark.parametrize("bad", [2.0, "2", None, True, False])
def test_non_int_tolerance_rejected(bad):
    with pytest.raises(TypeError):
        ConservationChecker(tolerance=bad)


def test_negative_count_rejected():
    checker = ConservationChecker()
    with pytest.raises(ValueError):
        checker.evaluate({("A0", "A1"): -3}, {})
    with pytest.raises(ValueError):
        checker.evaluate({}, {("A0", "A1"): -1})


@pytest.mark.parametrize("bad", [2.5, "5", None, True])
def test_non_int_count_rejected(bad):
    checker = ConservationChecker()
    with pytest.raises(TypeError):
        checker.evaluate({("A0", "A1"): bad}, {})


@pytest.mark.parametrize(
    "bad_key",
    [("A0",), ("A0", "A1", "B0"), "A0A1", ("A0", 1)],
)
def test_malformed_edge_key_rejected(bad_key):
    checker = ConservationChecker()
    with pytest.raises(TypeError):
        checker.evaluate({bad_key: 5}, {})


def test_non_dict_inputs_rejected():
    checker = ConservationChecker()
    with pytest.raises(TypeError):
        checker.evaluate([("A0", "A1", 5)], {})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        checker.evaluate({}, "not a dict")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Large-volume sanity (data volume / no overflow surprises)                    #
# --------------------------------------------------------------------------- #


def test_large_counts_inflation_detected():
    checker = ConservationChecker(tolerance=2)
    result = checker.evaluate({("A0", "A1"): 1_000_000}, {("A0", "A1"): 10})
    assert result[0].flagged is True
    assert result[0].reason == "inflated"
    assert result[0].delta == 999_990
