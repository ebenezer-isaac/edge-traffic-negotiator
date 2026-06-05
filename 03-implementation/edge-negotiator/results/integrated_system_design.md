# Integrated System — Design (The Edge Negotiator end-to-end assembly)

**Modules:** `src/system.py` (orchestrator) · `src/run_system.py` (CLI) ·
**Tests:** `tests/test_system.py` (38 cases) ·
**Brief reference:** the centerpiece that ASSEMBLES every separately-tested part
into one runnable pipeline so final integration into the canonical project is
trivial.

This is the integration proof. It does **not** re-implement any subsystem — it
composes their PUBLIC APIs behind one immutable `SystemConfig` with explicit,
swappable backend choices, and wires the audit log at the documented integration
point (`results/audit_log_design.md` §7). The default config runs the whole
assembly in CI with **no Docker, no Foundry, no SUMO**.

---

## 1. What the integrated system runs end-to-end

```
                          ┌──────────────────────────────────────────────────┐
                          │              IntegratedSystem(SystemConfig)       │
                          └──────────────────────────────────────────────────┘
                                                │ run()
              ┌─────────────────────────────────┴───────────────────────────────┐
              │ requires_sumo?                                                    │
       no ────┘ (default)                                              yes ───────┘ (grid/lambeth/mqtt/slm)
       _run_fake()                                                     _run_sumo()
              │                                                                   │
   ┌──────────┴───────────┐                                       ┌───────────────┴───────────────┐
   │ deterministic         │                                      │ TraCI + SUMO microsimulation   │
   │ in-memory TraCI conn   │                                      │ (real grid2x2 / lambeth net)   │
   │ (no SUMO)              │                                      │                                │
   └──────────┬───────────┘                                       └───────────────┬───────────────┘
              │                                                                    │
              ▼                  ── identical composition below ──                 ▼
     ┌─────────────────────────────────────────────────────────────────────────────────────┐
     │ JunctionIdentity ×N  ──register──►  Registry | RegistryService(Besu)                  │
     │        │                                   │  (audit_log mirrored)                    │
     │        │ public keys (DER)                 ▼                                           │
     │        └──────────────►  MessageBus | MqttBusAdapter  ◄── adjacency / edge_map         │
     │                                  │  publish / inbox (signed, verified)                 │
     │                                  ▼                                                     │
     │              CoordinatedController(StubAgent | SLMAgent)                               │
     │                 │ decide(): Channel-A (SLM note) + Channel-B (coord term)              │
     │                 │ publishes signed "toward", reads verified inbox,                     │
     │                 │ reconciles claims vs observation → ConservationChecker               │
     │                 ▼                                                                      │
     │           ctrl.events[]   ── _drain_audit (THE SEAM) ──►  AuditLog                     │
     │           ctrl.detections[]                              hash-chain + Ed25519 sig       │
     │                                                          + Merkle anchor (Besu bridge)  │
     │                                                                                        │
     │  MaliciousPublisher(attacks.py) ── injects spoof/fault/sybil during the run ──►        │
     └─────────────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
     SystemResult { traffic, coordination, audit(verify_chain + merkle_root +
                    inclusion_proof), attack_outcomes, backends }
```

**Verified end-to-end (this assembly):**

| Backend combination | Run path | Status |
|---|---|---|
| inprocess / memory / stub / grid2x2 / audit-on (**DEFAULT**) | fake-conn (no SUMO) | **CI-verified** (the default test fixture) |
| + injected spoof / under-report / not-neighbour / revoked / bad-signature | fake-conn | **CI-verified** (each scored against the right detector layer) |
| inprocess / memory / stub / **grid2x2** / audit-on | **live SUMO** | **verified live** (real tripinfo; test runs when SUMO present) |
| inprocess / memory / stub / **lambeth** (9 TLS) / audit-on | **live SUMO** via `edge_map_from_net` | **verified live** (real net; ran manually — verified_messages>0, chain valid) |
| **mqtt** transport | live SUMO + broker | **wired + live-gated** (skips cleanly without broker) |
| **besu** registry | live SUMO + node | **wired + live-gated** (skips cleanly without node) |
| **slm** agent | live SUMO + Foundry | **wired + live-gated** (opt-in; needs Foundry Local) |

---

## 2. Config matrix (the swappable choices)

`SystemConfig` is a frozen dataclass; every field is validated in `__post_init__`.

| Field | Values | Default | Backend |
|---|---|---|---|
| `transport` | `inprocess` / `mqtt` | `inprocess` | `MessageBus` / `run_mqtt_coord.MqttBusAdapter` |
| `registry`  | `memory` / `besu` | `memory` | `Registry` / `registry_service.RegistryService` |
| `agent`     | `stub` / `slm` | `stub` | `coordinated_controller.StubAgent` / `slm_agent.SLMAgent` |
| `network`   | `grid2x2` / `lambeth` | `grid2x2` | string-convention / `edge_map_from_net` |
| `audit`     | `True` / `False` | `True` | `audit_log.AuditLog` |
| `attacks`   | tuple of `AttackSpec` | `()` | `attacks.MaliciousPublisher` + injectors |

