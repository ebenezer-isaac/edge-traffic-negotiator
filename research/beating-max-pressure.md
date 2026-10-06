# Beating MaxPressure on Mean Delay with a Small On-Device LLM: A Ranked, Cited Playbook for Myopic Single-Junction Signal Control

## TL;DR
- The single biggest lever is **state representation, not model size**: give the SLM *delay/age-weighted pressure* per phase (backlog + accumulated waiting time), not raw queues, because MaxPressure is throughput-optimal but provably not delay-optimal and is memoryless on waiting time — a delay-weighted rule is the principled way an own-junction-only agent can beat it on delay (Wu, Ghosal, Zhang & Chuah 2018; Varaiya 2013). Feed this as a pre-computed numeric table so the 0.5–1.7B model *ranks* rather than *computes*.
- At 0.5B–1.7B, the cheap no-fine-tuning wins are: **(1) present pre-computed per-phase scores; (2) keep reasoning OUT of the JSON — emit a short free-text rationale then the JSON action, never answer-field-first; (3) constrain only the final action token to the valid phase set (guided-choice), not a full JSON grammar over the reasoning; (4) keep qwen3 in `/no_think`; (5) add hysteresis + min-green + phase-skip.** Self-consistency and heavy few-shot give little at this scale and cost latency.
- The reliability guarantee comes from your **MaxPressure shield plus a delay-weighted decision rule**: with a correct shield the SLM can never do worse than MaxPressure on validity, and with delay-weighted scoring it has a principled path to lower mean delay. If you want to *reliably* beat the baseline across the smallest models, **LoRA/QLoRA imitation fine-tuning on trajectories from a delay-optimising oracle (offline SUMO optimiser) is the highest-confidence upgrade** — LLMLight's Qwen2-0.5B went from 1124.8s to 328.1s average travel time this way and beat Llama2-70B.

## Key Findings

1. **MaxPressure's weakness is exactly what an own-junction SLM can exploit.** MaxPressure maximises throughput and stabilises queues whenever the demand is stabilisable — Varaiya (2013) proves it "stabilizes a demand whenever there exists any stabilizing controller … requires no knowledge of the demand, although it needs turn ratios." But it is derived from a store-and-forward model with strong assumptions (infinite links, zero switching loss) and weights movements by *instantaneous* queue length only — it is memoryless on how long vehicles have waited. Wu, Ghosal, Zhang & Chuah (2018, IEEE T-VT) prove a **delay-based back-pressure controller is *also* throughput-optimal but achieves better fairness and lower excessive delay**, because queue-based control can starve a lane whose queue stays short. This is your theoretical licence: a delay/age-weighted score using only own-approach information can reduce mean delay relative to instantaneous max-pressure while preserving stability.

2. **Switching discipline matters more than the weight function.** Robbennolt, Chen & Levin (2022, TRR) found in a large SUMO microsimulation of downtown Austin that "the way green time is assigned (cyclic or non-cyclic) has a larger impact on performance than the weight function used by the max-pressure controller," and Barman & Levin (2022, TRR) found a **cyclic max-pressure policy with phase-skipping when no vehicles wait, plus min/max-green, gives the best delay**. Instantaneous acyclic max-pressure switches too often; once switching loss is modelled, "the original max pressure control (Varaiya, 2013) is no longer a throughput-optimal policy" (SCMP, Sun et al., TR-C 2022). Hysteresis + min-green is therefore not a hack but a delay-reducing mechanism (it cuts lost time from clearance/startup and reduces stops).

