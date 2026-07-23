# Experiment D: the self-referential coupling boundary (D6, §4.5)

**MODELLED PILOT (descriptive); inferential contrast PROTOCOL-gated**. n=1 case study (this corridor); NO 'corridors in general' claim.

> the preemption attack controls the signal phase; the phase gates honest-witness coverage of the footprint; so an insider can open a coverage desert that conceals a conservation-consistent deviation -- the audit's measured blind spot, reported not defended.

## Independently-calibrated detection threshold

- CUSUM/conservation tau = 1.948 at FP budget 0.050 (realised FP 0.050), benign model half-normal(scale=1.0), calibrated WITHOUT the attack set.
- Conservation-consistent deviation := residual < tau -> no conservation trace; only LIVE witness coverage can catch it.

## Coverage-vs-escape surface (MODELLED, descriptive)

| avg coverage | phase-lock | eff. coverage | escape (95% CI) | well-mixed | excess |
|---|---|---|---|---|---|
| 0.1 | 0.0 | 0.10 | 0.903 [0.894,0.912] | 0.900 | 0.003 |
| 0.1 | 0.5 | 0.05 | 0.949 [0.942,0.956] | 0.900 | 0.049 |
| 0.1 | 1.0 | 0.00 | 1.000 [1.000,1.000] | 0.900 | 0.100 |
| 0.3 | 0.0 | 0.30 | 0.692 [0.678,0.706] | 0.700 | -0.008 |
| 0.3 | 0.5 | 0.15 | 0.854 [0.842,0.863] | 0.700 | 0.154 |
| 0.3 | 1.0 | 0.00 | 1.000 [1.000,1.000] | 0.700 | 0.300 |
| 0.5 | 0.0 | 0.50 | 0.499 [0.485,0.513] | 0.500 | -0.001 |
| 0.5 | 0.5 | 0.25 | 0.762 [0.750,0.775] | 0.500 | 0.262 |
| 0.5 | 1.0 | 0.00 | 1.000 [1.000,1.000] | 0.500 | 0.500 |
| 0.7 | 0.0 | 0.70 | 0.296 [0.282,0.311] | 0.300 | -0.004 |
| 0.7 | 0.5 | 0.35 | 0.653 [0.639,0.668] | 0.300 | 0.353 |
| 0.7 | 1.0 | 0.00 | 1.000 [1.000,1.000] | 0.300 | 0.700 |
| 0.9 | 0.0 | 0.90 | 0.102 [0.093,0.112] | 0.100 | 0.002 |
| 0.9 | 0.5 | 0.45 | 0.546 [0.531,0.562] | 0.100 | 0.447 |
| 0.9 | 1.0 | 0.00 | 1.000 [1.000,1.000] | 0.100 | 0.900 |

## Conditional lemma (four sufficient hypotheses)

- phase-coupled coverage of the footprint within its live phase window > threshold
- honest independent corroboration keys only
- cross-audited non-equivocating quorum
- no operator creation-time omission

- Dense well-mixed escape mean = 0.102; lemma holds numerically: **True** (escape -> 0 as coverage -> 1). escape -> 0 as coverage -> 1 in the well-mixed regime; the residual is the 1-coverage witness-miss floor, not an audit failure. The lemma is near-definitional; its content is the empirical coverage threshold.

## The severe directional finding (DESCRIPTIVE; inferential decision gated)

- Estimator: escape(phase-locked pocket) - escape(well-mixed) at matched avg coverage
- Descriptive estimate (mid-coverage) = 0.504, direction as predicted (phase-lock raises escape): **True**
- Decision rule: lower one-sided CI bound on the contrast EXCEEDS Delta (NOT excludes zero); CI: curve-bootstrap, N fixed under the seal
- **Inferential decision: NOT_RUN -- PROTOCOL_NOT_A_PASSED_CONTROL**
  - gated: witness coverage is MODELLED, not grounded in documented A501 SCOOT/MOVA loop placement -> per §4.5 modelled cells are EXCLUDED from the headline inferential contrast
  - gated: demand is not time-resolved (§8 hard startup gate) -> no inferential claim
  - gated: Delta must be pinned to a real external operational-harm threshold, not the placeholder here
  - gated: the pre-registration seal (estimator + comparator + Delta + CI + fixed N + hashed §9 artifacts) is not yet in force

## Limitations

- verified-provenance features carry PARTIAL physical signal (position/time/route) but not enough to adjudicate physical veracity; the veracity triad is unrecoverable, so those cells -> unknown (the system never adjudicates it).
- Witness coverage is MODELLED (linear phase-lock model), NOT documented A501 loop placement; modelled cells are excluded from any headline inferential contrast per §4.5.
- Per-cell CIs are DESCRIPTIVE (bootstrap), non-inferential; no per-cell claim without a multiplicity correction.
- The severe directional finding is computed descriptively; the pre-registered inferential decision is NOT run (PROTOCOL_NOT_A_PASSED_CONTROL, §4.5/§12).
- Geometry n=1; the only generalisation axis is sensitivity to demand/phase-offset draws.
