# Literary survey — index

> **Direction note (2026-07-21, supersedes the 2026-05-31 note below).** The dissertation has **pivoted again**.
> The single source of truth is now
> [`../specs/001-edge-negotiator/MASTER-SPEC.md`](../specs/001-edge-negotiator/MASTER-SPEC.md) (the
> `PROJECT-DECISION-BRIEF.md` this note used to point to has been deleted; do not cite it). The frozen thesis —
> *an on-device, trust-preserving coordination layer for signalised junctions, plus a measured characterisation of
> exactly which stealthy insider deviations it can and cannot hold accountable* — has three contributions: **(a)** a
> deterministic real-time gate that refuses signed-but-uncorroborated emergency preemption from a compromised
> insider and clears physically-corroborated real emergencies; **(b)** a **Certificate-Transparency-style,
> quorum-anchored, cross-audited, signature-verified accountability log** (mechanism credited to prior art —
> RFC 6962, CONIKS, A2M, TrInc, PeerReview, Küsters — cited, NOT claimed novel); and **(c)** the novel object, a
> **self-referential coupling** — the preemption attack controls the signal phase, which is also the variable that
> gates honest-witness coverage, so executing the attack opens the very coverage desert that conceals it, stated as
> a conditional lemma and measured on the real **Euston Road (A501)** corridor (the synthetic 2×2 grid is a
> unit-test fixture only; Lambeth/Southwark/Brixton/Elephant & Castle/A23/A3 are dropped). A frozen on-device
> **Phi-4-mini** SLM (the only model; Qwen3-4B is dropped) is the mandatory, self-contained co-equal contribution
> (citation-faithful legal-reasoning note + disambiguation + frozen-vs-hardened tradeoff) — it is NOT the instrument
> of the boundary map. The **equity-audit framing** (Gini/Rawlsian/Disparate Impact/ATRS-as-an-equity-metric)
> **and the CoT-faithfulness probe are dropped as contributions** (equity/fairness auditing is not part of the
> current thesis). What is **retained, reframed** is the UK legal-accountability treatment and the India
> **comparative-accountability lens** (lit-review §2.8.2/§2.8.3): ATRS survives only as a transparency-and-logging
> standard, and India only as a comparative accountability lens — not as equity metrics. The CoT-faithfulness
> literature is retained only as background for why the SLM's internal reasoning note is validated against cited
> statute and never trusted, not as a standalone experiment.

**175 papers** total: 147 across seven completed deep-research prompts, plus **28 added by Prompt 9** (2026-05-31), of
which **1 (`ssiframe25`) was dropped as redundant**. Prompt 8 (India context) is superseded — see its file for the
current status. The seven original prompts **remain valid background** for the parts that do not conflict with the
current thesis — the traffic-LLM, RL-baseline, cited-DLT-benchmark, CoT-faithfulness, and edge-hardware surveys still
ground the pivoted direction; the equity-audit and India-regulatory-comparison content within them does not. The
Prompt-9 additions are **staged, not yet merged** into the locked `registry.json` (see "How to cite"). Do not add,
remove, or re-tag papers in `registry.json` without a supervisor instruction.

## File map

