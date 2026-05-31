# Edge Negotiator dissertation — scope lock-in

**Status:** LOCKED as of 2026-04-26. Do not propose alternative topics, models, hardware, corridors, or ledger platforms without re-opening this file. If a future agent disagrees with anything here, raise it explicitly with the user before acting on it.

---

## 1. What this dissertation is

UCL MSc Systems Engineering for IoT (SEIOT) dissertation. Title (working): *"The Edge Negotiator: a Quarterly Equity Audit Protocol for LLM-Driven Decentralised Traffic Signal Control."*

**Primary novel contribution** = the first executable equity-audit protocol for an LLM-driven traffic signal controller, evaluated on a real London corridor in SUMO, with results anchored to a permissioned blockchain ledger.

**Secondary novel contribution** = a counterfactual demographic re-run probing the controller for indirect-discrimination behaviour, plus a small CoT-faithfulness sub-experiment in the discussion chapter.

## 2. Supervisors

- **Dr Akin Delibasi (UCL)** — distributed systems, swarm robotics, AcoustoBots. Reviews: SUMO experimental design, MaxPressure shield correctness, FC-vs-UC interventional comparison logic, statistical methodology.
- **Lee Stott (Microsoft)** — Foundry Local, Phi-4, Microsoft Agent Framework. Reviews: Phi-4-mini access via Foundry Local, UK ATRS / EU AI Act framing, public-sector commercial fit. Lee provided four critique pillars on the STSD coursework that the dissertation must answer:
  - **S1.** CoT exposure risks in safety-critical control
  - **S2.** Operationalising fairness / equity audits in practice
  - **S3.** Evidential basis for cited production deployments
  - **S4.** Performance and governance trade-offs of the blockchain audit layer

## 3. Locked topic — what we are doing

Three deliverables, in priority order:

1. **PRIMARY: Quarterly Equity Audit Execution.** Execute the 18-step protocol from `01-research/prompt-outputs/prompt4-equity-audit-protocol.pdf` end-to-end on the Elephant & Castle–Brixton corridor (5×5 km, Lambeth/Southwark, London). Compute Gini, Rawlsian max-min, DIR, pedestrian parity with BCa bootstrap CIs and Holm–Bonferroni correction. Pass thresholds: Gini < 0.30, DIR ≥ 0.80, pedestrian parity ≤ 1.25. Answers Stott S2.
2. **SECONDARY: Counterfactual Demographic Re-run.** Re-run the same SUMO demand with the LSOA → IMD/Census join shuffled. Permutation-test |Δ delay| under the null that the SLM is demographic-blind. Answers Stott S2 indirect-discrimination leg.
3. **DISCUSSION CHAPTER: CoT Faithfulness Probe.** Inject biased hints into ~1,000 phase decisions. Report channel-divergence rate per Young2026 four-quadrant taxonomy. Required by `prompt3-cot-faithfulness.pdf` §4 design checklist. Answers Stott S1 minimally.

**Effort budget:** ~310 student-hours of novel work, well inside a 6-month MSc.

## 4. Locked architectural substrate — do not vary

| Layer | Locked choice | Source of decision |
|---|---|---|
| Primary SLM | Qwen3-4B (thinking + non-thinking modes) | `prompt1-slm-shortlist.pdf` |
| Comparator SLM | Phi-4-mini (3.8B) | Microsoft alignment + prompt1 |
| Anchor model | Traffic-R1 (3B) — but only with Prompt 5 hedged framing | `prompt5-deployment-claims-verification.pdf` Claim 1 |
| Deterministic shield | MaxPressure (Varaiya formulation; MP-Delay open derivation) | coursework Code 2; Survey-TSC + MP-Delay |
| Hot-path output | Single-token phase ID | prompt3 §1 |
| Audit-path output | Structured JSON with bounded `reasoning_text` field, `trace_type:"post_hoc_justification"`, reasoning field precedes phase field per Tam et al. | prompt3 §4 |
| Constrained decoding | XGrammar or Outlines | prompt3 §2.4 |
| Formal verifier | Z3 SMT for hard safety constraints (no conflicting greens, min clearance) | prompt3 §2.4 |
| Primary ledger | Hyperledger Besu QBFT in `--network=dev` Docker, single container, web3.py client | `prompt2-blockchain-comparison.pdf` §6 |
| Comparator ledger | Trillian Tessera (RFC 6962 Merkle log) — for the §4 "does this need a blockchain at all" question | prompt2 §6 secondary recommendation |
| On-chain payload | 32-byte SHA-256 hash; full 2 KB payload off-chain in SQLite | prompt2 implementation sketch |
| Simulator | Eclipse SUMO 1.20+, Python TraCI | prompt4 §3 Step 1 |
| Network extract | OpenStreetMap, bbox `[51.450°N, -0.125°W]` to `[51.495°N, -0.080°W]` | prompt4 §3 Step 1 |
| Demographic joins | LSOA boundaries (ONS 2021) → IMD 2019 deciles → Census 2021 ethnicity (TS021) | prompt4 §2.2 |
| k-anonymity floor | Exclude any LSOA with population < 500 or < 50 in any audited ethnic category | prompt4 §3 Step 4 |
| Statistical tests | Welch's t, Mann-Whitney U, BCa bootstrap (B = 10,000), Holm–Bonferroni for m = 4 | prompt4 §2.3 |
| Reporting standard | UK ATRS Tier 1 + Tier 2 templates | prompt4 §2.5 |

