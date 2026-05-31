# Lee Stott Repos — Cross-Repo Synthesis

**Investigation date:** 2026-04-16 (updated with oBeaver investigation 2026-04-16)
**Repos investigated:** router-demo-app, modelrouter-routelens, FLPerformance, local-cag, local-rag, **microsoft/obeaver**
**Method:** Six isolated-context agents, one per repo, each producing a 1,500–3,500 word structured analysis. This document synthesises across all six.

---

## TL;DR Per Repo

| Repo | Verdict | One-line reason |
|------|---------|-----------------|
| router-demo-app | **Ignore** | 100% cloud Azure, ~7,800 ms latency, hard-coded GPT-4.1/GPT-5/etc., zero CPU support |
| modelrouter-routelens | **Implement similar pattern** | Useful ~250-LOC comparator skeleton for SLM A/B and Besu vs Tessera; lift patterns, add rigour |
| FLPerformance | **Adapt — secondary benchmarking tool** | Real benchmark tool with CPU support and CPU-vs-GPU comparison; works for Phi proxies; **does NOT cover Qwen3-4B or Traffic-R1** |
| local-cag | **Ignore for hot/safety; borrow for audit path** | Doesn't actually implement CAG — it's lexical RAG mislabelled; Foundry-locked; useful as counter-example |
| local-rag | **Adapt for future operator dashboard** | TF-only, Foundry-locked, but the audit-path RAG pattern is right; lift patterns, not code |
| **obeaver (microsoft/obeaver)** | **Use directly — primary SLM runtime** | Tech Preview but **Qwen3-4B is first-class** via `obeaver convert`; ChatML formatter hard-coded; ORT GenAI engine + Foundry Local dual-engine; OpenAI-compatible API; one-day port of FLPerformance benchmark logic onto oBeaver's HTTP endpoint solves Qwen3-4B benchmarking |

---

## What This Tells Us About Lee's Asks

Lee asked three things in the call:
1. **Explore things that can be done on the edge**
2. **Try to run Beaver which runs on full CPU instead of GPU**
3. **Can I run something on my own machine**

### Answer 1: Things that can be done on the edge
The five repos collectively map to a "local-first AI" pattern set: model routing, paired-runtime diagnostics, performance benchmarking, CAG, and RAG. None of them are designed for traffic control specifically. **The transferable patterns are**:
- **Foundry Local as a local inference runtime** (Windows-first; ships catalog includes Phi-3.5-mini, Qwen2.5-3B, Mistral, gpt-oss-20b)
- **A/B paired-runtime comparison harness** (RouteLens pattern) — directly applicable to our Besu vs Tessera comparator
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

**Findings strengthen the synthesis's prior CPU verdict:**
- 10 ms hot-path budget is unreachable on this hardware (best: 374 ms, **37× over**)
- GPU vs CPU for the same model: **8.6× faster TTFT, 4× faster audit total**
- CPU-only is decisively non-viable for 3–4B SLMs in any sub-second control loop
- Qwen3 family is empirically more reliable than Qwen2.5 at small scale (validates the locked SLM choice)
- Smaller models are faster but produce garbage 30% of the time without CFG-constrained decoding

**Implication for the Edge Negotiator (unchanged by oBeaver):**
- **Hot path (single-token phase ID, target ~10 ms): CPU-only is infeasible.** Even with single-token output, TTFT alone exceeds the budget by 60–300×.
- **Audit path (post-hoc CoT, ~50–200 tokens, target <500 ms): CPU-only is borderline-infeasible.** Decode time alone for 100 tokens at 100 ms/tok is 10 seconds. Acceptable only if generated in background and consumed asynchronously by the audit log.
- **Future-work edge deployment**: a small NPU or integrated GPU is the realistic minimum. Pure CPU is not credible.

This remains a useful empirical finding for the dissertation: **"CPU-only edge inference for sub-second control loops is not feasible at the current state of the art for sub-7B SLMs, including with optimised inference runtimes such as ONNX Runtime via oBeaver."**

**However, oBeaver materially changes the benchmarking plan in a different way** — see Answer 3.

### Answer 3: Can I run something on my own machine? (RESHAPED by oBeaver)

Yes — and the picture is now better than the original FLPerformance-only plan suggested. The oBeaver investigation found that **Qwen3-4B is first-class supported via `obeaver convert Qwen/Qwen3-4B`** (Qwen3 architecture is hard-coded in `engine_ort.py:453-466` with ChatML formatter). This eliminates the "we need to write a separate harness" gap.

