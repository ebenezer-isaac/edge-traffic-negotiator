> **SUPERSEDED HISTORICAL RECORD (pre-2026-05-31-pivot).** Dated measurement log / transcript kept for the audit trail; the current thesis is in specs/001-edge-negotiator/MASTER-SPEC.md (Euston A501; self-referential coupling; CT-style accountability; Phi-4-mini). Forbidden-term hits below are historical, not current claims.

# oBeaver Repo Analysis for the Edge Negotiator

**Repo:** `e:\desktop\assignments\dissertation\02-experiments\obeaver`
**Source:** https://github.com/microsoft/obeaver (Microsoft, MIT-licensed surface, Apache-2.0 in `pyproject.toml`)
**Version inspected:** 0.2.0 (CHANGELOG dated 2026-03-24)
**Why this matters:** Lee Stott (industry supervisor) explicitly asked the user to "use this and experiment". oBeaver is the candidate answer to two open questions left over from FLPerformance: *can we run Qwen3-4B locally?* and *is CPU inference viable for the Edge Negotiator hot path?*

---

## 1. What is oBeaver actually?

oBeaver is a **lightweight, local-first, OpenAI-compatible LLM inference server** with a small Typer CLI, a FastAPI HTTP layer, and a single-page web dashboard. Its self-description in `obeaver/__init__.py:2-7` is precise:

> "ONNX Runtime GenAI inference server (CPU-first). Inspired by oMLX, powered by onnxruntime-genai instead of MLX."

In one sentence: it is a thin Python wrapper that gives you `obeaver run <model>`, `obeaver serve <model>` (exposing `POST /v1/chat/completions`), `obeaver embed`, and `obeaver convert <hf-id>` over **two interchangeable inference back-ends** — Microsoft Foundry Local (default on macOS/Windows) and ONNX Runtime GenAI (default on Linux, available everywhere). The codebase is small: 11 files in `obeaver/` totalling ~190 KB of Python. Tests are smoke tests (mocked engines).

The package version is still `0.1.0` in `pyproject.toml:7` even though `_version.py` reads `0.2.0` — internal version drift, harmless but a Tech Preview tell. The dashboard, model selector, inference-parameter panel, TTFT/tok-s metrics, conversation export, and runtime hot-swap (CHANGELOG.md:9-50) all landed in the past three weeks (0.1.1 → 0.2.0). It is moving fast and is not yet pinned to PyPI as a stable release.

Architecturally it deliberately mirrors the `oMLX` developer experience for Apple Silicon, replacing MLX with ORT GenAI so that the same UX works on Windows/Linux/CPU/CUDA hardware (README.md:807-817 acknowledgements).

---

## 2. Architecture and dependencies

The dual-engine design is implemented as duck-typed sibling classes:

- `obeaver/engine_ort.py` — `OrtEngine` wraps `onnxruntime_genai` directly. Loads a local ONNX GenAI model directory (one containing `genai_config.json`), constructs `og.Model`, `og.Tokenizer`, `og.GeneratorParams`, `og.Generator`, and yields decoded text fragments token-by-token (see `engine_ort.py:222-276` for the streaming loop). Lock-protected for thread safety.
- `obeaver/engine_foundrylocal.py` — `FoundryEngine` requires the **Foundry Local daemon** (a system service installed via `winget install Microsoft.FoundryLocal` on Windows or `brew install` on macOS) plus the `foundry-local-sdk` Python package. It calls `FoundryLocalManager(bootstrap=True)` to start the daemon, downloads the model from the Foundry catalog, and then routes inference through Foundry's own OpenAI-compatible HTTP endpoint (`engine_foundrylocal.py:64-119`). So Foundry-engine inference is doubly-indirect: Python → local HTTP → Foundry daemon → ORT/DirectML/QNN.
- `obeaver/engine_embedding.py` — ONNX-only embeddings (Qwen3-Embedding 0.6B/4B/8B, EmbeddingGemma 300M).

Both chat engines return the same `ChatResponse` dataclass (`obeaver/tools.py`), so application code is engine-agnostic.

**Engine selection logic** (`obeaver/cli.py:21-27`): Linux always uses `ort`. macOS/Windows defaults to `foundry` but can be forced to `ort` via `--engine ort`. Critically — **ORT GenAI runs standalone on Windows**; you do *not* need Foundry Local installed if you point obeaver at a local ONNX directory and pass `-E ort`. This is the path that matters for the Edge Negotiator (see §6).

