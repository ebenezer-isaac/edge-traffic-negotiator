# H2: trust coefficient (local sensing as the ultimate truth)

**PASS** &mdash; per-source trust; verified against the recipient's LOCAL SENSING (ground truth); truth nudges up (diminishing), a lie collapses trust x0.25 (extreme, asymmetric).

- Params: prior 0.5, truth-reward 0.15, lie-factor 0.25 (x, multiplicative collapse), corroboration floor 0.5.

## Trust trajectories (trust after each verified claim)

- honest (12 truths): [0.5, 0.575, 0.6387, 0.6929, 0.739, 0.7781, 0.8114, 0.8397, 0.8638, 0.8842, 0.9016, 0.9163, 0.9289]
- recovering (8 truths, 1 lie, 3 truths): [0.5, 0.575, 0.6387, 0.6929, 0.739, 0.7781, 0.8114, 0.8397, 0.8638, 0.2159, 0.3335, 0.4335, 0.5185]
- persistent liar (3 truths, 3 lies): [0.5, 0.575, 0.6387, 0.6929, 0.1732, 0.0433, 0.0108]
- flaky (truth/lie x5): [0.5, 0.575, 0.1437, 0.2722, 0.068, 0.2078, 0.052, 0.1942, 0.0485, 0.1913, 0.0478]

## Final trust

| Source | Trust | Truths | Lies | Can corroborate? |
|---|---|---|---|---|
| junction-honest | 0.9289 | 12 | 0 | yes |
| junction-recovering | 0.5185 | 11 | 1 | yes |
| junction-liar | 0.0108 | 3 | 3 | NO |
| junction-flaky | 0.0478 | 5 | 5 | NO |

## The asymmetry (extreme lie penalty)

- 10 consecutive verified truths to climb from the 0.5 prior to 0.90 trust; but a SINGLE lie from a high-trust source (here 0.86, after 8 truths) collapses it by 0.65 to 0.22, below the 0.5 corroboration floor. Honesty is earned slowly, betrayed instantly.

## Checks

- [x] honest_trust_rises
- [x] one_lie_collapses_below_floor
- [x] one_lie_undoes_many_truths
- [x] persistent_liar_cannot_corroborate
- [x] flaky_cannot_corroborate
- [x] honest_source_can_corroborate
- [x] recovery_is_slow
- [x] asymmetry_truths_up_gt_one_lie_down
- [x] local_sensing_is_arbiter

> Deterministic mechanism demonstration; parameters are pinned design choices, not fitted. Local sensing is the arbiter and is never doubted -- it is the ground truth an agent can always rely on.
