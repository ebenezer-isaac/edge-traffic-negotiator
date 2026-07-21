# The Edge Negotiator: Master Build & Experiment Specification

**Status**: CANONICAL, frozen. Supersedes conflicting framings elsewhere. Created 2026-07-16 after a 10-agent adversarial teardown (academic, methods, security, business, legal, build + 4 sadist re-passes). This is the single document an autonomous builder (Fable) works from overnight. Where any other doc disagrees with this one, THIS wins and the other must be corrected or quarantined.

**Golden rule for the builder**: fail loud, never degrade silently. A run that cannot prove the real model answered, the corpus was retrieved, the edges resolved, and the signatures verified MUST abort, not emit green tables. A fake-green null is worse than a crash. This project has already produced fake nulls once (every prior "result" came from a deterministic stub); it must not happen again.

---

## 0. Why this rewrite exists (the teardown verdict)

Ten reviewers independently converged: the honest engineering core is real and defensible, but the written record reads as three different projects, the named novelty (SLM) was never validly measured, "coordination" is causally inert, and the accountability layer verifies no cryptography and is not wired to the log it claims to prove things over. The fixes are mechanical and known. This spec encodes them.

**Non-negotiable constraints (user-set, do not relitigate):**
- The SLM is a REQUIRED component of the thesis. It stays. (Its *job* is redefined below so it is load-bearing and honestly measurable.)
- Substrate is a real recognisable London road: **Euston Road (A501)**, a short 3-4 signal stretch, greenfield cutover from the synthetic corridor.
- Fault rules are grounded in real UK law (`01-research/uk-traffic-law.md`), cited, never invented.
- Deadline August 2026; scope is not cut, it is phased (honest overnight subset first, then deepen).

---

## 1. The ONE thesis (frozen)

> **The Edge Negotiator is an on-device, trust-preserving coordination layer for signalised junctions that (a) refuses signed-but-uncorroborated emergency-preemption claims from a compromised insider while still clearing physically corroborated real emergencies, (b) binds every control decision non-repudiably to a signing key in a tamper-evident, externally-anchored log, (c) produces, via a frozen on-device SLM reasoning over retrieved UK-law policy, a human-readable, rule-cited EVIDENCE PACK that supports (never replaces) a human/court fault inquiry, and (d) reports a measured envelope of where consistency-based detection holds and where it provably collapses.**

**The novel, defensible object** (lead with this): the **measured detectability-and-containment envelope** (recall/latency vs lie-magnitude, with the false-preemption cost of tightening the band) plus the **SLM-generated auditable evidence pack**. Not "the SLM beats a rule," not "coordination optimises traffic."

**What every doc must DROP (from the teardown):**
- "prove fault", "verdict", "who was at fault" as a determination → replace with "evidence pack / candidate attribution, for human review."
- "blockchain" as a headline / "decentralised" / Iroha → it is a signed hash-chained log with an optional Besu/QBFT anchor, single trust domain.
- EU AI Act as a UK legal mandate → it does not apply in the UK; cite it only as a voluntary governance benchmark.
- "coordination clears emergencies" as a measured claim → coordination is currently inert (B1); either made causal and re-measured or reported as a negative result.
- "the SLM is the load-bearing defence" → the deterministic conservation+corroboration gate is load-bearing; the SLM is load-bearing on the EXPLANATION/evidence axis (§3).
- Traffic-R1 must be confronted in related work (a 3B production TSC model exists; our differentiator is frozen/inspectable/no-poisoning-surface + the trust layer, not raw TSC skill).

---

## 2. Single Source of Truth (freeze; every doc must conform)

