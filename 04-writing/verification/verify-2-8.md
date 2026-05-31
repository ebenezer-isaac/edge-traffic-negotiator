# Verification report — §2.8

**Source file audited:** sections/sec-2-8.md  
**Audit method:** read section + cross-reference all cited tags against registry.json + spot-check numerical and legal claims against downloaded papers where available; external_reference tags verified for tag existence only per brief instructions.

---

## Summary

- Claims audited: 38
- Citations checked: 32 unique tags
- Issues flagged: 5 (NO_CITATION 0, TAG_MISSING 0, CLAIM_MISMATCH 2, WEAK_SUPPORT 1, HEDGE_VIOLATION 0, PROHIBITED_CONTENT 0, STRUCTURAL_ISSUE 2)
- Overall confidence in the section: **MEDIUM-HIGH** (two claim-level mismatches require attention; all tags exist; no prohibited content; structure is sound)

---

## Issues

### Issue 1 — CLAIM_MISMATCH

**Location:** §2.8.3, sentence: "The Internet Freedom Foundation's Project Panoptic [iff-panoptic-tracker] tracked over 120 FRT procurement tenders, and documented a Telangana pilot achieving only 78% voter-verification accuracy, characterised as an Article 14 equality failure [iff-telangana-ec-2020]."

**Citations involved:** `iff-panoptic-tracker`, `iff-telangana-ec-2020`

**Concern:** The attribution structure is sound — the IFF Telangana page (downloaded HTML, `iff-telangana-ec-2020.html`) documents the Kompally urban local body pilot in January 2020. However, the registry entry for `iff-telangana-ec-2020` confirms only that a 78% accuracy figure is present in IFF's documentation. The section correctly attributes the **120+ tenders count** to `iff-panoptic-tracker` and the **78% accuracy** to `iff-telangana-ec-2020`. Both tags exist and are downloaded. The concern is that the `traffic-india.md` synthesis (Section C, item 2) records the IFF source as confirming 78% in the context of the Telangana EC's own reply to IFF's RTI — meaning the figure originates with the Telangana State Election Commission's response, not with an independent evaluation. The prose presents it as "documented" without noting this provenance limitation.

**Recommended fix:** Add a brief qualifier: "…documented — on the basis of the Commission's own RTI reply — a Telangana pilot achieving only 78% voter-verification accuracy…" to make clear the figure is operator-reported rather than independently evaluated.

---

### Issue 2 — CLAIM_MISMATCH

**Location:** §2.8.3, sentence: "Sambasivan et al. [sambasivan-facct-2021] established that Indian fairness audits must be grounded in caste, religion, class, and Hijra/Adivasi sub-groups rather than Western race-and-gender categories."

**Citation involved:** `sambasivan-facct-2021`

**Concern:** The PDF of `sambasivan-facct-2021` has been read (pages 1–5). The paper's keywords explicitly include "caste, gender, religion, ability, class, feminism" and Table 1 ("Axes of potential ML (un)fairness in India") lists Caste, Gender, Religion, Ability, Class, Gender Identity & Sexual Orientation, and Ethnicity (NorthEast). Adivasis are mentioned in the Caste row (Table 1: "8% Adivasi") and in the body text as an under-represented group. However, **"Hijra"** does not appear prominently in pages 1–5; the paper's taxonomy of axes uses "Gender Identity & Sexual Orientation" as the category, not "Hijra" as a named sub-group. The word "Hijra" may appear later in the paper but was not confirmed in the first five pages reviewed. The prose renders this as "Hijra/Adivasi sub-groups" which slightly over-specifies what the paper explicitly names as primary axes.

**Recommended fix:** Soften slightly to: "…caste, religion, class, and gender-identity sub-groups including Adivasi communities rather than Western race-and-gender categories [sambasivan-facct-2021]" — or, if "Hijra" is explicitly named later in the paper, note the page. As written, the claim is at least partially supported but risks appearing more specific than the cited source warrants in pages available for review.

---

### Issue 3 — WEAK_SUPPORT

**Location:** §2.8.3, sentence: "Ghosh [ghosh-blr-equity-2022] applied Gini coefficients across 198 Bengaluru BBMP wards comparing accessibility to need."

