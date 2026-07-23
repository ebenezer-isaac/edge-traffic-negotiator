"""Fault-finding tests for the trust-coefficient mechanism (src/trust.py,
src/experiment_trust.py).

Written to FAIL if trust is not asymmetric (a lie must cost far more than a truth
gains), if a collapsed source can still corroborate, if local-sensing verification is
bypassed, or if the ledger mutates in place.
"""
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import experiment_trust as et  # noqa: E402
import trust as T  # noqa: E402


def test_prior_for_unseen_source():
    L = T.TrustLedger()
    assert L.trust_of("nobody") == T.PRIOR


def test_verified_truth_raises_trust_with_diminishing_returns():
    L = T.TrustLedger()
    a = L.verify("s", True).trust_of("s")
    b = L.verify("s", True).verify("s", True).trust_of("s")
    assert a > T.PRIOR                 # a truth raises trust
    assert b > a                       # more truths raise it further
    assert b < 1.0                     # but never reaches/exceeds 1


def test_lie_collapses_trust_extremely():
    L = T.TrustLedger()
    after_lie = L.verify("s", False).trust_of("s")
    assert after_lie == pytest.approx(T.PRIOR * T.LIE_FACTOR)   # multiplicative collapse
    assert after_lie < T.PRIOR


def test_asymmetry_one_lie_costs_more_than_one_truth_gains():
    L = T.TrustLedger()
    gain = L.verify("s", True).trust_of("s") - T.PRIOR
    drop = T.PRIOR - L.verify("s", False).trust_of("s")
    assert drop > gain                 # a lie hurts more than a truth helps
    # and dramatically so: one lie undoes many truths of building.
    built = L
    for _ in range(8):
        built = built.verify("s2", True)
    high = built.trust_of("s2")
    after_one_lie = built.verify("s2", False).trust_of("s2")
    assert high - after_one_lie > 0.5   # a single lie erases most of 8 truths


def test_collapsed_source_cannot_corroborate():
    L = T.TrustLedger()
    for _ in range(3):
        L = L.verify("liar", False)     # keeps lying -> collapses
    assert L.trust_of("liar") < T.CORROBORATION_FLOOR
    assert L.can_corroborate("liar") is False


def test_honest_source_can_corroborate():
    L = T.TrustLedger()
    for _ in range(6):
        L = L.verify("honest", True)
    assert L.can_corroborate("honest") is True


def test_trust_bounds():
    L = T.TrustLedger()
    for _ in range(50):
        L = L.verify("s", True)
    assert L.trust_of("s") <= 1.0
    for _ in range(50):
        L = L.verify("s", False)
    assert L.trust_of("s") >= 0.0


def test_ledger_is_immutable():
    L = T.TrustLedger()
    L2 = L.verify("s", True)
    assert L is not L2                 # a new ledger is returned
    assert L.trust_of("s") == T.PRIOR  # the original is unchanged


def test_local_sensing_is_the_only_arbiter():
    # verify() takes ONLY confirmed_by_local_sensing; there is no way to move trust
    # except via a local-sensing verification (record_claim alone must not move it).
    L = T.TrustLedger().record_claim("s")
    assert L.trust_of("s") == T.PRIOR  # a mere claim does not change trust


# --------------------------------------------------------------------------- #
# The demonstration experiment passes all its checks.
# --------------------------------------------------------------------------- #
def test_experiment_passes_all_checks():
    r = et.run()
    assert r["passed"] is True
    assert all(r["checks"].values()), r["checks"]
    assert r["final"]["junction-honest"]["can_corroborate"] is True
    assert r["final"]["junction-liar"]["can_corroborate"] is False
    assert r["asymmetry"]["truths_to_reach_0.90"] >= 5
