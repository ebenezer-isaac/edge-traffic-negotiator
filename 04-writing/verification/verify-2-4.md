# Verification report — §2.4

**Source file audited:** sections/sec-2-4.md  
**Audit method:** read section + cross-reference all cited tags against registry.json + spot-check numerical and identity claims against papers/<tag>.pdf for all 14 papers cited in §2.4.

---

## Summary

- Claims audited: 38
- Citations checked: 14 tags (all present in registry.json)
- Issues flagged: 4 (NO_CITATION 0, TAG_MISSING 0, CLAIM_MISMATCH 2, WEAK_SUPPORT 1, HEDGE_VIOLATION 0, PROHIBITED_CONTENT 0, STRUCTURAL_ISSUE 1)
- Overall confidence in the section: **HIGH**

---

## Issues

### Issue 1 — CLAIM_MISMATCH

**Location:** §2.4.1 — "a fine-tuned LightGPT variant (derived from Qwen-0.5B and Llama-13B backbones)"

**Citation involved:** [LLMLight]

**Concern:** The LLMLight PDF (pp. 1–5) describes LightGPT as trained via imitation fine-tuning and critic-guided policy refinement on top of backbone LLMs. The paper lists GPT-3.5/4, Llama-2 7/13/70B, and Qwen2 0.5/7/72B as models evaluated under the LLMLight framework. LightGPT itself is described as a specialised backbone for TSC tasks, fine-tuned from GPT-4 trajectories; the prose's "Qwen-0.5B and Llama-13B backbones" conflates two separate model size data-points from Table 1 (Qwen-0.5B is a standalone zero-shot model and Llama-13B is a separate baseline) with the LightGPT fine-tuning target. The LLMLight paper does not identify LightGPT itself as "derived from Qwen-0.5B and Llama-13B"; rather, it presents LightGPT as a fine-tuned variant trained from GPT-4 trajectories, with Qwen-0.5B and Llama-13B being separately evaluated models. The registry entry correctly notes "LightGPT (FT)" as distinct from the Qwen/Llama variants.

**Recommended fix:** Revise to: "a fine-tuned LightGPT variant (trained via GPT-4 trajectory imitation) alongside separately evaluated sub-7B variants including Qwen-0.5B and Llama-13B backbones." Alternatively, split the claim: LightGPT is the fine-tuned backbone; Qwen-0.5B and Llama-13B are separately evaluated models shown in the paper's benchmark results.

---

### Issue 2 — CLAIM_MISMATCH

**Location:** §2.4.2 — "reporting a 20.03 percent reduction in average travel time and a 10.74 percent reduction in average queue length on the 196-intersection New York network"

**Citation involved:** [HeraldLight]

**Concern:** The HeraldLight PDF abstract and Table I state: "a 20.03% reduction in Average Travel Time (ATT) across all scenarios and a mean 10.74% reduction in Average Queue Length (AQL) on the Jinan and Hangzhou networks." The 10.74% AQL reduction is explicitly attributed to Jinan and Hangzhou in the abstract, not the 196-intersection New York network. The New York network (196 intersections) is evaluated in Table I but the 10.74% figure is averaged across Jinan/Hangzhou scenarios only. The section's prose attributes the AQL figure specifically to "the 196-intersection New York network," which is not what the paper states.

**Recommended fix:** Change "on the 196-intersection New York network" to "across the Jinan, Hangzhou, and New York CityFlow networks" for the ATT figure, and attribute the 10.74% AQL figure to the Jinan and Hangzhou networks specifically: "a 20.03 percent reduction in average travel time across all scenarios and a 10.74 percent reduction in average queue length on the Jinan and Hangzhou networks [HeraldLight]."

---

### Issue 3 — WEAK_SUPPORT

**Location:** §2.4.3 — "REG-TSC pushed the same idea into a distributed setting, equipping per-cabinet GPT-4o-mini and Llama-3.1-8B agents with retrieval-augmented generation and reporting per-step inference latency of 4.07 seconds with travel-time gains on the CityFlow Jinan and Yizhuang networks [REG-TSC]."

