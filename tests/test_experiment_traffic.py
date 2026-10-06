"""Fault-finding tests for the H1 headline harness (src/experiment_traffic.py).

No live dependencies: SUMO is stubbed by the deterministic FakeConn and the SLM is
stubbed by a fake OpenAI client wired into a REAL SLMAgent (so the real parse/shield
seam is exercised, not a hand-waved mock). These cover the wiring that must NOT
silently regress -- each test is written to FAIL if the wiring it guards is removed:

  * both arms build the SAME shield-gated controller (HybridController over MaxPressure);
  * completion is counted as arrival>=0 (metrics.throughput), NEVER len(tripinfo);
  * the audit log is injected, signs the real decisions, and verify_chain +
    Merkle inclusion hold -- and a tampered entry is CAUGHT;
  * the SLM arm is shield-gated: a deliberately-bad proposal is overridden to the
    MaxPressure choice, while a valid proposal is honoured.
"""
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import experiment_traffic as ex  # noqa: E402
from audit_log import AuditLog  # noqa: E402
from controllers import MaxPressureController  # noqa: E402
from hybrid_controller import HybridController  # noqa: E402
from identity import JunctionIdentity  # noqa: E402
from slm_agent import SLMAgent  # noqa: E402
from system_fakeconn import FakeConn, initial_halting  # noqa: E402


# --------------------------------------------------------------------------- #
# A fake OpenAI client so a REAL SLMAgent can be driven with scripted content.
# --------------------------------------------------------------------------- #
class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content):
        self._content = content

    def create(self, **_kwargs):
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, content):
        self.completions = _FakeCompletions(content)


class _FakeClient:
    def __init__(self, content):
        self.chat = _FakeChat(content)


def _slm_agent_returning(content: str) -> SLMAgent:
    """A REAL SLMAgent whose HTTP client is replaced by a scripted fake (offline)."""
    agent = SLMAgent(base_url="http://127.0.0.1:1/v1", model="fake-test-model")
    agent.client = _FakeClient(content)
    return agent


def _fake_conn():
    return FakeConn(initial_halting())


# --------------------------------------------------------------------------- #
# 1. Both arms build the SAME shield-gated controller.
# --------------------------------------------------------------------------- #
def test_build_controller_is_hybrid_over_maxpressure_both_arms():
    baseline_ctrl = ex.build_controller(_fake_conn(), ["A0"], ex.NullAgent())
    slm_ctrl = ex.build_controller(_fake_conn(), ["A0"], _slm_agent_returning('{"phase": 0}'))
    for ctrl in (baseline_ctrl, slm_ctrl):
        # HybridController IS the shield wiring; it extends MaxPressure (the shield).
        assert isinstance(ctrl, HybridController)
        assert isinstance(ctrl, MaxPressureController)
    # The ONLY difference is the proposal source.
    assert isinstance(baseline_ctrl.agent, ex.NullAgent)
    assert isinstance(slm_ctrl.agent, SLMAgent)


def test_null_agent_arm_is_pure_maxpressure():
    conn = _fake_conn()
    ctrl = ex.build_controller(conn, ["A0"], ex.NullAgent(), gate=2)
    st = ctrl.tls["A0"]
    mp_choice = MaxPressureController.decide(ctrl, "A0", st)
    used = ctrl.decide("A0", st)
    # NullAgent proposes nothing -> the MaxPressure shield choice stands verbatim.
    assert used == mp_choice
    assert ctrl.events[-1]["slm_phase"] is None
    assert ctrl.events[-1]["used"] == mp_choice


# --------------------------------------------------------------------------- #
# 2. Completion counting: arrival>=0, NEVER len(tripinfo).
# --------------------------------------------------------------------------- #
_TRIPINFO_MIXED = """<?xml version="1.0"?>
<tripinfos>
  <tripinfo id="c1" depart="0.00" arrival="50.00" duration="50.00" waitingTime="5.00" timeLoss="4.00" routeLength="100.0"/>
  <tripinfo id="c2" depart="1.00" arrival="80.00" duration="79.00" waitingTime="9.00" timeLoss="7.00" routeLength="200.0"/>
  <tripinfo id="c3" depart="2.00" arrival="120.00" duration="118.00" waitingTime="20.00" timeLoss="15.00" routeLength="300.0"/>
  <tripinfo id="r1" depart="3.00" arrival="-1.00" duration="200.00" waitingTime="150.00" timeLoss="140.00" routeLength="400.0"/>
  <tripinfo id="r2" depart="4.00" arrival="-1.00" duration="210.00" waitingTime="160.00" timeLoss="150.00" routeLength="400.0"/>
  <tripinfo id="u1" depart="-1.00" arrival="-1.00" duration="0.00" waitingTime="0.00" timeLoss="0.00" routeLength="0.0"/>
</tripinfos>
"""


