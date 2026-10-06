# Build log (forward)

This log records build phases going forward under the locked thesis (`MASTER-SPEC.md` §1).
Each phase must pass its adversarial spec-alignment battery before the next begins (§0, §11);
a phase is not complete until its §12 acceptance gate passes or records an honest SKIP/negative.
Entries are append-only: one short block per phase (date, scope, battery outcome, artifacts hash-pinned in §10).
The full commit-by-commit history lives in git.

## Greenfield-clean milestone (flatten to day-one intent)
Flattened the whole repo + agent memory to the locked thesis so no future agent is misled by iteration history (history preserved in git). Commits: pre-pivot doc trees deleted; 26 historical result notebooks deleted; MASTER-SPEC de-versioned + docs greenfielded (GLOSSARY/GROUND-RULES/FORMAL-SPEC kept, 6 stale reports + experiment-1 deleted with substance folded, hardening-log reset, top-level + code-package READMEs); pre-pivot code archaeology removed (bench_mqtt/qbft/ledger, collect_results, demo_2node, run_hybrid, run_scaling, sweep_baselines, run_corridor_coord) with import-DAG safety (demoted-layer infra kept as opt-in backends); battery findings closed + all week/milestone/de-risk vocabulary neutralized.
BATTERY: fresh adversarial examiner over the whole clean state = 0 FATAL / 6 MAJOR; all 6 fixed + re-verified (0 residual iteration traces in scanned scope, dangling refs repointed to MASTER-SPEC, memory index rebuilt to 7 files). Suite 617 passed / 27 skipped. §10 hash-pin registry BYTE-IDENTICAL throughout (9 pins verified). Pinned artifacts keep frozen v7 markers as a documented exception (ground_rules.yaml de-version deferred to the multi-vehicle-KB re-pin).
NEXT: resume building under the clean foundation. H1 headline = SLM controller vs MaxPressure on Euston (PENDING, first up); then coordination arm + model x config sweep; H2 accident-audit demo; multi-vehicle KB + adversarial P/R/FPR/FNR; live anchor; powered n>=30.
