# H1 multi-topology: which model wins where, and why

Models: ['qwen2.5-0.5b', 'qwen3.5-0.8b', 'qwen3.5-2b']  |  seed 42  |  horizon 1200s  |  topologies: ['euston_corridor']

## euston_corridor (real linear arterial (A501), 4 signals)
- MaxPressure baseline: delay 314.5s, completed 361/624, teleports 65

| Model | Delay (s) | Delay | Completed | Throughput | Joint | P99 |
|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 235.0 | beats -25.3% | 472 | beats | **clean_win** | 0.25 |
| qwen3.5-0.8b | SKIP | -- | -- | -- | -- | -- |
| qwen3.5-2b | SKIP | -- | -- | -- | -- | -- |

## Explanatory analysis (WHY the advantage varies)

- Hypothesis: the SLM's delay+throughput advantage is largest where MaxPressure gridlocks hardest (constrained/saturated topology) and narrows where the network self-regulates
- Trend across cells: **None**

| Topology | Model | Baseline gridlock proxy | Delay win % | Joint |
|---|---|---|---|---|
| euston_corridor | qwen2.5-0.5b | 107.1 (tp 65, stranded 0.421) | +25.3 | clean_win |

- Compare each row's baseline gridlock proxy (teleports + stranded%) to the delay-win size. The mechanism: MaxPressure's eager myopic switching wastes the most time exactly where gridlock compounds, so the steadier SLM controller gains most there.

> DESCRIPTIVE multi-topology pilot (n=1/cell); inferential significance §8-gated. Grids are SYNTHETIC contrasts to the real Euston corridor; real-London multi-area OSM nets are the next infra step (harness is net-agnostic). Which model wins where + WHY, from the joint verdicts.
