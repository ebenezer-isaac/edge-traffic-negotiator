"""Append-only, tamper-evident DECISION + EVENT audit log for The Edge Negotiator.

This is the subsystem MASTER-SPEC.md (s.6) calls for: a
"tamper-evident audit log recording every decision and identity/registry
change", with an external ledger (Hyperledger Besu — ONE optional anchor
witness of the >=2-witness Certificate-Transparency-style quorum, §6.7) as an
**async anchor only**; the accountability mechanism is credited to CT prior art,
not claimed novel, and Besu is a demoted anchor OPTION, not the contribution.

It deliberately mirrors the hash-chain already used by ``src/registry.py``
(same canonical-JSON + sha256(prev_hash || canonical(event)) construction, same
contiguous ``seq``, same ``verify_chain`` semantics) so the two logs speak the
same bytes and an auditor reasons about one scheme, not two. The difference is
scope and scale: ``Registry`` chains a handful of membership events in place;
``AuditLog`` chains *every per-decision event* emitted by
``CoordinatedController`` (thousands per run) and adds three things the registry
does not need:

  1. **Optional issuer signatures.** Each entry's hash can be signed by a
     :class:`~identity.JunctionIdentity` (Ed25519). ``verify_signatures``
     re-checks every signed entry against its issuer's DER public key, so a
     swapped or forged signature is caught independently of the hash chain.

  2. **Merkle anchoring (the bridge to Besu).** The benchmark found a
     single Besu write costs ~2.1 s, so per-entry anchoring is infeasible. We
     instead fold a *batch* of entry hashes into one Merkle root
     (:meth:`merkle_root`); a single ~2.1 s write anchors the whole batch.
     :meth:`inclusion_proof` produces the Merkle branch for one entry and the
     module-level :func:`verify_inclusion` re-derives the root from
     ``(entry_hash, branch)`` -- so anyone holding only the on-chain root can
     later prove a specific decision was in the anchored batch without the log.

  3. **Persistence.** :meth:`to_jsonl` / :meth:`from_jsonl` serialise the log
     to JSON-lines so it survives across runs and is independently auditable;
     loading **re-verifies the chain** and rejects a tampered file.

Hash chain (identical scheme to ``registry.py``)
------------------------------------------------
Each entry carries ``seq`` (contiguous from 0), ``prev_hash`` (the previous
entry's ``hash``, or 64 zeros for genesis), the caller's ``event`` payload, and
``hash``::

    hash = sha256(prev_hash_hex + canonical_json(entry_without_hash_or_sig)).hexdigest()

where ``canonical_json = json.dumps(..., sort_keys=True, separators=(",", ":"))``.
The signature (if any) is intentionally NOT part of the hashed body -- the hash
commits to the content; the signature commits to the hash -- so the two
integrity mechanisms are cleanly layered and independently verifiable.

Immutability / boundaries
-------------------------
``append`` deep-copies the caller's event (via a canonical-JSON round-trip,
which also proves serialisability at the boundary) and never mutates inputs or
previously stored entries. Non-dict events, non-serialisable events, and events
carrying reserved envelope keys are rejected explicitly. ``entries`` hands back
copies so a caller cannot reach into and reorder the log in place.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Callable, Iterable

# Reuse the EXACT genesis sentinel the registry uses so the two chains align.
GENESIS_PREV_HASH = "0" * 64

# Envelope keys the log owns; a caller's event payload may not collide with them.
_RESERVED_KEYS = frozenset(
    {"seq", "prev_hash", "hash", "event", "issuer", "signature"}
)

# Defensive ceiling so a single hostile/huge event cannot exhaust memory when
# loading an untrusted JSONL file. ~4 MiB of canonical JSON per entry is already
# far larger than any real decision event (a few hundred bytes).
_MAX_EVENT_BYTES = 4 * 1024 * 1024


def _canonical_json(obj: dict) -> str:
    """Deterministic JSON for hashing: sorted keys, no whitespace.

    Identical to ``registry._canonical_json`` so both chains hash byte-for-byte
    the same way. ``sort_keys`` makes the encoding insensitive to key insertion
    order; ``separators`` strips incidental whitespace.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash_body(prev_hash: str, body: dict) -> str:
    """sha256 over prev_hash_hex concatenated with the canonical body JSON."""
    payload = prev_hash + _canonical_json(body)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _hash_pair(left_hex: str, right_hex: str) -> str:
    """Internal Merkle node: sha256 of the two child hex digests concatenated.

    We hash the hex strings (not raw bytes) for symmetry with the entry hashes,
    which are themselves hex digests. Deterministic and order-sensitive
    (``hash_pair(a, b) != hash_pair(b, a)``) so a branch's left/right flags
    matter -- exactly what makes the inclusion proof bind position as well as
    value.
    """
    return hashlib.sha256((left_hex + right_hex).encode("utf-8")).hexdigest()


