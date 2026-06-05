"""Control-path-safe service layer over the on-chain Besu agent registry.

`RegistryService` makes the on-chain `AgentRegistry` (see `src/besu_registry.py`)
**usable on the real-time control path** despite its ~1.4-2.1 s write latency. It
is the production "service part" the brief calls for: a thin, event-sourced
facade that gives `MessageBus` (`src/message_bus.py`) the *same* membership
surface as the local `src/registry.py` Registry — `is_approved`, `public_key`
and an iterable `audit_log` — but answers them from an **in-memory cache** in
microseconds, never from a synchronous `eth_call` and never blocking on
consensus.

Why this layer exists (BESU-SPIKE.md §6 / results/ledger_bench.md)
------------------------------------------------------------------
The single biggest integration risk is *coupling membership checks or audit
writes to consensus latency*. Measured: a write commit is ~1.4-2.1 s median
(p95 up to ~5 s); a read `eth_call` is ~30-50 ms; the in-memory equivalent is
~15 microseconds. So:

  * **Reads (control path) MUST be local.** `is_approved` / `public_key` answer
    from a cache built by replaying `AgentRegistered` / `AgentRevoked` events and
    kept fresh by polling for new events. They never touch the network.
  * **Writes (admin path) MUST be off-loop.** `register` / `revoke` submit the
    transaction on a background worker and return a `PendingWrite` handle
    immediately. Callers that need finality call `handle.await_commit()` (or the
    service-level `flush()`); nothing on the control path ever awaits a receipt.

Graceful degradation
---------------------
If the node becomes unreachable the service keeps serving the **last-known
cache** and flips its `status` to ``stale`` / ``disconnected`` so the corridor
keeps running on the most recent allowlist instead of crashing. Failures are
surfaced explicitly (status + ``last_error`` + raising on an *explicit*
``refresh()``), never silently swallowed.

Chain abstraction (testability)
-------------------------------
The chain is hidden behind the small :class:`EventSource` protocol
(``read_events`` / ``submit_register`` / ``submit_revoke`` / ``is_connected``).
``BesuEventSource`` adapts a live :class:`BesuRegistry`; unit tests inject an
in-memory fake, so cache rebuild, revoke propagation, stale-mode and MessageBus
drop-in compatibility are all exercised with no live node. One integration test
drives the real adapter and is skipped cleanly when no Besu is up.
"""
from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, runtime_checkable

# ---------------------------------------------------------------------------- #
# Status + errors
# ---------------------------------------------------------------------------- #

STATUS_CONNECTED = "connected"      # last refresh succeeded, within freshness window
STATUS_STALE = "stale"              # serving cache, but it has not refreshed recently
STATUS_DISCONNECTED = "disconnected"  # node unreachable / refresh erroring


class RegistryServiceError(RuntimeError):
    """Raised for explicit service-level failures (e.g. refresh() on a dead node)."""


# ---------------------------------------------------------------------------- #
# Event + write-handle value objects (immutable)
# ---------------------------------------------------------------------------- #

# Canonical event shape replayed into the cache. ``action`` is "register" or
# "revoke"; ``public_key`` is the DER bytes for a register (None for revoke);
# ``block_number`` / ``log_index`` give a total order. This is exactly what a
# BesuRegistry audit_log entry carries (minus the on-chain provenance we add
# back when we expose audit_log), so the adapter is a 1:1 translation.
@dataclass(frozen=True)
class RegistryEvent:
    action: str
    junction_id: str
    public_key: bytes | None
    block_number: int
    log_index: int
    tx_hash: str | None = None


@runtime_checkable
class EventSource(Protocol):
    """The minimal chain surface RegistryService needs.

    A real implementation (``BesuEventSource``) talks to Besu; a fake one drives
    an in-memory list. All four methods are allowed to raise on a transport
    failure — RegistryService catches those at the boundary and degrades.
    """

    def is_connected(self) -> bool:
        ...

    def read_events(self, from_block: int) -> list[RegistryEvent]:
        """Return events with ``block_number >= from_block``, totally ordered."""
        ...

    def submit_register(self, junction_id: str, public_key: bytes) -> None:
        """Submit (and, for Besu, mine) a register tx. May block ~seconds."""
        ...

    def submit_revoke(self, junction_id: str) -> None:
        """Submit (and, for Besu, mine) a revoke tx. May block ~seconds."""
        ...


