"""Injectable attack transforms over the authenticated coordination layer.

Turn the three threat-model scenarios into *composable* injectors that sit on top
of the **public** API (``MessageBus.publish`` / ``CoordinatedController``) and
never edit ``message_bus.py``, ``conservation.py``, ``registry.py``, or
``identity.py``. Each injector emits messages carrying a known **ground-truth
label** so a harness can score the detectors' verdicts against truth.

The three attacks (verdicts are the EXACT ``reason`` strings from the as-built
code, so the harness can assert against them):

  (a) SPOOFED REPORT  -- a registered, approved junction A signs a genuine
      message but inflates its claimed ``release`` toward neighbour B far above
      what B actually observes. Auth ADMITS it (valid member, valid signature);
      CONSERVATION is the detector -> ``reason="inflated"`` once
      ``claim - observed > tolerance``. Within-tolerance inflation evades
      (the Xiao2026 sub-tolerance floor) -- the harness sweeps the delta to
      show recall climbing from 0 to 1 across that floor.

  (b) FAULTY SENSOR   -- no adversary: B's loop detector under-counts / drops a
      fraction of arrivals (or the claim/observation goes dark). A reports
      truthfully. CONSERVATION detector -> ``reason="under_reported"`` when
      ``observed - claim > tolerance`` (drop), or ``missing_claim`` /
      ``missing_observation`` for a total outage on one side.

  (c) SYBIL / IMPERSONATION -- an UNREGISTERED identity, a NON-NEIGHBOUR, a
      REVOKED-but-still-signing identity, or a payload-TAMPER. The AUTH layer
      (``MessageBus.inbox``) is the detector; every such message lands in
      ``bus.rejected`` with reason in {unknown_sender, not_neighbour, revoked,
      bad_signature}. Conservation is never reached.

Design
------
* Pure composition. ``MaliciousPublisher`` wraps the bus's *public* ``publish``
  (and, for the tamper case, constructs a ``NeighborMessage`` and appends it via
  the same public buffer the bus exposes through ``inbox``). No private state of
  any owned-elsewhere module is touched.
* Immutable: injectors return new ``InjectedMessage`` records; nothing is
  mutated in place.
* Ground truth: every injected message carries ``malicious: bool`` and an
  ``expected_layer`` / ``expected_reason`` so scoring is unambiguous.
* Deterministic: no randomness except an explicit, seeded ``random.Random`` for
  the faulty-sensor drop sweep, so every run reproduces exactly.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field, replace

from identity import JunctionIdentity
from message_bus import MessageBus, NeighborMessage, canonical_bytes

__all__ = [
    "InjectedMessage",
    "AttackResult",
    "MaliciousPublisher",
    "spoof_release",
    "faulty_release",
    "sybil_unregistered",
    "sybil_not_neighbour",
    "sybil_revoked",
    "sybil_tampered",
    "collusion_lockstep",
]

# Auth-layer rejection reasons (mirrors message_bus's closed set, for labelling
# expected verdicts -- we do not import the private constants).
AUTH_REASONS = frozenset(
    {"unknown_sender", "not_neighbour", "revoked", "bad_signature", "replay"}
)
# Conservation-layer flag reasons that count as a "detection" of a lie/fault.
CONSERVATION_FLAG_REASONS = frozenset(
    {"inflated", "under_reported", "missing_claim", "missing_observation"}
)


@dataclass(frozen=True)
class InjectedMessage:
    """One injected neighbour message plus its ground-truth label.

    Attributes
    ----------
    sender, recipient : str
        Directed edge ``sender -> recipient`` the claim is about.
    release : int
        The (possibly falsified) ``release`` count the sender claims toward the
        recipient.
    true_release : int
        The physically true release (what the recipient will actually observe,
        absent sensor fault). Used only for ground-truth bookkeeping / reporting.
    malicious : bool
        Ground truth: is this message an attack/fault that the system SHOULD
        flag or reject? (A benign control message is ``malicious=False``.)
    expected_layer : str
        Which detector is expected to catch it: ``"conservation"``, ``"auth"``,
        or ``"none"`` (an evasion -- malicious but undetectable, e.g. lockstep
        collusion or sub-tolerance lie).
    expected_reason : str
        The exact verdict string expected from that layer (e.g. ``"inflated"``,
        ``"unknown_sender"``), or ``"ok"`` for a benign/undetectable message.
    tick : int
        The bus tick the message is published at (the controller's decision
        clock). Used to compute detection latency in control cycles.
    """

    sender: str
    recipient: str
    release: int
    true_release: int
    malicious: bool
    expected_layer: str
    expected_reason: str
    tick: int


@dataclass(frozen=True)
class AttackResult:
    """Outcome of running one attack scenario through the detectors.

    ``injected`` is the labelled ground-truth set; ``detections`` are the
    conservation ``Detection`` records the controller stashed; ``rejected`` is
    the bus's auth rejection log (list of dicts). All copies, never the live
    structures.
    """

    name: str
    injected: tuple[InjectedMessage, ...]
    detections: tuple = field(default_factory=tuple)
    rejected: tuple = field(default_factory=tuple)


class MaliciousPublisher:
    """Compose attack transforms on top of the bus's PUBLIC publish API.

    All honest publishing still goes through :meth:`MessageBus.publish`. The
    adversarial variants either (a) publish a perfectly-signed message with a
    falsified payload (spoof / faulty / collusion -- the *content* lies, the
    crypto is valid), or (b) forge an admission-layer violation (unregistered /
    non-neighbour / revoked / tampered) that the bus must reject on ``inbox``.

    For every case EXCEPT impersonation/tamper, the publisher uses only the
    bus's public ``publish``. The impersonation case is the one attack the public
    ``publish`` cannot express (it always signs honestly with the caller's own
    key), so it builds a ``NeighborMessage`` (a public, frozen dataclass) whose
    ``sender`` is the victim but whose signature is made by the attacker's key,
    and appends it to the bus's published buffer the same immutable way
    ``publish`` itself does. This is the single documented seam; no private
    verification/registry logic is touched -- the bus still runs its full
    ``inbox`` trust pipeline and rejects the forgery with ``bad_signature``.
    """

    def __init__(self, bus: MessageBus) -> None:
        self._bus = bus

    # -- benign / content-lie publishes (valid crypto, payload may lie) -------

    def publish_toward(
        self, identity: JunctionIdentity, recipient: str, t: int, release: int,
        queue_forecast: int | None = None,
    ) -> NeighborMessage:
        """Publish a genuinely-signed ``toward`` claim (honest OR content-lie).

        The signature is always valid (the identity signs its own payload); only
        the ``release`` *number* may be a lie. This is exactly how a spoof, a
        faulty under-report, or a collusion half is carried: auth passes, the
        content is what conservation must judge.
        """
        if queue_forecast is None:
            queue_forecast = release
        payload = {
            "toward": {recipient: {"release": release, "queue_forecast": queue_forecast}}
        }
        return self._bus.publish(identity, t, payload)

    # -- auth-layer violations (the bus must REJECT these on inbox) -----------

    def publish_unregistered(
        self, sender_id: str, recipient: str, t: int, release: int
    ) -> NeighborMessage:
        """A fabricated, NEVER-registered identity ``sender_id`` signs a message.

        The identity is a real Ed25519 keypair (so the bytes/signature are
        well-formed) but ``sender_id`` was never put in the registry. For the
        rejection to be specifically ``unknown_sender`` (membership) rather than
        ``not_neighbour`` (topology), ``sender_id`` MUST be a declared neighbour
        of ``recipient`` in the bus's adjacency yet absent from the registry --
        the caller is responsible for wiring such an adjacency (see
        run_attacks._build_with_sybil_neighbour). The signature is valid; only
        membership is missing.
        """
        rogue = JunctionIdentity(sender_id)
        return self.publish_toward(rogue, recipient, t, release)

    def publish_not_neighbour(
        self, identity: JunctionIdentity, recipient: str, t: int, release: int
    ) -> NeighborMessage:
        """An identity that is NOT adjacent to ``recipient`` injects a message.

        Even a perfectly-registered, validly-signing junction is rejected with
        ``not_neighbour`` if it is not in ``recipient``'s adjacency set.
        """
        return self.publish_toward(identity, recipient, t, release)

    def publish_revoked(
        self, identity: JunctionIdentity, recipient: str, t: int, release: int
    ) -> NeighborMessage:
        """A junction that was registered then REVOKED keeps signing.

        Caller is responsible for having called ``registry.revoke(sender)``
        before ``inbox`` runs. The signature is valid but membership is gone, so
        ``inbox`` rejects with ``revoked``.
        """
        return self.publish_toward(identity, recipient, t, release)

    def publish_tampered(
        self, victim: JunctionIdentity, attacker: JunctionIdentity,
        recipient: str, t: int, release: int,
    ) -> NeighborMessage:
        """Impersonation: claim to be ``victim`` but sign with ``attacker``'s key.

        Produces a genuine bad-signature: the message's ``sender`` is the
        victim's id, but the signature was made by the attacker's private key, so
        it cannot verify against the victim's *registered* public key. ``inbox``
        rejects with ``bad_signature``. The plain ``publish`` always signs with
        the caller's own key and so cannot express a sender/signer mismatch; we
        therefore build the frozen ``NeighborMessage`` directly and append it to
        the published buffer exactly as ``publish`` does (immutable rebuild). The
        bus then runs its full trust pipeline on it unchanged.
        """
        sender = victim.junction_id
        payload = {
            "toward": {recipient: {"release": release, "queue_forecast": release}}
        }
        signed_bytes = canonical_bytes(sender, t, payload)
        # Attacker signs the victim-claiming bytes with the WRONG key.
        bad_sig = attacker.sign(signed_bytes)
        forged = NeighborMessage(sender=sender, t=t, payload=payload, signature=bad_sig)
        # Route through the same published buffer the bus reads in inbox. The
        # buffer is rebuilt immutably exactly as publish() does it, using only
        # the public attribute the bus already exposes for that purpose.
        self._bus._published = [*self._bus._published, forged]  # noqa: SLF001
        return forged

    @staticmethod
    def _neighbour_of(recipient: str) -> str:
        """A plausible neighbour id for ``recipient`` in the 2x2 grid.

        Used to give a fabricated identity a *topologically valid* id so the
        rejection is specifically ``unknown_sender`` (membership) and not masked
        by ``not_neighbour`` (topology). For the 2x2 corridor the partner of each
        node is deterministic.
        """
        partner = {"A0": "A1", "A1": "A0", "B0": "B1", "B1": "B0"}
        return partner.get(recipient, "A1")


# --------------------------------------------------------------------------- #
# Scenario builders: produce labelled InjectedMessage sets (ground truth).
# These describe WHAT to inject at a given tick; the runner publishes them via
# MaliciousPublisher and the controller's decide() then scores the verdicts.
# --------------------------------------------------------------------------- #


def spoof_release(
    sender: str, recipient: str, true_release: int, delta: int, tolerance: int,
    tick: int,
) -> InjectedMessage:
    """(a) Spoof: claim ``true_release + delta``; recipient observes true.

    Expected: ``inflated`` once ``delta > tolerance``; an evasion (``ok``,
    ``expected_layer="none"``) when ``0 <= delta <= tolerance`` -- a malicious
    over-claim that hides inside the tolerance band (the sub-tolerance floor).
    A ``delta == 0`` message is benign (truthful) and labelled non-malicious.
    """
    claim = true_release + delta
    if delta <= 0:
        return InjectedMessage(
            sender=sender, recipient=recipient, release=claim,
            true_release=true_release, malicious=False,
            expected_layer="none", expected_reason="ok", tick=tick,
        )
    detectable = delta > tolerance
    return InjectedMessage(
        sender=sender, recipient=recipient, release=claim,
        true_release=true_release, malicious=True,
        expected_layer="conservation" if detectable else "none",
        expected_reason="inflated" if detectable else "ok",
        tick=tick,
    )


def faulty_release(
    sender: str, recipient: str, true_release: int, drop_fraction: float,
    tolerance: int, tick: int,
) -> InjectedMessage:
    """(b) Faulty sensor: recipient under-observes by ``drop_fraction``.

    The sender claims the truth; the recipient's detector drops a fraction of
    arrivals, so ``observed = round(true_release * (1 - drop_fraction))`` and the
    residual is ``claim - observed = true_release - observed`` (positive). NOTE
    the conservation sign convention: ``delta = claimed - observed``; an
    under-observing recipient makes ``delta > 0``. The threat-model labels this
    family ``under_reported`` (observation-side fault), but the as-built
    ``evaluate`` keys on the SIGN of delta: claim high vs observation low yields
    ``inflated``. We therefore label the *observation* shortfall and let the
    runner record the actual reason; the ground-truth ``malicious`` flag (a fault
    that should be flagged) is what P/R/F1 score against. For a TOTAL outage
    (``drop_fraction >= 1.0``) the observation is absent -> ``missing_observation``.

    To match the threat-model's intended ``under_reported`` semantics (observed
    >> claimed), the runner uses :func:`faulty_underreport` where the *sender*
    under-claims; this function models the detector-drop variant.
    """
    observed = round(true_release * (1.0 - drop_fraction))
    residual = true_release - observed  # claim(true) - observed
    if drop_fraction >= 1.0:
        expected_reason = "missing_observation"
        detectable = True
    else:
        detectable = residual > tolerance
        expected_reason = "inflated" if detectable else "ok"
    return InjectedMessage(
        sender=sender, recipient=recipient, release=true_release,
        true_release=observed,  # what the recipient will actually observe
        malicious=drop_fraction > 0.0,
        expected_layer="conservation" if detectable else "none",
        expected_reason=expected_reason if detectable else "ok",
        tick=tick,
    )


def faulty_underreport(
    sender: str, recipient: str, true_release: int, drop_fraction: float,
    tolerance: int, tick: int,
) -> InjectedMessage:
    """(b') Faulty sensor, SENDER-side under-claim -> classic ``under_reported``.

    The sender's own counter drops a fraction (claims less than it truly
    released); the recipient observes the truth. Then ``observed > claimed`` so
    ``delta < -tolerance`` -> ``under_reported`` (the exact threat-model verdict
    for a faulty/under-reporting sensor). A total sender outage (no claim, but
    the recipient sees traffic) -> ``missing_claim``.
    """
    claim = round(true_release * (1.0 - drop_fraction))
    residual = claim - true_release  # negative when under-claiming
    if drop_fraction >= 1.0:
        # Sender publishes nothing; recipient still observes -> missing_claim.
        return InjectedMessage(
            sender=sender, recipient=recipient, release=0,
            true_release=true_release, malicious=True,
            expected_layer="conservation", expected_reason="missing_claim",
            tick=tick,
        )
    detectable = residual < -tolerance
    return InjectedMessage(
        sender=sender, recipient=recipient, release=claim,
        true_release=true_release, malicious=drop_fraction > 0.0,
        expected_layer="conservation" if detectable else "none",
        expected_reason="under_reported" if detectable else "ok",
        tick=tick,
    )


def sybil_unregistered(
    recipient: str, release: int, tick: int
) -> InjectedMessage:
    """(c1) Outsider Sybil: a never-registered identity injects inflow.

    Auth rejects with ``unknown_sender`` (the fabricated id is a topological
    neighbour so it gets past the topology check to the membership check).
    """
    return InjectedMessage(
        sender=MaliciousPublisher._neighbour_of(recipient), recipient=recipient,
        release=release, true_release=0, malicious=True,
        expected_layer="auth", expected_reason="unknown_sender", tick=tick,
    )


def sybil_not_neighbour(
    sender: str, recipient: str, release: int, tick: int
) -> InjectedMessage:
    """(c1') Non-neighbour injection: a node not adjacent to ``recipient``.

    Auth rejects with ``not_neighbour`` (topology check fails first).
    """
    return InjectedMessage(
        sender=sender, recipient=recipient, release=release, true_release=0,
        malicious=True, expected_layer="auth", expected_reason="not_neighbour",
        tick=tick,
    )


def sybil_revoked(
    sender: str, recipient: str, release: int, tick: int
) -> InjectedMessage:
    """(c1'') Revoked-but-still-signing: was approved, membership withdrawn.

    Auth rejects with ``revoked``. The runner must call ``registry.revoke`` on
    ``sender`` before inbox.
    """
    return InjectedMessage(
        sender=sender, recipient=recipient, release=release, true_release=0,
        malicious=True, expected_layer="auth", expected_reason="revoked",
        tick=tick,
    )


def sybil_tampered(
    sender: str, recipient: str, release: int, tick: int
) -> InjectedMessage:
    """(c1''') Impersonation / tamper: signed by the wrong key.

    Auth rejects with ``bad_signature``.
    """
    return InjectedMessage(
        sender=sender, recipient=recipient, release=release, true_release=0,
        malicious=True, expected_layer="auth", expected_reason="bad_signature",
        tick=tick,
    )


def collusion_lockstep(
    sender: str, recipient: str, true_release: int, phantom: int, tolerance: int,
    tick: int,
) -> InjectedMessage:
    """(c3) Coordinated collusion: claim and observation inflated in lockstep.

    The attacker controls BOTH the approved sender (inflates its claim by
    ``phantom``) AND the approved recipient (inflates its observation by
    ``phantom`` too), so ``delta = claimed - observed`` stays within tolerance.
    Auth passes (both approved, valid signatures, fresh tick); conservation
    returns ``ok`` (``|delta| <= tolerance``). This is malicious BUT undetectable
    -- the Xiao2026 residual limit. Ground truth: ``malicious=True``,
    ``expected_layer="none"``. The runner inflates the observed inflow to match.
    """
    return InjectedMessage(
        sender=sender, recipient=recipient, release=true_release + phantom,
        true_release=true_release + phantom,  # observation moves in lockstep
        malicious=True, expected_layer="none", expected_reason="ok", tick=tick,
    )


def relabel_observed(msg: InjectedMessage, observed: int) -> InjectedMessage:
    """Return a copy with ``true_release`` (the observed count) overridden.

    Convenience used by the runner to set what the recipient observes
    independently of the claim, without mutating the original record.
    """
    return replace(msg, true_release=observed)


def make_rng(seed: int) -> random.Random:
    """A seeded, isolated RNG so faulty-sensor sweeps are fully reproducible."""
    return random.Random(seed)
