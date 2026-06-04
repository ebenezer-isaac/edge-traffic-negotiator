"""Adversarial tests for the three Wk7-8 attack injectors + their detectors.

Asserts, against the AS-BUILT detectors driven through the genuine
``CoordinatedController.decide`` path (deterministic StubAgent + in-memory TraCI
stand-in, no SUMO / no Foundry):

  (a) SPOOF  -> conservation flags ``inflated`` once delta > tolerance, and a
      sub-tolerance over-claim correctly EVADES (no flag).
  (b) FAULTY -> conservation flags ``under_reported`` for an under-claim beyond
      tolerance; a small drop within tolerance is NOT flagged.
  (c) SYBIL  -> the AUTH layer rejects unknown_sender / not_neighbour / revoked /
      bad_signature; NONE of these reach conservation.
      And the COLLUSION lockstep case evades BOTH layers (the honest negative).

Plus:
  * a BENIGN control run yields ~zero flags / zero rejections (false-positive
    sanity);
  * the measured P/R/F1 per attack are exactly the reproducible values;
  * the tolerance ROC trades recall for false-alarm rate monotonically.

src/ is inserted on sys.path so imports resolve under `python -m pytest tests`.
"""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import attacks  # noqa: E402
import run_attacks as ra  # noqa: E402
from attacks import MaliciousPublisher  # noqa: E402


# --------------------------------------------------------------------------- #
# (a) SPOOF -> conservation 'inflated'; sub-tolerance evades.
# --------------------------------------------------------------------------- #

def test_spoof_above_tolerance_is_flagged_inflated():
    """A1 claims 40 toward A0; A0 observes 15. delta=25 > 2 -> inflated."""
    ctrl, bus, identities, _ = ra._build({"A1": 15}, tolerance=2)
    MaliciousPublisher(bus).publish_toward(identities["A1"], "A0", 0, 40)
    ctrl.decide("A0", ctrl.tls["A0"])
    flagged = [d for d in ctrl.detections if d.flagged and (d.src, d.dst) == ("A1", "A0")]
    assert flagged, "an over-claim beyond tolerance must be flagged"
    assert flagged[0].reason == "inflated"
    assert flagged[0].delta > 0  # claimed exceeds observed


def test_spoof_within_tolerance_evades():
    """A sub-tolerance over-claim (delta=2 at tol=2) is 'ok' -- the Xiao floor."""
    ctrl, bus, identities, _ = ra._build({"A1": 15}, tolerance=2)
    MaliciousPublisher(bus).publish_toward(identities["A1"], "A0", 0, 17)  # +2
    ctrl.decide("A0", ctrl.tls["A0"])
    edge = [d for d in ctrl.detections if (d.src, d.dst) == ("A1", "A0")]
    assert edge, "the edge should be reconciled"
    assert not edge[0].flagged, "a within-tolerance lie must NOT be flagged"
    assert edge[0].reason == "ok"


def test_spoof_label_matches_detector_across_sweep():
    """For every delta, the injector's expected_reason matches the live detector
    (the ground-truth label is faithful to the as-built code)."""
    rows, cm, _lat = ra.run_spoof(tolerance=2, deltas=[0, 1, 2, 3, 5, 25])
    for r in rows:
        if r["expected_reason"] == "inflated":
            assert r["detected"] and r["reason"] == "inflated", r
        else:  # ok / sub-tolerance
            assert not r["detected"] and r["reason"] == "ok", r
    # No false positives, and recall < 1 because of the sub-tolerance evasions.
    assert cm["fp"] == 0
    assert cm["fn"] >= 1, "sub-tolerance lies must show up as missed (honest)"


# --------------------------------------------------------------------------- #
# (b) FAULTY -> conservation 'under_reported'; small drop evades.
# --------------------------------------------------------------------------- #

def test_faulty_under_claim_beyond_tolerance_is_under_reported():
    """A1 under-claims (10) vs A0's true observation (20). delta=-10 < -2."""
    ctrl, bus, identities, _ = ra._build({"A1": 20}, tolerance=2)
    MaliciousPublisher(bus).publish_toward(identities["A1"], "A0", 0, 10)
    ctrl.decide("A0", ctrl.tls["A0"])
    flagged = [d for d in ctrl.detections if d.flagged and (d.src, d.dst) == ("A1", "A0")]
    assert flagged, "an under-claim beyond tolerance must be flagged"
    assert flagged[0].reason == "under_reported"
    assert flagged[0].delta < 0  # observed exceeds claimed


