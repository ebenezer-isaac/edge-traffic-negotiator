# The Edge Negotiator — Integration Status ("integrate later" tracker)

**Purpose:** the single tracker a future session/agent uses to fold the de-risk build on
`experiments/de-risk` into the canonical project. For each part: is it built, how is it tested
(CI vs live-gated), which commit carries it, and does it compose transparently or need a seam.
**Companion:** `SYSTEM-ARCHITECTURE.md` (the authoritative map). **Findings source:** `DE-RISK-INDEX.md`.

**Build state in one line:** every part is **built, committed, and green**. 335 tests collected
(308 pass in CI, 27 skipped without a live broker/node/Foundry). The whole assembly runs
end-to-end in CI with no Docker/Foundry/SUMO via the default `SystemConfig`. **Exactly one
composition seam** remains (the audit hook, deferred to a documented one-liner) plus four
**characterised-but-deferred** design decisions. Nothing else needs a seam — the rest is wiring
and provisioning.

The build landed in five waves; all under `03-implementation/edge-negotiator/`, branch
`experiments/de-risk`, working tree clean for code (only presentation files + an untracked
`results/showcase/` are dirty):

| Commit | Wave |
|---|---|
| `af7c7ea` | Wk1-2: 2×2 SUMO grid + MaxPressure baseline |
| `35188c5`/`773006d`/`62f119a` | SLM agent + hybrid controller + validated SLM-in-the-loop |
| `6368b67` | Milestone 2: authenticated cross-junction coordination (mechanism) |
| `6451eb6` | De-risk wave 1: hard data + drop-in modules (identity/registry/conservation/besu/mqtt/attacks/metrics/stats) |
| `451a5f7` | De-risk wave 3: QBFT, scaling, honest real-SLM measurement |
| `a4d0a24` | **Wave 4 (production parts):** `audit_log.py`, `registry_service.py`, `run_mqtt_coord.py`, `evaluation.py` |
| `3a22ffc` | **Wave 5 (integration):** `system.py`/`run_system.py` — end-to-end assembly of all parts |
| `cd43127` | `INTEGRATION-PLAYBOOK.md` (the ordered de-risk→merge path) |

---

## 1. Per-part status table

Legend — **Tested:** CI = runs in plain pytest; live = gated, skips cleanly without the service.
**Composition:** transparent = drop-in via public API; seam = needs the documented one-liner.

| Part | Built | Tested | Committed (last) | Composes |
|---|---|---|---|---|
| `identity.py` | ✅ | CI — 20 | `6451eb6` | transparent (signs decisions + registry events) |
| `registry.py` | ✅ | CI — 18 | `6451eb6` | transparent (bus drop-in) |
| `besu_registry.py` | ✅ | live (Besu) — via reg-svc integration test | `6451eb6` | transparent (same 4 methods as `Registry`) |
| `registry_service.py` | ✅ | CI — 19 (18 fake + 1 live-gated Besu) | `a4d0a24` | transparent (µs-cache drop-in for the bus) |
| `message_bus.py` | ✅ | CI — 18 | `6368b67` (+inbox index `451a5f7`) | transparent (controller `bus` slot) |
| `mqtt_transport.py` | ✅ | live (broker) — 10 | `6451eb6` | transparent (verification REUSED) |
| `conservation.py` | ✅ | CI — 24 | `6451eb6` | transparent (controller reconciliation) |
| `audit_log.py` | ✅ | CI — 51 | `a4d0a24` | **SEAM** (mirrored post-step; see §2) |
| `controllers.py` | ✅ | CI via coordination + live SUMO | `af7c7ea` | transparent (baseline + shield) |
| `hybrid_controller.py` | ✅ | CI via coordination | `773006d` | transparent (parent of coordinated) |
| `coordinated_controller.py` | ✅ | CI — 29 (StubAgent/FakeConn) + live SUMO | `6368b67` (+P1–P4 `451a5f7`) | transparent (read-only; `edge_map` injected) |
| `slm_agent.py` | ✅ | live (Foundry) — smoke + bench | `35188c5` | transparent (agent slot, deferred import) |
| `metrics.py` | ✅ | CI — 28 | `6451eb6` | transparent (consumes tripinfo) |
| `stats.py` | ✅ | CI via evaluation | `6451eb6` | transparent |
| `attacks.py` | ✅ | CI — 18 | `6451eb6` | transparent (injectors on public API) |
| `evaluation.py` | ✅ | live (SUMO) — 16 | `a4d0a24` | transparent (composes `run_one`/`metrics`/`stats`/`run_attacks`) |
| `system.py` + `system_fakeconn.py` | ✅ | CI — 23 (335 across project) | `3a22ffc` | **orchestrator** (carries the one seam) |
| `run_system.py` (CLI) | ✅ | CI via test_system | `3a22ffc` | transparent |
| `run_mqtt_coord.py` | ✅ | live (broker) — 12 | `a4d0a24` | transparent (`MqttBusAdapter` bus drop-in) |
| `run_coordinated.py` / `run_metrics_sweep.py` / `run_slm_metrics.py` | ✅ | live (SUMO/Foundry) | `6368b67`/`451a5f7` | transparent (runners) |
| `run_attacks.py` | ✅ | CI (StubAgent, no SUMO) | `6451eb6` | transparent |
| `run_scaling.py` / `sweep_baselines.py` / `collect_results.py` | ✅ | live (SUMO) | `451a5f7`/`6451eb6` | transparent (harnesses) |
| `bench_ledger.py` / `bench_qbft.py` / `bench_mqtt.py` / `bench_slm.py` | ✅ | live (Besu/QBFT/broker/Foundry) | `6451eb6`/`451a5f7` | n/a (measurement only) |
| `contracts/AgentRegistry.sol` | ✅ | live (Besu) — exercised by `besu_registry` | `6451eb6` | transparent (on-chain `Registry`) |

