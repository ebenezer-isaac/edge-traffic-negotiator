# Lee Stott Repos — Cross-Repo Synthesis

**Investigation date:** 2026-04-16 (updated with oBeaver investigation 2026-04-16)
**Repos investigated:** router-demo-app, modelrouter-routelens, FLPerformance, local-cag, local-rag, **microsoft/obeaver**
**Method:** Six isolated-context agents, one per repo, each producing a 1,500–3,500 word structured analysis. This document synthesises across all six.

> **Framing note (conformed to the current thesis, 2026-07-21 re-pivot):** this investigation was carried out under the project's April-2026 architecture, which planned Qwen3-4B as a co-primary SLM alongside Phi-4-mini, Traffic-R1 as a benchmark anchor, and a Besu-vs-Tessera blockchain comparator as the trust path. The current architecture (`specs/001-edge-negotiator/MASTER-SPEC.md`) freezes on **Phi-4-mini (3.8B) as the sole SLM** and demotes the blockchain-backend comparison to a cited Certificate-Transparency-style quorum-anchored + cross-audited accountability log — no blockchain backend is built or compared. The empirical hardware measurements below are unchanged (real numbers from real runs) and remain directly relevant, especially the Phi-4-mini rows. The forward-looking recommendations that assumed Qwen3-4B/Traffic-R1 as co-primary or a Besu/Tessera comparator are superseded; those passages are reframed below rather than deleted, so the investigation history stays legible.

---

## TL;DR Per Repo

| Repo | Verdict | One-line reason |
|------|---------|-----------------|
| router-demo-app | **Ignore** | 100% cloud Azure, ~7,800 ms latency, hard-coded GPT-4.1/GPT-5/etc., zero CPU support |
| modelrouter-routelens | **Implement similar pattern** | Useful ~250-LOC comparator skeleton for SLM A/B and an accountability-log comparator (signed log vs quorum-anchored CT-style anchor); lift patterns, add rigour |
| FLPerformance | **Adapt — secondary benchmarking tool** | Real benchmark tool with CPU support and CPU-vs-GPU comparison; works for Phi-4-mini directly; **does not cover Qwen3-4B or Traffic-R1**, which were the earlier plan's secondary comparison models |
| local-cag | **Ignore for hot/safety; borrow for audit path** | Doesn't actually implement CAG — it's lexical RAG mislabelled; Foundry-locked; useful as counter-example |
| local-rag | **Adapt for future operator dashboard** | TF-only, Foundry-locked, but the audit-path RAG pattern is right; lift patterns, not code |
| **obeaver (microsoft/obeaver)** | **Use directly — SLM runtime** | Tech Preview; runs Phi-4-mini via Foundry Local and, if a comparison model is ever wanted again, Qwen3-family models are first-class via `obeaver convert`; ChatML formatter hard-coded; ORT GenAI engine + Foundry Local dual-engine; OpenAI-compatible API |

---

## What This Tells Us About Lee's Asks

Lee asked three things in the call:
1. **Explore things that can be done on the edge**
2. **Try to run Beaver which runs on full CPU instead of GPU**
3. **Can I run something on my own machine**

### Answer 1: Things that can be done on the edge
The five repos collectively map to a "local-first AI" pattern set: model routing, paired-runtime diagnostics, performance benchmarking, CAG, and RAG. None of them are designed for traffic control specifically. **The transferable patterns are**:
- **Foundry Local as a local inference runtime** (Windows-first; ships catalog includes Phi-3.5-mini, Qwen2.5-3B, Mistral, gpt-oss-20b)
- **A/B paired-runtime comparison harness** (RouteLens pattern) — directly applicable to an accountability-log comparator (signed hash-chained log vs quorum-anchored CT-style anchor)
- **CPU-vs-GPU benchmarking** (FLPerformance pattern) — directly applicable to Phi-4-mini latency profiling
- **Lexical retrieval over a small static corpus** (local-cag pattern) — applicable to our audit-path NEMA/MUTCD reference lookup

### Answer 2: CPU-only inference (the "Beaver" / oBeaver question — RESOLVED EMPIRICALLY)

**Lee's "Beaver" reference resolved as `microsoft/obeaver`** — Microsoft's official local LLM inference toolkit, ONNX Runtime + Foundry Local dual-engine, currently CPU-only (Tech Preview, GPU/NPU on roadmap). Lee asked the user on 3 April 2026 to "use this and experiment." **We installed oBeaver, ran it on the user's machine, and benchmarked four model/hardware combinations.** Full runbook in `02-experiments/runbook/`.

**Direct empirical measurements on the user's RTX 2060 / Windows 10 machine:**

