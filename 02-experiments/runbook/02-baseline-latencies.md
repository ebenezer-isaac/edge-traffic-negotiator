# Runbook 02 — Baseline Latency Measurements

**Date:** 2026-04-16
**Hardware:**
- CPU: Windows 10 host, x86_64 (specifics TBD via `wmic cpu get name`)
- GPU: **NVIDIA GeForce RTX 2060** (6 GB VRAM, ~4 GB free), CUDA 13.1, driver 591.59
- Note: Older than the synthesis's assumed RTX 3060/4060 mobile. Recorded for honest reporting.

**Method:** Custom `benchmark.py` script in `runbook/`. Sends two prompts (hot-path single-token, audit-path ~100-token CoT) via streaming HTTP to oBeaver's OpenAI-compatible endpoint at `http://127.0.0.1:18000/v1/chat/completions`. Measures TTFT (time-to-first-token), total latency, decode tok/s. 12 iterations per prompt, 2 warmup discarded. Temperature 0.

**Models tested (via Foundry Local engine, oBeaver 0.1.0):**
1. `qwen2.5-0.5b` on CPU (smoke test, smallest available)
2. `phi-4-mini` on GPU (RTX 2060, the comparison SLM in the locked architecture)
3. `phi-4-mini` on CPU (CPU-vs-GPU comparison for the same model)

**Not yet tested:** Qwen3-4B (primary SLM — requires HF auth + ORT conversion, separate runbook), Traffic-R1 (same constraint).

---

## Headline Numbers

| Model | Hardware | Hot-path TTFT median | Hot-path total median | Audit-path total median | Decode tok/s median | JSON correctness |
|-------|----------|----------------------|------------------------|--------------------------|----------------------|------------------|
| qwen2.5-0.5b | CPU (Foundry) | **772 ms** | 836 ms | 4,672 ms | 29.2 | **3 of 10 wrong** ("CB", "4", out-of-range) |
| phi-4-mini (3.8B) | **GPU** (RTX 2060) | **374 ms** | 470 ms | 8,453 ms | 13.5 | **10 of 10 correct** ("1") |
| phi-4-mini (3.8B) | CPU (Foundry) | **3,230 ms** | 3,494 ms | 33,470 ms | 3.6 | 10 of 10 correct (but truncated audit outputs: 79–119 tokens vs 109 on GPU) |

---

## Findings

### F1 — Hot-path 10ms target is unreachable on this hardware
The Edge Negotiator's design target was ~10ms for the single-token hot path. Best observed (phi-4-mini GPU): **374ms TTFT, 470ms total** — missed by 37–47×. On CPU, the gap is 320–349×. **No quantity of ONNX optimisation closes this gap with current consumer hardware**; the 10ms target is achievable only on dedicated NPU/ASIC silicon or with much smaller models that can't reason about traffic priority.

**Implication for the dissertation:** the hot-path budget framing must be relaxed from "single-cycle SUMO step (10ms)" to "phase-actuation interval (typical 5+ seconds for traffic signals)". Fortunately this is exactly the natural cadence of traffic control. The 10ms framing was overly aggressive.

### F2 — Audit-path 500ms target is also unreachable, but the implications differ
Best observed (phi-4-mini GPU): **8.5 seconds** for ~109 tokens. CPU: 33 seconds. The audit path was already designed to run **asynchronously** (decisions execute optimistically; CoT is generated in the background and committed to the ledger when ready). The 500ms target was for the dissertation's evaluation-time fast-cycle simulation. Real audit-trail commitment within 10 seconds on GPU is acceptable for the use case.

### F3 — GPU vs CPU is decisive (4–9× speedup on the same model)
Phi-4-mini speedup CPU→GPU on the same workload:
- Hot-path TTFT: 3230ms → 374ms = **8.6× faster**
- Audit-path total: 33,470ms → 8,453ms = **4.0× faster**
- Decode tok/s: 3.6 → 13.5 = **3.7× faster**

For the dissertation's experimental design: the SUMO simulation must run with the SLM on GPU. CPU is non-viable even for the audit path on a 3.8B model. **This empirically confirms what the FLPerformance investigation predicted from public benchmarks.**

### F4 — Smaller is faster but unreliable
qwen2.5-0.5b on CPU (772ms TTFT) was **2× faster than phi-4-mini on GPU** for hot-path TTFT. But the model returned garbage 3/10 times: "CB" instead of a phase number, "4" instead of 0–3. **This empirically validates Prompt 3's argument that CFG-constrained decoding (XGrammar/Outlines) is essential** — the model alone cannot be trusted to produce structured output even on a trivially constrained prompt.

**Implication:** the dissertation's locked decision to wrap SLM output with CFG-constrained JSON via XGrammar is now backed by direct empirical evidence on the user's own hardware. Without CFG, the smaller model would be unusable; with CFG, it might be the right hot-path choice (subject to faithfulness validation).

### F5 — The bigger model on GPU was 100% reliable
phi-4-mini GPU returned exactly "1" for all 10 hot-path runs. This suggests the architectural decision to ship Phi-4-mini as the comparison SLM (and possibly fall back to it under load via the routing pattern from RouteLens) is sound. Even without CFG-constrained decoding, Phi-4-mini was reliable on this prompt.

### F6 — Foundry Local CPU model is BIGGER than GPU model
Counter-intuitively: phi-4-mini CPU is 4.8 GB on disk, GPU is 3.7 GB. This is because the CPU INT4 builds include extra fallback weights and an unfused execution graph optimised for x86 SIMD. Worth noting for storage planning but doesn't affect benchmark results.

### F7 — There is significant warmup variability in the first 1–2 runs
Across all three benchmarks, runs 1 and 2 (warmup) were 30–80% slower than the steady-state. The benchmark script discards them. For the SUMO offline-profiling-then-inject methodology, the latency distribution should also discard warmup to avoid contaminating the injected delays.

---

## Per-Run Detail

Files written by the benchmark script:
- `runbook/results/qwen25-05b-cpu.json`
- `runbook/results/phi4-mini-gpu.json`
- `runbook/results/phi4-mini-cpu.json`

Each contains the full per-run timings (`ttft_ms`, `total_ms`, `decode_ms`, `n_tokens`, `decode_tok_per_s`, `text`) plus aggregated summary statistics (min, max, median, mean, stdev, p95).

Server logs:
- `runbook/logs/server-phi4-mini-gpu.log`
- `runbook/logs/server-phi4-mini-cpu.log`

---

## What's Next

1. **HF authentication** + ORT model download/conversion for **Qwen3-4B** (primary SLM) and Traffic-R1 (anchor)
2. Re-run benchmark on Qwen3-4B both CPU and GPU
3. Add a third probe: structured JSON output with `response_format` to test the empirical reliability of structured output (vs the free-form text used here)
4. Profile **TTFT distribution at varying input prompt length** (300, 600, 1500, 3000 tokens) — current benchmark uses ~150-token prompts; the Edge Negotiator's actual prompts in the SUMO loop will vary
5. Use the captured latency distributions to seed the SUMO TraCI step delay injection (Approach A from Prompt 6 §3)
