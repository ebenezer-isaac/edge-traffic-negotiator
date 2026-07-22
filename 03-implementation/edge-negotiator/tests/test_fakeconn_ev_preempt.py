"""Phase-6 (§6.2, build F4): the committed FakeConn vehicle-API stub + a POSITIVE
assertion that a scripted REAL emergency vehicle, sensed locally, is preempted.

No SUMO. The stub (system_fakeconn.FakeConn) exposes the corrected TraCI surface
the EV detector reads:
  * lane.getLastStepVehicleIDs(lane)   -- vehicle ids on a lane (LANE call, F4)
  * lane.getLength(lane)               -- lane length for horizon test
  * vehicle.getVehicleClass(vid)       -- "emergency" triggers detection
  * vehicle.getLanePosition(vid)       -- position for (len - pos) <= ev_horizon
  * simulation.getTime()               -- monotonic sim clock

The preemption assertion is CAUSAL, not coincidental: local halting is set so
plain MaxPressure prefers the OTHER phase, so an executed choice of the EV's
phase can only come from the EV preemption. A no-EV control proves the same
controller returns the MaxPressure phase when no ambulance is present.
"""
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from coordinated_controller import StubAgent  # noqa: E402
from conservation import ConservationChecker  # noqa: E402
from emergency_controller import EmergencyController  # noqa: E402
from identity import JunctionIdentity  # noqa: E402
from message_bus import MessageBus  # noqa: E402
from net_topology import edge_of_lane  # noqa: E402
from registry import Registry  # noqa: E402
import run_coordinated  # noqa: E402
from system_fakeconn import FakeConn, FakeSimulation  # noqa: E402

ADJACENCY = run_coordinated.ADJACENCY
_EV_ID = "AMB0"


def _build_ev_controller(with_ev: bool):
    """EmergencyController on A0 with a fake conn. Local halting makes plain
    MaxPressure prefer PHASE 1 (B0A0_0 large); the ambulance, when present, is on
    the phase-0 in-lane near the stop line. corroboration_required=False (naive
    victim) but local sensing needs no corroboration anyway; advance claims off
    so this is pure local-sensing preemption."""
    halting = {
        "A1A0_0": 1,   # phase-0 in-lane (small queue)
        "B0A0_0": 8,   # phase-1 in-lane (large queue) -> MaxPressure prefers phase 1
        "A0A1_0": 0,   # out-lanes
        "A0B0_0": 0,
    }
    # Script one emergency vehicle on the phase-0 in-lane, 190 m along a 200 m
    # lane -> (200 - 190) = 10 m from the stop line, inside ev_horizon (195 m).
    if with_ev:
        vehicles = {"A1A0_0": (_EV_ID,)}
        classes = {_EV_ID: "emergency"}
        positions = {_EV_ID: 190.0}
    else:
        vehicles, classes, positions = {}, {}, {}
    conn = FakeConn(halting, vehicles=vehicles, classes=classes, positions=positions)

    tls = ["A0", "A1", "B0", "B1"]
    identities = {jid: JunctionIdentity(jid) for jid in tls}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    ev_bus = MessageBus(registry, ADJACENCY)
    checker = ConservationChecker(tolerance=2)
    ctrl = EmergencyController(
        conn, ["A0"], StubAgent(), identities=identities, registry=registry,
        bus=bus, adjacency=ADJACENCY, checker=checker, slm_junctions=["A0"],
        gate=0, coord_weight=0.0,
        ev_bus=ev_bus, corroboration_required=False, preemption_enabled=True,
        advance_claims_enabled=False, verbose=False,
    )
    return ctrl, conn


# --------------------------------------------------------------------------- #
# The vehicle-API stub exposes exactly the corrected surface (build F4).
# --------------------------------------------------------------------------- #

def test_stub_exposes_corrected_vehicle_api():
    _ctrl, conn = _build_ev_controller(with_ev=True)
    # LANE calls.
    assert conn.lane.getLastStepVehicleIDs("A1A0_0") == (_EV_ID,)
    assert conn.lane.getLastStepVehicleIDs("B0A0_0") == ()      # none scripted
    assert conn.lane.getLength("A1A0_0") == 200.0               # default length
    # VEHICLE calls.
    assert conn.vehicle.getVehicleClass(_EV_ID) == "emergency"
    assert conn.vehicle.getLanePosition(_EV_ID) == 190.0
    # F4: getLastStepVehicleIDs is a LANE call, NOT a vehicle call. If the stub
    # exposed it on .vehicle, a regression could read ids off the wrong object.
    assert not hasattr(conn.vehicle, "getLastStepVehicleIDs")


