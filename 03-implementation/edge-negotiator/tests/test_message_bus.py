"""Adversarial tests for src/message_bus.py -- the security core.

The bus is the trust boundary for cross-junction coordination: it must deliver
ONLY messages from approved, adjacent peers carrying a valid signature over the
exact claimed bytes, never re-deliver a prior tick, and record a precise reason
for every drop. These tests attack each of those guarantees.

src/ is inserted on sys.path so `import message_bus` works when run as
`python -m pytest tests` from the project root.
"""
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from identity import JunctionIdentity  # noqa: E402
from message_bus import MessageBus, NeighborMessage, canonical_bytes  # noqa: E402
from registry import Registry  # noqa: E402

# Topology from the project brief (2x2 grid).
ADJACENCY = {
    "A0": ["A1", "B0"],
    "A1": ["A0", "B1"],
    "B0": ["A0", "B1"],
    "B1": ["A1", "B0"],
}


def _fresh():
    """Registry + identities for A0, A1, B0, B1, all registered & approved."""
    registry = Registry()
    idents = {jid: JunctionIdentity(jid) for jid in ("A0", "A1", "B0", "B1")}
    for jid, ident in idents.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    return registry, idents, bus


def _reasons(bus):
    return [r["reason"] for r in bus.rejected]


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #

def test_happy_neighbour_delivered_payload_intact():
    registry, idents, bus = _fresh()
    payload = {"phase": 2, "predicted_outflow": 17, "queue": [3, 0, 1]}
    bus.publish(idents["A1"], t=5, payload=payload)

    inbox = bus.inbox("A0")
    assert len(inbox) == 1
    msg = inbox[0]
    assert msg.sender == "A1"
    assert msg.t == 5
    assert msg.payload == payload          # payload intact
    assert bus.rejected == []              # nothing dropped


def test_publish_returns_signed_message():
    registry, idents, bus = _fresh()
    msg = bus.publish(idents["A1"], t=1, payload={"x": 1})
    assert isinstance(msg, NeighborMessage)
    assert msg.sender == "A1"
    assert len(msg.signature) == 64        # Ed25519 signature length


# --------------------------------------------------------------------------- #
# Non-neighbour
# --------------------------------------------------------------------------- #

def test_non_neighbour_not_delivered():
    # B1 is approved and registered, but B1 is NOT adjacent to A0.
    registry, idents, bus = _fresh()
    bus.publish(idents["B1"], t=3, payload={"phase": 1})

    inbox = bus.inbox("A0")
    assert inbox == []
    assert _reasons(bus) == ["not_neighbour"]
    assert bus.rejected[0]["sender"] == "B1"
    assert bus.rejected[0]["recipient"] == "A0"


# --------------------------------------------------------------------------- #
# Tamper: original signature, mutated payload
# --------------------------------------------------------------------------- #

def test_tampered_payload_rejected_bad_signature():
    registry, idents, bus = _fresh()
    good = bus.publish(idents["A1"], t=7, payload={"phase": 2})
    # Forge a message: keep A1's real signature, but mutate the payload.
    forged = NeighborMessage(
        sender="A1", t=7, payload={"phase": 9}, signature=good.signature
    )
    # Inject the forged message directly into the bus buffer (attacker on wire).
    bus._published = [forged]

    inbox = bus.inbox("A0")
    assert inbox == []
    assert _reasons(bus) == ["bad_signature"]


def test_tampered_tick_rejected_bad_signature():
    registry, idents, bus = _fresh()
    good = bus.publish(idents["A1"], t=7, payload={"phase": 2})
    forged = NeighborMessage(
        sender="A1", t=8, payload={"phase": 2}, signature=good.signature
    )
    bus._published = [forged]
    assert bus.inbox("A0") == []
    assert _reasons(bus) == ["bad_signature"]


# --------------------------------------------------------------------------- #
# Revoked
# --------------------------------------------------------------------------- #

def test_revoked_sender_rejected():
    registry, idents, bus = _fresh()
    registry.revoke("A1")
    bus.publish(idents["A1"], t=2, payload={"phase": 0})

    inbox = bus.inbox("A0")
    assert inbox == []
    assert _reasons(bus) == ["revoked"]


# --------------------------------------------------------------------------- #
# Unknown sender (never registered)
# --------------------------------------------------------------------------- #

