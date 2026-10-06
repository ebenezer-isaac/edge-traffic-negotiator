"""Fault-finding tests for the H1 CONFIG ARMS (MASTER-SPEC §3 {myopic,
+coordination, +prediction}) and the +prediction lever in CoordinatedController.

No live dependencies. The +prediction lever is driven at the real decide()/step()
seam via a test-local TraCI stand-in that (unlike the §10-hash-pinned FakeConn)
exposes ``getLastStepVehicleNumber`` -- so a phase whose queue is short but whose
platoon is APPROACHING (moving, not yet halting) can be shown to flip the served
phase. Each test is written to FAIL if the wiring it guards regresses:

  * predict_weight == 0.0 leaves the choice EXACTLY at MaxPressure (structural zero);
  * predict_weight > 0.0 with an approaching platoon FLIPS the served phase away
    from the MaxPressure choice, and records pred_changed / pred_adjusted_decisions;
  * build_controller returns the right controller per config (myopic Hybrid;
    coordination/prediction Coordinated with the right weights);
  * TimingAgent forwards the neighbour note iff forward_note is set;
  * the scale-summary picks the SIMPLEST parity-or-better config honestly.
"""
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import experiment_traffic as ex  # noqa: E402
from coordinated_controller import CoordinatedController  # noqa: E402
from hybrid_controller import HybridController  # noqa: E402
from identity import JunctionIdentity  # noqa: E402
from message_bus import MessageBus  # noqa: E402
from registry import Registry  # noqa: E402
from system_fakeconn import FakeSimulation, FakeTL  # noqa: E402


# --------------------------------------------------------------------------- #
# A TraCI stand-in that exposes getLastStepVehicleNumber (moving = vehnum -
# halting), so the +prediction lever can be exercised at the real control seam.
# The §10-pinned FakeConn deliberately does NOT expose it; this local fake adds
# exactly that one read on top of the same A0 (phase0 = A1->A0, phase1 = B0->A0)
# topology, without touching the pinned module.
# --------------------------------------------------------------------------- #
class _PredLane:
    def __init__(self, halting: dict, vehnum: dict):
        self._halting = dict(halting)
        self._vehnum = dict(vehnum)

    def getLastStepHaltingNumber(self, lane_id):
        if lane_id not in self._halting:
            raise KeyError(lane_id)
        return self._halting[lane_id]

    def getLastStepVehicleNumber(self, lane_id):
        # A lane's total vehicle count defaults to its halting count (moving = 0)
        # unless the test scripts more vehicles present (an approaching platoon).
        if lane_id not in self._halting:
            raise KeyError(lane_id)
        return self._vehnum.get(lane_id, self._halting[lane_id])

    def getLastStepVehicleIDs(self, lane_id):
        if lane_id not in self._halting:
            raise KeyError(lane_id)
        return ()


class _PredConn:
    """FakeConn-shaped stand-in whose lane also answers getLastStepVehicleNumber."""

    def __init__(self, halting: dict, vehnum: dict, sim_time: float = 0.0):
        self.lane = _PredLane(halting, vehnum)
        self.trafficlight = FakeTL()
        self.simulation = FakeSimulation(sim_time)


class _NullAgent:
    """Never proposes -> the deterministic (coord/pred-adjusted) reference stands."""

    model = "null"

    def choose_phase(self, junction_id, num_phases, halting_per_phase,
                     neighbor_note: str = ""):
        return None


class _EchoAgent:
    """Records the neighbour note it was given; never proposes."""

    model = "echo"

    def __init__(self):
        self.notes: list[str] = []

    def choose_phase(self, junction_id, num_phases, halting_per_phase,
                     neighbor_note: str = ""):
        self.notes.append(neighbor_note)
        return None


def _solo_coordination(tls=("A0",)):
    """Coordination scaffolding for a SOLO junction (no neighbours) so the ONLY
    active lever is prediction -- coordination messaging is structurally absent."""
    identities = {jid: JunctionIdentity(jid) for jid in tls}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    adjacency = {jid: [] for jid in tls}
    bus = MessageBus(registry, adjacency)
    return identities, registry, bus, adjacency


def _make_coord_ctrl(conn, agent, *, coord_weight, predict_weight):
    identities, registry, bus, adjacency = _solo_coordination()
    return CoordinatedController(
        conn, ["A0"], agent, identities=identities, registry=registry, bus=bus,
        adjacency=adjacency, coord_weight=coord_weight, predict_weight=predict_weight,
        flow_window=0.0, gate=2)