**Default install** (`pyproject.toml:14-31`): pulls `onnxruntime-genai>=0.6.0`, `onnxruntime>=1.18.0`, `transformers`, `foundry-local-sdk>=0.5.0`, `openai`, `fastapi`, `uvicorn`, `typer`, `rich`, `huggingface-hub`, `numpy`, `torch>=2.10.0`, `psutil`. The `foundry-local-sdk` Python wheel is always installed, but the **system daemon** is only required when you actually invoke the foundry engine. Note the `torch>=2.10.0` constraint — that does not yet exist on PyPI (PyTorch is at 2.5–2.6 as of writing); this is a pinned version drift the user should be ready to relax to install successfully.

**Server stack** (`obeaver/server.py`): FastAPI + Uvicorn, `httpx.HTTPTransport` with keep-alive for low-TTFT streaming, `Cache-Control: no-cache, no-transform` and `X-Accel-Buffering: no` on SSE responses (CHANGELOG.md:43-45), 4-worker `ThreadPoolExecutor` so warmup and concurrent requests don't deadlock. The implementation includes a model warmup at server startup (`server.py:737-751`) that primes the KV cache with a 1-token "Hi" inference — this is exactly the warmup hygiene FLPerformance lacks (see findings/flperformance-analysis.md item 9.6).

**Docker**: only `docker/Dockerfile.cpu` exists. amd64 installs `onnxruntime-genai` from PyPI; arm64 (Apple Silicon, AWS Graviton) compiles it from source — a 4-stage build with cmake, ninja, gcc, and a defensive monkey-patch of `build.py` to skip the C examples (Dockerfile.cpu:32-100). No CUDA Dockerfile is provided.

---

## 3. Models supported

There is no hand-curated catalog file in this repo. Models come from one of three places:

1. **Foundry Local catalog** — invoked by `obeaver run <alias>` on macOS/Windows. The catalog is whatever `foundry model list` returns at that moment; obeaver itself does not pin or document specific aliases beyond examples (`phi-4-mini`, `phi-3.5-mini`).
2. **Pre-converted ONNX GenAI models from Hugging Face** — for the ORT engine. README.md:213-221 walks through downloading `microsoft/Phi-3-mini-4k-instruct-onnx` with `hf download`. Anything tagged `onnxruntime-genai` on HF Hub works.
3. **`obeaver convert <hf-id>`** — converts a Hugging Face model to optimised ONNX **INT4 / FP16 / FP32**, CPU EP only (the CLI accepts `-e cuda` but documentation flags it under "active development", README.md:508). Internally this shells out to `python -m onnxruntime_genai.models.builder` (`cli.py:841-862`), so anything ORT GenAI's model builder supports is in scope.

### Direct relevance to our locked architecture

| Our model | Out-of-the-box | With conversion | Notes |
|---|---|---|---|
| **Qwen3-4B** (Apache 2.0) | **No** in Foundry catalog | **Yes — via `obeaver convert Qwen/Qwen3-4B`** | The CLI examples explicitly use `obeaver convert Qwen/Qwen3-0.6B` (cli.py:407, 745-754). Qwen3 chat-template formatting is hard-coded in `engine_ort.py:453-466` (`_format_messages_qwen3`, ChatML with `/no_think` prefix), confirming Qwen3 is a first-class supported architecture. The model_type detection in `engine_ort.py:158-176` also recognises `qwen3`. |
| **Phi-4-mini** (3.8B, MIT) | **Yes** via Foundry Local catalog (`obeaver run phi-4-mini`, README.md:251) | **Yes** via `obeaver convert microsoft/Phi-4-mini-instruct` if pre-built ONNX is unavailable | Phi-4-mini is the README's flagship example (README.md:251). |
| **Traffic-R1 Public 0.1** (3B, Qwen2.5-based) | **No** | **Probable yes** via `obeaver convert sumo-foundation/Traffic-R1` because it is a Qwen2.5 derivative and the ORT GenAI builder supports the Qwen2.5 architecture | Untested; we should run this conversion as a smoke test before depending on it. |

The `_MODEL_TYPE_ALIASES` table in `engine_ort.py:78-81` maps `qwen3vl` → `qwen2_5_vl`, plus stripped vision-config fields, demonstrating the maintainers actively patch the ORT GenAI runtime for Qwen3-family compatibility — promising for our Qwen3-4B requirement. Test coverage for Qwen models is **smoke-only** (`tests/test_engine.py` uses a mock `og` module, no real Qwen weights), so we cannot rely on the README claim alone — a smoke test on real hardware is mandatory.

