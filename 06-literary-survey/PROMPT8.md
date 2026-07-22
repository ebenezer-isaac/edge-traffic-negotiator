# Prompt 8 — India compliance, equity precedent, and Bengaluru-corridor anchors for the Edge Negotiator dissertation

> **Archived / superseded (2026-07-21).** This prompt was written under a since-dropped dissertation framing (a
> Quarterly Equity Audit Protocol on a Lambeth/Southwark SUMO corridor, evaluating Qwen3-4B + Phi-4-mini anchored to
> Hyperledger Besu QBFT). That framing is superseded by
> [`../specs/001-edge-negotiator/MASTER-SPEC.md`](../specs/001-edge-negotiator/MASTER-SPEC.md): the substrate is now
> the real **Euston Road (A501)**, the only model is **Phi-4-mini**, the accountability mechanism is a
> Certificate-Transparency-style quorum-anchored + cross-audited log (conceded to prior art, not a blockchain
> contribution), and **equity/fairness auditing and the Indian-regulatory-comparison chapter are not part of the
> current thesis** — there is no Bengaluru secondary chapter. This file is retained only as an archived record of
> the original research scope and its underlying Indian statutory/case-law/dataset citations (genuine prior-art
> references are not deleted); its framing paragraphs below describe the OLD, no-longer-current brief and must not
> be read as a live specification.

## Context (do not skip — this constrains the answer)

This is the eighth prompt in a UCL MSc Systems Engineering for IoT dissertation literature survey. The previous seven prompts produced 147 papers across CoT faithfulness, deterministic SLM + classical fallback, Microsoft commercial intelligence, multi-agent robotics, traffic-LLM control, and edge blockchain — all global / UK / China / EU-anchored. **[Original, now-superseded framing:]** the dissertation primary contribution was at the time understood to be **locked**: a Quarterly Equity Audit Protocol, executed in SUMO on the Elephant & Castle–Brixton corridor (Lambeth/Southwark, London), evaluating an LLM-driven traffic signal controller (Qwen3-4B + Phi-4-mini, MaxPressure shield, structured-JSON+bounded-CoT logging anchored to Hyperledger Besu QBFT). The protocol joined SUMO output to LSOA boundaries, IMD 2019 deciles, and ONS 2021 Census ethnicity, computed Gini / Rawlsian / DIR / pedestrian-parity, and reported under the UK ATRS template. None of this is current — see the banner above.

Two reasons this prompt exists:
1. The student will spend up to 90 days of dissertation work remotely from India under UCL Study Away (Academic Manual §3.5.2). The methodology chapter must situate the audit alongside the Indian regulatory regime, not only the EU AI Act / UK ATRS / US NIST AI RMF triad.
2. There is an optional secondary chapter applying the *same* equity-audit protocol to a Bengaluru corridor (likely ORR–Marathahalli or a comparable BBMP-managed arterial). This chapter will only be added if primary work finishes ahead of schedule, but the literature anchors must be in place either way so the dissertation can credibly claim the protocol generalises.

## Question

Identify and verify the precise Indian regulatory, judicial, dataset, and academic sources required to (a) frame the equity audit chapter against Indian constitutional and statutory law, (b) cite Indian algorithmic-fairness case studies alongside the existing five (Ofqual, SyRI, Amazon, Chicago SSL, NYC ADS), (c) anchor a possible Bengaluru-corridor SUMO build in real geographic and demographic data, and (d) verify any Indian municipal AI traffic deployment claim under the same five-tier evidence hierarchy used in Prompt 5.

## Scope — five themes

### Theme 1: Indian regulatory and constitutional anchors

