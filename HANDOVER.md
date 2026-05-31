# Handover prompt — Edge Negotiator dissertation, fresh-session onboarding

Paste this verbatim into a new Claude Code (or other agent) session in this repo. It is self-contained: a fresh agent reading it has everything it needs to continue without re-deriving prior decisions.

> **Pivot notice (2026-05-31):** This project was reframed on 2026-05-31. Any older note describing the dissertation as a "Quarterly Equity Audit Protocol" with a CoT-faithfulness probe as an experiment is **superseded**. The equity audit and the CoT probe are no longer contributions. The new direction is below. The single source of truth is `03-implementation/PROJECT-DECISION-BRIEF.md`.

---

## Who I am and what I am doing

I am the UCL MSc Systems Engineering for IoT student writing the Edge Negotiator dissertation, supervised by Dr Akin Delibasi (UCL) and Lee Stott (Microsoft — Foundry Local, Phi-4). The project is **_The Edge Negotiator: Verified-Source Cross-Junction Coordination for SLM-Driven Traffic Signal Control._** A corridor of small-language-model agents — **Phi-4-mini (3.8B) via Microsoft Foundry Local, one per signalised junction** — coordinates signal timing by sharing predicted traffic state with neighbours, evaluated in **Eclipse SUMO on a real Lambeth corridor** (Brixton→Elephant & Castle; ~6 SLM-controlled junctions within a ~10–13-junction corridor, the rest on MaxPressure). Every agent has a **cryptographic identity** (Ed25519/ECDSA signatures); inter-junction messages are signed and verified against an **on-chain allowlist of approved agents with `revoke()` (Hyperledger Besu, permissioned)**; a **vehicle-conservation plausibility check** flags neighbour reports physically inconsistent with observed flow (spoofed or faulty); and a **tamper-evident audit log** records every decision and identity/registry change. SLM output is **terse (a single phase action, no chain-of-thought)**, justified by the CoT-faithfulness literature surveyed in the lit review. A deterministic **MaxPressure shield** validates or overrides every SLM decision and runs alone at quiet junctions.

The one defensible thesis claim: *authenticated, plausibility-checked cross-junction coordination for SLM-driven traffic control gives verifiable agent identity and spoofing/fault detection with a non-repudiable audit trail — with no claim of game-theoretic incentive-compatibility.*

## Read these before doing anything

In strict order:

1. **`03-implementation/PROJECT-DECISION-BRIEF.md`** — **THE single source of truth.** Decisions locked 2026-05-31. Where anything else (including `00-SCOPE-LOCKIN.md`) diverges, this brief wins. Covers what we are building, the locked decisions table, challenges/mitigations from the code audit, the ~3-month build plan, the terse-output (CoT) justification, what we can/cannot claim, baselines/metrics, and open action items.
2. **`C:\Users\Ebenezer\.claude\projects\e--assignments-dissertation\memory\MEMORY.md`** — index to the memory entries (`working-style`, `dissertation-direction`). Already loaded by the runtime, but skim for orientation.
3. **`00-SCOPE-LOCKIN.md`** at the repo root — the locked-scope file. **Note:** its original framing is the old equity-audit scope; the decision brief formally supersedes it pending a clean rewrite. Read it for repo context and for whatever it has been updated to say, but treat the brief as authoritative on any conflict.
4. **`06-literary-survey/INDEX.md`** — map of the literature survey. Its technical surveys ground the new direction (the CoT-faithfulness chapter is now design justification, not an experiment).

## Where the project is right now

- **Decisions locked 2026-05-31** (the reframe in the decision brief). Title retained, scope reframed.
- **Literature review** in `04-writing/` submits **~2026-06-03**. It is Edge-Negotiator-framed and **still holds** — its technical surveys (incl. the §2.6 CoT-faithfulness material) ground the new direction. **Do not rewrite it.**
- **28 new identity/detection papers** gathered (Prompt 9), currently staged in `prompt9-*-urls.txt` and not yet catalogued into the registry.
- **Build NOT yet started.**
- **Supervisor sign-off on the pivot is PENDING** (Akin: SUMO/MaxPressure/stats; Lee: Foundry/Phi/identity).

**Next concrete step — one of:**
1. Draft the **supervisor one-pager** to obtain sign-off on the reframe; or
2. **Scaffold the Wk 1–2 grid pipeline** — sumo-rl on a 2×2 synthetic grid, TraCI loop, MaxPressure baseline, and a single Phi-4-mini terse agent via Foundry Local returning `{"phase": N}` with pause-sim timing.

## Hard rules for any agent picking this up

These REPLACE all earlier hard rules.

- **Build on `sumo-rl`** (MIT, arbitrary nets). **Do NOT build on CoLLMLight/CityFlow** — CoLLMLight is welded to CityFlow; treat it as reference only and *reimplement* the neighbour-message algorithm, do not port the code.
- **Phi-4-mini is the primary model.** Qwen3-4B is an **optional late "model-agnostic" ablation only**, and only if a clean 1–2 week buffer exists.
- **Terse single-phase output, NO chain-of-thought.** The SLM emits an action only (`{"phase": N}`). Accountability comes from the signed audit log, not model self-narration.
- **Blockchain is async audit/registry ONLY** — on-chain allowlist + `revoke()` + audit log + conservation-check contract. It is **never in the real-time control loop** (fast path = signed messages over MQTT).
- **Make only honest claims.** Claim provenance / non-repudiation and verifiable identity — **NOT** "trust" or "truth" (the ledger faithfully records garbage-in too). Acknowledge the **`Xiao2026`** limit ourselves: a coordinated, conservation-respecting attacker can evade the consistency check; the auth layer is the complement.
- **`Tian2025` is motivation only** — no incentive-compatibility claims (type-incoherent for frozen LLMs).
- **Honour the India 90-day Study Away constraint.** The SUMO-on-laptop substrate (RTX 4050 8GB) was chosen partly to be London-resource-independent; the new build still fits. Do not recommend changes that anchor work to UCL hardware or on-site resources.
- **Do not rewrite the submitting literature review.** It is Edge-Negotiator-framed and holds; reuse it as design justification.

## How to confirm you have the picture

Before taking any action, reply with a one-paragraph summary stating: (1) the new project spine — authenticated + conservation-checked **cross-junction coordination** as the integrity layer over an SLM corridor; (2) the model — **Phi-4-mini** via Foundry Local, terse output, no CoT; (3) the identity mechanism — **Ed25519/ECDSA signatures + on-chain Besu allowlist with `revoke()`** plus the vehicle-conservation plausibility check; (4) the threats demonstrated — primary **spoofed traffic-state report**, secondary **faulty sensor**, optional **Sybil count-inflation**; (5) the next deliverable — the **supervisor sign-off one-pager** or the **Wk 1–2 grid pipeline scaffold**. If your summary contradicts `03-implementation/PROJECT-DECISION-BRIEF.md`, re-read that brief before acting.
