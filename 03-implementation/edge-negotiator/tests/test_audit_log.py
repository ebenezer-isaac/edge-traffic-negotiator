"""Adversarial tests for src/audit_log.py.

Append-only, tamper-evident DECISION + EVENT audit log with a sha256 hash-chain
(mirroring registry.py), Ed25519 issuer signatures, Merkle batch anchoring (the
bridge to the ~2.1 s Besu write), and JSONL persistence.

Run from the edge-negotiator dir:
    .venv/Scripts/python -m pytest tests/test_audit_log.py -q

Per the testing rules these tests exist to BREAK the code: chain/reorder tamper,
forged Merkle proofs, swapped signatures, JSONL round-trip + tamper rejection,
and boundary/garbage inputs.
"""
import copy
import hashlib
import json
import os
import sys

import pytest

# Put src/ on sys.path so `import audit_log` works without packaging.
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from audit_log import (  # noqa: E402
    GENESIS_PREV_HASH,
    AuditLog,
    verify_inclusion,
)
from identity import JunctionIdentity  # noqa: E402


def _decision_event(tls="A0", used=1):
    """A realistic per-decision event (shape from CoordinatedController.events)."""
    return {
        "tls": tls,
        "halting": [3, 7, 2],
        "slm_phase": used,
        "shield_phase": 1,
        "used": used,
        "tick": 0,
        "detections": [],
    }


def _populated(n=5):
    log = AuditLog()
    for i in range(n):
        log.append(_decision_event(tls=f"A{i}", used=i % 3))
    return log


# -- happy path: chain ---------------------------------------------------------

def test_empty_log_verifies_and_is_empty():
    log = AuditLog()
    assert len(log) == 0
    assert log.entries() == []
    assert log.verify_chain() is True


def test_append_returns_chained_entry_with_genesis_prev_hash():
    log = AuditLog()
    entry = log.append(_decision_event())
    assert entry["seq"] == 0
    assert entry["prev_hash"] == GENESIS_PREV_HASH
    assert entry["event"]["tls"] == "A0"
    assert entry["issuer"] is None and entry["signature"] is None
    assert log.verify_chain() is True


def test_chain_links_and_contiguous_seq():
    log = _populated(5)
    entries = log.entries()
    assert [e["seq"] for e in entries] == [0, 1, 2, 3, 4]
    for prev, cur in zip(entries, entries[1:]):
        assert cur["prev_hash"] == prev["hash"]
    assert entries[0]["prev_hash"] == GENESIS_PREV_HASH
    assert log.verify_chain() is True


def test_hash_formula_matches_registry_scheme():
    log = AuditLog()
    e = log.append(_decision_event())
    body = {"seq": e["seq"], "prev_hash": e["prev_hash"], "event": e["event"]}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    expected = hashlib.sha256((e["prev_hash"] + canonical).encode("utf-8")).hexdigest()
    assert e["hash"] == expected


# -- tamper evidence -----------------------------------------------------------

def test_single_field_tamper_breaks_chain():
    log = _populated(4)
    assert log.verify_chain() is True
    # Reach into the live stored entry and mutate one event field.
    log._log[1]["event"]["used"] = 99
    assert log.verify_chain() is False


def test_tamper_seq_breaks_chain():
    log = _populated(3)
    log._log[2]["seq"] = 5
    assert log.verify_chain() is False


def test_tamper_prev_hash_breaks_chain():
    log = _populated(3)
    log._log[2]["prev_hash"] = "0" * 64
    assert log.verify_chain() is False


def test_tamper_recomputing_own_hash_still_breaks_via_prev_link():
    """A tamperer who recomputes the mutated entry's own hash still desyncs the
    next entry's prev_hash, so the chain is still detected as broken."""
    log = _populated(3)
    e1 = log._log[1]
    e1["event"]["used"] = 42
    body = {"seq": e1["seq"], "prev_hash": e1["prev_hash"], "event": e1["event"]}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    e1["hash"] = hashlib.sha256((e1["prev_hash"] + canonical).encode("utf-8")).hexdigest()
    # e1 self-consistent, but log[2].prev_hash no longer matches e1.hash.
    assert log.verify_chain() is False


def test_reorder_breaks_chain():
    log = _populated(4)
    log._log[1], log._log[2] = log._log[2], log._log[1]
    assert log.verify_chain() is False


