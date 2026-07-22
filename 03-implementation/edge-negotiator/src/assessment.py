"""§6.3 assessment: mechanical ORIGIN classification over the VERIFIED audit log.

Full rewrite of the removed ``fault_attribution`` module. The old reader spoke the
pre-§11 singular schema (``driving_input_seq``, ``sig_valid``, scalar
``corroboration_count``, ``mp_choice``, ``trigger``) and emitted a human-vs-AI
VERDICT. Both are gone: the producer (§6.2) now emits the §11 record schemas
(message / sighting / decision, ``driving_input_seqs`` a PLURAL list of
``[seq, sighter_key]`` pairs), and the current spec forbids a machine verdict in
the forensic channel (§7/§12 D2). This module produces a SPLIT instead.

Two clearly-separated outputs (§5 / §12 D2)
-------------------------------------------
``fault_report`` returns ``{status, refusal, evidence_pack, internal_note}``:

  * ``evidence_pack`` — only mechanically-true, reproducible facts (verified
    sender-key results, chain/completeness results, WHICH corroboration checks
    are independent [mechanical, origin-independent], neutral cited-rule text).
    It carries NO ``candidate_origin`` / confidence / ``fault_weight`` / "attacker"
    / "lie" / "verdict" label. Header: "Provenance record; not a determination of
    legal fault." This is the CLOSED forensic channel.
  * ``internal_note`` — the mechanical ORIGIN classification (the scored 3-class
    subset). Counsel-gated; NEVER merged into the pack.

Two NAMED signature layers, kept distinct (§6.3)
------------------------------------------------
  * ISSUER layer — ``AuditLog.verify_signatures(registry_der_dict)``, driven by
    ``system._audit_bundle``. Verifies each entry's ENVELOPE signature (the issuer
    that appended it). NOT this module's job; documented here for the reader.
  * SENDER layer — THIS module. Per causal SENDER message record it runs
    ``identity.verify(registry_der[sender], canonical_bytes(sp.sender, sp.t,
    sp.payload), bytes.fromhex(sender_signature))``. A keyless ``kind:"sighting"``
    carries no sender signature (§11), so the sender layer skips it.

Gates before attributing (fail loud, §6.3/§6.7)
-----------------------------------------------
``fault_report`` runs ``verify_chain()`` ONCE, a window-completeness check, and
``identity.verify`` per causal sender; on ANY failure it REFUSES with ``UNKNOWN``
(crypto/integrity) or ``INCOMPLETE_DISCLOSURE`` (window not complete) — never a
silent/null result, never a green attribution. The FULL external quorum-anchor +
cross-auditor completeness proof is OUT of the overnight subset (§11 build order);
the completeness gate here is the in-window structural proxy (every referenced
driving-input seq resolves to a present record). Documented, not hidden.

The origin is decided by MECHANICAL PROVENANCE PREDICATES over exactly two
features (signing-key count; recomputed independent-corroboration count over
``driving_input_seqs``) — never the SLM, and this module NEVER reads the runtime
``classification`` field. Corroboration is RECOMPUTED from independently-signed
records (§6.6), never a self-asserted scalar. Where the origin is a signing party
it names the KEY identifier as recorded, never a person.

Pure + deterministic: reads records, never mutates them, always returns fresh
objects.
"""
from __future__ import annotations

from identity import verify as _identity_verify
from message_bus import canonical_bytes
# ONE canonical reader-side flatten (lifts event.* + preserves the envelope seq +
# carries the envelope issuer/signature). Reused, never re-implemented here.
from system_ev import flatten_entries as flatten

# --------------------------------------------------------------------------- #
# ORIGIN ontology (§2 full set) + the SCORED 3-class subset (§2/§3).
# --------------------------------------------------------------------------- #
# Full ontology constants may exist; the SCORED subset is exactly the 3 below +
# unknown. `colluding-keys` / `system-classifier` / `system-detector` are NOT in
# the overnight scored subset (they need a predicate that does not exist here) —
# they resolve to `unknown`, honestly.
ATTACKER_KEY = "attacker-key"
SYSTEM_CLASSIFIER = "system-classifier"
SYSTEM_DETECTOR = "system-detector"
SENSOR_FED_SPOOF = "sensor-fed-spoof"
COLLUDING_KEYS = "colluding-keys"
LEGITIMATE = "legitimate"
UNKNOWN = "unknown"

ORIGIN_ONTOLOGY = frozenset({
    ATTACKER_KEY, SYSTEM_CLASSIFIER, SYSTEM_DETECTOR, SENSOR_FED_SPOOF,
    COLLUDING_KEYS, LEGITIMATE, UNKNOWN,
})

