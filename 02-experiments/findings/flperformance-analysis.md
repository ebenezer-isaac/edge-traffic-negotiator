> **SUPERSEDED HISTORICAL RECORD (pre-2026-05-31-pivot).** Dated measurement log / transcript kept for the audit trail; the current thesis is in specs/001-edge-negotiator/MASTER-SPEC.md (Euston A501; self-referential coupling; CT-style accountability; Phi-4-mini). Forbidden-term hits below are historical, not current claims.

# FLPerformance Repo Analysis for the Edge Negotiator

**Repo:** `e:\desktop\assignments\dissertation\02-experiments\FLPerformance`
**Source:** https://github.com/leestott/FLPerformance (Lee Stott, Microsoft)
**Version inspected:** 2.0.0 (CHANGELOG dated 2026-03-12)
**Purpose of this document:** Decide whether FLPerformance is the laptop-side benchmark harness for the Edge Negotiator dissertation, and if so, exactly how to use it.

---

## 1. What does it do?

FLPerformance is a **full-stack web application** (React + Vite frontend on port 3000; Express + Node.js backend on port 3001) whose only job is to drive Microsoft Foundry Local through its official JavaScript SDK and measure inference performance of locally-loaded SLMs. It is not a CLI; you run `npm run dev`, open a browser, click **Initialise Foundry Local**, **Add Model**, **Load Model**, then **Run Benchmark**.

Concretely, the backend (see `src/server/benchmark.js:89-184`, `runSingleInference`) issues OpenAI-compatible chat completions through the embedded Foundry Local web service:

```javascript
const stream = await client.chat.completions.create({
  model: modelName,
  messages: [{ role: 'user', content: scenario.prompt }],
  max_tokens: scenario.max_tokens || 100,
  temperature: config.temperature || 0.7,
  stream: true
}, { signal: controller.signal });
```

For each scenario it iterates N times, captures token timestamps from the SSE stream, computes percentiles, polls `systeminformation` for CPU/RAM/GPU utilisation, and writes everything to `results/storage.json` (or SQLite if `better-sqlite3` builds successfully).

The "default" suite is one file: `benchmarks/suites/default.json`. It contains nine **very short** prompts ("What is the capital of France?", "Explain how photosynthesis works", etc.) with `max_tokens` between 50 and 300. There is no system prompt support and no notion of a multi-turn conversation. Suite definitions are pure JSON, so adding new scenarios is trivial:

```json
{
  "name": "edge-negotiator-hot-path",
  "scenarios": [
    { "name": "intersection-A-rush",
      "prompt": "<our 1500-token traffic-state prompt>",
      "max_tokens": 30 }
  ],
  "default_config": { "iterations": 50, "streaming": true, "timeout": 60000 }
}
```

It is — bluntly — a thin, well-instrumented OpenAI-streaming-client wrapper with a chart UI on top, locked specifically to Foundry Local as its inference backend.

---

## 2. What models does it benchmark?

**Out of the box, FLPerformance supports anything in the Foundry Local catalog**, queried at runtime via `manager.catalog.getModels()` (see `src/server/orchestrator.js:107`). It does not ship a hard-coded model list.

The Foundry Local catalog (Microsoft-curated) at the time of writing includes mainly: phi-3-mini-4k-instruct, phi-3.5-mini, phi-4, qwen2.5-0.5b/1.5b/3b/7b, qwen2.5-coder variants, llama-3.2-1b/3b, mistral-7b, deepseek-r1-distill variants. Variants are pre-baked for CPU (`*-generic-cpu:N`), CUDA GPU (`*-cuda-gpu:N`), and sometimes Qualcomm NPU.

**Direct relevance to the Edge Negotiator's locked architecture:**

