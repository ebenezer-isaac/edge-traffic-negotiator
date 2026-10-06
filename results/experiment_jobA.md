# Experiment Job-A — citation-faithful legal-reasoning note (PILOT)

- **Model:** Phi-4-mini-instruct-generic-gpu:5 (frozen, Foundry Local, temperature 0)
- **Split:** novel  ·  **n = 97**  ·  corpus = 18 law_rules
- **Corpus presentation:** CAG (whole-corpus-in-context, all 18 rules) is PRIMARY; TF-IDF k=10 RAG retained as head-to-head comparator (§2/§3)
- **RAG arm source:** REUSED from the committed run (not re-run this session)
- **Gold:** POLICY-BASE-DERIVED PROXY (annotator-blind, event_type->applies_when); NOT human-graded; NOT the D5 gate
- **CAG determinism (temp 0):** 3/3 notes identical-citation on re-run (rate 1.0)

> PILOT / PROXY. The gold is policy-base-derived (event_type -> applies_when), annotator-blind, NOT human-graded. This is NOT the §12 D5 gate (which needs human faithfulness grading + 2-rater kappa >= 0.6). D5 is NOT claimed passed.

## 3-way results (novel split)

| Metric | SLM RAG (k=10) | **SLM CAG (primary)** | Un-rigged template |
|---|---|---|---|
| Citation-correctness (mean F1) | 0.338 | 0.124 | 0.479 |
| Precision (mean) | 0.416 | 0.247 | 1.000 |
| Recall (mean) | 0.343 | 0.082 | 0.316 |
| Exact-set-match rate | 0.000 | 0.000 | 0.000 |
| FCR (per note) | 0.526 | 0.000 | 0.000 |
| FCR (per citation) | 0.544 | 0.000 | 0.000 |
| Fabrication rate (per note, SCORED) | 0.052 | 0.000 | 0.000 |
| Fabricated citations (count, SCORED) | 5 | 0 | 0 |
| Abstention rate | 0.278 | 0.753 | 0.000 |
| Parse-failure rate (counts as failure) | 0.000 | 0.000 | 0.000 |

## Split-dominance verdicts (§3 pinned resolution)

- Pinned PRE-RUN (pilot): FCR ceiling (per note) = 0.2, MDE on citation-F1 = 0.1
- **RAG vs template:** F1 delta = **-0.141** · clears MDE: False · under FCR ceiling: False → **TEMPLATE_WINS** (citation-F1 gap -0.141 <= -MDE; the honestly-scored template beats the SLM note)
- **CAG vs template:** F1 delta = **-0.356** · clears MDE: False · under FCR ceiling: True → **TEMPLATE_WINS** (citation-F1 gap -0.356 <= -MDE; the honestly-scored template beats the SLM note)

## CAG − RAG delta (does whole-corpus reason-then-classify move the needle?)

- ΔF1 (CAG − RAG) = **-0.214**
- ΔFCR per note (CAG − RAG) = **-0.526**
- Δfabrication rate per note (CAG − RAG, SCORED) = **-0.052**
- CAG fabrication ATTEMPTS dropped by the controller = **0** (scored fabrication count: CAG 0 vs RAG 5)
- CAG scored-fabrication is ~0 BY CONSTRUCTION: the reason-then-classify controller drops any judged-applicable id absent from the 18-rule corpus. cag_fabrication_attempts_dropped_by_controller counts what the model tried to fabricate before the drop.

## Per-job latency (§8 FLPerformance nearest-rank; D-lat)

- **Job A (CAG reason-then-classify):** n=96 (warmup 1 discarded) · P50 37.82s · P95 39.87s · P99 40.75s · max 40.75s · mean 36.06s
- Method: FLPerformance nearest-rank (index=ceil(p/100*N)-1); warmup discarded
- Small-N caveat: at N < 100 the nearest-rank P99 index collapses to the last sample, so Job-A P99 is effectively the observed MAX. Reported with N + warmup.
- Architectural finding: the tens-of-seconds Job-A P99 is the quantitative justification for the §3/§4 invariant that the SLM is post-hoc, non-evidential, counsel-gated and NEVER on the real-time gate path.

## Caveats

- Gold is a policy-base-derived PROXY for the §3 human-graded applicable-rule labels; this is a PILOT (n=97), not the §12 D5 gate (needs human grading + 2-rater kappa>=0.6). D5 is NOT claimed passed.
- Citation-correctness is measured vs the proxy gold, not statute-text faithfulness graded by qualified humans.
- CAG scored-fabrication is ~0 BY CONSTRUCTION (the reason-then-classify controller drops out-of-corpus ids); see cag_minus_rag for the raw fabrication ATTEMPTS the controller dropped.
- The Job-A note is internal/counsel-gated and never enters the evidence pack.