class PendingWrite:
    """Handle for an off-loop register/revoke submission.

    ``register()`` / ``revoke()`` return one of these immediately (the control
    path never blocks). The background worker runs the submission; the caller
    calls :meth:`await_commit` only when it actually needs finality (admin
    tooling, tests). ``await_commit`` re-raises whatever the submission raised so
    a failed admin write is never silently lost.
    """

    __slots__ = ("action", "junction_id", "_done", "_error", "_committed")

    def __init__(self, action: str, junction_id: str) -> None:
        self.action = action
        self.junction_id = junction_id
        self._done = threading.Event()
        self._error: BaseException | None = None
        self._committed = False

    def _resolve(self, error: BaseException | None) -> None:
        self._error = error
        self._committed = error is None
        self._done.set()

    @property
    def done(self) -> bool:
        return self._done.is_set()

    @property
    def committed(self) -> bool:
        """True once the tx has been accepted on-chain without error."""
        return self._committed

    @property
    def error(self) -> BaseException | None:
        return self._error

    def await_commit(self, timeout: float | None = None) -> bool:
        """Block until the write resolves; return True on success.

        Raises the underlying error if the submission failed, or
        :class:`TimeoutError` if it did not resolve within ``timeout`` seconds.
        """
        if not self._done.wait(timeout):
            raise TimeoutError(
                f"{self.action}({self.junction_id!r}) did not commit within "
                f"{timeout}s"
            )
        if self._error is not None:
            raise self._error
        return True


# A unit-of-work the worker thread executes. Kept private.
@dataclass
class _WriteJob:
    fn: Callable[[], None]
    handle: PendingWrite


# ---------------------------------------------------------------------------- #
# Besu adapter
# ---------------------------------------------------------------------------- #

class BesuEventSource:
    """Adapts a live :class:`BesuRegistry` to the :class:`EventSource` protocol.

    Reads translate the registry's ``audit_log`` (rebuilt from on-chain events)
    into ordered :class:`RegistryEvent`s. Writes call straight through to the
    registry's (blocking, mined) ``register`` / ``revoke``.
    """

    def __init__(self, besu_registry: Any) -> None:
        self._reg = besu_registry

    def is_connected(self) -> bool:
        try:
            # BesuRegistry holds a connected web3; a cheap probe is reading the
            # block number. We tolerate any failure as "not connected".
            return bool(self._reg._w3.is_connected())  # type: ignore[attr-defined]
        except Exception:
            return False

    def read_events(self, from_block: int) -> list[RegistryEvent]:
        events: list[RegistryEvent] = []
        for entry in self._reg.audit_log:  # ordered by (block, log_index)
            if entry["block_number"] < from_block:
                continue
            action = entry["action"]
            pk: bytes | None = None
            if action == "register":
                # audit_log carries only the sha256 fingerprint, not the key
                # bytes; re-read the current key for a register of the currently
                # approved junction. For superseded/older registers we still need
                # *some* key to seed the cache, so fall back to fetching it from
                # the registry's contract event directly below.
                pk = self._reg.public_key(entry["junction_id"])
            events.append(
                RegistryEvent(
                    action=action,
                    junction_id=entry["junction_id"],
                    public_key=pk,
                    block_number=entry["block_number"],
                    log_index=entry["log_index"],
                    tx_hash=entry.get("tx_hash"),
                )
            )
        return self._with_event_keys(events)

    def _with_event_keys(self, events: list[RegistryEvent]) -> list[RegistryEvent]:
        """Backfill register key bytes from the raw contract logs.

        ``public_key()`` only returns the *currently approved* key, so a register
        that was later revoked or superseded would otherwise carry ``None``. We
        read the raw ``AgentRegistered`` logs (which embed the full key) and map
        them by (block_number, log_index) to recover the exact key each event
        registered. Best-effort: if the raw read fails we keep what we have.
        """
        registers = [e for e in events if e.action == "register" and e.public_key is None]
        if not registers:
            return events
        try:
            raw = self._reg._contract.events.AgentRegistered().get_logs(from_block=0)  # type: ignore[attr-defined]
        except Exception:
            return events
        by_pos = {
            (ev["blockNumber"], ev["logIndex"]): bytes(ev["args"]["publicKey"])
            for ev in raw
        }
        patched: list[RegistryEvent] = []
        for e in events:
            if e.action == "register" and e.public_key is None:
                key = by_pos.get((e.block_number, e.log_index))
                if key is not None:
                    e = RegistryEvent(
                        action=e.action,
                        junction_id=e.junction_id,
                        public_key=key,
                        block_number=e.block_number,
                        log_index=e.log_index,
                        tx_hash=e.tx_hash,
                    )
            patched.append(e)
        return patched

    def submit_register(self, junction_id: str, public_key: bytes) -> None:
        self._reg.register(junction_id, public_key)

    def submit_revoke(self, junction_id: str) -> None:
        self._reg.revoke(junction_id)


