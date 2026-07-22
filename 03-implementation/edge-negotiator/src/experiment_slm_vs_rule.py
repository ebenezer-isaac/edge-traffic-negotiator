"""Experiment 1: characterize the edge SLM against a reference rule on flagged
ambiguous cases (see specs/001-edge-negotiator/experiment-1-slm-vs-rule.md).

This is a CHARACTERIZATION, not a competition. The well-tuned deterministic rule
(``RuleDisambiguator``) is a yardstick; the SLM (Phi-4-mini via Foundry Local) is
measured against it on identical labelled cases. A clean null (the rule suffices)
is a valid finding. Results are always reported PER SPLIT (anticipated vs novel),
never pooled: the rule is tuned on the anticipated split, so parity there is
expected; the novel split (held-out feature combinations plus genuinely new event
types) is where a frozen, no-retraining reasoner could differ.

Two run modes:
  * rule-only (default): tunes and scores the rule. NO Foundry needed, runs now.
  * --with-slm: also scores the real SLM and measures its temperature-0
    determinism on the novel split. Needs Foundry Local up (`foundry service
    start` + load phi-4-mini).

    python src/experiment_slm_vs_rule.py                 # rule baseline (now)
    python src/experiment_slm_vs_rule.py --with-slm      # + real Phi-4-mini
    python src/experiment_slm_vs_rule.py --with-slm --determinism-reps 5
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from time import perf_counter

import ambiguous_decision as ad
from slm_latency import summarize_latency

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.normpath(os.path.join(HERE, "..", "results"))


class _SLMDecider:
    """Wraps SLMAgent.classify_case as a Decision decider. An unparseable or
    failed answer is counted and mapped to REJECT (the safe, no-preemption
    default), so a broken model never fabricates a preemption."""

    def __init__(self, agent):
        self.agent = agent
        self.parse_failures = 0
        self.calls = 0
        self.latencies_s: list = []  # per-call Job-B wall-clock (§8 latency profiling)

    def decide(self, case) -> str:
        self.calls += 1
        t0 = perf_counter()
        out = self.agent.classify_case(case)
        self.latencies_s.append(perf_counter() - t0)
        if out is None:
            self.parse_failures += 1
            return ad.REJECT
        return out


def _determinism(agent, cases, reps: int) -> dict:
    """Temperature-0 run-to-run agreement of the SLM on ``cases``: the fraction
    of cases whose decision is identical across all ``reps`` calls."""
    if reps < 2:
        return {"reps": reps, "note": "determinism needs reps >= 2"}
    stable = 0
    for c in cases:
        seen = {agent.classify_case(c) for _ in range(reps)}
        if len(seen) == 1:
            stable += 1
    return {"reps": reps, "n_cases": len(cases),
            "agreement_pct": round(100.0 * stable / len(cases), 1) if cases else None}


def _probe_foundry():
    """Return an SLMAgent if the real-model precondition holds, else (None, reason).

    Reuses the SHARED ``slm_agent.probe_foundry_determinism`` so this path's SKIP
    now covers BOTH reachability AND temp-0 determinism (it previously only
    checked reachability). SKIP-not-abort: never raises. The import failure is
    still caught locally so an absent ``slm_agent`` degrades to a skip too."""
    try:
        from slm_agent import probe_foundry_determinism
    except Exception as exc:
        return None, f"import failed: {type(exc).__name__}: {exc}"
    return probe_foundry_determinism()


def run(with_slm: bool = False, seed: int = 0, determinism_reps: int = 5) -> dict:
    cases = ad.generate_dataset(seed=seed)
    anticipated = [c for c in cases if c.split == "anticipated"]

    # The rule is tuned on the ANTICIPATED split only, then scored on everything.
    rule = ad.RuleDisambiguator().tune(anticipated)
    rule_scores = ad.evaluate(rule, cases)

    out = {
        "experiment": "slm_vs_rule_characterization",
        "seed": seed,
        "n_cases": len(cases),
        "n_anticipated": len(anticipated),
        "n_novel": len(cases) - len(anticipated),
        "rule_thresholds": {"corr_k": rule.corr_k, "residual_max": rule.residual_max,
                            "persistence_p": rule.persistence_p,
                            "agreement_min": rule.agreement_min},
        "rule": rule_scores,
    }

    if with_slm:
        agent, reason = _probe_foundry()
        if agent is None:
            out["slm"] = {"skipped": True, "reason": reason}
        else:
            decider = _SLMDecider(agent)
            out["slm"] = ad.evaluate(decider, cases)
            out["slm"]["parse_failures"] = decider.parse_failures
            out["slm"]["calls"] = decider.calls
            out["slm"]["model"] = agent.model
            # Job-B per-call latency (§8, FLPerformance nearest-rank, W=1 warmup).
            out["slm"]["job_b_latency"] = summarize_latency(decider.latencies_s, warmup=1)
            novel = [c for c in cases if c.split == "novel"]
            out["slm_determinism_novel"] = _determinism(agent, novel, determinism_reps)

    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, "experiment1_slm_vs_rule.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    _print_summary(out, path)
    return out


def _fmt(block: dict, key: str) -> str:
    s = block.get(key, {})
    return (f"acc={s.get('accuracy')}, F1={s.get('f1')}, "
            f"false_preempt={s.get('false_preemption_rate')}")


def _print_summary(out: dict, path: str) -> None:
    print("=" * 72)
    print("Experiment 1: SLM vs reference rule (characterization, per split)")
    print(f"  dataset: {out['n_cases']} cases "
          f"({out['n_anticipated']} anticipated, {out['n_novel']} novel), seed={out['seed']}")
    print(f"  rule thresholds (tuned on anticipated): {out['rule_thresholds']}")
    print("-" * 72)
    print("  RULE (the yardstick):")
    for split in ("anticipated", "novel", "overall"):
        print(f"    {split:12s} {_fmt(out['rule'], split)}")
    if "slm" in out:
        if out["slm"].get("skipped"):
            print(f"  SLM: SKIPPED, {out['slm']['reason']}")
        else:
            print(f"  SLM ({out['slm'].get('model')}), "
                  f"parse_failures={out['slm'].get('parse_failures')}/{out['slm'].get('calls')}:")
            for split in ("anticipated", "novel", "overall"):
                print(f"    {split:12s} {_fmt(out['slm'], split)}")
            det = out.get("slm_determinism_novel", {})
            print(f"  SLM determinism (novel, temp 0): {det.get('agreement_pct')}% "
                  f"identical over {det.get('reps')} reps")
            lat = out["slm"].get("job_b_latency", {})
            if lat.get("n"):
                print(f"  SLM Job-B latency (§8 nearest-rank, n={lat['n']}, warmup "
                      f"{lat['warmup_discarded']}): P50={lat['p50']:.3f}s "
                      f"P95={lat['p95']:.3f}s P99={lat['p99']:.3f}s max={lat['max']:.3f}s")
    print("=" * 72)
    print(f"  written: {path}")


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Experiment 1: SLM-vs-rule characterization.")
    ap.add_argument("--with-slm", action="store_true",
                    help="also score the real Phi-4-mini (needs Foundry Local up)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--determinism-reps", type=int, default=5,
                    help="temp-0 repeats per novel case for the determinism check")
    return ap


if __name__ == "__main__":
    args = _build_parser().parse_args()
    run(with_slm=args.with_slm, seed=args.seed,
        determinism_reps=args.determinism_reps)
