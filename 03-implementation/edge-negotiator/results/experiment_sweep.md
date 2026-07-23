# H1 model x config sweep: feasibility map + scale threshold (Euston A501)

**PILOT / SMOKE** -- n=1 per cell. On-device SLM controller vs myopic MaxPressure across {model} x {config}. NOT a significance claim.

- Corridor: Euston Road A501 spine (euston_spine.net.xml, 4 TLS)
- Demand: base.rou.xml (DfT-AADF-calibrated ~1h; saturating under a controller)
- Baseline (myopic MaxPressure): completed=361, mean delay=314.55 s, teleports=65
- Seed: 42  |  horizon: 1200 s  |  gate: 2  |  decision interval: 10 s

## Feasibility map (delay verdict vs MaxPressure)

| Model | Size (GB) | Config | Verdict | SLM delay (s) | rel % | completed | SLM served/calls | P99 (s) | coord/pred changed | audit |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen2.5-0.5b | 0.68 | myopic | **slm_beats** | 235.00 | -25.3 | 472 | 157/311 | 0.293 | None/None | yes |
| qwen2.5-0.5b | 0.68 | coordination | **slm_beats** | 235.00 | -25.3 | 472 | 157/311 | 0.298 | 0/0 | yes |
| qwen2.5-0.5b | 0.68 | prediction | **slm_beats** | 297.92 | -5.3 | 392 | 185/322 | 0.311 | 56/7 | yes |
| qwen2.5-1.5b | 1.51 | myopic | **slm_beats** | 306.92 | -2.4 | 383 | 210/322 | 0.411 | None/None | yes |
| qwen2.5-1.5b | 1.51 | coordination | **slm_beats** | 306.92 | -2.4 | 383 | 210/322 | 0.431 | 27/0 | yes |
| qwen2.5-1.5b | 1.51 | prediction | **match** | 315.07 | 0.2 | 366 | 216/329 | 0.492 | 43/8 | yes |
| phi-4-mini-reasoning | 3.15 | myopic | SKIPPED | -- | -- | -- | -- | -- | -- | measured choose_phase latency ~8.5s/decision (pr |
| phi-4-mini-reasoning | 3.15 | coordination | SKIPPED | -- | -- | -- | -- | -- | -- | measured choose_phase latency ~8.5s/decision (pr |
| phi-4-mini-reasoning | 3.15 | prediction | SKIPPED | -- | -- | -- | -- | -- | -- | measured choose_phase latency ~8.5s/decision (pr |
| phi-4-mini | 3.72 | myopic | **match** | 314.71 | 0.1 | 360 | 220/315 | 0.605 | None/None | yes |
| phi-4-mini | 3.72 | coordination | **match** | 314.71 | 0.1 | 360 | 220/315 | 0.583 | 31/0 | yes |
| phi-4-mini | 3.72 | prediction | **slm_beats** | 295.84 | -5.9 | 389 | 219/316 | 0.701 | 50/11 | yes |

## Scale threshold

- **Reached**: smallest model **qwen2.5-0.5b** (0.68 GB) at simplest config **myopic** -> slm_beats (SLM 235.00 s vs baseline 314.55 s)

## Caveats

- PILOT: demand is DfT daily-AADF magnitude+mix; temporal profile assumed -> inferential claims GATED until time-resolved TfL counts land (§8).
- SMOKE: n=1 per cell -> descriptive only, NO significance claim.
- On-device only (Foundry Local); the audit layer is LIVE on every cell.
- A longer horizon than the smoke, so saturation lets 'beat' appear if any model/config achieves it; a full-hour n>=30 run is the confirmatory step.
