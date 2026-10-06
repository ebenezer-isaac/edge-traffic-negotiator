# H1 config arms: SLM controller vs myopic MaxPressure (Euston A501)

- Controller under test: on-device SLM (phi-4-mini via Foundry Local)

**PILOT / SMOKE** -- n=1 per arm. Config-arm validation (each arm runs live + is genuinely wired/causal), NOT the powered sweep.

- Corridor: Euston Road A501 spine (euston_spine.net.xml, 4 TLS)
- Demand: base.rou.xml (DfT-AADF-calibrated, daily resolution)
- Baseline: myopic MaxPressure (Varaiya) -- fixed reference
- Seed: 42  |  horizon: 300 s  |  event-gate: 2  |  decision interval: 10 s

- **myopic**: per-junction queues only; no coordination; no neighbour note
- **coordination**: signed neighbour exchange feeds a coordination note + a coordination-adjusted deterministic reference (coord_weight>0)
- **prediction**: coordination PLUS the +prediction lever: approaching in-motion vehicles anticipated in the reference + the note (predict_weight>0)

## Head-to-head

| Metric | MaxPressure | SLM myopic | SLM coordination | SLM prediction |
|---|---|---|---|---|
| completed (arrival>=0) | 126 | 126 | 126 | 124 |
| departed | 224 | 224 | 224 | 224 |
| running at end | 98 | 98 | 98 | 100 |
| mean network delay (s) | 91.25 | 91.25 | 91.25 | 91.29 |
| median completed travel (s) | 75.00 | 75.00 | 75.00 | 74.50 |
| teleports | 0 | 0 | 0 | 0 |
| SLM choose_phase P99 (s) | -- | 0.570 | 0.601 | 0.804 |
| audit verify_chain | yes | yes | yes | yes |

## Per-config verdict + coordination liveness

### myopic
- **match** on delay: baseline 91.25 s vs SLM 91.25 s (delta 0.00 s, 0%)
- choose_phase latency P50/P95/P99 = 0.473/0.546/0.570 s (n=49)
- served-by: slm=41, shield=0, anti_starvation=17; SLM valid proposals=50, notes forwarded=0
- coordination: n/a (myopic arm, no coordination layer)

### coordination
- **match** on delay: baseline 91.25 s vs SLM 91.25 s (delta 0.00 s, 0%)
- choose_phase latency P50/P95/P99 = 0.483/0.526/0.601 s (n=49)
- served-by: slm=41, shield=0, anti_starvation=17; SLM valid proposals=50, notes forwarded=0
- coordination WIRING: 50 signed messages published, 62 verified received, 187 rejected (window 30 s)
- coordination CAUSAL: coord_weight=1.0, adjusted-reference changed 0 decisions; prediction (predict_weight=0.0) changed 0 decisions -- STRUCTURAL ZERO on this substrate (honest §3 finding)

### prediction
- **match** on delay: baseline 91.25 s vs SLM 91.29 s (delta 0.04 s, 0.0%)
- choose_phase latency P50/P95/P99 = 0.524/0.692/0.804 s (n=50)
- served-by: slm=41, shield=0, anti_starvation=18; SLM valid proposals=51, notes forwarded=31
- coordination WIRING: 51 signed messages published, 62 verified received, 190 rejected (window 30 s)
- coordination CAUSAL: coord_weight=1.0, adjusted-reference changed 2 decisions; prediction (predict_weight=1.0) changed 2 decisions

## Simplest config reaching parity-or-better (proto scale-threshold)

- Simplest config at parity-or-better: **myopic**
- Per-config status: {'myopic': 'match', 'coordination': 'match', 'prediction': 'match'}
- SMOKE n=1: descriptive only. The powered feasibility MAP over {model} x {config} + a real scale threshold is phase 2, gated on time-resolved demand (§8).

## Caveats

- PILOT: demand is DfT daily-AADF magnitude+mix; temporal profile assumed -> inferential claims GATED until time-resolved TfL counts land (§8).
- SMOKE: n=1, short horizon -> descriptive only, NO significance claim.
- Audit layer LIVE on every arm (signed hash-chain + Merkle inclusion proof).
- Baseline is myopic MaxPressure; the config arms vary only the controller's information, never the MaxPressure safety floor.
