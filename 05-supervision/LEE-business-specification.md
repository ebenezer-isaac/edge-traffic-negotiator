# The Edge Negotiator: Specification (for Lee Stott, Microsoft)

**Student:** 25153651 (UCL MSc Systems Engineering for IoT) · **Date:** 2026-06-20
**Product line:** Edge AI for safety-critical infrastructure · **Platform:** Microsoft Foundry Local + Phi-4-mini
**Document type:** business-readable specification (problem, value, KPIs, requirements, MVP, milestones)

---

## 1. Executive summary

Traffic signals at adjacent junctions increasingly "talk" to coordinate green waves and emergency-vehicle preemption. Once junctions communicate, a compromised-but-authenticated insider can claim a fake emergency to commandeer preemption — and today's coordination systems either trust that channel outright or secure who-sent-it without ever asking whether the claim is corroborated by physical reality.

The Edge Negotiator is an on-device, trust-preserving coordination layer for a corridor of signalised junctions (piloted on the real **Euston Road, A501**), built on three contributions. (1) A **deterministic real-time gate** — Ed25519 authentication, a vehicle-conservation/CUSUM plausibility check, and corroboration — that **refuses** a signed-but-uncorroborated emergency-preemption claim from a compromised insider, and **clears** a physically-corroborated real emergency, on top of a classical MaxPressure controller that stays in charge by default as the safety floor. (2) A **Certificate-Transparency-style, quorum-anchored, cross-audited, signature-verified accountability log**: every message and decision is hash-chained, anchored to ≥2 external witnesses, and cross-audited — the mechanism is credited to prior art (RFC 6962, CONIKS, A2M, TrInc, PeerReview), not claimed as a novel invention. (3) The novel object: a **self-referential coupling** — the preemption attack controls the signal phase, which is also the variable that gates honest-witness coverage, so executing the attack opens the very coverage desert that conceals it — stated as a conditional lemma under explicit hypotheses, with one severe, pre-registered measurement of its boundary on the real corridor. A frozen **Phi-4-mini (3.8B)**, one per junction and served locally by **Microsoft Foundry Local**, is a self-contained fourth answer to the same question: a citation-faithful legal-reasoning note over the verified audit window, measured on citation-correctness and false-citation-rate against an un-rigged rule-based baseline.

**What makes this deployable:** the inter-junction channel is signed and plausibility-checked, giving each agent verifiable identity for its neighbours, and every decision lands in an externally-anchored, cross-audited log rather than a machine verdict. This is the same verifiable-agent-identity trust problem that Entra Agent ID addresses, here made physical and measured against a named adversary.

**Why Microsoft cares:** it is a concrete, safety-critical showcase of (a) edge SLM inference on Foundry Local with no cloud dependency and no fine-tuning, producing a citation-faithful accountability note rather than an unaccountable action, and (b) verifiable agent identity plus an externally-anchored accountability log for multi-agent systems — the Entra Agent ID trust problem in hardware, with an honest, measured account of where that accountability holds and where it does not.

---

## 2. Problem and value

| | |
|---|---|
| **Problem** | Cross-junction emergency coordination (ambulance preemption, incident clearance) requires junctions to communicate. A compromised-but-authenticated insider can exploit that channel to force a fake preemption, and a merely-signed message does not distinguish a lie from the truth. What is mechanically accountable after the fact, and what is not, has to be stated honestly rather than assumed. |
| **Who has it** | City traffic authorities deploying connected or adaptive signals; emergency-services preemption operators. |
| **Today's gap** | Existing LLM/RL coordinators (CoLLMLight, LA-Light, REG-TSC) trust their inputs and run in the cloud at 8B–72B. Blockchain-based traffic-security work secures vehicle-to-signal data, not signal-to-signal coordination, and gives non-repudiation (who sent it), not truthfulness (whether it's true). None runs on local hardware with no retraining requirement, and none couples the attack lever to the accountability coverage it needs to be caught. |
| **Our value** | A deterministic gate that refuses an uncorroborated preemption claim and clears a corroborated one; a signed, quorum-anchored, cross-audited accountability log (mechanism credited to prior art, not claimed novel); a measured, honest boundary of what that combination can and cannot hold accountable — plus a frozen 3.8B edge model producing a citation-faithful legal-reasoning note, on local hardware, with no cloud call and no retraining. |

---

## 3. Business KPIs (success in business terms)

