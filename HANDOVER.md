> **Onboarding / handover doc, reframed to the current thesis at the 2026-07 cutover.** The single source of truth is `specs/001-edge-negotiator/MASTER-SPEC.md`; where anything here conflicts with it, the MASTER-SPEC governs. This doc is a fresh-session orientation aid, not an authority. (History: it predates the 2026-05-31 pivot and once described an equity-audit / CoT-faithfulness project and a Lambeth/Besu build; both are dropped, see the MASTER-SPEC.)

# Handover prompt — Edge Negotiator dissertation, fresh-session onboarding

Paste this verbatim into a new Claude Code (or other agent) session in this repo. It is self-contained: a fresh agent reading it has enough to continue without re-deriving prior decisions. On any conflict, defer to `specs/001-edge-negotiator/MASTER-SPEC.md`.

---

## Who I am and what I am doing

I am the UCL MSc Systems Engineering for IoT student writing the Edge Negotiator dissertation, supervised by Dr Akin Delibasi (UCL) and Lee Stott (Microsoft, Foundry Local / Phi-4).

The project is **an on-device, trust-preserving coordination layer for signalised junctions, plus a measured characterisation of exactly which stealthy insider deviations it can and cannot hold accountable.** It is evaluated in **Eclipse SUMO on the real Euston Road (A501) corridor, a 3-4 signal stretch in central London** (the synthetic 2x2 grid is a unit-test fixture only). One frozen small language model, **Phi-4-mini (3.8B) via Microsoft Foundry Local, one per junction**, sits over the coordination layer. A deterministic **MaxPressure controller is the default and safety shield**; the SLM is invoked only on an anomaly/emergency trigger and separately writes a citation-faithful legal-reasoning note over the audit record.

The one question the work answers: *in a compromised-insider emergency, what can be held accountable mechanically, and what remains a human/counsel judgment that even an on-device reasoner cannot faithfully automate?* Three contributions:

1. **A deterministic real-time gate** that refuses a signed-but-uncorroborated emergency preemption from a compromised insider, and clears physically-corroborated real emergencies.
2. **A Certificate-Transparency-style, quorum-anchored, cross-audited, signature-verified accountability log.** The mechanism is **credited to prior art (RFC 6962, CONIKS, A2M, TrInc, PeerReview, Küsters), cited, and NOT claimed novel.** It records garbage faithfully; non-repudiation is not truthfulness.
3. **The novel object: a self-referential coupling.** The preemption attack controls the signal phase, which is also the variable that gates honest-witness coverage, so executing the attack opens the very coverage desert that conceals it. Stated as a conditional lemma under explicit hypotheses, with one severe, pre-registered measurement of its boundary on the real Euston corridor. The honest boundary, not an unconditional guarantee, is the finding.

The SLM is a **self-contained co-equal contribution, not the instrument of the boundary map** (scored origins are decided by mechanical provenance predicates). Job A: a citation-faithful legal-reasoning note, scored on citation-correctness and false-citation-rate on novel legal fact-combinations against an un-rigged rule-to-text template. Job B: a guarded disambiguation classifier. Job C: a frozen-vs-hardened robustness/adaptivity tradeoff. A pre-committed kill-criterion may demote the *claim*, never the SLM's presence. No traffic-performance claim: the coordination effect is reported as an inert structural zero.

## Read these before doing anything

In strict order:

1. **`specs/001-edge-negotiator/MASTER-SPEC.md`** — **THE single source of truth.** Direction, scope, threat model, the free-deviation boundary, the acceptance-test gates (§12), and the framing every other doc conforms to.
2. **`03-implementation/PROJECT-PROPOSAL.md`** and **`03-implementation/FORMAL-SPECIFICATION.md`** — the earlier proposal (reasoning + related work) and the parameter/algorithm/metric reference. Both conformed to the current thesis; MASTER-SPEC governs on conflict.
3. **`03-implementation/METHODOLOGY-AND-IMPLEMENTATION-DESIGN.md`** — the build plan + edge-case register.
4. **`C:\Users\Ebenezer\.claude\projects\e--assignments-edge-traffic-negotiator\memory\MEMORY.md`** — index to the memory entries; skim for orientation.
5. **`06-literary-survey/INDEX.md`** — map of the literature survey grounding the related-work positioning.

## Where the project is right now

