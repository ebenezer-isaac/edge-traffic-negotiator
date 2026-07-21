# The Edge Negotiator: Master Build & Experiment Specification (v2)

**Status**: CANONICAL, frozen for direction. Consolidates two 10-agent adversarial teardowns (round 2 vs the docs, round 3 vs this spec). Single document Fable builds from.

**BUILD-TARGET NOTICE (read first):** this spec describes the INTENDED built system. A claim in it is *not settled* until its §12 acceptance gate passes over a real run. Sections that describe unbuilt behaviour (§1(b)/(c), §3, §6, §8, §9) are targets ("must become"), not statements about current code. The current code is the pre-teardown state; §5 + §11 are the path to conform it. Do not quote any number or capability as achieved until its gate is green.

**Golden rule:** fail loud, never degrade silently. Any gate that cannot prove its precondition (real model answered, corpus retrieved, edges resolved, signatures verified) must SKIP-with-a-recorded-skip or ABORT that specific step, never emit a green result. A fake-green null is worse than a crash; this project has produced one before.

---

## 0. Locked constraints (user decisions; do NOT overturn without consulting the user)

- SLM is a REQUIRED component (its job is defined below so it is load-bearing and honestly measured).
- Substrate: real **Euston Road (A501)**, short 3-4 signal stretch. Pre-built and committed, never regenerated at build time (§9). The synthetic corridor is retained only as a unit-test fixture.
- Fault rules grounded in cited UK law (`01-research/uk-traffic-law.md`).
- **Fault output = SPLIT** (2026-07-16 decision): a pure, cryptographically-verified PROVENANCE evidence pack (shareable/court-facing, NO machine verdict, NO confidence, NO accusation) + a firewalled, NON-EVIDENTIAL internal AI triage note (human-vs-AI reasoning, shown to a reviewer only AFTER the raw provenance).
- **Novel object = the DUALITY** (2026-07-16 decision): characterise the bounded class of stealthy, conservation-consistent lies the real-time gate provably CANNOT detect (measured on the physical-impact axis), and prove the tamper-evident log still attributes them AFTER the fact to a verified signing key with cited UK law. "The attacks nobody can stop live, but we can still name who did it."
- Deadline August 2026; scope phased, not cut.

---

## 1. The one thesis (frozen)

> An on-device, trust-preserving coordination layer for signalised junctions whose contribution is a **duality**: a deterministic real-time gate that refuses signed-but-uncorroborated emergency preemption from a compromised insider (and clears physically corroborated real emergencies), paired with a tamper-evident, signature-verified audit that, for the bounded class of stealthy conservation-consistent lies the gate provably cannot catch in real time, still **attributes** the responsible signing key after the fact and assembles a UK-law-cited **evidence pack** for a human fault inquiry. A frozen on-device SLM is the mandatory reasoner that turns the verified audit trail + retrieved statute into that post-hoc attribution note.

**Lead with (the novel object):** the real-time-undetectable-but-forensically-attributable **duality**, its measured stealthy-lie class (physical-impact axis), and the post-hoc attribution-to-key. NOT "a detectability ROC," NOT "the SLM beats a rule," NOT "coordination optimises traffic."

**Drop / reframe (settled):** "prove fault / verdict" → split evidence pack (no machine verdict); "blockchain" headline → signed hash-chained log with an **optional operator-controlled anchor (single trust domain)** [NOT "externally-anchored"; tamper-evident against third parties, not against the operator, §6.8]; EU AI Act → voluntary benchmark, not UK law; "coordination clears emergencies" → reported honestly (currently inert, B1; measured as a single-term toggle, §8); confront Traffic-R1 (differentiator is the trust/attribution role + the duality, not raw TSC skill or "small/frozen").

**SLM (mandatory) role:** the reasoner for the post-hoc **internal attribution note** (Job A) and the honestly-characterised disambiguation classifier (Job B). Neither requires beating a rule; both are measured non-circularly (§3, §8).

---

## 2. Single Source of Truth (freeze; every live doc conforms)

