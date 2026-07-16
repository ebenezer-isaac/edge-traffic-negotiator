"""Tests for system-level fairness and worst-case metrics (src/emergency_metrics.py).

Run from the project root with the venv interpreter:
    .venv/Scripts/python -m pytest tests/test_emergency_metrics.py -v

Context: the supervisors asked for system-level trade-offs -- "fairness across
junctions" and "worst-case guarantees" -- reported alongside throughput. This
module implements all four fairness ideologies from the traffic-signal-control
literature (Jain, Gini, Rawlsian, utilitarian) plus a worst-case (tail) report,
as pure functions of plain delay lists (no SUMO, no TraCI).

These tests exist to BREAK the metrics, per repo testing philosophy: known-value
checks (hand-computed by hand, not just "does it run"), edge cases (empty,
single-element, all-zero, negative, NaN/Inf), and property tests (bounds,
scale invariance) that would catch a wrong formula even if a single known-value
test happened to pass by coincidence.
"""

import math
import os
import random
import statistics
import sys

import pytest

# src/ is not installed; put it on the path so `import emergency_metrics` resolves.
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from emergency_metrics import (  # noqa: E402
    EmergencyMetricsError,
    fairness_report,
    gini,
    jains_index,
    p95,
    rawlsian_worst,
    summarize,
    utilitarian_mean,
    worst_case_report,
)


# =========================================================================== #
# jains_index                                                                  #
# =========================================================================== #
class TestJainsIndex:
    def test_all_equal_is_one(self):
        assert jains_index([5.0, 5.0, 5.0]) == pytest.approx(1.0)

    def test_all_equal_different_magnitude(self):
        assert jains_index([2.0, 2.0]) == pytest.approx(1.0)

    def test_one_hot_is_one_over_n(self):
        # Hand-computed: sum=10, sum^2=100, sumsq=100, n=4 -> 100/(4*100)=0.25=1/n.
        assert jains_index([10.0, 0.0, 0.0, 0.0]) == pytest.approx(0.25)
        assert jains_index([10.0, 0.0, 0.0, 0.0]) == pytest.approx(1.0 / 4)

    def test_hand_computed_mixed_vector(self):
        # [1,2,3]: sum=6, sum^2=36, sumsq=1+4+9=14, n=3 -> 36/42.
        assert jains_index([1.0, 2.0, 3.0]) == pytest.approx(36.0 / 42.0)

    def test_empty_is_defined_as_perfectly_fair(self):
        # Convention: vacuous case (no groups to be unfair between) -> 1.0.
        assert jains_index([]) == pytest.approx(1.0)

    def test_single_element_is_one(self):
        assert jains_index([42.0]) == pytest.approx(1.0)

    def test_all_zero_is_defined_as_perfectly_fair(self):
        # Convention (per spec): all-zero -> 1.0, not NaN/ZeroDivisionError.
        assert jains_index([0.0, 0.0, 0.0]) == pytest.approx(1.0)

    def test_negative_value_rejected(self):
        with pytest.raises(EmergencyMetricsError, match="negative"):
            jains_index([1.0, -2.0, 3.0])

    def test_nan_rejected(self):
        with pytest.raises(EmergencyMetricsError, match="NaN/Inf"):
            jains_index([1.0, float("nan")])

    def test_inf_rejected(self):
        with pytest.raises(EmergencyMetricsError, match="NaN/Inf"):
            jains_index([1.0, float("inf")])

    def test_bool_rejected(self):
        # bool is a subclass of int in Python; guard against it explicitly
        # since a delay of True/False is not a meaningful value.
        with pytest.raises(EmergencyMetricsError):
            jains_index([1.0, True])

    def test_does_not_mutate_input(self):
        values = [3.0, 1.0, 2.0]
        original = list(values)
        jains_index(values)
        assert values == original

    def test_bounds_property_random_vectors(self):
        rng = random.Random(1234)
        for _ in range(200):
            n = rng.randint(1, 20)
            values = [rng.uniform(0.0, 100.0) for _ in range(n)]
            j = jains_index(values)
            assert (1.0 / n) - 1e-9 <= j <= 1.0 + 1e-9

    def test_scale_invariance(self):
        # Jain's index is invariant under multiplying every value by a positive
        # constant (both numerator and denominator scale by k^2).
        base = [1.0, 2.0, 3.0, 4.0]
        scaled = [v * 7.5 for v in base]
        assert jains_index(base) == pytest.approx(jains_index(scaled))

    def test_shift_is_not_invariant(self):
        # Documented property: Jain's index is NOT shift-invariant. Adding a
        # constant to an unequal vector makes it look "fairer" (ratio of sums
        # approaches 1 as the additive constant dominates the original spread).
        base = [1.0, 2.0, 3.0]
        shifted = [v + 1000.0 for v in base]
        assert jains_index(shifted) > jains_index(base)
        assert jains_index(shifted) < 1.0  # still not perfectly equal


