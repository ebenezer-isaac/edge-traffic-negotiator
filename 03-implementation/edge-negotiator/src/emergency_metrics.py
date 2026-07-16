"""System-level fairness and worst-case traffic metrics ("The Edge Negotiator").

Context: the supervisors asked for system-level trade-offs to be reported
alongside throughput -- specifically "fairness across junctions" and
"worst-case guarantees". A mean travel-time number can hide a controller that
optimises the average by starving one junction (or a handful of unlucky
vehicles) of green time. This module makes that trade-off visible.

Four fairness ideologies (traffic-signal-control fairness literature)
----------------------------------------------------------------------
  Jain's index     efficiency/closeness ideology: how close is the allocation
                   to being equal, scaled so 1.0 = perfectly equal.
  Gini coefficient egalitarian ideology: standard inequality measure from
                   welfare economics; 0.0 = perfect equality.
  Rawlsian worst   maximin ideology (Rawls' difference principle): judge the
                   system by its WORST-OFF member, not its average.
  Utilitarian mean classic aggregate-welfare ideology: judge the system by
                   its mean outcome (what a plain average already reports,
                   included here so all four ideologies are reported side by
                   side from the same helper).

Plus a worst-case (tail) report: the maximum and 95th-percentile individual
vehicle delay, which is the "worst-case guarantee" a fairness-across-groups
number alone cannot show (a system can be fair across junctions while still
producing individual vehicles with catastrophic delay).

Design
------
Pure functions of plain ``list[float]`` / ``dict[str, list[float]]`` values.
No SUMO, no TraCI, no I/O: everything here is unit-testable on hand-computed
vectors (see tests/test_emergency_metrics.py). No dependency beyond the
Python standard library.

Immutability: nothing here mutates its inputs. Any internal sorting is done
on a new list (``sorted(values)`` never touches the caller's list in place).

Non-negativity convention
--------------------------
All values fed to these functions are assumed to be delays (seconds), which
are physically non-negative. Every function validates its input at the
boundary and raises ``EmergencyMetricsError`` on a negative, non-finite
(NaN/Inf), or non-numeric value, rather than silently producing a misleading
number. This mirrors the "never trust external data" boundary-validation
convention used elsewhere in this codebase (see src/metrics.py).

Empty-input convention
-----------------------
An empty list has no disagreement to measure, so the two RELATIVE fairness
metrics are defined as the vacuously-fair value:
  jains_index([]) == 1.0     (see also: jains_index([0, 0, ...]) == 1.0)
  gini([])        == 0.0     (see also: gini([0, 0, ...]) == 0.0)
The two ABSOLUTE (unit-bearing) metrics have no defined value over zero
observations, so they follow this repo's existing NaN-for-undefined
convention (see metrics.completion_rate) rather than silently returning 0.0,
which would be indistinguishable from a genuine zero-delay observation:
  rawlsian_worst([]) is NaN
  utilitarian_mean([]) is NaN
  p95([]) is NaN
"""
from __future__ import annotations

import math
from typing import Dict, List

__all__ = [
    "EmergencyMetricsError",
    "jains_index",
    "gini",
    "rawlsian_worst",
    "utilitarian_mean",
    "p95",
    "fairness_report",
    "worst_case_report",
    "summarize",
]


class EmergencyMetricsError(ValueError):
    """Raised when an input delay value is malformed or violates an invariant
    (non-numeric, NaN/Inf, or negative)."""


def _validate_values(values: List[float], context: str) -> None:
    """Boundary validation: every element must be a finite, non-negative
    real number. Never trust external data (see repo security rules).

    Raises ``EmergencyMetricsError`` naming the offending index/value/context
    so a caller can trace which group or report triggered it.
    """
    for i, v in enumerate(values):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise EmergencyMetricsError(
                f"{context}: element {i} is not numeric: {v!r}")
        fv = float(v)
        if math.isnan(fv) or math.isinf(fv):
            raise EmergencyMetricsError(
                f"{context}: element {i} is NaN/Inf: {v!r}")
        if fv < 0.0:
            raise EmergencyMetricsError(
                f"{context}: element {i} is negative ({v!r}); "
                f"delays must be >= 0")


