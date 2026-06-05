# Evaluation Harness Design — The Edge Negotiator (Wk9-10 results generator)

This is the integration-ready "part" that produces the dissertation's **results
matrix** end-to-end: one harness, both halves of the thesis (traffic performance
AND security), emitting a machine-readable JSON and a markdown report.

- Harness (reusable library): [`src/evaluation.py`](../src/evaluation.py)
- CLI: [`src/run_evaluation.py`](../src/run_evaluation.py)
- Tests: [`tests/test_evaluation.py`](../tests/test_evaluation.py)

It does **not** edit any existing file. It composes the already-validated
building blocks through their public APIs:
`run_metrics_sweep.run_one` (SUMO + StubAgent + the required write flags +
`metrics.py` scoring), `metrics.parse_tripinfo`/`matched_diff`,
`stats.summarize_sweep`/`bca_bootstrap`/`permutation_test`, and
`run_attacks.run_all` (detection).

---

## 1. The experiment matrix

```
cell = controller  x  seed
```

| axis | values | notes |
| --- | --- | --- |
| controller (`modes`) | `fixed`, `maxpressure`, `uncoordinated`, `coordinated` | subset selectable; deduped, order preserved |
| seed | `0 .. N-1` | paired across controllers (same seed = same demand draw); **N is one flag** |
| scenario | clean traffic (matrix) **+** `+attack` (detection eval) | the security half is its own deterministic eval, run alongside |

- **Agent:** the deterministic `StubAgent` by default (Foundry-free,
  reproducible). A real agent can be injected for an explicit Foundry-backed run;
  the JSON records which was used (`config.agent`).
- **SUMO flags (enforced):** every traffic cell runs through `run_one`, which
  sets `--tripinfo-output.write-unfinished --tripinfo-output.write-undeparted`.
  The harness then **validates** `write_unfinished_present || write_undeparted_present`
  on every row and refuses to score a silently-degraded tripinfo (which would
  collapse `completion_rate` to a meaningless 1.0).

The matrix is `O(modes × seeds)` SUMO runs for traffic, plus a fixed, fast,
SUMO-free detection eval.

## 2. Metrics: headline vs contrast

**Headline (throughput-controlled — these decide the verdict):**

| metric | direction | why it is robust |
| --- | --- | --- |
| `mean_network_delay` | lower = better | total time-in-network ÷ **all departed** vehicles; stranded vehicles keep their accrued time, so "completes fewer but faster" earns no spurious win |
| `completion_rate` | higher = better | completed ÷ departed (needs `write-unfinished`) |
| `throughput` | higher = better | completed count; a count, cannot be gamed by stranding |

**Contrast only (NEVER the headline):**

- `avg_travel_time_completed` — the OLD Milestone-2 completed-only mean. Under
  survivorship bias it had the **wrong sign**. Shown in a clearly-flagged
  "Contrast only" block so the reader can see if its sign disagrees with
  `mean_network_delay`.
- `matched_diff` (same-vehicle) — the survivorship-**safe** travel-time
  statement: restrict to vehicles completed in BOTH the mode and the baseline,
  per seed, then BCa + paired permutation over seeds.

**Statistics (per headline metric, paired on seed vs `baseline`):** per-mode
mean + BCa 95% CI, paired difference vs baseline + its BCa CI, paired
permutation p-value, Holm-Bonferroni across the controller family. All from
`stats.summarize_sweep`.

**Detection (security) table:** precision / recall / F1 + first-detect latency
per attack family (spoof → conservation, faulty sensor → conservation,
sybil/impersonation → auth), a tolerance ROC, and the honest collusion-evasion
residual (malicious but caught by neither layer).

## 3. Outputs

`run_evaluation(cfg)` returns an immutable `EvalReport` with:

- `.json` — machine-readable: `config`, `traffic_rows` (per-cell), `traffic_tables`
  (per-metric stats records), `matched_set`, `detection`.
- `.markdown` — verdict, per-mode means, per-metric inferential tables, the
  flagged contrast block, the matched-set contrast, the detection table + ROC.

The CLI writes `<stem>.md` and `<stem>.json`.

## 4. How to launch the runs

`--out` is a path **stem** (`.md` and `.json` are appended). `--seeds` is the
seed **count** (`0..N-1`); the only difference between the CI matrix and the
dissertation sweep is that number.

**Tiny CI matrix (default — 2 modes, 3 seeds, end=200, fast):**

```
.venv/Scripts/python src/run_evaluation.py
```

**FULL dissertation sweep (the one line):**

```
.venv/Scripts/python src/run_evaluation.py --seeds 30 --end 1000 --modes fixed maxpressure uncoordinated coordinated --baseline maxpressure --out results/evaluation_matrix
```

That produces `results/evaluation_matrix.md` and `results/evaluation_matrix.json`
with all four controllers, 30 paired seeds, the full 1000-step horizon, BCa
10k / permutation 10k, and the detection table.

Useful variants: `--no-detection` (traffic only), `--coord-weight <λ>`,
`--tolerance <vehicles>`, `--baseline fixed`.

## 5. Tests

`tests/test_evaluation.py` runs a tiny matrix (2 modes, 2 seeds, end=200,
StubAgent) end-to-end and asserts: every cell used the full-population tripinfo
flags; the throughput-controlled metric is the headline while
`avg_travel_time_completed` appears ONLY as a flagged contrast; the stats columns
(BCa CI, paired diff, permutation p, Holm) are present; the detection
P/R/F1/latency columns are present; the JSON is serialisable; results are
**deterministic given seeds** (two runs agree to the bit); and config validation
rejects bad input. Tiny by design so CI stays fast.

```
.venv/Scripts/python -m pytest tests/test_evaluation.py -v
```

## 6. Integration point

This is the **Wk9-10 results generator**. Downstream of the controllers,
`metrics.py`, `stats.py`, and `run_attacks.py`; upstream of the dissertation's
results chapter. It is the single entry point that turns "the system" into "the
numbers and tables in the thesis" — run it once with `--seeds 30` to regenerate
the entire results matrix (traffic + security) reproducibly.