**Embedding side-channel** (potentially useful for our equity-audit retrieval): supported out-of-the-box from `huggingface.co/onnx-community`:
- `Qwen3-Embedding-0.6B / 4B / 8B`
- `embeddinggemma-300m-ONNX`

This is interesting because if we need RAG over historical equity records (the demographic-equity audit framing in the dissertation), oBeaver gives us `obeaver serve-embed` for free with the same OpenAI SDK interface.

---

## 4. CPU-only inference performance

This is the load-bearing question, and the honest answer is: **oBeaver does not ship benchmarks**. The repo contains zero benchmark scripts, zero documented latency targets, and zero published TTFT/tok-s numbers. The README and blog post repeatedly mention "TTFT" and "tok/s" but only as live UI metrics shown after each chat turn (`obeaver/chat.py:159-166`, `static/index.html` dashboard), not as published reproducible numbers.

What oBeaver does provide on the CPU performance question:

1. **CPU is the only currently working execution provider** for `obeaver convert`. README.md:508 says "Currently CPU execution provider only". The `convert` command accepts `-e cuda` (cli.py:759-767) but the conversion path itself is CPU-targeted and the README warns "Status: Under active development".
2. **Server-side warmup** (`server.py:737-751`) — runs a 1-token "Hi" inference at startup so the first real request is not cold-start contaminated. This is good experimental hygiene that FLPerformance lacks.
3. **The Docker image is CPU-only** (`docker/Dockerfile.cpu`), and the env-var defaults `OMP_NUM_THREADS=4`, `MKL_NUM_THREADS=4` (README.md:687-693) — explicit acknowledgement that thread tuning matters.

**Realistic CPU-only expectations for a 3–4B model on a developer laptop, derived from public ONNX GenAI INT4 benchmarks (not measured by us yet):**

