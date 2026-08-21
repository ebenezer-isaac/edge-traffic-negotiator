# Reference papers (local copies, downloaded 2026-08-08; 39 PDFs + RFC txt, all arXiv IDs verified against abstract pages)

## Batch 2 additions (2026-08-08 afternoon)
- **Classic RL TSC lineage:** `colight-1905.05717`, `frap-1905.04722`, `attendlight-2010.05772`, `survey-tsc-methods-1904.08117` (Wei/Zheng survey covers PressLight + MPLight, which have NO arXiv preprints — cite via proceedings).
- **Backpressure theory (arXiv-available substitutes for paywalled Varaiya 2013):** `backpressure-capacity-aware-1309.6484` (Gregoire/Wongpiromsarn), `backpressure-unknown-routing-1401.3357` (local-measurement stability — parallels our sensing-only shield).
- **SLM / on-device:** `survey-slm-2410.20011`, `on-device-llm-review-2409.00088`, `phi-3-report-2404.14219`, `phi-4-report-2412.08905`, `qwen2.5-report-2412.15115`, `qwen3-report-2505.09388`.
- **Distillation:** `survey-kd-llms-2402.13116`, `orca-2306.02707` (explanation-trace distillation from GPT-4 — direct precedent), `self-instruct-2212.10560`, `agentinstruct-2407.03502`.
- **Quantization:** `gptq-2210.17323`, `awq-2306.00978`, `quant-eval-2507.17417`, `quant-lora-balance-2407.17029` (quantization×LoRA degradation — directly our int4-after-QLoRA risk).
- **Positioning surveys:** `llm4drive-survey-2311.01043`, `llm-ad-survey-2409.14165`.
- **Shield architecture theory:** `rl-shielding-1708.08611` (canonical shielding formalism), `action-masking-2006.14171`, `neurosymbolic-masking-2602.10598`.
- `ct-rfc6962.txt` — canonical RFC text (PDF mirror unavailable).

## TSC × LLM prior art (position the fine-tune axis against these)
- `llmlight-lightgpt-2312.16044.pdf` — LLMLight/LightGPT, KDD 2025. THE closest prior work: GPT-4-distilled LoRA fine-tunes for TSC down to 0.5B (Qwen2), MIT checkpoints on HF. CityFlow, Jinan/Hangzhou. Our recipe is theirs with a deterministic verifier replacing the RL critic, on SUMO + real London + on-device serving.
- `traffic-r1-2508.02344.pdf` — Traffic-R1, ACL 2026. Qwen2.5-3B, R1-style RL fine-tune, claims real deployment. Apache-2.0 checkpoint.
- `dglight-2604.25259.pdf` — DGLight 2026. Llama3-8B + GRPO. Key calibration table: entire LLM-vs-MaxPressure gap ≈ 1-2%.
- `collmlight-2503.11739.pdf` — CoLLMLight, ICLR 2026 poster. Cooperative network-wide LLM agents (our coordination-format cousin).
- `curalight-2604.05663.pdf` — CuraLight 2026. Debate-curated LoRA distillation; the one fine-tuning TSC paper on SUMO.
- `illm-tsc-2407.06025.pdf` — iLLM-TSC 2024. RL proposes, cloud LLM vetoes — the inverted mirror of our hybrid shield.
- `lats-distill-2603.24361.pdf` — LATS 2026. LLM→MARL latent distillation; the only other "distill into a small deployed model" TSC work.
- `evolvesignal-2509.03335.pdf` — EvolveSignal (switching-hysteresis evidence used in our delay-aware prompt design).
- `collusion-tsc-2111.02845.pdf` / `nonrepudiation-tsc-1906.02628.pdf` — H2 trust-layer positioning cites.

## Fine-tuning methodology
- `lora-2106.09685.pdf` — LoRA (Hu et al. 2021).
- `qlora-2305.14314.pdf` — QLoRA (Dettmers et al. 2023) — our training method.
- `forgetting-scaling-2401.05605.pdf` — catastrophic-forgetting scaling laws (limitations section).

## H2 / audit
- `ct-rfc6962.pdf` — Certificate Transparency RFC 6962 (the conceded mechanism basis).
- `dahl-legal-hallucination-2401.01301.pdf` — Dahl et al. 2024, legal citation hallucination (Job-A framing).

## Known gaps (paywalled — fetch via UCL library login)
- Varaiya 2013, "Max pressure control of a network of signalized intersections," Transportation Research Part C — THE baseline cite; UCL has TRC access.
- CONIKS / PeerReview / TrInc etc. (mostly free on USENIX/author pages if needed for H2 depth).