def test_drop_entry_breaks_chain():
    log = _populated(4)
    del log._log[2]  # seq now 0,1,3,4 -> contiguity fails
    assert log.verify_chain() is False


def test_entries_returns_copies_not_live_objects():
    log = _populated(2)
    snap = log.entries()
    snap[0]["event"]["used"] = 12345
    snap.append({"bogus": True})
    # Neither the mutation nor the append touched the log.
    assert log.entries()[0]["event"]["used"] != 12345
    assert len(log) == 2
    assert log.verify_chain() is True


def test_entries_filter_predicate():
    log = AuditLog()
    log.append(_decision_event(tls="A0", used=0))
    log.append(_decision_event(tls="A1", used=2))
    log.append(_decision_event(tls="A2", used=2))
    twos = log.entries(filter=lambda e: e["event"]["used"] == 2)
    assert [e["event"]["tls"] for e in twos] == ["A1", "A2"]


# -- Merkle anchoring ----------------------------------------------------------

def test_merkle_root_deterministic():
    log = _populated(8)
    assert log.merkle_root() == log.merkle_root()
    assert log.merkle_root(0, 8) == log.merkle_root(0, 8)


def test_merkle_root_single_entry_is_that_entry_hash():
    log = _populated(1)
    assert log.merkle_root(0, 1) == log._log[0]["hash"]


def test_merkle_root_changes_when_an_entry_changes():
    log_a = _populated(4)
    root_a = log_a.merkle_root()
    log_b = _populated(4)
    log_b._log[2]["hash"] = "f" * 64  # simulate a different anchored hash
    assert log_b.merkle_root() != root_a


def test_inclusion_proof_verifies_for_every_entry_odd_batch():
    # Odd batch exercises the lone-node promotion path.
    log = _populated(7)
    root = log.merkle_root(0, 7)
    for i in range(7):
        branch = log.inclusion_proof(i, 0, 7)
        assert verify_inclusion(log._log[i]["hash"], branch, root) is True


def test_inclusion_proof_verifies_subrange():
    log = _populated(10)
    root = log.merkle_root(2, 8)
    for i in range(2, 8):
        branch = log.inclusion_proof(i, 2, 8)
        assert verify_inclusion(log._log[i]["hash"], branch, root) is True


def test_forged_entry_proof_fails():
    log = _populated(8)
    root = log.merkle_root(0, 8)
    branch = log.inclusion_proof(3, 0, 8)
    forged_hash = hashlib.sha256(b"not in the batch").hexdigest()
    assert verify_inclusion(forged_hash, branch, root) is False


def test_tampered_branch_fails():
    log = _populated(8)
    root = log.merkle_root(0, 8)
    branch = log.inclusion_proof(3, 0, 8)
    branch[0]["hash"] = "a" * 64
    assert verify_inclusion(log._log[3]["hash"], branch, root) is False


def test_flipped_branch_position_fails():
    log = _populated(8)
    root = log.merkle_root(0, 8)
    branch = log.inclusion_proof(3, 0, 8)
    branch[0]["position"] = "left" if branch[0]["position"] == "right" else "right"
    assert verify_inclusion(log._log[3]["hash"], branch, root) is False


def test_wrong_root_fails():
    log = _populated(8)
    branch = log.inclusion_proof(3, 0, 8)
    assert verify_inclusion(log._log[3]["hash"], branch, "0" * 64) is False


def test_verify_inclusion_rejects_garbage_branch():
    log = _populated(4)
    root = log.merkle_root(0, 4)
    h = log._log[0]["hash"]
    assert verify_inclusion(h, [{"hash": 123, "position": "right"}], root) is False
    assert verify_inclusion(h, [{"hash": "a" * 64, "position": "x"}], root) is False
    assert verify_inclusion(h, ["not-a-dict"], root) is False
    assert verify_inclusion(None, [], root) is False


def test_merkle_root_empty_range_raises():
    log = _populated(3)
    with pytest.raises(ValueError):
        log.merkle_root(2, 2)
    empty = AuditLog()
    with pytest.raises(ValueError):
        empty.merkle_root()


def test_inclusion_proof_index_out_of_range_raises():
    log = _populated(4)
    with pytest.raises(IndexError):
        log.inclusion_proof(4, 0, 4)
    with pytest.raises(IndexError):
        log.inclusion_proof(0, 2, 4)  # index 0 outside [2,4)