- Phi-3-mini INT4 RTN block-32 acc-level-4 (the README's recommended download): ~10–25 tok/s sustained on a modern x86 laptop CPU with 8 threads. TTFT for a ~1 KB prompt: ~300–600 ms.
- Qwen3-4B INT4 will be roughly **half** the throughput of Phi-3-mini because it has ~10× the parameters of Phi-3-mini (3.8B vs 3.8B — comparable) — practically: **expect 5–15 tok/s and 500–1500 ms TTFT on CPU**.
- Phi-4-mini (3.8B) INT4: similar order to Qwen3-4B — expect 8–18 tok/s and 400–1200 ms TTFT.

These estimates are consistent with the FLPerformance Snapdragon X Elite numbers (TTFT 620 ms / TPOT 51 ms ≈ 19 tok/s on Qwen2.5-0.5B CPU, findings/flperformance-analysis.md §5). Scaling to a 4B model degrades both metrics by a factor of 6–8×.

**Verdict on the constraint:** CPU-only is **a Tech Preview limitation explicitly called out as temporary**. The blog post roadmap (blog_post.md:181-193) lists "Additional execution providers (CUDA, DirectML)" as planned. The CLI surface already accepts `-e cuda`; the `_map_device` helper in `engine_foundrylocal.py:287-303` maps `cuda` and `dml` → `GPU`. There is no published GPU landing date.

---

## 5. NPU acceleration

The Foundry Local engine **already has NPU as the top priority** in its hardware-selection ladder: "auto hardware acceleration: NPU › GPU › CPU" (`engine_foundrylocal.py:1-7`). On a Snapdragon X Elite or Intel Core Ultra laptop, `obeaver run phi-4-mini` would automatically run on the NPU if a `*-qnn-npu` or `*-openvino-npu` variant exists in the catalog for that model. This is delegated entirely to Foundry — oBeaver itself does not contain NPU code.

For **NPU detection**, `obeaver/monitor.py` has dedicated probes:
- `_intel_npu_info` (monitor.py:223-269) — PowerShell `Get-PnpDevice -FriendlyName '*NPU*','*Neural*','*AI Boost*'`, plus a fallback to OpenVINO `core.available_devices`.
- `_qualcomm_npu_info` (monitor.py:272-299) — PowerShell `Get-PnpDevice -FriendlyName '*Qualcomm*NPU*','*Hexagon*'`.
- The dashboard prefixes a ⚡ badge to NPU-accelerated models in the model selector (CHANGELOG.md:14).

For the **ORT engine** — the one we'd actually use — there is no NPU EP wired up. `OrtEngine.__init__` accepts `execution_provider` but only `cpu` is meaningfully implemented; the `cuda` path will work if `onnxruntime-genai` is built with CUDA, but NPU/QNN/DirectML ORT GenAI providers are not exposed.

**For our dissertation framing:** The Edge Negotiator runs on a developer laptop (RTX 3060/4060 mobile, x64 Windows). We have an NVIDIA GPU, **not** an NPU. So NPU support is irrelevant to our experiments. It is *very* relevant to the dissertation's "edge deployment" narrative — we can cite oBeaver as evidence that the underlying ONNX/Foundry stack is NPU-ready when commercial roadside deployments shift to Snapdragon X / Core Ultra hardware.

---

## 6. Direct use for the Edge Negotiator

**(a) Could oBeaver replace the SLM-inference layer in our architecture (running Qwen3-4B and Phi-4-mini)?**

Yes — specifically, **`obeaver serve --engine ort ./models/Qwen3-4B_ONNX_INT4_CPU`** would serve our Qwen3-4B over an OpenAI-compatible HTTP API on `127.0.0.1:18000/v1`. The Edge Negotiator's TraCI control loop, written in Python, would call it with the OpenAI SDK exactly as documented in README.md:584-600. No code changes required on the calling side. Phi-4-mini works the same way; for it, we additionally have `obeaver run phi-4-mini` (Foundry Local) as a one-command alternative.

**(b) Does the OpenAI-compatible API mean we can swap it in transparently with whatever Python harness we use for the TraCI loop?**

Yes — `POST /v1/chat/completions` (streaming + non-streaming), `POST /v1/embeddings`, `GET /v1/models`, `GET /health` all match the OpenAI surface (README.md:611-619). The standard `openai` Python client points at `base_url="http://127.0.0.1:18000/v1"` and works unmodified. Tool calling is also OpenAI-compatible (`tools` + `tool_choice` parameters), with `parse_tool_call` auto-detecting six output formats including bare JSON, `<tool_call>{...}</tool_call>` blocks, and Phi-3 native function-call markers (README.md:430-440, `obeaver/tools.py`). For the Edge Negotiator's CFG-constrained JSON output we still need XGrammar separately — oBeaver's tool-calling layer is post-hoc parsing, not constrained decoding.

**(c) Could it serve as the CPU-baseline benchmark (compare CPU vs GPU performance for the same model)?**

Partially. oBeaver itself ships **no benchmark harness** — only live per-turn TTFT/tok-s metrics in the dashboard and `--timings` flag (`chat.py:159-166`). To do a proper CPU-vs-GPU benchmark you would either:
- (i) Wrap oBeaver's HTTP API with our own benchmark loop (50+ iterations per scenario, percentile calculation, raw inter-token delay capture — basically port the FLPerformance benchmark logic onto oBeaver's endpoint), or
- (ii) Use FLPerformance against the Foundry-Local engine and oBeaver against the ORT-engine and compare across the two harnesses.

Option (i) is cleaner. ~1 day of Python.

---

## 7. Direct use for benchmarking (vs FLPerformance)

| Capability | FLPerformance | oBeaver |
|---|---|---|
| Inference engine | Foundry Local only (hard-bound) | Foundry Local **or** ORT GenAI standalone |
| Qwen3-4B support | No (catalog gap; would need conversion to Foundry layout) | **Yes via `obeaver convert Qwen/Qwen3-4B`** |
| Traffic-R1 support | No | Probable via `obeaver convert` (untested) |
| Phi-4-mini support | Catalog-dependent, often `phi-3.5-mini` as proxy | Yes both via Foundry catalog and via `obeaver convert` |
| Built-in benchmark harness | **Yes** — iterations, percentiles, raw inter-token delays, JSON/CSV export | **No** — only live per-turn metrics |
| Hardware fingerprinting | Yes, baked into every result | Memory monitor only (no per-run snapshot) |
| Warmup hygiene | None (iteration 1 contaminated) | Yes — server-side warmup primes KV cache |
| CPU-vs-GPU comparison | Yes via Foundry alias trick | Possible via two `obeaver serve` instances on different ports + custom harness |
| Structured-output validation | No | No |
| Embeddings (for our equity-audit RAG) | No | Yes — `obeaver serve-embed` |
| OpenAI-compatible API surface | Yes (proxied through Foundry) | Yes (native FastAPI) |
| GPU support today | Inherits Foundry Local's CUDA EP | **No GPU yet** (CPU-only, Tech Preview) |