| KPI | What it means to a city operator | Target / acceptance |
|---|---|---|
| **Emergency-vehicle delay** | How much faster a real ambulance clears the corridor | Reduced vs no-preemption baseline; reported with confidence intervals |
| **Spoofed-preemption resistance** | A fake emergency cannot commandeer the signal | Signed-but-uncorroborated emergency claims are refused; corroborated real emergencies are cleared |
| **No-harm guarantee** | Adding the coordination layer does not slow normal traffic | Defended-vs-undefended benign delta within the pre-registered margin (else reported honestly as overhead); the coordination traffic-flow effect itself is reported as a structural zero, not a headline benefit |
| **Accountability coverage** | How much of a stealthy deviation the layer can actually hold accountable, honestly bounded | The measured free-deviation boundary: which deviation classes the gate catches live or the log renders quorum+cross-audit-detectable, and which remain out of scope (colluding keys, operator omission, identity-root/quorum compromise) |
| **Safe degradation** | When a claim is untrusted, the corridor still functions | Automatic refusal + fallback to local control; no gridlock attributable to the defence |
| **Edge feasibility** | Runs on local hardware within a decision budget | Phi-4-mini median ~0.5 s/decision on Foundry Local; gated so a corridor stays within budget |
| **Auditability** | Every decision and identity change is reviewable after the fact | Signed, hash-chained, quorum-anchored (≥2 witnesses) log with a named cross-auditor; completeness is not the same as integrity, and this is stated |
| **SLM legal-reasoning quality** | Whether the on-device note cites the right rule for a novel fact pattern | Citation-correctness + false-citation-rate on novel combinations, vs an un-rigged rule-to-text baseline; a clean null is reported as honestly as a win |

---

## 4. Functional requirements (MVP)

