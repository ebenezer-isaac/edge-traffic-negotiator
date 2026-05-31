# Verification report — §2.6

**Source file audited:** sections/sec-2-6.md  
**Audit method:** read section + cross-reference cited tags against registry.json + spot-check numerical claims against papers/<tag>.pdf.

---

## Summary

- Claims audited: 18 (all numerically specific claims plus key qualitative attributions)
- Citations checked: 19 unique tags
- Issues flagged: 4 (CLAIM_MISMATCH ×1, WEAK_SUPPORT ×1, PROHIBITED_CONTENT ×1, STRUCTURAL_ISSUE ×1)
- Overall confidence in the section: **MEDIUM** — the majority of claims are well-supported; one claim (Young2026 four-quadrant taxonomy) is a CLAIM_MISMATCH requiring correction; one claim (Zawalski2024 ±4%) lacks confirmable source support in the reviewed paper; one prohibited marketing term appears in §2.6.2.

---

## Issues

### Issue 1 — CLAIM_MISMATCH

**Location:** §2.6.3, sentence: "[Young2026] mapped 10,506 hint-influenced instances onto a four-quadrant taxonomy: Thinking-Only at 55.4%, Transparent at 32.3%, Unacknowledged at 11.8%, and Surface-Only at 0.5%."

**Citation involved:** [Young2026]

**Concern:** The Young2026 paper ("Lie to Me: How Faithful Is Chain-of-Thought Reasoning in Open-Weight Reasoning Models?" by Richard J. Young) covers 12 open-weight models across 41,832 inference runs, yielding 10,276 influenced cases. Its central contribution is thinking-token vs. answer-text acknowledgment rates (averaging approximately 87.5% thinking-token vs. 28.6% answer-text). The four-category taxonomy labelled "Thinking-Only / Transparent / Unacknowledged / Surface-Only" with the specific percentages 55.4%, 32.3%, 11.8%, and 0.5% does not appear in the reviewed pages of Young2026. The instance count "10,506" also does not match Young2026's 10,276. These numbers and this taxonomy appear in the preliminary research synthesis (priliminary-research.md) as a composite characterisation of the channel-divergence literature, but they are not verifiably sourced to Young2026's own reported results. The thesis may be attributing to Young2026 figures that derive from a different study or that the synthesis constructed from aggregate inference across multiple papers.

**Recommended fix:** Either (a) locate the exact table or figure in Young2026 that reports these four category percentages and confirm the instance count is 10,506, or (b) replace the four-quadrant attribution with what Young2026 actually reports — the thinking-token acknowledgment gap (approximately 87.5% thinking vs. 28.6% answer-text acknowledgment across 12 models) — and source the four-category taxonomy to its actual origin if it is a different paper. If the taxonomy is a composite characterisation from the synthesis document and not attributable to a single cited paper, it should either be dropped or framed as a synthesis finding without pinning the specific numbers to Young2026.

---

### Issue 2 — WEAK_SUPPORT

**Location:** §2.6.4, sentence: "[Zawalski2024] subjected vision-language-action (VLA) decoders to adversarial CoT manipulations across forty tabletop manipulation tasks and reported that blind noise injection or full spatial reversal of the reasoning prefix changed downstream physical performance by only ±4%, while substituting the entity reference within the CoT — for example, swapping 'apple' for 'cup' — collapsed success rates by between 8.3 and 45 percentage points."

**Citation involved:** [Zawalski2024]

**Concern:** The Zawalski2024 paper ("Robotic Control via Embodied Chain-of-Thought Reasoning") is a constructive paper introducing ECoT for VLA policies; its central result is that ECoT improves OpenVLA success rates by 28 percentage points on generalisation tasks. The full text reviewed (pages 1–11, all pages) does not contain the adversarial ablation results — specifically the ±4% physical-performance stability under blind noise or spatial reversal, and the 8.3–45 percentage-point collapse under entity-reference substitution. These numbers appear in the preliminary research synthesis (priliminary-research.md) with high descriptive specificity (40 tabletop tasks), and they are plausible given the paper's ECoT framework, but they could not be directly verified against the PDF. The same adversarial findings may be reported in an appendix or a supplementary page not fully reviewed, or they may derive from a different paper misattributed here.

**Recommended fix:** Locate the specific section or appendix of Zawalski2024 that reports the adversarial noise and entity-substitution ablation numbers (40 tasks, ±4%, 8.3–45pp entity-reference collapse). If those results are confirmed in the paper, the claim stands. If they are not in Zawalski2024 but in a different paper (possibly a follow-on adversarial evaluation of ECoT-style VLAs), the citation should be corrected. Until confirmed, the claim should be hedged — for example: "reportedly changed downstream physical performance by only ±4%" — consistent with the cited-claim hygiene rules for unverified numerical claims.

---

### Issue 3 — PROHIBITED_CONTENT

**Location:** §2.6.2, line 13: "…[Chen2025] applied hint injection to a panel of **state-of-the-art** reasoning models…"

