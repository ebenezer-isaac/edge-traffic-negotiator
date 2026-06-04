"""Signed neighbour-message bus for The Edge Negotiator.

Cross-junction coordination (brief Milestone-2, Wk 3-4): each signalised
junction's SLM agent publishes a short predicted-state report; its *adjacent*
junctions consume those reports to coordinate phases. The bus is the security
boundary -- a junction must only ever act on a report that:

  * came from a junction that is actually its neighbour (topology adjacency),
  * was published by a *currently approved* agent (the permissioned registry),
  * carries a valid Ed25519 signature over the exact bytes it claims, and
  * has not already been consumed (no replay of a prior tick's report).

Anything failing those checks is dropped and recorded in ``rejected`` with a
precise reason, never silently swallowed and never crashing the receiver.

Transport
---------
This implementation is *in-process*: ``publish`` stores a signed
``NeighborMessage`` in an internal buffer and ``inbox`` reads from it. MQTT is
deferred (brief): the publish/inbox split is intentionally the same shape an
MQTT adapter would wrap -- ``publish`` produces a fully self-describing,
self-authenticating message (sender, t, payload, signature) that could be
serialised onto a topic, and ``inbox`` performs *all* trust checks on receipt,
so an MQTT subscriber would reuse the identical verification path. No broker
dependency is introduced now.

Canonical bytes
---------------
The signed/verified bytes are ``canonical_bytes(sender, t, payload)`` --
deterministic JSON with sorted keys and no whitespace -- so signer and verifier
hash byte-identical input regardless of dict ordering.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from identity import JunctionIdentity, verify
from registry import Registry

# Valid rejection reasons (closed set -- the bus never emits anything else).
_REASON_UNKNOWN_SENDER = "unknown_sender"
_REASON_REVOKED = "revoked"
_REASON_BAD_SIGNATURE = "bad_signature"
_REASON_NOT_NEIGHBOUR = "not_neighbour"
_REASON_REPLAY = "replay"


@dataclass(frozen=True)
class NeighborMessage:
    """An authenticated neighbour report.

    Immutable (frozen): once published, the (sender, t, payload, signature)
    tuple is fixed, so the bytes a verifier checks are exactly the bytes that
    were signed. ``payload`` is a plain dict; treat it as read-only.
    """

    sender: str
    t: int
    payload: dict
    signature: bytes


def canonical_bytes(sender: str, t: int, payload: dict) -> bytes:
    """Deterministic byte encoding of a message's signable content.

    Sorted keys + no whitespace make the encoding canonical, so the signer and
    every verifier produce byte-identical input independent of dict ordering.
    """
    return json.dumps(
        {"sender": sender, "t": t, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


class MessageBus:
    """In-process signed bus enforcing topology + registry + crypto + replay.

    Construct with the shared :class:`Registry` (membership / public keys) and
    the static neighbour ``adjacency`` (``{junction_id: [neighbour_id, ...]}``).
    Both are treated as read-only by the bus.
    """

    def __init__(self, registry: Registry, adjacency: dict[str, list[str]]) -> None:
        self._registry = registry
        # Freeze adjacency into neighbour sets for O(1), copy-safe membership
        # tests; we never mutate the caller's dict or lists.
        self._neighbours: dict[str, frozenset[str]] = {
            jid: frozenset(neighbours) for jid, neighbours in adjacency.items()
        }
        # All published messages, in publish order. Verification happens on
        # read (inbox), exactly as an MQTT subscriber would verify on receipt.
        self._published: list[NeighborMessage] = []
        # Replay guard: set of (recipient, sender, t) tuples already delivered.
        self._delivered: set[tuple[str, str, int]] = set()
        # Append-only rejection log.
        self._rejected: list[dict] = []

        # -- P2: per-recipient scan index (removes the O(n^2) full rescan) ----
        # On a full (t is None) scan, ``_scan_pos[recipient]`` is how many of the
        # ``_published`` entries this recipient has ALREADY examined. A later
        # inbox(recipient) only examines the suffix that appeared since, so a run
        # of R rounds over a buffer that grows to N messages costs O(N) total per
        # recipient instead of O(N^2).
        self._scan_pos: dict[str, int] = {}
        # Replay logging is bounded: a message already delivered to a recipient is
        # recorded as ``replay`` AT MOST ONCE per (recipient, sender, t). The first
        # genuine re-read of the SAME message still logs one ``replay`` (security
        # semantics + existing tests preserved); subsequent rescans of that same
        # old message do NOT re-log it, so the rejected log cannot grow quadratically
        # from repeated rescans. Genuine fresh rejections are unaffected.
        self._replay_logged: set[tuple[str, str, int]] = set()
        # Same bounding for permanent (non-replay) rejections, keyed by
        # (recipient, sender, t, reason) -- a stable verdict logged once.
        self._reject_logged: set[tuple[str, str, int, str]] = set()
        # Snapshot of the buffer length last time we scanned, so we can detect a
        # caller that REPLACES/truncates ``self._published`` directly (the
        # adversarial tests inject forged messages this way) and safely rescan
        # from the start rather than trusting a now-stale cursor.
        self._scanned_len: int = 0

    # -- publish -------------------------------------------------------------

    def publish(
        self, identity: JunctionIdentity, t: int, payload: dict
    ) -> NeighborMessage:
        """Sign ``payload`` for tick ``t`` and store the message.

        The message is signed with ``identity``'s private key over
        ``canonical_bytes(identity.junction_id, t, payload)``. Publishing does
        not authorise delivery -- all trust checks run in :meth:`inbox`. The
        payload is shallow-copied so a later caller-side mutation cannot change
        what was signed.
        """
        if not isinstance(identity, JunctionIdentity):
            raise TypeError("identity must be a JunctionIdentity")
        if not isinstance(t, int) or isinstance(t, bool):
            raise TypeError("t must be an int")
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dict")

        sender = identity.junction_id
        # Copy so the signed content is frozen against later external mutation.
        frozen_payload = dict(payload)
        signature = identity.sign(canonical_bytes(sender, t, frozen_payload))

        message = NeighborMessage(
            sender=sender, t=t, payload=frozen_payload, signature=signature
        )
        self._published = [*self._published, message]
        return message

    # -- inbox ---------------------------------------------------------------

    def inbox(self, recipient: str, t: int | None = None) -> list[NeighborMessage]:
        """Return verified, authorised, non-replayed messages for ``recipient``.

        A published message is delivered iff ALL hold:
          * its sender is a neighbour of ``recipient`` (per adjacency),
          * the sender is currently approved in the registry,
          * its signature verifies against the sender's registered public key
            over ``canonical_bytes(sender, t, payload)``, and
          * ``(recipient, sender, t)`` has not been delivered before (no replay).

        If ``t`` is given, only messages with that tick are considered. Every
        message that is considered but dropped is appended to :attr:`rejected`
        with a precise reason; delivery is idempotent thanks to the replay guard.
        """
        neighbours = self._neighbours.get(recipient, frozenset())
        delivered: list[NeighborMessage] = []

        # P2 index. For the common full scan (t is None -- the controller's path)
        # start from where this recipient last finished, so we never re-walk the
        # whole ever-growing buffer. Detect a caller that REPLACED or truncated
        # ``_published`` directly (adversarial tests inject forged messages this
        # way) and fall back to a full rescan from 0 so correctness never depends
        # on a now-stale cursor. The tick-filtered path (t is not None) always
        # scans from 0 -- it is only used in small, explicit test calls.
        published = self._published
        buf_len = len(published)
        if t is None:
            start = self._scan_pos.get(recipient, 0)
            if buf_len < self._scanned_len or start > buf_len:
                start = 0  # buffer was replaced/truncated -> rescan safely
            self._scanned_len = buf_len
        else:
            start = 0

        # We may need to keep the cursor pinned at the first not-yet-finalised
        # message: a freshly delivered message must remain re-scannable so a later
        # call still records exactly one ``replay`` for it (security semantics +
        # existing tests). Track the lowest index that is NOT yet finalised.
        first_unfinalised = buf_len if t is None else None

        for idx in range(start, buf_len):
            message = published[idx]
            if t is not None and message.t != t:
                continue

            sender = message.sender
            key = (recipient, sender, message.t)

            # 1) Topology: sender must be an adjacency neighbour of recipient.
            if sender not in neighbours:
                self._reject_once(recipient, sender, message.t, _REASON_NOT_NEIGHBOUR)
                continue

            # 2) Membership: sender must be currently approved.
            #    Distinguish never-registered (unknown_sender) from revoked
            #    using the registry's stored public key as the signal.
            public_key = self._registry.public_key(sender)
            if not self._registry.is_approved(sender) or public_key is None:
                reason = (
                    _REASON_REVOKED
                    if self._was_ever_registered(sender)
                    else _REASON_UNKNOWN_SENDER
                )
                self._reject_once(recipient, sender, message.t, reason)
                continue

            # 3) Crypto: signature must verify over the canonical bytes. This
            #    also catches impersonation (sender claims A1 but signed with a
            #    different key) and tampered payloads -- both yield a signature
            #    that does not match A1's registered public key.
            expected = canonical_bytes(sender, message.t, message.payload)
            if not verify(public_key, expected, message.signature):
                self._reject_once(recipient, sender, message.t, _REASON_BAD_SIGNATURE)
                continue

            # 4) Replay: same (recipient, sender, t) must not deliver twice.
            if key in self._delivered:
                # Log the replay AT MOST ONCE per (recipient, sender, t): the first
                # genuine re-read records it; rescans of the same old message in
                # later rounds do not, so the log can't grow quadratically.
                if key not in self._replay_logged:
                    self._reject(recipient, sender, message.t, _REASON_REPLAY)
                    self._replay_logged.add(key)
                continue

            self._delivered.add(key)
            delivered.append(message)
            # Pin the cursor at this freshly delivered message so a later scan
            # re-encounters it once (to log its single replay) before skipping on.
            if t is None and first_unfinalised == buf_len:
                first_unfinalised = idx

        if t is None:
            self._scan_pos[recipient] = first_unfinalised

        return delivered

    @property
    def rejected(self) -> list[dict]:
        """Append-only log of dropped messages.

        Each entry is ``{"recipient", "sender", "t", "reason"}`` with ``reason``
        in {unknown_sender, revoked, bad_signature, not_neighbour, replay}.
        Returns a shallow copy so callers cannot mutate the bus's own log.
        """
        return list(self._rejected)

    # -- internals -----------------------------------------------------------

    def _reject(self, recipient: str, sender: str, t: int, reason: str) -> None:
        self._rejected = [
            *self._rejected,
            {"recipient": recipient, "sender": sender, "t": t, "reason": reason},
        ]

    def _reject_once(self, recipient: str, sender: str, t: int, reason: str) -> None:
        """Record a PERMANENT (non-replay) rejection at most once per message.

        Topology / membership / signature verdicts are stable for a given
        (recipient, sender, t, reason): a message rejected for one of these
        reasons will be rejected for the SAME reason on every rescan. Logging it
        once keeps the rejection reason and security guarantee intact while
        preventing the ``rejected`` log from growing unboundedly when the bus is
        rescanned each round (P2). The first occurrence is recorded exactly as
        before; genuine fresh rejections of NEW messages are unaffected.
        """
        marker = (recipient, sender, t, reason)
        if marker in self._reject_logged:
            return
        self._reject_logged.add(marker)
        self._reject(recipient, sender, t, reason)

    def _was_ever_registered(self, junction_id: str) -> bool:
        """True iff ``junction_id`` appears as a registration in the audit log.

        Lets us report ``revoked`` (was approved, now not) distinctly from
        ``unknown_sender`` (never registered) without the registry exposing a
        private "known" set. The audit log is the ledger-agnostic source of truth.
        """
        for event in self._registry.audit_log:
            if event.get("action") == "register" and event.get("junction_id") == junction_id:
                return True
        return False
