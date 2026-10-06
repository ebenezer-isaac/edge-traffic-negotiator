"""Tests for the Experiment 1 harness (rule side, pure, no Foundry) and the
SLM decision parser. The real-SLM path is not exercised here (needs Foundry);
these cover the parts that must not silently regress."""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import ambiguous_decision as ad  # noqa: E402
import experiment_slm_vs_rule as ex  # noqa: E402
from slm_agent import SLMAgent  # noqa: E402


# --- the SLM decision parser (pure, no network) --------------------------- #

def test_parse_decision_json_real():
    assert SLMAgent._parse_decision('{"decision": "real"}') == ad.ESCALATE_REAL


def test_parse_decision_json_fake():
    assert SLMAgent._parse_decision('{"decision": "fake"}') == ad.REJECT


def test_parse_decision_reject_and_faulty_map_to_reject():
    assert SLMAgent._parse_decision('decision: reject') == ad.REJECT
    assert SLMAgent._parse_decision('faulty') == ad.REJECT


def test_parse_decision_bare_word():
    assert SLMAgent._parse_decision("this is real") == ad.ESCALATE_REAL


def test_parse_decision_ambiguous_or_garbage_is_none():
    assert SLMAgent._parse_decision("real or fake, unsure") is None
    assert SLMAgent._parse_decision("42") is None
    assert SLMAgent._parse_decision("") is None


# --- the SLM decider wrapper (conservative on failure) -------------------- #

class _NoneAgent:
    def classify_case(self, case):
        return None


class _FixedAgent:
    def __init__(self, out):
        self._out = out
    def classify_case(self, case):
        return self._out


def _a_case():
    return ad.generate_dataset(seed=0)[0]


def test_slm_decider_maps_none_to_reject_and_counts_failures():
    d = ex._SLMDecider(_NoneAgent())
    assert d.decide(_a_case()) == ad.REJECT
    assert d.parse_failures == 1 and d.calls == 1


def test_slm_decider_passes_through_valid():
    d = ex._SLMDecider(_FixedAgent(ad.ESCALATE_REAL))
    assert d.decide(_a_case()) == ad.ESCALATE_REAL
    assert d.parse_failures == 0


# --- the rule-side run (pure, deterministic) ------------------------------ #

def test_run_rule_only_is_deterministic_and_perfect_on_anticipated(tmp_path, monkeypatch):
    # redirect the results write into a temp dir so the test is isolated
    monkeypatch.setattr(ex, "RESULTS", str(tmp_path))
    out = ex.run(with_slm=False, seed=0)
    assert out["n_cases"] == out["n_anticipated"] + out["n_novel"]
    # the rule is tuned on the anticipated split -> parity/perfect expected there
    assert out["rule"]["anticipated"]["accuracy"] == 1.0
    # per-split reported separately, never only pooled
    assert "novel" in out["rule"] and "overall" in out["rule"]
    # no fabricated preemptions from the deterministic rule
    assert out["rule"]["overall"]["false_preemption_rate"] == 0.0
    assert os.path.exists(os.path.join(str(tmp_path), "experiment1_slm_vs_rule.json"))


def test_run_skips_slm_gracefully_when_foundry_down(tmp_path, monkeypatch):
    monkeypatch.setattr(ex, "RESULTS", str(tmp_path))
    monkeypatch.setattr(ex, "_probe_foundry", lambda: (None, "Foundry down (test)"))
    out = ex.run(with_slm=True, seed=0)
    assert out["slm"]["skipped"] is True
    assert "Foundry down" in out["slm"]["reason"]
