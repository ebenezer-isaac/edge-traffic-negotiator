# H1 headline: on-device SLM controller vs MaxPressure (Euston A501)

**PILOT / SMOKE** -- n=1, myopic config. NOT the powered sweep, NOT a significance claim.

- Corridor: Euston Road A501 spine (euston_spine.net.xml, 4 TLS)
- Demand: base.rou.xml (DfT-AADF-calibrated, daily resolution)
- Seed: 42  |  horizon (sim end): 300 s  |  event-gate: 2  |  decision interval: 10 s

## Head-to-head

| Metric | MaxPressure (baseline) | SLM (phi-4-mini, myopic) |
|---|---|---|
| completed (arrival>=0) | 126 | 126 |
| departed | 224 | 224 |
| running at end | 98 | 98 |
| mean network delay (s) | 91.25 | 91.25 |
| median completed travel time (s) | 75.00 | 75.00 |
| avg completed travel time (s, biased) | 81.97 | 81.97 |
| teleports | 0 | 0 |
| SLM choose_phase P50 / P99 (s) | -- | 0.486 / 0.634 |
| audit verify_chain | yes | yes |
| audit decision records | 58 | 58 |
| Merkle inclusion proof | yes | yes |

## Verdict (delay, this config)

- **match** on mean_network_delay_s (lower is better)
- baseline delay 91.25 s vs SLM 91.25 s (SLM - baseline = 0.00 s, 0%)
- **Real-time viability**: choose_phase P50=0.486 s, P95=0.526 s, P99=0.634 s vs 10 s interval -- P99 within interval: yes
- SLM calls: 50 (None/invalid -> shield fallback: 0)
- Served-by breakdown (58 decisions): 41 served by a valid SLM proposal (41 agreed with the MaxPressure shield, 0 diverged from it), 0 served by the MaxPressure shield (0 of which were SLM None/invalid fallbacks), 17 FORCED by the anti-starvation fairness shield (NOT SLM-authored -- the fairness override, neither the SLM proposal nor MaxPressure's argmax).
- The SLM issued 50 valid proposals in total (participation); authorship of the SERVED phase is the served-by breakdown above. An anti-starvation override interval is attributed to the shield, never to the SLM.

## Caveats

- PILOT: demand is DfT daily-AADF magnitude+mix; temporal profile assumed -> inferential claims GATED until time-resolved TfL counts land (§8).
- SMOKE: n=1, short horizon -> descriptive only, NO significance claim.
- Audit layer LIVE on both arms (signed hash-chain + Merkle inclusion proof).
