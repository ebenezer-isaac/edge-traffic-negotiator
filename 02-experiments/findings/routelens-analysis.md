# RouteLens (modelrouter-routelens) — Relevance Analysis for Edge Negotiator

**Repo:** `e:\desktop\assignments\dissertation\02-experiments\modelrouter-routelens`
**Upstream:** https://github.com/leestott/modelrouter-routelens
**License:** MIT
**Author intent (from blog):** Validate that Microsoft Foundry Model Router routes identical prompts consistently across two Azure SDK surfaces (Chat Completions vs Project Responses). Diagnose a specific 408 timeout issue.
**Reviewed against:** Edge Negotiator (Qwen3-4B vs Phi-4-mini SLMs, local laptop, SUMO simulation, Z3 verifier, Besu vs Tessera blockchain comparator).

---

## 1. What does it do?

RouteLens is a thin Node.js diagnostic harness that fans the same prompt through two Azure endpoint configurations and records the result. From `src/matrix.js:24-85` and `src/index.js:38-94`, the loop is straightforward:

1. Load a fixed prompt set (`src/prompts.js:12-47`: 5 prompts across `echo`, `summarize`, `code`, `reasoning`).
2. For every `prompt × path × run`, build a task that calls either `sendChatCompletion` (`src/clients/chatCompletions.js:30-85`) or `sendProjectResponse` (`src/clients/projectResponses.js:32-90`).
3. Run all tasks under bounded concurrency (`src/utils.js:43-60`) with transient-error retry (`src/utils.js:16-35`, retries on 408/429/502/503/504 with exponential backoff + jitter).
4. Stream every result as a JSONL line into `logs/` (`src/logger.js:18-22`).
5. Print a console report (`src/report.js`) and/or serve a single-page web dashboard from `public/index.html` via a zero-dependency HTTP server (`src/server.js`).
6. A second mode `--repro408` (`src/repro408.js`) sweeps timeouts of 10/30/60 s on a known-bad prompt to classify failures as `client_timeout`, `server_408`, or `other`.

The key insight: **both "paths" are actually the same Chat Completions API hitting the same model-router deployment** — the comment at `src/clients/projectResponses.js:27-28` admits "the Responses API is not yet available on cognitiveservices.azure.com Model Router deployments". So the tool currently compares the same SDK call routed via two different base URLs, not two genuinely different runtimes.

It is a **diagnostic/observability tool**, not a benchmark suite. There is no warm-up, no statistical test, no fixed seed, no first-token-latency measurement, no streaming, no controlled hardware accounting. Latency is measured wall-clock around an HTTP call (`performance.now()` in `src/clients/chatCompletions.js:33,48`), which is dominated by network RTT to Azure, not by inference compute.

## 2. Architecture and dependencies

Dependencies (`package.json:39-42`): only **`dotenv`** and **`openai` ≥4.85**. Node 18+. No native modules, no test dependencies (uses `node:test`). Total runtime footprint is a few MB.

Architecture is shallow:

- `src/config.js` — frozen object built from env vars; `validateConfig()` exits if any of `FOUNDRY_PROJECT_ENDPOINT`, `AOAI_BASE_URL`, `AOAI_API_KEY` are missing.
- `src/clients/*.js` — two near-identical OpenAI SDK clients, differing only in `baseURL`.
- `src/matrix.js` / `src/repro408.js` — orchestrators producing a uniform result shape.
- `src/utils.js` — `sleep`, `withRetry`, `runConcurrent`, `timeoutController`. Generic, ~75 lines.
- `src/logger.js` — appendFileSync to a timestamped JSONL.
- `src/report.js` — pure aggregation + console table.
- `src/server.js` — `node:http` SPA server with REST endpoints (`/api/run/matrix`, `/api/results`, `/api/logs/view`, etc.) and in-memory run state.

Runs entirely on the developer machine, but every request hits **Azure cloud**. Nothing local-inference-related.

## 3. Direct use for the Edge Negotiator

**No, it cannot be used directly.** The blockers are structural, not cosmetic:

- The clients are bound to the OpenAI SDK calling Azure Cognitive Services with an `api-key` header (`src/clients/chatCompletions.js:16-22`). Qwen3-4B and Phi-4-mini are **local SLMs** in our setup; they would be served by vLLM, llama.cpp, or Ollama. Even if those expose OpenAI-compatible endpoints (vLLM and Ollama do), pointing RouteLens at them would still inherit assumptions baked into the harness.
- It does not measure what we need: TTFT, decode tokens/sec, KV-cache hit rate, GPU memory, prefix-cache reuse, constrained-decoding overhead (XGrammar), CFG validity rate, single-token phase-ID latency, or post-hoc CoT generation cost. The "TPS" in `src/server.js:99-101` is just `total_tokens / wall_clock_seconds` — meaningless when wall clock is mostly network.
- Prompts are static text strings. Edge Negotiator inputs are structured intersection state vectors with prefix-cached system prompts.
- No support for streaming, no separation of prefill vs decode, no concurrency-vs-latency curves.

