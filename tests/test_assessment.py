"""Tests for assessment.py (§6.3): the mechanical ORIGIN classifier + the SPLIT
over the §11 producer schema. Replaces test_fault_attribution.py atomically.

Fault-finding, not fake-green — each test fails if the logic it checks breaks:
  * break the ev_id causal walk        -> the E2 fixture test fails (non-monotone).
  * count a self-sighting as corroboration -> attacker-key flips to legitimate.
  * break the corroboration recompute  -> attacker-key vs legitimate flips.
  * break the identity.verify SENDER gate -> the tamper test stops refusing.
  * break verify_chain gating          -> the broken-chain test stops refusing.
  * leak an origin into the pack        -> the pack-purity test fails.
"""
import json
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import assessment as A  # noqa: E402
from audit_log import AuditLog  # noqa: E402
from conservation import ConservationChecker  # noqa: E402
from coordinated_controller import StubAgent  # noqa: E402
from emergency_controller import EmergencyController  # noqa: E402
from identity import JunctionIdentity  # noqa: E402
from message_bus import MessageBus, canonical_bytes  # noqa: E402
from registry import Registry  # noqa: E402
from system_ev import flatten_entries  # noqa: E402

_FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "fixtures", "e2_worked_example.json")

ADJ = {"A0": ["A1", "B0"], "A1": ["A0", "B1"],
       "B0": ["A0", "B1"], "B1": ["A1", "B0"]}


# --------------------------------------------------------------------------- #
# Synthetic flat-record builders (the §11 shape the reader consumes).
# --------------------------------------------------------------------------- #

def _msg(seq, sender, ev_id):
    return {"kind": "message", "seq": seq, "sender": sender,
            "sender_pubkey_fpr": None, "sender_pubkey_der": None,
            "signed_payload": {"sender": sender, "t": 100,
                               "payload": {"ev_claim": {"ev_id": ev_id}}},
            "sender_signature": "00" * 64}


def _signed_sighting_msg(seq, sender, ev_id):
    return {"kind": "message", "seq": seq, "sender": sender,
            "signed_payload": {"sender": sender, "t": 100,
                               "payload": {"sighting": {"ev_id": ev_id}}},
            "sender_signature": "00" * 64}


def _keyless_sighting(seq, ev_id):
    return {"kind": "sighting", "seq": seq, "sighter_key": None,
            "ev_id": ev_id, "approach": "in_A", "t": 100, "position": None}


def _decision(seq, junction, pairs, ev="X"):
    return {"kind": "decision", "seq": seq, "junction": junction,
            "driving_input_seqs": [list(p) for p in pairs], "t": 150.0,
            "executed": "preempt", "classification": "LEGITIMATE",
            "policies_applied": ["corroboration"]}


def _outcome(ev_id, junction="J1"):
    return {"type": "false_preemption", "junction": junction, "t": 160, "ev_id": ev_id}


# --------------------------------------------------------------------------- #
# 1. The FROZEN E2 fixture: causal walk + 3-class origins vs pinned expectations.
# --------------------------------------------------------------------------- #

def test_e2_fixture_reproduces_pinned_origins_and_causal_seqs():
    """Load the read-only fixture; feed ONLY records+outcomes to the classifier;
    compare to the out-of-band `expected`. Only the ev_id causal walk + the
    two-feature partition (with the self-sighting NOT counted) passes all three.
    Fails if the selector is positional/recency or the self-sighting corroborates.
    """
    with open(_FIXTURE, encoding="utf-8") as fh:
        fixture = json.load(fh)
    records = fixture["records"]              # already flat §11 records
    outcomes = {o["id"]: o for o in fixture["outcomes"]}
    expected = {e["outcome_id"]: e for e in fixture["expected"]}

    for oid, exp in expected.items():
        note = A._classify_outcome(records, outcomes[oid])
        assert note["causal_decision_seq"] == exp["causal_decision_seq"], oid
        assert note["origin"] == exp["origin"], oid
        assert note["culprit_key"] == exp["culprit_key_fpr"], oid

    # The recovered id->causal-seq map is the pinned NON-MONOTONE permutation.
    got = {oid: A._classify_outcome(records, outcomes[oid])["causal_decision_seq"]
           for oid in ("o1", "o2", "o3")}
    assert got == {"o1": 8, "o2": 10, "o3": 4}


