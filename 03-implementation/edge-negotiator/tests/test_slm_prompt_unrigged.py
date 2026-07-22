"""§8/D4 un-rigged-baseline guard: the SLM disambiguation prompt must NOT leak
the reference rule's decision threshold, and must give the SLM the SAME features
the rule reads (information parity, neither more nor less). These tests lock the
property this phase established; the prior rig ("1.0 = the limit" in the prompt)
would have failed test_disambig_guidance_states_no_numeric_cut.

This is the STATIC half of D4 (no Foundry needed); the behavioural leak test over
a live model rides the Foundry phase. Pure string/structure assertions, no SUMO."""
import os
import re
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import slm_agent as s  # noqa: E402
from ambiguous_decision import FlaggedCase, RuleDisambiguator  # noqa: E402

# The reference rule's tuned grid + defaults (ambiguous_decision.RuleDisambiguator).
# NONE of these may appear as a stated cut anywhere the SLM is prompted, or the
# SLM would be handed the rule's decision boundary (a rigged comparison).
_RULE_GRID_VALUES = ("0.75", "1.25", "1.5", "1.50")
_THRESHOLD_WORDS = ("limit", "threshold", "cutoff", "cut-off", "boundary")


def _assembled_disambig_text() -> str:
    """Everything the disambiguation model is instructed with, EXCLUDING live case
    data: the system guidance + the few-shot user texts + their reply suffixes."""
    parts = [s.SYSTEM_DISAMBIG]
    for user_text, _decision in s._DISAMBIG_FEWSHOT:
        parts.append(user_text)
    return "\n".join(parts)


def test_disambig_guidance_states_no_numeric_cut():
    """SYSTEM_DISAMBIG is pure QUALITATIVE guidance: no digit at all, so it cannot
    encode the rule's numeric threshold (this alone catches the old '1.0 = the
    limit' rig)."""
    assert re.search(r"\d", s.SYSTEM_DISAMBIG) is None, (
        "SYSTEM_DISAMBIG must carry no numeric cut; found a digit")


def test_no_threshold_framing_in_guidance():
    """No 'limit/threshold/boundary'-style framing in the guidance text — the SLM
    is told the DIRECTION each signal points, never where the rule cuts."""
    low = s.SYSTEM_DISAMBIG.lower()
    hits = [w for w in _THRESHOLD_WORDS if w in low]
    assert not hits, f"SYSTEM_DISAMBIG uses threshold framing: {hits}"


def test_no_rule_grid_value_in_assembled_prompt():
    """None of the rule's tuned grid values (0.75/1.25/1.5) nor the default cut
    1.0 appears as a stated value in the guidance or the hand-crafted few-shot —
    so no edit can silently hand the SLM the rule's boundary and stay green."""
    text = _assembled_disambig_text()
    for v in (*_RULE_GRID_VALUES, "1.0"):
        # Match the grid value as a STANDALONE number, not as a prefix of a larger
        # datum: ban the cut "1.0", but do not false-trip on a future few-shot
        # residual like "1.05" (the value is data, not a stated threshold).
        assert re.search(rf"(?<!\d){re.escape(v)}(?!\d)", text) is None, (
            f"rule grid/default value {v!r} leaked into the prompt as a cut")


def test_case_evidence_exposes_every_rule_feature():
    """Information parity: _case_evidence must surface EVERY feature the rule reads
    (RuleDisambiguator.decide keys on corroboration_count, residual, persistence,
    neighbour_agreement) plus local_sensing — neither the threshold (more) nor a
    missing feature (less). A probe case with distinctive values proves presence."""
    case = FlaggedCase(
        case_id="probe", event_type="emergency_claim", corroboration_count=3,
        residual=1.23, persistence=5, neighbour_agreement=0.42,
        local_sensing=True, severity=0.67, split="novel", label="real")
    ev = s.SLMAgent._case_evidence(case)
    assert "also saw it: 3" in ev              # corroboration_count
    assert "1.23" in ev                        # residual, as the RAW number
    assert "persisted: 5" in ev                # persistence
    assert "0.42" in ev                        # neighbour_agreement
    assert "directly: yes" in ev               # local_sensing


def test_residual_shown_raw_not_binned():
    """The residual is the raw number (information parity with the rule), NOT a
    qualitative band whose boundary would reproduce the rule's cut (the rejected
    first attempt binned at 1.0 == residual_max default)."""
    lo = s.SLMAgent._case_evidence(_probe(residual=0.90))
    hi = s.SLMAgent._case_evidence(_probe(residual=0.95))
    assert "0.90" in lo and "0.95" in hi, "residual must be the raw value"
    # Two residuals on the same side of the rule's 1.0 cut must render DIFFERENTLY
    # (a band would collapse them to one phrase, discarding signal + implying a cut).
    assert lo != hi


def test_rule_default_threshold_is_what_we_refuse_to_leak():
    """Anchors the test's intent to the real rule: the default cut we must not
    leak IS 1.0 (so test_no_rule_grid_value_in_assembled_prompt is guarding the
    right constant). If the rule's default changes, this fails loudly."""
    assert RuleDisambiguator().residual_max == 1.0


def _probe(**over):
    base = dict(case_id="p", event_type="emergency_claim", corroboration_count=1,
                residual=0.5, persistence=2, neighbour_agreement=0.5,
                local_sensing=False, severity=0.5, split="novel", label="real")
    base.update(over)
    return FlaggedCase(**base)
