#!/usr/bin/env python3
"""One-shot: add traffic-india.md entries to registry.json with their original short-tags."""
from __future__ import annotations
import json
from pathlib import Path

REG = Path(__file__).parent / "registry.json"
SOURCE_PROMPT = "prompt8-traffic-india"

# (tag, title, year, url, source_type, category, relevance)
# category 'a' = primary (statute/judgment/peer-reviewed/government policy/dataset release)
# category 'b' = supporting (operator report/journalism/legal commentary/working paper)
ENTRIES = [
    # Theme 1 — regulatory and constitutional anchors
    ("dpdpa-2023", "The Digital Personal Data Protection Act, 2023 (No. 22 of 2023) — Gazette of India", 2023,
     "https://egazette.gov.in/WriteReadData/2023/248045.pdf", "Statute", "a",
     "Defines 'digital personal data' and Data Fiduciary obligations governing CCTV/ANPR feeds in the equity-audit pipeline; Indian counterpart to UK GDPR's personal data definition."),
    ("dpdp-rules-gsr843-2025", "DPDP Rules 2025 — MeitY Gazette G.S.R. 843(E)/844(E)/845(E)/846(E), 13 Nov 2025", 2025,
     "https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf", "Statute", "a",
     "Phased calendar (DPB live 13 Nov 2025; Rules 3, 5–16 incl. cross-border transfer 13 May 2027) determines DPDPA enforceability over UK→India processing during dissertation timeline."),
    ("niti-rai-part1", "Responsible AI #AIForAll — Approach Document Part 1: Principles", 2021,
     "https://www.niti.gov.in/sites/default/files/2021-02/Responsible-AI-22022021.pdf", "Government policy", "a",
     "Codifies seven Indian RAI principles (Equality, Inclusivity & Non-Discrimination, Privacy & Security) derived from Articles 14/15 — doctrinal hook for fairness metrics."),
    ("niti-rai-part2", "Responsible AI #AIForAll — Part 2: Operationalising Principles", 2021,
     "https://www.niti.gov.in/sites/default/files/2021-08/Part2-Responsible-AI-12082021.pdf", "Government policy", "a",
     "Operationalises Part 1 principles via procurement, audits and sectoral regulators — closest Indian analogue to a public-sector AI-audit playbook for municipal traffic ITS."),
    ("meity-ai-advisory-mar2024", "MeitY Advisory on intermediary due-diligence / AI-content labelling, 15 Mar 2024", 2024,
     "https://www.meity.gov.in/writereaddata/files/Advisory%2015March%202024.pdf", "Government policy", "a",
     "Establishes labelling, bias/discrimination and electoral-integrity due-diligence duties for LLM-driven systems deployed in India — relevant to disclosure obligations of LLM-based equity audit tool."),
    ("dia-status-2026", "India to Regulate AI Under DPDPA, IP Laws, No Standalone AI Law — MediaNama", 2025,
     "https://www.medianama.com/2025/12/223-india-ai-law-digital-india-act-stalled/", "Journalism", "b",
     "Confirms Digital India Act draft remains unreleased as of December 2025; MeitY pivoting to non-binding India AI Governance Guidelines — caveat that DIA cannot be cited as live regulation."),
    ("constitution-india", "Constitution of India (Articles 14, 15, 16, 21 — Part III Fundamental Rights)", 1950,
     "https://www.indiacode.nic.in/bitstream/123456789/15240/1/constitution_of_india.pdf", "Statute", "a",
     "Articles 14/15/16/21 provide the constitutional yardstick for fairness audit of traffic-signal allocation across socio-economic groups."),
    ("puttaswamy-2017", "Justice K.S. Puttaswamy v. Union of India (Right to Privacy), (2017) 10 SCC 1", 2017,
     "https://main.sci.gov.in/supremecourt/2012/35071/35071_2012_Judgement_24-Aug-2017.pdf", "Judgment", "a",
     "Anchors informational privacy as Article 21 fundamental right; supplies proportionality test for CCTV/ANPR-based traffic-signal data processing."),
    ("puttaswamy-aadhaar-2018", "Justice K.S. Puttaswamy v. Union of India (Aadhaar), (2019) 1 SCC 1", 2018,
     "https://api.sci.gov.in/supremecourt/2012/35071/35071_2012_Judgement_26-Sep-2018.pdf", "Judgment", "a",
     "Applies Puttaswamy-I proportionality to large-scale state biometric/identification systems — analogous to municipal CCTV/ANPR ingestion at signalised intersections."),
    ("rajagopal-1994", "R. Rajagopal v. State of Tamil Nadu (Auto Shankar), (1994) 6 SCC 632", 1994,
     "https://digiscr.sci.gov.in/view_judgment?id=MjQ4NTY%3D", "Judgment", "a",
     "First SC articulation of an Article 21 'right to be let alone' grounding individual privacy claims against state surveillance imagery — precedent for DPDPA obligations on CCTV-derived personal data."),
    ("jpc-pdpb-report-2021", "Report of the Joint Parliamentary Committee on the PDP Bill, 2019 (16 Dec 2021)", 2021,
     "https://eparlib.nic.in/bitstream/123456789/835465/1/17_Joint_Committee_on_the_Personal_Data_Protection_Bill_2019_1.pdf", "Government policy", "a",
     "Documents legislative pre-history — sensitive-data categories, data-localisation drafting, JPC's rejection of EU adequacy — explaining why DPDPA 2023 dropped sensitive-data classification."),
    ("barandbench-dpdp-rules-2025", "MeitY notifies final Digital Personal Data Protection Rules 2025 — Bar and Bench", 2025,
     "https://www.barandbench.com/view-point/meity-notifies-final-digital-personal-data-protection-rules-2025", "Legal commentary", "b",
     "Confirms 13 May 2027 deadline for Rules 3, 5–16 (cross-border transfers, security safeguards, data-principal rights) — citation for DPDPA cross-border regime not enforceable during fieldwork."),
    ("prs-dpdp-bill-2023", "PRS Legislative Brief — The Digital Personal Data Protection Bill, 2023", 2023,
     "https://prsindia.org/billtrack/digital-personal-data-protection-bill-2023", "Legal commentary", "b",
     "Independent non-vendor summary mapping DPDPA 2023 against PDP Bill 2019 / JPC Report — single-page reference for DPDPA-vs-UK-GDPR comparison."),
    ("indconlawphil-blog", "Indian Constitutional Law and Philosophy blog (Gautam Bhatia) — DPDPA / surveillance / privacy posts", "2017-2025",
     "https://indconlawphil.wordpress.com/", "Legal commentary", "b",
     "Constitutionally grounded scholarly critique linking DPDPA s.8(7), Puttaswamy proportionality and over-broad state retention powers — critical lens for the dissertation's normative chapter."),

    # Theme 2 — algorithmic-fairness case studies
    ("dreze-khera-jharkhand-2017", "Aadhaar and Food Security in Jharkhand: Pain Without Gain? (Drèze, Khalid, Khera, Somanchi)", 2017,
     "https://www.epw.in/journal/2017/50/special-articles/aadhaar-and-food-security-jharkhand.html", "Peer-reviewed", "a",
     "Audit-methodology precedent (random village sampling + transaction-record reconciliation) for measuring algorithmic exclusion errors — transferable to traffic-signal access audits."),
    ("khera-aadhaar-welfare-2017", "Impact of Aadhaar on Welfare Programmes (Khera)", 2017,
     "https://www.epw.in/journal/2017/50/special-articles/impact-aadhaar-welfare-programmes.html", "Peer-reviewed", "a",
     "Establishes canonical Indian framing that opaque biometric/algorithmic gate-keeping becomes a 'tool of exclusion' — central to defining fairness harms in Indian public-service AI."),
    ("libtech-mgnrega-2024", "MGNREGA Implementation in India: Insights and Trends, Apr–Sep 2024 (LibTech India)", 2024,
     "https://libtech.in/wp-content/uploads/2024/10/India_Apr-Sep_2024.pdf", "Operator report", "b",
     "Reproducible field-audit template (RTI + MIS scraping + worker survey) quantifying ABPS/Aadhaar-driven deletions — methodological model for the equity audit."),
    ("iff-panoptic-tracker", "Project Panoptic — facial recognition tracker (Internet Freedom Foundation)", 2020,
     "https://panoptic.in/", "Operator report", "b",
     "Open dossier (120+ FRT tenders) with methodology for tracking algorithmic public-services in India incl. Telangana cluster relevant to caste/religion-disaggregated audit design."),
    ("iff-telangana-ec-2020", "Illegal use of Facial Recognition for Voter Verification in Telangana (IFF / Project Panoptic)", 2020,
     "https://internetfreedom.in/the-telangana-ec/", "Operator report", "b",
     "Documents 78% accuracy in a Telangana FRT pilot leading to rights-denial — precedent for treating low-accuracy algorithmic gating as Article 14 failure."),
    ("iff-delhi-frt-rti", "Is the illegal use of FRT by Delhi Police akin to mass surveillance? (IFF, RTI-based)", 2020,
     "https://internetfreedom.in/is-the-illegal-use-of-facial-recognition-technology-by-the-delhi-police-akin-to-mass-surveillance-you-decide-project-panoptic/", "Legal commentary", "b",
     "RTI exposé revealing Delhi Police FRT operating <1% accuracy with function creep — judicial-scrutiny precedent for demanding accuracy disclosure on public-sector AI."),
    ("vidhi-frt-delhi-2021", "The Use of Facial Recognition Technology for Policing in Delhi (Vipra, Vidhi)", 2021,
     "https://vidhilegalpolicy.in/research/the-use-of-facial-recognition-technology-for-policing-in-delhi/", "Working paper", "b",
     "Empirical spatial-statistics audit showing FRT disproportionately affects Muslims via uneven CCTV placement — India-context fairness definition for traffic-camera siting."),
    ("sambasivan-facct-2021", "Re-imagining Algorithmic Fairness in India and Beyond (Sambasivan et al.)", 2021,
     "https://arxiv.org/pdf/2101.09995", "Peer-reviewed", "a",
     "Foundational Indian-context fairness paper — caste, religion, class, Hijra/Adivasi sub-groups (not Western race/gender) drive fairness definitions; required anchor."),
    ("dreze-khera-bpl-2010", "The BPL Census and a Possible Alternative (Drèze & Khera)", 2010,
     "https://www.epw.in/journal/2010/9/special-articles/bpl-census-and-possible-alternative.html", "Peer-reviewed", "a",
     "Critique of SECC-2011-style proxy-means scoring — shows how multi-criterion algorithmic targeting misclassifies Adivasi/poor households; precedent for auditing rule-based eligibility logics."),
    ("garg-pmjay-bmc-2024", "AB-PMJAY after four years — utilisation, quality, financial protection (Garg et al.)", 2024,
     "https://pmc.ncbi.nlm.nih.gov/articles/PMC11321205/", "Peer-reviewed", "a",
     "Empirical evidence SECC-2011-driven algorithmic eligibility for PMJAY does not translate into financial protection (78% catastrophic-expenditure) — outcome-based audit precedent."),
    ("karusala-chi-2024", "Understanding Contestability on the Margins (Karusala, Upadhyay, Veeraraghavan, Gajos)", 2024,
     "https://dl.acm.org/doi/10.1145/3613904.3641898", "Peer-reviewed", "a",
     "Qualitative study of contestation against algorithmic land-ownership decisions in rural India — recourse-and-contestation criteria for traffic-signal AI redress."),
    ("amnesty-iff-banthescan-2021", "Ban the Scan: Hyderabad (Amnesty Intl. + IFF + ARTICLE 19)", 2021,
     "https://banthescan.amnesty.org/hyderabad/index.html", "Operator report", "b",
     "Geospatial audit (53–63% area CCTV coverage in two Hyderabad neighbourhoods) — methodology portable to mapping signal sensor coverage against caste/religion demographics."),

    # Theme 3 — Smart Cities Mission technical infrastructure
    ("uvh26-arxiv", "The Urban Vision Hackathon Dataset and Models: UVH-26 v1.0 (IISc)", 2025,
     "https://arxiv.org/pdf/2511.02563", "Working paper", "a",
     "UVH-26: 26,646 1080p Bengaluru Safe-City CCTV frames, 1.8M bboxes, 14 IRC vehicle classes; CC BY 4.0 dataset, faces blurred — usable under UK GDPR + DPDPA."),
    ("uvh26-hf", "UVH-26 dataset card (Hugging Face — iisc-aim/UVH-26)", 2025,
     "https://huggingface.co/datasets/iisc-aim/UVH-26", "Dataset release", "a",
     "Canonical CC BY 4.0 download with COCO JSON annotations; non-anonymised variants withheld — usable for dissertation with attribution and no re-identification attempt."),
    ("idd-2019", "IDD: A Dataset for Exploring Problems of Autonomous Navigation in Unconstrained Environments (Varma et al.)", 2019,
     "https://arxiv.org/pdf/1811.10200", "Peer-reviewed", "a",
     "Canonical India Driving Dataset (10,004 frames, 34 classes, Hyd/Blr dashcam); IIIT-H non-commercial licence; faces and plates not blurred — usable only with documented DPIA."),
    ("iddaw-wacv24", "IDD-AW: Benchmark for Safe and Robust Segmentation in Adverse Weather (Shaik et al.)", 2024,
     "https://openaccess.thecvf.com/content/WACV2024/papers/Shaik_IDD-AW_A_Benchmark_for_Safe_and_Robust_Segmentation_of_Drive_WACV_2024_paper.pdf", "Peer-reviewed", "a",
     "5,000 RGB+NIR frames in rain/fog/snow/low-light; IIIT-H non-commercial licence; unblurred faces/plates — MSc-usable only with DPIA + non-publication of raw frames."),
    ("iddx-cvprw24", "IDD-X: Multi-View Dataset for Ego-relative Important Object Localization (Parikh et al.)", 2024,
     "https://arxiv.org/pdf/2404.08561", "Peer-reviewed", "a",
     "Dual-view driving video dataset (697K bboxes, 3,634 scenarios, 19 explanation categories); IIIT-H non-commercial licence; conditionally usable with ethics review."),
    ("dats-2022", "DATS_2022: Versatile Indian Dataset for Object Detection in Unstructured Traffic (Paranjape & Naik)", 2022,
     "https://www.sciencedirect.com/science/article/pii/S2352340922006643", "Peer-reviewed", "a",
     "10,000+ Maharashtra (Pune) road-scene mobile-camera images, 45 classes; explicitly CC BY 4.0; unblurred faces/plates — usable with attribution and DPIA."),
    ("godl-india", "Government Open Data Licence – India (Gazette of India, OGDL)", 2017,
     "https://www.data.gov.in/sites/default/files/Gazette_Notification_OGDL.pdf", "Statute", "a",
     "GODL-India v1.0: worldwide royalty-free non-exclusive rights, attribution required, share-alike NOT required; §4 excludes personal information — covered datasets guaranteed not re-identifiable."),
    ("scodp-portal", "Smart Cities Open Data Portal (catalogue + GODL-India landing)", 2019,
     "https://smartcities.data.gov.in/government-open-data-license-india", "Government policy", "a",
     "Canonical entry point to 100-city catalogue (25 sectors, 75+ standard templates) under GODL-India v1.0; portal scope formally excludes personal data — usable with attribution."),
    ("iudx-whitepaper", "The India Urban Data Exchange: Rationale, Architecture and Methodology (IISc/MoHUA)", 2020,
     "https://iudx.org.in/portfolio/the-urban-data-exchange/", "Government policy", "a",
     "Canonical IUDX architecture (catalogue/consent/resource servers) covering Surat/Pune/Varanasi transit deployments — primary anchor for Indian smart-city data-exchange layer."),
    ("iudx-discussion-2018", "Data Exchange Framework for Indian Smart Cities (MoHUA/IISc)", 2018,
     "https://iudx.org.in/archives/Discussion_Paper-Data_Exchange_Framework_for_Indian_Smart_Cities.pdf", "Government policy", "a",
     "Foundational MoHUA/IISc paper specifying open APIs, data schemas and OSCI consortium model — citable provenance for IUDX's open-source vendor-neutral architecture."),
    ("dsc-strategy-2019", "DataSmart Cities: Empowering Cities through Data (MoHUA Smart Cities Mission)", 2019,
     "https://smartnet.niua.org/sites/default/files/resources/datasmart_cities.pdf", "Government policy", "a",
     "Defines People–Process–Platform pillars, MDO/CDO roles, and binding link to NDSAP/GODL — institutional anchor for the audit's who-publishes-what provenance chain."),
    ("scm-guidelines-2015", "Smart Cities Mission: Statement and Guidelines (MoHUA, June 2015)", 2015,
     "https://smartcities.gov.in/guidelines", "Government policy", "a",
     "Founding mission document (₹48,000 cr CSS, 100 cities, SPV model, Pan-City + ABD); legal/financial basis for ICCC and pan-city ITS deployments under audit."),
    ("iccc-maturity-2018", "ICCC Maturity Assessment Framework and Toolkit v1.0 (MoHUA/NIUA)", 2018,
     "https://smartnet.niua.org/sites/default/files/resources/iccc_maturity_assessment_framework_toolkit_vf211218.pdf", "Operator report", "b",
     "Canonical ICCC reference framework: functional/technological/governance use-cases incl. traffic surveillance, ANPR, signal control — system boundary for the LLM equity audit."),
    ("dmaf-cycle2-2021", "Data Maturity Assessment Framework Cycle 2 Report (MoHUA Smart Cities Mission)", 2021,
     "https://mohua.gov.in/dataSmartCities/uploads/resource/resourceDoc/Resource_Doc_1723188893_Data_Maturity_Assessment_Framework_(DMAF)_Cycle_2_Report.pdf", "Government policy", "a",
     "Operationalises CDO/CDA/CDP roles and reports city-level data-maturity scores; baseline for audit's data-availability findings."),

    # Theme 4 — urban transport equity research
    ("wri-blr-jobs-2024", "Jobs Near Metro Rail Transit in Bengaluru (Chanchani, Dhindaw, Palanichamy et al.)", 2024,
     "https://wri-india.org/sites/default/files/BloreJobsMetroPub-17th-Oct-online.pdf", "Operator report", "b",
     "Geospatial job-accessibility-to-transit baselines for Bengaluru incl. ORR/Marathahalli belt — equity demand layer for the corridor signal-equity audit."),
    ("wri-tmf-metro-2023", "Improving Metro Access in India: Evidence from Three Cities (WRI India–TMF)", 2023,
     "https://wri-india.org/sites/default/files/Improving%20metro%20access%20in%20India_%20Working%20Paper.pdf", "Operator report", "b",
     "Quantifies last-mile access inequity (gender, income) at Bengaluru metro stations — methodological template for stratifying signal-cycle wait costs by user group."),
    ("omi-eomi-2022", "Ease of Moving Index – India Report 2022 (OMI Foundation / Ola Mobility Institute)", 2023,
     "https://olawebcdn.com/ola-institute/easeofmoving-2022.pdf", "Operator report", "b",
     "Multi-city (incl. Bengaluru) inclusivity, walkability and pedestrian-infrastructure scores — benchmark for the audit's qualitative equity dimensions."),
    ("omi-eomi-2018", "Ease of Moving Index – India Report 2018 (Ola Mobility Institute)", 2018,
     "https://olawebcdn.com/ola-institute/ease-of-moving.pdf", "Operator report", "b",
     "Earliest pan-India equity/affordability/safety baseline enabling 2018→2022 trend triangulation for Bengaluru."),
    ("niti-mpi-2023", "National Multidimensional Poverty Index: A Progress Review 2023 (NITI/UNDP/OPHI)", 2023,
     "https://www.niti.gov.in/sites/default/files/2023-08/India-National-Multidimentional-Poverty-Index-2023.pdf", "Government policy", "a",
     "707-district MPI scores incl. Bengaluru Urban & Rural — anchors deprivation-weighting layer of the corridor equity audit (NITI MPI as IMD analogue)."),
    ("dult-cmp-2020", "Comprehensive Mobility Plan for Bengaluru, 2020 (DULT, Govt. of Karnataka)", 2020,
     "https://dult.karnataka.gov.in/assets/front/pdf/Comprehensive_Mobility_Plan.pdf", "Government policy", "a",
     "Official mode-share, OD and ORR-corridor traffic-volume data; defines BBMP/BMRCL signal-policy context for the secondary chapter."),
    ("iihs-urban-transport-2015", "Urban Transport in India: Challenges and Recommendations (IIHS, Mahadevia et al.)", 2015,
     "https://iihs.co.in/knowledge-gateway/wp-content/uploads/2015/07/RF-Working-Paper-Transport_edited_09062015_Final_reduced-size.pdf", "Working paper", "b",
     "IIHS canonical synthesis: pedestrians >40% of road fatalities in Bengaluru/Delhi/Kolkata — foundational equity framing for India-context anchors."),
    ("verma-mumbai-rawls-2026", "A Multidimensional Urban Transport Equity Assessment Framework: A Case of Mumbai (Cities)", 2026,
     "https://www.sciencedirect.com/science/article/abs/pii/S0264275125008066", "Peer-reviewed", "a",
     "Operationalises Rawlsian Difference Principle + Sen's Capability Approach in an Indian megacity — explicit Rawlsian triangulation target."),
    ("ghosh-blr-equity-2022", "Assessing Equity in Public Transportation in an Indian City (Case Studies on Transport Policy)", 2022,
     "https://www.sciencedirect.com/science/article/abs/pii/S2213624X22001948", "Peer-reviewed", "a",
     "Computes Public Transportation Accessibility Index vs Need Index across 198 BBMP wards — directly transferable equity-metric methodology for signal-audit."),
    ("bhatnagar-blr-affordability-2025", "Accessibility and Affordability of Public Transportation in an Indian Megacity (UPTR)", 2025,
     "https://www.tandfonline.com/doi/full/10.1080/29941849.2025.2449830", "Peer-reviewed", "a",
     "Bengaluru low/low-mid-income mode-choice modelling around metro — quantitative equity baseline for ORR–Marathahalli low-income worker commute."),
    ("joshi-intersectional-2021", "Intersectionality-based policy analysis: Equity in mobility in India (Transport Policy)", 2021,
     "https://www.sciencedirect.com/science/article/abs/pii/S0967070X20309276", "Peer-reviewed", "a",
     "Intersectional (gender × class × age) framing of Indian transport inequity — supports vulnerable-group weighting in the audit protocol."),
    ("gangopadhyay-mumbai-gini-2021", "Public Transit Accessibility for Healthcare in Greater Mumbai (J. Transp. Geogr.)", 2021,
     "https://www.sciencedirect.com/science/article/abs/pii/S0966692321001769", "Peer-reviewed", "a",
     "Uses Gini coefficient + Lorenz curves on Indian ward-level transit accessibility — explicit Gini triangulation target for India."),
    ("bbmp-wards-243-2022", "Delimitation of 243 Wards in BBMP – 2022 Notification", 2022,
     "https://bbmp.gov.in/ucc_file/BBMP-243-Wards.pdf", "Government policy", "a",
     "Authoritative BBMP ward boundary file (2022 reorganisation) — defines administrative units for ward-level exposure indices."),
    ("opencity-blr-signals", "Bengaluru City Traffic Police – Signal Timings Data (OpenCity / Civic Data Lab)", 2022,
     "https://data.opencity.in/dataset/bengaluru-city-traffic-signal-data", "Dataset release", "a",
     "Junction-level signal phase timings for ~12 Bengaluru junctions (BTP-sourced); only open BBMP/BTP-derived signal-timings input — implicit licence, attribution to BTP."),
    ("wri-blr-suraksha-2022", "Bengaluru Invests $128M in Building Safer Roads (Suraksha75, WRI)", 2022,
     "https://www.wri.org/outcomes/bengaluru-india-invests-128-million-building-safer-roads", "Operator report", "b",
     "Documents BBMP's 75-junction safety-redesign criteria (pedestrian volume, crash data) — working precedent for equity-weighted intersection prioritisation."),

    # Theme 5 — municipal AI traffic deployment claim verification
    ("keralacam-livelaw-2025", "V D Satheesan v State of Kerala, 2025 LiveLaw (Ker) 524 — LiveLaw report", 2025,
     "https://www.livelaw.in/high-court/kerala-high-court/kerala-high-court-privacy-concerns-ai-camera-installation-safe-kerala-project-302139", "Legal commentary", "a",
     "Authoritative judicial record of Safe Kerala's state architecture, NIC-server data flow and Keltron procurement — leading Indian precedent on automated traffic enforcement."),
    ("keralacam-barandbench-2023", "Mohanan VV v State of Kerala, 2023 LiveLaw (Ker) 287 — Bar and Bench report", 2023,
     "https://www.barandbench.com/news/cannot-discourage-installation-ai-traffic-cameras-allegations-lack-transparency-corruption-kerala-high-court", "Judgment", "a",
     "Establishes judicial framing AI traffic enforcement is 'innovative', not enjoinable on procurement/transparency allegations — frames equity-vs-innovation tension."),
    ("keralacam-southfirst-2024", "Kerala HC permits state to release 2nd Keltron instalment for AI cameras", 2024,
     "https://thesouthfirst.com/kerala/kerala-high-court-permits-state-government-to-release-2nd-instalment-to-keltron-for-ai-cameras/", "Journalism", "b",
     "Confirms procurement architecture: 726 cameras (675 AI-enabled), Rs 232 cr BOOT contract, Keltron–SRIT chain — strongest documented Indian deployment."),
    ("batcs-deccanherald-singh", "How Bengaluru rewired its traffic signals to beat gridlock — Op-ed by Police Comm. Seemant Kumar Singh", 2025,
     "https://www.deccanherald.com/opinion/how-bengaluru-rewired-its-traffic-signals-to-beat-gridlock-3832080", "Operator report", "b",
     "Police commissioner's own performance claim (>95% automation, <5% manual overrides) — primary operator data point for BATCS."),
    ("batcs-spotgenie-2025", "Bengaluru's Smart Signals: AI Traffic Control Cutting Commute Times — SpotGenie blog", 2025,
     "https://blog.spotgenie.in/bengalurus-ai-powered-smart-traffic-signals/", "Journalism", "b",
     "Documents 41 active junctions (plan to 165 by Jan 2026), 33% wait-time reduction and 18% throughput at Hudson Circle — best granular performance numbers, trade blog."),
    ("batcs-bs-moderato", "Bengaluru begins testing new adaptive Japanese traffic signal tech (MODERATO) — Business Standard", 2024,
     "https://www.business-standard.com/india-news/bengaluru-begins-testing-new-adaptive-japanese-traffic-signal-tech-moderato-124021300475_1.html", "Journalism", "b",
     "Documents parallel MODERATO system (28 junctions, JICA-funded, Nagoya Electric Works, ₹72 cr) — counter-narrative disambiguating BATCS from Bengaluru's other adaptive deployments."),
    ("surat-dmeo-iccc", "Surat ICCC Case Study (Development Monitoring & Evaluation Office, NITI Aayog)", 2021,
     "https://dmeo.gov.in/sites/default/files/2021-08/Package4_UrbanTransformation_CaseStudy14.pdf", "Government policy", "a",
     "Government-published case study on Surat ICCC — closest thing to an independent evaluation of an Indian ICCC traffic component."),
    ("surat-rfp-sscdl", "RFP for Selection of Implementing Agency for ICCC, Surat (SSCDL-ICCC-RFP-01-2019)", 2019,
     "https://www.suratsmartcity.com/Documents/Tenders/SSCDL_ICCC_AC1_2019.pdf", "Operator report", "b",
     "Primary procurement document detailing ATCS / ANPR / RLVD scope — Tier-2 evidence of what Surat actually contracted vs vendor marketing."),
    ("mumbai-dna-atc", "BMC to convert all manual traffic signals to ATC — DNA, citing senior BMC official", 2017,
     "https://www.dnaindia.com/mumbai/report-bmc-to-convert-all-manual-traffic-signals-in-city-to-atc-2561912", "Journalism", "b",
     "Concrete operator number — 253 of 613 Mumbai signals converted to ATC — anchors modest reality of 'AI' in BMC."),
    ("indore-fpj-itms", "Indore: Smart ITMS Comes Into Force at 14 Traffic Points — Free Press Journal", 2023,
     "https://www.freepressjournal.in/indore/indore-smart-itms-comes-into-force-at-14-traffic-points-in-city", "Journalism", "b",
     "Operator/officials' on-the-record numbers: ITMS at 14 of 50 planned junctions, integrated with NIC e-challan portal — supports cautious framing of Indore 'smart' claims."),
    ("hyderabad-trafficinfra", "Greater Hyderabad: Intelligent implementation of ITS — DSP Narsing Rao Motta interview", 2024,
     "https://trafficinfratech.com/greater-hyderabad-intelligent-implementation-of-its/", "Operator report", "b",
     "Hyderabad/Cyberabad ITMS data: average speed 19→25 km/h over 4 years, 86 lakh vehicle base — best operator numbers, no independent evaluation."),
    ("htrims-bel-2012", "Hyderabad Traffic Management System Overview (HTRIMS) — APTS / GHMC presentation", 2013,
     "https://www.scribd.com/document/118552367/HTRIMS", "Operator report", "b",
     "Original HTRIMS = ₹66.5 cr awarded to BEL in 2012 for 221 signals — directly contradicts 'TCS/NEC' attribution and corrects vendor mis-attribution risk."),
    ("delhi-transport-rfp", "Delhi Transport Department RFP — Implementation of AI Solutions in Transport Department", 2024,
     "https://transport.delhi.gov.in/transport/ai-project-transport-department", "Government policy", "a",
     "Demonstrates Delhi ITMS is at tender stage, not deployed — guards against propagating vendor pilot claims as performance baselines."),
]


