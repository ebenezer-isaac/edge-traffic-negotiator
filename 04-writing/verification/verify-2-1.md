# Verification report — §2.1

**Source file audited:** sections/sec-2-1.md  
**Audit method:** read section + exhaustive prohibited-content scan + structural compliance check + cross-reference framing previews against sec-2-2.md through sec-2-9.md.

---

## Summary

- Claims audited: 0 factual claims with inline citations (§2.1 is a roadmap section; no citation-bearing factual assertions are made)
- Citations checked: 0
- Issues flagged: 4 (broken down: NO_CITATION 0, TAG_MISSING 0, CLAIM_MISMATCH 0, WEAK_SUPPORT 0, HEDGE_VIOLATION 0, PROHIBITED_CONTENT 0, STRUCTURAL_ISSUE 4)
- Overall confidence in the section: MEDIUM

---

## Issues

### Issue 1 — STRUCTURAL_ISSUE

**Location:** "Section 2.5 surveys the edge-hardware benchmark literature and shows that it is mature enough to constrain a future cabinet deployment but does not yet report validated closed-loop integration of a 4–8B controller against a downstream SUMO loop under sustained thermal load; the empirical contribution of this dissertation is accordingly evaluated on a developer-class GPU rather than cabinet-class edge silicon."

**Citation involved:** none

**Concern:** §2.1 assigns §2.5 the role of surveying "edge-hardware benchmark literature." But §2.4 in the actual text is what covers LLM-for-TSC, and §2.5 covers "Small language models on edge hardware." The content description given for §2.5 in §2.1 ("edge-hardware benchmark literature … mature enough to constrain a future cabinet deployment … no validated closed-loop integration of a 4–8B controller against a downstream SUMO loop under sustained thermal load") matches §2.5 correctly. However, the grouping header in §2.1 labels §§2.2–2.5 as "Technical baselines and controller selection (§§2.2–2.5)," yet §2.4 maps the "LLM-for-TSC frontier" and §2.5 specifically covers edge hardware. The section numbering in the structural preview is internally consistent with actual section content; this is not a mismatch. **No error here — see Issue 2 below for the real cross-reference problem.**

**Recommended fix:** Disregard; the preview is accurate. (Issue entered to document the cross-check was performed.)

---

### Issue 2 — STRUCTURAL_ISSUE

**Location:** "Section 2.6 establishes that the Chain-of-Thought faithfulness literature converges on a well-evidenced conclusion: explicit CoT traces are post-hoc rationalisations rather than faithful causal records … the architecture this dissertation presents therefore treats the CoT log as conditionally valuable justification governed by a six-property design checklist rather than as evidence of why the model decided as it did."

**Citation involved:** none

**Concern:** §2.6 in the actual text (sec-2-6.md) closes on "a six-property design checklist — auditability of the structured output, integrity protection of the trace once written, structured-JSON output with bounded reasoning length, formal verification of the actuator command emitted alongside the trace, separation of the decision channel from the justification channel, and a statistical faithfulness probe applied off-line." The §2.1 preview accurately captures this. However, the section is grouped under "Auditability, ledger, and fairness (§§2.6–2.8)," yet §2.6 is a CoT faithfulness section that does not primarily deal with the audit ledger. This grouping header slightly misrepresents §2.6's primary contribution, which is about faithfulness (an input to the architecture decision about logging), not the ledger itself. A reader skimming §2.1 may form the incorrect impression that §2.6 is predominantly about auditable logging mechanics rather than the underlying faithfulness failure mode.

**Recommended fix:** Revise the subsection header from "Auditability, ledger, and fairness (§§2.6–2.8)" to something like "CoT faithfulness, audit ledger, and equity (§§2.6–2.8)" to accurately represent §2.6's primary content.

---

### Issue 3 — STRUCTURAL_ISSUE

**Location:** "Section 2.8 shows that no existing algorithmic-fairness audit covers traffic signal control; UK and EU regulatory frameworks compel auditability of high-risk public-sector AI at controller level, but no published audit instantiates those frameworks for an LLM-driven controller, and Indian regulatory comparative framing alongside Indian transport-equity research provides methodological precedents that have not been combined with signal-timing audit on a real corridor."

**Citation involved:** none