`coordinated_controller.py` already absorbed the four DE-RISK §9/§10 `src/` fixes
(committed `451a5f7`): **P1** generalised edge resolution (injected `edge_map`, kills the silent
OSM no-op), **P2** inbox index (O(n²)→amortised O(1)), **P3** `reconcile_silent_neighbours`
(default OFF), **P4** `coord_override` (default OFF). So those are *built and tested*, not pending
code — only their *enablement decisions* remain (§4).

---

## 2. The ONE known composition seam (the audit hook)

**What it is.** `audit_log_design.md` §7.1 specifies the audit hook as a *one-line addition
inside* `CoordinatedController.decide()`, immediately after the controller appends its decision
event to `self.events`. The de-risk rule was *read-only on the controller* (owned elsewhere), so
`IntegratedSystem` instead **mirrors** the controller's public `.events` list into the `AuditLog`
*after each control step* (`system.py:_drain_audit`), signing each entry with the deciding
junction's identity.

**Why it is a deferral, not a workaround.** The mirrored record is **byte-identical** to what the
in-file hook would produce — the controller already emits a fully JSON-serialisable event dict
(`tls, halting, slm_phase, shield_phase, used, overridden, tick, published, expected_incoming,
incoming_per_phase, mp_choice, coord_choice, coord_changed, coord_overrode, received,
neighbor_note, detections`) that passes `AuditLog._validate_event` unchanged. The *only* named
difference: the append happens one control step later (still long before the run ends, the chain
is verified, and the Merkle root is produced). `verify_chain()==True` in every run.

**The exact in-file promotion (removes the seam).** Per `audit_log_design.md` §7.1 and
`integrated_system_design.md` §7 step 1, in the *canonical* `CoordinatedController`:

```python
# __init__, next to  self.detections = []
self.audit = AuditLog()

# decide(), immediately after  self.events.append(event)
self.audit.append({"kind": "decision", **event}, issuer=self.identities.get(tl))
```

Then `IntegratedSystem._drain_audit` becomes a no-op — delete it and read `ctrl.audit` directly.
That is the single one-line in-file change the whole build defers.

**Other deferrals (not seams — just boundary care or off-by-design):**
- `seq` collision: the registry's own `seq` is carried as `registry_seq` in the mirrored registry
  event because `seq` is a reserved `AuditLog` envelope key. Permanent, correct, no action.
- Attack scoring keys on `(recipient, sender, tick)` to ignore the benign self-echo replay the bus
  logs on a clean run (a documented `run_attacks` quirk). No action.
- The **Merkle-anchor flusher** (the off-loop background write of `merkle_root(last_anchored, n)`
  to Besu every K decisions / T seconds) is *designed* (`audit_log_design.md` §3, modelled on the
  `RegistryService` write-worker) but **not wired** — anchoring is exercised in-process
  (`_audit_bundle` computes root + a sample inclusion proof) but no live periodic Besu write runs.
  This is integration step 3 below, not a code defect.

---

## 3. Final integration checklist (promote `experiments/de-risk` → main/canonical)

Ordered; nothing here changes a tested subsystem's public API (wiring + provisioning only).
Cross-ref `integrated_system_design.md` §7 and `DE-RISK-INDEX.md` "Integration TODO".

1. **Merge `experiments/de-risk` → `main`.** All code is committed and the tree is clean (only
   presentation assets + untracked `results/showcase/` are dirty). No rebase conflicts expected —
   the de-risk parts are additive to `src/`.
