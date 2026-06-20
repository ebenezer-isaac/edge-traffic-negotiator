# The Edge Negotiator — Project Specification (MVP, Requirements, KPIs)

**Audience:** supervisors (Lee Stott, Akin Delibasi), project review / standup.
**Status:** living document, 2026-06-20. Authoritative for *scope and acceptance*; the
[PROJECT-DECISION-BRIEF.md](PROJECT-DECISION-BRIEF.md) remains authoritative for *design rationale*, and
[DE-RISK-INDEX.md](DE-RISK-INDEX.md) for *measured evidence*. Where this document states a target, it is a
commitment to measure, not a claim already proven.

> Tooling note: Lee suggested GitHub Spec Kit (speckit.org) under Copilot. This document is the
> specification artifact itself, written to be portable into a Spec Kit `/specify` workflow (the sections
> below map to Spec Kit's user-scenarios / requirements / acceptance structure). It was authored directly,
> not generated through Copilot.

---

## 1. Problem & business context

City transport authorities are beginning to put AI agents in charge of safety-relevant infrastructure such
as traffic signals. Two risks block deployment:

1. **Trust of inputs.** Signal agents coordinate by exchanging traffic-state reports with neighbours. A
   spoofed report (compromised roadside unit) or a faulty sensor can degrade or weaponise control, and the
   operator cannot currently tell a real report from a manipulated one.
2. **Accountability.** When an AI agent makes a control decision, there is no tamper-evident record of *who*
   decided *what* on *which* inputs. Liability, incident review, and regulatory audit all need that record.

**The Edge Negotiator** is a reference design that lets small-language-model (SLM) signal agents coordinate a
corridor while making every inter-agent message **verifiable** and every decision **auditable**, with a
deterministic safety controller that can always override the AI. The value to an authority is *trustworthy,
accountable AI signal control that degrades safely under attack or fault.*

---

## 2. Stakeholders & users

| Stakeholder | Interest |
|---|---|
| City / transport authority (operator) | Safe, accountable signal control; detect compromised/faulty units; audit trail for incidents |
| Roadside agent (junction) | Coordinate with neighbours using only trusted inputs |
| Security / compliance reviewer | Non-repudiable log of decisions and identity changes |
| Researcher (this project) | Defensible contribution: the integrity layer, evaluated with statistical rigour |

---

## 3. Vision & the one defensible claim

> Authenticated, plausibility-checked cross-junction coordination for SLM-driven traffic control: verifiable
> agent identity (signatures + permissioned registry) plus a vehicle-conservation consistency check give
> spoofing/fault detection and a non-repudiable audit trail, with a deterministic MaxPressure shield
> guaranteeing safety. No claim of game-theoretic incentive-compatibility.

The **primary contribution is the integrity layer.** Control itself uses a **tiered, heuristic-first
architecture** (Section 9): a deterministic workhorse (MaxPressure, optionally with predictive green-wave
coordination) runs the predictable case, and the SLM is invoked **only as a guarded exception handler** when
the conservation/anomaly detector flags uncertainty. The performance objective is to **beat MaxPressure (even marginally) on delay**, pursued two-pronged so the
headline does not depend on the riskiest component:
1. **Floor (reliable):** deterministic predictive coordination (math green-wave) beats *vanilla* MaxPressure on
   delay by exploiting its myopia (MaxPressure is throughput-optimal, not delay-optimal). Literature-backed
   (coordinated/predictive control, CoLight); needs no smart SLM.
2. **Ceiling (the bet):** a retrieval-augmented (RAG) context-enhanced SLM, invoked only on the
   complex/uncertain states where MaxPressure is weakest, aims to push performance further. This is
   retrieval-augmented decision-making (in-context "experience" without training, the only route to
   learned-like behaviour under the no-training / 8 GB constraint). High-ceiling, reported honestly including
   nulls.
3. **Safety floor:** the deterministic shield guarantees the guarded system never regresses normal flow vs
   MaxPressure.

We do **not** claim the SLM beats a heuristic at *trivial in-distribution phase selection* (it does not, and
it is slower); the SLM is deployed only where it can add value. RL-beats-MaxPressure results require training
(closed to us by the 8 GB inference-only constraint); LLM-beats-MaxPressure results typically use far larger
models, so the 3.8B + RAG attempt is a genuine bet, not an assumed outcome.

---

## 4. MVP (minimum viable product)

The smallest system that demonstrates the value proposition end-to-end:

- **M-1** A corridor of N signalised junctions in Eclipse SUMO under a **tiered controller**: MaxPressure
  (optionally predictive-coordinated) drives every junction by default; the SLM is invoked only when the
  anomaly detector flags uncertainty; a deterministic shield validates the SLM's proposal and can always
  override it, so an escalation can never make control unsafe.
- **M-2** Signed neighbour messaging: each agent has a cryptographic identity; messages are Ed25519-signed and
  verified against a permissioned registry before they can influence any decision.
- **M-3** Registry with `register` / `revoke` under a single city-authority admin key, backed by an async
  permissioned ledger (Hyperledger Besu QBFT), never on the control loop.
- **M-4** Vehicle-conservation plausibility check that flags neighbour reports physically inconsistent with
  independent observation (spoofed over-claim or faulty under-claim).
- **M-5** Tamper-evident, hash-chained audit log of every control decision and every identity/registry change.
- **M-6** A **live attack demonstration**: inject a spoofed report / faulty sensor / impersonation and show
  detection and rejection firing in real time (not asserted, demonstrated).
- **M-7** Evaluation harness producing throughput-controlled traffic metrics and detection precision/recall,
  with proper statistics (BCa bootstrap, paired permutation, Holm correction) over ≥30 seeds.

**MVP acceptance** = M-1..M-7 all demonstrable on one corridor, reproducibly, without manual intervention.

### Build status against MVP

| Item | Status | Evidence |
|---|---|---|
| M-1 hybrid SLM + shield | Built | `hybrid_controller.py`, `controllers.py` |
| M-2 signed bus + verify | Built | `message_bus.py`, `identity.py` (166+ tests) |
| M-3 registry + revoke + Besu/QBFT | Built | `registry.py`, `besu_registry.py`, QBFT spike |
| M-4 conservation detection | Built (offline-validated) | `conservation.py`, `flow_conservation.py`, attack eval |
| M-5 hash-chained audit | Built | `audit_log.py` |
| M-6 live attack demo | **Not built** (gap) | offline harness only; no live injection path |
| M-7 stats eval, 30 seeds | Built (traffic + detection) | `evaluation.py`, `stats.py`, `evaluation_matrix.*` |

The two open items are **M-6 (live attack demonstration)** and the **coordination-performance objective**
(KPI-7), both in progress.

---

## 5. Scope boundary

**In scope (MVP + this dissertation):** single corridor; 6 SLM-controlled junctions within a real Lambeth
network plus a controlled synthetic corridor for the performance study; Ed25519 identity + allowlist +
`revoke`; conservation check for uncoordinated spoof + faulty sensor; async Besu audit; statistical
evaluation; live attack demo.

**Out of scope (named as future work):** DID/Verifiable-Credentials identity (allowlist suffices for a
single-operator pilot); multi-operator federation / multisig governance; defence against a *coordinated,
conservation-respecting* collusion attack (acknowledged residual limit, contained by `revoke` + audit, not
detection); city-scale (hundreds of junctions) sharding; real-time hardware-in-the-loop deployment.

---

## 6. Functional requirements

| ID | Requirement |
|---|---|
| FR-1 | Each SLM junction emits a terse phase decision `{"phase": N}`, no chain-of-thought; on parse failure or invalid index the MaxPressure shield decision stands. |
| FR-2 | The shield (MaxPressure) validates every SLM proposal and acts alone at event-gated quiet junctions. |
| FR-3 | Junctions exchange neighbour messages carrying an actual vehicle `release` toward each neighbour; messages are Ed25519-signed over canonical bytes. |
| FR-4 | A message may influence a decision only if it is from an adjacency neighbour, from a currently-approved registry member, signature-valid, and non-replayed; all rejects are logged with a precise reason. |
| FR-5 | The registry supports `register` and `revoke` under a single admin key; membership and key changes are recorded as audit events. |
| FR-6 | The conservation check reconciles each claimed release against independently observed flow and flags sustained inconsistency (over-claim = spoof, under-claim = fault). |
| FR-7 | Every control decision and every identity/registry change is appended to a hash-chained, tamper-evident audit log. |
| FR-8 | Coordination influences the executed decision through a causal pathway (predictive pressure term and/or SLM prompt), with a `coord_weight=0` ablation that reduces exactly to MaxPressure. |
| FR-9 | The system supports injecting spoof / faulty-sensor / impersonation attacks and reporting detection outcomes against ground truth. |

---

## 7. Business KPIs / success metrics

Measurable, with targets. "Target" = commitment to measure and report honestly, including nulls.

| ID | KPI | Target | How measured |
|---|---|---|---|
| KPI-1 | Spoof detection precision | ≥ 0.95 at the operating tolerance | attack eval, ground-truth labelled |
| KPI-2 | Spoof / fault detection recall | ≥ 0.60 above the jitter tolerance band | tolerance ROC |
| KPI-3 | Detection latency | ≤ a small constant number of control cycles | windows-to-flag on injected attack |
| KPI-4 | Impersonation / replay rejection | 100% (every unsigned/forged/replayed message dropped) | auth-layer eval |
| KPI-5 | Integrity overhead off the control loop | sign+verify p95 well inside the decision interval (msg transport p95 ~ ms vs ~10 s interval) | transport + crypto benchmarks |
| KPI-6 | Audit completeness & integrity | 100% of decisions + identity changes logged; hash-chain verifies; ledger never blocks control | audit + ledger isolation test |
| KPI-7 | Traffic performance vs MaxPressure | **Beat MaxPressure (even marginally) on mean-network-delay**, Holm-significant: floor via predictive coordination, ceiling via RAG-SLM on complex states | 30-seed sweep, BCa + permutation + Holm, on a headroom corridor |
| KPI-8 | Reproducibility | deterministic, CI-able without proprietary services; ≥30 seeds | StubAgent path, full-population tripinfo |
| KPI-9 | Safe degradation | zero control-loop stalls when ledger/broker degrade | fault-injection on async paths |

KPI-7 is the open performance bet. Current honest status: on the existing oversaturated grid and the Lambeth
arterial, coordination is *neutral* vs MaxPressure (no headroom). A dedicated corridor substrate with
green-wave headroom is built; next is the deterministic predictive controller (the reliable floor), then the
RAG-SLM enhancement on complex states (the ceiling bet). The margin target will be calibrated against the
specific RL/LLM-beats-MaxPressure results in the literature review.

---

## 8. Technical / non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | Per-decision latency must fit the event-gated interval (~10 s). Measured Phi-4-mini median ~0.5 s; >18x headroom. |
| NFR-2 | The permissioned ledger is strictly asynchronous (registry + audit only). Membership checks hit a locally-cached allowlist; audit writes are batched off-loop. On-chain writes (~1.5-2.1 s) must never gate a control decision. |
| NFR-3 | Security by default: all external inputs validated at the boundary; replay guard on the message bus; signature verification against registered keys; no secrets in source; reject malformed/hostile payload fields. |
| NFR-4 | Reproducibility: every result runs from a fixed seed; the deterministic StubAgent path runs with no proprietary dependency; tripinfo emitted with `--write-unfinished --write-undeparted` so metrics are survivorship-safe. |
| NFR-5 | Fast path transport (MQTT) and trust path (Besu) are decoupled; a degraded broker or node must not stall control (graceful "missing report = no update"). |
| NFR-6 | Immutability and explicit error handling throughout (no silent swallow); controllers never crash the simulation on a transport/GUI error. |
| NFR-7 | Evaluation on a real London (Lambeth A23/A3) corridor calibrated to DfT counts, plus a controlled synthetic corridor for the performance study. |

---

## 9. Architecture (summary)

**Tiered control (heuristic-first, AI-guarded):**
```
 default ─▶ MaxPressure (+ predictive green-wave coordination)   ← runs the predictable case, fast, optimal
              │
              │  conservation/anomaly detector flags uncertainty (spoof? fault? spillback? conflict?)
              ▼
 escalate ─▶ SLM exception handler  ──proposes──▶  deterministic shield validates / can override
              (invoked rarely, only on trigger)                  (safety guarantee: never worse than MaxPressure)
```

**Fast path (real-time, signed):** Agent A --sign(state+release)--> Agent B; event-gated.
**Trust path (async, Besu QBFT):** permissioned registry of approved identities + `revoke()`;
conservation check (claimed release vs observed inflow); hash-chained audit log.

Two unifications make the design coherent: (a) the *same* signed `release` messages serve both integrity
(conservation reconciliation) and predictive coordination (timed platoon arrival -> green-wave
pre-positioning); (b) the conservation/anomaly detector that catches spoof/fault is *also* the trigger that
decides when to escalate from heuristic to SLM. Integrity and the AI-guard reinforce each other.

---

## 10. Assumptions, constraints, dependencies

- 8 GB VRAM edge device; Phi-4-mini INT4, inference-only (no training).
- Foundry Local serialises SLM calls; mitigated by terse output, event-gating, ≤6-8 SLM junctions.
- Real Lambeth demand is coarse; anchored to DfT AADF + calibrators (GEH<5 at anchors).
- Single-operator pilot governance (one admin key); multisig is optional hardening.
- Dependencies: Eclipse SUMO, Hyperledger Besu (pinned 24.12.0), Foundry Local, MQTT broker, Python stack.

---

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| No traffic-performance headroom over MaxPressure | Headline the integrity contribution (proven); pursue performance only on a corridor with green-wave headroom; report nulls honestly |
| Coordination causally inert with a reliable agent | Predictive pressure term that actually disposes + `coord_weight=0` ablation; or real-SLM prompt pathway at full seed power |
| Conservation check proves consistency, not truth | Threat model scoped to uncoordinated spoof + fault; collusion named as residual limit, contained by revoke + audit |
| Ledger latency on control loop | Strictly async; cached allowlist; batched audit |
| Single broker / single key SPOF | Named as production hardening (redundancy, multisig) |

---

## 12. Claims vs non-claims (honesty boundary)

**Can claim:** message authenticity from a currently-approved member; tamper-evident registration/revocation +
audit; detection of inconsistent (uncoordinated-spoof or faulty) neighbour reports; safe override by a
deterministic shield.

**Cannot claim:** that the blockchain "creates trust" or "prevents lying" (it records garbage-in faithfully);
incentive-compatibility; which of two disagreeing junctions is wrong; defence against a coordinated,
conservation-respecting attacker. Traffic-performance superiority over MaxPressure is **not yet established**
and will be claimed only if the powered corridor evaluation supports it.

---

## 13. Roadmap

1. Corridor headroom substrate + predictive coordination controller (in progress) — KPI-7.
2. Live attack demonstration (M-6) — the integrity story, shown not asserted.
3. Powered 30-seed evaluation: traffic (vs fixed/MaxPressure) + detection (P/R/F1/latency).
4. Write-up + viva; optional Qwen model-agnostic ablation if buffered.
