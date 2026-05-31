# The Edge Negotiator — Architecture Synthesis

**Status:** Architecture locked for the reframed project (2026-05-31), pending supervisor sign-off. Mirrors `03-implementation/PROJECT-DECISION-BRIEF.md`, the single source of truth.

> **This document supersedes the prior "Edge Negotiator — Locked Architecture Synthesis" (the equity-audit / Gini / CoT-faithfulness-probe / Besu-vs-Tessera framing).** That earlier synthesis is **stale and must not be acted on**. The pre-pivot state is recoverable at git commit `bcd06cb`. The dissertation pivoted on 2026-05-31; everything below reflects the new project.

**Working title (retained, reframed):** *The Edge Negotiator: Verified-Source Cross-Junction Coordination for SLM-Driven Traffic Signal Control.*

**Programme context:** UCL MSc SEIOT. Supervisors: Akin Delibasi (SUMO / MaxPressure / statistics) and Lee Stott (Foundry Local / Phi / identity). Hardware: RTX 4050 8GB laptop. Constraint: 90-day build, SUMO-on-laptop, executed from India.

---

## The Pitch

A corridor of **small-language-model agents — Phi-4-mini (3.8B) via Microsoft Foundry Local, one per signalised junction** — that **coordinate signal timing by sharing predicted traffic state** with their neighbours, evaluated in **Eclipse SUMO on a real Lambeth corridor** (Brixton → Elephant & Castle). Every agent holds a **cryptographic identity**; inter-junction messages are **signed and verified against a permissioned-ledger registry of approved agents**; and a **vehicle-conservation plausibility check** flags neighbour reports physically inconsistent with observed flow (spoofed or faulty). A tamper-evident ledger records every decision and every identity/registry change. A deterministic **MaxPressure shield** validates or overrides every SLM decision and runs alone at quiet junctions.

The architecture has two paths:

- **Fast path (real-time):** Agent A signs `state + forecast` and sends it to neighbour B over MQTT; Phi-4-mini proposes a phase; the MaxPressure shield acts. Signatures are verified against the registry.
- **Trust path (async, off the control loop):** Hyperledger Besu permissioned ledger holds the on-chain registry of approved identities with `revoke()`, runs the conservation reconciliation, and stores the tamper-evident audit log (provenance, non-repudiation).

**The one defensible claim (the thesis is staked on this):**
> *Authenticated, plausibility-checked cross-junction coordination for SLM-driven traffic control — verifiable agent identity (signatures + on-chain registry) plus a vehicle-conservation consistency check yield spoofing/fault detection and a non-repudiable audit trail, with no claim of game-theoretic incentive-compatibility.*

---

## Locked Architecture

| Component | Decision | Basis |
|---|---|---|
| Primary SLM | **Phi-4-mini 3.8B only**, via Foundry Local (INT4, inference-only) | Qwen edge irrelevant for the terse phase task; 8GB VRAM, no training |
| Optional SLM ablation | **Qwen3-4B** — late "model-agnostic" ablation *only* if a clean 1-2 wk buffer exists | Not co-primary; conversion is fiddly, edge unclear |
| SLM output | **Terse action only (`{"phase": N}`), no chain-of-thought** | CoT-faithfulness literature (design justification, §"Why terse") + latency budget |
| SLM role in loop | **Hybrid: SLM proposes, MaxPressure shield disposes; event-gated (skip quiet junctions)** | SafeLight SUMO precedent; event-trigger precedent (Amanullah/Keijzer) |
| MaxPressure shield | Deterministic (Varaiya 2013) — validates/overrides every SLM decision; runs alone at quiet junctions | Provides a safe, always-available fallback |
| Agent identity | **Ed25519/ECDSA signatures + small on-chain allowlist + `revoke()`.** DID/VC is future work | DID/VC is 3-5× the work and brittle for a single domain |
| Blockchain role | **Hyperledger Besu (QBFT) — async only: registry + audit log + conservation-check contract.** Never in the control loop (~1-2s finality) | Besu agent: async only; fast path is signed MQTT messages |
| Integrity comparison | **Besu permissioned ledger vs plain signed append-only log** | Quantifies what the chain buys over plain signing |
| Conservation check | Vehicle-conservation reconciliation: did A's claimed outflow match B's observed inflow within the travel-time window? | Catches insider FDI (spoofed reports) + faulty sensors |
| Communication | Signed neighbour-message bus over **MQTT** | Fast path transport |
| Registry governance | **Single city-authority admin key** (multisig = optional hardening) | Defensible for a one-operator pilot |
| Corridor scale | **~6 SLM-controlled junctions** (headroom to 8-10) within a **~10-13-junction real Lambeth corridor**; remaining junctions on MaxPressure | ~3 wk sweep at N=6 including re-run tax |
| Simulation base | **sumo-rl** (MIT, arbitrary nets) — reimplement the neighbour-message algorithm | NOT CoLLMLight/CityFlow (welded to CityFlow, not SUMO) |
| Network | Real Lambeth corridor (Brixton → Elephant & Castle), OSM-derived in netedit; demand from DfT AADF + assumed peak profile + SUMO `routeSampler`/calibrators | Real-corridor anchor with cited demand-synthesis method |
| Threats demonstrated | **(1) spoofed traffic-state report [primary], (2) faulty sensor [secondary], (3) optional Sybil count-inflation** | Conservation check catches insider FDI + faults; auth catches impersonation/replay |

---

## Contributions