| Model | Engine | Hardware | Hot-path TTFT (median) | Audit-path total (median) | Output reliability |
|-------|--------|----------|--------------------------|------------------------------|--------------------|
| qwen2.5-0.5b | Foundry | CPU | 772 ms | 4,672 ms | 3 of 10 garbage |
| phi-4-mini (3.8B) | Foundry | **GPU** | **374 ms** | 8,453 ms | 10 of 10 OK |
| phi-4-mini (3.8B) | Foundry | CPU | 3,230 ms | 33,470 ms | 10 of 10 OK |
| Qwen3-0.6B-DQ-ONNX | ORT | CPU | 1,538 ms | 11,180 ms | 10 of 10 OK |

**Findings:**
- 10 ms hot-path budget is unreachable on this hardware (best: 374 ms, **37× over**)
- GPU vs CPU for the same model (Phi-4-mini): **8.6× faster TTFT, 4× faster audit total**
- CPU-only is decisively non-viable for 3–4B SLMs in any sub-second control loop
- Phi-4-mini was perfectly reliable (10 of 10) on both GPU and CPU in this run
- Smaller models are faster but produce garbage 30% of the time without CFG-constrained decoding

*(The Qwen3-0.6B row above compared favourably to Qwen2.5-0.5B at the time; that comparison informed model selection under the April-2026 plan and is retained here as an accurate record of what was measured. It does not bear on the current architecture, which fixes Phi-4-mini as the sole SLM.)*

**Implication for the Edge Negotiator:**
- **Hot path (single-token phase ID, target ~10 ms): CPU-only is infeasible.** Even with single-token output, TTFT alone exceeds the budget by 60–300×.
- **Audit path (post-hoc note generation, ~50–200 tokens, target <500 ms): CPU-only is borderline-infeasible.** Decode time alone for 100 tokens at 100 ms/tok is 10 seconds. Acceptable only if generated in background and consumed asynchronously by the audit log.
- **Future-work edge deployment**: a small NPU or integrated GPU is the realistic minimum. Pure CPU is not credible.

This remains a useful empirical finding for the dissertation: **"CPU-only edge inference for sub-second control loops is not feasible at the current state of the art for sub-7B SLMs, including with optimised inference runtimes such as ONNX Runtime via oBeaver."**

**However, oBeaver materially changes the benchmarking plan in a different way** — see Answer 3.

### Answer 3: Can I run something on my own machine? (RESHAPED by oBeaver)

Yes. oBeaver runs Phi-4-mini via its Foundry Local engine on the user's own hardware, satisfying Lee's ask directly. Its ORT GenAI engine additionally has first-class support for the Qwen3 model family (`engine_ort.py:453-466`, hard-coded ChatML formatter) — useful if a future comparison model is ever wanted, though the current architecture does not require one.

**Updated plan (conformed to Phi-4-mini as the sole SLM):**
1. **Install Foundry Local** (Windows-first, ships on Windows 10 — both oBeaver and FLPerformance use it)
2. **Install oBeaver** (with the documented `pyproject.toml` workaround for the broken `torch>=2.10.0` pin: `pip install --no-deps -e .`)
3. **Run Phi-4-mini via oBeaver's Foundry Local engine** (`obeaver run phi-4-mini`) and cross-validate against Foundry Local direct
4. **Run Phi-4-mini via FLPerformance** for the CPU-vs-GPU dual-alias comparison
5. **Write a small Python benchmark harness (~1 day)** that hits oBeaver's OpenAI-compatible HTTP endpoint and replicates FLPerformance's metrics (TTFT, TPOT, p50/p95/p99, structured-output validation)
6. **Capture latency distributions** for offline injection into the SUMO TraCI loop

**The (superseded) split between the two tools, retained for the record:**
| Model | Tool | Engine | Why (April-2026 plan) |
|-------|------|--------|-----|
| Qwen3-4B (then co-primary, now dropped) | oBeaver | ORT GenAI | Foundry catalog doesn't have it; oBeaver does via conversion |
| Phi-4-mini (now the sole SLM) | FLPerformance + oBeaver | Foundry Local | Better benchmarking UI in FLPerformance; oBeaver as cross-validation |
| Traffic-R1 (cited benchmark anchor, not deployed) | oBeaver | ORT GenAI | Foundry catalog doesn't have it; oBeaver via conversion |
| Phi-3.5-mini (proxy) | FLPerformance | Foundry Local | Already in catalog; useful for FLPerformance-supported analyses |
| Qwen2.5-3B (proxy) | FLPerformance | Foundry Local | Already in catalog; useful for FLPerformance-supported analyses |