**Updated plan:**
1. **Install Foundry Local** (Windows-first, ships on Windows 10 — both oBeaver and FLPerformance use it)
2. **Install oBeaver** (with the documented `pyproject.toml` workaround for the broken `torch>=2.10.0` pin: `pip install --no-deps -e .`)
3. **Convert and run Qwen3-4B via oBeaver's ORT engine**: `obeaver convert Qwen/Qwen3-4B && obeaver serve Qwen/Qwen3-4B -e cpu` (or `-e cuda` once GPU support lands)
4. **Run Traffic-R1 via oBeaver's ORT engine** (also Qwen3-based, same conversion path)
5. **Run Phi-4-mini via Foundry Local engine** (or via FLPerformance — see split below)
6. **Write a small Python benchmark harness (~1 day)** that hits oBeaver's OpenAI-compatible HTTP endpoint and replicates FLPerformance's metrics (TTFT, TPOT, p50/p95/p99, structured-output validation)
7. **Capture latency distributions** for offline injection into the SUMO TraCI loop (Approach A from Prompt 6 §3)
8. **For CPU vs GPU comparison**: use FLPerformance's dual-alias pattern on Phi-4-mini proxies (Foundry catalog), then re-validate via oBeaver

**The split between the two tools:**
| Model | Tool | Engine | Why |
|-------|------|--------|-----|
| Qwen3-4B (primary) | oBeaver | ORT GenAI | Foundry catalog doesn't have it; oBeaver does via conversion |
| Phi-4-mini (comparison) | FLPerformance + oBeaver | Foundry Local | Better benchmarking UI in FLPerformance; oBeaver as cross-validation |
| Traffic-R1 (anchor) | oBeaver | ORT GenAI | Foundry catalog doesn't have it; oBeaver via conversion |
| Phi-3.5-mini (proxy) | FLPerformance | Foundry Local | Already in catalog; useful for FLPerformance-supported analyses |
| Qwen2.5-3B (proxy) | FLPerformance | Foundry Local | Already in catalog; useful for FLPerformance-supported analyses |

This dual-tool setup gives us latency profiles for all three locked models on the user's actual hardware, satisfying both the dissertation's empirical needs and Lee's "use oBeaver and experiment" request.

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

**Direct application: Besu vs Tessera comparator.** Replay identical decision streams through both backends, log every interaction, surface divergences. Add what RouteLens lacks: warm-up discards, paired Wilcoxon tests, BCa bootstrap CIs, fixed seeds, CSV export. Cite RouteLens as visible prior art for the comparator pattern; do not cite as a benchmarking methodology.

### Pattern 2: CPU-vs-GPU dual-alias benchmarking (from FLPerformance)
Load the same model under two aliases (`-cpu`, `-cuda`), benchmark both in the same suite, compare in UI. **Direct application: characterise the Edge Negotiator's hot-path and audit-path latency budget headroom under both compute targets.** The data feeds the dissertation's "what hardware would deployment require" discussion.

### Pattern 3: Sub-second lexical retrieval over static corpus (from local-cag and local-rag)
Both repos demonstrate that lexical (TF or keyword-scored) retrieval over a 20-doc corpus achieves sub-millisecond retrieval latency. **Direct application: audit-path NEMA/MUTCD reference lookup** — preload the constraint catalog as a small static corpus, retrieve relevant sections at query time for the SLM's CoT generation. This is "RAG over static corpus", which the local-cag analysis correctly identified as the pattern, regardless of the misleading repo name.

---

## CAG vs RAG: Resolved for the Edge Negotiator

The local-cag and local-rag analyses jointly settle the CAG/RAG question for our architecture:

| Integration point | Pattern | Why |
|-------------------|---------|-----|
| Hot path (single-token phase ID) | **Neither** | No latency budget for any retrieval; decision context already in prompt |
| Safety path (Z3 SMT) | **Neither (deterministic logical lookup)** | The Z3 verifier is not retrieval; it's constraint satisfaction |
| Audit path (post-hoc CoT) constraint preamble | **CAG (true CAG, not the local-cag mislabelled version)** | NEMA constraint catalog is small, stable, fits Qwen3-4B context window; prefix-caching makes per-decision overhead near-zero |
| Equity audit context (offline) | **Static lookup, not retrieval** | LSOA→IMD join is a SQL join, not RAG |
| Future-work operator audit dashboard | **RAG** | Unbounded growing audit log won't fit context; human-tolerable latency; mandatory citations |
| Future-work decision-precedent retrieval | **Neither** | Wrong shape — the corpus is numeric state vectors, not text; vector similarity over latents is the right tool |

