# The Edge Negotiator: Test, Audit, and Fault-Attribution Specification

**Status**: Test contract, CONFORMED to `MASTER-SPEC.md` (the single source of truth). The forensic reader is `src/assessment.py` — the §6.3 mechanical ORIGIN classifier with the **evidence-pack / internal-note SPLIT**, NOT a machine-determination reader. The system emits no machine determination of fault: the split is (1) a mechanically-verifiable provenance evidence pack carrying only reproducible facts (no origin label, no confidence, no accusation) and (2) a firewalled, non-evidential, counsel-gated internal AI note that alone carries the ORIGIN classification. Part 2 below has been conformed: the old human-vs-AI determination enum (ATTACKER/SYSTEM_CLASSIFIER/OUT_OF_SCOPE_COLLUSION/…) is replaced by the §2 ORIGIN ontology `{attacker-key, system-classifier, system-detector, sensor-fed-spoof, colluding-keys, legitimate, unknown}`, and the Part 1 record is the §11 pinned schema (`driving_input_seqs` SET, no `sig_valid`). Created 2026-07-16; conformed at the D1 cutover.
**Purpose**: lock down, unambiguously, (1) every adversarial and functional test case and its expected outcome, (2) how we systematically try to break the system, (3) how the system attributes fault for any adverse outcome to a specific responsible party, and (4) the audit record that makes every decision reconstructable. This is the document the tests are written from; a behaviour not covered here is a gap to close, not a judgement call at build time.

Grounded in: `GROUND-RULES-POLICY.md` (policies P1-P8, criteria B1-B5, attack taxonomy), `FORMAL-SPECIFICATION.md` §8 (invariants R/A/S), `src/audit_log.py` (the tamper-evident chain), `src/ambiguous_decision.py` (classification contract).

---

## Part 1. The audit record (what is logged for everything)

Every message received, every control decision, and every identity/registry change is appended to the tamper-evident hash-chained log (`AuditLog`, `sha256(prev_hash || canonical(event))`, optional Ed25519 issuer signature, Merkle-anchored in batches). Nothing that influences a control action is unlogged.

These are the **§11 pinned schemas** of MASTER-SPEC (which supersedes any earlier TEST-AUDIT §1.1). No record carries a `sig_valid:bool`; the signature is stored verbatim and re-verified by `identity.verify` at attribution time.

