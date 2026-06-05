# The Edge Negotiator — System Architecture (Authoritative Map)

**Status:** master architecture document for the de-risk build on branch `experiments/de-risk`.
**Scope:** every module under `03-implementation/edge-negotiator/src/`, its tests, and how
the parts compose into one runnable, verifiable system.
**Companion:** `INTEGRATION-STATUS.md` (the "integrate later" tracker) and the per-subsystem
design notes under `edge-negotiator/results/*_design.md`.
**Source of truth for findings:** `DE-RISK-INDEX.md`. This document is read-only over the code:
it describes what was built, never edits it.

The thesis claim is **verifiable decentralised traffic optimisation using edge SLMs**. The
system has two planes that meet at the controller:

- a **fast path** — signed neighbour messages over MQTT drive a per-junction SLM-proposes /
  MaxPressure-shield-disposes control loop in real time (~6 ms transport, ~0.48 s SLM);
- a **trust path** — a permissioned Besu registry (who is approved) plus a hash-chained,
  Merkle-anchored audit log (what was decided), strictly **off** the control loop (~2.1 s writes).

The honest headline (DE-RISK §3/§4): the **integrity contribution** (authentication +
conservation detection + tamper-evident audit) is the result, not a traffic-performance win
(MaxPressure ≈ fixed-time on the single Lambeth arterial; coordination is throughput-neutral
at the measured seed counts).

---

## 1. Component diagram (fast path + trust path + control loop)

```
                         ┌──────────────────────────────────────────────────────────────┐
                         │                    PER-JUNCTION EDGE NODE                       │
                         │                                                                 │
   neighbour reports     │   ┌─────────────────────┐        ┌───────────────────────────┐ │
   (signed, over MQTT)   │   │  SLM / SHIELD LOOP   │        │   DETECTION & RECONCILE    │ │
        ▲   │            │   │                      │        │                            │ │
        │   ▼            │   │ slm_agent.SLMAgent   │        │ conservation.              │ │
 ┌──────┴───────────┐    │   │  (Phi-4-mini,Foundry)│        │   ConservationChecker      │ │
 │  FAST PATH        │    │   │  proposes a phase ───┼──┐     │  claim N  vs  observed M   │ │
 │                   │    │   │  None on any failure │  │     │  → inflated/under_reported │ │
 │ mqtt_transport.   │◄───┼─► │                      │  ▼     │    /missing_* (Detection)  │ │
 │   MqttTransport   │pub │   │ controllers.         │ used   └─────────────▲──────────────┘ │
 │  (paho, QoS1)     │sub │   │  MaxPressureController│ phase                │ claims+observed │
 │     │             │    │   │  = SHIELD (disposes) │  │                    │                 │
 │     ▼             │    │   │     ▲                │  │     ┌──────────────┴──────────────┐ │
 │ message_bus.      │    │   │ hybrid_controller.   │  │     │ coordinated_controller.     │ │
 │   MessageBus  ────┼────┼─► │  HybridController    │  │     │   CoordinatedController     │ │
 │  verify on inbox: │ Neighbor│ (event-gate quiet) │  └────►│  publish "toward" / read    │ │
 │  topology+member+ │Message  │     ▲                │        │  inbox / Channel-A+B / log  │ │
 │  Ed25519+replay   │    │   └─────┼────────────────┘        └──────────────┬──────────────┘ │
 │     │             │    │         │ MaxPressure baseline                   │ events[]        │
 └─────┼─────────────┘    │   identity.JunctionIdentity (Ed25519 sign/verify)│ detections[]    │
       │ public_key /     │         │ keys (DER)                             │                 │
       │ is_approved      │         ▼                                        ▼                 │
       │            ┌─────┴─────────────────────────┐         ┌──────────────────────────────┐│
       │            │        TRUST PATH (async)      │         │   audit_log.AuditLog          ││
       │            │                                │         │  sha256 hash-chain            ││
       └────────────┤ registry.Registry  (local)     │         │  + Ed25519 issuer sig         ││
   membership read  │   ── or ──                     │ mirror  │  + Merkle root (batch anchor) ││
   (cache, µs)      │ registry_service.RegistryService│◄───────┤  + JSONL persistence          ││
                    │   (in-mem cache over Besu)      │ reg     └──────────────┬───────────────┘│
                    │       ▲ events (poll)           │ events                 │ merkle_root     │
                    └───────┼────────────────────────┘                        │ (every K/T)     │
                            │ eth_call (read ~15-50ms)                         ▼ ~2.1 s write    │
                    ┌───────┴─────────────────────────────────────────────────────────────────┐│
                    │  besu_registry.BesuRegistry  ──►  contracts/AgentRegistry.sol (onlyOwner) ││
                    │  Hyperledger Besu (dev 1-block | prod QBFT 4-validator)                   ││
                    │  AgentRegistered / AgentRevoked events  =  on-chain audit log             ││
                    └──────────────────────────────────────────────────────────────────────────┘
```

