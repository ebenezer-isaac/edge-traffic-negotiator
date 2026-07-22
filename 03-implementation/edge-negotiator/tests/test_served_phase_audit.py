"""The audit must record the phase ACTUALLY SERVED, not the pre-override proposal
(MASTER-SPEC §4 H2 -- the accident-reconstruction deliverable).

The bug (found by battery): the decision event / §11 record was written INSIDE
``decide()`` with the SLM/shield proposal computed BEFORE the anti-starvation
override in ``step()``. When the fairness shield overrode (a phase hit max_skip),
the SERVED phase (``best``) differed from the recorded phase (``used``), so the
audit hash-chained the WRONG phase; and on a GATE-SKIPPED interval the override
changed the served phase with NO audit record at all.

These tests drive the REAL ``step()`` boundary (not ``decide()`` directly) and
FORCE an anti-starvation override, then assert the recorded served phase == the
phase actually served. They FAIL on the buggy code:
  (a) full path      : the buggy record wrote executed = used (pre-override).
  (b) gate-skip path : the buggy code emitted NO record for the override interval.
  (c) decision_stats : the buggy stats counted the override as "SLM agreed/used".
Both the H1 headline harness (HybridController + mirror -> AuditLog) and the
PRODUCTION path (CoordinatedController's inline §11 log_decision) are covered.

Deterministic diagonal FakeConn (system_fakeconn): phase 0 greens in-lane A1A0_0,
phase 1 greens B0A0_0. A big phase-0 queue makes MaxPressure always prefer phase 0
so phase 1 starves and is force-served at max_skip -- the override under test.
No SUMO / Foundry.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import experiment_traffic as ex  # noqa: E402
from audit_log import AuditLog  # noqa: E402
from conservation import ConservationChecker  # noqa: E402
from coordinated_controller import CoordinatedController, StubAgent  # noqa: E402
from hybrid_controller import HybridController  # noqa: E402
from identity import JunctionIdentity  # noqa: E402
from message_bus import MessageBus  # noqa: E402
from registry import Registry  # noqa: E402
from system_fakeconn import FakeConn  # noqa: E402

_MAX_SKIP = 3
_MIN_GREEN = 10
ADJACENCY = {"A0": ["A1", "B0"], "A1": ["A0", "B1"],
             "B0": ["A0", "B1"], "B1": ["A1", "B0"]}


def _halting(p0: int, p1: int) -> dict:
    """Diagonal in/out lane halting: phase-0 in-lane, phase-1 in-lane, out-lanes."""
    return {"A1A0_0": p0, "B0A0_0": p1, "A0A1_0": 0, "A0B0_0": 0}


class _FixedSLM:
    """Always proposes phase 0 (agreeing with the shield on the busy phase), so an
    override to phase 1 is unambiguously the fairness shield's, never the SLM's."""

    model = "fixed-phase-0"

    def choose_phase(self, junction_id, num_phases, halting_per_phase,
                     neighbor_note: str = ""):  # noqa: ARG002
        return 0


def _drive_hybrid(ctrl, conn, halting_for, intervals):
    """Drive HybridController.step() and MIRROR each new event into a fresh signed
    AuditLog (exactly as experiment_traffic.run_arm does). Returns (audit, served)."""
    audit = AuditLog()
    identities = {"A0": JunctionIdentity("A0")}
    logged = 0
    st = ctrl.tls["A0"]
    served = [st["cur"]]          # interval 0 = ctor initial phase (0)
    interval, guard = 1, 0
    while len(served) < intervals and guard < 100000:
        guard += 1
        pre = (st["mode"] == "green" and st["t"] == ctrl.min_green - 1)
        if pre:
            conn.lane._halting = halting_for(interval)
        ctrl.step()
        logged = ex.mirror_new_events(audit, identities, ctrl.events, logged)
        if pre:
            served.append(st["cur"])
            interval += 1
    assert len(served) == intervals, f"driver stalled: {served}"
    return audit, served


def _decision_records(audit):
    return [e["event"] for e in audit.entries()
            if e["event"].get("kind") == "decision"]


# --------------------------------------------------------------------------- #
# H1 headline harness (HybridController + mirror -> AuditLog).
# --------------------------------------------------------------------------- #

def test_h1_override_records_served_phase_not_proposal():
    """(a) Full (gate-passing) path: on the override interval the SLM proposed
    phase 0 (== shield), but the fairness shield force-serves phase 1. The audit
    record's executed MUST be the SERVED phase (1), not the proposal (0)."""
    conn = FakeConn(_halting(9, 1))
    ctrl = HybridController(conn, ["A0"], _FixedSLM(), gate=0, min_green=_MIN_GREEN)
    audit, served = _drive_hybrid(ctrl, conn, lambda i: _halting(9, 1), intervals=4)

    # Phase 1 starves and is force-served exactly at interval 3 (skip hit max_skip).
    assert served == [0, 0, 0, 1], served
    recs = _decision_records(audit)
    assert len(recs) == 3, recs                       # one per decision interval
    override = recs[2]
    # THE FIX: executed is the SERVED phase (1), not the pre-override proposal (0).
    assert override["executed"] == 1 == served[3]
    assert override["executed"] != override["proposal"]  # proposal was 0 (buggy value)
    assert override["proposal"] == 0                     # provenance preserved
    assert override["slm_phase"] == 0                    # SLM provenance preserved
    assert override["shield_phase"] == 0                 # MaxPressure argmax preserved
    assert override["served_by"] == "anti_starvation"
    # The chain still verifies with the corrected served phase.
    assert audit.verify_chain() is True
    # The non-override intervals faithfully record the SLM-served phase 0.
    assert all(r["executed"] == 0 and r["served_by"] == "slm" for r in recs[:2])


