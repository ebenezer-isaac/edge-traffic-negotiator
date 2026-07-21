# The Edge Negotiator: Master Build & Experiment Specification (v4)

**Status**: CANONICAL, frozen for direction. Consolidates four adversarial teardowns (round 2 vs the docs, round 3 vs v1, round 4 vs v2, round 5 vs v3). Single document Fable builds from.

**v4 CHANGELOG (2026-07-21, user-approved honest-framing recalibration + round-5 Bucket-A fixes):**
- **Contribution reframed to an HONEST CONDITIONAL GUARANTEE + CHARACTERISATION** (user decision 2026-07-21). Round-5 showed, via three independent reviewers, that (i) the accountability mechanism is textbook Certificate Transparency + accountability, and (ii) the *unconditional* "no-free-lie" claim is provably false against a colluding-key / operator-omission insider. So: the mechanism is CONCEDED as CT-style and cited head-on; the coupling is stated as an explicitly CONDITIONAL theorem; and the real contribution is the **characterisation** — the first quantified map of which stealthy insider attacks this coordination layer resists vs fails on a real London corridor. This is a *tightening* of the v3 coupling, not a new pivot: coordination, the SLM, the UK-law pipeline, and the coupling all stay; only the strength of one security claim changes (unconditional → conditional + measured).
- **"Lie" → "deviation"** throughout the headline (legal M5): the confusion matrix exists *because* lie-vs-error is confusable, so the claim must not prejudge dishonesty.
- **Anchor upgraded from single external witness to a QUORUM / gossip anchor** (≥2 independent witnesses; novelty M1, security F1): a single-node anchor is reachable by the operator-adjacent adversary.
- Round-5 Bucket-A no-regret fixes folded throughout (pin the record *producer* not just the shape; sever the confusion-matrix scoring label from the engine input; pin the attack grid incl collusion-degree + witness-density; external identity root for enrolment; GDPR payload minimisation; the unscheduled doc rewrites; the SLM kill-criterion against a fair defended baseline). Full ledger in `_hardening-log.md`.

**BUILD-TARGET NOTICE (read first):** this spec describes the INTENDED built system. A claim is *not settled* until its §12 acceptance gate passes over a real run. Sections describing unbuilt behaviour (§1(b)/(c), §3, §6, §8, §9) are targets ("must become"), not statements about current code. The current code is the pre-teardown state; §5 + §11 are the path to conform it. Do not quote any number or capability as achieved until its gate is green.

**Golden rule:** fail loud, never degrade silently. Any gate that cannot prove its precondition (real model answered, corpus retrieved, edges resolved, signatures verified, quorum-anchored) must SKIP-with-a-recorded-skip or ABORT that specific step, never emit a green result. A fake-green null is worse than a crash; this project has produced one before.

---

## 0. Locked constraints (user decisions; do NOT overturn without consulting the user)

- SLM is a REQUIRED component (its job is defined below so it is load-bearing and honestly measured). A pre-committed kill-criterion (§8) may demote the SLM's CLAIM, never its presence.
- Substrate: real **Euston Road (A501)**, short 3-4 signal stretch. Pre-built and committed, never regenerated at build time (§9). The synthetic corridor is retained only as a unit-test fixture.
- Fault rules grounded in cited UK law (`01-research/uk-traffic-law.md`).
- **Fault output = SPLIT** (2026-07-16): a mechanically-verifiable PROVENANCE evidence pack (closed forensic channel, NO machine verdict, NO confidence, NO accusation, mechanical origin-independent rule citation) + a firewalled, NON-EVIDENTIAL, counsel-gated internal AI triage note (origin reasoning, shown to a reviewer only AFTER the raw provenance).
- **Novel object = the DUALITY, expressed as an HONEST CONDITIONAL COUPLING + a CHARACTERISATION** (2026-07-21, supersedes the unconditional v3 wording): characterise the bounded class of stealthy, conservation-consistent DEVIATIONS the real-time gate provably cannot detect (measured on the physical-impact axis), and prove the **conditional coupling**: *no covertly-effective deviation is both undetectable live AND untraceable after, CONDITIONAL ON (a) its corroboration being sourced only from honest independent keys, and (b) a non-equivocating quorum/gossip anchor.* The contribution is NOT the mechanism (conceded to be Certificate-Transparency-style accountability, cited) — it is the **quantified map** of exactly where that conditional holds and where it fails (colluding keys, operator creation-time omission, witness-density → 0), on a real London corridor, with a frozen SLM as the auditable reasoner.
- **A QUORUM / gossip anchor is MANDATORY for any non-equivocation claim** (2026-07-21): ≥2 independent external witnesses the operator cannot jointly rewrite. A single-node or mock anchor CANNOT back the conditional coupling and must be labelled "not externally anchored."
- Deadline August 2026; scope phased, not cut.

---

## 1. The one thesis (frozen)

> An on-device, trust-preserving coordination layer for signalised junctions, and a **characterisation** of exactly which stealthy insider attacks it can and cannot hold accountable. Contribution: (a) a deterministic real-time gate that refuses signed-but-uncorroborated emergency preemption from a compromised insider and clears physically-corroborated real emergencies; (b) a Certificate-Transparency-style, quorum-anchored, signature-verified accountability log (mechanism conceded to prior art, cited); and (c) the novel object — a quantified map of the bounded class of stealthy conservation-consistent deviations the gate cannot catch in real time, together with an explicitly **conditional coupling**: no such deviation is both undetectable live and untraceable afterwards *provided* its corroboration comes only from honest independent keys and the anchor is a non-equivocating quorum. The map measures, as first-class results, exactly where that proviso fails (two colluding keys manufacturing corroboration; an operator omitting a record before anchoring; vanishing witness density) — the honest boundary is the finding. A frozen on-device SLM is the mandatory reasoner that turns the verified, quorum-complete audit window + retrieved statute into a non-evidential, counsel-gated origin-classification note, evaluated for citation-faithfulness and for a measured frozen-vs-adaptive robustness/adaptivity tradeoff.