# --------------------------------------------------------------------------- #
# 2. The scored 3-class subset by mechanical predicate.
# --------------------------------------------------------------------------- #

def test_keyless_lone_sighting_is_sensor_fed_spoof():
    records = [_keyless_sighting(1, "EV"), _decision(2, "J1", [(1, None)])]
    note = A._classify_outcome(records, _outcome("EV"))
    assert note["origin"] == A.SENSOR_FED_SPOOF
    assert note["scored_class"] == A.KEYLESS_LONE_SIGHTING
    assert note["culprit_key"] is None
    assert note["signing_key_count"] == 0


def test_uncorroborated_signed_is_attacker_key():
    records = [_msg(1, "A1", "EV"), _decision(2, "J1", [(1, "A1")])]
    note = A._classify_outcome(records, _outcome("EV"))
    assert note["origin"] == A.ATTACKER_KEY
    assert note["scored_class"] == A.UNCORROBORATED_SIGNED
    assert note["culprit_key"] == "A1"          # names the KEY, not a person
    assert note["independent_corroboration_count"] == 0


def test_independent_second_key_flips_to_legitimate():
    """Same claim, but a DIFFERENT key independently sighted it -> corroborated ->
    legitimate. Flipping the second key back to the claimer (self-sighting) must
    return attacker-key — the corroboration-recompute discriminator."""
    corroborated = [_msg(1, "A1", "EV"), _signed_sighting_msg(2, "B1", "EV"),
                    _decision(3, "J1", [(1, "A1"), (2, "B1")])]
    note = A._classify_outcome(corroborated, _outcome("EV"))
    assert note["origin"] == A.LEGITIMATE
    assert note["scored_class"] == A.CORROBORATED
    assert note["independent_corroboration_count"] == 1

    self_sighting = [_msg(1, "A1", "EV"), _signed_sighting_msg(2, "A1", "EV"),
                     _decision(3, "J1", [(1, "A1"), (2, "A1")])]
    note2 = A._classify_outcome(self_sighting, _outcome("EV"))
    assert note2["origin"] == A.ATTACKER_KEY, "a self-sighting must NOT corroborate"
    assert note2["independent_corroboration_count"] == 0


def test_no_causal_decision_is_unknown():
    records = [_msg(1, "A1", "EV"), _decision(2, "J1", [(1, "A1")])]
    note = A._classify_outcome(records, _outcome("SOMETHING-ELSE"))
    assert note["origin"] == A.UNKNOWN
    assert note["causal_decision_seq"] is None
    assert note["culprit_key"] is None


def test_selector_covers_both_message_and_keyless_sighting_inputs():
    """One decision driven by a keyless sighting, one by a signed message; each
    outcome resolves to the correct decision purely by the ev_id walk."""
    records = [
        _keyless_sighting(1, "EV-K"), _decision(2, "J1", [(1, None)]),
        _msg(3, "A1", "EV-M"), _decision(4, "J1", [(3, "A1")]),
    ]
    assert A._classify_outcome(records, _outcome("EV-K"))["causal_decision_seq"] == 2
    assert A._classify_outcome(records, _outcome("EV-M"))["causal_decision_seq"] == 4


def test_marginal_piggyback_rule_is_marked_deferred():
    records = [_msg(1, "A1", "EV"), _decision(2, "J1", [(1, "A1")])]
    note = A._classify_outcome(records, _outcome("EV"))
    assert note["marginal_piggyback_rule"] == A.NOT_IMPLEMENTED_OVERNIGHT