def test_h1_gate_skipped_override_still_emits_served_record():
    """(b) Gate-skipped interval whose served phase the override CHANGES still emits
    an audit record of the SERVED phase. On the buggy code decide() returned early
    (no event) so the phase-1 service was UNRECORDED."""
    conn = FakeConn(_halting(9, 1))
    ctrl = HybridController(conn, ["A0"], _FixedSLM(), gate=2, min_green=_MIN_GREEN)

    # Intervals 1,2 busy (gate passes, phase 1 accrues skips); interval 3 goes
    # quiet (total halting 0 < gate) so the SLM is skipped -- yet phase 1 has hit
    # max_skip, so the override force-serves it.
    def halting_for(i):
        return _halting(0, 0) if i == 3 else _halting(9, 1)

    audit, served = _drive_hybrid(ctrl, conn, halting_for, intervals=4)
    assert served == [0, 0, 0, 1], served

    recs = _decision_records(audit)
    # THE FIX: a record EXISTS for the gate-skipped override interval (3 total, not
    # the buggy 2), and it records the SERVED phase 1.
    assert len(recs) == 3, [r["executed"] for r in recs]
    gate_skip_rec = recs[2]
    assert gate_skip_rec["executed"] == 1 == served[3]
    assert gate_skip_rec["served_by"] == "anti_starvation"
    assert audit.verify_chain() is True


def test_h1_decision_stats_classifies_override_as_anti_starvation():
    """(c) decision_stats attributes the override interval to the fairness shield,
    NOT to the SLM. The buggy stats counted it as an SLM agreement/use."""
    conn = FakeConn(_halting(9, 1))
    ctrl = HybridController(conn, ["A0"], _FixedSLM(), gate=0, min_green=_MIN_GREEN)
    _audit, served = _drive_hybrid(ctrl, conn, lambda i: _halting(9, 1), intervals=4)
    assert served == [0, 0, 0, 1]

    stats = ex.decision_stats(ctrl.events)
    assert stats["decisions"] == 3
    # Exactly ONE override, attributed to anti-starvation (never to the SLM).
    assert stats["anti_starvation_overrides"] == 1
    assert stats["served_by"] == {"slm": 2, "shield": 0, "anti_starvation": 1}
    # The SLM authored only the 2 non-override intervals -- NOT 3 (the buggy count
    # that mislabelled the override as "SLM agreed and used").
    assert stats["slm_agreed_with_shield"] == 2
    assert stats["slm_proposal_served"] == 2
    # The SLM still SPOKE on all three (participation), but authored only two.
    assert stats["slm_valid_proposals"] == 3


