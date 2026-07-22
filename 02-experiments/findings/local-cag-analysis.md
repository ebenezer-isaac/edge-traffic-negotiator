> **SUPERSEDED HISTORICAL RECORD (pre-2026-05-31-pivot).** Dated measurement log / transcript kept for the audit trail; the current thesis is in specs/001-edge-negotiator/MASTER-SPEC.md (Euston A501; self-referential coupling; CT-style accountability; Phi-4-mini). Forbidden-term hits below are historical, not current claims.

# `local-cag` (Lee Stott, Microsoft) — Relevance Analysis for the Edge Negotiator

**Repo:** https://github.com/leestott/local-cag (cloned to `e:\desktop\assignments\dissertation\02-experiments\local-cag`)
**Stack:** Node.js 20+, Express 4, `foundry-local-sdk` 0.9.0, single HTML frontend
**Headline self-description:** "fully offline, on-device Context-Augmented Generation (CAG) support agent" for gas-field engineers
**TL;DR:** The project is genuinely useful as a *Foundry Local integration sample* and as a *safety-first prompt-engineering pattern*, but its "CAG" is naming theatre — under the hood it is a small in-memory document store with keyword scoring that injects a top-3 selection into the system prompt on every call. There is no KV-cache preload, no prefix caching, no long-context warm-up. For the Edge Negotiator the code itself is not reusable, and the *pattern* is only marginally interesting for the audit path. Recommendation is **(c) ignore for the hot/safety paths, (b) optionally adapt the keyword-selection idiom for the audit path** — see Section 10.

---

## 1. What does it do?

A field-engineer Q&A web app for gas inspection/maintenance. At startup it:

1. Reads the 20 markdown files in `docs/` (~42 KB total, confirmed via `wc -c` — 42,413 bytes), each one a short procedural guide (gas leak detection, PPE, emergency shutdown, fault codes, etc.).
2. Parses optional YAML front-matter (`title`, `category`, `id`).
3. Selects a Foundry Local model based on RAM budget, downloads it if missing, loads it in-process.
4. Serves a single `public/index.html` chat UI on `127.0.0.1:3000` with SSE-streamed tokens.

On every user query the server picks the top 3 documents by keyword overlap and inlines them into a fresh `messages` array along with the system prompt (`src/chatEngine.js:118-159`). That is the entire "CAG" mechanism.

Endpoints (`src/server.js:71-142`): `POST /api/chat`, `POST /api/chat/stream`, `GET /api/status` (SSE init progress), `GET /api/context`, `GET /api/health`. Tests use Node's built-in test runner; they cover prompt structure, doc loading, and route surface — no inference benchmarks.

## 2. CAG implementation pattern

This is the most important finding. **There is no real CAG here.** I grepped for `cache|kv|prefix|preload|warmup` across `src/` and found only HTTP `Cache-Control: no-cache` headers and the model-download cache. No KV-cache priming, no prefix caching of the system prompt, no extended-context windowing.

What it actually does (`src/chatEngine.js:118-159`, `src/context.js:188-216`):

```
on each query:
  terms = tokenize(userMessage)            // strip stop-words, length>2
  scored = docs.map(d => sum(
    8 * (d.title contains term) +
    3 * (d.category contains term) +
    1 * (d.content contains term)))
  top3 = scored.sort().slice(0, 3)
  context = focused_sections(top3, terms, maxCharsPerDoc=1600, maxSections=2)
  messages = [
    { system: SYSTEM_PROMPT },             // ~300 tokens
    { system: "Available documents: ..." + context },  // ~6K chars
    ...history.slice(-4),
    { user: userMessage },
  ]
  await chatClient.completeStreamingChat(messages, ...)
```

This is **lexical retrieval-augmented generation with a tiny corpus that fits in RAM**, dressed up as CAG. The author's own README admits as much: *"Rather than injecting all 20 documents into every prompt... the engine selects the top 3 most relevant documents per query using keyword scoring"* (`README.md:171`). Their own `findRelevantDocs` (`src/context.js:188`) is a classic TF-style scorer; only the absence of an embedding model and vector DB lets them call it CAG.

Genuine CAG (in the sense the Edge Negotiator might benefit from) would mean: build the KV-cache once at startup against a fixed corpus, persist that cache, and on each query reuse it via prefix-cache hits (Anthropic prompt cache, vLLM `prefix_caching=True`, llama.cpp `--prompt-cache`, etc.). **None of that happens here.** Even the system prompt is re-sent on every request inside a fresh `messages` array.