Box → module mapping is the **module catalogue** in §3. The orchestrator that wires every box
into one runnable pipeline is `system.IntegratedSystem` (§5); `run_mqtt_coord.MqttBusAdapter`
is the bus-shaped drop-in that puts the broker between `publish` and `inbox` without forking
any crypto.

---

## 2. Data flow of one control decision (end-to-end)

This is exactly what `CoordinatedController.decide(tl, st)` does each time an SLM junction's
green timer expires (~`min_green` ≈ 10 s), with the audit hook mirrored by the orchestrator
(the documented seam, §6). Sub-step letters match `coordinated_controller.py`.

```
1. SHIELD baseline        MaxPressureController.decide() → mp_choice (argmax pressure).
   (controllers.py)       If tl not an SLM junction, or total halting < gate → return mp_choice
                          (event-gate: skip the SLM when quiet; the deterministic pick stands).

2. PUBLISH (a)            toward_release = _toward_counts(st, mp_choice)        # actual outflow
   (message_bus +         payload = {"toward": {nb: {"release": r, "queue_forecast": r}}}
    identity)             msg = bus.publish(identities[tl], tick, payload)
                          → identity.sign(canonical_bytes(sender,t,payload))   # Ed25519
                          → MQTT: MqttTransport serialises (sig→b64) onto edge-negotiator/junction/<tl>

3. NEIGHBOUR VERIFY (b)   bus.inbox(tl)  runs ALL trust checks on each received NeighborMessage:
   (message_bus.inbox)      topology:  sender ∈ adjacency[tl]      else reject not_neighbour
                            membership: registry.is_approved(sender) else reject revoked/unknown_sender
                            crypto:    identity.verify(pubkey, canonical_bytes, sig) else bad_signature
                            replay:    (recipient,sender,t) unseen   else reject replay
                          Accepted messages → expected_incoming, incoming_by_neighbour, claims{(src,tl):rel}.

4. COORDINATE (c, c')     incoming_per_phase = attribute each neighbour's release to local green phases.
                          Channel B (deterministic): adj_halting[gi] = halting[gi] + coord_weight*incoming_per_phase[gi]
                                                     coord_choice = argmax(adj_halting)   (= mp_choice if coord_weight==0)
                          Channel A (prompt):        note = "Incoming … phase gi +k …"  → SLMAgent.choose_phase(note)
                          proposal = SLM phase (or None on any failure).
                          used = proposal if valid else coord_choice.    # shield disposes
                          [optional P4] coord_override: a valid proposal can be overridden by coord_choice
                                        when its adjusted-pressure margin exceeds a threshold (default OFF).

5. CONSERVATION (d)       observed = _observed_inflows(tl, claim_srcs [+ silent approved neighbours if P3])
   (conservation.evaluate) detections = checker.evaluate(claims, observed)
                          → Detection(flagged, reason ∈ {ok,inflated,under_reported,missing_claim,
                            missing_observation}); appended to ctrl.detections and embedded in the event.

6. EVENT                  ctrl.events.append({tls,halting,slm_phase,shield_phase,used,tick,published,
                          expected_incoming,incoming_per_phase,mp_choice,coord_choice,coord_changed,
                          coord_overrode,received,neighbor_note,detections})  → return used.

7. AUDIT APPEND (seam)    IntegratedSystem._drain_audit (post-step): for each new ctrl.events entry,
   (audit_log.append)     audit.append({"kind":"decision", **event}, issuer=identities[tl])
                          → sha256 hash-chain link + Ed25519 signature over the entry hash.
                          (Canonical in-file hook would append INSIDE decide(); see §6 / INTEGRATION-STATUS.)

8. PERIODIC ANCHOR        every K decisions / T seconds, OFF the control loop:
   (audit_log.merkle_root) root = audit.merkle_root(last_anchored, len(audit))     # folds the batch
   → besu_registry         Besu write of `root` (~2.1 s) anchors thousands of decisions in one tx.
                          verify_inclusion(entry_hash, branch, root) later proves any single
                          decision was in the anchored batch from only the on-chain root.
```