| Our model | Foundry Local catalog status |
|-----------|------------------------------|
| **Qwen3-4B** | NOT in the standard Foundry Local catalog at present. Foundry Local ships qwen2.5 series (0.5B, 1.5B, 3B, 7B). Qwen3 family is newer than the catalog snapshot. |
| **Phi-4-mini (3.8B)** | Foundry Local ships `phi-4` (14B) and `phi-3.5-mini` (3.8B). Phi-4-mini specifically may or may not be in the catalog depending on Microsoft's update cadence; closest equivalent in the existing storage is `phi-3.5-mini`. |
| **Traffic-R1 Public 0.1** | Definitively NOT in the catalog. It is a third-party fine-tune on HuggingFace, not a Microsoft-blessed model. |

**Workaround paths for non-catalog models:**

1. The **Cache tab** (`src/server/cacheManager.js`, `cacheManager.listCacheModels`) can scan an alternate directory of ONNX models. If Qwen3-4B or Traffic-R1 are converted to the Foundry Local on-disk layout (publisher subdirectory + `foundry.modelinfo.json`), they appear in the model list. This requires the model to be in **ONNX format**, packaged the way Foundry expects — which is non-trivial and is the primary friction.
2. Failing that, one would have to either (a) wait for Microsoft to add them to the catalog, or (b) bypass FLPerformance entirely and use the native runtime for that model (llama.cpp/Ollama for Qwen3-4B; Hugging Face Transformers for Traffic-R1).

The repo's own `results/storage.json` shows two models actually benchmarked on the author's machine: **`qwen2.5-0.5b`** and **`phi-3.5-mini`**, both via `*-generic-cpu` variants on a Snapdragon X Elite. Phi-3.5-mini is the nearest stand-in we have for our Phi-4-mini target.

---

## 3. What metrics does it report?

The aggregation logic in `src/server/benchmark.js:272-317` produces a fixed set of per-scenario aggregates:

| Metric | Source | Notes |
|--------|--------|-------|
| `tps` (overall tokens/sec) | total tokens / total wall time | End-to-end including TTFT |
| `ttft` (ms) | first stream chunk timestamp − request start | Streaming only; reports **median** TTFT (line 303), not mean |
| `tpot` (ms) | mean of inter-token deltas | Streaming only; raw deltas preserved in `interTokenDelays` |
| `gen_tps` | 1000 / TPOT | Pure generation throughput (excludes TTFT) |
| `latency_p50/p95/p99` (ms) | percentile of end-to-end latencies | Calculated using `Math.ceil((p/100)*N) - 1` indexing |
| `error_rate`, `timeout_rate` | failures / iterations × 100 | Percentages |
| `cpu_avg`, `ram_avg`, `gpu_avg` | `systeminformation` snapshot mean | `gpu_avg` is null on machines where GPU utilisation is not exposed (Qualcomm Adreno on Snapdragon shows null) |
| `total_tokens`, `total_iterations`, `successful_iterations` | counters | Per scenario |

**Critically absent:**
- **No structured-output reliability metric.** There is no JSON-schema validation, no constrained decoding, no `response_format` parameter — the prompt is sent as plain user text and the response body is discarded after token counting (line 130-148). For the Edge Negotiator we need to measure whether the SLM actually emits parseable JSON; FLPerformance provides no such hook.
- **No power/energy.** No watt readings, no battery-drain, no NVIDIA `nvidia-smi --query-gpu=power.draw`. Important if Lee Stott's interest is "CPU vs GPU power efficiency".
- **No GPU memory.** `vram` is captured once at run start as a static hardware fact (`src/server/benchmark.js:62-69`) but VRAM utilisation during inference is not tracked.
- **No prompt-length sweep.** All scenarios use a single hard-coded prompt; no parametric study over input length.
- **No faithfulness probe.** Output content is not even examined.
- **`raw_data` is preserved** (per-iteration `interTokenDelays` array, line 263 storage), so post-hoc statistical analysis is possible — useful for re-computing P95/P99 with our preferred percentile method if needed. Confirmed by inspecting `results/storage.json`: every iteration has a full `interTokenDelays` array.

