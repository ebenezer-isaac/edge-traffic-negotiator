# Shared agent rulebook — Chapter 2 Literature Review drafting

This document is read by every drafting agent before producing a section. Read it end-to-end once. Do not reproduce its text.

## What you are doing

You are drafting one section of Chapter 2 (Literature Review) of a UCL MSc dissertation. The chapter target is 10,000–13,000 words across nine sections (§2.1–§2.9). You are writing one of those sections. The chapter argues that no published work instantiates and measures a self-referential coupling — in which a stealthy insider preemption attack controls the same signal phase that gates honest-witness coverage — on a real signalised corridor, backed by an on-device frozen Phi-4-mini reasoner, a deterministic Max-Pressure shield, and a Certificate-Transparency-style, quorum-anchored, cross-audited accountability log (mechanism credited to prior art). The substrate is the real Euston Road (A501) corridor. There is no equity-audit axis, no Qwen backbone, and no blockchain foregrounded as the contribution.

## Output contract

- **Markdown** file at the path the per-section brief specifies.
- ATX headers (`##` for the section heading, `###` for sub-sections).
- Inline citations as `[short-tag]` where the tag matches `06-literary-survey/registry.json`. Example: `the canonical Max-Pressure derivation [Survey-TSC]`. Multiple tags: `[MP-Delay; MP-Pedestrian]`.
- End the section with an HTML comment: `<!-- §2.X word count: NNNN -->` (replace 2.X and NNNN).
- Hit the word budget within ±20%. Do not pad.

## Academic register — strict rules

- **Past tense** for cited findings; **present tense** for analytic claims.
- **No first-person plural.** Do not write "we", "our", "us". Acceptable subjects: "this dissertation", "the proposed system", "the architecture", or passive voice.
- **No marketing language.** Avoid "powerful", "groundbreaking", "state-of-the-art", "cutting-edge".
- **No editorialising or rhetorical questions.** State, cite, critique, link.
- **Critical engagement is mandatory.** Every section must engage at least one weakness, contradiction, missing benchmark, or vendor-bias issue in the cited literature. Do not summarise uncritically.
- **Synthesise, do not list.** A list of paper summaries is not a literature review. Each paragraph either (a) reports what prior work established, (b) critiques a limitation, or (c) links to a design decision the chapter argues for.

## Prohibited content (do NOT write any of these — they are internal scaffolding)

- The student's location, travel, residence, or "Study Away" status.
- Names of supervisors (no "Akin", "Delibasi", "Stott", "Lee Stott").
- "Stott S1", "Stott S2", "Stott S3", "Stott S4", "Stott pillar", or any reference to four-pillar critique framing.
- Prose references to internal scaffolding files: `00-SCOPE-LOCKIN.md`, `prompt1-…`, `prompt2-…`, `prompt3-…`, `prompt4-…`, `prompt5-…`, `prompt6-…`, `prompt7-…`, `PROMPT8.md`, `PROMPT_LITREVIEW.md`. You may *read* these files for content; you may not *cite* them in the prose.
- "The locked thesis", "the locked architecture". Use "this dissertation", "the proposed system", "the architecture this dissertation presents", or passive voice.
- UCL Academic Manual references, GR 6.1, India Graduate Route compliance, DPIA process discussion.
- Methodology details that belong in Chapter 3: BCa bootstrap iterations, k-anonymity floors, Z3 verification rules, SUMO calibration parameters, Holm–Bonferroni correction, demographic-join procedures.
- Implementation details that belong in Chapter 4: Foundry Local engine selection, Docker container layout, web3.py client code.
- Results from this dissertation's own experiments: no SUMO numbers, no Gini values, no latency tables.
- "We thank…", "we acknowledge…", "the author acknowledges…".

## Mandatory hedged framings (apply verbatim where these appear)

The seven claims below have been independently verified and require hedged framing whenever cited:

1. **Traffic-R1 [Traffic-R1]** — Production-deployment claims are UNVERIFIED. Frame as "an emerging line of LLM-driven traffic-signal-control research" (e.g., Zou et al.'s Traffic-R1) rather than as evidence of large-scale operational deployment. Note the PCITECH (SSE: 600728) vendor-academic affiliation explicitly in the first paragraph that cites Traffic-R1. Do not cite the "55,000 daily drivers" figure as established fact; if mentioned, prefix with "the authors report a partial production trial covering, by their account, around 55,000 daily drivers, a figure that has not been independently verified".
2. **Hyperledger Iroha 2** — DISPUTED. Do not cite Iroha 2 as a deployment substrate or quote its "~1 s finality". The chapter's accountability-log position is a Certificate-Transparency-style, quorum-anchored, cross-audited log whose mechanism is credited to prior art; a permissioned Besu QBFT ledger is only a demoted, optional anchoring witness. Do not foreground any blockchain as the contribution, and do not write Iroha 2 into any claim.
3. **Southampton/Minima drone "first blockchain black box"** — VENDOR-ONLY. Drop entirely. Do not cite under any framing.
4. **Google Project Green Light** — PARTIALLY VERIFIED. Cite as "Google's Project Green Light, a vendor-reported deployment with operator-supplied delay-reduction figures and limited independent reproduction". Do not quote specific percentages as established results.
5. **Alibaba City Brain** — PARTIALLY VERIFIED. Cite as "Alibaba's City Brain platform, with vendor-published throughput claims that independent academic reproductions have only partially confirmed".
6. **Yunex FUSION at TfL** — PARTIALLY VERIFIED. Cite as "the Yunex FUSION adaptive-control suite, which Transport for London has procured for new and upgraded sites" without quoting vendor-supplied delay-reduction figures.
7. **NVIDIA Jetson Orin Nano benchmarks** — PARTIALLY VERIFIED. NVIDIA's 38–43 tok/s figure is MLC-engine-specific. Cite as "vendor-reported 38–43 tok/s on the MLC inference engine, with independent reproductions landing 7–15% below that".

## Citation discipline

- Every factual claim has a citation. "X is well-known" is not acceptable.
- Use only `[short-tag]` values that exist in `06-literary-survey/registry.json`. If a tag you need is missing from the registry, stop drafting and note it in a `<!-- TODO -->` comment instead of inventing a tag.
- Multiple sources for a single claim concatenate inside one bracket pair: `[tag1; tag2; tag3]`.
- The downloadable corpus lives at `06-literary-survey/papers/`. Each paper is named `<short-tag>.<ext>` (`.pdf`, `.html`, etc.). When verifying a specific number you cite, open the relevant paper and confirm.

## Structure of every section

1. Open with a one-sentence statement of what the section will establish.
2. Two to five thematic sub-sections (use `###` headers) with their own word budgets.
3. Close with a two-sentence "land on" paragraph stating what design decision the section's literature compels and how it informs the chapter's argument. No editorialising.

## Reference resolution at stitch time

Cite by `[short-tag]` only. After Wave 1 + Wave 2, a stitch step assigns sequential IEEE-numbered references and produces a unified References section. Do not write a per-section references list.