# -- signatures ----------------------------------------------------------------

def test_signed_entries_verify():
    ident = JunctionIdentity("A0")
    log = AuditLog()
    for i in range(3):
        log.append(_decision_event(used=i), issuer=ident)
    pubs = {"A0": ident.public_key}
    assert log.verify_signatures(pubs) is True
    # Every entry recorded its issuer + a hex signature.
    for e in log.entries():
        assert e["issuer"] == "A0"
        assert isinstance(e["signature"], str) and len(e["signature"]) == 128


def test_swapped_signature_fails():
    a = JunctionIdentity("A0")
    log = AuditLog()
    log.append(_decision_event(used=0), issuer=a)
    log.append(_decision_event(used=1), issuer=a)
    # Swap the two entries' signatures: each entry now carries a valid signature
    # of the OTHER entry's hash -> verification must fail.
    log._log[0]["signature"], log._log[1]["signature"] = (
        log._log[1]["signature"], log._log[0]["signature"],
    )
    assert log.verify_signatures({"A0": a.public_key}) is False


def test_signature_from_wrong_key_fails():
    a = JunctionIdentity("A0")
    b = JunctionIdentity("A0")  # same id, different keypair
    log = AuditLog()
    log.append(_decision_event(), issuer=a)
    # Verify with B's public key under A's issuer id -> wrong key -> False.
    assert log.verify_signatures({"A0": b.public_key}) is False


def test_unknown_issuer_key_fails():
    a = JunctionIdentity("A0")
    log = AuditLog()
    log.append(_decision_event(), issuer=a)
    assert log.verify_signatures({"B9": a.public_key}) is False


def test_tampered_event_invalidates_signature_via_hash():
    a = JunctionIdentity("A0")
    log = AuditLog()
    log.append(_decision_event(used=0), issuer=a)
    # Tamper the event AND repair the chain hash so verify_chain might pass; the
    # signature was over the ORIGINAL hash, so signature check still fails.
    e = log._log[0]
    e["event"]["used"] = 99
    body = {"seq": e["seq"], "prev_hash": e["prev_hash"], "event": e["event"]}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    e["hash"] = hashlib.sha256((e["prev_hash"] + canonical).encode("utf-8")).hexdigest()
    assert log.verify_chain() is True  # chain repaired
    assert log.verify_signatures({"A0": a.public_key}) is False  # sig still wrong


def test_unsigned_entries_skip_signature_check():
    log = _populated(3)  # no issuer
    assert log.verify_signatures({}) is True


def test_malformed_signature_hex_fails():
    a = JunctionIdentity("A0")
    log = AuditLog()
    log.append(_decision_event(), issuer=a)
    log._log[0]["signature"] = "zz-not-hex"
    assert log.verify_signatures({"A0": a.public_key}) is False


def test_mixed_signed_and_unsigned():
    a = JunctionIdentity("A0")
    log = AuditLog()
    log.append(_decision_event(used=0), issuer=a)
    log.append(_decision_event(used=1))  # unsigned
    log.append(_decision_event(used=2), issuer=a)
    assert log.verify_chain() is True
    assert log.verify_signatures({"A0": a.public_key}) is True


# -- persistence (JSONL) -------------------------------------------------------

def test_jsonl_roundtrip_preserves_and_reverifies():
    log = _populated(6)
    text = log.to_jsonl()
    loaded = AuditLog.from_jsonl(text)
    assert loaded.entries() == log.entries()
    assert loaded.verify_chain() is True
    assert loaded.merkle_root(0, 6) == log.merkle_root(0, 6)


def test_jsonl_roundtrip_preserves_signatures():
    a = JunctionIdentity("A0")
    log = AuditLog()
    for i in range(4):
        log.append(_decision_event(used=i), issuer=a)
    loaded = AuditLog.from_jsonl(log.to_jsonl())
    assert loaded.verify_signatures({"A0": a.public_key}) is True


def test_jsonl_empty_log_roundtrips():
    log = AuditLog()
    assert log.to_jsonl() == ""
    loaded = AuditLog.from_jsonl("")
    assert len(loaded) == 0 and loaded.verify_chain() is True


