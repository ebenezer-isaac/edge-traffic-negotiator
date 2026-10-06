# H1 config arms: WIRING VALIDATION (StubAgent, NOT the SLM) vs myopic MaxPressure (Euston A501)

- Controller under test: StubAgent (deterministic argmax-over-queue; NOT the SLM) -- config-arm WIRING/CAUSALITY validation only

**PILOT / SMOKE** -- n=1 per arm. Config-arm validation (each arm runs live + is genuinely wired/causal), NOT the powered sweep.

> WIRING VALIDATION ONLY -- the controller is the deterministic StubAgent, NOT the SLM. Proves the config-arm machinery is live and causal on the real net; NOT an SLM feasibility result.

- Corridor: Euston Road A501 spine (euston_spine.net.xml, 4 TLS)
- Demand: base.rou.xml (DfT-AADF-calibrated, daily resolution)
- Baseline: myopic MaxPressure (Varaiya) -- fixed reference
- Seed: 42  |  horizon: 300 s  |  event-gate: 2  |  decision interval: 10 s

- **myopic**: per-junction queues only; no coordination; no neighbour note
- **coordination**: signed neighbour exchange feeds a coordination note + a coordination-adjusted deterministic reference (coord_weight>0)
- **prediction**: coordination PLUS the +prediction lever: approaching in-motion vehicles anticipated in the reference + the note (predict_weight>0)

## Head-to-head

| Metric | MaxPressure | Stub myopic | Stub coordination | Stub prediction |
|---|---|---|---|---|
| completed (arrival>=0) | 126 | 126 | 126 | 126 |
| departed | 224 | 224 | 224 | 224 |
| running at end | 98 | 98 | 98 | 98 |
| mean network delay (s) | 91.25 | 91.25 | 91.25 | 91.25 |
| median completed travel (s) | 75.00 | 75.00 | 75.00 | 75.00 |
| teleports | 0 | 0 | 0 | 0 |
| SLM choose_phase P99 (s) | -- | 0.000 | 0.000 | 0.000 |
| audit verify_chain | yes | yes | yes | yes |

## Per-config verdict + coordination liveness

### myopic
- **match** on delay: baseline 91.25 s vs SLM 91.25 s (delta 0.00 s, 0%)
- choose_phase latency P50/P95/P99 = 0.000/0.000/0.000 s (n=49)
- served-by: slm=41, shield=0, anti_starvation=17; SLM valid proposals=50, notes forwarded=0
- coordination: n/a (myopic arm, no coordination layer)

### coordination
- **match** on delay: baseline 91.25 s vs SLM 91.25 s (delta 0.00 s, 0%)
- choose_phase latency P50/P95/P99 = 0.000/0.000/0.000 s (n=49)
- served-by: slm=41, shield=0, anti_starvation=17; SLM valid proposals=50, notes forwarded=0
- coordination WIRING: 50 signed messages published, 62 verified received, 187 rejected (window 30 s)
- coordination CAUSAL: coord_weight=1.0, adjusted-reference changed 0 decisions; prediction (predict_weight=0.0) changed 0 decisions -- STRUCTURAL ZERO on this substrate (honest §3 finding)

### prediction
- **match** on delay: baseline 91.25 s vs SLM 91.25 s (delta 0.00 s, 0%)
- choose_phase latency P50/P95/P99 = 0.000/0.000/0.000 s (n=49)
- served-by: slm=41, shield=0, anti_starvation=17; SLM valid proposals=50, notes forwarded=30
- coordination WIRING: 50 signed messages published, 62 verified received, 187 rejected (window 30 s)
- coordination CAUSAL: coord_weight=1.0, adjusted-reference changed 2 decisions; prediction (predict_weight=1.0) changed 2 decisions

## Simplest config reaching parity-or-better (proto scale-threshold)

- Simplest config at parity-or-better: **myopic**
- Per-config status: {'myopic': 'match', 'coordination': 'match', 'prediction': 'match'}
- SMOKE n=1: descriptive only. The powered feasibility MAP over {model} x {config} + a real scale threshold is phase 2, gated on time-resolved demand (§8).

## Caveats

- WIRING VALIDATION ONLY: the controller is the deterministic StubAgent, NOT the SLM. This run proves the config-arm machinery is live + causal on the real net; it is NOT an SLM feasibility result (D-H1-perf).
- PILOT: demand is DfT daily-AADF magnitude+mix; temporal profile assumed -> inferential claims GATED until time-resolved TfL counts land (§8).
- SMOKE: n=1, short horizon -> descriptive only, NO significance claim.
- Audit layer LIVE on every arm (signed hash-chain + Merkle inclusion proof).
- Baseline is myopic MaxPressure; the config arms vary only the controller's information, never the MaxPressure safety floor.
