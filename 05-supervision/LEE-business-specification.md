# The Edge Negotiator — Specification (for Lee Stott, Microsoft)

**Student:** 25153651 (UCL MSc Systems Engineering for IoT) · **Date:** 2026-06-20
**Product line:** Edge AI for safety-critical infrastructure · **Platform:** Microsoft Foundry Local + Phi-4-mini
**Document type:** business-readable specification (problem, value, KPIs, requirements, MVP, milestones)

---

## 1. Executive summary

Traffic signals at adjacent junctions increasingly "talk" to coordinate (green waves, emergency-vehicle preemption). The moment they talk, the messages between them become an attack surface: a faulty or compromised junction can lie, and a naive coordinator will act on the lie — wasting green time, starving side streets, or being tricked into clearing the road for an ambulance that does not exist.

The Edge Negotiator is a traffic-signal control system where a small language model (**Phi-4-mini, 3.8B, running locally on Microsoft Foundry Local**, one agent per junction) coordinates with its neighbours over a **signed, plausibility-checked** channel, on top of a classical controller that stays in charge by default and acts as a safety net. The contribution is **trustworthy degradation**: when a neighbour's messages are authenticated but compromised, the system detects the inconsistency and falls back safely rather than acting on a lie.

**Why Microsoft cares:** it is a concrete, safety-critical showcase of (a) edge SLM inference on Foundry Local with no cloud dependency and no fine-tuning, and (b) verifiable agent identity for multi-agent systems — the same trust problem Entra Agent ID addresses, here made physical and measurable.

---

## 2. Problem and value

| | |
|---|---|
| **Problem** | Coordinated signal control assumes neighbours are honest. A single faulty or compromised junction can degrade a whole corridor, and emergency-preemption channels are spoofable. |
| **Who has it** | City traffic authorities deploying connected/adaptive signals; emergency-services preemption operators. |
| **Today's gap** | Existing LLM/RL coordinators (CoLLMLight, LA-Light, REG-TSC) trust their inputs and run in the cloud at 8B–72B. Blockchain-based traffic-security work secures vehicle→signal data, not signal↔signal coordination. None measures how detection degrades as an attacker gets more capable. |
| **Our value** | A frozen 3.8B edge model + a vehicle-conservation plausibility check that (1) keeps coordinating when neighbours are honest, (2) detects and safely degrades when one lies, and (3) leaves a tamper-evident audit trail — all on local hardware. |

---

## 3. Business KPIs (success in business terms)

| KPI | What it means to a city operator | Target / acceptance |
|---|---|---|
| **Emergency-vehicle delay** | How much faster a real ambulance clears the corridor | Reduced vs no-preemption baseline; reported with confidence intervals |
| **Spoofed-preemption resistance** | A fake emergency cannot commandeer the signal | 100% of uncorroborated emergency claims refused (no false preemption) |
| **No-harm guarantee** | Adding the security layer does not slow normal traffic | Defended-vs-undefended benign delta within the pre-registered margin (else reported honestly as overhead) |
| **Attack detection quality** | How reliably a lying neighbour is caught | Precision/recall/detection-latency reported across a sweep of lie sizes (the "detectability envelope") |
| **Safe degradation** | When a neighbour is untrusted, the corridor still functions | Automatic fallback to local control on the flagged edge; no gridlock attributable to the defence |
| **Edge feasibility** | Runs on local hardware within a decision budget | Phi-4-mini median ~0.5 s/decision on Foundry Local; gated so a corridor stays within budget |
| **Auditability** | Every decision and identity change is reviewable after the fact | Tamper-evident hash-chained log of all signed messages and decisions |

---

## 4. Functional requirements (MVP)

1. **FR-1 Authenticated coordination.** Each junction signs (Ed25519) its neighbour messages; receivers verify against a permissioned key registry with revocation. Unsigned/forged/revoked messages are rejected with a logged reason.
2. **FR-2 Plausibility check.** Each receiver reconciles a neighbour's *claimed* outflow against its *observed* inflow (vehicle conservation); a sustained inconsistency is flagged.
3. **FR-3 Guarded SLM exception handling.** A classical MaxPressure controller decides by default; the Phi-4-mini agent is invoked only on a trigger (anomaly / emergency / incident) and its proposal is validated by a deterministic safety shield.
4. **FR-4 Emergency preemption with corroboration.** A real emergency vehicle, sensed locally, is granted preemption. A *claimed* emergency is granted preemption only if corroborated by independent physical sensing — defeating a spoofed claim even from an authenticated insider.
5. **FR-5 Safe fallback.** On a flagged neighbour, the affected junction degrades to local control automatically (no human in the loop).
6. **FR-6 Tamper-evident audit.** All signed messages and decisions are hash-chained for after-the-fact review.

