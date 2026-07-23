# H1: delay AND throughput (does the delay win cost throughput?)

**qwen2.5-0.5b x myopic is a CLEAN WIN: delay 235.0s (-25.3%) AND throughput 472 completed (+111 vs baseline 361, +30.7%). The delay win does NOT cost throughput -- it improves both.**

- Question: does the SLM's delay win sacrifice throughput? (MaxPressure is throughput-optimal by design, Akin)
- Baseline MaxPressure: delay 314.5 s, completed 361 (throughput), departed 624, completion rate 0.579

| Model x config | Delay (s) | Delay | Completed | Throughput | Joint |
|---|---|---|---|---|---|
| qwen2.5-0.5b x myopic | 235.0 | beats -25.3% | 472 (+111) | beats +30.7% | **clean win** |
| qwen2.5-0.5b x coordination | 235.0 | beats -25.3% | 472 (+111) | beats +30.7% | **clean win** |
| qwen2.5-0.5b x prediction | 297.9 | beats -5.3% | 392 (+31) | beats +8.6% | **clean win** |
| qwen2.5-1.5b x myopic | 306.9 | beats -2.4% | 383 (+22) | beats +6.1% | **clean win** |
| qwen2.5-1.5b x coordination | 306.9 | beats -2.4% | 383 (+22) | beats +6.1% | **clean win** |
| qwen2.5-1.5b x prediction | 315.1 | match +0.2% | 366 (+5) | match +1.4% | **match** |
| phi-4-mini-reasoning x myopic | -- | SKIP | -- | -- | -- |
| phi-4-mini-reasoning x coordination | -- | SKIP | -- | -- | -- |
| phi-4-mini-reasoning x prediction | -- | SKIP | -- | -- | -- |
| phi-4-mini x myopic | 314.7 | match +0.1% | 360 (-1) | match -0.3% | **match** |
| phi-4-mini x coordination | 314.7 | match +0.1% | 360 (-1) | match -0.3% | **match** |
| phi-4-mini x prediction | 295.8 | beats -5.9% | 389 (+28) | beats +7.8% | **clean win** |

- Clean wins: 6   |   trade-offs: 0
- Descriptive PILOT lens on committed data (n=1/cell); no significance claim. Completion counts comparable (same net+demand+seed).
