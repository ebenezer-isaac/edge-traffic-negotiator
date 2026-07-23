# H1 multi-seed robustness: qwen2.5-0.5b x myopic

**Across 5 seeds: mean delay 270.5s vs 305.9s baseline (-11.6%); mean throughput 413 vs 367 completed (+12.6%); 4/5 seeds a clean win on both. Mixed across seeds (see per-seed).**

- Seeds: [42, 1, 2, 3, 7]  |  horizon 1200s
- Delay wins: 4/5  |  throughput wins: 3/5  |  joint: {'clean_win': 4, 'trade_off': 0, 'match': 0, 'regression': 1}

## Per seed

| Seed | Baseline delay | SLM delay | Baseline compl | SLM compl | Joint |
|---|---|---|---|---|---|
| 42 | 314.5 | 235.0 | 361 | 472 | clean_win |
| 1 | 373.9 | 304.3 | 281 | 362 | clean_win |
| 2 | 275.3 | 267.6 | 414 | 415 | clean_win |
| 3 | 275.9 | 284.2 | 403 | 396 | regression |
| 7 | 289.8 | 261.6 | 376 | 422 | clean_win |

## Aggregate (mean +/- std)

- baseline_delay_s: 305.9 +/- 36.9 (min 275.3, max 373.9, n=5)
- slm_delay_s: 270.5 +/- 23.1 (min 235.0, max 304.3, n=5)
- baseline_completed: 367 +/- 46.9 (min 281, max 414, n=5)
- slm_completed: 413.4 +/- 35.9 (min 362, max 472, n=5)

> DESCRIPTIVE multi-seed robustness (Akin), NOT a powered n>=30 significance test -- demand is DfT daily-resolution so inferential significance stays §8-gated until time-resolved TfL counts. A win that holds across seeds is far stronger than a single draw.