Under the current architecture only the Phi-4-mini row is load-bearing; the rest is retained as a record of what was investigated.

---

## Cross-Repo Patterns Worth Lifting

### Pattern 1: Paired-runtime comparator (from RouteLens)
~250 LOC pattern with these elements:
- Bounded-concurrency worker pool (RouteLens `src/utils.js:43-60`, ~18 lines)
- Transient-error retry with jittered backoff (`src/utils.js:16-35`)
- JSONL append-only audit logger (`src/logger.js:18-22`)
- Result-shape normalisation across heterogeneous backends (`src/clients/*.js:49-79`)
- Side-by-side divergence highlighter (`src/report.js:53-77`)
- Two-mode CLI dispatch (full sweep + targeted reproduction)

**Direct application: an accountability-log comparator.** Replay identical decision streams through a plain signed append-only log and a quorum-anchored, cross-audited CT-style log, log every interaction, surface divergences. Add what RouteLens lacks: warm-up discards, paired Wilcoxon tests, BCa bootstrap CIs, fixed seeds, CSV export. Cite RouteLens as visible prior art for the comparator pattern; do not cite as a benchmarking methodology.

### Pattern 2: CPU-vs-GPU dual-alias benchmarking (from FLPerformance)
Load the same model under two aliases (`-cpu`, `-cuda`), benchmark both in the same suite, compare in UI. **Direct application: characterise the Edge Negotiator's hot-path and audit-path latency budget headroom under both compute targets, for Phi-4-mini.** The data feeds the dissertation's "what hardware would deployment require" discussion.

### Pattern 3: Sub-second lexical retrieval over static corpus (from local-cag and local-rag)
Both repos demonstrate that lexical (TF or keyword-scored) retrieval over a 20-doc corpus achieves sub-millisecond retrieval latency. **Direct application: audit-path NEMA/MUTCD reference lookup** — preload the constraint catalog as a small static corpus, retrieve relevant sections at query time for the SLM's internal reasoning note. This is "RAG over static corpus", which the local-cag analysis correctly identified as the pattern, regardless of the misleading repo name.

---

## CAG vs RAG: Resolved for the Edge Negotiator

The local-cag and local-rag analyses jointly settle the CAG/RAG question for our architecture:

| Integration point | Pattern | Why |
|-------------------|---------|-----|
| Hot path (single-token phase ID) | **Neither** | No latency budget for any retrieval; decision context already in prompt |
| Real-time gate (deterministic auth/conservation checks) | **Neither (deterministic checks, not retrieval)** | The gate is not retrieval; it's cryptographic verification + a conservation/CUSUM check |
| Audit path (internal, firewalled note) | **CAG (true CAG, not the local-cag mislabelled version)** | NEMA/statute constraint catalog is small, stable, fits Phi-4-mini's context window; prefix-caching makes per-decision overhead near-zero |
| Future-work operator audit dashboard | **RAG** | Unbounded growing audit log won't fit context; human-tolerable latency; mandatory citations |
| Future-work decision-precedent retrieval | **Neither** | Wrong shape — the corpus is numeric state vectors, not text; vector similarity over latents is the right tool |

**Important terminology note for the dissertation:** "CAG" is used loosely in the practitioner community. Lee Stott's `local-cag` repo is actually lexical RAG over a small in-memory corpus, not true context-augmented generation. The dissertation's discussion of CAG vs RAG should define the terms carefully and cite this loose usage as a reason for the careful definition.

---

## What's Missing — We Need to Build This Ourselves

The five repos cover model routing, A/B comparison, performance benchmarking, CAG, and RAG. **None of them cover:**

1. **Structured-output reliability evaluation** (XGrammar/Outlines JSON schema compliance under stress) — needed for the SLM Job A/B characterisation
2. **Citation-faithfulness / false-citation-rate evaluation** on novel legal fact-combinations against an un-rigged rule-to-text template baseline — needed for the SLM's primary metric (Job A)
3. **The deterministic real-time gate + accountability-log integration with SLM output** — domain-specific to traffic control
4. **The quorum-anchored, cross-audited CT-style accountability log** (≥2 witnesses + a named cross-auditor) — we have the design in `specs/001-edge-negotiator/MASTER-SPEC.md` §6.7/§9; need to build it
5. **MaxPressure deterministic baseline implementation** — standard in the TSC literature; many open implementations exist

For (1)–(3) we need a custom Python harness on top of Foundry-supported Phi-4-mini. Estimated effort: 2–3 days of focused work to stand up the harness, then weeks of running.

---

## Concrete Next Steps

