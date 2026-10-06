# H1 SOTA: delay-aware myopic SLM vs vanilla myopic vs MaxPressure

**PILOT / SMOKE**, n=1. Technique: delay-aware myopic: waiting-time priority (LLMLight) + switching hysteresis (EvolveSignal); own-junction info only.

- Baseline myopic MaxPressure: delay 314.55 s, completed 361
- Seed 42, horizon 1200 s, gate 2

| Model | Size | myopic (vanilla) | sota (delay-aware) | sota vs myopic |
|---|---|---|---|---|
| qwen3-0.6b | 0.52 | slm_beats (267.09s) | slm_beats (262.91s) | -4.18s IMPROVED |
| qwen2.5-0.5b | 0.68 | slm_beats (235.00s) | slm_beats (291.30s) | 56.30s |
| qwen3-1.7b | 1.39 | slm_beats (233.73s) | slm_beats (239.77s) | 6.04s |
| phi-4-mini | 3.72 | match (314.71s) | slm_beats (270.42s) | -44.28s IMPROVED LIFTED |

## Summary

- SOTA improved delay over vanilla myopic for: ['phi-4-mini', 'qwen3-0.6b']
- SOTA lifted the verdict (loses->match or match->beats) for: ['phi-4-mini']
- SOTA beats MaxPressure for: ['phi-4-mini', 'qwen2.5-0.5b', 'qwen3-0.6b', 'qwen3-1.7b']

## Caveats

- PILOT n=1, DfT daily-AADF demand (temporal profile assumed) -> DESCRIPTIVE only, NO significance claim (§8).
- SOTA arm is still MYOPIC (own-junction only): the levers are waiting-time priority + switching hysteresis, not coordination or prediction.
- Audit live on every arm; degraded (all-shield) arms are skip-recorded.