**Lead with (the novel object):** the **characterisation** — the measured map of the stealthy-deviation class (physical-impact axis) and the conditional coupling's *boundary* (where collusion / operator-omission / low witness-density break it), on the real Euston corridor. NOT "a novel security mechanism," NOT "a detectability ROC," NOT "the SLM beats a rule," NOT "coordination optimises traffic."

**Position vs prior art (concede head-on, do not claim the mechanism):** the accountability layer IS a Certificate-Transparency / tamper-evident-log / accountability construction — RFC 6962 (Laurie et al 2013), CONIKS (Melara 2015), A2M (Chun SOSP 2007), TrInc (Levin NSDI 2009), PeerReview (Haeberlen SOSP 2007), Haber-Stornetta 1991, Schneier-Kelsey 1999, Küsters-Truderung-Vogt CCS 2010. The stealthy-deviation class is textbook FDI — Liu-Ning-Reiter 2011, Teixeira-Sandberg 2015, Mo-Sinopoli 2010; collusion against TSC — Qu-Tang-Ma (arXiv 2111.02845); non-repudiation ≠ truthfulness — Li-Nejad-Zhang (arXiv 1906.02628). **The increment is (a) the conditional coupling stated and proven with explicit assumptions, and (b) the first quantified measurement of its boundary on a real signalised corridor tied to cited UK statute** — an application/measurement contribution, honestly labelled as such. Confront Traffic-R1 (differentiator = the accountability role + the measured boundary, not raw TSC skill or "small/frozen").

**SLM (mandatory) role:** the reasoner for the post-hoc **internal origin-classification note** (Job A) and the honestly-characterised disambiguation classifier (Job B), plus a measured **robustness/adaptivity tradeoff** (Job C: frozen vs a hardened continual-learner under poisoning). Its claim is falsifiable via a pre-committed kill-criterion (§8); the SLM stays in the system regardless.

---

## 2. Single Source of Truth (freeze; every live doc conforms)

| Item | Frozen value |
|---|---|
| Headline / novel object | The CHARACTERISATION: the measured map of the stealthy conservation-consistent deviation class + the conditional coupling and its failure boundary (collusion / operator-omission / witness-density), on Euston A501 |
| Mechanism basis | Certificate-Transparency-style quorum-anchored accountability log — CONCEDED to prior art (RFC 6962 et al), cited, NOT claimed novel |
| Fault output | SPLIT: mechanically-verifiable provenance pack (no verdict/confidence/accusation; mechanical origin-independent citation; closed forensic channel) + firewalled, non-evidential, counsel-gated internal AI note |
| SLM role | Mandatory; Job A = counsel-gated origin-note reasoner; Job B = characterised disambiguation classifier; Job C = measured frozen-vs-hardened-continual robustness/adaptivity tradeoff; not the load-bearing real-time defence |
| Real-time defence | Deterministic Ed25519 auth + conservation/CUSUM + corroboration gate |
| Model | Phi-4-mini, 3.8B, frozen, Foundry Local |
| Deploy target | Foundry Local in SUMO; Jetson/INT4 = future hardware-in-loop only |
| Ledger | Signed hash-chained AuditLog + a QUORUM/gossip external anchor (≥2 independent witnesses) for the monotonic completeness commitment + first-party signed per-signer emission counts. Completeness ≠ integrity: the anchor holds only under the stated conditional (§6.7). |
| **Substrate** | **Euston Road (A501) 3-4 signal stretch, pre-built & committed; synthetic corridor = fixture only; Lambeth dropped** |
| Fault attribution ontology | Origin over the audit log: `attacker-key` / `system-classifier` / `system-detector` / `sensor-fed-spoof` / `colluding-keys` / `legitimate` / `unknown`. Lives in the INTERNAL note, never in the shareable pack. Where the origin is a signing party it names a KEY, never a person. |
| Origin classification (the hard object) | 7-way origin classification vs the injected latent cause, reported as a full CONFUSION MATRIX. The scoring label is SEVERED from any field the engine/SLM reads (§3). Crypto attribute-to-key is a separate ~100% verification CHECK, explicitly NOT the contribution. |
| Evidence pack content | verified sender key + enrolment provenance + chain/signature verification + quorum-completeness proof + which corroboration checks failed (mechanical, origin-independent) + neutral cited-rule text (mechanical selection, source-tagged, as-at date, secondary sources flagged "reference only"). No origin verdict, no confidence, no "attacker"/"lie" label. |
| CoT / reasoning | The internal note DOES contain reasoning; VALIDATED against cited statute, never trusted; raise `max_tokens`. Non-evidential, firewalled, counsel-gated. |
| RAG | policy text retrieved into the prompt from `ground_rules.yaml` + `uk-traffic-law.md`; small curated corpus; fail-loud if empty; not the Qdrant experience-store |
| Coordination effect | a STRUCTURAL ZERO (inert term); reported as such, NOT framed as an empirical experiment (§8) |
| EV benefit (StubAgent demo, deterministic gate, n=30) | 31.1 s [25.4, 36.5] (preemption on vs off; NOT coordination, NOT SLM) |
| Gate cost (StubAgent demo) | 8.0 s [3.7, 12.5] · Worst-case harm avoided 16.05 s [11.51, 20.44] · **Mean harm avoided 4.63 s [3.25, 5.99]** |
| Seeds / determinism | n≥30 for any inferential claim (current exp1 n=1 / exp2 n=3 = pilots); determinism N=100 across restarts |
| STSD coursework | superseded; in-body stale claims to be NEUTRALISED (target-state, per §5) |