3. **Format/JSON constraints impose a large "reasoning tax" on small models — the most important decoding finding for your setup.** Tam et al. (2024, EMNLP Industry; arXiv 2408.02442) show forcing JSON output degrades reasoning accuracy 10–30%: GPT-3.5 GSM8K fell from 76.6 to 49.3, LLaMA-3-8B from 74.7 to 48.9, and LLaMA-3-8B Last-Letter from 70.1 to 28.0. Crucially the loss was **not from parse failures** — "the parsing error rate for the Last Letter task in JSON format is only 0.148%, yet there exists a substantial 38.15% performance gap" — but from (a) the schema consuming model capacity and (b) JSON-mode putting the answer field before the reasoning field, which skips chain-of-thought entirely: "100% of GPT-3.5 Turbo JSON-mode responses placed the 'answer' key before the 'reason' key, resulting in zero-shot direct answering instead of zero-shot chain-of-thought reasoning." Follow-up work ("Capacity, Not Format," 2026; "The Format Tax," 2026) confirms **capacity-limited (small) models are hurt most and the fix is to decouple reasoning from formatting** — reason in free text first, structure last.

4. **BUT for a pure classification/selection output, constraining to the valid option set *helps* small models.** Tam et al. found the opposite sign on classification: Gemini-1.5-Flash on DDXPlus went from 41.6 (text) to 60.3 (JSON) because "constraining possible answers resulted in reducing errors in answer selection." A benchmark on sub-5B Gemma models shows constrained decoding to a fixed option set gave up to +0.35 quality on a 24-category classification task because "small language models often fail to generate a valid selection without formal runtime constraints." **Implication: constrain the final phase-index token to {0…K−1}; do not grammar-constrain the reasoning.**

5. **Self-consistency and few-shot are weak at this scale.** Majority-vote self-consistency "under-performs across all settings, particularly on symbolic tasks" for 7B models (14% on WebOfLies with DeepSeek-7B; 21% on MultiArith with Mistral-7B) and shows diminishing returns generally; its N× latency cost is unaffordable in a 10s loop when you already run temperature 0. Few-shot demonstrations help only "on complex tasks" and "may even worsen model performance in some cases" (INSTRUCTEVAL), with small open models (LLaMA-2-7B) gaining little; benefit is highly dependent on demonstration label balance.

6. **Quantization: use INT8; be cautious with INT4 on the smallest models.** INT8/W8 is near-lossless. INT4/W4 AWQ costs little on large models but reasoning tasks degrade more on small models, and quantized reasoning models paradoxically emit *longer* CoT (worse latency); DSR1-Qwen-1.5B lost 1.04% under W4A16 AWQ. The ACL-2025 study "Give Me BF16 or Give Me Death" (Kurtic et al.) documents that STEM/coding-style tasks lose most under aggressive quantization.

7. **Model choice: Qwen3-1.7B/4B and Phi-4-mini are the strongest sub-4B structured-decision backbones in 2025–26; reasoning-tuned variants rarely earn their latency here.** Per the Qwen3 Technical Report (arXiv 2505.09388), edge models "outperform baselines even with more parameters, including our previous Qwen2.5 models, in either the thinking or the non-thinking mode"; specifically "Qwen3-1.7B/4B/8B/14B/32B-Base perform similarly to Qwen2.5-3B/7B/14B/32B/72B-Base models," and on STEM/coding/reasoning "even outperform the larger Qwen2.5 models." Phi-4-mini (3.8B) has "significantly improved … instruction following and function calling." Reasoning-tuned small models (Phi-4-mini-reasoning, R1-distills) win on math but overthink: smaller models overthink more, and on a 1.5B model *suppressing* reasoning ("No-Reasoning") gave the best accuracy in the EdgeReasoning study — validating your `/no_think` choice.

## Details — Ranked Techniques

Ordering: cheapest/no-fine-tuning first (Tier A), then decoding/model (Tier B), then adaptation (Tier C). Each entry gives (a) what to change; (b) effect on **delay** and **latency**; (c) scale at which it works; (d) citation.

### TIER A — No fine-tuning, cheap to try first

