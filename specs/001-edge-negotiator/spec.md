# Feature Specification: The Edge Negotiator

**Feature Branch**: `001-edge-negotiator`
**Status**: Stakeholder specification (the WHAT and WHY)
**Owner**: Ebenezer Veeraraju (UCL MSc Systems Engineering for IoT, 25153651)
**Supervisors**: Dr A. Delibasi (UCL), L. Stott (Microsoft)
**Input**: On-device SLMs at neighbouring traffic junctions coordinate to clear emergencies and handle incidents, and stay safe when a junction's coordination messages are compromised.

> Authored in the GitHub Spec Kit format (Spec-Driven Development). This is the `spec.md` (the WHAT and WHY for stakeholders). The single source of truth for direction, scope, and framing is `MASTER-SPEC.md`; this document defers to it wherever the two touch.

---

## 1. Overview (for business stakeholders)

Neighbouring traffic signals increasingly coordinate (green waves, ambulance preemption). The moment they act on each other's messages, a hijacked junction that still holds a valid key can lie, and a naive coordinator acts on the lie: wasted green, starved side streets, or a road cleared for an ambulance that does not exist.

The Edge Negotiator is an on-device system for a stretch of signalised junctions, each running a small language model (SLM) on the junction itself. It asks one two-part question (the full statement is `MASTER-SPEC.md` §1): **H1 performance** — can an on-device SLM traffic-signal controller match or beat the MaxPressure baseline on the real Euston Road (A501), and at what model scale and configuration; and **H2 trust** — is every decision provably auditable, so an accident can be mechanically reconstructed afterwards. A classical controller (MaxPressure) stays in charge by default and is the safety net; the SLM is the candidate controller under study and, on flagged ambiguous cases, a guarded exception handler. A deterministic gate refuses a signed-but-uncorroborated emergency preemption from a compromised insider and clears physically-corroborated real emergencies; a signed, hash-chained accountability log (a Certificate-Transparency-style, quorum-anchored, cross-audited design credited to prior art, not claimed novel) makes every decision reconstructable.

This is an exploratory feasibility and scale-threshold study: limitations are explicitly allowed, and a negative or a scale-threshold is a valid result. Within H2, the audit's **measured blind spot** is reported honestly as a supporting result: the preemption attack controls the signal phase, which is *also* the variable that gates honest-witness coverage, so executing the attack opens the very coverage gap that would conceal it (the **self-referential coupling**). The honest boundary of what is accountable, not an unconditional guarantee, is what that result reports.

---

## 2. User Scenarios & Testing *(mandatory)*

### Primary user story
As a city traffic authority, when an emergency vehicle crosses a corridor, I want neighbouring junctions to clear a path together so the vehicle is delayed as little as possible, and I want a faked emergency from a tampered or hijacked junction to be refused, so the signal cannot be hijacked to starve other roads.

### Acceptance scenarios

1. **Real ambulance, single junction**
   **Given** an approved corridor with the system running, **when** an emergency vehicle is physically detected on a junction's own approach, **then** that junction preempts to clear it as a bounded, transient response (local sensing is strong evidence but is itself spoofable: a lone keyless local reading cannot force *sustained* preemption, and repeated keyless-driven preemptions are charged against a per-junction budget).

2. **Real ambulance, cross-junction coordination**
   **Given** an emergency vehicle that an upstream junction has already, independently sensed, **when** a downstream junction receives a signed advance claim for that vehicle, **then** the downstream junction pre-clears for it before arrival (the claim is corroborated by an independent sighting).

3. **Spoofed emergency from a compromised insider**
   **Given** a junction that holds a valid key but is compromised, **when** it sends a correctly signed claim for an emergency vehicle that does not exist, **then** the receiving junction authenticates the signature but withholds preemption because no independent sighting and no local vehicle corroborate it, and it stays on the classical controller.

4. **Real claim not yet corroborated**
   **Given** a signed advance claim that no other junction has yet confirmed, **when** it arrives, **then** preemption is withheld until a junction physically confirms the vehicle (the gate requires evidence, not intent).

5. **No regression when nobody lies**
   **Given** honest operation with no attack, **when** the defended system and a trust-everything baseline run on identical traffic, **then** their normal-traffic performance is within a pre-registered margin (the trust layer does not penalise honest operation).