---

## 3. The SLM (mandatory): jobs, all non-circular

**Job A — counsel-gated origin-classification note reasoner.** Given the *cryptographically-verified AND quorum-complete* audit window + retrieved statute, the SLM writes the **internal, non-evidential** note:
```
{ candidate_origin: attacker-key|system-classifier|system-detector|sensor-fed-spoof|colluding-keys|legitimate|unknown,
  cited_rules: ["RTA1988-s36", ...],   // ids resolvable in ground_rules.yaml/uk-traffic-law.md
  reasoning: "<=120 words linking VERIFIED facts to cited rules>",
  fault_weight_note: "MUST-rule (statute) | should-rule (advisory, RTA s.38(7))" }
```
Firewalled from the pack (§7); shown to a reviewer only after raw provenance; in a real deployment generated only under counsel once litigation is genuinely contemplated (legal §7.4). For the dissertation's evaluation it runs on incidents to produce the characterisation dataset, explicitly labelled non-evidential.

**Primary metric = 7-way origin-classification accuracy vs the injected latent cause, as a full CONFUSION MATRIX** — with the scoring label SEVERED from any field the engine/SLM reads (the injector's `ground_truth` is used ONLY to score, NEVER in the prompt or the engine input; methods F1). The engine's origin decision uses ONLY an enumerated set of verified-provenance features (§6.4). Pin the injected class PRIOR (balanced or an operationally-justified prior); report per-class precision/recall AND a SEPARATE accuracy restricted to the hard triad {authentic-deviation, honest-sensor-error, detector-error}, each with its own MDE and a stated minimum that can FAIL D6 (methods F2). Pairs provably non-separable from provenance are pre-declared and forced to `unknown`, never scored as wins. Also measured: citation-correctness vs held-out applicable-rule labels (annotator blind to the retrieved set), gated on 2-rater Cohen's kappa ≥ 0.6 else NOT_ASSESSED (methods M8); **faithfulness graded against STATUTE TEXT by qualified human raters (no LLM-as-judge — circular)**, reported on settled-law AND (as a proxy, or NOT_ASSESSED-with-reason) on novel combos (methods M9); the **SLM false-citation rate** on novel combos as a PRIMARY number (Dahl et al 2024).

**Job A baseline = a deterministic rule-to-text template WITH a graceful fallback** ("nearest applicable rule; no exact match"). Coverage scored by citation CORRECTNESS, not presence. Pin the numeric false-citation ceiling and the exact dominance rule (both-metrics, tie-handling) before the run (methods M10). A distinction-grade result may be "honest template abstention beats confident SLM hallucination." A citation whose supporting fact lacks verified provenance is a validation FAILURE (anti prompt-injection, §6/E6).

**Job B — disambiguation classifier**, characterised under §8. Win-or-a-powered-null; the thesis does not hang on it.

**Job C — robustness/adaptivity tradeoff.** Measure the frozen SLM vs a **hardened** continual-learner (with standard poisoning defenses — TRIM Jagielski S&P 2018; Steinhardt-Koh-Liang NeurIPS 2017) under a fully-specified poisoning threat model (channel, budget, objective), reporting BOTH the robustness gain of freezing AND its adaptivity loss under distribution shift, with the same n/MDE/CI/pre-registration as Exp1 (methods F6). A naive undefended learner is NOT an acceptable baseline.

**The E2 rule (attribution direction) + tie-break:** a validly-signed, uncorroborated claim that caused harm → the **sender key** (`attacker-key`); this WINS the tie against the "catchable phantom" branch (signed + zero-corroboration + harmful → `attacker-key`). `system-classifier`/`system-detector` require proof the AI erred on a WELL-EVIDENCED case vs ground truth. A frozen read-only worked-example fixture (input records → expected origin string, authored pre-overnight) pins the expected verdict (build MAJOR-7). Verdict inputs come ONLY from cryptographically-verified provenance; corroboration is RECOMPUTED from independently-signed sighting records (§6.6), never a self-asserted scalar.

---

## 4. Architecture

```
default -> MaxPressure (+ coordination term, INERT structural zero; not an experiment)     safety floor
   trigger (EV sensed | advance claim | conservation anomaly | incident | conflicting-green)
      -> deterministic gate: Ed25519 auth + registry + conservation/CUSUM + corroboration  <- real-time defence
           advance-claim ambiguous middle -> disambiguator (rule or SLM Job B, withhold-only)
      -> shield: min/max green, clearance, ANTI-STARVATION (MaxPressureController.step)      safety invariants
   every message + signed sighting + decision -> AuditLog (sender-signature + hash-chain)
   batch -> monotonic completeness commitment + first-party per-signer counts
         -> QUORUM external anchor (>=2 independent witnesses) so equivocation is externally detectable
   incident/stealthy-deviation post-hoc -> verify chain+signatures+quorum-completeness -> EVIDENCE PACK (provenance)
                                        -> SLM Job A internal note (origin + cited law), firewalled + counsel-gated
```

---

## 5. Consistency remediation (D1; gates everything)

1. Generate the **full forbidden-term manifest** with `grep -rl` (blockchain, liability, verdict, decentralis(z)ed, optimization, Iroha, "EU AI Act", **"detectability envelope"/"detectability ROC"**). Conform ALL. Terms inside a quotation of prior work are allowed.
2. Pin ONE canonical banner string. **Neutralise the STSD coursework in-body claims** (EU-AI-Act → "voluntary benchmark", delete "60ms", blockchain → signed log + quorum anchor, decentralised-optimisation → the current thesis). A banner alone does NOT satisfy D1; the D1 grep runs LAST over the manifest; a quarantined file must be neutralised or explicitly excluded via a **verbatim allowlist** (§12 D1), never free-text.
3. Fix the v1 contradictions (resolved): C1 policies (§12); C2 `colluding-keys` kept (§2); C3 anchor is CT-style + cited, not "novel"; C4 SSOT complete.
4. Propagate the §6.1 signature record into `TEST-AUDIT-FAULT-SPEC.md §1.1` (delete `sig_valid:bool`) AND conform TEST-AUDIT Part 2's ORIGIN enum to §2 (lowercase-kebab, add `sensor-fed-spoof` + `legitimate`, the E2 direction) (N5).
5. **Rewrite the thesis sentence across ALL live docs** to the §1 characterisation framing — `spec.md` §1 overview + SC-001 + SC-005; `TEST-AUDIT §3.3(c)` (→ physical-impact axis); **the 05-supervision layer** (`PROJECT-STATUS-AND-PLAN.md`, `AKIN-research-survey-and-direction.md`, `FEEDBACK-RESPONSE-MATRIX.md`, `lee-progress-update.html`) and `report/edge-negotiator-report.tex`; **`PROJECT-PROPOSAL.md`:57/:82** ("detectability envelope" own-claim) — OR add dated supervisor snapshots to the D1 allowlist with a stated reason (consistency B3/B4). DEMO-REPORT: StubAgent + powered means only (8/16/4.63; single-seed outliers labelled). Remove the deleted `PROJECT-DECISION-BRIEF` ref + no-CoT + MaxPressure-selection prompt from `slm_agent.py`.
6. **Rewrite `spec.md` scenario 1 / FR-003/004 / SC-002**: "local sensing is strong but SPOOFABLE; a lone keyless local reading cannot force sustained preemption" (consistency B2, negates the old "cannot be spoofed").
7. **Land the GROUND-RULES §F + TEST-AUDIT amendment** so the "a decision citing no policy is a defect" rule EXEMPTS the SLM Job-A note (non-evidential, carries `cited_rules` not P1-P8) — currently GROUND-RULES:92 + TEST-AUDIT:39/127 state the unqualified defect; §12 must not claim this is "LANDED" until it is (consistency B1, the v3 false done-claim).

---

## 6. Security (accountability layer: cryptographic, quorum-anchored, wired, honestly bounded)

1. **Store the signable PREIMAGE, minimised** (security S5 + GDPR MAJOR-4). Message records carry `{kind:"message", seq, sender, sender_pubkey_fpr, sender_pubkey_der, signed_payload:{sender,t,payload_min}, sender_signature}` where `payload_min` is minimised to the NON-personal fields needed to verify + reason (no raw EV/vehicle identifiers or fine location beyond what the reasoning requires; assess against Art 9 in the DPIA), `sender_signature` is lowercase hex, and `sender_pubkey_der` is the 44-byte DER key (a fingerprint cannot verify). Verification is recomputable from the record alone: `identity.verify(sender_pubkey_der, canonical_bytes(sp["sender"], sp["t"], sp["payload_min"]), bytes.fromhex(sender_signature))` (build MAJOR-6/10).
2. **Wire the pipeline end-to-end, from the real PRODUCER** (build FATAL-1/2/3). Lift the no-edit rule for `CoordinatedController.decide` / `EmergencyController.decide` specifically: capture each `NeighborMessage` at consumption, emit a `kind:"message"` record (with its real `signature`), stamp the driving message's audit `seq` into the decision record's `driving_input_seq`, and emit `kind:"sighting"` (§6.6) + `kind:"decision" {seq, driving_input_seq, junction, t, classification, policies_applied}`. Add a `flatten(entries)->list[dict]` adapter that lifts `event.*` up AND remaps producer field names (`tls→junction`, `tick→t`), preserving envelope `seq`. Reconcile that `EmergencyController.ev_events` (source of false_preemption/missed_ev) is mirrored into the log. The item-3 acceptance test MUST consume the log produced by `IntegratedSystem(...).run()` (or an end-to-end `EmergencyController` run), NOT a hand-built dict.
3. **Verify crypto + quorum-completeness before attributing.** `fault_report` takes the AuditLog + registry pubkeys, runs `verify_chain()` once + `identity.verify(...)` per causal record + the §6.7 quorum-completeness proof, and refuses (`UNKNOWN`/`INCOMPLETE_DISCLOSURE` + abort flag) on any failure. The tamper test isolates `identity.verify`: swap `sender_signature` for a valid-form signature from the WRONG key while re-chaining so `verify_chain()==True`; only `identity.verify` can reject (build FATAL-4). Wire the dead `_audit_bundle` cross-check with the registry DER dict.
4. **Split sensor-spoof from detector-fault, by an EVIDENCE-DERIVED predicate** (build MAJOR-8). `sensor-fed-spoof` fires when a lone KEYLESS local sighting with NO second independent signed sighting forced sustained green; `system-detector` requires proof the detector erred on a well-evidenced case. The engine computes this from records; `ground_truth` is SCORING-ONLY. State plainly: the label is a POST-HOC forensic call; drop "local sensing cannot be spoofed."
5. **External identity root + counter-signed rotation** (security FATAL-2). An identity root EXTERNAL to the operator (manufacturer attestation key / CA / physically-witnessed enrolment ceremony) signs the genesis key→entity binding — "self-sign" alone only proves key-controls-key. Rotation/re-registration requires the incumbent key's counter-signature; recovery from a genuinely lost key requires an EXTERNAL quorum (specified concretely, §6.7), NOT a unilateral operator override (which would reopen the framing attack). The pack carries ENROLMENT provenance. State the availability cost explicitly.
6. **Corroboration = key-bound, sensor-backed, time-windowed, route-consistent** (security F1/S6/S8). Add a signed `kind:"sighting" {sighter_key, ev_id, approach, t, position, signature}`; corroboration is RECOMPUTED by walking these, so every corroborating signal is attributable to a key. A lone KEYLESS local reading may NOT be the independent corroboration forcing sustained green; otherwise the pack marks it "corroboration not key-attributable." Independence must be checked against a MEASURED, non-attacker-authored position source (security MAJOR-3); absent that, route-consistency is a plausibility filter only and adds no security against a colluder — state so. Reject stale sightings, expire `_sightings` on TTL, bind the per-claim nonce to `(ev_id, approach, time-window, claimer)` + route-consistency; persist the replay high-water-mark across restarts.
7. **Completeness via a QUORUM anchor; completeness ≠ integrity** (security FATAL-1, novelty FATAL-3/M1). Add a signed monotonic append-only commitment; write `(seq_high, merkle_root)` per batch to **≥2 independent external witnesses** (e.g. a Sigstore/Rekor transparency-log entry AND a second named single-node ledger RPC) the operator cannot jointly rewrite. A Merkle root proves PRESENCE, not ABSENCE — so ALSO require each signer to emit a first-party signed emission COUNT ("junction J asserts it emitted N messages this window"), gossiped to the quorum, reconciled against disclosed records; a mismatch is `INCOMPLETE_DISCLOSURE`. Bound the max unanchored window; treat any gap as `INCOMPLETE_DISCLOSURE`. State plainly, inline: this catches rollback/selective-disclosure and per-signer under-count, but **creation-time omission by a signer about its OWN never-emitted record, and a k-of-n colluding-key coalition, remain out of reach** — these are measured as the coupling's boundary (§8), not defended. A single-node or mock anchor CANNOT back the claim.
8. **Ship the flagged build items:** consecutive-spillback cap forcing a CUSUM window; payload size/field/depth bound at the bus; no preemption during detector warmup.
9. **Prompt-injection guard, content-vs-provenance** (security S7). Untrusted content enters the SLM prompt only as delimited NON-instruction context. The oracle distinguishes "field authentically LOGGED" from "content independently CORROBORATED"; attacker-authored free-text may not be a citation's sole support. Honestly bounded: under collusion (§6.6) a corroborating sighting can itself be an attacker key, so provenance-to-a-key ≠ truth — stated, not defended.
10. **Origin-independent citation selection** (security S4). The pack's failed-checks set and cited-rule selection are a mechanical, origin-INDEPENDENT function (cite every rule touching any present field); a test proves the citation set is not a function of the injected origin.
11. **Honest bound, stated inline in §1/§13** (security MAJOR-7). The conditional coupling holds against an adversary that (i) controls ONE corridor key and is NOT the operator, under (ii) a non-equivocating quorum anchor. The measured/ out-of-scope failure set — operator-alone creation-time omission, external-identity-root or quorum compromise, and any multi-key (colluding) insider — is the characterisation's boundary, reported, not claimed defended.

---

## 7. Legal framing (split; pack mechanically-verifiable, note counsel-gated; residual limits documented)

1. The EVIDENCE PACK emits only mechanically-true, reproducible facts: verified sender key + enrolment provenance, chain/signature/quorum-completeness verification results, which corroboration checks failed (mechanical, origin-independent §6.10), neutral cited-rule text (mechanical selection). NO `candidate_origin`, confidence, `fault_weight` conclusion, or "attacker"/"lie" label. Header: "Provenance record; not a determination of legal fault." Distribution is a CLOSED forensic channel, not "shareable/public."
2. `technical_causal_chain` (which verified input drove which decision) is separated from `legal_causation: NOT_ASSESSED`.
3. Every cited rule carries `binding_statute` vs `advisory_highway_code` (+ RTA s.38(7)), source-provenance, an as-at date, and the KB caveat verbatim; secondary-sourced or low-confidence rules are degraded to "reference only, verify against primary source" and excluded from any emission (legal m2). A pinned legal-currency review date with a fail-loud staleness gate.
4. The SLM note is NON-EVIDENTIAL, restricted, firewalled, and — in a real deployment — generated only under counsel once litigation is genuinely contemplated (the always-on auto-note is NOT privileged: Waugh v BRB [1980] AC 521; Three Rivers No 6; SFO v ENRC [2018] EWCA Civ 2006). For the dissertation it is generated for evaluation, labelled non-evidential. No consequential action on the note alone; meaningful human review = competent, empowered reviewer sees raw provenance first, records independent reasons, assembles their own record set (Art 22 / SCHUFA C-634/21).
5. Conflicting-green is reported as the PHYSICAL fact only ("simultaneous green on conflicting controlled links per `getControlledLinks`"); legal characterisation `NOT_ASSESSED` (Bird v Pearce vs Gorringe/Stovin/Poole BC v GN [2019] UKSC 25, added to the KB, is unsettled). TfL is the named controller/authority (A501 is TLRN; DPA 2018 s.8 public-task); a private edge operator would need Art 6(1)(f) + a documented LIA (legal M4).
6. Criminal-implying language never appears in an auto-emitted field (Defamation Act 2013 s.1; UK GDPR Art 10; DPA 2018 Sch 1 condition + Appropriate Policy Document required for any criminal-offence processing).
7. GDPR: personal data + salt strictly OFF-CHAIN under a bounded retention clock; the quorum anchor stores ONLY a Merkle root provably non-re-linkable without the off-chain secret (verify the preimage never enters the committed leaf identifiably); Art 17(3)(b)/(e) + Art 6(1)(e) with a documented balancing test; DPIA records residual re-linkability during retention.
8. **Documented residual legal LIMITATIONS (honest, not claimed solved):** curation-of-applicable-rules is itself an adjudicative act (R v Bates / Horizon reliability line) — mitigated by mechanical origin-independent citation + human assembly, not eliminated; the note's privilege status is deployment-dependent; the preimage's indefinite-retention-vs-erasure tension is bounded, not resolved.

---

## 8. Experiments (the ONE valid protocol)

**Experiment D (the headline, the characterisation + conditional coupling):**
- Construct a family of **conservation-consistent** deviations (residual below the INDEPENDENTLY-CALIBRATED threshold — set from the honest CUSUM operating point at a fixed, NUMERICALLY-PINNED FP budget WITHOUT reference to the attack set, and bound to the same real-calibration gate as inferential claims; report the residual distribution vs that threshold; methods M7). Parameterise by **physical impact** (green-time stolen, EV delay). Do NOT claim "recall collapses" (tautological). Cite + beat the FDI prior art; detectability is SETUP.
- **The conditional coupling, stated as a THEOREM with explicit assumptions** (methods F3): assumptions = (witness-density > 0) ∧ (corroboration from honest independent keys only) ∧ (non-equivocating quorum anchor). Under the assumptions, partition each deviation into {caught live by corroboration / leaves a quorum-detectable trace / free (neither)} and show the free region is empty. Then — the actual contribution — **VARY the assumptions as first-class attack axes** and MEASURE the free region as it grows: collusion-degree (k colluding keys), witness-density → 0, operator creation-time omission. Report the free-region fraction over a PRE-REGISTERED attack grid whose sampling measure INCLUDES collusion-degree and witness-density (not just the 2-D impact axes; methods F4), per cell, with the sampling distribution stated. The honest boundary is the finding.
- **Origin classification (the hard measured object):** 7-way accuracy vs the injected latent cause as a full CONFUSION MATRIX, scoring label SEVERED from engine input (§3), pinned class prior, hard-triad accuracy with its own MDE and a failing threshold (methods F1/F2). Crypto attribute-to-key reported separately as a ~100% verification check, labelled not-the-contribution. State explicitly: the matrix measures SLM reasoning CONDITIONAL on externally-supplied ground truth; the SYSTEM does not itself discriminate a real EV from collusively-fabricated corroboration (novelty MAJOR-2).

**Experiment 1 (Job B classifier), de-circularised:** SUMO-injection ground truth with genuine class overlap; pre-register the noise params before any SLM result. Report the accuracy CEILING of (i) the baseline's EXACT class — axis-aligned conjunctions, dev-tuned — and (ii) the unrestricted Bayes-optimal NONLINEAR classifier, computed ANALYTICALLY from the known injector forward model (not estimated), restricted to regions where injector density exceeds a pre-registered floor, MC error propagated into the CI (methods M2). Judge the SLM vs the nonlinear ceiling; pre-register an MDE for the ceiling-minus-SLM GAP. Define the novel/OOD split by a PRE-REGISTERED classifier-independent distance-from-dev-support criterion with the EXACT metric formula + dev-frozen standardisation + fixed-percentile threshold, and ALSO report accuracy as a CONTINUOUS curve vs distance so no threshold DOF exists (methods M1); do not call low-density-in-distribution "OOD". Disjoint dev/test splits in code; git-hash-SEAL the ENTIRE analysis bundle (noise params, OOD metric+threshold, prompt, MDE) under one hash before any test eval; global test-eval counter hard-capped at 1 (methods M5). NO threshold-DEFINING constant in the prompt (assert; legit evidence numbers pass); ban labelled few-shots + comparative bands; add a BEHAVIORAL leak test (SLM implied dev boundary coincides with the rule's box boundary = leak; methods M4). `real_model=true` hash/quant/version asserted; parse-failures COUNT AS failures, reported jointly with recall; decompose reasoning-accuracy-on-parseable vs end-to-end (methods M3); memoise only at 100% agreement else report a distribution (methods M10). Stats: n≥30; paired deltas; BCa + paired permutation + Holm; a pre-registered numeric MDE justified from an EXTERNAL operational-harm threshold (seconds EV delay / FP%) with a pinned conservative SD rule (upper 90% CI of a pilot at n≥20; methods M6); TOST equivalence; null only when CI half-width < MDE. Determinism N≥100.

