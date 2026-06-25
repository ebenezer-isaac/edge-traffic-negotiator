# Experiment 1 Scope: Does the SLM beat a well-tuned rule on flagged ambiguous cases?

**Status**: Scope / design (not yet run)
**Created**: 2026-06-21
**Decides**: the headline contribution (SLM vs the trust-preserving coordination layer), per Akin's and Lee's feedback.

---

## 0. Why this experiment

Both supervisors flagged the same gap: every measured result so far (31s / 16s / 8s) comes from the **deterministic** corroboration gate, so the SLM, the named novelty, is **unevaluated**. Akin: "the SLM, which is your named novelty, is not yet evaluated... decide and defend whether the headline contribution is the SLM or the trust-preserving coordination layer."

**Honest current state (grounded in the code, not the canon's intent):**
- `slm_agent.py` SYSTEM prompt tells Phi-4-mini to "pick the green phase with the MOST waiting vehicles." That is MaxPressure restated in natural language, so the SLM cannot beat MaxPressure on phase selection by construction.
- `coordinated_controller.py:711` (`used = proposal if proposal is not None else coord_choice`): the SLM phase choice is causal, but it is choosing among queue lengths (the same task as the shield); the coordination term is the inert fallback (the B1 bug).
- `emergency_controller.py`: emergency admissibility (`_admissible_ev`) is fully deterministic (local sensing trusted; advance claim needs corroboration). The SLM is never consulted on the real-vs-spoofed decision.

**Conclusion:** the SLM currently makes no decision where it could plausibly beat a rule. Experiment 1 must first point it at a decision a fixed rule cannot cleanly settle, then evaluate it. This reframing is the core of the experiment.

---

## 1. The decision the SLM must own (define the ambiguous case)

**Ambiguous / flagged case (definition):** a control tick where a detector flags an anomaly that a fixed per-junction rule cannot cleanly classify, specifically a conservation residual outside the plausibility band, or an emergency/incident claim, where the evidence is partial or conflicting.

**The SLM's decision:** given cross-junction context (neighbour sightings, the corroboration pattern, flow consistency across the junctions), classify the flagged event as **real (escalate: preempt / reallocate)** vs **spoofed-or-faulty (reject: stay on MaxPressure, discount the claim)**. Plus the EV nuance the deterministic gate leaves open: priority among multiple simultaneous emergencies, and EV-plus-incident routing.

**Testable escalation rule (what invokes the SLM):** a trigger fires when (a) the windowed conservation detector flags `inflated` / `under_reported` for a neighbour this tick, OR (b) an emergency/incident claim is authenticated but only partially corroborated (corroboration count below the rule's hard-accept threshold and above zero). Clear-cut cases (fully corroborated, or zero corroboration with no local sensing) stay deterministic; only the middle escalates to the SLM. The SLM proposal is then validated by the deterministic shield (it can never violate the safety envelope or force preemption on a zero-evidence claim).

This is the triggered-regime decision path from `METHODOLOGY-AND-IMPLEMENTATION-DESIGN.md` §1.2, which is **not yet built**.

---

## 2. The well-tuned rule baseline (the bar to beat)

Two non-AI baselines, both using the SAME inputs the SLM gets:

- **`rule_disambiguator`**: fixed thresholds on corroboration count, conservation residual magnitude, and CUSUM persistence. Example form: escalate-as-real iff (independent corroborations >= k) AND (residual within band) AND (persistence >= p); else reject. Thresholds tuned on a development split, reported.
- **`maxpressure_preempt`**: MaxPressure plus the deterministic EV preemption rule, no SLM, no cross-junction reasoning (the emergency floor the canon prescribes in §5.1, **not yet built**). Shows how much benefit is the deterministic preemption alone vs the SLM nuance.

The comparison must be SLM vs a *strong* rule, not a strawman, or the result is not defensible.

---

## 3. Decision metric

- **Primary:** classification quality on labelled flagged states, accuracy, F1, and false-preemption rate (escalations granted to a spoofed/non-existent event).
- **Decision-attribution breakdown** on states where rule and SLM disagree: agree / disagree-SLM-better / disagree-SLM-worse / shield-vetoed (`PROJECT-PROPOSAL.md` §8).
- **Secondary (traffic outcome):** incident-recovery time and emergency-vehicle delay on the subset, so a classification win is tied to a real-world effect.

---

## 4. Dataset (flagged states with ground truth)

- **Curated hard-state micro-benchmark:** hand-built flagged states with known-correct labels, covering real incident, spoofed preemption grab, within-tolerance partial lie, multiple simultaneous emergencies, and EV-plus-incident. Each carries the correct escalate/reject decision.
- **Harvested states:** flagged ticks collected from the demand-sweep runs (Experiment 2), labelled by the injected ground truth (we control which events are attacks).
- **Split:** development split for tuning the rule thresholds and the prompt; held-out test split for the reported numbers. Sizes and the labelling protocol pre-registered before the test split is touched.

---

## 5. Foundry Local run protocol (the real Phi-4-mini)

- Use `slm_agent.SLMAgent` (exists; OpenAI-compatible call to Foundry Local). A **new disambiguation prompt** is required: the current prompt only asks for a phase index; this experiment needs a prompt that presents the cross-junction evidence and asks for the escalate/reject judgment.
- **Determinism:** measure temp-0 run-to-run agreement at N=100 on the **disambiguation prompts specifically** (longer and context-laden, where determinism is least guaranteed; existing 100% agreement is only for the short phase prompt). Report it. THEN memoise SLM decisions by prompt-hash so traffic variance is isolated from model variance.
- **Power:** n=30 paired seeds (the StubAgent path structurally cannot show the effect; the bench in `bench_slm.py` confirms Foundry serialises calls at roughly 0.5s each, so gate the SLM on triggers and cap concurrent escalations).
- **Pin:** model hash, quantisation, Foundry version, decode params, seeds.

---

## 6. Statistics

Paired on seed; BCa bootstrap + paired permutation + Holm (the existing `stats.py` stack). Pre-register the primary metric family. Report effect sizes with confidence intervals as the headline and p-values as support. State the minimum detectable effect (MDE) so a null reads as "below MDE = X", not "no difference."

---

## 7. Headline-decision logic (what Akin asked us to decide and defend)

- **If the SLM beats the rule** (Holm-significant and practically meaningful) on the ambiguous set: the headline is the **SLM as cross-junction disambiguator**, the AI earns its place on the one decision a rule cannot make.
- **If the result is null** (within MDE): the headline is the **trust-preserving coordination layer**, and the null is a scoped, informative finding ("a fixed rule suffices for spoofed-emergency disambiguation, bounding where edge reasoning adds value"). This is a publishable result, not a failure, and matches the project's stated epistemic humility.

Either outcome is defensible. The experiment is designed so the answer is a contribution either way.

---

## 8. Build prerequisites before the eval can run (honest checklist)

| # | Prerequisite | Exists? |
|---|---|---|
| P1 | Wire the SLM disambiguation decision causally in a triggered regime (shield-validated) | No (gate is deterministic today) |
| P2 | `rule_disambiguator` + `maxpressure_preempt` baselines | No |
| P3 | Labelled flagged-state dataset + harvester from sweep runs | No |
| P4 | Determinism harness on the disambiguation prompt (extend `bench_slm.py`) | Partial (`bench_slm` exists for the phase prompt) |
| P5 | New disambiguation prompt for `SLMAgent` (current prompt is queue-length only) | No |
| P6 | B1 fix: the escalated proposal is the executed candidate, with an `escalation_changed_decisions` metric + regression test | No (B1 still inert) |

---

## 9. Risks and threats to validity

- **Foundry wall-clock at n=30:** start the run early in the background; memoise by prompt-hash; reduce matrix breadth before seed count.
- **SLM nondeterminism on longer prompts:** measure agreement first (§5); if low, the disambiguation result is itself a finding about edge-SLM reliability.
- **Dataset labelling bias:** use injected ground truth and pre-register the protocol; do not pick the test split post-hoc.
- **The decision may be one a rule handles fine:** a null is planned for and is a valid result (§7), not an excuse.
- **Strawman risk:** the rule baseline must be tuned and strong, or a SLM win is not credible.

---

## 10. Sequencing

1. P5 + P1: new disambiguation prompt and the causal triggered-regime decision path (+ P6 B1 fix and regression test).
2. P2: the rule baselines.
3. P3: the labelled dataset (curated micro-benchmark first; harvest from Experiment 2's sweep when that runs).
4. P4 + §5: determinism check on Foundry, then memoise.
5. Run n=30, score with §6 stats, produce the decision-attribution breakdown.
6. Apply §7 to set the headline, and write it up including a clean null if that is the result.

Experiment 1 depends on Experiment 2's demand sweep for the harvested dataset, but the curated micro-benchmark lets P1 to P6 and the first SLM-vs-rule run proceed in parallel.