**1.1 Message record** (one per received coordination/EV message; a *signed* sighting rides here as `payload.sighting`, since a junction cannot re-sign a neighbour's sighting):
```
{ "kind":"message", "seq":<int>, "sender":<jid>,
  "sender_pubkey_fpr":<hex>, "sender_pubkey_der":<hex>,
  "signed_payload":{ "sender":<jid>, "t":<logical tick>, "payload":{...} },
  "sender_signature":<hex> }
```

**1.1b Sighting record** (KEYLESS local reading ONLY — the §6.4 sensor-fed-spoof surface):
```
{ "kind":"sighting", "seq":<int>, "sighter_key":null, "ev_id":<id>,
  "approach":<edge>, "t":<tick>, "position":null }
```
`sighter_key` is `null` and the envelope signature is `null` (appended with `issuer=None`) — a valid, distinct encoding, NOT `missing_metadata`: a keyless local reading has signing-key-count 0, so it maps at the origin layer to `keyless-lone-sighting`→`sensor-fed-spoof`, never to `unknown`. A `driving_input_seqs` pair for a keyless input is `[seq, null]`.

**1.2 Decision record** (one per control tick at an SLM/emergency junction):
```
{ "kind":"decision", "seq":<int>,
  "driving_input_seqs":[ [<seq>,<sighter_key|null>], ... ],  # SET of ALL signed inputs consumed (no materiality filter)
  "junction":<jid>, "t":<sim time>, "executed":<phase>,
  "classification":"LEGITIMATE"|"SPOOFED_OR_FAULTY"|"UNKNOWN",  # a RUNTIME label, DISTINCT from ORIGIN; assessment.py MUST NOT read it for origin
  "policies_applied":[ ... ] }                               # check-stage vocab {corroboration, conservation_band, replay, membership}
```
`policies_applied` is the distinct check-stage vocabulary `{corroboration, conservation_band, replay, membership}`, not the P1-P8 decision-policy ids. The `classification` field is a runtime label only; ORIGIN is decided post-hoc by `assessment.py` from verified provenance and lives only in the internal note.

**1.3 Registry record**: `{ "kind":"registry", "seq":<int>, "entity_id":<jid>, "key_fingerprint":<hex>, "key_der":<hex>, "action":"register"|"revoke", "external_root_sig":<hex>, "self_sig":<hex>, "incumbent_countersig":<hex|null>, "admin_sig":<hex> }`.

**1.4 Outcome record** (per completed trip / per starvation / per incident, from tripinfo + shield): `{ "kind":"outcome", "type":"trip"|"starvation"|"false_preemption"|"missed_ev"|"gridlock", "junction":<jid|null>, "t":<tick>, "metrics":{...} }`.

**Guarantees.** (i) Contiguous `seq` + hash chain: any insertion/deletion/edit breaks `verify_chain`. (ii) Signed entries: `verify_signatures` (issuer) and per-sender `identity.verify` catch a forged/swapped signature independently; there is no stored `sig_valid` shortcut. (iii) `driving_input_seqs` links every decision to the full SET of signed inputs (and therefore the signing keys) that could have caused it, which is what makes origin classification possible. (iv) Persistence: `to_jsonl`/`from_jsonl` re-verifies on load. **Auditability KPI**: fraction of **deterministic** decision records with non-empty `policies_applied` and a classification consistent with them; target 100%, a zero-policy deterministic decision is a defect. The SLM Job-A internal note is EXEMPT from the empty-`policies_applied` rule (MASTER-SPEC §12 policy-KPI rule; TARGET-STATE pending the GROUND-RULES §F + TEST-AUDIT amendment of §5.7, not claimed landed).

---

## Part 2. The SPLIT: provenance evidence pack + origin classification

The system emits **no machine determination of fault**. For any adverse outcome, `src/assessment.py` produces two firewalled channels that are never merged:
1. a mechanically-verifiable **PROVENANCE EVIDENCE PACK** — only reproducible facts (verified sender key + enrolment provenance, chain/signature/quorum-completeness/cross-audit results, which corroboration checks failed [mechanical, origin-independent], neutral cited-rule text). It carries NO origin label, NO confidence, NO accusation, NO "attacker"/"lie" wording; header: "Provenance record; not a determination of legal fault."
2. a firewalled, **NON-EVIDENTIAL, counsel-gated internal AI note** that alone carries the ORIGIN classification. Where the origin is a signing party it names a **KEY, never a person**.

**Origin ontology (internal note only; MASTER-SPEC §2):** `attacker-key / system-classifier / system-detector / sensor-fed-spoof / colluding-keys / legitimate / unknown`. The scored subset is a DETERMINISTIC verification check over two mechanical features (signing-key count 0/1/≥2, recomputed-corroboration presence), deciding three classes: keyless-lone-sighting→`sensor-fed-spoof`, uncorroborated-signed→`attacker-key`, corroborated→`legitimate`; the veracity/collusion distinction inside the corroborated cell is honestly →`unknown`. This is a ~100% verification check, explicitly NOT the contribution.

**Adverse-outcome types** (each detected and logged as an `outcome` record):
- **A1 False preemption**: a green forced for an illegitimate/non-existent EV (starves cross traffic).
- **A2 Missed real emergency**: a legitimate EV not cleared.
- **A3 Starvation**: an approach skipped beyond `max_skip`.
- **A4 Gridlock / spillback** at a junction.
- **A5 Wrong incident reallocation**.

**2.1 Procedure** (`src/assessment.py`, deterministic; runs `verify_chain` + per-sender `identity.verify` + quorum-completeness + cross-audit FIRST, refusing `UNKNOWN`/`INCOMPLETE_DISCLOSURE` on any failure):
```
assess(outcome, registry_der):
  1. window = audit.slice(outcome.junction, [outcome.t - H, outcome.t])   # H = causal horizon
  2. verify chain + per-sender signatures + quorum-completeness + cross-audit; else -> INCOMPLETE_DISCLOSURE
  3. causal = decisions in window whose `executed` phase produced the outcome, selected by walking
             `driving_input_seqs` -> the driving input record whose ev id == outcome.ev_id
             (ev id from a signed advance-claim OR signed sighting on a kind:"message" input,
              or from a keyless kind:"sighting" input). NEVER read the runtime `classification` field.
  4. EVIDENCE PACK (mechanical, origin-independent): { outcome, causal_seqs:[...], driving_input_seqs,
       verified_sender_keys, enrolment_provenance, chain/signature/quorum/cross-audit results,
       which_corroboration_checks_failed, neutral_cited_rule_text }   # NO origin, NO confidence, NO accusation
  5. INTERNAL NOTE (firewalled, counsel-gated) — ORIGIN over verified provenance ONLY:
       attacker-key       iff recomputed independent-corroboration count == 0 over driving_input_seqs
                          (the SIGNING KEY, non-repudiable; the SET->culprit rule)
       sensor-fed-spoof   iff a keyless local reading drove a transient preemption (ground_truth SCORING-ONLY)
       legitimate         iff >=2 independently-signed keys corroborate (corroborated cell)
       colluding-keys     -> collapses to `unknown` at runtime: indistinguishable from `legitimate`
                          inside the corroborated cell (recall->0 by construction; keys attributable post-hoc)
       system-classifier  iff a purely-provenance-derived predicate shows the classifier mislabelled a
                          correctly-evidenced case (zero ground_truth), else -> unknown
       system-detector    iff a purely-provenance-derived predicate shows a detector false-negative, else -> unknown
       unknown            if no verified record decides it (flagged, never silent)
```
The marginal "need > corroborated magnitude" form (sub- vs supra-margin piggyback-inflation) is DEFERRED to Experiment D and NOT implemented overnight (no `need`/magnitude field exists in the current record); when implemented it is a leave-one-out recompute excluding the suspect input, and only SUPRA-margin piggyback is attributed (sub-margin is an in-scope FREE class, MASTER-SPEC §0).

**2.2 Non-repudiation (the accountability claim, honestly scoped).** Because every message is Ed25519-signed and hash-chained, a signed claim is cryptographically bound to the **signing key**, and the quorum anchor + named cross-auditor let an external party confirm the record was in the anchored batch (split-view detection) without holding the full log. This proves *which key emitted a claim* that drove a decision. It is NOT proof that the claim was false: non-repudiation ≠ truthfulness. Physical veracity is not adjudicable from provenance; the system never adjudicates it.

**2.3 Honest limits (stated, tested as expected-failures).**
- Attribution is to a **key**, not the human behind a compromised key.
- **Colluding keys (≥2)**, **operator creation-time omission**, and **admin-key / identity-root / cross-auditor compromise** are out of scope: the corroborated-cell veracity judgment is provenance-indistinguishable, so `colluding-keys` collapses to `unknown` at runtime; response is `revoke` + external review, keys attributable post-hoc.
- A within-band deviation that never crossed a threshold is an in-scope FREE class (MASTER-SPEC §0): not classified as an attack at runtime, recoverable post-hoc from the log once ground truth is known.

**2.4 Worked examples** (each becomes a test):
- *Phantom preemption by J1*: A1 at J2. The causal selector walks `driving_input_seqs` → J1's signed `ev_claim` (matching `outcome.ev_id`); the recomputed independent-corroboration count is 0 → internal-note origin **`attacker-key` (J1's key)**; the evidence pack records the failed corroboration checks with no origin label. In the defended system the gate refuses and there is no A1, so the pack records "signed claim by J1's key, uncorroborated, preemption withheld, no adverse outcome."
- *SLM mislabels a real incident as fake*: A2. Causal refusal, input well-evidenced (≥2-key corroboration held); if a purely-provenance-derived predicate shows the mislabel → internal-note origin **`system-classifier`**, else →`unknown`. This is exactly the failure Experiment 1 (Job B) measures (recall / false-negative rate).