**Experiment C (frozen-vs-adaptive):** as §3 Job C — hardened continual baseline, full poisoning threat model, robustness gain AND adaptivity loss, Exp1-grade rigor.

**Coordination:** NOT an experiment — the term is an inert structural zero; state that no run can move it and remove it from experimental claims (methods m1).

**Substrate:** Euston (§9); demand calibrated to a NAMED, TIME-RESOLVED source (TfL/DfT hourly profile + turning counts + vehicle mix, not a bare AADT; methods M7); calibration is a hard startup gate for any inferential claim (else "uncalibrated synthetic"). Every number labelled relative-in-SUMO.

---

## 9. Euston substrate (pre-built, committed, never regenerated at build time)

Literal build parameters live in a committed `euston-build.md` (authored in the prerequisite phase): exact bbox lat/lon; the full literal `netconvert` command incl `--tls.guess/--tls.join`; expected TLS + in-edge counts (asserted). Pre-build and COMMIT `euston.net.xml` + `edge_ids.json`. The overnight builder MUST NOT call `osmGet`. `edge_map_from_net(mode="chain")` hard-errors on the non-chain topology; derive from `net.getEdges()`/connections and assert coverage of every TLS-controlled in-edge. Conflicting-green uses `getControlledLinks()` + phase state; ship a fixture net with a known conflicting + a known safe phase. Pin the sumocfg collision flags; ship forced-collision + forced-hard-brake fixtures asserting detection fires at the known tick and nowhere else.

