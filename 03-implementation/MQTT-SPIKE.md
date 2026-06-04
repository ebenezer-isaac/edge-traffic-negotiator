# MQTT Fast-Path Transport — De-Risk Spike

**Goal (from `PROJECT-DECISION-BRIEF.md`):** the real-time control path is
*signed messages over MQTT*; the Besu ledger is the *slow, async trust path*.
The shipped `MessageBus` (`edge-negotiator/src/message_bus.py`) is **in-process**.
This spike puts a **real broker** between `publish` and `inbox` behind the
**same publish/inbox semantics**, measures real pub/sub latency, and confirms
Wk3-4+ networking is an *integrate-and-merge*, not a rewrite.

**Outcome: PASS.** A signed neighbour message round-trips through a live
`eclipse-mosquitto` broker and is verified by the **identical** topology +
registry + Ed25519 + replay checks the in-process bus uses (verification is
*reused, not forked*). Measured p95 end-to-end latency is **8.2 ms** — about
**1,200x inside** the ~10 s SLM decision interval. MQTT is comfortably fast
enough for the per-decision control loop.

---

## What was built

| File | Role |
|---|---|
| `edge-negotiator/src/mqtt_transport.py` | `MqttTransport` wrapping a `MessageBus`. `publish()` signs **via the bus** (`MessageBus.publish`, reusing `identity` + `canonical_bytes`) and ships the signed `NeighborMessage` as JSON (signature base64'd) to `edge-negotiator/junction/<sender>`. On receipt a subscriber deserialises and runs `verify_received()`, which feeds the message into a receiver-side `MessageBus` and calls `MessageBus.inbox()` — **all** trust logic is the bus's own code. Broker-down raises `MqttTransportError` (no swallow). |
| `edge-negotiator/src/bench_mqtt.py` | Measures end-to-end **publish -> verified-deliver** latency (median + p95 over ≥100 msgs) and throughput, vs the in-process bus doing the *same verification work*. Refuses to write fabricated numbers if the broker is down. |
| `edge-negotiator/tests/test_mqtt_transport.py` | 16 tests over the **real broker**: round-trip verifies with payload intact; tampered payload → `bad_signature`; non-neighbour → `not_neighbour`; revoked → `revoked`; unknown sender → `unknown_sender`; QoS-1 duplicate → `replay`; dead broker raises. Skips cleanly if no broker is reachable. |
| `edge-negotiator/results/mqtt_bench.md` | Generated benchmark report (raw numbers + interpretation). |

**Design choice — reuse, don't fork.** The in-process bus was already shaped so
`publish` produces a self-authenticating message and `inbox` does *all* trust
checks on receipt. The MQTT layer therefore drives the **same** receive buffer
from a broker instead of from a local `publish`, and the **same** `inbox()`
verifies it. The broker adds transport only and makes **no** security decision.
This is what makes the guarantees provably identical (the adversarial tests
assert each rejection reason matches the in-process bus's closed set).

---

## Reproduce

From `edge-negotiator/` (venv python = `.venv/Scripts/python`):

```bash
# 1. Install the client (one-off)
.venv/Scripts/python -m pip install paho-mqtt

# 2. Stand up the broker (port 1883; pick another if busy)
docker run -d --name edge-mosquitto -p 1883:1883 eclipse-mosquitto:2 \
  sh -c "printf 'listener 1883\nallow_anonymous true\n' > /mosquitto/config/mosquitto.conf && exec mosquitto -c /mosquitto/config/mosquitto.conf"

# 3. Tests (round-trip + adversarial, over the real broker)
.venv/Scripts/python -m pytest tests/test_mqtt_transport.py -v

# 4. Benchmark (writes results/mqtt_bench.md)
.venv/Scripts/python src/bench_mqtt.py --messages 200

# 5. Tear down
docker rm -f edge-mosquitto
```

If the broker is on a non-default port, pass `--host/--port` to the bench and set
`EDGE_MQTT_HOST` / `EDGE_MQTT_PORT` for the tests.

---

## Measured numbers

`eclipse-mosquitto 2.x` in Docker, QoS 1, no retain, plaintext, anonymous,
localhost `127.0.0.1:1883`. 200 messages. Timed unit = **sign → deliver → full
verification** (topology + membership + Ed25519 + replay) — i.e. the moment the
receiver could *act* on the report. Identical unit on both backends.

| backend | median (ms) | p95 (ms) | mean (ms) | max (ms) | throughput (msg/s) |
|---|---|---|---|---|---|
| in-process (baseline) | 2.15 | 3.28 | 2.48 | 35.8 | ~450 |
| **MQTT (real broker)** | **5.93** | **8.18** | 6.29 | 52.8 | ~270 |

- The broker adds ~**3.8 ms** to the median (the round-trip); verification cost
  is byte-for-byte identical on both paths.
- Throughput is a **sequential round-trip** number (publish one, wait for its
  verified arrival, repeat) — a deliberately conservative lower bound, not a
  pipelined max.

*(Numbers are from one run on the dev machine; re-run step 4 to regenerate. The
in-process baseline's ms-scale latency is dominated by Ed25519 verify + a fresh
per-message bus allocation, not by the bus logic itself — it is the honest
"same verification work" comparator.)*

---

## Verdict — fast enough for the control loop?

**YES, with large margin.** The SLM makes a decision roughly every **10 s**
(validated upstream: Phi-4-mini drives a junction at ~10 s cadence). A
reasonable transport budget is **sub-100 ms**.

- Measured MQTT **p95 = 8.2 ms** → **~1,200x inside** the 10 s decision interval
  and **~12x under** the 100 ms transport target.
- Even the worst-case **max ≈ 53 ms** is still under the 100 ms target and a
  tiny fraction of the loop.
- **Transport is not the bottleneck.** SLM inference dominates end-to-end time by
  two-to-three orders of magnitude. Moving from in-process to a real broker does
  not threaten the control loop.

---

## Production corridor — settings the spike does NOT yet have

- **QoS 1** for reports (at-least-once). The bus's `(recipient, sender, t)`
  replay guard makes a duplicate **safe** (rejected as `replay`), so QoS 1 is
  the right trade. **Avoid QoS 2** — its 4-way handshake roughly doubles latency
  for a guarantee the application layer already provides.
- **Retain OFF** for per-tick reports. A retained report would be redelivered to
  a reconnecting subscriber and (correctly) rejected as a replay — wasted work
  and a stale-tick hazard. Retain only suits slow-changing config topics.
- **TLS (MQTTS / 8883)** with broker-cert validation. Payloads are already
  Ed25519-signed end-to-end, so TLS is for **confidentiality + metadata/topic
  protection + anti-tamper-on-the-wire**, *not* authenticity (the signature
  already guarantees that). On a roadside network the link is untrusted, so TLS
  is mandatory.
- **Per-junction client auth + broker ACLs**: each junction may PUBLISH only to
  `edge-negotiator/junction/<its-own-id>` and SUBSCRIBE only to neighbours
  (mTLS client certs preferred; username/password minimum). The spike runs
  `allow_anonymous true` — fine for a localhost measurement, not for production.
  Defence-in-depth: even without ACLs an attacker writing to another junction's
  topic is caught by the signature check, but ACLs stop the junk reaching the
  verifier and block topic-squatting / DoS.
- **Broker redundancy**: a single broker is a corridor-wide SPOF. Production
  needs a clustered/bridged broker or per-segment brokers.

---

## Biggest production-networking risk

**Broker availability and the roadside-network latency tail — not throughput.**
The clean-LAN p95 is comfortable, but a real corridor adds (a) a **single-broker
single-point-of-failure** whose loss silences all coordination, and (b) **packet
loss / tail latency on lossy cellular or mesh roadside links**, which QoS 1 turns
into retransmits + duplicates (correct, thanks to the replay guard, but it widens
p99 well beyond the LAN p95 measured here).

**Mitigations** (largely supported by the existing design): broker redundancy; a
**bounded message TTL** so a late report is dropped rather than acted on; and
treating a missing neighbour report as *"no update"* in the controller (graceful
degradation) — the topology + replay model already makes a dropped or stale
report safe to ignore rather than fatal.

---

## Integration note for Wk3-4+

Because `MqttTransport` exposes the **same publish/inbox semantics** and reuses
the bus verification verbatim, swapping the in-process bus for the MQTT transport
in the coordinated controller is an integrate-and-merge: construct an
`MqttTransport(recipient, MessageBus(registry, adjacency))` per junction, call
`publish(identity, t, payload)` to send, and `poll()` (or an `on_delivered`
callback) to receive verified reports. No crypto, topology, or replay code
changes.