The fast path (steps 1–6) is wholly local + ~6 ms transport. The trust path (steps 7–8 writes)
is async and never blocks a decision: membership *reads* hit a microsecond in-memory cache
(`RegistryService`), and audit *writes* are batched behind a Merkle root.

---

## 3. Module catalogue

Tests = test functions collected from the matching `tests/test_*.py` (335 total collected;
27 skipped without live broker/node/Foundry). Live-deps: **none** = pure-Python/CI;
**SUMO**/`MQTT`/`Besu`/`Foundry` = needs that service (live-gated, skips cleanly).

| Module (`src/`) | Role | Key public API | Tests | Live-deps | Design doc |
|---|---|---|---|---|---|
| `identity.py` | Per-junction Ed25519 identity; sign/verify (DER 44-byte keys, 64-byte sigs). `verify` never raises on hostile input. | `JunctionIdentity(jid)`, `.public_key`, `.sign(bytes)`; `verify(pub,payload,sig)->bool` | 20 | none | (registry §) |
| `registry.py` | Local in-memory permissioned allowlist + sha256 hash-chained audit log (membership ledger). | `register/revoke`, `is_approved`, `public_key`, `audit_log`, `verify_chain` | 18 | none | DE-RISK §1 |
| `besu_registry.py` | On-chain allowlist (web3/solc); drop-in for `Registry`. Writes=tx (mined), reads=`eth_call`; events = on-chain audit log. | `deploy/attach`, `register/revoke`, `is_approved`, `public_key`, `audit_log`, `verify_chain` | (via reg-svc live test) | Besu | `BESU-SPIKE.md`, `QBFT-SPIKE.md`, `ledger_bench.md` |
| `registry_service.py` | Control-path-safe facade over Besu: µs cache reads, off-loop write worker, graceful stale/disconnected. Drop-in for the bus. | `start/close`, `is_approved`, `public_key`, `audit_log`, `register/revoke`(→`PendingWrite`), `refresh`, `flush`, `status`, `health` | 19 | Besu (1 live test) | `registry_service_design.md` |
| `message_bus.py` | In-process signed neighbour bus: enforces topology + membership + Ed25519 + replay on `inbox`. O(1)-amortised per-recipient index. | `MessageBus(registry,adjacency)`, `publish(id,t,payload)`, `inbox(recipient)`, `.rejected`; `NeighborMessage`, `canonical_bytes` | 18 | none | (milestone-2) |
| `mqtt_transport.py` | MQTT adapter wrapping `MessageBus` — same self-authenticating frame; verification REUSED, not forked. | `MqttTransport(recipient,bus,...)`, `publish`, `poll`, `subscribe_neighbours`; `serialize/deserialize`, `verify_received` | 10 | MQTT | `MQTT-SPIKE.md`, `mqtt_bench.md` |
| `conservation.py` | The detection primitive: reconcile claimed outflow vs observed inflow per edge. Stateless, immutable. | `ConservationChecker(tolerance)`, `evaluate(claims,observed)->[Detection]` | 24 | none | DE-RISK §2, `attacks_report.md` |
| `audit_log.py` | Append-only tamper-evident decision+event log: sha256 chain + optional Ed25519 sig + Merkle batch anchor + JSONL. | `append(event,issuer)`, `entries`, `verify_chain`, `verify_signatures`, `merkle_root`, `inclusion_proof`, `to/from_jsonl`; `verify_inclusion` | 51 | none | `audit_log_design.md` |
| `controllers.py` | `MaxPressureController` = classical baseline AND always-on safety shield; `FixedTimeController` baseline. | `MaxPressureController(conn,tls,...)`, `.decide`, `.step`, `.green_halting` | (via coordination) | SUMO (at runtime) | `lambeth_controllability.md` |
| `hybrid_controller.py` | SLM-proposes / shield-disposes, event-gated (skip SLM when quiet); logs every decision. | `HybridController(conn,tls,agent,slm_junctions,gate,...)`, `.decide`, `.events` | (via coordination) | SUMO | (brief §5) |
| `coordinated_controller.py` | Authenticated cross-junction coordination layer (publish/verify/Channel-A+B/conservation) + `StubAgent` + `edge_map_from_net`. | `CoordinatedController(...)`, `.decide`, `.detections`, `.events`; `StubAgent`; `edge_map_from_net(net,mode)` | 29 | SUMO (real runs); none (StubAgent/FakeConn) | `COORDINATION-ALGORITHM-SPEC.md`, `corridor_coord.md` |
| `slm_agent.py` | Real SLM junction agent (Phi-4-mini via Foundry Local, OpenAI-compatible); terse `{"phase":N}`, None on any failure. | `SLMAgent(...)`, `.choose_phase(jid,n,halting,note)`; `discover_endpoint` | (smoke + live bench) | Foundry | `slm_bench.md`, DE-RISK §7 |
| `metrics.py` | Survivorship-robust traffic metrics from tripinfo (needs `--write-unfinished/-undeparted`). | `parse_tripinfo`, `summary`, `throughput`, `matched_diff`, `completion_rate`, … | 28 | none | DE-RISK §4, `milestone2_report.md` |
| `stats.py` | BCa bootstrap, paired-diff CI, permutation test, Holm-Bonferroni (stdlib+numpy, no scipy). | `bca_bootstrap`, `paired_diff_ci`, `permutation_test`, `holm_bonferroni`, `summarize_sweep` | (via evaluation) | none | (brief §7) |
| `attacks.py` | Injectable attack transforms over the PUBLIC API (spoof/faulty/sybil×4/collusion), each ground-truth-labelled. | `MaliciousPublisher(bus)`, `spoof_release`, `faulty_release`, `sybil_*`, `collusion_lockstep`; `InjectedMessage` | 18 | none | `THREAT-MODEL-ANALYSIS.md`, DE-RISK §2 |
| `evaluation.py` | Full results-matrix harness: TRAFFIC table (BCa CI + paired perm + Holm) + DETECTION table (P/R/F1/latency). | `EvalConfig`, `run_evaluation`->`EvalReport(.json,.markdown)` | 16 | SUMO | `evaluation_harness_design.md` |
| `system.py` | **The orchestrator** — `IntegratedSystem` composes every part behind a frozen `SystemConfig`; swappable backends; wires audit at the seam. | `SystemConfig`, `IntegratedSystem(cfg).run()->SystemResult`, `AttackSpec` | 23 (335 across project) | none default; SUMO/MQTT/Besu/Foundry opt-in | `integrated_system_design.md` |
| `system_fakeconn.py` | Deterministic in-memory TraCI stand-in + result-assembly helpers for the CI (no-SUMO) path. | `FakeConn`, `NoObsConn`, `initial_halting`, `coordination_counts`, `*_traffic_summary`, `config_dict` | (via test_system) | none | `integrated_system_design.md` |
| `run_system.py` | CLI launcher for `IntegratedSystem` (`--attack`, `--sumo`, `--transport/--registry/--agent`, `--out`). | `main()` | (via test_system) | per-flag | `integrated_system_design.md` §5 |
| `run_mqtt_coord.py` | Coordinated loop over a REAL broker via `MqttBusAdapter` (bus-shaped drop-in); `--compare` proves transport-swap transparency. | `run(...)`, `MqttBusAdapter`, `broker_reachable`, `_PerJunctionAdapter` | 12 | MQTT | `mqtt_coord_design.md` |
| `run_coordinated.py` | In-process coordination run + λ-sweep harness (the milestone-2 mechanism runner). | `run`, `ADJACENCY` | (via coordination) | SUMO | `corridor_coord.md` |
| `run_metrics_sweep.py` | Throughput-controlled SUMO sweep (`run_one`) — single source of the write-flag discipline reused by `evaluation`. | `run_one(mode,seed,end,coord_weight)` | (via evaluation) | SUMO | `coord_throughput.md` |
| `run_slm_metrics.py` | Honest coordination effect with the REAL Phi-4-mini, throughput-controlled. | `main()` | — | SUMO+Foundry | `coord_slm_honest.md` |
| `run_attacks.py` | Runs the three attack scenarios through the detectors; P/R/F1+latency vs ground truth (`run_all`, `_prf1`). | `run_all`, `_prf1` | (via attacks/eval) | none | `attacks_report.md` |
| `run_scaling.py` | Scaling harness 2×2→4×4 (confirms inbox fix is linear, >40× headroom). | `main()` | SUMO | `scaling.md`, DE-RISK §10 |
| `run_baseline.py`/`run_hybrid.py`/`run_evaluation.py` | Thin CLIs for baseline / hybrid / full-matrix runs. | `main()` | SUMO(+Foundry) | (respective) |
| `bench_ledger.py` | Besu vs in-memory registry latency benchmark (the ~2.1 s number). | `main()` | Besu | `ledger_bench.md` |
| `bench_qbft.py` | AgentRegistry latency under a REAL 4-validator QBFT network. | `main()` | Besu/QBFT | `qbft_bench.md` |
| `bench_mqtt.py` | MQTT pub→verified-deliver latency vs in-process baseline (the ~6 ms number). | `main()` | MQTT | `mqtt_bench.md` |
| `bench_slm.py` | SLM latency + multi-model ablation (the 0.48 s number; refutes "2–8 s"). | `main()` | Foundry | `slm_bench.md` |
| `sweep_baselines.py`/`collect_results.py`/`smoke_slm.py` | High-N baseline sweep / milestone-2 collector / SLM round-trip smoke. | `main()` | SUMO / SUMO / Foundry | DE-RISK §4 |

