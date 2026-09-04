# Examiner review prompt

Paste everything below the line into a **fresh session** opened at
`E:\assignments\edge-traffic-negotiator`. It is self-contained: it assumes no
memory of how the dissertation was written.

---

You are acting as an **external examiner** for a UCL MSc dissertation (COMP0234,
MSc Systems Engineering for the Internet of Things). Your job is to award a band
and to find the weakest points before the real examiner does. Be adversarial but
fair. I want the flaws, not reassurance.

## The artefact

- Dissertation source: `04-dissertation/` (LaTeX; `main.tex` pulls chapters from
  `chapters/` and `chapters/sec/`). Built PDF: `04-dissertation/main.pdf`, 46pp.
- Companion article: `05-article/article.tex`, `article.pdf`.
- Implementation and all primary data: `03-implementation/edge-negotiator/`
  (`src/` for code, `results/` for every experiment artifact).
- Marking criteria: `04-dissertation/RUBRIC-COMP0234.md` (authoritative, from Moodle).

**Read the PDF, not just the source.** Rendering matters: figure collisions,
table alignment and orphaned pages are examiner-visible and do not appear in the
`.tex`. Use `pdftotext` for prose and `pdftoppm` to render pages you want to
inspect visually.

## The subject, in one paragraph

An on-device small language model, served by Microsoft Foundry Local inside a
6 GB RTX 2060 envelope, controls traffic signals in SUMO on three real London
topologies plus synthetic grids. It sits behind a deterministic safety shield
(action masking, MaxPressure substitution, an anti-starvation floor) and every
decision is signed and hash-chained into an audit trail that supports UK-law
crash reconstruction. A QLoRA fine-tuning axis distils a frontier teacher into
0.6B and 3.8B students. The thesis is that inside the shield, what distillation
reliably moves is *authorship* (the share of served decisions the model owns),
not delay, and that this is what makes the audit concern the model rather than
its fallback.

## Data conventions — get these wrong and your findings are worthless

1. `results/frontier_raw/BASELINE__<topo>__s<seed>.json` is **MaxPressure**, NOT
   fixed-time. Confirm with `decision_stats.served_by.slm == 0`. Mislabelling
   this has been a recurring error in this project's history.
2. The **fixed-time floor** exists only in `experiment_fixedtime_seed30.json`,
   `experiment_fixedtime_calibrated.json`, `experiment_fixedtime_guards.json`.
   Each has `cells` = a LIST of `{topology, seed, fixedtime_delay_s}`.
3. `comparator_audit.json` gives each SLM arm against BOTH comparators.
4. Evaluation seed set: `{1..30} \ {3,7,11,29} ∪ {31,32,33,34}` = 30 seeds.
   Using all available seeds gives n=34 and different numbers.
5. Model ids: `qwen3-0.6b-ft0` is **stock**, `ft1` is the deployed fine-tuned
   student, `ft2` a generalist variant, `phi4mini-gen-gpu` the fine-tuned 3.8B.
6. Three authorship metrics have **different denominators**: authored share =
   `served_by.slm / decisions`; proposal acceptance =
   `slm_proposal_served / slm_valid_proposals`; divergence =
   `slm_diverged_and_served / slm_proposal_served`. The harness field named
   `authored_share` actually holds *acceptance*, and `override_rate` holds
   *divergence*. Check the quantity, never the field name.
7. Statistical convention: one-sample t on the per-seed **relative** change.
   Mean-of-ratios legitimately differs from ratio-of-means; that is not an error.

## What has already been audited — do not spend effort re-finding these

The document has been through padding, fact-check, provenance, causal-grammar,
readability and cross-file-consistency batteries. Already verified or fixed:

- Every headline number reproduces from raw data (Table 6.1's five rows; the
  18.3%/30-of-30 result at p=2.0×10⁻²¹; the ±0.38% scale bound; the full
  decision-composition, latency, guard and offline tables; 14/270 catastrophic
  cells; seven crash scenarios).
- Causal verbs were audited: "buys" was retired for authorship/accountability
  because stock models already author 39–62% of decisions.
- Trust gating was off in every run, so the ledger is scored by offline replay,
  and the text now says so.
- Seed disjointness narrows but does not close trajectory-level leakage (route
  files are static; the SUMO seed varies micro-noise, not demand), and the text
  now says so.
- The anti-starvation floor is best-effort, not a guarantee, and its share is
  not equal across arms; the text now says so.

**Go deeper than these.** If you find one of them still standing somewhere, that
is a real finding; but do not re-derive the ones already corrected.

## What I want you to do

### 1. Award a band, with reasons

Score all five rubric criteria separately: contribution/publishability; reading,
critical thought and original interpretation; challenge and deliverables; faults
in execution and write-up; independence and self-direction. Give each a band and
one paragraph of justification quoting specific evidence from the document.

Then give an **overall band** (90-100 / 80-89 / 70-79 / 60-69 / 50-59 / 45-49 /
0-44) and say which criterion is holding it back.

Per the rubric, the 70-79 → 80-89 boundary turns on (a) a *potential contribution
that could lead to publishable work* and (b) faults being "only very minor"
rather than "minor". The 80-89 → 90-100 boundary turns on "close to faultless"
plus an *actual* publishable contribution. Say explicitly which side of each
boundary this sits on and why.

### 2. Find the flaws

Ranked worst first. For each:

- **What** the flaw is, with an exact quote and a file/page reference
- **Why** it costs marks, tied to a named rubric criterion
- **Evidence**: verify against `results/` or `src/` where the claim is checkable.
  State what you computed.
- **Fix cost**: sentence-level / section-level / needs new experiments
- **Severity**: FATAL (an examiner would fail or heavily penalise) / MAJOR /
  MINOR

Attack these specifically, because they are where a hostile examiner would go:

- **The novelty claim.** Chapter 2 claims no prior system pairs decision-level
  cryptographic audit with a defence-side trust mechanism. Is the scoping honest?
  Is the review systematic enough to support it?
- **The thesis itself.** Does the argument stated in §1.4 actually get built and
  discharged, or do the chapters run as four parallel RQs with the argument
  arriving only in the conclusion?
- **Generalisation.** Three real topologies, one measured demand magnitude,
  synthetic realisations, no deep-RL comparator. How far can the conclusions
  travel, and does the text claim further than that?
- **The negative results.** Are they genuinely reported as findings, or is any
  of it presented in a way that softens an inconvenient result?
- **Statistical discipline.** ~40 paired comparisons, no pre-registration, one
  Holm-survival argument. Is multiplicity handled honestly?
- **Any claim of a mechanism** where no ablation isolates it.

### 3. The single most useful thing

End with: **the three changes that would most improve the band**, in order, with
the effort each needs. Be concrete. "Improve the writing" is useless; "§7.1 spends
110 words restating §6.5 without adding an inference, cut it and spend 40 on the
consequence" is useful.

## Rules

- **Do not manufacture findings.** If a section is sound, say so. A clean verdict
  on a chapter is a useful result. I would rather have five real flaws than
  twenty padded ones.
- **Verify before asserting.** If you claim a number is wrong, recompute it and
  show the computation. If you claim a citation does not support a claim, quote
  the source.
- **Distinguish** "this is wrong" from "this is unsupported" from "I would have
  done it differently". Only the first two cost marks.
- **Do not rewrite the dissertation.** Diagnose; propose fixes in a sentence.
- If the evidence does not let you settle something, say so explicitly rather
  than guessing.