**Practical consequence:** the repo cannot be cited as evidence that CAG is fast, simple, or appropriate for low-latency control loops, because it does not implement CAG.

## 3. Foundry Local dependency

Hard lock-in. `package.json:11-14` lists exactly two runtime deps: `express` and `foundry-local-sdk`. The chat engine (`src/chatEngine.js:10`, `:55`, `:88`) calls `FoundryLocalManager.create(...)`, `manager.catalog.getModel(...)`, `model.download(...)`, `model.load()`, `model.createChatClient()`. Every inference path goes through the SDK's native bindings — there is no OpenAI-compatible HTTP adapter, no llama.cpp shim, no Hugging Face fallback.

The *pattern* (load markdown, score by keywords, inject into prompt) is trivially portable to llama.cpp, vLLM, Ollama, or transformers — it is ~50 lines of business logic. But you would discard `chatEngine.js`'s SDK plumbing and `modelSelector.js`'s catalogue logic entirely. Foundry Local is a Windows-first runtime distributed via `winget install Microsoft.FoundryLocal` (`README.md:65-67`); it is not part of the Edge Negotiator stack.

## 4. Models supported

`src/modelSelector.js:17-29` defines a `QUALITY_RANK` array:

- `qwen2.5-7b`, `qwen2.5-14b`
- `phi-4` (14B), `gpt-oss-20b`
- `mistral-7b-v0.2`
- `phi-4-mini-reasoning`, `phi-3.5-mini`, `phi-3-mini-128k`, `phi-3-mini-4k`
- `qwen2.5-1.5b`, `qwen2.5-0.5b`