### Edge cases
- Two emergency vehicles converge on one junction from conflicting approaches: the higher-severity (closer or halted) one is served first; the other on the next safe cycle.
- A junction's own emergency detector flaps for one tick: preemption stays latched until the vehicle clears the junction.
- A neighbour that should report goes silent while traffic still arrives: the junction falls back to local observation for that approach.
- A replayed signed message from an earlier tick: dropped before it can trigger preemption.
- A revoked junction sends a claim mid-emergency: rejected, while a locally sensed real vehicle still triggers preemption.

---

## 3. Requirements *(mandatory)*

### Functional requirements

- **FR-001** Junctions MUST exchange coordination messages over a channel that authenticates the sender against an approved-member registry and rejects unsigned, forged, replayed, or revoked messages.
- **FR-002** Junctions MUST share what they physically sense (vehicle sightings, emergency vehicles) with adjacent junctions so the corridor can act together.
- **FR-003** A junction MUST grant a bounded, transient emergency preemption for a vehicle it physically detects on its own approach, but MUST NOT let a lone keyless local reading force sustained preemption, and MUST charge repeated keyless-driven preemptions against a per-junction budget (local sensing is spoofable).
- **FR-004** A junction MUST grant sustained emergency preemption on a neighbour's advance claim only when independently-signed corroboration from at least two keys supports it (a signed sighting from a junction other than the claimer), recomputed from signed sighting records rather than a self-asserted count.
- **FR-005** A junction MUST refuse preemption for an emergency claim that is authenticated but uncorroborated (the spoofed-emergency case), and remain on the classical controller.
- **FR-006** The classical controller MUST be the default and the safety floor: every clear-cut safety decision is deterministic and never depends on the AI.
- **FR-007** The AI MUST be invoked only on flagged, ambiguous cases (a detector-flagged anomaly the classical rule cannot settle), and its proposal MUST be validated by the deterministic safety net before execution.
- **FR-008** The system MUST flag a neighbour report that is inconsistent with the junction's own observation (a plausibility or vehicle-conservation check) and MUST stop coordinating on a report it has judged implausible.
- **FR-009** The system MUST record a tamper-evident log of signed messages and decisions for external audit.
- **FR-010** The system MUST degrade safely (fall back to local control) when a coordination input is missing, late, or flagged, without stalling traffic.

### Key entities
- **Junction agent**: a signalised intersection running the classical controller, the on-device AI, and the coordination client.
- **Coordination message**: a signed report between adjacent junctions (a sighting, an advance claim, or a routine release toward a neighbour).
- **Emergency trigger**: local sensing or an advance claim, each carrying a trust source that decides admissibility.
- **Registry**: the authority's list of approved junction identities, with revocation.
- **Audit log**: the append-only, tamper-evident record of messages and decisions.

---

## 4. Success criteria (business KPIs) *(measurable)*

- **SC-001 Emergency-vehicle delay**: enabling preemption reduces emergency-vehicle corridor time versus no preemption. *Measured on the fixture demo (StubAgent, deterministic gate): 31 s faster over 30 paired runs. This reflects preemption-on vs preemption-off, not coordination and not the SLM.*
- **SC-002 Spoof resistance**: every signed-but-uncorroborated sustained-preemption claim is refused; zero false sustained preemptions under a single compromised insider (one corridor key). *Measured on the fixture demo: worst affected side-street wait held 16 s below a trust-everything controller.*
- **SC-003 Cost of trust**: the evidence requirement adds a bounded, reported cost to genuine preemption. *Measured on the fixture demo: 8 s of ambulance time versus blindly trusting, accepted.*
- **SC-004 No-harm guarantee**: the trust layer does not slow normal traffic beyond a pre-registered margin.
- **SC-005 Characterisation quality**: precision, recall, and detection latency are reported across the deviation-magnitude axis to map the free-deviation boundary (which stealthy conservation-consistent deviations escape); the headline object is the phase-coupled coverage threshold measured on the real corridor, not a detection ROC.
- **SC-006 Edge feasibility**: an on-device AI decision completes within the per-decision budget on Microsoft Foundry Local, with no cloud call. *Target budget: [NEEDS CLARIFICATION: agreed per-decision latency ceiling for production].*
- **SC-007 Auditability**: every signed message and decision is recoverable from a tamper-evident log.

---

## 5. Constraints and non-functional requirements (technical)