def main() -> None:
    reg = json.loads(REG.read_text(encoding="utf-8"))
    existing_tags = {p["tag"] for p in reg["papers"]}
    existing_urls = {p["url"] for p in reg["papers"]}

    added = 0
    skipped_tag = 0
    skipped_url = 0
    for tag, title, year, url, source_type, category, relevance in ENTRIES:
        if tag in existing_tags:
            skipped_tag += 1
            print(f"  SKIP (tag exists)  {tag}")
            continue
        if url in existing_urls:
            skipped_url += 1
            print(f"  SKIP (url exists)  {tag} -> {url}")
            continue
        reg["papers"].append({
            "tag": tag,
            "title": title,
            "year": year,
            "url": url,
            "source_prompt": SOURCE_PROMPT,
            "source_type": source_type,
            "category": category,
            "relevance": relevance,
            "status": "pending",
            "filename": None,
            "size_bytes": None,
            "sha256": None,
            "http_status": None,
            "downloaded_at": None,
            "error": None,
        })
        existing_tags.add(tag)
        existing_urls.add(url)
        added += 1
        print(f"  +  {tag:35s} {url}")

    REG.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nadded {added}; skipped {skipped_tag} (tag), {skipped_url} (url); total entries now {len(reg['papers'])}")


if __name__ == "__main__":
    main()
