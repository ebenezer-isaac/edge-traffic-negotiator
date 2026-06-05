# De-Risk Index — hard data gathered ahead of implementation

Purpose: front-load the unknowns of Wk 5-10 with real measurements + drop-in modules, so later
stages are *integrate-and-merge*, not *discover-and-debug*. Generated 2026-06-04 on branch
`experiments/de-risk`. Each section links the artifact and states the hard finding + the
integration action it unlocks.

> Status legend: ✅ verified with data · ⏳ in progress · ⚠️ risk surfaced

## 0. Verified citations (design foundation)
All confirmed against arXiv (no fabrication):
- **CoLLMLight** arXiv:2503.11739 (Yuan, Lai, Liu) — cooperative LLM TSC, inter-agent coordination. Basis for the neighbour-message reimplementation.
- **CoLight** arXiv:1905.05717 (Wei et al., **CIKM 2019**) — graph-attention cooperative TSC; grounds the directional/upstream-dominant neighbour signal.
- **proofmember23** arXiv:2310.08163 (Pino, Margaria, Vesco, IEEE ITNAC 2023) — DID + proof-of-membership, single-domain; grounds the "strip VCs, allowlist is enough" identity decision.
- **Xiao2026** arXiv:2602.10162 (Xiao, Weng) — residual/consistency-check evasion limit (power-systems FDI; cited as an *analogous* result). Grounds the honest non-claim on coordinated collusion.

## 1. Besu permissioned registry (Wk 5-6) — ✅
Artifacts: `contracts/AgentRegistry.sol` (0.8.24, onlyOwner allowlist + events as audit log), `edge-negotiator/src/besu_registry.py` (verified drop-in for `src/registry.py`), `edge-negotiator/src/bench_ledger.py`, `edge-negotiator/results/ledger_bench.md`, `BESU-SPIKE.md`. End-to-end verified on a live node with real Ed25519 DER keys; `MessageBus(BesuRegistry(...))` works unchanged.

Latency (Besu 24.12.0 single-node dev, 1s block, 20 trials):
| op | Besu median | Besu p95 | local |
|---|---|---|---|
| register (write) | 1444 ms | 3863 ms | 0.015 ms |
| revoke (write) | 1842 ms | 5389 ms | 0.010 ms |
| isApproved (read) | 46 ms | 67 ms | 0.0002 ms |
| getPublicKey (read) | 32 ms | 48 ms | 0.0002 ms |
| batch of 10 registers | 20560 ms | — | 0.148 ms |

- **Async-registry assumption VALIDATED:** writes 1.4-1.8 s (inside the 1-2 s envelope), reads ~30-50 ms; on-chain write ~94,000× slower than in-memory ⇒ fine async, fatal on the control loop. Keeping the ledger strictly async is the right call.
- ⚠️ **Repro gotchas (caught, documented in BESU-SPIKE.md):** `besu:latest` (26.6.0-RC1) is broken (removed `--miner-enabled`) → **pin 24.12.0**; solc shanghai/PUSH0 reverts on the dev genesis → compile `evm_version="paris"`; dev-miner jitter drives p95. `py-solc-x`+solc not yet pinned in `requirements.txt` (flagged).
- **Integration risk (Wk5-6):** never couple the audit write to consensus latency — buffer/batch audit events off-loop (batched txs / Merkle-root anchoring); membership checks hit a locally-cached allowlist refreshed from on-chain events, never a synchronous `eth_call`.
- **Dual-path proven:** MQTT fast path (~6 ms, §6) + Besu trust path (~1.5 s) = exactly the brief's architecture, now with real numbers.
- **✅ Production QBFT validated** (`edge-negotiator/src/bench_qbft.py`, `results/qbft_bench.md`, `QBFT-SPIKE.md`): real 4-validator QBFT, register **2142 ms** (p95 2545), revoke 2169 ms, reads **~15 ms** (faster than dev). Async assumption holds *more cleanly* under BFT — deterministic finality, no PoW tail, tighter p95. **Write latency is block-period-dominated, NOT validator-count-dominated** (1→4 validators barely moved it). Prod rec: ≥4 validators (3f+1), 2 s block, gas-free + permissioning, recent EVM fork (drop paris pin), HSM/multisig admin. Open term: multi-host WAN (single-host loopback measured; block-period-dominated ⇒ modest RTT stays <2 s). Note: QBFT PoA `extraData` needs `ExtraDataToPOAMiddleware` for `get_block` (adapter unaffected).

