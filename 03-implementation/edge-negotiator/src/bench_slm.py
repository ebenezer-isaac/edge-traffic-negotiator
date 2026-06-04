"""bench_slm.py — DE-RISK benchmark for the Edge Negotiator SLM-in-the-loop design.

Measures two things with hard data, against whatever model Foundry Local currently
serves (discovered via SLMAgent / the /v1/models endpoint):

  1. LATENCY: per-call ``choose_phase`` wall-clock latency over a battery of varied
     queue inputs (>=50 calls). Reports median / p95 / max to confirm or refute the
     brief's "Foundry Local serialises calls ~2-8s each" assumption and whether it
     fits the event-gated ~10s decision interval with headroom.

  2. DECISION QUALITY: a fixed, seeded battery of synthetic junction states each with
     a KNOWN optimal phase (argmax of the per-phase halting queue). Reports
     parse-success rate (a valid {"phase":N} was returned, not None) and
     agreement-with-argmax-queue rate. This is the model-agnostic ablation signal.

Usage (model must already be loaded in Foundry Local; this script does NOT switch
models — the orchestrator loads each model then calls this with --tag):

    .venv/Scripts/python src/bench_slm.py --calls 60 --tag phi-4-mini --out results/_phi.json

Honest by construction: every call is timed and recorded; None results count as
parse failures; ties in the optimal phase are handled (any argmax index counts as
correct). No fabrication — if the endpoint errors, latencies/None are recorded as-is.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from dataclasses import dataclass, field

from slm_agent import SLMAgent


@dataclass(frozen=True)
class Case:
    """One synthetic junction state with its known-optimal (argmax-queue) phases."""
    junction_id: str
    halting: tuple[int, ...]

    @property
    def num_phases(self) -> int:
        return len(self.halting)

    @property
    def optimal_phases(self) -> frozenset[int]:
        """All argmax indices (ties => any of them is correct)."""
        top = max(self.halting)
        return frozenset(i for i, n in enumerate(self.halting) if n == top)


def build_battery(seed: int = 20240604) -> list[Case]:
    """Fixed, reproducible battery of junction states with a clear argmax phase.

    Mixes hand-picked unambiguous cases (clear single winner) with seeded random
    cases across 2-, 3-, and 4-phase junctions and a range of queue magnitudes.
    Random cases are re-rolled until they have a UNIQUE argmax, so "agreement with
    argmax" is a clean, unambiguous correctness signal (no tie ambiguity).
    """
    cases: list[Case] = [
        # Unambiguous, hand-picked — clear longest queue.
        Case("J-clear-2a", (9, 0)),
        Case("J-clear-2b", (0, 11)),
        Case("J-clear-2c", (12, 3)),
        Case("J-clear-3a", (1, 8, 2)),
        Case("J-clear-3b", (2, 1, 14)),
        Case("J-clear-3c", (10, 2, 1)),
        Case("J-clear-4a", (1, 2, 13, 3)),
        Case("J-clear-4b", (15, 1, 2, 4)),
        Case("J-clear-4c", (2, 3, 1, 17)),
        Case("J-clear-4d", (3, 11, 2, 1)),
        # Near-ties but still a unique winner (margin of 1) — harder discrimination.
        Case("J-margin-2a", (6, 5)),
        Case("J-margin-3a", (7, 8, 6)),
        Case("J-margin-4a", (5, 6, 4, 7)),
        # All-equal-but-one-low edge (winner still unique).
        Case("J-edge-3a", (4, 4, 5)),
    ]
    rng = random.Random(seed)
    n_random = 40  # battery >= 50 distinct states with the hand-picked ones above
    for k in range(n_random):
        nph = rng.choice([2, 2, 3, 3, 4])  # 2/3/4-phase, weighted toward small
        while True:
            q = tuple(rng.randint(0, 20) for _ in range(nph))
            top = max(q)
            if sum(1 for n in q if n == top) == 1:  # unique argmax
                break
        cases.append(Case(f"J-rand-{k:02d}-{nph}p", q))
    return cases


@dataclass
class CallResult:
    case_id: str
    halting: tuple[int, ...]
    optimal: tuple[int, ...]
    chosen: int | None
    latency_s: float
    parsed_ok: bool
    agrees: bool


@dataclass
class BenchSummary:
    tag: str
    model_id: str
    base_url: str
    n_calls: int
    latency_median_s: float
    latency_p95_s: float
    latency_max_s: float
    latency_min_s: float
    latency_mean_s: float
    parse_success_pct: float
    argmax_agreement_pct: float
    results: list[CallResult] = field(default_factory=list)


def _percentile(sorted_vals: list[float], pct: float) -> float:
    """Nearest-rank percentile (pct in [0,100]); robust for small n."""
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = pct / 100.0 * (len(sorted_vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = rank - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def run_bench(tag: str, calls: int, seed: int) -> BenchSummary:
    agent = SLMAgent()  # auto-discovers endpoint + currently-loaded model
    battery = build_battery(seed)
    # If asked for more calls than the battery has, cycle through it (deterministic).
    plan = [battery[i % len(battery)] for i in range(max(calls, len(battery)))]

    results: list[CallResult] = []
    for case in plan:
        t0 = time.perf_counter()
        chosen = agent.choose_phase(case.junction_id, case.num_phases, list(case.halting))
        dt = time.perf_counter() - t0
        parsed_ok = chosen is not None
        agrees = parsed_ok and chosen in case.optimal_phases
        results.append(CallResult(
            case_id=case.junction_id, halting=case.halting,
            optimal=tuple(sorted(case.optimal_phases)), chosen=chosen,
            latency_s=dt, parsed_ok=parsed_ok, agrees=agrees,
        ))

    lats = sorted(r.latency_s for r in results)
    n = len(results)
    n_parsed = sum(r.parsed_ok for r in results)
    n_agree = sum(r.agrees for r in results)
    return BenchSummary(
        tag=tag,
        model_id=agent.model,
        base_url=str(agent.client.base_url),
        n_calls=n,
        latency_median_s=statistics.median(lats),
        latency_p95_s=_percentile(lats, 95),
        latency_max_s=max(lats),
        latency_min_s=min(lats),
        latency_mean_s=statistics.fmean(lats),
        parse_success_pct=100.0 * n_parsed / n if n else 0.0,
        argmax_agreement_pct=100.0 * n_agree / n if n else 0.0,
        results=results,
    )


def _summary_to_dict(s: BenchSummary) -> dict:
    return {
        "tag": s.tag, "model_id": s.model_id, "base_url": s.base_url,
        "n_calls": s.n_calls,
        "latency_s": {
            "median": s.latency_median_s, "p95": s.latency_p95_s,
            "max": s.latency_max_s, "min": s.latency_min_s, "mean": s.latency_mean_s,
        },
        "parse_success_pct": s.parse_success_pct,
        "argmax_agreement_pct": s.argmax_agreement_pct,
        "results": [
            {
                "case_id": r.case_id, "halting": list(r.halting),
                "optimal": list(r.optimal), "chosen": r.chosen,
                "latency_s": r.latency_s, "parsed_ok": r.parsed_ok, "agrees": r.agrees,
            }
            for r in s.results
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--calls", type=int, default=60,
                    help="number of timed choose_phase calls (>=50 for the latency dist)")
    ap.add_argument("--tag", default="active",
                    help="human label for the currently-loaded model (e.g. phi-4-mini)")
    ap.add_argument("--seed", type=int, default=20240604)
    ap.add_argument("--out", default=None, help="write the raw JSON summary here")
    args = ap.parse_args()

    s = run_bench(args.tag, args.calls, args.seed)

    print(f"[{s.tag}] model_id={s.model_id}")
    print(f"  base_url={s.base_url}")
    print(f"  calls={s.n_calls}")
    print(f"  latency_s: median={s.latency_median_s:.3f} p95={s.latency_p95_s:.3f} "
          f"max={s.latency_max_s:.3f} min={s.latency_min_s:.3f} mean={s.latency_mean_s:.3f}")
    print(f"  parse_success={s.parse_success_pct:.1f}%  "
          f"argmax_agreement={s.argmax_agreement_pct:.1f}%")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(_summary_to_dict(s), f, indent=2)
        print(f"  wrote {args.out}")


if __name__ == "__main__":
    main()
