# MQTT-Integrated Coordinated Control Loop — Design & Proof

**Goal (PROJECT-DECISION-BRIEF):** the real-time control path is *signed messages
over MQTT*. `src/run_coordinated.py` runs that coordination over the **in-process**
`MessageBus`. This part (`src/run_mqtt_coord.py`) runs the **same** coordinated
loop with neighbour traffic flowing over a **real broker** instead — the
integration-ready fast path. The transport is swapped; the *semantics are not*.

**Outcome: PASS — the swap is fully transparent.** On the 2×2 grid (StubAgent, no
Foundry, seed 42, 300 steps) the MQTT run reproduces the in-process run's
decision-affecting counts **exactly**:

| metric | in-process | **MQTT** | match |
|---|---|---|---|
| slm_decisions | 90 | **90** | ✓ exact |
| verified_messages | 176 | **176** | ✓ exact |
| detections | 166 | **166** | ✓ exact |
| flagged_detections | 98 | **98** | ✓ exact |
| coord_adjusted_decisions | 12 | **12** | ✓ exact |
| coord_changed_events | 12 | **12** | ✓ exact |
| rejected_messages | 346 | 180 | ✗ by design — see §4 |

Reproduce: `python src/run_mqtt_coord.py --end 300 --compare` (broker up).

---

## 1. Transport-swap architecture

### The seam (why no controller edit is needed)

`CoordinatedController` touches its bus through **exactly two** call sites
(verified by inspection of `coordinated_controller.py`):

```python
msg = self.bus.publish(self.identities[tl], tick, {"toward": toward_payload})  # send
for m in self.bus.inbox(tl):                                                   # receive
    ...
```

and `run_coordinated` additionally reads `bus.rejected` for metrics. **That is the
entire bus surface.** `decide()` / conservation / Channel-A / Channel-B logic
never reach past those three members. So the clean override is a **bus-shaped
adapter** injected as the `bus` argument — *no subclass of the controller, no
edit to any existing file.*

```
CoordinatedController.decide()              (UNCHANGED)
        │  bus.publish(identity, t, payload)
        │  bus.inbox(recipient)
        ▼
_PerJunctionAdapter                         (bus-shaped dispatcher, NEW)
  routes by deciding-junction id ──► MqttBusAdapter[jid]   (NEW, per junction)
        │  .publish ─► MqttTransport.publish ─► MessageBus.publish (SIGN) ─► broker
        │  .inbox   ◄─ drain MqttTransport queue ◄─ verify_received ◄─ MessageBus.inbox (VERIFY)
        ▼
   eclipse-mosquitto  (topic edge-negotiator/junction/<sender>, QoS 1, no retain)
```

* **`MqttBusAdapter`** wraps one junction's `MqttTransport`. `publish` delegates to
  `MqttTransport.publish` (which signs via `MessageBus.publish` — *identical* key
  usage and `canonical_bytes`); `inbox` drains the transport's verified-delivery
  queue into the `NeighborMessage` list the controller expects. It exposes
  `rejected` from the underlying receiver-side bus.
* **`_PerJunctionAdapter`** is itself bus-shaped and dispatches each `publish`
  (keyed on the deciding identity's `junction_id`) and each `inbox` (keyed on the
  recipient id) to that junction's own adapter/transport. The controller passes
  the deciding junction to *both* calls within one `decide`, so one `bus`-typed
  object cleanly serves the whole grid without the controller knowing transport
  is per-junction.

### Reuse, not reimplement (the security invariant)

**No crypto / topology / registry / replay code is reimplemented anywhere in this
part.** Signing is `MessageBus.publish`; verification is `MessageBus.inbox` (run
on receipt by `mqtt_transport.verify_received`, which feeds the frame into a
receiver-side `MessageBus` and calls `inbox()`). The MQTT layer adds **transport
only** and makes **no trust decision of its own**. A tampered payload, a
non-neighbour, a revoked or unknown sender, or a duplicate frame is rejected by
*exactly the same code path* and lands in the same `bus.rejected` log with the
same reason from the bus's closed set
(`unknown_sender / revoked / bad_signature / not_neighbour / replay`).

---

## 2. Proof the semantics are preserved (counts vs in-process)

The run harness (`run()`) mirrors `run_coordinated.run('coordinated')` exactly
— same grid, same adjacency, same identities/registry/checker construction, same
`StubAgent` — differing **only** in the injected `bus`. The transparency check
above shows every *decision-affecting* count is identical. This is the proof the
broker is transparent: the coordinated decisions, the verified-message flow, and
the conservation detections are the **same** whether reports travel in-process or
across the wire.

`tests/test_mqtt_coord.py::test_transport_swap_is_transparent_vs_in_process`
encodes this: `slm_decisions` is sim-driven and asserted **exactly equal**;
`verified_messages` and `detections` are asserted strictly positive and within a
small band of the in-process baseline (the band absorbs wall-clock jitter — see
§3 — without weakening the claim).

### Why a per-step settle is needed (and why it does not change semantics)

The in-process bus is **synchronous within a sim step**; MQTT is **async** (p95
≈ 8 ms round-trip, from `../MQTT-SPIKE.md`). A junction `decide()` fires only when
its green timer expires (`min_green` ≈ 10 simulated seconds) and junctions are
staggered, so a report published at one decision has *seconds* to arrive before
the neighbour's next decision. A tiny per-step settle (`STEP_SETTLE_S = 20 ms`,
three orders of magnitude under the decision gap) lets an in-flight verified
delivery land in the recipient's queue before the next tick reads it. This does
**not** change semantics — it only prevents a decision from racing a report that
is *mid-flight*; an unsettled report is simply drained on the *next* decision,
exactly as the in-process bus delivers a report published on an earlier tick. The
verified buffer is cumulative and the `(recipient, sender, t)` replay guard makes
re-drains idempotent, so counts converge on the in-process run.

