# Verification report — §2.3

**Source file audited:** sections/sec-2-3.md  
**Audit method:** read section + cross-reference cited tags against registry.json + spot-check numerical claims against papers/<tag>.pdf; synthesis cross-checked against traffic-llms.md.

---

## Summary

- Claims audited: 22
- Citations checked: 12 unique tags (MPLight, FRAP, RESCO, CoLight, Adv-XLight, CityLight, MA2C-TSC, SafeLight, CFLight, Adv-DRL-TSC, T-REX, CollusionVeh)
- Issues flagged: 4 (NO_CITATION 0, TAG_MISSING 0, CLAIM_MISMATCH 1, WEAK_SUPPORT 2, HEDGE_VIOLATION 0, PROHIBITED_CONTENT 1, STRUCTURAL_ISSUE 0)
- Overall confidence in the section: MEDIUM (one claim_mismatch on a headline number; one prohibited-content term; two weak-support flags on paraphrased findings)

---

## Issues

### Issue 1 — CLAIM_MISMATCH

**Location:** §2.3.1, sentence: "MPLight instantiated this template at scale by combining a pressure-based reward with a phase-pair-invariant state representation, and reported approximately a thirteen-percent travel-time reduction over Max-Pressure on a Manhattan network of 2,510 intersections [MPLight]."

**Citation involved:** [MPLight]

**Concern:** The MPLight PDF (pages 1–5 reviewed) confirms the Manhattan 2,510-intersection experiment but does not state a 13% gain over Max-Pressure in the pages read. The RESCO paper's related-work section (p. 4) explicitly describes MPLight's headline result as "up to a 19.2% improvement in travel times over the next best compared method, PressLight" — not over Max-Pressure. The 13%-over-Max-Pressure figure originates from the traffic-llms.md registry synthesis entry ("~13% travel time over MaxPressure; scales to 2510 ints") and is reproduced in the RESCO registry entry, but it cannot be verified directly from the MPLight PDF pages available. The RESCO paper (§2.3 Related Work) attributes a different figure to the MPLight–PressLight comparison (19.2%). It is possible the 13% figure appears later in the MPLight paper's results tables (beyond the 5 pages read), but it cannot be confirmed from the accessible pages. Given that the RESCO narrative assigns a PressLight comparison (19.2%), not a Max-Pressure comparison, to MPLight's headline, there is a material risk that the 13%-over-Max-Pressure figure is either from a different configuration or is an approximation that conflates multiple comparisons.

**Recommended fix:** Check MPLight paper results tables (pages 6–9, not yet read) to confirm the specific percentage. If confirmed, add a parenthetical hedge: "reported approximately a thirteen-percent travel-time reduction over Max-Pressure (in one configuration; the same paper reports a 19.2% gain over PressLight)." If not confirmed in MPLight directly, attribute the figure to [RESCO] which discusses it, or soften to "reported travel-time reductions over both PressLight and Max-Pressure on a Manhattan network of 2,510 intersections [MPLight; RESCO]" without a specific percentage.

---

### Issue 2 — WEAK_SUPPORT

**Location:** §2.3.4, sentence: "[T-REX] benchmarked RL traffic-signal controllers under incident and sensor-fault conditions and reported sharp degradation, with the more complex state representations more brittle than simpler pressure-based ones — a counter-intuitive finding that punishes precisely the architectures (CoLight, Adv-CoLight) that perform best in the clean-sensor regime [T-REX]."

**Citation involved:** [T-REX]