def test_faulty_small_drop_within_tolerance_evades():
    """A 10% drop on 20 (claim 18 vs obs 20, delta -2) stays within tolerance."""
    ctrl, bus, identities, _ = ra._build({"A1": 20}, tolerance=2)
    MaliciousPublisher(bus).publish_toward(identities["A1"], "A0", 0, 18)
    ctrl.decide("A0", ctrl.tls["A0"])
    edge = [d for d in ctrl.detections if (d.src, d.dst) == ("A1", "A0")]
    assert edge and not edge[0].flagged and edge[0].reason == "ok"


def test_faulty_total_outage_is_undetected_by_controller():
    """As-built finding: a total sender outage (no claim) is NOT reconciled, so
    the missing_claim reason is unreachable via the live decide() path -- we
    assert the honest gap rather than pretend it is caught."""
    rows, cm, _lat = ra.run_faulty(tolerance=2, drop_fractions=[1.0])
    outage = rows[0]
    assert outage["malicious"] is True
    assert outage["detected"] is False, "controller does not flag a no-claim outage"
    assert "missing_claim unreachable" in outage["note"]
    assert cm["fn"] == 1


# --------------------------------------------------------------------------- #
# (c) SYBIL -> AUTH rejection; never reaches conservation. Collusion evades both.
# --------------------------------------------------------------------------- #

def test_sybil_unknown_sender_rejected_by_auth():
    ctrl, bus, identities, _ = ra._build_with_sybil_neighbour(tolerance=2)
    MaliciousPublisher(bus).publish_unregistered(ra.SYBIL_ID, "A0", t=0, release=40)
    ctrl.decide("A0", ctrl.tls["A0"])
    reasons = [r["reason"] for r in bus.rejected
               if r["recipient"] == "A0" and r["sender"] == ra.SYBIL_ID]
    assert reasons == ["unknown_sender"]
    # Never reached conservation: no detection on that edge.
    assert not any((d.src, d.dst) == (ra.SYBIL_ID, "A0") for d in ctrl.detections)


def test_sybil_not_neighbour_rejected_by_auth():
    ctrl, bus, identities, _ = ra._build({"A1": 0}, tolerance=2)
    MaliciousPublisher(bus).publish_not_neighbour(identities["B1"], "A0", t=0, release=40)
    ctrl.decide("A0", ctrl.tls["A0"])
    reasons = [r["reason"] for r in bus.rejected
               if r["recipient"] == "A0" and r["sender"] == "B1"]
    assert reasons == ["not_neighbour"]


def test_sybil_revoked_rejected_by_auth():
    ctrl, bus, identities, registry = ra._build({"A1": 0}, tolerance=2)
    registry.revoke("A1")
    MaliciousPublisher(bus).publish_revoked(identities["A1"], "A0", t=0, release=40)
    ctrl.decide("A0", ctrl.tls["A0"])
    reasons = [r["reason"] for r in bus.rejected
               if r["recipient"] == "A0" and r["sender"] == "A1"]
    assert reasons == ["revoked"]


def test_sybil_bad_signature_rejected_by_auth():
    """Claim to be A1 but sign with B0's key -> bad_signature."""
    ctrl, bus, identities, _ = ra._build({"A1": 0}, tolerance=2)
    MaliciousPublisher(bus).publish_tampered(
        identities["A1"], identities["B0"], "A0", t=0, release=40)
    ctrl.decide("A0", ctrl.tls["A0"])
    reasons = [r["reason"] for r in bus.rejected
               if r["recipient"] == "A0" and r["sender"] == "A1"]
    assert reasons == ["bad_signature"]
    # The forged message never produced a (valid) claim -> no detection.
    assert not any((d.src, d.dst) == ("A1", "A0") for d in ctrl.detections)


def test_collusion_lockstep_evades_both_layers():
    """Approved A1 inflates claim AND A0 observes the inflated count in lockstep.
    Auth admits (valid member/signature); conservation returns ok. Recall 0 --
    the honest negative result (Xiao2026), asserted explicitly."""
    rows, auth_cm, collusion = ra.run_sybil(tolerance=2)
    assert collusion["malicious"] is True
    assert collusion["detected_by_auth"] is False
    assert collusion["detected_by_conservation"] is False
    assert collusion["detected"] is False, "collusion must evade BOTH layers"