def test_completion_counts_arrivals_not_file_length(tmp_path):
    path = tmp_path / "tripinfo_mixed.xml"
    path.write_text(_TRIPINFO_MIXED, encoding="utf-8")
    m = ex.metrics_from_tripinfo(str(path), teleports=7, sim_steps=300)
    # 6 entries in the file, but only 3 completed (arrival >= 0).
    assert m["loaded"] == 6
    assert m["completed"] == 3
    assert m["completed"] != m["loaded"]  # the survivorship trap: never len(tripinfo)
    # departed = 5 (one undeparted, depart == -1); running = 2 (departed, no arrival).
    assert m["departed"] == 5
    assert m["running_at_end"] == 2
    assert m["undeparted"] == 1
    assert m["teleports"] == 7
    # mean_network_delay averages over ALL departed (completed + running), not just
    # survivors: (50+79+118+200+210)/5 = 131.4, strictly worse than the completed-
    # only mean (82.33) -- so stranding slow trips cannot look like an improvement.
    assert m["mean_network_delay_s"] == pytest.approx((50 + 79 + 118 + 200 + 210) / 5)
    assert m["avg_travel_time_completed_s"] == pytest.approx((50 + 79 + 118) / 3)
    assert m["mean_network_delay_s"] > m["avg_travel_time_completed_s"]
    # median completed travel time = middle of {50, 79, 118}.
    assert m["median_travel_time_completed_s"] == pytest.approx(79.0)


def test_metrics_completed_column_would_break_if_using_len():
    # Guard the specific bug the spec warns about: had the harness reported
    # len(entries) as completed, this would read 6, not 3.
    import io
    import xml.etree.ElementTree as ET
    root = ET.fromstring(_TRIPINFO_MIXED)
    naive_len = len(root.findall("tripinfo"))
    assert naive_len == 6  # the WRONG number
    # metrics_from_tripinfo must not agree with the naive len.
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(_TRIPINFO_MIXED)
        tmp = fh.name
    try:
        m = ex.metrics_from_tripinfo(tmp, teleports=0, sim_steps=1)
    finally:
        os.unlink(tmp)
    assert m["completed"] == 3 and m["completed"] != naive_len
    _ = io  # silence unused import linters


# --------------------------------------------------------------------------- #
# 3. Audit injected, signs real decisions, verify_chain + inclusion hold,
#    and a tampered entry is caught.
# --------------------------------------------------------------------------- #
def _run_decisions_into_audit(agent, n=3):
    conn = _fake_conn()
    ctrl = ex.build_controller(conn, ["A0"], agent, gate=2)
    identities = {"A0": JunctionIdentity("A0")}
    audit = AuditLog()
    logged = 0
    for _ in range(n):
        ctrl.decide("A0", ctrl.tls["A0"])
        logged = ex.mirror_new_events(audit, identities, ctrl.events, logged)
    pubkeys = {jid: ident.public_key for jid, ident in identities.items()}
    return audit, pubkeys, ctrl


def test_audit_injected_verify_chain_and_inclusion():
    audit, pubkeys, ctrl = _run_decisions_into_audit(ex.NullAgent(), n=3)
    bundle = ex.audit_bundle(audit, pubkeys)
    assert bundle["enabled"] is True
    assert bundle["entries"] == 3
    assert bundle["decision_entries"] == 3           # every mirrored record is a decision
    assert bundle["verify_chain"] is True
    assert bundle["verify_signatures"] is True       # signed by the junction identity
    assert bundle["inclusion_proof_valid"] is True   # Merkle inclusion proof holds
    # The mirrored records reflect the REAL controller decisions.
    assert len(ctrl.events) == 3
    kinds = {e["event"]["kind"] for e in audit.entries()}
    assert kinds == {"decision"}


def test_audit_tamper_is_detected():
    audit, pubkeys, _ = _run_decisions_into_audit(ex.NullAgent(), n=3)
    # Sanity: clean chain verifies.
    assert audit.verify_chain() is True
    # Tamper with a stored decision's executed phase AFTER the fact.
    audit._log[0]["event"]["executed"] = 999
    assert audit.verify_chain() is False
    # audit_bundle must refuse to emit a green result on a broken chain (§10).
    with pytest.raises(RuntimeError):
        ex.audit_bundle(audit, pubkeys)


