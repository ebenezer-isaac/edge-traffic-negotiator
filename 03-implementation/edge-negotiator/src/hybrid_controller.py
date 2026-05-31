"""Hybrid controller: SLM proposes, MaxPressure shield disposes (event-gated).

For each SLM-controlled junction, at a decision point:
  1. Quiet junction (total halting < gate) -> use MaxPressure directly (skip the SLM:
     the latency/compute isn't worth it, and MaxPressure is near-optimal under light load).
  2. Otherwise ask the SLM for a phase. Use it ONLY if it returns a valid phase;
     on None/invalid the deterministic MaxPressure choice stands (the "shield disposes").
Non-SLM junctions always run MaxPressure. Every SLM decision is logged (proposal vs
shield vs used) — the raw material for the audit trail and the coordination evaluation.
"""
from __future__ import annotations

from controllers import MaxPressureController


class HybridController(MaxPressureController):
    def __init__(self, conn, tls_ids, agent, slm_junctions=None,
                 gate: int = 2, min_green: int = 10, yellow: int = 3):
        super().__init__(conn, tls_ids, min_green=min_green, yellow=yellow)
        self.agent = agent
        self.slm = set(slm_junctions) if slm_junctions else set(tls_ids)
        self.gate = gate
        self.events: list[dict] = []  # decision log

    def decide(self, tl: str, st: dict) -> int:
        mp_choice = super().decide(tl, st)
        if tl not in self.slm:
            return mp_choice

        halting = [self.green_halting(st, gi) for gi in range(len(st["green"]))]
        if sum(halting) < self.gate:  # event-gate: quiet -> shield only
            return mp_choice

        proposal = self.agent.choose_phase(tl, len(st["green"]), halting)
        used = proposal if proposal is not None else mp_choice
        self.events.append({
            "tls": tl, "halting": halting,
            "slm_phase": proposal, "shield_phase": mp_choice, "used": used,
            "overridden": proposal is None or proposal != mp_choice,
        })
        return used
