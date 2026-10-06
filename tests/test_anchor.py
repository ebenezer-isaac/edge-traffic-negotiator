"""Fault-finding tests for salted-root anchoring + the >=2-witness cross-audit
(src/anchor.py, src/experiment_anchor.py; gate D-anchor).

Written to FAIL if: the salt is cosmetic (root unchanged), a forged-salt inclusion
proof is accepted, the cross-auditor misses an equivocation, a witness silently
overwrites history, or the runner claims external anchoring it did not perform.
"""
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import anchor as an  # noqa: E402
import experiment_anchor as ea  # noqa: E402


_HASHES = tuple(f"{i:064x}" for i in range(1, 6))  # 5 fake entry hashes


# --------------------------------------------------------------------------- #
# 1. Salted root: salt is load-bearing, inclusion proofs verify, forgery fails.
# --------------------------------------------------------------------------- #
def test_salt_changes_the_root():
    a = an.SaltedAnchor.from_hashes(_HASHES, salts=tuple("11" * 32 for _ in _HASHES))
    b = an.SaltedAnchor.from_hashes(_HASHES, salts=tuple("22" * 32 for _ in _HASHES))
    # Different salts -> different published root (salt is applied, not ignored).
    assert a.salted_root != b.salted_root


def test_salted_inclusion_proof_verifies_and_forgery_fails():
    a = an.SaltedAnchor.from_hashes(_HASHES)
    for i in range(len(_HASHES)):
        proof = a.salted_inclusion_proof(i)
        assert an.verify_salted_inclusion(proof, a.salted_root) is True
        # Wrong salt -> proof must FAIL (the salt is required, not cosmetic).
        forged = {**proof, "salt": "00" * 32}
        assert an.verify_salted_inclusion(forged, a.salted_root) is False
        # Wrong entry hash -> fail.
        forged2 = {**proof, "entry_hash": "ab" * 32}
        assert an.verify_salted_inclusion(forged2, a.salted_root) is False


def test_inclusion_against_wrong_root_fails():
    a = an.SaltedAnchor.from_hashes(_HASHES)
    proof = a.salted_inclusion_proof(0)
    assert an.verify_salted_inclusion(proof, "ff" * 32) is False


def test_from_hashes_rejects_empty_and_mismatched_salts():
    with pytest.raises(ValueError):
        an.SaltedAnchor.from_hashes(())
    with pytest.raises(ValueError):
        an.SaltedAnchor.from_hashes(_HASHES, salts=("11" * 32,))  # too few


# --------------------------------------------------------------------------- #
# 2. Witness + cross-audit: consistency, equivocation, quorum, append-only.
# --------------------------------------------------------------------------- #
def test_cross_audit_consistent_when_witnesses_agree(tmp_path):
    wa = an.LocalLedgerWitness("A", str(tmp_path / "a.json"))
    wb = an.LocalLedgerWitness("B", str(tmp_path / "b.json"))
    wa.submit("L", "aa" * 32)
    wb.submit("L", "aa" * 32)
    rep = an.CrossAuditor("x").audit([wa, wb], "L")
    assert rep["quorum_met"] is True
    assert rep["consistent"] is True
    assert rep["equivocation_detected"] is False


def test_cross_audit_detects_equivocation(tmp_path):
    wa = an.LocalLedgerWitness("A", str(tmp_path / "a.json"))
    wr = an.LocalLedgerWitness("R", str(tmp_path / "r.json"))
    wa.submit("L", "aa" * 32)
    wr.submit("L", "bb" * 32)               # a DIFFERENT root: a split view
    rep = an.CrossAuditor("x").audit([wa, wr], "L")
    assert rep["equivocation_detected"] is True
    assert rep["consistent"] is False       # a caught split view is NOT consistent


def test_cross_audit_quorum_not_met_with_one_witness(tmp_path):
    wa = an.LocalLedgerWitness("A", str(tmp_path / "a.json"))
    wa.submit("L", "aa" * 32)
    rep = an.CrossAuditor("x").audit([wa], "L")
    assert rep["quorum_met"] is False       # 1 witness cannot assert non-equivocation
    assert rep["consistent"] is False


def test_witness_is_append_only(tmp_path):
    wa = an.LocalLedgerWitness("A", str(tmp_path / "a.json"))
    wa.submit("L", "aa" * 32)
    wa.submit("L", "aa" * 32)               # same root: idempotent, fine
    with pytest.raises(ValueError):
        wa.submit("L", "bb" * 32)           # different root: rejected (no overwrite)


# --------------------------------------------------------------------------- #
# 3. External-witness probes never raise (SKIP-with-record).
# --------------------------------------------------------------------------- #
def test_besu_probe_skips_with_record_when_no_node():
    info, reason = an.try_besu_witness(rpc_url="http://127.0.0.1:1")
    assert info is None and isinstance(reason, str) and reason


# --------------------------------------------------------------------------- #
# 4. The runner: mechanism passes AND does not overclaim external anchoring.
# --------------------------------------------------------------------------- #
def test_runner_mechanism_passes_and_is_honest_about_external():
    r = ea.run()
    assert r["mechanism_passed"] is True
    assert all(r["mechanism_checks"].values())
    # It performed ZERO public writes -> must NOT claim external anchoring.
    assert r["external_witnesses"]["public_writes_performed"] == 0
    assert r["externally_anchored"] is False
    assert r["d_anchor_status"] == "MECHANISM_PASS_NOT_EXTERNALLY_ANCHORED"
    # The equivocation teeth + salted-root privacy both demonstrated.
    assert r["equivocation_test"]["equivocation_detected"] is True
    assert r["mechanism_checks"]["salt_applied_root_differs"] is True
    assert r["salted_inclusion"]["valid"] is True
    assert r["salted_inclusion"]["forged_salt_valid"] is False