# The scored 3-class subset labels (the genuinely 2-feature-decidable classes).
KEYLESS_LONE_SIGHTING = "keyless-lone-sighting"   # -> sensor-fed-spoof
UNCORROBORATED_SIGNED = "uncorroborated-signed"   # -> attacker-key (the E2 rule)
CORROBORATED = "corroborated"                     # -> legitimate

# Refusal tokens (never a green attribution). UNKNOWN doubles as the crypto/
# integrity refusal token; INCOMPLETE_DISCLOSURE is the completeness refusal.
INCOMPLETE_DISCLOSURE = "INCOMPLETE_DISCLOSURE"

# Overnight SET->culprit rule (build F1): culprit = attacker-key iff recomputed
# independent-corroboration count == 0 over driving_input_seqs. The marginal
# "need > corroborated magnitude" (piggyback) form is a DEFERRED leave-one-out
# recompute that lands in Experiment D — marked, never a silent gap.
NOT_IMPLEMENTED_OVERNIGHT = "NOT_IMPLEMENTED_OVERNIGHT"

# §7.1 pack header.
PACK_HEADER = "Provenance record; not a determination of legal fault."

# Origin-INDEPENDENT cited-rule selection (a pure function of outcome.type). These
# are neutral mechanical check names, NOT legal accusations — the binding-statute
# citation oracle is the deferred §9 ground_rules / Job-A work. §6.10 / D2: the
# citation set must NOT be a function of the injected origin.
_CITED_RULES_BY_TYPE = {
    "false_preemption": ("provenance-completeness-check",
                         "corroboration-independence-check"),
    "missed_ev": ("provenance-completeness-check",
                  "corroboration-independence-check"),
}
_DEFAULT_CITED_RULES = ("provenance-completeness-check",)


# --------------------------------------------------------------------------- #
# Record helpers (pure; never mutate).
# --------------------------------------------------------------------------- #

def _by_seq(records) -> dict:
    """Map envelope seq -> record for every seq-bearing record."""
    out: dict = {}
    for r in records:
        if isinstance(r, dict) and "seq" in r:
            out[r["seq"]] = r
    return out


def _driving_pairs(decision) -> list:
    """The ``[seq, sighter_key]`` pairs of a decision as (seq, key) tuples.

    Rejects malformed entries at the boundary; never raises. ``key`` is ``None``
    for a keyless input (§11 keyless encoding)."""
    pairs = decision.get("driving_input_seqs") if isinstance(decision, dict) else None
    if not isinstance(pairs, list):
        return []
    out: list = []
    for p in pairs:
        if isinstance(p, (list, tuple)) and len(p) == 2:
            out.append((p[0], p[1]))
    return out


def _ev_id_of(record) -> object:
    """Recover the ev id from a driving-input record (§6.3/§11 reconciliation).

    * keyless ``kind:"sighting"`` -> its ``ev_id``.
    * ``kind:"message"`` -> ``signed_payload.payload.ev_claim.ev_id`` (a signed
      advance-claim) OR ``signed_payload.payload.sighting.ev_id`` (a signed
      sighting-as-message; signed sightings ride ``kind:"message"``, §6.6).
    Anything else -> ``None``.
    """
    if not isinstance(record, dict):
        return None
    kind = record.get("kind")
    if kind == "sighting":
        return record.get("ev_id")
    if kind == "message":
        payload = (record.get("signed_payload") or {}).get("payload") or {}
        if isinstance(payload, dict):
            claim = payload.get("ev_claim")
            if isinstance(claim, dict) and claim.get("ev_id") is not None:
                return claim.get("ev_id")
            sighting = payload.get("sighting")
            if isinstance(sighting, dict):
                return sighting.get("ev_id")
    return None


def _outcome_ref(outcome) -> dict:
    """A neutral, fact-only reference to the outcome (no origin signal)."""
    if not isinstance(outcome, dict):
        return {"junction": None, "t": None, "ev_id": None, "type": None}
    return {k: outcome.get(k) for k in ("junction", "t", "ev_id", "type")}


# --------------------------------------------------------------------------- #
# Causal-decision selector over the NEW schema (no mp_choice / trigger).
# --------------------------------------------------------------------------- #

