# Powered why-analysis: model x scenario (multi-seed)

**Interaction model x scenario: significant.** Two-way ANOVA (n=3/cell): interaction F=32.2364, p<0.001 (significant at a=0.05), partial eta^2=0.858. The scenario is the dominant lever, but which SLM you run and the scenario-specific way it behaves BOTH move the outcome: model, scenario and their interaction are all significant.

## Design

- Models: qwen2.5-0.5b, qwen3-0.6b
- Seeds/cell: [42, 7, 123] (n=3)
- Horizon: end=1200, congestion gate=2
- Demand: DfT daily-resolution (SS8 gated) -- this tests the INTERACTION, not the headline vs live London demand.

## Per-cell behaviour (mean [sd] over seeds)

| Topology | TLS | Model | Delay vs baseline | Override rate | Agreement | Authored share |
|---|---|---|---|---|---|---|
| euston_corridor | 4 | qwen2.5-0.5b | -16.1% [sd 8.2] | 0.54 [sd 0.06] | 0.46 | 0.60 |
| euston_corridor | 4 | qwen3-0.6b | -21.4% [sd 5.9] | 0.61 [sd 0.04] | 0.39 | 0.69 |
| bloomsbury_grid | 9 | qwen2.5-0.5b | -0.4% [sd 5.1] | 0.36 [sd 0.02] | 0.64 | 0.64 |
| bloomsbury_grid | 9 | qwen3-0.6b | -3.7% [sd 2.1] | 0.59 [sd 0.04] | 0.41 | 0.71 |
| grid3x3 | 9 | qwen2.5-0.5b | +48.8% [sd 10.4] | 0.70 [sd 0.03] | 0.30 | 0.75 |
| grid3x3 | 9 | qwen3-0.6b | +24.9% [sd 10.5] | 0.44 [sd 0.03] | 0.56 | 0.85 |
| grid4x4 | 16 | qwen2.5-0.5b | +114.9% [sd 2.4] | 0.83 [sd 0.02] | 0.17 | 0.75 |
| grid4x4 | 16 | qwen3-0.6b | +34.9% [sd 11.0] | 0.27 [sd 0.02] | 0.73 | 0.96 |

Delay vs baseline: negative = faster than MaxPressure on that seed's own baseline; positive = slower. Override rate = share of SLM-authored decisions that diverged from the MaxPressure shield.

## Inferential two-way ANOVA (model x scenario, with replication)

- Grand mean delay change: 22.7492%

| Effect | SS | df | MS | F | p | partial eta^2 |
|---|---|---|---|---|---|---|
| Model | 4753.972 | 1 | 4753.972 | 79.7641 | <0.001 | 0.8329 |
| Scenario | 31564.3335 | 3 | 10521.4445 | 176.5332 | <0.001 | 0.9707 |
| Model x Scenario | 5763.9071 | 3 | 1921.3024 | 32.2364 | <0.001 | 0.858 |
| Within (error) | 953.6062 | 16 | 59.6004 | - | - | - |

**Reading (honest):**
- Scenario main effect: p<0.001 (significant at a=0.05), partial eta^2=0.9707 -- the topology/scenario is the overwhelming driver of whether the SLM helps or hurts.
- Model main effect: p<0.001 (significant at a=0.05), partial eta^2=0.8329 -- which SLM you run matters on its own.
- Interaction: p<0.001 (significant at a=0.05), partial eta^2=0.858 -- LARGE by Cohen's convention (partial eta^2 > 0.14) AND clears a=0.05: the SLMs do not just differ by a constant, they differ SCENARIO-BY-SCENARIO (e.g. on the densest grid qwen2.5 blows up far worse than qwen3). The interaction is real at this power; absolute significance vs live demand stays SS8-gated.

## Mechanism: does override rate explain the delay change?

- Pearson(override, delay change) = 0.47; Spearman = 0.214 (n_cells=8).
- The Pearson correlation is MODERATE and positive: cells where the SLM overrode MaxPressure more often do tend to show a larger delay change, consistent with 'divergence drives the loss.' But Spearman is much weaker, so the linear correlation leans on the extreme high-override / high-delay cell (the densest grid) rather than a monotone trend across all cells -- treat the mechanism as directional, not established. Either way the scenario main effect is far larger than this divergence signal.

## Limitations

- Demand is DfT daily-resolution (SS8): cross-seed variance is real, so the F-tests are legitimate, but absolute significance vs live London demand stays gated.
- n=3 seeds/cell across 4 scenarios: enough replication to make the interaction inferentially testable (Alin & Kurt 2006); the interaction reaches significance here, but more seeds would tighten the effect-size estimate.
- Mechanism correlation is over 8 cells only; treat as directional, not conclusive, and check its sensitivity to the most extreme cell.