**Hardware:** developer laptop with RTX 4050 (or any consumer GPU). The Quarterly Audit needs ~15 hours of SUMO compute per quarter (60 runs × 15 min). No edge hardware (Jetson, Hailo) is required for the locked thesis — those topics were on the alternatives list and are explicitly out of scope.

## 5. Stott's four critiques — how the locked thesis answers each

| Pillar | Answered by | Evidential weight |
|---|---|---|
| **S1** CoT exposure risks | Discussion-chapter faithfulness probe (~60 hrs); structured-JSON-with-bounded-CoT design from prompt3 §4 specified in methodology chapter | Sufficient |
| **S2** Equity-audit operationalisation | Primary chapter (#4 protocol execution) + secondary chapter (#5 counterfactual) | Strong |
| **S3** Evidential basis for deployments | Methodology + limitations chapters cite prompt5's hedged framings verbatim; Iroha 2 claim corrected; Traffic-R1 framed as anchor with vendor-affiliation caveat; Southampton/Minima drone dropped from Scenario 1 references | Sufficient |
| **S4** Blockchain trade-offs | Architecture chapter cites prompt2 §3 comparison matrix and §4 "does this workload need a blockchain" position; thesis runs Besu QBFT *and* Tessera comparator side-by-side as prompt2 §6 secondary recommendation | Strong |

## 6. The 90-day Study Away from India constraint

The student will spend up to 90 days of dissertation work remotely from India under UCL Academic Manual §3.5.2.

- **Highest-risk compliance issue:** Graduate Route eligibility under Immigration Rules Appendix Graduate GR 6.1. A 90-day absence on a 12-month MSc may disqualify Graduate Route unless treated as a "permitted study abroad programme". **Verify with UCL Student Immigration Compliance Team (immigration.compliance@ucl.ac.uk) before any travel commitment.** See `05-supervision/ucl-india-compliance-landscape.pdf`.
- **Data protection:** Aggregate hourly vehicle counts are not personal data under UK GDPR (Recital 26 motivated-intruder test) or under DPDPA 2023 Section 2(t). No cross-border transfer issue. The audit needs no personal data and no Indian municipal data.
- **Why the locked topic fits this constraint:** the entire empirical work is SUMO-on-a-laptop. Of the ten topics reviewed, only #4 + #5 are fully London-resource-independent. Topics requiring Jetson hardware (#9), camera renders (#10), liboqs JNI (#7), or vLLM hooks (#3) would have anchored the student to UCL.
- **Optional Bengaluru secondary chapter:** see `06-literary-survey/PROMPT8.md`. Only added if primary work finishes ahead of schedule and the user explicitly opts in. No commitment.

## 7. Cited-claim hygiene (from prompt5)

These corrections are mandatory and already partially reflected in the coursework:

- **Traffic-R1 (Zou et al. 2025):** UNVERIFIED. Frame as an example of emerging LLM-TSC research, not as evidence of production deployment. Note the PCITECH (SSE: 600728) vendor-academic affiliation. Do not cite the "55,000 daily drivers" figure as established fact.
- **Iroha 2:** DISPUTED. Bakong runs Iroha 1, not Iroha 2. Iroha 2 is at v2.0.0-rc.2.1 with no large-scale production user. Drop the "~1 s finality" figure or correct to "within seconds". Coursework reference [9] needs updating.
- **Southampton/Minima drone (coursework reference [31]):** VENDOR-ONLY. Drop from Scenario 1 or relegate to footnote. The "first blockchain black box" framing must be removed.
- **Google Project Green Light, Alibaba City Brain, Yunex FUSION at TfL, Jetson Orin Nano benchmarks:** PARTIALLY VERIFIED. Use prompt5's recommended hedged framings verbatim where these are cited.

## 8. What the dissertation will *not* claim

To prevent scope drift and false-confidence drafting:

- Will not claim absolute delay numbers transfer to real London deployment. Only relative fairness comparisons (FC vs UC, LSOA-A vs LSOA-B) are robust to SUMO's sim-to-real gap.
- Will not claim CoT logging is a faithful causal record of model computation. Position (d) from prompt3 §3 only: "conditionally valuable post-hoc justification" with the design checklist enforced.
- Will not claim the Bengaluru secondary chapter unless it is actually executed. The PROMPT8 deep research builds the evidence base regardless.
- Will not claim production readiness of Hyperledger Iroha 2. Will use Hyperledger Besu QBFT in dev mode, which is well-benchmarked.
- Will not claim regulatory standing under the Equality Act 2010 or DPDPA 2023. The audit demonstrates due-diligence methodology, not a tested legal position.

## 9. Out-of-scope topics (explicitly rejected)

These were considered and rejected. Do not revisit without re-opening this file:

- AcoustoBot semantic swarm (Akin's research but not on the chosen Edge Negotiator path)
- ML-DSA PQC overhead study (high JNI risk, low S2 alignment)
- Activation-steering attack on audit trail (too high-risk for 6 months)
- Phi-Silica NPU agentic benchmark (requires Copilot+ PC hardware not in budget)
- Microgrid drone swarm fault isolation
- Air-gapped disaster triage swarm
- Durable Agent Orchestration chaos test
- CMVK memory-poisoning defence benchmark
- Eykholt-style adversarial patch (interesting but out of scope for #4-anchored thesis)
- Independent Traffic-R1 reproduction as primary contribution (acceptable as a comparison run inside the primary chapter, but not as the headline)

## 10. File map

```
00-SCOPE-LOCKIN.md                  ← this file. Single source of truth.
01-research/
  project-proposal.pdf              ← original proposal (pre-lockin)
  synthesis.md                      ← cross-prompt synthesis
  prompt-outputs/                   ← seven completed deep-research prompts:
    prompt1-slm-shortlist.pdf       ← model selection (Qwen3-4B + Phi-4-mini + Traffic-R1 anchor)
    prompt2-blockchain-comparison.pdf  ← ledger selection (Besu QBFT + Tessera comparator)
    prompt3-cot-faithfulness.pdf    ← CoT logging design checklist (Position d)
    prompt4-equity-audit-protocol.pdf  ← THE PRIMARY CHAPTER PROTOCOL
    prompt5-deployment-claims-verification.pdf  ← seven-claim hedged-framing list
    prompt6-experimental-design.pdf
    prompt7-methodology-framework.pdf
    Small Language Models for Decentralized Traffic Signal Control_ A 2026 Field Guide.pdf
02-experiments/                     ← prior experiment scaffolding (FLPerformance, obeaver, router-demo-app, etc.) — most predates the locked scope and is reference material
03-implementation/                  ← empty; will hold the locked thesis implementation
04-writing/                         ← empty; will hold thesis chapters
05-supervision/
  ucl-india-compliance-landscape.pdf  ← Study Away + DPDPA + IUDX background
06-literary-survey/
  INDEX.md                          ← prompt-by-prompt summary
  PROMPT8.md                        ← India deep-research brief (locked, not yet executed)
  registry.json                     ← 147 papers, locked
  priliminary-research.md           ← Prompt 1 output (CoT faithfulness)
  deterministic-slm.md              ← Prompt 2 output (deterministic SLM 7 domains)
  microsoft-foundry.md              ← Prompt 3 output (Microsoft commercial intel)
  robotics.md                       ← Prompt 4 output (multi-agent CPS)
  traffic-llms.md                   ← Prompt 6 output (traffic LLM survey)
  edge-blockchain.md                ← Prompt 7 output (edge blockchain)
  papers/                           ← cached PDFs of the 147 sources
STSD/
  coursework.pdf                    ← submitted coursework (Codes of Conduct paper)
  STSD _ week 5/7/8.pdf             ← module materials
```

## 11. Re-opening conditions

Reopen this file (and treat its contents as up-for-revision) if and only if:

- A supervisor explicitly asks for a topic change in writing
- The Quarterly Audit protocol fails to produce results within 8 weeks of starting implementation (then reassess scope)
- A material defect is discovered in any locked architectural choice (e.g., Foundry Local cannot serve Qwen3-4B at all)
- The student withdraws from Study Away to India

Anything else is scope creep. Honour the lockin.