| Item | Frozen value |
|---|---|
| Headline / novel object | The DUALITY: stealthy-lie class undetectable in real time + post-hoc attribution-to-key with cited UK law |
| Fault output | SPLIT: pure provenance evidence pack (no verdict/confidence/accusation) + firewalled non-evidential internal AI note |
| SLM role | Mandatory; Job A = post-hoc attribution-note reasoner; Job B = characterised disambiguation classifier; not the load-bearing real-time defence |
| Real-time defence | Deterministic Ed25519 auth + conservation/CUSUM + corroboration gate |
| Model | Phi-4-mini, 3.8B, frozen, Foundry Local |
| Deploy target | Foundry Local in SUMO; Jetson/INT4 = future hardware-in-loop only |
| Ledger | Signed hash-chained AuditLog + optional operator-controlled Besu/QBFT anchor; single trust domain, one admin key; tamper-evident vs third parties only |
| **Substrate** | **Euston Road (A501) 3-4 signal stretch, pre-built & committed; synthetic corridor = fixture only; Lambeth dropped** |
| Fault attribution ontology | Origin over the audit log: `attacker-key` / `system-classifier` / `system-detector` / `sensor-fed-spoof` / `colluding-keys` / `legitimate` / `unknown`. This ontology lives in the INTERNAL note, never in the shareable evidence pack. Attribution is to a KEY, never a person. |
| Evidence pack content | verified sender key + chain/signature verification results + which corroboration checks failed + neutral cited-rule text (source-tagged, as-at date). No origin verdict, no confidence, no "attacker" label. |
| CoT / reasoning | The internal note DOES contain reasoning; it is VALIDATED against cited statute, never trusted; raise `max_tokens`. The note is non-evidential and firewalled. |
| RAG | policy text retrieved into the prompt from `ground_rules.yaml` + `uk-traffic-law.md`; small curated corpus; fail-loud if empty; not the Qdrant experience-store |
| Coordination effect | measured as the coordination term TOGGLED with all else fixed, per scale, with CI; reported honestly (currently inert) |
| EV benefit (n=30) | 31.1 s [25.4, 36.5] (preemption on vs off; NOT coordination, NOT SLM) |
| Gate cost | 8.0 s [3.7, 12.5] · Worst-case harm avoided 16.05 s [11.51, 20.44] · **Mean harm avoided 4.63 s [3.25, 5.99]** |
| Seeds / determinism | n=30 for any inferential claim (current exp1 n=1 / exp2 n=3 = pilots); determinism N=100 across restarts |
| STSD coursework | superseded; in-body stale claims neutralised (not merely bannered), see §5 |

---

## 3. The SLM (mandatory): two jobs, both non-circular

