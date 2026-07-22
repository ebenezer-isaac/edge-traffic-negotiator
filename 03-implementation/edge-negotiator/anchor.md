# anchor.md — the quorum external-anchor + cross-auditor contract

**FROZEN prerequisite artifact** (MASTER-SPEC v7 §6.7, §9, §10, §12 D-anchor). Hash-pinned by the §10 gate. This is the concrete contract the accountability layer's completeness commitment writes to and the fault engine verifies against.

**What is soundly DETECTED (in-scope, given honest+reachable witnesses+auditor):** operator EQUIVOCATION (split-view across witnesses) and ROLLBACK / SEQ-GAP of already-anchored, already-chained records. **What is only MEASURED / SURFACED, never ATTRIBUTED (the §8 boundary, not defended):** per-signer disclosure mismatches (a `disclosed ≠ signer-signed-claimed` count is provenance-INDISTINGUISHABLE between an operator drop and a signer lying about its own count, so it raises a conservative `INCOMPLETE_DISCLOSURE` flag for a HUMAN inquiry, and CANNOT be attributed to the operator); **out of reach entirely:** operator CREATION-TIME OMISSION of a never-emitted record, and a colluding-key coalition. The mechanism is Certificate-Transparency-style (RFC 6962 / Rekor / CONIKS / Chuat CNS 2015) — CREDITED to prior work, not claimed novel.

---

## 1. What is anchored (per batch)

The layer emits a per-batch **completeness commitment**, split across the two witnesses by data-protection sensitivity:

- **Public part (to W1, Rekor)** — carries NO personal data:
  `PubCommit = { batch_id:str, seq_low:int, seq_high:int, merkle_root:hex }`
  `seq_low..seq_high` is the CONTIGUOUS envelope-seq range covered (the AuditLog assigns seqs contiguously, so a gap is an anomaly); `merkle_root` is over the batch's entry hashes (proves PRESENCE via an inclusion proof; NOT absence — §5).
- **Restricted part (to W2 only, access-controlled ledger)** — pseudonymous, NOT on the public log:
  `RestrictedCommit = { batch_id, seq_low, seq_high, merkle_root, signer_counts:[ {key_fpr, emitted_count, signer_sig} ] }`
  where each `signer_sig` is that signer's OWN signature over `(batch_id, key_fpr, emitted_count)`. The operator CANNOT forge `signer_sig` (it lacks the signer's key), so a signer's claimed count is non-repudiable — but see §4.4: a mismatch is still inconclusive.

**GDPR (reconciles §7.7):** the PUBLIC W1 anchor holds ONLY `{batch_id, seq_low, seq_high, merkle_root}` — no `key_fpr`, no counts, no direct identifiers, so nothing pseudonymously re-linkable is on the immutable public log. `key_fpr` + counts (pseudonymous personal data under Art 4(5), re-linkable via enrolment provenance) live ONLY on the ACCESS-CONTROLLED W2 under the project's bounded-retention + DPIA regime (§7.7); they are NOT immutable/un-erasable. The merkle_root is over off-chain hashes whose salt is destroyed on erasure (§7.7).

---

## 2. The quorum: ≥2 INDEPENDENT witnesses (operator cannot jointly rewrite)

