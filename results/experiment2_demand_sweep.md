# Experiment 2: demand sweep (system-level trade-offs)

Seeds=3 (paired), steps=400, modes=nopreempt, maxpressure_preempt, defended, naive. Metrics from SUMO tripinfo; headline deltas carry BCa 95% CIs.

## Per-scale headline deltas (paired on seed)

### scale = 1.0
| effect | mean | 95% CI |
|---|---|---|
| ev_benefit_s (nopreempt-defended amb) | 28.333 | [24.0, 32.0] |
| coordination_gain_s (mpp-defended amb) | -3.333 | [-8.0, 0.333] |
| no_harm_netdelay_s (defended-mpp) | -0.709 | [-1.674, 0.201] |
| attack_worstcase_avoided_s (naive-defended, J2) | 10.403 | [0.63, 19.973] |
| fairness_gain_jain (defended-naive) | 0.143 | [0.094, 0.177] |

### scale = 2.0
| effect | mean | 95% CI |
|---|---|---|
| ev_benefit_s (nopreempt-defended amb) | 38.667 | [13.0, 54.0] |
| coordination_gain_s (mpp-defended amb) | 13.333 | [1.0, 20.333] |
| no_harm_netdelay_s (defended-mpp) | -1.214 | [-2.929, -0.284] |
| attack_worstcase_avoided_s (naive-defended, J2) | 13.933 | [-16.16, 43.457] |
| fairness_gain_jain (defended-naive) | 0.025 | [0.007, 0.036] |