| Item | Frozen value |
|---|---|
| Headline | Trust-preserving on-device coordination for emergency response + auditable evidence pack; SLM characterised, not claimed to beat the rule |
| SLM role | Load-bearing on EXPLANATION (evidence-pack reasoning + UK-law citation); characterised (honestly) on disambiguation; NOT the load-bearing defence |
| Load-bearing defence | Deterministic Ed25519 auth + conservation/CUSUM + corroboration gate |
| Model | Phi-4-mini, 3.8B, frozen, Microsoft Foundry Local |
| Deploy target | Foundry Local in SUMO simulation; Jetson/INT4 = future hardware-in-loop only |
| Ledger | Signed hash-chained `AuditLog` (built); Besu/QBFT = demoted, optional async anchor; single city authority, one admin key, permissioned registry |
| CoT / reasoning | SLM DOES emit a structured reasoning trace (needed for the evidence pack + auditability); it is NOT trusted as truth, it is VALIDATED for faithfulness against cited policies. Raise `max_tokens`. |
| Fault attribution meaning | key / classifier / detector origin over the audit log (built) + a UK-law citation layer (§7); attributes to a KEY, never a person |
| Fault → human? | "attributes to a signing key", never "human"; rename the `HUMAN_VS_AI` map to `ORIGIN` (attacker-key / system-classifier / system-detector / sensor-fed-spoof / legitimate / unknown) |
| RAG | policy text retrieved into the prompt from `ground_rules.yaml` + `uk-traffic-law.md`; small curated corpus; fail-loud if empty; not the Qdrant experience-store |
| Emergency SLM wiring | withhold-only disambiguator on advance claims; can never ADD preemption |
| Coordination effect | measured as `defended - maxpressure_preempt`, per scale, with CI; reported honestly (currently inert/negative) |
| Seeds | n=30 required for any inferential claim; current exp1(n=1)/exp2(n=3) are pilots, labelled as such until re-run |
| Determinism | N=100 across restarts; reps=2 is a pilot |
| EV benefit (n=30) | 31.1 s [25.4, 36.5] (preemption-on vs off; NOT a coordination or SLM result) |
| Gate cost | 8.0 s [3.7, 12.5] |
| Worst-case harm avoided | 16.05 s [11.51, 20.44] |
| STSD coursework | superseded earlier framing; quarantine with a banner, do not cite as current |

---

## 3. The SLM's mandatory role (reconciled: load-bearing on explanation, honestly characterised on classification)

The SLM has TWO jobs. Neither requires it to beat the rule.