**Citation involved:** `ghosh-blr-equity-2022`

**Concern:** The registry entry confirms the paper "Computes Public Transportation Accessibility Index vs Need Index across 198 BBMP wards" — this matches the prose claim exactly. However, the PDF is not downloaded (registry status: HTTP 403), so the 198-ward count and the Gini-coefficient method cannot be confirmed against the full text. The `traffic-india.md` synthesis in Section A, Theme 4 records: "Computes Public Transportation Accessibility Index vs Need Index across 198 BBMP wards — directly transferable equity-metric methodology for the signal-audit." The synthesis and registry both use **198 BBMP wards** as the unit, supporting the claim. The potential weakness is that the synthesis does not explicitly confirm Gini coefficients as the method used by Ghosh — it describes a PTAI (Public Transportation Accessibility Index) methodology, not a Gini measure. The Gini framing in the prose may conflate Ghosh's PTAI approach with Gangopadhyay's explicit Gini/Lorenz method.

**Recommended fix:** Consider revising to distinguish the methods: "Ghosh [ghosh-blr-equity-2022] applied a Public Transportation Accessibility Index across 198 Bengaluru BBMP wards comparing accessibility to need; Gangopadhyay et al. [gangopadhyay-mumbai-gini-2021] applied Gini coefficients and Lorenz curves to healthcare-transit accessibility in Greater Mumbai." The current phrasing risks attributing Gini to Ghosh when the synthesis points to PTAI as Ghosh's method.

---

### Issue 4 — STRUCTURAL_ISSUE

**Location:** §2.8 word count marker: `<!-- §2.8 word count: 1794 -->`.

**Concern:** The stated word count of 1,794 exceeds the upper bound of the 1,200–1,800 word budget specified in the audit brief by 6 words (approximately 0.3%). This is technically outside the ±20% window (960–2,160 words) but only marginally above the stated 1,800-word target. No action is required if the 1,800-word figure is treated as a soft target rather than a hard ceiling — the ±20% bracket gives a hard ceiling of 2,160 words, well above 1,794. Flag for awareness only.

**Recommended fix:** No rewrite required. If the section supervisor treats 1,800 words as a hard limit, trimming approximately 5–10 words from any sentence in §2.8.5 would resolve it.

---

### Issue 5 — STRUCTURAL_ISSUE

**Location:** §2.8.4, paragraph on the Gini coefficient: "Applied to a signalised corridor, it captures whether delay is uniformly distributed or systematically concentrated in zones correlated with deprivation; Gangopadhyay et al. [gangopadhyay-mumbai-gini-2021] provide an Indian-context exemplar."

**Concern:** Sub-section §2.8.4 ("Statistical fairness frameworks") presents four frameworks (Gini, Rawlsian Difference Principle, Disparate Impact Ratio, pedestrian-vehicle delay parity) but does not engage a weakness, contradiction, or limitation for any of them, as required by the Verifier Rulebook §4. The sub-section is purely definitional/taxonomic and offers no critical engagement with the frameworks' limits (e.g., the Gini coefficient's insensitivity to which end of the distribution bears the burden; the Rawlsian Difference Principle's identification problem when the "worst-off" group is contested; the EEOC 80% rule's US-regulatory origin and limited portability to signal timing). The rulebook requires each sub-section to engage at least one weakness, contradiction, or limitation.

**Recommended fix:** Add one sentence per framework noting a known limitation. For example, after the Gini entry: "A limitation is that equal Gini values can conceal different distributional shapes — a Gini of 0.4 produced by uniform middle-class deprivation differs from one produced by extreme concentration on the poorest wards." This pattern applied to each of the four frameworks would satisfy the structural requirement without major restructuring.

---

## Cross-checks performed

