"""Fault-finding tests for per-job SLM latency profiling (§8 / §12 D-lat).

PURE: no Foundry. These pin the FLPerformance NEAREST-RANK formula against
hand-computed values (including the N<100 P99==max collapse), the warmup discard,
and that ``usage_tps`` NEVER fabricates a rate when the response carries no usage.
"""
import math
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import pytest  # noqa: E402

from slm_latency import (nearest_rank_percentile, summarize_latency,  # noqa: E402
                         usage_tps)


# --------------------------------------------------------------------------- #
# 1. Nearest-rank formula: exact hand-computed values (NOT linear interpolation).
#    index = ceil(p/100 * N) - 1, clamped to [0, N-1].
# --------------------------------------------------------------------------- #

def test_nearest_rank_exact_values_n5():
    vals = [10, 20, 30, 40, 50]  # n=5, already sorted
    # p50: ceil(0.50*5)-1 = 3-1 = 2 -> vals[2]
    assert nearest_rank_percentile(vals, 50) == 30
    # p95: ceil(0.95*5)-1 = 5-1 = 4 -> vals[4]
    assert nearest_rank_percentile(vals, 95) == 50
    # a linear-interp p50 over this set would be 30 too, so pin an asymmetric case:
    # p90: ceil(0.90*5)-1 = 5-1 = 4 -> vals[4]=50 (nearest-rank), whereas linear
    # interpolation would give 46 — proving this is NOT linear-interp.
    assert nearest_rank_percentile(vals, 90) == 50


def test_nearest_rank_clamps_low_and_high():
    vals = [1, 2, 3, 4, 5]
    # p0: ceil(0)-1 = -1 -> clamped to 0
    assert nearest_rank_percentile(vals, 0) == 1
    # p100: ceil(5)-1 = 4 -> last element
    assert nearest_rank_percentile(vals, 100) == 5


def test_nearest_rank_p99_collapses_to_max_when_n_below_100():
    # THE small-N caveat: at N<100 the P99 index == N-1, so P99 == observed max.
    for n in (5, 10, 50, 99):
        vals = list(range(1, n + 1))  # ascending
        idx = math.ceil(0.99 * n) - 1
        assert idx == n - 1  # index is the last sample
        assert nearest_rank_percentile(vals, 99) == vals[-1] == max(vals)


def test_nearest_rank_p99_distinct_from_max_at_n100():
    # At N>=100 the P99 index is strictly below the last, so P99 != max in general.
    vals = list(range(1, 101))  # n=100
    # p99: ceil(99)-1 = 98 -> vals[98] = 99 (not the max 100)
    assert nearest_rank_percentile(vals, 99) == 99
    assert nearest_rank_percentile(vals, 99) != max(vals)


def test_nearest_rank_single_sample():
    assert nearest_rank_percentile([7.0], 50) == 7.0
    assert nearest_rank_percentile([7.0], 99) == 7.0


def test_nearest_rank_empty_fails_loud():
    with pytest.raises(ValueError):
        nearest_rank_percentile([], 50)


def test_nearest_rank_rejects_out_of_range_p():
    with pytest.raises(ValueError):
        nearest_rank_percentile([1, 2, 3], 150)


# --------------------------------------------------------------------------- #
# 2. summarize_latency: warmup discard + the reported shape.
# --------------------------------------------------------------------------- #

def test_summarize_discards_warmup():
    # the first (cold-start) sample is huge; W=1 must drop it before percentiles.
    samples = [999.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    out = summarize_latency(samples, warmup=1)
    assert out["warmup_discarded"] == 1
    assert out["n"] == 5                     # 6 - 1 warmup
    assert out["min"] == 1.0                 # the 999 cold start is gone
    assert out["max"] == 5.0
    assert out["p50"] == 3.0                 # ceil(0.5*5)-1 = 2 -> sorted[2]
    assert out["mean"] == pytest.approx(3.0)
    assert "nearest-rank" in out["method"]


def test_summarize_warmup_zero_keeps_all():
    out = summarize_latency([5.0, 1.0, 3.0], warmup=0)
    assert out["warmup_discarded"] == 0
    assert out["n"] == 3
    assert out["min"] == 1.0


def test_summarize_sorts_before_percentiles():
    # unsorted input must be sorted internally, not assumed pre-sorted.
    out = summarize_latency([5.0, 4.0, 3.0, 2.0, 1.0], warmup=0)
    assert out["min"] == 1.0 and out["max"] == 5.0
    assert out["p50"] == 3.0


def test_summarize_all_discarded_returns_none_not_crash():
    out = summarize_latency([42.0], warmup=1)   # nothing left after warmup
    assert out["n"] == 0
    assert out["warmup_discarded"] == 1
    assert out["p50"] is None and out["max"] is None and out["mean"] is None


def test_summarize_p99_equals_max_small_n():
    out = summarize_latency([1.0, 2.0, 3.0, 4.0, 5.0], warmup=0)  # n=5
    assert out["p99"] == out["max"] == 5.0


# --------------------------------------------------------------------------- #
# 3. usage_tps: NEVER fabricate — None when usage is absent or unusable.
# --------------------------------------------------------------------------- #

class _RespNoUsage:
    pass


class _Usage:
    def __init__(self, completion_tokens):
        self.completion_tokens = completion_tokens


class _RespWithUsage:
    def __init__(self, completion_tokens):
        self.usage = _Usage(completion_tokens)


class _RespDictUsage:
    def __init__(self, completion_tokens):
        self.usage = {"completion_tokens": completion_tokens}


def test_usage_tps_none_when_no_usage():
    assert usage_tps(_RespNoUsage(), 2.0) is None


def test_usage_tps_computes_when_present():
    assert usage_tps(_RespWithUsage(100), 2.0) == pytest.approx(50.0)


def test_usage_tps_dict_usage_supported():
    assert usage_tps(_RespDictUsage(60), 3.0) == pytest.approx(20.0)


def test_usage_tps_none_on_zero_or_negative_latency():
    assert usage_tps(_RespWithUsage(100), 0.0) is None
    assert usage_tps(_RespWithUsage(100), -1.0) is None


def test_usage_tps_none_on_missing_completion_tokens():
    assert usage_tps(_RespWithUsage(None), 2.0) is None
    assert usage_tps(_RespWithUsage(0), 2.0) is None