**Concern:** The T-REX abstract (pages 1–4 reviewed) confirms sharp degradation under incidents and confirms that "independent value-based and decentralized pressure-based methods offer fast convergence and generalization in stable traffic conditions… their performance degrades sharply under incident-driven distribution shifts," and that "hierarchical coordination methods tend to offer more stable and adaptable performance in large-scale, irregular networks." This is the inverse of what the prose states. The prose claims the *complex* representations (CoLight, Adv-CoLight) are *more* brittle; but T-REX's finding — that hierarchical methods are *more* stable — is directionally the opposite. T-REX does not specifically call out CoLight or Adv-CoLight as the brittle architectures; it contrasts independent/pressure-based methods with hierarchical ones, finding the latter *more* robust. The phrasing "more complex state representations more brittle" does not accurately represent T-REX's finding, and attributing this to CoLight/Adv-CoLight specifically is not supported by the pages read.

**Recommended fix:** Revise to accurately reflect T-REX: "reported that independent value-based and pressure-based controllers degrade sharply under incident-driven distribution shifts, while hierarchical coordination methods show more stable performance, though at the cost of slower convergence — a trade-off that complicates practical deployment [T-REX]." Remove the unsupported claim that CoLight and Adv-CoLight are specifically identified as the brittle architectures.

---

### Issue 3 — WEAK_SUPPORT

**Location:** §2.3.4, sentence: "SafeLight wrapped a residual RL policy in formal safety constraints and drove intersection collisions to approximately zero, but it did so at a measurable throughput cost relative to an unconstrained baseline [SafeLight]."

**Citation involved:** [SafeLight]

**Concern:** The SafeLight PDF (pages 1–4 reviewed) confirms "achieves over 99 percent reduction in collisions" — "approximately zero" is an acceptable paraphrase of this. However, the claim of "measurable throughput cost" is more nuanced. The SafeLight introduction says the method "can significantly reduce collisions while increasing traffic mobility" and the abstract states "Results show that our method can significantly reduce collisions while increasing traffic mobility." The paper explicitly claims *both* safety and mobility improvement simultaneously. The prose's assertion of a "measurable throughput cost" contradicts the paper's stated result. SafeLight reports better mobility *and* safety compared to Fixed-time control; the throughput comparison to an *unconstrained RL baseline* may show a cost, but the paper's headline is that it achieves safety gains without a mobility penalty relative to Fixed-time.

**Recommended fix:** Soften the throughput-cost claim: "SafeLight wrapped a residual RL policy in formal safety constraints and drove intersection collisions to near zero; its mobility results relative to unconstrained RL baselines are mixed, though the paper reports overall mobility improvements over Fixed-time control [SafeLight]." Alternatively, verify the specific throughput-vs-unconstrained comparison in SafeLight's results tables (pages 5–8, not reviewed) and qualify appropriately.

---

### Issue 4 — PROHIBITED_CONTENT

**Location:** §2.3.4, sentence: "...this is precisely the V2I-spoofing threat model that the architecture this dissertation presents inherits from any connected-vehicle data feed [CollusionVeh]."

**Phrase flagged:** "the architecture this dissertation presents"

**Concern:** The VERIFIER_RULEBOOK prohibits "The locked thesis" and "the locked architecture" as internal scaffolding shorthand, and flags first-person proximity language. While the exact string "the locked architecture" does not appear, the phrase "the architecture this dissertation presents" is a direct, unhedged self-referential framing that closely mirrors the prohibited category of internal scaffolding reference. More precisely, the rulebook prohibits "the locked architecture" as shorthand; this phrasing is a paraphrase of the same concept and in a literature review chapter should not self-reference the dissertation's own system design by name in a way that presupposes its architecture is settled.

**Recommended fix:** Rephrase to avoid direct self-reference: "...this is precisely the V2I-spoofing threat model that any SLM controller relying on connected-vehicle data feed must consider [CollusionVeh]." This removes the prohibited forward-reference to "the architecture this dissertation presents."

---

## Cross-checks performed

