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

    def __init__(self, conn, tls_ids, min_green: int = 10, yellow: int = 3):
        self.c = conn
        self.min_green = min_green
        self.yellow = yellow
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
            }
            conn.trafficlight.setRedYellowGreenState(tl, self.tls[tl]["green"][0])

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
                    best = max(range(len(st["green"])), key=lambda gi: self._pressure(st, gi))
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
