# The Edge Negotiator — Architecture Synthesis

**Status:** Conformed to the current thesis (2026-07-21 re-pivot). Mirrors `specs/001-edge-negotiator/MASTER-SPEC.md` §0–§3, the single source of truth.

> **This document supersedes all prior framings** — the equity-audit / Gini / CoT-faithfulness-probe / Besu-vs-Tessera coordination-trust synthesis, and the intermediate Lambeth cross-junction-coordination synthesis. Both earlier states are stale and must not be acted on; recoverable in git history if needed. Everything below reflects the current, frozen project.

**Working title (reframed):** *The Edge Negotiator: an on-device, trust-preserving coordination layer for signalised junctions, with a measured characterisation of the stealthy insider deviations it can and cannot hold accountable.*

**Programme context:** UCL MSc SEIOT. Supervisors: Akin Delibasi (SUMO / MaxPressure / statistics) and Lee Stott (Foundry Local / Phi / identity). Hardware: RTX 4050 8GB laptop. Constraint: build through August 2026, SUMO-on-laptop, executed from India.

---

## The Pitch

An on-device, trust-preserving coordination layer for signalised junctions, evaluated on a real corridor — **Euston Road (A501), a 3–4 signal stretch, central London** (the synthetic 2×2 grid is a unit-test fixture only, never the evaluation substrate). One frozen small-language-model agent — **Phi-4-mini (3.8B) via Microsoft Foundry Local** — sits per junction. A deterministic **MaxPressure shield** (Varaiya 2013) validates or overrides every SLM decision and runs alone at quiet junctions, with anti-starvation (`max_skip=3`); an admissible emergency preemption outranks the anti-starvation shield.

The project answers one question: *in a compromised-insider emergency, what can be held accountable mechanically, and what remains a human/counsel judgment that even an on-device reasoner cannot faithfully automate?* Three contributions:

- **(a) A deterministic real-time gate** that refuses signed-but-uncorroborated emergency preemption from a compromised insider, and clears physically corroborated real emergencies.
- **(b) A Certificate-Transparency-style, quorum-anchored, cross-audited, signature-verified accountability log.** The mechanism is credited to prior art — RFC 6962, CONIKS (Melara 2015), A2M (Chun 2007), TrInc (Levin 2009), PeerReview (Haeberlen 2007), Küsters CCS 2010 — cited, **not claimed novel**.
- **(c) The novel object: a self-referential coupling.** The preemption attack controls the signal phase, which is *also* the variable that gates honest-witness coverage — so executing the attack opens the very coverage desert that conceals it. Stated as a **conditional lemma** under explicit hypotheses (§8 of the spec), with one severe, pre-registered measurement of its boundary on the real Euston corridor. The honest boundary — not an unconditional guarantee — is the finding.

**The one defensible claim (the thesis is staked on this):**
> *A deterministic gate holds a compromised-insider emergency-preemption attack accountable exactly up to a measured, honestly-conceded boundary — because the attack lever (signal phase) is the same variable that gates the honest-witness coverage needed to catch it — and no further.*

Coordination between junctions is retained as an engineering property of the platform (MaxPressure + coordination term) but is reported as a **structural zero** — an inert term, not a headline benefit, and not an experiment. This project does not claim to optimise traffic.

---

## Locked Architecture