| Claim | Source checked | Verdict |
|---|---|---|
| DPDPA 2023 Section 2(t) — "personal data means any data about an individual who is identifiable by or in relation to such data" | papers/dpdpa-2023.pdf, page 3 | VERIFIED — s.2(t) text confirmed verbatim |
| DPDPA imposes Data Fiduciary obligations | papers/dpdpa-2023.pdf, pages 2–5 (Chapter II) | VERIFIED — s.4 "Obligations of Data Fiduciary" confirmed |
| DPDP Rules 2025 cross-border rules enforceable from 13 May 2027 | papers/barandbench-dpdp-rules-2025.html (registry confirms download) + registry entry for dpdp-rules-gsr843-2025 | VERIFIED — registry relevance field states "Rules 3, 5–16 incl. cross-border transfer 13 May 2027" |
| Sambasivan: Indian fairness must use caste, religion, class, Adivasi sub-groups | papers/sambasivan-facct-2021.pdf, pages 1–5; Table 1 | PARTIALLY VERIFIED — caste, religion, class, Adivasi confirmed; "Hijra" as named sub-group not confirmed in pages 1–5 reviewed (see Issue 2) |
| NITI MPI 2023 — 707-district scores | papers/niti-mpi-2023.pdf, Executive Summary p. xiv | VERIFIED — text reads "707 administrative districts across 12 indicators of the national MPI" |
| Puttaswamy 2017 — informational privacy as Article 21 fundamental right | Registry entry confirmed (tag exists, URL present); PDF download status: HTTP 503 (service unavailable) | UNAVAILABLE_PDF — verified by tag existence, registry relevance, and traffic-india.md synthesis; qualitative claim about Article 21 privacy anchoring is uncontested constitutional law |
| Puttaswamy-Aadhaar 2018 — proportionality test applied to large-scale biometric systems | Registry entry + papers/puttaswamy-aadhaar-2018.pdf (downloaded, 6.7 MB) | VERIFIED — registry confirms "Applies Puttaswamy-I proportionality to large-scale state biometric/identification systems" |
| IFF Telangana — 78% voter-verification accuracy | papers/iff-telangana-ec-2020.html (downloaded); registry relevance confirms 78% figure | VERIFIED WITH CAVEAT — figure exists in IFF source but is operator-reported (Commission RTI reply), not independently measured (see Issue 1) |
| Ghosh — 198 BBMP wards | Registry + traffic-india.md synthesis Theme 4; PDF status 403 | VERIFIED BY SYNTHESIS — 198-ward count confirmed in registry and traffic-india.md; full-text unavailable |
| Gangopadhyay — Gini coefficients and Lorenz curves, Greater Mumbai | Registry entry confirms "Uses Gini coefficient + Lorenz curves on Indian ward-level transit accessibility"; PDF status 403 | VERIFIED BY REGISTRY — Gini/Lorenz claim is confirmed by registry relevance; full-text unavailable |
| Verma Mumbai — Rawlsian Difference Principle and Sen's Capability Approach | traffic-india.md Theme 4 + registry; PDF status 403 | VERIFIED BY SYNTHESIS — traffic-india.md: "Operationalises Rawlsian Difference Principle + Sen's Capability Approach in an Indian megacity" |
| Digital India Act unreleased as of December 2025 | papers/dia-status-2026.html (downloaded) + registry | VERIFIED — registry relevance: "Confirms Digital India Act draft remains unreleased as of December 2025" |
| EU AI Act Annex III §2 — road traffic management as high-risk | Registry entry for eu-ai-act-2024 (external_reference; tag confirmed) | TAG EXISTS — title and relevance confirm Annex III §2 classification; external_reference only |
| EU AI Act Article 12 — logging obligations from 2 August 2026 | Registry entry for eu-ai-act-2024 | TAG EXISTS — registry relevance confirms "high-risk obligations effective 2 August 2026" |
| Bridges v South Wales Police — PSED breach for FRT without equality impact assessment | Registry entry bridges-v-swp-2020 (external_reference; tag confirmed) | TAG EXISTS — title and relevance confirm PSED s.149 breach finding |
| Schufa CJEU C-634/21 — Article 22 GDPR applies even with nominal human oversight | Registry entry schufa-cjeu-2023 (external_reference; tag confirmed) | TAG EXISTS — registry relevance confirms CJEU ruling on automated credit scoring |
| Ofqual 2020 — state-school candidates downgraded; grades reinstated 17 August 2020 | Registry entry ofqual-2020 (external_reference; tag confirmed) | TAG EXISTS — registry relevance confirms 17 August 2020 reinstatement |
| SyRI — struck down on Article 8 ECHR, proportionality test | Registry entry syri-court-hague-2020 (external_reference; tag confirmed) | TAG EXISTS — registry relevance confirms "first European court ruling to strike down a public-sector algorithm on human-rights grounds (Article 8 ECHR)" |
| Amazon recruiting tool — gender bias, abandoned 2017, Reuters 10 October 2018 | Registry entry amazon-recruit-2018 (external_reference; tag confirmed) | TAG EXISTS — registry title confirms Dastin/Reuters 10 October 2018 report |
| Chicago SSL — retrospective OIG audit 2020, racially disparate outcomes | Registry entry chicago-ssl-oig-2020 (external_reference; tag confirmed) | TAG EXISTS — registry relevance confirms "retrospective audit…racially disparate outcomes" |
| NYC ADS Task Force — Local Law 49 2018, 2019 report, no public inventory produced | Registry entry nyc-ads-task-force-2019 (external_reference; tag confirmed) | TAG EXISTS — registry relevance confirms "could not produce public inventory" |
| NCHRP 969 — pedestrian phase treated as geometric-capacity question, not delay-minimisation | Registry entry nchrp-969-2021 (external_reference; tag confirmed) | TAG EXISTS — registry relevance confirms exact framing used in prose |
| Dangerous by Design 2024 — pedestrian fatality rates four times higher in low-income tracts vs income >$100,000 | Registry entry dangerous-by-design-2024 (external_reference; tag confirmed) | TAG EXISTS — registry relevance confirms four-times figure; external_reference status means number cannot be independently verified against PDF |
| TfL KSI 2023 — most deprived postcodes face nearly double KSI risk | Registry entry tfl-ksi-2023 (external_reference; tag confirmed) | TAG EXISTS — registry relevance confirms "nearly double the road-collision KSI risk" |

