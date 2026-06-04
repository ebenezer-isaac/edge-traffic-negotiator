# Coordination Algorithm Specification — The Edge Negotiator

**Status:** Design specification (no production code). Derived from `PROJECT-DECISION-BRIEF.md`
(single source of truth), the as-built code in `edge-negotiator/src/`, and a clean
reimplementation of the neighbour-message idea from **CoLLMLight** (arXiv:2503.11739, Yuan,
Lai & Liu, HKUST-GZ, 2025) and the neighbour-attention idea from **CoLight** (arXiv:1905.05717;
CIKM 2019; DOI 10.1145/3357384.3357902; Wei et al.). We *reimplement the algorithm*, we do **not**
port either paper's CityFlow-welded code.

**Scope discipline.** This document specifies behaviour and interfaces only. It does not authorise
any change under `edge-negotiator/src/` or `edge-negotiator/tests/`. Where it identifies a code
mismatch (§4) it states the recommended fix; applying it is a separate, gated task.

---

## 0. The problem, stated precisely

Each signalised junction runs one Phi-4-mini agent (3.8B, Foundry Local, OpenAI-compatible
endpoint). Inference is **serialised** and costs roughly 2 s per call (no batching; see
`PROJECT-DECISION-BRIEF.md` §3). The agent emits **only** `{"phase": N}` — no chain-of-thought,
by design (brief §5; CoT-faithfulness literature, `CoT-Faith` arXiv:2505.05410). A deterministic
**MaxPressure shield** (`controllers.py::MaxPressureController`) validates or overrides every
proposal and runs alone at quiet junctions (`hybrid_controller.py`).

The coordination question is therefore narrow and unusual:

> Given that the model is a frozen black box that returns one integer and we cannot afford a
> reasoning trace, **how does a neighbour's predicted traffic state change this junction's chosen
> phase at all?**

CoLLMLight's answer — and ours — is that coordination is **entirely a property of the input
context**, not of model internals. Neighbour information enters by being *verbalised into the
prompt* (CoLLMLight eq. 4: `X = Prompt(O_t, G, T_t, D)`, then `â = f_LLM(X)`). Our contribution
versus CoLLMLight is to find the **minimal** such context that survives a 2 s/terse-output budget,
to wrap the message in the project's signed/conserved integrity layer, and to keep a deterministic
shield as the final authority.

---

## 1. What each junction shares, and at what cadence

### 1.1 The minimal useful neighbour signal (the core argument)

CoLLMLight shares, per neighbouring lane, the 4-tuple `o = [n_queue, n_move, τ (avg wait),
ρ (occupancy)]` plus a spatiotemporal graph and a Δt=5-step history, and then asks the LLM to
*predict* downstream states under each candidate action. That is rich, but it was validated on a
fine-tuned Llama-3.1-8B on cloud GPUs with multi-second budgets per intersection and long prompts.
It is too heavy for a terse Phi-4-mini under serialised 2 s inference: every extra field is extra
prompt tokens (slower decode) and extra ways for a non-fine-tuned 3.8B model to get confused.

**We specify the minimal signal as a per-neighbour pair:**

For a sending junction `S` with neighbour set `N(S)`, the message toward each neighbour `B ∈ N(S)`
carries two integers:

1. **`release`** — the count of vehicles **about to be released toward `B`** in the next control
   window. Concretely: the upstream halting + just-arrived count on the lane group whose green
   movement feeds edge `S→B`, conditioned on `S`'s *current/just-chosen* phase. This is the
   short-horizon *outflow `S` is committing to send `B`*.
2. **`queue_forecast`** — a one-number **short-horizon queue forecast** for that same approach: the
   projected queue length on the `S→B` approach at the end of the next window (a cheap linear
   roll-forward `q_now + arrivals − served`; no model inference, computed in the controller).

Everything else CoLLMLight sends (moving count, average wait, occupancy fraction, multi-step
history, full graph) is **dropped** from the wire signal. Rationale:

