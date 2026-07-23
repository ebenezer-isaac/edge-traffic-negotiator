# H1 multi-topology: which model wins where, and why

Models: ['qwen2.5-0.5b', 'qwen3-0.6b']  |  seed 42  |  horizon 1200s  |  topologies: ['euston_corridor', 'bloomsbury_grid', 'grid3x3', 'grid4x4']

## euston_corridor (real linear arterial (A501), 4 signals)
- MaxPressure baseline: delay 314.5s, completed 361/624, teleports 65

| Model | Delay (s) | Delay | Completed | Throughput | Joint | P99 |
|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 235.0 | beats -25.3% | 472 | beats | **clean_win** | 0.25 |
| qwen3-0.6b | 267.1 | beats -15.1% | 411 | beats | **clean_win** | 0.50 |

## bloomsbury_grid (REAL London grid (Bloomsbury WC1, 9 signals), 9 signals)
- MaxPressure baseline: delay 516.7s, completed 267/1393, teleports 105

| Model | Delay (s) | Delay | Completed | Throughput | Joint | P99 |
|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 542.5 | loses 5.0% | 251 | loses | **regression** | 0.24 |
| qwen3-0.6b | 507.2 | match -1.8% | 299 | beats | **clean_win** | 0.47 |

## grid3x3 (synthetic 3x3 grid (more routes), 9 signals)
- MaxPressure baseline: delay 301.4s, completed 630/991, teleports 0

| Model | Delay (s) | Delay | Completed | Throughput | Joint | P99 |
|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 483.1 | loses 60.3% | 300 | loses | **regression** | 0.25 |
| qwen3-0.6b | 412.7 | loses 36.9% | 366 | loses | **regression** | 0.52 |

## grid4x4 (synthetic 4x4 grid (most routes), 16 signals)
- MaxPressure baseline: delay 143.2s, completed 1000/1000, teleports 0

| Model | Delay (s) | Delay | Completed | Throughput | Joint | P99 |
|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 304.1 | loses 112.4% | 713 | loses | **regression** | 0.22 |
| qwen3-0.6b | 202.2 | loses 41.2% | 879 | loses | **regression** | 0.47 |

## Explanatory analysis (WHY the advantage varies)

- Hypothesis: the SLM's delay+throughput advantage appears where MaxPressure gridlocks (teleports>0) and disappears where the network self-regulates (free-flowing, zero teleports)
- Trend across cells: **regime separation (n=8 cells, DESCRIPTIVE): the SLM WINS only where MaxPressure gridlocks (teleports>0) and LOSES on free-flowing nets (mean win congested 9.3% vs free-flowing -62.7%). Across all topologies r=0.73, but this is driven by the free-vs-congested split, NOT a graded law: WITHIN the congested nets the direction INVERTS (more gridlock -> smaller win) (r_congested=-0.93). So the honest claim is a congestion-REGIME effect, not 'win grows monotonically with gridlock'. n=1 seed/cell: not a significance test.**

| Topology | Model | Baseline gridlock proxy | Delay win % | Joint |
|---|---|---|---|---|
| euston_corridor | qwen2.5-0.5b | 107.1 (tp 65, stranded 0.421) | +25.3 | clean_win |
| euston_corridor | qwen3-0.6b | 107.1 (tp 65, stranded 0.421) | +15.1 | clean_win |
| bloomsbury_grid | qwen2.5-0.5b | 185.8 (tp 105, stranded 0.808) | -5.0 | regression |
| bloomsbury_grid | qwen3-0.6b | 185.8 (tp 105, stranded 0.808) | +1.8 | clean_win |
| grid3x3 | qwen2.5-0.5b | 36.4 (tp 0, stranded 0.364) | -60.3 | regression |
| grid3x3 | qwen3-0.6b | 36.4 (tp 0, stranded 0.364) | -36.9 | regression |
| grid4x4 | qwen2.5-0.5b | 0.0 (tp 0, stranded 0.0) | -112.4 | regression |
| grid4x4 | qwen3-0.6b | 0.0 (tp 0, stranded 0.0) | -41.2 | regression |

- Mechanism HYPOTHESIS (not demonstrated at n=1): MaxPressure is throughput-optimal and near-ideal when traffic flows freely, so the SLM's waiting-time-aware policy only adds latency there; when MaxPressure gridlocks, queue management has headroom to help.

> DESCRIPTIVE multi-topology pilot (n=1/cell); inferential significance §8-gated. Grids are SYNTHETIC contrasts to the real Euston corridor; real-London multi-area OSM nets are the next infra step (harness is net-agnostic). Which model wins where + WHY, from the joint verdicts.
