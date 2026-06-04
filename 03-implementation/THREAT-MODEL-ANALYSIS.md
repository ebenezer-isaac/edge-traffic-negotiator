# Threat-Model Analysis — The Edge Negotiator

**Scope.** This document is the dissertation threat-model section, grounded in the
**AS-BUILT** code, not an idealised design:
`src/conservation.py` (`ConservationChecker.evaluate`), `src/message_bus.py`
(`MessageBus.inbox`), `src/identity.py` (Ed25519 sign/verify), and `src/registry.py`
(permissioned allowlist + hash-chained audit log). It answers: what the
vehicle-conservation check detects vs misses; how a coordinated attacker evades it;
the cleanest honest formal guarantee; and three Wk7-8 attack scenarios mapped to
layer / detector verdict / metric. Companion: `PROJECT-DECISION-BRIEF.md` §6.

---

## Verdict (read this first)

The integrity layer is **sound but narrow, and we must claim it narrowly.** Two
**independent** primitives compose: (1) an Ed25519-signature + permissioned-registry
+ replay-guard authentication layer (`message_bus.inbox`) that decides *who may
speak*, and (2) a stateless vehicle-conservation plausibility check
(`conservation.evaluate`) that decides *whether two approved parties' reports are
mutually consistent within an integer tolerance*. Together they detect every
**outsider** attack (impersonation, replay, non-member injection, tampering) and
every **uncoordinated insider** attack or fault that pushes a single edge's
claim/observation gap beyond `tolerance`. They do **not** detect a
conservation-respecting insider — an authenticated, currently-approved sender who
lies *within* tolerance, or who colludes with a second approved party to keep the
books balanced. This is the residual-FDI limit of `Xiao2026Residual.pdf` instantiated
in our domain, and it is fundamental to consistency checking, not a bug we can patch.

> **Single most-attackable weakness in our claimed contribution:** a **coordinated,
> conservation-respecting insider collusion** — two currently-approved junctions A and
> B that inflate A's *claimed* outflow and B's *observed* inflow in lockstep on edge
> A→B. Both pass `auth` (valid signatures, approved members, fresh ticks); the per-edge
> `delta = claimed − observed` stays `<= tolerance`, so `evaluate` returns
> `reason="ok", flagged=False`. Neither layer fires. Auth proves *who* signed; it
> cannot prove the signed numbers are *true*. The consistency check proves the two
> reports *agree*; it cannot prove they are *true*. Our defensible contribution must
> therefore be stated as **"authenticated, consistency-checked coordination with
> spoof/fault detection against uncoordinated adversaries and faults"** — never as
> trust, truth, or collusion-resistance.

---

## 1. What the conservation check DETECTS vs MISSES (as-built `evaluate` semantics)

`ConservationChecker.evaluate(claims, observed)` is **stateless** and **per-edge**.
For every directed edge present in *either* dict it emits exactly one frozen
`Detection(src, dst, claimed, observed, delta, flagged, reason)`, sorted by edge key.
`delta = claimed − observed`. The decision tree (lines 156-165) is, in priority order:

| Condition (in order) | `flagged` | `reason` | Physical meaning |
|---|---|---|---|
| edge in `observed` only (no claim) | `True` | `missing_claim` | B saw traffic A denies sending — fabricated/withheld inflow |
| edge in `claims` only (no obs) | `True` | `missing_observation` | A claims output B never saw — sensor outage / fabricated outflow |
| both present, `delta > tolerance` | `True` | `inflated` | claimed ≫ observed — count-inflation spoof |
| both present, `delta < −tolerance` | `True` | `under_reported` | observed ≫ claimed — under-report / drop / fault |
| both present, `|delta| <= tolerance` | `False` | `ok` | mutually consistent within band |

Default `tolerance = 2` vehicles (constructor; `bool` rejected as a stray type,
negative rejected). `_validate_counts` rejects non-dict inputs, malformed keys, and
non-int / negative / boolean counts at the boundary — so malformed/hostile *tallies*
raise rather than silently mis-score (a deliberate fail-closed input contract).

### DETECTS (high confidence)
- **Uncoordinated count-inflation spoof** on edge A→B: A inflates its claim while B's
  honest observation is unchanged ⇒ `delta > tolerance` ⇒ `inflated`. This is the
  primary threat (§4a).
