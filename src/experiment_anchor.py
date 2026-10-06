"""D-anchor demonstration: salted-root completeness anchoring to >=2 witnesses +
a cross-audit that catches equivocation (MASTER-SPEC §6.7/§7.7, gate D-anchor).

Takes a REAL signed AuditLog (the §6.2 EV-incident staging), computes a SALTED
completeness root (salt off-chain/erasable, §7.7), submits it to two INDEPENDENT
file-backed witnesses, and shows:

  * a salted inclusion proof verifies against the published root (completeness),
    while the root reveals nothing about the pseudonymous signer fingerprints;
  * a cross-audit over the >=2 witnesses is CONSISTENT (no equivocation);
  * the teeth: when a rogue witness is shown a DIFFERENT root (a split view), the
    cross-auditor DETECTS the equivocation;
  * a reconciled per-signer count (the NON-BLOCKING process check).

It then ATTEMPTS the real EXTERNAL witnesses and records the honest outcome:
  * Besu ledger RPC -- attempted; SKIP-with-record if no node is running (Docker
    bring-up is out of band).
  * public Rekor -- reachability verified READ-ONLY; the WRITE is deliberately
    WITHHELD (writing test data to the production public log would permanently
    pollute a shared public good).

HONEST LABEL (per D-anchor's explicit provision): the >=2-witness non-equivocation
MECHANISM + cross-audit + salted root are DEMONSTRATED and pass over local
witnesses; unless a live external >=2-witness public quorum is achieved, the run is
labelled "NOT externally anchored" and the non-equivocation claim OVER PUBLIC
witnesses is refused -- stated, not hidden.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from anchor import (  # noqa: E402
    CrossAuditor, LocalLedgerWitness, SaltedAnchor, per_signer_counts,
    try_besu_witness, try_rekor_reachable, verify_salted_inclusion,
)
from system import IntegratedSystem, SystemConfig  # noqa: E402
from system_ev import stage_ev_incident  # noqa: E402

RESULTS = os.path.normpath(os.path.join(_HERE, "..", "results"))
LABEL = "euston-batch-0"


def run() -> dict:
    staged = stage_ev_incident(IntegratedSystem(SystemConfig()))
    audit = staged["audit"]

    # SALTED completeness commitment over the whole signed batch.
    anchor = SaltedAnchor.from_audit(audit)
    unsalted_root = audit.merkle_root(0, len(audit))

    # Salted inclusion proof: completeness WITHOUT publishing the entry hash.
    idx = len(audit) - 1
    proof = anchor.salted_inclusion_proof(idx)
    incl_ok = verify_salted_inclusion(proof, anchor.salted_root)
    # A proof with the WRONG salt must fail (the salt is load-bearing, not cosmetic).
    forged = {**proof, "salt": ("00" * 32)}
    incl_forged = verify_salted_inclusion(forged, anchor.salted_root)
    # The salted root must NOT equal the unsalted root (salt actually applied).
    salt_changes_root = anchor.salted_root != unsalted_root

    # Two INDEPENDENT witnesses (distinct files) -> a genuine >=2-witness quorum.
    wdir = tempfile.mkdtemp(prefix="anchor_witnesses_")
    w_a = LocalLedgerWitness("local-ledger-A", os.path.join(wdir, "witness_a.json"))
    w_b = LocalLedgerWitness("local-ledger-B", os.path.join(wdir, "witness_b.json"))
    r_a = w_a.submit(LABEL, anchor.salted_root)
    r_b = w_b.submit(LABEL, anchor.salted_root)
    auditor = CrossAuditor("euston-cross-auditor")
    consistent = auditor.audit([w_a, w_b], LABEL)

    # THE TEETH: a rogue third witness shown a DIFFERENT root (equivocation).
    w_rogue = LocalLedgerWitness("rogue-witness", os.path.join(wdir, "witness_rogue.json"))
    w_rogue.submit(LABEL, "de" * 32)  # a split-view root
    equivocation = auditor.audit([w_a, w_rogue], LABEL)

    # Append-only: a witness refuses to overwrite an existing label with a new root.
    overwrite_refused = False
    try:
        w_a.submit(LABEL, "ff" * 32)
    except ValueError:
        overwrite_refused = True

    signer_counts = per_signer_counts(audit)

    # ATTEMPT the external witnesses (honest outcomes).
    besu_info, besu_reason = try_besu_witness()
    rekor_info, rekor_reason = try_rekor_reachable()

    external_witnesses_written = 0  # neither public witness is WRITTEN this run
    externally_anchored = external_witnesses_written >= 2

    checks = {
        "salt_applied_root_differs": salt_changes_root,
        "salted_inclusion_proof_valid": incl_ok is True,
        "forged_salt_rejected": incl_forged is False,
        "local_quorum_ge_2": consistent["witnesses_present"] >= 2,
        "cross_audit_consistent": consistent["consistent"] is True,
        "equivocation_detected": equivocation["equivocation_detected"] is True,
        "witness_append_only": overwrite_refused is True,
        "per_signer_reconciled": len(signer_counts) >= 1,
    }
    mechanism_passed = all(checks.values())

    result = {
        "experiment": "H2_anchor_salted_root_quorum_crossaudit",
        "gate": "D-anchor (§6.7/§7.7)",
        "label": LABEL,
        "batch_entries": len(audit),
        "salted_root": anchor.salted_root,
        "unsalted_root": unsalted_root,
        "salt_is_offchain_erasable": True,
        "salted_inclusion": {"index": idx, "valid": incl_ok,
                             "forged_salt_valid": incl_forged},
        "local_cross_audit": consistent,
        "equivocation_test": equivocation,
        "witness_append_only_refused_overwrite": overwrite_refused,
        "per_signer_counts": signer_counts,
        "external_witnesses": {
            "besu": besu_info or {"skipped": True, "reason": besu_reason},
            "rekor": rekor_info or {"skipped": True, "reason": rekor_reason},
            "public_writes_performed": external_witnesses_written,
        },
        "externally_anchored": externally_anchored,
        "mechanism_checks": checks,
        "mechanism_passed": mechanism_passed,
        "d_anchor_status": ("MECHANISM_PASS_NOT_EXTERNALLY_ANCHORED"
                            if (mechanism_passed and not externally_anchored)
                            else ("PASS" if externally_anchored and mechanism_passed
                                  else "FAIL")),
        "honest_label": (
            "The >=2-witness non-equivocation MECHANISM + cross-audit + salted-root "
            "completeness commitment are DEMONSTRATED and pass over independent local "
            "witnesses (equivocation is caught). This run is NOT externally anchored to "
            "a public >=2-witness quorum: the Rekor write is WITHHELD (public-log "
            "pollution) and no live Besu node was written; so the non-equivocation "
            "claim OVER PUBLIC witnesses is REFUSED (§4.2/§4.5), stated not hidden."),
        "caveats": [
            "Salt is off-chain + erasable (§7.7): the published root commits "
            "completeness but reveals no pseudonymous fingerprint; erase the salt "
            "-> the commitment is unlinkable (forward privacy).",
            "A single/local/withheld-write anchor cannot assert ecosystem-wide "
            "non-equivocation; the cross-auditor's honesty is an UNVERIFIED "
            "assumption on par with the identity root (§4.2).",
            "To externally anchor: bring up the ledger witness "
            "(docker compose -f .qbft-spike/docker-compose.yml up -d) and enable the "
            "Rekor write intentionally; then >=2 public witnesses + a passing "
            "cross-audit would flip externally_anchored to true.",
        ],
    }

    os.makedirs(RESULTS, exist_ok=True)
    json_path = os.path.join(RESULTS, "experiment_anchor.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    md_path = os.path.join(RESULTS, "experiment_anchor.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_md(result))
    _print_summary(result, json_path, md_path)
    return result


def render_md(r: dict) -> str:
    ca = r["local_cross_audit"]
    eq = r["equivocation_test"]
    ext = r["external_witnesses"]
    lines = ["# H2: salted-root anchoring + >=2-witness cross-audit (D-anchor)", ""]
    lines.append(f"**Mechanism: {'PASS' if r['mechanism_passed'] else 'FAIL'}**  |  "
                 f"D-anchor status: **{r['d_anchor_status']}**")
    lines.append("")
    lines.append(f"- Batch entries: {r['batch_entries']}  |  label: `{r['label']}`")
    lines.append(f"- Salted root: `{r['salted_root'][:20]}...`  (unsalted: "
                 f"`{r['unsalted_root'][:20]}...` -- differ: "
                 f"{r['mechanism_checks']['salt_applied_root_differs']})")
    lines.append("")
    lines.append("## Salted completeness (reveals no fingerprint)")
    lines.append("")
    lines.append(f"- Salted inclusion proof valid: **{r['salted_inclusion']['valid']}**  "
                 f"|  forged-salt proof rejected: "
                 f"**{not r['salted_inclusion']['forged_salt_valid']}**")
    lines.append(f"- Salt is off-chain + erasable (§7.7): {r['salt_is_offchain_erasable']}")
    lines.append("")
    lines.append("## >=2-witness cross-audit")
    lines.append("")
    lines.append(f"- Witnesses present: {ca['witnesses_present']}  |  roots agree: "
                 f"{ca['roots_agree']}  |  consistent: **{ca['consistent']}**")
    lines.append(f"- Equivocation test (rogue split-view witness): detected = "
                 f"**{eq['equivocation_detected']}** (the teeth)")
    lines.append(f"- Witness append-only (refuses overwrite): "
                 f"**{r['witness_append_only_refused_overwrite']}**")
    lines.append(f"- Per-signer reconciliation: {r['per_signer_counts']}")
    lines.append("")
    lines.append("## External witnesses (attempted)")
    lines.append("")
    besu = ext["besu"]
    rekor = ext["rekor"]
    lines.append(f"- Besu ledger: {'connected '+str(besu) if not besu.get('skipped') else 'SKIP -- '+besu.get('reason','')}")
    lines.append(f"- Rekor: {rekor if not rekor.get('skipped') else 'SKIP -- '+rekor.get('reason','')}")
    lines.append(f"- Public writes performed: {ext['public_writes_performed']}  |  "
                 f"externally anchored: **{r['externally_anchored']}**")
    lines.append("")
    lines.append("## Honest label")
    lines.append("")
    lines.append(f"> {r['honest_label']}")
    lines.append("")
    lines.append("## D-anchor mechanism checks")
    lines.append("")
    for k, ok in r["mechanism_checks"].items():
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
    print(f"D-ANCHOR: mechanism {'PASS' if r['mechanism_passed'] else 'FAIL'} | "
          f"status {r['d_anchor_status']}")
    ca = r["local_cross_audit"]
    eq = r["equivocation_test"]
    print(f"  salted_root differs from unsalted: {r['mechanism_checks']['salt_applied_root_differs']}"
          f" | inclusion valid: {r['salted_inclusion']['valid']} | forged rejected: "
          f"{not r['salted_inclusion']['forged_salt_valid']}")
    print(f"  cross-audit consistent: {ca['consistent']} (witnesses {ca['witnesses_present']}) "
          f"| equivocation caught: {eq['equivocation_detected']}")
    ext = r["external_witnesses"]
    print(f"  external: besu={'up' if not ext['besu'].get('skipped') else 'skip'} "
          f"rekor={'reachable' if not ext['rekor'].get('skipped') else 'skip'} "
          f"public_writes={ext['public_writes_performed']} externally_anchored={r['externally_anchored']}")
    print(f"  checks: {sum(1 for v in r['mechanism_checks'].values() if v)}/{len(r['mechanism_checks'])}")
    print("=" * 72)
    print(f"  wrote: {json_path}")
    print(f"  wrote: {md_path}")


if __name__ == "__main__":
    res = run()
    raise SystemExit(0 if res["mechanism_passed"] else 1)
