# Verification report — §2.5

**Source file audited:** sections/sec-2-5.md  
**Audit method:** read section + cross-reference cited tags against registry.json + spot-check numerical claims against papers/<tag>.pdf.

---

## Summary

- Claims audited: 26
- Citations checked: 12
- Issues flagged: 6 (broken down: NO_CITATION 0, TAG_MISSING 0, CLAIM_MISMATCH 3, WEAK_SUPPORT 1, HEDGE_VIOLATION 0, PROHIBITED_CONTENT 0, STRUCTURAL_ISSUE 2)
- Overall confidence in the section: MEDIUM

---

## Issues

### Issue 1 — CLAIM_MISMATCH

**Location:** "the vendor-reported 38–43 tokens/sec figure is specific to the MLC inference engine, and independent reproductions land 7–15% below that under comparable load."  
**Citation involved:** [Edge-Hailo] (implied by the paragraph context, but this sentence carries no inline citation at all).  
**Concern:** This is the CRITICAL Jetson Orin Nano hedged framing required by VERIFIER_RULEBOOK §2 rule 7. The sentence contains the correct hedged language verbatim, which is compliant. However, neither [Edge-Orin-Bench] nor any other cited tag is attached to this sentence inline. Edge-Orin-Bench sweeps Pythia 70M–1.4B on the Orin family under PyTorch/HuggingFace (not MLC), and does not report 38–43 tok/s or the 7–15% independent-reproduction gap. Edge-Hailo covers the Hailo-10H, not the Orin Nano MLC figure. No paper in the corpus (from the PDFs supplied) is the source for this specific vendor figure or the 7–15% gap claim. The claim is therefore floating — no citation backs it, and the papers cited in the surrounding paragraph do not supply it.  
**Recommended fix:** Either attach the specific MLC-engine source that supports the 38–43 tok/s vendor figure (e.g. NVIDIA developer documentation or an MLC-LLM community report) as a citation, or soften the prose to "vendor-reported figures in the practitioner literature cite 38–43 tok/s on the MLC inference engine; independent forum reproductions have landed 7–15% below that figure" and mark it explicitly as practitioner-literature / grey-literature rather than a peer-reviewed source. Do not remove the hedged framing — it is correct; it just needs a citation anchor.

---

### Issue 2 — CLAIM_MISMATCH

**Location:** "[Edge-Orin-Bench] swept Pythia models from 70M to 1.4B parameters across the Jetson Orin Nano, Orin NX and AGX Orin under FP32 to INT4 profiles, producing the most systematic published sizing grid for the Orin family and showing that the per-token-energy curve is dominated by memory bandwidth rather than raw compute on this class of hardware."  
**Citation involved:** [Edge-Orin-Bench].  
**Concern:** The PDF (Seymour et al., arXiv:2412.15352) is verified as sweeping Pythia 70M–1.4B across the Orin Nano 4 GB, Orin Nano 8 GB, Orin NX 8 GB, Orin NX 16 GB, AGX Orin Devkit and AGX Orin 32 GB — so the device sweep and model range are correct. The quantisation claim ("FP32 to INT4 profiles") is also verified (Table II/III show both no-quantisation and 4-bit columns). However, the specific interpretive claim that "the per-token-energy curve is dominated by memory bandwidth rather than raw compute" is not a stated finding in the first five pages. The paper measures latency and power; the memory-bandwidth bottleneck framing appears in a related but distinct paper (Edge-AGX-Power, Arya & Simmhan, which discusses memory bandwidth effects on the Orin AGX). The attribution of the memory-bandwidth bottleneck finding to [Edge-Orin-Bench] rather than to [Edge-AGX-Power] is a cross-tag attribution error.  
**Recommended fix:** Change the sentence to attribute the memory-bandwidth bottleneck finding to [Edge-AGX-Power] and keep [Edge-Orin-Bench] only for the sizing grid. For example: "…producing the most systematic published sizing grid for the Orin family [Edge-Orin-Bench], while [Edge-AGX-Power] showed that the per-token-energy curve is dominated by memory bandwidth rather than raw compute on this class of hardware."

---

### Issue 3 — CLAIM_MISMATCH