2. **Promote the audit one-liner in-file** (§2): add `self.audit = AuditLog()` in
   `CoordinatedController.__init__` and the one `self.audit.append(...)` in `decide()`; turn
   `_drain_audit` into a no-op / delete it and read `ctrl.audit`. Re-run `tests/test_system.py`
   and `tests/test_audit_log.py` (expect green; `verify_chain` stays True).
3. **Enable `reconcile_silent_neighbours=True`** on the canonical controller construction so total
   sensor outage produces a reachable `missing_claim` Detection on the live path (DE-RISK §2; P3
   code already present, default OFF). Add/promote the live-path outage test.
4. **Pin contract + transport deps in `requirements.txt`** — `py-solc-x` (+ solc `0.8.24`),
   `paho-mqtt`, `pyproj`, `pytest`, `tabulate` (DE-RISK §1/§6; flagged as not-yet-pinned).
5. **Decide `coord_override`** (§4 open decision): ship advisory (`coord_override=False`, today's
   behaviour) or override-capable (`True` + a chosen threshold). Whichever is chosen, set it
   explicitly at construction and record the rationale (this is a *thesis* decision, not just code).
6. **Wire the Merkle-anchor flusher** (off-loop background write of `merkle_root` to Besu every
   K/T), modelled on the `RegistryService` write-worker (`audit_log_design.md` §3). Off the
   control loop; one ~2.1 s write per batch.
7. **Run the 30-seed evaluation** (`evaluation.run_evaluation` / `run_slm_metrics`,
   `--seeds 30`) to resolve the underpowered coordination effect (n=4 → "not detected, not
   absent"); headline `mean_network_delay` / `completion_rate` / `throughput` + matched-set, and
   **drop completed-only avg travel time** (wrong sign under survivorship bias, DE-RISK §4).
8. **Provision live backends** for the live-gated tests to flip from skipped to passing unchanged:
   `eclipse-mosquitto:2` (MQTT), `hyperledger/besu:24.12.0` (registry; **pin 24.12.0**, not
   `latest`/`26.6.0-RC1` which removed `--miner-enabled`), Foundry Local Phi-4-mini (SLM). The
   `--mqtt-host/port`, `--besu-rpc`, `--agent slm` knobs are already plumbed.
9. **(Optional) Attacks over live transports** and **more nets** (`grid3x3`/`grid4x4` already under
   `sumo/`) via `edge_map_from_net` exactly as lambeth — both are additive, live-gated.

---

## 4. Open design decisions still owed

Characterised by the de-risk wave; each needs a *decision*, not more discovery.

| Decision | Current state | What's owed | Ref |
|---|---|---|---|
| **Channel-B override** | `used = SLM_proposal if valid else coord_choice`; `coord_override` exists, default OFF. With a reliable SLM the deterministic coordination term is computed, counted, then discarded ⇒ the only causal channel is Channel-A (the prompt note). | Decide: keep coordination **advisory** (Channel-A only) or make the shield **override** a valid proposal when coordination strongly disagrees (set `coord_override` + threshold). A thesis decision with a measurement plan (30 seeds, real SLM). | DE-RISK §8 |
| **Multisig admin key** | `AgentRegistry` is `onlyOwner` (single city-authority key). | Decide production hardening: HSM-backed key and/or multisig owner (documented as optional in the contract NatSpec + QBFT spike, not implemented). | `AgentRegistry.sol`, `QBFT-SPIKE.md` |
| **Bus sharding at scale** | Single all-pairs neighbour bus; compute scales sub-linearly but `rejected_messages` grows super-linearly. | Decide a per-neighbourhood sharding strategy for hundreds of junctions (not needed at corridor scale). | DE-RISK §10 |
| **Silent-neighbour reconciliation default** | `reconcile_silent_neighbours` default OFF (preserves as-built attack-report scenarios). | Decide to flip ON at integration so `missing_claim` is reachable live (recommended). | DE-RISK §2 |

---

## 5. What is genuinely DONE vs genuinely REMAINING

**Done (built, committed, green):** all 18 core `src/` modules + the orchestrator; the contract;
335 tests (308 CI-pass, 27 live-gated-skip); every measured number in `SYSTEM-ARCHITECTURE.md` §7;
the full swappable-backend matrix wired and live-gated; the four DE-RISK `src/` fixes (P1–P4)
already folded into the controller; the audit chain verifying end-to-end with Merkle inclusion.

**Remaining (wiring + decisions, no new subsystem):** the one-line in-file audit promotion;
enabling `reconcile_silent_neighbours`; pinning deps; the Channel-B override / multisig / sharding
decisions; wiring the off-loop Merkle-anchor flusher; provisioning the live services; and running
the 30-seed evaluation that turns the underpowered coordination null into a resolved result. None
of these is discovery — they are the documented, ordered last mile.
