"""Hybrid controller: SLM proposes, MaxPressure shield disposes (event-gated).

For each SLM-controlled junction, at a decision point:
  1. Quiet junction (total halting < gate) -> use MaxPressure directly (skip the SLM:
     the latency/compute isn't worth it, and MaxPressure is near-optimal under light load).
  2. Otherwise ask the SLM for a phase. Use it ONLY if it returns a valid phase;
     on None/invalid the deterministic MaxPressure choice stands (the "shield disposes").
Non-SLM junctions always run MaxPressure. Every SLM decision is logged (proposal vs
shield vs used vs SERVED) — the raw material for the audit trail and the coordination
evaluation.

SERVED-phase provenance (MASTER-SPEC §4 H2)
-------------------------------------------
``decide()`` runs INSIDE ``_decide_with_anti_starvation`` and returns the pre-override
choice (``used``); step() may then override it to a starved phase. The audit must
record the phase ACTUALLY served. So decide() records ``used`` as provenance and a
provisional ``served == used``; ``_on_served`` (called by step() after the override)
repairs ``served`` to the served phase ``best`` and tags ``served_by``. When an
override changes the served phase on a GATE-SKIPPED interval (decide() emitted no
event), ``_on_served`` emits an event so the served-phase change is never silent.
"""
from __future__ import annotations

from controllers import MaxPressureController


def served_by(slm_phase, shield_phase, used, served) -> str:
    """Who AUTHORED the phase actually served this interval (honest provenance).

      * ``anti_starvation`` -- the fairness shield overrode the decision's choice
        (``served != used``): NEITHER the SLM proposal NOR the shield's argmax, but
        the forced most-starved phase.
      * ``slm``             -- a valid SLM proposal was served (``used == served``
        and the SLM proposed exactly the served phase).
      * ``shield``          -- the MaxPressure shield choice was served (SLM was
        silent/invalid, or the run is the null-agent baseline).
    """
    if served != used:
        return "anti_starvation"
    if slm_phase is not None and slm_phase == served:
        return "slm"
    return "shield"


