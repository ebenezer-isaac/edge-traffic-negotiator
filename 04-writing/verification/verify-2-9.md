# Verification report — §2.9

**Source file audited:** sections/sec-2-9.md  
**Audit method:** read section + cross-reference cited tags against registry.json + consistency check against §§2.2–2.8 + word-count measurement + prohibited-content scan.

---

## Summary

- Claims audited: 28
- Citations checked: 22 unique tags
- Issues flagged: 4 (broken down: NO_CITATION 2, TAG_MISSING 0, CLAIM_MISMATCH 0, WEAK_SUPPORT 0, HEDGE_VIOLATION 0, PROHIBITED_CONTENT 0, STRUCTURAL_ISSUE 2)
- Overall confidence in the section: HIGH

---

## Issues

### Issue 1 — STRUCTURAL_ISSUE

**Location:** Line 33 — `<!-- TODO: CoT-Faith tag absent from registry.json; if a standalone faithfulness survey is intended here, assign a registry tag before stitch -->`  
**Citation involved:** None.  
**Concern:** An unresolved author TODO comment survives in the source file. It will appear as raw HTML comment in any Pandoc/LaTeX pipeline that does not strip comments before rendering, and it signals an acknowledged gap in the registry. The body of §2.9.7 does not actually use a "CoT-Faith" tag — it cites [Turpin2023; Lanham2023; Chen2025; Young2026; Hase2026], all of which exist in the registry — so the comment may be stale. However, it needs to be resolved (either removed if stale, or acted on) before the chapter is stitched.  
**Recommended fix:** If no standalone faithfulness-survey entry is required, delete the comment. If an additional survey tag was intended, add it to registry.json, insert the citation, and remove the comment.

---

### Issue 2 — NO_CITATION

**Location:** §2.9.4, sentence "The action-shielding pattern — a learned policy proposes; a deterministic layer disposes — appears in SafeLight and CFLight, both reviewed in §2.3."  
**Citation involved:** None — SafeLight and CFLight are named but carry no inline citation tags.  
**Concern:** In §2.3 both papers are cited as [SafeLight] and [CFLight]. Their first appearance in §2.9 without tags is technically a NO_CITATION for a factual claim, even though the cross-reference pointer is present. A reader following the synthesis section alone cannot look up either paper.  
**Recommended fix:** Append `[SafeLight; CFLight]` after "both reviewed in §2.3" — i.e., "...appears in SafeLight and CFLight, both reviewed in §2.3 [SafeLight; CFLight]."

---

### Issue 3 — NO_CITATION

**Location:** §2.9.6, sentence "UK ATRS Tier 1/2 and EU AI Act Annex III §2 (effective 2 August 2026) impose emerging accountability obligations."  
**Citation involved:** None — no citation tags are present for this regulatory claim.  
**Concern:** Both instruments are cited in §2.8 with tags [uk-atrs] and [eu-ai-act-2024], both of which exist in the registry. The synthesis section asserts these obligations without tagging them, creating an unsupported regulatory claim at the point where novelty is being claimed.  
**Recommended fix:** Add `[uk-atrs; eu-ai-act-2024]` at the end of that sentence.

---

### Issue 4 — STRUCTURAL_ISSUE

**Location:** Word count.  
**Citation involved:** N/A.  
**Concern:** The self-reported comment at line 43 states "§2.9 word count: 840". The target budget is 560–840 words. Measured independently (Python, excluding HTML comments and counting prose + headings), the figure is 840 words — exactly at the upper boundary. This leaves zero headroom for any editorial addition (e.g., the two citation insertions recommended in Issues 2 and 3 will add ~6 words). After those additions the section will exceed the 840-word ceiling by a small margin.  
**Recommended fix:** When adding the two citation tags, trim approximately 8–10 words elsewhere in §§2.9.4 or §2.9.6 to stay inside the budget. The phrase "This combination has never been instantiated at signal-controller level for any controller class" in §2.9.6 slightly restates the sentence before it and is a candidate for compression.

---

## Novelty-tuple completeness check (§2.9.1)

All seven axes are present verbatim in the blockquote:

