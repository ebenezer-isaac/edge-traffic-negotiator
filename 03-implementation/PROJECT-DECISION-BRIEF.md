# The Edge Negotiator — Project Decision Brief

**Status:** Decisions locked 2026-05-31 (supersedes the equity-audit framing in `00-SCOPE-LOCKIN.md`, pending supervisor sign-off). Title retained, reframed.

**Working title:** *The Edge Negotiator: Verified-Source Cross-Junction Coordination for SLM-Driven Traffic Signal Control.*

This brief consolidates a verified feasibility investigation (cloned repos + 5-agent code audit + 4-agent decision research + 28 new papers). It is the single source of truth for the build. Where it diverges from `00-SCOPE-LOCKIN.md`, this brief wins.

---

## 1. What we are building

A corridor of **small-language-model agents (Phi-4-mini 3.8B via Microsoft Foundry Local), one per signalised junction**, that **coordinate signal timing by sharing predicted traffic state** with their neighbours, evaluated in **Eclipse SUMO on a real London (Lambeth) corridor**. Every agent has a **cryptographic identity**; inter-junction messages are **signed and verified against a permissioned-ledger (Hyperledger Besu) registry of approved agents**; and a **vehicle-conservation plausibility check** flags reports physically inconsistent with neighbours (spoofed or faulty). A tamper-evident ledger records all decisions and all identity/registry changes. A deterministic **MaxPressure shield** validates or overrides every SLM decision and runs alone at quiet junctions.

```
 ┌─ FAST PATH (real-time, signed messages) ──────────────┐
 │  Agent A ──sign(state + forecast)──▶ Agent B          │
 │  Phi-4-mini proposes phase · MaxPressure shield acts   │
 └────────────────────────────────────────────────────────┘
        │ verify sig vs registry      │ hash every decision
 ┌─ TRUST PATH (async, Besu permissioned ledger) ────────┐
 │  • on-chain registry of approved agent identities      │
 │    + revoke() for a compromised agent                  │
 │  • conservation check: did A's claimed outflow match   │
 │    B's observed inflow within the travel-time window?  │
 │  • tamper-evident audit log (provenance, non-repudiation)│
 └────────────────────────────────────────────────────────┘
```

**The one defensible claim (stake the thesis on this):**
> *Authenticated, plausibility-checked cross-junction coordination for SLM-driven traffic control — verifiable agent identity (signatures + on-chain registry) and a vehicle-conservation consistency check give spoofing/fault detection and a non-repudiable audit trail, with no claim of game-theoretic incentive-compatibility.*

---

## 2. Locked decisions

| # | Decision | Choice | Basis |
|---|---|---|---|
| Spine | Research focus | **(a) authentication + (b) conservation-check fused as the integrity layer; (c) coordination is the platform** | User + novelty agent: integrative novelty is open |
| Model | Which SLM | **Phi-4-mini only.** Qwen3-4B = optional late "model-agnostic" ablation only if a clean 1-2 wk buffer | Model agent (high): Qwen edge irrelevant for terse phase task; conversion 3-6 fiddly days |
| Output | What the SLM emits | **Terse action only (`{"phase": N}`), no reasoning** | CoT-faithfulness literature (see §5) + latency budget |
| Role | SLM in the loop | **Hybrid: SLM proposes, MaxPressure shield disposes; event-gated (skip quiet junctions)** | Detection agent (high): SafeLight SUMO precedent; Amanullah/Keijzer event-trigger precedent |
| Identity | Auth mechanism | **Build: Ed25519/ECDSA signatures + small on-chain allowlist + `revoke()`. Position DID/VC as future work** | Identity agent (~0.9): `proofmember23` strips VCs for single-domain; DID/VC is 3-5× work and brittle |
| Ledger | Blockchain role | **Registry + audit log + conservation-check contract. Plus "Besu vs plain signing" comparison** | Besu agent: async only, never in control loop |
| Scale | Corridor size | **6 SLM-controlled junctions** (headroom to 8-10 with terse output) within a **~10-13-junction real Lambeth corridor** (Brixton→Elephant & Castle), rest on MaxPressure | Scale agent: ~3 wk sweep at N=6 incl. re-run tax |
| Threats | What we demonstrate | **(1) spoofed traffic-state report [primary], (2) faulty sensor [secondary], (3) optional Sybil count-inflation** | Detection agent: conservation check catches insider FDI + faults; auth catches impersonation/replay |
| Admin key | Registry governance | **Single city-authority key** (multisig = optional hardening) | Identity agent: defensible for one-operator pilot |
| Old scope | Equity audit + CoT probe | **Dropped as contributions.** CoT literature repurposed as design justification (§5); equity dropped | User |
| Process | Supervisors / lit review | **Project may evolve past the submitted lit review; title retained, reframed.** Supervisor sign-off pending | User |

---

## 3. Challenges & mitigations (from the code audit)

