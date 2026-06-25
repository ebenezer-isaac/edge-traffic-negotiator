# Feature Specification: The Edge Negotiator

**Feature Branch**: `001-edge-negotiator`
**Created**: 2026-06-21
**Status**: Draft (MVP scope for supervisor review)
**Owner**: Ebenezer Veeraraju (UCL MSc Systems Engineering for IoT, 25153651)
**Supervisors**: Dr A. Delibasi (UCL), L. Stott (Microsoft)
**Input**: On-device SLMs at neighbouring traffic junctions coordinate to clear emergencies and handle incidents, and stay safe when a junction's coordination messages are compromised.

> Authored in the GitHub Spec Kit format (Spec-Driven Development). This is the `spec.md` (the WHAT and WHY for stakeholders). Technology and build sequencing live in `plan.md` and `tasks.md`. Project facts are drawn from the canonical `03-implementation/PROJECT-PROPOSAL.md` and the measured results in `03-implementation/DEMO-REPORT.md`.

---

## 1. Overview (for business stakeholders)

Neighbouring traffic signals increasingly coordinate (green waves, ambulance preemption). The moment they act on each other's messages, a faulty or hijacked junction can lie, and a naive coordinator acts on the lie: wasted green, starved side streets, or a road cleared for an ambulance that does not exist.

The Edge Negotiator is a corridor of traffic junctions that **coordinate to handle emergencies and incidents together**, each running a small AI model on the junction itself. A classical controller (MaxPressure) stays in charge by default and is the safety net; the AI is consulted only on the hard, ambiguous cases. Because junctions act on neighbours' reports, the system is built to **detect a compromised neighbour and degrade safely** rather than believe the lie.

The headline value is coordinated emergency response. Robustness to a compromised junction is the property that makes that coordination safe to deploy.

---

## 2. User Scenarios & Testing *(mandatory)*

### Primary user story
As a city traffic authority, when an emergency vehicle crosses a corridor, I want neighbouring junctions to clear a path together so the vehicle is delayed as little as possible, and I want a faked emergency from a tampered or hijacked junction to be refused, so the signal cannot be hijacked to starve other roads.

### Acceptance scenarios

1. **Real ambulance, single junction**
   **Given** an approved corridor with the system running, **when** an emergency vehicle is physically detected on a junction's own approach, **then** that junction preempts to clear it (local sensing is trusted and cannot be spoofed).

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
- **FR-003** A junction MUST grant emergency preemption for a vehicle it physically detects on its own approach.
- **FR-004** A junction MUST grant emergency preemption on a neighbour's advance claim only when an independent source corroborates it (a sighting from a junction other than the claimer, or its own local sensing).
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

- **SC-001 Emergency-vehicle delay**: coordinated preemption reduces emergency-vehicle corridor time versus no preemption. *Measured baseline: 31 s faster over 30 paired runs.*
- **SC-002 Spoof resistance**: every uncorroborated emergency claim is refused; zero false preemptions under a single compromised insider. *Measured: worst affected side-street wait held 16 s below a trust-everything controller.*
- **SC-003 Cost of trust**: the evidence requirement adds a bounded, reported cost to genuine preemption. *Measured: 8 s of ambulance time versus blindly trusting, accepted.*
- **SC-004 No-harm guarantee**: the trust layer does not slow normal traffic beyond a pre-registered margin.
- **SC-005 Detection quality**: precision, recall, and detection latency are reported across a sweep of lie sizes (the detectability envelope).
- **SC-006 Edge feasibility**: an on-device AI decision completes within the per-decision budget on Microsoft Foundry Local, with no cloud call. *Target budget: [NEEDS CLARIFICATION: agreed per-decision latency ceiling for production].*
- **SC-007 Auditability**: every signed message and decision is recoverable from a tamper-evident log.

---

## 5. Constraints and non-functional requirements (technical)

- **C-001 On the edge, no cloud, no retraining**: the deployed model is a frozen small model running locally (Microsoft Foundry Local). Training is permitted only for comparison baselines, never for the deployed model.
- **C-002 Single trust domain**: one city authority, one administrative key; a permissioned key registry rather than a decentralised ledger.
- **C-003 Safety is deterministic**: hard minimum and maximum green, mandatory clearance intervals, and an anti-starvation override are owned by the controller and cannot be violated by the AI.
- **C-004 Simulation substrate**: evaluation is in SUMO microsimulation (emergency-vehicle dynamics and lane blockage); results are relative-in-simulator, not absolute field numbers.
- **C-005 Verifiable agent identity**: each junction has a cryptographic identity, the same agent-trust problem as Microsoft Entra Agent ID, made physical and measurable.

---

## 6. MVP scope

**In scope (MVP):**
- The four-junction arterial corridor with the classical controller, signed coordination, registry, and plausibility check.
- Coordinated emergency handling: local-sensing preemption plus corroborated downstream pre-clearing.
- The live exploit-then-defend demonstration (real ambulance cleared; signed-but-spoofed emergency refused) with three modes (defended, trust-everything victim, no-preemption baseline).
- Measured results over 30 paired runs with confidence ranges.

**Out of scope (this MVP; tracked as next steps):**
- Making normal-traffic green-wave coordination steer decisions, not only verify them (currently verified end to end, not yet causal).
- Coordinated incident reallocation around a blockage.
- The real on-device model evaluation on Foundry Local (the demo uses a deterministic stand-in; the corroboration gate is deterministic, so the safety result is unchanged).
- A real-city arterial and a full demand sweep.
- Defence against colluding insiders or a stolen administrative key.

---

## 7. Current status (built vs next)

- **Built and measured**: signed coordination, registry, plausibility check, classical controller and safety net, the corroboration gate, the four-junction corridor, the exploit-then-defend demo, and the 30-run metrics. In one defended run: 6 local-sensing preemptions, 7 corroborated downstream preemptions, 6 phantom claims withheld.
- **Verified but not yet causal**: normal-traffic green-wave coordination (next build step).
- **Designed, not yet run**: real on-device model on Foundry Local; incident reallocation; real-city net and demand sweep.

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
