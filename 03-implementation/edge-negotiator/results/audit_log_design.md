# Audit-Log Subsystem — Design

**Module:** `src/audit_log.py` · **Tests:** `tests/test_audit_log.py` (51 cases, all green)
**Brief reference:** PROJECT-DECISION-BRIEF.md §6 — *"tamper-evident audit log recording every decision and identity/registry change"*, with the blockchain as an **async anchor only**.

This subsystem is the integration-ready audit-log part of The Edge Negotiator. It is an
**append-only, tamper-evident decision + event log** with a sha256 hash-chain, optional
Ed25519 issuer signatures, **Merkle batch anchoring** as the bridge to Hyperledger Besu,
and JSONL persistence so the log survives runs and is independently auditable.

---

## 1. Goals & non-goals

| | |
|---|---|
| **Goal** | Record *every* per-decision event from `CoordinatedController` and every identity/registry change in a single contiguous, tamper-evident chain. |
| **Goal** | Detect any post-hoc mutation, reorder, or deletion of a logged record without trusting the storage medium. |
| **Goal** | Make on-chain anchoring affordable: anchor *thousands* of entries with a *single* Besu write via a Merkle root. |
| **Goal** | Persist independently (JSONL) and re-verify on load. |
| **Non-goal** | Prove an *approved agent is honest*. The log proves *what was recorded and that it was not altered*; it does not vouch for the truth of a decision (that is the conservation + registry layers' job — same scoping as `conservation.py`'s "consistency not truth"). |
| **Non-goal** | Synchronous on-chain writes. Anchoring is strictly off the control loop. |

---

## 2. Hash chain (mirrors `registry.py`)

The chain is byte-for-byte the same construction the registry already uses, so an auditor
reasons about **one** scheme across both logs.

Each entry is an envelope:

```
{ "seq": <int, contiguous from 0>,
  "prev_hash": <hex, previous entry's hash | "0"*64 for genesis>,
  "event": <the caller's validated, canonicalised payload dict>,
  "hash": <hex>,
  "issuer": <issuer junction_id | null>,
  "signature": <hex Ed25519 sig of `hash` | null> }
```

with

```
body = {"seq", "prev_hash", "event"}                      # signature NOT in the body
hash = sha256(prev_hash_hex + canonical_json(body)).hexdigest()
canonical_json = json.dumps(..., sort_keys=True, separators=(",",":"), allow_nan=False)
GENESIS_PREV_HASH = "0"*64
```

`verify_chain()` recomputes the whole chain and returns `False` on the first inconsistency:
non-contiguous `seq`, a `prev_hash` that does not link the previous `hash`, or a stored
`hash` that does not match the recomputed body hash. A tamperer who edits a field **and**
recomputes that entry's own hash still desyncs the *next* entry's `prev_hash`, so the chain
is still detected as broken (test: `test_tamper_recomputing_own_hash_still_breaks_via_prev_link`).

**Why the signature is outside the hashed body:** the hash commits to the *content*; the
signature commits to the *hash*. Layering them keeps the two integrity mechanisms
independent and individually verifiable, and lets an entry be re-signed/anchored without
re-hashing the payload.

**One deliberate divergence from `registry.py`:** `allow_nan=False`. Python's `json` would
otherwise emit non-standard `NaN`/`Infinity` literals that do not survive the JSONL
round-trip and would desync the chain on reload. We reject them at the boundary instead.

---

## 3. Merkle anchoring — the Besu bridge (the core de-risk pairing)

### The cost reality (measured, `results/ledger_bench.md`)

A single Besu write is **not** cheap: measured `register` median **1.44 s**, `revoke`
**1.84 s**, p95 up to **5.4 s** on a 1 s-block dev chain; a production QBFT network (2 s
default block period + validator round-trips) sits at the **top of, or above, the brief's
~2.1 s envelope**. Writing one transaction per control decision (sub-second cadence across
6 junctions) would couple control latency to consensus latency — `batch_register_10` shows
un-batched per-tx cost scales linearly (≈20 s for 10). **Per-event anchoring does not scale.**

### The fix: anchor a batch with one root

`merkle_root(start, end)` folds the entry **hashes** of a batch into a single 64-hex root
(Bitcoin-style: an odd level promotes its last node by duplication). One ~2.1 s Besu write
of that root anchors the **entire batch** — thousands of decisions per on-chain transaction.
The control loop only buffers entries in memory; a background flusher periodically computes
a root over the new range and submits it (off-loop, like the registry writes the brief
already keeps async).

