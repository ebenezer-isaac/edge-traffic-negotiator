"""Fault-finding tests for the crash -> UK-law inference + audit suite
(src/crash_law.py, src/experiment_crash_law.py).

Written to FAIL if the law is not grounded in the verified facts, if an unauthorised
vehicle could claim the emergency exemption, if a dark/conflicting-green case is
mis-mapped, or if a tampered incident record is not caught.
"""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import crash_law as cl  # noqa: E402
import experiment_crash_law as ecl  # noqa: E402
from legal_corpus import load_corpus  # noqa: E402

CORPUS = load_corpus()


def _ids(facts):
    return [l["rule_id"] for l in cl.infer_applicable_law(facts, CORPUS)]


def test_civilian_red_is_driver_offence():
    ids = _ids(cl.CrashFacts(signal_state="red", crossing_class="civilian"))
    assert "LR-driver-red" in ids and "LR-red-prohibition" in ids


def test_authorised_corroborated_ambulance_gets_exemption():
    ids = _ids(cl.CrashFacts(signal_state="red", crossing_class="ambulance",
                             key_present=True, key_valid=True,
                             authority_class="emergency", corroborated=True))
    assert "LR-ev-exemption" in ids and "LR-griffin-calibration" in ids


def test_unauthorised_fake_ambulance_gets_NO_exemption():
    # An "ambulance" with no valid emergency key and no corroboration must NOT get the
    # exemption -- it is treated as a red-running offence (prevents a spoof from
    # laundering into an exemption).
    ids = _ids(cl.CrashFacts(signal_state="red", crossing_class="ambulance",
                             key_present=False, key_valid=False, corroborated=False))
    assert "LR-ev-exemption" not in ids
    assert "LR-driver-red" in ids


def test_maintenance_never_exempt():
    ids = _ids(cl.CrashFacts(signal_state="red", crossing_class="maintenance",
                             key_present=True, key_valid=True, authority_class="works"))
    assert "LR-maintenance-no-exemption" in ids
    assert "LR-ev-exemption" not in ids


def test_amber_maps_to_amber_rule():
    assert "LR-amber" in _ids(cl.CrashFacts(signal_state="amber", crossing_class="civilian"))


def test_dark_signal_overrides_red_running():
    ids = _ids(cl.CrashFacts(signal_state="dark", crossing_class="civilian"))
    assert ids == [next(l["rule_id"] for l in cl.infer_applicable_law(
        cl.CrashFacts(signal_state="dark", crossing_class="civilian"), CORPUS))]
    assert "LR-dark-signals" in ids
    assert "LR-driver-red" not in ids           # no red-running offence when dark


def test_conflicting_green_is_authority_misfeasance():
    ids = _ids(cl.CrashFacts(signal_state="green", crossing_class="civilian",
                             conflicting_green=True))
    assert "LR-authority-misfeasance" in ids


def test_every_cited_rule_is_grounded_in_the_kb():
    # No invented citations: every rule_id/statute_ref must exist in the KB.
    kb_ids = {r.rule_id for r in CORPUS.rules}
    facts = cl.CrashFacts(signal_state="red", crossing_class="ambulance",
                          key_valid=True, authority_class="emergency", corroborated=True,
                          second_party_on_green=True)
    for l in cl.infer_applicable_law(facts, CORPUS):
        assert l["rule_id"] in kb_ids
        assert l["statute_ref"] and l["text"]    # cited to the KB, with text


# --------------------------------------------------------------------------- #
# The suite: all scenarios proven (verified audit + correct law + tamper caught).
# --------------------------------------------------------------------------- #
def test_suite_all_scenarios_proven():
    r = ecl.run()
    assert r["all_proven"] is True
    assert r["n_scenarios"] >= 7
    for s in r["scenarios"]:
        assert s["verify_chain"] is True
        assert s["verify_signatures"] is True
        assert s["tamper_caught"] is True          # forged signature caught
        assert s["expected_rule_inferred"] is True  # the engineered law is inferred


def test_suite_tamper_is_actually_caught():
    # Every scenario must demonstrate a real tamper-catch (not vacuously true).
    r = ecl.run()
    assert all(s["tamper_caught"] for s in r["scenarios"])