`contracts/AgentRegistry.sol` (Solidity 0.8.24, `onlyOwner` allowlist; `AgentRegistered`/
`AgentRevoked` events are the on-chain audit log; keys stored as opaque DER bytes) is the
on-chain counterpart of `registry.py`, exercised by `besu_registry.py`.

---

## 4. The decision data flow as types

```
JunctionIdentity.sign ─► NeighborMessage{sender,t,payload:{toward:{nb:{release,queue_forecast}}},signature}
        │ serialize (sig→b64)                          ▲ deserialize
        ▼                                              │
   MQTT topic edge-negotiator/junction/<sender>  ──────┘
        │ MessageBus.inbox verifies (topology+member+Ed25519+replay)
        ▼
   claims:{(src,dst):int}  +  observed:{(src,dst):int}  ─► ConservationChecker.evaluate
        ▼                                                       ▼
   used phase (int)                                     [Detection{flagged,reason}]
        ▼                                                       ▼
   ctrl.events[]  ───── _drain_audit ─────►  AuditLog.append(event, issuer=identity)
                                                  ▼ hash-chain + Ed25519 sig
                                             merkle_root(batch) ──► Besu anchorRoot (off-loop)
```

`canonical_bytes` (sorted-keys, no-whitespace JSON) is the one encoding both signer and every
verifier hash, so an MQTT subscriber recomputes byte-identical input. The audit-log hash-chain
uses the **same** sha256(`prev_hash` ‖ canonical_json) construction as `registry.py`, so both
chains "speak the same bytes" (one auditor scheme).

