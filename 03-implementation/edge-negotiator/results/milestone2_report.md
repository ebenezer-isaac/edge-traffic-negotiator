> **SUPERSEDED HISTORICAL DE-RISK RECORD (pre-2026-05-31 pivot).** Dated lab-notebook measurements kept for the audit trail; the substrate here (Lambeth A23/A3) was DROPPED and the ledger/Besu framing DEMOTED. Current thesis: specs/001-edge-negotiator/MASTER-SPEC.md (Euston A501; self-referential coupling; CT-style accountability credited to prior art; Phi-4-mini). Numbers/terms below are historical, not current claims.

# Milestone-2 results (2x2 grid)

END=500 sim-steps. SLM seeds=[42, 7, 13], det seeds=[42, 7, 13].
SLM model: Phi-4-mini-instruct-generic-gpu:5


## avg_travel_time_s (baseline = maxpressure)

| group         |   n |    mean |   ci_lo |   ci_hi | is_baseline   |   diff_vs_baseline |   diff_ci_lo |   diff_ci_hi | diff_excludes_zero   |   n_pairs |     perm_p |   holm_threshold | holm_reject   |
|:--------------|----:|--------:|--------:|--------:|:--------------|-------------------:|-------------:|-------------:|:---------------------|----------:|-----------:|-----------------:|:--------------|
| fixed         |   3 | 134.73  |  129.92 | 138.053 | False         |            9.56    |         1.57 |     14.52    | True                 |         3 |   0.244176 |        0.0166667 | False         |
| maxpressure   |   3 | 125.17  |  123.44 | 126.807 | True          |          nan       |       nan    |    nan       | False                |         0 | nan        |      nan         | False         |
| uncoordinated |   3 | 125.14  |  121.76 | 127.163 | False         |           -0.03    |        -2.52 |      2.27333 | False                |         3 |   1        |        0.05      | False         |
| coordinated   |   3 | 118.943 |  114.62 | 121.19  | False         |           -6.22667 |       -13.73 |     -2.43667 | True                 |         3 |   0.244176 |        0.025     | False         |

## avg_waiting_time_s (baseline = maxpressure)

| group         |   n |    mean |   ci_lo |   ci_hi | is_baseline   |   diff_vs_baseline |   diff_ci_lo |   diff_ci_hi | diff_excludes_zero   |   n_pairs |     perm_p |   holm_threshold | holm_reject   |
|:--------------|----:|--------:|--------:|--------:|:--------------|-------------------:|-------------:|-------------:|:---------------------|----------:|-----------:|-----------------:|:--------------|
| fixed         |   3 | 69.39   |   65.97 | 71.55   | False         |           20.7733  |        13.96 |   24.66      | True                 |         3 |   0.244176 |        0.0166667 | False         |
| maxpressure   |   3 | 48.6167 |   46.83 | 50.3433 | True          |          nan       |       nan    |  nan         | False                |         0 | nan        |      nan         | False         |
| uncoordinated |   3 | 47.4233 |   44.9  | 49.2333 | False         |           -1.19333 |        -4.97 |    1.63      | False                |         3 |   0.753125 |        0.05      | False         |
| coordinated   |   3 | 45.8733 |   44.07 | 46.9733 | False         |           -2.74333 |        -7.94 |    0.0233333 | False                |         3 |   0.491051 |        0.025     | False         |

## Coordination mechanism (live, summed over coordinated seeds)

- verified signed neighbour messages consumed: **974**
- rejected messages (bad sig / revoked / replay / non-neighbour): **39783**
- conservation reconciliations performed: **937**

## Throughput (completed trips, mean over seeds)

- fixed: 109.3
- maxpressure: 113.7
- uncoordinated: 111.7
- coordinated: 104.0

> Caveat: avg_travel_time_s / avg_waiting_time_s are averaged over *completed* trips only.
> Coordinated completes ~8 fewer trips than uncoordinated/MaxPressure, so its lower travel-time
> mean is survivorship-confounded (slow trips unfinished at END=500, hence excluded) and is NOT
> claimed as a coordination win. Milestone-2 establishes the integrity + coordination MECHANISM and
> the causal pathway (coord_weight=0 ablation); the performance question is deferred to the real
> Lambeth corridor with throughput-controlled metrics and 30 seeds (Wk 9-10).