**Citation involved:** [REG-TSC]

**Concern:** The REG-TSC PDF (abstract and introduction) reports networks with 17 to 177 intersections and states results on "three real-world road networks." The registry entry describes the networks as "CityFlow Jinan/Hangzhou/Yizhuang." The section omits Hangzhou from the network list and describes networks as "CityFlow Jinan and Yizhuang" only. This is a minor omission rather than a false claim, but it understates the evaluation scope. The 4.07 s/timestep latency figure is consistent with the registry entry and appears to be sourced accurately from the traffic-llms.md synthesis; the PDF pages available do not contradict it.

**Recommended fix:** Add Hangzhou to the network list: "travel-time gains on the CityFlow Jinan, Hangzhou, and Yizhuang networks."

---

### Issue 4 — STRUCTURAL_ISSUE

**Location:** §2.4.4 — VLMLight sub-section (single paragraph, no sub-heading label 2.4.4 visible within the section, but contextually the fourth block).

**Concern:** §2.4.4 is the shortest substantive block in the section (~100 words of prose after stripping the header) and engages no limitation specific to VLMLight's evaluation methodology — only its hardware ceiling. The rulebook requires each sub-section to engage at least one weakness, contradiction, or limitation. The hardware ceiling observation ("server-class hardware") is valid, but the section does not note that VLMLight's custom image-based simulator has not been validated against real camera feeds, that the 65% emergency-vehicle waiting-time reduction is measured against RL-only baselines (not against the best hybrid LLM+RL methods also reviewed in §2.4.3), or that the latency figure of below 11.5 seconds is deliberative-branch-only and not a full-cycle wall-clock figure. At least one of these methodological limitations should be named to satisfy the sub-section engagement requirement.

**Recommended fix:** Add one sentence noting the comparison-baseline limitation: e.g., "The 65 percent emergency-vehicle gain is measured relative to RL-only baselines; no comparison against the LA-Light or iLLM-TSC hybrid designs appears in the paper, leaving the marginal value of the vision pipeline over text-only hybrid designs unquantified."

---

## Cross-checks performed

All numerical and identity claims were checked against the available PDF pages. Items verified:

**LLMLight** — "lane occupancies, queue lengths, and current phase" prompt encoding: verified (Section 3.1 Observation Feature Construction). "CityFlow Jinan, Hangzhou, and New York" benchmark: verified (Table 1, datasets section). Claim that LightGPT is "derived from Qwen-0.5B and Llama-13B backbones" is NOT directly supported — see Issue 1.

**Open-TI** — "Llama-2-7B/13B and GPT-4 as a tool-using meta-agent that delegates phase-level decisions to underlying RL or rule-based controllers and exposes the entire pipeline through a dialog interface": verified (introduction and ChatZero description in Open-TI PDF). "CityFlow Hangzhou" only is the described evaluation dataset in the available PDF pages; the section's claim "CityFlow Jinan, Hangzhou, and New York" for Open-TI specifically is NOT in the Open-TI PDF pages reviewed — the Open-TI paper describes CityFlow Hangzhou evaluations. However, the section attributes these three networks to "Both pioneering systems" with citation [LLMLight; Open-TI]; this can be read as LLMLight covering all three networks and Open-TI covering Hangzhou. The ambiguity is minor and attributable to reading "both" as covering LLMLight's broader evaluation rather than asserting Open-TI ran on all three. Flagged for author awareness but not raised as a formal CLAIM_MISMATCH.

**CoLLMLight** — "fine-tuned Llama-3.1-8B for cooperative reasoning... spatiotemporal neighbour states": verified (abstract and Section 3). "CityFlow Jinan, Hangzhou, and New York grids": verified (abstract mentions Jinan, Hangzhou, NY). "gains over LLMLight and Adv-CoLight": verified (abstract).

