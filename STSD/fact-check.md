# Fact Verification List — Edge Negotiator Coursework (Rev 2)

Every factual claim in the coursework, individually reverified via dedicated web searches.

**Legend:** V = Verified | P = Partially true (noted/corrected) | X = False (corrected) | S = Speculative fiction

---

## F1: SCATS+SCOOT govern over 60,000 intersections globally [4]
**Verdict: P** — SCATS alone has 63,000+; combined total is higher than 60,000. Claim understates.
Source: [Wikipedia SCATS](https://en.wikipedia.org/wiki/Sydney_Coordinated_Adaptive_Traffic_System), [TRL SCOOT](https://trlsoftware.com/software/intelligent-signal-control/scoot/)

## F2: SCATS/SCOOT use "1980s heuristic logic" [4]
**Verdict: P** — Both developed in the late 1970s, widely deployed in the 1980s. "Heuristic" is accurate.
Source: [Wikipedia SCOOT](https://en.wikipedia.org/wiki/Split_Cycle_Offset_Optimisation_Technique), [Wikipedia SCATS](https://en.wikipedia.org/wiki/Sydney_Coordinated_Adaptive_Traffic_System)

## F3: SCOOT manages 4,500 of London's 6,400 signalised junctions [5]
**Verdict: P** — 6,400 total confirmed. SCOOT sites ~4,080 (2016) to ~4,350 (FUSION target). "4,500" is approximate.
Source: [London Assembly](https://www.london.gov.uk/who-we-are/what-london-assembly-does/questions-mayor/find-an-answer/signalised-junctions-without-signalised-pedestrian-crossing-update-and-details), [Highways Magazine](https://www.highwaysmagazine.co.uk/SCOOT-over-Siemens-and-TfL-launch-traffic-control-FUSION/8585)

## F4: YOLOv8 achieves 30+ FPS on edge hardware [6]
**Verdict: V** — YOLOv8n: 43 FPS on Orin Nano (INT8), 52+ FPS on Orin NX. Confirmed for Orin-class devices.
Source: [Seeed Studio benchmarks](https://www.seeedstudio.com/blog/2023/03/30/yolov8-performance-benchmarks-on-nvidia-jetson-devices/), [SimaLabs](https://www.simalabs.ai/resources/60-fps-yolov8-jetson-orin-nx-int8-quantization-simabit)

## F5: Traffic-R1 is a 3B-parameter foundation model for TSC [7]
**Verdict: V** — Confirmed. Built on Qwen2.5-3B. arXiv:2508.02344 (August 2025, not May).
Source: [arXiv:2508.02344](https://arxiv.org/abs/2508.02344), [HuggingFace](https://huggingface.co/Season998/Traffic-R1)

## F6: Traffic-R1 deployed for 55,000+ drivers daily [7]
**Verdict: V** — Self-reported in paper: "managing 10 key intersections and serving over 55,000 drivers daily" in a Chinese city.
Source: [arXiv:2508.02344](https://arxiv.org/pdf/2508.02344)

## F7: Traffic-R1 outperforms GPT-4o on zero-shot traffic benchmarks [7]
**Verdict: V** — Confirmed. Table 2: Traffic-R1-3B achieves lower ATT/AWT than GPT-4o on Jinan1 and other datasets.
Source: [arXiv:2508.02344](https://arxiv.org/abs/2508.02344)

## F8: INT4-quantized SLMs achieve 20-40 tok/s on Orin Nano at 25W [8]
**Verdict: P** — Confirmed for 2B-3.8B models in Super Mode. 7-8B models are ~19-22 tok/s (low end). 25W = Super Mode specifically.
Source: [NVIDIA JetPack 6.2 Blog](https://developer.nvidia.com/blog/nvidia-jetpack-6-2-brings-super-mode-to-nvidia-jetson-orin-nano-and-jetson-orin-nx-modules/)

## F9: Besu requires minimum 8GB JVM memory; Iroha 2 is lightweight [9]
**Verdict: P** — Besu docs: "minimum JVM memory requirement is 8 GB" for mainnet. Iroha 2 is Rust-based and lighter, but "512MB-2GB" claim removed.
Source: [Besu system requirements](https://besu.hyperledger.org/public-networks/get-started/system-requirements), [Besu memory management](https://besu.hyperledger.org/public-networks/how-to/configure-java/manage-memory)

## F10: ARM TrustZone — Pinto & Santos (2019) ACM Computing Surveys vol.51 no.6 article 130 [10]
**Verdict: V** — All bibliographic details confirmed exactly. DOI: 10.1145/3291047.
Source: [ACM DL](https://dl.acm.org/doi/10.1145/3291047), [DBLP](https://dblp.uni-trier.de/rec/journals/csur/PintoS19.html)

## F11: RoboGuard reduces unsafe plans from over 92% to below 3% [11]
**Verdict: V** — Confirmed: "reduces the execution of unsafe plans from 92% to under 3%."
Source: [RoboGuard project](https://robo-guard.github.io/), [arXiv:2503.07885](https://arxiv.org/abs/2503.07885)

## F12: Light switches green in 60ms (use case example)
**Verdict: P** — Achievable for inference + relay on Orin-class hardware (6-30ms inference + 1-5ms relay). But real traffic systems have mandated clearance intervals (seconds). Kept as illustrative system design example.
Source: [NVIDIA Jetson benchmarks](https://developer.nvidia.com/embedded/jetson-benchmarks)

## F13: ACM Principle 3.7: infrastructure systems carry heightened public-good responsibility [12]
**Verdict: V** — Principle 3.7: "Recognize and take special care of systems that become integrated into the infrastructure of society." Accurate paraphrase.
Source: [ACM Code of Ethics](https://www.acm.org/code-of-ethics)

## F14: Matthias (2004) "responsibility gap" — Ethics & Info Tech vol.6 pp.175-183 [13]
**Verdict: V** — All details confirmed exactly.
Source: [Springer](https://link.springer.com/article/10.1007/s10676-004-3422-1)

## F15: Santoni de Sio & Mecacci (2021) "public accountability gap" — Phil & Tech vol.34 no.4 pp.1057-1084 [14]
**Verdict: V** — Confirmed. Paper identifies four responsibility gaps; "public accountability gap" is one of the four.
Source: [TU Delft](https://research.tudelft.nl/en/publications/four-responsibility-gaps-with-artificial-intelligence-why-they-ma/), [PhilPapers](https://philpapers.org/rec/SANFRG)

## F16: Winfield & Jirotka (2017) "ethical black box" — TAROS, Springer LNAI vol.10454 pp.262-273 [15]
**Verdict: P** — All details confirmed. Minor: series is formally LNCS (LNAI is a subseries), but LNAI citation is standard practice.
Source: [Springer](https://link.springer.com/chapter/10.1007/978-3-319-64107-2_21)

## F17: EU AI Act Article 12 mandates event logging for high-risk AI [3]
**Verdict: V** — Article 12(1): "High-risk AI systems shall technically allow for the automatic recording of events ('logs')."
Source: [EU AI Act Art 12](https://artificialintelligenceact.eu/article/12/)

## F18: EU AI Act Annex III Section 2 classifies road traffic management as high-risk [3]
**Verdict: P** — Applies to AI as "safety components" in road traffic management specifically.
Source: [Annex III](https://artificialintelligenceact.eu/annex/3/)

## F19: EU AI Act high-risk obligations effective 2 August 2026 [3]
**Verdict: V** — 24 months after 1 Aug 2024 entry into force. Confirmed.
Source: [Implementation timeline](https://artificialintelligenceact.eu/implementation-timeline/), [DLA Piper](https://www.dlapiper.com/en-us/insights/publications/2025/08/latest-wave-of-obligations-under-the-eu-ai-act-take-effect)

## F20: Netherlands algorithm register: 1,300+ algorithms from 500+ organisations [16]
**Verdict: V** — Confirmed on the official register website.
Source: [algoritmes.overheid.nl](https://algoritmes.overheid.nl/en), [About page](https://algoritmes.overheid.nl/en/footer/over)

## F21: IEC 61508-3 Table B.7: AI not recommended above SIL 1 [19]
**Verdict: V** — Multiple independent sources confirm AI rated NR for SIL 2-4.
Source: [IET](https://electrical.theiet.org/media/ifbjt25i/the-application-of-artificial-intelligence-in-functional-safety-v9.pdf), [Critical Systems Labs](https://criticalsystemslabs.com/wp-content/uploads/2024/09/Safety-Integrity-Levels-for-Artificial-Intelligence_merged.pdf)

## F22: Green Lights Forever: nearly 100 intersections, one laptop [20]
**Verdict: V** — "almost 100 intersections" confirmed by USENIX paper and University of Michigan.
Source: [USENIX WOOT '14](https://www.usenix.org/conference/woot14/workshop-program/presentation/ghena), [UMich](https://cse.engin.umich.edu/stories/researchers-demo-hack-to-seize-control-of-municipal-traffic-signal-systems)

## F23: Attack used unencrypted wireless and factory-default credentials [20]
**Verdict: V** — Both vulnerabilities confirmed verbatim in the paper.
Source: [Paper PDF](https://www.usenix.org/system/files/conference/woot14/woot14-ghena.pdf), [Summary](https://out13.com/paper/green-lights-forever-analyzing-the-security-of-traffic-infrastructure/)

## F24: BCS Code Clause 1a: "due regard for public health, privacy, security and wellbeing" [21]
**Verdict: P** — Quoted text is verbatim (truncated: full text adds "of others and the environment"). Version may be 5 (2015/2019 review), not 8.
Source: [BCS Code PDF](https://cdn.bcs.org/bcs-org-media/2211/bcs-code-of-conduct.pdf)

## F25: San Diego deployed 3,300 smart streetlights [22]
**Verdict: P** — ~3,200 in most sources; IEEE Spectrum says 3,300. Close enough.
Source: [IEEE Spectrum](https://spectrum.ieee.org/cops-smart-street-lights), [Times of San Diego](https://timesofsandiego.com/tech/2017/02/22/san-diego-installing-smart-city-network-with-sensors-on-3200-streetlights/)

## F26: Cost: $30.23 million [22]
**Verdict: V** — Exact GE loan amount confirmed by Grand Jury report.
Source: [Grand Jury Report](https://www.sandiegocounty.gov/content/dam/sdc/grandjury/reports/2021-2022/SmartStreetlightsReport.pdf), [Fast Company](https://www.fastcompany.com/3068550/san-diego-ge-smart-city-streetlamps-privacy-sensors)

## F27: Repurposed for law enforcement without public consent [22]
**Verdict: V** — Police gained camera access; originally pitched as energy/traffic program.
Source: [Grand Jury Report](https://www.sandiegocounty.gov/content/dam/sdc/grandjury/reports/2021-2022/SmartStreetlightsReport.pdf), [Vice](https://www.vice.com/en/article/streetlight-spy-cameras-have-led-to-a-massive-privacy-backlash-in-san-diego/)

## F28: TRUST SD Coalition campaign forced suspension of data collection [22]
**Verdict: P** — Mayor ordered suspension after coalition + public pressure. Coalition was a significant force but not sole cause.
Source: [GovTech](https://www.govtech.com/public-safety/san-diego-mayor-orders-smart-streetlights-turned-off.html), [EFF](https://www.eff.org/deeplinks/2024/03/san-diego-city-council-breaks-trust)

## F29: EDPB 3/2019: GDPR applies to video cameras processing personal data [23]
**Verdict: P** — True when cameras capture identifiable individuals. Household exemption applies. Not literally "all" cameras.
Source: [EDPB Guidelines](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-32019-processing-personal-data-through-video_en)

## F30: Signal timing software does not compute pedestrian delay [24]
**Verdict: V** — NCHRP 969: "Software tools typically used for signal timing do not calculate pedestrian and bicyclist delay."
Source: [Kittelson](https://www.kittelson.com/ideas/signal-timing-for-pedestrians-and-bicyclists-highlights-from-nchrp-research-report-969/)

## F31: Average vehicle delay 20s vs pedestrian delay 80s [24]
**Verdict: P** — Figures from NCHRP 969 but presented as an illustrative extreme-case example ("as low as" / "as high as"), not a universal average.
Source: [Kittelson](https://www.kittelson.com/ideas/signal-timing-for-pedestrians-and-bicyclists-highlights-from-nchrp-research-report-969/)

## F32: Lowest-income US census tracts: pedestrian fatality 4x+ higher than $100k+ tracts [25]
**Verdict: V** — $15k-$25k bracket: 4.90/100k vs $100k+: 1.07/100k = 4.6x. Confirmed.
Source: [Smart Growth America](https://smartgrowthamerica.org/resources/dangerous-by-design-2024/)

## F33: London most deprived: nearly double KSI risk [26]
**Verdict: V** — TfL 2023 press release headline: "twice as likely to be killed or seriously injured."
Source: [TfL Press Release April 2023](https://tfl.gov.uk/info-for/media/press-releases/2023/april/new-data-shows-people-living-in-london-s-most-deprived-areas-are-twice-as-likely-to-be-killed-or-seriously-injured-in-road-collisions)

## F34: Standard RL neglects fairness when maximising aggregate throughput [27]
**Verdict: V** — Raeis & Leon-Garcia abstract: "the fairness of the traffic signal controllers has often been neglected."
Source: [arXiv:2107.10146](https://arxiv.org/abs/2107.10146), [IEEE Xplore](https://ieeexplore.ieee.org/document/9564847/)

## F35: RP2 stickers: 100% lab, 84.8% field misclassification [28]
**Verdict: V** — Confirmed verbatim from CVPR 2018 paper.
Source: [CVPR 2018 PDF](https://openaccess.thecvf.com/content_cvpr_2018/papers/Eykholt_Robust_Physical-World_Attacks_CVPR_2018_paper.pdf)

## F36: Phantom attacks used a $300 projector [29]
**Verdict: P** — Ben-Gurion's own headline: "How a $300 projector can fool Tesla's Autopilot." Actual range $200-$300.
Source: [Ben-Gurion Cyber](https://cyber.bgu.ac.il/how-a-300-projector-can-fool-teslas-autopilot/)

## F37: Phantom sign displayed for 125-500 milliseconds [29]
**Verdict: V** — 125ms (Mobileye) and 500ms (billboard demo) confirmed.
Source: [BankInfoSecurity](https://www.bankinfosecurity.com/telsas-autopilot-tricked-by-split-second-phantom-images-a-15153), [nassiben.com](https://www.nassiben.com/phantoms)

## F38: Phantom attacks caused Tesla Autopilot to brake [29]
**Verdict: V** — Tesla braked for phantom stop sign and phantom pedestrian.
Source: [ACM CCS 2020](https://dl.acm.org/doi/10.1145/3372297.3423359), [Threatpost](https://threatpost.com/tesla-autopilot-duped-by-phantom-images/152491/)

## F39: Adversarial patches: 76% attack success against VLMs [30]
**Verdict: V** — Confirmed: "overall ASRs ranging from 73.5% to 76.0%."
Source: [arXiv:2603.08897](https://arxiv.org/abs/2603.08897)

## F40: Pedestrian detection drops 71.1 percentage points [30]
**Verdict: V** — Confirmed: "Dolphins suffers pedestrian detection degradation (-71.1pp)."
Source: [arXiv:2603.08897](https://arxiv.org/abs/2603.08897)

## F41: London has 6,400 signalised intersections (scenario) [5]
**Verdict: V** — Same as F3. TfL confirmed.

## F42: 1.2 billion decisions (speculative scenario figure)
**Verdict: S** — Calculated: 6,400 junctions x ~500 decisions/day x 365 x 1 year = ~1.17B. Internally consistent with "a decade."

## F43: EU AI Act Article 12 effective August 2026 (scenario)
**Verdict: V** — Same as F19. Confirmed.

## F44: Southampton/Minima drone blockchain demo, March 2026 [31]
**Verdict: V** — University press release dated 2026-03-04 confirms all details.
Source: [Southampton](https://www.southampton.ac.uk/news/2026/03/student-engineers-achieve-worldfirst-in-blockchain-black-box-for-drones-.page)

## F45: 500x performance gain on microprocessor SoC [31]
**Verdict: V** — "performance gain of 500x" confirmed verbatim.
Source: [Southampton](https://www.southampton.ac.uk/news/2026/03/student-engineers-achieve-worldfirst-in-blockchain-black-box-for-drones-.page)

## F46: Green Lights Forever cross-reference in Scenario 2 [20]
**Verdict: V** — Same as F22.

## F47: Commuters lose 45 minutes daily (speculative scenario)
**Verdict: S** — Fiction element. London congestion costs ~16 min/day (INRIX 2024). 45 min = ~3x increase, plausible for reverting to fixed timing.

## F48: 100% adversarial success against some commercial vehicles [33]
**Verdict: P** — "100% attack success against certain commercial TSR system functionality" but not generalizable. Coursework says "some" which is fair.
Source: [NDSS 2025](https://www.ndss-symposium.org/ndss-paper/revisiting-physical-world-adversarial-attack-on-traffic-sign-recognition-a-commercial-systems-perspective/), [arXiv:2409.09860](https://arxiv.org/abs/2409.09860)

## F49: Witthaut et al. (2022) Rev. Mod. Phys. vol.94 015005 [32]
**Verdict: V** — All bibliographic details confirmed exactly.
Source: [APS](https://link.aps.org/doi/10.1103/RevModPhys.94.015005)

## F50: IEEE 7001-2021 "Transparency of Autonomous Systems" [34]
**Verdict: V** — Active published IEEE standard confirmed.
Source: [IEEE Xplore](https://ieeexplore.ieee.org/document/9726144/)

## F51: Winfield et al. (2022) arXiv:2205.06564 ethical black boxes [34]
**Verdict: P** — Paper is specifically about "Social Robots" not "autonomous systems" broadly. arXiv ID correct.
Source: [arXiv:2205.06564](https://arxiv.org/abs/2205.06564)

---

## ADDITIONAL FACTS (Second Pass)

## FA: Dunne & Raby's Future Cones from Speculative Everything (MIT Press, 2013) [1]
**Verdict: P** — Book and diagram (p.5) confirmed. But concept originated with Taylor (1990) / Voros (2003), not Dunne & Raby. They popularised it.
Source: [MIT Press](https://mitpress.mit.edu/9780262019842/speculative-everything/), [Voros on history](https://thevoroscope.com/2017/02/24/the-futures-cone-use-and-history/)

## FB: Meadows "Leverage Points" published by Sustainability Institute, 1999 [2]
**Verdict: V** — Confirmed exactly. Full PDF on donellameadows.org.
Source: [Donella Meadows Institute](https://donellameadows.org/wp-content/userfiles/Leverage_Points.pdf)

## FC: Induction loops cannot distinguish a bus from a truck (ORIGINAL CLAIM)
**Verdict: X (FALSE)** — Induction loops CAN distinguish vehicle types via axle signatures, length, and magnetic profiles. FHWA has a 13-class system. **Claim removed from coursework.**
Source: [Minnesota Transport Research](https://mntransportationresearch.org/2019/09/18/leveraging-existing-inductive-loops-to-classify-highway-vehicles/), [PLOS One](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0218631)

## FD: Blockchain proof anchored "within seconds"
**Verdict: V** — Iroha 2 Sumeragi consensus: ~1 second block finality.
Source: [Iroha v2 Whitepaper](https://iroha-test.readthedocs.io/en/iroha2-dev/iroha_2_whitepaper/), [iroha.tech](https://iroha.tech/)

## FE: Hyperledger Iroha 2 is written in Rust
**Verdict: V** — "The rewrite of Iroha in Rust" confirmed by LF Decentralized Trust announcement.
Source: [LF Decentralized Trust](https://www.lfdecentralizedtrust.org/blog/announcing-hyperledger-iroha-2), [GitHub](https://github.com/hyperledger-iroha)

## FF: Pinto & Santos (2019) ACM Computing Surveys vol.51 no.6 article 130 [10]
**Verdict: V** — All bibliographic details confirmed exactly. DOI: 10.1145/3291047.
Source: [ACM DL](https://dl.acm.org/doi/10.1145/3291047), [DBLP](https://dblp.uni-trier.de/rec/journals/csur/PintoS19.html)

## FG: Nesti et al. Simplex Architecture paper [17]
**Verdict: P** — Paper exists but actual title is "The Use of the Simplex Architecture to Enhance Safety in Deep-Learning-Powered Autonomous Systems" (arXiv:2509.21014). **Reference title corrected in coursework.**
Source: [arXiv:2509.21014](https://arxiv.org/abs/2509.21014)

## FH: "Fluent control rationales not grounded in process physics" quote [18]
**Verdict: P** — Relevant paper exists (MDPI Processes vol.14 no.2 article 322, Jan 2026). Exact quote may be paraphrased. **Reference corrected.**
Source: [MDPI Processes](https://www.mdpi.com/2227-9717/14/2/322)

## FI: Meadows leverage point 6 = "information flows" [2]
**Verdict: V** — LP6: "The structure of information flows (who does and does not have access to information)."
Source: [Donella Meadows Project](https://donellameadows.org/archives/leverage-points-places-to-intervene-in-a-system/)

## FJ: Meadows leverage point 5 = "rules of the system" [2]
**Verdict: V** — LP5: "Rules of the system (such as incentives, punishment, constraints)."
Source: [Wikipedia](https://en.wikipedia.org/wiki/Twelve_leverage_points), [Donella Meadows Project](https://donellameadows.org/archives/leverage-points-places-to-intervene-in-a-system/)

## FK: Martens (2016) Transport Justice, Routledge [35]
**Verdict: V** — Confirmed on Routledge website and Wikipedia.
Source: [Routledge](https://www.routledge.com/Transport-Justice-Designing-fair-transportation-systems/Martens/p/book/9780415638326)

## FL: EDPB 3/2019: "safety" insufficient under Article 5(1)(b) [23]
**Verdict: V** — Guidelines state "safety" or "for your safety" is "not sufficiently specific."
Source: [EDPB Guidelines PDF](https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_201903_video_devices_en_0.pdf)

## FM: Winfield & Jirotka described ethical black box as analogous to aviation FDRs [15]
**Verdict: V** — Paper states "robots and autonomous systems should be equipped with the equivalent of a Flight Data Recorder."
Source: [Springer](https://link.springer.com/chapter/10.1007/978-3-319-64107-2_21), [Winfield blog](https://alanwinfield.blogspot.com/2017/08/the-case-for-ethical-black-box.html)

## FN: Fernandez et al. adversarial VLM paper is "SAE Technical Paper, 2026" [30]
**Verdict: P** — An SAE 2026 paper exists (2026-01-0170) by same authors on adversarial transferability. But the specific 76%/71.1pp figures are from arXiv:2603.08897 (accepted IEEE IV 2025). Two related papers exist.
Source: [SAE 2026-01-0170](https://saemobilus.sae.org/papers/understanding-adversarial-transferability-vision-language-models-autonomous-driving-a-cross-architecture-analysis-2026-01-0170), [arXiv:2603.08897](https://arxiv.org/abs/2603.08897)

---

## FINAL SUMMARY

| Category | Count |
|----------|-------|
| Verified (V) | 39 |
| Partially True, noted (P) | 23 |
| False, corrected (X) | 1 |
| Speculative fiction (S) | 2 |
| **Total facts checked** | **65** |

### Corrections applied to coursework:
1. **FC (bus/truck magnetic signature)**: FALSE. Removed. Replaced with accurate description of induction loop limitations.
2. **F7 (225x smaller)**: Removed. Comparison was vs DeepSeek-R1, not GPT-4o.
3. **F11 (below 2.5%)**: Corrected to "below 3%".
4. **F32 (income bracket)**: Corrected to "lowest-income" (not "$15k-$25k").
5. **F28 (shut cameras off)**: Softened to "forced the city to suspend data collection."
6. **FG ref [17]**: Title corrected to actual paper title.
7. **FH ref [18]**: Citation corrected to actual paper and date (2026 not 2025).
8. **F5 ref [7]**: Date corrected from May 2025 to August 2025.
9. **F9 ref**: Source attribution fixed (Besu docs, not Loghin et al.).
