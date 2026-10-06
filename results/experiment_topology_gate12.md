# H1 multi-topology: which model wins where, and why

Models: ['qwen2.5-0.5b', 'qwen3-0.6b']  |  seed 42  |  horizon 1200s  |  topologies: ['euston_corridor', 'bloomsbury_grid', 'grid3x3', 'grid4x4']

## euston_corridor (real linear arterial (A501), 4 signals)
- MaxPressure baseline: delay 314.5s, completed 361/624, teleports 65

| Model | Delay (s) | Delay | Completed | Throughput | Joint | P99 |
|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 278.7 | beats -11.4% | 412 | beats | **clean_win** | 0.25 |
| qwen3-0.6b | 253.2 | beats -19.5% | 445 | beats | **clean_win** | 0.47 |

## bloomsbury_grid (REAL London grid (Bloomsbury WC1, 9 signals), 9 signals)
- MaxPressure baseline: delay 516.7s, completed 267/1393, teleports 105

| Model | Delay (s) | Delay | Completed | Throughput | Joint | P99 |
|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 554.6 | loses 7.3% | 206 | loses | **regression** | 0.24 |
| qwen3-0.6b | 532.5 | loses 3.1% | 243 | loses | **regression** | 0.50 |

## grid3x3 (synthetic 3x3 grid (more routes), 9 signals)
- MaxPressure baseline: delay 301.4s, completed 630/991, teleports 0

| Model | Delay (s) | Delay | Completed | Throughput | Joint | P99 |
|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 435.8 | loses 44.6% | 345 | loses | **regression** | 0.23 |
| qwen3-0.6b | 427.9 | loses 42.0% | 352 | loses | **regression** | 0.51 |

## grid4x4 (synthetic 4x4 grid (most routes), 16 signals)
- MaxPressure baseline: delay 143.2s, completed 1000/1000, teleports 0

| Model | Delay (s) | Delay | Completed | Throughput | Joint | P99 |
|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 252.5 | loses 76.4% | 770 | loses | **regression** | 0.22 |
| qwen3-0.6b | 183.4 | loses 28.1% | 958 | loses | **regression** | 0.50 |

## Explanatory analysis (WHY the advantage varies)

- Hypothesis: the SLM's delay+throughput advantage appears where MaxPressure gridlocks (teleports>0) and disappears where the network self-regulates (free-flowing, zero teleports)
- Trend across cells: **regime separation (n=8 cells, DESCRIPTIVE): the SLM WINS only where MaxPressure gridlocks (teleports>0) and LOSES on free-flowing nets (mean win congested 5.1% vs free-flowing -47.8%). Across all topologies r=0.71, but this is driven by the free-vs-congested split, NOT a graded law: WITHIN the congested nets the direction INVERTS (more gridlock -> smaller win) (r_congested=-0.95). So the honest claim is a congestion-REGIME effect, not 'win grows monotonically with gridlock'. n=1 seed/cell: not a significance test.**

| Topology | Model | Baseline gridlock proxy | Delay win % | Joint |
|---|---|---|---|---|
| euston_corridor | qwen2.5-0.5b | 107.1 (tp 65, stranded 0.421) | +11.4 | clean_win |
| euston_corridor | qwen3-0.6b | 107.1 (tp 65, stranded 0.421) | +19.5 | clean_win |
| bloomsbury_grid | qwen2.5-0.5b | 185.8 (tp 105, stranded 0.808) | -7.3 | regression |
| bloomsbury_grid | qwen3-0.6b | 185.8 (tp 105, stranded 0.808) | -3.1 | regression |
| grid3x3 | qwen2.5-0.5b | 36.4 (tp 0, stranded 0.364) | -44.6 | regression |
| grid3x3 | qwen3-0.6b | 36.4 (tp 0, stranded 0.364) | -42.0 | regression |
| grid4x4 | qwen2.5-0.5b | 0.0 (tp 0, stranded 0.0) | -76.4 | regression |
| grid4x4 | qwen3-0.6b | 0.0 (tp 0, stranded 0.0) | -28.1 | regression |

- Mechanism HYPOTHESIS (not demonstrated at n=1): MaxPressure is throughput-optimal and near-ideal when traffic flows freely, so the SLM's waiting-time-aware policy only adds latency there; when MaxPressure gridlocks, queue management has headroom to help.

> DESCRIPTIVE multi-topology pilot (n=1/cell); inferential significance §8-gated. Grids are SYNTHETIC contrasts to the real Euston corridor; real-London multi-area OSM nets are the next infra step (harness is net-agnostic). Which model wins where + WHY, from the joint verdicts.
