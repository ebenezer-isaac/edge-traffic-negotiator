"""Tests for src/registry_service.py — the control-path-safe registry facade.

Two layers:

  * **Fast unit tests (no live node).** The chain is behind the small
    ``EventSource`` protocol, so a ``FakeEventSource`` drives the cache from an
    in-memory event list. These prove: cache rebuild from a full event replay,
    revoke reflected in the cache, off-loop writes return a pending handle and
    resolve, batched flush, graceful degradation (stale / disconnected while
    serving the last-known cache), and **drop-in compatibility** — a real
    ``MessageBus(registry_service, adjacency)`` delivers and rejects messages
    using the service exactly as it does with the local ``Registry``.

  * **One live-gated integration test.** It stands up a real ``BesuRegistry``
    via ``BesuEventSource`` and is skipped cleanly when no Besu RPC is reachable
    (same pattern as the MQTT tests skip without a broker). Point it at a node
    with EDGE_BESU_RPC (default http://127.0.0.1:8545).

src/ is inserted on sys.path so ``import registry_service`` works under
``python -m pytest tests`` from the project root, matching the other tests.
"""
import os
import socket
import sys
import threading
import time
from urllib.parse import urlparse

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from identity import JunctionIdentity  # noqa: E402
from message_bus import MessageBus  # noqa: E402
from registry_service import (  # noqa: E402
    BesuEventSource,
    PendingWrite,
    RegistryEvent,
    RegistryService,
    RegistryServiceError,
    STATUS_CONNECTED,
    STATUS_DISCONNECTED,
    STATUS_STALE,
)

ADJACENCY = {
    "A0": ["A1", "B0"],
    "A1": ["A0", "B1"],
    "B0": ["A0", "B1"],
    "B1": ["A1", "B0"],
}


# --------------------------------------------------------------------------- #
# Fake event source: an in-memory chain for fast, deterministic unit tests.
# --------------------------------------------------------------------------- #


class FakeEventSource:
    """In-memory ``EventSource``: writes append events, reads return them.

    Each submit advances a synthetic block number so events have a total order,
    just like the chain. ``connected`` and ``fail_*`` flags let tests force
    transport failures to exercise graceful degradation. ``submit_delay`` lets a
    test observe that a write is genuinely off-loop (the caller returns before
    the slow submission finishes).
    """

    def __init__(self) -> None:
        self._events: list[RegistryEvent] = []
        self._block = 0
        self.connected = True
        self.fail_read = False
        self.fail_write = False
        self.submit_delay = 0.0
        self._lock = threading.Lock()

    # -- protocol --
    def is_connected(self) -> bool:
        return self.connected

    def read_events(self, from_block: int) -> list[RegistryEvent]:
        if self.fail_read or not self.connected:
            raise ConnectionError("fake node unreachable")
        with self._lock:
            return [e for e in self._events if e.block_number >= from_block]

    def submit_register(self, junction_id: str, public_key: bytes) -> None:
        self._submit(RegistryEvent("register", junction_id, bytes(public_key), 0, 0))

    def submit_revoke(self, junction_id: str) -> None:
        # mirror the contract: revoking a never-registered id is an error.
        if not any(
            e.action == "register" and e.junction_id == junction_id
            for e in self._events
        ):
            raise KeyError(junction_id)
        self._submit(RegistryEvent("revoke", junction_id, None, 0, 0))

    # -- helpers --
    def _submit(self, ev: RegistryEvent) -> None:
        if self.submit_delay:
            time.sleep(self.submit_delay)
        if self.fail_write or not self.connected:
            raise ConnectionError("fake node unreachable")
        with self._lock:
            self._block += 1
            self._events.append(
                RegistryEvent(
                    action=ev.action,
                    junction_id=ev.junction_id,
                    public_key=ev.public_key,
                    block_number=self._block,
                    log_index=0,
                    tx_hash=f"0x{self._block:064x}",
                )
            )

    def seed_register(self, junction_id: str, public_key: bytes) -> None:
        """Pre-load a register without going through the off-loop path."""
        self.submit_register(junction_id, public_key)


def _identities(*jids):
    return {jid: JunctionIdentity(jid) for jid in jids}


# --------------------------------------------------------------------------- #
# Cache rebuild from a full event replay (the event-sourcing core).
# --------------------------------------------------------------------------- #