# Halting: phase-0 queue (A1A0_0)=5 beats phase-1 queue (B0A0_0)=3, so plain
# MaxPressure serves phase 0. A big APPROACHING platoon on phase 1's in-edge
# (13 present, 3 halting => 10 moving) should let +prediction flip to phase 1.
_HALTING = {"A1A0_0": 5, "B0A0_0": 3, "A0A1_0": 0, "A0B0_0": 0}
_VEHNUM_PLATOON_P1 = {"A1A0_0": 5, "B0A0_0": 13, "A0A1_0": 0, "A0B0_0": 0}


# --------------------------------------------------------------------------- #
# 1. Prediction OFF (predict_weight == 0.0) is a structural zero: exactly MP.
# --------------------------------------------------------------------------- #
def test_prediction_off_is_structural_zero():
    conn = _PredConn(_HALTING, _VEHNUM_PLATOON_P1)
    ctrl = _make_coord_ctrl(conn, _NullAgent(), coord_weight=0.0, predict_weight=0.0)
    st = ctrl.tls["A0"]
    used = ctrl.decide("A0", st)
    ev = ctrl.events[-1]
    # MaxPressure serves phase 0 (queue 5 > 3); prediction is inert so used == 0.
    assert used == 0
    assert ev["coord_choice"] == 0
    assert ev["pred_changed"] is False
    assert ctrl.pred_adjusted_decisions == 0
    assert ev["pred_per_phase"] == [0, 0]  # not even computed when the lever is off


# --------------------------------------------------------------------------- #
# 2. Prediction ON flips the served phase toward the approaching platoon.
# --------------------------------------------------------------------------- #
def test_prediction_flips_choice_to_approaching_platoon():
    conn = _PredConn(_HALTING, _VEHNUM_PLATOON_P1)
    ctrl = _make_coord_ctrl(conn, _NullAgent(), coord_weight=0.0, predict_weight=1.0)
    st = ctrl.tls["A0"]
    used = ctrl.decide("A0", st)
    ev = ctrl.events[-1]
    # phase 1: queue 3 + 10 approaching = 13 beats phase 0: queue 5 + 0 = 5.
    assert ev["pred_per_phase"] == [0, 10]
    assert ev["mp_choice"] == 0          # MaxPressure alone would serve phase 0
    assert ev["coord_choice"] == 1       # prediction moves the reference to phase 1
    assert ev["pred_changed"] is True
    assert ctrl.pred_adjusted_decisions == 1
    assert used == 1                     # NullAgent -> the predicted reference stands


def test_prediction_inert_when_no_approaching_traffic():
    # Same queues but NO moving vehicles anywhere (vehnum == halting): prediction
    # is on but has nothing to anticipate, so it must NOT change the choice.
    conn = _PredConn(_HALTING, dict(_HALTING))
    ctrl = _make_coord_ctrl(conn, _NullAgent(), coord_weight=0.0, predict_weight=1.0)
    used = ctrl.decide("A0", ctrl.tls["A0"])
    ev = ctrl.events[-1]
    assert ev["pred_per_phase"] == [0, 0]
    assert ev["pred_changed"] is False
    assert ctrl.pred_adjusted_decisions == 0
    assert used == 0  # unchanged from MaxPressure


def test_prediction_served_phase_audit_is_correct_through_step():
    # Drive a full step() (min_green elapsed) and confirm the SERVED phase recorded
    # on the event is the prediction-driven phase -- the H2 audit must reflect what
    # was actually served, not the pre-prediction MaxPressure choice.
    conn = _PredConn(_HALTING, _VEHNUM_PLATOON_P1)
    ctrl = _make_coord_ctrl(conn, _NullAgent(), coord_weight=0.0, predict_weight=1.0)
    st = ctrl.tls["A0"]
    st["t"] = ctrl.min_green  # next step() is a decision interval
    ctrl.step()
    ev = ctrl.events[-1]
    assert ev["served"] == 1
    assert ev["served_by"] in ("shield",)  # NullAgent: the (predicted) shield ref
    # The served phase is the prediction-driven phase, and no anti-starvation
    # override fired on this first interval.
    assert ev["used"] == 1


# --------------------------------------------------------------------------- #
# 3. The neighbour note carries the approaching-platoon clause iff prediction on.
# --------------------------------------------------------------------------- #
def test_prediction_note_mentions_approaching_only_when_on():
    # OFF: myopic/coordination note has no "Approaching" clause.
    off_agent = _EchoAgent()
    off = _make_coord_ctrl(_PredConn(_HALTING, _VEHNUM_PLATOON_P1), off_agent,
                           coord_weight=0.0, predict_weight=0.0)
    off.decide("A0", off.tls["A0"])
    assert off_agent.notes[-1] == ""  # no neighbours, no prediction -> empty note

    on_agent = _EchoAgent()
    on = _make_coord_ctrl(_PredConn(_HALTING, _VEHNUM_PLATOON_P1), on_agent,
                          coord_weight=0.0, predict_weight=1.0)
    on.decide("A0", on.tls["A0"])
    assert "Approaching" in on_agent.notes[-1]
    assert "phase 1 +10" in on_agent.notes[-1]


