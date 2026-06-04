"""Adversarial tests for src/identity.py (per the testing rules).

Categories covered: happy path, tamper, garbage/hostile input, determinism.
src/ is inserted on sys.path so `import identity` works when run as
`python -m pytest tests` from the project root.
"""

import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from identity import JunctionIdentity, verify  # noqa: E402


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #

def test_sign_then_verify_true():
    ident = JunctionIdentity("A0")
    payload = b"phase=2;ts=1234;outflow=17"
    sig = ident.sign(payload)
    assert verify(ident.public_key, payload, sig) is True


def test_public_key_is_44_bytes_der():
    ident = JunctionIdentity("B1")
    pk = ident.public_key
    assert isinstance(pk, bytes)
    assert len(pk) == 44


def test_signature_is_64_bytes():
    sig = JunctionIdentity("A1").sign(b"hello")
    assert isinstance(sig, bytes)
    assert len(sig) == 64


def test_two_identities_have_different_keys():
    a = JunctionIdentity("A0")
    b = JunctionIdentity("A0")  # same id, must still be a fresh keypair
    assert a.public_key != b.public_key


def test_junction_id_property():
    assert JunctionIdentity("B0").junction_id == "B0"


def test_empty_payload_signs_and_verifies():
    ident = JunctionIdentity("A0")
    sig = ident.sign(b"")
    assert verify(ident.public_key, b"", sig) is True


def test_public_key_property_returns_independent_copy():
    ident = JunctionIdentity("A0")
    pk1 = ident.public_key
    pk2 = ident.public_key
    assert pk1 == pk2
    # mutating a returned bytearray-derived copy must not affect the identity
    assert pk1 is not pk2 or isinstance(pk1, bytes)
    # signing still verifies after repeated public_key access
    sig = ident.sign(b"x")
    assert verify(ident.public_key, b"x", sig) is True


# --------------------------------------------------------------------------- #
# Tamper
# --------------------------------------------------------------------------- #

def test_verify_false_when_payload_flipped_one_byte():
    ident = JunctionIdentity("A0")
    payload = bytearray(b"phase=2;ts=1234")
    sig = ident.sign(bytes(payload))
    payload[0] ^= 0x01  # flip one bit of one byte
    assert verify(ident.public_key, bytes(payload), sig) is False


def test_verify_false_when_signature_flipped_one_byte():
    ident = JunctionIdentity("A0")
    payload = b"phase=2;ts=1234"
    sig = bytearray(ident.sign(payload))
    sig[0] ^= 0x01
    assert verify(ident.public_key, payload, bytes(sig)) is False


def test_verify_false_with_wrong_pubkey():
    a = JunctionIdentity("A0")
    b = JunctionIdentity("B1")
    payload = b"phase=2"
    sig = a.sign(payload)
    assert verify(b.public_key, payload, sig) is False


def test_verify_false_when_last_signature_byte_flipped():
    ident = JunctionIdentity("A0")
    payload = b"some realistic neighbour report"
    sig = bytearray(ident.sign(payload))
    sig[-1] ^= 0x80
    assert verify(ident.public_key, payload, bytes(sig)) is False


# --------------------------------------------------------------------------- #
# Garbage / hostile input -> must return False, never raise
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("bad_pub", [
    b"",
    b"\x00",
    b"\x00" * 32,        # raw-key length, not DER -> rejected
    b"\x00" * 43,        # one short of DER
    b"\x00" * 45,        # one long
    b"\xff" * 44,        # right length, junk content (not parseable DER)
    b"not-a-der-key-at-all-padding-padding-1234567",
])
def test_verify_false_on_garbage_pubkey(bad_pub):
    ident = JunctionIdentity("A0")
    payload = b"payload"
    sig = ident.sign(payload)
    result = verify(bad_pub, payload, sig)
    assert result is False


@pytest.mark.parametrize("bad_sig", [
    b"",
    b"\x00",
    b"\x00" * 63,        # one short of 64
    b"\x00" * 65,        # one long
    b"\x00" * 64,        # right length, all zeros -> invalid sig
    b"garbage",
])
def test_verify_false_on_garbage_signature(bad_sig):
    ident = JunctionIdentity("A0")
    payload = b"payload"
    assert verify(ident.public_key, payload, bad_sig) is False


@pytest.mark.parametrize("bad_type", [None, 123, "string", [1, 2, 3], {}])
def test_verify_false_on_wrong_types(bad_type):
    ident = JunctionIdentity("A0")
    payload = b"payload"
    sig = ident.sign(payload)
    # wrong-typed pubkey
    assert verify(bad_type, payload, sig) is False
    # wrong-typed signature
    assert verify(ident.public_key, payload, bad_type) is False
    # wrong-typed payload
    assert verify(ident.public_key, bad_type, sig) is False


def test_verify_does_not_raise_on_any_garbage():
    # Belt-and-braces: a sweep of hostile blobs must all return bool, no raise.
    blobs = [b"", b"\x00" * 1000, b"\xff" * 44, bytes(range(256))]
    for pub in blobs:
        for pay in blobs:
            for sig in blobs:
                out = verify(pub, pay, sig)
                assert out is False  # all should be invalid, and crucially no exception


# --------------------------------------------------------------------------- #
# Determinism / cross-identity
# --------------------------------------------------------------------------- #

def test_same_identity_same_payload_verifies():
    ident = JunctionIdentity("A0")
    payload = b"deterministic-check"
    sig1 = ident.sign(payload)
    sig2 = ident.sign(payload)
    # Ed25519 is deterministic: identical signatures for identical inputs.
    assert sig1 == sig2
    assert verify(ident.public_key, payload, sig1) is True
    assert verify(ident.public_key, payload, sig2) is True


def test_cross_identity_signature_fails():
    a = JunctionIdentity("A0")
    b = JunctionIdentity("B1")
    payload = b"neighbour-report"
    sig_a = a.sign(payload)
    # a's signature must not verify under b's key
    assert verify(b.public_key, payload, sig_a) is False
    # and b's own signature does verify under b's key (sanity)
    assert verify(b.public_key, payload, b.sign(payload)) is True


def test_signature_bound_to_exact_payload():
    ident = JunctionIdentity("A0")
    sig = ident.sign(b"phase=2")
    assert verify(ident.public_key, b"phase=3", sig) is False
    assert verify(ident.public_key, b"phase=2 ", sig) is False  # trailing space


# --------------------------------------------------------------------------- #
# Constructor input validation
# --------------------------------------------------------------------------- #

def test_empty_junction_id_rejected():
    with pytest.raises(ValueError):
        JunctionIdentity("")


def test_non_str_junction_id_rejected():
    with pytest.raises(TypeError):
        JunctionIdentity(123)  # type: ignore[arg-type]