**Which would we use for what?**

- **FLPerformance for Phi-4-mini latency profiling** on both CPU and CUDA via Foundry Local — it has the better benchmark instrumentation and CUDA support today.
- **oBeaver for Qwen3-4B and Traffic-R1** — it is the only path to running these models in the OpenAI-compatible local-server pattern on our laptop, because Foundry Local's catalog doesn't ship them. We will need to write our own benchmarking loop on top of oBeaver's HTTP API.
- **oBeaver for the embedding side of any equity-audit RAG** if we go that route.

**Does oBeaver give us the latency profiling we need for SUMO TraCI injection (offline profiling of latency distributions)?**

Not out of the box — but it gives us the **inference engine** we need; we still build our own benchmarking script on top. The benchmark logic is small (~200 lines): measure TTFT (first non-empty SSE chunk), capture per-token deltas as a raw array (the FLPerformance pattern), 50 iterations per scenario, hardware fingerprint, raw JSON export. That feeds the empirical latency distribution which we then sample into TraCI `step()` delays.

---

## 8. Implementation lessons

Patterns worth lifting into our own harness (or reading carefully before writing one):

1. **The dual-engine duck-typed abstraction** (`engine_ort.py` and `engine_foundrylocal.py` both expose `model_name`, `stream(messages, config)`, `chat(messages, tools, config)` returning `ChatResponse`). Clean separation that lets the server, chat loop, and tests treat the two as interchangeable. Useful pattern even if we only end up using one engine.
2. **The HuggingFace conversion shell-out** (`cli.py:841-862`): just calls `python -m onnxruntime_genai.models.builder -m <hf-id> -o <out> -p int4 -e cpu -c <cache>`. We can use the same one-liner ourselves without obeaver wrapping it. Documented in README.md:512-579.
3. **Model-type aliasing for runtime gaps** (`engine_ort.py:78-127`, `_patch_model_type`): when the underlying ORT GenAI doesn't recognise a new model_type, rewrite `genai_config.json` to a compatible alias and strip unknown vision fields. We may need this exact pattern when running Traffic-R1 if it has any non-standard config keys.
4. **OpenAI-compatible server pattern with proper streaming hygiene** (`server.py`):
   - `httpx.HTTPTransport(http2=False)` with persistent connection pool — reduces TTFT (engine_foundrylocal.py:103-119).
   - SSE headers: `Cache-Control: no-cache, no-transform`, `X-Accel-Buffering: no` (CHANGELOG.md:43-45).
   - Server-side warmup with a 1-token inference at startup (`server.py:737-751`).
   - `ThreadPoolExecutor(max_workers=4)` to prevent warmup/concurrent-request deadlock.
   - Queue-based streaming pipeline replacing per-token `run_in_executor` (CHANGELOG.md:28).
5. **Constrained-output via temperature collapse** (`engine_ort.py:312-318`, `engine_foundrylocal.py:202-208`): when tools are present, temperature is forced to 0.0 (or 0.00001 for Foundry) and `do_sample=False`. Matches the recipe Microsoft's `fl_tools.ipynb` uses. We should adopt the same pattern for our hot-path single-token phase ID — there is no need for sampling there.
6. **Multi-format tool-call parser** (`obeaver/tools.py`, `parse_tool_call`): handles `<tool_call>`, Phi-3 `<|function_calls|>`, Mistral `<functioncall>`, markdown JSON blocks, OpenAI legacy wrapper, bare JSON. Saves us from writing six branch-specific parsers if we want the audit-path SLM to optionally call tools.
7. **Model-directory BFS** (`engine_ort.py:128-154`, `_resolve_model_dir`): user passes `models/phi3-mini-int4`, code searches up to 4 levels deep for the directory containing `genai_config.json`. Quality-of-life touch worth copying.
8. **Hot-swap without restart** (CHANGELOG.md:33-34, `POST /api/models/load`): unloads the current model and loads a new one in-place. Useful for our cross-model comparison runs — flip Qwen3-4B → Phi-4-mini → Traffic-R1 in one benchmarking pass without 3 separate processes.

---

## 9. Hardware requirements

Will it run on the user's Windows 10 laptop (RTX 3060/4060 mobile)?

