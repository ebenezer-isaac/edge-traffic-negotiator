"""Deterministic in-memory TraCI stand-in for the IntegratedSystem CI path.

Split out of ``system.py`` so the orchestrator stays focused (and under the
800-line file rule). Mirrors ``tests/test_coordination.py`` + ``run_attacks.py``
exactly: recipient A0, in-edges A1->A0 on phase 0 and B0->A0 on phase 1. The
``release`` published by a (possibly malicious) sender sets the CLAIM; the lane
halting on the sender's in-edge sets the independent OBSERVATION. No SUMO.
"""
from __future__ import annotations

# Default observed inflow A0 sees on edge A1->A0 (lane A1A0_0) on a clean run.
_BASE_OBSERVED_A1 = 5

# Phase-1 local queue, kept above the default event-gate (2) so EVERY decide()
# round passes the gate and reconciles — even when an attack drives the phase-0
# observation edge (A1A0_0) to 0. Without this a spoof that zeroes the observed
# inflow would also drop the total local queue below the gate and short-circuit
# the decision before conservation runs.
_BASE_PHASE1_QUEUE = 4


def initial_halting() -> dict:
    return {
        "A1A0_0": _BASE_OBSERVED_A1,   # observation edge A1->A0 (phase 0)
        "B0A0_0": _BASE_PHASE1_QUEUE,  # phase-1 local queue (keeps gate satisfied)
        "A0A1_0": 0,                   # out-lanes
        "A0B0_0": 0,
    }


class FakeLane:
    """traci.lane stand-in with mutable per-edge observations (for attacks)."""

    def __init__(self, halting: dict):
        self._halting = dict(halting)

    def getLastStepHaltingNumber(self, lane_id):
        if lane_id not in self._halting:
            raise KeyError(lane_id)
        return self._halting[lane_id]

    def set_observed(self, sender: str, value: int) -> None:
        """Set the halting A0 observes on edge ``sender->A0`` (e.g. A1 -> A1A0_0)."""
        self._halting = {**self._halting, f"{sender}A0_0": value}

    def observed_for(self, sender: str) -> int:
        return self._halting.get(f"{sender}A0_0", 0)


class FakeTL:
    class _Phase:
        def __init__(self, state):
            self.state = state

    class _Logic:
        def __init__(self, phases):
            self.phases = phases

    def __init__(self):
        self._phases = [
            self._Phase("Gr"), self._Phase("yr"),
            self._Phase("rG"), self._Phase("ry"),
        ]
        self._links = [
            [("A1A0_0", "A0A1_0", "")],   # movement 0: in A1->A0, out A0->A1
            [("B0A0_0", "A0B0_0", "")],   # movement 1: in B0->A0, out A0->B0
        ]

    def getAllProgramLogics(self, tl):
        return [self._Logic(self._phases)]

    def getControlledLinks(self, tl):
        return self._links

    def setRedYellowGreenState(self, tl, state):
        return None


class FakeConn:
    def __init__(self, halting: dict):
        self.lane = FakeLane(halting)
        self.trafficlight = FakeTL()


class NoObsConn:
    """Placeholder conn for SUMO-path attack injection (no observation to set)."""

    class _Lane:
        def set_observed(self, *_a, **_k):
            return None

        def observed_for(self, *_a, **_k):
            return 0

    def __init__(self):
        self.lane = self._Lane()


# --------------------------------------------------------------------------- #
# Result-assembly helpers (pure functions).
# --------------------------------------------------------------------------- #

def group_attacks(specs) -> dict:
    """Group AttackSpec-like objects by their .tick (duck-typed, no import)."""
    out: dict = {}
    for spec in specs:
        out = {**out, spec.tick: [*out.get(spec.tick, []), spec]}
    return out


def coordination_counts(ctrl, bus, transports=None) -> dict:
    """Verified / rejected / detections / coord_adjusted counts from the run."""
    if ctrl is None:
        return {}
    events = ctrl.events
    verified = sum(len(e.get("received", [])) for e in events
                   if isinstance(e.get("received"), list)
                   and not any("error" in r for r in e["received"]))
    if transports:
        rejected = sum(len(tr.bus.rejected) for tr in transports.values())
    elif bus is not None:
        rejected = len(bus.rejected)
    else:
        rejected = 0
    return {
        "decisions": len(events),
        "verified_messages": verified,
        "rejected_messages": rejected,
        "detections": len(ctrl.detections),
        "flagged_detections": sum(1 for d in ctrl.detections if d.flagged),
        "coord_weight": ctrl.coord_weight,
        "coord_adjusted_decisions": ctrl.coord_adjusted_decisions,
        "coord_changed_events": sum(1 for e in events if e.get("coord_changed")),
    }


def fake_traffic_summary(rounds: int, decisions: int) -> dict:
    """Traffic-shaped summary for the no-SUMO CI path.

    The fake-conn harness exercises the coordination/audit/attack pipeline, not a
    microsimulation, so there is no tripinfo. We surface ``completed`` as the
    number of completed decision rounds (a real >0 signal the pipeline ran) and
    flag the absence of a microsimulation explicitly so a consumer never mistakes
    this for SUMO travel-time data.
    """
    return {
        "source": "fake_conn",
        "microsimulation": False,
        "completed": decisions,
        "rounds": rounds,
    }


def sumo_traffic_summary(tripinfo_path: str) -> dict:
    """Parse the real tripinfo into survivorship-robust metrics (metrics.py)."""
    from metrics import parse_tripinfo, summary, throughput
    run = parse_tripinfo(tripinfo_path)
    s = summary(run)
    s["source"] = "sumo"
    s["microsimulation"] = True
    s["completed"] = throughput(run)
    return s


def config_dict(cfg: SystemConfig) -> dict:
    return {
        "transport": cfg.transport, "registry": cfg.registry, "agent": cfg.agent,
        "network": cfg.network, "audit": cfg.audit, "seed": cfg.seed,
        "end": cfg.end, "rounds": cfg.rounds, "coord_weight": cfg.coord_weight,
        "tolerance": cfg.tolerance, "gate": cfg.gate,
        "attacks": [{"kind": a.kind, "sender": a.sender, "recipient": a.recipient,
                     "tick": a.tick} for a in cfg.attacks],
        "requires_sumo": cfg.requires_sumo, "is_default": cfg.is_default,
    }