# --------------------------------------------------------------------------- #
# 3. Completeness proxy + flatten canonicity.
# --------------------------------------------------------------------------- #

def test_completeness_flags_a_dangling_driving_input():
    records = [_msg(1, "A1", "EV"), _decision(2, "J1", [(1, "A1"), (99, "A1")])]
    decision = A._select_causal_decision(records, _outcome("EV"))
    ok, missing = A._completeness(records, decision)
    assert ok is False and missing == [99]


def test_flatten_is_the_one_canonical_system_ev_implementation():
    assert A.flatten is flatten_entries


# --------------------------------------------------------------------------- #
# 4. The gated entry point over a REAL producer log.
# --------------------------------------------------------------------------- #

def _phantom_ev_log():
    """Build a real §6.2 producer log: A1 signs a phantom ev_claim to A0; the
    naive victim consumes it and emits the message + EV decision records. Returns
    (audit, identities, registry, phantom_id)."""
    conn = __import__("system_fakeconn").FakeConn(
        {"A1A0_0": 1, "B0A0_0": 8, "A0A1_0": 0, "A0B0_0": 0})
    identities = {j: JunctionIdentity(j) for j in ("A0", "A1", "B0", "B1")}
    registry = Registry()
    for j, ident in identities.items():
        registry.register(j, ident.public_key)
    bus = MessageBus(registry, ADJ)
    ev_bus = MessageBus(registry, ADJ)
    audit = AuditLog()
    ctrl = EmergencyController(
        conn, ["A0"], StubAgent(), identities=identities, registry=registry,
        bus=bus, adjacency=ADJ, checker=ConservationChecker(tolerance=2),
        slm_junctions=["A0"], gate=2, coord_weight=0.0, ev_bus=ev_bus,
        corroboration_required=False, preemption_enabled=True,
        advance_claims_enabled=True, verbose=False, audit_log=audit)
    phantom_id = "PHANTOM-AMB"
    ctrl.inject_phantom_claim("A1", "A0", phantom_id, "A1A0")
    ctrl.decide("A0", ctrl.tls["A0"])
    return audit, identities, registry, phantom_id


def _der_dict(identities):
    return {j: ident.public_key for j, ident in identities.items()}


def test_fault_report_attributes_uncorroborated_phantom_to_the_key():
    audit, identities, registry, phantom_id = _phantom_ev_log()
    r = A.fault_report(audit, _der_dict(identities), _outcome(phantom_id, "A0"))
    assert r["status"] == "OK"
    note = r["internal_note"]
    assert note["origin"] == A.ATTACKER_KEY
    assert note["culprit_key"] == "A1"          # the signing key drove the phantom
    # sender layer actually ran and passed on the untampered log.
    assert any(c["sender_signature_verified"] for c in r["evidence_pack"]["sender_signature_checks"])


def _rebuild_with_tampered_sender(audit, identities, tamper_seq):
    """Re-append every event, replacing ONE message's sender_signature with a
    valid-FORM signature from a DIFFERENT JunctionIdentity. Recomputing the chain
    on re-append keeps verify_chain()==True and the ISSUER layer valid; only the
    SENDER layer (identity.verify) can now reject."""
    imposter = JunctionIdentity("A1")           # different key, same id label
    rebuilt = AuditLog()
    for e in audit.entries():
        event = dict(e["event"])
        if e["seq"] == tamper_seq and event.get("kind") == "message":
            sp = event["signed_payload"]
            forged = imposter.sign(canonical_bytes(sp["sender"], sp["t"], sp["payload"]))
            event = {**event, "sender_signature": forged.hex()}
        issuer = identities.get(e["issuer"]) if e["issuer"] else None
        rebuilt.append(event, issuer=issuer)
    return rebuilt