- **Faulty / under-reporting sensor**: B's detector drops vehicles (or A under-states)
  while the counterpart is honest ⇒ `delta < −tolerance` ⇒ `under_reported` (§4b).
- **One-sided fabrication / data outage**: a claim with no matching observation, or an
  observation with no matching claim ⇒ `missing_observation` / `missing_claim`. This is
  where a naive Sybil/fabricated-inflow attack lands if the spoofer does not also forge
  the *counterparty's* side (§4c).
- **Gross magnitude errors** of any single-sided origin that exceed the integer band.

### MISSES (by construction — must be stated as non-claims)
- **Coordinated, conservation-respecting collusion** (the headline weakness): A and B
  move claim and observation together so `|delta| <= tolerance`. Verdict is `ok`. This
  is the `Xiao2026Residual.pdf` "physically-consistent FDI stays on the measurement
  manifold and produces no abnormal residual" result, instantiated for a directed-edge
  conservation residual instead of an AC-power-flow residual. The same multi-sensor
  coordinated-FDI undetectability is shown in power state estimation by
  `Obata2023FDIState.pdf`.
- **Within-tolerance lying**: any single-party falsification with
  `|claimed − observed| <= tolerance` (e.g. ±2 vehicles at default) is `ok`. Tolerance
  is a hard floor on detectable manipulation magnitude — a smart attacker simply lies
  *inside the band* every cycle. There is **no statistical accumulation** across ticks
  in the as-built code (stateless `evaluate`), so a slow within-band drift is invisible.
- **Attribution / who-is-wrong**: `evaluate` flags an *edge*, never a *culprit*. On a
  flagged edge it cannot say whether A over-claimed or B under-observed. The docstring
  states this explicitly ("CANNOT identify which of two disagreeing parties is wrong").
  This is the *upstream-node / false-accusation* hazard of `Derhab2020FlowConserv.pdf`:
  a flag against an edge can implicate an *honest* node whose counterpart misbehaved.
- **Truth**: the check proves *consistency*, not *correctness*. Two honest-but-wrong
  sensors that happen to agree are `ok`; two colluding liars who agree are `ok`. The
  blockchain "records garbage-in" faithfully (Brief §6).

---

## 2. The Xiao2026 evasion, concretely — and why auth is the necessary complement

### 2.1 How lockstep inflation slips through
Take edge A→B, default `tolerance = 2`. Honest baseline: A released 18, B observed 17,
`delta = 1` ⇒ `ok`. A coordinated attacker controlling **both** approved junctions
inflates the books in lockstep to fake corridor demand on A→B:

```
claims   = {("A","B"): 48}     # A over-claims by +30
observed = {("A","B"): 47}     # B over-observes by +30
# delta = 48 - 47 = 1  <= tolerance(2)  ->  flagged=False, reason="ok"
```

`evaluate` returns `Detection(claimed=48, observed=47, delta=1, flagged=False,
reason="ok")`. The 30-vehicle phantom flow is invisible because the *residual* (delta),
not the absolute magnitude, is all the check ever inspects. This is exactly
`Xiao2026Residual.pdf`: a manipulation that **stays on the conservation manifold**
(`claimed ≈ observed`) produces **no abnormal residual** and is, by a property of the
manifold itself, indistinguishable from nominal data — independent of the attacker's
sophistication. Our directed-edge conservation residual is a one-dimensional special
case of their measurement-manifold argument. `Obata2023FDIState.pdf` shows the same
"undetectable from the residual" result for coordinated multi-sensor FDI in power state
estimation. The corridor impact: the downstream MaxPressure shield and SLM coordinate
on inflated pressure, mis-prioritising A→B's phase against genuinely busier approaches.

### 2.2 Why the signature + registry layer is the necessary complement
The conservation check is blind to *identity*; it is fed claim/observation tallies and
never asks who produced them. Everything that decides *whether a report is even
admissible* lives in `MessageBus.inbox`, which drops a published `NeighborMessage`
unless **all** hold (lines 150-190):

1. **Topology** — `sender ∈ neighbours[recipient]` else `not_neighbour`.
2. **Membership** — `registry.is_approved(sender)` and a non-`None` `public_key`, else
   `revoked` (was registered, per hash-chained audit log) or `unknown_sender` (never
   registered). Revocation is effective the instant `registry.revoke()` removes the key.