| Component | Decision | Basis |
|---|---|---|
| Primary SLM | **Phi-4-mini (3.8B), frozen, via Foundry Local (INT4, inference-only)** — the only model | 8GB VRAM budget; no training; terse latency budget |
| SLM role | **Self-contained co-equal contribution**, not the instrument of the boundary map. Job A = citation-faithful legal-reasoning note (primary metric); Job B = disambiguation classifier (characterised); Job C = frozen-vs-hardened robustness/adaptivity tradeoff | §3 of the spec |
| Fault-output channel | **SPLIT, never merged.** (1) A mechanically-verifiable provenance evidence pack — reproducible facts only, no machine verdict/confidence/accusation, header "Provenance record; not a determination of legal fault." (2) A firewalled, non-evidential, counsel-gated internal AI triage note | §0/§5 of the spec |
| MaxPressure shield | Deterministic (Varaiya 2013) — validates/overrides every SLM decision; runs alone at quiet junctions; anti-starvation `max_skip=3`; an admissible emergency preemption outranks the anti-starvation shield | Safety floor |
| Real-time defence | Deterministic Ed25519 auth + conservation/CUSUM + a corroboration gate (≥2 keys); keyless sustained preemption hard-refused + a junction-aggregate cumulative keyless-transient budget | §6 of the spec |
| Accountability mechanism | **Certificate-Transparency-style, quorum-anchored, cross-audited accountability log** — a signed hash-chained AuditLog + a quorum external anchor (≥2 witnesses, e.g. a Rekor transparency log + a named single-node ledger RPC) + a named cross-auditor. Not a blockchain; not foregrounded as a contribution — credited to prior art | Mechanism conceded; the coupling + measurement is the contribution |
| Registry | **Permissioned key registry** (not a decentralised ledger) with an external identity root + counter-signed rotation | §6.5 of the spec |
| Fault ontology (internal note only) | `attacker-key / system-classifier / system-detector / sensor-fed-spoof / colluding-keys / legitimate / unknown`. Where the origin is a signing party it names a **key, never a person** | §2 of the spec |
| Origin classification | A deterministic, mechanical partition over two features (signing-key count, recomputed corroboration), deciding three classes: `keyless-lone-sighting`→sensor-fed-spoof, `uncorroborated-signed`→attacker-key, `corroborated`→legitimate. The veracity/collusion distinction is honestly `→unknown`. A verification check, not the primary metric | §3 of the spec |
| Substrate | **Real Euston Road (A501), a 3–4 signal stretch, central London**, pre-built and committed. Synthetic 2×2 grid = unit-test fixture only | §0/§9 of the spec |
| Legal grounding | UK law only — RTA 1988 s.36/s.38, GDPR/DPA 2018, *Goodes*, *Gorringe*, *Stovin*, *Poole BC v GN* et al (`01-research/uk-traffic-law.md`) | §7 of the spec |
| Coordination effect | **A structural zero** — reported as such, not an experiment, not a headline benefit | §2/§8 of the spec |

---

## Contributions

1. **(a) A deterministic real-time gate** refusing signed-but-uncorroborated emergency preemption from a compromised insider, clearing physically corroborated real emergencies — Ed25519 auth + registry + conservation/CUSUM + corroboration (≥2 keys); keyless sustained preemption hard-refused with a junction-aggregate keyless-transient budget.
2. **(b) A Certificate-Transparency-style, quorum-anchored, cross-audited accountability log** — mechanism credited to prior art (RFC 6962, CONIKS, A2M, TrInc, PeerReview, Küsters), cited, not claimed novel. Reports a signed-log-vs-plain-log cost/benefit characterisation.
3. **(c) The self-referential coupling (the novel object)** — the preemption attack controls the signal phase, which also gates honest-witness coverage, so executing the attack opens the coverage desert that conceals it. Stated as a conditional lemma with one severe, pre-registered measurement of the boundary on the real Euston corridor: how the real signal-phase-coupled sighting-coverage geometry shifts the deviation-escape surface away from the well-mixed prediction, and which deviation classes escape in scope.
4. **A self-contained SLM contribution** — Phi-4-mini's citation-faithful legal-reasoning note (Job A, primary metric: citation-correctness + false-citation-rate on novel fact-combinations vs an un-rigged rule-to-text template baseline), a disambiguation classifier (Job B, characterised), and a frozen-vs-hardened robustness/adaptivity tradeoff (Job C, reported).

*Note:* coordination between junctions is retained as a platform property but is a **structural zero**, not a contribution. The **equity-audit framing** (Gini/Rawlsian/Disparate Impact/ATRS-as-an-equity-metric/CoT-faithfulness-as-contribution) is **dropped** — it is not a current contribution. What is **retained (reframed)** is the UK legal-accountability treatment and the India comparative-accountability lens (see lit-review §2.8.2/§2.8.3): ATRS survives only as a transparency-and-logging standard, and India only as a comparative accountability lens — not as equity metrics. Incentive-compatibility is not claimed.

---

## Position vs Prior Art

The accountability layer **is** Certificate Transparency / accountability infrastructure (RFC 6962, CONIKS, A2M, TrInc, PeerReview, Haber-Stornetta 1991, Küsters CCS 2010) — the mechanism is conceded, not claimed novel. The stealthy attack class is False Data Injection (Liu-Ning-Reiter 2011, Teixeira-Sandberg 2015, Mo-Sinopoli 2010); unobservability's topology-dependence is owned by Kosut et al (IEEE TSG 2011) and Hendrickx et al (IEEE TAC 2014). The domain-closest signal-attack work (Chen et al I-SIG NDSS 2018; Ghena et al WOOT 2014) does **not** couple the attack lever to the observability gate. The increment — not claimed as "first" — is the **self-referential coupling** (attack lever = coverage gate) instantiated and measured on a real signalised corridor. This confronts Traffic-R1 on the accountability role and the measured coupling, not on "the SLM beats a rule" or "coordination optimises traffic."

---

## Build Plan

Phased per `specs/001-edge-negotiator/MASTER-SPEC.md` §11 (build order) and §9 (Euston substrate + prerequisite artifacts, pre-built and committed rather than authored overnight). At a high level:

