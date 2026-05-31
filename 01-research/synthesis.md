# Edge Negotiator — Locked Architecture Synthesis

**Status:** Research phase complete. All seven deep-research prompts run, evaluated, and integrated. Architecture is fully locked. Ready for implementation.

**Last updated:** 2026-04-16

---

## The Pitch

The Edge Negotiator is a decentralised traffic signal architecture combining edge-deployed Small Language Models with cryptographic audit via permissioned blockchain. The dissertation evaluates it in SUMO simulation on commodity hardware. Two original empirical contributions:

1. **Cost-benefit profile of permissioned blockchain audit (Hyperledger Besu QBFT) vs append-only Merkle logging (Tessera)** for AI decision provenance at municipal scale
2. **Faithfulness profile of Chain-of-Thought reasoning logs from a 4B-parameter SLM (Qwen3-4B) operating in a decide-first-justify-after architecture**, evaluated as a monitorability signal — addressing an evidence gap in sub-7B safety-adjacent control loops

---

## Locked Architecture

| Layer | Decision | ADR | Source |
|-------|----------|-----|--------|
| Primary SLM | Qwen3-4B (Apache 2.0, dual thinking modes) | 001 | Prompt 1 |
| Comparison SLM | Phi-4-mini (MIT, 3.8B) | 001 | Prompt 1 |
| Benchmark anchor | Traffic-R1 Public 0.1 (cite, don't deploy) | 001 | Prompts 1, 5 |
| Primary ledger | Hyperledger Besu QBFT (Docker dev mode, web3.py) | 002 | Prompt 2 |
| Comparator ledger | Tessera Merkle log (POSIX, single instance) | 002 | Prompt 2 |
| Hardware | Developer laptop (RTX 3060/4060), SUMO simulation | 003 | Supervisor-approved |
| Safety verifier | Z3 SMT for hard safety constraints | 004 | Prompt 3 |
| Safety fallback | MaxPressure (Varaiya 2013), always logged alongside | 004 | Prompts 1, 3 |
| Hot-path output | Single-token phase ID + CFG-constrained JSON via XGrammar | 005 | Prompts 1, 3 |
| Audit-path output | Structured CoT, labelled `trace_type: "post_hoc_justification"` | 006 | Prompt 3 |
| Communication | MQTT (Mosquitto Docker container) | 007 | Prompt 7 |
| Threat model | Hybrid STRIDE × NIST AI RMF | §B | Prompt 7 |
| Network | Lambeth/Southwark 5×5 km, OSM-derived | — | Prompts 4, 6 |
| Audit area | Same network, IMD 2019 + ONS 2021 | — | Prompt 4 |

---

## Five Codes of Conduct (STSD coursework, now operationalised)

1. **Algorithmic Transparency & Accountability** — implemented via blockchain audit + structured CoT
2. **Fail-Safe Manual Override** — implemented via Z3 verifier + MaxPressure fallback + hardware kill switch
3. **Data Sovereignty & Edge-First Processing** — architectural pattern (anonymised structured descriptions, not raw video)
4. **Equitable Service Provision** — implemented via quarterly Gini-of-delays audit against IMD deciles
5. **Adversarial Robustness** — implemented via architectural separation (object detection separate from semantic reasoning)

---

## Two Empirical Contributions

### Contribution 1: Besu QBFT vs Tessera Cost-Benefit
- Workload: ~3.2M tx/day at TfL scale (~37 TPS sustained, 100 TPS bursts), 2KB signed decision proofs, 60s finality target
- Both backends implemented; replay identical decision streams through both
- **Metrics**: write latency distribution, finality time, proof size, storage growth, query latency for quarterly equity audit, operational complexity
- **Threat model dimension**: what each defends against (operator compromise, validator collusion, split-view attacks, censorship, key compromise)
- **Result type**: quantification of architectural commitment, not litigation of whether to commit

### Contribution 2: Qwen3-4B CoT Faithfulness Probe
- **Evidence gap**: no published study has tested CoT faithfulness for sub-7B SLMs in safety-adjacent control loops
- **Primary method**: Turpin et al. biasing-features methodology
- **Secondary method**: Lanham truncation probe
- **Comparisons**: Qwen3-4B thinking-mode vs non-thinking-mode; Qwen vs Phi-4-mini
- **Operationalised threshold**: CoT correlates with at least 3 of 5 observable state variables at r > 0.5; below threshold, downgrade to decorative
- **Position taken**: CoT is conditionally valuable as monitorability, structurally post-hoc by architecture — five design conditions specified

---

## Experimental Design Summary

- **Network**: 5×5 km Lambeth/Southwark corridor (Elephant & Castle to Brixton)
- **Scenarios**: AM peak, off-peak, PM peak, incident perturbation
- **Conditions**: 16 (2⁴ factorial: CoT × Z3 × MaxPressure × thinking mode) + 2 single-factor swaps (Qwen vs Phi, Besu vs Tessera) = 18
- **Seeds**: 30 pre-registered per condition × 4 scenarios = 2,160 simulation runs
- **Statistical tests**: Welch's t / Mann-Whitney U, Cohen's d, BCa bootstrap (B=10,000), Holm-Bonferroni at q=0.10
- **Pre-specified primary endpoints**: ATT (traffic), Gini (equity), fallback rate (safety)

---

## Six Baselines

| Method | Type | Notes |
|--------|------|-------|
| Fixed-time (Webster's) | Classical | Optimised cycle from calibrated flows |
| Actuated SOTL | Classical | Gap-based phase extension |
| MaxPressure | Classical | Also serves as always-on fallback |
| CoLight | RL | Canonical MARL baseline, retrained on study network |
| Traffic-R1 Public 0.1 | LLM | Benchmark anchor; CityFlow-trained, SUMO-evaluated with caveat |
| Edge Negotiator (full) | Proposed | Qwen3-4B + Z3 + MaxPressure fallback + Besu ledger |

---

## Honesty Clauses (Pre-Drafted Defensive Language)

The Prompt 6 output includes ready-to-paste defensive language for five non-claims:

1. **No real-world deployment claim**: "This work evaluates the Edge Negotiator architecture in a simulated environment using SUMO. No traffic signals were controlled in the physical world."
2. **No edge-hardware claim**: "The 'Edge' in Edge Negotiator denotes architectural topology — decision-making co-located with intersection controllers rather than centralised in a cloud — not a specific hardware platform."
3. **No causal safety claim**: "Surrogate safety measures (TTC, PET) computed in SUMO are accepted proxies for conflict severity but are not crash predictions."
4. **No equity deployment claim**: "Equity metrics are computed on simulated delay distributions joined to IMD 2019 deciles at LSOA granularity. SUMO's pedestrian model lacks demographic fidelity."
5. **No CoT-as-explanation claim**: "Post-hoc CoT generated in the audit path is labelled `trace_type: post_hoc_justification` and treated as a monitorability signal, not as a faithful explanation."

---

## Threat Model (Hybrid STRIDE × NIST AI RMF)

First-page entries:

| ID | Threat | STRIDE | NIST AI RMF | Mitigation |
|----|--------|--------|-------------|------------|
| TM-001 | Adversarial inputs to SLM perception | Tampering | Confabulation, InfoSec | Z3 verification, MaxPressure fallback |
| TM-002 | SLM hallucination / post-hoc rationalisation | Repudiation | Confabulation | CoT as monitoring signal, not explanation |
| TM-003 | Compromised audit log | Tampering, Repudiation | Value Chain Integration | Besu QBFT multi-validator consensus |
| TM-004 | Communication compromise | Spoofing, InfoDisclosure | InfoSec | TLS on MQTT, signed messages |
| TM-005 | Insider key compromise | Spoofing, ElevationOfPrivilege | InfoSec | HSM key storage, BFT validator separation |

---

## What's Next (Implementation Phase)

### Build order (suggested)
1. SUMO Lambeth/Southwark network (Steps 1–4 of equity protocol)
2. SLM inference wrapper (Qwen3-4B + Phi-4-mini) with structured output via XGrammar
3. Besu in Docker dev mode + AuditLog.sol contract
4. Tessera as second backend (POSIX, single-instance)
5. Z3 verifier with NEMA constraint set
6. MaxPressure as fallback + always-on baseline
7. TraCI ↔ agent ↔ ledger loop
8. Ablation harness with pre-registered seeds

### Realistic timeline (post-research)
- 4 weeks: implementation + initial runs
- 2 weeks: full experimental sweep (2,160 runs)
- 4 weeks: writing
- 2 weeks: revision + viva prep

---

## File Map

```
e:\desktop\assignments\dissertation\
├── 01-research\
│   ├── prompt-outputs\          ← all 7 deep-research PDFs + SLM field guide
│   ├── conversations\           ← 11 renamed convo logs (project history)
│   ├── synthesis.md             ← this document
│   └── project-proposal.pdf
├── 02-experiments\              ← Lee Stott repo investigations
│   ├── router-demo-app\
│   ├── modelrouter-routelens\
│   ├── FLPerformance\
│   ├── local-cag\
│   ├── local-rag\
│   └── findings\                ← per-repo analysis docs
├── 03-implementation\           ← code, runs, results (future)
├── 04-writing\                  ← dissertation chapters (future)
├── 05-supervision\              ← supervisor sign-offs, compliance
└── STSD\                        ← STSD coursework (delivered)
```

---

## Open Questions for Lee (industry supervisor)

1. **Edge experimentation scope** — what specifically does "explore things that can be done on the edge" entail for this dissertation? Beyond MaxPressure fallback and single-token hot path, what other edge-friendly patterns are worth investigating?
2. **CPU-only inference target** — Beaver mentioned for full-CPU inference. Is this for benchmarking comparison, fallback option, or candidate model swap?
3. **Foundry Local fit** — does the Foundry Local Model Router make sense as an architectural pattern for the Edge Negotiator's SLM stack (route between Qwen3 thinking/non-thinking modes, fallback to smaller model under load)?
4. **RAG/CAG integration** — is local-rag / local-cag a candidate for the audit-path or future work pointer?

These are open lines for the next supervision check-in.
