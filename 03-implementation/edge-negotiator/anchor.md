# anchor.md — the quorum external-anchor + cross-auditor contract

**FROZEN prerequisite artifact** (MASTER-SPEC v7 §6.7, §9, §10, §12 D-anchor). Hash-pinned by the §10 gate. The concrete contract the accountability layer's completeness commitment writes to and the fault engine verifies against.

**What is soundly DETECTED (in-scope, given honest+reachable+FINAL witnesses+auditor):** operator EQUIVOCATION (split-view across witnesses) and ROLLBACK / SEQ-GAP of already-anchored, already-chained records (under the single-global-seq assumption, §4.3 / §4 step 3). **What is only MEASURED / SURFACED, never ATTRIBUTED, never gate-blocking (the §8 boundary, not defended):** per-signer disclosure mismatches — a `disclosed ≠ signer-signed-claimed` count is provenance-INDISTINGUISHABLE between an operator drop and a signer lying about its own count (BOTH directions), so it raises a conservative `INCOMPLETE_DISCLOSURE` flag for a HUMAN inquiry and CANNOT be attributed to the operator, nor does it fail the anchor gate (else a lone lying signer could DoS the operator's true non-equivocation claim). **Out of reach entirely:** operator CREATION-TIME OMISSION of a never-emitted record, and a colluding-key coalition. Mechanism = Certificate-Transparency-style (RFC 6962 / Rekor / CONIKS / Chuat CNS 2015), CREDITED to prior work, not claimed novel.

---

## 1. What is anchored (per batch)

- **The witnessed completeness commitment (to BOTH W1 and W2) — provably non-re-linkable without the off-chain salt:**
  `Commit = { batch_id:str, seq_low:int, seq_high:int, salted_root:hex }`
  `seq_low..seq_high` = the CONTIGUOUS envelope-seq range the batch covers (the single-instance AuditLog assigns global seqs contiguously and `verify_chain` enforces it, so a gap/overlap is an anomaly, §4.3); `salted_root` = the Merkle root over KEYED/SALTED leaf commitments, one per entry, where each leaf = `HMAC(salt, entry_body)` and the per-batch `salt` is held ONLY in the erasable off-chain store (the §7.7 mechanism). Without the salt the root + any inclusion proof are provably non-re-linkable to a person, so the immutable witness carries NO re-linkable personal data; WITH the salt (held by the operator during bounded retention) an inclusion proof still proves PRESENCE, NOT absence (§5). This is ALL that is witnessed — the quorum's job is to make the SALTED-ROOT + SEQ-RANGE non-equivocable.
- **The per-signer emission counts — OFF-CHAIN, access-controlled, ERASABLE (NOT on any witness/ledger):**
  `SignerCounts = [ {key_fpr, emitted_count, signer_sig} ]` where `signer_sig` is that signer's OWN signature over `(batch_id, key_fpr, emitted_count)` (the operator cannot forge it — it lacks the signer's key). Stored in the restricted off-chain store under the project's bounded-retention + DPIA regime, so Art 17 erasure is feasible. These INSTRUMENT the out-of-scope operator boundary (§6.7); they are NOT witnessed and NOT required to be (§6.7 never requires the counts to be anchored).

**GDPR (implements §7.7, not a substitute):** neither immutable witness (W1 public Rekor, W2 ledger) carries `key_fpr`, counts, or any direct/pseudonymous identifier — only `{batch_id, seq_low, seq_high, salted_root}`. The `key_fpr` + counts (pseudonymous personal data, Art 4(5)) AND the per-batch `salt` live ONLY in the erasable off-chain store. Re-linkage protection is the §7.7 SALT, not source-minimisation: because entry bodies carry `sender_pubkey_fpr` (§6.1/§6.2), an unsalted root would immutably commit to pseudonymous personal data on a public log (Rekor) — which is exactly why §7.7 mandates the salt. **The current `AuditLog.merkle_root` (audit_log.py:298) folds UNSALTED entry hashes and is therefore NOT the witnessed root; the salted-leaf commitment is a NEW mechanism wired in the scoped anchor-integration phase (§11, out of the overnight subset), not the existing method.** Art 17: the immutable root cannot be deleted, but crypto-erasure of the off-chain `salt` renders it + all its inclusion proofs permanently non-re-linkable (Art 17(3) + DPIA-recorded residual re-linkability while the salt is retained, §7.7).

---

## 2. The quorum: ≥2 INDEPENDENT witnesses (operator cannot jointly rewrite)

