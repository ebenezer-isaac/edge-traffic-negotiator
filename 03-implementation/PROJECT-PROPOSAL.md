# The Edge Negotiator: Canonical Project Proposal

**Status:** CANONICAL. This is the single source of truth for the project's direction, scope, novelty, and evaluation. It supersedes all earlier direction/planning docs (the prior `PROJECT-DECISION-BRIEF.md`, `SPECIFICATION.md`, `00-SCOPE-LOCKIN.md`, `SYSTEM-ARCHITECTURE.md`, `INTEGRATION-STATUS.md`, `DEMO-GUIDE.md`). Their content is consolidated here; their history remains in git.
**Authoritative companions (kept, not superseded):** `METHODOLOGY-AND-IMPLEMENTATION-DESIGN.md` (the build plan + edge-case register), `FORMAL-SPECIFICATION.md` (parameters, equations, metrics, data flow), `VERIFICATION-REPORT.md` (the 201-agent fact-check), and `06-literary-survey/` (the paper corpus). The earlier Jun 4-5 de-risk spike docs (Besu/QBFT/MQTT/threat-model/coordination-spec/de-risk-index) were removed from the working tree as superseded; their content is reflected here and their history remains in git.
**Last refined:** 2026-06-20, after a four-reviewer adversarial pass (novelty, methodology, threat-model, scope), a verified related-work survey, and a 201-agent citation/math/claims fact-check (see `VERIFICATION-REPORT.md`).

---

## In plain terms (read this first)

Traffic lights at neighbouring junctions increasingly coordinate (green waves, ambulance preemption). The moment they talk, a faulty or hijacked junction can lie, and a naive coordinator acts on the lie: wasted green, starved side streets, or a signal tricked into clearing the road for an ambulance that does not exist.

This project puts a small AI (Phi-4-mini, running locally, never retrained) at each junction. The junctions coordinate over a channel that is **digitally signed and sanity-checked**, on top of a classical controller (MaxPressure) that stays in charge by default and acts as a safety net. The real question is *not* "can the AI beat the classical controller on normal traffic" (it cannot, and we say so plainly) but: **when a neighbour's signed messages are compromised, does the system notice and degrade safely instead of believing the lie?** The headline experiment spoofs a fake emergency to grab green time, and shows the system refuses it because preemption is gated on *physical corroboration*, not on the signature alone.

Every specialist term below (MaxPressure, conservation check, CUSUM, BCa, GEH, and so on) is translated in plain language in [`GLOSSARY.md`](GLOSSARY.md).

## 1. One-line thesis

> A traffic-signal control system in which a deterministic MaxPressure controller is the default and safety shield, neighbouring junctions coordinate over an **authenticated, plausibility-checked** channel, and a frozen edge SLM is a guarded exception handler, evaluated for the first time as a **statistically-powered characterisation of how SLM-coordinated signal control degrades, and is defended, when the coordination channel is compromised.**

The headline contribution is **trustworthy degradation under authenticated-but-compromised coordination**, with a measured detection-and-safety envelope. Traffic-performance is a secondary, honestly-reported axis (floor + ceiling, Section 8), not the headline. The SLM is **load-bearing on one job a heuristic cannot do**: disambiguating a detector-flagged anomaly (a genuine incident needing escalation vs a spoofed emergency engineered to grab preemption) using cross-junction context, where a fixed per-junction rule has no basis to decide. It is not claimed to beat a heuristic at routine phase selection (it does not, and it is slower); it is deployed only on flagged-anomaly states.

---

## 2. Why this project direction (decision record)

Every row is a decision reached through analysis and adversarial review, with the reasoning that survived. This table exists so the direction is not relitigated and future work does not regress to a discarded option.

