> **SUPERSEDED HISTORICAL DE-RISK RECORD (pre-2026-05-31 pivot).** Dated lab-notebook measurements kept for the audit trail; the substrate here (Lambeth A23/A3) was DROPPED and the ledger/Besu framing DEMOTED. Current thesis: specs/001-edge-negotiator/MASTER-SPEC.md (Euston A501; self-referential coupling; CT-style accountability credited to prior art; Phi-4-mini). Numbers/terms below are historical, not current claims.

# RegistryService — control-path-safe service layer over the Besu registry

`src/registry_service.py`. This is the production "service part" that makes the
on-chain `AgentRegistry` (`contracts/AgentRegistry.sol`, driven by
`src/besu_registry.py`) **usable on the real-time control path** despite its
~1.4-2.1 s write latency. It wraps `BesuRegistry` behind an **event-sourced
in-memory cache** and an **off-loop write path**, exposing the exact membership
surface `MessageBus` (`src/message_bus.py`) already consumes from the local
`src/registry.py` Registry.

The design follows the BESU-SPIKE.md §6 de-risk playbook verbatim: *membership
checks hit a locally-cached allowlist refreshed from on-chain events, never a
synchronous `eth_call` on the control path; audit writes are batched off-loop.*

---

## 1. Why this layer exists (the latency problem)

From `results/ledger_bench.md` (measured, Besu 24.12.0 single-node dev, 1.0 s
block period):

| op | in-memory | Besu median | Besu p95 |
|---|---|---|---|
| register / revoke (write) | ~15 µs | **1.44 / 1.84 s** | 3.9 / 5.4 s |
| is_approved / public_key (read `eth_call`) | ~0.2 µs | 46 / 32 ms | 67 / 48 ms |

The control loop verifies membership **per neighbour message**. A synchronous
`eth_call` (30-50 ms) per message would couple control latency to the network;
a synchronous write (~1.4 s) on the loop would be catastrophic (~94,000x the
in-memory cost). So the service splits the two paths:

- **Reads → local cache** (microseconds, zero network).
- **Writes → background worker** (admin/async; the caller never blocks).

---

## 2. Event-sourcing design

The on-chain `AgentRegistered` / `AgentRevoked` events **are** the source of
truth and the audit log. The cache is a **fold over that event stream**:

```
start():   replay all events from block 0  ->  build {approved, known, audit_log}
refresh(): read events from next_block     ->  fold the new suffix in
```

State lives in an immutable `_CacheState` snapshot (`approved` dict, `known`
frozenset, `audit_log` tuple, `next_block`). Each refresh builds a **new**
snapshot off to the side and swaps it in with a single locked assignment, so a
concurrent control-path reader always sees a consistent view — never a
half-applied event. `next_block` advances past the highest ingested block, and
an incremental fold skips anything not strictly newer than the last applied
`(block_number, log_index)`, so re-reads never duplicate or lose events.

Cache refresh is driven two ways:

- **Explicit** `refresh()` — used by admin tooling and after a `flush()`; raises
  `RegistryServiceError` on an unreachable node (hard error, no silent stale).
- **Background poller** — when `poll_interval > 0`, a daemon thread polls and
  *degrades* on failure (marks disconnected, keeps the last cache) instead of
  raising. This is the corridor's "keep fresh automatically" mode.

### Chain abstraction (testability)

The chain sits behind a tiny `EventSource` protocol —
`is_connected` / `read_events(from_block)` / `submit_register` /
`submit_revoke`. `BesuEventSource` adapts a live `BesuRegistry` (reads translate
its `audit_log`; a best-effort backfill recovers each register's full key bytes
from the raw `AgentRegistered` logs, since `public_key()` only returns the
*currently approved* key). Unit tests inject an in-memory `FakeEventSource`, so
the entire service is exercised with no node.

---

## 3. Off-loop write path

`register()` / `revoke()`:

1. validate inputs **synchronously** (cheap; raises `ValueError`/`TypeError`),
2. enqueue the slow on-chain submission to a single background worker thread,
3. return a **`PendingWrite` handle immediately** — the control path never
   blocks on the ~1.4-2.1 s commit.

The caller takes finality only when it needs it:

- `handle.await_commit(timeout)` — blocks for this one write; **re-raises** the
  underlying error (e.g. a contract revert / `KeyError`) so a failed admin write
  is never silently lost.
- `flush(timeout)` — drains the whole queue (batch of membership changes), then
  `refresh()` reflects them in the cache.

The worker preserves submission order (FIFO), so a `register` then `revoke` of
the same id always applies in that order. A write that raises is captured on its
handle and **does not kill the worker** — the next queued write still runs.

> **Writes are ADMIN / async, not per-decision.** Registering or revoking an
> agent is a city-authority governance action that happens occasionally, not on
> every traffic-control tick. The ~2.1 s latency is therefore irrelevant to
> control cadence — it is paid off-loop by whoever asked for finality.