def _select_causal_decision(records, outcome):
    """The decision whose driving input's ev id == ``outcome.ev_id`` (§6.3).

    Walks each decision's ``driving_input_seqs`` -> input record -> its ev id, and
    matches on ``outcome.ev_id`` (covering BOTH message-borne and keyless-sighting
    inputs). This is NOT positional/recency/seq-order — the frozen E2 fixture is
    built so only this walk recovers its non-monotone id->causal-seq permutation.
    When several decisions match (not the case in the fixture) the earliest by seq
    is chosen deterministically.
    """
    if not isinstance(outcome, dict):
        return None
    ev_id = outcome.get("ev_id")
    if ev_id is None:
        return None
    junction = outcome.get("junction")
    by_seq = _by_seq(records)
    matches: list = []
    for r in records:
        if not isinstance(r, dict) or r.get("kind") != "decision":
            continue
        if junction is not None and r.get("junction") not in (None, junction):
            continue
        for seq, _key in _driving_pairs(r):
            if _ev_id_of(by_seq.get(seq)) == ev_id:
                matches.append(r)
                break
    if not matches:
        return None
    matches.sort(key=lambda d: d.get("seq", 0))
    return matches[0]


def _completeness(records, decision):
    """In-window structural completeness: every driving-input seq resolves.

    Returns ``(ok, missing_seqs)``. The FULL external quorum-anchor + cross-audit
    completeness proof is deferred (§11); this is the local proxy the reader can
    compute without the anchor.
    """
    by_seq = _by_seq(records)
    missing = [seq for seq, _k in _driving_pairs(decision) if seq not in by_seq]
    return (not missing, missing)


def _claimer_key(records, decision, ev_id):
    """The signing key of the driving input that CLAIMED ``ev_id`` (or None).

    The claimer is the earliest-by-seq driving input whose resolved ev id equals
    the outcome ev id. A keyless claim yields ``None`` (its key-count is 0).
    """
    by_seq = _by_seq(records)
    for seq, key in sorted(_driving_pairs(decision), key=lambda p: (p[0] is None, p[0])):
        if _ev_id_of(by_seq.get(seq)) == ev_id:
            return key
    return None


def _features(records, decision, outcome):
    """The two mechanical features over ``driving_input_seqs`` (§2/§3/§6.6).

    * ``key_count`` — distinct non-null signing keys among the driving inputs.
    * ``indep_corrob`` — distinct non-null signing keys DIFFERENT from the claimer
      key (a self-sighting under the claimer's own key does NOT count — RECOMPUTED
      from independently-signed records, never a self-asserted scalar).
    Returns ``(key_count, indep_corrob, claimer_key)``.

    Defense-in-depth note (gate-verified path): the signing keys are read from the
    decision's ``driving_input_seqs`` pair labels, which are chain-committed and,
    on the ``fault_report`` path, each causal message's signature is verified per
    SENDER against the trusted registry -- so a mislabelled pair would break
    ``verify_chain`` or the sender gate. A stronger form would re-derive each key
    directly from the resolved driving-input record's verified sender; deferred as
    equivalent-under-the-gate (§6.6 permits reading the key from the record).
    """
    ev_id = outcome.get("ev_id") if isinstance(outcome, dict) else None
    claimer = _claimer_key(records, decision, ev_id)
    signing_keys = {k for _s, k in _driving_pairs(decision) if k is not None}
    indep_keys = {k for k in signing_keys if k != claimer}
    return len(signing_keys), len(indep_keys), claimer


# --------------------------------------------------------------------------- #
# Origin classification (PRIVATE pure core; runs NO crypto gate). Underscore-
# prefixed on purpose: it must ONLY be called on ALREADY-VERIFIED provenance --
# by `fault_report` AFTER its verify_chain + sender-signature + completeness
# gates pass, or by the E2 fixture test whose `_scope` declares crypto out-of-
# band. Calling it on unverified records would attribute an origin without the
# §6.3 gate (a spoofed record classified, or an honest key framed) -- never do
# that; go through `fault_report`.
# --------------------------------------------------------------------------- #