# =========================================================================== #
# gini                                                                         #
# =========================================================================== #
class TestGini:
    def test_all_equal_is_zero(self):
        assert gini([5.0, 5.0, 5.0]) == pytest.approx(0.0)

    def test_one_hot_hand_computed(self):
        # Hand-computed via the sorted-rank formula:
        # sorted=[0,0,0,10], n=4, weights (2i-n-1) for i=1..4: -3,-1,1,3
        # weighted sum = -3*0 -1*0 +1*0 +3*10 = 30; total=10 -> G=30/(4*10)=0.75.
        assert gini([10.0, 0.0, 0.0, 0.0]) == pytest.approx(0.75)

    def test_hand_computed_mixed_vector(self):
        # [1,2,3,4]: sorted=[1,2,3,4], n=4, weights -3,-1,1,3
        # weighted = -3*1 -1*2 +1*3 +3*4 = -3-2+3+12=10; total=10 -> G=10/(4*10)=0.25
        assert gini([1.0, 2.0, 3.0, 4.0]) == pytest.approx(0.25)

    def test_empty_is_zero(self):
        assert gini([]) == pytest.approx(0.0)

    def test_single_element_is_zero(self):
        assert gini([99.0]) == pytest.approx(0.0)

    def test_all_zero_is_zero(self):
        assert gini([0.0, 0.0, 0.0]) == pytest.approx(0.0)

    def test_negative_value_rejected(self):
        with pytest.raises(EmergencyMetricsError, match="negative"):
            gini([1.0, -1.0])

    def test_nan_rejected(self):
        with pytest.raises(EmergencyMetricsError, match="NaN/Inf"):
            gini([1.0, float("nan")])

    def test_does_not_mutate_input(self):
        values = [3.0, 1.0, 2.0]
        original = list(values)
        gini(values)
        assert values == original

    def test_bounds_property_random_vectors(self):
        rng = random.Random(4321)
        for _ in range(200):
            n = rng.randint(1, 20)
            values = [rng.uniform(0.0, 100.0) for _ in range(n)]
            g = gini(values)
            assert -1e-9 <= g <= 1.0 + 1e-9

    def test_scale_invariance(self):
        base = [1.0, 2.0, 3.0, 4.0]
        scaled = [v * 3.0 for v in base]
        assert gini(base) == pytest.approx(gini(scaled))

    def test_shift_is_not_invariant(self):
        # Adding a constant increases the mean but not the absolute spread, so
        # Gini strictly decreases (distribution looks more equal).
        base = [1.0, 2.0, 3.0, 100.0]
        shifted = [v + 1000.0 for v in base]
        assert gini(shifted) < gini(base)


# =========================================================================== #
# rawlsian_worst                                                               #
# =========================================================================== #
class TestRawlsianWorst:
    def test_matches_max(self):
        values = [3.0, 7.0, 2.0, 19.5]
        assert rawlsian_worst(values) == pytest.approx(max(values))

    def test_single_element(self):
        assert rawlsian_worst([42.0]) == pytest.approx(42.0)

    def test_empty_is_nan(self):
        assert math.isnan(rawlsian_worst([]))

    def test_negative_value_rejected(self):
        with pytest.raises(EmergencyMetricsError, match="negative"):
            rawlsian_worst([1.0, -5.0])

    def test_random_vectors_match_builtin_max(self):
        rng = random.Random(55)
        for _ in range(100):
            n = rng.randint(1, 50)
            values = [rng.uniform(0.0, 500.0) for _ in range(n)]
            assert rawlsian_worst(values) == pytest.approx(max(values))