def test_all_four_auth_violations_caught():
    """The auth confusion over the four admission cases is perfect (recall 1.0)."""
    _rows, auth_cm, _coll = ra.run_sybil(tolerance=2)
    assert auth_cm == {"tp": 4, "fp": 0, "fn": 0, "tn": 0}


# --------------------------------------------------------------------------- #
# Benign control: ~zero flags and zero rejections (false-positive sanity).
# --------------------------------------------------------------------------- #

def test_benign_control_yields_no_flags_or_rejections():
    """An honest message (claim == observation) is admitted and NOT flagged.

    NB: A0 also publishes its OWN outgoing report each decide(); reading its
    inbox, the bus drops A0's self-echo with reason 'not_neighbour' (a node is
    not its own neighbour). That self-echo is NOT a false positive against a
    peer, so the meaningful sanity check is: the legitimate neighbour A1 is
    never rejected, and conservation raises zero flags.
    """
    ctrl, bus, identities, _ = ra._build({"A1": 12}, tolerance=2)
    MaliciousPublisher(bus).publish_toward(identities["A1"], "A0", 0, 12)
    ctrl.decide("A0", ctrl.tls["A0"])
    peer_rejections = [r for r in bus.rejected if r["sender"] != "A0"]
    assert peer_rejections == [], f"a legitimate neighbour was rejected: {peer_rejections}"
    flagged = [d for d in ctrl.detections if d.flagged]
    assert flagged == [], f"benign run must produce zero flags, got {flagged}"


def test_benign_jitter_within_tolerance_not_flagged():
    """Honest in-transit jitter (claim 13 vs observed 12) stays within tolerance."""
    ctrl, bus, identities, _ = ra._build({"A1": 12}, tolerance=2)
    MaliciousPublisher(bus).publish_toward(identities["A1"], "A0", 0, 13)
    ctrl.decide("A0", ctrl.tls["A0"])
    assert not any(d.flagged for d in ctrl.detections)


# --------------------------------------------------------------------------- #
# Reproducible aggregate metrics + ROC monotonicity.
# --------------------------------------------------------------------------- #

def test_measured_prf1_are_reproducible():
    """The headline P/R/F1 are exactly the documented, reproducible numbers."""
    res = ra.run_all(tolerance=2)
    _sr, spoof_cm, _sl = res["spoof"]
    _fr, faulty_cm, _fl = res["faulty"]
    _yr, sybil_cm, _coll = res["sybil"]

    sp, srec, sf1 = ra._prf1(spoof_cm["tp"], spoof_cm["fp"], spoof_cm["fn"])
    assert (spoof_cm["tp"], spoof_cm["fp"], spoof_cm["fn"], spoof_cm["tn"]) == (4, 0, 2, 1)
    assert sp == 1.0  # zero false positives

    assert (faulty_cm["tp"], faulty_cm["fp"], faulty_cm["fn"], faulty_cm["tn"]) == (3, 0, 2, 1)

    assert sybil_cm == {"tp": 4, "fp": 0, "fn": 0, "tn": 0}


def test_conservation_latency_is_one_cycle():
    """A clearly-detectable spoof fires the SAME cycle it appears (stateless)."""
    assert ra.measure_conservation_latency(tolerance=2) == 1


def test_tolerance_roc_trades_recall_for_false_alarm():
    """Raising tolerance is monotone non-increasing in recall and in false-alarm
    rate (you trade missed lies for fewer jitter false-alarms)."""
    table = ra.run_tolerance_roc([0, 1, 2, 3, 5, 10])
    recalls = [row["recall"] for row in table]
    far = [row["false_alarm_rate"] for row in table]
    assert recalls == sorted(recalls, reverse=True), recalls
    assert far == sorted(far, reverse=True), far
    # At tolerance 0 we false-alarm on benign jitter; high tolerance never does.
    assert far[0] > 0.0
    assert far[-1] == 0.0


def test_injected_message_is_immutable_and_relabel_returns_copy():
    """InjectedMessage is frozen; relabel_observed returns a NEW record."""
    msg = attacks.spoof_release("A1", "A0", true_release=15, delta=10,
                                tolerance=2, tick=0)
    relabelled = attacks.relabel_observed(msg, observed=99)
    assert relabelled is not msg
    assert relabelled.true_release == 99
    assert msg.true_release == 15  # original unchanged (immutability)
