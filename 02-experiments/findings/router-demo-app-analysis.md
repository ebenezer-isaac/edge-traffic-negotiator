# router-demo-app — Analysis for the Edge Negotiator dissertation

**Repo:** `e:\desktop\assignments\dissertation\02-experiments\router-demo-app`
**Origin:** https://github.com/leestott/router-demo-app
**Reviewer date:** 2026-04-16
**Verdict (TL;DR):** Ignore as a code dependency. Borrow the **measurement harness pattern** if anything.

---

## 1. What does it do?

It is a **single-page React + TypeScript web app** that fires the same prompt at two Azure OpenAI deployments side-by-side and renders a comparison table. One deployment is Microsoft Foundry's `model-router` (a hosted "intelligent dispatcher" that picks an underlying GPT model per request); the other is a fixed standard deployment (default `gpt-5-nano`).

Concretely, on a button click the app:

1. POSTs the prompt to `${endpoint}/openai/deployments/model-router/chat/completions` and to the same path with `gpt-5-nano` (`src/hooks/useCompletion.ts:74-88`).
2. Reads the `response.model` field, which Foundry populates with the model the router actually selected (`useCompletion.ts:102-103`).
3. Calculates an estimated USD cost from a hard-coded per-1K-token price table (`src/config/pricing.ts:1-14`, `calculateCost()` at lines 16-35).
4. Aggregates latency, token count, cost, and a per-model histogram in a `useMemo` reducer (`src/hooks/useResults.ts:15-47`).
5. Renders four metric cards, a Recharts bar chart of model distribution, and a results table.

The app ships **10 hand-crafted benchmark prompts** in `src/config/prompts.ts` ranging from "classify a customer review" (simple, ~50 tokens) to a long API-spec analysis prompt (~3,500 tokens). It also has a free-text "Custom Prompt" panel (`src/components/PromptSelector.tsx:39-89`) capped at 50,000 characters. There is a `Routing Mode` dropdown (`balanced` | `cost` | `quality`) but the value is **not actually sent in the API body** — the README admits routing mode must be configured in the Foundry Portal and the dropdown is purely informational (`App.tsx:121-123`, README line 217).

The companion `BLOG_POST.md` is a marketing piece with sample numbers (router ~$0.029 vs standard ~$0.030 over 10 prompts, ~4.5% saving in Balanced mode).

## 2. Architecture and dependencies

**Stack (`package.json`):** React 19, TypeScript 5.9, Vite 7, Tailwind CSS 4, Recharts 3, Playwright (devDep, used only for screenshot capture). No backend, no database, no inference code — every dependency is a UI library or a build tool.

**Where things run:**

- **Browser (client-only).** All API calls originate from the user's browser via `fetch` in `useCompletion.ts:74`. There is no server in this repo.
- **Azure cloud.** Both endpoints (`VITE_ROUTER_ENDPOINT`, `VITE_STANDARD_ENDPOINT`) are required to be `https://<resource>.cognitiveservices.azure.com` (see `.env.example` lines 6, 12). The `model-router` deployment, the `gpt-5-nano` deployment, and the routing decision logic itself all live in **Azure Foundry / Azure OpenAI**.
- **Pricing data.** Pulled from `modelmeters.com` (a community mirror of the Azure Retail Prices API) by `scripts/update-pricing.mjs:27-28`, baked into `src/config/pricing.ts` at build time.

**Authentication.** Hard-keyed: API keys are loaded from `VITE_*` env vars and shipped into the browser bundle. The README and `endpoints.ts:1-13` explicitly call this out as acceptable for "local development and personal demos only" — for production the recommendation is to proxy through a backend and use Managed Identity. **This means even running the demo requires you to expose live Azure keys to your browser.**

**The "router" itself is opaque.** All routing logic — prompt complexity analysis, model selection, mode handling — happens server-side inside Foundry. This repo just observes `response.model` after the fact.

## 3. Direct use for the Edge Negotiator

**No.** It is unusable as-is. Specific blockers:

| Edge Negotiator requirement | router-demo-app reality |
|---|---|
| Local inference on developer laptop (RTX 3060/4060) | Pure cloud: every call hits Azure |
| Qwen3-4B and Phi-4-mini as the SLMs | Hard-wired to Azure-hosted GPT-4.1, GPT-5, gpt-oss-120b, llama-4-maverick, deepseek-v3 (`src/config/pricing.ts:3-12`) |
| No cloud dependency for the dissertation | Will not start without `VITE_ROUTER_ENDPOINT` + API key (`useCompletion.ts:49-51`) |
| Hot-path latency budget (one signal cycle, sub-second) | Reported router latency ~7,500-7,800 ms (README line 243); the demo has a **60 second** timeout (`useCompletion.ts:10`) |
| CFG-constrained JSON via XGrammar | Standard chat completion with no grammar/structured output enforcement |
| Single-token phase ID output | `max_completion_tokens: 1024` (`useCompletion.ts:84`) |
| Z3 SMT safety verifier integration | Not present; routing is fire-and-forget |
| MaxPressure deterministic fallback | No fallback logic; an `AbortError` is just shown as a red banner (`App.tsx:147-151`) |

To "rewire" it, you would have to replace the entire `useCompletion.ts` (the only meaningful logic file, ~140 lines) with calls to a local inference server (vLLM / llama.cpp / Ollama), strip the pricing module (irrelevant for local models), throw out `model-router` entirely, and reimplement the routing decision yourself. At that point you have rewritten the app — only the React UI scaffolding (which you don't need anyway, since the dissertation evaluation is in SUMO, not a web UI) survives.

## 4. Implementation lessons

**The "borrow ideas in spirit" question, taken seriously:**

### 4a. Could a Foundry Model Router pattern route between Qwen3 thinking-mode and non-thinking-mode based on traffic-state complexity?

**The pattern is conceptually transferable. The Foundry implementation is not.** Foundry's router is itself a trained classifier model running on Azure that adds ~500-1,500 ms of dispatch latency before the chosen model even starts generating (inferred from the README's reported ~7,800 ms router latency vs ~6,100-7,700 ms standard). For the Edge Negotiator's hot path, **paying any second-model dispatch tax is fatal** — you would be doubling your latency before producing a phase ID.

A lighter pattern that fits the dissertation: a **single deterministic gate** (e.g. `vehicle_count > N || queue_imbalance > T || pedestrian_request`) that flips Qwen3 between `/no_think` and `/think` modes via the system prompt switch Qwen3 supports natively. This is a plain `if` statement, not a learned router. Cost is microseconds, the decision is auditable, and Z3 can verify the gate condition itself. The router-demo-app does not implement or even discuss this pattern — its routing is a black-box hosted service.

### 4b. Could it route between Qwen3-4B and Phi-4-mini based on latency budget?

**The repo demonstrates the comparison harness, not the routing logic.** The useful lesson is the *measurement* shape: same prompt → two endpoints → record `{model, latencyMs, totalTokens, content}` → aggregate (`useResults.ts:15-47`). That data shape is reusable for benchmarking Qwen3-4B against Phi-4-mini in your dissertation chapter on model selection. But the *decision* of which to route to is again hosted-only and not exposed.

A latency-budget router for two local models is trivial to build standalone: time-box the primary call with a deadline, fall back to the secondary on timeout. That pattern is well-documented in real-time inference literature (deadline scheduling, anytime algorithms). You do not need this repo to implement it.

### 4c. Is the routing logic local or cloud-dependent?

**100% cloud-dependent.** There is zero routing code in this repo. `useCompletion.ts` does one HTTP POST to Azure and reads `data.model` from the response. The actual routing brain (the trained dispatcher model) is an Azure Foundry service that you cannot inspect, modify, or run locally. This is the single biggest disqualifier for the Edge Negotiator: the dissertation is explicitly local-only.

## 5. Benchmarking relevance

**Limited but non-zero.** The repo gives you:

- A **template for a side-by-side comparison harness** — the `useResults.ts:15-47` reducer pattern (router results / standard results, avg latency, total cost, distribution histogram) maps cleanly to "Qwen3-4B vs Phi-4-mini on N traffic scenarios". You could lift the data shape (`CompletionResult` interface in `src/types/index.ts:11-24`) verbatim, swap `chosenModel` for `modelVariant`, and adapt.
- A **prompt-set design idea** — categorising prompts by complexity (`simple` | `medium` | `complex` | `long-context`, `src/types/index.ts:6`) is a structure you should mirror for traffic scenarios (e.g. `low-flow` | `peak-flow` | `incident` | `pedestrian-heavy`).

But it does **not** answer "which model is best for our use case" because:

