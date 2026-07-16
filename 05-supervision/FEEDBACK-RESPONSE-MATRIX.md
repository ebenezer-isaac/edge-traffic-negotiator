# Supervisor Feedback: Response Matrix and Research Grounding

**Date**: 2026-06-25 · Maps every Lee (2026-06-22) and Akin (2026-06-23) ask to its status, what satisfies it, and the gap. Research claims below are grounded in cited literature, not asserted.

---

## 1. Response matrix

| # | Ask (source) | Status | What satisfies it / what is missing |
|---|---|---|---|
| L1 / A3 | Critical synthesis: why prior systems fail under adversarial conditions; derive the gap | Partial | First-principles derived-gap paragraph added to PROPOSAL §3. To make it citation-backed needs the deep-research pass (§3 below). |
| L2 / A1 | Formalise "robust degradation" (systems property / math) | Done | R1-R4 in FORMAL-SPEC §8. Grounded in CPS-resilience metrics (degradation rate, recovery, steady-state). |
| A1 | Testable escalation rule for "ambiguous case" | Done | A1-A3 escalation predicate in FORMAL-SPEC §8. |
| L3 / A2 | Explicit, systematic threat model (capabilities, trust boundaries, failure modes, single-node vs collusion, key compromise) | Exists, needs surfacing | Full model in PROPOSAL §6; must be lifted into the report as its own section. |
| L4 / A5 | Document experimental design (variables, controls, seeds, CI computation) | Partial | Stats stack exists (BCa + paired permutation + Holm, `stats.py`); seeds paired 0..29 across modes. Needs: written methods section + unify the emergency metrics onto BCa (currently percentile bootstrap). |
| L5 / A5 | System-level trade-offs: throughput, fairness across junctions, worst-case | Partial | Throughput exists (`metrics.py`). Fairness + worst-case MISSING, must build (metric choice settled below). |
| L6 / A5 | Interpret significance (statistical AND practical), null discussion | Method ready | Needs write-up discipline: report effect sizes + CIs + MDE, and a null-result subsection. |
| L7 / A6 | Critical limitations (simulator, scalability, single trust domain, what a null means) | Done | Added in the cutover (PROPOSAL §11). |
| L8 | Connect to a systems-engineering framework (reliability eng / safety assurance case) | Buildable (writing) | Structure the safety argument as a GSN assurance case (below). |
| A4 | Evaluate the SLM: baseline rule + decision metric, run, report either way, decide headline | Scoped, not built | Experiment 1 (`specs/001-edge-negotiator/experiment-1-slm-vs-rule.md`). The build + Foundry run is the critical path. |

---

## 2. Research-grounded design decisions

### 2.1 Robust degradation is defensible as a defined property
The CPS-resilience literature quantifies resilience via **degradation rate, recovery capacity, and steady-state behaviour**, and explicitly notes these metrics "remain largely application-specific and lack standardization" ([CPS cyber-resilience survey, arXiv:2302.05402](https://arxiv.org/pdf/2302.05402); [resilience quantitative framework, MDPI 15/8285](https://www.mdpi.com/2076-3417/15/15/8285)). So defining our own testable R1-R4 (detect within bounded windows, contain, bounded degradation vs local-control fallback, safety invariance) is the expected practice, not a gap. Frame R3 as the "degraded steady-state bound" the literature names.

### 2.2 Fairness metric (settled: Jain + worst-case)
TSC fairness has four ideology-grounded families: **Jain's index** (closeness of waiting times, 1/N to 1), **Gini** (egalitarian), **max delay** (Rawlsian / worst-case), and average delay (utilitarian) ([Fair DRL TSC, arXiv:2107.10146](https://arxiv.org/pdf/2107.10146); [four-ideology fairness eval, MDPI app14178047](https://www.mdpi.com/2076-3417/14/17/8047)). **Recommendation:** report **Jain's index over per-junction mean delay** (fairness across junctions, exactly Lee's phrase) plus **max per-vehicle and max per-junction delay** (Rawlsian worst-case, exactly Lee's "worst-case guarantees"). Two numbers cover both his asks with standard metrics.

### 2.3 Safety assurance case = GSN
A safety case is "a structured argument supported by evidence that a system is safe"; **GSN** documents it as goals, strategies, and solutions (evidence) ([GSN safety case, ScienceDirect S0951832022005488](https://www.sciencedirect.com/science/article/pii/S0951832022005488); [Open Autonomy Safety Case Framework, arXiv:2404.05444](https://arxiv.org/pdf/2404.05444)). **Plan:** add a one-figure GSN argument: top goal "control action is safe under a compromised neighbour", strategy "safety established by a deterministic envelope independent of the AI", solutions = the S1-S4 invariants + the shield-veto-rate evidence + the corroboration-gate result. This directly answers L8 and puts the SLM explicitly outside the trust base.

### 2.4 The adversarial gap is real and citable
The literature confirms adaptive/DRL and connected-vehicle signal control "fully trust that vehicles send true information", making them vulnerable to falsified-data attacks, and that colluding certified vehicles can defeat them ([vulnerability of TSC under attack, UCI/TRB18](https://ics.uci.edu/~alfchen/yiheng_trb18.pdf); [adversarial attacks on DRL-TSC with colluding vehicles, ACM TIST 3625236](https://dl.acm.org/doi/full/10.1145/3625236); [cybersecurity of TSC with connected vehicles, NSF 10427124](https://par.nsf.gov/biblio/10427124)). This is the hard data behind "prior approaches fail under adversarial conditions" and behind why the coordination channel is a growing attack surface. The deep-research pass (§3) turns this into a per-system failure analysis.

### 2.5 Emergency-preemption baseline
The standard non-AI baseline is a **rule-based green-extension / green-wave preemption** (e.g. the "Walabi" rule-based EMV green wave in SUMO); V2I preemption reduces EV response time ~43-51% ([EV preemption w/ spillback, IET ITS itr2.12518](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12518); [EMVLight, arXiv:2109.05429](https://arxiv.org/pdf/2109.05429); [USDOT V2I preemption eval](https://www.itskrs.its.dot.gov/2018-b01259)). Our `maxpressure_preempt` baseline should implement green-extension preemption on locally-sensed EVs, which is exactly the deterministic floor Experiment 1 needs.

---

## 3. What still needs deep research (the browser prompt)
One thing genuinely needs a full multi-paper read rather than a search snippet: the **per-system adversarial-failure analysis** of the 12 competitor systems, which is what turns Akin's "derive the gap" from a paragraph into a defensible synthesis. The prompt for that is provided separately for a browser deep-research run. Its output feeds PROPOSAL §3-4 and the dissertation related-work chapter.