def test_audit_bundle_empty_log():
    audit = AuditLog()
    bundle = ex.audit_bundle(audit, {})
    assert bundle["entries"] == 0
    assert bundle["merkle_root"] is None
    assert bundle["inclusion_proof_valid"] is None


# --------------------------------------------------------------------------- #
# 4. The SLM arm is shield-gated (deliberately-bad proposal -> overridden).
# --------------------------------------------------------------------------- #
def test_slm_parser_rejects_out_of_range_phase():
    # The real validation seam: an out-of-range phase index is rejected -> None,
    # which is what makes the shield fall back to MaxPressure.
    assert SLMAgent._parse('{"phase": 99}', num_phases=2) is None
    assert SLMAgent._parse('{"phase": 1}', num_phases=2) == 1
    assert SLMAgent._parse("banana", num_phases=2) is None


def test_bad_slm_proposal_is_overridden_by_shield():
    conn = _fake_conn()
    # A deliberately-bad SLM: proposes phase 99 (out of range for the 2-phase TLS).
    bad_agent = _slm_agent_returning('{"phase": 99}')
    ctrl = ex.build_controller(conn, ["A0"], bad_agent, gate=2)
    st = ctrl.tls["A0"]
    mp_choice = MaxPressureController.decide(ctrl, "A0", st)
    used = ctrl.decide("A0", st)
    # Shield disposes: the invalid proposal is dropped and MaxPressure stands.
    assert used == mp_choice
    ev = ctrl.events[-1]
    assert ev["slm_phase"] is None       # parser rejected 99 -> None
    assert ev["used"] == mp_choice
    assert ev["overridden"] is True


def test_valid_slm_proposal_is_honoured():
    conn = _fake_conn()
    st_probe = ex.build_controller(_fake_conn(), ["A0"], ex.NullAgent())
    mp_choice = MaxPressureController.decide(st_probe, "A0", st_probe.tls["A0"])
    # Choose a valid phase DIFFERENT from the MaxPressure choice so "honoured"
    # is distinguishable from "shield fallback".
    other = 1 - mp_choice
    good_agent = _slm_agent_returning('{"phase": %d}' % other)
    ctrl = ex.build_controller(_fake_conn(), ["A0"], good_agent, gate=2)
    used = ctrl.decide("A0", ctrl.tls["A0"])
    assert used == other                       # the valid SLM proposal wins
    ev = ctrl.events[-1]
    assert ev["slm_phase"] == other
    assert ev["used"] == other


def test_event_gate_skips_slm_when_quiet():
    # Below the gate the SLM is not consulted at all (event-gated) -> no event,
    # shield choice returned. A regression that always calls the SLM would append
    # an event here and fail this test.
    conn = FakeConn({"A1A0_0": 0, "B0A0_0": 0, "A0A1_0": 0, "A0B0_0": 0})
    calls = {"n": 0}

    class _CountingAgent:
        model = "counting"

        def choose_phase(self, *a, **k):
            calls["n"] += 1
            return 0

    ctrl = ex.build_controller(conn, ["A0"], _CountingAgent(), gate=2)
    ctrl.decide("A0", ctrl.tls["A0"])
    assert calls["n"] == 0            # gate held: SLM never consulted
    assert ctrl.events == []          # no decision event emitted when quiet


# --------------------------------------------------------------------------- #
# 5. TimingAgent records per-call latency and drops the neighbour note (myopic).
# --------------------------------------------------------------------------- #
def test_timing_agent_records_latency_and_is_myopic():
    seen = {"note": "unset"}

    class _EchoAgent:
        model = "echo"

        def choose_phase(self, junction_id, num_phases, halting_per_phase,
                         neighbor_note=""):
            seen["note"] = neighbor_note
            return 0

    timing = ex.TimingAgent(_EchoAgent())
    out = timing.choose_phase("A0", 2, [5, 0], neighbor_note="SHOULD BE DROPPED")
    assert out == 0
    assert timing.calls == 1
    assert len(timing.latencies_s) == 1
    assert timing.latencies_s[0] >= 0.0
    # Myopic: the neighbour note is NOT forwarded to the inner agent.
    assert seen["note"] == ""
    assert timing.model == "echo"


def test_timing_agent_counts_none_returns():
    timing = ex.TimingAgent(ex.NullAgent())
    assert timing.choose_phase("A0", 2, [5, 0]) is None
    assert timing.none_returns == 1