### This week
1. **Install Foundry Local** on the user's Windows machine
2. **Run FLPerformance against Phi-3.5-mini and Qwen2.5-3B on the user's GPU** to get baseline latency distributions (proxy models; the primary model is Phi-4-mini)
3. **Run FLPerformance again with `-cpu` aliases** to get CPU baselines (answers Lee's CPU question with hard numbers)
4. **Write a 200-line Python script using `llama.cpp` or `transformers`** to benchmark Phi-4-mini directly with our actual prompt templates (the FLPerformance results plus this script give the full picture)

### Next 2–3 weeks
5. **Build the Euston Road (A501) SUMO network** (pre-built and committed per `specs/001-edge-negotiator/MASTER-SPEC.md` §9)
6. **Stand up the signed hash-chained AuditLog** with the accountability-log schema from the spec
7. **Stand up the quorum anchor** (≥2 witnesses, e.g. a Rekor transparency log + a named single-node ledger RPC) **and a named cross-auditor**
8. **Wire the TraCI ↔ Python agent ↔ AuditLog loop**
9. **Implement MaxPressure baseline** (existing open-source implementations exist)
10. **Wire the deterministic gate with the cited UK statute set** (`01-research/uk-traffic-law.md`)

### Patterns to lift, not code
11. **RouteLens comparator skeleton** (~250 LOC) → adapt for the accountability-log comparator and any future SLM benchmarking harness
12. **Local-cag section-scoring pattern** → adapt for the audit-path constraint preamble (true CAG via prefix caching)
13. **FLPerformance CPU/GPU dual-alias pattern** → use for the Phi-4-mini benchmarking discussion

### What NOT to do
- **Don't depend on router-demo-app or any cloud-routing pattern.** Latency is fatal and the dissertation is local-only.
- **Don't build a blockchain backend or a Besu/Tessera comparator.** The trust path is a cited Certificate-Transparency-style quorum-anchored + cross-audited log, not a blockchain; the mechanism is credited to prior art, not implemented as a novel contribution.
- **Don't trust the "CAG" name in `local-cag`.** The implementation is RAG. The dissertation needs careful CAG/RAG definition.

---

## Open Questions for Lee (Industry Supervisor)

1. **~~What is "Beaver"?~~** RESOLVED — `microsoft/obeaver`, your 3 April 2026 email. Cloned, investigated, integrated into the benchmarking plan. Runs Phi-4-mini directly; Qwen3-family models are first-class via `obeaver convert` if a comparison model is ever wanted.
2. **Is the Foundry Model Router pattern relevant to anything in the current architecture?** The cloud router pattern adds dispatch latency that's fatal for the hot path. With a single frozen SLM (Phi-4-mini) there is no model-routing decision to make in the current design — flagging this as effectively resolved rather than open.
3. **For CPU-only inference, oBeaver confirms the FLPerformance finding: hot path is GPU-only territory for 3–4B SLMs.** Should I reframe the dissertation's "edge deployment" framing accordingly, or are you specifically interested in CPU-only as a fallback / lower-tier deployment mode? oBeaver's NPU-acceleration roadmap may be the realistic future-work path for true edge deployment.
4. **For RAG/CAG: the local-rag and local-cag patterns are useful for the audit path and future operator dashboard, not the hot path.** Want me to design the audit-path constraint CAG into the implementation now, or scope it to "designed but not implemented" in this dissertation?
5. **oBeaver follow-up:** the repo is Tech Preview with documented dependency issues (broken `torch>=2.10.0` pin in `pyproject.toml:29`). Is there an internal Microsoft channel to get a stable build, or should I just use the documented workaround (`pip install --no-deps -e .`)?

---

## File Map

```
e:\desktop\assignments\dissertation\02-experiments\
├── router-demo-app\         ← cloned, source code reviewed
├── modelrouter-routelens\   ← cloned, source code reviewed
├── FLPerformance\           ← cloned, source code reviewed
├── local-cag\               ← cloned, source code reviewed
├── local-rag\               ← cloned, source code reviewed
├── obeaver\                 ← cloned, source code reviewed (SLM runtime for Phi-4-mini)
└── findings\
    ├── router-demo-app-analysis.md     ← per-repo deep dive
    ├── routelens-analysis.md           ← per-repo deep dive
    ├── flperformance-analysis.md       ← per-repo deep dive
    ├── local-cag-analysis.md           ← per-repo deep dive
    ├── local-rag-analysis.md           ← per-repo deep dive
    ├── obeaver-analysis.md             ← per-repo deep dive (most strategic value)
    └── synthesis.md                    ← this document
```

Each analysis is structured 9–13 sections covering: what it does, dependencies, direct-use feasibility, implementation lessons, benchmarking relevance, hardware requirements, CPU support, risks, and a concrete recommendation.