**`ground_rules.yaml` schema:** `{id, source: primary|secondary, statute_ref, binding: MUST|should, text, applies_when, fault_weight}`, each `statute_ref` cross-linked to a pinned `uk-traffic-law.md` id format. **Exp-1 injector spec:** feature-vector schema, noise model + params, label file format, target Bayes-error floor — all pinned before the phase. **Anchor contract (`anchor.md`):** the concrete witnesses (e.g. Rekor + a named single-node ledger RPC), submit/verify calls, and fail-loud offline behaviour.

---

## 10. Fail-loud gates (each SCOPE-LOCAL; SKIP-with-record when its precondition is absent, ABORT only that step)

- Real-model gate; Corpus gate; Net gate — as before (SKIP-and-mark, other work proceeds).
- **Quorum-anchor gate:** any non-equivocation / conditional-coupling claim requires a real write to ≥2 independent witnesses + a reconciled per-signer count; a single-node/mock anchor is labelled "not externally anchored" and CANNOT back the claim.
- Per-run: `slm_calls_ok/total` above threshold; the decider on SLM-measured rows is actually `slm`; every attributed record passed signature + chain + quorum-completeness verification; an incomplete window returns `INCOMPLETE_DISCLOSURE`.
- Doc + corridor work is gated on NONE of Foundry/Euston/corpus/anchor.

