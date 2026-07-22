"""Deterministic signal controllers for the Edge Negotiator.

`MaxPressureController` is both the classical baseline and the always-on safety
*shield* the SLM agent's proposals are checked against (see PROJECT-DECISION-BRIEF.md).

MaxPressure (Varaiya): at each decision interval serve the phase with the greatest
pressure = sum over the movements that phase gives green to of
    (upstream halting count) - (downstream halting count).
It is throughput-optimal under mild assumptions and needs only local queue counts.

Controllers drive a TLS by writing full state strings via
`setRedYellowGreenState`, which holds until changed — so we own every transition
(green -> yellow clearance -> next green) rather than letting SUMO's fixed program
auto-advance.
"""
from __future__ import annotations


def _is_green(state: str) -> bool:
    return ("G" in state or "g" in state) and "y" not in state


class MaxPressureController:
    """Run MaxPressure on a set of traffic lights via a live TraCI connection."""

    def __init__(self, conn, tls_ids, min_green: int = 10, yellow: int = 3,
                 anti_starvation_enabled: bool = True, max_skip: int = 3):
        self.c = conn
        self.min_green = min_green
        self.yellow = yellow
        # Anti-starvation (shield): force-serve a green phase that has been passed
        # over for `max_skip` consecutive decision intervals (spec §6.8, D7).
        self.max_skip = max_skip
        self.anti_starvation_enabled = anti_starvation_enabled
        # EMERGES from the mechanism -- a test READS it, never assigns it (D7).
        self.anti_starvation_violations = 0
        self.tls: dict[str, dict] = {}
        for tl in tls_ids:
            phases = conn.trafficlight.getAllProgramLogics(tl)[0].phases
            green_idx = [i for i, p in enumerate(phases) if _is_green(p.state)]
            links = conn.trafficlight.getControlledLinks(tl)
            self.tls[tl] = {
                # candidate green phase state strings
                "green": [phases[i].state for i in green_idx],
                # the yellow that clears each green = the phase immediately after it
                "yellow": [phases[(i + 1) % len(phases)].state for i in green_idx],
                "in_lanes": [lk[0][0] if lk else None for lk in links],
                "out_lanes": [lk[0][1] if lk else None for lk in links],
                "cur": 0,        # index into "green" currently served
                "mode": "green",  # "green" | "yellow"
                "t": 0,          # seconds elapsed in current mode
                # per-green-phase skip counter (1:1 with approach); 0 = just served.
                "skip": [0] * len(green_idx),
            }
            conn.trafficlight.setRedYellowGreenState(tl, self.tls[tl]["green"][0])
            # The ctor's initial green (phase 0) IS decision interval 0: run the
            # SAME post-service update so counters advance from construction.
            self._record_service(self.tls[tl], 0)

    def _pressure(self, st: dict, gi: int) -> int:
        """Pressure of green phase `gi`: sum of (in-queue - out-queue) over its greens."""
        halting = self.c.lane.getLastStepHaltingNumber
        p = 0
        for i, ch in enumerate(st["green"][gi]):
            if ch in "Gg":
                if st["in_lanes"][i]:
                    p += halting(st["in_lanes"][i])
                if st["out_lanes"][i]:
                    p -= halting(st["out_lanes"][i])
        return p

    def green_halting(self, st: dict, gi: int) -> int:
        """Total upstream halting vehicles the green phase `gi` would serve (SLM input)."""
        halting = self.c.lane.getLastStepHaltingNumber
        return sum(halting(st["in_lanes"][i]) for i, ch in enumerate(st["green"][gi])
                   if ch in "Gg" and st["in_lanes"][i])

    def decide(self, tl: str, st: dict) -> int:
        """Choose which green phase to serve. Default = max pressure; subclasses may override."""
        return max(range(len(st["green"])), key=lambda gi: self._pressure(st, gi))

    def _record_service(self, st: dict, served: int,
                        preempt_locked: bool = False) -> None:
        """Post-service skip-counter update, applied ONCE per decision interval to
        the phase actually served -- whether chosen by max-pressure argmax, by a
        re-eval that stayed on the current phase, or by the anti-starvation
        override. Reset the served phase to 0; age every OTHER green phase by one
        interval; then if any counter now EXCEEDS max_skip record an anti-starvation
        violation (a starvation the override failed to prevent). Called from BOTH
        the ctor (interval 0) and step() (intervals 1..N).

        ``preempt_locked`` marks an interval where an admissible EV preempt is
        legitimately holding the signal (spec §6.8 precedence). The skip counters
        STILL age (fairness debt is tracked, so the deferred phase is force-served
        promptly once the preempt ends), but a resulting over-max_skip is
        LEGITIMATE_DEGRADATION -- NOT a shield failure -- so the violation increment
        is suppressed, keeping D7 clean under an admissible preempt held past
        max_skip. Base MaxPressureController never locks, so this is always False
        there and the fixture path is unchanged."""
        skip = st["skip"]
        # New list (immutability where practical) stored back on the per-tl state.
        new_skip = [0 if q == served else skip[q] + 1 for q in range(len(skip))]
        st["skip"] = new_skip
        if not preempt_locked and any(s > self.max_skip for s in new_skip):
            self.anti_starvation_violations += 1

    def _preempt_locked_phase(self, tl: str) -> int | None:
        """Phase locked by an active admissible emergency preemption this tick, or
        None. Base controller has no emergency layer, so never locks. Subclasses
        (EmergencyController) override to report an in-progress admissible EV
        preempt, which OUTRANKS the anti-starvation override (spec §6.8)."""
        return None

    def _decide_with_anti_starvation(self, tl: str, st: dict) -> int:
        """Wrap the phase CHOICE (not the pressure math) with the anti-starvation
        override.

        ALWAYS calls decide() FIRST so every subclass side-effect fires and the §11
        kind:"decision" audit record is emitted every interval (never skipped by an
        override). Then applies precedence:
          * disabled              -> return the normal choice (counters still update
                                     in step() so negative_control sees violations);
          * an admissible EV preempt is locked -> return the normal choice (emergency
                                     preemption OUTRANKS fairness; the shield never
                                     cuts an active preempt);
          * else if some phase has reached max_skip AND the normal choice is NOT
            itself a starved phase -> force-serve the most-starved (highest skip;
            tie-break highest _pressure, then lowest index);
          * else -> the normal choice.
        Behaviour-equivalent to the pre-refactor logic on the 2-phase fixture: at
        most one phase is >= max_skip at a time, so `normal` is either that phase
        (served -> no override) or the other (override to it)."""
        normal = self.decide(tl, st)
        if not self.anti_starvation_enabled:
            return normal
        if self._preempt_locked_phase(tl) is not None:
            return normal
        reached = [p for p in range(len(st["skip"]))
                   if st["skip"][p] >= self.max_skip]
        if reached and normal not in reached:
            return max(reached,
                       key=lambda p: (st["skip"][p], self._pressure(st, p), -p))
        return normal

    def step(self) -> None:
        """Advance every controlled TLS by one simulated second."""
        for tl, st in self.tls.items():
            st["t"] += 1
            if st["mode"] == "yellow":
                if st["t"] >= self.yellow:
                    self.c.trafficlight.setRedYellowGreenState(tl, st["green"][st["cur"]])
                    st["mode"], st["t"] = "green", 0
            else:  # green phase running
                if st["t"] >= self.min_green:
                    # A decision interval: the override wraps the phase choice, then
                    # the served phase's counters update exactly once. A deferral
                    # while an admissible EV preempt holds the signal is legitimate
                    # (spec §6.8) -> its over-max_skip is not a violation.
                    best = self._decide_with_anti_starvation(tl, st)
                    preempt_locked = self._preempt_locked_phase(tl) is not None
                    self._record_service(st, best, preempt_locked=preempt_locked)
                    if best != st["cur"]:
                        # show the clearing yellow for the phase we are leaving
                        self.c.trafficlight.setRedYellowGreenState(tl, st["yellow"][st["cur"]])
                        st["mode"], st["t"], st["cur"] = "yellow", 0, best
                    else:
                        st["t"] = 0  # re-evaluate again after another min_green


class FixedTimeController:
    """No-op: leave SUMO running each TLS's default fixed-time program (Webster-style baseline)."""

    def step(self) -> None:
        return
