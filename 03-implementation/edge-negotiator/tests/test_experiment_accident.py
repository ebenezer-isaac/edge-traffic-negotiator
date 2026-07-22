"""Fault-finding tests for the H2 accident-reconstruction demo (src/experiment_accident.py).

The demo is the D-accident headline (§4.4). These tests are written to FAIL if the
demo could ever emit a green result over an unverifiable log, if the tamper slips
through, or if the which-key attribution regresses. No live model / SUMO needed --
the incident is the deterministic §6.2 fixture.
"""
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import assessment as A  # noqa: E402
import experiment_accident as ac  # noqa: E402
from system import IntegratedSystem, SystemConfig  # noqa: E402
from system_ev import stage_ev_incident  # noqa: E402


def _staged():
    staged = stage_ev_incident(IntegratedSystem(SystemConfig()))
    return staged, ac._der_dict(staged["identities"])


# --------------------------------------------------------------------------- #
# 1. End-to-end: the demo passes every D-accident sub-claim.
# --------------------------------------------------------------------------- #
def test_demo_passes_all_checks():
    r = ac.run()
    assert r["passed"] is True
    assert all(r["checks"].values()), r["checks"]
    # The eight sub-claims are all present (no silently-dropped check).
    assert set(r["checks"]) >= {
        "verify_chain", "verify_signatures", "merkle_inclusion_proof",
        "phantom_commandeered_recorded", "which_key_attributed_to_signing_key",
        "reconstruction_derived_from_verified_records",
        "evidence_pack_is_fact_only", "tamper_caught_by_identity_verify"}


def test_which_key_attributes_phantom_to_signing_key():
    r = ac.run()
    kp = r["which_key"]["phantom"]
    assert kp["origin"] == A.ATTACKER_KEY
    assert kp["culprit_key"] == "A1"          # names the KEY, never a person
    # The real EV was locally sensed -> keyless, no signing key attributed.
    assert r["which_key"]["real"]["culprit_key"] is None


def test_what_shows_commandeering_off_baseline():
    r = ac.run()
    w = r["what_happened"]
    assert w["phantom_commandeered"] is True
    assert w["phantom_executed_phase"] != w["baseline_phase"]
    assert w["real_preempted"] is True


# --------------------------------------------------------------------------- #
# 2. The tamper test has teeth: a chain-surviving substitution is still caught.
# --------------------------------------------------------------------------- #
def test_tamper_survives_chain_but_is_caught():
    r = ac.run()
    t = r["tamper_test"]
    assert t["applicable"] is True
    assert t["verify_chain_after_tamper"] is True      # chain still verifies
    assert t["verify_signatures_after_tamper"] is True  # issuer layer still ok
    assert t["fault_report_status"] == "REFUSED"        # yet the report refuses
    assert t["caught_by_identity_verify"] is True


# --------------------------------------------------------------------------- #
# 3. The verification layer REFUSES to go green over a broken audit.
# --------------------------------------------------------------------------- #
def test_verify_layer_raises_on_broken_chain():
    staged, der = _staged()
    audit = staged["audit"]
    # Mutate a hashed field -> verify_chain must fail -> the demo must not proceed.
    audit._log[-1]["event"]["executed"] = "tampered-in-place"
    assert audit.verify_chain() is False
    with pytest.raises(RuntimeError):
        ac._verify_layer(audit, der)


def test_reconstruct_refuses_on_broken_chain():
    staged, der = _staged()
    audit = staged["audit"]
    ev = staged["ev_incident"]
    records = list(__import__("system_ev").flatten_entries(audit))
    audit._log[-1]["event"]["executed"] = "tampered-in-place"
    outcome = ac._outcome(ev["phantom_ev_id"], "A0", ev.get("real_tick_t"),
                          ac._PHANTOM_TYPE)
    recon = ac._reconstruct(audit, der, records, outcome)
    assert recon["status"] == "REFUSED"


# --------------------------------------------------------------------------- #
# 4. The evidence pack is fact-only (no origin/verdict leakage).
# --------------------------------------------------------------------------- #
def test_evidence_pack_is_fact_only():
    r = ac.run()
    assert r["reconstruction_phantom"]["evidence_pack_is_fact_only"] is True
