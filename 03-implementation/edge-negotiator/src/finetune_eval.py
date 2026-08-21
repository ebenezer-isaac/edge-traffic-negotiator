"""Offline holdout eval (MASTER-SPEC §14.3 step 5): evaluate a Foundry-served model
against the FROZEN holdout at int4-as-served. Reports, per prompt format, accuracy vs
the teacher label, JSON-validity (strict {"phase": N} primary-regex hit), and parse
failures. The stock model of the same family is the paired control — run both and
compare. Zero training deps: uses the project venv + the live SLMAgent parse rules.

Usage:
  python src/finetune_eval.py --model qwen3-0.6b-ft1 --formats sota
  python src/finetune_eval.py --model qwen3-0.6b     --formats sota myopic prediction
Writes results/ft_dataset/eval_<model>.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time

_SRC = os.path.dirname(os.path.abspath(__file__))
FTDIR = os.path.join(os.path.dirname(_SRC), "results", "ft_dataset")

from openai import OpenAI  # noqa: E402

from slm_agent import discover_endpoint  # noqa: E402

STRICT = re.compile(r'\{\s*"phase"\s*:\s*(\d+)\s*\}')
BRACED = re.compile(r'\{[^{}]*"?phase"?\s*[:=]\s*(\d+)[^{}]*\}')
KEYED = re.compile(r'"?phase"?\s*[:=]\s*(\d+)')
BARE = re.compile(r"\b(\d+)\b")


def parse(text):
    """(phase, tier): tier 'strict' = exact {"phase": N}; then live-parser fallbacks."""
    m = STRICT.search(text)
    if m:
        return int(m.group(1)), "strict"
    m = BRACED.search(text)
    if m:
        return int(m.group(1)), "braced"
    m = KEYED.search(text)
    if m:
        return int(m.group(1)), "keyed"
    m = BARE.search(text)
    if m:
        return int(m.group(1)), "bare"
    return None, "none"


def main(model, formats, limit=None):
    rows = []
    with open(os.path.join(FTDIR, "holdout.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["format"] in formats:
                rows.append(r)
    if limit:
        rows = rows[:limit]
    base, _ = discover_endpoint()
    client = OpenAI(base_url=base, api_key="none")
    stats = {f: {"n": 0, "correct": 0, "strict": 0, "parsed": 0, "latency": []}
             for f in formats}
    t_start = time.time()
    for i, r in enumerate(rows):
        sys_c = next(m["content"] for m in r["messages"] if m["role"] == "system")
        usr_c = next(m["content"] for m in r["messages"] if m["role"] == "user")
        gold = json.loads(next(m["content"] for m in r["messages"]
                               if m["role"] == "assistant"))["phase"]
        t0 = time.time()
        err = None
        try:
            resp = client.chat.completions.create(
                model=model, temperature=0, max_tokens=256,
                messages=[{"role": "system", "content": sys_c},
                          {"role": "user", "content": usr_c}])
            text = resp.choices[0].message.content or ""
        except Exception as exc:
            err, text = str(exc), ""
        dt = time.time() - t0
        s = stats[r["format"]]
        if err is not None:
            # FAIL LOUD but RECOVER: Foundry Local can self-restart under sustained load
            # (measured 3x, 2026-08-08/19). On repeated errors, re-discover the endpoint,
            # reload the model, rebuild the client, and RETRY THE SAME ROW (stats intact).
            # Abort only if recovery itself fails repeatedly (wrong model id etc.).
            s.setdefault("api_errors", 0)
            s["api_errors"] = s["api_errors"] + 1
            if s["api_errors"] % 5 == 0:
                import subprocess, time as _t
                print(f"[recover] {s['api_errors']} errors; bouncing client for {model}",
                      flush=True)
                _t.sleep(10)
                subprocess.run(["foundry", "model", "load", model], capture_output=True,
                               timeout=300, shell=True)
                from slm_agent import discover_endpoint as _de
                base, _ = _de()
                client = OpenAI(base_url=base, api_key="unused")
            if s["api_errors"] >= 40:
                raise SystemExit(f"ABORT: unrecoverable API errors calling '{model}': {err}")
            # retry same row by re-appending it to the end of the queue
            rows.append(r)
            continue
        phase, tier = parse(text)
        s["n"] += 1
        s["latency"].append(dt)
        if tier == "strict":
            s["strict"] += 1
        if phase is not None:
            s["parsed"] += 1
            if phase == gold:
                s["correct"] += 1
        if (i + 1) % 100 == 0:
            done = i + 1
            rate = done / (time.time() - t_start)
            print(f"  {done}/{len(rows)} ({rate:.1f}/s)", flush=True)
    out = {"model": model, "formats": {}}
    for f, s in stats.items():
        if s["n"] == 0:
            continue
        lat = sorted(s["latency"])
        out["formats"][f] = {
            "n": s["n"], "accuracy": round(s["correct"] / s["n"], 4),
            "strict_json_rate": round(s["strict"] / s["n"], 4),
            "parse_rate": round(s["parsed"] / s["n"], 4),
            "latency_p50": round(lat[len(lat) // 2], 3),
            "latency_p99": round(lat[min(len(lat) - 1, int(len(lat) * 0.99))], 3),
        }
    p = os.path.join(FTDIR, f"eval_{model.replace(':', '_')}.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2), flush=True)
    print(f"wrote {p}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Offline holdout eval vs teacher labels.")
    ap.add_argument("--model", required=True)
    ap.add_argument("--formats", nargs="*", default=["sota"])
    ap.add_argument("--limit", type=int, default=None)
    ns = ap.parse_args()
    main(ns.model, ns.formats, limit=ns.limit)
