# anchor.md — the quorum external-anchor + cross-auditor contract

**FROZEN prerequisite artifact** (MASTER-SPEC v7 §6.7, §9, §10, §12 D-anchor). Hash-pinned by the §10 gate. This is the concrete contract the accountability layer's completeness commitment writes to and the fault engine verifies against. Nothing here weakens the honest bound: the quorum anchor makes operator ROLLBACK / SELECTIVE-DISCLOSURE / PER-SIGNER-UNDERCOUNT externally detectable **iff the cross-auditor is honest and reachable**; it does NOT defeat operator CREATION-TIME OMISSION of a never-emitted record, nor a colluding-key coalition — those are the MEASURED boundary (§8), not defended.

---

## 1. What is anchored (per batch)

For each closed audit batch the layer emits a **completeness commitment**:
```
Commitment = { seq_high:int, merkle_root:hex, per_signer_counts:{ key_fpr: emitted_count }, batch_id:str }
```
- `seq_high` = the highest AuditLog envelope seq in the batch (monotonic, append-only).
- `merkle_root` = Merkle root over the batch's entry hashes (proves PRESENCE of any included entry via an inclusion proof; does NOT prove absence — see §5).
- `per_signer_counts` = each signer's OWN first-party signed assertion "I emitted N records this window" (§6.7); a mismatch vs disclosed records is the per-signer-undercount signal.
- Personal data is NEVER in the commitment: `merkle_root` is over hashes of OFF-CHAIN records whose salt is destroyed on erasure (§7.7); the commitment carries no payload, only the root + counts + seqs.

---

## 2. The quorum: ≥2 INDEPENDENT witnesses (operator cannot jointly rewrite)

The commitment is submitted to **at least two independent external witnesses** in different trust domains:

- **W1 — Sigstore Rekor transparency log** (public, append-only, tamper-evident; https://rekor.sigstore.dev). A `rekord`/`intoto` entry carrying the canonicalised `Commitment` JSON. Rekor returns a signed entry with an inclusion proof + a Signed Tree Head (STH); the log is publicly auditable and gossiped, so the operator cannot silently rewrite it. (This is Certificate-Transparency-style; the mechanism is CREDITED to prior art — RFC 6962, Rekor — not claimed novel.)
- **W2 — a named single-node external ledger RPC** (demo scale: a single-node Hyperledger Besu / QBFT instance run by a party OTHER than the signal operator, or a second independent transparency log). Exposes `anchor(commitment) -> receipt` and `get(batch_id) -> commitment` over JSON-RPC. Production would use a multi-validator quorum; the demo single node is honestly labelled "one external witness, not a Byzantine quorum" (§6.7).

**Independence requirement:** W1 and W2 MUST be operable/rewritable only by DISJOINT trust domains, neither of which is the signal operator's admin-key tier. The out-of-scope residual (stated in §1/§13) is an adversary who compromises the issuing admin key AND W1 AND W2 AND the cross-auditor simultaneously.

---

## 3. Submit / verify API (concrete calls)

```
# submit (at batch close, operator-side)
anchor_submit(commitment) -> { w1_receipt: {uuid, sth, inclusion_proof}, w2_receipt: {tx_id, block, sig}, ts }
    - writes `commitment` to BOTH W1 and W2.
    - FAIL-LOUD: if EITHER witness is unreachable / rejects, DO NOT proceed silently.
      Return status="NOT_EXTERNALLY_ANCHORED"; the §10 anchor gate marks the run
      "not externally anchored" and any non-equivocation / conditional-coupling claim
      is REFUSED (never presented green). A mock/in-memory anchor returns this status.

# verify (post-hoc, fault-engine-side, per batch)
anchor_verify(batch_id) -> { w1_ok:bool, w2_ok:bool, agree:bool, commitment }
    - w1_ok  = Rekor inclusion proof + STH verify for the entry.
    - w2_ok  = W2 receipt signature + block-membership verify.
    - agree  = the `Commitment` retrieved from W1 == the one from W2 (byte-canonical).
    - FAIL-LOUD: any of {w1_ok, w2_ok} false, or a witness unreachable -> return
      INCOMPLETE_DISCLOSURE (the batch's completeness is NOT provable) -> fault_report
      refuses an origin determination on any causal window overlapping that batch.
```

---

## 4. The NAMED cross-auditor (split-view / equivocation detection)

**Auditor identity:** a scheduled process `xaudit`, run by a party INDEPENDENT of the signal operator (named in the deployment; its honesty + independence is an UNVERIFIED TRUST ASSUMPTION, on par with the external identity root — stated in §6.7/§13, NOT defended). A single auditor is a WEAKER instantiation than the cited CT multi-auditor gossip (Chuat CNS 2015); production uses ≥2 gossiping auditors.

**xaudit(batch_id) each window:**
1. fetch the `Commitment` from W1 AND from W2 independently.
2. **split-view check:** assert W1.commitment == W2.commitment (byte-canonical). A mismatch = the operator presented DIFFERENT views to the two witnesses = equivocation -> raise `EQUIVOCATION_DETECTED`.
3. **monotonicity check:** assert `seq_high` is non-decreasing across consecutive batches on each witness (no rollback) -> else `ROLLBACK_DETECTED`.
4. **per-signer reconciliation:** for each signer, assert `per_signer_counts[key]` == the number of that signer's records disclosed in the batch. `disclosed < claimed` on a signer's OWN count = that signer under-disclosed (a signer framing itself is nonsensical; an operator dropping a signer's record shows as `disclosed < claimed`); `disclosed > claimed` = a lying signer under-counted, NOT operator suppression (mismatch DIRECTION is defined, §6.7) -> raise `INCOMPLETE_DISCLOSURE` with the direction.
5. gossip the observed (batch_id, W1.root, W2.root) so a later auditor / third party can cross-check (the CT gossip step; single-auditor demo logs it locally + is labelled assumed-honest).

**Without a passing xaudit, non-equivocation is ASSUMED, not enforced** — the §12 D-anchor gate REFUSES to count the coupling claim as anchored unless xaudit ran and passed.

---

## 5. Honest bounds (stated inline; the MEASURED boundary, not defended)

- A Merkle root proves PRESENCE (inclusion), never ABSENCE. So **operator CREATION-TIME OMISSION** (a signer never emits its own incriminating record, and it therefore never enters the batch) is NOT caught by W1/W2/xaudit — it is in the free-deviation boundary (§8), measured, not defended. The per-signer FIRST-PARTY count narrows this only to the extent a signer honestly counts its own emissions.
- **Colluding keys** (k-of-n) produce mutually-consistent records that pass every check — out of scope (§8 boundary).
- The **single-node W2** and **single xaudit** are weaker than a Byzantine quorum + multi-auditor gossip; demo-scale limitation, honestly labelled.
- **Trust relocation:** non-equivocation now rests on (W1 ∧ W2 ∧ xaudit) honesty/independence; identity→entity binding rests on the external identity root (§6.5). Both are unverified assumptions, listed in §13.

---

## 6. Build / demo status

- **Demo-buildable now (free/public):** W1 = a real Rekor entry (public good, no cost); xaudit = a local scheduled job reconciling W1 vs W2. W2 = a single-node Besu in a local container (or a 2nd public transparency log).
- **§10 anchor gate:** any run without a real write to BOTH witnesses + a passing xaudit is labelled "not externally anchored" and its coupling claim is refused (fail-loud) — a mock anchor CANNOT back the claim.
- **OUT of the overnight subset** (§11): the live W1/W2/xaudit integration is its own scoped task; the overnight build uses the in-memory commitment + this contract as the target, labelled not-externally-anchored.
