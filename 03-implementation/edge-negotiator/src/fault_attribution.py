"""Fault attribution over the audit log: who was at fault in an adverse outcome.

Realises Part 2 of `TEST-AUDIT-FAULT-SPEC.md`. Given an adverse outcome (a false
preemption, a missed emergency, starvation, gridlock), this walks the audit
records, finds the decision(s) that caused it, follows each decision's
`driving_input_seq` back to the message (and therefore the signing key) that
drove it, and returns a verdict naming who was at fault. Because every message
is Ed25519-signed and hash-chained, a lie is cryptographically bound to its
signing key, so the culprit is provable, not asserted (non-repudiation).

The headline distinction (the dissertation's accountability claim): was the
adverse outcome a HUMAN's fault (a person fed a false or unauthorised input,
attributable to their key) or the AI's fault (the classifier or detector
misjudged a correctly-evidenced case)? The verdicts map onto exactly that:

    ATTACKER              -> human   (an identified key fed a false/unauthorised input)
    OUT_OF_SCOPE_COLLUSION-> human   (>=2 keys, undetectable at runtime, keys still named)
    SYSTEM_CLASSIFIER     -> ai      (the rule/SLM mislabelled a well-evidenced case)
    SYSTEM_DETECTOR       -> ai      (a detector false-negatived / a sensor lied to itself)
    LEGITIMATE_DEGRADATION-> none    (every decision was correct; harm is the accepted cost)
    UNKNOWN               -> unknown (no record explains it; flagged, never silent)

This module is pure and deterministic: it reads records (dicts matching the
spec schema, e.g. from ``AuditLog`` events) and never mutates them. Runtime
producers that emit those records live in the controller/audit layer; this
module is the forensic reader, unit-tested on synthetic logs.
"""
from __future__ import annotations

# Verdicts (Part 2.1) and their human-vs-AI mapping (the accountability claim).
ATTACKER = "ATTACKER"
OUT_OF_SCOPE_COLLUSION = "OUT_OF_SCOPE_COLLUSION"
SYSTEM_CLASSIFIER = "SYSTEM_CLASSIFIER"
SYSTEM_DETECTOR = "SYSTEM_DETECTOR"
LEGITIMATE_DEGRADATION = "LEGITIMATE_DEGRADATION"
UNKNOWN = "UNKNOWN"

HUMAN_VS_AI = {
    ATTACKER: "human",
    OUT_OF_SCOPE_COLLUSION: "human",
    SYSTEM_CLASSIFIER: "ai",
    SYSTEM_DETECTOR: "ai",
    LEGITIMATE_DEGRADATION: "none",
    UNKNOWN: "unknown",
}

DEFAULT_HORIZON = 60  # ticks looked back from the outcome for a causal decision


def _messages_by_seq(entries):
    return {e["seq"]: e for e in entries
            if e.get("kind") == "message" and "seq" in e}


def _window_decisions(entries, junction, t, horizon):
    lo = t - horizon
    out = [e for e in entries
           if e.get("kind") == "decision" and e.get("junction") == junction
           and lo <= e.get("t", -1) <= t]
    out.sort(key=lambda e: e.get("t", 0))
    return out


def _catchable_phantom(msg, decision) -> bool:
    """True if a policy SHOULD have rejected this input (so accepting it is the
    classifier's error, not an undetectable attack): zero independent
    corroboration (P3) or an out-of-band residual (P5)."""
    corr = decision.get("corroboration_count")
    if corr is None:
        corr = msg.get("corroboration_count", 0) if msg else 0
    in_band = True
    if msg and isinstance(msg.get("conservation"), dict):
        in_band = msg["conservation"].get("in_band", True)
    return corr == 0 or (not in_band)


def _causal_decision(decisions, outcome):
    """The decision that produced the outcome (latest matching one in window)."""
    ev = outcome.get("ev_id")
    typ = outcome.get("type")
    cands = decisions
    if ev is not None:
        matched = [d for d in decisions if d.get("trigger", {}).get("ev_id") == ev]
        cands = matched or decisions
    if typ == "false_preemption":
        preempts = [d for d in cands if d.get("executed") != d.get("mp_choice")]
        cands = preempts or cands
    elif typ == "missed_ev":
        withheld = [d for d in cands if d.get("executed") == d.get("mp_choice")]
        cands = withheld or cands
    return cands[-1] if cands else None


