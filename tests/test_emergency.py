"""Unit tests for the emergency corroboration gate (the headline security
mechanism). These are pure-logic tests of EmergencyController._admissible_ev /
_corroborated -- no SUMO needed -- so the spoof-rejection behaviour cannot
silently regress.

The gate's contract (FORMAL-SPECIFICATION.md §4):
  * local_sensing            -> always admissible (cannot spoof a real vehicle
                                into a junction's own sensor);
  * advance_claim (defended) -> admissible ONLY with INDEPENDENT corroboration
                                (a sighting from a junction other than the
                                claimer, or local sensing of the same vehicle);
  * advance_claim (naive)    -> admissible on authentication alone (the victim).
"""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from emergency_controller import EmergencyController  # noqa: E402


def _gate(corroboration_required=True, sightings=None):
    """An EmergencyController with ONLY the gate attributes set (no SUMO)."""
    g = object.__new__(EmergencyController)
    g.corroboration_required = corroboration_required
    g._sightings = sightings or {}
    return g


# --- local sensing is always trusted --------------------------------------- #

def test_local_sensing_is_admissible():
    g = _gate()
    assert g._admissible_ev("local_sensing", "AMB", None, "J1", ("AMB", "J0J1")) is True


# --- a phantom advance-claim is refused (the attack) ----------------------- #

def test_phantom_claim_withheld_when_uncorroborated():
    g = _gate(sightings={})  # nobody has seen PHANTOM
    assert g._admissible_ev("advance_claim", "PHANTOM", "J1", "J2", None) is False


def test_claimer_cannot_self_corroborate():
    # Only the claimer (J1) reports the sighting -> not independent -> refused.
    g = _gate(sightings={"AMB": {"J1": ("J1J2", 5)}})
    assert g._admissible_ev("advance_claim", "AMB", "J1", "J2", None) is False


def test_own_record_does_not_corroborate_via_store():
    # A sighting attributed to the receiver itself (J2) is excluded from the
    # independent-corroboration set; only genuine local sensing (local_ev) counts.
    g = _gate(sightings={"AMB": {"J2": ("J1J2", 5)}})
    assert g._admissible_ev("advance_claim", "AMB", "J1", "J2", None) is False


# --- a real claim is admitted once independently corroborated -------------- #

def test_independent_sighting_corroborates():
    # J0 (not the claimer, not the receiver) independently saw AMB.
    g = _gate(sightings={"AMB": {"J0": ("WJ0", 3)}})
    assert g._admissible_ev("advance_claim", "AMB", "J1", "J2", None) is True


def test_local_sensing_corroborates_a_claim():
    g = _gate()
    assert g._admissible_ev("advance_claim", "AMB", "J1", "J2", ("AMB", "J1J2")) is True


def test_corroboration_requires_matching_ev_id():
    # A sighting of a DIFFERENT vehicle must not corroborate this claim.
    g = _gate(sightings={"OTHER": {"J0": ("WJ0", 3)}})
    assert g._admissible_ev("advance_claim", "AMB", "J1", "J2", None) is False


# --- the naive victim trusts authentication alone -------------------------- #

def test_naive_victim_trusts_uncorroborated_claim():
    g = _gate(corroboration_required=False, sightings={})
    assert g._admissible_ev("advance_claim", "PHANTOM", "J1", "J2", None) is True


# --- unknown sources are never admissible ---------------------------------- #

def test_unknown_source_refused():
    g = _gate()
    assert g._admissible_ev("garbage", "AMB", "J1", "J2", None) is False