def test_jsonl_trailing_newlines_ignored():
    log = _populated(2)
    loaded = AuditLog.from_jsonl(log.to_jsonl() + "\n\n  \n")
    assert loaded.entries() == log.entries()


def test_jsonl_load_rejects_tampered_event():
    log = _populated(3)
    lines = log.to_jsonl().splitlines()
    entry = json.loads(lines[1])
    entry["event"]["used"] = 777  # tamper one field, leave hash stale
    lines[1] = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    tampered = "\n".join(lines)
    with pytest.raises(ValueError):
        AuditLog.from_jsonl(tampered)
    # But forensic load with verify=False is allowed and shows it broken.
    forensic = AuditLog.from_jsonl(tampered, verify=False)
    assert forensic.verify_chain() is False


def test_jsonl_load_rejects_reordered_lines():
    log = _populated(3)
    lines = log.to_jsonl().splitlines()
    lines[0], lines[1] = lines[1], lines[0]
    with pytest.raises(ValueError):
        AuditLog.from_jsonl("\n".join(lines))


def test_jsonl_load_rejects_bad_json():
    with pytest.raises(ValueError):
        AuditLog.from_jsonl("{not valid json")


def test_jsonl_load_rejects_unexpected_keys():
    log = _populated(1)
    entry = json.loads(log.to_jsonl())
    entry["extra"] = "surprise"
    with pytest.raises(ValueError):
        AuditLog.from_jsonl(json.dumps(entry))


def test_jsonl_load_rejects_non_object_line():
    with pytest.raises(ValueError):
        AuditLog.from_jsonl("[1, 2, 3]")


def test_from_jsonl_rejects_non_str():
    with pytest.raises(TypeError):
        AuditLog.from_jsonl(b"bytes")


# -- boundary / garbage input --------------------------------------------------

def test_append_rejects_non_dict():
    log = AuditLog()
    for bad in ["str", 123, None, [1, 2], (1,), object()]:
        with pytest.raises(TypeError):
            log.append(bad)


def test_append_rejects_reserved_keys():
    log = AuditLog()
    for key in ("seq", "prev_hash", "hash", "event", "issuer", "signature"):
        with pytest.raises(ValueError):
            log.append({key: "x"})


def test_append_rejects_non_serialisable_event():
    log = AuditLog()
    with pytest.raises(ValueError):
        log.append({"obj": object()})
    with pytest.raises(ValueError):
        log.append({"bad_float": float("nan")})
    with pytest.raises(ValueError):
        log.append({"inf": float("inf")})


def test_append_rejects_non_str_keys():
    log = AuditLog()
    with pytest.raises(TypeError):
        log.append({1: "numeric key"})


def test_append_does_not_mutate_caller_event_and_is_isolated():
    log = AuditLog()
    event = _decision_event()
    original = copy.deepcopy(event)
    log.append(event)
    # Mutating the caller's dict after append must not change the stored entry.
    event["used"] = 999
    event["halting"].append(42)
    assert log.entries()[0]["event"] == original
    assert log.verify_chain() is True


def test_huge_event_rejected():
    log = AuditLog()
    huge = {"blob": "x" * (5 * 1024 * 1024)}  # > _MAX_EVENT_BYTES
    with pytest.raises(ValueError):
        log.append(huge)


def test_large_log_chain_and_merkle_scale():
    """A large log (anchoring use-case) still verifies and proves inclusion."""
    log = AuditLog()
    n = 2000
    for i in range(n):
        log.append({"i": i, "used": i % 3})
    assert log.verify_chain() is True
    root = log.merkle_root(0, n)
    # Spot-check inclusion at boundaries and an interior point.
    for idx in (0, 1, 999, n - 1):
        branch = log.inclusion_proof(idx, 0, n)
        assert verify_inclusion(log._log[idx]["hash"], branch, root) is True
    # A forged hash must not prove in.
    assert verify_inclusion("f" * 64, log.inclusion_proof(0, 0, n), root) is False


def test_merkle_root_rejects_bad_range_types():
    log = _populated(4)
    with pytest.raises(TypeError):
        log.merkle_root(True, 3)
    with pytest.raises(TypeError):
        log.merkle_root(0, "3")


def test_entries_rejects_non_callable_filter():
    log = _populated(2)
    with pytest.raises(TypeError):
        log.entries(filter=123)