---

## 4. Hardware coverage

`getHardwareInfo` (`src/server/benchmark.js:47-81`) records:
- CPU manufacturer/brand/cores/physicalCores
- Total RAM in GB
- GPU controller[0] model + VRAM
- OS platform/distro/release/arch

**On the developer-laptop class:** the existing `results/storage.json` was produced on:
```
CPU: Snapdragon X Elite X1E78100 (12 cores)
RAM: 32 GB
GPU: Qualcomm Adreno X1-85 (vram: 0 MB reported, gpu_avg: null in results)
OS: Windows 11 ARM64
```

That is **the wrong hardware class for our dissertation** (ARM64 Snapdragon, no CUDA), but it proves the harness runs on a consumer laptop. On an **RTX 3060/4060 Mobile + x64**, all paths work because (a) Foundry Local has CUDA execution providers, (b) `systeminformation` reads NVIDIA GPUs cleanly through nvml and exposes `utilizationGpu`, and (c) Foundry Local's CUDA variants will be the default for models that have one.

**Verdict:** Yes, this runs on our laptop. The code path is identical regardless of whether the chosen model variant runs on CPUExecutionProvider or CUDAExecutionProvider — that choice is made when the catalog returns a variant (`info.runtime.deviceType` and `info.runtime.executionProvider`, see `orchestrator.js:165`). The metrics layer is hardware-agnostic.

The only real concern: the example results show `gpu_avg: null` on Qualcomm. We need to verify on RTX-class hardware that `si.graphics().controllers[0].utilizationGpu` is populated (it should be — `systeminformation` queries nvml on Windows when an NVIDIA driver is present).

---

## 5. CPU-only inference

Foundry Local catalogs each model with multiple **variants** keyed by execution provider: `*-generic-cpu:N` for CPU, `*-cuda-gpu:N` for CUDA, `*-qnn-npu:N` for Qualcomm NPU. The actual storage shows the author benchmarked the **CPU variants** explicitly:

```
foundry_id: "qwen2.5-0.5b-instruct-generic-cpu:4"
foundry_id: "Phi-3.5-mini-instruct-generic-cpu:1"
deviceType: "CPU"
executionProvider: "CPUExecutionProvider"
```

Real measured numbers on Snapdragon CPU from `results/storage.json` (qwen2.5-0.5b, "Simple Q&A - Short", 5 iterations):
- TTFT median: **620 ms**
- TPOT mean: **51.4 ms** (so generation rate ≈ 19 tok/s)
- Overall TPS: **12.9** (dragged down by TTFT)
- p50 latency: 1099 ms; p95: 3737 ms

**For the Edge Negotiator's targets:**
- **Hot-path target ~10 ms.** A 620 ms TTFT on a 0.5B CPU model is **62× over budget** before generating a single output token. Even on a Phi-4-mini class model the TTFT on CPU will be hundreds of ms minimum. Conclusion FLPerformance can validate: CPU-only inference cannot meet a 10 ms hot-path target with current SLMs at our prompt sizes — and FLPerformance is exactly the right instrument to demonstrate that empirically and quantitatively.
- **Audit-path target ~500 ms.** With 50 ms/token CPU generation, a 50–200 token CoT JSON would take 2.5–10 s. Again, FLPerformance can produce the evidence quickly.

**Yes, FLPerformance measures CPU performance** — that is the variant the author chose for his own benchmarks. It is well-suited to "characterise CPU-only feasibility", which directly answers Lee Stott's question about CPU vs GPU. The natural experiment: load the same model under both `*-generic-cpu` and `*-cuda-gpu` aliases and compare. The QUICK_START Pro Tip explicitly recommends this:
```
3. Compare NPU vs CPU:
   - Load two models with unique aliases:
     - phi-3.5-mini-npu (NPU device)
     - phi-3.5-mini-cpu (CPU device)
   - Run benchmark with both selected
```

---

## 6. Foundry Local dependency

