"""Lee fair re-test (SLM arm of the vehicle-authorisation categorised eval).

Lee Stott's 2026-06-25 program, points 1-2, applied to the SLM: policies stated
STRUCTURED and IN-PROMPT, and the model made to reason AGAINST NAMED RULES
before classifying -- versus the same model classifying from facts alone. The
deterministic KB gate (experiment_vehicle_auth) is the gold reference; the
dataset is its exact 26-claim balanced categorised set. Metrics per Lee's
point 4: class accuracy, grant confusion (positive = should-DENY) with
P/R/FPR/FNR, dangerous false grants, and P50/P95/P99 latency.

Two arms per model:
  scaffold   -- KB rules rendered into the prompt + reason-then-classify
  bare       -- claim facts only, direct classification (the earlier style)
The delta between arms is the measured value of Lee's scaffold; whether the
scaffolded SLM matches the deterministic gate decides if the earlier SLM
negative was a handicap artefact or robust.

Usage: python src/experiment_slm_auth_lee.py --model phi-4-mini
Writes results/slm_auth_lee_<model>.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
RESULTS = os.path.normpath(os.path.join(_HERE, "..", "results"))

from openai import OpenAI  # noqa: E402

from experiment_vehicle_auth import build_dataset  # noqa: E402
from slm_agent import discover_endpoint  # noqa: E402
from vehicle_authorization import load_kb  # noqa: E402

ANSWER = re.compile(
    r'\{[^{}]*"class"\s*:\s*"(LEGITIMATE|SPOOFED_OR_FAULTY|UNKNOWN)"[^{}]*'
    r'"grant"\s*:\s*(true|false)[^{}]*\}', re.I)


def render_rules() -> str:
    """The KB's structured authorisation rules, stated explicitly (Lee point 1)."""
    entities, preempt_actions = load_kb()
    lines = ["NAMED RULES (each row is authoritative; cite rule ids in reasoning):"]
    for i, (cls, e) in enumerate(sorted(entities.items()), 1):
        lines.append(
            f"R{i} class={cls}: preemption_allowed={e.preemption_allowed}, "
            f"actions_allowed={list(e.actions_allowed)}, "
            f"authorising_key_classes={list(e.authorising_key_classes)}, "
            f"key_required={e.key_required}")
    lines.append(f"R-act: actions that REQUEST preemption = {list(preempt_actions)}.")
    lines.append(
        "R-cls: LEGITIMATE = asserted class exists in the rules AND a valid key of "
        "an authorising class is present AND the action is in actions_allowed. "
        "SPOOFED_OR_FAULTY = key invalid/absent-when-required/wrong class, OR two "
        "approved reports contradict. UNKNOWN = asserted class not in the rules, "
        "or required claim fields missing (asserted_class, action, key_present; "
        "key_present without key_class is incomplete).")
    lines.append("R-grant: grant=true ONLY for a LEGITIMATE claim whose action "
                 "requests preemption AND whose class has preemption_allowed=true.")
    return "\n".join(lines)


def render_claim(c) -> str:
    return (f"CLAIM: asserted_class={c.asserted_class!r}, action={c.action!r}, "
            f"key_present={c.key_present}, key_valid={c.key_valid}, "
            f"key_class={c.key_class!r}, contradictory={c.contradictory}, "
            f"metadata={dict(c.metadata)!r}")


SYS_SCAFFOLD = (
    "You are the authorisation gate of a traffic junction. First reason in at "
    "most 4 short lines AGAINST THE NAMED RULES you are given (cite rule ids "
    "like R3, R-grant). Then output EXACTLY one final line of JSON: "
    '{"class": "LEGITIMATE"|"SPOOFED_OR_FAULTY"|"UNKNOWN", "grant": true|false}')
SYS_BARE = (
    "You are the authorisation gate of a traffic junction. Decide whether the "
    "claim is LEGITIMATE, SPOOFED_OR_FAULTY, or UNKNOWN and whether preemption "
    "should be granted. Output EXACTLY one final line of JSON: "
    '{"class": "LEGITIMATE"|"SPOOFED_OR_FAULTY"|"UNKNOWN", "grant": true|false}')


