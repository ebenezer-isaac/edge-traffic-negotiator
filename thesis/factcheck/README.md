# Deterministic fact-check harness

Every numeric token in the report body is traced to a quantity computed from
the committed experiment artifacts, with a provenance record, or is
explicitly allowlisted as a non-result (literature figure, hardware id,
statute, seed, LaTeX constant). No model is in the loop: everything is
Python over `03-implementation/edge-negotiator/results/`.

## Run

```
cd 04-dissertation/factcheck
python check.py     # extract claims -> compute facts -> FACTCHECK-REPORT.md, factcheck.json, facts.json
python tables.py    # positional audit of every result-table cell -> TABLE-AUDIT.md
```

Both are pure functions of the `.tex` sources and the results directory.
`facts.json` records a 12-hex sha256 prefix of every artifact read.

## Files

| file | role |
|---|---|
| `extract.py` | walks `main.tex` through `\input`, strips comments, TikZ, `\label/\ref/\cite`, lengths and column specs, and emits every numeric token with `file:line` and its sentence |
| `facts.py` | the registry: closed-loop effects (one-sample *t* on per-seed relative change, CI on the same; paired *t* on absolute delays and Wilcoxon also registered), authorship denominators, guard metrics, latency under five explicit definitions, offline accuracies, dataset build counts, retention, authorisation re-test, EV metrics, trust battery, calibration probes, failure forensics, crash-law, ANOVA |
| `facts_extra.py` | powered catalogue stock arms (seeds 1..30), catalogue-vs-compiled provenance, phi-4-mini-reasoning p99s, teacher cross-audit agreement, decision battery, horizon probe per seed, exploratory-sweep bests, generic numeric-leaf registration of the remaining experiment JSONs (backtrace by JSON path) |
| `check.py` | matches tokens to fact renders, applies `allowlist.json`, writes the report |
| `tables.py` | maps each cell of the main tables to the fact it claims to print (a coincidental match elsewhere in the text cannot mask a wrong cell) |
| `allowlist.json` | token + context regex + reason for every non-result number |

## Conventions (from EXAMINER-REVIEW-PROMPT.md)

* `frontier_raw/BASELINE__*` is MaxPressure (asserted: `served_by.slm == 0`).
* Fixed-time floor only in `experiment_fixedtime_{seed30,calibrated,guards}.json`.
* Evaluation seeds `{1..30} \ {3,7,11,29} ∪ {31..34}`; stock catalogue arms use seeds 1..30.
* `ft0` = stock control, `ft1` = deployed student, `phi4mini-gen-gpu` = 3.8B student; config `sota`.
* authored share = `served_by.slm/decisions`; acceptance = `slm_proposal_served/slm_valid_proposals`;
  divergence = `slm_diverged_and_served/slm_proposal_served` (the harness field named
  `authored_share` holds acceptance and `override_rate` holds divergence).
* A CI may be printed either as rounded bounds or as round(mean) ± round(half-width); both renders are registered.
* Ties in rounding (e.g. 3.25) accept both half-even and half-up renders.

## What it found on 2026-09-07 (first full run)

Fixed from artifact values: Euston ft vs MaxPressure −3.9 → −3.8; stock Euston
*p* .222 → .221; stock oversaturated CI upper +4.2 → +4.1; robustness *p*
.354 → .355 and .358 → .365; horizon-probe teleports 830 → 834; Euston
peak-hour completion 44.3 → 45.3 (stale pre-correction figure); the §6.2
exploratory-sweep sentence mislabelled its comparator (MaxPressure, not the
fixed-time floor, which has no grid cells). Two latency definitions had been
mixed in prose (pooled median 1.64 s vs median-of-cells 1.75 s); the table
caption now states its definition and the prose cites the table.

## Limits

Token matching verifies that a printed number *is* an artifact-derived
quantity; the table audit verifies *which* quantity for every table cell.
Prose sentences can still attach a verified number to the wrong noun; the
backtrace in `FACTCHECK-REPORT.md` lists every fact that renders to each
token so a reader can judge. Numbers stated as operational observations
(the crash row index) are allowlisted with that reason, not verified.
