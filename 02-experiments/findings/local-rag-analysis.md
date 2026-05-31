# `local-rag` (Lee Stott / Microsoft) — Analysis for the Edge Negotiator

**Repo path:** `e:\desktop\assignments\dissertation\02-experiments\local-rag`
**Upstream:** https://github.com/leestott/local-rag
**Version inspected:** v2.0.0 (CHANGELOG dated 2026-03-13)
**Companion sample referenced:** `local-cag` (https://github.com/leestott/local-cag)

---

## 1. What does it do?

`local-rag` is a Node.js / Express demo of an offline Retrieval-Augmented Generation chatbot for gas-field inspection engineers. Twenty markdown procedural documents in `local-rag\docs\` (gas leak detection, PPE, valve inspection, etc.) are chunked and indexed at startup. A browser UI sends questions to `/api/chat/stream`, the server retrieves top-K chunks via TF-IDF cosine similarity over a SQLite store, prepends them as a second system message, calls Phi-3.5-Mini through Foundry Local, and streams tokens back over SSE.

The architecture is intentionally minimal and pedagogical: the entire RAG pipeline is six small files in `local-rag\src\` (`chatEngine.js`, `chunker.js`, `vectorStore.js`, `ingest.js`, `prompts.js`, `server.js`, `config.js`) totalling well under 1,000 lines. There is no LangChain, no embedding model, no external vector DB, no auth, no multi-user notion. It is a "scenario sample for learning and experimentation" (README L343).

The system prompt (`local-rag\src\prompts.js` L2-L33) hard-codes a safety-first format (Summary → Safety Warnings → Steps → Reference) and a refusal string: *"This information is not available in the local knowledge base."* Two prompt sizes are shipped: full (~300 tokens) and compact (~80 tokens) for "edge mode" which also drops top-K from 5 to 3 and max output tokens from 1024 to 512 (`chatEngine.js` L101, L142).

---

## 2. RAG stack

| Stage | Implementation | File / line |
|---|---|---|
| Document loader | `fs.readdirSync` over `docs/`, only `.md` files | `ingest.js` L23-L26 |
| Front-matter | Hand-rolled YAML-lite parser (`title`, `category`, `id`) | `chunker.js` L9-L21 |
| Chunker | Whitespace tokens, fixed sliding window (200 tokens, 25 overlap) | `chunker.js` L28-L41; `config.js` L15-L17 |
| Embedding | **None.** Bag-of-words term frequency, lower-cased, stripped to `[a-z0-9₂\-']` | `chunker.js` L47-L58 |
| Vector store | `better-sqlite3`, single `chunks` table, `tf_json` column | `vectorStore.js` L31-L42 |
| Index | In-memory inverted index (term → Set<rowIdx>) built lazily | `vectorStore.js` L62-L82 |
| Similarity | Plain cosine over TF maps; query-side TF computed per call | `chunker.js` L63-L74; `vectorStore.js` L99-L124 |
| Re-ranking | None |
| Prompt assembly | Two system messages: instructions, then `Document N: title [category]\ncontent` blocks | `chatEngine.js` L108-L139 |
| Generation | Foundry Local SDK `model.createChatClient()` → `completeStreamingChat` | `chatEngine.js` L70-L72, L185-L191 |
| Transport to UI | SSE per chunk, `[DONE]` sentinel | `server.js` L57-L86 |

There is no IDF anywhere in the code despite the name "TF-IDF" in the README — only term frequency. That is fine for a 200-chunk corpus but worth flagging: README claims overstate the technique.

---

## 3. Foundry Local dependency

**Hard dependency.** `chatEngine.js` L8 imports `FoundryLocalManager` from `foundry-local-sdk` (`package.json` L15: `"foundry-local-sdk": "^0.9.0"`). The class is bound to the SDK's `catalog.getModel(...) → model.download → model.load → model.createChatClient` lifecycle (`chatEngine.js` L43-L72). The CHANGELOG records that in v2.0.0 the project *removed* the `openai` npm package and switched fully to the native Foundry SDK chat client — so the OpenAI-compatible escape hatch present in v1.x is gone.

To swap in llama.cpp / vLLM / Ollama / `transformers`, the entire `ChatEngine` class would need rewriting. That said, the *RAG plumbing* (chunker, vector store, ingest, server) has zero coupling to Foundry — `chunker.js` and `vectorStore.js` import nothing from the SDK. So the **pattern** ports cleanly; the **code** does not. For our project, only the chunker + SQLite store are realistically liftable; the chat engine would be replaced wholesale by a llama-cpp-python or vLLM call.

---

## 4. Models supported

- **Generation:** Whatever Foundry Local's catalog exposes. Code hard-codes `model: "phi-3.5-mini"` in `config.js` L10. README L338 says you can swap to "any model available in the Foundry Local catalog" — which means Microsoft's curated SLMs (Phi family, some Mistral/Llama variants depending on Foundry version). **Qwen3-4B is not in the Foundry catalog at time of writing**, so directly reusing this engine for the Edge Negotiator is a non-starter.
- **Embedding:** None. There is no embedding model in the loop at all. This is a deliberate design point reiterated in README L213 ("No embedding model needed for chunking") and blog_post.md L182-L189.
- **Hardware variant selection:** SDK auto-selects GPU > NPU > CPU at load time (`chatEngine.js` L50-L51 comment). No control surface exposed in the code.

---

## 5. Hardware requirements

Genuinely laptop-friendly. The README explicitly targets CPU and NPU machines (Copilot+ PCs, Surface devices) and states "no GPU required" (L21, blog_post.md L153). Phi-3.5-Mini at INT4 is ~2 GB on disk (README L65) and runs in low single-digit GB of RAM. Retrieval is sub-millisecond on the 200-chunk corpus (blog_post.md L124, L199) because TF cosine over an in-memory inverted index is trivial.

For Lee Stott's CPU-performance question specifically: this codebase confirms CPU inference is viable for Phi-3.5-Mini through Foundry Local, but it does not benchmark token/s — only retrieval is timed. End-to-end first-token latency will be dominated by the SLM cold start (multi-second on first request) and steady-state TPS (Phi-3.5-Mini on a modern laptop CPU is usually 8-25 tok/s; on RTX 3060/4060 mobile, ~40-80 tok/s). None of those numbers are in the repo — would need to measure.

---

## 6. Direct use for the Edge Negotiator

| Integration point | Verdict | Why |
|---|---|---|
| **Audit-path retrospective analysis** (post-decision NEMA / MUTCD lookup) | **Genuine fit.** Out-of-loop, latency-tolerant, well-bounded corpus (a few hundred pages of standards). The exact pattern in this repo (markdown docs + sliding-window chunks + sub-ms TF retrieval + SLM with citations) maps almost 1:1. The "Reference" field in the prompt template (`prompts.js` L31) is the audit-trail citation we need. | High |
| **Equity audit context** (LSOA-specific deprivation context for flagged decisions) | **Pattern fits, content does not.** LSOA deprivation data is structured (IMD deciles, LA boundaries) — better served by a SQL lookup keyed on LSOA code than by free-text retrieval. RAG only helps if you're pulling *narrative* context (council equity policies, ONS commentary). For numeric IMD lookup, this repo is overkill. | Partial |
| **Decision precedent retrieval** (future work, top-K similar past decisions) | **Pattern wrong.** Past decisions are structured records (state vector + chosen phase + outcome metric), not prose. You want a similarity search over a state-embedding space (FAISS over numeric vectors, or learned approximations), not TF cosine over text. The local-rag chunker actively *destroys* numeric precision (`chunker.js` L51 strips most non-alpha chars). | Low |
| **Operator-facing audit dashboard** (NL Q&A over immutable audit log with citations) | **Strongest fit.** The audit log is naturally chunkable per-decision-record, the SSE-streaming + sources panel UX (`server.js` L75-L80, README L96-L98) is exactly the right interaction model, and citations matter for compliance review. The local-rag UI flow (question → retrieved chunks shown with relevance scores → grounded answer) is precisely what an EU-AI-Act-style operator console wants. | High |

The two genuine fits (audit retrospective analysis, operator audit dashboard) share one property: **out-of-loop, post-hoc, human-in-the-loop**. Neither touches the SUMO 1-Hz control loop. That is consistent with our locked architecture excluding RAG from the hot path.

---

## 7. Implementation lessons

**Worth lifting:**

1. **Two-system-message prompt assembly** (`chatEngine.js` L131-L139): keep the safety/format instructions in one system message and the retrieved context in a second labelled system message, rather than concatenating. This plays well with prefix caching (which our audit path already uses) because the first system message is invariant across queries.
2. **Lazy in-memory inverted index** (`vectorStore.js` L62-L82) built once, invalidated on writes (`_invalidateCache` L57-L60). Sub-ms retrieval for a few hundred chunks with no external dependency. Useful for the audit-log corpus, which fits this size class easily.
3. **Sources-first SSE streaming** (`chatEngine.js` L194-L202): yield the source list *before* the first token, so the UI can render citations while the model is still generating. Good UX pattern for an operator console.
4. **Filename sanitisation + traversal check** (`server.js` L97, L108-L111): minimal but correct.
5. **Front-matter as metadata** (`chunker.js` L9-L21, `ingest.js` L42-L46): cheap way to keep `category`/`id` separate from body text and make them filterable. We could use this for tagging audit records by intersection-ID, decision-class, etc.

**Worth ignoring:**

1. **TF-only similarity.** Fine for 20 procedural docs; *wrong* for NEMA/MUTCD/EU-AI-Act text where vocabulary varies across the same concept and where rare-but-decisive terms (e.g. "gridlock", "preemption") need IDF weighting. For our use, swap in either real TF-IDF (one extra pass at ingest) or a small embedding model (e.g. `bge-small-en-v1.5`, ~130 MB, 384-dim) into LanceDB or FAISS-flat.
2. **Whitespace tokenisation.** Strips numbers and punctuation aggressively (`chunker.js` L51) — kills MUTCD section numbers like "4D.04" and IMD decile values. We need a tokeniser that preserves alphanumeric identifiers.
3. **Fixed-size sliding window.** The README itself (L242-L246) admits section-aware chunking is better for "hundreds of long documents". NEMA TS-2 and MUTCD are exactly that. Use heading-aware splitting with a max-size cap.
4. **Vector-store choice.** SQLite + JSON columns is fine at 200 chunks. For NEMA + MUTCD + EU AI Act we are at 10⁴-10⁵ chunks; LanceDB or `sqlite-vec` (proper ANN) is the right step up while keeping zero-server simplicity.

---

## 8. Latency characteristics

The repo only measures retrieval, not end-to-end. Documented numbers:

- **Retrieval:** sub-millisecond once the inverted-index cache is warm (`blog_post.md` L124, L199). README L228 quotes "~1 ms" and contrasts with "~100-500ms if an embedding model had to encode each query".
- **Ingestion:** "all 20 documents are chunked and indexed in under a second" (README L229).
- **Generation:** not benchmarked. Dominated by Phi-3.5-Mini token rate (not measured here).

**Implication for us:** retrieval itself is never the bottleneck. The bottleneck is always SLM generation. So RAG vs CAG vs no-retrieval is a *prompt-length* trade-off, not a *retrieval-cost* trade-off. For our hot path (sub-100 ms budget for a single phase-ID token after the safety verifier), even sub-ms retrieval is irrelevant if the resulting prompt expands the prefill cost by 500-2000 tokens. **Strictly out-of-loop** for the Edge Negotiator. The audit path can absorb it; the hot path cannot.

---

## 9. Risks

1. **Foundry Local lock-in.** `chatEngine.js` is now SDK-native (CHANGELOG v2.0.0). Foundry Local is Windows-first (`winget install Microsoft.FoundryLocal`, README L62), Microsoft-controlled, catalog-restricted, and offers no Linux story for headless cluster runs. For a UCL dissertation that needs reproducibility on the marker's machine and possibly on a Linux compute node, this is a real portability risk. Our project must not adopt the SDK; we lift the *patterns* only.
2. **Catalog constraint.** Qwen3-4B (our locked primary SLM) is not in the Foundry catalog. Adopting Foundry would force a model swap, which contradicts the locked architecture decision (Apache 2.0 + native dual thinking modes are Qwen3-specific).
3. **No IDF, no semantic similarity.** Pure TF cosine will under-retrieve on the long-tail vocabulary in regulatory text. Direct reuse on NEMA/MUTCD will silently produce poor citations.
4. **Vector-store ceiling.** `better-sqlite3` + JSON-encoded TF maps + brute-force cosine over candidate set works at 200 chunks (`vectorStore.js` L99-L124 scans all candidates). At 10⁴+ chunks it degrades; at 10⁵+ it is unusable. Need ANN (LanceDB, `sqlite-vec`, or qdrant) for any real corpus.
5. **No auth, no rate limiting.** `server.js` L36-L86 trusts every request. Acceptable for a localhost demo; not acceptable for the operator dashboard. We would re-write the transport layer.
6. **Maintenance overhead** is genuinely low here — that is the appeal. SQLite file, no daemon, no Docker. The *upgrade* to a real embedding store undoes some of that simplicity, which is the trade we accept for retrieval quality.

---

## 10. CAG vs RAG decision for our project

The companion `local-cag` sample uses the same Foundry stack but **preloads** the entire document corpus into the model's context once and reuses the prefix cache, instead of retrieving at query time. The blog_post.md table at L31-L40 frames it cleanly: CAG when the corpus is small and stable; RAG when it is large or you need fine-grained source attribution.

For the Edge Negotiator, the answer is **neither in the hot path; CAG for the audit-path constraint preamble; RAG for the operator dashboard and the future-work decision-precedent feature**. Argued specifically:

**Hot path (1 Hz, single-token phase ID + CFG-constrained JSON):** Use neither. Retrieval at 1-10 ms is cheap; the cost is *prompt growth*. Every retrieved chunk inflates prefill, which on a constrained laptop GPU is the dominant latency contributor for short outputs. Hot path uses a fixed micro-prompt with state vector only. This was already the locked decision and `local-rag`'s actual numbers reinforce it.

**Safety path (Z3 SMT + always-on MaxPressure fallback):** Neither. The constraint set is small, fixed, and logical, not textual. As the dissertation already notes, "deterministic constraint retrieval in safety path is RAG by another name" — but it is a key-value lookup, not a similarity search.

**Audit path (post-hoc CoT in structured JSON, prefix-cached):** **CAG.** The relevant corpus per decision is small and stable (the active intersection's NEMA phase table, the controller's own ruleset, the recent decision history within a window). Preloading this once per session and prefix-caching it gives us:
- Deterministic, fully reproducible audit reasoning
- Zero retrieval latency to amortise
- No risk of retrieval misses (a RAG miss in an audit context is a citation gap that has to be explained)
- Native fit with the prefix-caching mechanism the audit path already uses for the CoT format

The corpus is small enough that it fits in Qwen3-4B's context (32K-128K depending on variant) with room for the per-decision payload. CAG is strictly better here than RAG — RAG only wins when the corpus exceeds the context window, which the per-intersection audit corpus does not.

**Operator audit dashboard (future work, NL Q&A over the immutable audit log):** **RAG.** The audit log grows unboundedly (one record per decision per intersection per second across a multi-junction simulation). It will not fit in context. This is exactly RAG's territory: large, growing, structured-but-textual corpus, queried by humans with latency in the seconds, citations mandatory. This is where `local-rag`'s pattern (sources-first SSE, citation panel, two-system-message prompt) earns its keep.

**Decision-precedent retrieval (future work, top-K similar past decisions):** **Neither classical RAG nor CAG.** As noted in §6, this is similarity over numeric state vectors, not text. The right tool is a vector index (FAISS-flat or HNSW) over learned or hand-crafted state embeddings. Calling it "RAG" overloads the term — it is nearest-neighbour retrieval feeding a model, which is the same shape but a different stack.

**Equity audit context:** **Hybrid leaning CAG.** The IMD/LSOA structured table is a SQL join. Any narrative council policy text small enough to be relevant per intersection should be preloaded (CAG) to keep the equity reasoning deterministic and inspectable.

---

## 11. Concrete recommendation

**Adapt the pattern (option b) — specifically for the future-work operator audit dashboard, and lift the inverted-index + sources-first-SSE patterns now for the audit-path tooling.** Do not adopt the code, the SDK, or the model.

Justification: the repo's value is in three concrete patterns that are demonstrably correct for laptop-class hardware — (i) lazy in-memory inverted index over a SQLite-backed chunk table for sub-ms retrieval, (ii) two-system-message prompt assembly that keeps invariant instructions separate from variable context (prefix-cache friendly), and (iii) sources-first SSE streaming with a citation panel. All three are directly relevant to the operator audit dashboard and to any audit-path tooling that surfaces NEMA/MUTCD references with citations. Everything else — Foundry Local SDK, Phi-3.5-Mini, TF-only similarity, fixed-size whitespace chunking, the Express server, the gas-engineering domain corpus — is either incompatible with the Edge Negotiator's locked stack (Qwen3-4B, llama.cpp / vLLM, Apache-2.0 toolchain, Linux-portable) or insufficient for the regulatory-text retrieval quality we need. The hot path and safety path remain RAG-free as already decided; CAG is the right call for the audit-path constraint preamble; this repo informs only the future-work operator dashboard and a few internal patterns. Treat `local-rag` as a reference implementation to read, not a dependency to import.