def test_unknown_sender_rejected():
    # Build a registry where A1 is NEVER registered, but is still adjacent to A0.
    registry = Registry()
    registry.register("A0", JunctionIdentity("A0").public_key)
    a1 = JunctionIdentity("A1")  # never registered
    bus = MessageBus(registry, ADJACENCY)

    bus.publish(a1, t=4, payload={"phase": 1})
    inbox = bus.inbox("A0")
    assert inbox == []
    assert _reasons(bus) == ["unknown_sender"]


# --------------------------------------------------------------------------- #
# Replay
# --------------------------------------------------------------------------- #

def test_replay_not_redelivered():
    registry, idents, bus = _fresh()
    bus.publish(idents["A1"], t=6, payload={"phase": 3})

    first = bus.inbox("A0")
    assert len(first) == 1
    assert bus.rejected == []

    second = bus.inbox("A0")          # same (recipient, sender, t)
    assert second == []
    assert _reasons(bus) == ["replay"]


def test_replay_is_per_recipient():
    # A1 publishes once; both A0 and B1 are neighbours of A1 and each may
    # consume it exactly once. Replay is keyed on (recipient, sender, t).
    registry, idents, bus = _fresh()
    bus.publish(idents["A1"], t=9, payload={"phase": 1})

    assert len(bus.inbox("A0")) == 1
    assert len(bus.inbox("B1")) == 1   # different recipient -> still delivered
    assert len(bus.inbox("A0")) == 0   # A0 replay
    assert _reasons(bus) == ["replay"]


# --------------------------------------------------------------------------- #
# Impersonation: attacker signs claiming to be A1 with a different key
# --------------------------------------------------------------------------- #

def test_impersonation_rejected_bad_signature():
    registry, idents, bus = _fresh()
    attacker = JunctionIdentity("attacker")  # different keypair
    t = 11
    payload = {"phase": 2}
    # Attacker forges sender="A1" but signs with its OWN key.
    forged_sig = attacker.sign(canonical_bytes("A1", t, payload))
    forged = NeighborMessage(
        sender="A1", t=t, payload=payload, signature=forged_sig
    )
    bus._published = [forged]

    inbox = bus.inbox("A0")
    assert inbox == []
    # Signature does not match A1's *registered* public key.
    assert _reasons(bus) == ["bad_signature"]


# --------------------------------------------------------------------------- #
# Filtering by tick
# --------------------------------------------------------------------------- #

def test_inbox_filters_by_tick():
    registry, idents, bus = _fresh()
    bus.publish(idents["A1"], t=1, payload={"p": 1})
    bus.publish(idents["A1"], t=2, payload={"p": 2})

    only_t2 = bus.inbox("A0", t=2)
    assert len(only_t2) == 1
    assert only_t2[0].t == 2
    # t=1 was never considered for this call, so no rejection recorded.
    assert bus.rejected == []


# --------------------------------------------------------------------------- #
# Input validation at boundaries
# --------------------------------------------------------------------------- #

def test_publish_rejects_non_dict_payload():
    registry, idents, bus = _fresh()
    with pytest.raises(TypeError):
        bus.publish(idents["A1"], t=1, payload=["not", "a", "dict"])


def test_publish_rejects_bool_tick():
    # bool is a subclass of int; t must be a genuine int.
    registry, idents, bus = _fresh()
    with pytest.raises(TypeError):
        bus.publish(idents["A1"], t=True, payload={"p": 1})


def test_published_payload_frozen_against_later_mutation():
    # Mutating the caller's dict after publish must not change what was signed.
    registry, idents, bus = _fresh()
    payload = {"phase": 2}
    bus.publish(idents["A1"], t=1, payload=payload)
    payload["phase"] = 99              # external mutation after publish

    inbox = bus.inbox("A0")
    assert len(inbox) == 1
    assert inbox[0].payload == {"phase": 2}   # signed snapshot, not 99


def test_rejected_log_is_copy():
    registry, idents, bus = _fresh()
    bus.publish(idents["B1"], t=1, payload={"p": 1})  # not_neighbour for A0
    bus.inbox("A0")
    snapshot = bus.rejected
    snapshot.append({"bogus": True})
    assert len(bus.rejected) == 1      # internal log unaffected