---

## 5. The config matrix of `IntegratedSystem` (system.py)

`SystemConfig` is a frozen, fully-validated dataclass. Each backend choice swaps exactly one box;
the **default** (`inprocess/memory/stub/grid2x2/audit-on/no-attacks`) runs in CI with no Docker,
no Foundry, no SUMO (`is_default == True`). Non-default backends are opt-in and **live-gated**.

| Field | Values | Default | Swaps in | Live dep |
|---|---|---|---|---|
| `transport` | `inprocess` / `mqtt` | `inprocess` | `MessageBus` ↔ `run_mqtt_coord.MqttBusAdapter` (per-junction `MqttTransport`) | MQTT broker |
| `registry` | `memory` / `besu` | `memory` | `Registry` ↔ `RegistryService(BesuEventSource(BesuRegistry))` | Besu node |
| `agent` | `stub` / `slm` | `stub` | `StubAgent` (argmax) ↔ `SLMAgent` (Phi-4-mini) | Foundry Local |
| `network` | `grid2x2` / `lambeth` | `grid2x2` | `f"{src}{dst}"` string convention ↔ `edge_map_from_net` (sumolib-derived `(src,dst)→edge`) | SUMO |
| `audit` | `True` / `False` | `True` | `AuditLog` on (append+sign+anchor) ↔ off (`{"enabled": false}`) | none |
| `attacks` | tuple of `AttackSpec` | `()` | `MaliciousPublisher` injectors at scheduled ticks | none |
| run knobs | `seed,end,rounds,coord_weight,tolerance,gate` | `42,200,40,1.0,2,2` | sim/eval parameters | — |
| conn knobs | `mqtt_host/port,besu_rpc,use_sumo` | `127.0.0.1:1883`, `:8545`, `False` | live connection targets | — |