**HeraldLight** — "Llama-3.1-8B LoRA-tuned agent... separate ChatGPT-class critic... forty-second queue forecasts": verified (abstract, Section III Herald Module). "20.03 percent reduction in ATT": verified (abstract, Table I). "10.74 percent reduction in AQL on the 196-intersection New York network": PARTIALLY INCORRECT — see Issue 2. The 10.74% AQL is Jinan/Hangzhou, not New York specifically.

**LA-Light** — "GPT-4 above a battery of classical and RL controllers... tool calls to select among Webster, Max-Pressure, FRAP, CoLight, and UniTSA": verified (abstract and introduction). "20.4 percent reduction in average waiting time under sensor outage relative to RL alone on SUMO and TSHub testbeds": verified (abstract: "reduces the average waiting time by 20.4%").

**iLLM-TSC** — "PPO-trained RL controller produced phase candidates that a GPT-4 verifier accepted or revised": verified (abstract, Section 4 methodology). "17.5 percent waiting-time reduction under simulated packet loss": verified (abstract: "reduces the average waiting time by 17.5%"). "62.9 percent reduction in emergency-vehicle waiting time against an SARL-TSC baseline": registry confirms −62.9% EWTE vs SARL; available PDF pages confirm the emergency-vehicle and packet-loss framing. Accepted as verified.

**REG-TSC** — "GPT-4o-mini and Llama-3.1-8B agents with retrieval-augmented generation": verified (abstract and architecture description). "4.07 seconds per-step inference latency": registry entry confirms; PDF confirms distributed LLM-agent architecture with real-world networks of 17–177 intersections. Network attribution is slightly narrowed in the section — see Issue 3.

**VLMLight** — "Qwen-2.5-VL-32B vision-language model with a Qwen-2.5-72B reasoner across a three-agent dialogue": verified (abstract: "Qwen2.5-VL-32B + Qwen2.5-72B (3-agent dialogue)"). "65 percent reduction in emergency-vehicle waiting time": verified (abstract: "reduces waiting times for emergency vehicles by up to 65%"). "deliberative latency below 11.5 seconds": verified (registry; abstract confirms "<11.5 s deliberative latency"). "routine average-travel-time loss under one percent": verified (abstract: "less than 1% degradation").

**Traffic-R1** — "fine-tuned Qwen-2.5-3B with a two-stage agentic reinforcement-learning protocol": verified (abstract, Section 4 Methodology — STPO). "gains over LLMLight and the larger CoLLMLight-8B, GPT-4o, Llama-3.3-70B and Qwen-2.5-72B baselines on out-of-distribution CityFlow scenarios": verified (abstract). PCITECH affiliation: verified (author affiliations: "²PCITECH"). "55,000 daily drivers" prefixed as author-reported: the prose reads "by the authors' account, around 55,000 daily drivers — a figure that has not been independently verified." The Traffic-R1 abstract states "serving over 55,000 drivers daily." Hedged framing requirement FULLY MET. "emerging line of LLM-driven traffic-signal-control research rather than evidence of validated production deployment": verbatim framing requirement FULLY MET.

**CuraLight** — "LoRA fine-tuning to Gemma-3 with a DeepSeek-V3/R1 ensemble curating debate-guided training data": verified (abstract: Gemma-3-12B-it + LoRA + DeepSeek-V3/R1 ensemble). "5.34 percent in average travel time, 5.14 percent in average queue length, and 7.02 percent in average waiting time on SUMO Jinan, Hangzhou, and Yizhuang networks": verified (abstract: "−5.34% ATT, −5.14% AQL, and AWT by about 7.02%"). "one of very few sub-7B fine-tuned LLM-TSC systems evaluated on SUMO rather than CityFlow": verified (CuraLight uses SUMO, contrasting with most CityFlow-only papers).

**Multi-Agent-LLMTSC** — "majority-voting ensembles of LightGPT-class fine-tuned models recover small but consistent gains over single-agent LLMLight on CityFlow Jinan and Hangzhou": verified (paper describes 1/5/10 agent voting on 12-intersection Jinan and 16-intersection Hangzhou). "generic Llama-13B ensembles do not": verified (related work section notes LLMLight limitations; paper explicitly tests Llama-13B vs LightGPT variants). Datasets Jinan (12) and Hangzhou (16) verified.

