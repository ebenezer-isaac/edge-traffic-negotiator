"""Fault-finding tests for the multi-authorised-vehicle classifier + its categorised
evaluation (src/vehicle_authorization.py, src/experiment_vehicle_auth.py).

Each test is written to FAIL if the safety-critical authorisation logic regresses:
a maintenance vehicle MUST NOT be granted preemption; a wrong-class key MUST be
signal_tampering; an unknown class / missing metadata MUST resolve to UNKNOWN; and
the confusion-matrix maths must count a dangerous false grant correctly.
"""
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import experiment_vehicle_auth as ev  # noqa: E402
import vehicle_authorization as va  # noqa: E402

ENTS = va.load_entities()


def _c(**kw):
    return va.VehicleClaim(**kw)


# --------------------------------------------------------------------------- #
# 1. Genuine authorised EVs are granted; genuine non-preempt actions are not.
# --------------------------------------------------------------------------- #
def test_genuine_ambulance_is_granted_preemption():
    r = va.classify(_c(asserted_class="ambulance", action="preempt",
                       key_present=True, key_valid=True, key_class="emergency"), ENTS)
    assert r["classification"] == va.LEGITIMATE
    assert r["preemption_granted"] is True


def test_police_escort_hold_is_granted():
    r = va.classify(_c(asserted_class="police", action="escort_hold",
                       key_present=True, key_valid=True, key_class="emergency"), ENTS)
    assert r["classification"] == va.LEGITIMATE and r["preemption_granted"] is True


def test_fire_lane_hold_is_legit_but_not_preemption():
    r = va.classify(_c(asserted_class="fire", action="lane_hold",
                       key_present=True, key_valid=True, key_class="emergency"), ENTS)
    assert r["classification"] == va.LEGITIMATE
    assert r["preemption_granted"] is False   # lane-hold is not a signal preemption


# --------------------------------------------------------------------------- #
# 2. The safety-critical denials -- each attack family.
# --------------------------------------------------------------------------- #
def test_maintenance_is_never_granted_preemption():
    # Even a fully-valid maintenance vehicle requesting its allowed action gets NO
    # preemption; and a maintenance vehicle REQUESTING preempt is tampering.
    ok = va.classify(_c(asserted_class="maintenance", action="lane_closure",
                        key_present=True, key_valid=True, key_class="works"), ENTS)
    assert ok["classification"] == va.LEGITIMATE and ok["preemption_granted"] is False
    bad = va.classify(_c(asserted_class="maintenance", action="preempt",
                         key_present=True, key_valid=True, key_class="works"), ENTS)
    assert bad["classification"] == va.SPOOFED_OR_FAULTY
    assert bad["preemption_granted"] is False


def test_works_key_asserting_ambulance_is_signal_tampering():
    r = va.classify(_c(asserted_class="ambulance", action="preempt",
                       key_present=True, key_valid=True, key_class="works"), ENTS)
    assert r["classification"] == va.SPOOFED_OR_FAULTY
    assert r["attack_category"] == "signal_tampering"
    assert r["preemption_granted"] is False


def test_invalid_or_absent_key_is_invalid_id():
    absent = va.classify(_c(asserted_class="ambulance", action="preempt"), ENTS)
    assert absent["classification"] == va.SPOOFED_OR_FAULTY
    assert absent["attack_category"] == "invalid_id"
    invalid = va.classify(_c(asserted_class="ambulance", action="preempt",
                            key_present=True, key_valid=False, key_class="emergency"), ENTS)
    assert invalid["classification"] == va.SPOOFED_OR_FAULTY
    assert invalid["preemption_granted"] is False


def test_unknown_vehicle_type_is_unknown():
    r = va.classify(_c(asserted_class="drone", action="preempt",
                       key_present=True, key_valid=True, key_class="emergency"), ENTS)
    assert r["classification"] == va.UNKNOWN
    assert r["attack_category"] == "unknown_vehicle_type"
    assert r["preemption_granted"] is False


