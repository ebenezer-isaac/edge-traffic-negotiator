# Literary survey — index

> **Direction note (2026-05-31).** The dissertation has **pivoted**. The single source of truth is now
> [`../03-implementation/PROJECT-DECISION-BRIEF.md`](../03-implementation/PROJECT-DECISION-BRIEF.md), which supersedes the
> equity-audit framing in `00-SCOPE-LOCKIN.md` (supervisor-approved 2026-05-31). The new spine —
> *The Edge Negotiator: Verified-Source Cross-Junction Coordination for SLM-Driven Traffic Signal Control* —
> pairs **authenticated agent identity** (Ed25519/ECDSA signatures + an on-chain permissioned registry with
> `revoke()`) and a **vehicle-conservation plausibility check** for spoof/fault detection with **SLM (Phi-4-mini)
> cross-junction coordination**, all evaluated in SUMO on a real Lambeth corridor. The **equity-audit protocol and
> the CoT-faithfulness probe are dropped as contributions**; the CoT-faithfulness survey is repurposed as the
> *design justification* for terse SLM output.

**175 papers** total: 147 across seven completed deep-research prompts, plus **28 added by Prompt 9** (2026-05-31), of
which **1 (`ssiframe25`) was dropped as redundant**. Prompt 8 (India context) remains in flight. The seven original
prompts **remain valid background** — the traffic-LLM, RL-baseline, blockchain, CoT-faithfulness, and edge-hardware
surveys all still ground the pivoted direction. The Prompt-9 additions are **staged, not yet merged** into the locked
`registry.json` (see "How to cite"). Do not add, remove, or re-tag papers in `registry.json` without a supervisor
instruction.

## File map

| File | Theme | Papers | Role under the pivoted direction |
|---|---|---|---|
| `priliminary-research.md` | Prompt 1 — CoT faithfulness in sub-7B SLMs and safety-critical control | 25 | **Repurposed as the justification for terse SLM output** (no chain-of-thought): explicit CoT traces are post-hoc rationalisations, not faithful causal records, so emitting reasoning adds latency with no trustworthy interpretability benefit. No longer a separate experiment/probe. |
| `deterministic-slm.md` | Prompt 2 — Deterministic SLM + classical fallback + tamper-evident ledger across 7 domains | 44 | Background: grounds the MaxPressure-shield "SLM proposes, deterministic disposes" pattern and the tamper-evident audit log. |
| `microsoft-foundry.md` | Prompt 3 — Microsoft commercial intelligence | 5 MSR papers + case-study coverage | Background: Foundry Local / Phi deployment context for the SLM agents. |
| `robotics.md` | Prompt 4 — LLM/SLM orchestration over deterministic low-level control in multi-agent CPS | 18 | Background: multi-agent CPS orchestration precedent for cross-junction coordination. |
| `traffic-llms.md` | Prompt 6 — Traffic signal control with LLMs/SLMs | 52 | Core traffic-domain background and baseline anchor (Traffic-R1, LLMLight, CoLLMLight, CoLight, MaxPressure, etc.). |
| `edge-blockchain.md` | Prompt 7 — Permissioned blockchain & PQC for AI audit | 20 | Background: grounds the Besu permissioned-ledger registry + audit log (async trust path, never in the control loop). |
| `PROMPT8.md` | Prompt 8 — India compliance, equity precedent, Bengaluru-corridor anchors | (in flight) | Background only; equity precedent de-emphasised after the pivot. |
| `PROMPT9.md` | **Prompt 9 (2026-05-31) — Identity/registry + physical-consistency/spoofing detection** | **28 added (1 dropped)** | **Directly grounds the new integrity layer.** Catalogues the 28 new papers in two pillars (see below). |
| `registry.json` | Master inventory — short-tag, title, year, URL, source-prompt, category, relevance | 147 (locked); Prompt-9 tags staged, not yet merged | — |

The seven completed prompts also exist as PDFs in `01-research/prompt-outputs/` (Prompts 1–7 in their original form). The
markdown files in this folder are the verbatim Section A/B/C/D outputs with their registry annotations.

## Prompt 9 — the two new pillars (see `PROMPT9.md`)

Prompt 9 added **28 papers** (23 auto-downloaded + 5 fetched via UCL; **1, `ssiframe25`, dropped as redundant**), cached in
`papers/` and staged in the URL lists `prompt9-identity-urls.txt` and `prompt9-detection-urls.txt`. `PROMPT9.md` is the
authoritative catalogue of these papers, their short-tags, and their relevance. The two pillars:

1. **Identity / registry** (`prompt9-identity-urls.txt`) — DID/VC, blockchain-PKI, on-chain key registry & revocation.
   Grounds the authenticated-identity layer; note `proofmember23` motivates *stripping* full DID/VC down to a
   signatures-plus-allowlist scheme for the single-domain pilot (DID/VC positioned as future work).
2. **Physical-consistency / spoofing detection** (`prompt9-detection-urls.txt`) — vehicle-conservation checking,
   false-data-injection, and Sybil detection. Grounds the conservation plausibility check.
   **Honest caveat to carry through:** `Xiao2026` shows that a *coordinated, conservation-respecting* attacker can evade
   the consistency check — so the check proves consistency, not truth, and the authentication layer is its complement.

**Integrative novelty (replaces the old equity tuple).** The contribution is the *conjunction*: authenticated identity +
vehicle-conservation plausibility checking + SLM cross-junction coordination. Each piece is individually well-trodden; the
pairing is what is open. There is **no claim of game-theoretic incentive-compatibility** (type-incoherent for frozen LLMs).

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

**Prompt-9 tags (identity + detection) exist in `PROMPT9.md`, NOT yet in `registry.json`.** They include identity tags such
as `slvcdida25`, `endorse25`, `didvcsurvey24`, `proofmember23`, `dpkidrone24`, and detection tags such as
`Xiao2026Residual`, `Amanullah2026CoopMD`, `Derhab2020FlowConserv`, `Azam2022Sybil`, `Obata2023FDIState`,
`Keijzer2021Intersection` (full list and exact tags in `PROMPT9.md`; `ssiframe25` was dropped). **Before citing any
Prompt-9 paper by registry tag, merge it into `registry.json` first** — until then, cite via `PROMPT9.md`. If a tag is
needed and not in `registry.json`, add it to the registry first; do not invent.

## Cited-claim hygiene

Apply the prompt5 hedged framings whenever you cite Traffic-R1, Google Project Green Light, Alibaba City Brain, Yunex
FUSION at TfL, Hyperledger Iroha 2, or NVIDIA Jetson Orin Nano benchmarks. Drop the Southampton/Minima drone claim
entirely. See `00-SCOPE-LOCKIN.md` §7. Additionally, carry the `Xiao2026` evasion caveat (the conservation check proves
consistency, not truth) whenever the spoof/fault-detection contribution is described.

## Per-paper PDF cache

Cached PDFs live in `06-literary-survey/papers/` named by short-tag. The download script `papers.py` regenerates the cache
from `registry.json` URLs. URL lists for individual prompts: `prompt2-urls.txt`, `prompt3-urls.txt`, `prompt6-urls.txt`,
`prompt7-urls.txt`, and the Prompt-9 lists `prompt9-identity-urls.txt` and `prompt9-detection-urls.txt`.