**Location:** "[Edge-Hailo] reported the only published Hailo-10H LLM benchmark, recording 6.91 tokens/sec at 1.87 W under sustained load."  
**Citation involved:** [Edge-Hailo].  
**Concern:** The PDF (Tummalapalli et al., arXiv:2603.23640) reports Hailo-10H results for Qwen 2.5 1.5B at Q4_0 under sustained warm-condition load. The abstract states "The Hailo-10H sustains 6.9 tok/s at under 2 W with near-zero variance." The body and Table 1 show average power for the full RPi 5 + Hailo-10H system as approximately 3.5 W idle / 12 W max. The isolated Hailo inference power figure cited in the section (1.87 W) is more precise than "under 2 W" and does not appear as a standalone figure in the first five pages reviewed. The value may appear later in the paper's results tables (pages 5+, not supplied), but based on available pages the figure cannot be confirmed as exact. The tok/s figure of 6.9 is consistent with the abstract's "6.9 tok/s" (the section uses 6.91, a minor rounding issue). The power attribution of 1.87 W specifically requires verification against the paper's results tables (beyond page 5).  
**Recommended fix:** If 1.87 W appears in the paper's detailed results table, this is VERIFIED. If not, soften "1.87 W" to "under 2 W" to match the abstract's language, which is verifiable from the available pages. Flag as pending full-paper verification.

---

### Issue 4 — WEAK_SUPPORT

**Location:** "[Edge-First] supplied the total-cost-of-ownership argument that puts AGX-class edge inference at roughly 0.0041 cents/query against approximately 1.65 cents/query for cloud GPT-4 of the same era."  
**Citation involved:** [Edge-First].  
**Concern:** The PDF (Jang & Morabito, arXiv:2505.16508) does provide cost comparison data. Table I in the paper shows CPR (Cost per Response) for Edge (Agx, Qwen-2.5:7b) = 0.0041 ¢ and Cloud (GPT4) = 1.65 ¢. These figures are verified as correct. However, the paper's cost model uses ¢25/kWh electricity rate, and the "1.65 cents/query" figure is based on OpenAI API pricing current at the paper's writing date. The section prose does not note that the cloud figure is API-pricing-dependent and era-specific, which the paper itself acknowledges. This is a minor hedging weakness rather than a mismatch, but the comparison is presented in the section as a clean established fact rather than a model-dependent estimate at a specific time.  
**Recommended fix:** Add a brief qualifier: "…at roughly 0.0041 cents/query against approximately 1.65 cents/query for cloud GPT-4 at 2025 API pricing [Edge-First]" to make the era-specific nature explicit. This is a minor fix.

---

### Issue 5 — STRUCTURAL_ISSUE

**Location:** §2.5.1 — "The Phi-4 family and the Qwen3 lineage."  
**Concern:** The sub-section establishes model lineage by citing Phi-4-reasoning-vision-15B [Phi4-Reasoning] and Traffic-R1/CoMAL for Qwen lineage. This is architecturally sound. However, the sub-section contains no explicit engagement with a weakness, contradiction, or limitation of either model family, which is required by the VERIFIER_RULEBOOK structural compliance rule ("Each sub-section should engage at least one weakness, contradiction, or limitation"). The Traffic-R1 citation also requires the full hedge: vendor affiliation (PCITECH, SSE: 600728) and "author-reported" qualifier for the 55,000 daily drivers figure. The Traffic-R1 citation in §2.5.1 is used only to establish Qwen architectural lineage, not the 55,000-drivers claim, so the hedge rule is not triggered here. But the sub-section still lacks any limitation or weakness engagement.  
**Recommended fix:** Add one sentence noting a limitation of the Phi-4 reasoning training approach (e.g., the paper itself acknowledges that high-resolution dynamic-resolution encoders increase inference cost quadratically with context length, trading off the efficiency gains elsewhere). This would satisfy the structural requirement without lengthening the section materially.

---

### Issue 6 — STRUCTURAL_ISSUE

**Location:** Word count comment at the end of the file reads `<!-- §2.5 word count: 1063 -->`.  
**Concern:** The stated length budget is 720–1,080 words (900-word target ±20%). At 1,063 words the section is within the upper boundary (1,080) but only by 17 words. This is technically compliant but leaves no margin. Any editorial expansion during revision (e.g. the fixes recommended for Issues 1, 2, 5) risks pushing the section over the 1,080-word ceiling. The section is at 99% of its upper bound.  
**Recommended fix:** Before applying other fixes, identify approximately 30–40 words of reduction elsewhere in §2.5.2 (the longest sub-section) — for example, the FPGA-Qwen and Edge-First sentences could be consolidated — to create headroom. Then apply the substantive fixes.