**FLPerformance is hard-bound to Foundry Local.** Specifically:
- `package.json` lists `foundry-local-sdk: ^0.9.0` as a dependency.
- `orchestrator.js` constructs `FoundryLocalManager.create({ appName: 'FLPerformance' })` and calls `manager.startWebService()`. There is no abstraction layer over inference engines.
- The OpenAI client is pointed at `${manager.urls[0]}/v1` with `apiKey: 'foundry-local'`. While the API surface is OpenAI-compatible, the URL is owned by the Foundry Local runtime.
- `cacheManager.js` reads `~/.foundry/foundry.config.json` for cache path resolution.
- The bootstrap code in `src/server/index.js:792-797` calls `orchestrator.initialize()` on server startup; if Foundry Local is not installed, the entire backend logs `Foundry Local initialization failed` and most endpoints become unusable.

**Cannot benchmark via llama.cpp, Ollama, vLLM, or ONNX Runtime directly.** It is theoretically possible to repoint the OpenAI client's `baseURL` at any OpenAI-compatible server (Ollama at `:11434/v1`, llama.cpp's `--host`, vLLM, LM Studio, text-generation-webui, etc.) by editing `orchestrator.js:55-58`, but:
- The model lifecycle (`loadModel`, `unloadModel`, `getModelInfo`) all assume Foundry Local's catalog API — those would need rewriting against Ollama's `/api/tags` or equivalent.
- The Cache tab assumes Foundry's on-disk layout.
- Effort to convert into an engine-agnostic harness: **realistically 1–2 days of focused refactoring** (replace the orchestrator with a thin HTTP wrapper around any OpenAI-compatible endpoint; gut the catalog/cache code).

For our purposes: if Qwen3-4B and Traffic-R1 ever land in Foundry Local, this works as-is. Otherwise we either fork the orchestrator or run two harnesses in parallel.

---

## 7. Direct use for the Edge Negotiator

Walking through the four sub-questions:

**(a) Profile Qwen3-4B and Phi-4-mini latency on the laptop with our actual prompt templates (~500–2000 input tokens, ~30–80 output tokens)?**
- *Phi-4-mini:* If `phi-4-mini` (or `Phi-3.5-mini` as a near-substitute) is in the Foundry catalog on x64 Windows + CUDA, **yes, immediately** — copy our real prompt into a custom suite JSON, set `max_tokens: 80`, set `iterations: 50`, run.
- *Qwen3-4B:* Almost certainly **not without conversion work**. Foundry Local ships qwen2.5 not qwen3. We would either benchmark `qwen2.5-3b-instruct` as the closest available stand-in, or take the Qwen3-4B ONNX build (if one exists) and place it in a custom cache directory recognised by Foundry's filesystem layout. Both are imperfect.

For long input prompts (1500+ tokens): the harness sends them straight through the OpenAI client with no truncation, so this works mechanically. But the suite JSON does not support multi-line prompts elegantly — practical workaround is to load suites programmatically or just embed the prompt as a single-line string with `\n` escapes.

**(b) Compare CPU vs GPU performance for the same model?**
- **Yes, cleanly.** Add the same model with two aliases (`phi-3.5-mini-cpu`, `phi-3.5-mini-cuda`), select both in the Benchmarks tab, run. Side-by-side comparison cards appear automatically. This is one of the headline use cases the author optimised for.

**(c) Characterise the latency-budget headroom for hot-path and audit-path designs?**
- **Yes, with caveats.** Per-iteration TTFT and inter-token delay arrays are preserved in `raw_data` (verified by inspecting `results/storage.json`). We can reconstruct any percentile for our dissertation Section 3, including tail behaviour.
- **Caveat 1:** The harness measures TTFT including network overhead between Node.js and the Foundry web service (loopback HTTP), which adds maybe 1–3 ms — negligible for our budgets but worth noting.
- **Caveat 2:** No support for very-short outputs like a single phase ID token. With `max_tokens: 1` the TPOT array is empty — but TTFT is still captured, which is what matters for a single-token hot-path decision.