## 2. Attack / detection evaluation (Wk 7-8) — ✅
Artifacts: `edge-negotiator/src/attacks.py`, `edge-negotiator/src/run_attacks.py`, `tests/test_attacks.py` (18 tests), `edge-negotiator/results/attacks_report.md`. **166 tests pass; no existing files edited (composed on the public API).**

Hard data @ tolerance=2 (StubAgent, in-memory TraCI stand-in, fully reproducible):
| attack | P | R | F1 | latency | detector |
|---|---|---|---|---|---|
| spoof (insider over-claim) | 1.000 | 0.667 | 0.800 | 1 cycle | conservation `inflated` |
| faulty (under-claim) | 1.000 | 0.600 | 0.750 | 1 cycle | conservation `under_reported` |
| sybil / impersonation (4 auth cases) | 1.000 | 1.000 | 1.000 | 0 cycles | auth `bus.rejected` |

- Recall<1 is correct: within-tolerance lies evade (precision stays 1.0). Tolerance ROC (spoof): recall 1/1/1/0.8/0.6/0.4 at tol 0/1/2/3/5/10; false-alarm 0.67/0.33/0.0 at tol 0/1/2. No operating point catches a sub-tolerance lie without false-alarming on honest jitter.
- **recall=0 (honest, reported as correct negatives):** coordinated collusion (Xiao2026 — neither layer fires; only `revoke`+audit contains it) and sub-tolerance single-party lying (stateless check accumulates no cross-tick evidence).
- ⚠️ **As-built gap → Wk7-8 integration TODO:** total sensor **outage** is undetected by the live path — `decide()` never feeds an observed-only edge to conservation, so the `missing_claim` reason the primitive *can* emit is unreachable. **Fix: reconcile edges where a registered neighbour should have claimed but didn't** (add a temporal expectation of claims per approved neighbour).
- Closed-corridor note: `unknown_sender` is unreachable when every junction is provisioned (needed a phantom node to exhibit) — informs the Sybil threat surface framing.

## 3. Lambeth corridor controllability (Wk 9-10 substrate) — ✅
Artifacts: `edge-negotiator/sumo/lambeth/{lambeth_spine.sumocfg, base.rou.xml, run_lambeth.py, sweep_results.json}`, `edge-negotiator/results/lambeth_controllability.md`. `src/`/`tests/` untouched (runner imports controllers verbatim).

- **✅ Controller stack runs UNMODIFIED on all 9 real TLS, full 3600 s, scales 0.3→3.0, zero exceptions.** MaxPressure's `getAllProgramLogics/getControlledLinks` parsing + green→yellow pairing all survive real irregular topology. Wk9-10 swap = **low technical risk.**
- **Clean operating point: `--scale 1.0` (~3600 veh/h) → 0–6 teleports, 93–97% completion, ~14 s wait.** Tipping at 1.3–1.5; gridlock onset ~2.0; the prior 490-teleport AADF state ≈ scale 3.0. Calibrated config committed.
- **6 SLM junctions fall out of topology:** exactly 6 of 9 TLS have ≥2 green phases (the SLM action space); 3 single-green pedestrian/merge signals excluded. Real headroom is in ~3 multi-stage clusters (5–11 links).
- ⚠️ **Latent risks:** MaxPressure skips native all-red clearance at cluster junctions (less conservative than real signal); 3 junctions are structural no-ops for MaxPressure (single green).
- ⚠️ **Scientific framing risk (the real one):** MaxPressure ≈ fixed-time on this single arterial (96.8% vs 92.8% completion) ⇒ **modest SLM performance headroom on the corridor.** Combined with §4, headline the **integrity contribution** (auth + detection, §1–§2), not a traffic-performance win.

## 4. Evaluation methodology — stats power + throughput metric — ✅ (high-impact)
Artifacts: `edge-negotiator/src/metrics.py` (+`tests/test_metrics.py`, 28 tests), `edge-negotiator/src/sweep_baselines.py`, `edge-negotiator/results/baselines_highN.md`. **148 tests pass total; no existing files modified.**