| File | Theme | Papers | Role under the pivoted direction |
|---|---|---|---|
| `priliminary-research.md` | Prompt 1 — CoT faithfulness in sub-7B SLMs and safety-critical control | 25 | Background: motivates why the SLM's internal, non-evidential, counsel-gated reasoning note is validated against cited statute and never trusted as a machine verdict — not a standalone CoT-faithfulness experiment/probe. |
| `deterministic-slm.md` | Prompt 2 — Deterministic SLM + classical fallback + tamper-evident ledger across 7 domains | 44 | Background: grounds the "SLM proposes, deterministic MaxPressure shield disposes" pattern and the tamper-evident audit log. |
| `microsoft-foundry.md` | Prompt 3 — Microsoft commercial intelligence | 5 MSR papers + case-study coverage | Background: Foundry Local / Phi-4-mini deployment context for the frozen on-device SLM. |
| `robotics.md` | Prompt 4 — LLM/SLM orchestration over deterministic low-level control in multi-agent CPS | 18 | Background: multi-agent CPS orchestration precedent for the deterministic-shield-validates-every-SLM-decision pattern. |
| `traffic-llms.md` | Prompt 6 — Traffic signal control with LLMs/SLMs | 52 | Core traffic-domain background and baseline anchor (Traffic-R1, LLMLight, CoLLMLight, CoLight, MaxPressure, etc.); confront Traffic-R1 on the accountability role + measured coupling, not on coordination performance. |
| `edge-blockchain.md` | Prompt 7 — Permissioned blockchain & PQC for AI audit | 20 | Background only: the cited Besu/QBFT/Tessera/GoQuorum benchmarks are prior-art anchor OPTIONS for the CT-style quorum witness set, not the core mechanism — the accountability layer's mechanism is conceded to Certificate-Transparency-style prior art (RFC 6962 et al), never foregrounded as a blockchain contribution. |
| `PROMPT8.md` | Prompt 8 — India compliance, equity precedent, Bengaluru-corridor anchors | (superseded) | **Archived.** Written for the dropped Quarterly Equity Audit Protocol; equity/fairness auditing and the Indian-regulatory-comparison chapter are not part of the current thesis. Retained for its underlying Indian-law citations only. |
| `PROMPT9.md` | **Prompt 9 (2026-05-31) — Identity/registry + physical-consistency/spoofing detection** | **28 added (1 dropped)** | **Directly grounds the identity root / registry + corroboration layer.** Catalogues the 28 new papers in two pillars (see below). |
| `registry.json` | Master inventory — short-tag, title, year, URL, source-prompt, category, relevance | 147 (locked); Prompt-9 tags staged, not yet merged | — |

The seven completed prompts also exist as PDFs in `01-research/prompt-outputs/` (Prompts 1–7 in their original form). The
markdown files in this folder are the verbatim Section A/B/C/D outputs with their registry annotations.

## Prompt 9 — the two new pillars (see `PROMPT9.md`)

Prompt 9 added **28 papers** (23 auto-downloaded + 5 fetched via UCL; **1, `ssiframe25`, dropped as redundant**), cached in
`papers/` and staged in the URL lists `prompt9-identity-urls.txt` and `prompt9-detection-urls.txt`. `PROMPT9.md` is the
authoritative catalogue of these papers, their short-tags, and their relevance. The two pillars:

1. **Identity / registry** (`prompt9-identity-urls.txt`) — DID/VC, blockchain-PKI, permissioned key registry & revocation.
   Grounds the external identity root + registry layer; note `proofmember23` motivates *stripping* full DID/VC down to a
   signatures-plus-allowlist scheme for the single-domain pilot (DID/VC positioned as future work).
2. **Physical-consistency / spoofing detection** (`prompt9-detection-urls.txt`) — vehicle-conservation checking,
   false-data-injection, and Sybil detection. Grounds the conservation/CUSUM + corroboration gate.
   **Honest caveat to carry through:** `Xiao2026Residual` shows that a *coordinated, conservation-respecting* (≥2-key
   colluding) attacker can evade the consistency check — this is exactly the §0 hypothesis-failure axis (colluding
   keys are out of scope); the check proves consistency, not truth, and the authentication/corroboration layer is its
   complement, never a defeat of the boundary claim.

**The novel object (replaces both the old equity tuple and the earlier "integrative novelty" framing above).** The
headline is the **self-referential coupling**: the preemption attack controls the signal phase, which is also the
variable that gates honest-witness coverage, so executing the attack opens the very coverage desert that conceals it —
stated as a conditional lemma under explicit hypotheses (honest keys only, cross-audited non-equivocating quorum, no
operator omission, adequate phase-coupled coverage) and measured once, severely, on Euston A501. Identity/registry +
corroboration + the CT-style log are each individually well-trodden (conceded to prior art); the coupling + its
measured boundary is what is open. There is **no claim of game-theoretic incentive-compatibility** (type-incoherent for
frozen LLMs), and **no claim that coordination is optimised** (the coordination term is a structural zero, reported not
experimented on).

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