Derived: `requires_sumo == use_sumo or transport=="mqtt" or network=="lambeth"` → routes
`run()` to `_run_sumo` (real tripinfo via `metrics.py`) vs `_run_fake` (deterministic FakeConn,
40 decide() rounds). `AttackSpec.kind ∈ {spoof, under_report, not_neighbour, revoked,
bad_signature}` — the first two route to conservation, the last three to auth.

`SystemResult{config, traffic, coordination, audit, attack_outcomes, backends}` is the single
immutable bundle each run produces; `audit` carries `verify_chain`, `merkle_root`, and a sample
`inclusion_proof` (last entry). Default run bundle (reproducible): 44 audit entries (40 decision
+ 4 registry), `verify_chain==True`, deterministic Merkle root, `inclusion_proof_valid==True`.

---

## 6. Threat model — what each layer guarantees (cross-ref `THREAT-MODEL-ANALYSIS.md`)

Three layers, three disjoint jobs. **Authentication ≠ conservation ≠ audit.**

| Layer | Module | Guarantees | Does NOT guarantee |
|---|---|---|---|
| **Authentication / membership** | `identity` + `registry`/`registry_service` + `message_bus.inbox` | Only a *currently-approved neighbour* with a *valid Ed25519 signature* over the *exact bytes*, *not replayed*, is ever acted on. Forgery, impersonation, non-neighbour injection, revoked-sender, and replay are dropped to `bus.rejected` with a precise reason. **Measured P=R=F1=1.0, 0-cycle latency** on the four sybil/impersonation cases. | That an authenticated agent *tells the truth*. Membership ≠ honesty (contract NatSpec + brief §6). |
| **Conservation (plausibility)** | `conservation.ConservationChecker` | Catches *uncoordinated* lies/faults: an approved agent over-claiming (`inflated`), under-reporting / faulty sensor (`under_reported`), or a one-sided outage (`missing_claim`/`missing_observation`) once `|claim−observed| > tolerance`. **Measured P=1.0** (no false alarms above tolerance). | *Truth*, only *mutual consistency*. It cannot say which of two disagreeing parties is wrong. |
| **Audit (accountability)** | `audit_log.AuditLog` + Besu anchor | *Integrity of the record*: any post-hoc edit, re-hash, reorder, deletion, JSONL tamper, swapped signature, or forged inclusion proof is detected (`verify_chain`/`verify_signatures`/`verify_inclusion`). On-chain anchoring extends this to *completeness against a published commitment* (defeats tail-truncation). | *Truthfulness of a recorded claim*; and it cannot force `append` to be called (suppress-logging is an operational/liveness concern, not cryptographic). |

### The honest non-claims (do not overstate — DE-RISK §2/§3/§8)

- **Coordinated, conservation-respecting collusion** — two attackers inflating A's claim and B's
  observation in lockstep keep the books balanced; **no layer fires**. Only `revoke` + the audit
  trail contain it. This is the **Xiao2026** residual limit (arXiv:2602.10162, cited as an
  analogous FDI result). Recall is correctly **0** here and reported as a correct negative.
- **Sub-tolerance single-party lying** — a within-tolerance inflation evades; the stateless check
  accumulates no cross-tick evidence. Recall climbs 0→1 across the tolerance floor; no operating
  point catches a sub-tolerance lie without false-alarming on honest jitter.