**Finding 1 — the pipeline detects real effects at n=30 (decisively).** MaxPressure beats fixed-time on every robust metric, all surviving Holm: throughput **+19.0 trips** (perm_p=2e-4), completion_rate **+0.034** (2e-4), mean_network_delay **−29.9 s** (2e-4), total_network_delay **−1754 s** (1.8e-3). ⇒ The Milestone-2 non-rejections were a **power problem (n=3)**, not a broken pipeline. **Action: Wk9-10 needs ~30 seeds.**

**Finding 2 — ⚠️ the old metric had the WRONG SIGN.** Completed-trips-only `avg_travel_time` showed MaxPressure **+33.4 s worse** (significant!) — but MaxPressure is genuinely better; it completes ~19 more trips/seed, *including the slow congested ones fixed-time strands*. Admitting those slow trips into MaxPressure's average inflates it. The robust `mean_network_delay` (counts stranded vehicles' accrued time) correctly shows MaxPressure **−29.9 s better**. The 2×2 grid is heavily oversaturated (~30% completion), which is why the confound is so stark. **Action: headline `mean_network_delay` / `completion_rate` / `throughput`; use `matched_diff` for any travel-time claim. The completed-only avg travel time is actively misleading and must be dropped as a headline.**

**Finding 3 — reinterprets Milestone-2.** The "coordinated −6.2 s vs MaxPressure" was over the biased metric; coordinated completed ~8 *fewer* trips, so on throughput-controlled metrics it is likely **no better (possibly worse)** on the oversaturated grid. The matched-set diff (shared vehicles) is **+2.07 s, not significant (p=0.47)** — i.e. on the *same* vehicles, controllers travel at indistinguishable speed; differences are about *which* vehicles get through. **Action (wave 2): re-run the SLM sweep with `--tripinfo-output.write-unfinished` and re-evaluate coordinated/uncoordinated under `metrics.py`.** Until then, the only honest Milestone-2 claim is the *mechanism*, not any performance effect.

## 6. MQTT fast-path transport — ✅
Artifacts: `edge-negotiator/src/mqtt_transport.py`, `edge-negotiator/src/bench_mqtt.py`, `tests/test_mqtt_transport.py` (16 tests), `edge-negotiator/results/mqtt_bench.md`, `MQTT-SPIKE.md`. **182 tests pass (broker up); 166+16-skipped (broker down, never red).** Verification REUSED from MessageBus, not forked.
- Real broker (eclipse-mosquitto:2, 200 msgs): **pub→verified-deliver median 5.93 ms, p95 8.18 ms** (in-process baseline 2.15/3.28 ms; broker adds ~3.8 ms). Throughput ~270 msg/s.
- **Transport is NOT the bottleneck** — p95 is ~1,200× inside the ~10 s SLM decision interval, ~12× under a 100 ms target. SLM inference dominates.
- Integrate-and-merge: one `MqttTransport(recipient, MessageBus(registry, adjacency))` per junction; publish/poll, no crypto/topology/replay change.
- ⚠️ Production: single-broker SPOF (need redundancy + bounded TTL + graceful "missing report = no update"); lossy roadside links widen p99 via QoS-1 retransmits (safe under replay guard); needs TLS/8883 + per-junction client auth/ACLs (spike was anonymous/plaintext).