- **`release` is the one field that is causally about *me*.** CoLight's empirical finding
  (Fig. 2b/c) is that neighbour influence is *directional and asymmetric*: an upstream neighbour
  about to dump traffic onto my approach matters far more than a downstream one. `release` is
  exactly the upstream-toward-me quantity, pre-resolved to *my* edge. It is the single highest-value
  bit for anticipating my own next-window inflow and avoiding receiving a platoon into a queue I
  just chose not to clear.
- **`queue_forecast` supplies the "is this about to get worse?" gradient** that a single instantaneous
  count cannot. It is the terse stand-in for CoLLMLight's future-state prediction step — but computed
  deterministically in the controller, not by the SLM, so it costs zero inference tokens.
- **Both are integers** → 1–2 tokens each in the prompt, and they map onto data the controller
  already computes. `MaxPressureController.green_halting()` already sums the upstream halting a green
  phase would serve; `release` is that same sum restricted to the movement feeding a specific
  neighbour edge. No new sensing is required.
- **Terseness is a safety property here, not just a budget concession.** A non-fine-tuned 3.8B model
  given a 4-field × k-neighbour × 5-step table will pattern-match poorly and slowly. Two integers per
  neighbour keep the augmented prompt within ~30–60 extra tokens for a 2–4-neighbour grid junction.

**Why not less?** A single bit ("congested toward you: y/n") loses the magnitude the receiver needs to
distinguish "ignore" from "pre-empt". Two integers is the floor that preserves *direction + magnitude
+ trend*.

**Why not more?** Average wait `τ` and occupancy `ρ` are weakly identifiable by a terse model and
duplicate information already in `queue_forecast`/`release`; multi-step history blows the token budget
under serialised inference. They are explicitly deferred to an optional ablation (see §5.4).

### 1.2 Cadence — event-gated, never fixed-rate

Per `PROJECT-DECISION-BRIEF.md` §3 (serialised ~2 s inference) and the `Amanullah2026CoopMD` /
`Keijzer2021Intersection` event-trigger precedent, messaging is **event-gated**, mirroring
CoLLMLight's complexity-aware reasoning (its congestion-risk coefficient `n_c`, and its
communication threshold `α` that filters out low-occupancy neighbour lanes).

A junction `S` **emits** a neighbour message toward `B` only when an event fires:

- **E1 — release event:** `S` has just selected (or is about to select) a green that releases a
  platoon of size `≥ θ_release` toward `B`. (`θ_release` ≈ the existing event gate `gate=2` in
  `hybrid_controller.py`; tune on the grid.)
- **E2 — queue-build event:** `queue_forecast(S→B)` crosses a build threshold `θ_queue`, signalling
  `B` that spillback toward it is forming even before release.

A junction `S` **consults** neighbour messages (i.e. folds them into a prompt for the SLM) only at
its own decision points, and only when it is *already* past the local event gate (`sum(halting) ≥
gate`) — i.e. only at junctions the hybrid controller has decided are busy enough to wake the SLM
at all. Quiet junctions never message, never consult, and run MaxPressure alone. This is the direct
analogue of CoLLMLight `n_c = 0 ⇒ no cooperation`.

**Freshness gate.** Each message carries `ts` and a `window` length; a receiver discards any message
older than one control window (`now − ts > window`) and treats it as "no neighbour signal". Stale
predictions are silently dropped, never blended (see §6).

**Net effect on the latency budget:** at most one SLM call per busy junction per decision window,
exactly as today; coordination adds *prompt tokens*, not *extra calls*. Serialisation is preserved.

---

## 2. Folding neighbour messages into a no-CoT decision

The model emits only `{"phase": N}`. So coordination **cannot** live in the model's reasoning — it
must live in the *context we hand the model* and in the *deterministic post-processing*. Two
complementary channels:

### 2.1 Channel A — prompt augmentation (coordination enters via context)

We extend the existing user prompt in `slm_agent.py::choose_phase`. Today it is:

