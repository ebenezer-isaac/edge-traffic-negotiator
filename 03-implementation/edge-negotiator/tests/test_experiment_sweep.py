"""Fault-finding tests for the H1 model x config sweep assembly (src/experiment_sweep.py).

The live sweep is exercised end-to-end on the real net; these tests pin the PURE
assembly logic that turns cells into the feasibility map + scale threshold, plus the
per-model probe's SKIP contract. Each is written to FAIL if the logic it guards
regresses (wrong scale-threshold ordering, a skipped cell counted as parity, a
non-deterministic model treated as usable).
"""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import experiment_sweep as sw  # noqa: E402


def _models(*aliases):
    by = {m["alias"]: m for m in sw.MODEL_CATALOG}
    return [by[a] for a in aliases]


def _ran_cell(status, delay=90.0, slm_calls=40, slm_proposal_served=25):
    return {"verdict": {"status": status, "slm_delay_s": delay,
                        "baseline_delay_s": 91.0, "slm_relative_delay": -0.01},
            "metrics": {"completed": 120},
            "latency": {"p99": 0.5},
            "slm_calls": slm_calls, "slm_proposal_served": slm_proposal_served,
            "coordination": {"coord_adjusted_decisions": 0, "pred_adjusted_decisions": 2},
            "audit": {"verify_chain": True}}


def _skipped(reason="foundry down"):
    return {"skipped": True, "reason": reason}


# --------------------------------------------------------------------------- #
# Catalog is ordered smallest -> largest (the scale-threshold scan depends on it).
# --------------------------------------------------------------------------- #
def test_catalog_ordered_small_to_large():
    sizes = [m["size_gb"] for m in sw.MODEL_CATALOG]
    assert sizes == sorted(sizes)
    assert sw.MODEL_CATALOG[0]["alias"] == "qwen2.5-0.5b"      # smallest
    assert sw.MODEL_CATALOG[-1]["alias"] == "phi-4-mini"        # largest


# --------------------------------------------------------------------------- #
# Scale threshold: SMALLEST model x SIMPLEST config reaching parity-or-better.
# --------------------------------------------------------------------------- #
def test_scale_threshold_picks_smallest_simplest_parity():
    models = _models("qwen2.5-0.5b", "qwen2.5-1.5b")
    cells = {
        "qwen2.5-0.5b": {"myopic": _ran_cell("slm_loses"),
                         "coordination": _ran_cell("slm_loses"),
                         "prediction": _ran_cell("match")},
        "qwen2.5-1.5b": {"myopic": _ran_cell("slm_beats"),
                         "coordination": _ran_cell("slm_beats"),
                         "prediction": _ran_cell("slm_beats")},
    }
    st = sw._scale_threshold(cells, models, sw.CONFIGS)
    # Smallest model that reaches parity is qwen0.5b (via prediction), even though a
    # LARGER model reaches it at a simpler config -- smaller model wins the scan.
    assert st["reached"] is True
    assert st["smallest_model"] == "qwen2.5-0.5b"
    assert st["simplest_config"] == "prediction"


def test_scale_threshold_prefers_simplest_within_a_model():
    models = _models("qwen2.5-0.5b")
    cells = {"qwen2.5-0.5b": {"myopic": _ran_cell("slm_loses"),
                              "coordination": _ran_cell("match"),
                              "prediction": _ran_cell("slm_beats")}}
    st = sw._scale_threshold(cells, models, sw.CONFIGS)
    assert st["simplest_config"] == "coordination"  # not prediction


def test_scale_threshold_honest_negative():
    models = _models("qwen2.5-0.5b", "phi-4-mini")
    cells = {"qwen2.5-0.5b": {c: _ran_cell("slm_loses") for c in sw.CONFIGS},
             "phi-4-mini": {c: _ran_cell("slm_loses") for c in sw.CONFIGS}}
    st = sw._scale_threshold(cells, models, sw.CONFIGS)
    assert st["reached"] is False
    assert st["smallest_model"] is None