# ---------------------------------------------------------------------------
# The four fairness ideologies
# ---------------------------------------------------------------------------
def jains_index(values: List[float]) -> float:
    """Jain's fairness index (Jain, Chiu & Hawe, 1984): the efficiency/
    closeness ideology.

    Formula: J(x) = (sum x_i)^2 / (n * sum x_i^2)

    Range: J in [1/n, 1] for n non-negative values.
      * J == 1.0            all values equal (perfectly fair).
      * J == 1/n            one value holds everything, the rest are zero
                            (one-hot; the worst case for a fixed n).
    Scale-invariant: multiplying every value by the same positive constant
    leaves J unchanged. NOT shift-invariant: adding a constant to every
    value moves J towards 1.0 (see tests for the property test that pins
    this down precisely).

    Convention: empty input and all-zero input both return 1.0 ("vacuously"
    / "perfectly" fair respectively -- see module docstring), rather than
    raising a ZeroDivisionError.
    """
    if not values:
        return 1.0
    _validate_values(values, "jains_index")
    n = len(values)
    total = sum(values)
    if total == 0.0:
        # All values are zero (non-negative + sum==0 implies every element
        # is zero): defined as perfectly fair, not undefined.
        return 1.0
    sum_sq = sum(v * v for v in values)
    return (total * total) / (n * sum_sq)


def gini(values: List[float]) -> float:
    """Gini coefficient (Gini, 1912): the egalitarian ideology.

    Formula used here is the efficient sorted-rank form, which is
    mathematically equivalent to the standard mean-absolute-difference
    definition G = sum_i sum_j |x_i - x_j| / (2 * n^2 * mean(x)):

        G = sum_{i=1}^{n} (2*i - n - 1) * x_(i)  /  (n * sum(x))

    where x_(i) is the i-th smallest value (1-indexed rank, ascending sort).
    This form is O(n log n) (one sort) instead of O(n^2) (all pairs) and
    gives identical results.

    Range: G in [0, 1). G == 0.0 means perfect equality; higher values mean
    more concentrated inequality (G approaches (n-1)/n, its maximum for a
    fixed n, when one value holds everything and the rest are zero).
    Scale-invariant (like Jain's index); NOT shift-invariant -- adding a
    constant to every value strictly decreases G (raises the mean without
    changing the absolute spread).

    Convention: empty input and all-zero input both return 0.0 (no
    inequality to measure / a mean of zero would otherwise divide by zero).
    """
    if not values:
        return 0.0
    _validate_values(values, "gini")
    n = len(values)
    total = sum(values)
    if total == 0.0:
        return 0.0
    sorted_vals = sorted(values)
    weighted = sum(
        (2 * i - n - 1) * v for i, v in enumerate(sorted_vals, start=1))
    return weighted / (n * total)


def rawlsian_worst(values: List[float]) -> float:
    """Rawlsian (maximin) worst-case metric: John Rawls' difference
    principle -- judge a distribution by its WORST-OFF member, not its
    average.

    Formula: max(x)

    Convention: undefined (NaN) for an empty list -- there is no worst-off
    member to report, and returning 0.0 would be indistinguishable from a
    genuine zero-delay observation.
    """
    if not values:
        return math.nan
    _validate_values(values, "rawlsian_worst")
    return float(max(values))


def utilitarian_mean(values: List[float]) -> float:
    """Utilitarian metric: the classic aggregate/sum-maximising ideology --
    judge a distribution by its mean outcome.

    Formula: mean(x) = sum(x) / n

    Convention: undefined (NaN) for an empty list (0/0).
    """
    if not values:
        return math.nan
    _validate_values(values, "utilitarian_mean")
    return sum(values) / len(values)