class HybridController(MaxPressureController):
    def __init__(self, conn, tls_ids, agent, slm_junctions=None,
                 gate: int = 2, min_green: int = 10, yellow: int = 3,
                 delay_aware: bool = False, gate_mode: str = "sum"):
        if gate_mode not in ("sum", "max"):
            raise ValueError(f"gate_mode must be 'sum' or 'max', got {gate_mode!r}")
        super().__init__(conn, tls_ids, min_green=min_green, yellow=yellow)
        self.agent = agent
        self.slm = set(slm_junctions) if slm_junctions else set(tls_ids)
        self.gate = gate
        # Congestion gate mode (default "sum" -> byte-identical to prior behaviour).
        #   "sum": consult the SLM when TOTAL halting across phases >= gate. This SCALES
        #          with the number of phases, so a 4-phase grid junction trips it more
        #          easily than a 2-phase corridor junction (topology-dependent).
        #   "max": consult the SLM only when the LARGEST single-phase queue >= gate, i.e.
        #          a real standing queue on some approach. Topology-INVARIANT: a free-
        #          flowing net (short queues everywhere) defers to MaxPressure regardless
        #          of phase count, so the SLM acts only under genuine congestion -- the
        #          "congestion-gated hybrid" (match MaxPressure in free flow, beat it under
        #          gridlock). Chosen from the mechanism (SLM helps only where MaxPressure
        #          gridlocks), applied UNIFORMLY across topologies (not tuned per net).
        self.gate_mode = gate_mode  # validated at the top of __init__
        # SOTA DELAY-AWARE myopic mode (default OFF -> byte-for-byte the queue-only
        # controller). When ON, decide() passes the agent a per-phase context with
        # queue + mean waiting time + current-phase marker (own-junction info only),
        # so a delay-aware SLM can beat MaxPressure on delay via waiting-time priority
        # + switching hysteresis. It ONLY enriches what the agent sees; the shield,
        # anti-starvation, and served-phase audit are unchanged.
        self.delay_aware = bool(delay_aware)
        self.events: list[dict] = []  # decision log
        # Per-interval decision context, set by decide(), consumed by _on_served
        # so it can repair the SERVED phase on the just-logged event (or emit one
        # for a gate-skipped interval whose served phase the override changed).
        self._served_ctx: dict | None = None

    def decide(self, tl: str, st: dict) -> int:
        mp_choice = super().decide(tl, st)
        if tl not in self.slm:
            self._served_ctx = {"tl": tl, "recorded": mp_choice, "event_index": None,
                                "gate_skipped": False, "mp_choice": mp_choice,
                                "slm_phase": None, "halting": None, "emitted": False}
            return mp_choice

        halting = [self.green_halting(st, gi) for gi in range(len(st["green"]))]
        quiet = (max(halting) < self.gate if self.gate_mode == "max"
                 else sum(halting) < self.gate)
        if quiet:  # congestion gate: below threshold -> shield only (defer to MaxPressure)
            self._served_ctx = {"tl": tl, "recorded": mp_choice, "event_index": None,
                                "gate_skipped": True, "mp_choice": mp_choice,
                                "slm_phase": None,
                                "halting": [int(h) for h in halting],
                                "emitted": False}
            return mp_choice

        if self.delay_aware:
            # Own-junction delay context: queue + mean waiting time per phase +
            # which phase is currently green (for switching hysteresis). Myopic:
            # no neighbour / upstream info.
            cur = st["cur"]
            phase_context = [
                {"queue": int(halting[gi]),
                 "waiting": self.green_waiting(st, gi),
                 "current": gi == cur}
                for gi in range(len(st["green"]))
            ]
            proposal = self.agent.choose_phase(tl, len(st["green"]), halting,
                                               phase_context=phase_context)
        else:
            proposal = self.agent.choose_phase(tl, len(st["green"]), halting)
        used = proposal if proposal is not None else mp_choice
        # `served` is PROVISIONAL (== used); _on_served repairs it to the served
        # phase post-anti-starvation. On a directly-driven decide() (no step()),
        # no override applies, so served == used stands correctly.
        self.events.append({
            "tls": tl, "halting": halting,
            "slm_phase": proposal, "shield_phase": mp_choice, "used": used,
            "served": used,
            "served_by": served_by(proposal, mp_choice, used, used),
            "overridden": proposal is None or proposal != mp_choice,
        })
        self._served_ctx = {"tl": tl, "recorded": used,
                            "event_index": len(self.events) - 1,
                            "gate_skipped": False, "mp_choice": mp_choice,
                            "slm_phase": proposal,
                            "halting": [int(h) for h in halting], "emitted": False}
        return used

    def _on_served(self, tl: str, st: dict, best: int) -> None:
        """Record the SERVED phase (post anti-starvation) on this interval's event.

        Case (a) -- decide() logged an event this interval (gate passed): repair its
        ``served``/``served_by`` to the served phase ``best`` (a fresh event object;
        never mutate in place).
        Case (b) -- decide() logged NO event (gate-skipped / non-SLM) BUT the
        override changed the served phase: emit an event recording the served phase,
        so a gate-skipped override is never a silent, unrecorded phase change.
        """
        ctx = self._served_ctx
        if not ctx or ctx["tl"] != tl:
            return
        idx = ctx["event_index"]
        if idx is not None:
            ev = self.events[idx]
            self.events[idx] = {
                **ev, "served": best,
                "served_by": served_by(ev.get("slm_phase"), ev.get("shield_phase"),
                                       ev.get("used"), best),
            }
        elif best != ctx["recorded"]:
            self.events.append({
                "tls": tl, "halting": ctx["halting"] or [],
                "slm_phase": None, "shield_phase": ctx["mp_choice"],
                "used": ctx["recorded"], "served": best,
                "served_by": "anti_starvation",
                "overridden": True, "gate_skipped": ctx["gate_skipped"],
            })
