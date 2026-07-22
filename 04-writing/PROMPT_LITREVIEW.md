# Prompt — draft Chapter 2 (Literature Review) of the Edge Negotiator dissertation

Run this prompt against an agent that has full read access to this repository. It produces a single Markdown file `04-writing/02-literature-review.md` containing the dissertation's Chapter 2 in submission-ready form.

---

## Mandatory pre-reading (in this order, no skipping)

1. `00-SCOPE-LOCKIN.md` — the locked topic, architecture, supervisors, Stott pillars, cited-claim hygiene, and out-of-scope rejections. The literature review must be consistent with every locked decision in this file.
2. `06-literary-survey/INDEX.md` — map of the 147-paper survey across eight prompts.
3. `06-literary-survey/registry.json` — master inventory. Every citation in the chapter must use a short-tag that exists here. If a tag is needed and missing, stop and ask the user; do not invent.
4. The eight prompt outputs in `06-literary-survey/`:
   - `priliminary-research.md` (Prompt 1 — CoT faithfulness)
   - `deterministic-slm.md` (Prompt 2 — deterministic SLM + fallback + ledger)
   - `microsoft-foundry.md` (Prompt 3 — Microsoft commercial intelligence)
   - `robotics.md` (Prompt 4 — multi-agent CPS)
   - `traffic-llms.md` (Prompt 6 — traffic LLM/SLM control) — **the primary anchor**
   - `edge-blockchain.md` (Prompt 7 — permissioned blockchain & PQC)
   - `india-context.md` (Prompt 8 output, when present) — Indian regulatory framing
5. The five PDF prompt outputs in `01-research/prompt-outputs/`:
   - `prompt1-slm-shortlist.pdf` (Qwen3-4B + Phi-4-mini + Traffic-R1 anchor decision)
   - `prompt2-blockchain-comparison.pdf` (Besu QBFT + Tessera comparator decision)
   - `prompt3-cot-faithfulness.pdf` (Position d + six-property design checklist)
   - `prompt4-equity-audit-protocol.pdf` (the 18-step protocol — read but do not duplicate; this is methodology, not lit review)
   - `prompt5-deployment-claims-verification.pdf` (the seven hedged framings)
6. `STSD/coursework.pdf` — the submitted Codes of Conduct paper. The lit review must be consistent with the framing already taken in the coursework, but expanded to academic-paper depth.

If `india-context.md` (Prompt 8) is not yet present, write Sections 2.8 and 2.9 with placeholders flagged `<!-- TODO: integrate Prompt 8 sources -->` and proceed; do not block.

## What the chapter must do

The literature review chapter has six jobs in this dissertation, no more and no less:

1. **Establish the problem space.** Traffic signal control, why classical adaptive systems (SCOOT, SCATS) are insufficient, why semantic reasoning matters.
2. **Review the technical baseline.** Reinforcement learning for traffic signal control — the dominant prior approach the dissertation must compare against.
3. **Position the LLM/SLM-for-TSC frontier.** What sub-7B SLM controllers exist; what edge-hardware constraints they operate under; what gaps remain.
4. **Justify every architectural choice.** The reader should finish §§2.5–2.7 understanding *why* the design chose a frozen Phi-4-mini on-device reasoner, a MaxPressure shield, SUMO on the real Euston Road (A501) corridor, and a Certificate-Transparency-style, quorum-anchored, cross-audited accountability log (mechanism credited to prior art) — because the literature compels these choices.
5. **Scaffold the legal-accountability framing.** Accountability of automated public-sector decisions, UK statute and case law (RTA 1988 duties, GDPR/DPA 2018, public-law liability), the firewall between a mechanically-verifiable provenance evidence pack and a counsel-gated origin classification, and why no existing signal controller produces such a record.
6. **Land the novel object.** State the self-referential coupling (attack lever = signal phase = honest-witness coverage gate) as a conditional lemma, separate it from the two co-equal engineering contributions and the credited accountability mechanism, and explain which increment no prior work occupies.

