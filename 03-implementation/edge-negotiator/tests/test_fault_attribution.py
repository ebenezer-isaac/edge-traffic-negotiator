"""Tests for fault_attribution: the human-vs-AI verdict over synthetic audit logs
(TEST-AUDIT-FAULT-SPEC Part 2). Pure, no SUMO."""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import fault_attribution as fa  # noqa: E402


def _msg(seq, sender, sig=True, approved=True, in_band=True, corr=0, replay=False):
    return {"kind": "message", "seq": seq, "t": 100, "sender": sender,
            "sig_valid": sig, "registry_status": "approved" if approved else "revoked",
            "replay": replay, "corroboration_count": corr,
            "conservation": {"in_band": in_band}}


def _dec(t, junction, driving_seq, cls, executed, mp, decider="rule",
         policies=None, ev="AMB", corr=None):
    d = {"kind": "decision", "seq": 900 + t, "t": t, "junction": junction,
         "driving_input_seq": driving_seq, "classification": cls,
         "executed": executed, "mp_choice": mp, "decider": decider,
         "policies_applied": policies or [], "trigger": {"ev_id": ev}}
    if corr is not None:
        d["corroboration_count"] = corr
    return d


# --- ATTACKER = human fault ------------------------------------------------ #

def test_unauthenticated_input_is_human_attacker():
    entries = [_msg(1, "J1", sig=False, approved=False),
               _dec(105, "J2", 1, "LEGITIMATE", executed=2, mp=0)]
    r = fa.fault_report(entries, {"type": "false_preemption", "junction": "J2",
                                  "t": 105, "ev_id": "AMB"})
    assert r["verdict"] == fa.ATTACKER
    assert r["human_or_ai"] == "human"
    assert r["culprit"] == "J1"


def test_collusion_consistent_phantom_is_out_of_scope_human():
    # signed, approved, corroborated (corr>0) and in-band -> undetectable at runtime
    entries = [_msg(1, "J1", corr=2, in_band=True),
               _dec(105, "J2", 1, "LEGITIMATE", executed=2, mp=0, corr=2)]
    r = fa.fault_report(entries, {"type": "false_preemption", "junction": "J2",
                                  "t": 105, "ev_id": "AMB"})
    assert r["verdict"] == fa.OUT_OF_SCOPE_COLLUSION
    assert r["human_or_ai"] == "human"


# --- SYSTEM_CLASSIFIER = AI fault ------------------------------------------ #

def test_catchable_phantom_accepted_is_ai_classifier_fault():
    # zero corroboration, in-band -> P3 should have rejected; classifier accepted -> AI fault
    entries = [_msg(1, "J1", corr=0, in_band=True),
               _dec(105, "J2", 1, "LEGITIMATE", executed=2, mp=0, decider="slm", corr=0)]
    r = fa.fault_report(entries, {"type": "false_preemption", "junction": "J2",
                                  "t": 105, "ev_id": "AMB"})
    assert r["verdict"] == fa.SYSTEM_CLASSIFIER
    assert r["human_or_ai"] == "ai"
    assert r["culprit"] == "slm"


def test_missed_real_emergency_is_ai_classifier_fault():
    entries = [_msg(1, "J1", corr=2, in_band=True),
               _dec(105, "J2", 1, "SPOOFED_OR_FAULTY", executed=0, mp=0, decider="slm")]
    r = fa.fault_report(entries, {"type": "missed_ev", "junction": "J2",
                                  "t": 105, "ev_id": "AMB", "ground_truth": "real"})
    assert r["verdict"] == fa.SYSTEM_CLASSIFIER
    assert r["human_or_ai"] == "ai"


# --- no fault / unknown ---------------------------------------------------- #

def test_starvation_by_admissible_ev_is_legitimate():
    entries = [_dec(105, "J2", None, "LEGITIMATE", executed=1, mp=0, ev="AMB")]
    r = fa.fault_report(entries, {"type": "starvation", "junction": "J2", "t": 105})
    assert r["verdict"] == fa.LEGITIMATE_DEGRADATION
    assert r["human_or_ai"] == "none"


def test_gridlock_is_legitimate_degradation():
    entries = [_dec(105, "J2", None, "LEGITIMATE", executed=0, mp=0, ev=None)]
    r = fa.fault_report(entries, {"type": "gridlock", "junction": "J2", "t": 105})
    assert r["verdict"] == fa.LEGITIMATE_DEGRADATION


def test_no_causal_decision_is_unknown():
    r = fa.fault_report([], {"type": "false_preemption", "junction": "J9", "t": 500})
    assert r["verdict"] == fa.UNKNOWN
    assert r["human_or_ai"] == "unknown"


def test_report_carries_evidence_and_policies():
    entries = [_msg(1, "J1", sig=False, approved=False),
               _dec(105, "J2", 1, "LEGITIMATE", executed=2, mp=0, policies=["P2"])]
    r = fa.fault_report(entries, {"type": "false_preemption", "junction": "J2", "t": 105})
    assert r["evidence_seqs"] and 1 in r["evidence_seqs"]
    assert r["policies_applied"] == ["P2"]