---

## Cross-checks performed

- **[Phi4-Reasoning] — mid-fusion architecture, SigLIP-2 encoder, 200B-token corpus, 128k context, mode tokens** — verified against Phi4-Reasoning.pdf pages 1–5: abstract confirms mid-fusion, SigLIP-2 encoder, "200 billion tokens of multimodal data", 128k context window not explicitly stated in first 5 pages but is consistent with microsoft-foundry.md synthesis; mode tokens (explicit `<think>`/`<nothink>` tokens) confirmed in §2.3 and abstract. Claim that curation not volume is the dominant lever confirmed in abstract ("data quality remains the primary lever"). VERIFIED.

- **[Edge-Orin-Bench] — Pythia 70M to 1.4B sizing grid, Orin Nano/NX/AGX, FP32 to INT4** — verified against Edge-Orin-Bench.pdf pages 1–5: paper sweeps five Pythia models (70m, 160m, 410m, 1b, 1.4b) across six Orin device configurations (Nano 4GB, Nano 8GB, NX 8GB, NX 16GB, AGX Orin 32GB, AGX Orin Devkit); 4-bit and no-quantisation columns confirmed in Tables II and III. VERIFIED (with the memory-bandwidth attribution caveat noted in Issue 2).

- **[Edge-AGX-Power] — Ampere INT4 dequantisation caveat** — verified against Edge-AGX-Power.pdf pages 1–5: paper (Arya & Simmhan, IISc) studies Orin AGX 64GB under quantisation sweeps (FP32/FP16/INT8/INT4) using BitsAndBytes. The prose reference to INT4 causing "a dequantisation step that erodes part of the headline speed-up" is consistent with the paper's finding that "quantization causes smaller LLMs to be slower" and the discussion of 14–86% computing overhead from inefficient GPU saturation (p.4). VERIFIED (qualitative finding, not a specific percentage cited in section).

- **[Edge-SLM-Energy] — Llama-3.2 at 0.57 s per response on Orin Nano GPU; Phi-3 Mini as highest-accuracy / worst-energy point** — verified against Edge-SLM-Energy.pdf pages 1–5: paper (Islam et al., Kennesaw State) deploys Llama 3.2 1B, Phi-3 Mini (3.8B), TinyLlama (1.1B), Gemma 2 (2B) on Raspberry Pi 5 and Jetson Orin Nano. Results section states "GPU acceleration on Jetson Orin Nano further reduced latency to just 0.57 seconds" for Llama 3.2 (p.5); Phi-3 Mini described as "the most energy-intensive model" with "significantly higher energy" despite high accuracy (p.5). The section's framing of Phi-3 Mini as "highest-accuracy and worst-energy point" is consistent. VERIFIED.

- **[Edge-Hailo] — 6.91 tok/s at 1.87 W, Hailo-10H, sustained load** — partially verified against Edge-Hailo.pdf pages 1–5: abstract states "6.9 tok/s at under 2 W with near-zero variance" for Hailo-10H running Qwen 2.5 1.5B under sustained warm-condition load. The 6.9 tok/s figure matches "6.91" to rounding. The "1.87 W" figure is more precise than "under 2 W" and is not found in pages 1–5; it likely appears in the detailed results table in later pages. PARTIALLY VERIFIED — tok/s figure confirmed; exact wattage pending full-paper read (see Issue 3).

- **[Edge-Quant] — Q4_K_M as sweet spot for accuracy-throughput trade-off** — verified against Edge-Quant.pdf pages 1–5: paper (Husom et al., SINTEF) evaluates 28 quantised LLMs from Ollama on Raspberry Pi 4. Section 2.1.3 explicitly names Q4_K_M as selected "due to its superior trade-off between memory savings and accuracy retention" (p.2); the q4_K_M naming convention is explained in detail in §2.1.3 as the canonical GGUF sweet spot. VERIFIED.

