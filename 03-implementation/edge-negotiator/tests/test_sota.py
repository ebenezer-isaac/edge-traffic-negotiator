"""Fault-finding tests for the SOTA delay-aware myopic controller
(slm_agent.SYSTEM_DELAY_AWARE, controllers.green_waiting, HybridController.delay_aware,
build_controller "sota", experiment_sota assembly).

Written to FAIL if: the delay-aware prompt is not actually used, the waiting-time
state is not passed, the delay-aware path breaks the served-phase audit or the shield,
or the sota A/B delta logic is wrong. No live model/SUMO.
"""
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import experiment_sota as es  # noqa: E402
import experiment_traffic as ex  # noqa: E402
from controllers import MaxPressureController  # noqa: E402
from hybrid_controller import HybridController  # noqa: E402
from slm_agent import SYSTEM, SYSTEM_DELAY_AWARE, SLMAgent  # noqa: E402
from system_fakeconn import FakeSimulation, FakeTL  # noqa: E402


# --------------------------------------------------------------------------- #
# A capturing fake OpenAI client: records the messages sent, returns scripted JSON.
# --------------------------------------------------------------------------- #
class _CapClient:
    def __init__(self, content):
        self._content = content
        self.last_messages = None

        class _Chat:
            def __init__(self, outer):
                self._outer = outer
                self.completions = self

            def create(self, **kw):
                self._outer.last_messages = kw["messages"]

                class _R:
                    def __init__(self, c):
                        self.choices = [type("C", (), {"message": type("M", (), {"content": c})()})()]
                return _R(self._outer._content)
        self.chat = _Chat(self)


def _slm_with(content):
    a = SLMAgent(base_url="http://127.0.0.1:1/v1", model="fake")
    a.client = _CapClient(content)
    return a


# --------------------------------------------------------------------------- #
# 1. Delay-aware mode uses SYSTEM_DELAY_AWARE + the waiting-time/current state.
# --------------------------------------------------------------------------- #
def test_delay_aware_uses_delay_prompt_and_state():
    a = _slm_with('{"phase": 1}')
    ctx = [{"queue": 5, "waiting": 12.0, "current": True},
           {"queue": 3, "waiting": 40.0, "current": False}]
    out = a.choose_phase("A0", 2, [5, 3], phase_context=ctx)
    assert out == 1
    msgs = a.client.last_messages
    assert msgs[0]["content"] == SYSTEM_DELAY_AWARE     # delay-aware system prompt
    user = msgs[1]["content"]
    assert "wait=12s" in user and "wait=40s" in user   # accumulated waiting-time state
    assert "(CURRENT)" in user                                    # hysteresis marker


def test_green_waiting_uses_real_traci_lane_api():
    # Guard against API drift / a fictional method: the reader green_waiting relies
    # on MUST exist on the real traci.lane domain (SUMO), not just on a mock.
    import traci  # noqa: PLC0415
    assert hasattr(traci.lane, "getWaitingTime")


def test_qwen3_gets_no_think_suffix_others_do_not():
    q = SLMAgent(base_url="http://127.0.0.1:1/v1", model="qwen3-0.6b-generic-gpu:2")
    assert q.think_suffix == " /no_think"
    other = SLMAgent(base_url="http://127.0.0.1:1/v1", model="qwen2.5-0.5b")
    assert other.think_suffix == ""


def test_no_think_suffix_appended_to_system_prompt():
    a = _slm_with('{"phase": 0}')
    a.think_suffix = " /no_think"          # simulate a qwen3 agent
    a.choose_phase("A0", 2, [5, 0])
    assert a.client.last_messages[0]["content"].endswith(" /no_think")


def test_queue_only_mode_unchanged_when_no_context():
    a = _slm_with('{"phase": 0}')
    a.choose_phase("A0", 2, [5, 3])          # no phase_context -> vanilla
    msgs = a.client.last_messages
    assert msgs[0]["content"] == SYSTEM       # original prompt, byte-for-byte
    assert "mean_wait" not in msgs[1]["content"]


# --------------------------------------------------------------------------- #
# 2. green_waiting reads the waiting-time API and is transport-safe.
# --------------------------------------------------------------------------- #
class _WaitLane:
    # Exposes the REAL traci.lane waiting API (getWaitingTime), not a fictional one.
    def __init__(self, halting, waiting):
        self._h = dict(halting)
        self._w = dict(waiting)

    def getLastStepHaltingNumber(self, l):
        return self._h.get(l, 0)

    def getWaitingTime(self, l):
        return self._w.get(l, 0.0)


class _WaitConn:
    def __init__(self, halting, waiting):
        self.lane = _WaitLane(halting, waiting)
        self.trafficlight = FakeTL()
        self.simulation = FakeSimulation(0.0)


class _NoWaitConn:
    """Conn WITHOUT getLastStepMeanWaitingTime (like the pinned FakeConn)."""
    class _L:
        def getLastStepHaltingNumber(self, l):
            return 0
    def __init__(self):
        self.lane = self._L()
        self.trafficlight = FakeTL()
        self.simulation = FakeSimulation(0.0)


def test_green_waiting_reads_mean_wait():
    conn = _WaitConn({"A1A0_0": 5, "B0A0_0": 3, "A0A1_0": 0, "A0B0_0": 0},
                     {"A1A0_0": 30.0, "B0A0_0": 4.0, "A0A1_0": 0.0, "A0B0_0": 0.0})
    c = MaxPressureController(conn, ["A0"])
    st = c.tls["A0"]
    # phase 0 serves in-lane A1A0_0 (wait 30), phase 1 serves B0A0_0 (wait 4).
    assert c.green_waiting(st, 0) == pytest.approx(30.0)
    assert c.green_waiting(st, 1) == pytest.approx(4.0)