So Phi *and* Qwen2.5 *and* Mistral *and* gpt-oss-20b — anything Foundry Local catalogues as `task: "chat-completion"` is eligible (`src/modelSelector.js:78`). Coder variants are skipped (`SKIP_ALIASES`, `:32-37`). Notably absent: **Qwen3** (the Edge Negotiator's locked primary). Qwen3 only appears in the Foundry catalogue if Foundry has shipped it; if not, this selector would never pick it. That is a forward-compatibility gap, not a hard block.

## 5. Hardware requirements

CPU-only is explicitly supported. The README states *"no GPU required, works on CPU/NPU"* (`README.md:23`) and the blog post repeats this (`blog_post.md:137`). Selection logic (`src/modelSelector.js:60-89`) sizes the model file against `os.totalmem() * 0.6` and skips anything bigger; default cap is 8 GB (`src/config.js:19`). On a 16 GB laptop you'd land on `qwen2.5-7b` or `phi-4-mini-reasoning`; on an 8 GB laptop you'd drop to `phi-3.5-mini` or smaller.

**For the Edge Negotiator's RTX 3060/4060 mobile target this is a non-issue** — the laptop has plenty of RAM and a usable GPU; the limiting factor is whether Foundry Local exposes Qwen3-4B with a CUDA EP (Foundry uses ONNX Runtime; quality of CUDA EP support for Qwen3 specifically is the open question, not the CAG pattern). Lee Stott's CPU question is answered by Foundry Local itself, not by this sample.

## 6. Direct use for the Edge Negotiator — point by point

The whole architecture assumes a *human-in-the-loop, conversational* workload (multi-second responses are fine). The Edge Negotiator hot path is sub-100 ms tick-bound. Mapping is therefore narrow:

- **Hot path (single-token phase ID + XGrammar JSON).** No. The hot path's whole point is *not* re-feeding 6 KB of context per tick. Any "CAG" that re-injects a system prompt the size this repo uses (~6 K chars + 300-token system) on every decision would blow the latency budget. Even a true KV-cache CAG would be marginal — the hot path's input is the live state vector, not a static corpus. Reject.

- **Audit path (post-hoc CoT JSON).** Maybe — and this is the only place the repo's *pattern* (not its code) has any merit. The audit path runs off-tick, can tolerate hundreds of ms, and benefits from grounding in NEMA traffic-engineering reference material. The pattern would be: index the NEMA spec / TRB green-book extracts the same way `src/context.js:239` loads markdown, do keyword scoring against the just-made decision's feature vector, inject top-K sections, ask the SLM to justify in structured JSON. This is *not* CAG in the technical sense — it is RAG-over-static-corpus. The Edge Negotiator already plans prefix-cached audit prompts; combining prefix-caching of the system prompt + per-decision retrieval of relevant NEMA sections is the natural fit. Strength of merit: low-to-moderate, and you already had this on the audit-path roadmap.

- **Safety path (Z3 SMT with NEMA constraints).** No. Z3 is deterministic and the constraint set is static formal logic; there is no role for an SLM-readable markdown corpus here. If anything, this repo is an anti-pattern for safety: it relies on prompting the model to "not hallucinate" (`src/prompts.js:19-22`) — exactly what the Edge Negotiator architecture rejected by going to formal verification.

- **Equity reasoning (IMD context per LSOA).** Marginal. You *could* preload an LSOA's IMD profile + protected-characteristic narrative as a system message and ask the SLM to flag inequities. But IMD data is structured (decile, sub-domain scores), not narrative — so a JSON injection plus a templated reasoning prompt beats the markdown-and-keyword pattern this repo uses. The keyword scorer in `src/context.js:188` would not even fire usefully on IMD numerical data.

**Net:** one weak match (audit path), no strong matches. The repo does not unlock anything that the existing Edge Negotiator design isn't already doing better.

## 7. Implementation lessons (patterns we could lift even without CAG)

These are concrete, transferable, and small:

1. **YAML front-matter on doc files for `title`/`category`/`id`** (`src/context.js:221-233`). Trivially useful for organising the NEMA reference corpus in the audit path or any test-fixture corpus.
2. **Two-tier prompt with full vs compact mode** (`src/prompts.js`, `src/chatEngine.js:119-121`). The Edge Negotiator's audit path could use the same pattern: full CoT prompt for forensic mode, compact prompt for normal logging. This is good prompt hygiene, not a novel idea, but worth borrowing the structure.
3. **Section-level scoring with per-section char budget** (`src/context.js:138-145`, `:147-182`). Heading gets weight 5, body weight 2; cap each doc at 1.6 KB across max 2 sections. A reasonable default if we ever do markdown-grounded audit.
4. **SSE init-status broadcast pattern** (`src/server.js:36-57`). Generally useful for any long-warming local model — the Edge Negotiator's experiment harness could expose model-loading progress this way to the SUMO viewer.
5. **`requireReady` middleware** that returns 503 while the model loads (`src/server.js:60-68`). Defends against premature inference calls, useful for the experiment runner.
6. **Stop-word-filtered tokenisation** (`src/context.js:14-51`). 20-line, dependency-free; fine as a baseline scorer.

What you should **not** copy:
- The keyword scorer for safety-critical retrieval — too brittle, no semantic understanding (no "regulator fault" ↔ "low pressure" link unless verbatim).
- The "trust the model not to hallucinate" prompt strategy.
- The conflation of "in-memory docs" with "CAG."

## 8. Latency characteristics

The repo demonstrates **nothing measurable**. There are no benchmarks, no timing harness, no token/sec numbers, no warm-up vs cold-start comparison. I grepped for `latency|tokens.per.sec|benchmark|throughput` — only hits were UI `setTimeout` calls and `Cache-Control: no-cache` headers.

The README claims (`README.md:195`): *"No retrieval overhead; prompt is already assembled"* and *"Retrieval adds latency (embedding + similarity search)"*. The first is contradicted by the code: per-query keyword scoring + per-section ranking + per-doc trimming runs every call (`_buildMessages` in `chatEngine.js:118`). The cost is small (probably <1 ms for 20 docs) but it is not zero, and the framing that "the prompt is already assembled" is misleading.

The actual saving versus a real RAG implementation is the absence of an *embedding model load + vector index lookup*. For a 20-document, 42 KB corpus that saving is real but irrelevant — both approaches would be sub-millisecond. The bottleneck is SLM decoding, which is identical regardless of how you assembled the context. **The repo cannot evidence the "CAG is faster" claim.**

For dissertation purposes: do not cite this project as latency evidence for CAG vs RAG. It contains no such measurements, and the difference it would measure is in the noise.

## 9. Risks

- **Foundry-Local lock-in.** Whole inference path goes through `foundry-local-sdk` native bindings (`src/chatEngine.js:10`, `:88`). Migrating off is a rewrite, not a port.
- **Windows-centric runtime.** `winget install Microsoft.FoundryLocal` is the documented install path (`README.md:65`). Cross-platform support exists in principle but the sample is Windows-first.
- **Qwen3 not in the model rank list.** `QUALITY_RANK` (`src/modelSelector.js:17-29`) stops at Qwen2.5 and Phi-4. Qwen3-4B (the Edge Negotiator primary) would either be silently ignored or fall through to `qualityScore = 1` (the unranked default at `:103`).
- **Naming risk.** Citing this repo as a "CAG implementation" in a dissertation invites a viva question you cannot defend, because it is not one. If you reference it, frame it as *"a markdown-grounded prompt-injection sample using Foundry Local."*
- **No KV-cache reuse.** Even the system prompt is re-sent every call. On a real CAG benchmark this would be the worst-case path. The Edge Negotiator's audit-path design (prefix-cached) is already a stronger pattern.
- **Tiny corpus (42 KB).** The "no chunking, just load it all" approach is only viable because the corpus is trivial. NEMA references would dwarf this; the pattern does not scale to the audit-path's needs without modification.
- **Brittle scorer.** Keyword overlap with hard-coded stop words (`src/context.js:14-37`) — `"low"` and `"high"` are not stop-worded but `"would"` is, an arbitrary choice that would matter for traffic-engineering vocabulary.

## 10. Concrete recommendation

**(c) Ignore for the hot path and safety path.** Hot path latency budget rules out any context-injection pattern this repo demonstrates; safety path is correctly served by Z3 + formal NEMA constraints, not by markdown grounding.

**(b) For the audit path only, borrow the *pattern* — not the code or the framing.** Specifically: organise NEMA / TRB / equity-reference material as front-matter-tagged markdown, use a section-level scorer like `src/context.js:147-182` as a baseline against the just-made decision's feature vector, and inject top-K sections into a prefix-cached audit prompt. This is RAG over a static corpus, not CAG, and should be described as such. The Edge Negotiator's existing audit-path plan (post-hoc CoT in structured JSON, prefix-cached) is already 80% of this; the marginal addition is a corpus loader and a scorer, both of which are ~100 lines.

**Justification.** The repo's value is as a *Foundry-Local integration tutorial* and a *safety-first prompt sample*, not as a CAG reference. Its "CAG" is keyword-RAG-with-fewer-dependencies. The Edge Negotiator's hot path needs single-token decoding + grammar-constrained JSON — neither benefits from this pattern. Its safety path needs SMT, not prompting. Its audit path could use a markdown-grounded scorer, but the heavy lifting (prefix caching, structured-JSON output, Qwen3 dual-mode reasoning) is outside this repo's scope. Citing it in the dissertation should be limited to: (i) an example of the Foundry Local SDK in action; (ii) an example of safety-first prompt structuring; (iii) a counter-example for "CAG vs RAG" framing — i.e. evidence that the term is being used loosely in the practitioner community and needs careful definition in the literature review.

---

### Files referenced

- `e:\desktop\assignments\dissertation\02-experiments\local-cag\README.md` (claims, architecture overview)
- `e:\desktop\assignments\dissertation\02-experiments\local-cag\package.json` (deps, model keywords)
- `e:\desktop\assignments\dissertation\02-experiments\local-cag\src\chatEngine.js` (the "CAG" orchestration — `_buildMessages` at `:118-159`)
- `e:\desktop\assignments\dissertation\02-experiments\local-cag\src\context.js` (doc loading + keyword scorer — `findRelevantDocs` at `:188-216`, section ranking at `:138-182`)
- `e:\desktop\assignments\dissertation\02-experiments\local-cag\src\modelSelector.js` (RAM-budgeted selector, `QUALITY_RANK` at `:17-29`)
- `e:\desktop\assignments\dissertation\02-experiments\local-cag\src\prompts.js` (full + compact prompts)
- `e:\desktop\assignments\dissertation\02-experiments\local-cag\src\config.js` (`maxContextDocs=3`, `ramBudgetPercent=0.6`)
- `e:\desktop\assignments\dissertation\02-experiments\local-cag\src\server.js` (SSE pattern at `:36-57`, `requireReady` at `:60-68`)
- `e:\desktop\assignments\dissertation\02-experiments\local-cag\docs\01-gas-leak-detection.md` (representative corpus document, ~1.4 KB)
- `e:\desktop\assignments\dissertation\02-experiments\local-cag\blog_post.md` (author's narrative — repeats the CAG framing)
- `e:\desktop\assignments\dissertation\02-experiments\local-cag\CHANGELOG.md` (v2 added "query-time document selection" — i.e. moved away from true context preload)