def run_arm(client, model, cases, scaffold: bool):
    rules = render_rules()
    stats = {"n": 0, "class_correct": 0, "grant_correct": 0,
             "tp": 0, "fp": 0, "fn": 0, "tn": 0, "parse_fail": 0,
             "dangerous_false_grants": 0, "latency": [], "misses": []}
    for case in cases:
        c = case["claim"]
        usr = (rules + "\n\n" + render_claim(c)) if scaffold else render_claim(c)
        t0 = time.time()
        try:
            resp = client.chat.completions.create(
                model=model, temperature=0, max_tokens=512,
                messages=[{"role": "system",
                           "content": SYS_SCAFFOLD if scaffold else SYS_BARE},
                          {"role": "user", "content": usr}])
            text = resp.choices[0].message.content or ""
        except Exception as exc:
            raise SystemExit(f"ABORT: API error on '{model}': {exc}")
        stats["latency"].append(time.time() - t0)
        m = None
        for m in ANSWER.finditer(text):
            pass  # last match wins (final line rule)
        stats["n"] += 1
        if m is None:
            stats["parse_fail"] += 1
            pred_cls, pred_grant = None, None
        else:
            pred_cls = m.group(1).upper()
            pred_grant = m.group(2).lower() == "true"
        exp_cls, exp_grant = case["expected_class"], case["expect_grant"]
        if pred_cls == exp_cls:
            stats["class_correct"] += 1
        if pred_grant is not None and pred_grant == exp_grant:
            stats["grant_correct"] += 1
        # confusion on the DENY-positive convention (matches the KB-gate artifact):
        should_deny = not exp_grant
        did_deny = (pred_grant is not None) and (not pred_grant)
        if should_deny and did_deny:
            stats["tp"] += 1
        elif should_deny and not did_deny:
            stats["fp"] += 1  # granted what must be denied
            stats["dangerous_false_grants"] += 1
        elif not should_deny and did_deny:
            stats["fn"] += 1  # denied a genuine claim
        else:
            stats["tn"] += 1
        if pred_cls != exp_cls or (pred_grant is not None and pred_grant != exp_grant):
            stats["misses"].append({"category": case["category"],
                                    "expected": [exp_cls, exp_grant],
                                    "got": [pred_cls, pred_grant]})
    lat = sorted(stats["latency"])
    nr = lambda q: lat[min(len(lat) - 1, max(0, -(-int(q * len(lat)) // 1) - 1))]
    tp, fp, fn = stats["tp"], stats["fp"], stats["fn"]
    out = {
        "n": stats["n"],
        "class_accuracy": round(stats["class_correct"] / stats["n"], 4),
        "grant_accuracy": round(stats["grant_correct"] / stats["n"], 4),
        "parse_fail": stats["parse_fail"],
        "precision": round(tp / (tp + fp), 4) if tp + fp else None,
        "recall": round(tp / (tp + fn), 4) if tp + fn else None,
        "false_positive_rate": round(fp / (fp + stats["tn"]), 4)
            if fp + stats["tn"] else None,
        "false_negative_rate": round(fn / (fn + tp), 4) if fn + tp else None,
        "dangerous_false_grants": stats["dangerous_false_grants"],
        "latency_p50": round(nr(0.50), 3), "latency_p95": round(nr(0.95), 3),
        "latency_p99": round(nr(0.99), 3),
        "misses": stats["misses"],
    }
    return out


def main(model):
    cases = build_dataset()
    base, _ = discover_endpoint()
    client = OpenAI(base_url=base, api_key="unused")
    result = {"experiment": "lee_fair_retest_slm_auth",
              "gold": "deterministic KB gate (experiment_vehicle_auth)",
              "model": model, "dataset_size": len(cases),
              "arms": {"scaffold": run_arm(client, model, cases, True),
                       "bare": run_arm(client, model, cases, False)}}
    p = os.path.join(RESULTS, f"slm_auth_lee_{model.replace(':', '_')}.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps({k: v for k, v in result["arms"].items()}, indent=1), flush=True)
    print(f"wrote {p}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Lee fair re-test: SLM authorisation arm.")
    ap.add_argument("--model", required=True)
    main(ap.parse_args().model)