```
Junction A1. Waiting vehicles per phase: phase 0 = 7, phase 1 = 3, ...
Which phase should get green now? Reply ONLY {"phase": <index>}.
```

We augment it with a short, fixed-format **incoming-pressure block** built from validated neighbour
messages, and we *bind each neighbour fact to the local phase that serves that direction* so a terse
model does not have to reason about geometry:

```
Junction A1. Waiting vehicles per phase: phase 0 = 7, phase 1 = 3, phase 2 = 5, phase 3 = 2.
Incoming from neighbours (vehicles heading INTO this junction soon):
  - from A0 toward phase 0 approach: 9 arriving, queue rising to 12
  - from A2 toward phase 2 approach: 1 arriving, queue steady
Serve the phase facing the worst combined (waiting + incoming) pressure.
Reply ONLY {"phase": <index>}.
```

Design rules that make this work for a terse 3.8B model:

- **Pre-resolve geometry in the controller, not the model.** The controller already knows the map
  from neighbour edge `A0→A1` to the local phase index whose green serves that approach. So the
  prompt says "toward phase 0 approach", turning a spatial-reasoning problem into a simple
  "add these two numbers per phase" problem. This is the terse-model equivalent of CoLLMLight's
  spatiotemporal graph `G` and of CoLight's *index-free* per-neighbour attention — we precompute the
  alignment so the model needn't.
- **Verbalise magnitude + trend only** (`N arriving, queue rising/steady/falling`), matching the §1.1
  signal. No raw graph, no history table.
- **One imperative line** restates the objective as combined pressure so the model has an explicit
  rule to follow, since it will not narrate one.
- **Deterministic ordering & formatting** (sorted by neighbour id; fixed phrasing) keeps the prompt
  cache-friendly and the parse robust. `temperature=0` already set.
- **Bounded size:** only neighbours that *passed an event gate and verification* appear; typically
  1–3 lines. Token growth is small and constant-ish, protecting the 2 s budget.

### 2.2 Channel B — deterministic fold (coordination that does not trust the model)

Because the model may ignore or mis-weight the block, neighbour information **also** enters the
deterministic side, independent of the SLM:

- The MaxPressure shield's pressure term is **augmented with anticipated inflow**. Standard pressure
  for phase `gi` is `Σ (upstream_halting − downstream_halting)`. We add the verified incoming
  release bound to that direction: `pressure'(gi) = pressure(gi) + λ · Σ_{B→here served by gi}
  release(B→here)`. This is a coordinated-MaxPressure baseline *and* the shield's coordinated
  reference choice. (`λ` small, tuned; `λ=0` recovers today's shield exactly, giving a clean
  ablation.)
- This means coordination has a guaranteed effect **even if the SLM never reads the block**, which
  is the conservative engineering stance the brief's "shield disposes" doctrine demands.

So: the SLM *may* coordinate via Channel A (prompt), and the shield *always* coordinates via
Channel B (augmented pressure) — and the shield has the final say (§3).

---

## 3. The MaxPressure shield in the coordinated setting

The shield's role is unchanged in spirit — **SLM proposes, shield disposes** — but its reference
computation and its override criteria gain a coordination-aware form.

| Aspect | Uncoordinated (today) | Coordinated (this spec) |
|---|---|---|
| Shield reference choice | `argmax pressure(gi)` over local queues | `argmax pressure'(gi)` incl. verified incoming-release term (Channel B) |
| SLM input | local halting per phase | local halting **+** verified incoming-pressure block (Channel A) |
| Accept SLM proposal when | valid phase index returned | valid index **and** within the safety envelope (see below) |
| Override / fallback when | proposal is `None`/invalid | same, **plus** when proposal violates the coordinated safety envelope |
| Quiet junction | shield only (event gate) | unchanged — no message, no SLM |

