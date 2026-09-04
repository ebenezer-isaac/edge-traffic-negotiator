# Pre-submission checklist (COMP0234, deadline 2026-09-07)

## Blocking — needs information only Ebenezer can get (Moodle / module lead)
- [ ] **Declaration wording** — replace the placeholder on the title page
      (`frontmatter.tex`, the `\todo` on the `\begin{titlepage}` block) with the exact
      departmental text.
- [ ] **Word limit** — confirm the COMP0234 figure. Target in force is **12,000**
      (Ebenezer, 2026-09-03). Body text was ~13,500 after the comparator corrections;
      a compression pass across Ch.1--3 and Ch.5--7 is in progress.
- [ ] **Is the research article a required deliverable?** Not stated in the public module
      catalogue; confirm with the module lead. It is written either way.

## Blocking — mechanical, do LAST
- [ ] **Flip draft mode off**: `preamble.tex` → `\newif\ifdraft\draftfalse`.
      Then verify: `pdftotext main.pdf - | grep -E 'TODO|evidence:'` returns nothing.
- [ ] **D1 framing grep** (MASTER-SPEC §5.2/§12) — must run LAST, after all writing edits.
      Scope: live docs excluding `**/.venv*/`, `.olive-cache/`, `01-research/papers/*.pdf`,
      LaTeX build artifacts. Allowlist per §12 D1 items (a)–(i).
- [ ] **Clean rebuild to convergence**: `latexmk -C && latexmk -pdf` twice; confirm
      0 `!` errors, 0 undefined citations, 0 undefined references in `main.log`.
- [ ] Remove the working note at the top of each chapter
      (`% WORD BUDGET: ... COMP0234 limit UNVERIFIED`).
- [ ] Re-run the number/hedge guard and reconcile every diff:
      `python <scratchpad>/numsnap.py check pretrim`.

## Content — outstanding
- [ ] **Euston peak-hour calibrated sweep** (running 2026-09-03, ~04:30 ETA):
      qwen ft1 + ft0, 30 disjoint seeds, config `sota`. The fixed-time floor for that
      map is already complete at n=30. This is the uniformity test the calibration
      defence promises; report it whichever way it falls and delete the `\todo` in
      `sec:res-guards`. Early signal at n=3: the fine-tuned arm is +10.6% against the
      floor, i.e. calibration does NOT rescue the corridor.
- [ ] Apply the twelve verified fixes queued in `<scratchpad>/PENDING-FIXES.md`
      (they were blocked on the compression agents holding the chapter files).

## Verified complete
- [x] **Comparator mislabelling corrected (2026-09-03) — the big one.**
      `frontier_raw/BASELINE__*.json` is the **MaxPressure** arm, not fixed-time
      (`experiment_fixedtime.py:78` says so). `tab:closedloop-full`, `tab:robust`,
      `tab:calib`, the abstract, intro, discussion and conclusion all said
      "vs fixed-time" while carrying MaxPressure numbers. Recomputed independently
      and confirmed. The missing fixed-time floors were then measured
      (`experiment_fixedtime_calibrated.json`, `experiment_fixedtime_guards.json`,
      plus seeds 31–34 added to `experiment_fixedtime_seed30.json`) so every
      comparison is now n=30 against BOTH comparators, which is what Ch.5 promised.
      Net effect: Old Street becomes a significant win (−9.7 to −11.6%, p ≤ .002)
      where it had been reported as a null; the calibrated grid becomes ft −8.8%
      vs the floor and stock +11.9%. The 18.3% head-to-head is unaffected.
      One claim retracted: distillation does NOT repair the Euston corridor deficit.
- [x] **Backpressure citation restored to its true source.** The heavy-load Lyapunov
      theorem and both quoted phrases are Gregoire et al., *Back-pressure traffic
      signal control with unknown routing rates* (arXiv:1401.3357), verified against
      the cached PDF in `01-research/papers/`. They were attributed to Zaidi et al.
      **The earlier checklist entry claiming the Zaidi citation had been "fixed" to
      T-ITS 2016 was itself the error** — no Zaidi PDF exists in the repo at all.
      New bib key `gregoire2014routing`; `zaidi2014backpressure` is now uncited.
- [x] Statistics made internally consistent: a one-sample $t$ on the per-seed
      **relative** change (matching the reported CI) is now used throughout, replacing
      a mix of that CI with a paired $t$ on **absolute** delays. This flips the Euston
      MaxPressure-vs-fixed-time cell to significant (p=.025); the disagreement with the
      absolute-scale test is disclosed in `sec:res-maxpressure`.
- [x] Article corrected to match: comparator columns, abstract, conclusion, limitations,
      the self-contradictory divergence definition, a dangling `fig:auth` reference,
      and the `\todo{verify email}` that rendered in red.
- [x] `\euro` was undefined and had been breaking the dissertation build outright;
      `textcomp` + a `\providecommand` fallback added to `preamble.tex`.
- [x] Divergence upper bound corrected 0.18 → 0.17 (config-filtered, 30 disjoint seeds).
- [x] Test suite: 819 passed, 27 skipped, 0 failed (2026-08-24).
- [x] Authorship metrics recomputed on correct denominators; all occurrences updated.
- [x] MaxPressure reversal retracted at n=30 and reported as a self-retraction.
- [x] Euston peak-hour reported as measured harm, not a null.
- [x] Throughput guard metrics reported; Bloomsbury scoped as gridlock-regime.
- [x] Every offline-table cell backed by a committed evaluation artifact.

## Known-open, decide before submission
- **ft1 vs ft2.** The offline table's "Qwen3-0.6B generalist ft" row is checkpoint
  **ft2** (all-format, 59,533 examples); every closed-loop result uses **ft1**
  (sota-only, 14,493 examples, 97.4% on sota). Both must be named. Queued.
- **Trust RQ4.** "A blatant attack costs more against fine-tuned controllers" holds in
  four of six controller-map cells, is exactly equal in one and smaller in one.
  Soften to a tendency. Queued with the numbers.

## Build
```
cd 04-dissertation && latexmk -pdf main.tex     # ~40pp
cd 05-article      && latexmk -pdf article.tex  # 4pp
```
Note: never run two `latexmk` builds in the same directory concurrently — it corrupts
the `.aux`/`.xref` and produces spurious errors.
