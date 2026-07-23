"""Tests for the LIVE trust integration in EmergencyController (full-scale, both
supervisors). These pin the two safety-critical invariants:

  1. Trust is scored ONLY against local sensing (the ultimate, never-doubted truth):
     a claim confirmed by a local sensing is a truth; a claim that expires unseen is a lie.
  2. Trust is DISCOUNT-ONLY: it can withhold a caught-liar's cross-junction corroboration
     but can NEVER add a corroboration, and NEVER gates local sensing. So the headline
     phantom-defence cannot regress, and a real ambulance is always preempted locally.

The methods under test (_trust_observe, _corroborated) are pure given object state, so a
light stub carries exactly the attributes they read -- no SUMO/Foundry needed. Written to
FAIL if trust ever loosens the gate, if a lie fails to collapse trust, or if the default
(trust OFF) changes the corroboration behaviour."""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from emergency_controller import EmergencyController as EC  # noqa: E402
from trust import TrustLedger  # noqa: E402


class _Stub:
    """Minimal carrier of the state _trust_observe / _corroborated read."""
    def __init__(self, gating=True, ttl=120.0):
        self.trust_gating = gating
        self.trust_claim_ttl = ttl
        self.trust = TrustLedger()
        self._claim_first = {}
        self._locally_confirmed = set()
        self._truth_settled = set()
        self._provisional_keys = set()
        self._provisional_lies = {}
        self._sightings = {}
        self._t = 0.0

    def _sim_time(self):
        return self._t

    # delegate to the real controller methods so _corroborated's internal
    # self._live_can_corroborate(...) resolves on the stub (we test the REAL logic).
    def _effective_trust(self, source):
        return EC._effective_trust(self, source)

    def _live_can_corroborate(self, source):
        return EC._live_can_corroborate(self, source)


def _claim(frm, ev_id, edge="e1"):
    return {"from": frm, "ev_id": ev_id, "approach_edge": edge, "t": 0}


# --------------------------------------------------------------------------- #
# 1. Local sensing is the ground truth: confirmed claim -> trust UP.
# --------------------------------------------------------------------------- #
def test_confirmed_claim_raises_trust():
    s = _Stub()
    EC._trust_observe(s, "J2", None, [_claim("J1", "amb1")])          # J1 claims amb1
    assert s.trust.trust_of("J1") == 0.5                              # not yet verified
    s._t = 10.0
    EC._trust_observe(s, "J2", ("amb1", "e1"), [])                    # J2 locally sees amb1
    assert s.trust.trust_of("J1") > 0.5                               # confirmed -> truth
    assert s.trust.summary()["J1"]["truths"] == 1
    assert ("amb1", "J1") in s._truth_settled


def test_phantom_claim_expires_into_a_provisional_lie_and_locks_out():
    s = _Stub(ttl=100.0)
    EC._trust_observe(s, "J2", None, [_claim("J1", "ghost")])         # J1 claims a phantom
    s._t = 50.0
    EC._trust_observe(s, "J2", None, [])                              # not yet past TTL
    assert s._provisional_lies.get("J1", 0) == 0
    assert EC._live_can_corroborate(s, "J1") is True                 # innocent until TTL
    s._t = 200.0                                                      # now past TTL, never seen
    EC._trust_observe(s, "J2", None, [])
    assert s._provisional_lies["J1"] == 1                            # provisional lie recorded
    assert EC._effective_trust(s, "J1") < 0.5                        # effective trust discounted
    assert EC._live_can_corroborate(s, "J1") is False               # caught liar locked out
    # and it PERSISTS (a phantom never arrives) -> effectively permanent lockout
    s._t = 5000.0
    EC._trust_observe(s, "J2", None, [])
    assert EC._live_can_corroborate(s, "J1") is False