### Proof of inclusion without the log

A verifier holding **only** the on-chain root can later prove a specific decision was in the
anchored batch:

- `inclusion_proof(index, start, end)` → ordered Merkle branch
  `[{"hash", "position": "left"|"right"}, …]` (leaf→root; `position` is the *sibling's* side).
- `verify_inclusion(entry_hash, branch, root)` re-derives the root and returns `True` iff it
  matches. A forged entry hash, a tampered branch hash, a flipped position, or the wrong root
  all yield `False`. It never raises on hostile input (same contract as `identity.verify`).

Determinism is guaranteed: the same range always yields the same root and the same branches
(tests `test_merkle_root_deterministic`, `…_verifies_for_every_entry_odd_batch`,
`…_verifies_subrange`). The lone-node promotion is reflected as a `"right"` sibling equal to
the node itself so a proof re-derives exactly the root the anchor used.

**Anchoring flow (integration sketch):**

```
control loop ──append(event[,issuer])──► AuditLog (in-memory chain)
                                            │
              every K decisions / T seconds │  (off the control loop)
                                            ▼
                              root = log.merkle_root(last_anchored, len(log))
                                            │  ~2.1 s, async
                                            ▼
                              Besu: anchorRoot(root, range)   ← single write/batch
```

---

## 4. Signatures (optional, per-entry)

`append(event, issuer=<JunctionIdentity>)` signs the entry **hash** with the issuer's
Ed25519 key (via `JunctionIdentity.sign`) and stores `issuer` + hex `signature`.
`verify_signatures({junction_id: der_public_key})` re-checks every signed entry with
`identity.verify`. A swapped signature (valid sig of *another* entry's hash), a wrong key,
an unknown issuer, or malformed hex all return `False`; unsigned entries are skipped. Because
the signature is over the hash, tampering the event (even with the chain hash repaired)
invalidates the signature too (test: `test_tampered_event_invalidates_signature_via_hash`).

Signing is **optional** so pure persistence/anchoring callers pay no crypto cost; the
`identity` import is lazy.

---

## 5. Persistence (JSONL)

`to_jsonl()` emits one canonical-JSON entry per line; `from_jsonl(text, verify=True)` parses,
validates the envelope shape (exact key set, basic types), and **re-verifies the chain**,
raising `ValueError` if the file was tampered (mutated field, reordered/dropped lines, bad
JSON, unexpected keys). `verify=False` allows a forensic load of a known-broken log. Round
trips preserve entries, signatures, and Merkle roots (tests under *persistence (JSONL)*).

---

## 6. Boundary validation (security rules: validate at every boundary)

- `append` rejects non-dict events, non-string keys, keys colliding with reserved envelope
  keys, non-JSON-serialisable values, `NaN`/`Inf`, and events whose canonical encoding
  exceeds **4 MiB** (`_MAX_EVENT_BYTES`, guards against a hostile huge event on load).
- The event is deep-copied via a canonical-JSON round-trip on the way in, so the log never
  holds a caller-mutable reference and every stored event is guaranteed JSONL-round-trippable
  (test: `test_append_does_not_mutate_caller_event_and_is_isolated`).
- `entries()` and `append()` hand back deep copies — callers cannot reorder or edit the live
  log; only an external tamperer reaching into `_log` can, which is exactly what
  `verify_chain` catches.
- Merkle range/index inputs are type- and bounds-checked; empty ranges raise rather than
  silently anchoring nothing.

---

## 7. Integration points

### 7.1 `CoordinatedController` — one `append` per decision

`CoordinatedController.decide()` builds a per-decision event dict and does
`self.events.append({...})` at `src/coordinated_controller.py:571`. The integration is a
**one-line addition** there (no edit to existing files is part of *this* part; this is the
documented hook for the integration step):

```python
# after constructing `event = {...}` (the dict currently appended to self.events):
self.events.append(event)
self.audit.append(event, issuer=self.identities.get(tl))   # <-- audit hook
```

The event dict already produced — `tls`, `halting`, `slm_phase`, `shield_phase`, `used`,
`overridden`, `tick`, `published`, `expected_incoming`, `incoming_per_phase`, `mp_choice`,
`coord_choice`, `coord_changed`, `coord_overrode`, `received`, `neighbor_note`, `detections`
— is already a plain JSON-serialisable dict (ints, lists, nested dicts of the same), so it
passes `_validate_event` unchanged. The deciding junction `tl` has an identity in
`self.identities`, so each decision can be **signed by the junction that made it** — giving
non-repudiation per decision. The controller would own one `AuditLog` (constructed alongside
`self.detections = []`).

### 7.2 `Registry` — mirror or merge registry events

`Registry` already hash-chains its own register/revoke events (`registry.py:148`
`_append_event`). Two clean integration options:

1. **Mirror:** on each `register`/`revoke`, also `audit.append({"kind":"registry", **event})`
   so identity/registry changes land in the *same* chain as decisions (the brief asks for
   "every decision **and** identity/registry change" in one tamper-evident log). The registry
   keeps its own chain for membership queries; the audit log is the unified record.
2. **Anchor both:** since both chains use the identical sha256 construction, a single Besu
   anchor transaction can carry the Merkle root of the decision log *and* the registry log
   tip — one ~2.1 s write covers both.

The recommended wiring is **option 1** (unified chain) for the audit record, with registry
events tagged `"kind": "registry"` and decision events untagged (or `"kind": "decision"`),
so `entries(filter=…)` can slice the log by kind.

### 7.3 Identities

`append(..., issuer=identity)` uses the same `JunctionIdentity` instances the controller
already holds in `self.identities`, and `verify_signatures` consumes the same canonical
**DER** public keys the registry stores — so identity, registry, and audit log all speak the
same bytes (no new key encoding introduced).

---

## 8. Threat coverage — what it detects vs. not

| Threat | Detected? | Mechanism |
|---|---|---|
| Edit a single logged field (post-hoc) | **Yes** | `verify_chain` — body hash mismatch |
| Edit a field **and** re-hash that entry | **Yes** | next entry's `prev_hash` desyncs |
| Reorder entries | **Yes** | non-contiguous `seq` / broken `prev_hash` link |
| Delete / truncate an entry | **Yes** | `seq` contiguity breaks (interior); see note on tail |
| Tamper the persisted JSONL file | **Yes** | `from_jsonl` re-verifies and raises |
| Forge a Merkle inclusion proof for a non-anchored decision | **Yes** | `verify_inclusion` re-derives a different root |
| Swap / forge an entry's signature | **Yes** | `verify_signatures` — Ed25519 check fails |
| Repair the chain hash after tampering a signed event | **Yes** | signature was over the original hash → still fails |
| Inject a non-serialisable / oversized / reserved-key event | **Yes** (rejected at append) | boundary validation |
| **Truncate the tail of the in-memory log before anchoring** | **No (in-memory alone)** | a contiguous prefix is internally valid; the **on-chain anchor closes this** — the anchored root commits to the batch length/range, so a missing tail entry fails its inclusion proof against the published root. This is *the* reason anchoring is part of the design, not optional. |
| **A coordinated, conservation-respecting attacker** who lies *before* logging | **No** | out of scope — the log faithfully records what it is given; detecting a false-but-consistent claim is the `conservation.py` + registry/authentication layers' job (the `Xiao2026` limit, brief §6). |
| Suppress logging entirely (never call `append`) | **No** | requires liveness/anchoring cadence enforcement (operational, not cryptographic). |

**Key boundary:** the chain proves *integrity of the record*; on-chain anchoring extends that
to *completeness against a published commitment* (defeats tail-truncation); neither proves
*truthfulness of the recorded claim* — that is deliberately the conservation/authentication
layers' responsibility.

---

## 9. Test summary

`tests/test_audit_log.py` — **51 tests, all passing**; full suite **232 passed, 16 skipped**
(skips pre-existing, SUMO/Foundry-gated). Adversarial coverage: chain verifies; single-field
tamper, seq tamper, prev_hash tamper, re-hash-after-tamper, reorder, and drop all → `False`;
Merkle root deterministic + inclusion proofs verify across odd batches and sub-ranges, while
forged entries / tampered branches / flipped positions / wrong roots / garbage branches all
fail; signed entries verify and swapped/wrong-key/unknown-issuer/malformed-hex signatures
fail; JSONL round-trip preserves entries, signatures and roots and re-verifies, while
tampered/reordered/bad-JSON/unexpected-key/non-object files are rejected; boundary tests
cover non-dict, reserved keys, non-serialisable (incl. NaN/Inf), non-str keys, huge events,
caller-mutation isolation, and a 2000-entry scale test for chain + Merkle inclusion.
