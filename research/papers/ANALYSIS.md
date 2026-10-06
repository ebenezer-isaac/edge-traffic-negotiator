# Literature Analysis — synthesis of 8 cluster reports (2026-08-08)

Method: 40-paper local library (see INDEX.md), read by parallel analyst agents against our
measured results; each cluster report extracted exact numbers, experimental scale, stated
limitations, and positioning verdicts. This file is the lit-review backbone. Our reference
results: offline per-decision (fine-tuned ft2 vs stock, int4-as-served, frozen holdouts):
sota 97.7/55.1, myopic 87.9/45.6, prediction 97.6/63.3, coordination 99.0/69.3; closed-loop
n=30 disjoint seeds: Euston ns (ft −3.8% sd 23), Bloomsbury interim ft +0.6% vs stock +2.1%;
override rate 0.12 (ft) vs 0.46 (stock); stock SLM beats fixed-time on Old Street −6..−12%
p<0.01; MaxPressure worse than fixed-time on all real London maps.

---

## 1. THE HEADLINE MECHANISM — why MaxPressure loses on real London (theorem-grounded)

From backpressure theory (Gregoire et al., 1309.6484 + 1401.3357, descendants of Varaiya):

1. **Finite capacity kills work-conservation** (1309.6484 Thm 1, proved unconditionally, any
   topology): plain linear-pressure control stops being work-conserving whenever queue
   capacities are bounded; deadlock constructions exist (their Figs 4-6). Short central-London
   links = small capacities everywhere → the failure condition is STANDING, not exceptional.
   Standard MaxPressure uses exactly the linear pressure form the theorem is proved against;
   their fix (capacity-normalized pressure, Thm 2) is NOT part of standard MaxPressure.
2. **The only stability proof for a deployable (non-oracle) controller requires heavy load**
   (1401.3357 Thm 2, eq. 4: EVERY queue ≥ saturation flow). Authors' own words: sub-saturation
   queues "can unstabilize the queuing network"; stability outside heavy load "is still a
   challenging problem." Real diurnal London demand sits below that threshold most of the day
   → the pressure signal chases arrival noise while fixed-time holds a steady cycle.
3. **Every favorable optimality number comes from uniform grids** (21×21 uniform grid: BP ~90%
   of BP*; heterogeneous params: ~80%), with the authors' own caveat that grid results "can
   not be extended to any kind of network."
4. **Mixed-priority London junctions fall outside the model domain entirely** (service is
   binary phase-determined only; no gap-acceptance/give-way/gyratory term) — the theorems
   don't apply there at all.

**Corroboration in the field's own tables:** AttendLight (NeurIPS 2020, 2010.05772) Table 3
shows MaxPressure LOSING to naive fixed-time by 5-19% on its least-regular topologies
(INT1 T-junctions: A1-3 +11%, A3-3 +19%, A5-3 +17%; INT3-A3-2 +5%) while winning on regular
4-ways — the same direction as our London reversal, strongest exactly where geometry departs
from the grid.

**Mandatory scope boundary:** SIX independent papers (CoLight, LLMLight, Traffic-R1, DGLight,
CoLLMLight, CuraLight) show MaxPressure beating fixed-time by 7-58% on CityFlow grid-like
networks (incl. "real" Manhattan/Jinan/Hangzhou topologies — but always with synthetic or
replayed-uniform demand). LATS shows the same on synthetic-demand Monaco. Our reversal must
ALWAYS be stated as: real irregular geometry × measured DfT demand × SUMO — never unqualified.
This scoping also pre-empts "your MaxPressure is broken": the same formulation behaves
conventionally on grids in our own data (grid3x3/grid4x4 −19/−27%).

## 2. TSC-LLM COMPETITOR MAP (what we cite, where we win, where they win)

