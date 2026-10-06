"""Builders + appenders for the §11 producer records (message / sighting / decision).

Split out of the controllers (which are at the file-size ceiling) so the record
SHAPES live in one place and both producers -- ``CoordinatedController`` and
``EmergencyController`` -- emit byte-identical schemas. These are the records the
forensic reader (``assessment``, the §6.3 origin classifier) consumes; every key
here matches MASTER-SPEC §11 exactly, with two forced renames noted below.

Schemas (MASTER-SPEC §11)
-------------------------
message  : {kind, sender, sender_pubkey_fpr, sender_pubkey_der, signed_payload,
            sender_signature}  -- appended at EACH consumption of a verified bus
           message. The §11 ``seq`` is the AuditLog ENVELOPE seq (returned by
           ``append``), never an event field (``seq`` is a reserved envelope key).
sighting : {kind, sighter_key, ev_id, approach, t, position}  -- the KEYLESS
           local-reading encoding ONLY (``sighter_key`` null; the §11 ``signature``
           is the AuditLog envelope signature, also null because it is appended
           with ``issuer=None``). Both null is the distinct keyless encoding (§6.4
           sensor-fed-spoof surface), NOT a missing-metadata cell.

           SIGNED (key-attributed) sightings are NOT emitted as ``kind:"sighting"``
           (SSOT reconciliation, MASTER-SPEC §11/§6.6): a junction does not hold a
           neighbour's key, so a fresh signed ``kind:"sighting"`` would be a
           FABRICATION. A signed sighting received over the EV bus is carried as a
           ``kind:"message"`` record with ``payload.sighting`` + the authentic WIRE
           signature; the §6.6 recompute + §6.3 origin-classifier read signed
           sightings from ``kind:"message"`` (by ``payload.sighting.ev_id`` +
           ``sender``) and keyless sightings from ``kind:"sighting"``.
decision : {kind, driving_input_seqs, junction, t, executed, classification,
            policies_applied}.

Two spec keys are renamed to dodge AuditLog's reserved envelope keys
(``{"seq","prev_hash","hash","event","issuer","signature"}``): the message
signature is ``sender_signature`` (as §6.2 already writes it), and the sighting
``signature`` is carried by the ENVELOPE signature (issuer layer) rather than an
event field named ``signature`` -- append would reject the latter. ``sender_pubkey_der``
is stored hex-encoded because the log round-trips through canonical JSON (raw
bytes are not JSON-serialisable); the reader does ``bytes.fromhex`` to verify.
"""
from __future__ import annotations

import hashlib

# §6.2 PINNED per-decision policy vocab {corroboration, conservation_band,
# replay, membership}. The EV path always applies corroboration; the
# coordination path always applies membership + replay, plus conservation_band
# iff a conservation check actually ran this decision. Never empty, never a lie.
EV_POLICIES = ("corroboration",)


def coordination_policies(conservation_ran: bool) -> list[str]:
    """Coordination-decision ``policies_applied`` (§6.2 pinned mapping)."""
    base = ["membership", "replay"]
    return [*base, "conservation_band"] if conservation_ran else base


def _fingerprint(der: bytes | None) -> str | None:
    return hashlib.sha256(der).hexdigest() if der else None


def build_message_record(m, registry) -> dict:
    """A §11 ``message`` record for a verified bus message ``m``.

    ``sender_pubkey_der`` / ``sender_pubkey_fpr`` are pulled from the registry AT
    CONSUMPTION (per §6.1), not from the message. The DER key is hex-encoded for
    JSON; ``sender_signature`` is ``m.signature.hex()``. ``signed_payload`` stores
    the EXACT bytes the signature covers -- ``canonical_bytes(sender, t, payload)``
    -- as its structured (sender, t, payload) triple, ``t`` the LOGICAL tick.
    """
    der = registry.public_key(m.sender)
    return {
        "kind": "message",
        "sender": m.sender,
        "sender_pubkey_fpr": _fingerprint(der),
        "sender_pubkey_der": der.hex() if der else None,
        "signed_payload": {"sender": m.sender, "t": m.t, "payload": m.payload},
        "sender_signature": m.signature.hex(),
    }


def build_sighting_record(ev_id, approach, t, position=None) -> dict:
    """A §11 ``sighting`` record -- the KEYLESS local-reading encoding ONLY, so
    ``sighter_key`` is always null (and the §11 ``signature`` rides the envelope,
    null via ``issuer=None``). SIGNED sightings are NOT re-encoded here -- a
    junction cannot re-sign a neighbour's sighting, so a signed ``kind:"sighting"``
    would be a FABRICATION; a signed sighting's authentic proof is the wire
    signature already captured in its ``kind:"message"`` record (``payload.sighting``).
    ``position`` is null as emitted (the local detector returns only (ev_id, edge))."""
    return {
        "kind": "sighting",
        "sighter_key": None,
        "ev_id": ev_id,
        "approach": approach,
        "t": t,
        "position": position,
    }


def build_decision_record(driving_pairs, junction, t, executed, classification,
                          policies_applied) -> dict:
    """A §11 ``decision`` record. ``driving_input_seqs`` is the FULL set of ALL
    signed inputs consumed this decision (no materiality filter); each pair is
    ``[envelope_seq, sighter_key]`` with ``sighter_key`` null for a keyless input.
    ``classification`` is a RUNTIME label DISTINCT from ORIGIN -- assessment.py
    MUST NOT read it for origin (§6.2)."""
    return {
        "kind": "decision",
        "driving_input_seqs": [list(p) for p in driving_pairs],
        "junction": junction,
        "t": t,
        "executed": executed,
        "classification": classification,
        "policies_applied": list(policies_applied),
    }


def log_messages(audit_log, registry, identities, recipient, msgs) -> list:
    """Append a ``message`` record per consumed verified message; return the
    ``[seq, sender]`` driving-input pairs. No-op ([]) when auditing is off."""
    if audit_log is None:
        return []
    issuer = identities.get(recipient)
    pairs: list = []
    for m in msgs:
        entry = audit_log.append(build_message_record(m, registry), issuer=issuer)
        pairs = [*pairs, [entry["seq"], m.sender]]
    return pairs


def log_sighting(audit_log, ev_id, approach, t, position=None):
    """Append a KEYLESS local ``sighting`` record (issuer=None); return its seq."""
    if audit_log is None:
        return None
    entry = audit_log.append(
        build_sighting_record(ev_id, approach, t, position), issuer=None)
    return entry["seq"]


def log_decision(audit_log, identities, junction, driving_pairs, t, executed,
                 classification, policies_applied):
    """Append a ``decision`` record signed by ``junction`` (issuer layer); return
    its seq. No-op (None) when auditing is off."""
    if audit_log is None:
        return None
    entry = audit_log.append(
        build_decision_record(driving_pairs, junction, t, executed,
                               classification, policies_applied),
        issuer=identities.get(junction))
    return entry["seq"]
