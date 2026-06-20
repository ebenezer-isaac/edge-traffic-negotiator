> **SUPERSEDED (2026-06-20) — historical record only.** This brief captures the 2026-05-31 pivot and an *earlier* framing (Hyperledger Besu allowlist as a core component, "verified-source coordination"). The project has since been locked to **coordinated multi-agent edge-SLM signal control handling cross-junction emergencies and incidents (frozen Phi-4-mini; MaxPressure default + shield; SLM as guarded exception handler), with coordination staying robust when a junction is compromised**, with blockchain demoted to an optional aside. For the current direction read `03-implementation/PROJECT-PROPOSAL.md` + `FORMAL-SPECIFICATION.md` (canon), and `05-supervision/AKIN-research-survey-and-direction.md` / `LEE-business-specification.md`. Kept only as the record of what was signed off.

# Dissertation scope pivot — request for sign-off

**Student:** 25153651 (UCL MSc Systems Engineering for IoT) · **Date:** 2026-05-31
**Supervisors:** Dr Akin Delibasi (UCL) · Lee Stott (Microsoft)
**Purpose:** I am requesting your sign-off on a reframing of the dissertation scope before the project (build) phase begins. The literature review submits as-is on ~2026-06-03; this affects only the empirical project that follows.

---

## TL;DR

I am pivoting from the **Quarterly Equity Audit Protocol** to **authenticated, plausibility-checked cross-junction coordination** for an SLM traffic controller. Same corridor, same simulator, same ledger family, same hardware — but the contribution moves from *fairness auditing* to *trust/integrity of multi-agent coordination*. The title is retained:

> **The Edge Negotiator: Verified-Source Cross-Junction Coordination for SLM-Driven Traffic Signal Control.**

---

## The new project (one paragraph)

A corridor of small-language-model agents (**Phi-4-mini via Microsoft Foundry Local**, one per junction) coordinate signal timing in **Eclipse SUMO** on a real **Lambeth corridor** (Brixton→Elephant & Castle; ~6 SLM-controlled junctions within a ~10–13-junction corridor, the rest on Max-Pressure). Each agent holds a **cryptographic identity** (Ed25519 signatures + an on-chain **Hyperledger Besu** allowlist with revocation); inter-junction messages are signed and verified against that registry; and a **vehicle-conservation plausibility check** flags reports physically inconsistent with neighbours (spoofed or faulty). A deterministic **Max-Pressure shield** validates/overrides every SLM decision and runs alone at quiet junctions. A tamper-evident ledger records all decisions.

**Defensible claim (no over-reach):** *verifiable agent identity + a vehicle-conservation consistency check give spoofing/fault detection and a non-repudiable audit trail for SLM-driven traffic control — with no claim of game-theoretic incentive-compatibility.*

## Why pivot

1. **More of a systems-engineering contribution** (better fit for SEIOT): distributed multi-agent coordination, authenticated messaging, Byzantine/fault detection — rather than a fairness-metrics audit.
2. **Stronger Microsoft alignment**: multi-agent SLM systems on Foundry Local + verifiable agent identity is squarely Lee's advocacy (and parallels Entra Agent ID).
3. **Verified buildable in 3 months on the existing laptop**: I cloned the candidate codebases and confirmed the platform before committing (see Evidence).

## What changes

| Preserved | Dropped / superseded | New |
|---|---|---|
| UCL MSc SEIOT; SUMO; real Lambeth corridor; Max-Pressure family; Hyperledger Besu; RTX 4050 laptop; 90-day India SUMO-on-laptop constraint; statistical rigour (BCa bootstrap, Holm–Bonferroni); lit review submits as-is | Quarterly Equity Audit; Gini/Rawlsian/DIR/pedestrian-parity; counterfactual demographic re-run; CoT-faithfulness as a *contribution*; incentive-compatibility framing | Ed25519 + on-chain Besu allowlist/revoke (identity); vehicle-conservation spoof/fault detection; terse single-phase SLM output; "Besu vs plain signed log" comparison |

**Threats demonstrated:** spoofed traffic-state report (primary), faulty sensor (secondary), optional Sybil count-inflation.

## Feasibility evidence (not hand-waved)

- **sumo-rl** confirmed as the build base (MIT, arbitrary networks, per-junction state exposed); CoLLMLight is CityFlow-welded and used as an algorithm reference only.
- **Foundry Local** is GA and serves Phi-4-mini INT4 on 8GB; latency is managed by pausing the sim during inference, event-gating, and terse output.
- **Besu** is async audit/registry only (never in the control loop). The identity design follows the single-administrative-domain literature (Pino et al. 2023, which deliberately omits heavy DID/VC for exactly this case).
- 28 supporting papers gathered for the two new pillars (identity/registry; consistency/spoof detection).

## For Dr Delibasi (UCL) — review asks

The systems/experimental core is yours to pressure-test:
- **Control architecture:** the hybrid "SLM proposes → Max-Pressure shield disposes," event-gated. Sound?
- **Detection method:** vehicle-conservation invariant (A's exit flow ≈ B's approach inflow within a travel-time window) as a fault/spoof detector — methodologically defensible? I flag the honest limit (Xiao & Weng 2026: a *conservation-respecting* attacker evades it; the identity layer is the complement).
- **Experimental design:** ~6 SLM junctions; baselines = Fixed-time, Max-Pressure, uncoordinated-vs-coordinated SLM (+ optional CoLight); metrics = ATT/queue/throughput + detection precision/recall/F1 at fixed false-alarm-rate + detection latency. Adequate?

## For Lee Stott (Microsoft) — review asks + critique mapping

- **Foundry Local / Phi-4-mini** as the per-junction agent runtime, and **verifiable agent identity** on a permissioned ledger — does this fit the Microsoft public-sector / agent-identity narrative?
- **Honest note on your four critique pillars:** **S1 (CoT exposure)** is now answered structurally — the SLM emits *no* chain-of-thought (terse output), justified by the CoT-faithfulness literature; accountability comes from the signed audit log, not model self-narration. **S3 (deployment claims)** — hedging retained (e.g. Traffic-R1). **S4 (blockchain trade-offs)** — strengthened into a "Besu permissioned ledger vs plain signed append-only log" comparison answering *does this even need a blockchain*. **S2 (equity-audit operationalisation)** — **this pivot drops the equity focus**, which was the original load-bearing answer to S2. That is the single change I most need your explicit view on.

## Timeline & the ask

Lit review submits ~2026-06-03 unchanged. Build is ~3 months (grid-pipeline → real corridor → identity+ledger → attacks+evaluation → write-up). **I'd appreciate written sign-off (or concerns) on the reframing** — in particular Lee's view on dropping the equity (S2) focus, and Akin's on the detection methodology — before I commit the build.

*Full detail: `03-implementation/PROJECT-DECISION-BRIEF.md` (repo). Honest limits and non-claims are documented there.*
