# H1 powered runs: honest §8 demand gate (D-H1-perf / D8)

**Status: GATED (pilot-only) -- inferential runs deferred**

- Gate: D-H1-perf / D8 (§8 demand-honesty startup gate)
- Demand honesty: Euston demand is DfT DAILY-AADF calibrated: magnitude + mix are REAL (cp 18077/56815, 2025), the hourly profile + directional split + turning proportions are ASSUMED. So every H1 traffic result here is a PILOT.

## Claimable now (descriptive pilots)

- DESCRIPTIVE pilot results, explicitly labelled PILOT / SMOKE / n=1 per cell (the feasibility map + scale threshold + the config-arm smoke).
- An honest NEGATIVE or a conditional POSITIVE is a valid pilot result and PASSES the D-H1-perf reporting gate when labelled (§12).

## Blocked until time-resolved demand

- Any significance / p-value / confidence-interval claim.
- A TOST parity conclusion or a powered null (null only when CI half-width < a pre-registered numeric MDE from an external operational-harm threshold).
- n>=30 paired deltas vs MaxPressure with ONE CI method across the study.

## What would unblock it

- A NAMED, TIME-RESOLVED demand source: TfL hourly counts + turning counts + vehicle mix for the Euston A501 corridor (§8/§9).
- Then: re-run the sweep at n>=30 seeds/cell under the pinned protocol (paired deltas, BCa/permutation + Holm, pre-registered MDE, TOST).

## Pilot evidence on file

- `experiment_sweep.json` — model x config feasibility map (PILOT, n=1/cell); scale threshold: qwen2.5-0.5b x myopic (reached=True)
- `experiment_traffic_arms.json` — config-arm smoke (PILOT, n=1/arm)

> This is an HONEST GATE, not a skipped obligation: the powered inferential runs are well-defined and would run unchanged once the time-resolved source lands; withholding the inferential claim until then is the correct scientific posture, not a gap.