---

## 11. Build order

**Prerequisite artifacts (pre-built during hardening, NOT overnight-blind):** `euston.net.xml` + `edge_ids.json` + `euston-build.md`; `ground_rules.yaml` + citation oracle; the SUMO-injection non-circular labelled dataset + pre-registered noise model; the frozen E2 worked-example fixture; `anchor.md` + a reachable ≥2-witness quorum endpoint for anchored runs.

**Pinned schemas the overnight build MUST use verbatim (supersedes TEST-AUDIT §1.1):**
- message: `{kind:"message", seq, sender, sender_pubkey_fpr, sender_pubkey_der, signed_payload:{sender,t,payload_min}, sender_signature(hex)}`
- sighting: `{kind:"sighting", seq, sighter_key, ev_id, approach, t, position, signature(hex)}`
- decision: `{kind:"decision", seq, driving_input_seq, junction, t, classification, policies_applied}`
- registry: `{kind:"registry", seq, entity_id, key_fingerprint, key_der, action:enrol|rotate|revoke, external_root_sig, self_sig, incumbent_countersig?, admin_sig}`
- ORIGIN enum (exact strings): `attacker-key`, `system-classifier`, `system-detector`, `sensor-fed-spoof`, `colluding-keys`, `legitimate`, `unknown`; each with an EVIDENCE-DERIVED trigger predicate + the `ground_truth` field used for SCORING ONLY.