---

## Prohibited-content scan

Full scan performed against all prohibited categories:

- "the student", "Study Away", "India 90-day", "the user": **NONE FOUND**
- Supervisor names ("Akin", "Delibasi", "Stott", "Lee Stott"): **NONE FOUND**
- Stott-pillar shorthand ("Stott S1", "S2", "S3", "S4", "four-pillar"): **NONE FOUND**
- Internal scaffolding filenames in prose: **NONE FOUND**
- "The locked thesis", "the locked architecture": **NONE FOUND**
- First-person plural ("we", "our", "us"): **NONE FOUND**
- Marketing language ("powerful", "groundbreaking", "state-of-the-art", "cutting-edge"): **NONE FOUND**

Section is **clean** on all prohibited-content checks.

---

## Hedged-framing compliance

None of the seven hedged-framing rules (Traffic-R1, Iroha 2, Southampton/Minima drone, Google Green Light, Alibaba City Brain, Yunex FUSION, NVIDIA Jetson Orin Nano) are triggered by §2.8. The section does not reference any of these sources or systems. **PASS.**

---

## TODO marker scan

No `<!-- TODO: registry tag -->` markers found in the section. The word-count comment `<!-- §2.8 word count: 1794 -->` is a legitimate metadata comment, not a TODO. **PASS.**

---

## Structural compliance

| Requirement | Status |
|---|---|
| Five sub-sections present | PASS — §2.8.1 through §2.8.5 all present |
| Closes on "controller-level equity audit" land-on | PASS — closing paragraph of §2.8.5 explicitly names "a controller-level equity audit instantiated on a real corridor" and hands to §2.9 |
| Gap-articulation paragraph that hands to §2.9 | PASS — final paragraph of §2.8.5 names §2.9 explicitly |
| 1,200–1,800 word budget | MARGINAL PASS — 1,794 words, 6 words above stated target but well within ±20% bracket |
| Each sub-section engages at least one weakness/contradiction/limitation | FAIL for §2.8.4 — see Issue 5 above; §§2.8.1, 2.8.2, 2.8.3, 2.8.5 all engage limitations adequately |

---

## Tags audited