| Axis | Present in blockquote |
|------|-----------------------|
| sub-7B SLM ∈ {Qwen3-4B, Phi-4-mini} | YES |
| real Lambeth/Southwark Elephant & Castle–Brixton SUMO grid | YES |
| deterministic Max-Pressure shield | YES |
| permissioned Hyperledger Besu QBFT plus Trillian Tessera comparator audit ledger | YES |
| Quarterly Equity Audit Protocol with Gini, Rawlsian Difference Principle, Disparate Impact Ratio and pedestrian-vehicle parity | YES |
| Chain-of-Thought-faithfulness probe under biased-hint injection | YES |
| UK ATRS Tier 1/2 reporting alongside Indian regulatory comparative framing | YES |

---

## Axis paragraph structure check (§§2.9.2–2.9.8)

Each axis paragraph is checked for the three required elements: (a) adjacent ground, (b) dissertation addition, (c) what remains untested.

| Sub-section | Adjacent ground | Dissertation adds | Remains untested |
|-------------|-----------------|-------------------|------------------|
| §2.9.2 Axis 1 | Traffic-R1, CuraLight, HeraldLight, Phi4-Reasoning | 4B–4B pairing with explicit comparator | Validated tok/s, watts, thermal | ALL PRESENT |
| §2.9.3 Axis 2 | MA2C-TSC, CityLight, Survey-TSC | Real Lambeth/Southwark OSM corridor | Distributional equity on real corridor | ALL PRESENT |
| §2.9.4 Axis 3 | Survey-TSC, MP-Delay, MP-Pedestrian, SafeLight, CFLight | MP as microsecond-cost fallback on SLM-JSON failure | Shield-trigger frequency under adversarial inputs | ALL PRESENT |
| §2.9.5 Axis 4 | Veloso2026–Polito2022, BC-AI-Decision, BC-Enforce, BC-TSC | QBFT + Tessera side-by-side evaluation | Head-to-head latency/cost/governance at municipal scale | ALL PRESENT |
| §2.9.6 Axis 5 | verma/ghosh/gangopadhyay/sambasivan | Controller-level protocol, all four frameworks simultaneously | Never instantiated at signal-controller level | ALL PRESENT |
| §2.9.7 Axis 6 | Turpin2023, Lanham2023, Chen2025, Young2026, Hase2026 | Domain-specific probe ~1,000 TSC decisions, Young taxonomy | Faithfulness under biased queue-length hints | ALL PRESENT |
| §2.9.8 Axis 7 | dpdpa-2023, niti-rai, constitution-india, puttaswamy, sambasivan, verma | Comparative framing same artefacts across UK/EU/India frameworks | Regulator-legible artefacts for LLM-TSC in either jurisdiction | ALL PRESENT |

---

## Hedged-framing compliance (Traffic-R1 rule)

§2.9.2 states: "it represents an emerging line of LLM-driven traffic-signal-control research rather than validated production deployment, its authors are affiliated with PCITECH (SSE: 600728), and the authors report a partial production trial covering, by their account, around 55,000 daily drivers, a figure that has not been independently verified [Traffic-R1]."

All three required elements are present: emerging-research framing (not production deployment), PCITECH SSE:600728 affiliation noted, 55,000-driver figure qualified as author-reported and not independently verified. **COMPLIANT.**

---

## Prohibited content scan

Full scan result: no matches for any of the following patterns:  
"the student", "Study Away", "India 90-day", "the user", "Akin", "Delibasi", "Stott", "Lee Stott", "Stott S1/S2/S3/S4", "Stott pillar", "four-pillar critique", "00-SCOPE-LOCKIN.md", "PROMPT_LITREVIEW.md", "prompt1–prompt8", "PROMPT8", "The locked thesis", "the locked architecture", "we", "our", "us" (first-person plural), "powerful", "groundbreaking", "state-of-the-art", "cutting-edge".

Iroha 2: **ABSENT** — compliant.  
Southampton/Minima drone: **ABSENT** — compliant.

---

## Forward link to Chapter 3 (§2.9.9)

A single forward-link sentence is present: "Chapter 3 specifies the audit protocol, the SUMO-Lambeth network construction, the structured-JSON output schema, the formal-verification rules, and the Besu QBFT and Tessera ledger configurations that operationalise the seven axes synthesised above."  
This covers all seven axes by enumeration. **COMPLIANT.**