Required coverage:
- **Digital Personal Data Protection Act 2023** (statutory text, MeitY notification G.S.R. 843(E) of 13 November 2025 finalising DPDP Rules 2025, phased-implementation calendar especially Section 16 cross-border transfers enforceable 13 May 2027)
- **NITI Aayog "Responsible AI for All"** Part 1 (Principles, Feb 2021) and Part 2 (Operationalising Principles, Aug 2021)
- **MeitY AI Advisory** (15 March 2024 and 8 May 2024 revisions — labelling, due-diligence obligations on intermediaries)
- **Digital India Act draft** (most recent public consultation document, if available)
- **Indian Constitution Articles 14 (equality before law), 15 (non-discrimination), 16 (equal opportunity in public employment), 21 (life and personal liberty)** — primary text, not commentary
- **K.S. Puttaswamy v Union of India (2017) 10 SCC 1** — the right-to-privacy nine-judge bench
- **K.S. Puttaswamy v Union of India (2018) 1 SCC 809** — the Aadhaar five-judge bench
- **R. Rajagopal v State of Tamil Nadu (1994)** — informational privacy precedent if cited in DPDPA literature
- **Personal Data Protection Bill 2019 / Joint Parliamentary Committee Report (2021)** — as historical context for the DPDPA's drafting choices

For each, prefer: official gazette PDF / Supreme Court of India judgment PDF / MeitY notification → peer-reviewed legal scholarship → top-tier Indian legal commentary (Indian Constitutional Law and Philosophy blog, Bar and Bench, Indian Express legal correspondents). No vendor-published "DPDPA explainers".

### Theme 2: Indian algorithmic-fairness case studies and audit precedents

Required coverage:
- **Aadhaar-based welfare exclusion** — Khera (Drèze, Khera, Yadav) PDS / NREGA exclusion studies; LibTech India audits; Right to Food Campaign documentation
- **Telangana facial-recognition controversy** — IFF (Internet Freedom Foundation) Project Panoptic documentation; the Hyderabad Cordon & Search FRT cases
- **Delhi Police facial recognition** — Delhi High Court orders, IFF litigation, RTI disclosures
- **SECC 2011 algorithmic targeting** — academic critiques of Socio-Economic Caste Census-derived welfare targeting
- **PMJAY / Ayushman Bharat algorithmic eligibility** — exclusion-error studies if peer-reviewed
- **e-Mulakat / prison video-conferencing FRT** if relevant
- **CCTV in Delhi / Lucknow / Hyderabad** — Common Cause v Union of India petitions, IFF reports
- At least **one Indian peer-reviewed paper on algorithmic fairness in public services** (FAccT / FAT* India track, ACM CHI India, IIT Bombay / IIIT-D / IIM-B publications)

For each: prefer peer-reviewed Indian academic publications and Internet Freedom Foundation case dossiers over journalism. Where journalism is the only source (e.g., Telangana FRT), use Scroll, The Wire, Article-14, The Hindu, Business Standard — never vendor blogs.

### Theme 3: Indian Smart Cities Mission technical infrastructure

Required coverage:
- **India Urban Data Exchange (IUDX)** — IISc Bangalore architecture papers, IUDX 2.0 documentation, list of operational cities and traffic-relevant catalogues (Surat transit, Pune, Varanasi, etc.)
- **Smart Cities Open Data Portal** — Government Open Data License – India (GODL-India, February 2017), catalogue inventory
- **UVH-26 dataset** (IISc + Bengaluru Traffic Police, 26,678 annotated CCTV images, 2024) — release paper or technical report, licence terms
- **IDD (Indian Driving Dataset)** — IIIT Hyderabad, CVPR Workshops 2018 paper, IDD-AW 2024 (adverse weather), IDD-X 2024 (multi-modal)
- **DATS_2022 Maharashtra** — release paper if available
- **DataSmart Cities Strategy** — MoHUA 2019 strategy document
- **Smart Cities Mission Operational Guidelines** (June 2015 + revisions)
- **Integrated Command and Control Centre (ICCC) reference architecture** — National Institute of Urban Affairs (NIUA) publications, MoHUA frameworks
- **City Data Officer (CDO) directory and policy** — DataSmart Cities role definition

Confirm dataset licences and confirm whether any contain re-identifiable personal data (CCTV facial images, vehicle registration plates) that would change the GDPR / DPDPA analysis.