def test_fault_report_refuses_on_tampered_sender_signature():
    """Isolates the identity.verify SENDER layer: verify_chain stays True and the
    ISSUER layer still verifies, yet the report refuses because the causal sender
    signature no longer matches the registry key."""
    audit, identities, registry, phantom_id = _phantom_ev_log()
    der_dict = _der_dict(identities)
    outcome = _outcome(phantom_id, "A0")
    # The causal decision + the seq of its signed driving message.
    records = list(flatten_entries(audit))
    causal = A._select_causal_decision(records, outcome)
    msg_seq = causal["driving_input_seqs"][0][0]

    tampered = _rebuild_with_tampered_sender(audit, identities, msg_seq)
    # Chain intact AND issuer layer intact -> only the sender layer can object.
    assert tampered.verify_chain() is True
    assert tampered.verify_signatures(der_dict) is True

    r = A.fault_report(tampered, der_dict, outcome)
    assert r["status"] == "REFUSED"
    assert r["refusal"] == A.UNKNOWN
    assert r["internal_note"]["origin"] == A.UNKNOWN
    assert r["internal_note"]["culprit_key"] is None    # never a green attribution


def test_fault_report_refuses_on_broken_chain():
    audit, identities, registry, phantom_id = _phantom_ev_log()
    # Mutate a field INSIDE the hashed event body -> verify_chain must fail.
    audit._log[-1]["event"]["executed"] = "tampered"
    assert audit.verify_chain() is False
    r = A.fault_report(audit, _der_dict(identities), _outcome(phantom_id, "A0"))
    assert r["status"] == "REFUSED"
    assert r["refusal"] == A.UNKNOWN


# --------------------------------------------------------------------------- #
# 5. The SPLIT — evidence pack purity (§12 D2).
# --------------------------------------------------------------------------- #

_FORBIDDEN = ("attacker", "verdict", "confidence", "candidate_origin", "lie")


def test_evidence_pack_has_no_forbidden_labels_and_carries_header():
    audit, identities, registry, phantom_id = _phantom_ev_log()
    r = A.fault_report(audit, _der_dict(identities), _outcome(phantom_id, "A0"))
    pack = r["evidence_pack"]
    # The origin lives ONLY in the internal note, never the pack.
    assert "candidate_origin" not in pack
    assert "origin" not in pack
    blob = json.dumps(pack).lower()
    for term in _FORBIDDEN:
        assert term not in blob, f"forbidden term {term!r} leaked into the pack"
    assert pack["header"] == A.PACK_HEADER
    assert pack["legal_causation"] == "NOT_ASSESSED"
    # The internal note DOES carry the origin (proves the split is real, not that
    # the origin was simply dropped everywhere).
    assert r["internal_note"]["origin"] == A.ATTACKER_KEY


def test_pack_citation_is_origin_independent():
    """Same outcome.type -> identical cited_rules whether the origin is attacker-key
    or legitimate (§6.10). The citation set is not a function of the origin."""
    attacker = [_msg(1, "A1", "EV"), _decision(2, "J1", [(1, "A1")])]
    legit = [_msg(1, "A1", "EV"), _signed_sighting_msg(2, "B1", "EV"),
             _decision(3, "J1", [(1, "A1"), (2, "B1")])]
    o = _outcome("EV")
    dec_a = A._select_causal_decision(attacker, o)
    dec_l = A._select_causal_decision(legit, o)
    pack_a = A._evidence_pack(o, attacker, dec_a, chain_ok=True,
                              sender_results=[], completeness_ok=True)
    pack_l = A._evidence_pack(o, legit, dec_l, chain_ok=True,
                              sender_results=[], completeness_ok=True)
    # Different origins (attacker-key vs legitimate) ...
    assert A._classify_outcome(attacker, o)["origin"] == A.ATTACKER_KEY
    assert A._classify_outcome(legit, o)["origin"] == A.LEGITIMATE
    # ... but identical cited-rule sets.
    assert pack_a["cited_rules"] == pack_l["cited_rules"]