def _validate_event(event: dict) -> dict:
    """Validate a caller event at the boundary and return a canonical deep copy.

    Rejects (explicitly, never silently): non-dict events, events whose top-level
    keys collide with reserved envelope keys, non-JSON-serialisable events, and
    events whose canonical encoding exceeds ``_MAX_EVENT_BYTES``. The returned
    object is a fresh structure decoded from the canonical JSON, so the log never
    holds a reference the caller can later mutate, and every stored event is
    guaranteed round-trippable through JSONL.
    """
    if not isinstance(event, dict):
        raise TypeError(
            f"event must be a dict, got {type(event).__name__}"
        )
    # Keys must be strings (JSON objects have string keys) and must not shadow
    # the envelope. Catch this before serialisation for a precise error.
    for key in event:
        if not isinstance(key, str):
            raise TypeError(f"event keys must be str, got {type(key).__name__}")
        if key in _RESERVED_KEYS:
            raise ValueError(
                f"event may not use reserved envelope key {key!r}"
            )
    try:
        canonical = _canonical_json(event)
    except (TypeError, ValueError) as exc:
        # json raises TypeError for non-serialisable objects, ValueError for
        # out-of-range floats (NaN/Inf with allow_nan disabled is ValueError).
        raise ValueError(f"event is not JSON-serialisable: {exc}") from exc
    if len(canonical.encode("utf-8")) > _MAX_EVENT_BYTES:
        raise ValueError("event exceeds maximum serialised size")
    # Decode back to a fresh, owned structure (defensive deep copy + proof of
    # round-trip fidelity).
    return json.loads(canonical)


