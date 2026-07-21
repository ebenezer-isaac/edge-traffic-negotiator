# The Edge Negotiator: Ground Rules and Decision Policy Base

**Status**: CANONICAL policy source of truth. Created 2026-07-16 in response to Lee's meeting feedback ("where is the policy actually defined?").
**Purpose**: the single, explicit, versioned, auditable definition of how the system decides whether a flagged signal is legitimate or an attack, and how it steers safely. Both the deterministic rule engine and the SLM (via retrieval) reason against THIS document. Therefore (a) every decision is traceable to a numbered policy (auditability), and (b) the rule-vs-SLM comparison is fair because both consume the same policies.

> Design intent: this markdown is the human-readable master. A machine-readable mirror (`ground_rules.yaml`, to build) carries the same policy ids for the rule engine, the RAG retrieval corpus, and the audit log, so a decision record can cite `policy_id` verbatim. Nothing here is inferred by the model at runtime: an unmatched case is classified `UNKNOWN` and escalated, never silently guessed.

---

## A. Authorized entities and allowed behaviours

| Entity class | Priority | Allowed behaviour | Expected signal signature |
|---|---|---|---|
| `ambulance` | 1 | Request preemption along its route; run active corridor | vClass=emergency, registered EV key, plausible route + speed |
| `fire` | 1 | Request preemption; may request lane hold at scene | vClass=emergency, registered EV key |
| `police` | 2 | Request preemption (pursuit) or escort hold | vClass=emergency, registered EV key; escort may be multi-vehicle |
| `maintenance` | 3 | Request lane closure / incident reservation, NOT preemption | registered works key; static or slow, scheduled window |
| `civilian` | n/a | No priority; counted as normal traffic | no EV key |

Rules: only classes 1-3 may influence signal priority; each must carry a registered key for its class (identity). A claim asserting a class its key is not authorized for is an attack (see C, `invalid_id`). Maintenance may reserve an incident but MUST NOT trigger EV preemption (a maintenance key asserting an ambulance preemption is `signal_tampering`).

---

## B. Legitimacy criteria for a claim

A claim is assessed on five independent signals (the same features the rule and SLM both receive):

- **B1 Identity**: signed by a currently-approved key authorized for the asserted class.
- **B2 Corroboration**: an independent junction (not the claimer) has physically sensed the same entity.
- **B3 Local sensing**: this junction physically senses the entity on its own approach (strongest evidence; cannot be spoofed remotely).
- **B4 Plausibility**: the claim is consistent with vehicle-conservation (reported counts inside the plausibility band) and with a physically feasible route/speed.
- **B5 Temporal consistency**: the sighting timing is consistent with the entity's route travel time (not stale, not impossibly early).

---

## C. Attack taxonomy (what we defend, and how it is classified)

| Attack | Definition | Signal that exposes it |
|---|---|---|
| `invalid_id` | Unsigned, unregistered, revoked, or wrong-class key | B1 fails |
| `signal_tampering` | Valid key, but asserts a class/action it is not authorized for | B1 (authorization) fails |
| `phantom_ev` | Signed claim for an entity that does not exist | B2 + B3 both fail (no corroboration, no local) |
| `count_inflation` | Signed but physically implausible counts | B4 fails (residual out of band) |
| `missing_metadata` | Required fields absent/null | schema check fails -> `UNKNOWN` |
| `contradictory_signals` | Two approved reports about the same edge disagree | B-signals conflict beyond tolerance |
| `replay` | A previously-valid message re-sent | dedup on (recipient, sender, t) |
| `withholding` | An expected report is silently dropped | silent-neighbour expectation |
| `unknown_vehicle_type` | An entity/behaviour not in section A | no matching policy -> `UNKNOWN` |
| **`collusion` (OUT OF SCOPE)** | >=2 keys craft mutually-consistent lies | evades B-signals by construction; contained by revoke + audit, not detection |
| **`key_compromise` (OUT OF SCOPE)** | Admin/root key stolen | single point of total failure, stated |

---

## D. Decision policies (numbered, auditable)