def test_late_arrival_vindicates_an_honest_junction():
    # THE MAJOR-FIX regression test: a REAL but congestion-slowed ambulance arrives AFTER
    # the provisional-lie TTL. Local sensing is the ultimate truth, so the late confirmation
    # must VINDICATE the honest claimer -- not leave it wrongly locked out.
    s = _Stub(ttl=100.0)
    EC._trust_observe(s, "J2", None, [_claim("J1", "amb_slow")])      # J1 claims (honestly)
    s._t = 150.0                                                      # past TTL, not yet seen
    EC._trust_observe(s, "J2", None, [])                             # -> provisional lie
    assert EC._live_can_corroborate(s, "J1") is False
    s._t = 160.0
    EC._trust_observe(s, "J2", ("amb_slow", "e1"), [])              # ambulance finally arrives
    assert EC._live_can_corroborate(s, "J1") is True                # vindicated, not locked out
    assert s._provisional_lies.get("J1", 0) == 0                    # provisional lie lifted
    assert s.trust.summary()["J1"]["truths"] == 1                   # counts as a committed truth


def test_multiple_concurrent_provisional_lies_all_vindicated_order_independent():
    # THE SECOND MAJOR-FIX regression test (snapshot-pollution): ONE honest junction has TWO
    # real claims that BOTH cross TTL before either arrives. Both provisional lies must lift
    # cleanly on arrival regardless of arrival ORDER -> the junction is NOT left stuck.
    for order in (("amb_x", "amb_y"), ("amb_y", "amb_x")):
        s = _Stub(ttl=100.0)
        EC._trust_observe(s, "J2", None, [_claim("J1", "amb_x"), _claim("J1", "amb_y")])
        s._t = 150.0
        EC._trust_observe(s, "J2", None, [])                        # both -> provisional lies
        assert s._provisional_lies["J1"] == 2
        assert EC._live_can_corroborate(s, "J1") is False
        s._t = 160.0
        EC._trust_observe(s, "J2", (order[0], "e1"), [])           # first arrives
        s._t = 170.0
        EC._trust_observe(s, "J2", (order[1], "e1"), [])           # second arrives
        assert s._provisional_lies["J1"] == 0                       # both lifted
        assert EC._live_can_corroborate(s, "J1") is True, f"stuck after order {order}"
        assert s.trust.summary()["J1"]["truths"] == 2               # two committed truths


def test_publisher_sensed_flow_is_never_a_false_lie():
    # In the REAL flow a junction only advance-claims a vehicle it has itself locally sensed,
    # which confirms the ev_id GLOBALLY. So even a very long TTL gap never yields a false lie.
    s = _Stub(ttl=1.0)
    EC._trust_observe(s, "J1", ("amb1", "e1"), [])                   # J1 senses locally first
    EC._trust_observe(s, "J2", None, [_claim("J1", "amb1")])         # then claims to J2
    s._t = 9999.0                                                     # arbitrarily long later
    EC._trust_observe(s, "J2", None, [])
    assert s._provisional_lies.get("J1", 0) == 0                     # never a provisional lie
    assert EC._live_can_corroborate(s, "J1") is True


def test_claim_scored_once_not_repeatedly():
    s = _Stub()
    EC._trust_observe(s, "J2", None, [_claim("J1", "amb1")])
    s._t = 10.0
    EC._trust_observe(s, "J2", ("amb1", "e1"), [])                    # truth
    t_after = s.trust.trust_of("J1")
    s._t = 20.0
    EC._trust_observe(s, "J2", ("amb1", "e1"), [])                    # same ev again
    assert s.trust.trust_of("J1") == t_after                         # not double-credited
    assert s.trust.summary()["J1"]["truths"] == 1


# --------------------------------------------------------------------------- #
# 2. DISCOUNT-ONLY: trust can only withhold cross-junction corroboration.
# --------------------------------------------------------------------------- #
def test_caught_liar_can_no_longer_corroborate():
    s = _Stub()
    s._sightings = {"amb1": {"J1": ("e1", 0)}}                        # J1 sighted amb1
    # A different junction J3 claims amb1; J1's sighting would corroborate it.
    assert EC._corroborated(s, "amb1", "J3", "J2", None) is True      # trusted J1 corroborates
    s.trust = s.trust.verify("J1", False)                            # J1 caught lying once
    assert s.trust.can_corroborate("J1") is False
    assert EC._corroborated(s, "amb1", "J3", "J2", None) is False     # discounted -> withheld