---

## 5. Technical requirements (non-functional)

| Area | Requirement |
|---|---|
| **Model** | Phi-4-mini (3.8B), frozen, inference-only, served by **Foundry Local** (no cloud, no fine-tuning). |
| **Latency** | SLM decision budget consistent with measured ~0.5 s/call; SLM invoked only on triggers and gated per corridor. |
| **Determinism** | Temperature-0; run-to-run agreement measured on the emergency prompts; decisions memoised by prompt-hash in evaluation. |
| **Identity** | Ed25519 keys per junction; permissioned registry with `revoke()`; constant-time verification. |
| **Safety envelope** | Hard min/max green, mandatory yellow + all-red clearance, anti-starvation bound — enforced deterministically, never overridable by the SLM. |
| **Simulator** | Eclipse SUMO (microscopic; supports `vClass=emergency` and lane blockage). |
| **Reproducibility** | Pinned model hash, quantisation, Foundry version, decode params, and seeds; results reproducible from (config, seed, model-hash). |
| **Threat scope (in)** | Outsider forgery, network replay/reorder (within session), a single compromised-but-approved insider lying above tolerance or spoofing an emergency. |
| **Threat scope (out, stated)** | ≥2-key conservation-respecting collusion (contained by revoke + audit, not detection); compromised admin key. |

---

## 6. MVP scope

**In:** authenticated coordination; conservation/anomaly detection with measured precision/recall; deterministic safety shield with no-regression result; the live spoof-a-fake-emergency demonstration; one synthetic corridor + one real Lambeth corridor, benign and attacked, with full statistics; the detectability-envelope figure; honest performance reporting.

**Out (deliberately):** novel cryptography; a claim that the SLM beats the classical controller on normal traffic; RAG/retrieval (optional ablation only); a live blockchain in the evaluation loop (a signed hash-chained log suffices; blockchain kept as a characterised aside); hardware-in-the-loop (named as future work).

---

## 7. Architecture (one diagram in words)

```
 default  -> MaxPressure controller (classical, throughput-optimal, microsecond)   [stays in charge]
               | trigger fires? (conservation anomaly / emergency / incident)
               v
 escalate -> Phi-4-mini agent on Foundry Local -- proposes a phase
               v
            deterministic safety shield validates / can override            [hard envelope]
```
Neighbour messages ride a signed bus verified against a permissioned registry; a vehicle-conservation check screens every claim before it can influence a decision; a hash-chained log records everything for audit.

---

## 8. Milestones

| Milestone | Deliverable | Status |
|---|---|---|
| M1 Coordination substrate | Signed bus + registry + MaxPressure shield, 2-node clickable demo | Built |
| M2 Detection | Vehicle-conservation + CUSUM anomaly detector | Built |
| M3 Emergency + corroboration | Emergency controller + corroboration gate; exploit-then-defend demo | Built (this session) |
| M4 Evaluation | Full demand sweep + real Lambeth corridor, benign + attacked, n=30, statistics | In progress |
| M5 Detectability envelope | Recall/latency vs lie-magnitude figure | Planned |
| M6 Write-up | Dissertation + reproducibility package | Planned |

---

## 9. What we can and cannot claim (honesty boundary)

**Can claim:** message authenticity from a currently-approved member; a tamper-evident, externally-auditable log; detection of inconsistent/spoofed neighbour reports with a *measured* envelope; a deterministic safety guarantee; a fair exploit-then-defend showing a competent cooperative controller is compromised and our layer defends it; an honest account of whether the edge SLM adds value on contested states.

**Cannot/do not claim:** novel cryptography; that the SLM beats the classical controller on routine traffic; that the blockchain creates trust (it records faithfully, including lies); which of two disagreeing junctions is the liar; defence against ≥2-key collusion or a compromised admin key; absolute (vs in-simulator) traffic numbers; external validity beyond SUMO (future work: hardware-in-the-loop).
