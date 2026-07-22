"""End-to-end tests for the full evaluation harness (src/evaluation.py).

A SMALL matrix (2 modes, 2-3 seeds, end=200, deterministic StubAgent) runs
end-to-end and must produce a well-formed report + JSON with the expected
columns. The tests exist to BREAK the harness, not to rubber-stamp it:

  * the throughput-controlled metric IS the headline; the OLD completed-only
    avg travel time is NOT the sole headline (it appears only as a flagged
    contrast);
  * the stats columns (BCa CI, paired diff, permutation p, Holm) are present;
  * detection P/R/F1/latency columns are present (one harness, both tables);
  * results are DETERMINISTIC given the seeds (two runs => identical numbers);
  * config validation rejects bad input at the boundary.

SUMO + traci are required (the project env has them). NO Foundry Local: every
SLM cell uses the injected StubAgent via run_metrics_sweep.run_one. The matrix
is kept tiny (end=200) so the suite stays fast.

    .venv/Scripts/python -m pytest tests/test_evaluation.py -v
"""
import json
import math
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import evaluation as E  # noqa: E402
from evaluation import (  # noqa: E402
    CONTRAST_METRIC, EvalConfig, EvaluationError, HEADLINE_METRICS,
    run_evaluation,
)


# --------------------------------------------------------------------------- #
# Shared tiny fixtures. SUMO runs are the slow part, so build the report ONCE
# at module scope and assert against it across many cheap tests.
# --------------------------------------------------------------------------- #
TINY = EvalConfig(
    modes=("maxpressure", "coordinated"),
    seeds=(0, 1),
    end=200,
    baseline="maxpressure",
    run_detection=True,
    detection_tolerance=2,
    n_boot=400, n_perm=400, stat_seed=0,
)


@pytest.fixture(scope="module")
def report():
    return run_evaluation(TINY)


# --------------------------------------------------------------------------- #
# Config validation (boundary).
# --------------------------------------------------------------------------- #
def test_config_rejects_unknown_mode():
    with pytest.raises(EvaluationError):
        EvalConfig(modes=("maxpressure", "teleport"), seeds=(0,))


def test_config_rejects_baseline_not_in_modes():
    with pytest.raises(EvaluationError):
        EvalConfig(modes=("maxpressure",), seeds=(0,), baseline="coordinated")


def test_config_rejects_empty_seeds():
    with pytest.raises(EvaluationError):
        EvalConfig(modes=("maxpressure",), seeds=())


def test_config_rejects_duplicate_seeds():
    with pytest.raises(EvaluationError):
        EvalConfig(modes=("maxpressure",), seeds=(0, 0, 1))


def test_config_dedupes_modes_preserving_order():
    cfg = EvalConfig(modes=("coordinated", "maxpressure", "coordinated"),
                     seeds=(0,), baseline="maxpressure")
    assert cfg.modes == ("coordinated", "maxpressure")


def test_with_n_seeds_is_one_flag_for_dissertation():
    cfg = TINY.with_n_seeds(30)
    assert cfg.seeds == tuple(range(30))
    assert len(cfg.seeds) == 30


# --------------------------------------------------------------------------- #
# The matrix runs end-to-end and produces the right shape.
# --------------------------------------------------------------------------- #
def test_traffic_rows_cover_every_cell(report):
    rows = report.rows
    # 2 modes x 2 seeds = 4 cells.
    assert len(rows) == 4
    seen = {(r["mode"], r["seed"]) for r in rows}
    assert seen == {("maxpressure", 0), ("maxpressure", 1),
                    ("coordinated", 0), ("coordinated", 1)}


def test_every_cell_used_full_population_tripinfo(report):
    """The required write flags must have taken effect on every cell."""
    for r in report.rows:
        assert r["write_unfinished_present"] or r["write_undeparted_present"], r


def test_headline_metric_tables_present_with_stats_columns(report):
    """Each throughput-controlled headline metric has the full stats stack."""
    for metric in HEADLINE_METRICS:
        recs = report.traffic_tables[metric]
        # one record per mode
        assert {r["group"] for r in recs} == set(TINY.modes)
        for r in recs:
            # per-group BCa CI columns
            for col in ("mean", "ci_lo", "ci_hi", "is_baseline"):
                assert col in r, (metric, col)
            if not r["is_baseline"]:
                # paired diff + permutation + Holm columns
                for col in ("diff_vs_baseline", "diff_ci_lo", "diff_ci_hi",
                            "diff_excludes_zero", "perm_p", "holm_threshold",
                            "holm_reject"):
                    assert col in r, (metric, col)


def test_throughput_controlled_metric_is_the_headline_not_completed_only(report):
    """mean_network_delay is a headline metric; avg_travel_time_completed is NOT.

    Guards the lesson: the wrong-sign completed-only average must
    never be the sole headline. It may appear ONLY as a flagged contrast block.
    """
    assert "mean_network_delay" in HEADLINE_METRICS
    assert CONTRAST_METRIC not in HEADLINE_METRICS
    # The contrast metric is computed (for the honesty contrast) but is labelled
    # as contrast, never as a headline.
    assert CONTRAST_METRIC in report.traffic_tables
    md = report.markdown
    # The report must headline the throughput-controlled metric...
    assert "mean_network_delay" in md
    # ...and explicitly flag the old metric as contrast / biased, NOT headline.
    assert "Contrast only" in md
    assert "biased" in md.lower()


