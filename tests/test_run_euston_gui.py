"""Guards for the SUMO-GUI viewer (src/run_euston_gui.py). No GUI/live deps here:
the live run() is a viewer, but its SKIP contract and model map must not regress."""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import run_euston_gui as g  # noqa: E402


def test_model_map_has_the_winning_model():
    assert "qwen2.5-0.5b" in g._MODEL_IDS
    assert g._MODEL_IDS["qwen2.5-0.5b"].startswith("qwen2.5-0.5b")


def test_slm_agent_skips_with_reason_when_foundry_down():
    # A dead endpoint must SKIP-with-record (return None + reason), never raise.
    import slm_agent

    class _Dead:
        def __init__(self, *a, **k):
            class _C:
                class models:
                    @staticmethod
                    def list():
                        raise ConnectionError("down")
            self.client = _C()

        def choose_phase(self, *a, **k):
            return None

    orig = slm_agent.SLMAgent
    slm_agent.SLMAgent = _Dead
    try:
        # discover_endpoint may hit the network; guard by also patching it to a stub.
        slm_agent.discover_endpoint = lambda *a, **k: ("http://127.0.0.1:1/v1", "x")
        agent, reason = g._slm_agent("qwen2.5-0.5b")
    finally:
        slm_agent.SLMAgent = orig
    assert agent is None
    assert isinstance(reason, str) and "reachable" in reason.lower()


def test_baseline_constant_matches_committed_sweep():
    # The context baseline printed by the viewer must match the committed sweep result.
    assert abs(g.BASELINE_DELAY_S - 314.55) < 0.01
