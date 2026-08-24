# Pre-submission checklist (COMP0234, deadline 2026-09-07)

## Blocking — needs information only Ebenezer can get (Moodle / module lead)
- [ ] **Word limit** — confirm the COMP0234 figure. Current body text is **~13,200 words**
      (excl. front matter, captions, bibliography, appendices). Safe if the limit is 14k;
      **over if it is 12k**. If 12k: cut Ch.2 (2.2k) and Ch.6 guard/robustness prose first.
- [ ] **Declaration wording** — replace the placeholder on the title page
      (`frontmatter.tex`, the `\todo` on the `\begin{titlepage}` block) with the exact
      departmental text.
- [ ] **UCL email format** — verify the address on the article title block
      (`05-article/article.tex`, `\todo{verify email}`).
- [ ] **Is the research article a required deliverable?** Not stated in the public module
      catalogue; confirm with the module lead. It is written either way.

## Blocking — mechanical, do LAST
- [ ] **Flip draft mode off**: `preamble.tex` → `\newif\ifdraft\draftfalse`.
      This hides all `\todo{}` and `\evidence{}` markers. Verify no red text survives
      in the PDF afterwards.
- [ ] **D1 framing grep** (MASTER-SPEC §5.2/§12) — must run LAST, after all writing edits.
      Scope: live docs excluding `**/.venv*/`, `.olive-cache/`, `01-research/papers/*.pdf`,
      LaTeX build artifacts. Allowlist amended 2026-08-21 (§12 D1 items (g)–(i)) to cover
      negation/disclaimer uses of "verdict" and legal-doctrine "liability" in the writing.
- [ ] **Clean rebuild to convergence**: `latexmk -C && latexmk -pdf` twice; confirm
      0 `!` errors, 0 undefined citations, 0 undefined references in `main.log`.
- [ ] Remove the working note at the top of each chapter
      (`% WORD BUDGET: ... COMP0234 limit UNVERIFIED`).

## Content — outstanding
- [ ] **Calibrated Bloomsbury results** (running 2026-08-24): fold the three arms into
      Ch.6 alongside the oversaturated cells as a demand-sensitivity comparison, and
      revisit the "fine-tuning repairs stock harm" claim in light of whether the harm
      survives in a free-flowing regime.
- [ ] Update `tab:guards` and `tab:robust` with the calibrated rows.
- [ ] Re-check every cross-reference after the above edits.

## Verified complete
- [x] Bibliography checked against source PDFs; 3 mis-attributions fixed
      (zaidi wrong arXiv id → T-ITS 2016; forgetting2024 = Kalajdzievski not Luo;
      gregoire title/authors), 13 placeholder author lists replaced. 4 entries
      documented as locally unverifiable.
- [x] Test suite: 819 passed, 27 skipped, 0 failed (2026-08-24).
- [x] Authorship metrics recomputed on correct denominators; all occurrences updated.
- [x] MaxPressure reversal retracted at n=30 and reported as a self-retraction.
- [x] Euston peak-hour reported as measured harm, not a null.
- [x] CIs + Wilcoxon added with multiple-comparison caveat.
- [x] Throughput guard metrics reported; Bloomsbury scoped as gridlock-regime.
- [x] Latency claims replaced with measured per-cell table.
- [x] Every offline-table cell backed by a committed evaluation artifact.

## Build
```
cd 04-dissertation && latexmk -pdf main.tex     # 40pp
cd 05-article      && latexmk -pdf article.tex  # 4pp
```
Note: never run two `latexmk` builds in the same directory concurrently — it corrupts
the `.aux`/`.xref` and produces spurious errors.