**Concern:** The actual §2.8 (sec-2-8.md) covers both UK/EU *and* Indian regulatory anchoring in considerable depth, with the Indian framework treated as supplying a "comparative analytical lens" and field-deployable audit methods. The §2.1 preview correctly identifies this dual-jurisdiction structure. However, the preview's phrasing "Indian regulatory comparative framing alongside Indian transport-equity research provides methodological precedents" slightly undersells the structural claim of §2.8, which is that Indian research supplies what UK/EU literature *lacks* (constitutionally grounded equity norms, Gini and Rawlsian transport-equity benchmarks). This is a framing weakness, not an outright inaccuracy.

**Recommended fix:** Strengthen the preview sentence to: "…Indian regulatory and constitutional comparative framing, combined with South Asian peer-reviewed transport-equity research (Gini coefficients, Rawlsian Difference Principle), supplies the methodological precedents that UK and EU literature currently lacks for controller-level audit." This matches §2.8.3's explicit closing claim and §2.8.5's "what the literature compels" paragraph.

---

### Issue 4 — STRUCTURAL_ISSUE

**Location:** "Section 2.9 closes the chapter on the novelty claim that motivates the entire review. Each of the seven axes of the architecture … is occupied by adjacent prior work. Their conjunction is not."

**Citation involved:** none

**Concern:** The §2.1 closing-claim paragraph lists seven axes for the novelty tuple and these must match §2.9 exactly. Cross-checking against §2.9.1 (sec-2-9.md):

| Axis | §2.1 wording | §2.9.1 wording | Match? |
|------|-------------|----------------|--------|
| 1 | "a sub-7B SLM controller" | "sub-7B SLM ∈ {Qwen3-4B, Phi-4-mini}" | Partial — §2.1 omits the model-name specifics |
| 2 | "a real Lambeth/Southwark Elephant & Castle–Brixton SUMO corridor" | "real Lambeth/Southwark Elephant & Castle–Brixton SUMO grid" | Match |
| 3 | "a deterministic Max-Pressure shield" | "deterministic Max-Pressure shield" | Match |
| 4 | "a permissioned Besu QBFT plus Tessera-comparator audit ledger" | "permissioned Hyperledger Besu QBFT plus Trillian Tessera comparator audit ledger" | Match (§2.1 uses informal abbreviation; acceptable) |
| 5 | "a Quarterly Equity Audit Protocol incorporating Gini, Rawlsian, disparate-impact-ratio and pedestrian-parity metrics" | "Quarterly Equity Audit Protocol with Gini, Rawlsian Difference Principle, Disparate Impact Ratio and pedestrian-vehicle parity" | Match |
| 6 | "a CoT-faithfulness probe under biased-hint injection" | "Chain-of-Thought-faithfulness probe under biased-hint injection" | Match |
| 7 | "UK ATRS Tier 1/2 reporting alongside Indian regulatory comparative framing" | "UK ATRS Tier 1/2 reporting alongside Indian regulatory comparative framing" | Match |

The only divergence is Axis 1: §2.1 writes "a sub-7B SLM controller" whereas §2.9.1 writes "sub-7B SLM ∈ {Qwen3-4B, Phi-4-mini}." §2.4 and §2.5 (the sections being previewed) both refer to Qwen3-4B and Phi-4-mini by name. The §2.1 roadmap elides the model names at Axis 1, which is acceptable for a roadmap context, but may create a mild inconsistency for a reader who compares §2.1's closing tuple against §2.9's definitive tuple. This is a minor consistency gap, not a factual error.

**Recommended fix:** Add the model-name pair to Axis 1 in §2.1's closing paragraph: "a sub-7B SLM controller (Qwen3-4B and Phi-4-mini)" to align with the specificity level of §2.9.1 and §2.4.5.

---

## Prohibited content scan

The following terms were searched exhaustively in sec-2-1.md:

| Term | Found? |
|------|--------|
| "Stott" | No |
| "S1", "S2", "S3", "S4" (Stott-pillar shorthand) | No |
| "Akin" | No |
| "Lee Stott" | No |
| "the locked thesis" / "the locked architecture" | No |
| "Study Away" | No |
| "India 90-day" | No |
| "the student" / "the user" | No |
| First-person plural: "we", "our", "us" | No |
| "prompt1" through "prompt8" / "PROMPT" (in prose) | No |
| "powerful", "groundbreaking", "state-of-the-art", "cutting-edge" | No |
| "00-SCOPE-LOCKIN.md" / "PROMPT_LITREVIEW.md" | No |

**Result: CLEAN — no prohibited content detected.**

---

## Hedged-framing compliance