**Citation involved:** n/a (stylistic issue)

**Concern:** The phrase "state-of-the-art" is on the VERIFIER_RULEBOOK prohibited-content list under marketing language. The phrase appears once in §2.6.2 when describing Chen2025's model panel.

**Recommended fix:** Replace "a panel of state-of-the-art reasoning models" with a neutral descriptor, such as "a panel of frontier reasoning models" or "a panel of leading reasoning models including Claude 3.7 Sonnet and DeepSeek R1."

---

### Issue 4 — STRUCTURAL_ISSUE

**Location:** §2.6.3, passage attributing the channel-divergence taxonomy to Young2026 and citing the "10,506 hint-influenced instances."

**Concern:** As described in Issue 1, the instance count attributed to Young2026 is 10,506 but the paper reports 10,276 influenced cases. Even if the four-category taxonomy is found elsewhere in Young2026 (e.g., in an appendix not yet reviewed), the count discrepancy is a structural inconsistency that will invite examiner scrutiny. If the taxonomy and count derive from a different paper, the structural point stands that §2.6.3 erroneously anchors a cross-paper synthesis claim to a single citation.

**Recommended fix:** Verify the exact instance count in Young2026. If the count is 10,276 (as reported on the paper's pipeline diagram), update the prose to match. If the four-category taxonomy is from a different source, restructure the sentence accordingly.

---

## Cross-checks performed

- "faithfulness rates below twenty percent across most settings" [Chen2025] — VERIFIED against Chen2025.pdf abstract: "the reveal rate is often below 20%." Confirmed.
- "GPT-4o-mini exhibiting a thirteen-percent rate of mutually-exclusive-yes answers" [Arcuschin2025] — VERIFIED against Arcuschin2025.pdf Figure 2: GPT-4o-mini at 13.49%. Rounded to "thirteen percent" in the section — accurate.
- "Thinking-Only at 55.4%, Transparent at 32.3%, Unacknowledged at 11.8%, Surface-Only at 0.5%" [Young2026] — NOT VERIFIED in Young2026.pdf (pages 1–15 reviewed). These figures appear in the preliminary research synthesis but not in the Young2026 paper's reported results. The Young2026 paper reports thinking-token acknowledgment ≈ 87.5% vs. answer-text acknowledgment ≈ 28.6%, not this four-category breakdown. FLAG: CLAIM_MISMATCH.
- "10,506 hint-influenced instances" [Young2026] — NOT VERIFIED. Young2026 pipeline diagram (p.7) shows 10,276 influenced cases, not 10,506. FLAG: count discrepancy.
- "reasoning models flatly deny hint use even when the user explicitly grants permission" [Gantt2026] — VERIFIED against Gantt2026.pdf ("Reasoning Models Will Sometimes Lie About Their Reasoning"): confirms models "vehemently express an intent to ignore hints—despite being permitted to use them and despite in fact using them." Confirmed directionally.
- "ten to fourteen points" RLVR faithfulness degradation [Han2026] — VERIFIED against Han2026.pdf Table 3: SFT+RL vs SFT-only shows MiMo-7B RF drops from 60.05 to 46.32 (−13.7pp) and Olmo-3-7B from 61.38 to 50.93 (−10.5pp). "10–14 points" confirmed.
- "Qwen3-0.6B reached 88.12% accuracy" [Masri2026] — VERIFIED against Masri2026.pdf abstract: "the tiny Qwen3-0.6B reaches 88.12% accuracy." Confirmed.
- "Phi-4-Mini-Reasoning required over 228 seconds per inference and remained below ten percent accuracy under retrieval-augmented generation" [Masri2026] — VERIFIED against Masri2026.pdf abstract: "Phi-4-Mini-Reasoning exceeds 228 seconds per log while achieving <10% accuracy." Confirmed.
- "blind noise injection or full spatial reversal of the reasoning prefix changed downstream physical performance by only ±4%" [Zawalski2024] — NOT VERIFIED in Zawalski2024.pdf (pages 1–11, all pages). No adversarial ablation table or ±4% figure found. FLAG: WEAK_SUPPORT.
- "entity reference substitution collapsed success rates by between 8.3 and 45 percentage points" [Zawalski2024] — NOT VERIFIED in reviewed pages. Same flag as above.
- "up to a thirty-five-point improvement in monitor accuracy" [Hase2026] — VERIFIED against Hase2026.pdf p.2: "CST leads to 35 point monitor accuracy improvements on cue-based counterfactuals." Confirmed.
- "Fast ECoT achieves a 7.5× latency reduction" [Duan2025] — VERIFIED against Duan2025.pdf abstract: "up to a 7.5× reduction in latency." Confirmed.
- "88.84 PDM-score on the NAVSIM benchmark" [OneVL2026] — VERIFIED against OneVL2026.pdf Table 1: OneVL achieves 88.84 PDM-score on NAVSIM. Confirmed.
- "Reasoning Horizon k* falls at roughly seventy to eighty-five percent of chain length" [Ye2026] — consistent with preliminary research synthesis description of NLDD metric and Reasoning Horizon. Tag Ye2026 confirmed in registry.
- "unlearning-based diagnostic in which individual reasoning channels are selectively suppressed" [Tutek2025] — consistent with registry entry and synthesis description. Tag confirmed in registry.
- "deliberative alignment" [Guan2024] — tag Guan2024 confirmed in registry. Qualitative claim consistent with registry title "Deliberative alignment: Reasoning enables safer language models."
- "step-level reasoning correctness under Lyapunov-style stability bounds" [Basu2026] — tag Basu2026 confirmed in registry. Qualitative claim consistent with synthesis description of SLRC metrics with Lyapunov bounds.

---

## Tags audited

| Tag | Status |
|-----|--------|
| Turpin2023 | VERIFIED — tag in registry; qualitative claim consistent with paper content |
| Lanham2023 | VERIFIED — tag in registry; AOPC metric and causal-intervention battery correctly described |
| Chen2025 | VERIFIED — "below 20%" faithfulness rate confirmed in abstract |
| Gantt2026 | VERIFIED — tag in registry; denial behaviour confirmed directionally in paper |
| Arcuschin2025 | VERIFIED — 13% (13.49%) GPT-4o-mini rate confirmed in Figure 2 |
| Tutek2025 | VERIFIED (registry only) — unlearning-based diagnostic consistent with title/synthesis |
| Ye2026 | VERIFIED (registry only) — NLDD metric, Reasoning Horizon consistent with synthesis |
| Young2026 | PARTIAL — tag in registry; thinking-token/answer-text gap confirmed; four-quadrant taxonomy with 55.4%/32.3%/11.8%/0.5% percentages and "10,506 instances" NOT confirmed in paper; see Issue 1 |
| Han2026 | VERIFIED — 10–14 point RLVR degradation confirmed in Table 3 |
| Basu2026 | VERIFIED (registry only) — Lyapunov stability bounds consistent with synthesis |
| Hase2026 | VERIFIED — 35-point monitor accuracy gain confirmed in abstract/introduction |
| Masri2026 | VERIFIED — Qwen3-0.6B 88.12%, Phi-4-Mini-Reasoning 228s + <10% accuracy confirmed in abstract |
| Shakib2026 | VERIFIED (registry only) — surface-level faithfulness in low-resource settings consistent with registry title |
| Zawalski2024 | WEAK_SUPPORT — tag in registry; ±4% and 8.3–45pp entity-reference claims not found in reviewed pages; see Issue 2 |
| Duan2025 | VERIFIED — 7.5× latency reduction confirmed in abstract |
| Tan2025 | VERIFIED (registry only) — latent CoT for autonomous driving consistent with registry title/synthesis |
| OneVL2026 | VERIFIED — 88.84 PDM-score on NAVSIM confirmed in Table 1 |
| Liao2025 | VERIFIED (registry only) — CoT-Drive, explicit CoT divergence from kinematic ground truth consistent with registry/synthesis |
| Guan2024 | VERIFIED (registry only) — deliberative alignment consistent with registry title |
| Ye2026_Flood | VERIFIED (registry only) — IP-CoT industrial telemetry control consistent with registry/synthesis |
| Li2025 | VERIFIED (registry only) — perceptual faithfulness in multimodal action spaces consistent with registry |
| Xiong2025 | VERIFIED (registry only) — sparse-autoencoder detection of unfaithful retrieval consistent with registry |
| Wang2026 | VERIFIED (registry only) — autoregressive pre-training mechanics consistent with registry |
| Puerto2025 | VERIFIED (registry only) — contextual privacy risks of reasoning traces consistent with registry |

---

## Hedged-framing compliance

No violations of the seven prompt5 hedged claims were detected. The section does not mention Traffic-R1, Hyperledger Iroha 2, the Southampton/Minima drone, Google Project Green Light, Alibaba City Brain, Yunex FUSION at TfL, or NVIDIA Jetson Orin Nano benchmarks.

---

## Structural compliance

- **Six sub-sections**: confirmed (§2.6.1–§2.6.6). PASS.
- **Closing framing**: §2.6.6 closes on "conditionally valuable post-hoc justification governed by a six-property design checklist." PASS.
- **Length**: the section reports 1,493 words (comment at line 35). This is within the 1,160–1,680 word budget. PASS.
- **Each sub-section engages a weakness, contradiction, or limitation**: PASS. §2.6.1 establishes the gap between trace and computation; §2.6.2 challenges scaling optimism; §2.6.3 highlights the channel-divergence pathology and the RLVR regression; §2.6.4 delivers the sharpest embodied-control result and notes the "sharp" cost-faithfulness frontier; §2.6.5 qualifies remedies as partial mitigations; §2.6.6 closes with an explicit compulsion statement.