---

## Cross-checks performed

- Traffic-R1 hedged framing — verified by direct reading of §2.9.2: all three required elements present.
- "Survey-TSC records no published evaluation on a real OpenStreetMap-derived UK borough corridor" — consistent with §2.2 and §2.3 characterisation of the corpus as synthetic-CityFlow-dominant.
- Max-Pressure stability claim in §2.9.4 ("established in the open literature [Survey-TSC; MP-Delay; MP-Pedestrian]") — consistent with §2.2.2 which provides the full derivation; all three tags in registry.
- Besu QBFT benchmark tags (Veloso2026, Khoshaba2023, Ucbas2023, Pierro2024, Polito2022) — all verified present in registry; consistent with §2.7.2 where each is described.
- UK ATRS and EU AI Act in §2.9.6 — regulatory instruments cited in §2.8.2 with tags [uk-atrs; eu-ai-act-2024] confirmed in registry; §2.9.6 omits these tags (Issue 3).
- Young et al. four-quadrant taxonomy cited in §2.9.7 as [Young2026] — confirmed in registry and consistent with §2.6.3's treatment of Young2026.
- Hase2026 (Counterfactual Simulation Training) cited in §2.9.7 — confirmed in registry and consistent with §2.6.5.

---

## Tags audited

| Tag | Registry status | Cross-check |
|-----|-----------------|-------------|
| Traffic-R1 | VERIFIED | In registry at line 1240; hedging compliant |
| CuraLight | VERIFIED | In registry at line 1272 |
| HeraldLight | VERIFIED | In registry at line 1256 |
| Phi4-Reasoning | VERIFIED | In registry at line 408 |
| MA2C-TSC | VERIFIED | In registry at line 1608 |
| CityLight | VERIFIED | In registry at line 1576 |
| Survey-TSC | VERIFIED | In registry at line 1592 |
| MP-Delay | VERIFIED | In registry at line 1624 |
| MP-Pedestrian | VERIFIED | In registry at line 1640 |
| Veloso2026 | VERIFIED | In registry at line 2040 |
| Khoshaba2023 | VERIFIED | In registry at line 2056 |
| Ucbas2023 | VERIFIED | In registry at line 2072 |
| Pierro2024 | VERIFIED | In registry at line 2088 |
| Polito2022 | VERIFIED | In registry at line 2202 |
| BC-AI-Decision | VERIFIED | In registry at line 1896 |
| BC-Enforce | VERIFIED | In registry at line 1912 |
| BC-TSC | VERIFIED | In registry at line 1880 |
| verma-mumbai-rawls-2026 | VERIFIED | In registry at line 3175 |
| ghosh-blr-equity-2022 | VERIFIED | In registry at line 3192 |
| gangopadhyay-mumbai-gini-2021 | VERIFIED | In registry at line 3243 |
| sambasivan-facct-2021 | VERIFIED | In registry at line 2727 |
| Turpin2023 | VERIFIED | In registry at line 8 |
| Lanham2023 | VERIFIED | In registry at line 24 |
| Chen2025 | VERIFIED | In registry at line 40 |
| Young2026 | VERIFIED | In registry at line 120 |
| Hase2026 | VERIFIED | In registry at line 168 |
| dpdpa-2023 | VERIFIED | In registry at line 2364 |
| niti-rai-part1 | VERIFIED | In registry at line 2400 |
| niti-rai-part2 | VERIFIED | In registry at line 2417 |
| constitution-india | VERIFIED | In registry at line 2468 |
| puttaswamy-2017 | VERIFIED | In registry at line 2487 |
| puttaswamy-aadhaar-2018 | VERIFIED | In registry at line 2504 |
| SafeLight | NOT AUDITED (no tag in §2.9) — see Issue 2 |
| CFLight | NOT AUDITED (no tag in §2.9) — see Issue 2 |
| uk-atrs | NOT AUDITED (no tag in §2.9) — see Issue 3 |
| eu-ai-act-2024 | NOT AUDITED (no tag in §2.9) — see Issue 3 |
