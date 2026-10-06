"""Permissioned agent registry with a tamper-evident (hash-chained) audit log.

Local stand-in for the future on-chain Hyperledger Besu registry described in
MASTER-SPEC.md. The interface is deliberately
**ledger-agnostic**: callers see register / revoke / is_approved / public_key and
an append-only `audit_log`; whether that log lives in memory (here) or on Besu
later is an implementation detail behind this class.

Trust model (MASTER-SPEC.md §6): this records *who is currently approved* and gives a
non-repudiable, tamper-evident history of every registration/revocation. It does
NOT vouch for the honesty of an approved agent — only its membership.

Public keys are stored and returned as **DER bytes** (the canonical Ed25519
encoding used everywhere in this project; raw 32-byte import is unsupported in
the pycryptodome build we use). The registry never parses them — it treats the
key as opaque bytes and only fingerprints them (sha256) for the audit log.

Hash chain
----------
Each audit event carries `prev_hash` (the previous event's `hash`, or 64 zeros
for genesis) and `hash`, where::

    hash = sha256(prev_hash_hex + canonical_json(event_without_hash)).hexdigest()

with `canonical_json = json.dumps(..., sort_keys=True, separators=(",", ":"))`.
`verify_chain()` recomputes the whole chain; any mutation of a logged field (or
reordering) breaks it.
"""
from __future__ import annotations

import hashlib
import json

GENESIS_PREV_HASH = "0" * 64


def _canonical_json(event: dict) -> str:
    """Deterministic JSON for hashing: sorted keys, no whitespace."""
    return json.dumps(event, sort_keys=True, separators=(",", ":"))


def _hash_event(prev_hash: str, event_without_hash: dict) -> str:
    """sha256 over prev_hash_hex concatenated with the canonical event JSON."""
    payload = prev_hash + _canonical_json(event_without_hash)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Registry:
    """Allowlist of approved agent identities + hash-chained audit log.

    State is kept immutable: `register`/`revoke` rebuild the approval map and
    append a new event rather than mutating existing structures, so the audit
    log entries handed out by the `audit_log` property are never edited in place
    by this class (only an external tamperer would mutate them — which is exactly
    what `verify_chain` is designed to catch).
    """

    def __init__(self) -> None:
        # junction_id -> DER public-key bytes for *currently approved* agents.
        self._approved: dict[str, bytes] = {}
        # set of junction_ids ever registered (so revoke-before-register can
        # raise KeyError while re-registration after revoke is still allowed).
        self._known: frozenset[str] = frozenset()
        # append-only list of audit events.
        self._log: list[dict] = []

    # -- mutating operations -------------------------------------------------

    def register(self, junction_id: str, public_key: bytes) -> None:
        """Approve `junction_id` with `public_key` (DER bytes); append an event.

        Re-registration after revocation is permitted and may carry a new key.
        """
        if not isinstance(junction_id, str) or not junction_id:
            raise ValueError("junction_id must be a non-empty string")
        if not isinstance(public_key, (bytes, bytearray)):
            raise TypeError("public_key must be bytes (canonical DER encoding)")
        public_key = bytes(public_key)

        self._approved = {**self._approved, junction_id: public_key}
        self._known = self._known | {junction_id}
        self._append_event("register", junction_id, public_key)

    def revoke(self, junction_id: str) -> None:
        """Revoke `junction_id`; append an event.

        Raises KeyError if the junction was never registered. Revoking an
        already-revoked (but previously registered) junction is idempotent at
        the approval level but still records an event for the audit trail.
        """
        if not isinstance(junction_id, str) or not junction_id:
            raise ValueError("junction_id must be a non-empty string")
        if junction_id not in self._known:
            raise KeyError(junction_id)

        if junction_id in self._approved:
            self._approved = {
                jid: key
                for jid, key in self._approved.items()
                if jid != junction_id
            }
        self._append_event("revoke", junction_id, None)

    # -- queries -------------------------------------------------------------

    def is_approved(self, junction_id: str) -> bool:
        """True iff `junction_id` is registered AND not currently revoked."""
        return junction_id in self._approved

    def public_key(self, junction_id: str) -> bytes | None:
        """Current approved DER public key for `junction_id`, else None."""
        return self._approved.get(junction_id)

    @property
    def audit_log(self) -> list[dict]:
        """Append-only audit log.

        Returns a shallow copy of the list (callers cannot append/reorder the
        registry's own list), but the event dicts themselves are the live
        objects — the TAMPER test reaches into one of these and mutates a field
        to prove `verify_chain` catches it.
        """
        return list(self._log)

    # -- integrity -----------------------------------------------------------

    def verify_chain(self) -> bool:
        """Recompute the sha256 hash-chain; False if any event was tampered."""
        prev_hash = GENESIS_PREV_HASH
        for expected_seq, event in enumerate(self._log):
            # seq must be contiguous from 0 and prev_hash must link the chain.
            if event.get("seq") != expected_seq:
                return False
            if event.get("prev_hash") != prev_hash:
                return False

            stored_hash = event.get("hash")
            event_without_hash = {k: v for k, v in event.items() if k != "hash"}
            recomputed = _hash_event(prev_hash, event_without_hash)
            if stored_hash != recomputed:
                return False

            prev_hash = stored_hash
        return True

    # -- internals -----------------------------------------------------------

    def _append_event(
        self, action: str, junction_id: str, public_key: bytes | None
    ) -> None:
        seq = len(self._log)
        prev_hash = self._log[-1]["hash"] if self._log else GENESIS_PREV_HASH
        pubkey_sha256 = (
            hashlib.sha256(public_key).hexdigest()
            if public_key is not None
            else None
        )
        event_without_hash = {
            "seq": seq,
            "action": action,
            "junction_id": junction_id,
            "pubkey_sha256": pubkey_sha256,
            "prev_hash": prev_hash,
        }
        event = {
            **event_without_hash,
            "hash": _hash_event(prev_hash, event_without_hash),
        }
        self._log.append(event)