def test_scale_threshold_excludes_slm_never_consulted():
    # A 'match' cell where the SLM was NEVER consulted (calls==0, gate never opened)
    # matches only because it IS the baseline -> must NOT be claimed as SLM parity.
    models = _models("qwen2.5-0.5b")
    cells = {"qwen2.5-0.5b": {
        "myopic": _ran_cell("match", slm_calls=0, slm_proposal_served=0),
        "coordination": _ran_cell("slm_loses"),
        "prediction": _ran_cell("slm_loses")}}
    st = sw._scale_threshold(cells, models, sw.CONFIGS)
    assert st["reached"] is False  # the degenerate never-consulted match is excluded


def test_scale_threshold_allows_shield_overrode_all_but_consulted():
    # SLM consulted (calls>0) but shield overrode every proposal (served==0) is a
    # LEGITIMATE SLM controller result -> a match here IS valid SLM parity.
    models = _models("qwen2.5-0.5b")
    cells = {"qwen2.5-0.5b": {
        "myopic": _ran_cell("match", slm_calls=40, slm_proposal_served=0),
        "coordination": _ran_cell("slm_loses"),
        "prediction": _ran_cell("slm_loses")}}
    st = sw._scale_threshold(cells, models, sw.CONFIGS)
    assert st["reached"] is True and st["simplest_config"] == "myopic"


def test_scale_threshold_ignores_skipped_cells():
    # A skipped cell must NOT count as parity-or-better even if a later real cell
    # loses -- otherwise a crash would masquerade as a pass.
    models = _models("qwen2.5-0.5b")
    cells = {"qwen2.5-0.5b": {"myopic": _skipped(), "coordination": _skipped(),
                              "prediction": _ran_cell("slm_loses")}}
    st = sw._scale_threshold(cells, models, sw.CONFIGS)
    assert st["reached"] is False


# --------------------------------------------------------------------------- #
# Feasibility map: one row per (model, config); skipped rows carry the reason.
# --------------------------------------------------------------------------- #
def test_feasibility_map_row_per_cell_with_skips():
    models = _models("qwen2.5-0.5b", "qwen2.5-1.5b")
    cells = {"qwen2.5-0.5b": {"myopic": _ran_cell("match"),
                              "coordination": _ran_cell("slm_loses"),
                              "prediction": _skipped("device lost")},
             "qwen2.5-1.5b": {c: _skipped("probe failed") for c in sw.CONFIGS}}
    rows = sw._feasibility_map(cells, models, sw.CONFIGS)
    assert len(rows) == 2 * len(sw.CONFIGS)  # every cell represented
    match_rows = [r for r in rows if r["status"] == "match"]
    assert len(match_rows) == 1 and match_rows[0]["model"] == "qwen2.5-0.5b"
    skipped_rows = [r for r in rows if r["status"] == "skipped"]
    assert len(skipped_rows) == 4
    assert any("device lost" in r["reason"] for r in skipped_rows)


def test_latency_gated_cell_is_skipped_and_not_parity():
    # A model skipped by the latency gate carries its MEASURED latency + reason and
    # must be a skipped map row that can never be a scale threshold.
    models = _models("phi-4-mini-reasoning")
    gated = {"skipped": True, "latency_gated": True, "measured_latency_s": 7.5,
             "reason": "measured choose_phase latency ~7.5s/decision > 3.0s gate ..."}
    cells = {"phi-4-mini-reasoning": {c: gated for c in sw.CONFIGS}}
    rows = sw._feasibility_map(cells, models, sw.CONFIGS)
    assert all(r["status"] == "skipped" for r in rows)
    assert any("7.5s" in r["reason"] for r in rows)
    assert sw._scale_threshold(cells, models, sw.CONFIGS)["reached"] is False


def test_feasibility_map_missing_cell_is_skipped_not_crash():
    # A model with NO cells recorded (e.g. sweep aborted before it) -> skipped rows.
    models = _models("phi-4-mini")
    rows = sw._feasibility_map({}, models, sw.CONFIGS)
    assert len(rows) == len(sw.CONFIGS)
    assert all(r["status"] == "skipped" for r in rows)