Derived: `requires_sumo` is True iff `use_sumo` **or** `transport=="mqtt"` **or**
`network=="lambeth"` (these only run under microsimulation). `is_default` is True
iff the config has no live dependency at all (the CI-able combination).

**`AttackSpec`** (`kind:sender:recipient[:release[:observed[:tick[:signer]]]]`):
`spoof`, `under_report` (→ conservation), `not_neighbour`, `revoked`,
`bad_signature` (→ auth). Each reuses an `attacks.py` transform verbatim.

---

## 3. Audit-log integration (the documented point + the seam)

The brief requires: *when audit is on, every decision is appended + signed to an
`AuditLog`, registry changes are mirrored into the same chain, and at run end
`verify_chain()==True` with a Merkle root.* This is wired as:

1. **Registry mirror** (`_mirror_registry`, brief §7.2 option 1): every
   `register`/`revoke` event from the chosen registry backend is appended to the
   audit log tagged `kind="registry"` and signed by the affected junction's
   identity — so identity/registry changes share the **same** tamper-evident
   chain as decisions. (The registry's own `seq` field is renamed `registry_seq`
   because `seq` is a reserved `AuditLog` envelope key.)

2. **Per-decision append** (`_drain_audit`): after each control step, every new
   entry in the controller's public `ctrl.events[]` is appended tagged
   `kind="decision"` and **signed by the deciding junction** (`event["tls"]`),
   giving non-repudiation per decision. The event dict the controller already
   produces (`tls, halting, slm_phase, …, detections`) is exactly what
   `AuditLog.append` validates — it passes unchanged.

3. **Run-end proof** (`_audit_bundle`): `verify_chain()`, a `merkle_root(0, n)`
   over the whole batch, and a **sample inclusion proof** for the last entry
   (`inclusion_proof` + module-level `verify_inclusion`) — proving a specific
   decision is in the anchored batch from only the on-chain root.

### The composition seam (honest report)

`audit_log_design.md` §7.1 specifies the hook as a **one-line addition inside
`CoordinatedController.decide()`**:

```python
self.events.append(event)
self.audit.append(event, issuer=self.identities.get(tl))   # <-- documented hook
```

We may **not** edit `coordinated_controller.py` (it is owned elsewhere). So the
integrated system mirrors the controller's public `.events` list into the
`AuditLog` from the orchestrator after each control step instead. This composes
**transparently** — the produced record is byte-identical to what the in-file
hook would produce — with one named difference: the append happens one control
step later (still long before the run ends and the chain/root are produced).
This is the single seam discovered; it is a *deferral*, not a workaround, and is
removed by the one-line promotion above when this assembly is folded into the
canonical controller. Everything else composed with no seam.

---

## 4. What composed transparently vs. needed a seam

| Part | Composition | Notes |
|---|---|---|
| `JunctionIdentity` / `verify` | transparent | used as-is for signing decisions + registry events |
| `Registry` / `RegistryService` | transparent | both expose `is_approved`/`public_key`/`audit_log`; drop-in for the bus and for the mirror |
| `MessageBus` / `MqttBusAdapter` | transparent | controller's `bus` slot; the adapter is a true drop-in (`run_mqtt_coord`) |
| `ConservationChecker` | transparent | driven via the controller's own reconciliation |
| `CoordinatedController` | transparent (read-only) | constructed with all collaborators; `edge_map` passed for lambeth |
| `StubAgent` / `SLMAgent` | transparent | agent slot; SLM is deferred-imported (Foundry-gated) |
| `attacks.MaliciousPublisher` | transparent | injectors reused verbatim; `AttackSpec` is a thin scheduling wrapper |
| `metrics.parse_tripinfo` / `summary` | transparent | consumes the real SUMO tripinfo (`--write-unfinished`) |
| `AuditLog` | **seam (deferral)** | mirror `.events` from the orchestrator instead of the in-`decide()` hook (see §3) |

Two minor adaptation details (not seams, just boundary care):
- `seq` collision → carried as `registry_seq` in the mirrored registry event.
- attack scoring keys on `(recipient, sender, tick)` to ignore the benign
  self-echo replay the bus logs on a clean run (a documented `run_attacks` quirk).

---

## 5. How to run each backend