- **C-001 On the edge, no cloud, no retraining**: the deployed model is a frozen small model running locally (Microsoft Foundry Local). Training is permitted only for comparison baselines, never for the deployed model.
- **C-002 Single trust domain**: one city authority, one administrative key; a permissioned key registry. The accountability log is anchored to an external quorum of independent witnesses with a named cross-auditor (a Certificate-Transparency-style design credited to prior art); it is a permissioned, quorum-anchored append-only log, not an open consensus ledger, and it is not the contribution.
- **C-003 Safety is deterministic**: hard minimum and maximum green, mandatory clearance intervals, and an anti-starvation override are owned by the controller and cannot be violated by the AI.
- **C-004 Simulation substrate**: evaluation is in SUMO microsimulation (emergency-vehicle dynamics and lane blockage); results are relative-in-simulator, not absolute field numbers.
- **C-005 Verifiable agent identity**: each junction has a cryptographic identity, the same agent-trust problem as Microsoft Entra Agent ID, made physical and measurable.

---

## 6. MVP scope

**Substrate.** The evaluation substrate is the real **Euston Road (A501)**, a 3-4 signal stretch in central London (pre-built, committed). The synthetic four-junction arterial corridor is a **unit-test fixture only**, used for the deterministic fixture demo below.

**In scope (MVP):**
- The signed coordination layer, registry, and plausibility check, exercised on the synthetic four-junction fixture with the classical controller and safety net.
- Emergency handling: bounded keyless local-sensing preemption plus ≥2-key-corroborated downstream pre-clearing.
- The live demonstration (real ambulance cleared; signed-but-spoofed sustained preemption refused) with three modes (defended, trust-everything victim, no-preemption baseline).
- Measured results over 30 paired runs with confidence ranges (fixture demo, StubAgent + deterministic gate).

**Out of scope (this MVP; tracked as next steps):**
- The headline measurement of the self-referential coupling on Euston A501 (the phase-coupled coverage threshold and the free-deviation boundary).
- Making the coordination term steer decisions: it is an inert structural zero, reported as such, not a traffic-performance experiment.
- Coordinated incident reallocation around a blockage.
- The real on-device model evaluation on Foundry Local (the demo uses a deterministic stand-in; the corroboration gate is deterministic, so the safety result is unchanged). The on-device SLM has two roles: the H1 traffic-signal controller under study (the headline feasibility question, `MASTER-SPEC.md` §3), and an H2 support that writes a citation-faithful legal-reasoning note scored on citation-correctness and false-citation-rate against an un-rigged rule-to-text template, plus a characterised disambiguation classifier; a demoted claim leaves the SLM's presence intact.
- The full Euston demand sweep calibrated to a named time-resolved source.
- Defence against colluding insiders (≥2 keys), operator creation-time omission, or a stolen administrative key.

---

## 7. Current status (built vs next)

- **Built and measured (synthetic fixture)**: signed coordination, registry, plausibility check, classical controller and safety net, the corroboration gate, the four-junction fixture, the live demo, and the 30-run metrics. In one defended run: 6 local-sensing preemptions, 7 corroborated downstream preemptions, 6 phantom claims withheld.
- **Committed, not yet the measured headline**: the real Euston Road (A501) net and its edge map.
- **Structural, not an experiment**: the normal-traffic coordination term (inert structural zero).
- **Designed, not yet run**: the headline H1 SLM-vs-MaxPressure model x config sweep on Euston A501 (`MASTER-SPEC.md` §3/§8); the coupling boundary measurement (Experiment D, `MASTER-SPEC.md` §4.5/§8); the real on-device model on Foundry Local (H1 controller + the H2 citation-faithful legal-reasoning note and disambiguation classifier, reported either way including a claim-demoting negative); incident reallocation; the full Euston demand sweep.

---

## 8. Review & acceptance checklist

- [ ] No implementation detail (HOW) has leaked into requirements (WHAT and WHY only).
- [ ] Every functional requirement is testable.
- [ ] Every success criterion is measurable and has a baseline or a target.
- [ ] Built versus planned status is stated honestly.
- [ ] Open questions are marked with [NEEDS CLARIFICATION].
- [ ] Business stakeholder can read sections 1, 4, and 6 without specialist knowledge.

## 9. Open questions [NEEDS CLARIFICATION]

- SC-006: the agreed per-decision latency ceiling for a production corridor.
- C-004: whether any hardware-in-the-loop target is in scope beyond simulation for the dissertation.
- The deployment unit for a pilot (number of junctions, which authority, which corridor).