def test_green_waiting_zero_without_api():
    c = MaxPressureController(_NoWaitConn(), ["A0"])
    st = c.tls["A0"]
    assert c.green_waiting(st, 0) == 0.0   # transport-safe: no waiting API -> 0


# --------------------------------------------------------------------------- #
# 3. HybridController delay_aware: passes context, shield-gates, audit correct.
# --------------------------------------------------------------------------- #
class _CapAgent:
    model = "cap"

    def __init__(self, ret):
        self.ret = ret
        self.last_context = "unset"

    def choose_phase(self, jid, n, halting, neighbor_note="", phase_context=None):
        self.last_context = phase_context
        return self.ret


def _wait_conn():
    return _WaitConn({"A1A0_0": 5, "B0A0_0": 3, "A0A1_0": 0, "A0B0_0": 0},
                     {"A1A0_0": 30.0, "B0A0_0": 4.0, "A0A1_0": 0.0, "A0B0_0": 0.0})


def test_delay_aware_controller_passes_context():
    agent = _CapAgent(0)
    ctrl = HybridController(_wait_conn(), ["A0"], agent, gate=2, delay_aware=True)
    ctrl.decide("A0", ctrl.tls["A0"])
    ctx = agent.last_context
    assert isinstance(ctx, list) and len(ctx) == 2
    assert set(ctx[0]) == {"queue", "waiting", "current"}
    assert any(c["current"] for c in ctx)          # a current-phase marker is set
    assert ctx[0]["waiting"] == pytest.approx(30.0)  # real waiting-time threaded in


def test_delay_aware_off_by_default_no_context():
    agent = _CapAgent(0)
    ctrl = HybridController(_wait_conn(), ["A0"], agent, gate=2)  # default off
    ctrl.decide("A0", ctrl.tls["A0"])
    # Vanilla path calls choose_phase WITHOUT phase_context -> it defaults to None.
    assert agent.last_context is None


def test_delay_aware_none_proposal_falls_back_to_shield():
    # In delay-aware mode too, a None proposal (the real SLM parse-reject path) must
    # fall back to the MaxPressure choice (shield disposes).
    agent = _CapAgent(None)
    ctrl = HybridController(_wait_conn(), ["A0"], agent, gate=2, delay_aware=True)
    st = ctrl.tls["A0"]
    mp = MaxPressureController.decide(ctrl, "A0", st)
    used = ctrl.decide("A0", st)
    assert used == mp
    assert ctrl.events[-1]["slm_phase"] is None
    assert ctrl.events[-1]["overridden"] is True


def test_delay_aware_slm_parse_rejects_out_of_range():
    # The out-of-range shield lives in the SLM parse: a delay-aware reply of an
    # invalid index returns None (-> the controller then uses the shield).
    a = _slm_with('{"phase": 99}')
    out = a.choose_phase("A0", 2, [5, 3],
                         phase_context=[{"queue": 5, "waiting": 1.0, "current": True},
                                        {"queue": 3, "waiting": 1.0, "current": False}])
    assert out is None


def test_delay_aware_served_phase_audit_correct_through_step():
    agent = _CapAgent(0)
    ctrl = HybridController(_wait_conn(), ["A0"], agent, gate=2, delay_aware=True)
    st = ctrl.tls["A0"]
    st["t"] = ctrl.min_green
    ctrl.step()
    ev = ctrl.events[-1]
    assert ev["served"] == ev["used"]       # no override this interval; served == used
    assert "served_by" in ev


# --------------------------------------------------------------------------- #
# 4. build_controller "sota" -> delay-aware HybridController.
# --------------------------------------------------------------------------- #
def test_build_controller_sota_is_delay_aware():
    ctrl = ex.build_controller(_wait_conn(), ["A0"], _CapAgent(0), config="sota")
    assert isinstance(ctrl, HybridController)
    assert ctrl.delay_aware is True


def test_build_controller_myopic_not_delay_aware():
    ctrl = ex.build_controller(_wait_conn(), ["A0"], _CapAgent(0), config="myopic")
    assert ctrl.delay_aware is False


# --------------------------------------------------------------------------- #
# 5. experiment_sota delta / summary logic (pure).
# --------------------------------------------------------------------------- #
def _arm(status, delay):
    return {"verdict": {"status": status, "slm_delay_s": delay}}


def test_delta_detects_improvement_and_lift():
    d = es._delta(_arm("slm_beats", 290.0), _arm("match", 314.0))
    assert d["sota_improved_delay"] is True     # 290 < 314
    assert d["sota_lifted_verdict"] is True      # match -> slm_beats


def test_delta_no_improvement():
    d = es._delta(_arm("match", 315.0), _arm("slm_beats", 235.0))
    assert d["sota_improved_delay"] is False     # 315 > 235
    assert d["sota_lifted_verdict"] is False      # beats -> match is a drop


def test_delta_no_lift_when_myopic_has_no_verdict():
    # myopic arm skipped/degraded (no verdict) -> a losing sota must NOT be "lifted".
    d = es._delta(_arm("slm_loses", 320.0), {"skipped": True})
    assert d["sota_lifted_verdict"] is False


def test_summary_buckets_models():
    cells = {
        "m1": {"delta": {"sota_improved_delay": True, "sota_lifted_verdict": True,
                         "sota_status": "slm_beats"}},
        "m2": {"delta": {"sota_improved_delay": False, "sota_lifted_verdict": False,
                         "sota_status": "match"}},
        "m3": {"skipped": True},
    }
    s = es._summary(cells)
    assert s["models_run"] == ["m1", "m2"]
    assert s["sota_improved_delay_over_myopic"] == ["m1"]
    assert s["sota_beats_maxpressure"] == ["m1"]