- **No traffic-performance win claimed** — MaxPressure ≈ fixed-time on the single Lambeth
  arterial (96.8% vs 92.8% completion); SLM coordination is throughput-neutral at measured seeds
  (Channel-B is advisory-on-fallback-only with a reliable agent — see §8 open decision). The
  thesis headline is **integrity**, not throughput.
- **`unknown_sender` is unreachable in a fully-provisioned closed corridor** (needs a phantom
  node) — a Sybil-surface framing point, not a defect.

---

## 7. Key measured numbers (one place — all from `DE-RISK-INDEX.md`)

| Quantity | Measured | Source | Meaning |
|---|---|---|---|
| **SLM decision latency** | Phi-4-mini median **0.482 s**, p95 0.553 s, max 1.54 s | `slm_bench.md` §7 | ~10× faster than brief's "2–8 s"; >18× headroom vs ~10 s gate; ~18–20 decisions/10 s/endpoint. |
| **MQTT pub→verified-deliver** | median **5.93 ms**, p95 8.18 ms (in-proc 2.15/3.28 ms) | `mqtt_bench.md` §6 | Transport is NOT the bottleneck (~1200× inside the SLM interval); ~270 msg/s. |
| **Besu write (dev)** | register **1444 ms** med (p95 3863), revoke 1842 ms | `ledger_bench.md` §1 | ~94,000× slower than in-memory ⇒ fine async, fatal on the loop. |
| **Besu read (dev)** | isApproved **46 ms**, getPublicKey 32 ms | `ledger_bench.md` §1 | Cheap eth_call; still cached by `RegistryService` (µs). |
| **QBFT (prod) write/read** | register **2142 ms** (p95 2545), reads **~15 ms** | `qbft_bench.md` §1 | Async holds *more cleanly* under BFT; block-period-dominated, not validator-count. |
| **Cached membership read** | **~15 µs** | `registry_service_design.md` | Control-path read never touches the network. |
| **Detection precision** | **P = 1.0** (auth R=1.0; conservation R<1 by design) | `attacks_report.md` §2 | Sybil/impersonation perfect; sub-tolerance lies correctly evade. |
| **Inbox cost** | per-call flat, **amortised O(1)** (was O(n²)) | `scaling.md` §10 | Per-recipient scan index; total linear in rounds. |
| **Scaling headroom** | 23 ms/decision @16 TLS vs ~1 s tick → **>40× headroom**; 4× junctions → 3.80× wall (sub-linear) | `scaling.md` §10 | Stack is not the scaling bottleneck. |
| **Audit chain** | `verify_chain==True` in every run; 2000-entry scale test green | `audit_log_design.md` §9 | Tamper/reorder/drop all detected; Merkle inclusion verifies. |
| **Stats power** | real effects at **n=30** (MaxPressure>fixed-time, all survive Holm) | DE-RISK §4 | Milestone-2 non-rejections were a power problem (n=3), not a broken pipeline. |

---

## 8. Open architectural decisions (carried into integration)

These are design choices the de-risk wave *surfaced and characterised* but deliberately left to
the integration step (full detail + the concrete one-liners in `INTEGRATION-STATUS.md`):

1. **Channel-B override** — today `used = SLM_proposal if valid else coord_choice`, so the
   deterministic coordination term is consulted only on SLM fallback; a reliable SLM never falls
   back ⇒ Channel-B is computed, counted, then discarded (DE-RISK §8). `coord_override`/
   `coord_override_threshold` exist (default OFF) to let the coordination-aware shield override a
   valid proposal. Decision owed: ship advisory or override-capable.
2. **Multisig admin key** — `AgentRegistry` is `onlyOwner` (single city-authority key); production
   hardening (HSM/multisig) is documented in the contract NatSpec + QBFT spike, not implemented.
3. **Bus sharding at scale** — `rejected_messages` grows super-linearly (all-pairs neighbour test);
   shard the bus per-neighbourhood at hundreds of junctions (DE-RISK §10).
4. **`reconcile_silent_neighbours` (P3)** — built and tested (default OFF) so total sensor outage
   yields a reachable `missing_claim`; flip ON at integration (DE-RISK §2).

The single known **composition seam** (the audit hook, mirrored post-step rather than appended
in-`decide()`) and the ordered promotion checklist are in `INTEGRATION-STATUS.md`.
