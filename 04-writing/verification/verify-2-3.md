# Verification report — §2.3 (SUPERSEDED BY THESIS CUT-OVER)

**Status:** SUPERSEDED. Do not rely on the findings that previously occupied this file.

This report audited the pre-cut-over draft of `sections/sec-2-3.md` (reinforcement learning for traffic signal control) under the retired seven-axis novelty framing. The RL prior-art survey and the safety/adversarial-robustness sub-literature (SafeLight, CFLight, Adv-DRL-TSC, T-REX, CollusionVeh) remain valid, but the substrate reference (a "SUMO Lambeth" grid) and the equity cross-references have been rewritten: the synthetic grid is now a unit-test fixture ahead of the real Euston Road (A501) corridor, and the aggregate-versus-per-decision critique now motivates the accountability framing rather than an equity audit.

Current thesis and framing: see `VERIFIER_RULEBOOK.md` and `sections/AGENT_RULEBOOK.md`.

**Action required:** re-run the Wave-3 audit against the rewritten `sec-2-3.md`. The prior findings have been removed so that no retired-framing assertions survive in this file.