def test_missing_metadata_is_unknown():
    for claim in (_c(asserted_class=None, action="preempt", key_present=True,
                     key_valid=True, key_class="emergency"),
                  _c(asserted_class="ambulance", action=None, key_present=True,
                     key_valid=True, key_class="emergency"),
                  _c(asserted_class="ambulance", action="preempt", key_present=True,
                     key_valid=True, key_class=None)):
        r = va.classify(claim, ENTS)
        assert r["classification"] == va.UNKNOWN
        assert r["attack_category"] == "missing_metadata"
        assert r["preemption_granted"] is False


def test_contradictory_signals_escalate_to_unknown():
    r = va.classify(_c(asserted_class="ambulance", action="preempt", key_present=True,
                       key_valid=True, key_class="emergency", contradictory=True), ENTS)
    assert r["classification"] == va.UNKNOWN
    assert r["attack_category"] == "contradictory_signals"
    assert r["preemption_granted"] is False


# --------------------------------------------------------------------------- #
# 3. load_entities is fail-loud: a KB row missing an authorisation field raises.
# --------------------------------------------------------------------------- #
def test_load_entities_fail_loud_on_missing_field(tmp_path):
    bad = tmp_path / "gr.yaml"
    bad.write_text(
        "entities:\n"
        "  - class: ambulance\n"
        "    priority: 1\n"          # missing preemption_allowed etc.
        "law_rules: []\n", encoding="utf-8")
    with pytest.raises(ValueError):
        va.load_entities(str(bad))


def test_load_entities_fail_loud_on_empty(tmp_path):
    empty = tmp_path / "gr.yaml"
    empty.write_text("entities: []\nlaw_rules: []\n", encoding="utf-8")
    with pytest.raises(ValueError):
        va.load_entities(str(empty))


def test_load_entities_fail_loud_on_non_bool_field(tmp_path):
    # A type-malformed bool (e.g. key_required: "yes") must RAISE, never coerce --
    # a silently-coerced key_required=False would drop the key gate.
    bad = tmp_path / "gr.yaml"
    bad.write_text(
        "entities:\n"
        "  - class: ambulance\n"
        "    preemption_allowed: true\n"
        "    actions_allowed: [preempt]\n"
        "    authorising_key_classes: [emergency]\n"
        "    key_required: \"yes\"\n"      # non-bool -> must raise
        "law_rules: []\n", encoding="utf-8")
    with pytest.raises(ValueError):
        va.load_entities(str(bad))


def test_load_kb_reads_preemption_actions():
    _ents, preempt = va.load_kb()
    assert "preempt" in preempt and "escort_hold" in preempt
    assert "lane_closure" not in preempt   # a non-preempt action


# --------------------------------------------------------------------------- #
# 4. The evaluation: dataset balance + confusion maths + a full-pass.
# --------------------------------------------------------------------------- #
def test_dataset_covers_every_attack_family():
    cats = {c["category"] for c in ev.build_dataset()}
    for required in ("unknown_vehicle", "invalid_id", "signal_tampering",
                     "missing_metadata", "contradictory"):
        assert required in cats, required
    # and at least one genuine grantable EV family.
    assert "valid_ambulance" in cats


def test_eval_runs_clean_with_zero_dangerous_false_grants():
    r = ev.run()
    assert r["all_correct"] is True
    cm = r["confusion_grant_deny"]
    assert cm["dangerous_false_grants"] == 0   # no illegitimate claim was granted
    assert cm["false_negative_rate"] == 0.0
    assert r["class_accuracy"] == 1.0 and r["grant_accuracy"] == 1.0


def test_confusion_counts_a_dangerous_false_grant():
    # Feed the confusion counter a case the classifier GRANTS but the label says
    # DENY (an injected label flip) -> it must land as a false negative (FN>=1),
    # proving the metric would catch a real regression, not always read 0.
    ents = ENTS
    trap = ev._case("trap", va.VehicleClaim(
        asserted_class="ambulance", action="preempt", key_present=True,
        key_valid=True, key_class="emergency"),
        va.LEGITIMATE, expect_grant=False)  # genuine grant, but labelled should-deny
    cm = ev._confusion([trap], ents)
    assert cm["fn"] == 1
    assert cm["false_negative_rate"] == 1.0
    assert cm["dangerous_false_grants"] == 1