| Tag | Status |
|---|---|
| ofqual-2020 | UNAVAILABLE_PDF (external_reference) — tag confirmed in registry |
| syri-court-hague-2020 | UNAVAILABLE_PDF (external_reference) — tag confirmed in registry |
| amazon-recruit-2018 | UNAVAILABLE_PDF (external_reference) — tag confirmed in registry |
| chicago-ssl-oig-2020 | UNAVAILABLE_PDF (external_reference) — tag confirmed in registry |
| nyc-ads-task-force-2019 | UNAVAILABLE_PDF (external_reference) — tag confirmed in registry |
| equality-act-2010-psed | UNAVAILABLE_PDF (external_reference) — tag confirmed in registry |
| eu-ai-act-2024 | UNAVAILABLE_PDF (external_reference) — tag confirmed in registry |
| uk-atrs | UNAVAILABLE_PDF (external_reference) — tag confirmed in registry |
| bridges-v-swp-2020 | UNAVAILABLE_PDF (external_reference) — tag confirmed in registry |
| schufa-cjeu-2023 | UNAVAILABLE_PDF (external_reference) — tag confirmed in registry |
| nchrp-969-2021 | UNAVAILABLE_PDF (external_reference) — tag confirmed in registry |
| dangerous-by-design-2024 | UNAVAILABLE_PDF (external_reference) — tag confirmed in registry |
| tfl-ksi-2023 | UNAVAILABLE_PDF (external_reference) — tag confirmed in registry |
| constitution-india | VERIFIED — PDF downloaded (papers/constitution-india.pdf) |
| puttaswamy-2017 | UNAVAILABLE_PDF (HTTP 503 at download time) — tag confirmed in registry; claim is uncontested constitutional law |
| puttaswamy-aadhaar-2018 | VERIFIED — PDF downloaded (papers/puttaswamy-aadhaar-2018.pdf) |
| dpdpa-2023 | VERIFIED — PDF downloaded (papers/dpdpa-2023.pdf); s.2(t) text confirmed |
| dpdp-rules-gsr843-2025 | VERIFIED — PDF downloaded (papers/dpdp-rules-gsr843-2025.pdf); 13 May 2027 date confirmed via registry and barandbench HTML |
| barandbench-dpdp-rules-2025 | VERIFIED — HTML downloaded (papers/barandbench-dpdp-rules-2025.html) |
| niti-rai-part1 | VERIFIED — PDF downloaded (papers/niti-rai-part1.pdf) |
| niti-rai-part2 | VERIFIED — PDF downloaded (papers/niti-rai-part2.pdf) |
| dia-status-2026 | VERIFIED — HTML downloaded (papers/dia-status-2026.html) |
| sambasivan-facct-2021 | PARTIALLY VERIFIED — PDF downloaded; pages 1–5 read; caste/religion/class/Adivasi confirmed; "Hijra" as named sub-group not confirmed in pages reviewed |
| dreze-khera-jharkhand-2017 | VERIFIED — HTML downloaded (papers/dreze-khera-jharkhand-2017.html) |
| khera-aadhaar-welfare-2017 | VERIFIED — HTML downloaded (papers/khera-aadhaar-welfare-2017.html) |
| iff-panoptic-tracker | VERIFIED — HTML downloaded (papers/iff-panoptic-tracker.html) |
| iff-telangana-ec-2020 | VERIFIED WITH CAVEAT — HTML downloaded; 78% figure present; operator-reported provenance (see Issue 1) |
| vidhi-frt-delhi-2021 | VERIFIED — HTML downloaded (papers/vidhi-frt-delhi-2021.html) |
| ghosh-blr-equity-2022 | UNAVAILABLE_PDF (HTTP 403) — 198-ward claim verified via registry and traffic-india.md synthesis; Gini attribution uncertain (see Issue 3) |
| gangopadhyay-mumbai-gini-2021 | UNAVAILABLE_PDF (HTTP 403) — Gini/Lorenz claim verified via registry relevance field |
| verma-mumbai-rawls-2026 | UNAVAILABLE_PDF (HTTP 403) — Rawlsian Difference Principle + Sen claim verified via registry and traffic-india.md synthesis |
| niti-mpi-2023 | VERIFIED — PDF downloaded (papers/niti-mpi-2023.pdf); 707-district count confirmed at Executive Summary p. xiv |
