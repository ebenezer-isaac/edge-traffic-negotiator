"""
Quick latency benchmark for an OpenAI-compatible local endpoint (oBeaver).
Measures TTFT, decode tok/s, total latency. Discards warmup runs.

Usage:
    python benchmark.py --model qwen2.5-0.5b --iters 12 --warmup 2 --out results.json
"""
import argparse
import json
import statistics
import time
from pathlib import Path

import httpx

# Representative Edge Negotiator hot-path prompt — short structured-output request
HOT_PATH_PROMPT = (
    "You are a traffic signal controller. Given the intersection state below, "
    "select the next phase. Return ONLY the phase number (0, 1, 2, or 3) — no other text.\n\n"
    "State: NB queue=15 cars + 1 bus, SB queue=0, EB queue=8 cars, WB queue=2 cars + 1 ambulance (urgency=5). "
    "Current phase: 0 (NB-SB green). Time in phase: 18s. Min green elapsed: yes.\n\n"
    "Phase:"
)

# Representative Edge Negotiator audit-path prompt — longer CoT explanation
AUDIT_PATH_PROMPT = (
    "You are a traffic signal controller. The decision was: switch to phase 2 (EB-WB green). "
    "The state at decision time was: NB queue=15 cars + 1 bus, SB queue=0, EB queue=8 cars, "
    "WB queue=2 cars + 1 ambulance (urgency=5). Current phase: 0 (NB-SB green). Time in phase: 18s.\n\n"
    "Explain the reasoning that led to this decision in 2-3 sentences."
)


def stream_one(client, base_url, model, prompt, max_tokens):
    """Stream one completion and measure TTFT, decode rate, total latency."""
    t0 = time.perf_counter()
    ttft = None
    n_tokens = 0
    text = ""

    with client.stream(
        "POST",
        f"{base_url}/v1/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "max_tokens": max_tokens,
            "temperature": 0.0,
        },
        timeout=60.0,
    ) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            payload = line[len("data: "):]
            if payload.strip() == "[DONE]":
                break
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            delta = event.get("choices", [{}])[0].get("delta", {})
            chunk = delta.get("content")
            if chunk is not None:
                if ttft is None:
                    ttft = time.perf_counter() - t0
                n_tokens += 1  # approximate (chunks are typically 1 token)
                text += chunk

    total = time.perf_counter() - t0
    decode_time = total - (ttft or 0)
    return {
        "ttft_ms": round((ttft or total) * 1000, 1),
        "total_ms": round(total * 1000, 1),
        "decode_ms": round(decode_time * 1000, 1),
        "n_tokens": n_tokens,
        "decode_tok_per_s": round(n_tokens / decode_time, 2) if decode_time > 0 else 0,
        "text": text,
    }


def percentile(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return xs[f]
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def summarise(runs, warmup):
    measured = runs[warmup:]
    metrics = ["ttft_ms", "total_ms", "decode_ms", "decode_tok_per_s", "n_tokens"]
    out = {"n_warmup": warmup, "n_measured": len(measured)}
    for m in metrics:
        vals = [r[m] for r in measured]
        out[m] = {
            "min": min(vals),
            "max": max(vals),
            "median": statistics.median(vals),
            "mean": round(statistics.mean(vals), 2),
            "stdev": round(statistics.stdev(vals), 2) if len(vals) > 1 else 0,
            "p95": round(percentile(vals, 0.95), 2),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:18000")
    ap.add_argument("--model", required=True)
    ap.add_argument("--iters", type=int, default=12)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Benchmark: {args.model} ===")
    print(f"Endpoint: {args.base_url}")
    print(f"Iterations: {args.iters} (warmup: {args.warmup})\n")

    with httpx.Client() as client:
        # Wait for server health
        for _ in range(20):
            try:
                h = client.get(f"{args.base_url}/health", timeout=2.0)
                if h.status_code == 200:
                    print(f"Server health OK: {h.json()}\n")
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            print("WARN: health check failed; proceeding anyway")

        results = {"hot_path": [], "audit_path": []}

        print("--- Hot-path runs (single-token output) ---")
        for i in range(args.iters):
            r = stream_one(client, args.base_url, args.model, HOT_PATH_PROMPT, max_tokens=4)
            tag = "warmup" if i < args.warmup else "measure"
            print(f"  [{tag} {i+1:2d}] TTFT={r['ttft_ms']:>7.1f}ms  total={r['total_ms']:>7.1f}ms  "
                  f"toks={r['n_tokens']:>3d}  text={r['text']!r}")
            results["hot_path"].append(r)

        print("\n--- Audit-path runs (CoT, ~50 tokens) ---")
        for i in range(args.iters):
            r = stream_one(client, args.base_url, args.model, AUDIT_PATH_PROMPT, max_tokens=120)
            tag = "warmup" if i < args.warmup else "measure"
            print(f"  [{tag} {i+1:2d}] TTFT={r['ttft_ms']:>7.1f}ms  total={r['total_ms']:>7.1f}ms  "
                  f"toks={r['n_tokens']:>3d}  decode={r['decode_tok_per_s']:>6.2f}tok/s")
            results["audit_path"].append(r)

    summary = {
        "model": args.model,
        "base_url": args.base_url,
        "hot_path": summarise(results["hot_path"], args.warmup),
        "audit_path": summarise(results["audit_path"], args.warmup),
        "raw": results,
    }
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"\nResults written to {out_path}")

    print("\n=== Summary ===")
    for path in ("hot_path", "audit_path"):
        s = summary[path]
        print(f"\n{path}:")
        print(f"  TTFT  median={s['ttft_ms']['median']:.1f}ms  p95={s['ttft_ms']['p95']:.1f}ms")
        print(f"  Total median={s['total_ms']['median']:.1f}ms  p95={s['total_ms']['p95']:.1f}ms")
        print(f"  Decode median={s['decode_tok_per_s']['median']:.2f}tok/s  "
              f"min={s['decode_tok_per_s']['min']:.2f}tok/s")


if __name__ == "__main__":
    main()