class AuditLog:
    """Append-only hash-chained log of decision/registry events with anchoring.

    Each :meth:`append` returns the newly created entry (a copy). Entries are
    never edited in place by this class; ``register``/``revoke``-style mutation
    is replaced by pure appends, mirroring the registry's immutable style. An
    external tamperer who mutates a stored field is exactly what
    :meth:`verify_chain` / :meth:`verify_signatures` are built to catch.
    """

    def __init__(self) -> None:
        # Append-only list of entry dicts. Private; handed out only via copies.
        self._log: list[dict] = []

    # -- append --------------------------------------------------------------

    def append(self, event: dict, issuer=None) -> dict:
        """Append ``event`` as the next chained entry; return a copy of it.

        ``event`` is validated and deep-copied at the boundary. If ``issuer`` is
        given it must expose ``junction_id: str`` and ``sign(bytes) -> bytes``
        (a :class:`~identity.JunctionIdentity`); the entry's hash is signed and
        the hex signature + issuer id are stored alongside (outside the hashed
        body). Returns a fresh copy so the caller cannot mutate the stored entry.
        """
        owned_event = _validate_event(event)
        seq = len(self._log)
        prev_hash = self._log[-1]["hash"] if self._log else GENESIS_PREV_HASH
        # The hashed body commits to seq + prev_hash + payload, NOT the signature.
        body = {"seq": seq, "prev_hash": prev_hash, "event": owned_event}
        entry_hash = _hash_body(prev_hash, body)

        issuer_id = None
        signature_hex = None
        if issuer is not None:
            issuer_id, signature_hex = self._sign_entry(issuer, entry_hash)

        entry = {
            **body,
            "hash": entry_hash,
            "issuer": issuer_id,
            "signature": signature_hex,
        }
        self._log.append(entry)
        return copy.deepcopy(entry)

    @staticmethod
    def _sign_entry(issuer, entry_hash: str) -> tuple[str, str]:
        """Sign ``entry_hash`` with ``issuer``; return (issuer_id, signature_hex).

        The signed payload is the entry hash's hex *bytes* (the exact bytes a
        verifier reconstructs in :meth:`verify_signatures`).
        """
        issuer_id = getattr(issuer, "junction_id", None)
        sign = getattr(issuer, "sign", None)
        if not isinstance(issuer_id, str) or not issuer_id:
            raise TypeError("issuer must expose a non-empty str junction_id")
        if not callable(sign):
            raise TypeError("issuer must expose a callable sign(bytes)")
        signature = sign(entry_hash.encode("utf-8"))
        if not isinstance(signature, (bytes, bytearray)):
            raise TypeError("issuer.sign must return bytes")
        return issuer_id, bytes(signature).hex()

    # -- read ----------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._log)

    def entries(self, filter: Callable[[dict], bool] | None = None) -> list[dict]:
        """Return copies of all entries, optionally filtered.

        ``filter`` is an optional predicate ``entry -> bool`` applied to a copy
        of each entry (so a misbehaving predicate cannot mutate the log). Returns
        a fresh list of deep copies; callers can sort/edit it freely without
        touching the log's own state.
        """
        if filter is not None and not callable(filter):
            raise TypeError("filter must be callable or None")
        out: list[dict] = []
        for entry in self._log:
            entry_copy = copy.deepcopy(entry)
            if filter is None or filter(entry_copy):
                out.append(entry_copy)
        return out

    # -- integrity: hash chain ----------------------------------------------

    def verify_chain(self) -> bool:
        """Recompute the sha256 hash-chain; False if any entry was tampered.

        Checks, for every entry in order: contiguous ``seq`` from 0, ``prev_hash``
        links the previous entry's ``hash``, and the stored ``hash`` equals the
        recomputed hash of ``{seq, prev_hash, event}``. Any single-field mutation
        or reorder breaks at least one of these. Mirrors ``Registry.verify_chain``.
        """
        prev_hash = GENESIS_PREV_HASH
        for expected_seq, entry in enumerate(self._log):
            if not isinstance(entry, dict):
                return False
            if entry.get("seq") != expected_seq:
                return False
            if entry.get("prev_hash") != prev_hash:
                return False
            body = {
                "seq": entry.get("seq"),
                "prev_hash": entry.get("prev_hash"),
                "event": entry.get("event"),
            }
            try:
                recomputed = _hash_body(prev_hash, body)
            except (TypeError, ValueError):
                # A tampered file could carry a non-serialisable event body.
                return False
            if entry.get("hash") != recomputed:
                return False
            prev_hash = entry["hash"]
        return True

    # -- integrity: signatures ----------------------------------------------

    def verify_signatures(self, public_keys: dict[str, bytes]) -> bool:
        """Verify every signed entry against its issuer's DER public key.

        ``public_keys`` maps ``issuer junction_id -> DER public-key bytes``.
        Returns True iff *every* entry that carries a signature verifies under
        the supplied key for its issuer. An unsigned entry (``signature`` is
        None) is skipped. Returns False if a signed entry's issuer is unknown,
        its signature is malformed, or the Ed25519 check fails (e.g. a swapped
        signature). Never raises on hostile input -- a bad blob yields False.
        """
        if not isinstance(public_keys, dict):
            raise TypeError("public_keys must be a dict")
        # Imported lazily so audit_log has no hard import-time crypto dependency
        # for callers that never sign (e.g. pure persistence/anchoring use).
        from identity import verify as _verify

        for entry in self._log:
            signature_hex = entry.get("signature")
            if signature_hex is None:
                continue
            issuer_id = entry.get("issuer")
            entry_hash = entry.get("hash")
            if not isinstance(issuer_id, str) or not isinstance(entry_hash, str):
                return False
            pub = public_keys.get(issuer_id)
            if pub is None:
                return False
            try:
                signature = bytes.fromhex(signature_hex)
            except (ValueError, TypeError):
                return False
            if not _verify(pub, entry_hash.encode("utf-8"), signature):
                return False
        return True

    # -- Merkle anchoring (the Besu bridge) ---------------------------------

    def merkle_root(self, start: int = 0, end: int | None = None) -> str:
        """Merkle root over the entry hashes in ``[start, end)`` (end exclusive).

        Folds a *batch* of entry hashes into a single 64-hex root so one ~2.1 s
        Besu write anchors the whole batch (per the ledger benchmark).
        Internal nodes use :func:`_hash_pair`; an odd level duplicates its last
        node (the standard Bitcoin-style promotion) so the tree is well defined
        for any batch size >= 1. Deterministic: the same range always yields the
        same root. Raises ``ValueError`` on an empty or out-of-bounds range -- a
        root over zero entries is meaningless and would silently anchor nothing.
        """
        leaves = self._range_hashes(start, end)
        if not leaves:
            raise ValueError("merkle_root requires a non-empty range")
        level = list(leaves)
        while len(level) > 1:
            if len(level) % 2 == 1:
                level = [*level, level[-1]]  # promote the lone last node
            level = [
                _hash_pair(level[i], level[i + 1])
                for i in range(0, len(level), 2)
            ]
        return level[0]

    def inclusion_proof(self, index: int, start: int = 0,
                        end: int | None = None) -> list[dict]:
        """Merkle branch proving entry ``index`` is in the batch ``[start, end)``.

        Returns the ordered list of sibling hashes from leaf to root, each as
        ``{"hash": <hex>, "position": "left"|"right"}`` where ``position`` is the
        side the SIBLING sits on relative to the running node. Feed it, with the
        entry's own hash and the anchored root, to :func:`verify_inclusion`. The
        promotion of a lone odd node is reflected by a ``"right"`` sibling equal
        to the node itself, so the proof re-derives the same root the anchor used.

        ``index`` is the *absolute* entry index; it must lie within ``[start,
        end)``. Raises ``IndexError`` / ``ValueError`` for out-of-range inputs.
        """
        leaves = self._range_hashes(start, end)
        if not leaves:
            raise ValueError("inclusion_proof requires a non-empty range")
        norm_start = self._norm_start(start)
        local = index - norm_start
        if local < 0 or local >= len(leaves):
            raise IndexError(
                f"index {index} is outside the anchored range "
                f"[{norm_start}, {norm_start + len(leaves)})"
            )
        branch: list[dict] = []
        level = list(leaves)
        pos = local
        while len(level) > 1:
            if len(level) % 2 == 1:
                level = [*level, level[-1]]
            if pos % 2 == 0:
                sibling = level[pos + 1]
                branch.append({"hash": sibling, "position": "right"})
            else:
                sibling = level[pos - 1]
                branch.append({"hash": sibling, "position": "left"})
            level = [
                _hash_pair(level[i], level[i + 1])
                for i in range(0, len(level), 2)
            ]
            pos //= 2
        return branch

    def _range_hashes(self, start: int, end: int | None) -> list[str]:
        """The ordered entry hashes for ``[start, end)`` (end exclusive)."""
        if isinstance(start, bool) or not isinstance(start, int):
            raise TypeError("start must be an int")
        if end is not None and (isinstance(end, bool) or not isinstance(end, int)):
            raise TypeError("end must be an int or None")
        n = len(self._log)
        norm_start = self._norm_start(start)
        norm_end = n if end is None else (end + n if end < 0 else end)
        if norm_start < 0 or norm_end > n or norm_start >= norm_end:
            raise ValueError(
                f"invalid range [{start}, {end}) over {n} entries"
            )
        return [self._log[i]["hash"] for i in range(norm_start, norm_end)]

    def _norm_start(self, start: int) -> int:
        n = len(self._log)
        return start + n if isinstance(start, int) and start < 0 else start

    # -- persistence ---------------------------------------------------------

    def to_jsonl(self) -> str:
        """Serialise the whole log to JSON-lines (one entry per line).

        Each line is canonical JSON of one entry. The result re-parses via
        :meth:`from_jsonl` to an equivalent log whose chain re-verifies. Returns
        an empty string for an empty log.
        """
        return "\n".join(_canonical_json(entry) for entry in self._log)

    @classmethod
    def from_jsonl(cls, text: str, verify: bool = True) -> "AuditLog":
        """Reconstruct an :class:`AuditLog` from :meth:`to_jsonl` output.

        Parses each non-empty line as one entry, validates the envelope shape,
        and (when ``verify`` is True, the default) re-verifies the hash chain --
        raising ``ValueError`` if the file was tampered with. Set ``verify=False``
        only to inspect a known-broken log for forensics. Blank lines are ignored
        so trailing newlines are harmless.
        """
        if not isinstance(text, str):
            raise TypeError("from_jsonl expects a str")
        log = cls()
        rebuilt: list[dict] = []
        for lineno, raw in enumerate(text.splitlines()):
            line = raw.strip()
            if not line:
                continue
            if len(line.encode("utf-8")) > _MAX_EVENT_BYTES:
                raise ValueError(f"line {lineno} exceeds maximum entry size")
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {lineno} is not valid JSON: {exc}") from exc
            rebuilt.append(cls._validate_entry_shape(entry, lineno))
        log._log = rebuilt
        if verify and not log.verify_chain():
            raise ValueError("loaded audit log failed chain verification (tampered)")
        return log

    @staticmethod
    def _validate_entry_shape(entry: object, lineno: int) -> dict:
        """Ensure a loaded line has the exact envelope keys and basic types."""
        if not isinstance(entry, dict):
            raise ValueError(f"line {lineno} is not a JSON object")
        required = {"seq", "prev_hash", "event", "hash", "issuer", "signature"}
        if set(entry) != required:
            raise ValueError(
                f"line {lineno} has unexpected keys {sorted(entry)!r}"
            )
        if not isinstance(entry["seq"], int) or isinstance(entry["seq"], bool):
            raise ValueError(f"line {lineno} seq must be an int")
        if not isinstance(entry["prev_hash"], str) or not isinstance(entry["hash"], str):
            raise ValueError(f"line {lineno} prev_hash/hash must be strings")
        if not isinstance(entry["event"], dict):
            raise ValueError(f"line {lineno} event must be an object")
        if entry["issuer"] is not None and not isinstance(entry["issuer"], str):
            raise ValueError(f"line {lineno} issuer must be a string or null")
        if entry["signature"] is not None and not isinstance(entry["signature"], str):
            raise ValueError(f"line {lineno} signature must be a string or null")
        return entry


def verify_inclusion(entry_hash: str, branch: Iterable[dict], root: str) -> bool:
    """Re-derive a Merkle root from ``(entry_hash, branch)`` and compare to ``root``.

    The verifier holds only the on-chain ``root`` and a single entry's hash plus
    its branch (from :meth:`AuditLog.inclusion_proof`); it walks the branch,
    combining the running hash with each sibling on the indicated side, and
    returns True iff the re-derived root equals ``root``. A forged entry, a
    tampered branch, or the wrong root yields False. Never raises on malformed
    input -- a verifier must reject a hostile proof, not crash on it.
    """
    if not isinstance(entry_hash, str) or not isinstance(root, str):
        return False
    try:
        node = entry_hash
        for step in branch:
            if not isinstance(step, dict):
                return False
            sibling = step.get("hash")
            position = step.get("position")
            if not isinstance(sibling, str):
                return False
            if position == "left":
                node = _hash_pair(sibling, node)
            elif position == "right":
                node = _hash_pair(node, sibling)
            else:
                return False
        return node == root
    except Exception:
        # Defensive: a hostile branch must never escalate to a crash.
        return False
