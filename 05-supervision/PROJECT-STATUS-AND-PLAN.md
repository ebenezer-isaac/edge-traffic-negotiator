# The Edge Negotiator: Project Status, Pending Work, and Timeline

**Date**: 2026-06-25 · **Status**: build ~70% of MUST scope complete; evaluation and the SLM experiment are the critical path.
**Basis**: verified against the code, tests, and existing results (not the canon's intent). Companion to `03-implementation/PROJECT-PROPOSAL.md` (scope), `specs/001-edge-negotiator/experiment-1-slm-vs-rule.md` (the headline experiment), and the supervisor feedback (Lee 2026-06-22, Akin 2026-06-23).

---

## 1. Executive summary

- The infrastructure is solid and tested (355 tests pass): signed coordination, registry + revoke, conservation/CUSUM detector, hash-chained audit log, the classical controller with min/max-green and clearance, the emergency corroboration gate, and the exploit-then-defend demo with measured n=30 results.
- **The two named novelties are unproven.** The SLM is not yet in any decision loop, and coordination shows no benefit (and some harm) on normal traffic in the existing results. Everything measured so far comes from the deterministic layer. Both supervisors identified this as the priority.
- The path to a distinction is: (1) make the SLM causal on the ambiguous cases and evaluate it against a strong rule, which decides the headline; (2) tighten the evaluation (demand sweep, fairness, worst-case, documented method); (3) formalise the core concepts and threat model in writing. Items (3) are low-risk and can start immediately; (1) is the long pole and depends on Foundry Local.

---

## 2. Progress report: what is built and measured

| Subsystem | Status | Evidence |
|---|---|---|
| Ed25519 signing + permissioned registry + revoke | Built, tested | `identity.py`, `registry.py`; 38 tests |
| Conservation + CUSUM plausibility detector | Built, tested | `flow_conservation.py`; 51 tests |
| Tamper-evident hash-chained audit log | Built, tested | `audit_log.py`; 51 tests |
| Classical controller: min/max green + clearance | Built (structural in `step()`) | `controllers.py:70-86` |
| Emergency controller + corroboration gate | Built, tested | `emergency_controller.py`; 9 gate tests |
| Exploit-then-defend demo, 3 modes | Built | `demo_emergency.py`, `measure_emergency.py` |
| Foundry Local SLM wiring | Built (phase-prompt only) | `slm_agent.py`; benched 100% argmax, 0.48s median |
| Coordination-causal fix (normal regime) | Built, tested | `coordinated_controller.py:709-711`; `coord_adjusted_decisions` |
| Statistics stack (BCa + permutation + Holm) | Built, tested | `stats.py`; self-calibration tests |
| Real Lambeth corridor port | Built (as robustness check) | `corridor_coord.md` (9 TLS) |

**Measured results that exist:**
- Emergency n=30 (paired seeds): ambulance 31s faster with preemption vs off [CI 25.4, 36.5]; spoof worst-case side-street wait held 16s below trust-everything; 8s gate cost. Source: `results/emergency_metrics_n30.json`.
- Attack detection: spoof P=1.0/R=0.67/F1=0.80; faulty-sensor P=1.0/R=0.60; impersonation P=R=1.0; collusion evades both layers (as stated). Source: `attacks_report.md`.
- Grid evaluation matrix n=30: all controller modes *hurt* vs MaxPressure on throughput/delay (Holm-reject). Source: `evaluation_matrix.md`.
- Coordination lambda-sweep n=15: coordinated == uncoordinated exactly (dead pathway vs that baseline). Source: `coord_throughput.md`.
- Real SLM coordinated vs uncoordinated n=4: non-significant, flagged underpowered. Source: `coord_slm_honest.md`.
- SLM latency/quality bench (5 models): Phi-4-mini 0.48s, 100% argmax agreement. Source: `slm_bench.md`.
- Lambeth demand behaviour: clean to scale 1.0, tipping ~1.3-1.5, gridlock >=2.0. Source: `lambeth_controllability.md`.

---

## 3. The central finding that drives the plan

Stated plainly so it is not rediscovered later:

1. **The SLM makes no decision it could win.** Its only prompt asks it to pick the phase with the most waiting vehicles (MaxPressure restated), and in the emergency path it is not called at all. So "the AI disambiguates the hard cases" is currently aspirational, not implemented.
2. **Coordination has no positive evidence on normal traffic.** Against uncoordinated it is a dead pathway; against MaxPressure it is worse. The benign "no harm" tie the fair-victim experiment needs is therefore not yet shown.
3. **The demonstrated contribution today is the deterministic trust layer**: the corroboration gate blocks spoofed emergencies, and preemption clears real ones faster. This matches the report's honest claims and is a genuine result, but it is not the SLM and not the coordination-improves-flow story.

Implication for the headline: unless the SLM (Experiment 1) or coordination (Experiment 2 / the B1 causal work) produces a positive, powered result, the defensible headline is the **trust-preserving coordination layer**, with the SLM and coordination-benefit reported as scoped nulls. The experiments are designed to settle this either way.

---

## 4. Pending work

### 4A. Supervisor-critical (both Lee and Akin)
| # | Item | Type | Depends on |
|---|---|---|---|
| S1 | Evaluate SLM vs a well-tuned rule on flagged cases; decide the headline | Experiment | 4B-1..4 |
| S2 | Formalise "robust degradation" (systems property), "ambiguous case" (testable escalation rule), "safety floor" | Writing | none |
| S3 | Explicit, systematic threat model section (capabilities, trust boundaries, single-node vs collusion, key compromise) | Writing | none (exists in PROPOSAL §6) |
| S4 | Derive the gap: why prior emergency/trust systems fail under adversarial conditions | Writing | none |
| S5 | Tighten evaluation: document seeds/pairing/CI method; add demand sweep; report throughput, fairness, worst-case | Build + writing | 4C |
| S6 | Critical limitations section + tie to reliability-engineering / safety-assurance-case framing | Writing | none |

### 4B. Canonical MUST-scope gaps (in code)
1. **SLM disambiguation decision path** made causal in a triggered regime, shield-validated (the SLM currently absent from the emergency decision). *Biggest gap.*
2. **`rule_disambiguator` baseline** (the strong non-AI bar) + **`maxpressure_preempt`** floor baseline. Neither exists.
3. **Anti-starvation override** in the shield (`max_skip`, most-starved approach). Flagged as a MUST in PROPOSAL §101, still missing; the shield's safety claim rests on it.
4. **`escalation_changed_decisions`** metric + regression test (the triggered-regime analogue of `coord_adjusted_decisions`).
5. **New disambiguation prompt** for `SLMAgent` (current prompt is queue-length only).
6. Trigger types beyond `emergency_vehicle`: at least **`incident`** and **`conservation_anomaly`** (the report lists incident reallocation as "to build"). `sensor_outage`/`abnormal_demand` are lower priority.

### 4C. Evaluation-harness gaps
1. **Demand sweep integrated into the main harness** across all modes (currently only a separate Lambeth script, fixed vs maxpressure, no statistics).
2. **Fairness-across-junctions metric** (e.g. Jain index or per-junction delay variance) and **worst-case metric** (max / p95 per-vehicle or per-junction delay). Neither exists.
3. **Real-SLM as a first-class `--agent` option** in `evaluation.py` (today it is a bespoke n=4 side-script; `EvalConfig.agent` is dead code on the default path).
4. **Labelled flagged-state dataset** for Experiment 1 (curated micro-benchmark + harvested-from-sweep).
5. **Unify the CI method**: the emergency n=30 used percentile bootstrap (`measure_emergency._bootstrap_ci`); the main sweep uses BCa + permutation + Holm. Move the emergency metrics onto the BCa stack so the whole thesis reports one documented method.

### 4D. Write-up (Milestone 6)
Dissertation chapters (methodology, results, discussion, limitations), a reproducibility package, and folding the formalisations (S2 to S6) into both the report and the thesis.

---

## 5. Milestone status (from LEE-business-specification.md)

| Milestone | Deliverable | Status |
|---|---|---|
| M1 Coordination substrate | signed bus + registry + shield, 2-node demo | Done |
| M2 Detection | conservation + CUSUM detector | Done |
| M3 Emergency + corroboration | emergency controller + gate + exploit-then-defend | Done |
| M4 Evaluation | demand sweep + real corridor, benign + attacked, n=30, stats | In progress (gaps in 4C) |
| M5 Detectability envelope | recall/latency vs lie-magnitude figure | Not started |
| M6 Write-up | dissertation + reproducibility package | Not started |

---

## 6. Timeline

**Deadline note:** no authoritative UCL submission deadline is recorded in the repo. The only mentions are an informal "September 2026" in stale (pre-pivot) fieldwork letters. **Confirm the real submission date so this can be calendarised.** The plan below is dependency-ordered with effort estimates; provisional calendar assumes a September 2026 submission with work starting now (late June).

| Phase | Work | Effort | Can start |
|---|---|---|---|
| **P0. Rigour writing** | S2 formalise concepts, S3 threat model, S4 gap derivation, S6 limitations + assurance case, document eval method (part of S5) | ~1 week | Now (no dependencies) |
| **P1. Make the SLM real** | 4B-1 causal triggered-regime path + shield validation, 4B-4 metric + test, 4B-5 disambiguation prompt, 4B-3 anti-starvation, 4B-2 baselines | ~2 to 3 weeks | Now (parallel with P0) |
| **P2. Evaluation build** | 4C-1 integrated demand sweep, 4C-2 fairness + worst-case metrics, 4C-3 real-SLM first-class, 4C-5 unify CI, 4C-4 dataset | ~1 to 2 weeks | After P1 baselines land |
| **P3. The experiments** | S1 SLM-vs-rule n=30 on Foundry (determinism check first), S5 demand sweep with throughput/fairness/worst-case + no-harm, M5 lie-magnitude detectability envelope, real Lambeth robustness run | ~2 to 3 weeks | After P1 + P2 (Foundry-bound) |
| **P4. Write-up (M6)** | dissertation chapters, fold in P0 formalisations, reproducibility package | ~3 to 4 weeks, overlapping | Draft alongside P3 |

**Critical path:** P1 (SLM causal) → P3 (SLM evaluation) → headline decision → write-up. This is the long pole and is Foundry-serialised, so start P1 immediately and begin the Foundry determinism check as soon as the disambiguation prompt exists.

---

## 7. Risks

- **The SLM may not beat the rule (a null).** Planned for: a clean null makes the headline the coordination/trust layer, still a defensible contribution (see experiment scope §7).
- **Coordination may stay non-beneficial or harmful on normal traffic.** Then coordination is honestly reported as a robustness substrate, not a performance win; the fair-victim benign-tie claim must be re-examined.
- **Foundry wall-clock at n=30** with serialised calls: memoise by prompt-hash, gate on triggers, start early.
- **SLM nondeterminism on longer disambiguation prompts** (only the short prompt is benched at 100%): measure first; low agreement is itself a finding.
- **Scope pressure vs deadline:** if time is short, cut in NICE order (RAG first, extra triggers next), keep the SLM experiment and the demand sweep as the two non-negotiables.

---

## 8. Immediate next steps (this week)

1. Confirm the real submission deadline (blocks the calendar).
2. Start P0 rigour writing (S2 to S4, S6): formal definitions, threat model, gap derivation, limitations. Low risk, directly lifts the mark, needs no experiments.
3. Start P1: write the disambiguation prompt (4B-5) and wire the SLM causally in the triggered regime (4B-1) with the metric + test (4B-4); add the `rule_disambiguator` and `maxpressure_preempt` baselines (4B-2).
4. Kick off the Foundry determinism check on the new disambiguation prompt as soon as it exists (the long pole).