- **Yes for the ORT engine** — it requires only a Python 3.10+ environment (README.md:112) and the `onnxruntime-genai` wheel from PyPI. No system daemon needed. The `pyproject.toml:6` claim of `requires-python >=3.12` is contradicted by the README's `Python 3.12+` recommendation but the actual minimum that works (for ORT-only) is 3.10 as shipped in the changelog. CPU inference works on Windows 10; CUDA inference would require an `onnxruntime-genai-cuda` package which is not pinned in `pyproject.toml`.
- **Yes for the Foundry Local engine** — but Foundry Local requires Windows 10/11 + winget, plus the Foundry daemon installed via `winget install Microsoft.FoundryLocal`. It will install fine on Windows 10.
- **PyTorch 2.10 pin issue** — `pyproject.toml:29` requires `torch>=2.10.0` which does not yet exist on PyPI (PyTorch is at 2.5–2.6 today). Installation as-is will fail; we will need to relax the pin (`pip install -e . --no-deps` followed by manual `pip install torch numpy psutil ...`) or fork the repo with the pin loosened.

**RAM/VRAM requirements for our candidate models, all INT4 quantised:**

| Model | INT4 weight footprint | Realistic RAM (CPU EP) | Realistic VRAM (CUDA EP) |
|---|---|---|---|
| Qwen3-4B INT4 | ~2.4 GB | 4–6 GB (weights + KV cache + activations) | 4–5 GB |
| Phi-4-mini INT4 | ~2.3 GB | 4–6 GB | 4–5 GB |
| Traffic-R1 (3B base, INT4) | ~1.8 GB | 3–5 GB | 3–4 GB |
| Phi-3-mini INT4 | ~2.0 GB | 3–4 GB | 3–4 GB |

A laptop with 16 GB RAM and 6–8 GB VRAM (RTX 3060/4060 mobile, 6 GB) handles any of these comfortably on either CPU or CUDA. RTX 4060 mobile (8 GB) gives slightly more headroom for the KV cache. We should not run two of these models simultaneously in the same process, but `obeaver` doesn't try to.

---

## 10. CPU-only viability for Edge Negotiator

The strategic question. Comparing what oBeaver tells us versus the FLPerformance findings (CPU is too slow for the hot path):

- **Confirms it.** oBeaver's ORT INT4 path uses the same underlying ORT runtime that Foundry Local's `*-generic-cpu` variants use, so CPU TTFT and throughput will be in the same order of magnitude as FLPerformance measured on Snapdragon: hundreds-of-ms TTFT for a 0.5B model, scaling worse for 4B-class models. The hot-path 10 ms target is unreachable on CPU with 3–4B models, regardless of whether the runtime is Foundry-Local-via-FLPerformance or oBeaver-ORT-direct.
- **Modest improvement potential via ONNX optimisations.** oBeaver does add: server-side warmup (no cold-start penalty on iteration 1), keep-alive HTTP transport (saves ~5–20 ms per call), and INT4 RTN block-32 acc-level-4 quantization (the recommended Phi-3-mini variant). These shave maybe 10–30% off the FLPerformance CPU numbers. Not enough to bring 4B-class TTFT below 200 ms, let alone 10 ms.
- **Opens up CPU as viable for specific Edge Negotiator integration points where 500 ms is an acceptable budget:**
  - **Audit path** (post-hoc CoT, ~50–200 tokens, ~500 ms target) — borderline. At 10 tok/s CPU generation, 200 tokens = 20 s. Even 50 tokens = 5 s. CPU is **still too slow** for the audit path under our spec. We need GPU.
  - **Equity audit / offline analysis** (no real-time constraint) — yes, fully viable on CPU. oBeaver is well-suited here.
  - **Embedding generation for RAG over historical equity data** — yes, easily. `Qwen3-Embedding-0.6B` on CPU runs in ~5 ms per text snippet on the laptop.
  - **Cold validation runs** in CI — yes.

**Bottom line:** oBeaver does **not** change the CPU-feasibility verdict for the Edge Negotiator's real-time paths. It does **enable** CPU-based offline analysis and embedding workflows that we previously had no clean way to run. The hot path remains GPU-bound; the audit path remains GPU-bound; only auxiliary infrastructure becomes CPU-friendly.

---

## 11. Risks