def test_cache_rebuilt_from_event_replay_on_start():
    src = FakeEventSource()
    idents = _identities("A0", "A1", "B0")
    for jid, ident in idents.items():
        src.seed_register(jid, ident.public_key)

    svc = RegistryService(src).start()
    try:
        for jid, ident in idents.items():
            assert svc.is_approved(jid) is True
            assert svc.public_key(jid) == ident.public_key
        assert svc.status == STATUS_CONNECTED
        # audit_log carries the MessageBus-read fields in chronological order.
        actions = [(e["action"], e["junction_id"]) for e in svc.audit_log]
        assert actions == [("register", "A0"), ("register", "A1"), ("register", "B0")]
        assert all(e["seq"] == i for i, e in enumerate(svc.audit_log))
    finally:
        svc.close()


def test_unknown_and_empty_ids_are_not_approved():
    svc = RegistryService(FakeEventSource()).start()
    try:
        assert svc.is_approved("nope") is False
        assert svc.public_key("nope") is None
        assert svc.is_approved("") is False
        assert svc.public_key("") is None
        # type-confusion inputs must not crash the control path.
        assert svc.is_approved(None) is False  # type: ignore[arg-type]
        assert svc.public_key(123) is None  # type: ignore[arg-type]
    finally:
        svc.close()


def test_revoke_reflected_in_cache_after_refresh():
    src = FakeEventSource()
    ident = JunctionIdentity("A1")
    src.seed_register("A1", ident.public_key)

    svc = RegistryService(src).start()
    try:
        assert svc.is_approved("A1") is True

        handle = svc.revoke("A1")
        assert isinstance(handle, PendingWrite)
        handle.await_commit(timeout=5.0)
        # The cache only changes when we ingest the new event.
        svc.refresh()

        assert svc.is_approved("A1") is False
        assert svc.public_key("A1") is None
        # The revoke is in the audit trail; A1 is still "known" (ever-registered).
        actions = [(e["action"], e["junction_id"]) for e in svc.audit_log]
        assert ("revoke", "A1") in actions
    finally:
        svc.close()


def test_reregister_after_revoke_restores_with_new_key():
    src = FakeEventSource()
    old = JunctionIdentity("A1")
    new = JunctionIdentity("A1")
    assert old.public_key != new.public_key

    svc = RegistryService(src).start()
    try:
        svc.register("A1", old.public_key).await_commit(5.0)
        svc.refresh()
        assert svc.public_key("A1") == old.public_key

        svc.revoke("A1").await_commit(5.0)
        svc.refresh()
        assert svc.is_approved("A1") is False

        svc.register("A1", new.public_key).await_commit(5.0)
        svc.refresh()
        assert svc.is_approved("A1") is True
        assert svc.public_key("A1") == new.public_key
    finally:
        svc.close()


def test_incremental_refresh_does_not_duplicate_or_lose_events():
    src = FakeEventSource()
    a = JunctionIdentity("A0")
    src.seed_register("A0", a.public_key)
    svc = RegistryService(src).start()
    try:
        assert len(svc.audit_log) == 1
        b = JunctionIdentity("B0")
        svc.register("B0", b.public_key).await_commit(5.0)
        svc.refresh()
        svc.refresh()  # second refresh must be a no-op (no duplicates)
        actions = [(e["action"], e["junction_id"]) for e in svc.audit_log]
        assert actions == [("register", "A0"), ("register", "B0")]
        assert all(e["seq"] == i for i, e in enumerate(svc.audit_log))
    finally:
        svc.close()


# --------------------------------------------------------------------------- #
# Off-loop writes: register/revoke return a handle and resolve asynchronously.
# --------------------------------------------------------------------------- #


def test_register_returns_immediately_then_commits_off_loop():
    src = FakeEventSource()
    src.submit_delay = 0.4  # a slow "mined" write
    a = JunctionIdentity("A0")
    svc = RegistryService(src).start()
    try:
        t0 = time.monotonic()
        handle = svc.register("A0", a.public_key)
        # The control-path caller returns FAST — well before the slow submit.
        assert (time.monotonic() - t0) < 0.2
        assert handle.done is False

        assert handle.await_commit(timeout=5.0) is True
        assert handle.committed is True
        assert handle.error is None
    finally:
        svc.close()


def test_write_validation_is_synchronous_and_explicit():
    svc = RegistryService(FakeEventSource()).start()
    try:
        with pytest.raises(ValueError):
            svc.register("", JunctionIdentity("A0").public_key)
        with pytest.raises(TypeError):
            svc.register("A0", "not-bytes")  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            svc.revoke("")
    finally:
        svc.close()


def test_failed_write_surfaces_via_await_commit_not_swallowed():
    src = FakeEventSource()
    svc = RegistryService(src).start()
    try:
        # revoke of a never-registered id -> KeyError from the source, which the
        # handle must re-raise (the worker must not swallow it).
        handle = svc.revoke("GHOST")
        with pytest.raises(KeyError):
            handle.await_commit(timeout=5.0)
        assert handle.committed is False
        assert isinstance(handle.error, KeyError)
    finally:
        svc.close()


