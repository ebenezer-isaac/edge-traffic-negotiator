"""Tests for the shared Foundry-determinism probe (MASTER-SPEC §10 golden rule /
D3 / §11 step 6) and the run_slm_metrics fail-loud gate.

These lock TWO invariants that the silent-null bug violated:
  * SKIP-not-ABORT -- the probe and the gated sweep NEVER raise when Foundry is
    absent; they record a skip and return. A test here FAILS if either raises.
  * NO SILENT DEGRADE -- a down / non-deterministic model can NEVER complete as a
    real-SLM result. The determinism dimension is proven LIVE by a fake model
    that answers every call but flips its answer across reps: it MUST be rejected.
"""
import os
import sys
import types

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import slm_agent  # noqa: E402
import run_slm_metrics as rsm  # noqa: E402
from slm_agent import probe_foundry_determinism  # noqa: E402


# --------------------------------------------------------------------------- #
# Fake agents injected via the `slm_agent.SLMAgent` construction seam. Each has
# the two surfaces the probe touches: `.client.models.list()` (reachability) and
# `.choose_phase(...)` (the temp-0 decision).
# --------------------------------------------------------------------------- #
def _reachable_client():
    return types.SimpleNamespace(models=types.SimpleNamespace(list=lambda: ["phi-4-mini"]))


class _DeterministicAgent:
    """Reachable and answers the SAME well-formed phase every call."""
    model = "fake-deterministic"

    def __init__(self, *a, **k):
        self.client = _reachable_client()
        self.calls = 0

    def choose_phase(self, junction_id, num_phases, halting_per_phase, neighbor_note=""):
        self.calls += 1
        return 0


class _NonDeterministicAgent:
    """Reachable and answers a well-formed phase EVERY call, but FLIPS it across
    reps. This is the case a reachability-only probe would wrongly accept -- the
    determinism dimension must reject it."""
    model = "fake-nondeterministic"

    def __init__(self, *a, **k):
        self.client = _reachable_client()
        self.calls = 0

    def choose_phase(self, junction_id, num_phases, halting_per_phase, neighbor_note=""):
        self.calls += 1
        return self.calls % 2  # 1, 0, 1, ... -> not all identical


class _NoAnswerAgent:
    """Reachable but never returns a well-formed decision (always None)."""
    model = "fake-no-answer"

    def __init__(self, *a, **k):
        self.client = _reachable_client()

    def choose_phase(self, *a, **k):
        return None


class _UnreachableAgent:
    """Constructs, but the cheap live call raises (dead service)."""
    model = "fake-unreachable"

    def __init__(self, *a, **k):
        def _boom():
            raise ConnectionError("connection refused")
        self.client = types.SimpleNamespace(models=types.SimpleNamespace(list=_boom))

    def choose_phase(self, *a, **k):  # pragma: no cover -- never reached
        raise AssertionError("choose_phase must not run once reachability fails")


# --------------------------------------------------------------------------- #
# (a) NO Foundry (the CI condition): SKIP-not-abort, reason names reachability.
# --------------------------------------------------------------------------- #
def test_probe_no_foundry_skips_not_raises():
    # Foundry is absent in CI: the real construction + models.list() must fail
    # into a recorded skip, NOT an exception.
    result = probe_foundry_determinism()
    assert isinstance(result, tuple) and len(result) == 2
    agent, reason = result
    assert agent is None
    assert isinstance(reason, str) and reason
    assert ("reachable" in reason.lower()) or ("foundry" in reason.lower())