| Decision | Options considered | Chosen | Why (the reasoning that held) |
|---|---|---|---|
| Performance basis | SLM beats MaxPressure on normal flow; vs match; vs not a perf claim | **Not a headline perf claim** | MaxPressure is throughput-optimal and ~microsecond; our own ablation shows Phi-4-mini reproduces argmax 100% on the easy task and loses on the oversaturated grid. Racing the heuristic on its home turf is a dead end. |
| SLM role | Co-equal proposer (SLM proposes every tick); vs drop SLM; vs guarded exception handler | **Guarded exception handler** | Math-first: MaxPressure runs the predictable case; the SLM is invoked only on an anomaly/emergency trigger; the deterministic shield guarantees safety. Justifies the SLM without claiming it beats the heuristic. |
| Headline contribution | The crypto/integrity layer as-is; vs performance; vs robustness-under-compromise | **Robustness under compromised coordination** | Signing/ledger/audit alone are commodity composition. The real, unoccupied result is detecting and safely degrading under an *authenticated-but-lying* neighbour, the case signatures and blockchain cannot catch. |
| Ledger | Hyperledger Besu/QBFT in the trust path; vs signed hash-chained log | **Signed hash-chained log; blockchain demoted to a justified-or-not aside** | Governance is a single city-authority key, so there is one trust domain and no Byzantine setting. A tamper-evident append-only log gives the same property. A ledger is justified only with >=2 mutually-distrusting authorities; we say so. |
| Emergencies | Standalone "beat preemption on emergencies"; vs cut; vs fuse into the security story | **Fuse: spoof-a-fake-emergency** | Standalone emergency handling is precedented (VLMLight, LA-Light, EMVLight) and weakly novel. Spoofing a fake emergency to commandeer preemption fuses emergencies + coordination + security into one experiment that is genuinely ours. |
| Simulator | CityFlow (CoLLMLight's); vs SUMO | **SUMO** | Microscopic; supports emergency-vehicle dynamics (`vClass=emergency`, bluelight device) and lane blockage that CityFlow cannot. Also differentiates cleanly from CoLLMLight and explains why they did no emergencies. |
| Substrate | One synthetic headroom corridor; vs real Lambeth; vs both + sweep | **Both + full demand sweep, pre-registered** | A single hand-built headroom corridor invites selection-bias rejection. Pre-register the operating point against the green-wave literature and always report the full demand sweep and the real Lambeth arterial. |
| RAG / Qdrant | Core; vs nice-to-have | **Nice-to-have, cut first** | Highest-effort, lowest-certainty, most likely null; controller-mediated retrieval only, optional ablation, never load-bearing. SLM-driven MCP tool-calls rejected (3.8B tool-calling is unreliable). |
| Identity | DID/VC; vs Ed25519 + permissioned registry | **Ed25519 + permissioned registry + revoke** | Full DID/VC verification is heavier than needed for a single trust domain; `proofmember23` itself proposes a lighter membership proof because VC verification is costly on constrained nodes. A permissioned key registry suffices here; DID/VC is future work. |

---

## 3. Novelty (honest, reviewer-hardened)

**The claim that survives adversarial review:** to our knowledge no prior system evaluates an LLM/SLM-coordinated, multi-junction signal controller under a **signed-but-compromised coordination channel**, characterising where consistency-based detection works and where it provably collapses.

Each individual axis is precedented; the **conjunction plus the empirical security result** is the contribution, not new cryptography:
- The guarded fast-default / slow-LLM-exception architecture is **VLMLight** (arXiv:2505.19486). We extend it explicitly, citing it as prior art, to the multi-junction and adversarial-channel setting it does not address (it is evaluated single-intersection, with no inter-junction trust model; note its fast branch is RL-trained and it does handle emergencies at one junction, so our delta is the multi-junction + compromised-channel scope, not emergency handling per se).
- Multi-agent LLM neighbour coordination is **CoLLMLight** (arXiv:2503.11739). Its agents share neighbour state (read from a spatiotemporal graph, not signed messages) with no authentication or plausibility check, and it fine-tunes an 8B model; we authenticate and plausibility-check an explicit message channel with a frozen 3.8B model.
- LLM-as-emergency-exception-handler is **LA-Light** (arXiv:2403.08337), cloud GPT-4 on SUMO, tested up to an 18-intersection network, benign faults only (sensor outage, routine emergency); our faults are *adversarial and signed*.
- The closest *attack-detection on coordination* is **Keijzer2021** (arXiv:2104.03801), a control-theoretic sliding-mode-observer residual filter for collaborative intersection control. It does give formal (theorem-based) detectability conditions; our delta is an **empirically measured detectability envelope across an attacker-capability axis** (the recall-collapse boundary, Section 7), plus cryptographic identity and a tamper-evident audit it does not have.

**We do not claim** (these are commodity or precedented, and we say so): novel cryptography; that the SLM beats a heuristic at routine phase selection; that emergency handling itself is new; that a ledger creates trust. The "no-training edge SLM" is framed as a *constraint*, not a novelty (VLMLight also uses frozen local models).

---

## 4. Related-work comparison (for supervisor review)

Verified against arXiv and the local corpus; unverified items flagged. "Their gap" is stated honestly, including where overlap is real and narrow.

| Paper (arXiv, year) | What they propose | Model & size (training?) | Simulator & scenarios | Coordination? | Security/trust? | Why we don't adopt it / their gap | What we use instead |
|---|---|---|---|---|---|---|---|
| **CoLLMLight** (2503.11739, 2025) | Cooperative LLM agents share spatiotemporal neighbour state, network-wide | Llama-3.1-8B, **fine-tuned** (SFT on GPT-4o reasoning; repo adds a PPO refine stage) | CityFlow; Jinan/Hangzhou/NY, normal flow | **Yes** (closest coordination analogue) | **No** (trusts shared state) | No authentication/plausibility check on neighbour state; needs fine-tuning; 8B > our edge target | Frozen 3.8B; Ed25519-signed + registry-verified + conservation-checked coordination |
| **VLMLight** (2505.19486, 2025) | Fast classical path + slow LLM reasoning for safety-critical cases; AgentCheck gates LLM-proposed phases (falls back to RL) | Qwen2.5-VL-32B + Qwen2.5-72B (text); VLM/LLM inference-only, **RL branch trained**; server-class | SUMO (image wrapper); emergency scenarios (handles them) | Internal multi-agent dialogue, **not** inter-junction | **No** | 72B not edge; evaluated single-junction; no compromised-input model | Same dual-branch idea, 3.8B edge SLM + MaxPressure shield + signed inter-junction coordination |
| **LA-Light** (2403.08337, 2024) | Tool-using LLM calls RL/rule controllers for long-tail (sensor fail, emergency) | GPT-4 Turbo + tools, cloud, no FT | SUMO; isolated 3-/4-way + a real 18-intersection Shanghai net | **Yes** (multi-junction tested) | **No** | Cloud GPT-4, benign faults only, no trust model | Local frozen SLM exception handler; adversarial (signed-but-lying) faults |
| **iLLM-TSC** (2407.06025, 2024) | LLM verifier refines/overrides a PPO RL controller under degraded comms | GPT-4 + PPO, cloud | SUMO/TSHub; packet-loss + emergency | No | Comms **degradation** only, not malicious | Cloud; degraded != adversarial; single junction | Edge SLM override; malicious spoofed-message threat model |
| **LLMLight** (2312.16044, 2024) | LLM as the signal-control agent; fine-tuned LightGPT | GPT-3.5/4, Llama-2 7-70B; LightGPT **fine-tuned** | CityFlow; Jinan/Hangzhou/NY | No | **No** | Single-agent, no coordination/security, best results need FT | Frozen SLM; MaxPressure default; coordination + trust |
| **EMVLight** (2206.13441, 2022) | Decentralised MARL: emergency-vehicle routing + signal preemption | MA-A2C, **trained RL** | SUMO; EMV networks (-42.6% EMV time) | **Yes** (MARL) | **No** | Pure RL (must train); no reasoning over novel incidents; no trust | SLM handles open-ended incidents without retraining; baseline/ceiling reference |
| **REG-TSC** (2510.26242, 2025) | RAG-enhanced distributed LLM agents + emergency handling (83% EMV wait reduction) | Llama-3.1-8B **fine-tuned** (LoRA); GPT-4o-mini for trajectory collection | SUMO; Jinan/Hangzhou/Yizhuang (17-177 intersections) | **Yes** (distributed) | **No** | 8B + RAG dependency; fine-tuning needed; no compromised-input robustness | Frozen 3.8B; RAG optional; signed + conservation-checked |
| **CoLight** (1905.05717, 2019) | Graph-attention RL for cooperative network control | GAT-DQN, **trained RL** | CityFlow; Hangzhou/Jinan/NY-196 | **Yes** | **No** | No language reasoning/emergencies/trust; needs training | Baseline only; we add frozen-SLM reasoning + security |
| **MaxPressure** (Varaiya 2013; no arXiv) | Provably throughput-maximising pressure control (full rule weights movements by saturation flow + turning ratios) | Analytical rule, no training | Reimplemented in SUMO/CityFlow | Local pressure (implicitly cooperative) | **No** | Not a competitor: it is our default + shield. We implement the simplified halting-count form `Σ(n_in−n_out)`, not the saturation-flow-weighted rule | Adopted directly as default + deterministic shield |
| **SafeLight** (2211.10871, 2023) | Safety-enhanced residual RL (3DQN) + a rule-based safety override (from the Federal timing manual) | Residual RL, **trained** | SUMO; synthetic + Cologne intersections | No | Safety override, **no** adversarial model | Needs training; no spoofed-input defence (it already has a deterministic safety layer, so our delta is the adversarial-trust story, not "we add a shield") | Deterministic shield (no training) for action safety; trust handled separately |
| **Blockchain-TSC** (1906.02628, 2019) | Blockchain validates connected-vehicle data vs spoofing | No model | I-SIG/CV pilot | No signal coordination | **Yes** (vehicle-data) | Permissioned (Hyperledger Fabric) consensus, still heavier than needed; no SLM; secures vehicle->signal, not signal<->signal | Lightweight hash-chained audit + Ed25519 vs permissioned registry |
| **proofmember23** (2310.08163, 2023) | DIDs + proof-of-membership to bootstrap IoT node trust | No model | Conceptual/IoT | No | **Yes** (identity) | Not traffic; no content plausibility check | Permissioned registry of keys + signature verify + conservation check on content |
| **Derhab2020** (Sensors 2020; no arXiv) | Relaxed flow-conservation to detect selective-routing attacks in WSNs | No model | WSN sim | Two-hop monitoring | **Yes** (flow-conservation) | Domain is sensor-network routing, not vehicle flow | We port flow-conservation to **vehicle** conservation across junctions |
| **Keijzer2021** (2104.03801, 2021) | Model-based (sliding-mode-observer) residual detection of attacks in collaborative intersection control | Observer/residual, no LLM | Single-intersection V2V sim | **Yes** (V2V) | **Yes** (attack detection) | Control-theoretic filter with formal detectability theorems but no empirical capability sweep; no SLM/identity/audit | Conservation check (lighter) + empirical detectability envelope + signatures + registry + audit |

**Positioning summary.** The unoccupied gap is the conjunction: a frozen no-training edge SLM as a guarded exception handler over a MaxPressure default+shield, where inter-junction coordination is cryptographically authenticated and screened by a vehicle-conservation plausibility check, evaluated in SUMO under a compromised channel. The three closest threats are CoLLMLight (same coordination, but trusts shared state, fine-tunes), VLMLight (same dual-branch safety architecture, but 72B and no trust), LA-Light (same exception-handler role, but cloud and benign faults). The honest bound, stated from first principles: a conservation check can only flag a residual that leaves the plausibility band, so our layer stops unauthenticated spoofing and gross/supra-tolerance faults, but not a key-holding adversary (or ≥2-key collusion) that crafts conservation-respecting injections inside the band; that case is contained by revoke + audit, not detection.

---

## 5. Architecture

**Tiered control (heuristic-first, AI-guarded), with two unifications.**

```
 default ─▶ MaxPressure (+ predictive green-wave coordination)   ← runs the predictable case; fast; throughput-optimal
              │  trigger fires? (conservation anomaly / emergency vehicle / incident / abnormal demand)
              ▼
 escalate ─▶ frozen SLM exception handler ──proposes──▶ deterministic shield validates / can override
              (invoked rarely, only on trigger)                  (safety envelope: min/max green, all-red clearance, anti-starvation)
```

- **Fast path (real-time):** junction A signs (Ed25519) a neighbour message carrying its release toward B; B verifies it against the permissioned registry and screens it with the conservation check before it can influence any decision; event-gated.
- **Trust path (async):** permissioned registry of approved identities with `revoke()`; vehicle-conservation reconciliation (claimed outflow vs observed inflow, adaptive band + CUSUM persistence); tamper-evident hash-chained audit log that anchors signed-message hashes (so an insider's lies are attributable to its key by an external auditor).

**Two unifications (the coherence of the project):**
1. The same signed `release` messages serve both integrity (conservation reconciliation) and coordination (timed platoon arrival for green-wave pre-positioning).
2. The conservation/anomaly detector that catches spoof/fault is **also** the trigger that escalates to the SLM, and the SLM's job on escalation is precisely to **disambiguate the flag**: a fixed rule cannot tell a genuine incident from a spoofed emergency, but the SLM can weigh cross-junction context (do neighbours corroborate the incident? is the claimed emergency physically consistent?) to decide whether to grant preemption or reject it. This is the one decision where the SLM is load-bearing; integrity and the AI-guard reinforce each other.

**Safety envelope (deterministic, independent of the SLM):** hard min/max green and mandatory yellow + all-red clearance on every transition (structural in the controller's `step()`, already built), plus an **anti-starvation override to be added to the shield** (track each approach's last-served tick; if any approach is skipped beyond `max_skip` decisions the shield forces it next cycle, an active emergency deferring it by at most one min-green+yellow). The shield clamps to this envelope; the SLM can never violate it. This is the formal safety claim, stronger than "MaxPressure vetoes invalid phases." Anti-starvation is the one envelope component not yet in the shield code path: it is a MUST build item with an `anti_starvation_violations` KPI.

---

## 6. Threat model (explicit)

**Attacker tiers (we state which we defend):**
1. **Outsider** (no key): forges/injects unsigned messages. Defended (auth rejects).
2. **Network adversary** (no key): observe/drop/reorder/replay on the wire. Replay is defended **within a session** (the bus dedupes `(recipient, sender, t)`); cross-restart monotonic persistence is a small, scoped change to the message bus (a persisted per-sender high-water-mark), flagged as a build item, not yet shipped. Drop/withhold is reconciled via silent-neighbour expectation.
3. **Single compromised insider** (one approved key): may lie within tolerance (undetected, stated), lie above tolerance (detected as an edge anomaly), or assert a fake emergency (the headline attack). Defended in the supra-tolerance and fake-emergency cases; the conservation check flags the edge, not the culprit (operational response: audit + revoke, with a guard against detector-driven DoS of an honest node).
4. **Colluding insiders (>=2 keys), conservation-respecting:** explicitly **out of scope**. By construction the colluders keep the mass-balance residual inside the band (one over-claims, another supplies a matching fake observation), so it is statistically indistinguishable from benign traffic and recall → 0. Contained by `revoke` + audit, not detection.
5. **Compromised admin/root key:** out of scope; the single point of total failure, stated plainly.

**Trust assumptions:** one honest city authority, one admin key (not compromised); registry is ground truth; per-junction private keys not exfiltrated; sensors honest-but-faulty (faults modelled; spoofing is the tier-3 case); clocks loosely synchronised (required for the replay window). Two further guards are **build items, not yet shipped**: a per-edge cap on consecutive spillback windows (added in the controller's reconcile loop, which is not frozen) that forces a reconciliation window through the CUSUM so an attacker cannot mask indefinitely behind the spillback classification; and a pre-verification payload size/field-count/depth bound so a valid insider cannot send an oversized signed payload. The detector flags an edge, not a culprit, so revocation is gated behind an **audit-before-revoke** policy with a per-neighbour flag-rate metric, preventing a forced flag from being weaponised to revoke an honest node.

---

## 7. The headline experiment: exploit, then defend (made fair)

The reviewer concern that "breaking an unauthenticated system is trivial" is addressed directly:

- **Victim baseline:** a cooperative controller **representative of the trust-everything class that CoLLMLight exemplifies** (CoLLMLight itself shares neighbour state via a graph rather than signed messages; we model the same trust assumption over an explicit message channel, which is the attack surface that class implicitly trusts). It is identical to our defended system **except** it omits signing, registry, and the conservation check, and is tuned to be **good in the benign case**. The defended-vs-victim benign delta is a **pre-registered acceptance criterion** (must be within the MDE / non-significant), and if the integrity layer's overhead does regress benign flow, that is itself a reported negative result rather than an assumed tie.
- **Adversary:** a single compromised-but-approved neighbour (tier 3), not an outsider. Attacks: (a) a signed over-claim/under-claim of release; (b) a **spoofed fake emergency** to commandeer preemption; (c) a within-tolerance/partial lie that the signed system must still reason about.
- **Break:** quantify the victim's degradation (network delay, wasted green on false preemption, induced gridlock, emergency-vehicle delay).
- **Defend:** signing blocks impersonation/replay; the conservation check (run through the **CUSUM detector we actually ship**, `flow_conservation.py`, not only the stateless checker) detects the inconsistency and the system **autonomously falls back to local MaxPressure on the flagged edge** (no human in the loop; we measure the traffic cost of this automatic degradation). On a flagged *emergency* claim specifically, the SLM disambiguates real-vs-spoofed using cross-junction context before any preemption is granted.
- **Scientific object:** a **detectability envelope**, operationalised as a *lie-magnitude sweep*: the spoofer's over-claim is parameterised as multiples of the live adaptive band (e.g. 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0x band), x30 seeds, and we plot recall and detection latency vs band-multiple. The **recall-collapse knee is the result** (where sub-tolerance lies evade), with collusion (recall=0) and spillback-masking marked as the bounding zeros, and benign false-alarm/false-preemption rate reported next to every recall number. This replaces the tautological "we detect supra-tolerance lies" with a measured boundary.
- **Scope:** the exploit-then-defend result is demonstrated on the synthetic corridor (clean edge ids, known ground truth); the same on the real Lambeth net uses the already-built injected `edge_map` path and is reported as a robustness check, not part of the 30-seed headline matrix.

---

## 8. Evaluation

**Baseline ladder:** fixed-time → MaxPressure → MaxPressure + tuned rule-based preemption (the strong non-AI emergency floor) → naive cooperative SLM (the fair victim) → the defended SLM system. An RL reference (CoLight/EMVLight-style, trained offline in SUMO; training is allowed for *baselines*, only the deployed SLM is inference-only) is included as a **ceiling reference**, not a bar we must beat.

**Performance, two-pronged and honest:**
- **Floor (reliable):** deterministic predictive coordination beats *vanilla* MaxPressure on delay where headroom exists (green-wave regime, literature-backed).
- **Ceiling (the bet, reported including nulls):** on **detector-flagged anomaly states** (the one place the SLM is load-bearing, Section 5), does the frozen SLM disambiguate real-vs-spoofed emergencies and reduce false-preemption / improve incident response versus the tuned rule, which cannot use cross-junction context? Answered by a **decision-attribution breakdown** (agree / disagree-better / disagree-worse / shield-vetoed) on flagged-anomaly states where rule and SLM disagree, plus a curated hard-state micro-benchmark with known-correct escalations. A clean powered null here is a *scoped, informative* result ("fixed rules suffice for spoofed-emergency disambiguation, bounding where edge reasoning helps"), not an excuse: the SLM is structurally central to this question, so the answer is a finding either way.
- **Safety floor:** the guarded system never regresses normal flow vs MaxPressure (shield guarantee), measured.

**Selection-bias controls:** pre-register the corridor topology and operating point against the green-wave literature; always report the **full demand sweep** (scale 0.3->3.0) for every controller and the **real Lambeth arterial**, not only the synthetic corridor. Lambeth controls topology/selection bias only; its demand is synthetic-calibrated, so this is not an external-validity claim (Section 11).

**Determinism + reproducibility:** measure SLM temp-0 run-to-run agreement (N=100) on the **emergency/triggered prompts specifically** (longer and context-laden, where determinism is least guaranteed; the existing 100%-agreement evidence is only for the short phase-selection prompt), reported separately; only then memoise SLM decisions by prompt-hash for the eval so traffic variance is isolated from model variance; run the **real-SLM eval at n=30** (the StubAgent path structurally cannot show the effect; n=4 is underpowered); pin model hash, quantisation, Foundry version, decode params, seeds.

**Statistics:** BCa bootstrap + paired permutation + Holm, paired on seed (existing stack). Pre-register the primary metric family; report effect sizes with CIs as the headline and p-values as support; state the minimum detectable effect so a null is "below MDE = X," not ambiguous. Emergency vehicles treated as a clustered unit (random effect per seed), with enough injections per seed for meaningful n.

**KPIs.** Detection: precision/recall/F1, detection latency (cycles), false-alarm and false-preemption rate under benign jitter. Safety: shield veto rate, anti-starvation compliance, safe-but-suboptimal rate. Traffic (survivorship-safe, full-population tripinfo): mean network delay, completion rate, throughput, matched-set travel time; emergency AETT/AEWT with non-completion penalised and emergency completion rate; incident recovery time with a pre-registered censoring rule. Integrity overhead: sign/verify latency, ledger-vs-signed-log comparison.

---

## 9. Scope: MUST / SHOULD / NICE

**MUST (minimum viable defensible thesis; ~70% of this MUST list is already built):** Ed25519 + registry + revoke; conservation/CUSUM detector + powered detection P/R/F1/latency; hash-chained audit anchoring message hashes; deterministic safety envelope + shield no-regression result; the **live attack demonstration** (M-6, the "shown not asserted" linchpin); one real corridor + one synthetic corridor, benign + attacked, n=30, full stats; the detectability-envelope figure; honest write-up of the performance result whatever it is.

**SHOULD:** predictive-coordination floor + the causal-coordination demonstration (Channel decision resolved); real-SLM n=30 ceiling run with decision-attribution; detection operating-envelope sensitivity analysis. (The fused spoof-a-fake-emergency experiment is the §7 headline and is therefore a MUST, via M-6 above; it is not a SHOULD.)

**NICE (cut first, in order):** RAG/Qdrant experience store; extra emergency scenarios beyond the fused one; multi-model (Qwen) ablation; live Besu/QBFT in the eval loop (keep async/characterised); scaling beyond the corridor (appendix).

---

## 10. Risks and edge cases

Full handling in `METHODOLOGY-AND-IMPLEMENTATION-DESIGN.md` (18-item register). Top risks: (1) frozen 3.8B fails the hard cases: mitigated by framing the shield-veto as a safety result and accepting a powered null; (2) real-SLM n=30 wall-clock: start it in the background early, reduce matrix breadth before seed count; (3) headroom-corridor selection bias: full sweep + real corridor + pre-registration; (4) coordination causally inert (the prior `coord_changed` was discarded): the escalated proposal must be the executed candidate, proven via an `escalation_changed_decisions` metric + CI regression guard; (5) silent edge-id no-op on real nets: explicit injected edge map + fail-loud startup assertion; (6) SLM nondeterminism: measure agreement on the emergency prompts, then memoise by prompt-hash; (7) Foundry serialisation: gate SLM on the trigger, cap SLM junctions, keep the StubAgent CI path; (8) detector weaponisation (force a flag to revoke an honest node): edge-level flag with audit-before-revoke policy + per-neighbour flag-rate metric; (9) anti-starvation not yet in the shield: add the deterministic last-served-tick override (MUST); (10) replay only within-session: add a persisted per-sender high-water-mark; (11) spillback-masking: cap consecutive spillback windows in the non-frozen reconcile loop to force a CUSUM window; (12) tautological detectability figure: the lie-magnitude sweep (MUST) supplies the x-axis.

---

## 11. Claims vs non-claims (the honesty boundary)

**We can claim:** message authenticity from a currently-approved member; tamper-evident, externally-auditable registration/revocation + decision/message log; detection of inconsistent (uncoordinated-spoof or faulty) neighbour reports with a measured envelope; a deterministic safety guarantee; a fair exploit-then-defend showing a competent cooperative controller is compromised and our layer defends it; an honest characterisation of whether a frozen edge SLM adds value on contested states.

**We cannot/do not claim:** novel cryptography; that the blockchain creates trust or prevents lying (it records garbage faithfully); that the SLM beats a heuristic at routine phase selection; incentive-compatibility; which of two disagreeing junctions is the liar; defence against conservation-respecting collusion or a compromised admin key; absolute (vs relative-in-simulator) traffic numbers; external validity beyond SUMO (named as future work: hardware-in-the-loop).
