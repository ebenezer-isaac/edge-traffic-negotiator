# H2 headline: the accident-reconstruction demo (D-accident)

**PASS** -- every D-accident sub-claim below is derived from cryptographically-verified records.

- Gate: D-accident (§12) / §4.4
- Scenario: NAIVE victim (corroboration_required=False): a compromised neighbour A1 signs a phantom EV advance-claim for a servable approach; the naive victim admits it and COMMANDEERS the signal off the MaxPressure baseline; a real EV is then sensed locally and legitimately preempts.

## Verification the reconstruction stands on

- verify_chain: **True**  |  verify_signatures: **True**  |  entries: 12
- Merkle completeness commitment: root `21ca3e487ba3a612...`, sample inclusion proof valid: **True**
- External quorum anchor + cross-auditor: DEFERRED to D-anchor (>=2 witnesses: Rekor + ledger RPC) -- live step, not this demo

## WHAT happened (executed-phase sequence)

- Baseline (MaxPressure) phase: 1
- Phantom tick executed phase: 0 -> commandeered off baseline: **True**
- Real-EV tick executed phase: 0 -> preempted: **True**
- Signed decision records: 4

## HOW it happened (driving signed inputs + policies)

- phantom: causal decision seq 7, executed `0`, driving inputs [[6, 'A1']], policies ['corroboration']
- real: causal decision seq 11, executed `0`, driving inputs [[10, None]], policies ['corroboration']

## WHICH KEY drove the causal decision (ev_id causal walk)

- Phantom: origin **attacker-key**, culprit key **A1** (signing-key count 1, independent corroboration 0) -- names a KEY, never a person
- Real EV: origin **sensor-fed-spoof**, culprit key None (keyless local sighting: no signing key)

## TAMPER test (the teeth)

- Substituted the causal phantom message's sender_signature (seq 6) with a different key's valid-form signature
- verify_chain after tamper: **True** (chain still intact) ; issuer layer: True
- fault_report: **REFUSED** (unknown) -> caught by identity.verify: **True**

## D-accident checks

- [x] verify_chain
- [x] verify_signatures
- [x] merkle_inclusion_proof
- [x] phantom_commandeered_recorded
- [x] which_key_attributed_to_signing_key
- [x] reconstruction_derived_from_verified_records
- [x] evidence_pack_is_fact_only
- [x] tamper_caught_by_identity_verify

## Caveats

- The external QUORUM anchor (>=2 witnesses: Rekor + ledger RPC) + the NAMED cross-auditor are the LIVE step gated by D-anchor (a separate phase); this demo proves reconstruction over the locally-verifiable completeness commitment (Merkle root + inclusion proof).
- The cross-auditor's honesty/independence is an UNVERIFIED assumption (on par with the identity root), stated not hidden (§4.2).
- Origin names a KEY, never a person; the evidence pack states only mechanically-true facts and does NOT adjudicate legal fault (§7.1).