**Coordinated safety envelope (new).** The shield rejects an otherwise-valid SLM phase if it is
*coordination-unsafe*, e.g. it would hold green for a movement that a verified neighbour message says
is about to receive a large platoon into an already-near-saturated downstream queue (spillback risk),
or it starves a phase whose `pressure'` (incl. incoming release) dominates by more than a margin
`δ`. On rejection the shield substitutes its own `argmax pressure'` choice and logs an
`overridden=true` event. This is a strict superset of today's "None ⇒ shield" rule; with `λ=0` and
`δ=∞` it degenerates to current behaviour, so the change is opt-in and ablatable.

**What does NOT change:** the shield remains deterministic, local-authority-final, and never calls
the SLM or the network in its decision path. Neighbour messages reach the shield only as
*already-verified, already-conserved integers* (the trust path has run first; §4, §6). The shield
never blocks on inference or on the ledger.

---

## 4. Mapping onto the signed message bus — and a mismatch to fix

`PROJECT-DECISION-BRIEF.md` §2 (wk 3–4) calls for a *signed neighbour-message bus (MQTT)* with
payload `{"toward": {neighbour: count}}`. **Finding: that bus does not yet exist in the codebase.**
The shipped trust-path code is `identity.py` (Ed25519 sign/verify over raw bytes), `registry.py`
(approve/revoke + hash-chained audit), and `conservation.py` (the consistency check). The message
*transport* and the *payload schema* are still to be built. This spec defines the contract they must
satisfy so code and design agree.

### 4.1 Wire message (one signed unit per emit)

```jsonc
{
  "from": "A0",                       // sender junction id (must be registry-approved)
  "ts":   1730000000.0,               // emit time (UNIX seconds) — freshness gate (§1.2)
  "window": 30,                       // seconds the forecast covers
  "toward": {                         // brief's field name — KEEP IT
    "A1": { "release": 9, "queue_forecast": 12 },
    "A3": { "release": 0, "queue_forecast": 4  }
  }
}
```

