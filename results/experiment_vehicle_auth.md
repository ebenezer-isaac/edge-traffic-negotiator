# H2: multi-authorised-vehicle authorisation -- categorised eval

**PASS** -- deterministic KB gate over 26 balanced categorised claims.

- Classifier: deterministic KB gate (vehicle_authorization.classify)
- Class accuracy: 1.000  |  grant/deny accuracy: 1.000

## Safety-critical confusion (positive = should be DENIED preemption)

- TP 18  FP 0  FN 0  TN 8
- Precision 1.000  |  Recall 1.000  |  FPR 0.000  |  FNR 0.000
- **Dangerous false grants (illegitimate claim granted preemption): 0**

## Per-category coverage

| Category | n | class correct | grant correct |
|---|---|---|---|
| contradictory | 2 | 2/2 | 2/2 |
| invalid_id | 3 | 3/3 | 3/3 |
| missing_metadata | 3 | 3/3 | 3/3 |
| signal_tampering | 3 | 3/3 | 3/3 |
| unknown_vehicle | 3 | 3/3 | 3/3 |
| valid_ambulance | 3 | 3/3 | 3/3 |
| valid_civilian | 1 | 1/1 | 1/1 |
| valid_fire | 2 | 2/2 | 2/2 |
| valid_fire_lanehold | 1 | 1/1 | 1/1 |
| valid_maintenance_hold | 2 | 2/2 | 2/2 |
| valid_police | 3 | 3/3 | 3/3 |

## Notes

- Balanced across authorised classes + every KB attack family; positive class is 'should be DENIED preemption' so recall measures catching illegitimate claims and FNR measures dangerous false grants.
- Deterministic KB gate: no model, sub-ms per claim; correctness/coverage eval, not a latency study.
- maintenance/civilian are LEGITIMATE entities but are NEVER granted preemption (preemption_allowed=false) -- a correct deny is not a miss.
