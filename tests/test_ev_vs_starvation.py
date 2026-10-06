"""EV-preempt precedence over the anti-starvation shield, driven via step()
(spec §6.8 precedence rule + §6.2 accountability spine).

Design rule under test (coordinator decision, consistent with LEGITIMATE_DEGRADATION
= "approach deferred by an admissible emergency preemption within policy"): an
ADMISSIBLE emergency preemption OUTRANKS anti-starvation fairness -- the shield must
NEVER cut an active ambulance green for cross-traffic fairness, and the §11
kind:"decision" audit record must ALWAYS be emitted (never skipped by an override).

The two failure modes this catches (it must FAIL for either):
  (i)  the anti-starvation override cuts the active EV preempt -> the served phase
       leaves the ambulance's phase while the preempt is active;
  (ii) the override short-circuits so decide() is skipped that interval -> the EV
       kind:"decision" record is missing (accountability hole).

Control: with NO EV present, a genuine non-emergency starvation STILL gets
force-served -> the shield itself still works; the precedence fix only suppresses
the override during an active admissible preempt.

No SUMO. The EmergencyController is driven through step() (NOT decide() directly),
so this exercises the real step()-boundary decision path where the bug lived.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from audit_log import AuditLog  # noqa: E402
from conservation import ConservationChecker  # noqa: E402
from coordinated_controller import StubAgent  # noqa: E402
from emergency_controller import EmergencyController  # noqa: E402
from identity import JunctionIdentity  # noqa: E402
from message_bus import MessageBus  # noqa: E402
from registry import Registry  # noqa: E402
import run_coordinated  # noqa: E402
from system_fakeconn import FakeConn  # noqa: E402

ADJACENCY = run_coordinated.ADJACENCY
_EV_ID = "AMB0"
_MAX_SKIP = 3
_MIN_GREEN = 10
_YELLOW = 3


def _build_controller(with_ev: bool):
    """EmergencyController on A0. Local halting makes plain MaxPressure prefer
    PHASE 1 (B0A0_0 large). When present, the ambulance sits on the phase-0
    in-lane inside ev_horizon -> an admissible LOCAL-SENSING preempt to phase 0
    every interval, so phase 1 (approach B) accrues skips. An AuditLog is injected
    so the §11 decision records can be counted (the accountability assertion)."""
    halting = {
        "A1A0_0": 1,   # phase-0 in-lane (small queue)
        "B0A0_0": 8,   # phase-1 in-lane (large) -> plain MaxPressure prefers phase 1
        "A0A1_0": 0,   # out-lanes
        "A0B0_0": 0,
    }
    if with_ev:
        vehicles = {"A1A0_0": (_EV_ID,)}
        classes = {_EV_ID: "emergency"}
        positions = {_EV_ID: 190.0}  # gap 10 m < ev_horizon (195) -> sensed
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
    audit = AuditLog()
    ctrl = EmergencyController(
        conn, ["A0"], StubAgent(), identities=identities, registry=registry,
        bus=bus, adjacency=ADJACENCY, checker=checker, slm_junctions=["A0"],
        gate=0, coord_weight=0.0, audit_log=audit,
        ev_bus=ev_bus, corroboration_required=False, preemption_enabled=True,
        advance_claims_enabled=False, verbose=False,
    )
    # Defaults must match the constants this test reasons about.
    assert ctrl.min_green == _MIN_GREEN and ctrl.yellow == _YELLOW
    assert ctrl.max_skip == _MAX_SKIP and ctrl.anti_starvation_enabled is True
    return ctrl, audit


def _drive(ctrl, intervals: int):
    """Drive step() through `intervals` decision intervals (interval 0 = ctor's
    initial green). Record the served phase at each boundary decision."""
    st = ctrl.tls["A0"]
    served = [st["cur"]]      # interval 0 = ctor initial phase (0)
    guard = 0
    while len(served) < intervals and guard < 100000:
        guard += 1
        pre = (st["mode"] == "green" and st["t"] == ctrl.min_green - 1)
        ctrl.step()
        if pre:
            served.append(st["cur"])
    assert len(served) == intervals, f"driver stalled: {served}"
    return served


def _ev_decision_records(audit):
    """§11 kind:"decision" records emitted by the EV path (policies == corroboration)."""
    return audit.entries(lambda e: e["event"]["kind"] == "decision"
                         and e["event"]["policies_applied"] == ["corroboration"])


# --------------------------------------------------------------------------- #
# EV preempt OUTRANKS the shield, held across >= max_skip+1 intervals.
# --------------------------------------------------------------------------- #

def test_active_ev_preempt_is_not_cut_by_starvation_shield():
    intervals = _MAX_SKIP + 3        # 6 > max_skip+1: phase 1 provably exceeds max_skip
    ctrl, audit = _build_controller(with_ev=True)
    served = _drive(ctrl, intervals)
    st = ctrl.tls["A0"]
    ev_phase = 0                     # phase 0 greens the ambulance's approach (A1A0)

    # (i) EV precedence: the ambulance's phase is served at EVERY interval; the
    # shield NEVER overrode it to the starving cross-approach (phase 1).
    assert served == [ev_phase] * intervals, served
    # The shield WOULD have fired absent the lock: phase 1's skip pushed past
    # max_skip while it was (legitimately) deferred by the preempt. The skip
    # counter STILL ages (so fairness resumes the instant the preempt ends)...
    assert st["skip"][1] > _MAX_SKIP, st["skip"]
    # ...but that over-max_skip is LEGITIMATE_DEGRADATION, NOT a shield failure:
    # the violation increment is suppressed while the admissible preempt holds, so
    # anti_starvation_violations stays 0 (this directly guards D7). Removing the
    # `not preempt_locked` guard in _record_service makes this assertion FAIL --
    # violations would climb to (skip[1] - max_skip) == 3 here.
    assert ctrl.anti_starvation_violations == 0, ctrl.anti_starvation_violations

    # (ii) Accountability: an EV decision record is emitted for EVERY decision
    # interval (intervals 1..N; interval 0 is the ctor, no decide()). A short-
    # circuiting override would have skipped decide() -> fewer records.
    ev_dec = _ev_decision_records(audit)
    assert len(ev_dec) == intervals - 1, len(ev_dec)
    assert len(ev_dec) >= _MAX_SKIP + 1
    for rec in ev_dec:
        assert rec["event"]["executed"] == ev_phase          # preempt executed
        assert rec["event"]["classification"] == "LEGITIMATE"

    # Cross-check the structured EV event log agrees: one admissible local-sensing
    # preempt per decision interval, none withheld.
    local = [e for e in ctrl.ev_events if e["source"] == "local_sensing"]
    assert len(local) == intervals - 1
    assert all(e["admissible"] and e["executed"] == ev_phase for e in local)


def test_preempt_lock_reflects_current_tick_only():
    """The lock is a per-tick signal: after driving the EV run it holds phase 0,
    and _preempt_locked_phase is consulted AFTER decide() runs (so it is current)."""
    ctrl, _audit = _build_controller(with_ev=True)
    _drive(ctrl, _MAX_SKIP + 2)
    assert ctrl._preempt_locked_phase("A0") == 0
    # A junction with no EV layer / no decision this tick has no lock.
    assert ctrl._preempt_locked_phase("A1") is None


# --------------------------------------------------------------------------- #
# Control: the shield STILL force-serves a genuine non-emergency starvation.
# --------------------------------------------------------------------------- #

def test_shield_still_force_serves_when_no_active_preempt():
    intervals = _MAX_SKIP + 3
    ctrl, _audit = _build_controller(with_ev=False)
    served = _drive(ctrl, intervals)

    # No EV -> plain MaxPressure serves phase 1 (larger queue); phase 0 starves and
    # MUST be force-served by the shield once it reaches max_skip (interval 4 here).
    assert served[0] == 0                          # ctor init
    assert 1 in served, served                     # cross-traffic served on pressure
    forced0 = [i for i in range(1, intervals) if served[i] == 0]
    assert forced0, f"shield failed to force-serve the starved phase: {served}"
    # The override prevented any counter from exceeding max_skip -> violations 0.
    assert ctrl.anti_starvation_violations == 0