- The signed bytes are `canonical_json(message_without_sig)` (sorted keys, no whitespace — reuse
  `registry._canonical_json`'s convention). Signature transported alongside in the bus envelope.
- Receiver pipeline: **(a)** `registry.is_approved(from)` → **(b)** fetch `registry.public_key(from)`
  → **(c)** `identity.verify(pubkey, signed_bytes, sig)` → **(d)** freshness gate on `ts` →
  **(e)** conservation reconciliation (§6) → **(f)** only then verbalise into the prompt (Channel A)
  and the augmented pressure (Channel B). Any failure ⇒ message dropped, treated as "no neighbour
  signal", logged.

### 4.2 The schema mismatch (recommend fixing)

The brief's payload is `{"toward": {neighbour: count}}` — a **scalar** count per neighbour. This
spec needs **two** numbers per neighbour (`release` + `queue_forecast`, §1.1). And the
**conservation checker as built** consumes a *different* shape again: `evaluate(claims, observed)`
where both are `dict[(src, dst) -> int]` — a flat dict keyed by a directed-edge **tuple**, with a
**single** int per edge (`conservation.py` lines 105–179).

So three shapes are currently in play:

| Source | Shape | Cardinality |
|---|---|---|
| Brief §2 | `{"toward": {neighbour: count}}` | 1 int / neighbour |
| This spec (wire) | `{"toward": {neighbour: {release, queue_forecast}}}` | 2 ints / neighbour |
| `conservation.py` (built) | `{(src, dst): int}` | 1 int / edge |

**Recommended fix (single source of truth = the wire schema in §4.1):**

1. **Keep the brief's key name `toward`** (preserves intent and any downstream references) but make
   its value an object `{release, queue_forecast}`, not a bare int. Update the brief's one-line
   schema note to match (`{"toward": {neighbour: {"release": int, "queue_forecast": int}}}`).
2. **Adapter, not rewrite, for conservation.** The conservation check only needs the *claimed
   outflow* per edge — which is precisely `release`. Add a thin, pure adapter (in the future bus
   module, **not** inside `conservation.py`) that flattens a verified message to the checker's
   existing input: `claims[(from, B)] = msg.toward[B].release`. This leaves the well-tested
   `conservation.py` contract (`dict[(src,dst)->int]`) untouched — important, since it has full
   adversarial test coverage. `queue_forecast` is *forecast only*; it is **never** fed to the
   conservation check (you cannot conserve a prediction — see §6).
3. **Do not** widen `conservation.py` to carry two ints; that would entangle a forecast with the
   physical-conservation invariant and weaken the detection contract.

This keeps `identity.py`/`registry.py`/`conservation.py` as-is and confines all new shape-handling to
the (still-to-be-written) bus layer.

---

## 5. The coordination hypothesis

**H1 (primary).** On the same network, demand, seeds and shield settings, a **coordinated** SLM
corridor (Channel A prompt augmentation + Channel B augmented pressure) achieves **lower average
travel time and lower average queue** than the **uncoordinated** SLM corridor (today's
`hybrid_controller.py` with `λ=0`, no neighbour block), with the gap statistically significant under
the project's BCa-bootstrap / Holm–Bonferroni plan (brief §4).

**Magnitude we would expect (stated honestly as a prior, not a result):**

- **2×2 synthetic grid:** *small* coordination gains — low single-digit % on ATT/AQL, and possibly
  inside the noise band on some seeds. A 2×2 grid has short links, few hops, and little room for
  platoon anticipation to pay off; CoLLMLight's own ablations show cooperation helps least on
  low-connectivity nets (its low-ICI Jinan/Hangzhou vs high-ICI New York, Table 1/2). The grid is for
  **plumbing validation** ("it coordinates", brief Milestone 2), not for a strong effect.
- **Real Lambeth corridor (~6 SLM junctions in a 10–13-junction arterial):** *larger* gains —
  plausibly **5–15% ATT** and a comparable AQL reduction at peak, where arterial platoons and
  spillback give upstream `release` real predictive value. This is the regime where CoLLMLight and
  CoLight report their biggest cooperative wins (high-connectivity, arterial/Manhattan-like). We
  pre-register the *direction* and the *ordering* (corridor gain > grid gain); the exact % is
  reported, not promised.

**H2 (mechanism / sanity).** Ablating Channel A only (no prompt block, keep `λ>0`) vs Channel B only
(no `λ`, keep block) vs both isolates whether the terse SLM actually *uses* the neighbour context or
whether all benefit comes from the deterministic augmented-pressure term. A defensible, honest result
includes the possibility that **most of the gain is Channel B** — which would itself be a finding
(terse frozen SLMs coordinate weakly through prompts; the deterministic fold carries the load).

**Failure criterion (pre-registered):** if coordinated ≈ uncoordinated on the *corridor* within CI,
the reported claim narrows to "authenticated, conservation-checked coordination is *feasible and
safe* at SLM latency", not "beneficial". The integrity contribution (auth + conservation + audit)
stands regardless of the size of the traffic win.

---

## 6. Honest limitations

1. **Shared predictions can be stale.** Under serialised 2 s inference, a neighbour's message
   describes a window that may have closed by the time we consult it. Mitigation: the freshness gate
   (§1.2) drops any message older than one window; stale data becomes "no signal", never a
   confidently-wrong signal. We **never** blend a stale forecast into the prompt.
2. **`queue_forecast` is a forecast — it can simply be wrong.** A cheap linear roll-forward
   mis-predicts under surges, turning, or signal changes upstream. This is why the forecast is
   **never** subjected to the conservation check (you cannot reconcile a prediction against a
   physical observation) and why the shield, not the forecast, holds final authority. Forecast error
   degrades the *quality* of coordination but cannot breach safety, because Channel B's contribution
   is bounded by `λ` and overridable by the envelope (§3).
3. **The conservation check proves consistency, not truth.** It catches *uncoordinated* spoofs and
   faults (inflated/under-reported/missing edges, `conservation.py` reasons) but, per
   `Xiao2026`/`Xiao2026Residual`, a **coordinated, conservation-respecting** attacker who inflates
   `A`'s claimed `release` and `B`'s observed inflow in lockstep keeps the books balanced and evades
   the check. We carry this caveat explicitly (brief §6). *This is precisely why the auth layer
   matters:* the conservation check bounds *physical* inconsistency; the **signature + registry +
   revoke()** layer bounds *who is even allowed to speak*, collapsing the attack surface to
   compromised-but-registered insiders rather than any network actor. Conservation and auth are
   complements, not substitutes.
4. **Only `release` is conservation-checkable; coordination value lives partly in the unverifiable
   `queue_forecast`.** So an insider can perturb the *forecast* field freely without tripping
   conservation. The mitigations are the bounded `λ`, the shield envelope, and the audit log (every
   accepted/overridden decision is hash-chained, `registry.py::verify_chain`), giving
   non-repudiation and post-hoc attribution even where prevention is impossible.
5. **Terse-SLM coordination may be weak by construction.** A frozen 3.8B model reading two integers
   per neighbour with no reasoning trace may under-use the signal (H2). We do not claim the SLM
   "understands" coordination; we claim the *system* coordinates, with the deterministic fold as the
   floor and the SLM as a (measured) bonus.

---

## Summary

Coordination for terse SLMs is achieved **through context, not cognition**: each busy junction emits
an event-gated, signed message carrying just two integers per neighbour — `release` (vehicles about
to be sent toward that neighbour) and `queue_forecast` (a cheap short-horizon queue projection) —
and a receiver folds them in twice: into the **prompt** (Channel A, geometry pre-resolved so a terse
model only has to add numbers per phase) and into the **shield's augmented pressure** (Channel B,
which guarantees a coordination effect even if the SLM ignores the block). The MaxPressure shield
keeps final, deterministic authority, now with a coordination-aware reference (`pressure'`) and a
spillback safety envelope; with `λ=0`, `δ=∞`, and no block it degenerates exactly to today's
uncoordinated hybrid, giving clean ablations. The design reuses `identity.py`, `registry.py`, and
`conservation.py` untouched; the only code-vs-spec mismatch is the payload schema, which I recommend
fixing by keeping the brief's `toward` key but making its value `{release, queue_forecast}` and
adding a thin adapter that feeds only `release` into the existing conservation contract. The
hypothesis is pre-registered with an honest prior: near-noise on the 2×2 grid, ~5–15% ATT/AQL on the
real corridor, with a stated fallback to a feasibility-and-safety claim if the traffic win is
absent.

