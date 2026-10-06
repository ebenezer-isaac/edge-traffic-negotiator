"""General-capability retention probe (threat-to-validity, finetune-feasibility §9).

Question: did traffic-decision SFT erode general capability (catastrophic
forgetting, arXiv:2401.05605)? Method: a fixed, seeded MMLU sample served
through the SAME Foundry endpoints as the traffic evals, ft vs identically-
compiled stock. Deterministic subsample (seed 7, 25 subjects x 8 items = 200);
temp 0; strict {"answer": "X"} contract with the live parser's fallbacks.
Scored against gold; API errors counted fail-loud, never scored.

Usage: python src/retention_probe.py --model phi4mini-gen-gpu
Writes results/ft_dataset/retention_<model>.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import time

_SRC = os.path.dirname(os.path.abspath(__file__))
FTDIR = os.path.join(os.path.dirname(_SRC), "results", "ft_dataset")
CACHE = os.path.join(FTDIR, "mmlu_sample.json")

from openai import OpenAI  # noqa: E402

from slm_agent import discover_endpoint  # noqa: E402

STRICT = re.compile(r'\{\s*"answer"\s*:\s*"?([ABCD])"?\s*\}', re.I)
LETTER = re.compile(r"\b([ABCD])\b")

SYSTEM = (
    "You are answering a multiple-choice question. Reply with ONLY a JSON "
    'object of the form {"answer": "A"} choosing one of A, B, C, D.'
)


def build_sample():
    """Deterministic 200-item MMLU sample: 8 items from each of 25 subjects."""
    if os.path.exists(CACHE):
        return json.load(open(CACHE, encoding="utf-8"))
    import pandas as pd
    from huggingface_hub import hf_hub_download

    path = hf_hub_download("cais/mmlu", "all/test-00000-of-00001.parquet",
                           repo_type="dataset")
    df = pd.read_parquet(path)
    rng = random.Random(7)
    subjects = sorted(df["subject"].unique())
    rng.shuffle(subjects)
    items = []
    for subj in subjects[:25]:
        sub = df[df["subject"] == subj].reset_index(drop=True)
        for i in rng.sample(range(len(sub)), 8):
            r = sub.iloc[i]
            items.append({
                "subject": subj,
                "question": str(r["question"]),
                "choices": [str(c) for c in r["choices"]],
                "answer": "ABCD"[int(r["answer"])],
            })
    with open(CACHE, "w", encoding="utf-8") as fh:
        json.dump(items, fh, indent=1)
    return items


def main(model):
    items = build_sample()
    base, _ = discover_endpoint()
    client = OpenAI(base_url=base, api_key="unused")
    correct = strict = parsed = errors = 0
    lat = []
    for i, it in enumerate(items):
        usr = it["question"] + "\n" + "\n".join(
            f"{l}. {c}" for l, c in zip("ABCD", it["choices"]))
        t0 = time.time()
        try:
            resp = client.chat.completions.create(
                model=model, temperature=0, max_tokens=256,
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": usr}])
            text = resp.choices[0].message.content or ""
        except Exception as exc:
            errors += 1
            if errors >= 10:
                raise SystemExit(f"ABORT: repeated API errors on '{model}': {exc}")
            continue
        lat.append(time.time() - t0)
        m = STRICT.search(text)
        if m:
            strict += 1
            ans = m.group(1).upper()
        else:
            m2 = LETTER.search(text)
            ans = m2.group(1).upper() if m2 else None
        if ans is not None:
            parsed += 1
            if ans == it["answer"]:
                correct += 1
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(items)}", flush=True)
    n = len(items) - errors
    out = {"model": model, "n": n, "errors": errors,
           "accuracy": round(correct / n, 4),
           "strict_json_rate": round(strict / n, 4),
           "parse_rate": round(parsed / n, 4),
           "latency_p50": round(sorted(lat)[len(lat) // 2], 3) if lat else None}
    p = os.path.join(FTDIR, f"retention_{model.replace(':', '_')}.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="MMLU retention probe via Foundry.")
    ap.add_argument("--model", required=True)
    main(ap.parse_args().model)