3. **Crypto** — `verify(public_key, canonical_bytes(sender,t,payload), signature)` must
   pass, else `bad_signature`. `canonical_bytes` is sorted-key, whitespace-free JSON, so
   signer and verifier hash byte-identical input. This single check defeats
   **impersonation** (claiming to be A1 but signing with another key fails verification
   against A1's *registered* key) and **payload tampering** (any edit changes the signed
   bytes). `identity.verify` is hardened to return `False` — never raise — on wrong key,
   short/tampered signature, or malformed DER, so a hostile blob cannot crash a receiver.
4. **Replay** — `(recipient, sender, t)` must be unseen, else `replay`.

So auth answers a question conservation cannot: *is this even a legitimate, current,
non-replayed message from the peer it claims to be?* Without auth, an **outsider** could
inject a perfectly conservation-consistent (`ok`) pair of forged reports and the
consistency check would wave it through — auth is what makes "approved sender" a
precondition before conservation is ever consulted. This composition (cryptographic
admission control as the first line, plausibility/consistency as the second) is the
standard C-ITS defence-in-depth posture of `Keijzer2021Intersection.pdf` (encryption +
authentication as first line, plausibility checks as second line against insiders that
slipped past) and `BC-V2X-Sec.pdf` (blockchain membership + anomaly detection).