### Theme 4: Indian urban transport equity research

Required coverage:
- **WRI India Ross Center for Sustainable Cities** publications on Bengaluru / Mumbai / Surat traffic equity (2020 onwards)
- **Ola Mobility Institute** "Ease of Moving" reports (2018, 2019, 2022 if extant) — specifically the equity / accessibility chapters
- **Indian Institute for Human Settlements (IIHS Bengaluru)** transport equity working papers
- **NITI Aayog Multidimensional Poverty Index** national report (2021) and updated district scores (2023) — especially Karnataka district MPI for the Bengaluru-corridor anchor
- **Census of India 2011 ward-level boundaries** — confirm availability for Bengaluru BBMP wards (198 / 243 ward delimitation history); confirm Census 2021 status (delayed)
- **Transport for Bengaluru / DULT (Directorate of Urban Land Transport)** Comprehensive Mobility Plan 2020 / 2024
- **BBMP Traffic Engineering Cell** publications or Lok Sabha / Rajya Sabha unstarred questions on signal optimization
- **Indian peer-reviewed transport-equity papers** (Transportation Research Part D / Part F India authors, Transportation in Developing Economies journal, Cities journal — at least 4 distinct papers on Indian urban transport accessibility / fairness / pedestrian safety)

Triangulate: at least one paper using Gini-coefficient or Rawlsian framing on Indian transport, so the methodology transfer is anchored in existing Indian literature.

### Theme 5: Indian municipal AI traffic deployment claim verification

Apply the prompt5 five-tier evidence hierarchy:
1. Peer-reviewed independent evaluations
2. Operator-published data (BBMP, Surat Smart City Ltd, Pune Smart City Development Corporation, etc.)
3. Credible journalism (The Hindu, Times of India urban-affairs desk, Business Standard, Hindustan Times, Scroll, The Wire, Bloomberg India)
4. Academic reproductions on public datasets
5. Vendor press releases (L&T Smart World, Honeywell, Siemens India, IBM India, Wipro, TCS) — flagged as WEAKEST

Claims to verify (mark each VERIFIED / PARTIALLY VERIFIED / VENDOR-ONLY / DISPUTED / UNVERIFIED with a recommended dissertation framing sentence):
- **Bengaluru Adaptive Traffic Control System (BATCS)** — Siemens / KITS deployment scale, claimed delay reduction
- **Bengaluru Smart Signal pilot** — Bosch + BBMP, any published metrics
- **Surat ICCC traffic optimization** — L&T Smart World scale, any third-party evaluation
- **Pune ICCC** — Tech Mahindra / L&T deployment
- **Ahmedabad Smart City traffic** — Honeywell deployment
- **Delhi Intelligent Traffic Management System** — any public performance data
- **Hyderabad Cyberabad Traffic Police AI signals** — TCS / NEC deployment
- **Mumbai BMC traffic signals** — any AI/adaptive deployment claims
- **Indore Smart City** — top-ranked Smart City, traffic component
- **Kerala Motor Vehicle Department AI Camera (Safe Kerala)** — Keltron + Trois Infotech, fines-issued claims (most-cited example, heavily disputed in High Court)

For each: name the exact source (URL + author + date), state what the source claims, identify whether the claim is corroborated by any non-vendor source, and produce the dissertation-framing sentence.

## Format requirements

Output as a single Markdown file `india-context.md` in the same shape as `traffic-llms.md` and `edge-blockchain.md`:

### Section A — Per-theme annotated tables

Five tables, one per theme. Columns: `Short-tag | Title | Year | Direct PDF or canonical URL | Source type | 1-sentence relevance to dissertation`.

Source-type vocabulary: `Statute | Judgment | Government policy | Peer-reviewed | Working paper | Operator report | Journalism | Dataset release | Legal commentary`.

Minimum row counts per theme: Theme 1 ≥ 6, Theme 2 ≥ 6, Theme 3 ≥ 6, Theme 4 ≥ 5, Theme 5 ≥ 5. Total ≥ 28 sources. No upper bound.