# ---------------------------------------------------------------------------
# Worst-case (tail) metric
# ---------------------------------------------------------------------------
def p95(values: List[float]) -> float:
    """95th-percentile worst-case tail delay.

    Method: linear interpolation between the two closest ranks (the same
    convention as numpy's default ``'linear'`` method / Excel's
    ``PERCENTILE.INC``), computed on a copy sorted ascending:

        idx = 0.95 * (n - 1)
        result = sorted(x)[floor(idx)] +
                 (idx - floor(idx)) * (sorted(x)[ceil(idx)] - sorted(x)[floor(idx)])

    For n == 1 the single value is returned directly. Convention: undefined
    (NaN) for an empty list.
    """
    if not values:
        return math.nan
    _validate_values(values, "p95")
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])
    idx = 0.95 * (n - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return float(sorted_vals[lo])
    frac = idx - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


# ---------------------------------------------------------------------------
# Report bundles
# ---------------------------------------------------------------------------
def fairness_report(group_delays: Dict[str, List[float]]) -> Dict[str, float]:
    """"Fairness across junctions" (or any grouping, e.g. per-movement):
    computes each group's MEAN delay, then reports all four fairness
    ideologies over that vector of per-group means.

    A group is meant to represent one junction (or movement); its mean delay
    is the single number that stands in for "how that group is doing", and
    the fairness ideologies then compare those per-group numbers to each
    other -- NOT the raw per-vehicle delays (that comparison is
    ``worst_case_report``'s job).

    Args:
        group_delays: {group_name: [per-vehicle delay, ...]}. A group with
            an empty delay list has an undefined mean and is REJECTED
            (raises EmergencyMetricsError) rather than silently contributing
            a NaN into the fairness computation -- callers should filter out
            empty groups (e.g. junctions with zero traffic in the window)
            before calling this.

    Returns:
        {
          "jain": Jain's index over the per-group means,
          "gini": Gini coefficient over the per-group means,
          "rawlsian_worst_group": max per-group mean (the worst-off group),
          "utilitarian_mean_group": mean of the per-group means,
          "n_groups": number of groups,
        }

    An empty mapping (n_groups == 0) is the vacuous case: jain=1.0, gini=0.0,
    and the two absolute metrics are NaN (see module docstring).
    """
    group_means: List[float] = []
    for name, delays in group_delays.items():
        if not delays:
            raise EmergencyMetricsError(
                f"fairness_report: group {name!r} has no delay values "
                f"(mean is undefined); filter out empty groups before calling")
        _validate_values(delays, f"fairness_report[{name!r}]")
        group_means.append(sum(delays) / len(delays))

    return {
        "jain": jains_index(group_means),
        "gini": gini(group_means),
        "rawlsian_worst_group": rawlsian_worst(group_means),
        "utilitarian_mean_group": utilitarian_mean(group_means),
        "n_groups": len(group_means),
    }


def worst_case_report(per_vehicle_delays: List[float]) -> Dict[str, float]:
    """"Worst-case guarantee" over individual vehicles (not groups): the
    tail of the per-vehicle delay distribution.

    Args:
        per_vehicle_delays: one delay value per vehicle.

    Returns:
        {"max": ..., "p95": ..., "n": number of vehicles}

    Empty input: max/p95 are NaN (undefined), n is 0.
    """
    return {
        "max": rawlsian_worst(per_vehicle_delays),
        "p95": p95(per_vehicle_delays),
        "n": len(per_vehicle_delays),
    }


def summarize(group_delays: Dict[str, List[float]]) -> Dict[str, float]:
    """Convenience bundle: fairness across groups PLUS worst-case and mean
    over all individual vehicles, in one dict.

    Merges:
      * ``fairness_report(group_delays)``                      (per-group)
      * ``worst_case_report(flattened per-vehicle delays)``    (per-vehicle)
      * ``utilitarian_mean`` over the same flattened per-vehicle delays,
        under the key ``"utilitarian_mean_vehicle"`` -- distinct from
        ``fairness_report``'s ``"utilitarian_mean_group"`` so the two mean
        conventions (mean-of-group-means vs. mean-of-all-vehicles) never
        collide in the merged dict.

    Raises whatever ``fairness_report`` raises (e.g. an empty group's delay
    list, or a negative/non-finite delay anywhere).
    """
    report = dict(fairness_report(group_delays))

    flattened: List[float] = [
        delay for delays in group_delays.values() for delay in delays
    ]
    report.update(worst_case_report(flattened))
    report["utilitarian_mean_vehicle"] = utilitarian_mean(flattened)
    return report