def test_flush_batches_multiple_writes_to_finality():
    src = FakeEventSource()
    src.submit_delay = 0.1
    idents = _identities("A0", "A1", "B0", "B1")
    svc = RegistryService(src).start()
    try:
        handles = [svc.register(jid, ident.public_key) for jid, ident in idents.items()]
        # None need have committed yet (they're queued off-loop).
        svc.flush(timeout=10.0)
        assert all(h.committed for h in handles)
        svc.refresh()
        for jid in idents:
            assert svc.is_approved(jid)
    finally:
        svc.close()


def test_writes_preserve_submission_order():
    src = FakeEventSource()
    a = JunctionIdentity("A0")
    svc = RegistryService(src).start()
    try:
        svc.register("A0", a.public_key)
        svc.revoke("A0")  # must apply AFTER the register
        svc.flush(timeout=10.0)
        svc.refresh()
        # register then revoke => not approved, both in the log in order.
        assert svc.is_approved("A0") is False
        actions = [(e["action"], e["junction_id"]) for e in svc.audit_log]
        assert actions == [("register", "A0"), ("revoke", "A0")]
    finally:
        svc.close()


# --------------------------------------------------------------------------- #
# Graceful degradation: serve last-known cache, surface stale/disconnected.
# --------------------------------------------------------------------------- #


def test_start_fails_loudly_if_initial_replay_unreachable():
    src = FakeEventSource()
    src.connected = False
    with pytest.raises(RegistryServiceError):
        RegistryService(src).start()


def test_node_unreachable_serves_last_known_cache_and_reports_disconnected():
    src = FakeEventSource()
    a = JunctionIdentity("A0")
    src.seed_register("A0", a.public_key)
    svc = RegistryService(src).start()
    try:
        assert svc.is_approved("A0") is True

        # Node drops. The control path keeps answering from the cache.
        src.connected = False
        assert svc.is_approved("A0") is True  # last-known cache, no crash
        assert svc.public_key("A0") == a.public_key

        # An EXPLICIT refresh raises (no silent swallow) and flips status.
        with pytest.raises(RegistryServiceError):
            svc.refresh()
        assert svc.status == STATUS_DISCONNECTED
        assert svc.last_error is not None
        # Cache still serves the last good allowlist.
        assert svc.is_approved("A0") is True
    finally:
        svc.close()


def test_status_goes_stale_when_refresh_is_old():
    src = FakeEventSource()
    fake_now = [1000.0]
    svc = RegistryService(src, stale_after=5.0, clock=lambda: fake_now[0]).start()
    try:
        assert svc.status == STATUS_CONNECTED
        fake_now[0] += 6.0  # no refresh for longer than stale_after
        assert svc.status == STATUS_STALE
        # A successful refresh clears staleness.
        svc.refresh()
        assert svc.status == STATUS_CONNECTED
    finally:
        svc.close()


def test_background_poller_recovers_after_reconnect():
    src = FakeEventSource()
    a = JunctionIdentity("A0")
    src.seed_register("A0", a.public_key)
    svc = RegistryService(src, poll_interval=0.05).start()
    try:
        # Drop the node; the poller degrades but does not crash.
        src.fail_read = True
        deadline = time.monotonic() + 2.0
        while svc.status != STATUS_DISCONNECTED and time.monotonic() < deadline:
            time.sleep(0.02)
        assert svc.status == STATUS_DISCONNECTED

        # Add an event and bring the node back; the poller must pick it up.
        src.fail_read = False
        b = JunctionIdentity("B0")
        src.seed_register("B0", b.public_key)
        deadline = time.monotonic() + 2.0
        while not svc.is_approved("B0") and time.monotonic() < deadline:
            time.sleep(0.02)
        assert svc.is_approved("B0") is True
        assert svc.status == STATUS_CONNECTED
    finally:
        svc.close()


def test_health_snapshot_reports_counts_and_status():
    src = FakeEventSource()
    a = JunctionIdentity("A0")
    src.seed_register("A0", a.public_key)
    svc = RegistryService(src).start()
    try:
        h = svc.health()
        assert h["status"] == STATUS_CONNECTED
        assert h["approved_count"] == 1
        assert h["known_count"] == 1
        assert h["last_error"] is None
    finally:
        svc.close()


# --------------------------------------------------------------------------- #
# Drop-in compatibility: MessageBus uses the service exactly like Registry.
# --------------------------------------------------------------------------- #