**(d) Generate the latency distribution for §3 of our experimental design (offline profiling, then injection into TraCI step delays)?**
- **Yes, this is its strongest use case.** Run 100+ iterations per scenario, export to JSON, parse the per-iteration arrays, fit a distribution (or just sample empirically), inject sampled delays into TraCI `step()` calls. The export format (`/api/benchmarks/runs/:id/export/json`) gives you everything needed in one file.

---

## 8. Implementation lessons

Concrete patterns worth lifting into our own harness regardless of whether we use FLPerformance directly:

1. **Streaming-based TTFT measurement** (`benchmark.js:121-148`). The pattern of "first chunk with `delta.content` ≠ empty" is the right way to measure TTFT against any OpenAI-compatible server — many naive harnesses use `time-to-first-byte` which is wrong because the server emits the SSE preamble before any model token.

2. **Inter-token delay capture as a raw array** (line 256). Storing every delta rather than a pre-aggregated mean/variance lets you re-cut the distribution later. We should mirror this for our experiments.

3. **Hardware fingerprint per run** (`getHardwareInfo`, `benchmark.js:47-81`). Stamping CPU/GPU/RAM/OS into every result makes cross-run comparison defensible — a small effort for big reproducibility wins. Lift this verbatim.

4. **Resource snapshot before/after each iteration** (line 234-241). Good for proving "GPU was actually being used" or detecting CPU thermal throttle across long runs.

5. **AbortController + timeout wrapper** (line 101-105) for inference deadlines. Clean cancellation pattern.

6. **The "Test before benchmark" idiom** (`POST /api/models/:id/test`, `index.js:279-344`). One inference call as a smoke test before committing to a multi-hour benchmark — saves enormous wasted time. Our harness should do the same.

7. **Suite-as-JSON, not code** (`benchmarks/suites/default.json`). Lets non-developers (us, three months from now) tweak prompts without editing source.

8. **The percentile indexing convention** (`benchmark.js:16-20`) uses `Math.ceil((p/100)*N) - 1` which is the "nearest-rank" method. This biases slightly conservative for small N. For our paper we should pick a percentile method explicitly (linear interpolation, R-7, etc.) and stick with it consistently.

---

## 9. Risks

1. **Foundry Local lock-in.** The single biggest risk. If our locked SLMs are not in the Foundry catalog, the harness needs surgery or replacement. Qwen3-4B and Traffic-R1 are both at risk here.

2. **No structured-output measurement.** The Edge Negotiator's hot path emits CFG-constrained JSON via XGrammar, and the audit path emits structured JSON CoT. FLPerformance measures latency but says nothing about whether the output parses, schema-validates, or matches the grammar. We will need a separate test for this — either bolted on to the benchmark engine (modify `runSingleInference` to attempt `JSON.parse` on the response and increment a `valid_json` counter) or run as a follow-up offline analysis.

3. **No prompt-length parametric sweep.** Our experimental design needs latency-vs-input-tokens curves. FLPerformance has no facility for this; you would run it nine times with nine different suites or write a script to drive the REST API with parametric scenarios.

4. **CUDA availability detection is not explicit.** The harness chooses whichever variant the catalog selects, and reports `executionProvider`. There is no failure-fast check that says "you asked for CUDA but only CPU variants are available". We could end up benchmarking CPU thinking we are benchmarking GPU.

5. **Web-UI-centric.** The recommended workflow is "click buttons in the browser". Reproducible CI-style runs need REST automation (the BLOGPOST shows the pattern but no scripts ship). For our dissertation we want scripted, reproducible runs from a single command.

6. **First-inference warmup contamination.** Foundry's first inference includes model load into VRAM, JIT compilation, kernel warmup. This shows clearly in the storage data: iteration 1 had TTFT=923ms vs iteration 2 onwards 547–633ms. The harness does not separate warmup iterations. We must add a warmup loop or discard iteration 1 in post-processing.