**Could it diagnose Qwen3-4B vs Phi-4-mini through identical prompt streams?** Only in the weakest possible sense — if you stood up two OpenAI-compatible local servers (one per model) and pointed `AOAI_BASE_URL` and `FOUNDRY_PROJECT_ENDPOINT` at them, the matrix loop would issue identical requests and log per-request latency. But the metrics it produces (p50/p95 wall-clock, error rate, "model chosen") miss everything that matters for an SLM benchmark on a laptop. You would learn whether both servers respond, not what their inference characteristics are.

**Could it serve as the Besu vs Tessera comparator pattern?** This is a more interesting question. Structurally, "fire identical requests at two backends, normalise results, log JSONL, compute paired stats, highlight divergences" is exactly the comparator pattern we need for blockchain instrumentation. The matrix loop in `src/matrix.js:24-85` and the model-diff in `src/report.js:53-77` are a working sketch of that pattern in ~150 lines. The shape is right; the implementation is too coupled to the OpenAI SDK to drop in. See §4.

## 4. Implementation lessons (patterns worth lifting)

Useful, in order of value:

1. **Result-shape normalisation.** `src/clients/chatCompletions.js:49-79` and `src/clients/projectResponses.js:53-83` normalise success and failure into the same flat object: `{path, ok, status, latencyMs, model, usage, responseId, content, error}`. Both paths' errors are coerced into `{name, message, status, code}` with message truncation. This is the right discipline for any A/B harness — paired comparison fails the moment one side has a different result shape. Lift this for both the SLM comparator and the Besu/Tessera comparator.

2. **JSONL append-only audit log.** `src/logger.js:18-22` writes one self-describing JSON object per request with an ISO timestamp prepended. Trivial, robust, append-safe under concurrency on a single writer. This is exactly the audit-trail substrate the Edge Negotiator needs for its post-hoc CoT capture and Z3-verifier decisions. Use the same pattern: timestamped JSONL keyed by `runId`/`promptId`/`path`.

3. **Bounded-concurrency worker pool.** `src/utils.js:43-60` is 18 lines of dependency-free worker pool. Lift verbatim if you need parallel SLM dispatch, replay, or replication runs.

4. **Transient-error retry with jittered exponential backoff.** `src/utils.js:16-35`. The set `{408, 429, 502, 503, 504}` is the right shortlist. For the Edge Negotiator hot path you do **not** want retry — falling back to MaxPressure is the policy — but for offline benchmark runs and the audit-path SLM call this is the right shape.

5. **Side-by-side divergence highlighter.** `src/report.js:53-77` (`printModelDiff`) groups results by `promptId`, computes the unique-model set per path, and flags `✗ DIFFER` when sets differ. The Besu vs Tessera comparator wants exactly this for transaction receipts, state roots, gas used, and finalisation latency. The 12-line `setsEqual` + sort-and-compare pattern is the template.

6. **Two-mode CLI dispatch.** `src/index.js:47-94` switches between `matrix` and `repro408`. Useful precedent for a comparator that supports a "full sweep" mode and a targeted "drill into known-pathological case" mode — directly applicable when you find a specific intersection scenario where Qwen3-4B and Phi-4-mini disagree.

7. **Web dashboard from `node:http`.** `src/server.js` is a single-file SPA backend with no framework. ~440 lines, including in-memory run state, log file browser, CORS headers, and traversal protection. If we want a quick visual sanity-check UI for benchmark runs without pulling in Next.js, this is a clean reference. The `analyseResults` function in `src/server.js:76-141` is also a good model for "compute everything the UI needs in one pass".

What **not** to lift:

- The `Object.defineProperty(config, "runs", {value: n})` mutation at `src/index.js:59,64` to override frozen config. Hack — pass config explicitly instead.
- `setsEqual` in `src/report.js:119-122` assumes both arrays are sorted; correct here because callers sort, but fragile.
- Run-state mutation in `src/server.js:240-242` (`currentRun.results.push(entry)`) violates immutability and is racy if two runs ever overlap. The `if (currentRun?.status === "running")` guard at `src/server.js:389` is the only protection.

## 5. Benchmarking relevance

