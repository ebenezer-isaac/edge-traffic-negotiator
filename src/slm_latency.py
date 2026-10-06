"""Per-job SLM latency profiling (MASTER-SPEC §8 latency paragraph / §12 D-lat).

Latencies are BIMODAL: the short jobs (``choose_phase``, Job-B ``classify_case``)
versus the long Job-A ``reason_note``/``reason_note_cag`` (tens-of-seconds class).
Each job is profiled separately and reported as ``{n, min, P50, P95, P99, max,
mean}`` using the FLPerformance NEAREST-RANK percentile (Lee Stott, FLPerformance
``src/server/benchmark.js::calculatePercentile``), NOT linear interpolation.

Nearest-rank formula: ``index = ceil((p/100) * N) - 1`` over the ascending-sorted
successful-call samples, clamped to ``[0, N-1]``. FLPerformance does NOT discard
cold-start warmup calls (its one gap; our April flperformance-analysis measured the
contamination), so we discard ``W >= 1`` warmup samples per job and state N and W.

Small-N caveat: at N < 100 the P99 nearest-rank index collapses to the LAST sample,
so P99 == max — Job-A P99 at small N is effectively the observed maximum. Report N
and W so this is legible.

TTFT/tokens-per-sec are reported ONLY where the endpoint exposes them; otherwise
recorded absent, NEVER fabricated (``usage_tps`` returns None when ``resp`` carries
no ``usage``).
"""
from __future__ import annotations

import math

__all__ = ["nearest_rank_percentile", "summarize_latency", "usage_tps"]


def nearest_rank_percentile(sorted_vals, p: float) -> float:
    """FLPerformance nearest-rank percentile of an ASCENDING-sorted sequence.

    ``index = ceil((p/100) * N) - 1``, clamped to ``[0, N-1]``. ``p`` in [0, 100].
    Raises on an empty input (an empty distribution has no percentile — fail loud
    rather than return a fabricated 0/NaN a caller might report as a real latency).
    """
    vals = list(sorted_vals)
    n = len(vals)
    if n == 0:
        raise ValueError("nearest_rank_percentile: empty sample (no percentile exists)")
    if not 0 <= p <= 100:
        raise ValueError(f"percentile p must be in [0, 100], got {p}")
    idx = math.ceil((p / 100.0) * n) - 1
    idx = max(0, min(idx, n - 1))
    return vals[idx]


def summarize_latency(samples_s, warmup: int = 1) -> dict:
    """Summarise per-call latencies (seconds) after discarding ``warmup`` cold starts.

    Returns ``{n, warmup_discarded, min, p50, p95, p99, max, mean, method}`` over the
    RETAINED samples. ``n`` is the retained count (post-warmup). If discarding warmup
    leaves nothing, returns an all-None summary with the counts so the caller can
    report "no measurable samples" rather than crash or fabricate.
    """
    raw = list(samples_s)
    warmup = max(0, int(warmup))
    discarded = min(warmup, len(raw))
    retained = raw[warmup:] if warmup < len(raw) else []
    method = "FLPerformance nearest-rank (index=ceil(p/100*N)-1); warmup discarded"
    if not retained:
        return {"n": 0, "warmup_discarded": discarded, "min": None, "p50": None,
                "p95": None, "p99": None, "max": None, "mean": None, "method": method}
    s = sorted(retained)
    n = len(s)
    return {
        "n": n,
        "warmup_discarded": discarded,
        "min": s[0],
        "p50": nearest_rank_percentile(s, 50),
        "p95": nearest_rank_percentile(s, 95),
        "p99": nearest_rank_percentile(s, 99),
        "max": s[-1],
        "mean": sum(s) / n,
        "method": method,
    }


def usage_tps(resp, latency_s: float):
    """Tokens/sec from an OpenAI-style response, or None if usage is absent.

    Guarded by ``getattr(resp, "usage", None)`` and a positive ``latency_s`` — never
    fabricates a rate when the endpoint did not report ``completion_tokens`` (§8:
    "record them absent, never fabricated").
    """
    usage = getattr(resp, "usage", None)
    if usage is None:
        return None
    completion = getattr(usage, "completion_tokens", None)
    if completion is None and isinstance(usage, dict):
        completion = usage.get("completion_tokens")
    if not isinstance(completion, (int, float)) or completion <= 0:
        return None
    if not isinstance(latency_s, (int, float)) or latency_s <= 0:
        return None
    return completion / latency_s