| Claim | Source verified against | Evidence |
|---|---|---|
| MPLight 2,510 intersections in Manhattan | papers/MPLight.pdf p.1 abstract | "2510 traffic lights in Manhattan, New York City" confirmed |
| MPLight ~13% travel-time reduction over Max-Pressure | papers/MPLight.pdf pp.1–5; RESCO.pdf p.4 related work | NOT directly confirmed in MPLight pp.1–5. RESCO attributes 19.2% to PressLight comparison, not Max-Pressure. Figure traced to traffic-llms.md registry synthesis entry only — see Issue 1 |
| FRAP 64×n^8 → 16×n^4 exploration reduction | papers/FRAP.pdf pp.3–5 (Section 4.4 Discussions) | Confirmed verbatim: "the model is required to observe only (2^2 × n^2) × (2^2 × n^2) = 16 × n^4 samples, a significant decrease in comparison with 64 × n^8 as in DRL" |
| RESCO reproduces MPLight ~11% gain over Max-Pressure | papers/RESCO.pdf p.4; traffic-llms.md registry | RESCO registry entry confirms "Reproduces MPLight ~11% gain over MP"; RESCO paper discusses MPLight in related work with 19.2% over PressLight — the 11% figure is in the registry synthesis, not confirmed in RESCO pp.1–5 read |
| CoLight first GAT-RL TSC on 196-int New York network | papers/CoLight.pdf pp.1–2 | Confirmed: "experiments on the simulator under different scales, including a real-world road network with about 200 intersections" (196-int Manhattan); "we are the first to use graph attentional network in the setting of reinforcement learning for traffic signal control" |
| Adv-XLight = Adv-CoLight = pre-LLM SOTA on Jinan/Hangzhou/NY | papers/Adv-XLight.pdf pp.1–2 | Confirmed: paper introduces "Advanced-CoLight" as achieving SOTA on standard benchmarks (Jinan, Hangzhou, NY datasets referenced) |
| CityLight: Manhattan (196), Chaoyang (97), Beijing (885 and 13,952), Jinan (3,930) | papers/CityLight.pdf pp.4–5 (§5.1.1) | Confirmed exactly: "Manhattan (196 intersections)… Chaoyang (97 intersections)… Central Beijing (885 intersections)… Jinan (3930 intersections)… Beijing (13952 intersections)" |
| CityLight beats Adv-CoLight and LLMLight at full-city scale via MAPPO | papers/CityLight.pdf p.1 abstract | Confirmed: "CityLight consistently outperforms both state-of-the-art universal policy models and individual policy methods, bringing an average 11.68% lift of the throughput" |
| MA2C: decentralised A2C on SUMO 5×5 grid and Monaco network | papers/MA2C-TSC.pdf p.1 abstract | Confirmed: "evaluated in both a large synthetic traffic grid and a large real-world traffic network of Monaco city" |
| SafeLight: near-zero collisions | papers/SafeLight.pdf p.1 (contributions) | Confirmed: "achieves over 99 percent reduction in collisions than the backbone RL model" |
| SafeLight throughput cost vs unconstrained baseline | papers/SafeLight.pdf pp.1–4 | NOT confirmed — paper claims mobility *improvement* vs Fixed-time; throughput cost vs unconstrained RL not explicitly stated in pp.1–4 reviewed — see Issue 3 |
| CFLight 93.1% collision reduction vs deep-Q baseline | papers/CFLight.pdf p.1 (contributions) | Confirmed verbatim: "achieving up to a 93.1% reduction in collision rates compared to 3DQN methods" |
| Adv-DRL-TSC: FGSM and black-box attacks raise queues; ensemble anomaly detector | registry.json entry | Registry entry confirms; PDF unavailable (not a valid PDF — HTML file stored at that path). Registry: "FGSM/black-box attacks substantially raise queues; ensemble anomaly detector lowest delay/false-alarm" — cross-referenced against traffic-llms.md synthesis |
| T-REX: sharp degradation under sensor faults; complex states more brittle | papers/T-REX.pdf pp.1–4 | Partially confirmed — T-REX confirms degradation under incidents; but "complex states more brittle" is not supported; hierarchical methods are *more* stable, not less — see Issue 2 |
| CollusionVeh: coordinated falsified V2X degrades policies; effect decreases as honest fleet grows | papers/CollusionVeh.pdf pp.1–4 | Confirmed: "the colluding effect will decrease if the number of colluding vehicles increases" and coordinated falsified V2X attacks confirmed |