---

## Part 3. Adversarial test matrix (how we try to break it)

Every attack category in `GROUND-RULES-POLICY.md` §C gets test cases at three levels: **unit** (pure gate/classifier logic), **integration** (live corridor, injected), and **forensic** (the fault report is correct). Columns: setup → injection → expected classification → expected system action → expected audit/fault → pass criterion.

| # | Attack | Injection | Expected classification | Expected action | Expected fault report | Pass criterion |
|---|---|---|---|---|---|---|
| T1 | `invalid_id` | unsigned / unregistered / revoked key sends a claim | (rejected at bus) | dropped, never processed | rejected at bus (`identity.verify` fails or not approved); no consumed-message or decision record | 0 decisions driven by it |
| T2 | `signal_tampering` | valid `maintenance` key asserts an ambulance preemption | SPOOFED_OR_FAULTY (P2 auth-class) | refused | pack: P2 auth-class fail; note origin `attacker-key` | preemption withheld, culprit key named in the note |
| T3 | `phantom_ev` | approved J1 signs EV claim, no vehicle exists | SPOOFED_OR_FAULTY (P3) | preemption withheld, stay MaxPressure | note origin `attacker-key` (J1) if any A1 else pack: uncorroborated, refused | 0 false preemptions across 30 seeds |
| T4 | `count_inflation` | approved key over-claims release beyond band | SPOOFED_OR_FAULTY (P5) | claim discounted, flagged | detector residual>band logged; note origin `attacker-key` | detected within D windows; recall reported |
| T5 | `missing_metadata` | claim with required field null | UNKNOWN (P8) | conservative reject + log for review | UNKNOWN, no silent guess | classified UNKNOWN, logged |
| T6 | `contradictory_signals` | two approved neighbours disagree on same edge | escalate (P6) → classify | discount both, escalate to disambiguator | records both inputs + the disagreement | both flagged; decision cites P6 |
| T7 | `replay` | re-send a prior-tick valid message | (dropped, replay) | dropped before conservation | dropped by replay dedup (HWM); no consumed-message or decision record | 0 decisions driven by replay |
| T8 | `withholding` | approved neighbour goes silent while traffic arrives | (sensor_outage) | fall back to local observation | silent-neighbour expectation logged | no stall; graceful fallback |
| T9 | `unknown_vehicle_type` | entity/behaviour not in §A | UNKNOWN (P8) | conservative reject + log | UNKNOWN | classified UNKNOWN, escalated |
| T10 | `collusion` (OUT OF SCOPE) | 2 keys: one over-claims, one supplies matching fake sighting | (evades: LEGITIMATE) | acted on (recall→0 by construction) | note origin →`unknown` at runtime (collusion indistinguishable in the corroborated cell); both keys attributable post-hoc | documented expected-failure |
| T11 | `key_compromise` (OUT OF SCOPE) | admin key forges registry | (total failure) | undefended | documented single-point-of-failure | expected-failure documented, not hidden |