1. Doc/framing remediation across the corpus (this document included) to the current thesis, gated by a forbidden-term sweep (§5 of the spec).
2. Wire the real accountability-log producer: message/sighting/decision records, signature capture at both inbox seams, the EV-vs-coordination causal-attribution rule.
3. Rewrite origin classification (assessment) to the 3-class scored subset over mechanical predicates; verify chain + signature + quorum-completeness + cross-audit before any attribution.
4. Land the deterministic real-time gate: Ed25519 auth, conservation/CUSUM, corroboration (≥2 keys), the keyless-transient budget.
5. Stand up the quorum anchor (≥2 witnesses) + named cross-auditor; the Euston substrate (pre-built `euston.net.xml`); the Job-A SLM note.
6. Run Experiment D (the coupling measurement, the headline) and Experiment 1 (Job B classifier) and Job C (frozen-vs-hardened tradeoff), all pre-registered under a single hash seal.
7. Write-up.

---

## Baselines & Metrics

**Baselines:**
- **Fixed-time** (Webster) and **MaxPressure** (also the shield).
- **Gate on vs off** for the real-time defence contribution.
- **An un-rigged rule-to-text template** for the SLM Job A comparison.

**Metrics:**
- **Gate:** admissibility of corroborated real emergencies vs refusal of uncorroborated signed preemption; the measured keyless-transient budget cost.
- **Coupling (Experiment D):** the coverage-vs-escape surface as a statistical object — a pre-registered contrast estimator over named cells, a closed-form well-mixed comparator, a directional prediction with a magnitude pinned to an external operational-harm threshold, a named CI method, N fixed under the seal.
- **SLM (Job A):** citation-correctness + false-citation-rate on novel legal fact-combinations, vs the un-rigged template baseline.
- **Coordination:** reported as a structural zero — not scored as a metric of merit.

---

## What We Can / Cannot Claim

**Can claim:**
- The gate refuses a signed-but-uncorroborated compromised-insider preemption and clears a physically corroborated real emergency.
- A signed, quorum-anchored, cross-audited accountability log — provenance and non-repudiation for every decision and identity/registry change.
- The self-referential coupling, as a conditional lemma under explicit stated hypotheses, with one measured, pre-registered boundary on the real Euston corridor.
- That a frozen on-device SLM can produce a citation-faithful legal-reasoning note, measured honestly against an un-rigged baseline (or that it cannot, if the pre-registered kill-criterion fires — the claim may be demoted, the SLM's presence never is).

**Cannot claim:**
- That the accountability log "creates trust" or "prevents lying" — it provides provenance and identity, not truth; it faithfully records garbage-in.
- Any determination of legal fault — the evidence pack carries no verdict, confidence, or accusation; that is a human/counsel judgment.
- Defence against colluding keys (≥2), operator creation-time omission, identity-root/quorum/cross-auditor compromise, or coverage below the phase-coupled threshold — these are out-of-scope, hypothesis-failure axes, stated honestly, not defended.
- Traffic optimisation — coordination is a structural zero, not a headline result.
- That the coupling is an unconditional guarantee — it holds only under its stated hypotheses (honest keys, cross-audited non-equivocating quorum, adequate coverage, no operator omission).

---

## Canonical Free-Deviation Boundary (state once, cross-reference elsewhere)

**In-scope, free classes** (the gate does not stop these, stated honestly): sub-margin piggyback-inflation on a corroborated event; keyless-transient sensor-spoof; compounded keyless transients; keyless magnitude-inflation of a genuine corroborated event.

**Out-of-scope / hypothesis-failure axes:** colluding keys (≥2); operator creation-time omission; identity-root/quorum/cross-auditor compromise; coverage below the phase-coupled threshold.

All of the above are measured and stated as the boundary of the finding, not defended as a guarantee.

---

## Key Engineering Constraints

| Constraint | Mitigation |
|---|---|
| Foundry Local serialises inference (no batching) | Terse Job-A/Job-B outputs; event-gate; state caching |
| Accountability log too slow for the control loop | Log is async — signing + append + batch anchor; fast path is the deterministic gate, not the log |
| Keyless local sensing is spoofable | Corroboration requires ≥2 independently-signed keys; keyless sustained preemption hard-refused with a cumulative budget |
| Provenance ≠ veracity | The veracity/collusion distinction is honestly conceded `→unknown`; not adjudicated by the system |
| Coarse real Euston demand data | Demand calibrated to a named, time-resolved source (TfL/DfT hourly + turning counts + mix); a hard startup gate for any inferential claim |
| 8GB VRAM | Phi-4-mini INT4, inference-only, no training |