---

## Tags audited

| Tag | Registry status | Cross-check status |
|---|---|---|
| MPLight | VERIFIED in registry | PDF pp.1–5 read; 13% figure not confirmed in pages read (numerical claim needs further verification in results section) |
| FRAP | VERIFIED in registry | PDF pp.1–5 read; exploration reduction 64×n^8 → 16×n^4 VERIFIED |
| RESCO | VERIFIED in registry | PDF pp.1–5 read; MPLight 11% figure confirmed in registry synthesis; RESCO pp.1–5 do not state this figure explicitly |
| CoLight | VERIFIED in registry | PDF pp.1–5 read; 196-int NY claim VERIFIED; first GAT-RL TSC VERIFIED |
| Adv-XLight | VERIFIED in registry | PDF pp.1–4 read; Adv-CoLight SOTA claim VERIFIED |
| CityLight | VERIFIED in registry | PDF pp.1–5 read; all network sizes VERIFIED |
| MA2C-TSC | VERIFIED in registry | PDF pp.1–4 read; 5×5 grid and Monaco VERIFIED |
| SafeLight | VERIFIED in registry | PDF pp.1–4 read; near-zero collision claim VERIFIED; throughput-cost claim WEAK_SUPPORT |
| CFLight | VERIFIED in registry | PDF pp.1–4 read; 93.1% collision reduction VERIFIED |
| Adv-DRL-TSC | VERIFIED in registry | PDF UNAVAILABLE (file is HTML, not valid PDF); claims cross-referenced via traffic-llms.md registry synthesis only |
| T-REX | VERIFIED in registry | PDF pp.1–4 read; degradation finding VERIFIED but directionality of brittleness claim is MISMATCHED — see Issue 2 |
| CollusionVeh | VERIFIED in registry | PDF pp.1–4 read; V2X falsification and fleet-size dependence VERIFIED |

---

## Additional notes (no issue flags required, for editor awareness)

**Word count:** The section comment states 1,291 words. This falls within the 1,000–1,440 permitted range (±20% of 1,200-word target). Compliant.

**Five sub-sections:** Present and correctly structured (2.3.1–2.3.5). Each sub-section contains at least one explicit limitation or weakness. Compliant.

**Closing land-on paragraph:** §2.3.5 names Max-Pressure, MPLight, CoLight, Adv-CoLight, MA2C, and RESCO as the comparison baselines. Compliant.

**Hedged-framing scan:** No instances of Traffic-R1, Iroha 2, Southampton/Minima drone, Google Project Green Light, Alibaba City Brain, Yunex FUSION, or NVIDIA Jetson Orin Nano benchmarks appear in §2.3. No HEDGE_VIOLATION issues.

**Prohibited-content scan (full):** No supervisor names, no "the student", no "Study Away", no "prompt1-" through "prompt8" scaffolding strings, no "the locked thesis", no "we/our/us" first-person plural, no marketing language ("powerful", "groundbreaking", "state-of-the-art", "cutting-edge"). One instance of "the architecture this dissertation presents" flagged as Issue 4 (borderline prohibited-content).

**Adv-DRL-TSC PDF status:** The file at `papers/Adv-DRL-TSC.pdf` is not a valid PDF (it appears to be an HTML file, as the read tool returned hex-character syntax errors indicating an HTML document). The claims attributed to [Adv-DRL-TSC] are consistent with the traffic-llms.md registry synthesis and the registry entry, but cannot be verified against a native PDF. This is not an issue with the drafted prose but should be noted for the evidence trail.