For **SLM benchmarking** (Qwen3-4B vs Phi-4-mini latency, throughput, hardware needs): **low**. The repo measures end-to-end wall-clock against a remote service. None of the metrics the dissertation needs (TTFT, decode tok/s, KV-cache behaviour, VRAM, CFG-constrained decode overhead, prefix-cache hit rate) are present. Use vLLM's built-in benchmark scripts, llama.cpp's `llama-bench`, or write a small harness that calls the local server's `/v1/completions` with `stream=true` and records first-token timestamps. The matrix loop and JSONL logger are still worth lifting as the *outer* harness around such a benchmark.

For the **Besu vs Tessera comparator**: **moderate**. The structural pattern is a good starting template — paired dispatch, normalised result shape, divergence detection, JSONL audit log. But the actual call sites and result shapes are incompatible. Implementation effort is "rewrite, keeping the architecture" rather than "adapt".

## 6. Hardware requirements and latency methodology

**Hardware:** The tool itself runs anywhere with Node 18+. Prerequisites (`README.md:62-66`): Azure subscription, Foundry project in **East US 2**, Model Router deployment. No local GPU, no local model. The "hardware requirement" is an Azure quota. Nothing transferable to laptop-class inference characterisation.

**Latency methodology:** `performance.now()` deltas around the OpenAI SDK call (`src/clients/chatCompletions.js:33,48`). Aggregation is sort-and-pick percentile via `Math.ceil((pct/100) * n) - 1` (`src/report.js:95-99`, `src/server.js:202-206`). No warm-up runs, no outlier rejection, no confidence intervals, no paired statistical tests, no streaming first-token timing. Concurrency is configurable but the same workers serve both paths, so any contention affects both equally — that's actually a small plus for paired comparison validity but it's not advertised as a design choice.

For the dissertation we need first-token latency, per-token decode latency, and confidence intervals (paired t-test or Wilcoxon signed-rank for SLM A/B; same for blockchain backends). RouteLens does none of this.

## 7. CPU-only inference

**Nothing.** Zero references to CPU, GPU, ONNX, llama.cpp, Ollama, vLLM, gguf, quantisation, or any local-inference tooling in the source, README, blog post, or `.env.example`. Every code path assumes an HTTPS endpoint with `api-key` header pointing at Azure Cognitive Services. If Lee Stott has CPU material, it is not in this repo. The repo cannot answer "does Phi-4-mini run on CPU?" because it never touches a model — it only routes to whatever Foundry decides.

## 8. Risks

- **Azure subscription required.** Hard dependency. No mock mode, no offline mode (`src/config.js:49-60` exits if endpoints/key are missing).
- **Costs money to run.** Every request is a billable Azure inference call. The default `RUNS=3 × 5 prompts × 2 paths = 30` requests per matrix run; a multi-run experiment could rack up tokens quickly.
- **Vendor lock-in.** Foundry-specific, Model-Router-specific, East-US-2-specific. Unusable if Azure access is unavailable. No abstraction layer to swap providers.
- **The two "paths" are not actually different.** Per the comment at `src/clients/projectResponses.js:27-28`, both clients call the same Chat Completions API at the same endpoint shape. The comparison reveals routing variance within Azure, not between SDK surfaces. For our purposes this means the "comparator" pattern is barely exercised — both backends have near-identical response shapes by construction.
- **Mutates frozen config from CLI args** (`src/index.js:57-65`) — minor code smell, but indicates the architecture wasn't designed for test isolation.
- **In-memory run state with race-prone mutation** in `src/server.js:240-249`. Acceptable for a dev tool, not for anything we'd ship.
- **No statistical rigour.** p50/p95 from a handful of samples with no warm-up. A dissertation cannot cite these methods.
- **Single-writer JSONL.** `appendFileSync` is fine within one process but offers no protection against concurrent runs on the same log file.

## 9. Concrete recommendation

**(b) Implement similar pattern.** Do not adopt RouteLens directly — it is structurally tied to Azure cloud inference and measures only what is meaningful for cloud routing diagnostics, none of which transfers to a local-laptop SLM benchmark or to laptop-paired blockchain comparator runs. But the *shape* of the harness — paired dispatch with normalised result envelopes, JSONL append-only audit log, bounded-concurrency worker pool, divergence reporter, two-mode CLI (broad sweep + targeted repro) — is exactly the comparator skeleton both the SLM-A/B work and the Besu-vs-Tessera work need. Lift the patterns from `src/utils.js`, `src/logger.js`, the result-normalisation discipline in `src/clients/*.js`, and the divergence logic in `src/report.js:53-77` as a starting sketch (~250 lines total), then build on top: add streaming/TTFT capture, prefix-cache hit accounting, paired statistical tests (Wilcoxon, BCa bootstrap CIs), warm-up runs with discarded samples, fixed seeds, and CSV export for R/Python analysis. Cite RouteLens in the dissertation as the visible-prior-art for the comparator pattern; do not cite it as a benchmarking methodology.