| Paper | Model/hardware | Stats rigor | Our edge | Their edge |
|---|---|---|---|---|
| LLMLight/LightGPT (KDD'25) | 0.5-13B LoRA, served on 4×A800-80GB | single-run, no seeds/CI anywhere | on-device int4/6GB; n=30; real London; per-decision table | 15-expert human eval; 196-int scale; TCO table |
| Traffic-R1 (ACL'26) | Qwen2.5-3B GRPO; server T4-class; "edge" is FUTURE WORK in own §6 | single-run + un-tested 6-wk A/B | we HAVE the edge artifact they claim toward; audit layer | real 10-intersection production deployment; RL avoids SFT forgetting (their Fig 5: SFT scores BELOW base on DROP/IFEval/GPQA) |
| DGLight (NUS dissertation, not peer-reviewed) | Llama3-8B, 2×H100-96GB | none | rigor, edge, audit | DQN-critic reward design; held-out-city transfer protocol |
| CoLLMLight (ICLR'26) | Llama3.1-8B, 2×A800; comparisons to 671B | none | edge, rigor, audit, offline fidelity axis | 196 real intersections; complexity-aware reasoning depth; ft-8B beats stock 671B (= "distillation beats scale", supports us) |
| CuraLight | Gemma-3-12B, ~44GB VRAM on L20 | single-run | edge (44GB vs 6GB!), rigor | 177-int zero-shot transfer; ensemble-curated labels (+9% over plain IFT; IFT alone +19.3% — supports FT-matters) |
| iLLM-TSC | GPT-4 cloud API, single synthetic 4-way | single-run; K=3 JSON retry w/ UNMEASURED silent fallback | our 100% strict JSON + fail-loud; real maps | degraded-comms threat model (packet loss + noise) — a scenario axis WE LACK (acknowledge); prompting-alone gains at frontier scale |
| LATS | teacher = 33M embedder (never deployed); student = MLP/GRU (NOT an LLM); RTX4090 | n=10 seeds, no tests | only actual generative SLM deployed on-device is ours | 25-28 int MARL scale; zero-shot transfer; granular ablation. Their pure-LLM baselines (Llama-2-7B/3-8B) perform WORST of all methods (supports stock-LLM-weak) |
| EvolveSignal | cloud frontier ensemble evolving FIXED-TIME code; 1 synthetic intersection, n≈3, no variance | none | everything except: | interpretable-artifact framing (output = readable Python) |

**Field ceiling vs MaxPressure: 1-2%** (LightGPT ~1.2%, DGLight ~1.4%, Advanced-CoLight ~1.9%
on Jinan best-config). Our closed-loop parity at n=30 is the SAME equivalence class, measured
properly; their 1-2% would not survive our seed variance and they never tested.

## 3. TRUST/AUDIT LAYER (H2) — three-way gap

- CollusionVeh (AAAI'22, 2111.02845): ~6% colluding vehicles → colluders' wait −92.5%, others
  +62.7%, vs undefended DRL control (Monaco, 30 int., 5 seeds). ATTACK-ONLY; explicitly calls
  for "real-time anomaly detection" as unbuilt future work → our trust ledger answers it.
  Their calibrated-lie-beats-maximal-lie result motivates our STEALTH-liar scenario.
- Blockchain-TSC (1906.02628): Hyperledger input-integrity architecture (100% spoof rejection,
  ~39ms), but never names a signature scheme, and its own future work concedes failure when
  the VALIDATORS collude. Heavier-weight than our per-decision Ed25519; input-integrity ≠
  decision-level accountability (our target).
- Frame: attack shown (CollusionVeh) + integrity-arch that fails under collusion (blockchain-TSC)
  + nobody defends → our lightweight signed audit + trust ledger + stealth/blatant/honest
  battery sits in the named opening. Cited forensic lineage: FIF-IoT, Guo proof-of-event.

## 4. SLM / ON-DEVICE POSITIONING

- Adopt taxonomies: SLM survey (2410.20011) techniques×constraints axes; on-device review
  (2409.00088) edge-only vs edge-cloud (we are edge-only), TTFT/VRAM/energy indicator template.
- NO traffic/control-loop case study exists in either survey — application gap by omission.
  Closest: DriveVLM (on-vehicle perception, no numbers), Octopus (2B function-calling,
  1.1-1.7s Android — latency comparator for our 0.3-1.5s).
- Reliability floor corroboration: Qwen2.5's own IFEval collapses 84.1 (72B) → 27.9 (0.5B);
  Phi-3 ungroundedness rises as mini shrinks. Consistent with our stock 45-69%.
- Qwen3 report complication: qwen3-0.6b (non-thinking) IFEval 54.5 / BFCL 44.1 ≥ qwen2.5
  bigger siblings, yet stock qwen3 was our weakest battery scorer. RESOLVED in-house: our
  harness DOES inject /no_think (slm_agent.py think_suffix) and stock qwen3 parsed at 93-100%
  strict JSON while choosing wrong phases → genuine decision-quality weakness, not think-mode
  corruption. Framing: IFEval measures generic instruction-following; our battery measures
  numeric decision quality — different capabilities, and the reports never test the latter.
- Distillation precedent naming our 55→97.7 jump: BabyLlama ("distillation can outperform
  pre-training"), Hsieh et al. (distilled students outperform LLMs). SLM survey §7.1 names
  size-vs-hallucination as unresolved — our per-decision reliability data is new evidence.

## 5. DISTILLATION + QUANTIZATION — three DECLARED threats-to-validity

1. **Orca (2306.02707) explanation-trace thesis vs our label-only distillation.** Defense:
   (a) task-shape — bounded closed decision schema ≈ classification; KD-survey taxonomy
   (2402.13116) endorses Labeling+SFT for exactly this cell; (b) Orca's own §9 concedes small
   models excel "in constrained settings"; (c) empirically near-teacher-ceiling (97.7% vs
   98-99% teacher-teacher agreement). CONCEDE: OOD generalization + native audit rationale
   untested — Orca-motivated risks, stated.
2. **Forgetting-scaling (2401.05605): inverse-loss law predicts general-capability drift at
   our 0.014 train loss.** Their own data shows task accuracy and base-behavior drift can
   diverge (ARC flat, 32.8% behavioral divergence). We have NO retention probe → run one
   (ARC/MMLU-style spot-check, ft2 vs ft0) or disclose as unmeasured limitation. Converges
   with Traffic-R1's SFT-forgetting ablation — doubly motivated.
3. **Quantization literature predicts degradation our int4-RTN pass didn't show.** GPTQ:
   small models are the HARD RTN case (OPT-1.3B RTN-4bit +229% PPL). AWQ: RTN weak generally
   but gap shrinks at 4-bit/g128. Quant-eval 2507.17417: catastrophic numbers are W4A4 (we
   are weight-only). Q-BLoRA (2407.17029): post-hoc PTQ after fine-tune lost 9.4% rel. even
   with GPTQ — closest analog to our merge-then-RTN order. SCOPE OUR CLAIM: "bit-identical
   held-out decision accuracy under weight-only int4 on a near-converged narrow-schema
   checkpoint, measured with a discrete accuracy metric coarser than perplexity" — an open
   favorable finding, not a literature-endorsed property.
- LoRA rank: r=16 well-supported (LoRA Table 6: r=1 suffices on WikiSQL-class tasks; QLoRA:
  "r does not affect performance") — extrapolated below 125M, flag as such.
- Pipeline ordering precision (for methods chapter): QLoRA trains adapters ON a 4-bit base and
  serves UNMERGED; we use QLoRA-style training then merge to bf16 then classic post-hoc int4
  RTN for serving — two different quantization steps in different senses; do not borrow
  QLoRA's authority for the RTN step.

## 6. SHIELD ARCHITECTURE THEORY — what our shield formally is (and is not)

(AD-survey/legal trio — llm4drive-2311.01043, llm-ad-2409.14165, dahl-2401.01301 — still
pending; Dahl hallucination rates remain earmarked for the Job-A legal-note framing.)

**Per-paper capsules:**
- **Alshiekh et al. (1708.08611, canonical).** Shield = a *correct-by-construction reactive
  system* synthesised from (a) a safety spec in the safety fragment of LTL (a safety word
  automaton) and (b) a finite-state MDP abstraction of the environment, by solving a 2-player
  safety game and implementing the winning strategy (§5-6). Two placements: *preemptive*
  (shield emits the safe-action list the learner picks from, Fig 1) and *post-posed* (shield
  monitors the chosen action and "substitutes the selected actions by safe actions whenever
  this is necessary to prevent the violation of φs", §5.2 — our topology). Proven properties:
  correctness against φs and *minimal interference* ("restricts the agent as little as
  possible and forbids actions only if they could endanger safe system behavior", §1+§6.1);
  learner convergence is preserved via a product-MDP argument (§7). Two honest notes we
  adopt: "planning ahead is the true power of synthesis" (§4 — the shield acts *before* the
  violation becomes unavoidable, not at it), and under the punishment-reward variant "there
  is no guarantee that unsafe actions are not part of the final policy. Therefore, the shield
  has to remain active even after the learning phase" (§5.2) — our shield is permanent too.
- **Invalid-action masking (Huang & Ontañón, 2006.14171).** Masking = replacing illegal-action
  logits with -∞ then renormalising; Prop. 1 proves the masked update is a valid policy
  gradient (masking is a state-dependent differentiable function, not a hack). Empirically
  masking *scales* with the invalid-action space (t_solve ≈ 12% across µRTS map sizes) while
  invalid-action *penalties* fail to scale (Table 2); and agents trained with the mask still
  behave partially valid when it is removed ("masking removed still behaves to some extent").
- **Neuro-symbolic action masking (NSAM, Han et al., AAMAS 2026, 2602.10598).** Learns the
  symbolic grounding (PSDD over propositional domain constraints) from minimal supervision,
  then masks actions whose preconditions fail — hard constraints ("strictly not explorable"),
  violation rates 0.1-6% during training vs frequently ~100% for unmasked baselines (Table 1).
  Its own future work names "richer forms of symbolic knowledge... such as temporal logics"
  (§8) — i.e., the masking literature itself points back toward Alshiekh-style specs. For us
  NSAM marks the middle rung: needed when constraints must be *learned* from raw states; our
  state is structured numerics with known constraints, so hand-specified masks are proper.
- **iLLM-TSC (2407.06025) — the inverted mirror.** RL (PPO) *proposes* a phase every τ=5s;
  a cloud LLM (GPT-4 API, §5.1) *assesses and vetoes* ("Should there be a discrepancy between
  the RL suggestion and the LLM's logical framework, the LLM intervenes to adjust the action",
  §4.4; Algorithm 1: K=3 regex-extraction retries, then silent fallback to the RL decision).
  Results: single synthetic 4-way SUMO intersection, single run; −17.5% mean waiting vs
  ADLight under degraded comms; EMV waiting −62.9% vs SARL-TSC (§5.4).

**Synthesis — position our shield honestly.** Ours is NOT a shield in the Alshiekh sense.
Decomposed, it is three weaker-but-sound pieces: (1) *preemptive action masking* — the SLM
chooses an index into a fixed menu of pre-vetted conflict-free phase programs, so "no
conflicting greens" holds by construction of the action set (the masking literature's
guarantee, and its Prop-1/NSAM results say structural exclusion beats hoping the model learns
legality); (2) a *post-posed default-substitution filter* — on a silent/invalid proposal the
deterministic MaxPressure choice is served (Alshiekh's post-posed placement, minus the
synthesis); (3) an *anti-starvation floor* — a runtime monitor forcing the most-starved phase,
a bounded-liveness property enforced by code, not proved from a spec. What we LACK vs the
formalism: no LTL safety specification, no MDP abstraction, no safety-game synthesis — hence
no correctness-for-all-abstraction-consistent-environments proof, no minimal-interference
proof, no lookahead (our floor reacts AT the starvation threshold; a synthesised shield acts
before violation becomes unavoidable). State this as a limitation. The upgrade path is
concrete and cheap at our scale: specify min-green/max-wait/no-conflict as a safety automaton,
abstract queue levels into bins (their 602-state water-tank product game is the size class of
one junction), solve the game, serve the winning-region shield — named future work, and it
would also import Alshiekh's §7 convergence preservation.

**Override rate ↔ interference/permissiveness.** Our measured quantity (0.12 ft vs 0.46
stock) is the share of *served SLM decisions that diverge from the MaxPressure counterfactual*
(experiment_why.py) — a run-time divergence metric, where the literature's "minimum
interference" is a design-time property of the shield. The mapping still earns its keep:
fine-tuning collapses divergence 0.46 → 0.12 while *improving* delay, i.e., the policy
internalised the shield's normative envelope and deviates selectively — the end-state the
masking literature observes when mask-trained agents stay largely valid unmasked, and the
regime where a minimally-interfering monitor is cheapest. The stock model's 0.46 divergence
with worse delay is the opposite reading: deviations as noise, the shield as load-bearing.

**Why our topology beats iLLM-TSC's for edge deployment.** They invert us: cheap local
learner proposes, expensive remote frontier model vetoes. That places the *least verifiable*
component (a prompted LLM) in the safety-monitor seat, makes every 5s control slot cloud-bound
(GPT-4 API), and on K failed extractions silently serves the unvetted RL action. Ours puts
the unverifiable component on the PROPOSAL side — worst case is a legal-but-suboptimal phase —
and keeps the veto deterministic, O(phases) arithmetic, local, and auditable; the edge premise
(6GB device, no link dependence) is only satisfiable this way round. CONCEDE their edges (§2
table stands): degraded-comms scenario axis we lack, and frontier-scale prompting gains.

## 7. FIVE GAP STATEMENTS THE DISSERTATION OWNS

1. Only work serving an actual generative SLM on-device (6GB, int4, Microsoft stack) for
   signal control — all rivals: cloud/server GPUs or non-LLM distilled students; Traffic-R1's
   edge claim is self-declared future work.
2. Only powered statistics in the field (n=30 disjoint seeds, CIs, declared nulls) — every
   competitor table is single-run or n≤10 without tests.
3. First measured reversal of MaxPressure vs fixed-time on real-geometry + measured-demand,
   with a theorem-grounded mechanism (finite capacity + sub-saturation demand + non-grid
   structure) and field-table corroboration (AttendLight T-junctions).
4. Only defense-side trust mechanism in the TSC falsified-data literature (attack papers
   stop at attacks; integrity architectures fail under validator collusion).
5. Only decision-level cryptographic audit — enabling failure forensics (catastrophic-seed
   walk-throughs) and the crash→UK-law evidence pack no other system can produce.

## 8. HONEST LIMITATIONS TO CARRY (from the literature's strengths)

- Traffic-R1 has real production deployment; we are simulation-only.
- CoLLMLight/LLMLight test 196-intersection scale; our networks are corridor/grid scale.
- iLLM-TSC's degraded-communication axis (packet loss/noise) is a scenario class we don't test.
- Held-out-city transfer (DGLight protocol) → our LOTO probe addresses this; run it.
- General-capability retention unprobed (see threat 2 above).
- Prompting-alone gains at frontier scale (iLLM-TSC) — acknowledge as the cheap alternative
  we rejected for capacity reasons at 0.6B (our stock-vs-ft table is the evidence).