# =========================================================================== #
# utilitarian_mean                                                             #
# =========================================================================== #
class TestUtilitarianMean:
    def test_hand_computed(self):
        assert utilitarian_mean([2.0, 4.0, 6.0]) == pytest.approx(4.0)

    def test_single_element(self):
        assert utilitarian_mean([10.0]) == pytest.approx(10.0)

    def test_empty_is_nan(self):
        assert math.isnan(utilitarian_mean([]))

    def test_all_zero(self):
        assert utilitarian_mean([0.0, 0.0]) == pytest.approx(0.0)

    def test_negative_value_rejected(self):
        with pytest.raises(EmergencyMetricsError, match="negative"):
            utilitarian_mean([1.0, -1.0])

    def test_matches_statistics_mean(self):
        rng = random.Random(9)
        values = [rng.uniform(0.0, 100.0) for _ in range(37)]
        assert utilitarian_mean(values) == pytest.approx(statistics.mean(values))


# =========================================================================== #
# p95                                                                          #
# =========================================================================== #
class TestP95:
    def test_hand_computed_linear_interpolation(self):
        # [1..10]: idx = 0.95*(10-1) = 8.55 -> between sorted[8]=9 and sorted[9]=10
        # frac=0.55 -> 9 + 0.55*(10-9) = 9.55
        values = [float(v) for v in range(1, 11)]
        assert p95(values) == pytest.approx(9.55)

    def test_single_element(self):
        assert p95([5.0]) == pytest.approx(5.0)

    def test_empty_is_nan(self):
        assert math.isnan(p95([]))

    def test_all_equal(self):
        assert p95([7.0, 7.0, 7.0, 7.0]) == pytest.approx(7.0)

    def test_unsorted_input_gives_same_result_as_sorted(self):
        values = [5.0, 1.0, 9.0, 3.0, 7.0, 2.0, 8.0, 4.0, 6.0, 10.0]
        assert p95(values) == pytest.approx(p95(sorted(values)))

    def test_negative_value_rejected(self):
        with pytest.raises(EmergencyMetricsError, match="negative"):
            p95([1.0, -1.0])

    def test_does_not_mutate_input(self):
        values = [5.0, 1.0, 3.0]
        original = list(values)
        p95(values)
        assert values == original

    def test_is_between_min_and_max(self):
        rng = random.Random(77)
        for _ in range(100):
            n = rng.randint(1, 50)
            values = [rng.uniform(0.0, 500.0) for _ in range(n)]
            result = p95(values)
            assert min(values) - 1e-9 <= result <= max(values) + 1e-9


# =========================================================================== #
# fairness_report -- "fairness across junctions"                               #
# =========================================================================== #
class TestFairnessReport:
    def test_realistic_small_mapping(self):
        # Three junctions; junction "C" is starved (much higher mean delay).
        group_delays = {
            "junctionA": [10.0, 12.0, 8.0],
            "junctionB": [11.0, 9.0, 10.0],
            "junctionC": [40.0, 45.0, 50.0],
        }
        # Means: A=10.0, B=10.0, C=45.0
        report = fairness_report(group_delays)
        assert report["n_groups"] == 3
        assert report["rawlsian_worst_group"] == pytest.approx(45.0)
        assert report["utilitarian_mean_group"] == pytest.approx((10.0 + 10.0 + 45.0) / 3)
        assert report["jain"] == pytest.approx(jains_index([10.0, 10.0, 45.0]))
        assert report["gini"] == pytest.approx(gini([10.0, 10.0, 45.0]))
        # Starved junction C should pull fairness well below 1 / equality below 0.
        assert report["jain"] < 1.0
        assert report["gini"] > 0.0

    def test_equal_junctions_are_perfectly_fair(self):
        group_delays = {"A": [10.0, 10.0], "B": [10.0, 10.0], "C": [10.0, 10.0]}
        report = fairness_report(group_delays)
        assert report["jain"] == pytest.approx(1.0)
        assert report["gini"] == pytest.approx(0.0)

    def test_empty_mapping_is_vacuously_fair(self):
        report = fairness_report({})
        assert report["n_groups"] == 0
        assert report["jain"] == pytest.approx(1.0)
        assert report["gini"] == pytest.approx(0.0)
        assert math.isnan(report["rawlsian_worst_group"])
        assert math.isnan(report["utilitarian_mean_group"])

    def test_group_with_empty_delay_list_rejected(self):
        with pytest.raises(EmergencyMetricsError, match="junctionX"):
            fairness_report({"junctionX": [], "junctionY": [5.0]})

    def test_group_with_negative_delay_rejected(self):
        with pytest.raises(EmergencyMetricsError, match="negative"):
            fairness_report({"junctionA": [1.0, -2.0]})

    def test_single_group_is_perfectly_fair(self):
        report = fairness_report({"only": [1.0, 2.0, 3.0]})
        assert report["n_groups"] == 1
        assert report["jain"] == pytest.approx(1.0)
        assert report["gini"] == pytest.approx(0.0)


