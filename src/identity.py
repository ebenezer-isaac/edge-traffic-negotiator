"""Per-junction cryptographic identity for The Edge Negotiator.

Every signalised junction in the corridor runs an SLM agent that exchanges
predicted traffic state with its neighbours over the fast message bus. Those
neighbour messages must be *authenticated*: a receiving junction has to know
the report genuinely came from a currently-approved peer and was not forged,
replayed-with-edits, or corrupted in transit.

This module gives each junction an Ed25519 keypair (`JunctionIdentity`). The
junction signs every outbound payload with its private key; a peer verifies the
signature against the sender's public key. The canonical wire/registry encoding
of a public key is its 44-byte DER (SubjectPublicKeyInfo) form -- these DER
public keys are exactly what later gets written into the on-chain Hyperledger
Besu allowlist of approved agents (and removed by `revoke()`), so identity here
and registry membership on-chain speak the same bytes.

The private key never leaves the identity object: there is no public accessor,
only `sign()`. `verify()` is a module-level, side-effect-free function that
returns a plain bool and -- per the security/testing rules -- never raises on a
bad signature or on malformed/garbage input; it returns False instead so that
an attacker-supplied blob can never crash a receiver.

Crypto: Ed25519 via pycryptodome (`Crypto.PublicKey.ECC` +
`Crypto.Signature.eddsa`, RFC 8032 mode). Public keys are always handled as DER
bytes -- raw 32-byte import is not supported in this pycryptodome build.
"""

from __future__ import annotations

from Crypto.PublicKey import ECC
from Crypto.Signature import eddsa

# Canonical sizes for the chosen encodings. Used for cheap, explicit
# boundary validation before handing bytes to the crypto layer.
_DER_PUBLIC_KEY_LEN = 44   # Ed25519 SubjectPublicKeyInfo DER
_SIGNATURE_LEN = 64        # Ed25519 signature (RFC 8032)


class JunctionIdentity:
    """A single junction's signing identity (fresh Ed25519 keypair).

    Construct one per junction. Keep the instance private to that junction:
    its private key is held internally and only ever exercised through
    `sign()`. Publish only `public_key` (DER) -- that is what neighbours and
    the on-chain allowlist need to verify this junction's messages.
    """

    __slots__ = ("_junction_id", "_key", "_public_key_der")

    def __init__(self, junction_id: str) -> None:
        if not isinstance(junction_id, str):
            raise TypeError(
                f"junction_id must be str, got {type(junction_id).__name__}"
            )
        if junction_id == "":
            raise ValueError("junction_id must be a non-empty string")

        # Fresh keypair per identity -- two identities never share keys.
        key = ECC.generate(curve="ed25519")

        # Precompute the canonical DER public key once. export_key returns a
        # new bytes object; we store it and hand back copies via the property
        # so callers can never mutate our cached encoding.
        public_key_der = key.public_key().export_key(format="DER")

        self._junction_id = junction_id
        self._key = key
        self._public_key_der = bytes(public_key_der)

    @property
    def junction_id(self) -> str:
        """The junction's identifier (e.g. ``"A0"``)."""
        return self._junction_id

    @property
    def public_key(self) -> bytes:
        """Canonical 44-byte DER-encoded Ed25519 public key.

        Returns a fresh copy each access so the internal cache stays immutable.
        """
        return bytes(self._public_key_der)

    def sign(self, payload: bytes) -> bytes:
        """Return the 64-byte Ed25519 signature over ``payload``.

        ``payload`` must be raw bytes (the exact bytes a verifier will check).
        """
        if not isinstance(payload, (bytes, bytearray)):
            raise TypeError(
                f"payload must be bytes, got {type(payload).__name__}"
            )
        signer = eddsa.new(self._key, "rfc8032")
        return signer.sign(bytes(payload))


def verify(public_key: bytes, payload: bytes, signature: bytes) -> bool:
    """Verify ``signature`` over ``payload`` for the DER ``public_key``.

    Returns True iff the signature is a valid Ed25519 signature of ``payload``
    under the given canonical DER public key. Returns False for any failure --
    wrong key, tampered payload, tampered/short signature, or malformed/garbage
    public-key bytes. This function never raises on bad or hostile input:
    a receiver must be able to reject an attacker's blob, not crash on it.
    """
    # Boundary validation: reject anything that is not plausibly the right
    # shape before touching the crypto layer. Wrong types -> not verifiable.
    if not isinstance(public_key, (bytes, bytearray)):
        return False
    if not isinstance(payload, (bytes, bytearray)):
        return False
    if not isinstance(signature, (bytes, bytearray)):
        return False

    # An Ed25519 signature is exactly 64 bytes; anything else cannot match.
    if len(signature) != _SIGNATURE_LEN:
        return False
    # A canonical DER Ed25519 public key is exactly 44 bytes.
    if len(public_key) != _DER_PUBLIC_KEY_LEN:
        return False

    try:
        pub = ECC.import_key(bytes(public_key))
        verifier = eddsa.new(pub, "rfc8032")
        verifier.verify(bytes(payload), bytes(signature))
        return True
    except (ValueError, TypeError):
        # ValueError: signature mismatch / unparseable DER.
        # TypeError: unexpected internal type rejection.
        # Either way: not a valid signature -> False, never propagate.
        return False
    except Exception:
        # Defensive catch-all: a hostile blob must never escalate to a crash
        # in a receiver. Any other crypto-layer failure is treated as invalid.
        return False
