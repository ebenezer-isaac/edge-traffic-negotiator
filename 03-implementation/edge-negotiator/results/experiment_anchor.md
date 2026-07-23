# H2: salted-root anchoring + >=2-witness cross-audit (D-anchor)

**Mechanism: PASS**  |  D-anchor status: **MECHANISM_PASS_NOT_EXTERNALLY_ANCHORED**

- Batch entries: 12  |  label: `euston-batch-0`
- Salted root: `8f1f71820d89aca074fc...`  (unsalted: `4d54e829fd607db54575...` -- differ: True)

## Salted completeness (reveals no fingerprint)

- Salted inclusion proof valid: **True**  |  forged-salt proof rejected: **True**
- Salt is off-chain + erasable (§7.7): True

## >=2-witness cross-audit

- Witnesses present: 2  |  roots agree: True  |  consistent: **True**
- Equivocation test (rogue split-view witness): detected = **True** (the teeth)
- Witness append-only (refuses overwrite): **True**
- Per-signer reconciliation: {'A0': 8, 'A1': 1, 'B0': 1, 'B1': 1, '<unsigned>': 1}

## External witnesses (attempted)

- Besu ledger: SKIP -- Besu RPC http://127.0.0.1:8545 not reachable (node not running). Start it: docker compose -f .qbft-spike/docker-compose.yml up -d
- Rekor: {'url': 'https://rekor.sigstore.dev/api/v1/log', 'tree_size': 2099218962, 'root_hash': '3c00de56a3b66180', 'write': 'WITHHELD (would permanently publish to the public log)'}
- Public writes performed: 0  |  externally anchored: **False**

## Honest label

> The >=2-witness non-equivocation MECHANISM + cross-audit + salted-root completeness commitment are DEMONSTRATED and pass over independent local witnesses (equivocation is caught). This run is NOT externally anchored to a public >=2-witness quorum: the Rekor write is WITHHELD (public-log pollution) and no live Besu node was written; so the non-equivocation claim OVER PUBLIC witnesses is REFUSED (§4.2/§4.5), stated not hidden.

## D-anchor mechanism checks

- [x] salt_applied_root_differs
- [x] salted_inclusion_proof_valid
- [x] forged_salt_rejected
- [x] local_quorum_ge_2
- [x] cross_audit_consistent
- [x] equivocation_detected
- [x] witness_append_only
- [x] per_signer_reconciled

## Caveats

- Salt is off-chain + erasable (§7.7): the published root commits completeness but reveals no pseudonymous fingerprint; erase the salt -> the commitment is unlinkable (forward privacy).
- A single/local/withheld-write anchor cannot assert ecosystem-wide non-equivocation; the cross-auditor's honesty is an UNVERIFIED assumption on par with the identity root (§4.2).
- To externally anchor: bring up the ledger witness (docker compose -f .qbft-spike/docker-compose.yml up -d) and enable the Rekor write intentionally; then >=2 public witnesses + a passing cross-audit would flip externally_anchored to true.