Both witnesses anchor the SAME `Commit` (root + seq-range; no personal data):
- **W1 — Sigstore Rekor transparency log** (public; https://rekor.sigstore.dev): an entry carrying `Commit`; returns a signed entry + inclusion proof + Signed Tree Head; publicly auditable + gossiped, so the operator cannot silently rewrite it.
- **W2 — a named single-node external ledger RPC** (demo: a single-node Hyperledger Besu/QBFT run by a party OTHER than the signal operator; production: a multi-validator quorum): `Commit` via `anchor()/get()`. **"single-node" = this witness's internal validator count; W2 is one of the ≥2 WITNESSES, NOT the §10 "single-node anchor" (= a lone witness) that is refused.** Honestly labelled: one external witness, not a Byzantine quorum.

**Independence:** W1 and W2 rewritable only by DISJOINT trust domains, neither the operator's admin-key tier. Out-of-scope residual (§1/§13): an adversary compromising the admin key AND W1 AND W2 AND xaudit simultaneously.

**NEW dependencies (scoped to the §11 anchor-integration phase, not in the current code):** the SALTED-leaf `salted_root` commitment (the current `AuditLog.merkle_root` is unsalted, §1 — NOT the witnessed root); the off-chain salt + `SignerCounts` record kind (not in the §11 schema set); the off-chain restricted store; W1/W2/xaudit integration. Realizable NOW as scaffolding (NOT yet the witnessed root): `AuditLog.merkle_root(start,end)` / `inclusion_proof` / contiguous per-entry global `seq` exist; the DISCLOSED-side count (a signer's actual records) is `AuditLog.entries()` filtered on `sender_pubkey_fpr`.

---

## 3. Submit / verify API

```
anchor_submit(commit, salt, signer_counts) -> { w1_receipt:{uuid,sth,inclusion_proof}, w2_receipt:{tx_id,block,sig}, ts }
    - writes `commit` (salted_root+seqs, no re-linkable personal data) to W1 AND W2; writes the
      per-batch `salt` AND `signer_counts` to the OFF-CHAIN erasable store (never to any witness).
    - FAIL-LOUD: if EITHER witness is unreachable/rejects -> status="NOT_EXTERNALLY_ANCHORED";
      the §10 anchor gate marks the run "not externally anchored" and REFUSES any non-equivocation
      / conditional-coupling claim (never green). A mock/in-memory anchor returns this status.
    - EMPTY-WINDOW: a batch with no new entries emits NO commit (AuditLog.merkle_root raises on an
      empty range); xaudit treats a legitimately-empty window as skip-with-record (seq_high carries
      unchanged), NOT a one-sided-absence anomaly.

anchor_verify(batch_id) -> { w1_ok, w2_ok, agree, commit }
    - w1_ok = Rekor inclusion proof + STH verify; w2_ok = W2 receipt sig + block-membership verify.
    - agree = the `Commit` from W1 == the `Commit` from W2, compared by _canonical_json
      (sort_keys, separators=(",",":"), allow_nan=False; = audit_log.py's scheme).
    - FAIL-LOUD: any of {w1_ok,w2_ok} false, or a witness UNREACHABLE (a reachability failure, not
      necessarily equivocation) -> INCOMPLETE_DISCLOSURE (completeness not provable) -> fault_report
      refuses an origin determination on any causal window overlapping the batch.
```

---

## 4. The NAMED cross-auditor (xaudit)

**Auditor:** a scheduled process `xaudit`, run by a party INDEPENDENT of the signal operator (named in the deployment; honesty + independence is an UNVERIFIED TRUST ASSUMPTION, on par with the external identity root §6.5/§13 — NOT defended). A single xaudit is WEAKER than the cited CT multi-auditor gossip (Chuat CNS 2015); production uses ≥2 gossiping auditors. The single-auditor demo's local gossip log provides no self-cross-check; it exists only for a LATER independent auditor to replay (stated, not relied on).

**xaudit(batch_id) each window:**
1. fetch `Commit` from W1 AND W2 independently.
2. **split-view (SOUND, in-scope DETECTION — gated on FINALITY not mere reachability):** assert the two `Commit`s agree byte-canonically; a mismatch = the operator showed DIFFERENT views to W1 vs W2 = `EQUIVOCATION_DETECTED`. A `batch_id` present on one witness but ABSENT on the other is `EQUIVOCATION_DETECTED` ONLY once the batch is FINAL on the present witness (W1: covered by a verified STH; W2: block depth ≥ the ledger's finality bound) AND the absent witness is reachable-and-caught-up PAST that anchor point; otherwise it is `INCOMPLETE_DISCLOSURE` (settlement-pending OR unreachable — W1/W2 have different, non-zero finality latencies, so a transient one-sidedness observed mid-propagation is NOT a split view). The distinguishing conditions are finality + reachability, never a single un-settled snapshot.
3. **monotone + CONTIGUOUS seq (SOUND, in-scope DETECTION of rollback/gap):** across consecutive non-empty batches assert `seq_low(next) == seq_high(prev)+1` AND monotone; a gap/overlap = `ROLLBACK_OR_GAP_DETECTED` (an already-anchored/already-chained record range was removed). Relies on a SINGLE global-seq AuditLog instance (stated assumption; per-junction logs would need per-stream contiguity). Closes the batch-drop hole.
4. **per-signer reconciliation (a MEASURED INSTRUMENT — surfaces, never attributes, never gate-blocks):** enumerate the EXPECTED signer roster from an operator-INDEPENDENT enrolment source (the §6.5 identity root), so an operator cannot hide a signer by omitting its count. For each expected signer: verify `signer_sig` (operator cannot forge it); then compare `emitted_count` (signer-signed) vs `disclosed` (that signer's records in the operator-SERVED batch — note `disclosed` is operator-mediated and not independently verifiable from the anchor alone). **A mismatch in EITHER direction is INCONCLUSIVE + NON-ATTRIBUTING (aligns §6.7):** `disclosed < emitted_count` = EITHER an operator drop OR a signer inflating its own signed count to frame the operator; `disclosed > emitted_count` = EITHER a signer under-counting OR an operator replaying a signer's validly-signed record (§6.6 nonce covers claims, not sightings). It raises a conservative `INCOMPLETE_DISCLOSURE` FLAG for a human inquiry — it CANNOT attribute suppression to the operator, and it does NOT fail the anchor gate (§6). **The count store is itself un-witnessed and operator-suppressible** (the operator can withhold the whole store, or show different count sets to different auditors); because the roster is operator-INDEPENDENT (§6.5), suppression yields a blanket non-attributing `INCOMPLETE_DISCLOSURE` only — never a green count, never an attribution — consistent with the §8 out-of-reach boundary.
5. gossip `(batch_id, root, seq_range)` for a later independent auditor to replay.

**Without a passing xaudit (equivocation + contiguity clean), non-equivocation is ASSUMED, not enforced** — the §12 D-anchor gate REFUSES to count the coupling claim as anchored.

---

## 5. Honest bounds (the MEASURED boundary, stated inline; not defended)

- Merkle root proves PRESENCE, never ABSENCE, so **operator CREATION-TIME OMISSION** (a signer never emits its own incriminating record; it never enters the batch, the seq range stays contiguous, no signer-signed count over-claims it) is OUT OF REACH — §8 free-deviation boundary, measured not defended.
- **Per-signer disclosure mismatch is INCONCLUSIVE** (operator-drop vs signer-lie, both directions) — surfaced for human inquiry, never attributed, never gate-blocking.
- **Colluding keys** (k-of-n) produce mutually-consistent records that pass every check — out of scope (§8 boundary).
- **Single-node W2 + single xaudit** are weaker than a Byzantine quorum + multi-auditor gossip — demo limitation, honestly labelled.
- **Trust relocation:** non-equivocation rests on (W1 ∧ W2 ∧ xaudit) honesty/independence; identity→entity binding rests on the external identity root (§6.5). Both are UNVERIFIED assumptions, listed in §13.

---

## 6. Build / demo status + the §10 gate

- **Demo-buildable (free/public):** W1 = a real Rekor entry (public, no cost); W2 = a single-node Besu in a local container run by a distinct party (concrete endpoint/party is a deployment placeholder, an unverified trust assumption like the §6.5 identity-root certifier); xaudit = a local scheduled job; the off-chain signer-count store = a local access-controlled DB.
- **§10 / §12 D-anchor gate — the PASS conditions.** §10/§12 name three conjuncts: ≥2 witnesses + a *reconciled* per-signer count + a PASSING cross-audit. Per §6.7 the count conjunct is discharged as a NON-BLOCKING PROCESS check, never a count-matching condition, so the gate PASSES on: (i) a real write of `Commit` to BOTH witnesses; (ii) a PASSING xaudit = equivocation-clean AND contiguity-clean. The per-signer reconciliation is RUN and its result LOGGED as an anti-tautology PROCESS check ("reconciled" = counts are signer-SIGNED + roster-complete + signatures verified), but a count MISMATCH SURFACES `INCOMPLETE_DISCLOSURE` for human inquiry and NEITHER fails the gate NOR attributes to the operator (a lone lying signer must not be able to DoS/refuse the operator's true non-equivocation claim). §10/§12 are amended to state this "reconciled = run-and-logged, non-gating" reading so the pinned artifact and spec do not diverge. Absent (i) or (ii), the run is "not externally anchored" and the coupling claim is REFUSED. A mock/single-witness/un-cross-audited anchor CANNOT back the claim.
- **OUT of the overnight subset** (§11): the live W1/W2/xaudit integration + the signer-signed-count record kind + the off-chain store + the completeness-commitment/merkle-root wiring are their own scoped tasks; the overnight build uses the in-memory commitment + this contract as the target, labelled not-externally-anchored.