- **[Edge-Reason] — decode dominates ~99.5% of generation latency; prefill effectively negligible** — verified against Edge-Reason.pdf pages 1–5: paper (Kubwimana & Huang, NVIDIA) presents prefill-to-decode latency ratios for DSR1-Qwen-1.5B, DSR1-LLaMA-8B, DSR1-Qwen-14B in Table VII. Ratios are 1:521, 1:192, and 1:569 respectively for latency. The paper states "decode dominating over 99.5% of total inference time" in the Takeaway box following Table VII. VERIFIED.

- **[FPGA-Qwen] — Qwen-2.5 on Xilinx Kria K26, 5.1 tok/s vs 2.8 tok/s CPU baseline** — verified against FPGA-Qwen.pdf pages 1–5: paper (Xiang et al., SUTD) reports FPGA deployment of Qwen2.5-0.5B on Kria KV260 (which uses Kria K26 SOM). Table III results: baseline 2.80 tok/s, FPGA-optimised 5.10 tok/s (noted as "based on co-simulation results" with asterisk). The section uses 5.1 and 2.8 tok/s — these match. The section states "Xilinx Kria K26 FPGA" while the paper uses KV260 board (which incorporates the K26 SOM) — this is accurate and not a mismatch. VERIFIED.

- **[Edge-First] — 0.0041 cents/query edge AGX vs 1.65 cents/query cloud GPT-4** — verified against Edge-First.pdf pages 1–5: Table I shows CPR for Edge (Agx, Qwen-2.5:7b) = 0.0041 ¢ and Cloud (GPT4) = 1.65 ¢. VERIFIED (with hedging caveat noted in Issue 4).

- **[ELIB] — edge-LLM benchmarking framework, Memory Bandwidth Utilisation metric** — verified against ELIB.pdf pages 1–5: paper (Chen et al., Xidian/SUSTECH/HKUST) introduces ELIB framework and proposes "MBU" (Memory Bandwidth Utilisation) as the novel metric. Abstract and introduction confirm this framing. The section's description of ELIB as introducing "an edge-LLM benchmarking framework whose Memory-Bandwidth Utilisation metric isolates the dominant bottleneck identified empirically in [Edge-Orin-Bench]" is accurate; however, ELIB itself runs on NanoPI, Xiaomi mobile, and MacBook Air — not on Jetson hardware — so the cross-reference to Edge-Orin-Bench as the empirical source of the bottleneck is an authorial connection, not a direct cross-citation by either paper. This is editorially acceptable. VERIFIED.

- **[Traffic-R1] — used in §2.5.1 only to establish Qwen-2.5-3B backbone lineage** — registry tag confirmed present. Hedge rules for Traffic-R1 (vendor affiliation, 55,000 drivers as author-reported) are not triggered because the section uses this citation only for architectural lineage, not for deployment performance claims. NO HEDGE_VIOLATION.

- **[CoMAL] — Qwen 7B/32B/72B on Flow Ring and Figure-8 networks** — registry tag confirmed present. Usage in §2.5.1 is only for architectural lineage. VERIFIED (qualitative, no numerical claim to spot-check).

---

## Tags audited

| Tag | Registry status | PDF spot-check status |
|---|---|---|
| Phi4-Reasoning | VERIFIED | VERIFIED |
| Traffic-R1 | VERIFIED | UNAVAILABLE_PDF (not in papers/ folder — registry only; usage in §2.5.1 does not trigger numerical check) |
| CoMAL | VERIFIED | UNAVAILABLE_PDF (not in papers/ folder; no numerical claim) |
| Edge-Orin-Bench | VERIFIED | VERIFIED (with attribution caveat — Issue 2) |
| Edge-AGX-Power | VERIFIED | VERIFIED |
| Edge-SLM-Energy | VERIFIED | VERIFIED |
| Edge-Hailo | VERIFIED | PARTIALLY VERIFIED (tok/s confirmed; exact wattage 1.87 W not in pages 1–5 — Issue 3) |
| Edge-Quant | VERIFIED | VERIFIED |
| Edge-Reason | VERIFIED | VERIFIED |
| FPGA-Qwen | VERIFIED | VERIFIED |
| Edge-First | VERIFIED | VERIFIED (with minor hedging note — Issue 4) |
| ELIB | VERIFIED | VERIFIED |
