# The Edge Negotiator: Test, Audit, and Fault-Attribution Specification

**Status**: CANONICAL, frozen test + accountability contract. Created 2026-07-16.
**Purpose**: lock down, unambiguously, (1) every adversarial and functional test case and its expected outcome, (2) how we systematically try to break the system, (3) how the system attributes fault for any adverse outcome to a specific responsible party, and (4) the audit record that makes every decision reconstructable. This is the document the tests are written from; a behaviour not covered here is a gap to close, not a judgement call at build time.

Grounded in: `GROUND-RULES-POLICY.md` (policies P1-P8, criteria B1-B5, attack taxonomy), `FORMAL-SPECIFICATION.md` §8 (invariants R/A/S), `src/audit_log.py` (the tamper-evident chain), `src/ambiguous_decision.py` (classification contract).

---

## Part 1. The audit record (what is logged for everything)

Every message received, every control decision, and every identity/registry change is appended to the tamper-evident hash-chained log (`AuditLog`, `sha256(prev_hash || canonical(event))`, optional Ed25519 issuer signature, Merkle-anchored in batches). Nothing that influences a control action is unlogged.

**1.1 Message record** (one per received coordination/EV message):
```
{ "kind":"message", "t":<tick>, "recipient":<jid>, "sender":<jid>,
  "channel":"coord"|"ev", "payload_hash":<sha256>, "sig_valid":<bool>,
  "registry_status":"approved"|"revoked"|"unknown", "replay":<bool>,
  "conservation":{ "residual":<float>, "in_band":<bool>, "cusum":<float> } }
```

**1.2 Decision record** (one per control tick at an SLM/emergency junction):
```
{ "kind":"decision", "t":<tick>, "junction":<jid>, "regime":"normal"|"triggered",
  "trigger":{ "source":"local_sensing"|"advance_claim"|"conservation_anomaly"|null,
              "ev_id":<id|null>, "claimer":<jid|null> },
  "driving_input_seq":<audit_seq_of_message|null>,   # links to the message that drove it
  "policies_applied":["P3","B2"],                     # from GROUND-RULES-POLICY.md
  "decider":"rule"|"slm"|"deterministic",
  "classification":"LEGITIMATE"|"SPOOFED_OR_FAULTY"|"UNKNOWN",
  "confidence":<0..1>, "mp_choice":<phase>, "executed":<phase>,
  "shield_vetoed":<bool>, "reason":<text> }
```

**1.3 Registry record**: `{ "kind":"registry", "t":<tick>, "action":"register"|"revoke", "junction":<jid>, "key_fingerprint":<hex> }`.

**1.4 Outcome record** (per completed trip / per starvation / per incident, from tripinfo + shield): `{ "kind":"outcome", "type":"trip"|"starvation"|"false_preemption"|"missed_ev"|"gridlock", "junction":<jid|null>, "t":<tick>, "metrics":{...} }`.

**Guarantees.** (i) Contiguous `seq` + hash chain: any insertion/deletion/edit breaks `verify_chain`. (ii) Signed entries: `verify_signatures` catches a forged/swapped signature independently. (iii) `driving_input_seq` links every decision to the exact message (and therefore the signing key) that caused it, which is what makes fault attribution possible. (iv) Persistence: `to_jsonl`/`from_jsonl` re-verifies on load. **Auditability KPI**: fraction of decision records with non-empty `policies_applied` and a classification consistent with them; target 100%, a zero-policy decision is a defect.

---

## Part 2. Fault attribution (who was at fault in a particular accident)

**Adverse-outcome types** (each detected and logged as an `outcome` record):
- **A1 False preemption**: a green forced for an illegitimate/non-existent EV (starves cross traffic).
- **A2 Missed real emergency**: a legitimate EV not cleared.
- **A3 Starvation**: an approach skipped beyond `max_skip`.
- **A4 Gridlock / spillback** at a junction.
- **A5 Wrong incident reallocation**.