1. **FR-1 Authenticated coordination channel.** Each junction signs (Ed25519) its neighbour messages; receivers verify against a permissioned key registry with revocation. Unsigned, forged, or revoked messages are rejected with a logged reason.
2. **FR-2 Plausibility check.** Each receiver reconciles a neighbour's claimed outflow against its observed inflow (vehicle conservation, CUSUM-monitored); a sustained inconsistency is flagged.
3. **FR-3 Deterministic emergency-preemption gate.** A real emergency vehicle, sensed locally, is granted preemption. A claimed emergency is granted preemption only if corroborated by independent physical sensing (≥2 keys); a signed-but-uncorroborated claim from a compromised insider is refused, defeating a spoofed claim even from an authenticated insider. A classical MaxPressure controller decides by default and enforces the safety envelope (min/max green, clearance, anti-starvation); the gate never lowers that floor.
4. **FR-4 Accountability log.** Every signed message, sighting, and decision is hash-chained into an append-only audit log; batches are anchored to a quorum of ≥2 external witnesses and reviewed by a named cross-auditor. Completeness is checked and reported; it is not conflated with integrity.
5. **FR-5 Evidence pack, split from any verdict.** A post-hoc incident review emits a mechanically-verifiable provenance evidence pack (verified sender key, chain/signature/quorum-completeness/cross-audit results, neutral cited-rule text) carrying no machine verdict, confidence, or accusation — plus a firewalled, non-evidential, counsel-gated internal AI note (the SLM's Job A), kept separate from the pack.
6. **FR-6 SLM legal-reasoning note (Job A).** Given a cryptographically-verified, quorum-complete audit window and the retrieved statute text, the frozen Phi-4-mini agent writes a citation-faithful note (candidate origin, cited rules, brief reasoning, fault-weight note); measured on citation-correctness and false-citation-rate on novel fact-combinations against an un-rigged rule-based baseline.
7. **FR-7 Safe fallback.** On a flagged or unresolved claim, the affected junction degrades to local control and the deterministic safety envelope, automatically (no human in the loop for real-time safety).

---

## 5. Technical requirements (non-functional)

| Area | Requirement |
|---|---|
| **Model** | Phi-4-mini (3.8B), frozen, inference-only, served by **Foundry Local** (no cloud, no fine-tuning); one per junction. |
| **Latency** | Real-time gate decisions are deterministic (no SLM in the control loop); the SLM's legal-reasoning note runs post-hoc over the verified audit window, budgeted to the measured ~0.5 s/call. |
| **Determinism** | Temperature-0; run-to-run agreement measured on the legal-reasoning prompts; decisions memoised by prompt-hash in evaluation. |
| **Identity** | Ed25519 keys per junction; permissioned registry with `revoke()`; constant-time verification; an external identity root signs the genesis key-to-entity binding. |
| **Safety envelope** | Hard min/max green, mandatory yellow + all-red clearance, anti-starvation bound (max_skip=3); enforced deterministically; an admissible emergency preemption outranks the anti-starvation shield, never the reverse. |
| **Accountability log** | Signed hash-chained AuditLog + a quorum external anchor (≥2 witnesses, e.g. a transparency log plus a named single-node ledger RPC) + a named cross-auditor. Completeness ≠ integrity, stated explicitly. |
| **Simulator** | Eclipse SUMO (microscopic; supports `vClass=emergency` and lane blockage). |
| **Reproducibility** | Pinned model hash, quantisation, Foundry version, decode params, and seeds; results reproducible from (config, seed, model-hash). |
| **Threat scope (in)** | Outsider forgery, network replay/reorder (within session), a single compromised-but-approved insider forcing an uncorroborated emergency-preemption claim. |
| **Threat scope (out, stated)** | Colluding keys (≥2); operator creation-time omission; identity-root/quorum/cross-auditor compromise; coverage below the phase-coupled threshold — all measured as the boundary, not defended. |

---

## 6. MVP scope

**In:** the deterministic real-time refusal/clearance gate on Foundry-local hardware; authenticated coordination with conservation/anomaly detection and measured precision/recall; a signed, hash-chained, quorum-anchored, cross-audited accountability log (mechanism credited to Certificate Transparency-style prior art); the live spoof-a-fake-emergency demonstration; one synthetic corridor (unit-test fixture only) + the real Euston Road (A501) corridor, benign and attacked, with full statistics; the self-referential-coupling measurement and its free-deviation boundary; the SLM's citation-faithful legal-reasoning note (Job A) as the primary SLM metric; honest performance reporting.

**Out (deliberately):** novel cryptography; a claim that the SLM beats the classical controller on routine traffic; a claim that the coordination layer optimises traffic flow (its effect is reported as a structural zero); RAG/retrieval (optional ablation only); a permissioned blockchain as the trust-path core (a cited prior-art anchor option only — a signed, quorum-anchored hash-chained log carries the claim); hardware-in-the-loop (named as future work).

---

## 7. Architecture (one diagram in words)

```
 default  -> MaxPressure controller (classical, throughput-optimal, microsecond)   [stays in charge; safety floor]
               | trigger fires? (EV sensed / advance claim / conservation anomaly / incident / conflicting-green)
               v
 gate     -> deterministic real-time gate: Ed25519 auth + registry + conservation/CUSUM + corroboration (>=2 keys)
               -> REFUSES signed-but-uncorroborated preemption; CLEARS physically-corroborated real emergencies
               v
            safety shield: min/max green, clearance, anti-starvation (never overridable by the SLM)
```
Every message, sighting, and decision is hash-chained into an AuditLog; batches are anchored to a quorum of external witnesses and reviewed by a named cross-auditor. Post-hoc, an incident review verifies chain + signatures + quorum-completeness + cross-audit, then emits (a) a mechanically-verifiable provenance evidence pack, no machine verdict, and (b) a firewalled, counsel-gated SLM legal-reasoning note (Job A) over the retrieved statute text. The SLM is never in the real-time control loop.

---

## 8. Milestones

| Milestone | Deliverable | Status |
|---|---|---|
| M1 Coordination substrate | Signed bus + registry + MaxPressure shield, 2-node clickable demo | Built |
| M2 Detection | Vehicle-conservation + CUSUM anomaly detector | Built |
| M3 Emergency gate + accountability | Deterministic refusal/clearance gate + corroboration; exploit-then-defend demo | Built (this session) |
| M4 Evaluation | Full demand sweep + real Euston Road (A501) corridor, benign + attacked, n=30, statistics; SLM Job A characterisation on anticipated and novel/unanticipated case splits | In progress |
| M5 Coupling measurement | The self-referential-coupling boundary: the one pre-registered coverage-vs-escape measurement on the real corridor | Planned |
| M6 Write-up | Dissertation + reproducibility package | Planned |

---

## 9. What we can and cannot claim (honesty boundary)

**Can claim:** a deterministic gate that refuses a signed-but-uncorroborated emergency-preemption claim and clears a physically-corroborated real emergency, running on local hardware with no cloud dependency and no retraining; message authenticity from a currently-approved member; a signed, quorum-anchored, cross-audited accountability log (mechanism credited to prior art, not claimed novel); a measured, honestly-bounded characterisation of the self-referential coupling between the attack lever and witness coverage; a fair exploit-then-defend showing a competent cooperative controller is compromised and our layer defends it; an honest, pre-committed account of the SLM's citation-correctness and false-citation-rate on novel legal fact-combinations, with a clean null reported as a valid finding.

**Cannot/do not claim:** novel cryptography or a novel accountability mechanism (Certificate Transparency-style accounting is prior art); that the SLM beats the classical controller on routine traffic; that the coordination layer optimises traffic flow (reported as a structural zero); that the log or the gate creates truth (it faithfully records and mechanically corroborates, it does not adjudicate veracity); which of two colluding, corroborating keys is the liar; defence against ≥2-key collusion, operator creation-time omission, or identity-root/quorum/cross-auditor compromise; absolute (vs in-simulator) traffic numbers; external validity beyond SUMO (future work: hardware-in-the-loop).