# --------------------------------------------------------------------------- #
# (b) run_slm_metrics.run_sweep under no-Foundry returns the skip marker, does
#     NOT raise, and does NOT touch SUMO/traci.
# --------------------------------------------------------------------------- #
def test_run_sweep_skips_and_never_touches_sumo(monkeypatch):
    # Force the probe to fail deterministically (independent of the network).
    monkeypatch.setattr(rsm, "probe_foundry_determinism",
                        lambda *a, **k: (None, "Foundry down (test)"))
    # Any SUMO start is a bug: the gate must short-circuit BEFORE traci.start.
    monkeypatch.setattr(rsm.traci, "start",
                        lambda *a, **k: pytest.fail("traci.start must not run on skip"))

    rows = rsm.run_sweep([0])
    assert rows == [{"skipped": True, "reason": "Foundry down (test)",
                     "probe": "foundry_determinism"}]
    assert rsm._is_skip(rows) is True


def test_main_writes_skip_record_not_a_report(monkeypatch, tmp_path):
    # main() on a skip must write a SKIP record and NOT a fabricated report, and
    # must exit cleanly (no traceback).
    monkeypatch.setattr(rsm, "probe_foundry_determinism",
                        lambda *a, **k: (None, "Foundry down (test)"))
    monkeypatch.setattr(rsm.traci, "start",
                        lambda *a, **k: pytest.fail("traci.start must not run on skip"))
    skip_md = tmp_path / "skip.md"
    skip_json = tmp_path / "skip.json"
    report_md = tmp_path / "report.md"
    report_json = tmp_path / "report.json"
    monkeypatch.setattr(rsm, "SKIP_MD", str(skip_md))
    monkeypatch.setattr(rsm, "SKIP_JSON", str(skip_json))
    monkeypatch.setattr(rsm, "RESULTS_MD", str(report_md))
    monkeypatch.setattr(rsm, "RESULTS_JSON", str(report_json))
    monkeypatch.setattr(rsm, "PROGRESS", str(tmp_path / "progress.txt"))
    # build_report must never run on a skip -- make it explode if it does.
    monkeypatch.setattr(rsm, "build_report",
                        lambda rows: pytest.fail("build_report must not run on skip"))
    monkeypatch.setattr(sys, "argv", ["run_slm_metrics.py", "--smoke"])

    rsm.main()  # must not raise

    assert skip_json.exists() and skip_md.exists()
    assert not report_md.exists() and not report_json.exists()
    assert "Foundry down (test)" in skip_md.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# (c) probe-passes / probe-rejects via the SLMAgent construction seam.
# --------------------------------------------------------------------------- #
def test_probe_passes_with_deterministic_agent(monkeypatch):
    monkeypatch.setattr(slm_agent, "SLMAgent", _DeterministicAgent)
    agent, reason = probe_foundry_determinism(reps=3)
    assert reason is None
    assert isinstance(agent, _DeterministicAgent)
    # the SAME agent is returned for reuse; it was actually exercised
    assert agent.calls == 3


def test_probe_rejects_non_deterministic_agent(monkeypatch):
    # THE determinism-dimension proof: a model that answers a well-formed phase
    # on EVERY call (so a reachability/None check passes) but is not stable at
    # temp 0 MUST be skipped, never accepted.
    monkeypatch.setattr(slm_agent, "SLMAgent", _NonDeterministicAgent)
    agent, reason = probe_foundry_determinism(reps=3)
    assert agent is None
    assert "non-deterministic" in reason.lower()


def test_probe_rejects_model_that_does_not_answer(monkeypatch):
    monkeypatch.setattr(slm_agent, "SLMAgent", _NoAnswerAgent)
    agent, reason = probe_foundry_determinism(reps=3)
    assert agent is None
    assert "well-formed" in reason.lower()


def test_probe_rejects_unreachable_service(monkeypatch):
    monkeypatch.setattr(slm_agent, "SLMAgent", _UnreachableAgent)
    agent, reason = probe_foundry_determinism(reps=3)
    assert agent is None
    assert "reachable" in reason.lower()


def test_probe_never_raises_even_if_construction_explodes(monkeypatch):
    # SKIP-not-abort holds even for an unexpected constructor failure.
    def _explode(*a, **k):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(slm_agent, "SLMAgent", _explode)
    agent, reason = probe_foundry_determinism(reps=3)
    assert agent is None
    assert isinstance(reason, str) and reason
