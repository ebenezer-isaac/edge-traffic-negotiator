"""Tests for src/registry.py — allowlist + tamper-evident audit log.

Run from the edge-negotiator dir:
    .venv/Scripts/python -m pytest tests/test_registry.py -v
"""
import hashlib
import json
import os
import sys

import pytest

# Put src/ on sys.path so `import registry` works without packaging.
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from registry import GENESIS_PREV_HASH, Registry  # noqa: E402

from Crypto.PublicKey import ECC  # noqa: E402


def _der_pubkey() -> bytes:
    """A fresh canonical 44-byte DER Ed25519 public key (project encoding)."""
    return ECC.generate(curve="ed25519").public_key().export_key(format="DER")


# -- happy path ----------------------------------------------------------------

def test_register_then_approved_and_pubkey_roundtrips():
    reg = Registry()
    pk = _der_pubkey()
    reg.register("A0", pk)
    assert reg.is_approved("A0") is True
    assert reg.public_key("A0") == pk


def test_unknown_id_not_approved_and_pubkey_none():
    reg = Registry()
    assert reg.is_approved("ghost") is False
    assert reg.public_key("ghost") is None


# -- revocation ----------------------------------------------------------------

def test_revoke_makes_unapproved_and_pubkey_none():
    reg = Registry()
    reg.register("A1", _der_pubkey())
    reg.revoke("A1")
    assert reg.is_approved("A1") is False
    assert reg.public_key("A1") is None


def test_revoke_before_register_raises_keyerror():
    reg = Registry()
    with pytest.raises(KeyError):
        reg.revoke("never-seen")


def test_re_register_after_revoke_approves_with_new_key():
    reg = Registry()
    pk1 = _der_pubkey()
    pk2 = _der_pubkey()
    assert pk1 != pk2
    reg.register("B0", pk1)
    reg.revoke("B0")
    assert reg.is_approved("B0") is False
    reg.register("B0", pk2)
    assert reg.is_approved("B0") is True
    assert reg.public_key("B0") == pk2


# -- audit log structure -------------------------------------------------------

def test_audit_log_grows_one_per_action_with_incrementing_seq():
    reg = Registry()
    assert reg.audit_log == []
    reg.register("A0", _der_pubkey())
    reg.register("A1", _der_pubkey())
    reg.revoke("A0")
    log = reg.audit_log
    assert len(log) == 3
    assert [e["seq"] for e in log] == [0, 1, 2]
    assert [e["action"] for e in log] == ["register", "register", "revoke"]
    assert log[0]["prev_hash"] == GENESIS_PREV_HASH
    # revoke event records no pubkey fingerprint
    assert log[2]["pubkey_sha256"] is None
    # register event fingerprints the key
    assert log[0]["pubkey_sha256"] is not None
    assert reg.verify_chain() is True


def test_pubkey_sha256_matches_registered_key():
    reg = Registry()
    pk = _der_pubkey()
    reg.register("A0", pk)
    assert reg.audit_log[0]["pubkey_sha256"] == hashlib.sha256(pk).hexdigest()


def test_event_has_exact_schema_keys():
    reg = Registry()
    reg.register("A0", _der_pubkey())
    event = reg.audit_log[0]
    assert set(event) == {
        "seq", "action", "junction_id", "pubkey_sha256", "prev_hash", "hash",
    }


def test_hash_formula_matches_spec():
    reg = Registry()
    pk = _der_pubkey()
    reg.register("A0", pk)
    e = reg.audit_log[0]
    without_hash = {k: v for k, v in e.items() if k != "hash"}
    canonical = json.dumps(without_hash, sort_keys=True, separators=(",", ":"))
    expected = hashlib.sha256(
        (e["prev_hash"] + canonical).encode("utf-8")
    ).hexdigest()
    assert e["hash"] == expected


def test_prev_hash_links_consecutive_events():
    reg = Registry()
    reg.register("A0", _der_pubkey())
    reg.register("A1", _der_pubkey())
    log = reg.audit_log
    assert log[1]["prev_hash"] == log[0]["hash"]


# -- tamper evidence -----------------------------------------------------------

def test_tamper_junction_id_breaks_chain():
    reg = Registry()
    reg.register("A0", _der_pubkey())
    reg.register("A1", _der_pubkey())
    assert reg.verify_chain() is True
    # reach into the logged event list and mutate a field
    reg.audit_log[0]["junction_id"] = "ATTACKER"
    assert reg.verify_chain() is False


def test_tamper_action_breaks_chain():
    reg = Registry()
    reg.register("A0", _der_pubkey())
    reg.revoke("A0")
    assert reg.verify_chain() is True
    reg.audit_log[1]["action"] = "register"
    assert reg.verify_chain() is False


def test_tamper_pubkey_fingerprint_breaks_chain():
    reg = Registry()
    reg.register("A0", _der_pubkey())
    reg.audit_log[0]["pubkey_sha256"] = "0" * 64
    assert reg.verify_chain() is False


def test_tamper_recomputing_hash_still_breaks_chain_via_prev_link():
    """A tamperer who recomputes the mutated event's own hash still desyncs the
    next event's prev_hash, so the chain is still detected as broken."""
    reg = Registry()
    reg.register("A0", _der_pubkey())
    reg.register("A1", _der_pubkey())
    log = reg.audit_log
    e0 = log[0]
    e0["junction_id"] = "ATTACKER"
    without_hash = {k: v for k, v in e0.items() if k != "hash"}
    canonical = json.dumps(without_hash, sort_keys=True, separators=(",", ":"))
    e0["hash"] = hashlib.sha256(
        (e0["prev_hash"] + canonical).encode("utf-8")
    ).hexdigest()
    # e0 now self-consistent, but log[1].prev_hash no longer matches e0.hash
    assert reg.verify_chain() is False


def test_tamper_reorder_breaks_chain():
    reg = Registry()
    reg.register("A0", _der_pubkey())
    reg.register("A1", _der_pubkey())
    # swap the two events in the underlying list
    reg._log[0], reg._log[1] = reg._log[1], reg._log[0]
    assert reg.verify_chain() is False


def test_audit_log_property_returns_copy_of_list():
    reg = Registry()
    reg.register("A0", _der_pubkey())
    snapshot = reg.audit_log
    snapshot.append({"bogus": True})
    # appending to the returned list must not grow the registry's own log
    assert len(reg.audit_log) == 1


# -- input validation ----------------------------------------------------------

def test_register_rejects_non_bytes_key():
    reg = Registry()
    with pytest.raises(TypeError):
        reg.register("A0", "not-bytes")


def test_register_rejects_empty_junction_id():
    reg = Registry()
    with pytest.raises(ValueError):
        reg.register("", _der_pubkey())
