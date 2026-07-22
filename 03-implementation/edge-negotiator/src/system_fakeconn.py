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


# Default lane length (m) reported by getLength when a lane is not given an
# explicit length -- long enough that a vehicle placed near the stop line is
# within the controller's default ev_horizon (195 m).
_DEFAULT_LANE_LEN = 200.0


class FakeLane:
    """traci.lane stand-in: per-lane halting + (for EV sensing) the vehicle ids
    currently on a lane and the lane length. All three are read by the emergency
    controller's local-EV detector (getLastStepVehicleIDs / getLength) and the
    coordination layer (getLastStepHaltingNumber). Vehicle/length maps default
    empty so a plain coordination FakeConn(halting) is byte-for-byte unchanged."""

    def __init__(self, halting: dict, vehicles: dict | None = None,
                 lengths: dict | None = None):
        self._halting = dict(halting)
        # lane_id -> tuple of vehicle ids on that lane (order as scripted; SUMO's
        # downstream-to-upstream lane ordering is NOT modelled).
        self._vehicles = {k: tuple(v) for k, v in (vehicles or {}).items()}
        self._lengths = dict(lengths or {})

    def _known(self, lane_id) -> bool:
        """A lane the stub knows about (any of the three maps mentions it). Real
        TraCI raises on a genuinely unknown lane for ALL lane calls; we mirror
        that so a later lane-resolution bug cannot hide behind a silent default."""
        return (lane_id in self._halting or lane_id in self._lengths
                or lane_id in self._vehicles)

    def getLastStepHaltingNumber(self, lane_id):
        if lane_id not in self._halting:
            raise KeyError(lane_id)
        return self._halting[lane_id]

    def getLastStepVehicleIDs(self, lane_id):
        """Vehicle ids on ``lane_id`` (empty tuple if none scripted on a KNOWN
        lane). This is the LANE call the EV detector uses -- NOT a vehicle-object
        call (build F4). Unknown lane -> KeyError, as real TraCI raises."""
        if not self._known(lane_id):
            raise KeyError(lane_id)
        return tuple(self._vehicles.get(lane_id, ()))

    def getLength(self, lane_id):
        """Lane length in metres (default _DEFAULT_LANE_LEN on a KNOWN lane).
        Unknown lane -> KeyError, as real TraCI raises."""
        if not self._known(lane_id):
            raise KeyError(lane_id)
        return float(self._lengths.get(lane_id, _DEFAULT_LANE_LEN))

    def set_observed(self, sender: str, value: int) -> None:
        """Set the halting A0 observes on edge ``sender->A0`` (e.g. A1 -> A1A0_0)."""
        self._halting = {**self._halting, f"{sender}A0_0": value}

    def observed_for(self, sender: str) -> int:
        return self._halting.get(f"{sender}A0_0", 0)


class FakeVehicle:
    """traci.vehicle stand-in exposing ONLY the two per-vehicle calls the EV
    detector needs: getVehicleClass + getLanePosition. It intentionally does NOT
    expose getLastStepVehicleIDs -- that is a LANE call (build F4); scripting it
    here would let a regression silently read vehicle ids off the wrong object."""

    def __init__(self, classes: dict | None = None,
                 positions: dict | None = None):
        self._classes = dict(classes or {})
        self._positions = dict(positions or {})

    def getVehicleClass(self, vid):
        if vid not in self._classes:
            raise KeyError(vid)  # mimics SUMO raising on an unknown vehicle
        return self._classes[vid]

    def getLanePosition(self, vid):
        if vid not in self._positions:
            raise KeyError(vid)
        return float(self._positions[vid])


class FakeSimulation:
    """traci.simulation stand-in with a MONOTONIC clock: getTime() never returns
    a smaller value than a prior call (advance() rejects negative dt and getTime
    is side-effect-free), matching SUMO's non-decreasing simulation time."""

    def __init__(self, start: float = 0.0):
        self._t = float(start)

    def getTime(self):
        return self._t

    def advance(self, dt: float = 1.0):
        if not isinstance(dt, (int, float)) or isinstance(dt, bool):
            raise TypeError("dt must be a number")
        if dt < 0:
            raise ValueError("simulation time is monotonic; dt must be >= 0")
        self._t = self._t + float(dt)
        return self._t


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
    """Deterministic TraCI connection stand-in. The coordination path uses only
    ``lane`` + ``trafficlight``; the emergency path additionally reads ``vehicle``
    (getVehicleClass/getLanePosition) + monotonic ``simulation`` (getTime). All EV
    maps default empty so ``FakeConn(halting)`` is unchanged for coordination."""

    def __init__(self, halting: dict, vehicles: dict | None = None,
                 lengths: dict | None = None, classes: dict | None = None,
                 positions: dict | None = None, sim_time: float = 0.0):
        self.lane = FakeLane(halting, vehicles, lengths)
        self.trafficlight = FakeTL()
        self.vehicle = FakeVehicle(classes, positions)
        self.simulation = FakeSimulation(sim_time)


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
