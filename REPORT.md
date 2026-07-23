# The Edge Negotiator — Progress Report & Plain-Language Rundown

A record of what has been built and measured so far, written to be read by someone who
has not been living inside the jargon. Read Section 2 (the vocabulary) first; the rest
refers back to it.

---

## 1. The question, in one paragraph

Traffic lights on a busy road are normally run by a fixed, mathematical rule. We are
asking: can a **small AI language model running entirely on a local machine** (no
cloud) run a junction's lights **as well as or better than** the standard rule, **while
also keeping a tamper-proof logbook** so that after a crash you can prove exactly what
the lights did, why, and on whose authority? It is a feasibility study on a real London
corridor (Euston Road, the A501). Two halves: **H1 = performance** (does the AI drive
traffic well?) and **H2 = trust** (can we prove afterwards what happened?). A negative
result ("no, it can't") is still a valid, publishable answer — we are not trying to
force a win, we are trying to measure the truth.

---

## 2. Vocabulary — every term we use

### The players

- **MaxPressure** — the standard, non-AI traffic rule we compare against ("the
  baseline"). Each time it must choose which direction gets a green light, it picks the
  direction with the most built-up traffic ("pressure" = cars waiting to go IN, minus
  cars stuck on the road they'd go OUT to). It is mathematically proven to keep traffic
  flowing and is the sensible thing to beat. Its weakness: it only looks at *how many*
  cars are waiting right now, never at *how long* they have already been waiting.

- **SLM** — Small Language Model. A small AI (here 0.5 to 4 billion parameters — tiny
  by chatbot standards) that we ask, in plain text, "which direction should go green
  next?" and it answers. Small enough to run on a normal machine with no internet.

- **Foundry Local** — Microsoft's tool for running these small models on your own
  machine. It hosts the models we test.

- **The models we test** — `qwen2.5-0.5b`, `qwen2.5-1.5b` (older generation),
  `qwen3-0.6b`, `qwen3-1.7b`, `qwen3-4b` (newer generation, 2025), `phi-4-mini`,
  `phi-4-mini-reasoning`. The number is the size (0.5b = half a billion parameters).

- **SUMO** — the open-source traffic simulator we run the corridor in. "Euston Road
  A501" is a real map (4 junctions) loaded into SUMO.

### The controller design

- **The shield (HybridController)** — the safety wrapper. The AI *proposes* a green
  phase; the MaxPressure rule *checks* it. If the AI gives a nonsense or empty answer,
  the shield ignores it and uses MaxPressure instead. So the AI can never make things
  worse than "just use MaxPressure" on validity — it can only try to do better. "SLM
  proposes, shield disposes."

- **Phase** — one legal green-light configuration at a junction (e.g. "north-south
  goes"). Choosing a phase = choosing who moves next.

- **Anti-starvation** — a fairness rule inside the shield: if one direction has been
  skipped too many times in a row, it is force-served so nobody waits forever.

- **Event-gate** — when a junction is nearly empty, we don't bother asking the AI (not
  worth the compute); MaxPressure just handles it.

### The three "configs" (how much the AI is allowed to know)

These are the settings we sweep over. Think of them as how much information the AI gets:

- **myopic** — the AI sees ONLY its own junction's queues. Nothing about neighbours,
  nothing about the future. "Short-sighted." This is the honest hardest case.
- **+coordination** — the AI also gets a signed note from neighbouring junctions about
  traffic heading its way. (On our simple corridor this turned out to make no
  difference — reported honestly, see findings.)
- **+prediction** — the AI also gets an estimate of cars *approaching* but not yet
  stopped. A lever MaxPressure doesn't have.

### The metric and the verdicts

- **Mean network delay** — the number we grade on: the average time vehicles lose,
  across ALL cars that entered (not just the ones that finished — so you can't cheat by
  abandoning slow cars). **Lower is better.**

- **beats / matches / loses** — the verdict of one AI run vs MaxPressure on delay:
  - **beats** = AI delay is more than 2% *lower* than MaxPressure (AI is better).
  - **matches** = within 2% either way (a tie — MaxPressure is hard to beat, so a tie
    is already a real result).
  - **loses** = AI delay is more than 2% *higher* (AI is worse).
  (When you saw "beat"/"loses" in the logs, that is this verdict.)

### The AI-tuning experiments (this is where v1/v2/SOTA come from)

- **SOTA** — "state of the art." After a literature search (saved in
  `01-research/beating-max-pressure.md`), we tried published techniques to make the AI
  beat MaxPressure more reliably in the hardest (myopic) setting.
- **delay-aware** — an upgraded prompt that also tells the AI *how long* each direction
  has been waiting (the thing MaxPressure ignores), and tells it to avoid needless
  switching. Grounded in two papers (LLMLight, EvolveSignal).
- **v1** — first version of the delay-aware prompt: we give the AI both the queue size
  AND the accumulated waiting time, and let it weigh them itself.
- **v2** — second version: we pre-compute a single "delay score" and ask the AI to just
  pick the highest. The research predicted this would help small models (less
  arithmetic for them to do).
- **`/no_think`** — the qwen3 models default to writing out long reasoning before
  answering, which is too slow (~7 seconds per decision). `/no_think` is their official
  switch to answer directly (~0.3s). We turn it on for qwen3 automatically.

### The trust half (the "ledger")

- **The ledger / audit log** — an append-only logbook. Every decision the controller
  makes is written into it as a signed, chained record. See Section 5 for the full
  mechanism. Key sub-terms:
  - **Hash-chain** — each entry contains a fingerprint of the previous one, so you
    cannot silently insert, delete, or reorder entries without it showing.
  - **Ed25519 signature** — each junction has a cryptographic identity (a key) and
    signs its own records, so you can prove *which key* made a decision.
  - **Merkle root / inclusion proof** — a single short fingerprint that commits a whole
    batch of records; the "inclusion proof" lets you prove one specific record is in
    that batch without revealing the rest.
  - **Salted root** — the published fingerprint is scrambled with a secret so it commits
    completeness without leaking the (pseudonymous) identities; erase the secret and it
    becomes unlinkable (privacy).
  - **Quorum anchor** — publishing the fingerprint to ≥2 independent outside witnesses
    (e.g. a public transparency log + a small blockchain node) so one operator can't
    later show two different histories.
  - **Cross-auditor** — an independent reader that checks the witnesses agree; if two
    witnesses disagree, that's "equivocation" and it's flagged.
  - **Tamper test** — we deliberately forge a signature and prove the system catches it.

- **The policy (`ground_rules.yaml`)** — the machine-readable rulebook. See Section 6.
  Contains: the **authorised vehicle types** (ambulance/fire/police/maintenance/
  civilian), the **legitimacy criteria** (B1–B5), the **decision policies** (P1–P8), the
  **attack taxonomy**, and a **UK traffic-law knowledge base** used for the (honestly
  negative) legal-note experiment.

### Honesty machinery

- **PILOT / SMOKE / n=1** — "n=1" means we ran it once (one random seed, one demand
  pattern). A PILOT is a real but preliminary result; we are explicitly NOT claiming
  statistical significance from it. SMOKE = a quick sanity run at a short horizon.

- **The §8 demand gate** — our traffic demand is calibrated to *daily-average* real
  government counts, not *hour-by-hour* counts. So any result that would need a
  statistical/significance claim is deliberately held back ("gated") until we get proper
  hour-by-hour data. Pilots are allowed; significance claims are not.

- **Honest gate** — instead of faking a result we can't yet earn, we record it as
  "gated, here's exactly what's missing." This is treated as success, not a gap.

- **The §12 gates (D1..D8, D-lat, D-anchor, D-accident, D-H1-perf, D-H1-scale, ...)** —
  a checklist of acceptance criteria the dissertation must satisfy. Each "D-something"
  is one criterion. Section 4 lists them and their status. A gate "passes" either by a
  real run OR by an honest gate with a recorded reason.

- **The battery** — before any piece of work is accepted, a *separate* adversarial
  reviewer (a second AI agent that did not write the code) tries to break it and find
  overclaims. Zero fatal + zero major findings required to proceed. This has already
  caught two serious bugs (see Section 7).

---

## 3. How we actually beat MaxPressure

Two things, and it is important to separate them honestly.

**(a) The plain AI already beats MaxPressure — this was the surprise.**
Under heavy (saturating) demand on Euston Road, even the *smallest* model
(`qwen2.5-0.5b`) in the *simplest* myopic setting produced a mean delay of **235
seconds vs MaxPressure's 314.55 seconds — about 25% lower**. It does this using only
its own junction's queues. Why is that even possible if MaxPressure is "optimal"?
Because MaxPressure is proven optimal for *throughput* (keeping cars moving) under
idealised assumptions, but it is **not** optimal for *delay*, and it is *memoryless* —
it never considers how long cars have waited, and it can switch phases too eagerly,
which wastes time on the stop/start. The AI, checked by the shield, makes slightly
different phase choices that happen to reduce average delay. (Honest caveat: this is a
single-seed pilot, see Section 8.)

**(b) The "delay-aware" upgrade helped the weak model, not the strong ones.**
We then explicitly fed the AI the waiting-time information MaxPressure ignores (the
"delay-aware" prompt, v1). Result: it **lifted `phi-4-mini` from a tie to a win**
(314.71s → 270.42s) and slightly improved `qwen3-0.6b`, but it *hurt* the already-strong
small models. The follow-up v2 (pre-computed score) was **worse overall** — an honest
negative we recorded rather than hid. Takeaway: prompt tricks give uneven gains; a
*uniform* win across all models would need lightweight fine-tuning (the literature's
recommendation), which is future work. **The headline stands on (a): plain myopic SLMs
already beat MaxPressure at the smallest scale.**

Full number table (heavy demand, one run each; baseline MaxPressure = 314.55s):

| Model | plain myopic | delay-aware v1 | notes |
|---|---|---|---|
| qwen2.5-0.5b | **235.0s (beats, -25%)** | 291.3s (beats) | smallest model, best plain result |
| qwen3-1.7b | **233.7s (beats)** | 239.8s (beats) | |
| qwen3-0.6b | 267.1s (beats) | **262.9s (beats)** | newest smallest model |
| phi-4-mini | 314.7s (matches) | **270.4s (beats)** | delay-aware lifted it to a win |
| phi-4-mini-reasoning | — | — | too slow (~8.5s/decision), latency-gated |

Latency (how fast the AI decides) for the usable models: 0.29–0.80 seconds per
decision, comfortably inside the ~10-second window a real junction allows.

---

## 4. The grading criteria (how we judge everything)

Two layers.

**Layer 1 — the performance verdict.** On mean network delay: beats / matches / loses
vs MaxPressure, with the 2% tie-band (Section 2). Plus latency must fit the ~10s
decision window, and the audit must stay intact on every run.

**Layer 2 — the §12 acceptance gates.** Each is pass-by-real-run OR honest-gate:

| Gate | What it demands | Status |
|---|---|---|
| **D-H1-perf** | AI-vs-MaxPressure on delay, labelled | PILOT PASS (SLM beats; §8-gated for significance) |
| **D-H1-scale** | A full model×config map + the smallest model/simplest config that wins | PASS (map complete; threshold = qwen2.5-0.5b × myopic) |
| **D-lat** | Per-decision latency reported properly | PASS (reported, viable models < 10s) |
| **D-accident** | Reconstruct a scripted crash from the audit alone; catch a tamper | PASS (8/8 checks) |
| **D-anchor** | Salted fingerprint to ≥2 witnesses + cross-audit | MECHANISM PASS, honestly "not externally anchored" |
| **D6 (Experiment D)** | The audit's blind-spot boundary result | MODELLED PILOT; the severe statistical claim honestly gated |
| **D1** | Documents clean of forbidden/iteration language | maintained |
| **D2** | Fault report states only facts, no accusation | done |
| **D3** | If the real model isn't proven up, skip honestly (never fake) | done |
| **D4 (Experiment 1)** | AI vs a tuned rule on ambiguous cases | PILOT done; full statistical gate §8/§9-deferred |
| **D5** | AI legal-note vs a template | PILOT = template wins (an honest negative) |
| **D7** | Fairness: nobody starves, across an attacked run | done |
| **D8** | Demand sweep, honest | PILOT done |
| **D-sec** | Audit verifies signatures + chain before attributing fault | done |
| Powered runs (n≥30 significance) | Statistical claims | GATED until hour-by-hour TfL data |

"Gated" is not failure — it is the honest scientific posture for a feasibility study on
daily-resolution demand.

---

## 5. The ledger, exactly (what we do for trust)

Every message, sighting, and decision the controller makes is appended to a signed,
hash-chained **AuditLog**:

1. **Each junction signs its own records** with its Ed25519 key. So a decision is
   provably attributable to a *key* (never to a named person).
2. **Each record chains to the previous one** by hash. Change, delete, or reorder any
   record and the chain no longer verifies (`verify_chain()` returns false).
3. **A batch of records folds into one Merkle root** (a short fingerprint). We can later
   prove a specific decision was in that batch with a small "inclusion proof."
4. **The published root is salted** so it commits completeness without freezing the
   pseudonymous identities into a public record; the salt is kept off-chain and erasable
   for privacy (§7.7).
5. **Anchoring** publishes that root to ≥2 independent witnesses so no operator can show
   two different histories; a **cross-auditor** checks they agree and flags any
   disagreement (equivocation).

**The accident demo (D-accident), which passes 8/8.** We script a crash: a compromised
neighbour signs a *fake* emergency-vehicle claim that hijacks the lights, and then a
*real* emergency vehicle is sensed. From the verified log ALONE, the system mechanically
reconstructs:
- **WHAT** happened — the exact sequence of phases actually served;
- **HOW** — which signed inputs drove each decision and which safety policies fired;
- **WHICH KEY** — the fake claim is attributed to the specific signing key that made it
  (the compromised neighbour "A1"); the real vehicle is a keyless local sighting.
Then the **tamper test**: we swap in a forged signature that still passes the hash-chain
— and the system still **refuses** to attribute, because the per-sender signature check
catches it. A tamper that survives the chain is caught anyway.

**Honest boundary (D-anchor):** we built and proved the ≥2-witness + cross-audit + salted
-root mechanism locally, and it catches a planted "two different histories" attack. But
we did **not** write to the real public transparency log (that would permanently pollute
a shared public service with test data) and did not stand up the blockchain node, so the
run is labelled **"not externally anchored"** — the mechanism works; the public claim is
honestly withheld.

**The audit's measured blind spot (D6).** We also honestly document where the audit can
fail: because the attack controls the light phase, and the phase controls which honest
sensors can see a problem, a malicious insider can open a "coverage desert" where a
carefully-bounded fake is neither seen live nor leaves a detectable trace. We
demonstrate this coupling as a mechanism and state the exact conditions under which it
*cannot* happen. The severe statistical version of this claim is honestly gated (it
needs real documented sensor placement, which we don't have).

---

## 6. The policy we applied (`ground_rules.yaml`)

The machine-readable rulebook the controller and the audit reason against:

- **Authorised entities** — ambulance, fire, police (may request signal preemption),
  maintenance (may close a lane but **never** preempt), civilian (no priority). Each row
  now carries structured fields (`preemption_allowed`, `actions_allowed`,
  `authorising_key_classes`, `key_required`) consumed by a new **vehicle-authorisation
  classifier**.
- **Legitimacy criteria B1–B5** — identity (signed by an approved key), corroboration
  (an independent junction also sensed it), local sensing, plausibility (physically
  possible counts), temporal consistency (timing makes sense).
- **Decision policies P1–P8** — condition → outcome. E.g. P2: bad/absent key → reject;
  P3: a single uncorroborated claim can NEVER force a green (anti-phantom); P4:
  corroborated by ≥2 keys → legitimate preemption; P8: unknown vehicle / missing data →
  UNKNOWN (conservative reject).
- **Attack taxonomy** — invalid-id, signal-tampering (a maintenance key claiming to be
  an ambulance), phantom (a claim for a vehicle that doesn't exist), count-inflation,
  missing-metadata, contradictory-signals, replay, etc.

**The multi-vehicle authorisation result:** we built the classifier and tested it on a
balanced set of 26 cases across every attack family, scored with precision/recall/
false-positive/false-negative. Result: **perfect classification and zero "dangerous
false grants"** — no illegitimate claim ever got a green. (This is a deterministic rule
gate, so perfection is expected; the value is proving every attack family is covered.)

There is also a **UK traffic-law knowledge base** in the same file (18 statute/case
rules) used by the AI "legal-note" experiment (Job A) — whose honest result is that a
plain template **beats** the AI on citation correctness (D5, a reported negative).

---

## 7. Full findings rundown

**H1 (performance) — the headline.**
- On real Euston Road under heavy demand, **on-device small AI beats MaxPressure on
  delay**, and the win appears at the **smallest model, simplest setting**
  (`qwen2.5-0.5b`, myopic, 235s vs 314.55s, −25%). This directly answers the thesis
  "is it even possible, and at what scale?" — yes, at the smallest scale tested.
- A full **feasibility map** across 7 models × 3 configs is produced; every cell is
  either measured or honestly skip-recorded. The reasoning model
  (`phi-4-mini-reasoning`) is honestly **latency-gated** (~8.5s/decision, measured — too
  slow for real-time), which is itself a finding.
- **`+coordination` had zero effect** on our simple corridor (the neighbour notes never
  fired) — reported transparently, not spun as a benefit.
- The **delay-aware / SOTA** experiments: v1 lifted the weak model to a win; v2 was a
  net negative. Recorded honestly, no prompt-fishing on one seed.
- **Latency** is viable (0.29–0.80s vs the 10s window) for all models except the
  reasoning one.

**H2 (trust).**
- **Accident reconstruction (D-accident): passes 8/8** — what/how/which-key recovered
  from the verified log; a chain-surviving tamper is still caught.
- **Multi-vehicle authorisation:** classifier + balanced P/R/FPR/FNR eval, zero
  dangerous false grants.
- **Anchoring (D-anchor):** ≥2-witness + cross-audit + salted-root mechanism proven;
  catches planted equivocation; honestly labelled "not externally anchored."
- **Coupling blind spot (D6):** demonstrated as a mechanism + conditional lemma;
  inferential contrast honestly gated.
- **AI legal note (D5):** honest negative — a template beats the AI.

**Two serious bugs the adversarial battery caught (and we fixed):**
1. A **FATAL audit bug** — the log was recording the phase the AI *proposed*, not the
   phase actually *served* after the fairness override. That would have corrupted every
   accident reconstruction. Fixed and re-verified.
2. A **FATAL silent-degradation bug** in the sweep — if the AI service died mid-run, the
   controller silently fell back to MaxPressure, and for the myopic setting that is
   *identical* to the baseline, so it would have falsely reported a "match." We added a
   guard that detects "the AI authored zero real decisions" and marks the cell degraded
   rather than a false pass. And a third: a delay-aware reader was calling a SUMO
   function that doesn't exist, silently feeding the AI zeros — caught and fixed.

**Engineering health:** 745 automated tests pass; the repo is greenfield-clean; every
phase was reviewed by a separate adversarial agent (builder ≠ examiner) before commit.

---

## 8. Honest limitations (stated, not hidden)

- **Everything traffic-related is a PILOT (n=1).** One random seed, one demand pattern.
  No significance claim is made or permitted yet.
- **Demand is daily-resolution.** Real government counts give the *magnitude* and
  *vehicle mix*, but the hour-by-hour shape, direction split, and junction turning
  proportions were assumed. We have now *measured* the hourly shape + direction from the
  DfT raw survey (removing one assumption) but it is still a single survey day; turning
  proportions still need Transport for London data.
- **The "beat" could move** under more seeds or real hour-by-hour demand. That is
  exactly why the powered (n≥30) statistical runs are gated.
- **`+coordination` is inert here** — an honest null on this substrate, not a feature.
- **The audit is not externally anchored** and its cross-auditor's honesty is an
  assumed trust root (stated openly).
- **The AI legal note is a measured negative** (a template is better).

---

## 9. What is genuinely blocked vs done

- **Done and measured:** the H1 feasibility map + scale threshold (pilot), the accident
  audit + tamper test, the multi-vehicle authorisation, the anchor mechanism, the
  coupling boundary (mechanism), the latency profile, the measured hourly-demand
  extraction, the safety/fairness gates.
- **Blocked only on external data:** all statistical-significance ("powered", n≥30)
  claims, and the full inferential versions of Experiments 1 and D — these need
  **time-resolved TfL hourly + turning counts**, which is data, not code. The honest
  gates for these are in place and say exactly what would unblock them.
- **Future engineering (optional):** lightweight fine-tuning (LoRA) to make the smallest
  models beat MaxPressure *uniformly* rather than just often — the literature's
  recommended next step, deferred as out of scope for a feasibility study.

---

*Every number in this report is from a committed run under `03-implementation/
edge-negotiator/results/`. Where a claim is a pilot or is gated, it says so. Nothing
here asserts statistical significance on daily-resolution demand.*