1. **Authenticated, plausibility-checked cross-junction coordination for SLM-driven signal control** — the integrative novelty: verifiable agent identity (Ed25519/ECDSA + on-chain registry with revocation) fused with a vehicle-conservation consistency check, atop an SLM coordination platform.
2. **Spoofing/fault detection from the conservation check** — demonstrated against a spoofed neighbour report (primary), a faulty sensor (secondary), and optionally Sybil count-inflation.
3. **A non-repudiable, tamper-evident audit trail** for every decision and identity/registry change, with a head-to-head **Besu-vs-plain-signed-log** cost/benefit characterisation.
4. **Evidence that small off-the-shelf SLMs can coordinate a corridor** versus classical and uncoordinated baselines.

*Note:* the CoT-faithfulness literature is now **design justification only** (it motivates terse output), not a contribution. Equity audit (Gini/Rawlsian/counterfactual demographic re-run) is **dropped**. Incentive-compatibility is **not** claimed (`Tian2025` is motivation only).

---

## Build Plan (~3 months)

1. **Wk 1-2 — Pipeline on a 2×2 synthetic grid (sumo-rl).** TraCI loop, MaxPressure baseline, a single SLM agent via Foundry Local returning a terse phase decision, pause-sim inference timing. *In parallel:* begin extracting and cleaning the real Lambeth network in netedit (long-pole, no code dependency).
2. **Wk 3-4 — Cross-junction coordination.** Signed neighbour-message bus (MQTT); event-gated SLM coordination across the grid; MaxPressure shield/override. **Milestone: the "it coordinates" demo.**
3. **Wk 5-6 — Identity + ledger.** Besu QBFT in Docker; Ed25519 signing; on-chain allowlist + `revoke()`; web3.py glue; async audit log of every decision.
4. **Wk 7-8 — Conservation-check contract + attacks.** Vehicle-conservation reconciliation; inject (1) spoofed report, (2) faulty sensor, (3) optional Sybil; measure detection.
5. **Wk 9-10 — Swap in Lambeth network + full sweep.** ~6 SLM junctions, 30 seeds × 4 scenarios; BCa bootstrap, Holm-Bonferroni.
6. **Wk 11-12 — Write-up + viva prep.** Optional Qwen3-4B model-agnostic ablation *only* if buffered.

Everything after Milestone 2 (end Wk 4) is the integrity contribution and its evaluation.

---

## Why Terse Output (Design Justification, Not a Contribution)

The SLM emits a single terse phase decision with **no chain-of-thought**, by design. The faithfulness literature (Lit-Review §2.6) shows explicit CoT traces are **post-hoc rationalisations, not faithful causal records** (Turpin et al. 2023, biasing-features methodology; Lanham et al. 2023, causal-intervention battery; consistent across the sub-7B corpus). Emitting reasoning would add latency and token cost while providing **no trustworthy interpretability benefit**. Accountability is instead provided structurally — by the signed, tamper-evident audit log — not by the model's self-narration. This repurposes an already-written lit-review chapter as architectural justification, not a separate experiment.

---

## Baselines & Metrics

**Baselines:**
- **Fixed-time** (Webster)
- **MaxPressure** (also the shield)
- **Uncoordinated-SLM vs coordinated-SLM**
- **Optional CoLight** (canonical MARL baseline)

Classical baselines are reimplemented (~30 lines each, MIT-clean) rather than vendoring GPL RESCO.

**Metrics:**
- **Traffic:** average travel time (ATT), average queue, throughput.
- **Detection:** precision / recall / F1 at a **fixed false-alarm rate**; detection latency in control cycles.
- **Integrity overhead:** signing latency, ledger commit latency, and the **Besu-vs-plain-signed-log** comparison.

---

## What We Can / Cannot Claim

**Can claim:**
- Message authenticity — the report came from a currently-approved, registered member.
- Tamper-evident on-chain registration/revocation and a non-repudiable audit trail.
- Detection of *inconsistent* (uncoordinated-spoof or faulty) neighbour reports.
- That small off-the-shelf SLMs can coordinate a corridor versus the baselines.

**Cannot claim:**
- That the blockchain "creates trust" or "prevents lying" — it provides **provenance and identity, not truth** (it faithfully records garbage-in).
- **Incentive-compatibility** — type-incoherent for frozen LLMs; `Tian2025` is motivation only.
- Which of two disagreeing junctions is the wrong one.
- Defence against a *coordinated, conservation-respecting* attacker — the **`Xiao2026` evasion limit**, acknowledged by us, which is precisely what the auth layer complements.

We also retain the **Traffic-R1 cited-claim hedge**: Traffic-R1 is cited as a benchmark anchor, not deployed.

---

## Key Engineering Constraints (from the code audit)

| Constraint | Mitigation |
|---|---|
| Foundry Local serialises inference (~2-8s/call, no batching) | Terse output (~2s); pause SUMO during inference; event-gate; ≤6-8 SLM junctions; state caching |
| sumo-rl, not CoLLMLight/CityFlow | Reimplement the neighbour-message algorithm on sumo-rl; do not port CityFlow code |
| Blockchain too slow for control (1-2s finality) | Ledger is async registry + audit only; fast path = signed MQTT; batch commits |
| Consistency ≠ truth | Scope the threat model to uncoordinated spoofs + faults; cite `Xiao2026` ourselves; auth layer is the complement |
| No structured-output enforcement in Foundry Local | Prompt-and-parse + JSON validation/retry; MaxPressure fallback on parse failure |
| Coarse real Lambeth demand data | DfT AADF as link anchors + assumed peak profile + SUMO `routeSampler`/calibrators (method cited) |
| 8GB VRAM | Phi-4-mini INT4, inference-only, no training |
