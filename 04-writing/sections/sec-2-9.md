## 2.9 Synthesis: the Edge Negotiator novelty tuple

This section maps each component of the proposed architecture against adjacent prior work to identify the unoccupied region the dissertation occupies.

### 2.9.1 The novelty tuple

> The unoccupied region in the literature is the joint tuple **(sub-7B SLM ∈ {Qwen3-4B, Phi-4-mini}) × (real Lambeth/Southwark Elephant & Castle–Brixton SUMO grid) × (deterministic Max-Pressure shield) × (permissioned Hyperledger Besu QBFT plus Trillian Tessera comparator audit ledger) × (Quarterly Equity Audit Protocol with Gini, Rawlsian Difference Principle, Disparate Impact Ratio and pedestrian-vehicle parity) × (Chain-of-Thought-faithfulness probe under biased-hint injection) × (UK ATRS Tier 1/2 reporting alongside Indian regulatory comparative framing).** Each axis is occupied by adjacent prior work; their conjunction is not.

### 2.9.2 Axis 1 — sub-7B SLM ∈ {Qwen3-4B, Phi-4-mini}

Traffic-R1 fine-tuned Qwen-2.5-3B for traffic-signal-control reasoning and is the closest published analogue; it represents an emerging line of LLM-driven traffic-signal-control research rather than validated production deployment, its authors are affiliated with PCITECH (SSE: 600728), and the authors report a partial production trial covering, by their account, around 55,000 daily drivers, a figure that has not been independently verified [Traffic-R1]. CuraLight combined Gemma-3 with a DeepSeek ensemble curator [CuraLight]; HeraldLight paired a Llama-3.1-8B agent with a cloud critic [HeraldLight]; the Phi-4 reasoning architecture is documented in [Phi4-Reasoning]. This dissertation adds a 4B–4B pairing with an explicit comparator isolating per-model contributions. Validated tokens/sec, watts, and thermal numbers under sustained closed-loop operation remain untested for either model.

### 2.9.3 Axis 2 — real Lambeth/Southwark Elephant & Castle–Brixton SUMO grid

Published LLM and RL traffic-signal-control evaluations rely predominantly on synthetic CityFlow networks (Jinan, Hangzhou, New York). The MA2C-TSC decentralised actor-critic study used a 5×5 SUMO grid [MA2C-TSC]; CityLight scaled MAPPO to large synthetic topologies [CityLight]; the canonical taxonomy [Survey-TSC] records no published evaluation on a real OpenStreetMap-derived UK borough corridor. This dissertation adds a real Lambeth/Southwark corridor derived from OpenStreetMap and calibrated against TfL loop counts. Distributional equity outcomes disaggregated by income decile and pedestrian mode share on any real corridor remain unpublished in the field.

### 2.9.4 Axis 3 — deterministic Max-Pressure shield

Max-Pressure throughput-stability, including its delay-aware and pedestrian-aware extensions, is established in the open literature [Survey-TSC; MP-Delay; MP-Pedestrian]. The action-shielding pattern — a learned policy proposes; a deterministic layer disposes — appears in SafeLight and CFLight, both reviewed in §2.3 [SafeLight; CFLight]. This dissertation adds the specific integration of Max-Pressure as a microsecond-cost fallback for the path where structured-JSON output from an SLM controller fails formal verification. Shield-trigger frequency under realistic adversarial sensor inputs on a real corridor remains untested.

### 2.9.5 Axis 4 — permissioned Hyperledger Besu QBFT plus Trillian Tessera comparator audit ledger

The empirical Besu QBFT performance envelope is documented in [Veloso2026; Khoshaba2023; Ucbas2023; Pierro2024; Polito2022], and the AI-decision-provenance template in [BC-AI-Decision; BC-Enforce; BC-TSC]. No prior study pairs a QBFT ledger with a Trillian Tessera Merkle-log comparator. This dissertation adds a side-by-side evaluation quantifying whether the AI-decision-provenance workload requires Byzantine-fault-tolerant consensus or whether an append-only transparency log suffices for a single-operator municipal deployment. Head-to-head latency, cost, and governance numbers at municipal scale for this workload class remain unpublished.

### 2.9.6 Axis 5 — Quarterly Equity Audit Protocol (Gini / Rawlsian / DIR / pedestrian parity)

The individual statistical frameworks are documented in South Asian urban-mobility equity work [verma-mumbai-rawls-2026; ghosh-blr-equity-2022; gangopadhyay-mumbai-gini-2021; sambasivan-facct-2021]. UK ATRS Tier 1/2 and EU AI Act Annex III §2 (effective 2 August 2026) impose emerging accountability obligations [uk-atrs; eu-ai-act-2024]. This dissertation adds a controller-level audit protocol instantiating all four frameworks simultaneously on a real London corridor — the first such instantiation for any signal-controller class.

### 2.9.7 Axis 6 — Chain-of-Thought-faithfulness probe under biased-hint injection

The CoT unfaithfulness literature is well-established: biasing features alter model answers without appearing in the reasoning trace [Turpin2023; Lanham2023; Chen2025]; capability scaling does not close the gap [Young2026]; and Counterfactual Simulation Training offers a partial remedy [Hase2026]. This dissertation adds a domain-specific probe injecting biased hints into approximately one thousand TSC phase decisions and reporting channel-divergence rate per the Young et al. four-quadrant taxonomy. Faithfulness behaviour under hint injection in a TSC-specific decision distribution — hints take the form of biased queue-length readings rather than multiple-choice patterns — remains untested.


### 2.9.8 Axis 7 — UK ATRS Tier 1/2 reporting alongside Indian regulatory comparative framing

The Indian regulatory corpus — DPDPA 2023 [dpdpa-2023], NITI Aayog RAI principles [niti-rai-part1; niti-rai-part2], Constitutional Articles 14/15/16/21 [constitution-india], and foundational privacy jurisprudence [puttaswamy-2017; puttaswamy-aadhaar-2018] — and the algorithmic-accountability literature on Indian urban contexts [sambasivan-facct-2021; verma-mumbai-rawls-2026] occupy adjacent ground. This dissertation adds comparative framing positioning the same audit artefacts against UK Equality Act 2010 PSED, EU AI Act Annex III §2 (effective 2 August 2026), DPDPA 2023, NITI Aayog RAI principles, and Articles 14/15/16/21. Regulator-legible audit artefacts have not been produced for any LLM-driven traffic-control system in either jurisdiction.

### 2.9.9 Forward link to Chapter 3

Chapter 3 specifies the audit protocol, the SUMO-Lambeth network construction, the structured-JSON output schema, the formal-verification rules, and the Besu QBFT and Tessera ledger configurations that operationalise the seven axes synthesised above.

<!-- §2.9 word count: 840 -->
