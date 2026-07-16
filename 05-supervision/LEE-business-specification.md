# The Edge Negotiator: Specification (for Lee Stott, Microsoft)

**Student:** 25153651 (UCL MSc Systems Engineering for IoT) · **Date:** 2026-06-20
**Product line:** Edge AI for safety-critical infrastructure · **Platform:** Microsoft Foundry Local + Phi-4-mini
**Document type:** business-readable specification (problem, value, KPIs, requirements, MVP, milestones)

---

## 1. Executive summary

Traffic signals at adjacent junctions increasingly "talk" to coordinate green waves and emergency-vehicle preemption. Today that coordination either runs in the cloud at 8B–72B scale, or relies on isolated classical controllers that cannot handle cross-junction incidents. Neither path gives a city operator real-time, on-device coordination that clears an ambulance corridor without a cloud call.

The Edge Negotiator is a coordinated multi-agent signal system where a small language model (**Phi-4-mini, 3.8B, running locally on Microsoft Foundry Local**, one agent per junction) coordinates multiple junctions to clear emergency vehicles and handle incidents. A classical MaxPressure controller stays in charge by default and acts as a deterministic safety shield. The SLM is invoked only as a guarded exception handler on hard or ambiguous cases (emergencies, anomalies, incidents) where pure classical control falls short. Where the SLM's added value on these ambiguous cases is measured, it is characterised against a well-tuned reference rule rather than raced to beat it; a clean null is reported as honestly as a win.

What makes this coordination **deployable**: the inter-junction channel is signed and plausibility-checked, giving each agent verifiable identity for its neighbours. A junction whose messages fail corroboration is isolated automatically, so a single faulty node cannot corrupt the corridor. This is the same verifiable-agent-identity trust problem that Entra Agent ID addresses, here made physical and measurable.

**Why Microsoft cares:** it is a concrete, safety-critical showcase of (a) edge SLM inference on Foundry Local with no cloud dependency and no fine-tuning, coordinating real cross-junction emergencies, and (b) verifiable agent identity for multi-agent systems: the Entra Agent ID trust problem in hardware.

---

## 2. Problem and value

| | |
|---|---|
| **Problem** | Cross-junction emergency coordination (ambulance preemption, incident clearance) requires junctions to communicate. Classical isolated controllers cannot do it. Cloud-scale LLM coordinators add latency and dependency. And once junctions communicate, a single faulty or compromised node can degrade the whole corridor. |
| **Who has it** | City traffic authorities deploying connected or adaptive signals; emergency-services preemption operators. |
| **Today's gap** | Existing LLM/RL coordinators (CoLLMLight, LA-Light, REG-TSC) trust their inputs and run in the cloud at 8B–72B. Blockchain-based traffic-security work secures vehicle-to-signal data, not signal-to-signal coordination. None runs on local hardware with no retraining requirement. |
| **Our value** | A frozen 3.8B edge model coordinating junctions for emergency response, on local hardware, with no cloud call and no retraining. A signed channel with vehicle-conservation plausibility check makes that coordination trustworthy: (1) coordinates normally when neighbours are honest, (2) detects and safely isolates a faulty or compromised neighbour, (3) leaves a tamper-evident audit trail. |

---

## 3. Business KPIs (success in business terms)

| KPI | What it means to a city operator | Target / acceptance |
|---|---|---|
| **Emergency-vehicle delay** | How much faster a real ambulance clears the corridor | Reduced vs no-preemption baseline; reported with confidence intervals |
| **Spoofed-preemption resistance** | A fake emergency cannot commandeer the signal | 100% of uncorroborated emergency claims refused (no false preemption) |
| **No-harm guarantee** | Adding the coordination layer does not slow normal traffic | Defended-vs-undefended benign delta within the pre-registered margin (else reported honestly as overhead) |
| **Attack detection quality** | How reliably a lying neighbour is caught | Precision/recall/detection-latency reported across a sweep of lie sizes (the "detectability envelope") |
| **Safe degradation** | When a neighbour is untrusted, the corridor still functions | Automatic fallback to local control on the flagged edge; no gridlock attributable to the defence |
| **Edge feasibility** | Runs on local hardware within a decision budget | Phi-4-mini median ~0.5 s/decision on Foundry Local; gated so a corridor stays within budget |
| **Auditability** | Every decision and identity change is reviewable after the fact | Tamper-evident hash-chained log of all signed messages and decisions |

---

## 4. Functional requirements (MVP)