**Important terminology note for the dissertation:** "CAG" is used loosely in the practitioner community. Lee Stott's `local-cag` repo is actually lexical RAG over a small in-memory corpus, not true context-augmented generation. The dissertation's discussion of CAG vs RAG should define the terms carefully and cite this loose usage as a reason for the careful definition.

---

## What's Missing — We Need to Build This Ourselves

The five repos cover model routing, A/B comparison, performance benchmarking, CAG, and RAG. **None of them cover:**

1. **Structured-output reliability evaluation** (XGrammar/Outlines JSON schema compliance under stress) — we need this for the SLM characterisation
2. **CoT faithfulness probing** (Turpin biasing, Lanham truncation) — we need this for empirical contribution #2
3. **Z3 safety verifier integration with SLM output** — domain-specific to traffic control
4. **Besu/Tessera Solidity contract + TraCI hook** — we have the Prompt 2 sketch; need to build it
5. **MaxPressure deterministic baseline implementation** — standard in the TSC literature; many open implementations exist

For (1), (2), and (3) we'll need a custom Python harness on top of the Foundry-supported model proxies (and a separate non-Foundry harness for Qwen3-4B and Traffic-R1). Estimated effort: 2–3 days of focused work to stand up the harness, then weeks of running.

---

## Concrete Next Steps

### This week
1. **Install Foundry Local** on the user's Windows machine
2. **Run FLPerformance against Phi-3.5-mini and Qwen2.5-3B on the user's GPU** to get baseline latency distributions
3. **Run FLPerformance again with `-cpu` aliases** to get CPU baselines (answers Lee's CPU question with hard numbers)
4. **Write a 200-line Python script using `llama.cpp` or `transformers`** to benchmark Qwen3-4B and Phi-4-mini directly with our actual prompt templates (the FLPerformance results plus this script give the full picture)

### Next 2–3 weeks
5. **Implement the SUMO Lambeth/Southwark network** (Prompt 4 protocol Steps 1–4)
6. **Stand up Besu in Docker dev mode** with the AuditLog.sol contract from the Prompt 2 sketch
7. **Stand up Tessera as second backend** for the comparator
8. **Wire the TraCI ↔ Python agent ↔ ledger loop** (Python sketch from Prompt 2)
9. **Implement MaxPressure baseline** (existing open-source implementations exist)
10. **Wire Z3 verifier with NEMA constraint set**

### Patterns to lift, not code
11. **RouteLens comparator skeleton** (~250 LOC) → adapt for Besu vs Tessera comparator and SLM A/B harness
12. **Local-cag section-scoring pattern** → adapt for audit-path NEMA constraint preamble (true CAG via prefix caching)
13. **FLPerformance CPU/GPU dual-alias pattern** → use for our SLM benchmarking discussion

### What NOT to do
- **Don't depend on router-demo-app or any cloud-routing pattern.** Latency is fatal and dissertation is local-only.
- **Don't expect Foundry Local to cover Qwen3-4B or Traffic-R1.** Plan a separate harness from the start.
- **Don't trust the "CAG" name in `local-cag`.** The implementation is RAG. The dissertation needs careful CAG/RAG definition.

---

## Open Questions for Lee (Industry Supervisor)

1. **~~What is "Beaver"?~~** RESOLVED — `microsoft/obeaver`, your 3 April 2026 email. Cloned, investigated, integrated into the benchmarking plan. Qwen3-4B works first-class via `obeaver convert Qwen/Qwen3-4B`.
2. **Is the Foundry Model Router pattern relevant for Edge Negotiator's Qwen3 mode-switching** (thinking vs non-thinking)? The cloud router pattern adds dispatch latency that's fatal for the hot path, but the *idea* of mode-switching is exactly what Qwen3 supports natively. Should I treat this as "deterministic gate, not learned router" in the dissertation?
3. **For CPU-only inference, oBeaver confirms the FLPerformance finding: hot path is GPU-only territory for 3–4B SLMs.** Should I reframe the dissertation's "edge deployment" framing accordingly, or are you specifically interested in CPU-only as a fallback / lower-tier deployment mode? oBeaver's NPU-acceleration roadmap may be the realistic future-work path for true edge deployment.
4. **For RAG/CAG: the local-rag and local-cag patterns are useful for the audit path and future operator dashboard, not the hot path.** Want me to design the audit-path NEMA-constraint CAG into the implementation now, or scope it to "designed but not implemented" in this dissertation?
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
├── obeaver\                 ← cloned, source code reviewed (now primary SLM runtime)
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
