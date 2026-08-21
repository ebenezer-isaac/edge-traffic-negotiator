# Fine-tuning feasibility study (research phase, 2026-08-06)

**Trigger:** supervisor directive (Akin Delibasi, meeting 2026-08-06): LoRA/QLoRA fine-tune an on-device SLM on frontier-model-distilled traffic decisions; check HuggingFace for prior art first; keep trainable parameters small; Claude generates both the training code and the dataset.

**Method:** four independent research tracks (fine-tuning technique + compute; Foundry Local custom-model serving; prior art; codebase audit), conducted 2026-08-06 before any spec change or implementation. This document is the synthesis. Sources cited inline.

---

## 1. Feasibility conclusion

**FEASIBLE, with one gating unknown that must be de-risked FIRST and a hard calendar constraint.**

- The pipeline `LoRA fine-tune (off-device) -> merge to bf16 -> Olive int4 ONNX compile -> register in the Foundry Local cache -> serve via the existing OpenAI-compatible endpoint` is officially documented by Microsoft and the tooling supports our exact architectures (Qwen3ForCausalLM and Phi3ForCausalLM are both in the onnxruntime-genai model builder; Foundry Local's own catalog qwen3/phi-4-mini artifacts are produced by that path). Confidence ~90% from documentation; **no published example exists of the complete LoRA-fine-tune -> Foundry-Local-serving chain in one artifact**, so doing it end-to-end is itself a small contribution and a real risk.
- Training compute is a non-issue: QLoRA of qwen3-0.6b/1.7b fits on the local RTX 2060; one UCL 4090 session covers dozens of runs including phi-4-mini. Serving stays on Foundry Local on the 2060 — **the hard requirement is not violated: only training happens off the Microsoft serving stack.**
- The existing eval harness needs **zero mandatory code changes**: `experiment_frontier.py --models <served-id>` falls through the CATALOG as a raw model ID.
- **We cannot build the dataset from existing logs** (859k decisions were logged as counts only; prompts/responses were discarded), but the decision-battery pipeline is a working seed of the distillation pipeline: CPU-only SUMO state sampling + Claude labeling, proven at n=80. Scaling to thousands is a few CPU-hours plus subagent labeling batches.
- **Prior art exists and must be cited**: LLMLight/LightGPT (KDD 2025) fine-tuned LLMs for signal control down to 0.5B (MIT, on HF). Its recipe (teacher demonstrations -> critic filter -> LoRA) is public; its data is not. Fine-tuned-LLM closed-loop gains over MaxPressure in that literature are ~1-2% — so the honest primary claim is **per-decision competence** (our battery gap: Claude 96% vs phi-4-mini 72% vs qwen3-0.6b 51%), with closed-loop delay as the secondary, possibly-null outcome.

**Single riskiest step:** GPU execution-provider match at serving time. Docs compile for CPU EP; CUDA EP registration for custom models has open flakiness issues (Foundry-Local #295 fixed-pending-release, #344 version-skew unresolved). Mitigation: CPU-compiled int4 is the guaranteed path and is latency-viable for a 0.6B; a GPU compile is an upside bet, not a dependency.

---

## 2. What each track found

### 2.1 Fine-tuning technique + compute (web research)

- **Framework: Unsloth** (explicit Qwen3 0.6B/1.7B support and guide; ~2x speed, ~70% less VRAM; RTX 2060 = CUDA 7.5 qualifies, fp16 not bf16). HF PEFT/TRL is the fallback reference implementation. Phi-4-mini works but has the most sharp edges (rope_scaling fix needs transformers >= 4.49; pad/eos-token trap causes infinite generation post-fine-tune — use the patched `unsloth/Phi-4-mini-instruct`; 200k vocab inflates training memory).
- **VRAM (QLoRA, estimates):** 0.6B ~1.5-2.5GB, 1.7B ~2.5-3.5GB, 3.8B ~4-5GB. The 2060 covers the two Qwen sizes; phi-4-mini wants the 4090.
- **Wall-clock (4090, ~3k examples x 3 epochs, estimates):** 0.6B ~15-30 min, 1.7B ~45-90 min, 3.8B ~2-4h. Compute is not the constraint.
- **Dataset size:** 200-500 curated examples already work for narrow structured tasks; **target 2,000-5,000 filtered examples**, stratified by topology, demand level, and phase outcome. Curation beats volume.
- **Distillation practice:** teacher generates k candidates per state, keep only verified-correct ones (rejection sampling). Our setting is favorable: correctness is checkable WITHOUT an LLM judge (legal-phase rule checks + a deterministic delay-aware greedy/pressure verifier), which is exactly the critic-filter role LLMLight used an RL value network for.
- **Failure modes to engineer around:** (i) chat-template mismatch between HF training and ONNX serving (the classic silent killer — verify with raw-string probes against the served endpoint); (ii) Qwen3 thinking-mode degradation when fine-tuned on non-thinking data (we train and serve non-thinking only, matching how we already run with `/no_think`); (iii) JSON-format regression (train targets byte-exact to what `SLMAgent._parse` expects; JSON-validity rate is a first-class eval metric); (iv) overfitting on templated inputs (dedupe near-identical states; hold out a stratified eval set BEFORE training).

### 2.2 Foundry Local custom-model serving (web research; the make-or-break)

- **Officially supported.** Microsoft Learn: "Compile Hugging Face models and run on Foundry Local" (updated 2026-07): `olive optimize --model_name_or_path <local merged checkpoint> --precision int4` -> write `inference_model.json` (`{"Name": "my-model:1"}` + a `PromptTemplate` extracted from the tokenizer chat template) -> copy into the Foundry cache -> discovered automatically, served via the same OpenAI-compatible endpoint. Microsoft's blog states verbatim that the same workflow applies to fine-tuned models.
- **Architectures:** onnxruntime-genai builder supports `Qwen3ForCausalLM`; phi-4-mini declares `Phi3ForCausalLM` (supported). The catalog's own qwen3-0.6b (0.52GB), qwen3-1.7b (1.39GB), phi-4-mini (3.72GB) artifacts come from this exact path — verified locally via `foundry model list`.
- **Quantization:** int4 RTN via the model-builder route; conversion of a 0.6B-4B model is minutes on CPU. Post-merge int4 can partially wash out fine-tune deltas -> **all reported evals run on the int4 artifact as served, never the fp16 checkpoint.**
- **LoRA adapters at runtime: NOT exposed by Foundry Local** (ONNX Runtime GenAI has the API; Foundry Local hides it). **Merge the LoRA into base weights before compiling** — the standard path anyway. Never export from a 4-bit checkpoint (bnb checkpoints fail Olive export, Foundry-Local #69); merge in bf16/fp16.
- **Known warts:** CUDA-EP registration flakiness for custom models (#295), custom models breaking across Foundry Local version upgrades (#344) -> **pin the Foundry Local version** the artifact is validated against and record it. SDK catalog-lookup wart for custom names -> the raw REST/OpenAI endpoint always works (which is what `slm_agent.py` uses).
- **Compliant fallback** if Foundry Local refuses the artifact: ONNX Runtime GenAI directly — the identical Microsoft runtime that powers Foundry Local. Defensible as the Microsoft stack; documented as a fallback, not the plan.

### 2.3 Prior art (web research)

- **LLMLight / LightGPT** (arXiv 2312.16044, KDD 2025, MIT, code public): GPT-4 demonstration trajectories -> critic (RL value network) filters high-quality ones -> LoRA imitation fine-tune -> critic-guided policy refinement. Checkpoints on HF include **LightGPT-0.5B-Qwen2** (our scale). Beats MaxPressure modestly on CityFlow Jinan/Hangzhou; roughly matches Advanced-CoLight. Training data NOT released; recipe reproducible with any teacher.
- **Traffic-R1** (arXiv 2508.02344, ACL 2026): Qwen2.5-3B, R1-style RL fine-tune, Apache-2.0 checkpoint on HF, claims real deployment. Training data withheld.
- **DGLight** (arXiv 2604.25259): the whole fine-tuned-LLM vs MaxPressure gap on CityFlow is ~1-2% — calibrates expectations for closed-loop delay.
- **iLLM-TSC** (arXiv 2407.06025): architecturally closest to our hybrid (RL proposes, cloud LLM vetoes — ours is inverted and on-device). No fine-tuning.
- **Nothing exists** on HF fine-tuning phi-family or qwen3 for TSC, and no published Claude-distilled TSC model. Our differentiators survive: SUMO + real London DfT demand (everyone else is CityFlow on Jinan/Hangzhou grids), on-device serving constraint, MaxPressure shield, trust/audit/UK-law layer, n=30 seed rigor.
- **Positioning duty:** cite LLMLight as the recipe source; optionally evaluate LightGPT-0.5B-Qwen2 / Traffic-R1-3B zero-shot on our maps as external baselines (their prompt formats are CityFlow-shaped; porting cost is real, so this is stretch scope).

### 2.4 Codebase audit (read-only investigation)

- **No training pairs exist in logs.** `frontier_raw/` (2,055 files, 859,468 decisions) stores aggregates only; response text is discarded in `SLMAgent.choose_phase` (src/slm_agent.py:249-257); per-decision events are dropped by `run_arm` unless `liars` is set.
- **The battery IS the dataset pipeline seed:** `SamplingAgent` captures full decision contexts via pure-CPU SUMO (~690 decisions/map/seed at end=1200); 80 states + Claude answers already stored; the `_diverse` picker dedupes on unique halting vectors. Scaling = more seeds/maps + subagent labeling + an optional rationale field.
- **Integration surface: SMALL.** `CATALOG.get(m, m)` fall-through (experiment_frontier.py:237) means `--models <served-id>` needs zero changes. `foundry` CLI is used only for `service status/start`, never model management.
- **Traps to fix BEFORE dataset build:**
  1. The battery prompt is NOT byte-identical to the live controller prompt (`claude_decision_battery.py:92-111` says `queue=/waiting_s=` vs live `queued=/wait=...s (CURRENT)`, different system wording). Canonicalize to the LIVE `slm_agent.py` format or we train on a prompt the controller never sends.
  2. `think_suffix = " /no_think" if "qwen3" in model` (slm_agent.py:219): the served fine-tune's ID must keep the `qwen3` substring AND training prompts must include the trailing `/no_think`, or the suffix logic must be made explicit config.
  3. Response parsing (`SLMAgent._parse`, slm_agent.py:283-295): braced JSON `{"phase": N}` first. Train targets emit exactly `{"phase": N}`.
  4. Optional 15-line change: persist per-decision events in future sweeps so every run doubles as training data.

---

## 3. What cannot be worked around (hard limits)

1. **Foundry Local not serving the artifact at all** (version skew, conversion failure). Probability low (~10%) but non-zero; the ONNX Runtime GenAI fallback keeps the Microsoft-stack story but weakens the "Foundry Local" claim to "Foundry Local runtime". De-risked by Step 0 below before any other work.
2. **int4 wash-out of the fine-tune delta.** If the merged model's gains vanish under int4 RTN quantization, there is no served improvement to report. Cannot be prevented, only measured — hence all evals at int4-as-served.
3. **Closed-loop delay may not move.** The literature says fine-tuned-LLM gains over MaxPressure are ~1-2%; our own powered n=30 result says the stock SLM already matches MaxPressure. The fine-tune's honest primary endpoint is per-decision competence (battery accuracy, catastrophic-failure count, divergence quality), not a delay revolution. A null closed-loop result is a reportable outcome, not a failure.
4. **Calendar.** Hard deadline 7 Sep; writing was to start mid-Aug. The expansion costs ~5-8 working days for one model before closed-loop eval wall-clock. It fits ONLY with a single primary model and parallel writing; a hard go/no-go checkpoint is mandatory.

## 4. What can be worked around (with the workaround)

| Problem | Workaround |
|---|---|
| No training pairs in existing logs | Battery pipeline: CPU SUMO sampling + Claude subagent labeling (proven at n=80) |
| GPU-EP compile flakiness | CPU-EP int4 is the guaranteed serve path; 0.6B stays latency-viable; GPU compile attempted as upside |
| Qwen3 thinking-mode degradation | Train + serve non-thinking only (`/no_think`, empty think block); state as scoped |
| phi-4-mini tokenizer/pad traps | Use patched unsloth checkpoint; or descope phi-4-mini to stretch goal |
| Chat-template mismatch across HF->ONNX hop | Embed PromptTemplate in inference_model.json; byte-level probe of the served endpoint before any experiment |
| Battery prompt != live prompt | Canonicalize battery to live format first (small change, must precede dataset build) |
| Foundry version skew breaking the artifact | Pin + record the Foundry Local version; re-validate after any upgrade |
| Overfitting templated states | Dedupe unique halting vectors; stratified held-out set built before training |
| Teacher labels wrong | Verifier filter (legal-phase rules + deterministic delay-aware reference) — rejection sampling, no LLM-as-judge |

## 5. Model choice

**Primary: qwen3-0.6b.** Largest headroom (51% battery accuracy vs Claude's 96%), trains on the local 2060 (no UCL dependency), fastest inference, cleanest Unsloth support, and mirrors LightGPT's proof that 0.5B-scale TSC fine-tuning works. **Stretch: phi-4-mini** (needs 4090, most tooling sharp edges, but the strongest stock model — tests whether distillation helps where headroom is small). qwen2.5-0.5b is the tiebreak alternative if qwen3's hybrid-thinking complicates training.

## 6. Timeline (calendar-honest, today = Wed 2026-08-06)

| Window | Work | Gate |
|---|---|---|
| Aug 6-8 | **Step 0: pipeline proof.** Olive-compile the STOCK qwen3-0.6b HF checkpoint -> register in Foundry cache -> serve -> run one existing sweep cell against it. No data work before this passes. | **GO/NO-GO: if Step 0 fails by Aug 8 evening, the expansion is descoped to a written design + prior-art analysis.** |
| Aug 8-12 | Canonicalize battery prompt to live format; sample ~10k states (CPU, stratified over topology x seed x demand); Claude-label via subagent batches with verifier filtering -> 2-5k accepted + 300-500 held-out eval set. | Dataset battery (dedupe, stratification, leakage check) |
| Aug 12-14 | QLoRA train qwen3-0.6b (2060 or 4090); merge bf16; Olive int4; offline eval AT INT4: battery accuracy, JSON-validity, held-out phase accuracy vs stock. | Offline gate: fine-tune must beat stock qwen3-0.6b on held-out battery accuracy at int4, else report negative and stop |
| Aug 14-20 | Closed-loop seed-30, fine-tuned vs stock vs MaxPressure vs fixed-time, Old Street + Euston peak-hour, myopic + sota. Existing harness, `--models` fall-through. Writing proceeds IN PARALLEL from Aug 12. | Existing §8 stats protocol |
| Aug 20-22 | Aggregate, dashboard/artifact update, dissertation chapter. **Absolute expansion cutoff Aug 22**; anything unfinished is reported as designed-not-run. | |

Person-time estimate: 5-8 working days for the primary model (research-agent estimate, consistent across tracks); each additional model +1-2 days. Closed-loop eval dominates wall-clock, not training.

## 7. What this does NOT change

The thesis headline stays frozen (MASTER-SPEC §0/§1). Fine-tuning is a new point on the **configuration axis** of the same scale-threshold question — "at what model scale / configuration does it become possible" now includes {stock, fine-tuned} — not a new thesis. Serving remains Foundry Local on the RTX 2060. The shield, audit, and trust layers are untouched. A null or negative fine-tune result is a valid, reportable outcome under the same honest-negative doctrine as everything else.

## 8. FT-0 pipeline proof: PASSED (2026-08-06, same day — two days ahead of the go/no-go gate)

The complete chain ran end-to-end on the stock checkpoint, per MASTER-SPEC §14.3 step 1:

1. **Toolchain:** isolated Python 3.11 venv (`.venv-olive`); olive-ai 0.13.0, onnxruntime-genai 0.15.2, torch 2.13.0+cpu, transformers 5.14.1. Note: `olive optimize` itself routed int4 through a GPTQ pass requiring HF `datasets` + calibration; the **onnxruntime-genai model builder was used directly instead** (`python -m onnxruntime_genai.models.builder -p int4 -e cpu`) — the same tool that produces Foundry's catalog artifacts (int4 RTN, no calibration). This is the pinned compile path for the fine-tune.
2. **Artifact:** Qwen/Qwen3-0.6B (bf16 HF checkpoint, 1.43GB) -> int4 ONNX in seconds, 387MB (model.onnx + external data + genai_config.json + tokenizer + chat_template.jinja).
3. **Registration:** `inference_model.json` (Name `qwen3-0.6b-ft0` — keeps the `qwen3` substring for the live `/no_think` suffix — + the ChatML PromptTemplate copied from the catalog qwen3-0.6b artifact); folder copied into the Foundry cache root. Discovered by `foundry cache ls`, loaded by `foundry model load` (cosmetic "Failed to process model #0 on page 1" pagination errors appear but do not block).
4. **Serving probe:** OpenAI endpoint, temp 0, 2 identical responses (determinism holds), empty think block, valid fenced JSON `{"phase": "0"}`, ~0.9-1.0s per call on CPU EP.
5. **Sweep cell (zero code changes, CATALOG fall-through):** `--models qwen3-0.6b-ft0 --configs myopic --topologies bloomsbury_grid --seeds 1` -> **measured**: 716 decisions, 700 valid SLM proposals (97.8% parse rate), 493 served-by-SLM, delay 517.8s vs baseline 518.7s, p99 latency 1.15s. Stock catalog qwen3-0.6b on the identical cell: 711 decisions, 692 valid, delay 527.6s, p99 0.78s — near-identical behavior profile (residual differences consistent with the different int4 quantizations), CPU-EP latency fully viable against the ~10s decision interval.

**Pins (per §14.4):** Foundry Local **0.8.119**; compile = ort-genai model builder int4/cpu; catalog GPU artifacts on this machine use the **WebGPU** EP (not CUDA — Windows build 19045 predates Windows ML EP autoregistration), so a WebGPU-provider genai_config is the documented upside path if CPU latency ever becomes limiting. GO for the dataset phase (§14.3 steps 2-3).

## 9. Measured results log (updated as gates pass)

**2026-08-07 — v1 offline gate PASSED.** qwen3-0.6b-ft1 (sota-only train, 14,493 examples, QLoRA r=16, 2 epochs, RTX 2060, train loss 0.0136) vs ft0 (stock compiled through the IDENTICAL int4-CPU pipeline — the fair control after the catalog WebGPU model was found emitting garbage tokens post-long-uptime, itself a recorded serving-reliability finding): **97.42% vs 55.10%** accuracy against frontier-teacher labels on the 1,510-state frozen sota holdout; strict-JSON 100% vs 93.4%; parse 100% both.

**2026-08-08 — generalist verdict + full 4-format offline table.** v2 (all-format train, 59,533 examples, 13.5h, loss 0.0145) matches the specialist on its own format (sota **97.68%** vs v1's 97.42%) → GENERALISTS ONLY. Complete table (ft2 vs ft0, same holdouts, int4-as-served): myopic **87.9% vs 45.6%**, sota **97.7% vs 55.1%**, prediction **97.6% vs 63.3%**, coordination **99.0% vs 69.3%**; strict-JSON 100% on every ft2 format. The myopic ceiling is intrinsically < 100% (privileged distillation: teacher saw waiting times the myopic prompt hides — disclosed in §14.4b). The prediction gap (+34.3pts) is direct evidence for the capacity hypothesis motivating §14.4b.

**2026-08-08 — Euston closed-loop interim (n=30, DISJOINT seeds, sota config).** ft1 mean −3.8% (sd 23.0, 17/30 wins, 3 catastrophic) vs ft0 −6.2% (sd 32.1, 20/30, 3 catastrophic) vs MaxPressure — both ns, matching the standing corridor null; fine-tune cut variance ~28% but did not delete the catastrophic tail on the corridor. **Robust structural finding: shield override rate 0.12 (ft1) vs 0.46 (ft0)** — the fine-tuned controller's decisions survive the MaxPressure shield ~4x more often, i.e. it genuinely owns most of the control. Bloomsbury + Old Street arms in flight.

**2026-08-08 — WebGPU serving of custom artifacts WORKS** (provider_options swap in genai_config, mirroring the catalog): ~720ms/call warm vs ~1,550ms CPU under load; **decision-equivalence CONFIRMED: 97.42% on the sota holdout — bit-identical accuracy to the CPU artifact — at p50 0.887s (vs 1.46s CPU), 100% strict JSON.** The full factorial runs on WebGPU-served artifacts; WebGPU long-uptime degradation risk mitigated by per-sweep health probes + fail-loud parse accounting.


**2026-08-19 — phi-4-mini (4GB-class flagship) trained + full offline table; SCALE-SATURATION FINDING.** Trained on hotrod (UCL RTX 4090, booking 4B0493CF): QLoRA r=16 on the full 59,533-example 4-format dataset, 2.3h, 8.9M trainable params (0.23%). Served int4 via Foundry Local WebGPU on the RTX 2060 at sub-second p50, 100% strict JSON. Full holdout table: sota 97.1 / myopic 88.7 / prediction 97.4 / coordination 99.3 — **statistically indistinguishable from qwen3-0.6b-ft2 (97.7/87.9/97.6/99.0) despite 6x the parameters.** Both students sit at the teacher-agreement ceiling (98-99%): distillation SATURATES the per-decision task at 0.6B; scale buys nothing beyond it (stock baselines differ — phi 72% vs qwen3 51% battery — but post-distillation the gap vanishes). Variant queue (LOTO + 4 format specialists) trained the same evening; int4 compiles run locally after a hotrod py3.9/transformers-5 incompatibility (pinned lesson: compile with the local .venv-olive pairing; tokenizer_class "TokenizersBackend"->"GPT2Tokenizer" patch required for Foundry; strip auto_map for phi). Second serving-reliability event recorded: Foundry service self-restarted mid-eval (port 59562->60734), killing a 5,500/5,580 run fail-loud — long-session serving instability is now a twice-measured finding.

**2026-08-20 — CLOSED-LOOP FINE-TUNE VERDICT (v1 sweep COMPLETE: ft1 vs ft0, sota config, 3 topologies x 30 DISJOINT seeds, paired per-seed vs fixed-time baseline).** Per-topology (mean rel-delay, paired t): Euston peak-hour ft1 −3.85% (p=.16) / ft0 −6.16% (p=.12), head-to-head ns — the corridor null persists at n=30. Bloomsbury grid: **ft0 significantly HARMFUL (final n=30: +2.64%, p=1.5e-03); ft1 neutral (+0.68%, ns); head-to-head ft1 beats ft0 by −1.81% (p=.019)** — the only significant closed-loop effect of fine-tuning is REPAIRING the harm the stock model does under grid congestion. Old Street: ft1 −3.12% / ft0 −1.13%, both ns. Pooled n=90: ft1 −2.10% (p=.14), ft0 −1.51% (p=.43). Structural finding CONFIRMED at scale: override rate ft 0.11–0.18 vs stock 0.46–0.60 on every topology; authored share up to 0.90 (Old St ft1) vs 0.54 (ft0) — **fine-tuning converts the system from shield-driven to SLM-authored control without degrading delay, which is the property the audit/accountability layer (H2) actually needs.** Honest scope: at n=30 fine-tuning does NOT significantly beat the fixed-time baseline on any single topology; the delay-decoupling paradox (offline accuracy ≠ closed-loop delay) survives fine-tuning, consistent with the shield bounding worst-case behaviour for both arms. The crash-lost cell (ft0/bloomsbury/s30) was re-run 2026-08-20 (measured −5.4% on that seed); figures here are final n=30 values. Third+fourth serving-reliability artifacts recorded the same night: eval harness now auto-recovers from Foundry service self-restarts (re-discover endpoint + reload + retry-row, stats intact), and Foundry registration of raw model-builder output requires SYNTHESIZING inference_model.json (builder emits none; a patch-in-place chain 400-failed until v2 wrote it from the working template).

**2026-08-20 15:00 — PHI OFFLINE TABLE COMPLETE (7 rows x 4 formats, int4-as-served WebGPU on the RTX 2060, full 5,580-row frozen holdout, 100% strict-JSON on every row).** Accuracy (sota/myopic/prediction/coordination): stock catalog 59.0/87.5/86.0/87.0; **generalist ft 97.1/88.7/97.4/99.3**; LOTO 96.8/88.3/97.4/99.1; sota-spec 97.8/87.9/89.5/93.3; myopic-spec 87.9/87.0/88.8/91.8; prediction-spec 91.3/87.9/97.3/98.4; coordination-spec 89.1/87.4/94.7/99.3. VERDICTS: (1) **no specialist beats the generalist on its own format** (max delta +0.65pt, sota; coordination identical; prediction -0.1); (2) every specialist pays 4-8pts off-format; (3) **the myopic specialist loses even on-format** (87.0 vs 88.7) — mixed-format training regularises against the privileged-label noise that pure-myopic training overfits; (4) LOTO = generalist on all formats (no topology memorisation offline); (5) stock phi is 100% format-compliant and 86-88% on three formats — the distillation gain concentrates in the delay-aware sota format (+38.1pts) — so at 3.8B the fine-tune buys decision quality, not formatting. GENERALISTS-ONLY is now confirmed at both 0.6B and 3.8B with a clean monotone story. (Note: the earlier "stock phi 72%" figure was a partial-sample battery number; this table is the definitive full-holdout control.) p50 latencies 0.4-1.1s across all rows.

**2026-08-20 evening — ARTIFACT-PROVENANCE SENSITIVITY (unplanned methodological finding).** On the 26 Euston-peak-hour seeds shared between the powered stock replication and the ft closed-loop sweep, catalog qwen3-0.6b vs the identical-pipeline int4 compile of the same weights (ft0): mean rel-delay vs fixed-time **+4.1% vs −5.2%** — a 9-point mean shift from quantisation/packaging provenance alone (authored share 0.62 vs 0.68, override 0.40 vs 0.47). Confirms the ft0-control design choice quantitatively; dissertation results § now carries it as a field caution ("the same model is not the same controller across serving artifacts"). Also extracted from experiment_seed30_powered.json (n=30, stock arms): Old Street = strongest powered stock wins vs FT (qwen2.5-sota −11.8% p<.001, qwen3-0.6b-sota −9.6% p<.001, phi-myopic −8.6% p<.001; qwen2.5-sota also −4.9% p=.014 vs MaxPressure); Euston peak-hour = powered corridor null (all arms ≈ MaxPressure, none beat the floor).

**2026-08-21 — PHI CLOSED-LOOP CONFIRMATION ARM COMPLETE (90/90 cells, deferred=0): SCALE SATURATION HOLDS END-TO-END.** phi4mini-generalist (3.8B), sota, 30 disjoint seeds/topology, paired vs fixed-time: Euston −3.79% (p=.151), Bloomsbury +0.64% (ns), Old Street −0.97% (ns), pooled n=90 −1.37% (p=.203). Versus qwen3-0.6b-ft1 on the SAME cells: Euston −3.85%, Bloomsbury +0.68% — statistically indistinguishable arm-for-arm. Authorship profile identical too: override 0.12–0.17, authored share 0.70–0.88 (Old St). The 3.8B student buys nothing over 0.6B offline OR closed-loop — the saturation claim is now end-to-end and the dissertation's scale-threshold answer is final: **0.6B suffices**. p99 latency ≤1.1s throughout (3.8B WebGPU on the 2060).

**2026-08-21 — RETENTION PROBE COMPLETE (final campaign measurement).** Seeded 200-item MMLU sample (25 subjects x 8, seed 7, strict {"answer": "X"} contract) through the SAME Foundry endpoints: **phi stock 57.5% -> phi ft 53.0%** (z=0.91, p=.37 — no significant loss at n=200, format discipline retained 94% strict); **qwen3-0.6b stock 26.0% -> ft 21.5%** — stock already AT CHANCE on this format, so 0.6B forgetting unmeasurable (floor effect). Written into dissertation §threats + article limitations. THE EXPERIMENTAL CAMPAIGN IS 100% COMPLETE — every planned measurement done: offline (7-row phi + qwen tables), closed-loop (qwen n=30 + phi n=30 confirmation), powered stock replication, audit/crash-law 7/7, trust battery, trust-traffic, retention. Remaining work is writing only.

## 10. Sources (primary)

- MS Learn: Compile Hugging Face models for Foundry Local — https://learn.microsoft.com/en-us/azure/foundry-local/how-to/how-to-compile-hugging-face-models
- MS Community Hub: Deploying Custom Models with Olive and Foundry Local — https://techcommunity.microsoft.com/blog/educatordeveloperblog/deploying-custom-models-with-microsoft-olive-and-foundry-local/4489002
- Foundry-Local issues #295 (CUDA EP), #344 (version skew), #69 (bnb export) — https://github.com/microsoft/Foundry-Local/issues
- onnxruntime-genai model builder (Qwen3/Phi3 support) — https://github.com/microsoft/onnxruntime-genai
- Unsloth Qwen3 fine-tuning guide — https://unsloth.ai/docs/models/tutorials/qwen3-how-to-run-and-fine-tune
- LLMLight/LightGPT — https://arxiv.org/abs/2312.16044 · https://github.com/usail-hkust/LLMTSCS · https://huggingface.co/lightgpt/LightGPT-0.5B-Qwen2
- Traffic-R1 — https://arxiv.org/abs/2508.02344 · https://huggingface.co/Season998/Traffic-R1
- DGLight — https://arxiv.org/abs/2604.25259 · iLLM-TSC — https://arxiv.org/abs/2407.06025
- PhiCookBook olive-ort fine-tune example — https://github.com/microsoft/PhiCookBook/blob/main/code/03.Finetuning/olive-ort-example/README.md
- Omdena QLoRA primer (supervisor-shared) — https://www.omdena.com/blog/fine-tuning-small-language-models
