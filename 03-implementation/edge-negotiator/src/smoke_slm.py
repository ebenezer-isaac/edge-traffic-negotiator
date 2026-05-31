"""Smoke test for the SLM agent — verifies the Foundry Local round-trip returns a
valid terse phase decision. Requires a model to be loaded in Foundry Local.

    python src/smoke_slm.py
    # or, if discovery fails, point it explicitly:
    FOUNDRY_LOCAL_ENDPOINT=http://127.0.0.1:PORT/v1 FOUNDRY_LOCAL_MODEL=<id> python src/smoke_slm.py
"""
from __future__ import annotations

from slm_agent import SLMAgent

if __name__ == "__main__":
    agent = SLMAgent()
    print(f"endpoint model: {agent.model}")
    # toy 2-phase junction: which phase has more waiting traffic should be chosen
    cases = [[8, 0], [0, 9], [4, 4], [2, 6]]
    for q in cases:
        phase = agent.choose_phase("A0", num_phases=2, halting_per_phase=q)
        verdict = "OK" if phase is not None else "FELL BACK (None -> shield)"
        print(f"  halting={q} -> phase={phase}  [{verdict}]")