# =========================================================================== #
# worst_case_report                                                            #
# =========================================================================== #
class TestWorstCaseReport:
    def test_realistic_small_list(self):
        delays = [5.0, 6.0, 7.0, 8.0, 100.0]
        report = worst_case_report(delays)
        assert report["n"] == 5
        assert report["max"] == pytest.approx(100.0)
        assert report["p95"] == pytest.approx(p95(delays))

    def test_empty_list(self):
        report = worst_case_report([])
        assert report["n"] == 0
        assert math.isnan(report["max"])
        assert math.isnan(report["p95"])

    def test_negative_value_rejected(self):
        with pytest.raises(EmergencyMetricsError, match="negative"):
            worst_case_report([1.0, -1.0])


# =========================================================================== #
# summarize -- convenience bundle                                              #
# =========================================================================== #
class TestSummarize:
    def test_realistic_small_mapping(self):
        group_delays = {
            "junctionA": [10.0, 12.0, 8.0],
            "junctionB": [11.0, 9.0, 10.0],
            "junctionC": [40.0, 45.0, 50.0],
        }
        result = summarize(group_delays)

        fr = fairness_report(group_delays)
        flattened = [10.0, 12.0, 8.0, 11.0, 9.0, 10.0, 40.0, 45.0, 50.0]
        wc = worst_case_report(flattened)

        for key, val in fr.items():
            assert result[key] == pytest.approx(val, nan_ok=True)
        for key, val in wc.items():
            assert result[key] == pytest.approx(val, nan_ok=True)
        assert result["utilitarian_mean_vehicle"] == pytest.approx(
            utilitarian_mean(flattened))
        # sanity: 9 vehicles total across 3 junctions.
        assert result["n"] == 9
        assert result["n_groups"] == 3

    def test_empty_mapping(self):
        result = summarize({})
        assert result["n_groups"] == 0
        assert result["n"] == 0
        assert result["jain"] == pytest.approx(1.0)
        assert math.isnan(result["utilitarian_mean_vehicle"])

    def test_keys_do_not_collide(self):
        # fairness_report's per-group mean and the per-vehicle mean must be
        # distinguishable keys in the merged dict. Use unequal group sizes so
        # mean-of-group-means and mean-of-all-vehicles are genuinely different
        # numbers (equal-size groups would make them coincide by arithmetic,
        # which would not actually prove the keys are independent).
        result = summarize({"A": [1.0], "B": [3.0, 4.0, 100.0]})
        assert "utilitarian_mean_group" in result
        assert "utilitarian_mean_vehicle" in result
        assert result["utilitarian_mean_group"] != result["utilitarian_mean_vehicle"]

    def test_propagates_negative_guard(self):
        with pytest.raises(EmergencyMetricsError, match="negative"):
            summarize({"A": [1.0, -1.0]})


# =========================================================================== #
# Immutability (organization-wide rule: never mutate inputs)                   #
# =========================================================================== #
class TestImmutability:
    def test_fairness_report_does_not_mutate_mapping_or_lists(self):
        group_delays = {"A": [3.0, 1.0, 2.0], "B": [5.0, 4.0]}
        snapshot = {k: list(v) for k, v in group_delays.items()}
        fairness_report(group_delays)
        assert group_delays == snapshot
        assert list(group_delays.keys()) == list(snapshot.keys())

    def test_summarize_does_not_mutate_mapping_or_lists(self):
        group_delays = {"A": [3.0, 1.0, 2.0], "B": [5.0, 4.0]}
        snapshot = {k: list(v) for k, v in group_delays.items()}
        summarize(group_delays)
        assert group_delays == snapshot

    def test_worst_case_report_does_not_mutate_list(self):
        delays = [9.0, 1.0, 5.0]
        original = list(delays)
        worst_case_report(delays)
        assert delays == original