**Job A — post-hoc attribution-note reasoner (the duality's second half).** Given the *cryptographically-verified* audit window + retrieved applicable statute, the SLM writes the **internal, non-evidential** note:
```
{ candidate_origin: attacker-key|system-classifier|system-detector|sensor-fed-spoof|colluding-keys|unknown,
  cited_rules: ["RTA1988-s36", ...],   // ids resolvable in ground_rules.yaml/uk-traffic-law.md
  reasoning: "<=120 words linking VERIFIED facts to cited rules>",
  fault_weight_note: "MUST-rule (statute) | should-rule (advisory, RTA s.38(7))" }
```
Firewalled from the evidence pack (§7). Shown to a reviewer only after the raw provenance. Measured: citation-correctness vs held-out applicable-rule labels produced WITHOUT showing the annotator the retrieved set; **faithfulness graded against STATUTE TEXT by an independent adjudicator (not against the rule)**; agreement with a 2-rater qualified gold standard (Cohen's kappa). Baseline: a deterministic rule-to-text template; the SLM's win condition is strictly dominating the template on faithfulness + coverage over **novel fact-combinations** absent from any rule table. A citation whose supporting fact lacks verified provenance is a validation FAILURE (anti prompt-injection, §6/E6).

**Job B — disambiguation classifier**, characterised under §8 (dev/test split, no leaked threshold, non-circular labels, n>=30, CIs, MDE, vs a tuned rule). Win-or-a-powered-null; the thesis does not hang on it.

**The E2 rule (attribution direction):** a validly-signed but uncorroborated claim that caused harm is attributed to the **sender key** (`attacker-key`), never to the AI. `system-classifier`/`system-detector` require proof the AI erred on a WELL-EVIDENCED case vs ground truth. Verdict inputs come ONLY from cryptographically-verified provenance; corroboration is RECOMPUTED by the engine from independently-signed sighting records, never read from a self-asserted scalar.

---

## 4. Architecture

```
default -> MaxPressure (+ coordination term, currently inert/advisory; measured by toggle)   safety floor
   trigger (EV sensed | advance claim | conservation anomaly | incident | conflicting-green)
      -> deterministic gate: Ed25519 auth + registry + conservation/CUSUM + corroboration  <- real-time defence
           advance-claim ambiguous middle -> disambiguator (rule or SLM Job B, withhold-only)
      -> shield: min/max green, clearance, ANTI-STARVATION                                   safety invariants
   every message + decision -> AuditLog (sender-signature + hash-chain + completeness commitment)
   incident/stealthy-lie detected post-hoc -> verify chain+signatures -> assemble EVIDENCE PACK (pure provenance)
                                            -> SLM Job A internal note (attribution + cited law), firewalled
```

---

## 5. Consistency remediation (D1; gates everything)

1. Generate the **full forbidden-term manifest** with `grep -rl` (blockchain ~37 files, liability ~34, verdict ~29, decentralis(z)ed ~20, optimization ~18, Iroha ~18, "EU AI Act" ~17). Conform ALL, not a hand-picked 12. Terms inside a quotation of prior work are allowed.
2. Pin ONE canonical banner string. **Neutralise the STSD coursework in-body claims** (rewrite the EU-AI-Act sentence to "voluntary benchmark", delete "60ms", reframe blockchain→signed log, decentralised-optimisation→the current thesis). A banner alone does NOT satisfy D1; the D1 grep runs LAST, over the manifest, and a quarantined file must either be neutralised or explicitly excluded from grep scope with a stated reason.
3. Fix the 4 internal contradictions this spec's v1 had (now resolved here): C1 policies (see §12); C2 ORIGIN keeps `colluding-keys` (§2); C3 "externally-anchored" struck (§1/§2); C4 SSOT completed (Substrate + harm rows, §2).
4. Propagate the §6.1 signature record into `TEST-AUDIT-FAULT-SPEC.md §1.1` (delete `sig_valid:bool`).
5. Fix `spec.md` SC-001 ("coordinated" → "preemption vs no-preemption, not coordination"); DEMO-REPORT (StubAgent + powered means only, 8/16/4.63; single-seed outliers labelled). Remove the deleted `PROJECT-DECISION-BRIEF` reference + the no-CoT + MaxPressure-selection prompt from `slm_agent.py`.

---

## 6. Security (the accountability layer must be cryptographic, wired, and honestly bounded)

1. **Store the sender's signature.** Message records carry `{sender, sender_pubkey_fpr, signed_bytes_hash, sender_signature}` (NOT a `sig_valid` bool).
2. **Wire the pipeline end-to-end.** Emit `kind:"message"` and `kind:"decision"` records (with `driving_input_seq`, `classification`, `policies_applied`) into `AuditLog`; add a flattening adapter (real entries nest under `event`) so `fault_attribution` reads the REAL log, not synthetic dicts.
3. **Verify crypto before attributing.** `fault_report` takes the AuditLog + registry pubkeys, runs `verify_chain()` once + `identity.verify(pubkey(sender), signed_bytes, sender_signature)` per causal record, and refuses (UNKNOWN + abort flag) on any failure. Wire the `system._audit_bundle` cross-check that is currently a comment above `return`.
4. **Split sensor-spoof from detector-fault.** Add `sensor-fed-spoof` (external) distinct from `system-detector` (AI). Require a second independent signal before a lone local sighting forces a *sustained* green. STATE plainly: the sensor-spoof-vs-detector-error label is a POST-HOC, ground-truth-dependent forensic call, not a runtime attribution; drop "local sensing cannot be spoofed" (it can be, physically).
5. **Sign + anchor registry events** (currently unsigned, operator-forgeable, the trust root).
6. **Corroboration = sensor-backed + time-windowed.** Enforce B5 in `_corroborated`: reject stale sightings (older than route-travel-time tolerance), require route/topology consistency and topological independence, expire `_sightings` on TTL, bind `ev_id` to a PER-CLAIM nonce. Corroboration is recomputed from independently-signed sightings, never a scalar.
7. **Completeness + anti-rollback.** Add a signed monotonic append-only commitment (anchored `(seq_high, root)` per batch) so omission/rollback/selective-disclosure is externally detectable. A fault report refuses a verdict when its causal window is not provably complete (`INCOMPLETE_DISCLOSURE`, never a default origin).
8. **Ship the flagged build items:** consecutive-spillback cap forcing a CUSUM window; persisted per-sender replay high-water-mark (cross-restart); payload size/field/depth bound at the bus; no preemption during detector warmup.
9. **Prompt-injection guard (Job A):** untrusted audit/message content (reason text, ev_id, payloads) enters the SLM prompt only as clearly-delimited NON-instruction context; the faithfulness oracle requires every asserted fact to trace to a verified audit field.
10. **Honest bound, stated inline everywhere it matters:** tamper-evidence holds against a third party, NOT against the log operator/admin-key tier (single trust domain, out of scope). "non-repudiation to a key" is scoped to an adversary weaker than the operator until the registry is signed-and-anchored and a real anchor exists; the mock anchor (§11) is NOT "externally-anchored".

---

## 7. Legal framing (split; evidence pack pure, note firewalled)

1. The EVIDENCE PACK emits only mechanically-true, reproducible facts: verified sender key, chain/signature verification result, which corroboration checks failed, neutral cited-rule text. NO `candidate_origin`, NO confidence, NO `fault_weight` conclusion, NO "attacker" label. Header: "Provenance record; not a determination of legal fault."
2. `technical_causal_chain` (which verified input drove which decision) is separated from `legal_causation: NOT_ASSESSED` (foreseeability/novus-actus/remoteness are the court's).
3. Every cited rule carries `binding_statute` vs `advisory_highway_code` (+ RTA s.38(7) note), source-provenance (primary/secondary), an as-at date, and the KB caveat verbatim. Never assert "hard_law" as a conclusion. A pinned legal-currency review date with a fail-loud staleness gate.
4. The SLM internal note (candidate_origin, reasoning) is explicitly NON-EVIDENTIAL, restricted-distribution, and firewalled from the pack AND from the reviewer's first look (raw provenance first, to avoid automation bias).
5. Conflicting-green = a FACTUAL detection only; legal characterisation `NOT_ASSESSED` (Bird v Pearce vs Gorringe/Stovin/Poole is unsettled). Confidence attaches to the detection, never to the law. TfL is the London authority entity.
6. `attacker-key` / criminal-implying language never appears in an auto-emitted shareable field (Defamation Act; UK GDPR Art 10 criminal-offence data; Art 22 automated decision). Meaningful human review defined: competent + empowered reviewer, sees raw provenance first, records independent reasons, logged override-rate KPI. No consequential action on the note alone.
7. GDPR: personal data off-chain only; the chain anchors a Merkle ROOT over off-chain records (NO per-record personal-data hash); per-record secret salt destroyed on erasure; retained under Art 17(3)(b)/(e) exemption with a documented balancing test + Art 6(1)(e) public-task basis; DPIA records residual re-linkability. Drop any "Art 17 satisfied by salted hash" claim.

---

## 8. Experiments (the ONE valid protocol)

**Experiment D (the headline, the duality):** construct a family of **conservation-consistent** lies (residual near zero) parameterised by **physical impact** (green-time stolen, EV delay induced); show the real-time gate's recall collapses along the physical-impact axis while residual stays invisible (the bounded stealthy class it provably cannot catch); then show the audit + Job-A attributes each such lie post-hoc to the correct signing key with cited law. Report the size of the undetectable-but-attributable region. This is the novel object.

**Experiment 1 (Job B classifier), de-circularised:**
- Ground truth from SUMO incident injections: the injector sets the latent real/phantom flag; a noisy sensing process generates observable evidence with genuine CLASS OVERLAP. The label MUST be non-recoverable from the observable feature vector by any monotone threshold; report label↔feature mutual information and a Bayes-error floor > 0.
- Disjoint dev/test seed splits IN CODE; tune rule + freeze prompt on dev only; `evaluate` once on test; forbid evaluate over tuning cases.
- NO numeric threshold in the SLM prompt; a pre-run assertion fails the run if the assembled prompt contains one.
- `real_model=true`: pin + assert model hash + quant + Foundry version; abort on mismatch. `parse_failures` a separate exclusion category, never folded into a safe default; abort if > threshold.
- Stats: n>=30 independent seeds; paired SLM-minus-rule deltas; BCa + paired permutation + Holm across {accuracy, F1, false-preemption} × {anticipated, novel}; a real power calc (alpha, power=0.8, piloted SD, Holm-adjusted alpha → derived n); a TOST equivalence test; declare a null ONLY when CI half-width < MDE (else "underpowered"). Determinism N>=100 across restarts.

**Experiment 2 (demand sweep):** full 30 seeds × 8 scales (0.3-3.0), longer horizon to steady state, all controllers; four-family fairness + worst-case + throughput; coordination effect = the coordination term TOGGLED with all else fixed (rename the confounded `defended - maxpressure_preempt` to "combined defended-stack effect"); no-harm as a pre-registered acceptance criterion (reported even if it regresses); no CI below n~=20.

**Substrate:** Euston (§9); demand calibrated to a NAMED source (TfL/DfT AADT); calibration is a startup gate that aborts or flags "uncalibrated synthetic" if the source is absent. Every number labelled relative-in-SUMO.

---

## 9. Euston substrate (pre-built, committed, never regenerated at build time)

Pre-build BY HAND and COMMIT `euston.net.xml` + `edge_ids.json` (the single source of edge ids): exact bbox lat/lon, full `netconvert` flag list, `--tls.guess/--tls.join` decisions, and the expected TLS + in-edge count asserted. The overnight builder MUST NOT call `osmGet`. `edge_map_from_net(mode="chain")` hard-errors on the non-chain Euston topology; derive the map from `net.getEdges()`/connections and assert coverage of every TLS-controlled in-edge. Conflicting-green detector uses `traci.trafficlight.getControlledLinks()` + phase state; ship a fixture net with a known conflicting phase + a known safe phase. Pin the sumocfg collision flags; ship a forced-collision + forced-hard-brake fixture asserting detection fires at the known tick and nowhere else.

---

## 10. Fail-loud gates (each SCOPE-LOCAL; SKIP-with-record when its precondition is absent, ABORT only that step, never the whole run)

- Real-model gate: Foundry reachable + one real structured call returns parseable output → else the SLM experiment is SKIPPED-and-marked, other work proceeds.
- Corpus gate: `ground_rules.yaml` non-empty + every P1-P8 + cited statute indexed → else Job A / Exp4 SKIPPED.
- Net gate: every scenario/label edge id resolves in `euston.net.xml`; `edge_map` covers all TLS in-edges → else Euston experiments SKIPPED (corridor fixtures still run).
- Anchor gate: any "externally-anchored" claim requires a REAL anchor write; a mock anchor is labelled "not externally anchored", never presented as such.
- Per-run: `slm_calls_ok/total` above threshold; the decider on SLM-measured rows is actually `slm`; every attributed record passed signature + chain verification; a fault report over an incomplete window returns `INCOMPLETE_DISCLOSURE`.
- Doc + corridor work is gated on NONE of Foundry/Euston/corpus.

---

## 11. Build order

**Prerequisite artifacts (pre-built during the hardening phase, NOT overnight-blind):** `euston.net.xml` + `edge_ids.json` (§9); `ground_rules.yaml` (P1-P8 index cross-linked to `uk-traffic-law.md` statute ids) + a citation oracle; the SUMO-injection non-circular labelled dataset (§8 Exp 1).

**Honest overnight subset (no Foundry/Euston/OSM dependence):**
1. Doc remediation over the full §5 manifest; D1 grep runs LAST as the gate.
2. Message-record schema + `kind:"message"` emission in the live seam (§6.1/6.2).
3. Rewire `fault_attribution` to the real AuditLog: rename to `assessment`/ORIGIN, add `sensor-fed-spoof`, flattening adapter, enforce `identity.verify` + `verify_chain` before attributing, wire the dead `_audit_bundle` cross-check (§6.3), the E2 direction (§3), the completeness commitment (§6.7).
4. Fix `slm_agent.py` as a STATIC edit: strip the "1.0 = the limit" threshold + threshold-shaped few-shots, raise `max_tokens`, drop the no-CoT stance; add the Job-A structured output.
5. Anti-starvation shield invariant + forced-skip unit test (deterministic, no SLM).
6. Foundry determinism probe as SKIP-not-abort (record `real_model` + determinism if up; else write a `skipped` result).

**OUT of the overnight subset (require the prerequisite artifacts / real runs; do NOT attempt blind):** Euston experiments; Job A / Exp4 citation runs; SUMO-injection-labelled Experiment 1; Experiment D (duality) full run; exploit-defend / D8; the 30-seed powered runs; live Besu (use in-memory + mock anchor, labelled). T10/T11 stay documented-xfail.

---

## 12. Acceptance tests (all binary; all required for distinction)

- D1 one-thesis-one-tree: full §5 manifest clean (neutralised or scope-excluded with reason); one thesis sentence across live docs. Grep runs last.
- D2 fault language = split; the shareable pack has no verdict/confidence/accusation; the SLM note is classed non-evidential + firewalled; a test fails if any shareable field carries an origin verdict.
- D3 `real_model=true` guard: a deliberately misconfigured run ABORTS/ SKIPS-with-record, never emits a null.
- D4 Experiment 1 run, powered, pre-registered: result file with CIs + a computed MDE + TOST; dev/test split enforced in code; label↔feature MI reported; no threshold in prompt (asserted).
- D5 non-circular labels (Bayes-error floor > 0) + a strong tuned `rule_disambiguator` baseline + Job-A vs rule-to-text template on novel combinations.
- D6 Experiment D figure: the stealthy conservation-consistent class on the physical-impact axis + its post-hoc attribution rate to the correct key.
- D7 anti-starvation: `anti_starvation_violations == 0` across the attacked n=30 matrix; forced-skip test triggers the override.
- D8 honest demand sweep + fairness + worst-case, all modes, one CI method; coordination toggle result reported (even if inert/negative).
- D-sec: fault engine verifies signatures + chain before attributing; a spoofed-local-sensing incident attributes to `sensor-fed-spoof`, not the AI; the evidence pack cites real UK statutes with source-tag + as-at date + the not-a-legal-determination header.
- **Policy-KPI rule (fixes C1):** the empty-`policies_applied` abort gate applies to DETERMINISTIC decision records only; the SLM Job-A note is exempt (it is non-evidential and carries `cited_rules`, not P1-P8). Stated in GROUND-RULES §F + TEST-SPEC.
- Tests: T1-T9 pass-required; T10/T11 documented-xfail (one place, no contradiction).

---

## 13. The viva sentence this spec must make true

"My contribution is a duality: a deterministic real-time gate that refuses a compromised insider's uncorroborated preemption, and, for the bounded class of stealthy conservation-consistent lies the gate provably cannot catch in real time, a signature-verified tamper-evident audit that still attributes the responsible key after the fact and assembles a UK-law-cited evidence pack for a human inquiry. The evidence pack states only cryptographically-verified facts; it does not adjudicate fault, that is the court's. A frozen on-device SLM writes the internal, non-evidential attribution note, characterised for citation-faithfulness against statute, and is separately reported, either way, on disambiguation against a tuned rule with a stated MDE and a fail-loud guard proving the real model ran. Coordination and traffic optimisation are not my claims; the trust duality is." Every clause backed by a run that passed its §12 gate, or it is not settled.