## 7. SLM latency + multi-model ablation — ✅ (assumption refuted)
Artifacts: `edge-negotiator/src/bench_slm.py`, `edge-negotiator/results/slm_bench.md` (+ raw `_bench_*.json`). Real Foundry-Local GPU measurements, 60 calls/model over a 54-state battery with known argmax-optimal phase.
- **"2-8s/call" REFUTED.** Phi-4-mini: median **0.482 s**, p95 **0.553 s**, max **1.54 s** (~10× faster than the brief's worst case). >18× headroom vs the ~10 s event-gated interval; one serialising endpoint serves ~18-20 decisions / 10 s. ⇒ **per-call latency is not the risk; more SLM junctions are feasible than assumed.**
- **Ablation (a real result):** all chat models emit valid `{"phase":N}` 100%, but argmax-agreement: phi-4-mini **100%**, qwen2.5-1.5b 48%, qwen2.5-0.5b 43%, qwen-coder-0.5b 35%. Task is **format-agnostic but NOT capability-agnostic** — small models are cheap but systematically wrong (bias to last/middle index).
- **phi-4-mini-reasoning unfit (1.7% parse):** emits reasoning, blows the 16-token cap → **empirically corroborates the terse/no-CoT decision (brief §5).**
- Conclusion: keep Phi-4-mini; spend the latency headroom on coordination + shield; the MaxPressure shield is what makes a weak SLM's bad pick *safe* (vetoed) rather than dangerous.

## 8. Throughput-controlled coordination + λ-sweep — ✅ (architectural gap found)
Artifacts: `edge-negotiator/src/run_metrics_sweep.py`, `edge-negotiator/results/coord_throughput.md` (n=15 seeds, StubAgent).
- **Headline: on throughput-controlled metrics, R2 coordination is NEUTRAL** (coordinated≈uncoordinated, all λ, Holm fail-to-reject) — but see the gap below for *why* this measurement can't see an effect.
- ⚠️ **ARCHITECTURAL GAP (the real finding):** across λ=0→4 every honest metric is *byte-identical* while `coord_adj_decisions` rises 0→16. Cause: as-built `used = SLM_proposal if valid else coord_choice`, so the **Channel-B coordination term is only consulted on SLM fallback (None)**. A reliable agent (StubAgent, or Phi-4-mini @ 0 failures) never falls back ⇒ Channel-B is computed, counted, then **discarded**. The earlier live "coordinated≠uncoordinated" came *entirely via Channel-A* (the prompt note moving the real SLM's pick), not the deterministic term.
- **Decision for Wk5-6+ integration:** should the coordination-aware shield *override* a valid SLM proposal when coordination strongly disagrees (true "shield disposes"), or stay advisory? Today it's advisory-on-fallback-only. Until decided, the only causal coordination channel is the prompt (Channel-A), whose effect hinges on the SLM heeding it.
- **Honest measurement plan:** measure coordination with the REAL SLM (responds to Channel-A) under `metrics.py` + ~30 seeds; the StubAgent harness structurally cannot show a Channel-B effect.
- **✅ Real-SLM complement** (`edge-negotiator/src/run_slm_metrics.py`, `results/coord_slm_honest.md`, n=4, real Phi-4-mini, throughput-controlled): **NEUTRAL but directionally positive on every metric** — mean_network_delay −1.72 (p=0.75), completion +0.007 (p=0.39), throughput +2.25 (p=0.51), matched_diff −1.02 s (p=0.75); all CIs include 0. **Coordination provably live** (634 Channel-A notes, 1306 verified msgs, 100 coord-changed decisions) ⇒ small-effect-vs-noise, NOT a fired-nothing null. Underpowered at n=4 ("not detected", not "absent"). Channel-A *does* nudge the real SLM helpfully; **need ~30 seeds to resolve.**

## 9. Corridor coordination — grid→corridor transfer — ✅ (critical bug caught)
Artifacts: `edge-negotiator/sumo/lambeth/run_corridor_coord.py`, `edge-negotiator/results/corridor_coord.md`.
- **Integrity stack RUNS on the real corridor:** unmodified controller logic over 9 real TLS @ scale 1.0, 6 multi-green junctions as SLM set, 0 exceptions, 1089 trips/1 teleport, valid registry hash-chain. Counts (chain, seed7, 1200s): 243 verified signed msgs, 167 conservation detections (38 under_reported / 9 inflated, 47 flagged), coord_adj=3.
- ⚠️⚠️ **CRITICAL: grid edge-id parsing is silently FALSE on real OSM nets.** Real TLS ids = OSM cluster strings, edges = OSM way ids (`-634042794#2`); **0** match `f"{from}{to}"`; `_split_edge` returns None for every real edge. Unmodified it **would NOT crash — it silently no-ops coordination** (empty `toward`, 0 verified, 0 detections) and Wk9-10 would never notice. Fix proven via an explicit sumolib-derived `(src,dst)→edge` map injected through a subclass (→82 published, 243 verified). **FOLD INTO `src/`: replace name-parsing with an injected edge map.**
- ⚠️ **`MessageBus.inbox()` is O(n²)** (rescans full buffer each decision) — source of the inflated "rejected" replay counts; invisible on 4 junctions, dominates wall-clock on 9 TLS/hour. **Index before scaling.**
- Coordination did not move travel time (matches §3 modest-headroom prediction) — a realism/integrity-generalisation result, not a throughput win.

## Integration TODO (concrete `src/` changes the de-risk wave surfaced)
1. **Generalise edge resolution** in `CoordinatedController` to an injected `(src,dst)→edge` map (kills the silent corridor no-op). [§9]
2. **Index `MessageBus.inbox()`** — per-recipient delivered-set + message index, drop the O(n²) rescan. [§9]
3. **Sensor-outage reconciliation** — feed observed-only edges (registered neighbour that should have claimed but didn't) to conservation so `missing_claim` is reachable on the live path. [§2]
4. **Channel-B override decision** — make the coordination-aware shield able to override a valid SLM proposal (today advisory-on-fallback-only ⇒ no effect with a reliable SLM). [§8]
5. **Reporting**: headline `mean_network_delay`/`completion_rate`/`throughput` + matched-set; drop completed-only avg travel time (wrong sign). [§4]
6. **requirements.txt**: pin py-solc-x, paho-mqtt, pyproj, pytest, tabulate (agents added them). [§1,§6]

## 10. Scaling 2×2 → 4×4 — ✅ (inbox fix confirmed linear)
Artifacts: `edge-negotiator/sumo/grid3x3/`, `edge-negotiator/sumo/grid4x4/`, `edge-negotiator/src/run_scaling.py`, `edge-negotiator/results/scaling.md`. Grid edge-ids follow `{src}{dst}` at all sizes (no edge_map needed); StubAgent, 3 seeds each, nothing crashed.
- TLS 4/9/16: controller wall 5.78/12.56/21.93 s; per-decision 16.0/18.5/23.3 ms. **4× junctions → 3.80× wall (sub-linear); inbox() now amortised-O(1)** (microbench: per-call flat, total linear in rounds — the O(n²) is gone). **23 ms/decision @16 TLS vs 1 s tick = >40× headroom; stack is not the scaling bottleneck.**
- ⚠️ Risks (not compute): `rejected_messages` grows super-linearly (all-pairs neighbour test) → shard bus per-neighbourhood at hundreds of junctions; fixed demand confounds cross-size traffic (2×2 gridlocks @31%, 4×4 free-flows @86%) → **scale demand to network capacity** (reinforces §3).

## 11. Full 30-seed evaluation matrix — ✅ (properly powered)
Artifacts: `edge-negotiator/results/evaluation_matrix.{md,json}` via `src/run_evaluation.py` (StubAgent, throughput-controlled, n=30).
- **MaxPressure is the strongest controller, significantly** (Holm-rejected, perm-p ≤ 3e-4 on all metrics): throughput 127.8 / completion 0.333 / mnd 541.0. Fixed (109.0/0.299/570.6) and the greedy StubAgent hybrid (103.2/0.288/580.7) both **significantly worse**; coordinated≡uncoordinated (StubAgent Channel-B inert).
- **Properly-powered confirmation:** on honest metrics the SLM approach does NOT beat MaxPressure on the oversaturated grid ⇒ **integrity is the contribution, not traffic performance.** Caveat: "SLM" rows use the deterministic StubAgent proxy; the real-Phi-4 Channel-A effect is the separate underpowered-at-n=4 (directionally +vs-uncoordinated) quantity — needs a slow real-SLM n=30 run to resolve.
- Detection table (same harness): spoof P=1.0/R=0.67, faulty P=1.0/R=0.60, sybil P=1.0/R=1.0.

## 5. Milestone-2 baseline (already committed)
See `edge-negotiator/results/milestone2_report.md`. Mechanism live (974 verified signed msgs, 937 reconciliations); 120 tests; R2 causal pathway ablatable; coordinated travel-time gain survivorship-confounded (not claimed).
