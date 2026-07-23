"""Multi-scenario crash -> UK-law audit suite (MASTER-SPEC §4 H2; full-scale phase).

A PREDEFINED set of crash scenarios. Each demonstrates a PARTICULAR UK traffic law
that governs the incident. For every scenario the suite:
  1. STAGES the crash as a SIGNED, hash-chained audit record (the mechanically-
     established incident facts: signal state, crossing vehicle class, key/authorisation,
     corroboration, conflicting-green);
  2. VERIFIES the audit (verify_chain + verify_signatures) -- proving the incident record
     is authentic and untampered;
  3. INFERS the applicable UK law directly FROM the verified record (crash_law), citing
     the specific KB rule + statute + the KB fault_weight;
  4. runs a TAMPER test -- a forged issuer signature that keeps the hash-chain valid is
     still caught by verify_signatures, so a doctored incident record cannot pass.

Result: for each scenario we show the explicit audit log, prove it beyond doubt, and
read the governing law off it. It is an EVIDENCE PACK (facts -> which rule governs),
NOT a fault verdict against any person (origin/keys, never names).
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from audit_log import AuditLog  # noqa: E402
from crash_law import CrashFacts, as_record, facts_from_record, infer_applicable_law  # noqa: E402
from identity import JunctionIdentity  # noqa: E402
from legal_corpus import load_corpus  # noqa: E402

RESULTS = os.path.normpath(os.path.join(_HERE, "..", "results"))


# The predefined scenario set: (name, description, facts, expected governing rule).
def _scenarios() -> list:
    return [
        ("civilian_runs_red",
         "A civilian car crosses the stop line against a red indication and collides.",
         CrashFacts(signal_state="red", crossing_class="civilian"),
         "LR-driver-red"),
        ("ambulance_crosses_red_exempt",
         "An authorised, corroborated ambulance crosses red on an emergency run and "
         "conflicts with a car lawfully on green.",
         CrashFacts(signal_state="red", crossing_class="ambulance", key_present=True,
                    key_valid=True, authority_class="emergency", corroborated=True,
                    second_party_on_green=True),
         "LR-ev-exemption"),
        ("maintenance_runs_red",
         "A highway maintenance/works vehicle crosses red; it is NOT an emergency vehicle.",
         CrashFacts(signal_state="red", crossing_class="maintenance", key_present=True,
                    key_valid=True, authority_class="works"),
         "LR-maintenance-no-exemption"),
        ("driver_crosses_on_amber",
         "A driver crosses on a steady amber when a safe stop was possible.",
         CrashFacts(signal_state="amber", crossing_class="civilian"),
         "LR-amber"),
        ("conflicting_green_fault",
         "The signal system emits a conflicting green (a positively-wrong indication); "
         "two movements are released at once.",
         CrashFacts(signal_state="green", crossing_class="civilian",
                    conflicting_green=True),
         "LR-authority-misfeasance"),
        ("dark_signal",
         "The signals are dark/inoperative at the time; a collision occurs at the "
         "junction.",
         CrashFacts(signal_state="dark", crossing_class="civilian"),
         "LR-dark-signals"),
        ("spoofed_ev_triggers_red_run",
         "A compromised-but-approved neighbour signs a PHANTOM ambulance claim that "
         "commandeers the signal; a civilian then crosses the resulting red and "
         "collides. The audit attributes the triggering claim to the signing KEY.",
         CrashFacts(signal_state="red", crossing_class="civilian",
                    claim_key="compromised-neighbour-key"),
         "LR-driver-red"),
    ]


def _stage(facts: CrashFacts, identity: JunctionIdentity, ev_id: str):
    """Build a signed, hash-chained AuditLog holding the incident record."""
    audit = AuditLog()
    audit.append(as_record(facts, identity.junction_id, ev_id, 100.0), issuer=identity)
    return audit


def _tamper_caught(facts: CrashFacts, ev_id: str, pubkeys: dict) -> bool:
    """Re-sign the incident record with a DIFFERENT key (same junction id). The rebuilt
    chain still verifies, but verify_signatures against the registered key must FAIL --
    a doctored incident record is caught."""
    imposter = JunctionIdentity("J")   # same id label, different key
    tampered = AuditLog()
    tampered.append(as_record(facts, "J", ev_id, 100.0), issuer=imposter)
    chain_ok = tampered.verify_chain()
    sigs_ok = tampered.verify_signatures(pubkeys)   # against the REAL key -> should fail
    return chain_ok and (sigs_ok is False)


def run() -> dict:
    corpus = load_corpus()
    identity = JunctionIdentity("J")
    pubkeys = {"J": identity.public_key}
    scenarios = []
    for name, desc, facts, expected in _scenarios():
        ev_id = f"EV-{name}"
        audit = _stage(facts, identity, ev_id)
        chain_ok = audit.verify_chain()
        sigs_ok = audit.verify_signatures(pubkeys)
        rec = audit.entries()[0]["event"]
        verified_facts = facts_from_record(rec)
        laws = infer_applicable_law(verified_facts, corpus)
        law_ids = [l["rule_id"] for l in laws]
        tamper = _tamper_caught(facts, ev_id, pubkeys)
        scenarios.append({
            "name": name, "description": desc,
            "audit_log": [{"seq": e["seq"], "issuer": e["issuer"],
                           "event": e["event"], "hash": e["hash"][:16]}
                          for e in audit.entries()],
            "verify_chain": chain_ok, "verify_signatures": sigs_ok,
            "verified_facts": rec,
            "governing_law": laws,
            "expected_rule": expected,
            "expected_rule_inferred": expected in law_ids,
            "tamper_caught": tamper,
            "proven": bool(chain_ok and sigs_ok and (expected in law_ids) and tamper),
        })
    passed = all(s["proven"] for s in scenarios)
    result = {
        "experiment": "H2_crash_uk_law_audit_suite",
        "n_scenarios": len(scenarios),
        "all_proven": passed,
        "claim": ("for each predefined crash scenario, the signed audit proves the "
                  "incident beyond doubt (chain + signatures verify, a tamper is caught) "
                  "and the governing UK traffic law is inferred directly from the "
                  "verified audit record + cited to the KB."),
        "scenarios": scenarios,
        "note": ("Evidence-pack mapping (audited facts -> which rule governs) with the "
                 "KB's own fault_weight; NOT a determination of fault against a person "
                 "(keys/origins, never names). Law grounding: 01-research/uk-traffic-law.md."),
    }
    os.makedirs(RESULTS, exist_ok=True)
    jp = os.path.join(RESULTS, "experiment_crash_law.json")
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    mp = os.path.join(RESULTS, "experiment_crash_law.md")
    with open(mp, "w", encoding="utf-8") as fh:
        fh.write(render_md(result))
    _print(result, jp, mp)
    return result


def render_md(r: dict) -> str:
    lines = ["# H2: multi-scenario crash -> UK-law audit suite", ""]
    lines.append(f"**{r['n_scenarios']} scenarios, all proven: "
                 f"{'YES' if r['all_proven'] else 'NO'}.** {r['claim']}")
    lines.append("")
    for s in r["scenarios"]:
        gl = s["governing_law"]
        lines.append(f"## {s['name'].replace('_',' ')}")
        lines.append(f"_{s['description']}_")
        lines.append("")
        f = s["verified_facts"]
        lines.append(f"- **Audit record** (seq {s['audit_log'][0]['seq']}, issuer "
                     f"`{s['audit_log'][0]['issuer']}`, hash `{s['audit_log'][0]['hash']}...`): "
                     f"signal=`{f['signal_state']}`, crossing=`{f['crossing_class']}`, "
                     f"key_valid={f['key_valid']}, authority=`{f['authority_class']}`, "
                     f"corroborated={f['corroborated']}, conflicting_green={f['conflicting_green']}"
                     + (f", claim_key=`{f['claim_key']}`" if f.get('claim_key') else ""))
        lines.append(f"- **Proof**: verify_chain=**{s['verify_chain']}**, "
                     f"verify_signatures=**{s['verify_signatures']}**, forged-signature "
                     f"caught=**{s['tamper_caught']}**")
        lines.append(f"- **Governing UK law (inferred from the verified record):**")
        for l in gl:
            lines.append(f"  - `{l['rule_id']}` ({l['statute_ref']}, fault_weight "
                         f"{l['fault_weight']}): {l['text']}")
            lines.append(f"    - why: {l['why']}")
        lines.append(f"- **Proven beyond doubt: {'YES' if s['proven'] else 'NO'}**")
        lines.append("")
    lines.append(f"> {r['note']}")
    lines.append("")
    return "\n".join(lines)


def _print(r, jp, mp):
    print("=" * 70)
    print(f"CRASH -> UK-LAW AUDIT SUITE: {r['n_scenarios']} scenarios, all proven: "
          f"{'YES' if r['all_proven'] else 'NO'}")
    for s in r["scenarios"]:
        gl = ", ".join(l["rule_id"] for l in s["governing_law"])
        print(f"  [{'OK' if s['proven'] else 'XX'}] {s['name']:<32} -> {gl}")
    print("=" * 70)
    print(f"  wrote: {jp}\n  wrote: {mp}")


if __name__ == "__main__":
    res = run()
    raise SystemExit(0 if res["all_proven"] else 1)