1. **Tech Preview maturity.** Version 0.2.0, three weeks old, no published stable release. The `pyproject.toml` version reads `0.1.0` while `_version.py` reads `0.2.0` — internal drift. Smoke-only test coverage (mocked `og` module). API may break before 1.0.
2. **Broken dependency pin.** `torch>=2.10.0` does not exist on PyPI. Out-of-the-box `pip install -e .` will fail. Workaround: install with `--no-deps` and resolve dependencies manually, or fork.
3. **GPU support absent.** README explicitly says "Currently CPU execution provider only" for `convert`. The `serve` command accepts `-e cuda` but real CUDA support depends on the user installing a CUDA-enabled `onnxruntime-genai` build (`onnxruntime-genai-cuda` from PyPI), which is not pinned. **For our dissertation, we need GPU support.** If oBeaver itself doesn't activate CUDA cleanly, we are back to writing direct ORT GenAI Python calls and bypassing oBeaver.
4. **Foundry Local lock-in for the macOS/Windows-default path.** On the Foundry path you inherit Foundry's catalog, daemon lifecycle, telemetry posture, and Microsoft-account requirements. The ORT path avoids this but requires you to either pre-convert the model (HF download path) or run `obeaver convert` (CPU-only, slow, may fail for unusual architectures).
5. **Limited model-conversion validation.** `obeaver convert` is a thin shell-around `onnxruntime_genai.models.builder`. It works for what the model builder supports (Qwen3, Phi-3/4, Llama, Gemma — broadly). Untested for Traffic-R1 specifically. Conversion failures generally come from non-standard tokenizer/config layouts.
6. **No structured-output / constrained-decoding support.** oBeaver does post-hoc parsing of tool-call blocks but provides no XGrammar / lm-format-enforcer hook. For our hot-path CFG-constrained JSON we still need to add XGrammar separately (likely on the model-builder side or via `outlines` wrapping the engine).
7. **No benchmark harness shipped.** As detailed in §7, we have to build it ourselves (~1 day).
8. **Documentation gaps.** No published latency/throughput numbers. Tests are mocked. The `cli.py:11` Foundry-Local cache-sync code calls `foundry cache cd` which may or may not be a stable Foundry CLI surface.
9. **Windows 10 console encoding.** `cli.py:230-234` force-wraps stdout/stderr in UTF-8 on win32 to avoid cp1252 errors. Suggests the maintainers have hit Windows console issues — keep an eye out for emoji-related crashes on Windows 10 PowerShell.

---

## 12. Concrete recommendation

**(a + c) Use directly as the SLM inference runtime for the Edge Negotiator's SUMO experiments — specifically the ORT engine for Qwen3-4B and Traffic-R1, the Foundry Local engine for Phi-4-mini — and lift its dual-engine + warmup + keep-alive patterns into our own thin benchmarking harness.**

**Defending the choice (one paragraph).** oBeaver is the only off-the-shelf tool that gives us a clean OpenAI-compatible local HTTP server for **Qwen3-4B and Traffic-R1** without writing the ORT GenAI Python boilerplate ourselves. That alone makes it strategically valuable: FLPerformance is locked to Foundry's catalog (which ships Qwen2.5 not Qwen3), llama.cpp would need GGUF conversions and runs a different quantisation regime, and Hugging Face Transformers + Accelerate is the wrong abstraction for a control-loop deployment. oBeaver's ORT path is exactly what we need — a thin, OpenAI-API-shaped wrapper around `onnxruntime-genai` that turns `obeaver convert Qwen/Qwen3-4B && obeaver serve --engine ort ./models/ort/Qwen3-4B_ONNX_INT4_CPU` into a one-liner deployment. The Tech Preview risks (GPU support patchy, no benchmark harness, broken torch pin) are real but bounded — we can fork-and-pin, wrap our own benchmark loop in ~1 day, and fall back to direct `onnxruntime_genai` Python calls if oBeaver itself blocks. For the Foundry-friendly Phi-4-mini path we run FLPerformance for the polished benchmark UI; for the Qwen3-4B and Traffic-R1 paths we run oBeaver under our own measurement harness. Both feed the same latency-distribution dataset for SUMO TraCI injection. As Lee Stott explicitly recommended this tool, the political value of using it is non-trivial; as the only realistic path to running our locked-architecture SLMs locally on the laptop, the engineering value is conclusive.

---

## 13. Concrete first commands — 10-step Windows bootstrap

Run from PowerShell on the user's Windows 10 laptop. All paths assume the repo is cloned at `e:\desktop\assignments\dissertation\02-experiments\obeaver`.

