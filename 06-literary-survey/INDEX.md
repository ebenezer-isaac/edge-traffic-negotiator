# Literary survey — index

147 papers across seven completed deep-research prompts plus one in-flight (Prompt 8 — India context). Registry is locked: do not add, remove, or re-tag papers without a supervisor instruction.

## File map

| File | Theme | Papers | Section C contribution |
|---|---|---|---|
| `priliminary-research.md` | Prompt 1 — CoT faithfulness in sub-7B SLMs and safety-critical control | 25 | Identifies that no published study has tested CoT faithfulness for sub-7B SLMs in safety-adjacent control loops |
| `deterministic-slm.md` | Prompt 2 — Deterministic SLM + classical fallback + tamper-evident ledger across 7 domains | 44 | Ranks Manufacturing, Energy, Swarm robotics highest; recommends two pivots (microgrid swarm, disaster triage) |
| `microsoft-foundry.md` | Prompt 3 — Microsoft commercial intelligence | 5 MSR papers + extensive case-study coverage | Lists Lee Stott's five advocated themes verbatim |
| `robotics.md` | Prompt 4 — LLM/SLM orchestration over deterministic low-level control in multi-agent CPS | 18 | Suggests AcoustoBot + Microsoft Agent Framework pivot |
| `traffic-llms.md` | Prompt 6 — Traffic signal control with LLMs/SLMs | 52 | Identifies the Edge Negotiator novelty tuple — **this is the primary anchor for the locked dissertation** |
| `edge-blockchain.md` | Prompt 7 — Permissioned blockchain & PQC for AI audit | 20 | Identifies the Besu QBFT vs Tessera × ML-DSA gap |
| `PROMPT8.md` | Prompt 8 — India compliance, equity precedent, Bengaluru-corridor anchors | (in flight) | Will produce ≥28 sources covering five themes |
| `registry.json` | Master inventory — short-tag, title, year, URL, source-prompt, category, relevance | 147 (locked) | — |

The seven completed prompts also exist as PDFs in `01-research/prompt-outputs/`. Those PDFs include Prompts 1–7 in their original form; the markdown files in this folder are the verbatim Section A/B/C/D outputs with their registry annotations.

## How to cite

Use the short-tag from `registry.json`. Examples that are verified to exist:

- Traffic SLMs: `Traffic-R1`, `LLMLight`, `CoLLMLight`, `HeraldLight`, `CuraLight`, `LA-Light`, `iLLM-TSC`, `VLMLight`, `REG-TSC`, `Multi-Agent-LLMTSC`, `EvolveSignal`, `SignalClaw`, `Open-TI/ChatZero`, `Masri-Vehicles`, `CoMAL`, `CityLight`
- RL baselines: `MPLight`, `CoLight`, `PressLight`, `FRAP`, `Adv-XLight`, `MA2C-TSC`
- Sims: `CityFlow`, `RESCO`, `Survey-TSC`, `MP-Delay`, `MP-Pedestrian`
- Edge HW: `Edge-Orin-Bench`, `Edge-AGX-Power`, `Edge-First`, `Edge-SLM-Energy`, `Edge-Hailo`, `Edge-Quant`, `Edge-Reason`, `FPGA-Qwen`, `ELIB`
- Safety: `SafeLight`, `CFLight`, `T-REX`, `Adv-DRL-TSC`, `CollusionVeh`
- CoT faithfulness: `CoT-Faith`, `Turpin2023`, `Lanham2023`, `Chen2025`, `Gantt2026`, `Arcuschin2025`, `Han2026`, `Hase2026`, `Siegel2025`, `Masri2026`, `Shakib2026`, `Wang2026`, `Tutek2025`, `Ye2026`, `Young2026`, `Basu2026`, `Guan2024`
- Embodied / control CoT: `Zawalski2024`, `Duan2025`, `Tan2025`, `OneVL2026`, `Liao2025`, `Ye2026_Flood`, `Li2025`, `Xiong2025`, `Puerto2025`
- Blockchain: `Veloso2026`, `Khoshaba2023`, `Ucbas2023`, `Pierro2024`, `Alown2025`, `Zheng2026`, `Alattar2025`, `Catarino2024`, `Fan2025`, `Kulothungan2024`, `Polito2022`, `AITH`, `BC-TSC`, `BC-AI-Decision`, `BC-Enforce`, `SALT-V`, `BeACONS`, `BC-V2X-Sec`, `BC-CCAM`, `BC-Offload`
- Microsoft Research: `Phi4-Reasoning`, `ITS-Complex`, `Interwhen`, `Khan-ICLR`, `AI-Provenance`

If a tag is needed and not in `registry.json`, add it to the registry first; do not invent.

## Cited-claim hygiene

Apply the prompt5 hedged framings whenever you cite Traffic-R1, Google Project Green Light, Alibaba City Brain, Yunex FUSION at TfL, Hyperledger Iroha 2, or NVIDIA Jetson Orin Nano benchmarks. Drop the Southampton/Minima drone claim entirely. See `00-SCOPE-LOCKIN.md` §7.

## Per-paper PDF cache

Cached PDFs live in `06-literary-survey/papers/` named by short-tag. The download script `papers.py` regenerates the cache from `registry.json` URLs. URL lists for individual prompts: `prompt2-urls.txt`, `prompt3-urls.txt`, `prompt6-urls.txt`, `prompt7-urls.txt`.
