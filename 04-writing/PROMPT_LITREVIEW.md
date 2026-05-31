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
4. **Justify every locked architectural choice.** The reader should finish §§2.5–2.7 understanding *why* the thesis chose Qwen3-4B + Phi-4-mini, MaxPressure shield, Besu QBFT, Tessera comparator, SUMO, the Elephant & Castle–Brixton corridor — not because the supervisor said so but because the literature compels these choices.
5. **Scaffold the equity audit.** Fairness in transport, algorithmic-fairness audit precedents, UK and Indian regulatory framings, why the existing literature does not contain a signal-timing equity audit.
6. **Land the novelty claim.** Synthesise the Edge Negotiator novelty tuple from `traffic-llms.md` §C and explicitly state which axes the thesis occupies that no prior work does.

Anything outside these six jobs belongs in another chapter. Specifically:

- **Do not duplicate methodology.** The 18-step audit protocol, the SUMO calibration recipe, the Z3 verification rules — these are Chapter 3.
- **Do not present results.** No SUMO numbers, no Gini values, no latency tables.
- **Do not editorialise.** The chapter is a critical synthesis, not a polemic. Engage with weaknesses (vendor bias, missing benchmarks, paywalled foundational papers) without sneering.
- **Do not list papers.** A list of summaries is not a literature review. Synthesise themes and cite *in support of* claims.

## Chapter structure and word budgets

Total target: **10,000–12,000 words** (typical UCL MSc literature-review chapter). Treat the budgets below as soft targets — go ±20% per section if the material warrants, but do not exceed 13,000 words total.

### 2.1 Introduction and roadmap (~400 words)

State what the chapter establishes, the order of sections, and the framing claim that the chapter will close on (the Edge Negotiator novelty tuple). One paragraph per section preview.

### 2.2 The traffic signal control problem and classical adaptive baselines (~1,200 words)

- Brief history: pre-timed → vehicle-actuated → adaptive (SCOOT, SCATS) — anchor in `Survey-TSC` taxonomy.
- The Max-Pressure family: cite `MP-Delay` and `MP-Pedestrian` as open derivations (note Varaiya 2013 is paywalled). Explain provable throughput stability and why MP is the deterministic shield in the locked architecture.
- `PressLight` as the theoretical bridge between Max-Pressure and reinforcement learning.
- One paragraph on the SCOOT/SCATS installed base in London and why a decentralised SLM controller is intellectually distinct from a centralised legacy adaptive system.
- Land on: *the locked thesis adopts Max-Pressure as the deterministic shield, not as the controller — this is the first architectural decision the literature demands.*

### 2.3 Reinforcement learning for traffic signal control (~1,200 words)

Synthesise four threads, each with 2–3 sources:

- **Single-intersection DQN** — `MPLight`, `FRAP` (phase-pair invariance reduces exploration 64×n⁸ → 16×n⁴).
- **Network-level cooperation** — `CoLight` (graph attention), `Adv-XLight` (pre-LLM SOTA on Jinan/Hangzhou/NY), `MA2C-TSC` (decentralised actor-critic on 5×5 grid which is structurally identical to the dissertation's Lambeth grid).
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

Land on: *the LLM-TSC frontier has matured to sub-7B controllers in the last 18 months, but no work to date has equity-audited any of them; this absence is the dissertation's primary opening.*

### 2.5 Small language models on edge hardware (~900 words)

- Microsoft Phi-4 family from `Phi4-Reasoning` — mid-fusion architecture, 200B-token curation, 128k context.
- Qwen3 lineage (cite via `Traffic-R1` and `CoMAL` as the closest academic anchors; no standalone Qwen3 paper exists in the registry, so frame Qwen3-4B as inheriting the architectural lineage these papers document).
- Edge benchmarks: `Edge-Orin-Bench` (Pythia 70M-1.4B sizing grid), `Edge-AGX-Power` (INT4 caveat — Ampere has no native INT4), `Edge-SLM-Energy` (Llama-3.2 0.57s on Orin Nano GPU; Phi-3 Mini best accuracy / worst energy), `Edge-Hailo` (Hailo-10H 6.91 tok/s @ 1.87W — only published Hailo-10H LLM benchmark), `Edge-Quant` (Q4_K_M sweet spot), `Edge-Reason` (decode dominates 99.5%), `FPGA-Qwen`, `Edge-First`, `ELIB`.
- Apply prompt5 Claim 7 hedged framing: NVIDIA's 38–43 tok/s figure is MLC-engine-specific; independent reproductions are 7–15% lower.
- Microsoft Phi-Silica claims from `microsoft-foundry.md` — hedge appropriately.

Land on: *the locked thesis runs Qwen3-4B and Phi-4-mini on a developer laptop, not on Jetson — this is a deliberate scope choice given the 90-day Study Away constraint and the fact that the empirical contribution is the audit protocol, not the edge benchmark. The edge-benchmark literature is reviewed because it constrains future deployment, not because the thesis runs on edge hardware.*

### 2.6 Chain-of-Thought faithfulness in safety-critical control (~1,400 words)

This section directly answers Stott S1. Synthesise four threads:

- **Foundational unfaithfulness** — `Turpin2023` (behavioural perturbation, BIG-Bench Hard accuracy degradation); `Lanham2023` (early answering, adding mistakes, paraphrasing, filler tokens, AOPC metric).
- **Frontier reasoning models** — `Chen2025` / `CoT-Faith` (under-20% faithfulness rate on hint injection); `Gantt2026` (models flatly deny hint use even when permitted); `Arcuschin2025` (implicit post-hoc rationalisation in unperturbed prompts, GPT-4o-mini 13% mutually-exclusive-yes rate).
- **Mechanistic and channel divergence** — `Tutek2025` (unlearning-based diagnosis); `Ye2026` (NLDD metric, Reasoning Horizon k* at 70-85% of chain length); `Young2026` (four-quadrant taxonomy: Thinking-Only 55.4%, Transparent 32.3%, Unacknowledged 11.8%, Surface-Only 0.5%); `Han2026` (RFEval; standard RLVR degrades faithfulness 10–14 points); `Basu2026` (SLRC step-level metrics + Lyapunov stability bounds).
- **SLM-specific and embodied/control** — `Masri2026` (Qwen3-0.6B 88.12%, Phi-4-Mini-Reasoning 228s/inference + <10% accuracy under RAG); `Shakib2026` (low-resource surface-level faithfulness patterns); `Zawalski2024` (VLA decoder ignores CoT logic — relies only on entity-reference integrity, ±4% physical performance under blind noise / spatial reversal); `Duan2025` (Fast ECoT 7.5× latency reduction); `Tan2025` and `OneVL2026` (Latent CoT abandons text entirely for autonomous driving — 88.84 PDM-score on NAVSIM); `Liao2025` (CoT-Drive — explicit CoT diverges from kinematic ground truth); `Ye2026_Flood` (IP-CoT inverse prompting, 95.32% accuracy via grammar-constrained decoding); `Li2025`, `Xiong2025` (RAGLens SAE-based hallucination detection); `Wang2026` (autoregressive unfaithfulness mechanics); `Puerto2025` (LRM contextual privacy risks).
- **Engineering remedies** — `Hase2026` (Counterfactual Simulation Training — 35-point monitor-accuracy improvement); `Guan2024` (deliberative alignment); the prompt3 §4 design checklist as the synthesis the dissertation adopts.

Land on: *the literature converges on the conclusion that explicit CoT cannot be trusted as a faithful causal record — it is post-hoc rationalisation. The locked thesis adopts Position (d) "conditionally valuable post-hoc justification with a six-property design checklist" from prompt3, and runs a faithfulness probe in the discussion chapter.*

### 2.7 Permissioned blockchain for AI audit ledgers (~1,200 words)

This section directly answers Stott S4. Synthesise three threads:

- **Why audit ledgers** — `BC-AI-Decision` (permissioned-chain AI-decision provenance design); `BC-Enforce` (Hyperledger Fabric + IPFS + ECDSA for intersection-camera audit); `BC-TSC` (only paper directly targeting blockchain audit for traffic signals — mitigates I-SIG single-vehicle congestion attack). Acknowledge the prompt2 §4 critical position: blockchain solves a trust problem this workload does not have, but is academically defensible as an architectural choice.
- **Empirical benchmarks of permissioned EVM** — `Veloso2026` (QBFT 200 TPS knee, sub-second latency, $239.60/month on AWS), `Khoshaba2023` (validator participation 0.85–0.95 sweet spot), `Ucbas2023` (Fabric vs Besu IoT — Besu degrades from 4.37s to 96.58s under 5,000 concurrent tx), `Pierro2024` (Besu vs Quorum payload bloat decay 100s TPS → sub-50 TPS at 50 KB), `Fan2025` (QBFT vs IBFT 2.0 six-node), `Catarino2024` (QBFT vs Clique determinism trade-off), `Kulothungan2024` (QBFT IoT gateway aggregation), `Polito2022` (Fabric channel privacy vs Tessera/Orion off-chain modules).
- **Privacy enclaves and PQC overhead** — `Alattar2025` (Quorum + Tessera 28-32s cross-chain latency); `AITH` (ML-DSA-87 4,627-byte CDC + Merkle chain to bypass per-event PQC signing); `Alown2025` and `Zheng2026` (Verkle trees compress proofs to O(log_k N), 5ms per-batch verification with ARM NEON); `BC-V2X-Sec`, `BC-CCAM`, `BC-Offload`, `SALT-V` (V2X ML-blockchain trade-offs and lightweight 5G V2X authentication — 0.035 ms compute, 1 ms e2e); `BeACONS` (RSU-anchored DID).

Land on: *the prompt2 §6 recommendation is followed verbatim — Hyperledger Besu QBFT in dev mode as the primary ledger (academically defensible, well-benchmarked, EVM ecosystem familiarity for the examiner) with Trillian Tessera as a parallel comparator answering the prompt2 §4 question "does this workload need a blockchain at all?" The thesis will produce a head-to-head latency / cost / governance table.*

### 2.8 Algorithmic fairness audits in public-sector AI (~1,500 words)

This section directly answers Stott S2. Three sub-currents:

- **The five existing algorithmic-fairness case studies** the dissertation cites (transcribe from prompt4 §2.4 with academic-register expansion): UK Ofqual A-level grading 2020 collapse; Dutch SyRI welfare-fraud algorithm Court of The Hague 2020 ruling; Amazon recruiting tool 2018 abandonment; Chicago Strategic Subject List OIG 2020 audit; NYC ADS Task Force 2018-2019 transparency failure. Cite by registry tag where present (these are policy / journalism / inquiry sources, may live in the registry under `AI-Gov-Reg`, `BiasX-Mod`, `Agent-Ethic`, `CitizenQuery` from prompt2 — verify before citing).
- **UK and EU regulatory anchoring** — Equality Act 2010 PSED s.149; EU AI Act Annex III §2 (road traffic management high-risk) and Article 12 (event logging); UK ATRS Tier 1/2 templates; Bridges v South Wales Police (2020); Schufa CJEU C-634/21. Some of these may not have registry tags — cite by full reference and add to the registry.
- **Indian regulatory and case-study anchoring** — pull entirely from `india-context.md` (Prompt 8) once present. Cover: DPDPA 2023 + DPDP Rules 2025 phased calendar (especially Section 16 cross-border transfers enforceable 13 May 2027); NITI Aayog Responsible AI Part 1 + Part 2; Articles 14 / 15 / 16 / 21 of the Constitution; Puttaswamy 2017 + 2018; Aadhaar PDS exclusion studies; IFF Project Panoptic facial-recognition cases; at least one Indian peer-reviewed transport-equity paper from Theme 4. **If `india-context.md` is not present, write this sub-section as `<!-- TODO: integrate Prompt 8 sources -->` placeholder paragraphs and proceed.**
- **Statistical fairness frameworks** — Gini coefficient, Rawlsian max-min, disparate impact ratio (80% rule), pedestrian-vehicle delay parity. Reference rigour comes from prompt4 §2.3 — do not duplicate the protocol detail here, only the conceptual framing.
- **Why no signal-timing equity audit exists** — synthesise prompt4 §2.4: NCHRP Report 969 (vehicle-prioritising signal-timing software does not even compute pedestrian delay); the absence of any FHWA, US DOT, or TfL signal-timing equity audit; Smart Growth America "Dangerous by Design 2024" 4× pedestrian-fatality differential by income; TfL April 2023 KSI deprivation-doubling finding.

Land on: *no existing algorithmic-fairness audit covers traffic signal control, no existing signal-timing equity audit applies modern statistical fairness frameworks, and the EU AI Act / UK ATRS reporting standards exist but no published audit instantiates them on a real corridor for an LLM-driven controller. The dissertation closes this gap.*

### 2.9 Synthesis — the Edge Negotiator novelty tuple (~700 words)

State the novelty tuple verbatim from `traffic-llms.md` §C, expanded to capture the equity-audit dimension:

> The unoccupied intersection in the literature is the joint tuple **(sub-7B SLM ∈ {Qwen3-4B, Phi-4-mini}) × (real Lambeth/Southwark Elephant & Castle–Brixton SUMO grid) × (deterministic MaxPressure shield) × (permissioned Besu QBFT + Tessera comparator audit ledger) × (Quarterly Equity Audit Protocol with Gini / Rawlsian / DIR / pedestrian parity) × (CoT-faithfulness probe under biased-hint injection) × (UK ATRS Tier 1/2 reporting alongside Indian regulatory framing).** Each axis exists in prior work; their conjunction does not.

For each of the seven tuple axes, write one paragraph explaining (a) which prior work occupies adjacent ground, (b) what the locked thesis adds, and (c) what specifically remains untested.

Close with a forward link to Chapter 3 (Methodology), naming the chapter's contents in one sentence: *Chapter 3 specifies the 18-step audit protocol, the SUMO-Lambeth network construction, the structured-JSON+bounded-CoT decision schema, the Z3 verification rules, and the Besu QBFT + Tessera ledger configurations.*

## Writing constraints

- **Academic register.** Past tense for cited findings, present tense for analytic claims. No first-person plural unless absolutely necessary; "this dissertation" is preferred to "we". No marketing language ("powerful", "groundbreaking"). No emojis.
- **Critical engagement.** Every section must engage with at least one weakness, contradiction, or vendor-bias issue in the cited literature. Do not summarise uncritically.
- **Hedged framings.** The seven flagged claims from prompt5 (Traffic-R1, Iroha 2, Southampton/Minima drone, Google Project Green Light, Alibaba City Brain, Yunex FUSION, Jetson Orin Nano benchmarks) MUST use the prompt5 recommended framings verbatim wherever cited. The Iroha 2 architecture must NOT appear in the chapter — the locked ledger is Hyperledger Besu QBFT.
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
5. The novelty tuple in §2.9 is stated verbatim and each axis has a paragraph.
6. No methodology, results, or implementation detail appears.
7. If `india-context.md` is absent, §2.8 sub-section on Indian regulatory anchoring is marked with the `<!-- TODO -->` placeholder; do not block.

If any stop condition cannot be met because of a missing tag, missing prior-prompt output, or genuine contradiction with `00-SCOPE-LOCKIN.md`, stop and report the specific issue rather than papering over it.
