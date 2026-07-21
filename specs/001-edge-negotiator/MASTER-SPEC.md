# The Edge Negotiator: Master Build & Experiment Specification (v3)

**Status**: CANONICAL, frozen for direction. Consolidates three adversarial teardowns (round 2 vs the docs, round 3 vs this spec, round 4 vs v2). Single document Fable builds from.

**v3 CHANGELOG (2026-07-21, user-approved keystone + round-4 no-regret fixes):**
- **Duality's second half reframed** (user decision 2026-07-21, overturns the 2026-07-16 attribute-to-key wording): from "attributes the responsible signing key" → an operator-binding **NON-EQUIVOCATION / COMPLETENESS COUPLING** ("no free lie", §0/§1/§8). Four independent round-4 reviewers showed attribute-to-key is trivial non-repudiation + prior-art accountability that breaks against the operator-adjacent insider.
- **A REAL external anchor is now MANDATORY** (overturns "optional mock Besu"): the operator must not be able to silently rewrite the log. This is the true gate on distinction (§0/§2/§6.7/§10).
- The **hard measured object is the 7-way ORIGIN classification** (confusion matrix), not the ~100% signature-to-key lookup (§3/§8/§12).
- Round-4 no-regret fixes folded in throughout (schema pinning, tie-break rule, nonlinear Bayes ceiling + OOD split, citation-correctness scoring, SLM kill-criterion, sighting-record schema, signature preimage, enrolment ceremony, detectability-envelope purge). Full ledger in `_hardening-log.md`.

**BUILD-TARGET NOTICE (read first):** this spec describes the INTENDED built system. A claim in it is *not settled* until its §12 acceptance gate passes over a real run. Sections describing unbuilt behaviour (§1(b)/(c), §3, §6, §8, §9) are targets ("must become"), not statements about current code. The current code is the pre-teardown state; §5 + §11 are the path to conform it. Do not quote any number or capability as achieved until its gate is green.

**Golden rule:** fail loud, never degrade silently. Any gate that cannot prove its precondition (real model answered, corpus retrieved, edges resolved, signatures verified, anchor written) must SKIP-with-a-recorded-skip or ABORT that specific step, never emit a green result. A fake-green null is worse than a crash; this project has produced one before.

---

## 0. Locked constraints (user decisions; do NOT overturn without consulting the user)

- SLM is a REQUIRED component (its job is defined below so it is load-bearing and honestly measured). A kill-criterion (§8) may demote the SLM's CLAIM, never its presence.
- Substrate: real **Euston Road (A501)**, short 3-4 signal stretch. Pre-built and committed, never regenerated at build time (§9). The synthetic corridor is retained only as a unit-test fixture.
- Fault rules grounded in cited UK law (`01-research/uk-traffic-law.md`).
- **Fault output = SPLIT** (2026-07-16 decision): a pure, cryptographically-verified PROVENANCE evidence pack (shareable/court-facing, NO machine verdict, NO confidence, NO accusation) + a firewalled, NON-EVIDENTIAL internal AI triage note (origin reasoning, shown to a reviewer only AFTER the raw provenance).
- **Novel object = the DUALITY, expressed as the COUPLING** (2026-07-21 decision, supersedes the 2026-07-16 attribute-to-key wording): characterise the bounded class of stealthy, conservation-consistent lies the real-time gate provably CANNOT detect (measured on the physical-impact axis), and prove the **coupling** — a lie in that class can only succeed if the operator *also* suppresses the independently-signed corroborating sightings, yet those same sightings are the physical evidence that would have caught it live; so under a completeness guarantee anchored to a REAL external witness the operator cannot silently rewrite, every such lie is EITHER catchable live by corroboration OR leaves an un-erasable externally-witnessed trace. **"No free lie": no third state where a lie is both invisible live AND untraceable after.** This property is novel AND evidential (it lives in the pure pack as verified completeness + corroboration facts) and it binds the operator.
- **A REAL external anchor is MANDATORY** (2026-07-21, overturns optional-mock): the non-equivocation guarantee is void without an external witness the operator cannot silently rewrite. Feasible at demo scale (single external witness / transparency-log or single-node external ledger; not necessarily full blockchain).
- Deadline August 2026; scope phased, not cut.

---

## 1. The one thesis (frozen)

> An on-device, trust-preserving coordination layer for signalised junctions whose contribution is a **duality realised as a coupling**: a deterministic real-time gate that refuses signed-but-uncorroborated emergency preemption from a compromised insider (and clears physically corroborated real emergencies), paired with an externally-anchored, tamper-evident, signature-verified audit for which the bounded class of stealthy conservation-consistent lies the gate provably cannot catch in real time exhibits the **no-free-lie property**: to escape the gate a lie must stay corroboration-consistent, and to escape post-hoc accountability the operator must suppress the very independently-signed sightings that corroborated it — but suppression is externally detectable under the anchored completeness commitment, and those same sightings are what corroboration checks against live. So the lie is either caught live or leaves an un-erasable, externally-witnessed trace from which a human inquiry can classify its origin against cited UK law. A frozen on-device SLM is the mandatory reasoner that turns the verified, complete audit window + retrieved statute into that post-hoc origin-classification note.

