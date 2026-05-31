# Runbook 03 — Qwen3 via ORT Engine (Without HF Authentication)

**Date:** 2026-04-16
**Goal:** Run Qwen3 family models locally without paying the HF-auth cost of `obeaver convert`.

---

## The Authentication Blocker

`obeaver convert Qwen/Qwen3-0.6B` requires Hugging Face authentication. Even for **public** Qwen3 models, the underlying `huggingface_hub` library (via the `transformers` dependency chain) raises `LocalTokenNotFoundError`:

```
huggingface_hub.errors.LocalTokenNotFoundError: Token is required (`token=True`),
but no token found. You need to provide a token or be logged in to Hugging Face
with `hf auth login` or `huggingface_hub.login`.
```

This is a hard blocker for `obeaver convert`. The user has not yet provided an HF personal access token.

## The Workaround — Pre-converted ONNX Builds

**Key insight:** `hf download` (the new HF CLI) works **without authentication** for public files. It just shows a rate-limit warning. So if a community has already published an ORT GenAI–compatible ONNX build of the model, we can grab it directly.

The community repo to look for is one with a `genai_config.json` file at the root. Search query that worked:
```
huggingface "Qwen3-4B" "genai_config.json" onnxruntime-genai
```

**For Qwen3-0.6B, the working repo is:** `onnx-community/Qwen3-0.6B-DQ-ONNX`

For Qwen3-4B (the dissertation's primary SLM), pre-converted ORT GenAI builds in the `onnx-community/` namespace are not currently published. Candidates worth investigating later:
- `lokinfey/Qwen3-1.7B-ONNX-INT4-CPU` — intermediate data point (1.7B)
- `EmbeddedLLM/` collection — community provider for ORT GenAI builds
- Or use `obeaver convert Qwen/Qwen3-4B` once HF auth is configured

---

## Two Required Patches to a Pre-converted Repo

The `onnx-community/Qwen3-0.6B-DQ-ONNX` `genai_config.json` is **WebGPU-targeted by default** and the model file is in a subdirectory. Two edits are needed before oBeaver can serve it:

### Patch 1 — Replace WebGPU provider options

```json
"session_options": {
    "log_id": "onnxruntime-genai",
    "provider_options": [
        { "webgpu": { "forceCpuNodeNames": "/model/embed_tokens/Gather" } }
    ]
},
```

becomes:

```json
"session_options": {
    "log_id": "onnxruntime-genai",
    "provider_options": []
},
```

(empty `provider_options` defaults to CPU)

### Patch 2 — Fix model filename path

The repo has the model at `onnx/model_q4f16.onnx`, but `genai_config.json` says:

```json
"filename": "model.onnx",
```

becomes:

```json
"filename": "onnx/model_q4f16.onnx",
```

Pick the variant you want from the available `.onnx` files in the `onnx/` subfolder. `model_q4f16` is INT4 weights with FP16 KV cache — good CPU choice.

---

## Steps to Repeat

```bash
# 1. Download (no HF auth needed for public ONNX repos)
hf download onnx-community/Qwen3-0.6B-DQ-ONNX \
  --local-dir e:/desktop/assignments/dissertation/02-experiments/models/ort/Qwen3-0.6B-DQ-ONNX

# 2. Apply both patches to genai_config.json (see above)

# 3. Serve via ORT engine
obeaver serve --engine ort \
  e:/desktop/assignments/dissertation/02-experiments/models/ort/Qwen3-0.6B-DQ-ONNX

# 4. Hit http://127.0.0.1:18000/v1/chat/completions with any OpenAI-compatible client
```

---

## Latency Results — Qwen3-0.6B-DQ-ONNX on CPU (ORT engine)

| Path | TTFT median | Total median | Decode median | Output tokens | Notes |
|------|-------------|--------------|----------------|----------------|-------|
| Hot-path (single-token request) | **1,538 ms** | 1,794 ms | 14.1 tok/s | **5 tokens** (because of `<think></think>` markers) | Phase IDs all valid (0–3) |
| Audit-path (~100-token CoT) | 1,383 ms | 11,180 ms | 10.4 tok/s | 64–167 (variable) | Reasoning quality acceptable |

---

## Important Finding — Qwen3 Thinking-Mode Markers Affect "Single-Token" Output

Even when the prompt explicitly requested only the phase number, Qwen3-0.6B emitted:

```
<think>

</think>

3
```

That's **5 tokens**, not 1. Because Qwen3 in thinking mode always wraps reasoning in `<think>...</think>` markers — even when there is no reasoning, it emits empty markers.

**Implication for the Edge Negotiator's locked architecture:**
- The "single-token phase ID hot path" budget assumed direct output
- Qwen3's thinking-mode markers add 4 tokens of overhead per request
- Two options:
  1. **Disable thinking mode** for the hot path (Qwen3 supports this via prompt format `<|im_start|>...<|im_end|>` without enabling thinking) — get true single-token output
  2. **Strip the markers** in post-processing and account for the latency cost of generating them
  3. **Move to non-thinking-mode by default** for the hot path; reserve thinking-mode for the audit path

This is exactly the kind of architectural adjustment Prompt 3's "five conditions for CoT logging" anticipated. The decoupling of hot-path (no CoT, single-token) and audit-path (full CoT) maps cleanly onto Qwen3's `enable_thinking=False` vs `enable_thinking=True` modes — but **only if we use the prompt format correctly**.

---

## Output Quality Comparison

Qwen3-0.6B vs qwen2.5-0.5b on the same hot-path prompt:

| Model | All outputs | Out-of-range / garbage |
|-------|-------------|------------------------|
| qwen2.5-0.5b (CPU, Foundry) | "2", "1", "3", "CB", "4", "0", "2", "1", "2", "1" | **3 of 10 wrong** ("CB", "4" out-of-range) |
| Qwen3-0.6B (CPU, ORT) | "3", "2", "0", "2", "0", "2", "0", "3", "0", "0", "2", "2" | **0 of 10 wrong** (all in 0–3) |

**Even at 0.6B, Qwen3 produces structurally sound output every time.** This validates Qwen3 as the locked primary SLM choice — the family appears to have better instruction-following at small parameter counts than Qwen2.5.

---

## Path to Qwen3-4B

Three options, in order of effort:
1. **Find a pre-converted Qwen3-4B-ORT-GenAI build.** `onnx-community/` may publish one in the future, or check `lokinfey/`, `EmbeddedLLM/`, `microsoft/` namespaces.
2. **Set up HF auth and run `obeaver convert Qwen/Qwen3-4B`.** Requires user to create HF token at https://huggingface.co/settings/tokens, then `hf auth login` or `export HF_TOKEN=...`. Conversion takes 30–60 minutes on CPU plus disk space.
3. **Use Qwen3-1.7B as an intermediate proxy** (download `lokinfey/Qwen3-1.7B-ONNX-INT4-CPU`, repeat the patch-and-serve workflow). Provides scaling data between 0.6B and 4B without needing HF auth.

For the next session, recommendation: **option 3 first** (no auth needed, gives us a 1.7B data point), then option 2 (proper Qwen3-4B once HF auth is set up).