**Positive / edge / unknown balance** (per Lee): every category above also has **positive** cases (legitimate versions that MUST be admitted: real ≥2-key-corroborated EV → LEGITIMATE/preempt), **edge** cases (borderline corroboration/residual/persistence), and **unknown** cases (novel combinations → UNKNOWN or escalate). These populate the anticipated-vs-novel split of the Experiment-1 dataset.

**3.3 Red-team playbook (structured, not ad hoc).** For each category: (a) minimal single-message attack; (b) sustained/repeated; (c) magnitude sweep (deviation size as multiples of the band — the free-deviation boundary, locate the recall-collapse point; on Euston the phase-coupled coverage threshold is the headline object, not a detection ROC); (d) timing attack (at phase boundary / last-vehicle-advantage analogue); (e) combined (attack during a real emergency, E6). Each run asserts the runtime classification, the action, AND the evidence-pack / origin-note split.

---

## Part 4. Metrics (measured per category, not just accuracy)

Per attack category and overall: **precision, recall, false-positive rate, false-negative rate**, detection latency (windows), false-preemption rate, and the **auditability KPI** (Part 1). Classification quality is reported per anticipated/novel split (Experiment 1). Traffic-outcome and worst-case per the demand sweep (Experiment 2/D); distributional-audit reporting is NOT a contribution and is not reported. Statistics: paired seeds, BCa CIs, permutation + Holm; state the MDE so a null is precise.

---

## Part 5. Coverage and acceptance (the lock)

- **Every** policy P1-P8 has >=1 unit test asserting its classification.
- **Every** attack category T1-T11 has unit + integration + forensic tests.
- **Every** functional requirement (spec.md FR-001..010) and success criterion (SC-001..007) maps to >=1 named test (traceability matrix, to build as `tests/TRACEABILITY.md`).
- **Every** adverse-outcome type A1-A5 has a test asserting the correct origin classification (internal note) and evidence pack.
- CI gate: full suite green, auditability KPI = 100% on the test corpus, and no **deterministic** decision record with empty `policies_applied` (the SLM Job-A note is exempt, §5.7 TARGET-STATE).
- A change that adds a behaviour without a test here is rejected in review.

---

## Part 6. Build order for this spec

1. Extend `AuditLog` event producers so decisions carry `policies_applied` + `driving_input_seqs` (SET) + `classification` (Part 1).
2. `src/assessment.py` (SUPERSEDES the former `src/fault_attribution.py`, now deleted): the §6.3 mechanical ORIGIN classifier over an `AuditLog` — gated (`verify_chain` + per-SENDER `identity.verify` + in-window completeness + cross-audit) with the evidence-pack/internal-note SPLIT; unit-tested on synthetic logs + the pinned E2 fixture. The Part-2 text above is now conformed to this SPLIT.
3. `src/adversarial_suite.py` + `tests/`: the Part 3 matrix as generators (unit + integration), organized by category.
4. Metrics extension for P/R/FPR/FNR per category (Part 4), reuse `emergency_metrics` + `stats`.
5. `tests/TRACEABILITY.md`: the FR/SC/policy/attack → test map (Part 5).