def _classify_outcome(records, outcome) -> dict:
    """Mechanically classify ONE outcome's origin from verified provenance.

    Returns the INTERNAL note dict (counsel-gated; never merged into the pack).
    NEVER reads the runtime ``classification`` field; decides purely from the two
    mechanical features. Honest ``unknown`` where the features cannot decide (no
    causal decision, or the provenance-indistinguishable veracity/collusion cell).
    """
    records = list(records)
    decision = _select_causal_decision(records, outcome)
    note = {
        "outcome_id": outcome.get("id") if isinstance(outcome, dict) else None,
        "outcome_ref": _outcome_ref(outcome),
        "causal_decision_seq": None,
        "origin": UNKNOWN,
        "culprit_key": None,
        "scored_class": None,
        "signing_key_count": None,
        "independent_corroboration_count": None,
        "marginal_piggyback_rule": NOT_IMPLEMENTED_OVERNIGHT,
        "rationale": "no causal decision matched the outcome ev_id",
    }
    if decision is None:
        return note

    key_count, indep_corrob, claimer = _features(records, decision, outcome)
    note = {
        **note,
        "causal_decision_seq": decision.get("seq"),
        "signing_key_count": key_count,
        "independent_corroboration_count": indep_corrob,
    }

    if key_count == 0:
        # keyless lone sighting (§6.4 sensor-fed-spoof surface).
        return {
            **note,
            "origin": SENSOR_FED_SPOOF,
            "culprit_key": None,
            "scored_class": KEYLESS_LONE_SIGHTING,
            "rationale": ("driving input is a keyless sighting (signing-key-count 0); "
                          "§6.4 sensor-fed-spoof, no key to attribute"),
        }
    if indep_corrob == 0:
        # validly-signed but uncorroborated -> the E2 rule (attacker-key).
        return {
            **note,
            "origin": ATTACKER_KEY,
            "culprit_key": claimer,
            "scored_class": UNCORROBORATED_SIGNED,
            "rationale": ("validly-signed but recomputed independent-corroboration is 0 "
                          "over driving_input_seqs (§3 E2 rule); attributed to the "
                          "signing key, never a person"),
        }
    # independently corroborated (>=2 keys). Colluding-keys vs legitimate is the
    # same provenance-indistinguishable veracity judgment as the triad (§8) -> NOT
    # separately scored; the scored subset maps this cell to legitimate.
    return {
        **note,
        "origin": LEGITIMATE,
        "culprit_key": None,
        "scored_class": CORROBORATED,
        "rationale": ("independent corroboration present (>=2 distinct signing keys); "
                      "colluding-keys vs legitimate is provenance-indistinguishable "
                      "and is NOT separately scored"),
    }


# --------------------------------------------------------------------------- #
# The SENDER signature layer + the evidence pack (mechanical, origin-independent).
# --------------------------------------------------------------------------- #

def _verify_senders(records, decision, registry_der_dict):
    """SENDER layer: identity.verify per causal signed MESSAGE record (§6.3).

    Keyless sightings carry no sender signature (§11) and are skipped. Returns
    ``(results, ok)`` where ``ok`` is False if any signed causal message's sender
    signature fails to verify against the trusted registry DER for its sender
    (unknown sender, malformed signature, or Ed25519 mismatch).
    """
    by_seq = _by_seq(records)
    reg = registry_der_dict if isinstance(registry_der_dict, dict) else {}
    results: list = []
    ok = True
    for seq, _key in _driving_pairs(decision):
        rec = by_seq.get(seq)
        if not isinstance(rec, dict) or rec.get("kind") != "message":
            continue  # keyless sighting: no sender-layer signature to verify
        sender = rec.get("sender")
        sp = rec.get("signed_payload") or {}
        sig_hex = rec.get("sender_signature")
        der = reg.get(sender)
        verified = False
        if der is not None and isinstance(sig_hex, str):
            try:
                verified = _identity_verify(
                    der,
                    canonical_bytes(sp.get("sender"), sp.get("t"), sp.get("payload")),
                    bytes.fromhex(sig_hex),
                )
            except (ValueError, TypeError):
                verified = False
        results.append({"seq": seq, "sender": sender,
                        "sender_signature_verified": bool(verified)})
        if not verified:
            ok = False
    return results, ok


def _corroboration_checks(records, decision) -> list:
    """Mechanical, origin-INDEPENDENT corroboration facts per driving input.

    Names the KEY identifier (never a person) and states whether each input is
    independently-signed relative to the claim. Carries NO origin/verdict label.
    """
    by_seq = _by_seq(records)
    pairs = _driving_pairs(decision)
    # The claim key = the earliest signing key present among the inputs (mechanical;
    # independent of any origin decision).
    claim_key = None
    for _seq, key in sorted(pairs, key=lambda p: (p[0] is None, p[0])):
        if key is not None:
            claim_key = key
            break
    checks: list = []
    for seq, key in pairs:
        rec = by_seq.get(seq)
        checks.append({
            "seq": seq,
            "signing_key": key,
            "kind": rec.get("kind") if isinstance(rec, dict) else None,
            "independently_signed": bool(key is not None and key != claim_key),
        })
    return checks


def _cited_rules(outcome) -> list:
    """Origin-INDEPENDENT neutral cited-rule text (pure function of outcome.type)."""
    t = outcome.get("type") if isinstance(outcome, dict) else None
    return list(_CITED_RULES_BY_TYPE.get(t, _DEFAULT_CITED_RULES))