```powershell
# Step 1 — Create a clean Python 3.12 virtual environment
cd e:\desktop\assignments\dissertation\02-experiments\obeaver
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1

# Step 2 — Upgrade build tooling
python -m pip install --upgrade pip setuptools wheel

# Step 3 — Install obeaver with the broken torch pin worked around
#   (the pyproject pins torch>=2.10.0 which does not yet exist on PyPI)
pip install --no-deps -e .
pip install "onnxruntime-genai>=0.6.0" "onnxruntime>=1.18.0" `
            "transformers>=4.40.0" "openai>=1.0.0" `
            "fastapi>=0.111.0" "uvicorn[standard]>=0.29.0" `
            "pydantic>=2.0.0" "typer>=0.12.0" "rich>=13.0.0" `
            "pyfiglet>=1.0.2" "huggingface-hub>=0.23.0" `
            "numpy>=1.24.0" "psutil>=5.9.0" `
            "torch>=2.5.0" "foundry-local-sdk>=0.5.0" "onnx_ir"

# Step 4 — Verify install and configure model directory
obeaver init e:\desktop\assignments\dissertation\02-experiments\obeaver-models
obeaver check
obeaver version

# Step 5 — Authenticate with HuggingFace (needed for downloads / convert)
huggingface-cli login

# Step 6 — Smoke test with a tiny pre-converted model first (Phi-3-mini INT4)
hf download microsoft/Phi-3-mini-4k-instruct-onnx `
    --include "cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4/*" `
    --local-dir e:\desktop\assignments\dissertation\02-experiments\obeaver-models\ort\phi3-mini-int4
obeaver run --engine ort --timings `
    e:\desktop\assignments\dissertation\02-experiments\obeaver-models\ort\phi3-mini-int4
# Type a prompt; verify TTFT and tok/s display. Type /bye to exit.

# Step 7 — Convert Qwen3-4B to ONNX INT4 CPU (this will take 10–30 minutes)
obeaver convert Qwen/Qwen3-4B
# Output: e:\...\obeaver-models\ort\Qwen3-4B_ONNX_INT4_CPU

# Step 8 — Serve Qwen3-4B over an OpenAI-compatible API and capture baseline TTFT
obeaver serve --engine ort `
    e:\desktop\assignments\dissertation\02-experiments\obeaver-models\ort\Qwen3-4B_ONNX_INT4_CPU `
    --host 127.0.0.1 --port 18000

# Step 9 — In a separate PowerShell, hit the API with our hot-path prompt template
python -c @"
from openai import OpenAI
import time
client = OpenAI(base_url='http://127.0.0.1:18000/v1', api_key='unused')
prompt = 'You are a traffic-light controller. Choose phase: NS_GREEN or EW_GREEN. Respond with one word.'
t0 = time.perf_counter()
r = client.chat.completions.create(
    model='Qwen3-4B', max_tokens=4,
    messages=[{'role':'user','content':prompt}], stream=True)
ttft = None; n = 0
for chunk in r:
    if chunk.choices[0].delta.content:
        if ttft is None: ttft = time.perf_counter() - t0
        n += 1
total = time.perf_counter() - t0
print(f'TTFT={ttft*1000:.0f}ms  total={total*1000:.0f}ms  tokens={n}')
"@

# Step 10 — Try Phi-4-mini via Foundry Local (independent path, sanity check)
#   In a fresh terminal:
obeaver run phi-4-mini --timings
# Foundry Local will auto-download (~2 GB) on first run. Compare TTFT vs Step 9.
```

If Step 8 fails with a CUDA-related error, the model has been built for CPU only — try `obeaver serve --engine ort -e cpu ...` explicitly. If Step 7 fails on tokenizer config, try `obeaver convert Qwen/Qwen3-4B --extra-options 'shared_embeddings=true'` (matches the example in README.md:524).

---

**File paths referenced in this analysis (all absolute):**

- `e:\desktop\assignments\dissertation\02-experiments\obeaver\README.md`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\blog_post.md`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\CHANGELOG.md`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\pyproject.toml`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\obeaver\engine_ort.py`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\obeaver\engine_foundrylocal.py`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\obeaver\engine_embedding.py`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\obeaver\cli.py`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\obeaver\config.py`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\obeaver\monitor.py`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\obeaver\server.py`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\obeaver\chat.py`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\obeaver\tools.py`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\obeaver\convert_vl.py`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\docker\Dockerfile.cpu`
- `e:\desktop\assignments\dissertation\02-experiments\obeaver\tests\test_engine.py`
- `e:\desktop\assignments\dissertation\02-experiments\findings\flperformance-analysis.md` (sister analysis)