### Section B — Adaptation matrix

A two-column table mapping each UK / EU ingredient already used in the dissertation to its Indian equivalent, citing the precise source from Section A:

| UK / EU ingredient | Indian equivalent (with `[short-tag]`) |
|---|---|
| LSOA boundaries (ONS 2021) | … |
| IMD 2019 deciles | … |
| ONS 2021 Census ethnicity | … |
| Equality Act 2010 PSED s.149 | … |
| EU AI Act Article 12 logging | … |
| EU AI Act Annex III §2 high-risk | … |
| UK GDPR personal-data threshold | … |
| UK ATRS Tier 1 / Tier 2 templates | … |
| Bridges v South Wales Police (2020) | … |
| Schufa CJEU C-634/21 | … |

Where no clean Indian equivalent exists, mark "no direct equivalent — note:" and explain.

### Section C — Gap analysis and dissertation framing claim

In ≤ 600 words, answer:
1. Which Stott critique pillars (S1 CoT risk, S2 equity operationalisation, S3 evidential basis, S4 blockchain trade-offs) does Indian-context coverage strengthen, and which does it leave unchanged?
2. Does any Indian deployment claim require correction in the existing coursework or registry? (Flag specifically.)
3. Is the Bengaluru-corridor secondary chapter feasible from open data alone? Specifically: are BBMP ward boundaries (198 vs 243 ward delimitation), NITI MPI Karnataka district scores, and at least one anonymised Bengaluru traffic flow / signal-timing dataset all simultaneously available under non-restrictive licences as of April 2026? If not, what is missing?
4. Does the dissertation need to acknowledge any India-specific data-protection constraint not already covered by the UK GDPR analysis? (DPDPA Section 2(t) personal-data definition; DPDPA Section 16 cross-border transfers; absence of UK adequacy decision in either direction as of April 2026.)
5. State the **precise India-context framing claim** the dissertation will adopt in the methodology chapter — one paragraph that the student can paste into the thesis verbatim with citations as `[short-tag]`.

### Section D — Plain download list

Flat list of every URL from Section A, in the order they appear, suitable for a `wget` / `curl` script. Group by theme with single-line headers.

## Hard constraints

- **No vendor press releases as primary evidence.** Every Theme 5 claim must be triangulated against at least one non-vendor source or explicitly marked VENDOR-ONLY with the recommendation to drop or footnote, exactly as Prompt 5 handled the Southampton / Minima drone claim.
- **Citation freshness.** Prefer 2024–2026 sources; older sources only when statutory (Constitution, Census 2011) or precedential (Puttaswamy 2017/2018).
- **No paywalled-only sources** unless absolutely no open alternative exists. Where a source is paywalled, name an open mirror or institutional repository.
- **Verify dataset licences.** Every dataset cited (UVH-26, IDD, DATS_2022, IUDX catalogues, Smart Cities portal data) must have an explicitly named licence in the relevance sentence.
- **Do not propose new methodology, models, hardware, or architecture.** This prompt's job is purely to surface jurisdictional, evidential, and corridor-anchor sources. **[Superseded — see the archival banner at the top of this file.]** At the time this prompt was written the technical substrate was understood to be Qwen3-4B + Phi-4-mini + MaxPressure shield + Besu QBFT + Tessera + SUMO Lambeth; the current substrate per `MASTER-SPEC.md` is Phi-4-mini only, on the real Euston Road (A501), with a Certificate-Transparency-style quorum-anchored + cross-audited accountability log (Besu/Tessera demoted to a cited prior-art anchor option, not the core mechanism).

## Stop conditions

Stop when Section A has ≥ 28 sources covering all five themes at the minimum per-theme counts, Section B has every row populated or explicitly marked "no direct equivalent", Section C answers all five sub-questions, and Section D's URL list is non-empty for every Section A entry. Do not pad with weak sources; if a theme has fewer than the minimum after exhaustive search, report the shortfall in Section C as a finding.