Anything outside these six jobs belongs in another chapter. Specifically:

- **Do not duplicate methodology.** The 18-step audit protocol, the SUMO calibration recipe, the Z3 verification rules — these are Chapter 3.
- **Do not present results.** No SUMO numbers, no Gini values, no latency tables.
- **Do not editorialise.** The chapter is a critical synthesis, not a polemic. Engage with weaknesses (vendor bias, missing benchmarks, paywalled foundational papers) without sneering.
- **Do not list papers.** A list of summaries is not a literature review. Synthesise themes and cite *in support of* claims.

## Chapter structure and word budgets

Total target: **10,000–12,000 words** (typical UCL MSc literature-review chapter). Treat the budgets below as soft targets — go ±20% per section if the material warrants, but do not exceed 13,000 words total.

### 2.1 Introduction and roadmap (~400 words)

State what the chapter establishes, the order of sections, and the framing claim that the chapter will close on (the self-referential coupling, measured on the real Euston A501 corridor). One paragraph per section preview.

### 2.2 The traffic signal control problem and classical adaptive baselines (~1,200 words)

- Brief history: pre-timed → vehicle-actuated → adaptive (SCOOT, SCATS) — anchor in `Survey-TSC` taxonomy.
- The Max-Pressure family: cite `MP-Delay` and `MP-Pedestrian` as open derivations (note Varaiya 2013 is paywalled). Explain provable throughput stability and why MP is the deterministic shield in the locked architecture.
- `PressLight` as the theoretical bridge between Max-Pressure and reinforcement learning.
- One paragraph on the SCOOT/SCATS installed base in London and why a per-cabinet SLM controller is intellectually distinct from a centralised legacy adaptive system.
- Land on: *the locked thesis adopts Max-Pressure as the deterministic shield, not as the controller — this is the first architectural decision the literature demands.*

### 2.3 Reinforcement learning for traffic signal control (~1,200 words)

Synthesise four threads, each with 2–3 sources:

- **Single-intersection DQN** — `MPLight`, `FRAP` (phase-pair invariance reduces exploration 64×n⁸ → 16×n⁴).
- **Network-level cooperation** — `CoLight` (graph attention), `Adv-XLight` (pre-LLM SOTA on Jinan/Hangzhou/NY), `MA2C-TSC` (decentralised actor-critic on 5×5 grid which is structurally analogous to the dissertation's synthetic unit-test grid ahead of the real Euston A501 stretch).
- **City-scale** — `CityLight` (Manhattan 196, Beijing 13,952).
- **Safety and adversarial robustness** — `SafeLight`, `CFLight`, `Adv-DRL-TSC`, `T-REX`, `CollusionVeh` — establishes the threat model the locked thesis inherits.

Land on: *RL controllers are the empirical comparison baseline (the dissertation will compare against MaxPressure, MPLight, CoLight, Adv-CoLight) but the locked architecture is not RL — and the literature shows RL is brittle under sensor faults and adversarial V2X, motivating the SLM + deterministic-shield combination.*

### 2.4 Large language models in traffic signal control (~1,500 words)

This is the densest section. Synthesise five sub-currents:

- **Pioneering controllers** — `LLMLight` (LightGPT, Qwen-0.5B FT variant); `Open-TI/ChatZero` (Llama2-7B/13B as TSC dialog meta-agent).
- **Cooperation across intersections** — `CoLLMLight` (Llama-3.1-8B FT, spatiotemporal neighbour passing); `HeraldLight` (dual-LLM agent + critic, herald-guided prompts).
- **Tool-use / hybrid LLM+RL** — `LA-Light` (GPT-4 + tool calls under sensor failure); `iLLM-TSC` (GPT-4 verifier on PPO RL); `REG-TSC` (distributed RAG agents).
- **Vision-language and meta-control** — `VLMLight`, `Virtual Traffic Police`.
- **Sub-7B / edge-deployable** — `Traffic-R1` (Qwen-2.5-3B + agentic RL — apply prompt5 Claim 1 hedged framing **without exception**: the "55,000 daily drivers" production-deployment claim is UNVERIFIED and the PCITECH SSE: 600728 vendor-academic affiliation must be flagged); `CuraLight` (Gemma-3 LoRA + DeepSeek ensemble curation); `Multi-Agent-LLMTSC` (LightGPT ensemble voting); `CoMAL` (Qwen-7B/32B/72B mixed autonomy); `EvolveSignal` and `SignalClaw` (LLM as offline algorithm-discovery agent — distinct from runtime LLM controllers).

Critical synthesis paragraph: only `Traffic-R1` (3B) and `CuraLight` (Gemma-3) combine sub-7B + multi-intersection + MaxPressure-comparable, and only Traffic-R1 has any edge-deployment claim — but no published paper reports validated tokens/sec, watts, or thermal numbers for the 4–8B class on a Jetson Orin Nano running an actual SUMO loop. This is one of the gap rails the dissertation rides.

Land on: *the LLM-TSC frontier has matured to sub-7B controllers in the last 18 months, but no work to date characterises what such a controller can and cannot hold mechanically accountable under a compromised-insider emergency preemption; this absence is the dissertation's primary opening.*

### 2.5 Small language models on edge hardware (~900 words)

- Microsoft Phi-4 family from `Phi4-Reasoning` — mid-fusion architecture, 200B-token curation, 128k context.
- The on-device reasoner is a single frozen Phi-4-mini (no Qwen backbone). Review the adjacent Qwen line (cite via `Traffic-R1` and `CoMAL`) only as the closest prior-art sizing context for a sub-7B TSC reasoner, explicitly stating the dissertation does not adopt a Qwen backbone.
- Edge benchmarks: `Edge-Orin-Bench` (Pythia 70M-1.4B sizing grid), `Edge-AGX-Power` (INT4 caveat — Ampere has no native INT4), `Edge-SLM-Energy` (Llama-3.2 0.57s on Orin Nano GPU; Phi-3 Mini best accuracy / worst energy), `Edge-Hailo` (Hailo-10H 6.91 tok/s @ 1.87W — only published Hailo-10H LLM benchmark), `Edge-Quant` (Q4_K_M sweet spot), `Edge-Reason` (decode dominates 99.5%), `FPGA-Qwen`, `Edge-First`, `ELIB`.
- Apply prompt5 Claim 7 hedged framing: NVIDIA's 38–43 tok/s figure is MLC-engine-specific; independent reproductions are 7–15% lower.
- Microsoft Phi-Silica claims from `microsoft-foundry.md` — hedge appropriately.

Land on: *this dissertation runs a single frozen Phi-4-mini on a developer-class GPU, not on Jetson — a deliberate scope choice, since the empirical contribution is the measured characterisation of the phase-coupled coverage boundary on the real Euston A501 corridor, not the edge benchmark. The edge-benchmark literature is reviewed because it constrains future deployment, not because the system runs on edge hardware.*

### 2.6 Chain-of-Thought faithfulness in safety-critical control (~1,400 words)

This section directly answers Stott S1. Synthesise four threads:

- **Foundational unfaithfulness** — `Turpin2023` (behavioural perturbation, BIG-Bench Hard accuracy degradation); `Lanham2023` (early answering, adding mistakes, paraphrasing, filler tokens, AOPC metric).
- **Frontier reasoning models** — `Chen2025` / `CoT-Faith` (under-20% faithfulness rate on hint injection); `Gantt2026` (models flatly deny hint use even when permitted); `Arcuschin2025` (implicit post-hoc rationalisation in unperturbed prompts, GPT-4o-mini 13% mutually-exclusive-yes rate).
- **Mechanistic and channel divergence** — `Tutek2025` (unlearning-based diagnosis); `Ye2026` (NLDD metric, Reasoning Horizon k* at 70-85% of chain length); `Young2026` (four-quadrant taxonomy: Thinking-Only 55.4%, Transparent 32.3%, Unacknowledged 11.8%, Surface-Only 0.5%); `Han2026` (RFEval; standard RLVR degrades faithfulness 10–14 points); `Basu2026` (SLRC step-level metrics + Lyapunov stability bounds).
- **SLM-specific and embodied/control** — `Masri2026` (Qwen3-0.6B 88.12%, Phi-4-Mini-Reasoning 228s/inference + <10% accuracy under RAG); `Shakib2026` (low-resource surface-level faithfulness patterns); `Zawalski2024` (VLA decoder ignores CoT logic — relies only on entity-reference integrity, ±4% physical performance under blind noise / spatial reversal); `Duan2025` (Fast ECoT 7.5× latency reduction); `Tan2025` and `OneVL2026` (Latent CoT abandons text entirely for autonomous driving — 88.84 PDM-score on NAVSIM); `Liao2025` (CoT-Drive — explicit CoT diverges from kinematic ground truth); `Ye2026_Flood` (IP-CoT inverse prompting, 95.32% accuracy via grammar-constrained decoding); `Li2025`, `Xiong2025` (RAGLens SAE-based hallucination detection); `Wang2026` (autoregressive unfaithfulness mechanics); `Puerto2025` (LRM contextual privacy risks).
- **Engineering remedies** — `Hase2026` (Counterfactual Simulation Training — 35-point monitor-accuracy improvement); `Guan2024` (deliberative alignment); the prompt3 §4 design checklist as the synthesis the dissertation adopts.

Land on: *the literature converges on the conclusion that explicit CoT cannot be trusted as a faithful causal record — it is post-hoc rationalisation. This dissertation therefore firewalls the reasoner's reasoning into a non-evidential, counsel-gated internal note validated against cited statute but never trusted; accountability is carried by the signed, quorum-anchored log, not by the trace.*

### 2.7 Accountability logs for automated-decision provenance (~1,200 words)

This section directly answers Stott S4. Synthesise three threads:

- **Why audit ledgers** — `BC-AI-Decision` (permissioned-chain AI-decision provenance design); `BC-Enforce` (Hyperledger Fabric + IPFS + ECDSA for intersection-camera audit); `BC-TSC` (only paper directly targeting blockchain audit for traffic signals — mitigates I-SIG single-vehicle congestion attack). Acknowledge the prompt2 §4 critical position: blockchain solves a trust problem this workload does not have, but is academically defensible as an architectural choice.
- **Empirical benchmarks of permissioned EVM** — `Veloso2026` (QBFT 200 TPS knee, sub-second latency, $239.60/month on AWS), `Khoshaba2023` (validator participation 0.85–0.95 sweet spot), `Ucbas2023` (Fabric vs Besu IoT — Besu degrades from 4.37s to 96.58s under 5,000 concurrent tx), `Pierro2024` (Besu vs Quorum payload bloat decay 100s TPS → sub-50 TPS at 50 KB), `Fan2025` (QBFT vs IBFT 2.0 six-node), `Catarino2024` (QBFT vs Clique determinism trade-off), `Kulothungan2024` (QBFT IoT gateway aggregation), `Polito2022` (Fabric channel privacy vs Tessera/Orion off-chain modules).
- **Privacy enclaves and PQC overhead** — `Alattar2025` (Quorum + Tessera 28-32s cross-chain latency); `AITH` (ML-DSA-87 4,627-byte CDC + Merkle chain to bypass per-event PQC signing); `Alown2025` and `Zheng2026` (Verkle trees compress proofs to O(log_k N), 5ms per-batch verification with ARM NEON); `BC-V2X-Sec`, `BC-CCAM`, `BC-Offload`, `SALT-V` (V2X ML-blockchain trade-offs and lightweight 5G V2X authentication — 0.035 ms compute, 1 ms e2e); `BeACONS` (RSU-anchored DID).

Land on: *the accountability layer is a Certificate-Transparency-style, quorum-anchored, cross-audited log whose immutable-provenance mechanism is credited to prior art (RFC 6962 and successors), built from at least two independent witnesses (a transparency log plus a named single-node ledger RPC, reconciled by a named cross-auditor). A permissioned Besu QBFT ledger is demoted to one optional anchoring witness, and the evaluation quantifies its marginal latency/cost/governance overhead over a plain cross-audited transparency log rather than presuming BFT consensus is needed. Do NOT foreground a blockchain as the contribution; do NOT cite Iroha 2.*

### 2.8 Legal accountability for automated public-sector decisions (~1,500 words)

Three sub-currents:

- **Accountability-failure case studies** (academic-register expansion): UK Ofqual A-level grading 2020 collapse; Dutch SyRI welfare-fraud algorithm Court of The Hague 2020 ruling; Amazon recruiting tool 2018 abandonment; Chicago Strategic Subject List OIG 2020 audit; NYC ADS Task Force 2018-2019 transparency failure. Frame each as an *accountability* failure — absence of a verifiable, independently-scrutinisable decision record — not as a disparate-impact/equity harm. Cite by registry tag.
- **UK legal framing, with EU comparator** — lead with UK domestic law: Road Traffic Act 1988 s.36/s.38 duties and Highway Code evidential status; Data Protection Act 2018 / UK GDPR automated-decision provisions; public-law highway-authority liability (Goodes v East Sussex, Gorringe v Calderdale); Equality Act 2010 PSED s.149 as a public-law accountability duty; UK ATRS Tier 1/2 as a transparency-and-logging expectation (not an equity metric); Bridges v South Wales Police (2020) and Schufa CJEU C-634/21 as accountability precedents. Cite the EU AI Act (Annex III road-traffic classification, Article 12 logging) only as an external comparator confirming that verifiable event logging is a converging expectation — not as the governing framework.
- **Comparative accountability framing: India** — DPDPA 2023 + DPDP Rules 2025 phased calendar; NITI Aayog Responsible AI Part 1 + Part 2 (accountability principles); Articles 14/15/16/21; Puttaswamy 2017 + 2018 (proportionality/demonstrability); Aadhaar exclusion studies and IFF/Vidhi facial-recognition audits, all framed as accountability/provenance failures. Do NOT import transport-equity quantitative frameworks (Gini/Rawlsian/DIR/pedestrian-parity) — the equity axis is dropped.
- **Separating verifiable provenance from contested origin** — the accountability literature's recurrent failure mode is conflating an opaque output with a determination; the design principle is a firewall between a mechanically-verifiable provenance evidence pack (reproducible facts only, no verdict/confidence/accusation) and a counsel-gated, non-evidential internal note where any origin classification names a signing key, never a person.
- **Why no provenance record exists for signal-control decisions** — signal-control software emits no per-decision provenance distinguishing a corroborated emergency preemption from a signed-but-uncorroborated one; and for LLM-driven controllers the CoT trace is unfaithful (§2.6), so accountability must come from the external signed log.

Land on: *UK statute and case law compel a documented, independently-verifiable provenance record for any automated signal controller; no such record exists for any class of controller, and no system produces the firewalled provenance evidence pack this dissertation builds for an insider-compromised emergency preemption.*

### 2.9 Synthesis — the self-referential coupling (~700 words)

State the novel object as a conditional lemma, not an unconditional guarantee:

> The increment is a self-referential coupling: the lever a stealthy insider uses to execute an emergency preemption is the signal phase, and the signal phase is also the variable that gates honest-witness coverage, so executing the attack opens the very coverage desert that conceals it. Under explicit hypotheses (honest signing keys, intact quorum anchor, honest cross-auditor, coverage above the phase-coupled threshold) a deviation is mechanically corroborable; the finding is the measured boundary of that conditional on the real Euston Road (A501) corridor. The accountability mechanism (Certificate-Transparency-style, quorum-anchored, cross-audited log) is credited to prior art; the deterministic refusal gate and the on-device Phi-4-mini legal-reasoning note are co-equal engineering contributions; the measured coupling boundary is the increment no prior work occupies.

Write one paragraph each for: (a) the coupling stated as a conditional lemma with its in-scope free-deviation classes and out-of-scope hypothesis-failure axes; (b) position against prior art (confront Traffic-R1 and the CoLLMLight line — differentiator is the accountability role plus the measured coupling, not "SLM beats a rule", not "coordination optimises traffic", not "a novel security mechanism"); (c) the deterministic refusal gate; (d) the accountability log credited to prior art; (e) the firewalled on-device legal-reasoning note. For each, explain which prior work occupies adjacent ground, what this dissertation adds, and what specifically remains untested.

Close with a forward link to Chapter 3 (Methodology), naming the chapter's contents in one sentence: *Chapter 3 specifies the deterministic refusal gate and MaxPressure shield, the real Euston A501 network construction and its synthetic-grid unit-test fixture, the structured-decision schema and provenance-evidence-pack format, the mechanical-provenance predicates, and the quorum-anchored, cross-audited accountability-log configuration.*

## Writing constraints

- **Academic register.** Past tense for cited findings, present tense for analytic claims. No first-person plural unless absolutely necessary; "this dissertation" is preferred to "we". No marketing language ("powerful", "groundbreaking"). No emojis.
- **Critical engagement.** Every section must engage with at least one weakness, contradiction, or vendor-bias issue in the cited literature. Do not summarise uncritically.
- **Hedged framings.** The seven flagged claims from prompt5 (Traffic-R1, Iroha 2, Southampton/Minima drone, Google Project Green Light, Alibaba City Brain, Yunex FUSION, Jetson Orin Nano benchmarks) MUST use the prompt5 recommended framings verbatim wherever cited. The Iroha 2 architecture must NOT appear in the chapter. The accountability layer is a Certificate-Transparency-style, quorum-anchored, cross-audited log (mechanism credited to prior art); a permissioned Besu QBFT ledger is only a demoted, optional anchoring witness and must never be foregrounded as the contribution.
- **Cite by short-tag from `registry.json`.** All citations use square-bracket short-tags exactly as they appear in the registry. Do not invent tags. If a needed tag does not exist, stop and ask the user.
- **No padding.** Eliminate sentences that do not advance the argument. Every paragraph should either (a) report what prior work established, (b) critique a limitation, or (c) link to a locked thesis decision.
- **No bleeding.** Methodology details (SUMO calibration parameters, k-anonymity floor, BCa bootstrap B = 10000) belong in Chapter 3. Architecture-spec details (Foundry Local engine selection, Docker container layout) belong in Chapter 4. Stay in lit-review register.
- **Honour the lock.** Every architectural choice is locked per `00-SCOPE-LOCKIN.md` §4. Do not editorialise about whether Llama would have been better, whether Fabric is technically correct, etc. Note the alternatives the literature considered, justify the locked choice in one sentence, and move on.

## Output format

A single Markdown file `04-writing/02-literature-review.md`. Use ATX headers (`##` for section, `###` for sub-section). Citations as `[short-tag]` inline. References list at the end is **not required** — the registry is the references list, and the methodology chapter will produce a formal bibliography in BibTeX.

Word count at the end of the file as an HTML comment: `<!-- word count: NNNN -->`.

## Stop conditions

Stop when:

1. The chapter is between 10,000 and 13,000 words inclusive.
2. Every section in the structure spec is present and within ±20% of its word budget.
3. Every cited short-tag exists in `registry.json`.
4. The seven prompt5 flagged claims, if cited, use the recommended hedged framings.
5. The self-referential coupling in §2.9 is stated as a conditional lemma, separated from the two co-equal engineering contributions and the credited accountability mechanism, with a paragraph per element.
6. No methodology, results, or implementation detail appears.
7. If `india-context.md` is absent, §2.8 sub-section on Indian regulatory anchoring is marked with the `<!-- TODO -->` placeholder; do not block.

If any stop condition cannot be met because of a missing tag, missing prior-prompt output, or genuine contradiction with `00-SCOPE-LOCKIN.md`, stop and report the specific issue rather than papering over it.
