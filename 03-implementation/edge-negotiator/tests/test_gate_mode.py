"""Tests for the topology-invariant congestion gate (HybridController.gate_mode).

The 'sum' gate scales with phase count (a 4-phase grid junction trips it more easily than a
2-phase corridor), which is exactly why the SLM over-fired on free-flowing grids. The 'max'
gate fires only on a real standing queue (largest per-phase queue >= gate), so a free-flowing
net defers to MaxPressure regardless of phase count. These pin that discriminator and that the
default ('sum') is unchanged. Built with object.__new__ + monkeypatched parent decide +
stubbed green_halting, so no SUMO/Foundry is needed -- the gate predicate is pure."""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from controllers import MaxPressureController  # noqa: E402
from hybrid_controller import HybridController as HC  # noqa: E402


class _RecAgent:
    def __init__(self):
        self.called = 0

    def choose_phase(self, *a, **k):
        self.called += 1
        return 0  # SLM would pick phase 0


def _mk(gate, gate_mode, halting, monkeypatch):
    # MaxPressure (the shield) would pick phase 1; the SLM (if consulted) picks 0.
    monkeypatch.setattr(MaxPressureController, "decide", lambda self, tl, st: 1)
    g = object.__new__(HC)
    g.agent = _RecAgent()
    g.slm = {"J"}
    g.gate = gate
    g.gate_mode = gate_mode
    g.delay_aware = False
    g.events = []
    g._served_ctx = None
    g.green_halting = lambda st, gi: halting[gi]
    st = {"green": ["G" + "r" * (len(halting) - 1)] * len(halting),
          "in_lanes": ["l%d" % i for i in range(len(halting))], "cur": 0}
    return g, st


def test_max_gate_defers_when_all_queues_short(monkeypatch):
    # halting [3,4]: max=4 < gate 5 -> the SLM must DEFER to MaxPressure (free-flow behaviour).
    g, st = _mk(5, "max", [3, 4], monkeypatch)
    out = g.decide("J", st)
    assert out == 1                 # MaxPressure choice served
    assert g.agent.called == 0      # SLM never consulted


def test_max_gate_fires_on_a_real_standing_queue(monkeypatch):
    # halting [3,7]: max=7 >= gate 5 -> a real queue -> SLM IS consulted (and its 0 is used).
    g, st = _mk(5, "max", [3, 7], monkeypatch)
    out = g.decide("J", st)
    assert g.agent.called == 1
    assert out == 0                 # SLM proposal served


def test_max_gate_is_phase_count_invariant(monkeypatch):
    # THE discriminator vs 'sum': four short queues [3,3,3,3] sum to 12 (would trip a sum-gate
    # of 5) but the MAX is 3 < 5 -> a free-flowing 4-phase grid junction correctly DEFERS.
    g, st = _mk(5, "max", [3, 3, 3, 3], monkeypatch)
    g.decide("J", st)
    assert g.agent.called == 0      # not fooled by phase count


def test_sum_gate_unchanged_default(monkeypatch):
    # Default 'sum': same [3,3,3,3] sums to 12 >= gate 5 -> SLM consulted (prior behaviour).
    g, st = _mk(5, "sum", [3, 3, 3, 3], monkeypatch)
    g.decide("J", st)
    assert g.agent.called == 1      # sum-gate fires where max-gate would defer


def test_gate_mode_validated():
    import pytest
    with pytest.raises(ValueError):
        HC(conn=None, tls_ids=[], agent=None, gate_mode="bogus")