# ---------------------------------------------------------------------------- #
# The service
# ---------------------------------------------------------------------------- #

@dataclass
class _CacheState:
    """Immutable snapshot of the replayed allowlist + audit log.

    Swapped atomically (one assignment) so a concurrent reader always sees a
    consistent view — never a half-applied event.
    """

    approved: dict[str, bytes] = field(default_factory=dict)
    known: frozenset[str] = field(default_factory=frozenset)
    audit_log: tuple[dict, ...] = ()
    next_block: int = 0  # lowest block we have NOT yet ingested


class RegistryService:
    """Control-path-safe, event-sourced facade over the on-chain registry.

    Drop-in for `src/registry.py` from `MessageBus`'s point of view: it exposes
    ``is_approved`` / ``public_key`` / ``audit_log`` answered from an in-memory
    cache, so ``MessageBus(registry_service, adjacency)`` works unchanged.

    Construct with any :class:`EventSource`. The cache is built once on
    :meth:`start` (full replay) and refreshed by polling — either explicitly
    (:meth:`refresh`) or by a background thread when ``poll_interval`` > 0.
    """

    def __init__(
        self,
        source: EventSource,
        *,
        poll_interval: float = 0.0,
        stale_after: float = 5.0,
        auto_flush: bool = True,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(source, EventSource):
            raise TypeError("source must implement the EventSource protocol")
        self._source = source
        self._poll_interval = max(0.0, float(poll_interval))
        self._stale_after = max(0.0, float(stale_after))
        self._auto_flush = bool(auto_flush)
        self._clock = clock

        self._state = _CacheState()
        self._state_lock = threading.Lock()

        self._last_refresh: float | None = None
        self._last_error: str | None = None
        self._connected = False

        # -- background machinery (created lazily on start) --
        self._stop = threading.Event()
        self._poll_thread: threading.Thread | None = None

        self._write_lock = threading.Lock()
        self._write_queue: list[_WriteJob] = []
        self._write_cv = threading.Condition(self._write_lock)
        self._worker_thread: threading.Thread | None = None
        self._started = False

    # -- lifecycle ----------------------------------------------------------- #

    def start(self) -> "RegistryService":
        """Build the cache from a full event replay and start background work.

        Raises :class:`RegistryServiceError` if the initial replay fails (we
        refuse to come up pretending to have an allowlist we never loaded).
        """
        if self._started:
            return self
        self._started = True

        # Initial full replay must succeed — coming up with an empty cache that
        # silently looks like "nobody is approved" would be a security footgun.
        try:
            self._refresh_locked(full=True)
        except Exception as exc:
            self._started = False
            raise RegistryServiceError(
                f"initial registry replay failed: {exc}"
            ) from exc

        # Off-loop write worker (always on — writes must never block the caller).
        self._worker_thread = threading.Thread(
            target=self._worker_loop, name="registry-write-worker", daemon=True
        )
        self._worker_thread.start()

        # Background poller (optional — explicit refresh() also works).
        if self._poll_interval > 0:
            self._poll_thread = threading.Thread(
                target=self._poll_loop, name="registry-poller", daemon=True
            )
            self._poll_thread.start()
        return self

    def close(self) -> None:
        """Stop background threads. Idempotent; safe to call without start()."""
        self._stop.set()
        with self._write_cv:
            self._write_cv.notify_all()
        for thread in (self._poll_thread, self._worker_thread):
            if thread is not None and thread.is_alive():
                thread.join(timeout=5.0)
        self._poll_thread = None
        self._worker_thread = None
        self._started = False

    def __enter__(self) -> "RegistryService":
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- control-path reads (cache only; never touch the network) ------------ #

    def is_approved(self, junction_id: str) -> bool:
        """True iff ``junction_id`` is currently approved. Microsecond, no I/O."""
        if not isinstance(junction_id, str) or not junction_id:
            return False
        return junction_id in self._state.approved

    def public_key(self, junction_id: str) -> bytes | None:
        """Current approved DER public key for ``junction_id``, else None."""
        if not isinstance(junction_id, str) or not junction_id:
            return None
        return self._state.approved.get(junction_id)

    @property
    def audit_log(self) -> list[dict]:
        """Chronological audit log (cache view), drop-in for Registry.audit_log.

        Each entry carries ``seq`` / ``action`` / ``junction_id`` /
        ``pubkey_sha256`` (the fields MessageBus reads) plus on-chain provenance.
        Returns a shallow copy so callers cannot mutate the service's view.
        """
        return [dict(e) for e in self._state.audit_log]

    # -- off-loop writes (admin/async; NEVER per control decision) ----------- #

    def register(self, junction_id: str, public_key: bytes) -> PendingWrite:
        """Submit a register OFF the control loop; return a pending handle.

        Validates inputs synchronously (cheap), then enqueues the ~1.4-2.1 s
        on-chain write to the background worker and returns immediately. Call
        ``handle.await_commit()`` when you need finality. This is an ADMIN
        operation — it must not be issued per traffic-control decision.
        """
        if not isinstance(junction_id, str) or not junction_id:
            raise ValueError("junction_id must be a non-empty string")
        if not isinstance(public_key, (bytes, bytearray)):
            raise TypeError("public_key must be bytes (canonical DER encoding)")
        key = bytes(public_key)
        return self._enqueue(
            "register", junction_id, lambda: self._source.submit_register(junction_id, key)
        )

    def revoke(self, junction_id: str) -> PendingWrite:
        """Submit a revoke OFF the control loop; return a pending handle."""
        if not isinstance(junction_id, str) or not junction_id:
            raise ValueError("junction_id must be a non-empty string")
        return self._enqueue(
            "revoke", junction_id, lambda: self._source.submit_revoke(junction_id)
        )

    def flush(self, timeout: float | None = None) -> None:
        """Block until every queued write has resolved (admin convenience).

        Useful after a batch of register/revoke calls when the operator wants to
        confirm the allowlist is committed before refreshing the cache. Raises
        :class:`TimeoutError` if the queue does not drain in time. After flush a
        :meth:`refresh` reflects the new on-chain state in the cache.
        """
        deadline = None if timeout is None else self._clock() + timeout
        while True:
            with self._write_lock:
                pending = [job.handle for job in self._write_queue]
                in_flight = self._in_flight
            handles = pending + ([in_flight] if in_flight is not None else [])
            if not handles:
                return
            for handle in handles:
                remaining = None
                if deadline is not None:
                    remaining = deadline - self._clock()
                    if remaining <= 0:
                        raise TimeoutError("flush timed out before queue drained")
                handle.await_commit(remaining)

    # -- explicit cache refresh ---------------------------------------------- #

    def refresh(self) -> None:
        """Poll the source for new events and apply them to the cache.

        Raises :class:`RegistryServiceError` if the source is unreachable — this
        is the *explicit* path, so the caller gets a hard error rather than a
        silent stale cache. The background poller uses the degrade-not-raise
        variant instead.
        """
        try:
            self._refresh_locked(full=False)
        except Exception as exc:
            self._mark_disconnected(str(exc))
            raise RegistryServiceError(f"registry refresh failed: {exc}") from exc

    # -- status / degradation ------------------------------------------------ #

    @property
    def status(self) -> str:
        """One of ``connected`` / ``stale`` / ``disconnected``.

        ``disconnected`` once a refresh has errored (serving last-known cache);
        ``stale`` when the last good refresh is older than ``stale_after``;
        ``connected`` otherwise.
        """
        if not self._connected:
            return STATUS_DISCONNECTED
        if self._last_refresh is None:
            return STATUS_DISCONNECTED
        if self._stale_after > 0 and (self._clock() - self._last_refresh) > self._stale_after:
            return STATUS_STALE
        return STATUS_CONNECTED

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def last_refresh_age(self) -> float | None:
        """Seconds since the last successful refresh, or None if never."""
        if self._last_refresh is None:
            return None
        return self._clock() - self._last_refresh

    def health(self) -> dict:
        """Snapshot of operational state (for logging / a /health endpoint)."""
        return {
            "status": self.status,
            "approved_count": len(self._state.approved),
            "known_count": len(self._state.known),
            "next_block": self._state.next_block,
            "last_refresh_age": self.last_refresh_age,
            "last_error": self._last_error,
            "queued_writes": len(self._write_queue),
        }

    # -- internals: refresh / replay ----------------------------------------- #

    def _refresh_locked(self, *, full: bool) -> None:
        """Read events from the source and fold them into a new cache snapshot.

        A *full* refresh replays from block 0 (used on start). An incremental
        refresh reads from ``next_block`` and appends. Either way the new state
        is built off to the side and swapped in with a single assignment, so a
        concurrent reader never observes a partial update.
        """
        if full:
            base = _CacheState()
        else:
            base = self._state

        new_events = self._source.read_events(base.next_block)

        approved = dict(base.approved)
        known = set(base.known)
        audit = list(base.audit_log)
        # next_block advances past the highest block we have actually ingested,
        # so an incremental read never re-ingests an already-applied event but
        # still re-reads the *current* highest block (events can share a block).
        next_block = base.next_block
        seq = len(audit)

        for ev in new_events:
            # Guard against the source handing back an already-applied event on
            # an incremental read (e.g. same block re-read): skip anything not
            # strictly newer than what we have by (block, log_index).
            if not full and audit:
                last = audit[-1]
                if (ev.block_number, ev.log_index) <= (
                    last["block_number"],
                    last["log_index"],
                ):
                    continue

            if ev.action == "register":
                if ev.public_key is None:
                    # A register with no recoverable key is unusable; record it
                    # in the audit trail but do not approve a keyless agent.
                    pubkey_sha256 = None
                else:
                    approved[ev.junction_id] = ev.public_key
                    pubkey_sha256 = hashlib.sha256(ev.public_key).hexdigest()
                known.add(ev.junction_id)
            elif ev.action == "revoke":
                approved.pop(ev.junction_id, None)
                pubkey_sha256 = None
            else:  # pragma: no cover - defensive; sources only emit the two
                raise RegistryServiceError(f"unknown event action: {ev.action!r}")

            audit.append(
                {
                    "seq": seq,
                    "action": ev.action,
                    "junction_id": ev.junction_id,
                    "pubkey_sha256": pubkey_sha256,
                    "block_number": ev.block_number,
                    "log_index": ev.log_index,
                    "tx_hash": ev.tx_hash,
                }
            )
            seq += 1
            next_block = max(next_block, ev.block_number + 1)

        new_state = _CacheState(
            approved=approved,
            known=frozenset(known),
            audit_log=tuple(audit),
            next_block=next_block,
        )
        with self._state_lock:
            self._state = new_state
        self._mark_connected()

    def _mark_connected(self) -> None:
        self._connected = True
        self._last_error = None
        self._last_refresh = self._clock()

    def _mark_disconnected(self, error: str) -> None:
        self._connected = False
        self._last_error = error

    # -- internals: background poller ---------------------------------------- #

    def _poll_loop(self) -> None:
        while not self._stop.wait(self._poll_interval):
            try:
                self._refresh_locked(full=False)
            except Exception as exc:  # degrade, do not crash the poller
                self._mark_disconnected(str(exc))

    # -- internals: off-loop write worker ------------------------------------ #

    _in_flight: PendingWrite | None = None

    def _enqueue(
        self, action: str, junction_id: str, fn: Callable[[], None]
    ) -> PendingWrite:
        handle = PendingWrite(action, junction_id)
        if not self._auto_flush or self._worker_thread is None:
            # No worker (service not started, or auto_flush disabled): run the
            # submission inline so the write still happens and resolves. This
            # keeps the API total — a caller never gets a handle that never
            # resolves — at the cost of blocking THIS call (acceptable for the
            # not-started / explicit-sync path; the control path always starts
            # the service and gets the async worker).
            self._run_job(_WriteJob(fn=fn, handle=handle))
            return handle
        with self._write_cv:
            self._write_queue = [*self._write_queue, _WriteJob(fn=fn, handle=handle)]
            self._write_cv.notify()
        return handle

    def _worker_loop(self) -> None:
        while True:
            with self._write_cv:
                while not self._write_queue and not self._stop.is_set():
                    self._write_cv.wait()
                if self._stop.is_set() and not self._write_queue:
                    return
                job = self._write_queue[0]
                self._write_queue = self._write_queue[1:]
                self._in_flight = job.handle
            self._run_job(job)
            with self._write_cv:
                self._in_flight = None

    @staticmethod
    def _run_job(job: _WriteJob) -> None:
        try:
            job.fn()
            job.handle._resolve(None)
        except BaseException as exc:  # never let a write error kill the worker
            job.handle._resolve(exc)
