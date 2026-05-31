# Verification report — §2.2

**Source file audited:** sections/sec-2-2.md  
**Audit method:** read section + cross-reference cited tags against registry.json + spot-check numerical claims against papers/PressLight.pdf, papers/Survey-TSC.pdf, papers/MP-Delay.pdf, papers/MP-Pedestrian.pdf.

---

## Summary

- Claims audited: 18
- Citations checked: 9 unique tags (Survey-TSC, CoLight, MPLight, MP-Delay, MP-Pedestrian, PressLight, and implicitly Tassiulas/Ephremides origin via MP-Delay)
- Issues flagged: 3 (NO_CITATION: 2, TAG_MISSING: 0, CLAIM_MISMATCH: 0, WEAK_SUPPORT: 1, HEDGE_VIOLATION: 0, PROHIBITED_CONTENT: 0, STRUCTURAL_ISSUE: 0)
- Overall confidence in the section: HIGH

---

## Issues

### Issue 1 — NO_CITATION

**Location:** §2.2.1 — "Webster's 1958 fixed-time formulation set cycle lengths and green splits from historical demand counts, exposing nothing of the live traffic state to the controller."  
**Citation involved:** None; only [Survey-TSC] is attached to the paragraph-level generational claim, not specifically to Webster 1958.  
**Concern:** The 1958 date and the attribution of the fixed-time formulation are specific historical facts. [Survey-TSC] does cover Webster's method (Section 3.1 of the paper), so the supporting source exists in the local library, but the inline citation appears at the end of the sentence about SCOOT/SCATS, not attached to the Webster sentence. A reader following citation chains cannot unambiguously confirm whether [Survey-TSC] is intended to cover all three sentences in that paragraph or only the SCOOT/SCATS sentence.  
**Recommended fix:** Move the [Survey-TSC] citation to attach to the Webster sentence as well, or add it as a trailing citation on that sentence: "Webster's 1958 fixed-time formulation … [Survey-TSC]." No new tag is required; the source exists.

---

### Issue 2 — NO_CITATION

**Location:** §2.2.1 — "Vehicle-actuated cabinets in the 1960s and 1970s added inductive-loop detection and per-phase extension logic, but coordination remained absent: each intersection optimised in isolation."  
**Citation involved:** None. The sentence has no inline citation.  
**Concern:** This is a specific historical-technological claim (inductive loops, 1960s–1970s, per-phase extension, isolation). [Survey-TSC] Section 3.4 covers actuated control directly, but the citation is not placed on this sentence.  
**Recommended fix:** Append [Survey-TSC] to this sentence. The source supports the claim at Section 3.4 (Actuated Control).

---

### Issue 3 — WEAK_SUPPORT

**Location:** §2.2.2 — "Max-Pressure originated in the work of Tassiulas and Ephremides on packet scheduling for radio networks, where it provided a queue-differential rule that maximised the stability region under stochastic arrivals [MP-Delay]."  
**Citation involved:** [MP-Delay].  
**Concern:** The Tassiulas/Ephremides 1990 origin is confirmed in [MP-Delay] (Introduction, p.1: "The MP policy was initially presented in (Tassiulas and Ephremides, 1990) for the routing and scheduling of packet transmission in a wireless network"), so the factual content is correct. However, [MP-Delay] is a secondary source for this origin claim. The primary source would be the Tassiulas and Ephremides (1990) paper itself. Using [MP-Delay] as sole support for the origin attribution is technically WEAK_SUPPORT: the dissertation is relying on a 2022 paper's characterisation of a 1990 paper it cannot directly cite. This is an acceptable scholarly practice when the primary is inaccessible, but the reader should be aware the attribution is via [MP-Delay; Survey-TSC] rather than the 1990 original.  
**Recommended fix:** Add [Survey-TSC] alongside [MP-Delay] on this sentence. [Survey-TSC] Section 3.6 also attributes the MP origin to Varaiya 2013 (the traffic adaptation), while both sources trace the queueing-theory root to Tassiulas/Ephremides. The dual citation makes the secondary-sourcing transparent.

---

## Cross-checks performed