**Honest overnight subset (no Foundry/Euston/OSM/anchor dependence):**
1. Doc remediation over the full §5 manifest (incl §5.5 supervision + PROJECT-PROPOSAL + report.tex, §5.6 spec.md sensing reframe, §5.7 GROUND-RULES §F amendment); D1 grep runs LAST with the verbatim allowlist.
2. Message + sighting emission from the real PRODUCER: lift the no-edit rule for `decide()`, capture `NeighborMessage` + its signature at consumption, stamp `driving_input_seq`, mirror `ev_events` (build FATAL-1/2/3).
3. Rewire `fault_attribution` to the real AuditLog: rename to `assessment`/ORIGIN with pinned enum strings + evidence-derived predicates; `flatten` adapter with the `tls→junction`/`tick→t` remap; enforce `identity.verify` + `verify_chain` + quorum-completeness before attributing; the E2 direction + tie-break against the frozen fixture; the tamper test isolating `identity.verify` over a log produced by `IntegratedSystem.run()`. Atomically replace `sig_valid` across module + tests + doc.
4. Fix `slm_agent.py` STATIC edit ONLY: strip "1.0 = the limit" + threshold-shaped few-shots (qualitativise 0.40/1.80), raise `max_tokens`, drop no-CoT + deleted-brief ref; add the Job-A output SHAPE (incl `legitimate`). Job-A CONTENT runs deferred (corpus-gated).
5. Anti-starvation: hook `MaxPressureController.step` (there is NO `ShieldController`); pin per-approach skip count + force-serve at `max_skip` + the `anti_starvation_violations` increment site; a COMMITTED forced-skip fixture where one approach genuinely never wins argmax, asserting it IS served within `max_skip` AND the counter EMERGES 0 (never set by the test) (build FATAL-5).
6. Foundry determinism probe as SKIP-not-abort.