def test_messagebus_delivers_with_registry_service_as_drop_in():
    src = FakeEventSource()
    idents = _identities("A0", "A1", "B0", "B1")
    for jid, ident in idents.items():
        src.seed_register(jid, ident.public_key)
    svc = RegistryService(src).start()
    try:
        bus = MessageBus(svc, ADJACENCY)  # service handed in place of Registry
        payload = {"phase": 2, "queue": [3, 0, 1]}
        bus.publish(idents["A1"], t=5, payload=payload)  # A1 is A0's neighbour

        inbox = bus.inbox("A0")
        assert len(inbox) == 1
        assert inbox[0].sender == "A1"
        assert inbox[0].payload == payload
    finally:
        svc.close()


def test_messagebus_rejects_revoked_sender_through_service():
    src = FakeEventSource()
    idents = _identities("A0", "A1", "B0", "B1")
    for jid, ident in idents.items():
        src.seed_register(jid, ident.public_key)
    svc = RegistryService(src).start()
    try:
        bus = MessageBus(svc, ADJACENCY)
        bus.publish(idents["A1"], t=7, payload={"phase": 1})

        # Revoke A1 on-chain, refresh the cache, then deliver: must be rejected.
        svc.revoke("A1").await_commit(5.0)
        svc.refresh()
        assert svc.is_approved("A1") is False

        delivered = bus.inbox("A0")
        assert delivered == []
        reasons = [r["reason"] for r in bus.rejected if r["sender"] == "A1"]
        assert "revoked" in reasons
    finally:
        svc.close()


def test_messagebus_rejects_unknown_sender_through_service():
    src = FakeEventSource()
    # Only A0 registered; GHOST is an adjacency neighbour but never registered.
    a0 = JunctionIdentity("A0")
    src.seed_register("A0", a0.public_key)
    svc = RegistryService(src).start()
    try:
        adj = {**ADJACENCY, "A0": ["A1", "B0", "GHOST"]}
        bus = MessageBus(svc, adj)
        ghost = JunctionIdentity("GHOST")
        bus.publish(ghost, t=3, payload={"phase": 1})

        assert bus.inbox("A0") == []
        reasons = [r["reason"] for r in bus.rejected if r["sender"] == "GHOST"]
        assert "unknown_sender" in reasons
    finally:
        svc.close()


# --------------------------------------------------------------------------- #
# Live-gated integration test (real Besu via BesuEventSource).
# Skipped cleanly when no node is reachable, like the MQTT tests skip w/o broker.
# --------------------------------------------------------------------------- #

_RPC = os.environ.get("EDGE_BESU_RPC", "http://127.0.0.1:8545")
# Well-known Besu dev account (throwaway dev chain only — never a real key).
_DEV_ADDR = "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73"
_DEV_KEY = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"


def _besu_up(rpc: str, timeout: float = 1.0) -> bool:
    parsed = urlparse(rpc)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8545
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.mark.skipif(
    not _besu_up(_RPC),
    reason=f"no Besu RPC reachable at {_RPC} (start hyperledger/besu:24.12.0 dev node)",
)
def test_integration_live_besu_cache_and_offloop_write():
    from besu_registry import BesuRegistry

    reg = BesuRegistry.deploy(_RPC, _DEV_ADDR, _DEV_KEY)
    a = JunctionIdentity("LIVE_A")
    b = JunctionIdentity("LIVE_B")
    # Seed one agent directly so the initial replay has something to build from.
    reg.register("LIVE_A", a.public_key)

    src = BesuEventSource(reg)
    svc = RegistryService(src, stale_after=30.0).start()
    try:
        # Cache built from the real on-chain event.
        assert svc.is_approved("LIVE_A") is True
        assert svc.public_key("LIVE_A") == a.public_key
        assert svc.status == STATUS_CONNECTED

        # Off-loop write of a second agent, awaited to finality (~1-2 s).
        handle = svc.register("LIVE_B", b.public_key)
        assert handle.await_commit(timeout=30.0) is True
        svc.refresh()
        assert svc.is_approved("LIVE_B") is True
        assert svc.public_key("LIVE_B") == b.public_key

        # Revoke reflected after refresh.
        svc.revoke("LIVE_A").await_commit(timeout=30.0)
        svc.refresh()
        assert svc.is_approved("LIVE_A") is False

        # Drop-in: a real MessageBus uses the live-backed service unchanged.
        bus = MessageBus(svc, {"LIVE_A": ["LIVE_B"], "LIVE_B": ["LIVE_A"]})
        bus.publish(b, t=1, payload={"phase": 1})  # B -> A; B is approved
        assert len(bus.inbox("LIVE_A")) == 1
    finally:
        svc.close()
