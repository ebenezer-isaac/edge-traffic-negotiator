"""H2 HEADLINE DEMONSTRATION: the accident-reconstruction demo (MASTER-SPEC §4.4;
gate D-accident, §12).

Scripts an accident on the corridor (a signed PHANTOM advance-claim from a
compromised-but-approved neighbour + a REAL locally-sensed EV incident, staged
by ``system_ev.stage_ev_incident`` against a NAIVE victim), then shows that from
the VERIFIED audit ALONE an investigator can MECHANICALLY reconstruct:

  * WHAT  happened  -- the decision/executed-phase sequence (the phantom
    COMMANDEERS the signal to phase 0 != the MaxPressure baseline; the real EV
    then legitimately preempts phase 0);
  * HOW   it happened -- the signed driving inputs each causal decision consumed
    (``driving_input_seqs``) and the policies that fired;
  * WHICH KEY drove the causal decision -- the ``ev_id`` causal walk attributes
    the phantom commandeering to the SIGNING KEY that claimed it (A1), never a
    person; the real EV is a keyless local sighting (no signing key).

The reconstruction is derived ONLY from records that passed:
  (1) hash-chain verification (``verify_chain``),
  (2) Ed25519 issuer-signature verification (``verify_signatures``),
  (3) a Merkle completeness commitment (root + a sample inclusion proof),
  (4) ``fault_report``'s own gates: driving-input completeness in-window + a
      per-causal-sender ``identity.verify``.
The external QUORUM anchor (>=2 witnesses: Rekor + a ledger RPC) and the NAMED
cross-auditor are the LIVE step gated by D-anchor (a separate phase); this demo
proves the reconstruction over the locally-verifiable completeness commitment and
states that boundary honestly.

TAMPER TEST (the teeth): one causal ``sender_signature`` is substituted with a
valid-FORM signature from a DIFFERENT key (same id label). The hash chain still
verifies (``verify_chain()==True``) and the issuer layer still verifies -- yet
``fault_report`` REFUSES (``UNKNOWN``) because the per-sender ``identity.verify``
catches the substituted signature. A tamper that survives the chain is still
caught; the demo passes only if it is.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import assessment as A  # noqa: E402
from audit_log import AuditLog, verify_inclusion  # noqa: E402
from identity import JunctionIdentity  # noqa: E402
from message_bus import canonical_bytes  # noqa: E402
from system import IntegratedSystem, SystemConfig  # noqa: E402
from system_ev import flatten_entries, stage_ev_incident  # noqa: E402

RESULTS = os.path.normpath(os.path.join(_HERE, "..", "results"))

# The outcome type the phantom false-preemption is filed under (§6.3 cited-rule
# selection is a pure function of this type; it carries NO origin signal).
_PHANTOM_TYPE = "false_preemption"
_REAL_TYPE = "ev_preemption"


def _der_dict(identities: dict) -> dict:
    """sender junction_id -> trusted DER public-key bytes (the registry keys)."""
    return {j: ident.public_key for j, ident in identities.items()}


def _outcome(ev_id, junction: str, t, type_: str) -> dict:
    return {"type": type_, "junction": junction, "t": t, "ev_id": ev_id}


def _verify_layer(audit: AuditLog, der: dict) -> dict:
    """The cryptographic verification the reconstruction stands on. RAISES if the
    chain or the Merkle inclusion proof fails -- the demo must never emit a green
    result over an unverifiable log (§10 golden rule)."""
    n = len(audit)
    chain_ok = audit.verify_chain()
    sig_ok = audit.verify_signatures(der)
    layer: dict = {"entries": n, "verify_chain": chain_ok,
                   "verify_signatures": sig_ok}
    if not chain_ok:
        raise RuntimeError("ACCIDENT DEMO: verify_chain() is False on the staged log")
    if not sig_ok:
        raise RuntimeError("ACCIDENT DEMO: verify_signatures() is False on the staged log")
    root = audit.merkle_root(0, n)
    idx = n - 1
    entry_hash = audit.entries()[idx]["hash"]
    branch = audit.inclusion_proof(idx, 0, n)
    incl = verify_inclusion(entry_hash, branch, root)
    if not incl:
        raise RuntimeError("ACCIDENT DEMO: Merkle inclusion proof invalid")
    layer.update({
        "merkle_root": root,
        "completeness_commitment": "merkle_root + sample inclusion proof",
        "sample_inclusion_index": idx,
        "inclusion_proof_valid": incl,
        "external_quorum_anchor": "DEFERRED to D-anchor (>=2 witnesses: Rekor + "
                                  "ledger RPC) -- live step, not this demo",
        "named_cross_auditor": "DEFERRED to D-anchor (split-view detection)",
    })
    return layer


def _decision_records(records) -> list:
    """The kind:'decision' records in seq order (the WHAT: executed-phase sequence)."""
    ds = [r for r in records if r.get("kind") == "decision"]
    return sorted(ds, key=lambda r: r.get("seq", 0))


def _reconstruct(audit: AuditLog, der: dict, records, outcome: dict) -> dict:
    """Run fault_report for one outcome and extract the what/how/which-key facts."""
    rep = A.fault_report(audit, der, outcome)
    note = rep.get("internal_note") or {}
    pack = rep.get("evidence_pack") or {}
    causal = A._select_causal_decision(records, outcome)
    how = None
    if isinstance(causal, dict):
        how = {
            "causal_decision_seq": causal.get("seq"),
            "executed_phase": causal.get("executed"),
            "driving_input_seqs": causal.get("driving_input_seqs"),
            "policies_applied": causal.get("policies_applied"),
        }
    return {
        "outcome": outcome,
        "status": rep.get("status"),
        "which_key": {
            "origin": note.get("origin"),
            "culprit_key": note.get("culprit_key"),
            "scored_class": note.get("scored_class"),
            "signing_key_count": note.get("signing_key_count"),
            "independent_corroboration_count": note.get("independent_corroboration_count"),
            "rationale": note.get("rationale"),
        },
        "how": how,
        "evidence_pack_is_fact_only": ("candidate_origin" not in pack
                                       and "fault_weight" not in pack),
        "sender_signature_checks": pack.get("sender_signature_checks"),
    }


def _rebuild_with_tampered_sender(audit: AuditLog, identities: dict, tamper_seq: int) -> AuditLog:
    """Re-append every event, substituting ONE causal message's sender_signature
    with a valid-FORM signature from a DIFFERENT key (same id label). Recomputing
    the chain on re-append keeps verify_chain()==True and the issuer layer valid;
    only the per-sender identity.verify can now reject (§6.3)."""
    imposter = JunctionIdentity("A1")  # different key, same id label
    rebuilt = AuditLog()
    for e in audit.entries():
        event = dict(e["event"])
        if e["seq"] == tamper_seq and event.get("kind") == "message":
            sp = event["signed_payload"]
            forged = imposter.sign(
                canonical_bytes(sp["sender"], sp["t"], sp["payload"]))
            event = {**event, "sender_signature": forged.hex()}
        issuer = identities.get(e["issuer"]) if e["issuer"] else None
        rebuilt.append(event, issuer=issuer)
    return rebuilt


def _tamper_test(audit: AuditLog, identities: dict, der: dict, records,
                 phantom_outcome: dict) -> dict:
    """Substitute the causal phantom message's sender signature; prove the tamper
    survives the hash chain but is CAUGHT by the per-sender identity.verify."""
    causal = A._select_causal_decision(records, phantom_outcome)
    if not isinstance(causal, dict) or not causal.get("driving_input_seqs"):
        return {"applicable": False,
                "reason": "no causal decision / driving inputs for the phantom outcome"}
    msg_seq = causal["driving_input_seqs"][0][0]
    tampered = _rebuild_with_tampered_sender(audit, identities, msg_seq)
    chain_still_ok = tampered.verify_chain()
    issuer_still_ok = tampered.verify_signatures(der)
    rep = A.fault_report(tampered, der, phantom_outcome)
    caught = (rep.get("status") == "REFUSED"
              and rep.get("refusal") == A.UNKNOWN
              and (rep.get("internal_note") or {}).get("culprit_key") is None)
    return {
        "applicable": True,
        "tampered_message_seq": msg_seq,
        "verify_chain_after_tamper": chain_still_ok,
        "verify_signatures_after_tamper": issuer_still_ok,
        "fault_report_status": rep.get("status"),
        "refusal": rep.get("refusal"),
        "caught_by_identity_verify": bool(caught),
        "note": ("a substituted sender_signature that KEEPS verify_chain()==True is "
                 "still caught by the per-sender identity.verify -> REFUSED, no "
                 "green attribution"),
    }


def run() -> dict:
    system = IntegratedSystem(SystemConfig())
    staged = stage_ev_incident(system)
    audit = staged["audit"]
    identities = staged["identities"]
    ev = staged["ev_incident"]
    der = _der_dict(identities)
    records = list(flatten_entries(audit))

    verify = _verify_layer(audit, der)

    # WHAT: the executed-phase sequence from the signed decision records.
    decisions = _decision_records(records)
    what = {
        "baseline_phase": ev["baseline"],
        "phantom_executed_phase": ev["phantom_executed"],
        "phantom_commandeered": ev["phantom_executed"] != ev["baseline"],
        "real_executed_phase": ev["real_executed"],
        "real_preempted": ev["real_preempted"],
        "decision_record_count": len(decisions),
        "executed_sequence": [{"seq": d.get("seq"), "junction": d.get("junction"),
                               "executed": d.get("executed"),
                               "classification": d.get("classification")}
                              for d in decisions],
    }

    phantom_outcome = _outcome(ev["phantom_ev_id"], "A0", ev.get("real_tick_t"),
                               _PHANTOM_TYPE)
    real_outcome = _outcome(ev["real_ev_id"], "A0", ev.get("real_tick_t"), _REAL_TYPE)

    recon_phantom = _reconstruct(audit, der, records, phantom_outcome)
    recon_real = _reconstruct(audit, der, records, real_outcome)
    tamper = _tamper_test(audit, identities, der, records, phantom_outcome)

    # D-accident sub-claims -> a single binary pass.
    checks = {
        "verify_chain": verify["verify_chain"] is True,
        "verify_signatures": verify["verify_signatures"] is True,
        "merkle_inclusion_proof": verify["inclusion_proof_valid"] is True,
        "phantom_commandeered_recorded": what["phantom_commandeered"] is True,
        "which_key_attributed_to_signing_key":
            (recon_phantom["status"] == "OK"
             and recon_phantom["which_key"]["origin"] == A.ATTACKER_KEY
             and recon_phantom["which_key"]["culprit_key"] == "A1"),
        "reconstruction_derived_from_verified_records": recon_phantom["status"] == "OK",
        "evidence_pack_is_fact_only": recon_phantom["evidence_pack_is_fact_only"] is True,
        "tamper_caught_by_identity_verify":
            (tamper.get("applicable") is True
             and tamper.get("verify_chain_after_tamper") is True
             and tamper.get("caught_by_identity_verify") is True),
    }
    passed = all(checks.values())

    result = {
        "experiment": "H2_accident_reconstruction_demo",
        "gate": "D-accident (§12) / §4.4",
        "corridor": "2x2 grid fixture (the §6.2 EV-incident staging; the audit "
                    "primitive is corridor-agnostic)",
        "scenario": ("NAIVE victim (corroboration_required=False): a compromised "
                     "neighbour A1 signs a phantom EV advance-claim for a servable "
                     "approach; the naive victim admits it and COMMANDEERS the "
                     "signal off the MaxPressure baseline; a real EV is then sensed "
                     "locally and legitimately preempts."),
        "verification_layer": verify,
        "what_happened": what,
        "how_it_happened": {"phantom": recon_phantom["how"], "real": recon_real["how"]},
        "which_key": {"phantom": recon_phantom["which_key"],
                      "real": recon_real["which_key"]},
        "reconstruction_phantom": recon_phantom,
        "reconstruction_real": recon_real,
        "tamper_test": tamper,
        "checks": checks,
        "passed": passed,
        "caveats": [
            "The external QUORUM anchor (>=2 witnesses: Rekor + ledger RPC) + the "
            "NAMED cross-auditor are the LIVE step gated by D-anchor (a separate "
            "phase); this demo proves reconstruction over the locally-verifiable "
            "completeness commitment (Merkle root + inclusion proof).",
            "The cross-auditor's honesty/independence is an UNVERIFIED assumption "
            "(on par with the identity root), stated not hidden (§4.2).",
            "Origin names a KEY, never a person; the evidence pack states only "
            "mechanically-true facts and does NOT adjudicate legal fault (§7.1).",
        ],
    }

    os.makedirs(RESULTS, exist_ok=True)
    json_path = os.path.join(RESULTS, "experiment_accident.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    md_path = os.path.join(RESULTS, "experiment_accident.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_md(result))
    _print_summary(result, json_path, md_path)
    return result


def render_md(r: dict) -> str:
    v = r["verification_layer"]
    w = r["what_happened"]
    kp = r["which_key"]["phantom"]
    kr = r["which_key"]["real"]
    t = r["tamper_test"]
    lines = ["# H2 headline: the accident-reconstruction demo (D-accident)", ""]
    lines.append(f"**{'PASS' if r['passed'] else 'FAIL'}** -- every D-accident "
                 "sub-claim below is derived from cryptographically-verified records.")
    lines.append("")
    lines.append(f"- Gate: {r['gate']}")
    lines.append(f"- Scenario: {r['scenario']}")
    lines.append("")
    lines.append("## Verification the reconstruction stands on")
    lines.append("")
    lines.append(f"- verify_chain: **{v['verify_chain']}**  |  verify_signatures: "
                 f"**{v['verify_signatures']}**  |  entries: {v['entries']}")
    lines.append(f"- Merkle completeness commitment: root `{str(v.get('merkle_root'))[:16]}...`, "
                 f"sample inclusion proof valid: **{v.get('inclusion_proof_valid')}**")
    lines.append(f"- External quorum anchor + cross-auditor: {v.get('external_quorum_anchor')}")
    lines.append("")
    lines.append("## WHAT happened (executed-phase sequence)")
    lines.append("")
    lines.append(f"- Baseline (MaxPressure) phase: {w['baseline_phase']}")
    lines.append(f"- Phantom tick executed phase: {w['phantom_executed_phase']} "
                 f"-> commandeered off baseline: **{w['phantom_commandeered']}**")
    lines.append(f"- Real-EV tick executed phase: {w['real_executed_phase']} "
                 f"-> preempted: **{w['real_preempted']}**")
    lines.append(f"- Signed decision records: {w['decision_record_count']}")
    lines.append("")
    lines.append("## HOW it happened (driving signed inputs + policies)")
    lines.append("")
    for label, how in (("phantom", r["how_it_happened"]["phantom"]),
                       ("real", r["how_it_happened"]["real"])):
        if how:
            lines.append(f"- {label}: causal decision seq {how['causal_decision_seq']}, "
                         f"executed `{how['executed_phase']}`, driving inputs "
                         f"{how['driving_input_seqs']}, policies {how['policies_applied']}")
        else:
            lines.append(f"- {label}: no causal decision resolved for this outcome")
    lines.append("")
    lines.append("## WHICH KEY drove the causal decision (ev_id causal walk)")
    lines.append("")
    lines.append(f"- Phantom: origin **{kp['origin']}**, culprit key **{kp['culprit_key']}** "
                 f"(signing-key count {kp['signing_key_count']}, independent "
                 f"corroboration {kp['independent_corroboration_count']}) -- names a "
                 "KEY, never a person")
    lines.append(f"- Real EV: origin **{kr['origin']}**, culprit key {kr['culprit_key']} "
                 f"(keyless local sighting: no signing key)")
    lines.append("")
    lines.append("## TAMPER test (the teeth)")
    lines.append("")
    if t.get("applicable"):
        lines.append(f"- Substituted the causal phantom message's sender_signature "
                     f"(seq {t['tampered_message_seq']}) with a different key's valid-form signature")
        lines.append(f"- verify_chain after tamper: **{t['verify_chain_after_tamper']}** "
                     f"(chain still intact) ; issuer layer: {t['verify_signatures_after_tamper']}")
        lines.append(f"- fault_report: **{t['fault_report_status']}** "
                     f"({t['refusal']}) -> caught by identity.verify: "
                     f"**{t['caught_by_identity_verify']}**")
    else:
        lines.append(f"- not applicable: {t.get('reason')}")
    lines.append("")
    lines.append("## D-accident checks")
    lines.append("")
    for k, ok in r["checks"].items():
        lines.append(f"- [{'x' if ok else ' '}] {k}")
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    for c in r["caveats"]:
        lines.append(f"- {c}")
    lines.append("")
    return "\n".join(lines)


def _print_summary(r: dict, json_path: str, md_path: str) -> None:
    print("=" * 72)
    print(f"H2 ACCIDENT-RECONSTRUCTION DEMO (D-accident): {'PASS' if r['passed'] else 'FAIL'}")
    v = r["verification_layer"]
    print(f"  verify_chain={v['verify_chain']} verify_signatures={v['verify_signatures']} "
          f"merkle_inclusion={v.get('inclusion_proof_valid')}")
    kp = r["which_key"]["phantom"]
    print(f"  WHAT: phantom commandeered={r['what_happened']['phantom_commandeered']} "
          f"(executed {r['what_happened']['phantom_executed_phase']} vs baseline "
          f"{r['what_happened']['baseline_phase']}); real preempted="
          f"{r['what_happened']['real_preempted']}")
    print(f"  WHICH KEY: phantom -> origin={kp['origin']} culprit_key={kp['culprit_key']}")
    t = r["tamper_test"]
    print(f"  TAMPER: chain_still_ok={t.get('verify_chain_after_tamper')} "
          f"fault_report={t.get('fault_report_status')} "
          f"caught={t.get('caught_by_identity_verify')}")
    print(f"  checks passed: {sum(1 for x in r['checks'].values() if x)}/{len(r['checks'])}")
    print("=" * 72)
    print(f"  wrote: {json_path}")
    print(f"  wrote: {md_path}")


if __name__ == "__main__":
    res = run()
    raise SystemExit(0 if res["passed"] else 1)