**2.1 Attribution procedure** (deterministic, runs against the audit log):
```
fault_report(outcome):
  1. window = audit.slice(outcome.junction, [outcome.t - H, outcome.t])   # H = causal horizon
  2. causal = decisions in window whose `executed` phase produced the outcome
             (e.g. the preempt that starved the cross street; the refusal that missed the EV)
  3. for each d in causal:
       input = audit.entry(d.driving_input_seq)          # the message that drove d (or local sensing)
       verdict =
         ATTACKER(input.sender)      if d.classification was wrong AND input came from a
                                     signed key whose report the audit shows was implausible/
                                     uncorroborated  -> the SIGNING KEY is the culprit (non-repudiable)
         SYSTEM_CLASSIFIER(d.decider, d.policies_applied)
                                     if the classifier (rule/SLM) mislabelled a correctly-evidenced
                                     case -> fault is ours, with the exact policy + decider named
         SYSTEM_DETECTOR(residual, threshold)
                                     if a conservation/EV detector false-negatived (missed it)
         LEGITIMATE_DEGRADATION      if every decision was correct per policy and the harm is the
                                     accepted cost (e.g. the 8 s gate cost, or congestion at scale)
         OUT_OF_SCOPE_COLLUSION      if the input passed all checks only because >=2 keys were
                                     mutually consistent (recall=0 by construction; see 3.3)
         UNKNOWN                     if no record explains the outcome (flagged, never silent)
  4. emit { outcome, causal_seqs:[...], driving_input_seq, culprit_key/junction,
            policies_applied, decider, verdict, evidence_chain:[audit seqs] }
```

**2.2 Non-repudiation (the core accountability claim).** Because every message is Ed25519-signed and hash-chained, a false claim is cryptographically bound to the **signing key**. The fault report can therefore prove *which junction emitted the lie* that drove a bad decision, and the Merkle anchor lets an external auditor confirm that record was in the anchored batch without holding the full log. This is "who was at fault", provable, not asserted.

**2.3 Honest limits (stated, tested as expected-failures).**
- The audit attributes to a **key**, not the human behind a compromised key.
- **Collusion (>=2 keys)** and **admin-key compromise** are out of scope: the audit still attributes to the keys involved and the response is `revoke` + external review, not runtime detection.
- A within-band lie that never crossed a threshold is attributed `LEGITIMATE_DEGRADATION` at runtime but is recoverable post-hoc from the log once ground truth is known.

**2.4 Worked examples** (each becomes a test):
- *Phantom preemption by J1*: A1 at J2. Procedure finds the causal preempt decision, `driving_input_seq` → J1's signed `ev_claim`, classification should have been SPOOFED_OR_FAULTY (P3), audit shows zero corroboration → verdict **ATTACKER(J1)**. In the defended system P3 fires and there is no A1, so the fault report instead records "attack attempted by J1, refused, no adverse outcome."
- *SLM mislabels a real incident as fake*: A2. Causal refusal, input well-evidenced (B2+B4 held), classifier=slm mislabelled → verdict **SYSTEM_CLASSIFIER(slm, [P7])**. This is exactly the failure Experiment 1 measures (recall / false-negative rate).

---

## Part 3. Adversarial test matrix (how we try to break it)

Every attack category in `GROUND-RULES-POLICY.md` §C gets test cases at three levels: **unit** (pure gate/classifier logic), **integration** (live corridor, injected), and **forensic** (the fault report is correct). Columns: setup → injection → expected classification → expected system action → expected audit/fault → pass criterion.