§2.1 makes no inline factual claims about Traffic-R1, Hyperledger Iroha 2, Southampton/Minima drones, Google Project Green Light, Alibaba City Brain, Yunex FUSION, or NVIDIA Jetson Orin Nano benchmarks. It is a roadmap section. No hedged-framing obligations are triggered in this section.

**Result: CLEAN — no hedge violations.**

---

## Length check

The section comment states `<!-- §2.1 word count: 426 -->`. The target is 320–480 words (±20% of 400-word budget). 426 words falls within the 320–480 band.

**Result: PASS.**

---

## Structural coverage check

| Required element | Present? | Notes |
|-----------------|----------|-------|
| Previews §2.2 in one short paragraph | Yes | Second paragraph, first sentence |
| Previews §2.3 in one short paragraph | Yes | Second paragraph, second sentence |
| Previews §2.4 in one short paragraph | Yes | Second paragraph, third sentence |
| Previews §2.5 in one short paragraph | Yes | Second paragraph, fourth sentence |
| Previews §2.6 in one short paragraph | Yes | Third paragraph, first sentence |
| Previews §2.7 in one short paragraph | Yes | Third paragraph, second sentence |
| Previews §2.8 in one short paragraph | Yes | Third paragraph, third sentence |
| Previews §2.9 (closing novelty claim) | Yes | Fourth paragraph |
| Closes on seven-axis novelty-tuple framing | Yes | Final paragraph lists all seven axes explicitly |
| No "what the literature compels" land-on required (roadmap section) | N/A | Roadmap sections are exempt from the sub-section weakness/limitation requirement per VERIFIER_RULEBOOK §4 |

**Result: All eight section previews present. Novelty-tuple closing claim present.**

---

## Cross-checks performed

No numerical or citation-bearing claims appear in §2.1. Cross-checks were limited to framing accuracy against the actual section texts:

- §2.1 preview of §2.2 ("only signal-control policy with a published throughput-stability proof … pedestrian-aware extension proven to generalise to London borough conditions … inverts the SCOOT/SCATS regional-controller assumption") — verified against sec-2-2.md §§2.2.2 and 2.2.5: accurate.
- §2.1 preview of §2.3 ("Max-Pressure, MPLight, CoLight and Adv-CoLight on CityFlow; MA2C and the RESCO suite on SUMO grids … consistent brittleness of pure reinforcement-learning controllers under sensor faults and adversarial V2X messaging") — verified against sec-2-3.md §§2.3.1–2.3.5: accurate.
- §2.1 preview of §2.4 ("fewer than thirty papers across roughly eighteen months; only Traffic-R1 (Qwen-2.5-3B) and CuraLight (Gemma-3) occupy the sub-7B size class … no paper in the corpus has executed a distributional equity audit") — verified against sec-2-4.md §§2.4.5–2.4.6: accurate. Note: §2.4 does not give a precise paper count but characterises the corpus size; the "fewer than thirty papers" figure in §2.1 is a characterisation consistent with the enumerated papers in sec-2-4.md.
- §2.1 preview of §2.5 ("mature enough to constrain a future cabinet deployment … does not yet report validated closed-loop integration of a 4–8B controller against a downstream SUMO loop under sustained thermal load … evaluated on a developer-class GPU") — verified against sec-2-5.md §2.5.4: accurate.
- §2.1 preview of §2.6 ("converges on a well-evidenced conclusion … six-property design checklist") — verified against sec-2-6.md §2.6.6: accurate.
- §2.1 preview of §2.7 ("Hyperledger Besu QBFT in development mode, paired with a Trillian Tessera RFC-6962 Merkle-log comparator … sub-second finality … whether the audit workload requires Byzantine-fault-tolerant consensus or whether a tamper-evident transparency log suffices") — verified against sec-2-7.md §2.7.4: accurate.
- §2.1 preview of §2.8 ("no existing algorithmic-fairness audit covers traffic signal control; UK and EU regulatory frameworks compel auditability … Indian regulatory comparative framing alongside Indian transport-equity research provides methodological precedents") — verified against sec-2-8.md §§2.8.3 and 2.8.5: substantively accurate; framing slightly undersells the Indian research contribution (see Issue 3).
- §2.1 novelty-tuple closing paragraph — verified axis-by-axis against sec-2-9.md §2.9.1: six of seven axes match verbatim or by clear abbreviation; Axis 1 omits model names (see Issue 4).

---

## Tags audited

No inline citation tags appear in §2.1. No tag verification was required.