1. The benchmarked models (GPT-4.1, GPT-5, etc.) are not in your candidate set.
2. The benchmarked tasks (classification, code debug, travel planning) bear no resemblance to discrete-choice traffic-phase selection under a 100ms-class deadline.
3. The reported metrics (USD cost, total tokens, end-to-end latency including TLS round-trip to Azure datacentres) are not the metrics that matter for SUMO simulation (decision quality, conformance to safety constraints, time-to-first-token on local GPU).

## 6. Hardware requirements and latency

**Hardware:** Just a developer machine running Node 18+. No GPU. No specific RAM requirement. Inference happens entirely on Azure-hosted hardware which is not characterised anywhere in the repo.

**Latency benchmarks:** The README (lines 240-258) and `BLOG_POST.md` (lines 110-148) report:

- Avg router latency: ~7,800 ms (Balanced), ~6,800 ms (Quality)
- Avg standard latency: ~7,300-8,300 ms

These are **end-to-end browser → Azure → browser** numbers, dominated by network RTT, queueing, and the chosen GPT model's generation time for ~1024-token outputs. They are not isolated inference latencies and are **three orders of magnitude too slow** for the Edge Negotiator's hot path. The repo provides **zero data** on tokens-per-second, time-to-first-token, or any latency decomposition.

## 7. CPU-only inference

**Not supported, not discussed, not relevant.** A grep for `cpu`, `local`, `ollama`, `gguf`, `qwen`, `phi`, `llama.cpp`, `onnx`, or `inference` across the entire source tree returns nothing meaningful — the only `cpu` hits are platform tags inside `package-lock.json` for native Vite/Tailwind binaries. The app contains no inference code at all. Every model invocation is an HTTPS call to Azure-hosted endpoints, where the underlying compute (presumably GPU clusters in Azure datacentres) is invisible to the client.

If Lee Stott specifically asked about CPU inference, **this repo does not address that question in any way**. You would need to look at separate Microsoft repos (DirectML, ONNX Runtime, or the Phi cookbook) for CPU-inference guidance — those are different codebases.

## 8. Risks

- **Azure subscription required.** You cannot run the demo without an Azure account, a Foundry project, a `model-router` deployment, and at least one standard model deployment. All three cost money per token (`VITE_ROUTER_API_KEY` and `VITE_STANDARD_API_KEY` are mandatory — `useCompletion.ts:49-51` throws if missing).
- **Vendor lock-in.** The entire "intelligent routing" value proposition lives inside Foundry. There is no portable artefact.
- **Client-side API keys.** The repo bakes Azure API keys into the browser bundle (`endpoints.ts:1-13` warns about this explicitly). For a dissertation it is irrelevant; flagging because it is a published Microsoft-affiliated demo recommending a pattern that is unsafe outside local-dev.
- **Routing opacity.** The `BLOG_POST.md` admits (line 171) that you can see *which* model was chosen but not *why*. For a dissertation that needs auditability (Z3 verification, post-hoc CoT), an opaque hosted dispatcher is a non-starter.
- **Quoted savings are unimpressive.** ~4.5% in Balanced mode (README line 244) on a tiny prompt set, with high run-to-run variance explicitly disclaimed (BLOG_POST line 102). Not a strong evidential base.
- **Licence is fine.** MIT (`LICENSE` file). No legal blocker, but there is essentially nothing to copy.
- **Stale-by-design.** Pricing has to be re-fetched manually; model menu shifts as Azure adds/removes models.

## 9. Concrete recommendation

**(c) Ignore — but note one transferable pattern.**

This repository is a marketing-flavoured demo for an Azure-only managed service. It demonstrates a hosted dispatcher pattern that is fundamentally incompatible with the Edge Negotiator's three locked constraints: **local-only execution**, **sub-second hot-path latency**, and **auditability via Z3**. Foundry's router is a black-box second model whose own dispatch latency would dominate any phase-decision deadline; its routing logic cannot be inspected, verified, or run on a developer laptop; and the SLMs in scope (Qwen3-4B, Phi-4-mini) are not even in its catalogue. The single transferable artefact is the *shape* of the side-by-side measurement harness in `src/hooks/useResults.ts:15-47` and the `CompletionResult` type in `src/types/index.ts:11-24` — a useful template to mirror when you build the Qwen3-vs-Phi-4 benchmark chapter, but ~30 lines of TypeScript that you would type from scratch in less time than it takes to fork the repo. **Do not adopt; do not subclass; do not depend.** If asked, cite it in the related-work section as "an example of cloud-hosted intelligent routing" and contrast it against the dissertation's local-deterministic-gate approach in one paragraph.