def test_stub_raises_on_unknown_ids_like_sumo():
    _ctrl, conn = _build_ev_controller(with_ev=True)
    # All lane calls raise on a genuinely unknown lane (mirrors TraCIException).
    with pytest.raises(KeyError):
        conn.lane.getLastStepHaltingNumber("NOPE_0")
    with pytest.raises(KeyError):
        conn.lane.getLastStepVehicleIDs("NOPE_0")
    with pytest.raises(KeyError):
        conn.lane.getLength("NOPE_0")
    with pytest.raises(KeyError):
        conn.vehicle.getVehicleClass("ghost")
    with pytest.raises(KeyError):
        conn.vehicle.getLanePosition("ghost")


def test_simulation_clock_is_monotonic():
    sim = FakeSimulation(start=0.0)
    t0 = sim.getTime()
    assert t0 == 0.0
    assert sim.getTime() == t0          # side-effect-free: repeated reads equal
    sim.advance(1.0)
    t1 = sim.getTime()
    assert t1 >= t0 and t1 == 1.0
    sim.advance(0.0)                    # zero advance is allowed (non-decreasing)
    assert sim.getTime() == t1
    with pytest.raises(ValueError):     # never goes backwards
        sim.advance(-1.0)
    with pytest.raises(TypeError):
        sim.advance("later")


# --------------------------------------------------------------------------- #
# POSITIVE assertion: the scripted real EV is preempted, and CAUSALLY so.
# --------------------------------------------------------------------------- #

def test_scripted_real_ev_is_preempted():
    ctrl, _conn = _build_ev_controller(with_ev=True)
    st = ctrl.tls["A0"]
    # The EV is on in_lanes[0]; the phase that greens its edge is the preempt phase.
    ev_lane = st["in_lanes"][0]
    assert ev_lane == "A1A0_0"
    ev_phase = ctrl._phase_serving(st, edge_of_lane(ev_lane))
    assert ev_phase == 0, "phase 0 greens the EV's approach"

    executed = ctrl.decide("A0", st)

    # decide() returns the preempt phase -> the EV took the signal.
    assert executed == ev_phase, f"expected preempt to phase {ev_phase}, got {executed}"
    # The EV event was logged as an ADMISSIBLE local-sensing preemption of THIS EV.
    ev_local = [e for e in ctrl.ev_events if e["source"] == "local_sensing"]
    assert len(ev_local) == 1
    ev = ev_local[0]
    assert ev["ev_id"] == _EV_ID
    assert ev["admissible"] is True
    assert ev["corroborated"] is True          # local sensing is self-corroborating
    assert ev["preempt_phase"] == ev_phase
    assert ev["executed"] == ev_phase


def test_preemption_is_causal_not_coincidental():
    """Same controller, NO ambulance: MaxPressure prefers phase 1, so the executed
    choice is 1 and there is no local-sensing event. Contrast with the EV run
    (executed 0) proves the preemption CHANGED the outcome -- it is causal."""
    ctrl, _conn = _build_ev_controller(with_ev=False)
    st = ctrl.tls["A0"]
    executed = ctrl.decide("A0", st)
    assert executed == 1, "with no EV, plain MaxPressure serves the larger queue (phase 1)"
    assert [e for e in ctrl.ev_events if e["source"] == "local_sensing"] == []


def test_out_of_horizon_ev_is_not_preempted():
    """An emergency vehicle still far from the stop line (outside ev_horizon) must
    NOT trigger preemption -- guards against a stub that detects any 'emergency'
    class regardless of position."""
    ctrl, conn = _build_ev_controller(with_ev=True)
    # 200 m lane, ev_horizon 195, detect iff (len - pos) <= 195 i.e. pos >= 5.
    # pos 4 -> gap 196 > 195 -> OUTSIDE, must not preempt.
    conn.vehicle._positions[_EV_ID] = 4.0
    st = ctrl.tls["A0"]
    executed = ctrl.decide("A0", st)
    assert executed == 1, "EV beyond ev_horizon must not preempt"
    assert [e for e in ctrl.ev_events if e["source"] == "local_sensing"] == []


def test_horizon_inclusive_boundary_preempts():
    """Pins the INCLUSIVE <= 195 boundary exactly: pos 5 on a 200 m lane -> gap
    195 == ev_horizon -> must still detect + preempt. Together with the pos-4
    out-case this brackets the boundary to a single metre, so a regression that
    shrinks ev_horizon is caught (not just any horizon in a wide range)."""
    ctrl, conn = _build_ev_controller(with_ev=True)
    conn.vehicle._positions[_EV_ID] = 5.0   # gap = 200 - 5 = 195 == horizon
    st = ctrl.tls["A0"]
    executed = ctrl.decide("A0", st)
    assert executed == 0, "EV exactly at ev_horizon (inclusive) must preempt"
    ev_local = [e for e in ctrl.ev_events if e["source"] == "local_sensing"]
    assert len(ev_local) == 1 and ev_local[0]["ev_id"] == _EV_ID