# --------------------------------------------------------------------------- #
# Per-model probe SKIP contract (offline: unreachable + non-deterministic).
# --------------------------------------------------------------------------- #
def test_probe_model_reps_guard():
    agent, reason, lat = sw._probe_model("http://127.0.0.1:1/v1", "x", reps=1)
    assert agent is None and "reps" in reason and lat is None


def test_probe_model_unreachable_skips_with_reason():
    # A dead endpoint must SKIP-with-record, never raise.
    agent, reason, lat = sw._probe_model("http://127.0.0.1:1/v1", "no-such-model")
    assert agent is None
    assert "not reachable" in reason


def test_probe_model_nondeterministic_skips(monkeypatch):
    # A model that answers differently across reps is non-deterministic -> SKIP.
    import slm_agent

    class _FlipAgent:
        model = "flip"

        def __init__(self, *a, **k):
            self._n = 0

            class _C:
                class models:
                    @staticmethod
                    def list():
                        return []
            self.client = _C()

        def choose_phase(self, *a, **k):
            self._n += 1
            return self._n % 2  # alternates 1,0,1 -> not all identical

    monkeypatch.setattr(slm_agent, "SLMAgent", _FlipAgent)
    agent, reason, _lat = sw._probe_model("http://x/v1", "flip", reps=3)
    assert agent is None
    assert "non-deterministic" in reason


# --------------------------------------------------------------------------- #
# Degradation guard (the battery FATAL fix): a consulted-but-all-None cell is a
# silent all-shield degradation and must be skipped, never scored as parity.
# --------------------------------------------------------------------------- #
def test_degradation_skip_all_none_is_skipped():
    # SLM consulted 40 times, every call returned None -> all-shield degradation.
    skip = sw._degradation_skip(calls=40, none_returns=40)
    assert skip is not None
    assert skip["skipped"] is True and skip["degraded"] is True
    assert "0/40" in skip["reason"]


def test_degradation_skip_healthy_cell_passes():
    # Some valid proposals -> a real SLM cell, not degraded.
    assert sw._degradation_skip(calls=40, none_returns=12) is None


def test_degradation_skip_no_calls_is_not_degraded():
    # Gate never opened (light demand): 0 calls is a distinct honest state, NOT
    # degradation, so it must NOT be skipped as degraded.
    assert sw._degradation_skip(calls=0, none_returns=0) is None


def test_degraded_cell_cannot_be_scale_threshold():
    # A degraded myopic cell (skipped) must NOT become a false scale threshold even
    # though an all-shield myopic arm would have verdict 'match' by construction.
    models = _models("qwen2.5-0.5b")
    degraded = sw._degradation_skip(calls=30, none_returns=30)
    cells = {"qwen2.5-0.5b": {"myopic": degraded,
                              "coordination": _ran_cell("slm_loses"),
                              "prediction": _ran_cell("slm_loses")}}
    st = sw._scale_threshold(cells, models, sw.CONFIGS)
    assert st["reached"] is False  # the degraded cell is invisible to the scan


def test_degraded_cell_shows_in_feasibility_map_as_skipped():
    models = _models("qwen2.5-0.5b")
    degraded = sw._degradation_skip(calls=30, none_returns=30)
    cells = {"qwen2.5-0.5b": {"myopic": degraded,
                              "coordination": _ran_cell("match"),
                              "prediction": _ran_cell("match")}}
    rows = sw._feasibility_map(cells, models, sw.CONFIGS)
    myopic_row = next(r for r in rows if r["config"] == "myopic")
    assert myopic_row["status"] == "skipped"
    assert "degraded" in myopic_row["reason"]


def test_probe_model_none_answer_skips(monkeypatch):
    import slm_agent

    class _NoneAgent:
        model = "none"

        def __init__(self, *a, **k):
            class _C:
                class models:
                    @staticmethod
                    def list():
                        return []
            self.client = _C()

        def choose_phase(self, *a, **k):
            return None

    monkeypatch.setattr(slm_agent, "SLMAgent", _NoneAgent)
    agent, reason, _lat = sw._probe_model("http://x/v1", "none", reps=3)
    assert agent is None
    assert "well-formed" in reason