7. **No NVML power readings.** Our dissertation may want power-per-token. The harness does not provide this; would need an `nvidia-smi` poller alongside.

8. **No Azure dependency** — the `@azure/identity` package in `package.json` is unused by the runtime code (likely vestigial). Confirmed by Grep: no imports of `@azure/identity` in `src/`. So at least there is no cloud login required.

9. **Snapdragon ARM64 caveat documented in `architecture.md:289-313`**: Foundry Local v0.8.117 has a known issue where the service starts but does not accept HTTP connections on ARM64. Not relevant to our x64 RTX 3060/4060 laptop, but worth knowing.

---

## 10. Concrete recommendation

**(b) Adapt for our use case** — specifically, **use it as the primary latency-profiler for any Foundry-supported model on our laptop**, but write a thin parallel harness (or contribute one back) for the structured-output reliability and prompt-length-sweep questions it cannot answer.

Justification: FLPerformance is the closest off-the-shelf tool we will find for "OpenAI-compatible streaming inference benchmark on a developer laptop with a clean visual UI". It already does the hardest parts well (TTFT measurement, percentile latency, raw inter-token delay capture, CPU-vs-GPU comparison via aliasing, JSON+CSV export, hardware fingerprinting). It is roughly half a day of effort to add custom traffic-control prompt suites; it would be a week to build the equivalent from scratch. The two genuine gaps — non-Foundry models like Traffic-R1, and structured-output validity — are both small enough to address with auxiliary scripts rather than abandoning the tool. For the parts we *can* use it for (Phi-3.5-mini as a Phi-4-mini stand-in; qwen2.5-3b as a Qwen3-4B stand-in; CPU-vs-CUDA variant comparison; latency distribution capture for TraCI injection) it is excellent.

---

## Practical bootstrap: exact commands to start benchmarking on the user's machine

The user is on an RTX 3060/4060 mobile, x64 Windows. Assumed: Node.js 22 already installed (visible from earlier shell output).

### Step 1: Install Foundry Local
```powershell
winget install Microsoft.FoundryLocal
foundry --version   # confirm install
```

### Step 2: Install FLPerformance dependencies
```powershell
cd e:\desktop\assignments\dissertation\02-experiments\FLPerformance
npm install --no-optional
cd src\client
npm install
cd ..\..
mkdir results -Force
```

### Step 3: Verify Foundry catalog has what we need
```powershell
foundry model list
# Look for: phi-3.5-mini, phi-4-mini (if present), qwen2.5-3b, qwen2.5-coder-3b
# Note both -generic-cpu and -cuda-gpu variants
```

### Step 4: Start the app
```powershell
.\START_APP.ps1
# Browser opens to http://localhost:3000
```

### Step 5: Replace the default suite with an Edge-Negotiator suite

Create `benchmarks/suites/edge-negotiator-hot-path.json`:
```json
{
  "name": "edge-negotiator-hot-path",
  "description": "Hot-path single-token phase decision",
  "scenarios": [
    {
      "name": "intersection-light-traffic-1500tok",
      "prompt": "<paste real Edge Negotiator hot-path prompt, ~1500 tokens>",
      "max_tokens": 1
    },
    {
      "name": "intersection-heavy-traffic-2000tok",
      "prompt": "<paste real Edge Negotiator hot-path prompt, ~2000 tokens>",
      "max_tokens": 1
    }
  ],
  "default_config": { "iterations": 100, "concurrency": 1, "timeout": 60000, "temperature": 0.0, "streaming": true }
}
```

Create a parallel `edge-negotiator-audit-path.json` with `max_tokens: 200` for the CoT JSON.

### Step 6: Add the same model twice for CPU vs GPU comparison