def _classify(decision, msg, outcome):
    """Return (verdict, culprit, reason) for a single causal decision."""
    typ = outcome.get("type")
    cls = decision.get("classification")
    decider = decision.get("decider", "unknown")

    if typ == "false_preemption":
        if msg is None:  # a local sighting drove a preempt for an event that was not real
            return (SYSTEM_DETECTOR, decision.get("junction"),
                    "local sensor reported a vehicle that did not exist")
        if not msg.get("sig_valid", False) or msg.get("registry_status") != "approved":
            return (ATTACKER, msg.get("sender"),
                    "acted on an unauthenticated or unapproved message")
        # signed, approved insider whose claim was false:
        if cls == "LEGITIMATE":
            if _catchable_phantom(msg, decision):
                return (SYSTEM_CLASSIFIER, decider,
                        "classifier accepted a catchable phantom that policy "
                        "P3/P5 should have rejected (zero corroboration or out-of-band)")
            return (OUT_OF_SCOPE_COLLUSION, msg.get("sender"),
                    "the false claim was corroboration-consistent and in-band, so it "
                    "was undetectable at runtime (>=2-key collusion class)")
        # flagged fake/unknown yet a preempt executed -> a shield/impl defect (ours)
        return (SYSTEM_CLASSIFIER, decider,
                "input was flagged but a preemption executed anyway (shield defect)")

    if typ == "missed_ev":
        if msg is None:
            return (SYSTEM_DETECTOR, decision.get("junction"),
                    "a real emergency was never sensed locally nor claimed")
        if msg.get("replay") or msg.get("withheld"):
            return (ATTACKER, msg.get("sender"),
                    "a genuine claim was withheld or replayed away")
        if cls in ("SPOOFED_OR_FAULTY", "UNKNOWN"):
            return (SYSTEM_CLASSIFIER, decider,
                    "classifier rejected a genuine emergency (false negative)")
        return (SYSTEM_DETECTOR, decision.get("junction"),
                "genuine emergency accepted but not cleared in time")

    if typ == "starvation":
        if decision.get("trigger", {}).get("ev_id"):
            return (LEGITIMATE_DEGRADATION, None,
                    "approach deferred by an admissible emergency preemption (within policy)")
        return (SYSTEM_DETECTOR, decision.get("junction"),
                "anti-starvation override did not fire when it should have")

    if typ == "gridlock":
        return (LEGITIMATE_DEGRADATION, None,
                "network saturation, not attributable to a specific decision")

    return (UNKNOWN, None, "no rule matched this outcome type")


def fault_report(entries, outcome, horizon: int = DEFAULT_HORIZON) -> dict:
    """Attribute fault for one adverse ``outcome`` against the audit ``entries``.

    ``entries``: list of record dicts (message/decision), spec Part 1 schema.
    ``outcome``: dict with at least ``type`` and ``junction`` and ``t``; may carry
    ``ev_id`` and ``ground_truth``. Returns a structured, auditable fault report.
    """
    junction = outcome.get("junction")
    t = outcome.get("t", 0)
    decisions = _window_decisions(entries, junction, t, horizon)
    causal = _causal_decision(decisions, outcome)

    if causal is None:
        verdict, culprit, reason = (UNKNOWN, None,
                                    "no decision in the causal window explains the outcome")
        driving, policies, evidence = None, [], []
    else:
        msgs = _messages_by_seq(entries)
        driving_seq = causal.get("driving_input_seq")
        msg = msgs.get(driving_seq) if driving_seq is not None else None
        verdict, culprit, reason = _classify(causal, msg, outcome)
        driving = (msg.get("sender") if msg else None)
        policies = causal.get("policies_applied", [])
        evidence = [s for s in (causal.get("seq"), driving_seq) if s is not None]

    return {
        "outcome": {k: outcome.get(k) for k in ("type", "junction", "t", "ev_id", "ground_truth")},
        "verdict": verdict,
        "human_or_ai": HUMAN_VS_AI[verdict],
        "culprit": culprit,
        "driving_input_sender": driving,
        "policies_applied": policies,
        "causal_decision_t": (causal.get("t") if causal else None),
        "reason": reason,
        "evidence_seqs": evidence,
    }