def test_markdown_has_both_traffic_and_detection_tables(report):
    md = report.markdown
    assert "## Traffic" in md
    assert "Security — detection results" in md
    # detection P/R/F1/latency header present
    assert "precision | recall | F1" in md
    # traffic stats header present
    assert "diff vs base" in md and "Holm reject" in md


def test_detection_table_has_prf1_and_latency(report):
    det = report.detection
    assert det is not None
    assert det["attacks"], "no detection rows"
    families = {r["attack"] for r in det["attacks"]}
    # the three threat-model families are all scored
    assert any("spoof" in f for f in families)
    assert any("faulty" in f for f in families)
    assert any("sybil" in f or "impersonation" in f for f in families)
    for r in det["attacks"]:
        for col in ("precision", "recall", "f1", "latency_cycles", "tp", "fp",
                    "fn", "tn"):
            assert col in r, col
        assert 0.0 <= r["precision"] <= 1.0
        assert 0.0 <= r["recall"] <= 1.0
    # auth family: perfect recall, zero-cycle latency (rejected on receipt).
    auth = next(r for r in det["attacks"] if "sybil" in r["attack"])
    assert auth["recall"] == 1.0
    assert auth["latency_cycles"] == 0
    # the honest collusion-evasion residual is recorded and is UNDETECTED.
    ce = det["collusion_evasion"]
    assert ce["malicious"] is True
    assert ce["detected"] is False


def test_json_is_serialisable_and_well_formed(report):
    blob = json.dumps(report.json)  # must not raise (no numpy types leak)
    back = json.loads(blob)
    assert back["config"]["agent"] == "StubAgent"
    assert back["config"]["n_seeds"] == 2
    assert back["config"]["baseline"] == "maxpressure"
    assert len(back["traffic_rows"]) == 4
    assert set(back["traffic_tables"].keys()) >= set(HEADLINE_METRICS)
    assert back["detection"] is not None


def test_matched_set_contrast_present(report):
    """Same-vehicle matched-set diff exists for the non-baseline mode."""
    matched = report.matched
    assert {r["mode"] for r in matched} == {"coordinated"}
    r = matched[0]
    assert r["baseline"] == "maxpressure"
    for col in ("n_seeds", "total_matched_veh", "mean_diff_mode_minus_baseline",
                "ci_lo", "ci_hi", "excludes_zero", "perm_p"):
        assert col in r, col


# --------------------------------------------------------------------------- #
# Determinism: same seeds => identical numbers (anti-flake guarantee).
# --------------------------------------------------------------------------- #
def test_deterministic_given_seeds():
    """Two independent runs of the same tiny config must agree to the bit.

    This is the reproducibility contract for the dissertation: StubAgent +
    fixed SUMO seeds + fixed stats seed => identical headline numbers. A
    non-deterministic cell (or an unseeded bootstrap) would FAIL here.
    """
    cfg = EvalConfig(
        modes=("maxpressure", "coordinated"), seeds=(0, 1), end=200,
        baseline="maxpressure", run_detection=False,
        n_boot=300, n_perm=300, stat_seed=0,
    )
    r1 = run_evaluation(cfg)
    r2 = run_evaluation(cfg)

    # Per-cell traffic metrics identical.
    def key(rows):
        return {
            (x["mode"], x["seed"]): (x["throughput"], x["completion_rate"],
                                     round(x["mean_network_delay"], 6))
            for x in rows
        }
    assert key(r1.rows) == key(r2.rows)

    # Stats output identical for the headline metric.
    def stat_key(rep):
        out = {}
        for rec in rep.traffic_tables["mean_network_delay"]:
            out[rec["group"]] = (
                None if rec["mean"] is None else round(rec["mean"], 8),
                rec["holm_reject"],
                None if rec["perm_p"] is None else round(rec["perm_p"], 8),
            )
        return out
    assert stat_key(r1) == stat_key(r2)


# --------------------------------------------------------------------------- #
# Single-mode degenerate matrix: baseline-only is allowed (no comparisons).
# --------------------------------------------------------------------------- #
def test_single_mode_matrix_runs_without_comparisons():
    cfg = EvalConfig(modes=("maxpressure",), seeds=(0, 1), end=200,
                     baseline="maxpressure", run_detection=False,
                     n_boot=200, n_perm=200)
    rep = run_evaluation(cfg)
    assert len(rep.rows) == 2
    # baseline-only: no matched-set rows (nothing to contrast against).
    assert rep.matched == []
    recs = rep.traffic_tables["throughput"]
    assert len(recs) == 1 and recs[0]["is_baseline"] is True