1. **FR-1 Multi-junction emergency coordination.** The Phi-4-mini agent coordinates neighbour junctions to clear an emergency-vehicle corridor; decisions run locally on Foundry Local with no cloud call and no retraining.
2. **FR-2 Authenticated coordination channel.** Each junction signs (Ed25519) its neighbour messages; receivers verify against a permissioned key registry with revocation. Unsigned, forged, or revoked messages are rejected with a logged reason.
3. **FR-3 Plausibility check.** Each receiver reconciles a neighbour's claimed outflow against its observed inflow (vehicle conservation); a sustained inconsistency is flagged.
4. **FR-4 Guarded SLM exception handling.** A classical MaxPressure controller decides by default; the Phi-4-mini agent is invoked only on a trigger (anomaly, emergency, or incident) and its proposal is validated by a deterministic safety shield.
5. **FR-5 Emergency preemption with corroboration.** A real emergency vehicle, sensed locally, is granted preemption. A claimed emergency is granted preemption only if corroborated by independent physical sensing, defeating a spoofed claim even from an authenticated insider.
6. **FR-6 Safe fallback.** On a flagged neighbour, the affected junction degrades to local control automatically (no human in the loop).
7. **FR-7 Tamper-evident audit.** All signed messages and decisions are hash-chained for after-the-fact review.

---

## 5. Technical requirements (non-functional)

| Area | Requirement |
|---|---|
| **Model** | Phi-4-mini (3.8B), frozen, inference-only, served by **Foundry Local** (no cloud, no fine-tuning). |
| **Latency** | SLM decision budget consistent with measured ~0.5 s/call; SLM invoked only on triggers and gated per corridor. |
| **Determinism** | Temperature-0; run-to-run agreement measured on the emergency prompts; decisions memoised by prompt-hash in evaluation. |
| **Identity** | Ed25519 keys per junction; permissioned registry with `revoke()`; constant-time verification. |
| **Safety envelope** | Hard min/max green, mandatory yellow + all-red clearance, anti-starvation bound; enforced deterministically, never overridable by the SLM. |
| **Simulator** | Eclipse SUMO (microscopic; supports `vClass=emergency` and lane blockage). |
| **Reproducibility** | Pinned model hash, quantisation, Foundry version, decode params, and seeds; results reproducible from (config, seed, model-hash). |
| **Threat scope (in)** | Outsider forgery, network replay/reorder (within session), a single compromised-but-approved insider lying above tolerance or spoofing an emergency. |
| **Threat scope (out, stated)** | ≥2-key conservation-respecting collusion (contained by revoke + audit, not detection); compromised admin key. |

---

## 6. MVP scope

**In:** multi-junction emergency coordination on Foundry Local; authenticated coordination with conservation/anomaly detection and measured precision/recall; deterministic safety shield with no-regression result; the live spoof-a-fake-emergency demonstration; one synthetic corridor + one real Lambeth corridor, benign and attacked, with full statistics; the detectability-envelope figure; honest performance reporting.

**Out (deliberately):** novel cryptography; a claim that the SLM beats the classical controller on routine traffic; RAG/retrieval (optional ablation only); a live blockchain in the evaluation loop (a signed hash-chained log suffices; blockchain kept as a characterised aside); hardware-in-the-loop (named as future work).

---

## 7. Architecture (one diagram in words)

```
 default  -> MaxPressure controller (classical, throughput-optimal, microsecond)   [stays in charge]
               | trigger fires? (conservation anomaly / emergency / incident)
               v
 escalate -> Phi-4-mini agent on Foundry Local -- coordinates neighbours, proposes a phase
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
| M4 Evaluation | Full demand sweep + real Lambeth corridor, benign + attacked, n=30, statistics; SLM-vs-reference-rule characterisation on the anticipated and novel/unanticipated case splits | In progress |
| M5 Detectability envelope | Recall/latency vs lie-magnitude figure | Planned |
| M6 Write-up | Dissertation + reproducibility package | Planned |

---

## 9. What we can and cannot claim (honesty boundary)

**Can claim:** coordinated multi-junction emergency response running on local hardware with no cloud dependency and no retraining; message authenticity from a currently-approved member; a tamper-evident, externally-auditable log; detection of inconsistent or spoofed neighbour reports with a measured envelope; a deterministic safety guarantee; a fair exploit-then-defend showing a competent cooperative controller is compromised and our layer defends it; an honest, pre-committed account of whether the edge SLM adds measurable value on ambiguous/contested states when characterised against a well-tuned reference rule, with a clean null reported as a valid finding.

**Cannot/do not claim:** novel cryptography; that the SLM beats the classical controller on routine traffic; that the blockchain creates trust (it records faithfully, including lies); which of two disagreeing junctions is the liar; defence against ≥2-key collusion or a compromised admin key; absolute (vs in-simulator) traffic numbers; external validity beyond SUMO (future work: hardware-in-the-loop).