Each policy is `condition -> classification / action`. A decision record cites the policy id(s) that fired. Classifications: `LEGITIMATE`, `SPOOFED_OR_FAULTY`, `UNKNOWN`.

- **P1 Local sensing wins.** If B3 (this junction senses the entity) → `LEGITIMATE` → preempt. (Cannot be spoofed remotely.)
- **P2 Auth gate.** If B1 fails (bad/absent/revoked/unauthorized key) → `SPOOFED_OR_FAULTY` (`invalid_id`/`signal_tampering`) → reject at the bus, do not process.
- **P3 Phantom refusal (safety-critical).** If B1 holds but neither B2 nor B3 (zero independent corroboration, no local sighting) → withhold preemption, stay on MaxPressure. A single message can NEVER force a green (this is the anti-phantom invariant; a valid-but-uncorroborated claim is treated as not-yet-actionable, not as true).
- **P4 Corroborated real.** If B1 and B2 and B4 and B5 all hold → `LEGITIMATE` → preempt / pre-clear.
- **P5 Implausible counts.** If B4 fails (residual out of band, persistent) → `SPOOFED_OR_FAULTY` (`count_inflation`) → discount the claim, log, and escalate to disambiguation if evidence is mixed.
- **P6 Contradiction.** If two approved reports about the same edge disagree beyond tolerance (B-signals conflict) → flag, discount both, escalate to disambiguation (the SLM's grey-zone job).
- **P7 Partial evidence (the ambiguous middle).** If B1 holds, evidence is partial (some but not decisive corroboration/plausibility/persistence) → this is the AMBIGUOUS case: escalate to the disambiguator (rule engine, then SLM) which reasons against P1-P6 and B1-B5 and returns a classification + the policies it applied.
- **P8 Unknown.** If no policy in P1-P7 cleanly applies (unknown vehicle type, missing metadata) → `UNKNOWN` → conservative reject + log for human review. Never a silent guess.

**Safety invariants (S1-S4, from `FORMAL-SPECIFICATION.md` §8), independent of classification:** min/max green, protected clearance, anti-starvation, and preemption only for a `LEGITIMATE` (corroborated or locally-sensed) entity. A classification can never violate these; the shield substitutes the deterministic choice if it would.

---

## E. Decision output contract (reasoning separated from classification)

Every disambiguation returns, and logs, a structured record (auditable):

```
{
  "case_id": "...",
  "policies_applied": ["P3", "B2"],      # which ground rules fired
  "reasoning": "no independent junction sensed the entity and this junction did not either; matches the phantom_ev pattern",
  "classification": "SPOOFED_OR_FAULTY",  # LEGITIMATE | SPOOFED_OR_FAULTY | UNKNOWN
  "confidence": 0.0-1.0,
  "steer_action": "stay_maxpressure" | "preempt(edge)" | "reallocate" | "reject"
}
```

The reasoning is produced BEFORE the classification so a wrong call is diagnosable, and the `policies_applied` field is what makes the decision auditable and traceable back to this document.

---

## F. Auditability guarantee

Every classification (rule or SLM) is written to the tamper-evident hash-chained audit log with its `policies_applied`, `classification`, and `confidence`. Auditability is itself a measured KPI: the fraction of decisions whose `policies_applied` is non-empty and whose classification is consistent with the cited policies. A decision that cites no policy is a defect (it means the system guessed), surfaced by the audit, not hidden.

---

## G. How this is consumed (build map)

- **Rule engine** (`ambiguous_decision.RuleDisambiguator`): encodes P1-P8 / B1-B5 as its logic; already partially built, to be aligned to these ids.
- **SLM** (`slm_agent`): retrieves the relevant policies (RAG) for a case and reasons against them, emitting the section E contract.
- **Data store / RAG** (to build): the policy corpus + a labelled past-case store, retrieved per case.
- **Adversarial test suite** (to build): organized by section C, with positive / negative / edge / `UNKNOWN` cases per category.
- **Metrics**: precision, recall, FPR, FNR per attack category, plus the section F auditability measure.
