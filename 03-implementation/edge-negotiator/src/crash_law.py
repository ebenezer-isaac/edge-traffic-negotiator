"""Infer the applicable UK traffic law for a crash FROM the verified audit facts
(MASTER-SPEC §4 H2; uk-traffic-law KB in ground_rules.yaml). Full-scale phase.

Each crash scenario is staged as a SIGNED, hash-chained audit record encoding the
mechanically-established incident facts (the signal state on the conflicting movement,
the class of the vehicle that crossed, its key/authorisation, whether an independent
junction corroborated it, whether the system emitted a conflicting green). The law is
then inferred DETERMINISTICALLY from those VERIFIED facts and cited to a specific rule
in the KB -- never guessed, never a fault verdict on a person: it is an evidence-pack
mapping "these audited facts" -> "this rule governs," with the KB's own fault_weight.

Precedence (from the KB + uk-traffic-law grounding):
  dark signal            -> LR-dark-signals (the MUST-obey duty falls away; HC r176)
  conflicting green      -> LR-authority-misfeasance (system created a trap; Bird v Pearce)
  crossing on amber      -> LR-amber
  crossing on red, by:
    emergency (authorised/corroborated) -> LR-ev-exemption + LR-griffin-calibration
    maintenance/works                   -> LR-maintenance-no-exemption + LR-driver-red
    civilian / unauthorised             -> LR-driver-red + LR-red-prohibition
  a green party in the conflict         -> LR-green-due-regard
  a second at-fault party               -> + LR-contrib-negligence / LR-contribution-1978

The point (supervisor ask): given the audit logs, we can prove the incident beyond
doubt (chain + signatures verify, a tamper is caught) AND infer which law applies
directly from those logs.
"""
from __future__ import annotations

from dataclasses import dataclass

_EMERGENCY = ("ambulance", "fire", "police")


@dataclass(frozen=True)
class CrashFacts:
    """The mechanically-established incident facts (as recorded in the signed audit)."""
    signal_state: str                 # "red" | "amber" | "green" | "dark"
    crossing_class: str               # civilian | ambulance | fire | police | maintenance
    key_present: bool = False
    key_valid: bool = False
    authority_class: str | None = None   # signing-key class (emergency|works|None)
    corroborated: bool = False        # an independent junction also sensed it
    conflicting_green: bool = False   # the system emitted a conflicting green (fault)
    second_party_on_green: bool = False  # another vehicle lawfully on green in the conflict
    claim_key: str | None = None      # signing key that triggered the state (for spoof)


def as_record(facts: CrashFacts, junction: str, ev_id: str, t: float) -> dict:
    """The §11-shaped signed audit record encoding the incident facts."""
    return {
        "kind": "incident", "junction": junction, "ev_id": ev_id, "t": t,
        "signal_state": facts.signal_state, "crossing_class": facts.crossing_class,
        "key_present": facts.key_present, "key_valid": facts.key_valid,
        "authority_class": facts.authority_class, "corroborated": facts.corroborated,
        "conflicting_green": facts.conflicting_green,
        "second_party_on_green": facts.second_party_on_green,
        "claim_key": facts.claim_key,
    }


def facts_from_record(rec: dict) -> CrashFacts:
    """Rebuild the facts from a VERIFIED audit record (read back, not assumed)."""
    return CrashFacts(
        signal_state=rec.get("signal_state"), crossing_class=rec.get("crossing_class"),
        key_present=bool(rec.get("key_present")), key_valid=bool(rec.get("key_valid")),
        authority_class=rec.get("authority_class"),
        corroborated=bool(rec.get("corroborated")),
        conflicting_green=bool(rec.get("conflicting_green")),
        second_party_on_green=bool(rec.get("second_party_on_green")),
        claim_key=rec.get("claim_key"))


def _cite(corpus, rule_id: str, why: str) -> dict | None:
    for r in corpus.rules:
        if r.rule_id == rule_id:
            return {"rule_id": r.rule_id, "statute_ref": r.statute_ref,
                    "fault_weight": r.fault_weight, "binding": r.binding,
                    "text": r.text, "why": why}
    return None


def infer_applicable_law(facts: CrashFacts, corpus) -> list:
    """Map VERIFIED incident facts -> applicable KB law rule(s), each cited + reasoned.
    Deterministic; grounded only in the audited facts. Returns a list (most-governing
    first). Never a determination against a person -- a rule-applicability mapping."""
    out: list = []

    def add(rid, why):
        c = _cite(corpus, rid, why)
        if c and c["rule_id"] not in {x["rule_id"] for x in out}:
            out.append(c)

    # 1. Dark signal: the MUST-obey duty falls away; no red-running offence.
    if facts.signal_state == "dark":
        add("LR-dark-signals", "the signal was dark/inoperative at the incident time, so "
            "the duty to obey it falls away (each driver reverts to ordinary care)")
        return out

    # 2. Conflicting green: the system positively created a trap (authority misfeasance).
    if facts.conflicting_green:
        add("LR-authority-misfeasance", "the audit shows the system emitted a conflicting "
            "green (a positively-wrong indication) -- misfeasance, not omission")
        add("LR-authority-nonfeasance", "authority fault otherwise defaults to zero; it "
            "turns non-zero only on this misfeasance/conflicting-green branch "
            "(low-confidence; legal_causation NOT_ASSESSED)")
        return out

    # 3. Amber.
    if facts.signal_state == "amber":
        add("LR-amber", "the vehicle crossed on a steady amber when a safe stop was "
            "possible (same effect as red)")
        return out

    # 4. Crossing on red, by vehicle class.
    if facts.signal_state == "red":
        cls = facts.crossing_class
        if cls in _EMERGENCY and (facts.corroborated or
                                  (facts.key_valid and facts.authority_class == "emergency")):
            add("LR-ev-exemption", "an authorised, corroborated emergency vehicle crossed "
                "red; not at fault merely for crossing (fault only on the endangerment test)")
            add("LR-griffin-calibration", "apportioning the EV-vs-other conflict: the "
                "default anchor is 60/40 against the non-emergency party")
            if facts.second_party_on_green:
                add("LR-green-due-regard", "the other party was on green but must proceed "
                    "with due regard; typically the minority share (Joseph Eva)")
        elif cls == "maintenance":
            add("LR-maintenance-no-exemption", "a highway maintenance/works vehicle is NOT "
                "an emergency vehicle for the red-light exemption; crossing red it is at "
                "fault exactly like an ordinary driver")
            add("LR-driver-red", "crossing the stop line against red is a criminal offence "
                "(TS10); near-conclusive of driver fault")
        else:  # civilian, or an unauthorised vehicle posing as an EV
            add("LR-driver-red", "the vehicle crossed the stop line against a red "
                "indication -- a criminal offence (RTA 1988 s36 / TS10)")
            add("LR-red-prohibition", "the red signal conveys the prohibition that "
                "vehicular traffic must not proceed beyond the stop line")
        if facts.second_party_on_green and cls not in _EMERGENCY:
            add("LR-contrib-negligence", "apportion between the parties per their shares")
        return out

    # 5. A green party involved in a conflict.
    if facts.signal_state == "green":
        add("LR-green-due-regard", "a driver proceeding on green must do so with due "
            "regard to others; typically a minority share against the red-crosser")
        return out

    return out