| Challenge | How we tackle it |
|---|---|
| Foundry Local serialises calls (~2-8s each, no batching) | Terse output (~2s); pause SUMO during inference; event-gate; ≤6-8 SLM junctions; state caching |
| CoLLMLight is welded to CityFlow, not SUMO | Build on **sumo-rl** (MIT, arbitrary nets); *reimplement* the neighbour-message algorithm, don't port the code |
| Blockchain too slow for control (1-2s finality) | Ledger is async registry + audit only; fast path = signed messages over MQTT; batch commits |
| Consistency check proves consistency, not truth | Scope threat model to uncoordinated spoofs + faults; cite `Xiao2026` evasion limit ourselves; auth layer is the complement |
| No structured-output enforcement in Foundry Local | Prompt-and-parse + JSON validation/retry; MaxPressure fallback on parse failure |
| Real Lambeth demand data is coarse | DfT AADF as link anchors + assumed peak profile + SUMO `routeSampler`/calibrators (cite the method) |
| 8GB VRAM | Phi-4-mini INT4, inference-only, no training |

---

## 4. Build plan (revised, ~3 months)

1. **Wk 1-2 — Pipeline on a 2×2 synthetic grid (sumo-rl).** TraCI loop, MaxPressure baseline, single SLM agent via Foundry Local returning a terse phase decision, pause-sim timing. *In parallel:* start extracting + cleaning the real Lambeth network in netedit (long-pole, no code dependency).
2. **Wk 3-4 — Cross-junction coordination.** Signed neighbour-message bus (MQTT); event-gated SLM coordination across the grid; MaxPressure shield/override.
3. **Wk 5-6 — Identity + ledger.** Besu QBFT in Docker; Ed25519 signing; on-chain allowlist + `revoke()`; web3.py glue; async audit log of every decision.
4. **Wk 7-8 — Conservation-check contract + attacks.** Vehicle-conservation reconciliation; inject (1) spoofed report, (2) faulty sensor, (3) optional Sybil; measure detection.
5. **Wk 9-10 — Swap in Lambeth network + full sweep.** ~6 SLM junctions, 30 seeds × 4 scenarios. Stats: BCa bootstrap, Holm-Bonferroni (reuse existing plan).
6. **Wk 11-12 — Write-up + viva prep.** Optional: Qwen3-4B model-agnostic ablation *only* if buffered.

**Milestone 2 (end Wk 4)** = the "it coordinates" demo; everything after is the integrity contribution + evaluation.

---

## 5. Design justification — why terse output (CoT)

The SLM emits a **single terse phase decision with no chain-of-thought**, by design. This is compelled by the faithfulness literature surveyed in Lit-Review §2.6: explicit CoT traces are **post-hoc rationalisations, not faithful causal records** (Turpin et al. 2023, biasing-features methodology; Lanham et al. 2023, causal-intervention battery; consistent across the sub-7B corpus). Emitting reasoning would therefore add latency and token cost while providing **no trustworthy interpretability benefit**. Accountability is instead provided structurally — by the signed, tamper-evident audit log — not by the model's self-narration. *(This repurposes an already-written lit-review chapter as architectural justification rather than a separate experiment.)*

---

## 6. What we can / cannot claim

**Can:** message authenticity from a currently-approved registered member; tamper-evident on-chain registration/revocation + audit; detection of *inconsistent* (uncoordinated-spoof or faulty) neighbour reports; "small off-the-shelf SLMs can coordinate a corridor" vs baselines.

**Cannot:** that the blockchain "creates trust" or "prevents lying" (it faithfully records garbage-in); incentive-compatibility (type-incoherent for frozen LLMs — `Tian2025` is motivation only); which of two disagreeing junctions is wrong; defence against a *coordinated, conservation-respecting* attacker (`Xiao2026` — acknowledged limit, motivates the auth layer).

---

## 7. Baselines & metrics

- **Traffic baselines:** Fixed-time (Webster), MaxPressure (also the shield), uncoordinated-SLM vs coordinated-SLM; optional CoLight. Reimplement classical baselines (~30 lines each, MIT-clean) rather than vendoring GPL RESCO.
- **Traffic metrics:** average travel time, average queue, throughput.
- **Detection metrics:** precision/recall/F1 at a fixed false-alarm rate; detection latency in control cycles.
- **Integrity overhead:** signing latency, ledger commit latency, "Besu vs plain signed log" comparison.

---

## 8. Open items requiring action

- [ ] Supervisor sign-off (Akin: SUMO/MaxPressure/stats; Lee: Foundry/Phi/identity) on this reframe.
- [ ] Formally supersede / update `00-SCOPE-LOCKIN.md` once signed off.
- [ ] Catalogue the 28 Prompt-9 papers into the registry (currently staged in `prompt9-*-urls.txt`).
- [ ] Decide multisig vs single admin key (default: single).