| # | Attack | Injection | Expected classification | Expected action | Expected fault report | Pass criterion |
|---|---|---|---|---|---|---|
| T1 | `invalid_id` | unsigned / unregistered / revoked key sends a claim | (rejected at bus) | dropped, never processed | message record `sig_valid=false`/`registry_status`≠approved; no decision | 0 decisions driven by it |
| T2 | `signal_tampering` | valid `maintenance` key asserts an ambulance preemption | SPOOFED_OR_FAULTY (P2 auth-class) | refused | verdict ATTACKER(key), policy P2 | preemption withheld, culprit key named |
| T3 | `phantom_ev` | approved J1 signs EV claim, no vehicle exists | SPOOFED_OR_FAULTY (P3) | preemption withheld, stay MaxPressure | ATTACKER(J1) if any A1 else "refused" | 0 false preemptions across 30 seeds |
| T4 | `count_inflation` | approved key over-claims release beyond band | SPOOFED_OR_FAULTY (P5) | claim discounted, flagged | detector residual>band logged; ATTACKER(key) | detected within D windows; recall reported |
| T5 | `missing_metadata` | claim with required field null | UNKNOWN (P8) | conservative reject + log for review | UNKNOWN, no silent guess | classified UNKNOWN, logged |
| T6 | `contradictory_signals` | two approved neighbours disagree on same edge | escalate (P6) → classify | discount both, escalate to disambiguator | records both inputs + the disagreement | both flagged; decision cites P6 |
| T7 | `replay` | re-send a prior-tick valid message | (dropped, replay) | dropped before conservation | message record `replay=true`; no decision | 0 decisions driven by replay |
| T8 | `withholding` | approved neighbour goes silent while traffic arrives | (sensor_outage) | fall back to local observation | silent-neighbour expectation logged | no stall; graceful fallback |
| T9 | `unknown_vehicle_type` | entity/behaviour not in §A | UNKNOWN (P8) | conservative reject + log | UNKNOWN | classified UNKNOWN, escalated |
| T10 | `collusion` (OUT OF SCOPE) | 2 keys: one over-claims, one supplies matching fake sighting | (evades: LEGITIMATE) | acted on (recall→0 by construction) | verdict OUT_OF_SCOPE_COLLUSION, both keys named | documented expected-failure; keys attributable post-hoc |
| T11 | `key_compromise` (OUT OF SCOPE) | admin key forges registry | (total failure) | undefended | documented single-point-of-failure | expected-failure documented, not hidden |

**Positive / edge / unknown balance** (per Lee): every category above also has **positive** cases (legitimate versions that MUST be admitted: real corroborated EV → LEGITIMATE/preempt), **edge** cases (borderline corroboration/residual/persistence), and **unknown** cases (novel combinations → UNKNOWN or escalate). These populate the anticipated-vs-novel split of the Experiment-1 dataset.

**3.3 Red-team playbook (structured, not ad hoc).** For each category: (a) minimal single-message attack; (b) sustained/repeated; (c) magnitude sweep (lie size as multiples of the band, the detectability envelope, locate the recall-collapse knee); (d) timing attack (at phase boundary / last-vehicle-advantage analogue); (e) combined (attack during a real emergency, E6). Each run asserts the classification, the action, AND the fault report.

---

## Part 4. Metrics (measured per category, not just accuracy)

Per attack category and overall: **precision, recall, false-positive rate, false-negative rate**, detection latency (windows), false-preemption rate, and the **auditability KPI** (Part 1). Classification quality is reported per anticipated/novel split (Experiment 1). Traffic-outcome and fairness/worst-case per Experiment 2. Statistics: paired seeds, BCa CIs, permutation + Holm; state the MDE so a null is precise.

---

## Part 5. Coverage and acceptance (the lock)

- **Every** policy P1-P8 has >=1 unit test asserting its classification.
- **Every** attack category T1-T11 has unit + integration + forensic tests.
- **Every** functional requirement (spec.md FR-001..010) and success criterion (SC-001..007) maps to >=1 named test (traceability matrix, to build as `tests/TRACEABILITY.md`).
- **Every** adverse-outcome type A1-A5 has a fault-attribution test asserting the correct verdict and culprit.
- CI gate: full suite green, auditability KPI = 100% on the test corpus, and no decision record with empty `policies_applied`.
- A change that adds a behaviour without a test here is rejected in review.

---

## Part 6. Build order for this spec

1. Extend `AuditLog` event producers so decisions carry `policies_applied` + `driving_input_seq` + `classification` (Part 1).
2. `src/fault_attribution.py`: the Part 2 procedure over an `AuditLog`; unit-tested on synthetic logs.
3. `src/adversarial_suite.py` + `tests/`: the Part 3 matrix as generators (unit + integration), organized by category.
4. Metrics extension for P/R/FPR/FNR per category (Part 4), reuse `emergency_metrics` + `stats`.
5. `tests/TRACEABILITY.md`: the FR/SC/policy/attack → test map (Part 5).