**Lead with (the novel object):** the **coupling / no-free-lie property** over the measured stealthy-lie class (physical-impact axis) under a real external anchor; and the **origin classification** of each lie from the complete, verified trace. NOT "a detectability ROC," NOT "attribution is a signature lookup," NOT "the SLM beats a rule," NOT "coordination optimises traffic."

**Position vs prior art (state explicitly, do not pretend it is new):** real-time-undetectable + post-hoc-tamper-evident is textbook accountability (Küsters CCS 2010; PeerReview SOSP 2007; Haber-Stornetta 1991; Schneier-Kelsey 1999) over textbook stealthy FDI (Liu-Ning-Reiter 2011; Teixeira-Sandberg 2015; Mo-Sinopoli 2010). Our increment is NOT the mechanism; it is (a) the **coupling** (corroboration-to-conceal == corroboration-to-catch) instantiated on a signalised corridor, which is the one non-obvious emergent link, and (b) the **first quantified map** of the physically-large-but-conservation-invisible insider-preemption class on a real London corridor tied to cited UK statute. Confront Traffic-R1 (differentiator = the trust/accountability role + the coupling, not raw TSC skill or "small/frozen").

**Drop / reframe (settled):** "prove fault / verdict" → split evidence pack (no machine verdict); "blockchain" headline → signed hash-chained log + a REAL external anchor for the completeness commitment (single admin trust domain for issuance, but the anchor is external — that is the point); EU AI Act → voluntary benchmark, not UK law; "coordination clears emergencies" → reported honestly (currently inert, B1; measured as a single-term toggle, §8).

**SLM (mandatory) role:** the reasoner for the post-hoc **internal origin-classification note** (Job A) and the honestly-characterised disambiguation classifier (Job B). Its measured contribution to the thesis is threefold: citation-faithful origin reasoning over the complete trace (Job A); disambiguation (Job B, win-or-powered-null); and the **frozen-is-safer** result — a data-poisoning attack vs a continual-learning baseline that MEASURES the robustness advantage of a frozen model (§8). Neither Job requires beating a rule; all are measured non-circularly.

---

## 2. Single Source of Truth (freeze; every live doc conforms)

| Item | Frozen value |
|---|---|
| Headline / novel object | The COUPLING / no-free-lie property over the measured stealthy-lie class, under a REAL external anchor + the post-hoc origin classification |
| Fault output | SPLIT: pure provenance evidence pack (no verdict/confidence/accusation) + firewalled non-evidential internal AI note |
| SLM role | Mandatory; Job A = post-hoc origin-classification note reasoner; Job B = characterised disambiguation classifier; + the frozen-is-safer poisoning result; not the load-bearing real-time defence |
| Real-time defence | Deterministic Ed25519 auth + conservation/CUSUM + corroboration gate |
| Model | Phi-4-mini, 3.8B, frozen, Foundry Local |
| Deploy target | Foundry Local in SUMO; Jetson/INT4 = future hardware-in-loop only |
| Ledger | Signed hash-chained AuditLog + **a REAL external anchor** for the monotonic completeness commitment (operator cannot silently rewrite). Issuance is one admin trust domain; the anchor is external and that binds the operator. |
| **Substrate** | **Euston Road (A501) 3-4 signal stretch, pre-built & committed; synthetic corridor = fixture only; Lambeth dropped** |
| Fault attribution ontology | Origin over the audit log: `attacker-key` / `system-classifier` / `system-detector` / `sensor-fed-spoof` / `colluding-keys` / `legitimate` / `unknown`. This ontology lives in the INTERNAL note, never in the shareable evidence pack. Attribution is to a KEY, never a person. |
| Origin classification (the hard object) | 7-way origin classification vs the injected latent cause, reported as a full CONFUSION MATRIX. Crypto attribute-to-key is a separate ~100% verification CHECK, explicitly NOT the contribution. |
| Evidence pack content | verified sender key + chain/signature verification results + externally-anchored completeness proof + which corroboration checks failed (mechanically, origin-independent) + neutral cited-rule text (source-tagged, as-at date). No origin verdict, no confidence, no "attacker" label. |
| CoT / reasoning | The internal note DOES contain reasoning; it is VALIDATED against cited statute, never trusted; raise `max_tokens`. The note is non-evidential and firewalled. |
| RAG | policy text retrieved into the prompt from `ground_rules.yaml` + `uk-traffic-law.md`; small curated corpus; fail-loud if empty; not the Qdrant experience-store |
| Coordination effect | measured as the coordination term TOGGLED with all else fixed, per scale, with CI; reported honestly (currently inert — a structural zero, not an empirical null; §8) |
| EV benefit (n=30) | 31.1 s [25.4, 36.5] (preemption on vs off; NOT coordination, NOT SLM) |
| Gate cost | 8.0 s [3.7, 12.5] · Worst-case harm avoided 16.05 s [11.51, 20.44] · **Mean harm avoided 4.63 s [3.25, 5.99]** |
| Seeds / determinism | n=30 for any inferential claim (current exp1 n=1 / exp2 n=3 = pilots); determinism N=100 across restarts |
| STSD coursework | superseded; in-body stale claims to be NEUTRALISED (target-state, per §5), not merely bannered |

