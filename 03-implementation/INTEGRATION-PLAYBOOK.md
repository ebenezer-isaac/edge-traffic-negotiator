# Integration Playbook — Wk 5-10 (de-risked, integrate-and-merge)

Every step below is backed by hard data + a ready module from the de-risk wave (branch
`experiments/de-risk`). Read alongside `DE-RISK-INDEX.md` (the evidence) and `PROJECT-DECISION-BRIEF.md`
(the plan). Status: the *mechanism* and *de-risk* are done; this is the ordered path to fold them in.

## Pre-merge housekeeping
- Merge `experiments/de-risk` → `main` (review first). Branch holds 3 commits: Milestone-2, de-risk wave, wave-3.
- `requirements.txt` already pins the new deps (py-solc-x, paho-mqtt, pyproj, pytest, tabulate).
- **Drop the misleading metric:** stop reporting completed-only avg travel time; headline `metrics.py` `mean_network_delay` / `completion_rate` / `throughput` + `matched_diff`. (§4 — it had the wrong sign.)

## Wk 5-6 — Besu permissioned registry
**Ready:** `contracts/AgentRegistry.sol`, `src/besu_registry.py` (verified drop-in for `Registry`), `src/bench_ledger.py`, `src/bench_qbft.py`, `BESU-SPIKE.md`, `QBFT-SPIKE.md`.
1. Stand up 4-validator QBFT (compose recipe in QBFT-SPIKE.md). **Pin `besu:24.12.0`**, gas-free.
2. Deploy `AgentRegistry.sol` — compile recent EVM fork (Shanghai/Cancun) so the `paris`/PUSH0 pin can be dropped.
3. Swap `Registry` → `BesuRegistry` at construction; `MessageBus(BesuRegistry(...), adjacency)` works unchanged (verified).
4. **Never put a write on the control loop** (~2.1s commit, block-period-dominated). Buffer audit events, flush off-loop (batched tx / Merkle anchoring); membership checks hit a locally-cached allowlist refreshed from `AgentRegistered`/`AgentRevoked` events.
5. web3 `get_block` needs `ExtraDataToPOAMiddleware` under QBFT (writes/reads via the adapter are unaffected).
- **Numbers to expect:** register ~2.1s, reads ~15ms. Validate the async assumption holds (it does).

## Wk 7-8 — Attacks + detection
**Ready:** `src/attacks.py`, `src/run_attacks.py`, `tests/test_attacks.py`, `results/attacks_report.md`, `THREAT-MODEL-ANALYSIS.md`.
1. Enable the sensor-outage capability project-wide: pass `reconcile_silent_neighbours=True` at the call sites and update the two `test_attacks.py` assertions that currently document the (now-closable) outage gap (§2).
2. Run the 3 scenarios; headline precision/recall/F1 + detection latency. Expect P=1.0; recall<1 only on within-tolerance lies; **report collusion recall=0 honestly** (Xiao limit — containment via `revoke` + audit, not detection).
3. Tolerance is the false-alarm knob (ROC in attacks_report.md): tol=2 gave 0 false alarms; tol=0 catches sub-tolerance lies but false-alarms on honest jitter.

## Wk 9-10 — Lambeth corridor + full sweep
**Ready:** `sumo/lambeth/{lambeth_spine.net.xml, lambeth_spine.sumocfg, base.rou.xml, run_lambeth.py, run_corridor_coord.py}`, `results/{lambeth_controllability.md, corridor_coord.md}`, `src/sweep_baselines.py`, `src/stats.py`, `src/metrics.py`, `src/run_slm_metrics.py`.
1. Controller runs unmodified on the 9 real TLS; **use `--scale 1.0`** (clean, ≤6 teleports). SLM set = the **6 multi-green TLS** (3 single-green signals excluded; headroom is in ~3 cluster junctions).
2. **Use the injected edge-map** — `CoordinatedController(edge_map=edge_map_from_net(net, mode))`. The grid `f"{src}{dst}"` parse silently no-ops on real OSM ids (§9, the critical catch). Corridor run confirmed 65 verified msgs / 47 detections this way.
3. Run the sweep with **`--tripinfo-output.write-unfinished --tripinfo-output.write-undeparted`** (see `run_slm_metrics.py`) so `metrics.py` sees the whole vehicle population.
4. **~30 seeds** (n=3-4 is underpowered: the n=30 baseline sweep proved the pipeline finds real effects, §4; the real-SLM coordination effect was directionally positive but sub-noise at n=4, §8).
5. Stats via `stats.py` (BCa + paired permutation + Holm). Headline robust metrics + `matched_diff`.
6. Scale demand to corridor capacity (fixed demand confounds, §10).
- **Honest expectation:** modest/neutral performance signal (MaxPressure≈fixed on this single arterial). **The contribution is the verified-source integrity layer, not a traffic-performance win** — frame accordingly.

## Performance/scaling notes (de-risked)
- SLM latency ~0.48s/call (the "2-8s" was refuted) → one endpoint serves ~18-20 serial decisions / 10s; more SLM junctions feasible.
- MQTT fast path ~6ms p50 (`src/mqtt_transport.py`) — not the bottleneck; production needs broker redundancy + TLS/8883 + per-junction auth.
- `MessageBus.inbox()` is now amortised-O(1) (§10); `rejected`-msg all-pairs growth → shard the bus per-neighbourhood at hundreds of junctions.
- Keep Phi-4-mini (terse task is NOT model-agnostic: Qwen 35-48% vs Phi 100%, §7); the shield makes weak picks safe.

## Open design decision (not yet made)
**Channel-B override** (`coord_override`, default off): should the coordination-aware shield override a *valid* SLM proposal when it strongly disagrees? Today coordination enters only via the Channel-A prompt note; with a reliable SLM the deterministic term is advisory-only (§8). Decide before the corridor sweep — it determines whether coordination has a deterministic causal channel or relies entirely on the SLM heeding the prompt.