---

## 4. Graceful degradation semantics

`status` is one of:

| status | meaning |
|---|---|
| `connected` | last refresh succeeded and is within `stale_after` |
| `stale` | serving the cache, but the last good refresh is older than `stale_after` |
| `disconnected` | a refresh has errored; serving the **last-known** cache |

Rules:

- **Start is loud.** If the *initial* replay fails, `start()` raises
  `RegistryServiceError` — the service refuses to come up pretending the
  allowlist is empty (which would silently look like "nobody is approved", a
  security footgun).
- **Runtime is soft.** Once up, an unreachable node never crashes the corridor:
  `is_approved` / `public_key` keep answering from the last-known cache, and
  `status` flips to `disconnected` with `last_error` set. The background poller
  recovers automatically when the node returns.
- **No silent swallow.** The *explicit* `refresh()` raises on failure; only the
  background poller degrades quietly (and even then records `last_error`).
- `health()` returns a snapshot (`status`, approved/known counts, `next_block`,
  `last_refresh_age`, `last_error`, `queued_writes`) for logging or a `/health`
  probe.

---

## 5. Integration points

**Drop-in for `MessageBus`.** `MessageBus` only ever calls
`registry.public_key(sender)`, `registry.is_approved(sender)`, and iterates
`registry.audit_log` reading `action` / `junction_id`. `RegistryService`
reproduces all three from the cache, so:

```python
from besu_registry import BesuRegistry
from registry_service import BesuEventSource, RegistryService
from message_bus import MessageBus

reg = BesuRegistry.attach(RPC, CONTRACT_ADDR, ABI, ADMIN, PRIVATE_KEY)  # or .deploy(...)
svc = RegistryService(BesuEventSource(reg), poll_interval=2.0, stale_after=10.0).start()

bus = MessageBus(svc, adjacency)   # <-- service handed in place of Registry(); unchanged
```

This is exactly where today's local `Registry()` is constructed. The controller
/ runner (`src/run_coordinated.py`, `src/coordinated_controller.py`) and the
MQTT transport (`src/mqtt_transport.py`, which delegates trust checks back to a
`MessageBus`) consume the service through that same `MessageBus`, so **no
control-path code changes**.

- **Reads** (`is_approved`, `public_key`) are served from cache on the fast path
  — microseconds, control-safe.
- **Membership freshness** comes from the poller applying new on-chain events
  (block-period-bounded staleness, surfaced via `status`).
- **Admin writes** (`register`, `revoke`, `flush`, `await_commit`) are an
  off-loop governance API, never invoked per control decision.

---

## 6. Latencies (measured + expected)

| path | mechanism | latency |
|---|---|---|
| `is_approved` / `public_key` | in-memory dict lookup | ~µs (no network) — vs 32-46 ms for a raw on-chain `eth_call` |
| cache freshness lag | poller interval + block period | `poll_interval` + ~1 block (dev 1.0 s; QBFT 2 s) |
| `register` / `revoke` commit (off-loop) | mined tx via `BesuRegistry` | **~1.4-2.1 s median**, p95 up to ~5 s (per `ledger_bench.md`) — paid by `await_commit`, never on the loop |
| control-path write impact | none | writes never run on the control path |

A production QBFT network (≥4 validators, 2 s block period) lands at the top of
or just above this write band; the read path stays microseconds because it never
leaves memory. The architecture's "ledger strictly async" decision is preserved.

---

## 7. Test coverage

`tests/test_registry_service.py` — **18 fast unit tests (no node) + 1 live-gated
integration test**, all green.

Fast tests (inject `FakeEventSource`):

- cache rebuilt from a full event replay; unknown/empty/type-confused ids safe;
- revoke reflected after refresh; re-register-after-revoke with a new key;
- incremental refresh neither duplicates nor loses events;
- off-loop write returns immediately then commits; synchronous input validation;
- failed write surfaces via `await_commit` (not swallowed); batched `flush`;
  writes preserve submission order;
- graceful degradation: loud start failure, last-known cache + `disconnected` on
  drop, `stale` transition, background-poller recovery, `health()` snapshot;
- **drop-in**: real `MessageBus(service, adjacency)` delivers a neighbour
  message, and rejects revoked / unknown senders through the service.

Live integration test (`test_integration_live_besu_cache_and_offloop_write`):
deploys a real `AgentRegistry`, builds the cache from on-chain events, performs
an off-loop `register` awaited to finality, sees a `revoke` after refresh, and
runs a real `MessageBus` over the live-backed service. It **skips cleanly** when
no Besu RPC is reachable (socket probe on `EDGE_BESU_RPC`, default
`127.0.0.1:8545`) — same pattern the MQTT tests use to skip without a broker.
Verified by running it against `hyperledger/besu:24.12.0` (dev mode): passed in
~6.5 s; container torn down after.