```bash
VENV=.venv/Scripts/python

# DEFAULT — CI-able, no live dependency. Prints + (optionally) saves the bundle.
$VENV src/run_system.py
$VENV src/run_system.py --out results/run.json

# Inject attacks (repeatable): kind:sender:recipient[:release[:observed[:tick[:signer]]]]
$VENV src/run_system.py --attack spoof:A1:A0:99:0:2
$VENV src/run_system.py --attack bad_signature:A1:A0:40:0:1:B0 --attack revoked:A1:A0:40:0:3

# Audit off (pipeline still runs; bundle reports {"enabled": false})
$VENV src/run_system.py --no-audit

# LIVE: SUMO microsimulation on the grid → real tripinfo metrics
$VENV src/run_system.py --sumo --network grid2x2 --end 300

# LIVE: SUMO on the REAL Lambeth spine (9 TLS) via edge_map_from_net
$VENV src/run_system.py --sumo --network lambeth --end 600

# LIVE: MQTT transport over a running eclipse-mosquitto broker
docker run -p 1883:1883 eclipse-mosquitto:2     # in another shell
$VENV src/run_system.py --transport mqtt --end 300

# LIVE: Besu registry over a running node
docker run -p 8545:8545 hyperledger/besu:24.12.0 ...   # in another shell
$VENV src/run_system.py --registry besu --sumo --end 300

# LIVE: real SLM (Phi-4-mini via Foundry Local)
foundry model run phi-4-mini                     # in another shell
$VENV src/run_system.py --agent slm --sumo --end 300
```

Tests:
```bash
$VENV -m pytest tests/test_system.py -q     # 38 passed, 2 skipped (mqtt+besu gated)
$VENV -m pytest -q                          # full suite: 308 passed, 27 skipped, 0 failed
```

---

## 6. Default-config result bundle (key numbers, reproducible)

`IntegratedSystem(SystemConfig()).run()` (inprocess/memory/stub/grid2x2/audit-on,
40 decision rounds):

```
traffic:      completed = 40 (decision rounds; microsimulation=False)
coordination: decisions=40  verified_messages=40  rejected_messages=79
              detections=40  flagged_detections=0  coord_adjusted_decisions=0
audit:        enabled=True  entries=44 (40 decision + 4 registry)
              verify_chain = True
              merkle_root  = 64-hex (deterministic per seed)
              inclusion_proof_valid = True (sample = last entry, branch_len 6)
attack_outcomes: []   (clean run — no spurious flags)
```

With `--attack spoof:A1:A0:99:0:2` the bundle additionally yields
`flagged_detections >= 1` and
`attack_outcomes = [{kind: spoof, detected: True, reason: "inflated",
captured_in_audit: True}]` — the flagged detection is **also** in the signed,
hash-chained audit record, and `verify_chain` stays True.

Live SUMO grid (`--sumo --end 150`) instead yields real survivorship-robust
metrics from `metrics.py` (e.g. `completed≈33`, `mean_network_delay≈63.9 s`,
`completion_rate≈0.22`) with the same audit guarantees.

**`verify_chain` result: `True`** in every default, attacked, audit-on,
fake-conn, and live-SUMO run exercised.

---

## 7. The "integrate later" checklist (temp-workspace → canonical project)

This assembly lives in the de-risk temp workspace. To promote it:

1. **Promote the audit hook in-file (removes the seam).** In the canonical
   `CoordinatedController.__init__`, add `self.audit = AuditLog()` next to
   `self.detections = []`; in `decide()`, after `self.events.append(event)`, add
   `self.audit.append({"kind": "decision", **event}, issuer=self.identities.get(tl))`.
   Then `IntegratedSystem._drain_audit` becomes a no-op (delete it and read
   `ctrl.audit` directly). This is the single one-line in-file change.

2. **Registry-event mirror at source.** Optionally mirror `Registry.register/revoke`
   into the same `AuditLog` at the registry boundary (or keep the orchestrator-side
   `_mirror_registry`); either keeps the unified chain.

3. **Merkle-anchor flusher.** Wire the off-loop background flusher sketched in
   `audit_log_design.md` §3 to submit `merkle_root(last_anchored, len(log))` to
   Besu every K decisions / T seconds (one ~2.1 s write per batch). The
   `RegistryService` write-worker pattern is the model.

4. **MQTT/Besu/SLM provisioning.** Stand up the Docker/Foundry services
   (`eclipse-mosquitto:2`, `besu:24.12.0`, Foundry Local Phi-4-mini) in the
   deployment env; the live-gated tests then flip from skipped to passing
   unchanged. The connection knobs (`--mqtt-host/port`, `--besu-rpc`) are already
   plumbed.

5. **Attacks over live transports.** Current attack injection is proven on the
   inprocess bus (auth/conservation are transport-agnostic). To inject over a
   live broker, route `MaliciousPublisher` through the deciding junction's
   transport bus (the `_underlying_bus` hook already picks it); add a live-gated
   test mirroring the inprocess attack tests.

6. **Network registry.** Add more nets to `_sumo_network` (grid3x3/grid4x4 already
   exist under `sumo/`) by deriving `(adjacency, edge_map)` with
   `edge_map_from_net` exactly as lambeth does.

Nothing in steps 1–6 changes a tested subsystem's public API — they are wiring
and provisioning. The composition itself is proven green here.
```