**OUT of the overnight subset (require prerequisites / real runs / the quorum anchor):** Euston experiments; Job A / citation-CONTENT runs; SUMO-injection Experiment 1; Experiment D full run + the quorum-anchored completeness runs; Experiment C (frozen-vs-adaptive); the 30-seed powered runs; the quorum-anchor integration (its own scoped task). T10/T11 documented-xfail.

---

## 12. Acceptance tests (all binary; all required for distinction)

- D1 one-thesis-one-tree: full §5 manifest clean; the excluded set ⊆ a VERBATIM allowlist AND every non-excluded live doc greps clean; one thesis sentence across live docs (incl spec.md, supervision layer, PROJECT-PROPOSAL, report.tex). Grep runs last.
- D2 fault language = split; the pack has no verdict/confidence/accusation; citation selection is origin-INDEPENDENT (a test proves the cited-rule set is not a function of the injected origin); the note is non-evidential + firewalled + counsel-gated; a test fails if any pack field carries an origin verdict or "lie"/"attacker" wording.
- D3 `real_model=true` guard: a misconfigured run ABORTS/SKIPS-with-record, never a null.
- D4 Experiment 1: CIs + numeric MDE (external-harm-justified) + TOST; dev/test split + one-hash-sealed analysis bundle + global eval-counter=1; classifier-independent OOD split + continuous accuracy-vs-distance curve; axis-aligned-conjunction ceiling AND analytic nonlinear Bayes ceiling; no threshold-defining constant (asserted) + behavioral leak test; parse-failures as failures.
- D5 non-circular labels + SLM vs the nonlinear ceiling + Job-A vs the graceful-fallback template on citation CORRECTNESS on novel combos + the SLM false-citation rate + citation-gold kappa≥0.6.
- **D6 Experiment D (the characterisation):** the stealthy class on the physical-impact axis (residual vs the numerically-pinned FP-budget threshold); the conditional coupling proven under stated assumptions; and — required — the MEASURED free-region fraction as collusion-degree / witness-density / operator-omission vary over the pre-registered grid (the boundary is the result); plus the 7-way origin CONFUSION MATRIX with the scoring label severed from engine input + hard-triad accuracy with a failing threshold.
- **D-anchor:** the completeness commitment is written to ≥2 independent witnesses + a reconciled per-signer count; a single-node/mock-anchored run is labelled "not externally anchored" and its coupling claim is refused (fail-loud).
- **D-SLM-kill:** the pre-committed kill/demote criterion is evaluated and reported; arm (iii) must beat a HARDENED continual baseline net of adaptivity loss (a naive learner does not count); multiplicity-corrected; the SLM stays in the system regardless.
- D7 anti-starvation: `anti_starvation_violations == 0` across the attacked n=30 matrix; the committed forced-skip fixture triggers the override and the counter EMERGES (never set by the test).
- D8 honest demand sweep + fairness + worst-case, all modes, one CI method; coordination reported as a structural zero, not an experiment.
- D-sec: fault engine verifies signatures + chain + quorum-completeness before attributing; the framing attack (operator re-registration) is defeated by the external identity root + counter-signed rotation; a keyless-local-sensing incident → `sensor-fed-spoof` via the evidence-derived predicate (not `ground_truth`) and marked "corroboration not key-attributable"; the tie-break matches the frozen fixture; the pack cites real UK statutes with source-tag + as-at date + the not-a-determination header; **the collusion + operator-omission failure cases are demonstrated and reported as the coupling's boundary, not defended.**
- **Policy-KPI rule (fixes C1):** the empty-`policies_applied` abort applies to DETERMINISTIC decision records only; the SLM Job-A note is exempt. The exemption is LANDED in GROUND-RULES §F + TEST-SPEC (not merely asserted; consistency B1).
- Tests: T1-T9 pass-required; T10/T11 documented-xfail.

---

## 13. The viva sentence this spec must make true

"My contribution is a characterisation. I build an on-device trust-preserving emergency-coordination layer — a deterministic gate that refuses a compromised insider's uncorroborated preemption, over a Certificate-Transparency-style quorum-anchored accountability log whose mechanism I credit entirely to prior work. My novel object is the measured map of what that layer can and cannot hold accountable. I prove a conditional coupling: for the bounded class of stealthy conservation-consistent deviations the gate cannot catch live, no deviation is both invisible live and untraceable afterwards — provided its corroboration comes only from honest independent keys and the anchor is a non-equivocating quorum. Then I measure exactly where that proviso fails: two colluding keys manufacture corroboration and leave no trace; an operator can omit its own record before anchoring; the guarantee decays as witness density falls. That boundary, quantified on the real Euston Road corridor against cited UK law, is the finding — I claim no novel primitive and no unconditional guarantee. The evidence pack states only cryptographically-verified, quorum-anchored facts through a closed forensic channel, selects citations mechanically, and does not adjudicate fault. A frozen on-device SLM writes the non-evidential, counsel-gated origin note, characterised for citation-faithfulness against statute with a pre-committed kill criterion, and I separately measure the robustness-versus-adaptivity tradeoff of freezing it against a hardened continual learner. Coordination and traffic optimisation are not my claims; the measured accountability boundary is." Every clause backed by a run that passed its §12 gate, or it is not settled.
