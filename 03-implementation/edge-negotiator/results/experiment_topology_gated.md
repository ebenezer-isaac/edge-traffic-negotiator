# H1 multi-topology: which model wins where, and why

Models: ['qwen2.5-0.5b', 'qwen3-0.6b']  |  seed 42  |  horizon 1200s  |  topologies: ['euston_corridor', 'bloomsbury_grid', 'grid3x3', 'grid4x4']

## euston_corridor (real linear arterial (A501), 4 signals)
- MaxPressure baseline: delay 314.5s, completed 361/624, teleports 65

| Model | Delay (s) | Delay | Completed | Throughput | Joint | P99 |
|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 269.4 | beats -14.4% | 428 | beats | **clean_win** | 0.24 |
| qwen3-0.6b | 242.4 | beats -22.9% | 460 | beats | **clean_win** | 0.47 |

## bloomsbury_grid (REAL London grid (Bloomsbury WC1, 9 signals), 9 signals)
- MaxPressure baseline: delay 516.7s, completed 267/1393, teleports 105

| Model | Delay (s) | Delay | Completed | Throughput | Joint | P99 |
|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 552.2 | loses 6.9% | 208 | loses | **regression** | 0.24 |
| qwen3-0.6b | 522.2 | match 1.1% | 269 | match | **match** | 0.47 |

## grid3x3 (synthetic 3x3 grid (more routes), 9 signals)
- MaxPressure baseline: delay 301.4s, completed 630/991, teleports 0

| Model | Delay (s) | Delay | Completed | Throughput | Joint | P99 |
|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 467.5 | loses 55.1% | 320 | loses | **regression** | 0.23 |
| qwen3-0.6b | 429.4 | loses 42.5% | 346 | loses | **regression** | 0.50 |

## grid4x4 (synthetic 4x4 grid (most routes), 16 signals)
- MaxPressure baseline: delay 143.2s, completed 1000/1000, teleports 0

| Model | Delay (s) | Delay | Completed | Throughput | Joint | P99 |
|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 279.0 | loses 94.9% | 732 | loses | **regression** | 0.22 |
| qwen3-0.6b | 172.9 | loses 20.8% | 933 | loses | **regression** | 0.50 |

## Explanatory analysis (WHY the advantage varies)

- Hypothesis: the SLM's delay+throughput advantage appears where MaxPressure gridlocks (teleports>0) and disappears where the network self-regulates (free-flowing, zero teleports)
- Trend across cells: **regime separation (n=8 cells, DESCRIPTIVE): the SLM WINS only where MaxPressure gridlocks (teleports>0) and LOSES on free-flowing nets (mean win congested 7.3% vs free-flowing -53.3%). Across all topologies r=0.67, but this is driven by the free-vs-congested split, NOT a graded law: WITHIN the congested nets the direction INVERTS (more gridlock -> smaller win) (r_congested=-0.95). So the honest claim is a congestion-REGIME effect, not 'win grows monotonically with gridlock'. n=1 seed/cell: not a significance test.**

| Topology | Model | Baseline gridlock proxy | Delay win % | Joint |
|---|---|---|---|---|
| euston_corridor | qwen2.5-0.5b | 107.1 (tp 65, stranded 0.421) | +14.4 | clean_win |
| euston_corridor | qwen3-0.6b | 107.1 (tp 65, stranded 0.421) | +22.9 | clean_win |
| bloomsbury_grid | qwen2.5-0.5b | 185.8 (tp 105, stranded 0.808) | -6.9 | regression |
| bloomsbury_grid | qwen3-0.6b | 185.8 (tp 105, stranded 0.808) | -1.1 | match |
| grid3x3 | qwen2.5-0.5b | 36.4 (tp 0, stranded 0.364) | -55.1 | regression |
| grid3x3 | qwen3-0.6b | 36.4 (tp 0, stranded 0.364) | -42.5 | regression |
| grid4x4 | qwen2.5-0.5b | 0.0 (tp 0, stranded 0.0) | -94.9 | regression |
| grid4x4 | qwen3-0.6b | 0.0 (tp 0, stranded 0.0) | -20.8 | regression |

- Mechanism HYPOTHESIS (not demonstrated at n=1): MaxPressure is throughput-optimal and near-ideal when traffic flows freely, so the SLM's waiting-time-aware policy only adds latency there; when MaxPressure gridlocks, queue management has headroom to help.

> DESCRIPTIVE multi-topology pilot (n=1/cell); inferential significance §8-gated. Grids are SYNTHETIC contrasts to the real Euston corridor; real-London multi-area OSM nets are the next infra step (harness is net-agnostic). Which model wins where + WHY, from the joint verdicts.