### 2.3 What auth itself does NOT solve
Auth proves *provenance and currency of membership*, never *honesty*. The registry
docstring is explicit: it records *who is currently approved*, and "does NOT vouch for
the honesty of an approved agent — only its membership." An **authenticated insider**
who is a currently-approved member can sign a *true-by-construction-but-false* payload:
every `inbox` check passes (valid signature, approved, neighbour, fresh tick), and the
lie is then handed to conservation — which catches it **only if it exceeds tolerance on
a single edge**. The §2.1 lockstep collusion passes *both* layers. This is precisely the
gap `Amanullah2026CoopMD.pdf` identifies in self-reported plausibility checks ("the
potential for trusted nodes to behave maliciously … detecting when previously honest
nodes abruptly exhibit rogue behaviour poses a significant challenge") and the insider
threat surveyed in `Shahariar2025Trust.pdf` ("isolating malicious insider attacks which
traditional security approaches fail to thwart") and `BC-V2X-Sec.pdf` ("internal
cyberattacks, hard to detect due to their valid credentials"). Our honest mitigation is
*containment, not detection*: `revoke()` + the tamper-evident hash-chained audit log
(`registry.verify_chain`) give **non-repudiable attribution after the fact** so a
compromised insider can be ejected and its history proven — not silent prevention.

---

## 3. The formal detection guarantee we can honestly claim

Let an edge `e = (A,B)` carry true released count `n_e` and true arrival count `m_e`.
Let `c_e` be A's signed claim and `o_e` be B's signed observation as admitted by
`inbox`. Let `τ = tolerance` (default 2).

**Admission (auth) guarantee.** A report is consumed by a recipient *only if* it is
(i) from a topological neighbour, (ii) signed by a key currently bound to that sender in
the registry, (iii) cryptographically valid over its exact bytes, and (iv) not a replay.
Equivalently: **no outsider, no revoked member, no impersonator, no tamperer, and no
replayer can place a value into `(c_e, o_e)`.** Anything else is logged in `rejected`
with a closed-set reason; nothing is silently dropped.

**Consistency (conservation) guarantee.** Given admitted `(c_e, o_e)`, `evaluate`
flags edge `e` **iff** `c_e` and `o_e` are mutually inconsistent at granularity `τ`:

> `flagged(e) = True  ⟺  |c_e − o_e| > τ`  (both present),
> with one-sided presence (`missing_claim` / `missing_observation`) always flagged.

**Honest detection theorem (what we claim).** *If at most one of the two parties on
edge `e` deviates from truth, and that deviation shifts the reported residual by more
than `τ` (i.e. `|c_e − o_e| > τ` whereas the honest residual `|n_e − m_e| <= τ`), then
`evaluate` flags `e` with reason `inflated` (claim-side over-report),
`under_reported` (observation-side / drop), or a `missing_*` reason (one-sided
fabrication or outage). Detection is per-edge, deterministic, and order-independent.*

**Matching honest non-claims (state these in the thesis):**
- **(N1) No truth claim.** We do not detect a *consistent* falsehood:
  `|c_e − o_e| <= τ` ⇒ `ok` regardless of `n_e, m_e`.
- **(N2) No coordinated-collusion claim.** If both parties deviate in lockstep so the
  residual stays `<= τ`, the edge is `ok` (`Xiao2026Residual.pdf`; `Obata2023FDIState.pdf`).
- **(N3) No attribution claim.** A flag localises a *bad edge*, not a *bad party*; an
  honest node may be implicated when its counterpart misbehaves
  (`Derhab2020FlowConserv.pdf` upstream-node effect).
- **(N4) No sub-tolerance / slow-drift claim.** Manipulations of magnitude `<= τ` per
  edge are undetectable; the stateless check accumulates no cross-tick evidence.
- **(N5) Auth ≠ honesty / blockchain ≠ trust.** Membership and a tamper-evident log give
  provenance, non-repudiation, and revocability — not incentive-compatibility and not
  prevention of lying (Brief §6; `Tian2025` is motivation only, type-incoherent for
  frozen LLMs).

---

## 4. Three Wk7-8 attack scenarios (layer · verdict · metric)

For each: the **injection**, **which layer catches it** (auth = `message_bus`,
conservation = `conservation.evaluate`, or neither), the **expected detector verdict**
(exact `reason` string from the as-built code), and the **demonstrating metric**.

### (a) Spoofed traffic-state report — PRIMARY
- **Injection.** A currently-approved junction A signs a genuine message but inflates
  its claimed outflow toward B (e.g. claims 40, true 15). B observes honestly (~15).
  Single-sided over-claim on edge A→B.
- **Layer that catches it.** **Conservation**, not auth — the message is validly signed
  by an approved neighbour, so `inbox` admits it (auth is *not* the detector here; this is
  the insider-FDI case `Keijzer2021Intersection.pdf` flags as needing a second line).
- **Expected verdict.** `delta = 40 − 15 = 25 > τ` ⇒
  `Detection(reason="inflated", flagged=True)`.
- **Metric.** Detection **precision/recall/F1** at a fixed false-alarm rate, swept over
  spoof magnitude `Δ ∈ {0,1,2,3,5,10,…}`; expect recall→1 once `Δ > τ`, and a controlled
  false-alarm rate from honest in-transit jitter at `Δ <= τ`. Report **detection latency**
  in control cycles (here 1 cycle — stateless, fires the tick the inflated edge appears).

### (b) Faulty sensor — SECONDARY
- **Injection.** No adversary. B's loop detector under-counts (drops ~50% of arrivals) or
  goes dark; A reports truthfully. Models a real fault, not an attack.
- **Layer that catches it.** **Conservation** (auth is irrelevant — both ends approved,
  signed, fresh).
- **Expected verdict.** Under-count: `delta < −τ` ⇒ `reason="under_reported"`. Total
  outage on that edge (claim present, observation absent): `reason="missing_observation"`.
- **Metric.** Same precision/recall/F1 vs drop-fraction; **detection latency** = 1 cycle.
  **Key caveat to report (N3):** the flag attaches to edge A→B and *cannot* distinguish
  "B's sensor faulty" from "A over-claimed" — demonstrate this ambiguity explicitly
  (`Derhab2020FlowConserv.pdf`), and note auth+revoke cannot fix a fault, only eject a node.

### (c) Sybil count-inflation — OPTIONAL, and the discriminating case
- **Injection.** Fabricated identities inflate apparent inflow on an edge — the classic
  VANET Sybil (`Azam2022Sybil.pdf`, `Balaram2023Sybil.pdf`: forged identities create a
  fake congestion scenario). Two distinct sub-cases that land on **different layers**:
  - **(c1) Outsider Sybil** — fabricated junction identities not in the registry, or
    fabricated inflow on a non-neighbour edge. **Caught by AUTH**: `inbox` rejects with
    `unknown_sender` (never registered) or `not_neighbour` (non-adjacent). Conservation is
    never reached. *Metric:* fraction of Sybil messages rejected at the bus (target 100%)
    + the `rejected`-log reason histogram; detection latency = 0 cycles (rejected on
    receipt, never delivered).
  - **(c2) On-ledger fabricated inflow** — an *approved* B reports arrivals on edge A→B
    that A never claims (A is honest / silent). **Caught by CONSERVATION**: observation
    present, no claim ⇒ `reason="missing_claim", flagged=True`. *Metric:* precision/recall
    on `missing_claim` flags; latency = 1 cycle.
  - **(c3) Coordinated Sybil = the evasion** — attacker controls approved A *and* B and
    fabricates *both* sides in lockstep (§2.1). **Caught by NEITHER**: auth passes
    (approved, signed, fresh), conservation returns `ok` (`|delta| <= τ`). *Metric:* this
    scenario's value is **negative-result** — measured recall = 0, demonstrating the
    `Xiao2026Residual.pdf` limit empirically and motivating the auth layer's
    revoke/audit containment as the only available response.

**Summary mapping**

| Scenario | Auth (`message_bus`) | Conservation (`evaluate`) verdict | Demonstrating metric |
|---|---|---|---|
| (a) Spoofed report (insider over-claim) | admits (valid member) | `inflated` | P/R/F1 vs Δ; latency 1 cycle |
| (b) Faulty sensor (under-count / outage) | admits | `under_reported` / `missing_observation` | P/R/F1 vs drop-fraction; **ambiguity (N3)** |
| (c1) Outsider Sybil | **rejects** `unknown_sender`/`not_neighbour` | (never reached) | % rejected at bus; latency 0 |
| (c2) On-ledger fabricated inflow | admits | `missing_claim` | P/R on `missing_claim` |
| (c3) Coordinated Sybil collusion | admits | `ok` (**MISS**) | recall = 0 (negative result; Xiao2026) |

---

## 5. Citations (by filename, in `06-literary-survey/papers/`)

- **`Xiao2026Residual.pdf`** — Xiao & Weng, *Limits of Residual-Based Detection for
  Physically Consistent False Data Injection* (arXiv:2602.10162, Feb 2026). The
  detectability limit: manifold-consistent manipulations produce no abnormal residual.
  Our headline non-claim (N2, §2.1, §4-c3).
- **`Obata2023FDIState.pdf`** — Obata, Kobayashi & Yamashita, IEICE Trans. Fundamentals
  E106-A(5) 2023, DOI 10.1587/transfun.2022MAP0010. Coordinated multi-sensor FDI is
  undetectable from the converged residual. Reinforces N2.
- **`Derhab2020FlowConserv.pdf`** — Derhab et al., *Sensors* 20(21):6106, 2020, DOI
  10.3390/s20216106. Flow-conservation IDS; the **upstream-node effect** (honest node
  falsely accused because its neighbour misbehaved). Grounds the attribution non-claim (N3).
- **`Amanullah2026CoopMD.pdf`** — Amanullah et al., *Coop-IntelliMD*, IEEE Access 2026,
  DOI 10.1109/ACCESS.2025.3638793. Self-reported plausibility checks are limited by
  trusted-node misbehaviour and abrupt honest→rogue transitions. Grounds §2.3.
- **`Keijzer2021Intersection.pdf`** — Keijzer, Jarmolowitz & Ferrari, *Detection of
  Cyber-Attacks in Collaborative Intersection Control* (arXiv:2104.03801, 2021).
  Auth/encryption as first line, plausibility checks as second line vs insiders. Grounds §2.2.
- **`Azam2022Sybil.pdf`** — Azam et al., *Sensors* 22(18):6934, 2022, DOI
  10.3390/s22186934. Sybil = forged identities fabricating fake congestion. Scenario (c).
- **`Balaram2023Sybil.pdf`** — Balaram et al., *Wireless Networks* 29:3435-3443, 2023,
  DOI 10.1007/s11276-023-03399-1. Sybil dummy-node injection in VANET. Scenario (c).
- **`Shahariar2025Trust.pdf`** — Shahariar & Phillips, *A Survey of Security Threats and
  Trust Management in VANETs*, Trans. Eng. Comput. Sci. 13(3):127-172, 2025, DOI
  10.14738/tmlai.1303.18943. Insider attacks evade traditional security. Grounds §2.3.
- **`BC-V2X-Sec.pdf`** — Gebrezgiher et al., *ML-Based Blockchain for Secure V2X*,
  *Sensors* 25(15):4793, 2025, DOI 10.3390/s25154793. Internal attackers with valid
  credentials are hard to detect; blockchain membership + anomaly detection. Grounds §2.2.
- **`SafeLight.pdf`** — Du et al. (arXiv:2211.10871, 2023). RL-shield precedent for the
  deterministic MaxPressure shield over the SLM (architecture context, Brief §2).