**Job A (load-bearing, the contribution): the evidence-pack reasoner.** On a flagged incident, the SLM is given the audit trail for the window + the retrieved applicable UK-law/policy records, and emits a structured, auditable assessment:
```
{ "candidate_attribution": "driver" | "signal_authority" | "emergency_vehicle" | "attacker_key" | "unknown",
  "cited_rules": ["RTA1988-s36", "TSRGD2016-Sch14-Pt1-para5(3)", ...],   // ids from uk-traffic-law.md
  "reasoning": "<=120 words linking evidence to the cited rules>",
  "fault_weight": "hard_law" | "advisory",                              // MUST-rule vs should-rule
  "confidence": 0.0-1.0,
  "disclaimer": "candidate attribution for human review; not a legal determination" }
```
This is what a fixed rule cannot do well (natural-language reasoning over statute + novel fact combinations) and it IS the auditability thesis (STSD Code 1). Measured on: **citation-correctness** (are the cited rules the applicable ones, checkable against the KB), **faithfulness** (does the attribution follow from the cited rules, checkable by a rule oracle), and **agreement with a blind human/legal gold standard** (Cohen's kappa). Win or lose, it is a real characterisation.

**Job B (honestly characterised): the disambiguation classifier.** The real-vs-spoofed classification on flagged ambiguous cases, run under the rigorous protocol in §8 (dev/test split, no leaked threshold, n>=30, CIs, MDE, vs the tuned rule). Reported either way including a genuine (powered) null.

**Resolves the CoT contradiction (F3):** we DO emit reasoning (auditability needs it) but we never trust it, we validate it against cited policy. Raise `SLMAgent.max_tokens` to fit the structured output; drop the "no reasoning" stance from `slm_agent.py`; drop the conflicting bare-decision prompt.

---

## 4. Architecture (the honest, wired version)

```
default -> MaxPressure (+ optional coordination term, currently advisory/inert -> §5 B1)   safety floor
   trigger fires (EV sensed | advance claim | conservation anomaly | incident)
      -> deterministic gate (auth + corroboration + conservation)      <- LOAD-BEARING defence
           advance-claim ambiguous middle -> SLM/rule disambiguator (withhold-only)  Job B
      -> shield validates (min/max green, clearance, ANTI-STARVATION)   safety invariants
   every decision + every message -> AuditLog (signed, hash-chained, anchored)
   incident detected (collision | hard-brake | conflicting-green) -> fault_attribution
           -> retrieve UK-law policy -> SLM evidence-pack reasoner       Job A
```

---

## 5. Consistency remediation (D1 — do this FIRST, it gates everything)

1. **Quarantine `STSD/coursework.md`**: add a top banner "SUPERSEDED earlier framing (decentralised blockchain optimisation); retained for history; see specs/001-edge-negotiator/MASTER-SPEC.md for the current project." Do not cite it as current.
2. **Fix the fatal self-contradictions** per the §2 table across PROJECT-PROPOSAL, DEMO-REPORT, spec.md, TEST-AUDIT-FAULT-SPEC, GROUND-RULES, FORMAL-SPEC, LEE/AKIN docs, PROJECT-STATUS-AND-PLAN:
   - DEMO-REPORT: strike "Phi-4-mini produced this"; state StubAgent + deterministic gate. Remove the "single-seed, no CIs" framing that contradicts its own n=30 table; present n=30 as the result, single-seed as an aside; quote only powered means (8s/16s/4.63s), move 11s/49s/45% single-seed outliers to a labelled illustration.
   - Everywhere: model = 3.8B; ledger = signed log (Besu demoted); fault = key not human; build-state of the emergency stack = built (only anti-starvation/max_green/replay-HWM/spillback-cap/payload-bound remain).
3. **Citation hygiene**: FairSCOSCA (2601.06275) cites the fairness-ideology mapping ONLY; re-source the "60,000 intersections / 565 cities" SCATS/SCOOT figure to a real deployment reference or delete it. Verify every arXiv id resolves and its month matches its year label; fix the LLMLight (2312.16044) model-floor/year mismatch.
4. **Auditability KPI (F4)**: scope it to the deterministic decider + the rule policies that fired; the SLM verdict is wrapped in those policy ids (the rule fired P3/P5/P7; the SLM arbitrated). No SLM decision is a "defect" for lacking policies.

---

## 6. Security fixes (the accountability layer must actually be cryptographic and wired)

1. **Store the sender's signature (CRITICAL).** Message audit records MUST carry `{sender, sender_pubkey_fpr, signed_bytes_hash, sender_signature}` , NOT a `sig_valid` boolean. The chain commits to content; the sender's signature is the non-repudiable binding.
2. **Wire the pipeline end-to-end (CRITICAL).** Emit `kind:"message"` and `kind:"decision"` records (with `driving_input_seq`, `classification`, `policies_applied`) from the live controller into `AuditLog`. Add a flattening adapter so `fault_attribution` reads real `AuditLog` entries (they nest under `event`). No claim of "provable attribution" until it runs over the real log, not synthetic dicts.
3. **fault_report MUST verify crypto.** Before any attribution, call `identity.verify(registry_pubkey(sender), signed_bytes, sender_signature)` and `AuditLog.verify_chain()`; refuse to attribute on any record that fails. Wire the promised signature cross-check in `system._audit_bundle` (currently a comment that returns without verifying).
4. **Split sensor-spoof from detector-fault (CRITICAL for honesty).** A false local-sensing-driven preemption must NOT auto-label the AI. Add `SENSOR_FED_SPOOF` (external/human) distinct from `SYSTEM_DETECTOR` (AI false-negative); log vClass/sensor provenance; require a plausibility cross-check before a lone local sighting forces a sustained green.
5. **Sign registry events** (currently unsigned, operator-forgeable).
6. **Corroboration = sensor-backed + time-windowed.** Enforce B5 in `_corroborated`: reject sightings older than route-travel-time tolerance, require route/topology consistency, expire `_sightings` on TTL, bind `ev_id` to a per-session nonce so a real vehicle's id cannot be replayed later to fake corroboration.
7. **Ship the flagged build items**: consecutive-spillback cap forcing a CUSUM window; persisted per-sender replay high-water-mark (cross-restart); pre-verify payload size/field/depth bound at the bus; disallow preemption on an edge still in detector warmup.
8. **State the honest bound plainly** (do not oversell): tamper-evidence holds against a third party editing after anchor, NOT against the log operator who controls the anchor (single trust domain); that is the admin-key tier, out of scope, and must be written as such.

---

## 7. Legal framing (evidence pack, not verdict)

1. Rename the fault output primitive from `verdict` to `assessment`; every value is a "candidate attribution requiring independent human/judicial confirmation." Header on every fault report: "Not a determination of legal fault."
2. Split `technical_causal_chain` (what we compute: which signed input drove which decision) from `legal_causation: NOT_ASSESSED` (foreseeability/novus-actus/remoteness are the court's).
3. Tag every retrieved rule `binding_statute` (RTA/TSRGD/RTRA + section) or `advisory_highway_code` (+ RTA s.38(7) note). Never emit "rule breached -> liable"; emit "consistent/inconsistent with [rule], evidential only."
4. Authority ("AI") fault defaults to ZERO and is non-zero ONLY on the misfeasance branch (conflicting-greens the system positively created; Bird v Pearce), flagged low-confidence; never a bare `SYSTEM = ours` admission (Gorringe/Stovin). TfL is the London authority entity.
5. Human-in-the-loop MUST: no consequential action on the `assessment` alone.
6. Data protection MUST: DPIA; lawful basis (public task); personal data off-chain behind an erasable pointer, chain anchors only salted hashes; note pseudonymised hashes may still be personal data.
7. EU AI Act = voluntary governance benchmark, not a UK obligation; UK deployment governed by UK GDPR/DPA 2018.

---

## 8. The ONE valid experiment (Experiment 1, done right) + Experiment 2

**Dataset & ground truth (kills the circularity):**
- Ground truth from **SUMO incident injections with simulator-side outcome labels** (real EV vs phantom is a fact set by the injector), OR blind human adjudication; a label may NOT derive from either decider's threshold.
- Disjoint **dev / test** splits by distinct seeds, pre-registered before the test set is generated. Prompt AND rule tuned on dev ONLY; test touched ONCE. Any prompt change after seeing test = a fresh held-out set.
- Spoof cases populated **near the decision boundary** (minimum-effective-lie) so false-preemption rate has non-zero variance.
- **No numeric threshold in the SLM prompt** (strip "1.0 = the limit" and the threshold-shaped few-shots); give raw evidence.

**Statistics:** n>=30 independent seeds; per-seed paired SLM-minus-rule deltas; BCa CI + paired permutation + Holm across {accuracy, F1, false-preemption} x {anticipated, novel}; a pre-stated **MDE** from a power calc so a null reads "below MDE = X". Determinism at **N>=100** across service restarts. `real_model=true` assertion (model hash + quant + Foundry version) that ABORTS if the stub/an unpinned memo served the decision.

**Counterfactuals:** coordination effect = `defended - maxpressure_preempt` (not `- nopreempt`); SLM effect measured only with the SLM causally in the loop (B1 fixed, proven by `escalation_changed_decisions > 0` and a regression guard that fails if `coordinated == uncoordinated`). Ambulance benefit averaged over >=30 injections (route x time), not one scripted trip.

**Experiment 2 (demand sweep):** full 30 seeds x 8 scales (0.3-3.0), longer horizon to steady state, all controllers, four-family fairness + worst-case + throughput, BCa CIs (never below n~=20), no-harm delta as a pre-registered acceptance criterion (report even if it regresses).

**Experiment 3 (the novel object):** lie-magnitude sweep -> recall-collapse knee, false-alarm/false-preemption next to every recall, collusion & spillback marked as bounding zeros. This is the headline figure.

**Experiment 4 (evidence-pack quality):** the SLM Job-A assessment scored on citation-correctness + faithfulness + blind human agreement (kappa).

All on the **Euston substrate** with demand calibrated to real counts where possible; label every number relative-in-SUMO.

---

## 9. Map cutover (Euston Road)

- One reproducible script: `osmGet` bbox for the Euston Road stretch -> `netconvert` (`--tls.guess`, `--tls.join` as needed) -> `euston.net.xml` + generated `edge_ids.json` (the SINGLE source of edge ids; every route/label/trigger references it).
- Fail-loud: `edge_map_from_net(mode="chain")` MUST hard-error on a non-chain net; derive the map from `net.getEdges()`/connections; assert coverage of every TLS-controlled in-edge; assert every referenced edge id exists.
- Conflicting-green detector operates on `traci.trafficlight.getControlledLinks()` + the phase state string; "conflict" = two links with G/g in the same phase whose connections cross. Ship a fixture net with a known conflicting phase and a known safe phase.
- Collision/hard-brake: pin the exact sumocfg collision flags (`--collision.action`, `--collision.check-junctions true`, decel thresholds); ship a scripted forced-collision + forced-hard-brake fixture asserting detection fires at the known tick and nowhere else.

---

## 10. Fail-loud gates (MUST all be wired; a run aborts if any fails)

- Startup: Foundry reachable AND one real disambiguation call returns a parseable structured answer (`real_model=true`).
- Startup: policy corpus non-empty AND every policy id P1-P8 + every cited statute indexed.
- Startup: every scenario/label edge id resolves in `euston.net.xml`; `edge_map` covers all TLS in-edges.
- Startup: if Besu selected, node reachable + contract deployed; else default to in-memory registry (never silently half-connect).
- Per-run: `slm_calls_ok / total` above threshold; `escalations_deferred` below threshold; zero decision records with empty `policies_applied`; the decider on SLM-measured rows is actually `slm` (not stub/fallback); every attributed record passed signature + chain verification.

---

## 11. Build order (honest overnight subset first; then phase)

1. Consistency remediation §5 (docs; cheap; unblocks everything).
2. Euston net + `edge_ids.json` + coverage assertions (§9).
3. Foundry liveness probe + `real_model=true` (§10).
4. `ground_rules.yaml` + small curated UK-law corpus + retrieval with empty-corpus fail-loud (§6/§7).
5. Security wiring §6 items 1-5 (store sender sig, emit records, wire fault_report + crypto verify, split sensor/detector, sign registry).
6. Class-aware admissibility + 4 vehicle classes + triggers, tested against §9 fixtures.
7. `fault_attribution` over the real log + UK-law citation layer (§7); A1-A5 + T1-T11 tests with the decider-actually-ran + crypto-verified assertions.
8. Anti-starvation in the shield (D7).
9. Experiment 1 done-right §8 (dev/test, n>=30, CIs, MDE) — smoke at 2-3 seeds overnight, launch n=30 deliberately.
10. Experiments 2/3/4.

**Phase OUT of the unattended overnight run** (do NOT attempt blind): live Besu node (use in-memory + mock anchor), the full UK-law RAG (ship a small curated corpus), the 30-seed powered runs (smoke only), conflicting-green as a network-wide safety monitor (fixture detect-and-log only), T10/T11 (documented expected-failures only), the Qdrant experience-store (off).

---

## 12. Distinction acceptance tests (D1-D8; all binary; all required)

- D1 one thesis, one tree: grep for "blockchain"/"EU AI Act"/"60ms"/"liability"/"optimization" -> every hit gone or under a "superseded" banner; one thesis sentence across all live docs.
- D2 fault language = assessment/non-repudiation; no "verdict"; disclaimer present; no test asserts a legal conclusion.
- D3 fail-loud `real_model=true`: a deliberately misconfigured run ABORTS, does not emit a null.
- D4 Experiment 1 run, powered, pre-registered: result file with CIs + stated MDE; disambiguation prompt (not queue-length); dev/test split enforced.
- D5 non-circular SLM task: labels independent of both deciders; no threshold in prompt; decision-attribution breakdown exists; vs a tuned `rule_disambiguator`.
- D6 detectability-envelope figure (Experiment 3) with the knee identified numerically.
- D7 anti-starvation: `anti_starvation_violations == 0` across the attacked n=30 matrix; a forced-skip test triggers the shield override.
- D8 honest demand sweep + fairness + worst-case for all modes, one unified CI method; the coordination-inert/negative result reported, not hidden.

Plus (from the security/legal passes, promoted to acceptance): the fault engine verifies signatures + chain before attributing; a spoofed-local-sensing incident attributes to `SENSOR_FED_SPOOF`, not the AI; the evidence pack cites real UK statutes and carries the not-a-legal-determination disclaimer.

---

## 13. The viva answer this spec must make true

"My load-bearing claim is the deterministic corroboration gate plus non-repudiation-to-a-key over a cryptographically verified, tamper-evident log, plus a measured detectability-and-containment envelope, and an SLM that generates a human-readable, UK-law-cited evidence pack. The SLM and the coordination pathway are reported as scoped, pre-registered results against a stated MDE, with a fail-loud guard proving the real model ran, so a null is a bounded finding not an artefact. My audit binds a message to a signing key; it does not adjudicate fault, fault is the court's, and my log is evidential." Every clause of that sentence must be backed by a run that exists. If it is not, the spec is not yet met.