In the UI Models tab:
- **Add Model** → alias `phi-3.5-mini-cpu`, model_id `Phi-3.5-mini-instruct-generic-cpu:1`
- **Add Model** → alias `phi-3.5-mini-cuda`, model_id `Phi-3.5-mini-instruct-cuda-gpu:1` (exact ID depends on what the catalog reports)
- Click **Load** on both. **Click Test on each** — confirm a real response comes back before benchmarking.

### Step 7: Run the suite

In the Benchmarks tab:
- Select both models (CPU and CUDA variants).
- Select the `edge-negotiator-hot-path` suite.
- Iterations: 100. Streaming: on. Timeout: 60000.
- Click **Run Benchmark**.
- Estimated wall time: a few minutes for 100 iterations × 2 scenarios × 2 models on a hot-path scenario; longer for audit path.

### Step 8: Pull results for analysis

Either click **Export JSON** in the Results tab, or via REST:
```powershell
$run = Invoke-RestMethod -Method Post -Uri http://localhost:3001/api/benchmarks/run -ContentType 'application/json' -Body '{ "modelIds":["..."], "suiteName":"edge-negotiator-hot-path", "config":{ "iterations":100, "streaming":true } }'
$runId = $run.runId
# Poll status until completed
do { Start-Sleep -Seconds 5; $st = Invoke-RestMethod "http://localhost:3001/api/benchmarks/runs/$runId/status" } while ($st.status -eq 'running')
Invoke-RestMethod "http://localhost:3001/api/benchmarks/runs/$runId/export/json" -OutFile "edge-negotiator-hotpath-$(Get-Date -Format yyyyMMdd-HHmmss).json"
```

The exported JSON contains the per-iteration `interTokenDelays` arrays — feed these into NumPy for the distribution our §3 needs.

### Step 9: Discard iteration 1 of every scenario

Add a warmup discard step in our analysis script. Iteration 1 always includes JIT/load overhead (visible in the existing `results/storage.json` data: 923ms vs subsequent 547–633ms TTFT).

### Step 10: For the structured-output reliability question

FLPerformance does not measure this. Build a 100-line parallel script that hits Foundry Local's OpenAI endpoint directly with the same prompts, parses each response with `JSON.parse` inside a try/catch, and counts validity. Reuse our suite JSON as the prompt source so the two harnesses stay in sync.

---

## Key file paths referenced

- `e:\desktop\assignments\dissertation\02-experiments\FLPerformance\src\server\benchmark.js` — the benchmark engine (the only file we would patch for structured-output checks)
- `e:\desktop\assignments\dissertation\02-experiments\FLPerformance\src\server\orchestrator.js` — Foundry Local SDK wrapper (the file to fork if we ever want to point at Ollama/vLLM)
- `e:\desktop\assignments\dissertation\02-experiments\FLPerformance\src\server\cacheManager.js` — cache directory layout reader (relevant for ONNX-converted custom models)
- `e:\desktop\assignments\dissertation\02-experiments\FLPerformance\src\server\index.js` — REST API surface (drives automation from PowerShell/Python)
- `e:\desktop\assignments\dissertation\02-experiments\FLPerformance\benchmarks\suites\default.json` — suite schema example to copy
- `e:\desktop\assignments\dissertation\02-experiments\FLPerformance\results\storage.json` — actual benchmark data from the author's Snapdragon machine (proves the harness produces the metrics we need)
- `e:\desktop\assignments\dissertation\02-experiments\FLPerformance\results\example\benchmark-example.json` — schema of the export format we will feed into our analysis pipeline
- `e:\desktop\assignments\dissertation\02-experiments\FLPerformance\AGENTS.md` — concise SDK v0.9.0 quirks reference (helpful if we patch the orchestrator)
- `e:\desktop\assignments\dissertation\02-experiments\FLPerformance\BLOGPOST.md` — author's narrative including the cautionary tale about phi-4 (8.5GB) running 31× slower than qwen2.5-coder-0.5b on a VRAM-constrained machine — directly relevant to our laptop sizing decisions
