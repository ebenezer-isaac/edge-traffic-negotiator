# High-N baseline sweep: fixed-time vs MaxPressure (2x2 grid)

Deterministic sweep, **n=30 seeds** (seeds 1..30), END=1000 sim-steps, no Foundry Local. Baseline = **fixed**; positive direction = MaxPressure should beat fixed-time.

Tripinfo emitted with `--tripinfo-output.write-unfinished --tripinfo-output.write-undeparted`, so metrics see the WHOLE vehicle population (loaded/departed/completed/running), not just survivors. Stats: BCa 95% CIs + paired permutation (10k) + Holm across the family.

## OLD metric -- mean travel time over COMPLETED trips only (survivorship-biased)

`metric = avg_travel_time_completed`

| group | n | mean | ci_lo | ci_hi | diff_vs_baseline | diff_ci_lo | diff_ci_hi | diff_excludes_zero | perm_p | holm_threshold | holm_reject |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed | 30 | 130.02 | 127.26 | 132.78 | nan | nan | nan | False | nan | nan | False |
| maxpressure | 30 | 163.46 | 148.18 | 184.99 | 33.439 | 18.457 | 54.161 | True | 0.00060 | 0.05000 | True |

## Throughput -- completed-trip count (cannot be gamed by stranding)

`metric = throughput`

| group | n | mean | ci_lo | ci_hi | diff_vs_baseline | diff_ci_lo | diff_ci_hi | diff_excludes_zero | perm_p | holm_threshold | holm_reject |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed | 30 | 109.40 | 105.30 | 115.09 | nan | nan | nan | False | nan | nan | False |
| maxpressure | 30 | 128.43 | 120.50 | 138.77 | 19.033 | 10.467 | 28.267 | True | 0.00020 | 0.05000 | True |

## Completion rate -- completed / departed

`metric = completion_rate`

| group | n | mean | ci_lo | ci_hi | diff_vs_baseline | diff_ci_lo | diff_ci_hi | diff_excludes_zero | perm_p | holm_threshold | holm_reject |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed | 30 | 0.30 | 0.29 | 0.31 | nan | nan | nan | False | nan | nan | False |
| maxpressure | 30 | 0.33 | 0.32 | 0.35 | 0.034 | 0.019 | 0.050 | True | 0.00020 | 0.05000 | True |

## NEW metric -- mean time-in-network over ALL departed vehicles (robust)

`metric = mean_network_delay`

| group | n | mean | ci_lo | ci_hi | diff_vs_baseline | diff_ci_lo | diff_ci_hi | diff_excludes_zero | perm_p | holm_threshold | holm_reject |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed | 30 | 569.89 | 559.58 | 577.59 | nan | nan | nan | False | nan | nan | False |
| maxpressure | 30 | 540.04 | 525.61 | 551.83 | -29.856 | -43.468 | -15.958 | True | 0.00020 | 0.05000 | True |

## NEW metric -- total outstanding network delay (completed + still-running)

`metric = total_network_delay`

| group | n | mean | ci_lo | ci_hi | diff_vs_baseline | diff_ci_lo | diff_ci_hi | diff_excludes_zero | perm_p | holm_threshold | holm_reject |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed | 30 | 207003.80 | 206188.94 | 207708.28 | nan | nan | nan | False | nan | nan | False |
| maxpressure | 30 | 205249.77 | 204290.92 | 206024.03 | -1754.033 | -2758.764 | -770.826 | True | 0.00180 | 0.05000 | True |

## Matched-set comparison (apples-to-apples)

Per seed, restrict to vehicles that completed under BOTH controllers, then take MaxPressure_avg - fixed_avg over that shared set. A controller cannot win here by completing a different (faster) subset. Paired over seeds:

- matched vehicles (summed over seeds): **3053**
- mean per-seed matched diff (MaxPressure - fixed): **2.074 s** (BCa 95% CI -2.288..8.701)
- paired permutation p (diff != 0): **0.47485**, excludes_zero=no

## Verdict

**Does the n=30 pipeline detect a real effect?** YES -- throughput diff (MP-fixed) = +19.03 trips (perm_p=0.0002, Holm reject=True); mean_network_delay diff = -29.86 s (perm_p=0.0002, Holm reject=True).

**Survivorship bias check.** Old completed-only avg-travel-time diff = +33.44 s (perm_p=0.0005999). Compare its SIGN/significance to mean_network_delay above: if they disagree, the old metric was being driven by which trips completed, not by genuinely faster travel -- exactly the Milestone-2 confound.