- **Direction locked** to the current thesis (self-referential coupling + measured characterisation; accountability mechanism credited to prior art; Euston A501 substrate; Phi-4-mini).
- **Substrate:** real Euston Road (A501) corridor for the headline measurement; the synthetic 2x2 grid is a unit-test fixture and deterministic-gate demo only.
- **~70% of the MUST scope is built** (Ed25519 + registry + revoke, MessageBus with auth+replay, FlowWindow, the conservation/CUSUM detector, traffic metrics, the stats stack, the evaluation harness, identity/registry, and the anchor spikes demoted to the cited-prior-art option). The MUST build items are the `EmergencyController` + deterministic shield (anti-starvation `max_skip=3`, corroboration gate, pressure floor), the signed EV sighting log, the five trigger evaluators, `emergency_metrics`, the `cooperative_naive` victim, the live attack injectors, and the free-deviation-boundary sweep.
- The Euston net (`euston_spine.net.xml`) is a **pending artifact** (needs `netconvert` on the target machine); the corridor runners are wired to it and marked PENDING until it exists.

**Next concrete step — one of:**
1. Build the pending `euston_spine.net.xml` from an OSM extract of the A501 corridor, then wire the corridor runners against it; or
2. Land a MUST build item (the `EmergencyController` + deterministic shield, or the live attack injectors + free-deviation-boundary sweep).

## Hard rules for any agent picking this up

- **Build on `sumo-rl`** (MIT, arbitrary nets). **Do NOT build on CoLLMLight/CityFlow** — CoLLMLight is welded to CityFlow; treat it as reference only and reimplement the neighbour-message algorithm, do not port the code.
- **Phi-4-mini is the ONLY model.** No multi-model ablation; the old Qwen option is dropped.
- **The SLM is a frozen, guarded exception handler**, invoked only on a trigger, always validatable/overridable by the deterministic shield. Its reasoning lives in the firewalled, counsel-gated internal note, validated against cited statute and never trusted. Do not request or rely on chain-of-thought as an accountability mechanism; accountability comes from the signed log.
- **Fault output is SPLIT and the two channels are never merged.** (1) A mechanically-verifiable provenance evidence pack: only reproducible facts (verified sender key, chain/signature/quorum/cross-audit results, which corroboration checks failed, neutral cited-rule text). It carries **no machine verdict, no confidence, no accusation, no "attacker"/"lie" label**; header "Provenance record; not a determination of legal fault." (2) A firewalled, non-evidential, counsel-gated internal AI triage note; where the origin is a signing party it names a **key, never a person**.
- **Identity = Ed25519 + a permissioned key registry + `revoke()`.** The accountability log is a signed hash-chained AuditLog anchored to a quorum of independent witnesses and read by a named cross-auditor. **Do NOT foreground a blockchain/Besu as the contribution** — a full consensus ledger is justified only with >=2 mutually-distrusting authorities; it is demoted to a cited-prior-art anchor option. The word "ledger" is fine for the signed hash-chained AuditLog.
- **Deterministic MaxPressure shield** validates or overrides every SLM decision and runs alone at quiet junctions; anti-starvation `max_skip=3` (pinned); an admissible (corroborated) emergency preemption outranks the anti-starvation shield.
- **Make only honest claims.** Claim message authenticity, tamper-evident auditability, detection of inconsistent neighbour reports with a measured boundary, a deterministic safety guarantee, and an honest characterisation of the SLM's value. Do NOT claim novel cryptography, a novel accountability mechanism (it is Certificate Transparency), that the log creates trust, that the SLM beats a heuristic at routine phase selection, or any traffic-performance benefit. Concede the boundary: a conservation-respecting insider inside the band, and >=2-key collusion, evade detection and are contained by revoke + audit, not detection.
- **UK legal framing** (RTA 1988 s.36/s.38, GDPR/DPA 2018, Goodes/Gorringe). Do not invoke the EU AI Act except when quoting cited prior art.
- **Honour the India 90-day Study Away constraint.** The SUMO-on-laptop substrate was chosen partly to be London-resource-independent; keep it so.

## How to confirm you have the picture

Before taking any action, reply with a one-paragraph summary stating: (1) the thesis — an on-device trust-preserving coordination layer **plus a measured characterisation** of which stealthy insider deviations it can and cannot hold accountable, with the self-referential coupling as the novel object; (2) the model — **Phi-4-mini** via Foundry Local, frozen, a co-equal contribution, not the instrument of the boundary map; (3) the accountability mechanism — a **CT-style, quorum-anchored, cross-audited, Ed25519-signed log credited to prior art**, plus the permissioned key registry and the vehicle-conservation check; (4) the fault output — a **split provenance evidence pack (no verdict) firewalled from a counsel-gated internal note**; (5) the substrate — the **real Euston Road (A501)** corridor, synthetic grid as a fixture only; (6) the next deliverable — the pending `euston_spine.net.xml` build or a MUST build item. If your summary contradicts `specs/001-edge-negotiator/MASTER-SPEC.md`, re-read that spec before acting.