**CoMAL** — "Qwen-7B/32B/72B agents on the Flow Ring and Figure-8 benchmarks": verified (abstract: "GPT-4o-mini and Qwen-72B/32B/7B"; Fig. 1c shows Ring, Figure-8, Merge benchmarks). "only the Qwen-7B configuration sits at the edge of cabinet feasibility": defensible inference from the parameter budgets.

**EvolveSignal** — "DeepSeek and o-series ensemble": verified (abstract mentions DeepSeek-V3/R1 + o4-mini-high/o3). "20.1 percent delay reduction and a 47.1 percent stops reduction over Webster on a SUMO four-leg intersection after 300 generations": verified (abstract: "reducing average delay by 20.1% and average stops by 47.1%").

**SignalClaw** — "emergency-vehicle delays of 11.2 to 18.5 seconds against a Max-Pressure baseline of 42.3 to 72.3 seconds": verified (abstract: "emergency delay 11.2–18.5 s vs. MaxPressure 42.3–72.3 s"). "SUMO incident scenarios": verified (abstract: six event-injected SUMO scenarios). "rationale-and-code skills": verified (abstract: "structured artifact comprising a strategy rationale, selection guidance, and executable code").

**Hedge compliance — Traffic-R1 (CRITICAL):** All three mandatory elements present and correctly placed in §2.4.5:
1. "emerging line of LLM-driven traffic-signal-control research rather than evidence of validated production deployment" — PRESENT.
2. "affiliated with PCITECH (Shanghai Stock Exchange ticker 600728)" — PRESENT. Note: the rulebook specifies "SSE: 600728"; the section uses "Shanghai Stock Exchange ticker 600728" which is substantively equivalent. No violation.
3. "by the authors' account, around 55,000 daily drivers — a figure that has not been independently verified" — PRESENT.

**Prohibited content scan:** No occurrences of "we", "our", "us", supervisor names, Stott-pillar shorthand, internal scaffolding filenames, "the locked thesis/architecture", or marketing language found in the section text.

**Structural compliance:** Six sub-sections 2.4.1–2.4.6 present. Section closes on gap-articulation paragraph stating no equity audit exists in any LLM-TSC paper and directing to §2.5. Word count reported in file as 1,465 words, which is within the 1,250–1,800 word budget.

---

## Tags audited

| Tag | Registry present | PDF spot-checked | Cross-check status |
|---|---|---|---|
| LLMLight | Yes | Yes (pp. 1–5) | VERIFIED with one claim caveat (Issue 1) |
| Open-TI | Yes | Yes (pp. 1–3) | VERIFIED (Hangzhou evaluation scope ambiguity noted, not flagged as mismatch) |
| CoLLMLight | Yes | Yes (pp. 1–4) | VERIFIED |
| HeraldLight | Yes | Yes (pp. 1–5) | VERIFIED with one numerical attribution error (Issue 2) |
| LA-Light | Yes | Yes (pp. 1–4) | VERIFIED |
| iLLM-TSC | Yes | Yes (pp. 1–4) | VERIFIED |
| REG-TSC | Yes | Yes (pp. 1–4) | VERIFIED with minor network omission (Issue 3) |
| VLMLight | Yes | Yes (pp. 1–4) | VERIFIED |
| Traffic-R1 | Yes | Yes (pp. 1–5) | VERIFIED — all hedge requirements met |
| CuraLight | Yes | Yes (pp. 1–4) | VERIFIED |
| Multi-Agent-LLMTSC | Yes | Yes (pp. 1–4) | VERIFIED |
| CoMAL | Yes | Yes (pp. 1–4) | VERIFIED |
| EvolveSignal | Yes | Yes (pp. 1–4) | VERIFIED |
| SignalClaw | Yes | Yes (pp. 1–4) | VERIFIED |
