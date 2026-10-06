"""Pure-logic tests for the triggered-regime additions to EmergencyController:
the FlaggedCase assembly used by the disambiguator hook, and the safety rule
that a disambiguator can only WITHHOLD preemption, never add it. No SUMO needed
(object.__new__ builds a controller with only the attributes under test)."""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import ambiguous_decision as ad  # noqa: E402
from emergency_controller import EmergencyController  # noqa: E402


def _bare(**attrs):
    g = object.__new__(EmergencyController)
    for k, v in attrs.items():
        setattr(g, k, v)
    return g


# --- _build_flagged_case counts only INDEPENDENT sightings ---------------- #

def test_flagged_case_counts_independent_sightings():
    g = _bare(_sightings={"AMB": {"J0": ("e", 1), "J1": ("e", 2)}})
    trig = {"source": "advance_claim", "ev_id": "AMB", "claimer": "J1",
            "approach_edge": "J1J2"}
    case = g._build_flagged_case(trig, "J2", None)
    # J0 is independent (not the claimer J1, not the receiver J2); J1 is excluded.
    assert case.corroboration_count == 1
    assert case.neighbour_agreement == 1.0
    assert case.local_sensing is False
    assert case.event_type == "emergency_claim"


def test_flagged_case_phantom_has_zero_corroboration():
    g = _bare(_sightings={})
    trig = {"source": "advance_claim", "ev_id": "PHANTOM", "claimer": "J1",
            "approach_edge": "J1J2"}
    case = g._build_flagged_case(trig, "J2", None)
    assert case.corroboration_count == 0
    assert case.neighbour_agreement == 0.0


def test_flagged_case_local_sensing_flag():
    g = _bare(_sightings={})
    trig = {"source": "advance_claim", "ev_id": "AMB", "claimer": "J1",
            "approach_edge": "J1J2"}
    case = g._build_flagged_case(trig, "J2", ("AMB", "J1J2"))
    assert case.local_sensing is True


def test_flagged_case_is_valid_flaggedcase():
    g = _bare(_sightings={"AMB": {"J0": ("e", 1)}})
    trig = {"source": "advance_claim", "ev_id": "AMB", "claimer": "J1",
            "approach_edge": "J1J2"}
    case = g._build_flagged_case(trig, "J2", None)
    assert isinstance(case, ad.FlaggedCase)
    # the reference rule can consume it without error
    assert ad.RuleDisambiguator().decide(case) in (ad.ESCALATE_REAL, ad.REJECT)


# --- the withhold-only safety rule (admissible = det AND escalate_real) ---- #
# This mirrors the exact boolean in decide(): a disambiguator can never turn a
# gate-refused claim into a preemption, only withhold a gate-admitted one.

def _combine(det_admissible: bool, decision: str) -> bool:
    return det_admissible and (decision == ad.ESCALATE_REAL)


def test_disambiguator_cannot_add_preemption_the_gate_refused():
    # gate refuses (phantom) -> stays refused no matter what the disambiguator says
    assert _combine(False, ad.ESCALATE_REAL) is False
    assert _combine(False, ad.REJECT) is False


def test_disambiguator_can_withhold_a_gate_admitted_claim():
    assert _combine(True, ad.REJECT) is False   # withheld
    assert _combine(True, ad.ESCALATE_REAL) is True  # allowed through


# --- the maxpressure_preempt mode exists and disables advance claims ------- #

def test_maxpressure_preempt_mode_disables_advance_claims():
    import demo_emergency as dm
    assert "maxpressure_preempt" in dm._MODES
    assert dm._MODES["maxpressure_preempt"]["advance_claims_enabled"] is False
    assert dm._MODES["maxpressure_preempt"]["preemption_enabled"] is True