# --------------------------------------------------------------------------- #
# 4. Boundary validation of predict_weight (same contract as coord_weight).
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", [-1.0, float("inf"), float("nan"), True, "1"])
def test_predict_weight_rejects_bad_values(bad):
    identities, registry, bus, adjacency = _solo_coordination()
    with pytest.raises((TypeError, ValueError)):
        CoordinatedController(
            _PredConn(_HALTING, _HALTING), ["A0"], _NullAgent(),
            identities=identities, registry=registry, bus=bus, adjacency=adjacency,
            predict_weight=bad)


# --------------------------------------------------------------------------- #
# 5. build_controller returns the correct controller + weights per config.
# --------------------------------------------------------------------------- #
def _coordination_dict():
    identities, registry, bus, adjacency = _solo_coordination()
    return {"identities": identities, "registry": registry, "bus": bus,
            "adjacency": adjacency, "edge_map": {}}


def test_build_controller_myopic_is_hybrid():
    ctrl = ex.build_controller(_PredConn(_HALTING, _HALTING), ["A0"], _NullAgent(),
                               config="myopic")
    assert isinstance(ctrl, HybridController)
    assert not isinstance(ctrl, CoordinatedController)


def test_build_controller_coordination_has_coord_no_prediction():
    ctrl = ex.build_controller(_PredConn(_HALTING, _HALTING), ["A0"], _NullAgent(),
                               config="coordination", coordination=_coordination_dict())
    assert isinstance(ctrl, CoordinatedController)
    assert ctrl.coord_weight == ex.COORD_WEIGHT and ctrl.coord_weight > 0
    assert ctrl.predict_weight == 0.0


def test_build_controller_prediction_has_both_levers():
    ctrl = ex.build_controller(_PredConn(_HALTING, _HALTING), ["A0"], _NullAgent(),
                               config="prediction", coordination=_coordination_dict())
    assert isinstance(ctrl, CoordinatedController)
    assert ctrl.coord_weight == ex.COORD_WEIGHT and ctrl.coord_weight > 0
    assert ctrl.predict_weight == ex.PREDICT_WEIGHT and ctrl.predict_weight > 0


def test_build_controller_coordination_requires_scaffolding():
    with pytest.raises(ValueError):
        ex.build_controller(_PredConn(_HALTING, _HALTING), ["A0"], _NullAgent(),
                            config="coordination", coordination=None)


def test_build_controller_rejects_unknown_config():
    with pytest.raises(ValueError):
        ex.build_controller(_PredConn(_HALTING, _HALTING), ["A0"], _NullAgent(),
                            config="clairvoyant")


# --------------------------------------------------------------------------- #
# 6. TimingAgent forwards the note iff forward_note is set.
# --------------------------------------------------------------------------- #
def test_timing_agent_forwards_note_when_enabled():
    inner = _EchoAgent()
    timing = ex.TimingAgent(inner, forward_note=True)
    timing.choose_phase("A0", 2, [5, 3], neighbor_note="COORD CONTEXT")
    assert inner.notes[-1] == "COORD CONTEXT"
    assert timing.notes_forwarded == 1


def test_timing_agent_drops_note_by_default():
    inner = _EchoAgent()
    timing = ex.TimingAgent(inner)  # default: myopic
    timing.choose_phase("A0", 2, [5, 3], neighbor_note="SHOULD BE DROPPED")
    assert inner.notes[-1] == ""
    assert timing.notes_forwarded == 0


# --------------------------------------------------------------------------- #
# 7. scale_summary picks the SIMPLEST parity-or-better config honestly.
# --------------------------------------------------------------------------- #
def _arm(status):
    return {"verdict": {"status": status}}


def test_scale_summary_prefers_simplest_parity():
    baseline = {"metrics": {}}
    arms = {"myopic": _arm("slm_loses"),
            "coordination": _arm("match"),
            "prediction": _arm("slm_beats")}
    ss = ex._scale_summary(baseline, arms, ex.CONFIGS)
    # coordination is the simplest config that reaches parity-or-better.
    assert ss["simplest_parity_or_better_config"] == "coordination"


def test_scale_summary_honest_negative():
    baseline = {"metrics": {}}
    arms = {c: _arm("slm_loses") for c in ex.CONFIGS}
    ss = ex._scale_summary(baseline, arms, ex.CONFIGS)
    assert ss["simplest_parity_or_better_config"] is None


def test_scale_summary_all_skipped():
    baseline = {"metrics": {}}
    arms = {c: {"skipped": True, "reason": "foundry down"} for c in ex.CONFIGS}
    ss = ex._scale_summary(baseline, arms, ex.CONFIGS)
    assert ss["status"] == "no_arm_ran"