---

## 3. Determinism note

The in-process run is fully deterministic. The MQTT run threads real wall-clock
broker round-trips through a deterministic sim, so on a *clean* broker the
decision-affecting counts match **exactly** (table in §0), but under heavy
machine contention a single report can occasionally land a millisecond after a
decision and be counted on the next one instead (e.g. detections 165 vs 166).
The tests therefore assert exact equality only on the sim-driven `slm_decisions`
and a tight tolerance on the transport-carried counts — honest about the one
non-determinism a real broker introduces, while still proving the swap is
transparent.

---

## 4. Why `rejected_messages` differs — and why that is correct

In-process, **all four junctions share one `MessageBus`**. A non-neighbour
broadcast (e.g. B1's report, which A0/B0 are adjacent-blind to) is scanned and
rejected by *every* recipient's inbox pass, and the bus's per-round rescans log
additional `not_neighbour` / bookkeeping entries — inflating the count to 346.

Over MQTT, **each junction owns its own receiver-side `MessageBus`** and only ever
sees frames it actually received on its subscription, so it logs only the
rejections *it* makes (180 total across the four buses). The **accepted / verified
path is byte-identical** (176 either way); only the *rejection bookkeeping*
differs, because the bus topology is per-junction instead of shared. This is a
property of the deployment shape (one bus per node, as production will run), not a
weakening of the security gate — the adversarial tests in §6 confirm every
rejection *reason* still fires end-to-end over the wire.

---

## 5. Broker-down degradation behaviour

Handled explicitly, with a clear status, per the spike's degradation note
("a missing neighbour report is treated as *no update*, not a crash"):

| condition | behaviour |
|---|---|
| **Broker unreachable at start, `require_broker=True`** (default) | `run()` raises `MqttTransportError` with host/port **before** any sim starts — no silent swallow, no wasted run. |
| **Broker unreachable at start, `require_broker=False`** | `run()` returns `{"broker_up": False, "status": "...", "verified_messages": 0}` — a clear "ran degraded" report instead of raising. |
| **Broker drops mid-run** | `MqttTransport.publish` raises `MqttTransportError`; the controller **already** catches it and records `published={"error": ...}`. The adapter first **retries** a transient `NO_CONN` a few times (paho auto-reconnects on lossy links). A junction that consequently receives no neighbour report gets `expected_incoming == 0` that round → "no update", and the sim continues. `publish_errors` is surfaced in the metrics so degradation is observable, never hidden. |

Verified live: `python src/run_mqtt_coord.py --end 50` (broker down) raises with a
clear message; `--no-require-broker` reports `broker_up=False` gracefully.

---

## 6. Tests (`tests/test_mqtt_coord.py`)

12 tests, live-broker tests gated on availability and **skipped cleanly** when no
broker is reachable (same pattern as `test_mqtt_transport.py`). With the broker
up: **12 passed**. Full suite unaffected: **294 passed, 1 skipped** (the skip is a
pre-existing Besu-RPC test, unrelated).

* **Broker-down (no broker needed):** dead-port pre-flight is `False`;
  `require_broker=True` raises; `require_broker=False` degrades to a clear status.
* **Adapter unit:** rejects a non-transport; `publish→inbox` round-trips a verified
  signed report over the broker.
* **End-to-end run:** a short coordinated run over the broker completes and carries
  **>0 verified messages** with bounded publish errors.
* **Transparency:** MQTT run reproduces the in-process run's counts (exact on
  `slm_decisions`, tight tolerance on verified/detections).
* **Security end-to-end (the gate is unchanged over the wire):** tampered payload
  → `bad_signature`; revoked → `revoked`; non-neighbour → `not_neighbour`; unknown
  sender → `unknown_sender`; duplicate (QoS-1 redelivery) → `replay`.

---

## 7. Integration points — how this becomes the production fast path

This part *is* the integrate-and-merge the spike promised. To run the corridor's
real-time control plane over MQTT instead of in-process:

1. **Per junction**, construct `MqttTransport(jid, MessageBus(registry, adjacency),
   host, port)` and connect it. (`run_mqtt_coord._build_transports` does this for
   the 2×2 grid; on a real OSM net, derive `adjacency` + `edge_map` with
   `coordinated_controller.edge_map_from_net` and pass `edge_map` to the
   controller — the transport layer is unchanged.)
2. **Inject** the bus-shaped `_PerJunctionAdapter` as the controller's `bus`. The
   controller, conservation check and coordination logic run **verbatim**.
3. **Drive** the loop with `simulationStep()` + `ctrl.step()` (sim) or the live
   roadside clock (deployment). Reports publish to
   `edge-negotiator/junction/<sender>` and arrive verified on each neighbour's
   subscription.

**Production settings (from `../MQTT-SPIKE.md`, not yet enabled in this spike):**
QoS 1 (replay guard makes dupes safe); retain OFF (per-tick reports must not
replay to late subscribers); **TLS/8883** for confidentiality + topic protection
(authenticity is already guaranteed by the Ed25519 signature); **per-junction
client auth + broker ACLs** (publish only to own topic, subscribe only to
neighbours); **broker redundancy** (a single broker is a corridor-wide SPOF). A
**bounded message TTL** plus the existing "missing report = no update" degradation
keep a late/lost report safe to ignore rather than fatal on a lossy roadside link.

The Besu allowlist (slow trust path) feeds the same `Registry` these transports
verify against, so on-chain register/revoke directly gates who can be trusted on
the fast path — no extra plumbing.