**Biggest design risk.** *Under serialised ~2 s inference, neighbour predictions can be stale by the
time the terse SLM consults them, and a frozen 3.8B model given only `{"phase": N}` to emit has no
way to reason about how much to trust a possibly-stale two-integer signal — so the coordination
benefit may collapse to whatever the deterministic Channel-B term contributes, making the "SLM
coordinates" claim hard to defend on its own.* The spec deliberately hedges this risk (freshness
gate, bounded `λ`, Channel-A/B ablation, shield-final authority, and a pre-registered
feasibility-not-benefit fallback), but it remains the central empirical gamble of the coordinated
configuration.

---

### Sources
- CoLLMLight: Cooperative Large Language Model Agents for Network-Wide Traffic Signal Control —
  Yuan, Lai, Liu (HKUST-GZ), 2025. arXiv:2503.11739. https://arxiv.org/abs/2503.11739
- CoLight: Learning Network-level Cooperation for Traffic Signal Control — Wei et al., CIKM 2019.
  arXiv:1905.05717; DOI 10.1145/3357384.3357902. https://arxiv.org/abs/1905.05717
- Project internal: `PROJECT-DECISION-BRIEF.md`; `edge-negotiator/src/{controllers,hybrid_controller,
  slm_agent,identity,registry,conservation}.py`; literary-survey tags `CoT-Faith` (arXiv:2505.05410),
  `Xiao2026`/`Xiao2026Residual`, `Amanullah2026CoopMD`, `Keijzer2021Intersection` (catalogued in
  `06-literary-survey/PROMPT9.md`).