---

## 3. The SLM (mandatory): jobs, all non-circular

**Job A — post-hoc origin-classification note reasoner (the duality's second half).** Given the *cryptographically-verified AND provably-complete* audit window + retrieved applicable statute, the SLM writes the **internal, non-evidential** note:
```
{ candidate_origin: attacker-key|system-classifier|system-detector|sensor-fed-spoof|colluding-keys|legitimate|unknown,
  cited_rules: ["RTA1988-s36", ...],   // ids resolvable in ground_rules.yaml/uk-traffic-law.md
  reasoning: "<=120 words linking VERIFIED facts to cited rules>",
  fault_weight_note: "MUST-rule (statute) | should-rule (advisory, RTA s.38(7))" }
```
(N1 fix: `legitimate` is present in the enum, matching the §2 ontology.) Firewalled from the evidence pack (§7). Shown to a reviewer only after the raw provenance.

**Primary metric = 7-way origin-classification accuracy vs the injected latent cause, reported as a full CONFUSION MATRIX** (methods F2). Foreground the HARD confusions (authentic lie vs honest sensor error vs detector error). The crypto attribute-to-key rate is reported SEPARATELY as a ~100% verification check and labelled "verification, not the contribution." Also measured: citation-correctness vs held-out applicable-rule labels produced WITHOUT showing the annotator the retrieved set; **faithfulness graded against STATUTE TEXT by qualified human raters (no LLM-as-judge for legal faithfulness — circular), restricted to settled-law cases, gated on Cohen's kappa ≥ 0.6 (else NOT_ASSESSED)**; the **SLM false-citation rate** on novel fact-combinations reported as a PRIMARY number (Dahl et al 2024 legal-hallucination risk).

**Job A baseline = a deterministic rule-to-text template WITH a graceful fallback** ("nearest applicable rule; no exact match" rather than empty). Coverage is scored by **citation CORRECTNESS, not presence** (a confident wrong citation loses to honest abstention). A distinction-grade result may be "honest template abstention beats confident SLM hallucination" — this is an acceptable, pre-registered outcome. A citation whose supporting fact lacks verified provenance is a validation FAILURE (anti prompt-injection, §6/E6).

**Job B — disambiguation classifier**, characterised under §8 (dev/test split, no leaked threshold, non-circular labels, n≥30, CIs, MDE, vs a tuned rule). Win-or-a-powered-null; the thesis does not hang on it.

**The E2 rule (attribution direction) + tie-break (build FATAL-3 fix):** a validly-signed, uncorroborated claim that caused harm is attributed to the **sender key** (`attacker-key`), never to the AI. This WINS the tie against the "catchable phantom" branch: signed + zero-corroboration + harmful → `attacker-key`. `system-classifier` applies ONLY when the AI erred on a WELL-EVIDENCED case vs ground truth; `system-detector` likewise requires proof the detector erred on a well-evidenced case. Verdict inputs come ONLY from cryptographically-verified provenance; corroboration is RECOMPUTED by the engine from independently-signed sighting records (§6.6 schema), never read from a self-asserted scalar.

---

## 4. Architecture

```
default -> MaxPressure (+ coordination term, currently inert/advisory; measured by toggle)   safety floor
   trigger (EV sensed | advance claim | conservation anomaly | incident | conflicting-green)
      -> deterministic gate: Ed25519 auth + registry + conservation/CUSUM + corroboration  <- real-time defence
           advance-claim ambiguous middle -> disambiguator (rule or SLM Job B, withhold-only)
      -> shield: min/max green, clearance, ANTI-STARVATION                                   safety invariants
   every message + signed sighting + decision -> AuditLog (sender-signature + hash-chain)
   batch -> monotonic completeness commitment -> REAL EXTERNAL ANCHOR (operator cannot rewrite)
   incident/stealthy-lie detected post-hoc -> verify chain+signatures+completeness -> EVIDENCE PACK (pure provenance)
                                            -> SLM Job A internal note (origin + cited law), firewalled
```

---

## 5. Consistency remediation (D1; gates everything)

1. Generate the **full forbidden-term manifest** with `grep -rl` (blockchain ~37 files, liability ~34, verdict ~29, decentralis(z)ed ~20, optimization ~18, Iroha ~18, "EU AI Act" ~17). Conform ALL, not a hand-picked 12. Terms inside a quotation of prior work are allowed.
2. Pin ONE canonical banner string. **Neutralise the STSD coursework in-body claims** (rewrite the EU-AI-Act sentence to "voluntary benchmark", delete "60ms", reframe blockchain→signed log + external anchor, decentralised-optimisation→the current thesis). A banner alone does NOT satisfy D1; the D1 grep runs LAST, over the manifest, and a quarantined file must either be neutralised or explicitly excluded from grep scope with a stated reason. The §2 STSD SSOT row is TARGET-STATE ("to be neutralised"), not a claim of done (N6).
3. Fix the 4 internal contradictions v1 had (resolved): C1 policies (§12); C2 ORIGIN keeps `colluding-keys` (§2); C3 "externally-anchored" is now a REAL claim backed by §6.7, not struck; C4 SSOT completed (§2).
4. Propagate the §6.1 signature record into `TEST-AUDIT-FAULT-SPEC.md §1.1` (delete `sig_valid:bool`), AND conform TEST-AUDIT Part 2's ORIGIN enum to §2 (lowercase-kebab, add `sensor-fed-spoof` + `legitimate`, the E2 direction) (N5).
5. Fix `spec.md`: **rewrite the §1 overview** (currently "headline value is coordinated emergency response") + **SC-005** ("detectability envelope") + **SC-001** ("coordinated") to the duality/coupling thesis on the physical-impact axis, so the D1 one-thesis-sentence test can pass (N3, N4). Rewrite `TEST-AUDIT §3.3(c)` from "lie size as multiples of the band / detectability envelope" to the physical-impact axis. DEMO-REPORT: StubAgent + powered means only (8/16/4.63; single-seed outliers labelled). Remove the deleted `PROJECT-DECISION-BRIEF` reference + the no-CoT + MaxPressure-selection prompt from `slm_agent.py`. Add "detectability envelope"/"detectability ROC" to the D1 forbidden-term manifest.
6. **Amend GROUND-RULES §F + TEST-AUDIT** so the "a decision citing no policy is a defect" rule explicitly EXEMPTS the SLM Job-A note (non-evidential, carries `cited_rules` not P1-P8) — currently §12 asserts this exemption exists but GROUND-RULES-POLICY.md:92 + TEST-AUDIT:39,127 still state the unqualified defect (N2). Either land the amendment or reword §12 to "must be stated in" (target).

---

## 6. Security (the accountability layer must be cryptographic, externally-anchored, wired, and honestly bounded)

1. **Store the sender's signable preimage, not just a digest** (security S5). Message records carry `{sender, sender_pubkey_fpr, signed_payload, sender_signature}` where `signed_payload` is the canonical `(sender, t, payload)` the bus actually signs, so `identity.verify(pubkey, canonical_bytes(signed_payload), sender_signature)` is recomputable from the stored record alone. (NOT a `sig_valid` bool; NOT a bare hash whose preimage is absent.)
2. **Wire the pipeline end-to-end.** Emit `kind:"message"`, `kind:"sighting"` (§6.6), and `kind:"decision"` records (with `driving_input_seq`, `classification`, `policies_applied`) into `AuditLog`. Add a `flatten(entries) -> list[dict]` adapter (real entries nest the payload under `event`; the adapter maps `event.*` up and PRESERVES the envelope `seq`) so `fault_attribution` reads the REAL log, not synthetic flat dicts. `driving_input_seq` references the audit-envelope `seq` of the driving message record. The item-3 test MUST run `fault_report` over a CONSTRUCTED real `AuditLog` and refuse on a tampered signature (build FATAL-2).
3. **Verify crypto + completeness before attributing.** `fault_report` takes the AuditLog + registry pubkeys, runs `verify_chain()` once + `identity.verify(...)` per causal record + the §6.7 completeness proof, and refuses (UNKNOWN + abort flag / `INCOMPLETE_DISCLOSURE`) on any failure. Wire the `system._audit_bundle` cross-check that is currently a comment above `return`; pass the registry DER pubkey dict in.
4. **Split sensor-spoof from detector-fault.** Add `sensor-fed-spoof` (external) distinct from `system-detector` (AI), each with an explicit trigger predicate and a `ground_truth` field the synthetic-log test reads (build B1). Require a second independent signal before a lone local sighting forces a *sustained* green. STATE plainly: the sensor-spoof-vs-detector-error label is a POST-HOC, ground-truth-dependent forensic call, not a runtime attribution; drop "local sensing cannot be spoofed" (it can be, physically).
5. **Enrolment ceremony + counter-signed rotation (security FATAL-2, the framing attack).** Registry `register` must NOT permit an operator to unilaterally re-bind an honest junction's id to a new attacker key. Each junction SELF-SIGNS its key at enrolment; rotation/re-registration requires the incumbent key's counter-signature (or a quorum external to the operator). Registry events are signed and anchored (§6.7). The evidence pack carries ENROLMENT PROVENANCE, not just current registry state, so a key→entity binding cannot be silently forged.
6. **Corroboration = key-bound, sensor-backed, time-windowed, route-consistent** (security FATAL-1 + S6 + S8). Add a signed `kind:"sighting"` record `{sighter_key, ev_id, approach, t, position}`; corroboration is RECOMPUTED by walking these signed sightings, so every corroborating signal is itself attributable to a key. A lone KEYLESS local sensor reading may NOT serve as the independent corroboration that forces sustained green; any signal that forces sustained preemption must be an attributable signed record, else the pack marks it "corroboration not key-attributable." Enforce B5 in `_corroborated`: reject stale sightings (older than route-travel-time tolerance), require route/topology consistency + topological independence, expire `_sightings` on TTL, bind `ev_id` to a PER-CLAIM nonce keyed on `(ev_id, approach, time-window, claimer)` + route-consistency against the corroborating sighting's trajectory.
7. **Completeness + anti-rollback via a REAL external anchor (the keystone).** Add a signed monotonic append-only commitment; write `(seq_high, merkle_root)` per batch to a **REAL external witness the operator cannot silently rewrite** (transparency-log or external single-node ledger). This is what makes omission/rollback/selective-disclosure externally detectable AGAINST THE OPERATOR — the property the whole coupling depends on. A mock/in-memory anchor does NOT satisfy this and must be labelled "not externally anchored" and cannot back any no-free-lie claim. A fault report refuses a verdict when its causal window is not provably complete against the anchor (`INCOMPLETE_DISCLOSURE`, never a default origin).
8. **Ship the flagged build items:** consecutive-spillback cap forcing a CUSUM window; persisted per-sender replay high-water-mark (cross-restart); payload size/field/depth bound at the bus; no preemption during detector warmup.
9. **Prompt-injection guard (Job A), content-vs-provenance (security S7):** untrusted audit/message content (reason text, ev_id, payloads) enters the SLM prompt only as clearly-delimited NON-instruction context. The faithfulness oracle distinguishes "field was authentically LOGGED" from "field content is independently CORROBORATED"; an attacker's own authentically-signed free-text may NOT be the sole support for a citation. Every asserted fact must trace to an independently-corroborated verified field.
10. **Origin-independent citation selection (security S4).** The evidence pack's failed-checks set and cited-rule selection must be a mechanical, origin-INDEPENDENT function (cite every rule touching any present field), so a reviewer cannot reconstruct `candidate_origin` from the "pure" pack and defeat the automation-bias control (D2). A test proves the citation set is not a function of the injected origin.
11. **Honest bound, stated inline everywhere it matters (security S3):** issuance is a single admin trust domain, but the completeness commitment is externally anchored (§6.7) so the operator IS bound against omission/rollback. Propagate this scope verbatim into §1 and §13 — do not assert an unqualified "we can name who did it." The residual out-of-scope adversary: one who compromises BOTH the issuing admin key AND the external anchor simultaneously.

---

## 7. Legal framing (split; evidence pack pure, note firewalled)

1. The EVIDENCE PACK emits only mechanically-true, reproducible facts: verified sender key + enrolment provenance, chain/signature verification result, externally-anchored completeness proof, which corroboration checks failed (mechanically, origin-independent §6.10), neutral cited-rule text. NO `candidate_origin`, NO confidence, NO `fault_weight` conclusion, NO "attacker" label. Header: "Provenance record; not a determination of legal fault."
2. `technical_causal_chain` (which verified input drove which decision) is separated from `legal_causation: NOT_ASSESSED` (foreseeability/novus-actus/remoteness are the court's).
3. Every cited rule carries `binding_statute` vs `advisory_highway_code` (+ RTA s.38(7) note), source-provenance (primary/secondary), an as-at date, and the KB caveat verbatim. Never assert "hard_law" as a conclusion. A pinned legal-currency review date with a fail-loud staleness gate.
4. The SLM internal note (candidate_origin, reasoning) is explicitly NON-EVIDENTIAL, restricted-distribution, firewalled from the pack AND from the reviewer's first look (raw provenance first, to avoid automation bias), and covered by legal privilege framing (internal work-product, not an auto-emitted conclusion).
5. Conflicting-green = a FACTUAL detection only; legal characterisation `NOT_ASSESSED` (Bird v Pearce vs Gorringe/Stovin/Poole is unsettled). Confidence attaches to the detection, never to the law. TfL is the London authority entity.
6. `attacker-key` / criminal-implying language never appears in an auto-emitted shareable field (Defamation Act; UK GDPR Art 10 criminal-offence data; Art 22 automated decision). Meaningful human review defined: competent + empowered reviewer, sees raw provenance first, records independent reasons, logged override-rate KPI. No consequential action on the note alone.
7. GDPR: personal data off-chain only; the external anchor stores a Merkle ROOT over off-chain records (NO per-record personal-data hash); per-record secret salt destroyed on erasure; retained under Art 17(3)(b)/(e) exemption with a documented balancing test + Art 6(1)(e) public-task basis; DPIA records residual re-linkability. Drop any "Art 17 satisfied by salted hash" claim.

---

## 8. Experiments (the ONE valid protocol)

**Experiment D (the headline, the coupling / no-free-lie property):**
- Construct a family of **conservation-consistent** lies (residual below the INDEPENDENTLY-CALIBRATED detection threshold — the threshold is set from the honest CUSUM operating point at a fixed FP budget WITHOUT reference to the attack set; report the residual distribution vs that threshold) parameterised by **physical impact** (green-time stolen, EV delay induced). Do NOT claim "recall collapses" (that is tautological by construction, methods F1); instead state: there exists a lie family whose residual stays sub-threshold yet whose physical impact is unbounded — the stealthy class. Cite + explicitly beat the FDI prior art; detectability is SETUP, not the contribution.
- **The coupling result (the novel object):** for each stealthy lie, show it can only pass corroboration if the operator suppresses ≥1 independently-signed sighting; then show that under the §6.7 externally-anchored completeness commitment such suppression is externally DETECTABLE. Report, over the attack family, the fraction that is (a) caught live by corroboration, (b) not caught live but leaves an anchored-detectable suppression trace, (c) NEITHER (the "free lie" region — target: empty, or a stated, bounded, honestly-reported residual). Prove the UNION of all live checks (conservation + CUSUM + corroboration) has recall below a stated bound on class (a)'s complement, so a lie caught by corroboration is NOT counted in the undetectable class (methods M9).
- **Origin classification (the hard measured object, methods F2):** the primary forensic metric is 7-way origin-classification accuracy vs the injected latent cause, reported as a FULL CONFUSION MATRIX, foregrounding authentic-lie vs honest-sensor vs detector-error confusions. Crypto attribute-to-key is reported separately as a ~100% verification check, labelled "verification, not contribution."
- Region size is reported as a FRACTION of the physically-realizable attack space (threshold fixed at its FP budget, impact axis bounded by physical max — not a free knob, methods M8). Specify which component each lie defeats (methods M9). Report which component (conservation vs full gate incl corroboration) each result isolates (no conflation).

**The frozen-is-safer result (SLM load-bearing, novelty M4):** run a data-poisoning attack against a continual-learning baseline and MEASURE the robustness advantage of the frozen SLM (attack success / drift under poisoning, frozen vs adapting). This gives the mandatory SLM a measured contribution to the thesis beyond the note.

**SLM KILL / DEMOTE criterion (pre-committed before any run, methods F4):** if the SLM neither (i) strictly dominates the graceful-fallback template on Job-A citation-correctness + coverage on settled-law NOVEL cases at an acceptable false-citation rate, NOR (ii) shows below-MDE equivalence on Job B, NOR (iii) shows a measured frozen-is-safer advantage — then the SLM's CLAIM is demoted to "characterised, not advantageous" and the thesis leans on the coupling alone. The SLM stays in the system (locked); only its claim moves. State this before the run so the design is falsifiable.

**Experiment 1 (Job B classifier), de-circularised (methods F3):**
- Ground truth from SUMO incident injections: the injector sets the latent real/phantom flag; a noisy sensing process generates observable evidence with genuine CLASS OVERLAP. **Pre-register the noise params before any SLM result.**
- Report the accuracy CEILING of (i) the baseline's EXACT function class — axis-aligned conjunctions (the `rule_disambiguator` is a box, not a monotone threshold), dev-tuned — and (ii) the unrestricted Bayes-optimal NONLINEAR classifier. Judge the SLM vs the NONLINEAR ceiling, so any margin is visibly a fraction of a built-in ceiling, not a rigged win.
- Define the dev/test and anticipated/novel split by a **classifier-INDEPENDENT OOD criterion** (distance from dev support), pre-registered — NOT by "where a reasoner could plausibly generalise" (that is SLM-favourable authoring).
- Disjoint dev/test seed splits IN CODE; tune rule + freeze prompt on dev only; git-hash-SEAL the test labels; `evaluate` once on test; log + flag every test eval; cap dev prompt revisions (methods M2).
- NO threshold-DEFINING constant in the SLM prompt (assert this, not "no numeric" — legit evidence numbers like 0.40 must pass, build B4); ban labelled few-shots + comparative bands that leak the boundary; strip/qualitativise the 0.40/1.80 few-shot residuals; an independent reviewer confirms no leak (methods M1).
- `real_model=true`: pin + assert model hash + quant + Foundry version; abort on mismatch. `parse_failures` COUNT AS a classification failure (primary metric), never folded into a safe default; report FP jointly with recall (methods M3). Memoise only at 100% agreement; below that report accuracy as a distribution (methods M10).
- Stats: n≥30 independent seeds; paired SLM-minus-rule deltas; BCa + paired permutation + Holm across {accuracy, F1, false-preemption} × {anticipated, novel}; a **pre-registered numeric MDE** (seconds EV delay / FP%) with a CONSERVATIVE piloted SD (not from n≤3); power=0.8, Holm-adjusted alpha → derived n; a TOST equivalence test; declare a null ONLY when CI half-width < MDE (else "underpowered"). Determinism N≥100 across restarts.

**Experiment 2 (demand sweep):** full 30 seeds × 8 scales (0.3-3.0), longer horizon to steady state, all controllers; four-family fairness + worst-case + throughput; **coordination effect** = the coordination term TOGGLED with all else fixed — but state plainly it is currently a STRUCTURAL ZERO (an inert term), not an empirical null; measuring a real effect needs a LIVE term = a different system than 31/16/8 (methods M6). Rename the confounded `defended - maxpressure_preempt` to "combined defended-stack effect". No-harm as a pre-registered acceptance criterion (reported even if it regresses); no CI below n≈20.

**Substrate:** Euston (§9); demand calibrated to a NAMED, TIME-RESOLVED source (TfL/DfT — hourly profile + turning counts + vehicle mix, NOT a bare AADT daily total, methods M7); calibration is a startup gate that aborts or flags "uncalibrated synthetic" if the source is absent, and is a hard gate for any inferential claim. Every number labelled relative-in-SUMO.

---

## 9. Euston substrate (pre-built, committed, never regenerated at build time)

Literal build parameters live in a committed companion file `euston-build.md` (authored during the prerequisite phase, NOT overnight-blind) that MUST pin, as concrete values not placeholders (build B6): exact bbox lat/lon; the full literal `netconvert` command incl `--tls.guess/--tls.join` decisions; the expected TLS count + in-edge count (asserted). Pre-build BY HAND and COMMIT `euston.net.xml` + `edge_ids.json` (the single source of edge ids). The overnight builder MUST NOT call `osmGet`. `edge_map_from_net(mode="chain")` hard-errors on the non-chain Euston topology; derive the map from `net.getEdges()`/connections and assert coverage of every TLS-controlled in-edge. Conflicting-green detector uses `traci.trafficlight.getControlledLinks()` + phase state; ship a fixture net with a known conflicting phase + a known safe phase. Pin the sumocfg collision flags; ship a forced-collision + forced-hard-brake fixture asserting detection fires at the known tick and nowhere else.

**`ground_rules.yaml` schema (pin per-rule fields, build B6):** `{id, source: primary|secondary, statute_ref, binding: MUST|should, text, applies_when, fault_weight}`, each `statute_ref` cross-linked to a `uk-traffic-law.md` id with a pinned id format. **Exp-1 injector spec (pin, build B6):** the feature-vector schema, the noise model + params, the label file format, and the target Bayes-error floor — all before the phase runs.

---

## 10. Fail-loud gates (each SCOPE-LOCAL; SKIP-with-record when its precondition is absent, ABORT only that step, never the whole run)

- Real-model gate: Foundry reachable + one real structured call returns parseable output → else the SLM experiment is SKIPPED-and-marked, other work proceeds.
- Corpus gate: `ground_rules.yaml` non-empty + every P1-P8 + cited statute indexed → else Job A / Exp4 SKIPPED.
- Net gate: every scenario/label edge id resolves in `euston.net.xml`; `edge_map` covers all TLS in-edges → else Euston experiments SKIPPED (corridor fixtures still run).
- **Anchor gate: any no-free-lie / non-equivocation / "externally-anchored" claim requires a REAL external anchor write that the operator cannot silently rewrite; a mock/in-memory anchor is labelled "not externally anchored" and CANNOT back the coupling claim (never presented as such).**
- Per-run: `slm_calls_ok/total` above threshold; the decider on SLM-measured rows is actually `slm`; every attributed record passed signature + chain + completeness verification; a fault report over an incomplete window returns `INCOMPLETE_DISCLOSURE`.
- Doc + corridor work is gated on NONE of Foundry/Euston/corpus/anchor.

---

## 11. Build order

**Prerequisite artifacts (pre-built during the hardening phase, NOT overnight-blind):** `euston.net.xml` + `edge_ids.json` + `euston-build.md` literals (§9); `ground_rules.yaml` (schema §9, P1-P8 cross-linked to `uk-traffic-law.md`) + a citation oracle; the SUMO-injection non-circular labelled dataset with the pre-registered noise model (§8 Exp 1); **the real external anchor endpoint** (transparency-log or single-node external ledger) reachable for the anchored runs.

**Pinned schemas the overnight build MUST use verbatim (build FATAL-1, single source, supersedes TEST-AUDIT §1.1):**
- message: `{kind:"message", seq, sender, sender_pubkey_fpr, signed_payload:{sender,t,payload}, sender_signature}`
- sighting: `{kind:"sighting", seq, sighter_key, ev_id, approach, t, position, signature}`
- decision: `{kind:"decision", seq, driving_input_seq, classification, policies_applied}`
- registry: `{kind:"registry", seq, entity_id, key_fingerprint, action:enrol|rotate|revoke, self_sig, incumbent_countersig?, admin_sig}`
- ORIGIN enum (exact strings): `attacker-key`, `system-classifier`, `system-detector`, `sensor-fed-spoof`, `colluding-keys`, `legitimate`, `unknown`; each with a trigger predicate + the `ground_truth` field the fault engine reads.

**Honest overnight subset (no Foundry/Euston/OSM/anchor dependence):**
1. Doc remediation over the full §5 manifest (incl spec.md §1 overview + SC-005 + TEST-AUDIT §3.3 + GROUND-RULES §F amendment); D1 grep runs LAST as the gate.
2. Message + sighting record schema + `kind:"message"`/`kind:"sighting"` emission in the live seam (§6.1/6.2/6.6); log each `bus.inbox` message in `_drain_audit` + stamp the driving seq (build B2).
3. Rewire `fault_attribution` to the real AuditLog: rename to `assessment`/ORIGIN with the pinned enum strings, add `sensor-fed-spoof` + `legitimate` + `sensor-fed-spoof` trigger, the `flatten` adapter, enforce `identity.verify` + `verify_chain` before attributing, wire the dead `_audit_bundle` cross-check with the registry pubkey dict (§6.3), the E2 direction + tie-break (§3), the completeness commitment check (§6.7). Atomically replace `sig_valid` across module + tests + doc; the new test runs over a CONSTRUCTED real AuditLog and refuses on a tampered signature (build B7, FATAL-2).
4. Fix `slm_agent.py` as a STATIC edit ONLY: strip the "1.0 = the limit" threshold + threshold-shaped few-shots (qualitativise the 0.40/1.80 residuals), raise `max_tokens`, drop the no-CoT stance + deleted-brief ref; add the Job-A structured output SHAPE (incl `legitimate`). Job-A CONTENT runs are deferred (corpus-gated), build B4.
5. Anti-starvation shield invariant + forced-skip unit test: pin the counter `anti_starvation_violations`, the max-skip bound, the hook point (base `ShieldController.step`), and an adversarial forced-skip scenario that cannot be written tautologically (build B3). Deterministic, no SLM.
6. Foundry determinism probe as SKIP-not-abort (record `real_model` + determinism if up; else write a `skipped` result).

**OUT of the overnight subset (require prerequisite artifacts / real runs / the real anchor; do NOT attempt blind):** Euston experiments; Job A / Exp4 citation-CONTENT runs; SUMO-injection-labelled Experiment 1; Experiment D (coupling) full run + the anchored completeness runs; the frozen-is-safer poisoning experiment; exploit-defend / D8; the 30-seed powered runs. The real external anchor integration is its own scoped task. T10/T11 stay documented-xfail.

---

## 12. Acceptance tests (all binary; all required for distinction)

- D1 one-thesis-one-tree: full §5 manifest clean (neutralised or scope-excluded with reason; incl "detectability envelope/ROC"); one thesis sentence across live docs incl `spec.md` §1 overview + SC-005. Grep runs last.
- D2 fault language = split; the shareable pack has no verdict/confidence/accusation; citation selection is origin-INDEPENDENT (a test proves the cited-rule set is not a function of the injected origin, S4); the SLM note is classed non-evidential + firewalled; a test fails if any shareable field carries an origin verdict.
- D3 `real_model=true` guard: a deliberately misconfigured run ABORTS/SKIPS-with-record, never emits a null.
- D4 Experiment 1 run, powered, pre-registered: result file with CIs + a computed numeric MDE + TOST; dev/test split enforced in code + git-hash-sealed labels; classifier-independent OOD split; the axis-aligned-conjunction ceiling AND the nonlinear Bayes ceiling both reported; no threshold-defining constant in prompt (asserted); parse-failures counted as failures.
- D5 non-circular labels (Bayes-error floor > 0) + the SLM judged vs the NONLINEAR ceiling + Job-A vs the graceful-fallback template scored on citation CORRECTNESS on novel combinations + the SLM false-citation rate reported.
- **D6 Experiment D figure (the coupling):** the stealthy conservation-consistent class on the physical-impact axis (residual vs the independently-calibrated threshold) + the three-way partition {caught live / anchored-detectable suppression trace / free-lie residual} + the **7-way origin-classification CONFUSION MATRIX** vs injected latent cause. Crypto attribute-to-key reported separately as a verification check, not the headline.
- **D-anchor: the completeness commitment is written to a REAL external anchor; a run with only a mock anchor is labelled "not externally anchored" and its no-free-lie claim is refused (fail-loud), never presented as green.**
- **D-SLM-kill: the pre-committed SLM kill/demote criterion is evaluated and reported either way; the SLM stays in the system regardless (locked).**
- D7 anti-starvation: `anti_starvation_violations == 0` across the attacked n=30 matrix; forced-skip test triggers the override.
- D8 honest demand sweep + fairness + worst-case, all modes, one CI method; coordination toggle result reported as a structural zero (not an empirical null).
- D-sec: fault engine verifies signatures + chain + completeness before attributing; the framing attack (operator re-registration) is defeated by enrolment self-sig + counter-signed rotation; a spoofed keyless-local-sensing incident attributes to `sensor-fed-spoof` (not the AI) and is marked "corroboration not key-attributable"; the tie-break (signed+uncorroborated+harmful → `attacker-key`) matches the T3 worked example; the evidence pack cites real UK statutes with source-tag + as-at date + the not-a-legal-determination header.
- **Policy-KPI rule (fixes C1):** the empty-`policies_applied` abort gate applies to DETERMINISTIC decision records only; the SLM Job-A note is exempt (non-evidential, carries `cited_rules`, not P1-P8). The exemption is LANDED in GROUND-RULES §F + TEST-SPEC (N2), not merely asserted here.
- Tests: T1-T9 pass-required; T10/T11 documented-xfail (one place, no contradiction).

---

## 13. The viva sentence this spec must make true

"My contribution is a coupling. There is a bounded class of stealthy, conservation-consistent lies my deterministic real-time gate provably cannot catch. My claim is that a lie in that class cannot be both invisible live and untraceable afterwards: to pass the gate it must stay corroboration-consistent, and to escape accountability the operator must suppress the very independently-signed sightings that corroborated it, but under a completeness commitment written to a real external anchor the operator cannot silently rewrite, that suppression is externally detectable, and those same sightings are what corroboration checks against live. So every such lie is either caught live or leaves an un-erasable, externally-witnessed trace, and from the complete verified trace a human inquiry can classify its origin — reported as a seven-way confusion matrix against ground truth, not as a signature lookup — against cited UK law. The evidence pack states only cryptographically-verified, externally-anchored facts and selects citations origin-independently; it does not adjudicate fault, that is the court's. A frozen on-device SLM writes the internal, non-evidential origin note, characterised for citation-faithfulness against statute with a pre-committed kill criterion, and I separately measure that freezing it resists a data-poisoning attack a continually-learning model does not. Coordination and traffic optimisation are not my claims; the trust coupling is." Every clause backed by a run that passed its §12 gate, or it is not settled.
