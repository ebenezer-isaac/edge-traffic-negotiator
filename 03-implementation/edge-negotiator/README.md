# edge-negotiator — implementation

Build for *The Edge Negotiator: Verified-Source Cross-Junction Coordination for SLM-Driven Traffic Signal Control*. See `../PROJECT-DECISION-BRIEF.md` for the locked design and `../../00-SCOPE-LOCKIN.md` for scope.

## Status

### Wk 1-2 grid pipeline ✅
- ✅ 2×2 SUMO grid scenario (`sumo/`) — 4 signalised junctions (`A0,A1,B0,B1`), seeded random demand.
- ✅ Deterministic controllers (`src/controllers.py`) — **MaxPressure** (baseline + safety shield) and Fixed-time.
- ✅ End-to-end TraCI runner (`src/run_baseline.py`) — verified: MaxPressure beats fixed-time (lower waiting, higher throughput).
- ✅ SLM junction agent (`src/slm_agent.py`) — Phi-4-mini via Foundry Local, terse `{"phase": N}`, turnkey endpoint discovery. Validated: 90 live decisions at A0, 0 failures.
- ✅ Hybrid controller (`src/hybrid_controller.py` + `src/run_hybrid.py`) — SLM proposes, MaxPressure shield disposes, event-gated.

### Wk 3-4 Milestone 2 — authenticated cross-junction coordination ✅ (mechanism)
- ✅ **Cryptographic identity** (`src/identity.py`) — per-junction Ed25519 keypairs (DER pubkeys = the bytes that go on-chain later); `sign`/`verify`, hostile-input-safe.
- ✅ **Permissioned registry** (`src/registry.py`) — approved-agent allowlist + `revoke()` + **hash-chained tamper-evident audit log** (`verify_chain()`); local stand-in for the Wk 5-6 Besu registry.
- ✅ **Signed neighbour-message bus** (`src/message_bus.py`) — Ed25519-signed `{"toward": {nb: {release, queue_forecast}}}`; verifies sig + membership + topology + replay; rejects bad-sig / revoked / replay / non-neighbour.
- ✅ **Vehicle-conservation check** (`src/conservation.py`) — reconciles claimed `release` vs observed inflow; flags `inflated` / `under_reported` / `missing_*`. Detection primitive (see `../THREAT-MODEL-ANALYSIS.md`).
- ✅ **Coordinated controller** (`src/coordinated_controller.py`) — publishes signed state, consumes verified neighbour forecasts, folds per-phase incoming into a deterministic coordination-aware choice (**Channel B**, weight `coord_weight`) + the SLM prompt note (Channel A); MaxPressure shield still disposes.
- ✅ **120 tests pass** (`tests/`) — incl. adversarial: tamper, revoke, replay, impersonation, spoof-flagging, chain-tamper.
- ✅ **Live-verified** (`src/run_coordinated.py`, `src/collect_results.py`, `results/`): 974 verified signed msgs, 937 conservation reconciliations over a 3-seed sweep; R2 causal pathway ablatable (`coord_weight=0` ⇒ coordinated ≡ uncoordinated).
- ⏳ Next (Wk 5-6+): Besu QBFT registry + web3.py glue; then attacks (spoof / fault / Sybil) with precision/recall (Wk 7-8); then swap in the real **Lambeth corridor** (`sumo/lambeth/`, already extracted, AADF-calibrated GEH<5) for the 30-seed throughput-controlled sweep (Wk 9-10).

> **Honest results caveat (2×2 grid, n=3).** See `results/milestone2_report.md`. Coordinated-SLM (Channel B) shows lower avg travel time than MaxPressure (BCa CI excludes 0) **but** completes ~8 fewer trips; since avg travel time is over *completed* trips only, this is **survivorship-confounded** and is **not** claimed as a coordination win. Milestone 2's claim is the *integrity + coordination mechanism* and the *causal pathway*, not a toy-grid performance gain — that question is deferred to the real corridor with throughput-controlled metrics and 30 seeds.

## Setup

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # sumo-rl, web3, openai, foundry-local-sdk
```
Requires **SUMO 1.20+** with `SUMO_HOME` set, and **Microsoft Foundry Local** (for the SLM agent).

## Run the baselines

```bash
.venv/Scripts/python src/run_baseline.py --controller maxpressure
.venv/Scripts/python src/run_baseline.py --controller fixed --gui   # watch it
```

## Run the SLM hybrid loop

Requires Foundry Local running with the model pulled (`foundry model download phi-4-mini`).

```bash
.venv/Scripts/python src/smoke_slm.py             # agent round-trip test
.venv/Scripts/python src/run_hybrid.py --slm A0   # SLM controls A0; rest = MaxPressure
```

## Regenerate the scenario (deterministic, seed 42)

```bash
cd sumo/networks
netgenerate --grid --grid.number 2 --grid.length 200 --grid.attach-length 60 \
  --no-turnarounds --default.lanenumber 1 --tls.set A0,A1,B0,B1 -o grid2x2.net.xml
python "$SUMO_HOME/tools/randomTrips.py" -n grid2x2.net.xml -r grid2x2.rou.xml -e 1000 --period 1.0 --seed 42 --validate
```

## Layout

```
edge-negotiator/
├── sumo/
│   ├── grid2x2.sumocfg
│   └── networks/        grid2x2.net.xml, grid2x2.rou.xml
├── src/
│   ├── controllers.py   MaxPressure + FixedTime
│   └── run_baseline.py  TraCI runner + metrics (tripinfo)
└── requirements.txt
```

> Foundry Local model cache is on **C:** (`C:\Users\Ebenezer\.cache\foundry-local`) to keep large weights off the E: drive.