# --------------------------------------------------------------------------- #
# PRODUCTION path: CoordinatedController emits the §11 decision record INLINE.
# --------------------------------------------------------------------------- #

def _build_coord(gate: int):
    conn = FakeConn(_halting(9, 1))
    identities = {j: JunctionIdentity(j) for j in ("A0", "A1", "B0", "B1")}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    audit = AuditLog()
    ctrl = CoordinatedController(
        conn, ["A0"], StubAgent(), identities=identities, registry=registry,
        bus=bus, adjacency=ADJACENCY, checker=ConservationChecker(tolerance=2),
        slm_junctions=["A0"], gate=gate, coord_weight=0.0, audit_log=audit)
    return ctrl, conn, audit


def _drive_coord(ctrl, conn, halting_for, intervals=4):
    st = ctrl.tls["A0"]
    served = [st["cur"]]
    interval, guard = 1, 0
    while len(served) < intervals and guard < 100000:
        guard += 1
        pre = (st["mode"] == "green" and st["t"] == ctrl.min_green - 1)
        if pre:
            conn.lane._halting = halting_for(interval)
        ctrl.step()
        if pre:
            served.append(st["cur"])
            interval += 1
    assert len(served) == intervals, f"driver stalled: {served}"
    return served


def test_production_coord_override_records_served_phase():
    """PRODUCTION: the inline §11 kind:"decision" record's executed is the SERVED
    phase (post anti-starvation), not the coordinated pre-override choice. StubAgent
    proposes phase 0; the shield force-serves phase 1 at max_skip."""
    ctrl, conn, audit = _build_coord(gate=0)
    served = _drive_coord(ctrl, conn, lambda i: _halting(9, 1), intervals=4)
    assert served == [0, 0, 0, 1], served

    decs = _decision_records(audit)
    assert len(decs) == 3, [d["executed"] for d in decs]
    # THE FIX: the override interval's §11 executed is the served phase (1).
    assert decs[2]["executed"] == 1 == served[3]
    assert all(d["executed"] == 0 for d in decs[:2])
    # The event log preserves provenance AND the corrected served phase.
    ov_event = ctrl.events[2]
    assert ov_event["used"] == 0 and ov_event["served"] == 1
    assert ov_event["served_by"] == "anti_starvation"
    assert audit.verify_chain() is True


def test_production_coord_gate_skipped_override_emits_served_record():
    """PRODUCTION: a gate-skipped interval whose served phase the override changes
    still emits a §11 decision record of the SERVED phase (no accountability hole).
    Buggy production returned early with NO record for that served-phase change."""
    ctrl, conn, audit = _build_coord(gate=2)

    def halting_for(i):
        return _halting(0, 0) if i == 3 else _halting(9, 1)

    served = _drive_coord(ctrl, conn, halting_for, intervals=4)
    assert served == [0, 0, 0, 1], served

    decs = _decision_records(audit)
    # THE FIX: 3 decision records (not the buggy 2); the gate-skip override interval
    # emits one recording the SERVED phase 1, with an empty driving-input set
    # (no signed inputs were consumed on a gate-skip).
    assert len(decs) == 3, [d["executed"] for d in decs]
    assert decs[2]["executed"] == 1 == served[3]
    assert decs[2]["driving_input_seqs"] == []
    assert audit.verify_chain() is True