- **W1 — Sigstore Rekor transparency log** (public; https://rekor.sigstore.dev): an entry carrying `PubCommit`. Rekor returns a signed entry + inclusion proof + Signed Tree Head; publicly auditable + gossiped, so the operator cannot silently rewrite it.
- **W2 — a named single-node external ledger RPC** (demo: a single-node Hyperledger Besu/QBFT run by a party OTHER than the signal operator; production: a multi-validator quorum): `RestrictedCommit` via `anchor()/get()`. **"single-node" here = a single external WITNESS's internal validator count; it is one of the ≥2 witnesses, NOT the §10 "single-node anchor" (= a lone witness) that is refused.** Honestly labelled: one external witness, not a Byzantine quorum.

**Independence:** W1 and W2 rewritable only by DISJOINT trust domains, neither the operator's admin-key tier. Out-of-scope residual (§1/§13): an adversary compromising the admin key AND W1 AND W2 AND xaudit simultaneously.

**NEW record-kind dependency:** the signer-signed `signer_count` assertion is a NEW signed record kind NOT in the §11 schema set and NOT produced by the current code — it is part of the scoped anchor-integration build phase (§11), alongside W1/W2/xaudit. The DISCLOSED-side count (a signer's actual records) is realizable now via `AuditLog.entries()` filtered on `sender_pubkey_fpr`; `merkle_root`/`seq` are realizable via the existing `AuditLog.merkle_root(start,end)` / `inclusion_proof` / contiguous per-entry `seq`.

---

## 3. Submit / verify API

```
anchor_submit(pub_commit, restricted_commit) -> { w1_receipt:{uuid,sth,inclusion_proof}, w2_receipt:{tx_id,block,sig}, ts }
    - writes pub_commit to W1, restricted_commit to W2.
    - FAIL-LOUD: if EITHER witness is unreachable/rejects -> status="NOT_EXTERNALLY_ANCHORED";
      the §10 anchor gate marks the run "not externally anchored" and REFUSES any
      non-equivocation / conditional-coupling claim (never green). A mock/in-memory
      anchor returns this status.

anchor_verify(batch_id) -> { w1_ok, w2_ok, agree, pub_commit }
    - w1_ok = Rekor inclusion proof + STH verify; w2_ok = W2 receipt sig + block-membership verify.
    - agree = the SHARED fields (batch_id, seq_low, seq_high, merkle_root) retrieved from W1 ==
      those in W2's RestrictedCommit, compared by the canonical scheme _canonical_json
      (sort_keys, separators=(",",":"), allow_nan=False; = audit_log.py's scheme).
    - FAIL-LOUD: any of {w1_ok,w2_ok} false, or a witness unreachable, or a batch present on
      one witness but ABSENT on the other -> INCOMPLETE_DISCLOSURE (completeness NOT provable)
      -> fault_report refuses an origin determination on any causal window overlapping the batch.
```

---

## 4. The NAMED cross-auditor (xaudit) — equivocation/rollback detection + a per-signer INSTRUMENT

**Auditor:** a scheduled process `xaudit`, run by a party INDEPENDENT of the signal operator (named in the deployment; its honesty + independence is an UNVERIFIED TRUST ASSUMPTION, on par with the external identity root, §6.5/§13 — NOT defended). A single xaudit is WEAKER than the cited CT multi-auditor gossip (Chuat CNS 2015); production uses ≥2 gossiping auditors, cross-checking each other. The single-auditor demo's "gossip" is a local append-only record that a LATER independent auditor/third party can replay — it provides no self-cross-check on its own (stated, not relied on).

**xaudit(batch_id) each window:**
1. fetch `PubCommit` from W1 AND the shared fields of `RestrictedCommit` from W2 independently.
2. **split-view (SOUND, in-scope DETECTION):** assert the shared fields agree byte-canonically; a mismatch = the operator showed DIFFERENT views to W1 vs W2 = `EQUIVOCATION_DETECTED`. A `batch_id` present on one witness but absent on the other is likewise `EQUIVOCATION_DETECTED` (not "undefined").
3. **monotone + CONTIGUOUS seq (SOUND, in-scope DETECTION of rollback/gap):** across consecutive batches assert `seq_low(next) == seq_high(prev)+1` (contiguous) AND monotone non-decreasing; a gap or overlap = `ROLLBACK_OR_GAP_DETECTED` (an already-anchored/already-chained record range was removed — detectable, though not attributable to a specific party without more). This closes the batch-drop/seq-gap hole.
4. **per-signer reconciliation (a MEASURED INSTRUMENT, NOT an in-scope detection):** enumerate the EXPECTED signer roster from an operator-INDEPENDENT enrolment source (the §6.5 identity root), so an operator cannot hide a signer by omitting its count row. For each expected signer: verify `signer_sig` over `(batch_id,key_fpr,emitted_count)` (the operator cannot forge it); then compare `emitted_count` (signer-signed) vs `disclosed` (that signer's records in the batch). **A mismatch in EITHER direction is INCONCLUSIVE and NON-ATTRIBUTING (aligns with §6.7):** `disclosed < emitted_count` is consistent with EITHER an operator drop OR a lone signer inflating its own signed count to frame the operator; `disclosed > emitted_count` is consistent with EITHER a lying signer under-counting OR an operator replaying a signer's validly-signed record (the §6.6 nonce covers claims, not sightings). So it raises a conservative `INCOMPLETE_DISCLOSURE` flag for a HUMAN inquiry and CANNOT attribute suppression to the operator — the per-signer channel INSTRUMENTS the out-of-scope operator boundary (§6.7), it does not detect within scope.
5. gossip `(batch_id, W1.root, W2.root, seq_range)` for a later independent auditor to replay.

**Without a passing xaudit (equivocation + contiguity clean), non-equivocation is ASSUMED, not enforced** — the §12 D-anchor gate REFUSES to count the coupling claim as anchored.

---

## 5. Honest bounds (the MEASURED boundary, stated inline; not defended)

- Merkle root proves PRESENCE, never ABSENCE, so **operator CREATION-TIME OMISSION** (a signer never emits its own incriminating record; it never enters the batch, the seq range is still contiguous, no signer-signed count over-claims it) is OUT OF REACH — in the §8 free-deviation boundary, measured not defended.
- **Per-signer disclosure mismatch is INCONCLUSIVE** (operator-drop vs signer-lie, both directions, §4.4) — surfaced, never attributed to the operator.
- **Colluding keys** (k-of-n) produce mutually-consistent records that pass every check — out of scope (§8 boundary).
- **Single-node W2 + single xaudit** are weaker than a Byzantine quorum + multi-auditor gossip — demo limitation, honestly labelled.
- **Trust relocation:** non-equivocation rests on (W1 ∧ W2 ∧ xaudit) honesty/independence; identity→entity binding rests on the external identity root (§6.5). Both are UNVERIFIED assumptions, listed in §13.

---

## 6. Build / demo status + the §10 gate

- **Demo-buildable (free/public):** W1 = a real Rekor entry (public, no cost); W2 = a single-node Besu in a local container run by a distinct party (concrete endpoint/party is a deployment placeholder, an unverified trust assumption like the §6.5 identity-root certifier); xaudit = a local scheduled job.
- **§10 / §12 D-anchor gate — THREE conditions, named explicitly (matching §10/§12):** (i) a real write to BOTH witnesses; (ii) a per-signer reconciliation that verifies SIGNER-SIGNED counts against the independent enrolment roster (NOT a bare operator-supplied match — an operator gaming its own counts must NOT pass); (iii) a PASSING xaudit (equivocation + contiguity clean). Absent any of the three, the run is labelled "not externally anchored" and the coupling claim is REFUSED. A mock/single-witness/un-cross-audited anchor CANNOT back the claim.
- **OUT of the overnight subset** (§11): the live W1/W2/xaudit integration + the signer-signed-count record kind + the completeness-commitment/merkle-root wiring are their own scoped tasks; the overnight build uses the in-memory commitment + this contract as the target, labelled not-externally-anchored.