def test_corroboration_withheld_via_provisional_discount():
    # The NEW wiring: _corroborated must withhold because of an OUTSTANDING PROVISIONAL lie
    # (a count), not only a committed-ledger lie. J1 has a real sighting that would
    # corroborate J3's claim, but J1 currently carries a provisional lie -> discounted.
    s = _Stub()
    s._sightings = {"amb1": {"J1": ("e1", 0)}}
    assert EC._corroborated(s, "amb1", "J3", "J2", None) is True      # baseline: J1 corroborates
    s._provisional_keys.add(("ghost", "J1"))                          # J1 has an outstanding lie
    s._provisional_lies["J1"] = 1
    assert EC._live_can_corroborate(s, "J1") is False
    assert EC._corroborated(s, "amb1", "J3", "J2", None) is False     # withheld via the count


def test_high_base_insider_still_locked_out_by_one_phantom():
    # An insider that earned high committed trust from many real claims is STILL locked out
    # by a single outstanding phantom: effective = high_base * lie_factor < floor.
    s = _Stub()
    for i in range(8):
        s.trust = s.trust.verify("J1", True)                         # climb committed base high
    assert s.trust.trust_of("J1") > 0.7 and EC._live_can_corroborate(s, "J1") is True
    s._provisional_keys.add(("ghost", "J1"))
    s._provisional_lies["J1"] = 1                                    # one unconfirmed phantom
    assert EC._effective_trust(s, "J1") < 0.5                        # high base * 0.25 < floor
    assert EC._live_can_corroborate(s, "J1") is False               # locked out regardless of base


def test_local_sensing_never_trust_gated():
    s = _Stub()
    # Build a genuinely HOSTILE trust world: every relevant source is BELOW the floor.
    s.trust = s.trust.verify("J1", False).verify("J3", False).verify("J0", False)
    assert not s.trust.can_corroborate("J1") and not s.trust.can_corroborate("J3")
    # Even so, the target's OWN local sensing (ultimate truth) still corroborates -- it is
    # never trust-gated. If a regression made local sensing trust-gated, this would fail.
    assert EC._corroborated(s, "amb1", "J3", "J2", ("amb1", "e1")) is True


def test_trust_never_adds_corroboration_on_zero_evidence():
    s = _Stub()
    # No sightings at all: high trust must NOT manufacture a corroboration.
    s.trust = s.trust.verify("J1", True).verify("J1", True)          # J1 highly trusted
    assert EC._corroborated(s, "amb1", "J1", "J2", None) is False     # nothing to corroborate


# --------------------------------------------------------------------------- #
# 3. Default OFF: trust changes nothing.
# --------------------------------------------------------------------------- #
def test_trust_off_is_a_noop_for_observe():
    s = _Stub(gating=False)
    EC._trust_observe(s, "J2", None, [_claim("J1", "amb1")])
    s._t = 500.0
    EC._trust_observe(s, "J2", None, [])
    assert s.trust.summary() == {}                                   # no scoring happened
    assert s._claim_first == {}


def test_trust_off_corroboration_ignores_trust():
    s = _Stub(gating=False)
    s._sightings = {"amb1": {"J1": ("e1", 0)}}
    s.trust = s.trust.verify("J1", False)                            # J1 would be a liar...
    assert s.trust.can_corroborate("J1") is False
    # ...but with gating OFF the classic corroboration behaviour is unchanged.
    assert EC._corroborated(s, "amb1", "J3", "J2", None) is True


# --------------------------------------------------------------------------- #
# 4. Asymmetry end-to-end: one lie undoes many truths.
# --------------------------------------------------------------------------- #
def test_one_lie_undoes_many_truths_in_live_path():
    s = _Stub()
    for i in range(6):                                               # six honest confirmations
        ev = f"amb{i}"
        EC._trust_observe(s, "J2", None, [_claim("J1", ev)])
        s._t += 5.0
        EC._trust_observe(s, "J2", (ev, "e1"), [])
    high = s.trust.trust_of("J1")
    assert high > 0.7 and s.trust.can_corroborate("J1")
    s.trust = s.trust.verify("J1", False)                            # a single lie
    assert s.trust.trust_of("J1") < 0.5                             # collapses below floor
    assert s.trust.can_corroborate("J1") is False