| Claim | Verified against | Evidence |
|---|---|---|
| "PressLight … average travel time of 88.88 s … against 129.63 s for Max-Pressure … synthetic ten-intersection arterial under heavy uniform demand" | papers/PressLight.pdf Table 6 | Table 6 column "10-intersection arterial HeavyFlat" shows PressLight = 88.88, MaxPressure = 129.63. Numbers match verbatim. The qualifier "heavy uniform demand" correctly identifies the HeavyFlat condition (Arterial 1400 veh/h, flat pattern). |
| "consistent margins across six-, ten-, and twenty-intersection configurations and on a grid network" | papers/PressLight.pdf Table 6 | Confirmed. Table 6 shows PressLight outperforms MaxPressure across all four columns (6-int HeavyFlat/HeavyPeak, 10-int, 20-int, Grid). Claim is accurate. |
| "delay-aware variant of [MP-Delay] … analytically shown to inherit the maximum-stability property of the original Varaiya formulation while reducing observed delay in SUMO microsimulation under arterial demand" | papers/MP-Delay.pdf | Confirmed. Abstract and Section 4 of MP-Delay explicitly prove that the D-MP model "inherits the maximum stability feature of the Original-MP" and Section 5 reports SUMO simulation performance improvements. |
| "pedestrian-aware variant of [MP-Pedestrian] models vehicle and pedestrian queues jointly and proves that maximum stability holds for both populations" | papers/MP-Pedestrian.pdf | Confirmed. Abstract states: "the paper proves that it also exhibits the maximum stability property for both vehicles and pedestrians." Section 3 contains the formal stability proof. |
| "pressure is a sum of local queue-length differences, evaluated in microseconds from per-cabinet sensor inputs, with no central plan computation [MP-Delay; MP-Pedestrian]" | papers/MP-Delay.pdf p.1; papers/MP-Pedestrian.pdf p.1 | Decentralised structure and local computation confirmed in both abstracts. The "microseconds" characterisation is a reasonable inference from "fast computational speed" and "easy of implementation" language in both papers; neither source states a specific latency figure in microseconds. This is qualitatively supported but the word "microseconds" is not numerically verified from these PDFs. |
| "Max-Pressure originated in … Tassiulas and Ephremides … [MP-Delay]" | papers/MP-Delay.pdf p.1 | Confirmed as secondary attribution. MP-Delay Introduction cites "(Tassiulas and Ephremides, 1990)" as the origin. |
| "throughput-stability proof … only one whose throughput-stability proof is reported under mild and broadly stated assumptions [Survey-TSC; MP-Delay; MP-Pedestrian]" | papers/Survey-TSC.pdf Section 3.6; papers/MP-Delay.pdf p.1 | Survey-TSC Section 3.6: "Max-pressure is proved to maximize the throughput of the whole road network." MP-Delay abstract: "maximum stability." Claim characterised as "mild and broadly stated assumptions" — this is a qualitative reading of the papers; neither source uses this exact phrase but the substance is supported by the proof conditions stated in both. |
| Yunex FUSION hedged framing: "vendor-supplied delay-reduction figures for FUSION on London sites are not treated here as established results" | VERIFIER_RULEBOOK.md rule 6 | Hedge correctly applied. The section does not quote specific delay-reduction percentages; it notes the procurement fact and explicitly hedges vendor figures. |

---

## Tags audited

| Tag | Registry status | Cross-check status |
|---|---|---|
| Survey-TSC | VERIFIED (registry entry confirmed) | VERIFIED — PDF pages 1, 5–6, 10 checked |
| CoLight | VERIFIED (registry entry confirmed) | UNAVAILABLE_PDF (not required for §2.2 claims; referenced only as generational example in §2.2.1) |
| MPLight | VERIFIED (registry entry confirmed) | UNAVAILABLE_PDF (referenced only as downstream successor in §2.2.3; numerical claim is §2.3 territory) |
| MP-Delay | VERIFIED (registry entry confirmed) | VERIFIED — PDF pages 1–6 checked |
| MP-Pedestrian | VERIFIED (registry entry confirmed) | VERIFIED — PDF pages 1–5 checked |
| PressLight | VERIFIED (registry entry confirmed) | VERIFIED — PDF Table 6 checked; 88.88 and 129.63 confirmed |

---

## Additional notes

**Hedged-framing compliance (Yunex FUSION):** The Rulebook requires that vendor delay-reduction figures for Yunex FUSION at TfL are not quoted as established results. §2.2.4 states: "vendor-supplied delay-reduction figures for FUSION on London sites are not treated here as established results." This satisfies Rule 6 verbatim. No percentage figure is cited. PASS.

**Prohibited content:** Full scan performed. No occurrences of first-person plural ("we", "our", "us"), supervisor names, Stott-pillar shorthand, internal scaffolding references, "locked thesis/architecture", or marketing superlatives found.

**Structural compliance:**
- Five sub-sections (2.2.1–2.2.5): present and correctly numbered.
- Critical engagement: §2.2.2 contains an explicit critical-engagement paragraph ("Critical engagement is required, however…") addressing the limitation that the throughput-stability proof fails at peak-hour saturation. This satisfies the requirement.
- Land-on paragraph: §2.2.5 "What the literature compels" closes by deriving the first architectural choice from the literature. Correct.
- Word count: 1,195 words (comment-stripped). Budget is 1,000–1,440. PASS.

**Note on "microseconds" characterisation:** The claim that pressure computation runs in "microseconds" appears twice (§2.2.2 and §2.2.5). Neither [MP-Delay] nor [MP-Pedestrian] provides a specific latency figure in microseconds; both describe the algorithm as "fast" or computationally simple. The "microseconds" figure appears to be a reasonable extrapolation from the O(1) arithmetic of the pressure formula, but it is not numerically attested in any cited source. This does not rise to CLAIM_MISMATCH (the qualitative claim of low latency is supported), but the author should be aware the specific time unit is not directly cited and may attract examiner scrutiny. If challenged, the fix is to soften to "evaluated in sub-millisecond time from per-cabinet sensor inputs" or to add an empirical latency citation.