def _evidence_pack(outcome, records, decision, *, chain_ok, sender_results,
                   completeness_ok) -> dict:
    """The EVIDENCE PACK — mechanically-true facts ONLY (§7.1 / §12 D2).

    NO candidate_origin / confidence / fault_weight / "attacker" / "lie" /
    "verdict". Header states it is not a determination of legal fault.
    """
    corr_checks = _corroboration_checks(records, decision) if decision else []
    return {
        "header": PACK_HEADER,
        "outcome_ref": _outcome_ref(outcome),
        "causal_decision_seq": decision.get("seq") if isinstance(decision, dict) else None,
        "chain_verified": bool(chain_ok),
        "window_complete": bool(completeness_ok),
        "sender_signature_checks": list(sender_results),
        "corroboration_checks": corr_checks,
        "cited_rules": _cited_rules(outcome),
        "legal_causation": "NOT_ASSESSED",
    }


def _refusal(outcome, token, reason, records, *, chain_ok, causal=None,
             sender_results=None):
    """Build a REFUSED result (never a green attribution)."""
    note = {
        "outcome_id": outcome.get("id") if isinstance(outcome, dict) else None,
        "outcome_ref": _outcome_ref(outcome),
        "causal_decision_seq": causal.get("seq") if isinstance(causal, dict) else None,
        "origin": token,          # UNKNOWN or INCOMPLETE_DISCLOSURE — refusal, not a class
        "culprit_key": None,
        "scored_class": None,
        "signing_key_count": None,
        "independent_corroboration_count": None,
        "marginal_piggyback_rule": NOT_IMPLEMENTED_OVERNIGHT,
        "rationale": reason,
    }
    pack = _evidence_pack(outcome, records, causal, chain_ok=chain_ok,
                          sender_results=sender_results or [],
                          completeness_ok=(token != INCOMPLETE_DISCLOSURE))
    return {"status": "REFUSED", "refusal": token,
            "evidence_pack": pack, "internal_note": note}


# --------------------------------------------------------------------------- #
# The gated entry point.
# --------------------------------------------------------------------------- #

def fault_report(audit_log, registry_der_dict, outcome) -> dict:
    """Attribute one ``outcome`` over a VERIFIED AuditLog, then SPLIT the output.

    ``registry_der_dict`` maps ``sender junction_id -> DER public-key bytes`` (the
    trusted registry keys, §6.1). Gates (fail loud): ``verify_chain`` once, a
    window-completeness proxy, and ``identity.verify`` per causal sender. On ANY
    failure returns ``status:"REFUSED"`` with ``UNKNOWN`` / ``INCOMPLETE_DISCLOSURE``.
    On success returns ``status:"OK"`` with a firewalled ``evidence_pack`` +
    ``internal_note``.
    """
    records = list(flatten(audit_log))

    # Gate 1 (integrity): recompute the hash chain ONCE.
    if not audit_log.verify_chain():
        return _refusal(outcome, UNKNOWN,
                        "hash-chain verification failed (tampered log)",
                        records, chain_ok=False)

    decision = _select_causal_decision(records, outcome)
    if decision is None:
        # Not a gate failure: the window verified but no decision explains the
        # outcome. Honest UNKNOWN origin (not silent/null), pack still emitted.
        note = _classify_outcome(records, outcome)
        pack = _evidence_pack(outcome, records, None, chain_ok=True,
                              sender_results=[], completeness_ok=True)
        return {"status": "OK", "refusal": None,
                "evidence_pack": pack, "internal_note": note}

    # Gate 2 (completeness): every referenced driving input resolves in-window.
    complete, missing = _completeness(records, decision)
    if not complete:
        return _refusal(outcome, INCOMPLETE_DISCLOSURE,
                        f"driving-input seqs absent from the window: {missing}",
                        records, chain_ok=True, causal=decision)

    # Gate 3 (SENDER layer): identity.verify per causal signed message.
    sender_results, sender_ok = _verify_senders(records, decision, registry_der_dict)
    if not sender_ok:
        return _refusal(outcome, UNKNOWN,
                        "a causal sender signature failed identity.verify",
                        records, chain_ok=True, causal=decision,
                        sender_results=sender_results)

    # Gates passed -> classify + split into pack (facts) and note (origin).
    note = _classify_outcome(records, outcome)
    pack = _evidence_pack(outcome, records, decision, chain_ok=True,
                          sender_results=sender_results, completeness_ok=True)
    return {"status": "OK", "refusal": None,
            "evidence_pack": pack, "internal_note": note}