**A1. Replace raw queues with pre-computed delay/age-weighted per-phase pressure scores (highest expected delay gain).**
(a) For each phase p, compute *offline in Python* a scalar such as `score_p = Σ_lanes∈p (queue_len × total_waiting_time)`, or the delay-based pressure of Wu et al. (max/accumulated waiting time per movement). Present the model a small table of `{phase, queue, total_wait, score}` and instruct it to pick (usually) the max-score phase, deviating only to prevent starvation. The LLM *ranks*; it does not do arithmetic (small LLMs are unreliable at this — they encode numbers digit-wise and make digit-space errors).
(b) **Delay: large positive** — directly targets the metric MaxPressure ignores and is the provable route to lower delay. **Latency: negligible** (arithmetic moves out of the model; prompt slightly longer).
(c) **Works at 0.5B–1.7B** — turning "compute pressure" into "compare given numbers" shrinks the task to small-model capacity.
(d) Wu, Ghosal, Zhang & Chuah, *IEEE T-VT* 67(2), 2018 (delay-based back-pressure); Levy & Geva 2024 (digit-wise number encoding, arXiv 2410.11781); LLMLight observation design (Lai et al., KDD'25).

**A2. Decouple reasoning from JSON — free-text rationale FIRST, action LAST, and never answer-first.**
(a) Prompt for one short line of reasoning ("Phase 2 has the highest score and longest wait → serve 2") then the JSON `{"phase": 2}` as the final tokens. Do not use a JSON schema that puts `phase` before any reasoning field.
(b) **Delay: positive** (recovers the 10–30% reasoning loss that JSON-first causes). **Latency: tiny increase** (a few extra rationale tokens; still well under 10s at temp 0 with `/no_think`).
(c) **Most important at 0.5B–1.7B**: the "format tax" falls hardest on capacity-limited models.
(d) Tam et al., EMNLP 2024 (arXiv 2408.02442); "Capacity, Not Format" 2026 (arXiv 2606.09410); "Thinking Before Constraining"/In-Writing (arXiv 2601.07525).

**A3. Constrain only the final action token to the valid phase set (guided-choice), not the whole output.**
(a) Use vLLM `guided_choice` / XGrammar / llguidance / Outlines to force the phase index into `{0…K−1}` *after* the rationale. This eliminates invalid/None outputs (so the shield rarely fires) without taxing reasoning.
(b) **Delay: mildly positive** (fewer fallbacks to raw MaxPressure means more delay-aware decisions actually execute). **Latency: negligible** — XGrammar achieves "near-zero overhead structure generation in end-to-end LLM serving" with "up to 100× speedup" in per-token structure handling (Dong et al., arXiv 2411.15100).
(c) **Works at 0.5B–1.7B and especially helps them** — small models "often fail to generate a valid selection without formal runtime constraints."
(d) Tam et al. 2024 (classification improves under constraint); sub-5B Gemma constrained-choice result (+0.35 on 24-way classification); XGrammar (Dong et al., arXiv 2411.15100); JSONSchemaBench (Geng et al., arXiv 2501.10868).

**A4. Keep/strengthen switching hysteresis + enforce min-green and phase-skip.**
(a) Beyond EvolveSignal-style hysteresis, add an explicit **min-green** (model may not switch before it elapses) and **skip empty phases**; expose "time-since-last-served" per phase so the model can prevent starvation.
(b) **Delay: positive** under most demands — cyclic/min-green discipline reduces lost time and stops; MaxPressure's instantaneous switching is a known delay weakness. **Latency: none.**
(c) **Scale-independent** (a shield/wrapper rule, not a model capability).
(d) Barman & Levin, *TRR* 2022 (cyclic MP + phase-skip best delay); Robbennolt, Chen & Levin, *TRR* 2022 (switching scheme > weight function); Levin, Hu & Odell, *TR-C* 2020 (cyclical phase structure); SCMP (Sun et al., *TR-C* 2022) on switching loss.

**A5. Normalise and format the numbers carefully.**
(a) Present integers (rounded queue counts, waiting-times in whole seconds), aligned in a compact table; optionally min-max normalise scores to 0–100. Avoid long decimals — LLMs make digit-space errors and split multi-digit numbers across tokens.
(b) **Delay: small positive** (fewer misreads → fewer wrong picks). **Latency: neutral.**
(c) **Especially helps 0.5B–1.7B.**
(d) Levy & Geva 2024 (arXiv 2410.11781); Singh & Strouse 2024 (tokenization & arithmetic, arXiv 2402.14903).

**A6. Add a commonsense + role instruction and ONE worked example (light few-shot), not many.**
(a) Keep the LLMLight-style "prioritise long queues and long-waiting vehicles, avoid starvation" instruction; add at most one balanced in-context demonstration mapping a state table to the correct action + one-line reason. Test with it ON and OFF — few-shot can hurt.
(b) **Delay: small/uncertain** (task-dependent; can help framing, can also distract a tiny model). **Latency: small increase** per extra example.
(c) At 0.5B–1.7B, gains from many-shot are unreliable; prefer 0–1 shot.
(d) Lai et al. KDD'25 (commonsense prompt); INSTRUCTEVAL (arXiv 2306.04757, "may even worsen … in some cases"); few-shot-on-small-models evidence (arXiv 2402.02549).

**A7. Do NOT rely on self-consistency / majority vote.**
(a) Skip multi-sample voting; keep temperature 0, single pass.
(b) **Delay: neutral-to-negative** (little accuracy gain on this symbolic task; can add noise). **Latency: strongly negative** (N× cost, unaffordable in a 10s loop).
(c) SC's justification (high single-pass variance) is weakest exactly where you want determinism; it "under-performs … particularly on symbolic tasks" even at 7B.
(d) Theorem-of-Thought (arXiv 2506.07106); "Self-Consistency Is Losing Its Edge" (arXiv 2511.00751).

### TIER B — Decoding & model selection (cheap, no training)

**B1. Prefer Qwen3-1.7B (or Qwen3-4B if latency allows) or Phi-4-mini as the backbone; run in non-thinking mode.**
(a) Benchmark qwen3-1.7B `/no_think` and phi-4-mini against qwen2.5-1.5B/0.5B on your SUMO harness; use the smallest that clears the delay bar.
(b) **Delay: positive** (stronger instruction-following → more correct picks). **Latency: `/no_think` keeps it ~0.3s vs ~7s.**
(c) 1.7B–4B is the sweet spot; 0.5B often needs A1 + Tier-A scaffolding or fine-tuning to be reliable.
(d) Qwen3 Technical Report (arXiv 2505.09388); Phi-4-Mini Technical Report (arXiv 2503.01743); EdgeReasoning (arXiv 2511.01866, NR best on 1.5B).

**B2. Avoid reasoning-tuned SLMs for this task unless benchmarked to win.**
(a) Treat phi-4-mini-reasoning / R1-distills as candidates only if `/no_think`-style suppression is impossible; their CoT overhead threatens the 10s budget and small reasoning models overthink.
(b) **Delay: unclear gain. Latency: worse** (long CoT).
(c) Reasoning tuning helps math at ≥1.5B but "smaller models … overthink"; on 1.5B, suppressing reasoning was best.
(d) Phi-4-Mini-Reasoning (arXiv 2504.21233); "Danger of Overthinking" (arXiv 2502.08235); EdgeReasoning (arXiv 2511.01866).

**B3. Use INT8 quantization; test INT4 only with AWQ/GPTQ and verify no delay regression.**
(a) Deploy W8/INT8 by default; if memory forces INT4, use AWQ or GPTQ (not vanilla PTQ) and re-benchmark decision accuracy AND CoT length.
(b) **Delay: INT8 ≈ neutral; INT4 risks small negative on the smallest models. Latency: INT4 ~2–5× faster decode but may emit longer output.**
(c) INT4 degradation is worst for the smallest models — the ones you most want to run.
(d) "Give Me BF16 or Give Me Death" (Kurtic et al., ACL 2025); "Quantization Meets Reasoning" (arXiv 2505.11574); EdgeReasoning (arXiv 2511.01866).

### TIER C — Lightweight adaptation (when Tier A/B don't reliably beat the baseline on the smallest models)

**C1. LoRA/QLoRA imitation fine-tuning on trajectories from a DELAY-optimising oracle (highest-confidence reliability upgrade).**
(a) Generate expert (state→action+rationale) trajectories from (i) an offline/optimal SUMO solver or delay-based MP and (ii) filter to actions a value network scores highest (LLMLight's recipe), then LoRA/QLoRA-fine-tune the SLM to imitate. Critically, train on a *delay-minimising* teacher, not on vanilla MaxPressure, so the student can exceed the baseline.
(b) **Delay: large positive** — this is what let LLMLight's Qwen2-0.5B reach 328.1s ATT (from 1124.8s origin) and *beat Llama2-70B*, using own-intersection info only and competitive with neighbour-communicating Advanced-CoLight. **Latency: unchanged at inference** (LoRA merges; still one forward pass).
(c) **This is the technique that makes 0.5B–1.7B reliably strong.** Per Dettmers et al., QLoRA "reduces memory usage enough to finetune a 65B parameter model on a single 48GB GPU while preserving full 16-bit finetuning task performance" (Guanaco reaches "99.3% of the performance level of ChatGPT while only requiring 24 hours of finetuning on a single GPU") — so fine-tuning a 0.5–4B model is trivial on modest hardware.
(d) LLMLight/LightGPT (Lai et al., KDD'25, arXiv 2312.16044 — imitation fine-tuning + critic-guided policy refinement via LoRA); QLoRA (Dettmers et al., arXiv 2305.14314); CoLLMLight fine-tuning strategy (arXiv 2503.11739).

**C2. Knowledge distillation from a larger TSC teacher (rationales + actions).**
(a) If a 7–14B model (or GPT-class) reliably beats MaxPressure on your corridor, distil its state→(reason, action) traces into the SLM (response-based KD / SFT), which also teaches the *reasoning style* that keeps the small model on-task.
(b) **Delay: positive. Latency: unchanged** at inference.
(c) Works at 0.5B–1.7B; distillation is "now a standard playbook" for compressing reasoning into tiny models (e.g., R1-Distill-Qwen-1.5B).
(d) LLMLight (GPT-4 → LightGPT distillation); LoRA-distillation evidence (arXiv 2511.19648, Qwen3-4B recovers most of teacher planning accuracy on ~10% of data).

**C3. RAG / in-context memory of past decisions (use only if you cannot fine-tune).**
(a) Retrieve nearest past (state, good-action) cases and inject as dynamic few-shot.
(b) **Delay: small positive; Latency: increases with retrieved context** (risk against the 10s budget on small models with long prompts).
(c) Marginal at 0.5B–1.7B — long-context few-shot is where small models are weakest; prefer C1/C2.
(d) RAG-enhanced distributed LLM-TSC (ResearchGate 397087983); DoubleDipper (arXiv 2406.13632) on few-shot context cost.

### Theory check (Question 6) — why an own-junction SLM can beat instantaneous MaxPressure on delay
MaxPressure selects the phase maximising `Σ (upstream queue − downstream queue)`; it is throughput-optimal (Varaiya 2013; Kouvelas et al. 2014) but (i) memoryless on waiting time, so it can starve short-but-old queues; (ii) instantaneous, so it ignores switching/clearance lost time and is no longer even throughput-optimal once switching loss is modelled ("the original max pressure control (Varaiya, 2013) is no longer a throughput-optimal policy … with … the phase switching loss," Sun et al., TR-C 2022). Three own-junction modifications provably or empirically cut delay: **(1) delay/age-weighted pressure** — weight movements by accumulated waiting time (Wu et al. 2018 prove throughput-optimality *and* better delay/fairness); **(2) backlog + age combined** — a weighted queue-and-delay score (Wu et al.'s general weighted scheme); **(3) min-green / clearance-aware, cyclic switching with phase-skip** — reduces lost time and stops (Barman & Levin 2022; Levin et al. 2020). An SLM given these signals is effectively executing a delay-weighted, hysteresis-constrained max-pressure rule — exactly the class of controllers shown to dominate instantaneous MaxPressure on delay while staying within own-junction information. The SLM's role is not to invent a better rule from scratch (a 0.5B model cannot) but to *rank pre-scored phases and apply commonsense anti-starvation deviations* — a task within its capacity.

## Recommendations (staged)

**Stage 0 — Instrument & establish the gap (before any model change).** Log per-phase queue, total waiting time, time-since-served, and the delay-based-pressure score every decision. Confirm current mean network delay vs MaxPressure on Euston Road A501 across low/medium/near-saturation demand. *Benchmark that changes the plan:* if the SLM already ties MaxPressure at medium demand, concentrate effort on the near-saturation regime, where delay-weighting helps most.

**Stage 1 — Ship Tier A (about a day's work, no training).** Implement A1 (pre-computed delay-weighted scores in a compact integer table), A2 (rationale-then-JSON, never answer-first), A3 (guided-choice on the phase token), A4 (min-green + phase-skip + time-since-served), A5 (clean number formatting). Keep A7 (no self-consistency). *Threshold to proceed:* if qwen3-1.7B `/no_think` now beats MaxPressure on mean delay in ≥2 of 3 demand regimes with p<0.05 over ≥10 seeds, you have a result.

**Stage 2 — Model/decoding sweep (Tier B).** Sweep {qwen2.5-0.5B, qwen2.5-1.5B, qwen3-0.6B, qwen3-1.7B, qwen3-4B, phi-4-mini} at INT8, temp 0, `/no_think`. Report the Pareto front of mean-delay vs per-decision latency. *Threshold:* pick the smallest model within the 10s budget that beats MaxPressure; if none does at 0.5–0.6B, that is itself a finding and motivates Stage 3.

**Stage 3 — LoRA/QLoRA imitation fine-tuning (Tier C1) to make the smallest models reliable.** Build an expert dataset from an offline SUMO delay optimiser (and/or delay-based MP), filter with a critic Q-network (LLMLight recipe), and QLoRA-fine-tune qwen2.5-0.5B/qwen3-0.6B/1.7B on (reason, action) targets. *Threshold:* aim to replicate LLMLight's qualitative result — a fine-tuned sub-1B model beating strong un-tuned baselines — and to *reliably* (every seed) beat MaxPressure on delay. If fine-tuning a 0.5B still can't clear the bar, distil from a 7–14B teacher (C2) instead.

**Stage 4 — Robustness & write-up.** Stress-test under incidents/demand shocks and report validator-fallback rate (how often the shield fires). A low fallback rate + delay win is the headline; a high fallback rate means the SLM is contributing little and MaxPressure is doing the work — flag this honestly.

## Caveats
- **Most cited head-to-head numbers are from grid/synthetic datasets (Jinan, Hangzhou, New York), not a London A501 corridor, and use *average travel time*, not your exact *mean network delay* metric.** Treat LLMLight/CoLLMLight magnitudes as directional, not as predictions for your setup.
- **LLMLight/CoLLMLight beat MaxPressure only *after* fine-tuning (LightGPT) or with GPT-4-class models.** Their *un-tuned small* models (e.g., Qwen2-0.5B "Origin" at 1124.8s ATT) were far worse than baselines — consistent with the expectation that a raw sub-1B model will *not* reliably beat MaxPressure without the Tier-A scaffolding and/or Tier-C fine-tuning here.
- **The "smaller models are hurt more by format constraints" claim is an inference** from the pattern in Tam et al. (who did not test large open models and list this as a limitation), corroborated by the "Capacity, Not Format" follow-up; it is well-supported directionally but not a single quantified scaling law.
- **Quantization results are task-dependent**; the INT4 figures cited are from math/coding reasoning benchmarks, not TSC — verify on your own harness before trusting INT4 on a 0.5B model.
- **EvolveSignal's result is vs Webster fixed-time, not vs MaxPressure**: it reports "reducing average delay by 20.1% and average stops by 47.1%" over Webster, and it discovers *fixed-time* code offline — relevant as a source of switching/green-allocation heuristics to hard-code into your shield, not as a real-time SLM controller.
- **iLLM-TSC's 17.5% waiting-time reduction is a *correction layer over an RL agent* under degraded communication**, not a standalone myopic single-junction controller; use its "LLM validates/adjusts a base policy" pattern as an analogue to your shield, not as a delay benchmark.
- Some 2026-dated arXiv sources surfaced (e.g., "Capacity, Not Format," SignalClaw, the Gemma small-model constrained-choice paper); they corroborate 2024–25 findings but should be double-checked for final provenance before formal citation.
## Measured on OUR harness (Euston A501, SUMO, end=1200, seed 42, PILOT n=1)

Applying the playbook to the real corridor (baseline myopic MaxPressure mean network
delay = 314.55 s; on-device models, temperature 0, `/no_think` for qwen3):

| Model | plain myopic (queue only) | delay-aware v1 (queue + accumulated wait, model weighs) | delay-aware v2 (A1: rank one pre-computed delay_score) |
|---|---|---|---|
| qwen2.5-0.5b | **235.0 s (beat)** | 291.3 s (beat) | 307.3 s (beat) |
| qwen3-1.7b | **233.7 s (beat)** | 239.8 s (beat) | 337.5 s (LOSES) |
| qwen3-0.6b | 267.1 s (beat) | **262.9 s (beat)** | 287.3 s (beat) |
| phi-4-mini | 314.7 s (match) | **270.4 s (beat, LIFTED)** | 326.7 s (LOSES) |

Honest findings (descriptive pilot, n=1, no significance claim per §8):
1. **Plain myopic SLM already beats MaxPressure on delay** for the small qwen models
   (qwen2.5-0.5b best at 235 s, -25%). The H1 "can a myopic SLM beat MaxPressure"
   question is answered YES at the smallest scale, without any delay-aware scaffolding.
2. **The delay-aware v1 framing (present queue AND accumulated wait, let the model
   weigh them) helped the WEAKER models** — it lifted phi-4-mini from match to beat
   (314.7 -> 270.4 s) and nudged qwen3-0.6b — **but HURT the already-strong small
   models** (qwen2.5-0.5b 235 -> 291 s). Not a uniform win.
3. **A1 as a single pre-computed delay_score (v2) was a NET NEGATIVE vs v1**: it
   dropped phi-4-mini and qwen3-1.7b back to LOSES. Collapsing queue+wait into one
   "rank the highest accumulated-wait phase" number made a greedily-serve-oldest policy
   that over-serves few-but-old queues; the richer two-number framing let the model
   balance backlog against age better. On this task/scale, giving the small model the
   raw signals to weigh beat pre-digesting them into one score.
4. We did NOT keep iterating the prompt on one seed (that would be p-hacking). The
   shipped delay-aware controller is v1; v2 is recorded as a measured negative.
5. Consistent with the playbook's own caveat: raw sub-4B models beating MaxPressure is
   real here but prompt-only gains are uneven; the route to a UNIFORM, reliable win
   across the smallest models is Tier-C LoRA/QLoRA imitation fine-tuning on a
   delay-optimising oracle (LLMLight recipe), not further prompt tuning.
