# Ethical frameworks for autonomous public IoT infrastructure: a literature survey

**Autonomous IoT systems deployed in public infrastructure — smart traffic signals, sensor networks, edge computing nodes — sit at the intersection of at least five unresolved scholarly debates**: professional accountability without a single developer, algorithmic fairness in life-affecting transport decisions, the power of speculative design to surface tensions before deployment, the surveillance-optimisation paradox, and the environmental cost of the hardware itself. This survey synthesises **~60 sources across these five vectors**, prioritising 2020–2025 peer-reviewed publications while including seminal earlier works. The literature reveals a consistent finding: existing governance frameworks were designed for centralised, human-controlled systems and break down when applied to decentralised, adaptive, sensor-driven public infrastructure. Each vector surfaces a different dimension of this breakdown — and together they define the research frontier for responsible autonomous infrastructure.

---

## 1. Professional codes of ethics struggle with decentralised autonomy

Three foundational professional codes govern computing practice, yet all were architected around identifiable human practitioners making discrete design decisions — an assumption that dissolves in decentralised IoT.

### Foundational codes

**IEEE Global Initiative on Ethics of Autonomous and Intelligent Systems** (2019). *Ethically Aligned Design: A Vision for Prioritizing Human Well-being with Autonomous and Intelligent Systems, First Edition*. IEEE Standards Association. Over 700 contributors produced the most comprehensive treatise on A/IS ethics, articulating principles including human well-being as the primary success criterion, discoverability of decision basis, and guarding against misuse. The companion **IEEE P7000 series** translates these into technical standards. Directly applicable to IoT sensor systems: the framework requires transparent, accountable decision-making in critical infrastructure, but its implementation guidance assumes a coherent development organisation.

**ACM Committee on Professional Ethics** — Gotterbarn, Don; Brinkman, Bo; Flick, Catherine; Kirkpatrick, Michael; Miller, Keith; Varanasi, Kate; Wolf, Marty J. (2018). *ACM Code of Ethics and Professional Conduct*. Association for Computing Machinery. The 2018 revision explicitly addresses modern IoT: **Principle 3.7 mandates that systems becoming infrastructure carry heightened responsibility for the public good**, and Principle 1.2 requires analysis of "consequences of data aggregation and emergent properties of systems." This infrastructure clause is the most directly relevant provision for autonomous public sensor networks, though it still addresses individual professionals rather than distributed development ecosystems.

**BCS, The Chartered Institute for IT** (current edition). *BCS Code of Conduct*. Structured around four duties — Public Interest, Relevant Authority, the Profession, and Professional Competence — the code requires members to "have due regard for public health, privacy, security and wellbeing of others and the environment." Its public interest mandate applies to IoT infrastructure, but like the ACM and IEEE codes, it addresses individual practitioners rather than distributed autonomous systems with no single accountable developer.

### The responsibility gap in autonomous systems

**Matthias, Andreas** (2004). "The Responsibility Gap: Ascribing Responsibility for the Actions of Learning Automata." *Ethics and Information Technology*, 6, 175–183. This seminal paper established that when autonomous, learning machines behave unpredictably, **traditional responsibility ascription breaks down entirely**. Society faces a choice between abandoning such machines or accepting an unbridgeable accountability vacuum. Foundational for understanding why professional codes struggle with adaptive IoT sensor networks.

**Santoni de Sio, Filippo; Mecacci, Giulio** (2021). "Four Responsibility Gaps with Artificial Intelligence: Why They Matter and How to Address Them." *Philosophy & Technology*, 34(4), 1057–1084. Expands Matthias's single gap into four interconnected problems: culpability gaps, moral accountability gaps, **public accountability gaps**, and active responsibility gaps. The public accountability gap — where citizens cannot obtain explanations for algorithmic decisions affecting public services — is especially pertinent for smart city infrastructure.

**Goetze, Trystan S.** (2022). "Mind the Gap: Autonomous Systems, the Responsibility Gap, and Moral Entanglement." *ACM FAccT '22*, Seoul. Directly evaluates professional codes (ACM, IEEE) as solutions to the responsibility gap and finds them to be "workarounds rather than genuine philosophical solutions." Proposes **moral entanglement via vicarious responsibility** — computing professionals are ethically required to take responsibility despite not being directly blameworthy. This reframing is critical for distributed IoT systems where responsibility diffuses across hardware vendors, algorithm designers, municipal operators, and data processors.

**Vallor, Shannon; Vierkant, Tillmann** (2024). "Find the Gap: AI, Responsible Agency and Vulnerability." *Minds and Machines*, 34(3), article 20. Offers a novel diagnosis: the real responsibility gap stems from a **"vulnerability gap"** — a structural asymmetry between human agents and sociotechnical systems. AI technologies contribute to "agency disintegration," fragmenting formerly coherent processes. This concept maps directly onto decentralised IoT networks where no single developer controls system behaviour.

### Smart city ethics and IoT governance

**Ziosi, Marta; Hewitt, Benjamin; Juneja, Prathm; Taddeo, Mariarosaria; Floridi, Luciano** (2022). "Smart Cities: Reviewing the Debate About Their Ethical Implications." *AI & Society* (Springer). Identifies four ethical dimensions of smart cities: network infrastructure (control, surveillance, data ownership), post-political governance, social inclusion, and sustainability. Provides the ethical landscape within which professional codes must operate.

**Kitchin, Rob** (2016). "The Ethics of Smart Cities and Urban Science." *Philosophical Transactions of the Royal Society A*, 374, 20160115. Directly calls for professional bodies including BCS, ACM, and IEEE to update ethical standards for data-driven urbanism. A prescient analysis of why codes designed for traditional software development are insufficient for pervasive urban sensor systems.

**Domínguez Hernández, Andrés; Klein, Ewan; Raab, Charles D.; Stewart, James K.** (2020). "Ethical and Responsible IoT: The Edinburgh Initiative." *European Journal of Law and Technology*, 11(2). One of the few papers developing a **practical ethical governance framework for IoT infrastructure deployment**, arguing that legal requirements alone are insufficient and must be augmented with adaptable ethical instruments. Identifies challenges including unaware data subjects, social exclusion, and opacity of IoT data flows.

**ACM Digital Government** (2024). "Governing Smart City IoT Interventions: A Complex Adaptive Systems Perspective." *Digital Government: Research and Practice*. Adopts a Complex Adaptive Systems lens to analyse IoT platform ethics in Karnataka, India, foregrounding justice, fairness, trust, and dignity. The CAS perspective explains why centralised ethical codes fail for distributed IoT systems.

---

## 2. Traffic algorithms embed and amplify spatial inequity

A rapidly growing body of work (most published 2021–2026) demonstrates that traffic signal optimisation algorithms, when maximising aggregate throughput, systematically disadvantage pedestrians, cyclists, and communities in lower-income areas. The gap between computer science fairness research and transportation justice scholarship remains largely unbridged.

### Fairness-aware traffic signal control

**Raeis, Majid; Leon-Garcia, Alberto** (2021). "A Deep Reinforcement Learning Approach for Fair Traffic Signal Control." *IEEE ITSC 2021*, 2512–2518. Introduces two formal fairness definitions — **delay-based fairness** (preventing extreme waiting times) and **throughput-based fairness** (preventing one flow from disproportionately impacting another). Demonstrates that standard RL-based traffic optimisation inherently neglects fairness when optimising aggregate metrics. Foundational for any AI-controlled signal infrastructure.

**FairSCOSCA** (2026, arXiv preprint 2601.06275). "FairSCOSCA: Fairness At Arterial Signals — Just Around The Corner." Proposes fairness extensions to **SCOOTS and SCATS — the two most widely deployed adaptive signal systems globally** (60,000+ intersections, 565 cities). Demonstrates that minimal algorithmic modifications improve Egalitarian, Rawlsian, Utilitarian, and Harsanyian fairness dimensions without sacrificing efficiency. Open-source implementation available. Tested via microsimulation of Esslingen, Germany.

**ACM JATS** (2025). "Fair Multi-Agent Reinforcement Learning for Traffic Control." *ACM Journal on Autonomous Transportation Systems*. Formalises fairness in decentralised multi-agent RL using **generalised Gini welfare functions**, demonstrating consistent fairness improvement across six environments without requiring specialised architectures.

**FELight** (2024). "FELight: Fairness-Aware and Sample-Efficient Traffic Signal Control Method." *IEEE Transactions*. Integrates a fairness metric with an activation threshold into the RL decision process, addressing the practical challenge that real-world sensor deployments produce limited and biased training data.

**Fang, Wei; Zhao, Xin; Zhang, Chao** (2024). "Fairness-aware multi-agent reinforcement learning and visual perception for adaptive traffic signal control." *Optoelectronics Letters*, 20, 764–768. Demonstrates integration of computer vision sensors with fairness-aware control, directly relevant to camera-equipped smart intersections.

**Zhang, Xiaocai; Chan, Lok Sang; Nassir, Neema; Sarvi, Majid** (2025). "Towards fair lights: A multi-agent masked deep reinforcement learning for efficient corridor-level traffic signal control." ScienceDirect. One of the few papers **explicitly optimising for pedestrian fairness** in adaptive signal systems, tested across five Melbourne traffic scenarios.

### Transport justice and disparate impact

**Martens, Karel** (2016). *Transport Justice: Designing Fair Transportation Systems*. Routledge. Foundational text arguing that governments have a duty to provide **equitable accessibility rather than optimise system performance**. Proposes accessibility thresholds as the primary metric — directly applicable to fairness objectives in smart traffic algorithms.

**Cai, William; Gaebler, Johann; Kaashoek, Justin; Pinals, Lisa; Madden, Samuel; Goel, Sharad** (2022). "Measuring racial and ethnic disparities in traffic enforcement with large-scale telematics data." *PNAS Nexus*, 1(4), pgac144. Uses second-by-second telematics data from hundreds of thousands of individuals across 10 US cities. Finds that **speeding rates are uncorrelated with neighbourhood demographics, yet enforcement is concentrated in non-White neighbourhoods** even after adjusting for actual speeding. Demonstrates how large-scale IoT data can audit for disparate impact.

**Austin, Regina** (2024). "Traffic Violence, Disparate Pedestrian Deaths, and Transportation Justice via Vision Zero." SSRN Working Paper 5004969. Argues that Vision Zero programmes must address discrimination in social and cultural values, not just infrastructure, emphasising that **marginalised communities suffer disproportionate pedestrian fatalities**.

**McCarroll, Mark; Cugurullo, Federico** (2022). "Cyclists and autonomous vehicles at odds: Can the Transport Oppression Cycle be Broken in the Era of Artificial Intelligence?" *AI & Society*. Applies a critical lens showing historical "transport oppression" patterns may repeat with autonomous vehicles and smart traffic systems, systematically disadvantaging cyclists and pedestrians.

**Amorim, Julianno de Menezes; de Abreu e Silva, João** (2024). "Comparing the application of different justice theories in equity analysis of transit projects." *Journal of Transport and Land Use*, 17(1), 21–40. Demonstrates that **different justice frameworks yield different equity assessments** — the choice of fairness metric fundamentally determines which populations are identified as underserved.

**Ferrell, Christopher E.; Eells, John M.; Reinke, David B.; Schroeder, Matthew M.** (2022). "Defining and Measuring Equity in Public Transportation." Mineta Transportation Institute Report 2100. Finds that traditional Title VI measures (race and income) correlate poorly with other inequity dimensions, demonstrating that transit fairness is multifaceted and **cannot be captured by a single metric**.

### Blockchain audit trails for accountability

**MDPI IoT Journal** (2025). "Using Blockchain Ledgers to Record AI Decisions in IoT." *IoT*, 6(3), Article 37. Proposes a blockchain-based framework creating **immutable audit trails of AI-driven IoT decisions**, where each inference (inputs, model ID, output) is logged to a permissioned ledger. Addresses EU AI Act logging mandates. No papers were found specifically combining blockchain audit trails with traffic signal control — a significant research gap.

---

## 3. Speculative design surfaces ethical tensions before deployment

Design fiction and speculative methods offer a structured approach to anticipating the social consequences of autonomous infrastructure before it is built. The field has matured from theoretical foundations (2005–2013) to applied HCI methodology (2017–2025), with direct applications to IoT and smart cities emerging.

### Foundational frameworks

**Dunne, Anthony; Raby, Fiona** (2013). *Speculative Everything: Design, Fiction, and Social Dreaming*. MIT Press. Foundational text systematising speculative design and introducing the **"future cones" (PPPP) framework**: probable, plausible, possible, and preferable futures. Argues design should move beyond problem-solving to pose "what if" questions. The PPPP cones are directly applicable to mapping autonomous infrastructure futures — distinguishing between what is probable (expanded surveillance), plausible (community data trusts), possible (fully autonomous municipal services), and preferable (equitable sensor deployment).

**Sterling, Bruce** (2005/2009). *Shaping Things* (MIT Press, 2005); "Design Fiction" (*ACM Interactions*, 2009). Coined **"design fiction"** and defined it as "the deliberate use of diegetic prototypes to suspend disbelief about change." Design fiction focuses on specific potential objects and services, making future technologies tangible and debatable through artifacts that exist within a fictional world's internal logic.

**Bleecker, Julian** (2009). *Design Fiction: A Short Essay on Design, Science, Fact and Fiction*. Near Future Laboratory. Formalised design fiction by synthesising Sterling's concept with David Kirby's "diegetic prototypes," arguing that **design fiction occupies the productive intersection of science, design, and fiction**. Connected design fiction directly to ubiquitous computing (Ubicomp) research — the intellectual lineage of IoT — arguing that Ubicomp is itself "a kind of fiction."

**Candy, Stuart; Kornet, Kelly** (2019). "Turning Foresight Inside Out: An Introduction to Ethnographic Experiential Futures." *Journal of Futures Studies*, Special Issue on Design and Futures. Introduces the **Ethnographic Experiential Futures (EXF) framework**, combining ethnographic futures research with experiential futures (XF). Candy's "Experiential Futures Ladder" maps progression from abstract (Setting → Scenario) to concrete (Situation → Stuff). Directly applicable for community engagement around IoT infrastructure — surfacing residents' hopes and anxieties about sensor-laden public spaces through situated interventions.

**Candy, Stuart; Dunagan, Jake** (2017). "Designing an Experiential Scenario: The People Who Vanished." *Futures*, 86, 136–153. Detailed methodological case study for creating immersive experiential scenarios that "collapse temporal distance," enabling communities to viscerally respond to possible autonomous infrastructure futures before deployment.

### Design fiction in HCI and responsible innovation

**Baumer, Eric P. S.; Blythe, Mark; Tanenbaum, Theresa Jean** (2020). "Evaluating Design Fiction: The Right Tool for the Job." *ACM DIS '20*, 1901–1913. Addresses the critical gap of evaluating design fiction in HCI, identifying **six evaluative traditions** (critical design, narratology, studio crits, user studies, scenarios, thought experiments). Essential methodological guidance for researchers using design fiction to investigate autonomous infrastructure.

**Wong, Richmond Y.; Mulligan, Deirdre K.; Van Wyk, Ellen; Pierce, James; Chuang, John** (2017). "Eliciting Values Reflections by Engaging Privacy Futures Using Design Workbooks." *Proceedings of the ACM on Human-Computer Interaction*, 1(CSCW), Article 111. **Best Paper Award.** Demonstrates that speculative design fictions about future sensing technologies surface normative questions about power, consent, and privacy that conventional privacy engineering misses. The design workbook method bridges critical/speculative design with value-sensitive design — directly transferable to engaging communities about environmental sensors and autonomous monitoring.

**Wong, Richmond Y.; Van Wyk, Ellen; Pierce, James** (2017). "Real-Fictional Entanglements: Using Science Fiction and Design Fiction to Interrogate Sensing Technologies." *ACM DIS '17*, 567–579. Uses science fiction texts as starting points for design fictions about sensing technologies, creating **"real-fictional entanglements"** that blur the boundary between present reality and fictional future. Provides a direct template for creating design fictions about IoT sensing infrastructure.

### Applied to smart cities and autonomous infrastructure

**Forlano, Laura; Mathew, Anijo** (2014). "From Design Fiction to Design Friction: Speculative and Participatory Design of Values-Embedded Urban Technology." *Journal of Urban Technology*, 21(4), 7–24. Introduces **"design friction"** — combining speculative design with participatory methods to embed values into urban technology design. Directly critiques how technology companies frame smart city agendas around efficiency while obscuring value choices.

**Forlano, Laura** (2019). "Stabilizing/Destabilizing the Driverless City: Speculative Futures and Autonomous Vehicles." *International Journal of Communication*, 13, 2811–2838. Uses ethnographic observation, qualitative interviews, and speculative design to demonstrate how **speculative interventions can resist and destabilize normative visions** of linear technological progress toward autonomous futures. Methodology transferable to any autonomous infrastructure context.

**Barron, Lee** (2022). "Smart Cities, Connected Cars, and Autonomous Vehicles: Design Fiction and Visions of Smarter Future Urban Mobility." *Technoetic Arts*, 20(3), 225–240. Applies speculative design and design fiction to critically analyse smart and autonomous vehicles within smart city contexts, identifying enhanced surveillance and data mining as critical ethical issues.

**Zhu, Chao-Fu et al.** (2024). "How HCI Integrates Speculative Thinking to Envision Futures." *Journal of Futures Studies*. Scoping review of 88 papers finding three primary ways HCI constructs futures through speculative thinking. Identifies gaps in rigor and evaluation that researchers applying speculative methods to IoT/smart city contexts should address.

**Cambridge Design Science** (2024–2025). "A Systematic Literature Review of the Speculative Design Process and a Proposed Framework." *Design Science*, Cambridge University Press. Reviews 53 speculative artifacts, categorising them as **Reflective, Exploratory, Interventional, and Heuristic** — a practical typology for selecting the right kind of speculative artifact for stakeholder engagement about IoT sensor deployment.

---

## 4. The surveillance-optimisation paradox demands architectural solutions

Traffic optimisation requires granular movement data; privacy demands its restriction. This fundamental tension has generated a growing literature on architectural responses — particularly edge computing and federated learning — alongside regulatory analysis and critical surveillance scholarship.

### Surveillance and smart city critique

**Melgaço, Lucas; van Brakel, Rosamunde** (2021). "Smart Cities as Surveillance Theatre." *Surveillance & Society*, 19(2). Argues that framing smart city surveillance solely through "surveillance capitalism" ignores the **complex surveillance assemblages driven by multiple actors and power relations**. Compares investment in mass surveillance to theatre in which politicians perform crime-fighting without genuine interest in outcomes.

**Makanadar, Ashish** (2024). "Digital surveillance capitalism and cities: data, democracy and activism." *Humanities and Social Sciences Communications* (Nature), 11, Article 1533. Proposes a paradigm shift: municipalities outsourcing digital infrastructure causes citizens to relinquish sovereignty over public-space data. Advocates **"data dignity" through differential privacy, secure multi-party computation, and distributed digital commons** as alternatives to proprietary data silos. Explores blockchain-based "crypto-cities" as governance models.

**Lucas, Evie; Simpson, Seamus** (2025). "Perspectives on citizen data privacy in a smart city — An empirical case study." *Convergence* (SAGE). Identifies a **"data privacy disconnect"** between citizens and policymakers, alongside a "transparency paradox" where providing more detail about data practices can actually reduce understanding. Finds surveillance embedded in smart cities undermines the sense of urban anonymity essential to city life.

### Edge computing as privacy architecture

**Gheisari, Mehdi; Pham, Quoc Viet; Alazab, Mamoun; Zhang, Xiaobo; Fernandez-Campusano, Christian; Srivastava, Gautam** (2019). "ECA: An Edge Computing Architecture for Privacy-Preserving in IoT-Based Smart City." *IEEE Access*, 7, 155779–155786. Proposes a privacy-preserving architecture using **ontology-based knowledge at the network edge**, applying privacy rules for each IoT device before data transmission to cloud servers. Foundational work demonstrating how edge processing protects sensitive data from traffic sensors and cameras.

**Rousseau, Franck; Jégou, Yvon; Abdennadher, Nabil et al.** (2022). "Toward blockchain-based fog and edge computing for privacy-preserving smart cities." *Frontiers in Sustainable Cities*, 4, Article 846987. Integrates blockchain, federated learning, and edge/fog computing, arguing that **processing data locally avoids concentrating private data in the hands of a few cloud providers**. Demonstrates that urban areas already contain abundant computing resources (IP cameras, traffic lights, sensors) that could form a distributed privacy-preserving architecture.

### GDPR and regulatory frameworks

**European Data Protection Board** (2020). *Guidelines 3/2019 on processing of personal data through video devices*, Version 2.0. The primary regulatory framework governing camera-equipped smart traffic infrastructure in the EU. Establishes that GDPR applies to **all functioning video cameras processing personal data** (including license plates and identifiable pedestrians). Generic purposes like "safety" are insufficient under Article 5(1)(b); each camera requires a specified purpose. When smart cameras enable facial or license plate recognition, biometric data provisions apply.

**IntechOpen** (2024). "GDPR Compliance in Video Surveillance Systems and Applications." Book chapter. Reviews technical solutions for GDPR compliance including anonymisation algorithms, encryption, and the engineering challenges of **anonymising bystanders while retaining useful traffic data** — a core tension for smart intersection controllers.

### Privacy-preserving technical approaches

**ScienceDirect** (2023). "Differential privacy in edge computing-based smart city applications: Security issues, solutions and future directions." Comprehensive study covering five data-lifecycle areas: transmitting, processing, model training, publishing, and location privacy. Finds that **differential privacy is particularly effective for resource-constrained edge environments**, providing a roadmap for implementation in traffic sensor networks.

**Pandya, Sudeep et al.** (2023). "Federated learning for smart cities: A comprehensive survey." *Sustainable Cities and Society* (Elsevier). Shows that federated learning enables **traffic prediction models to learn from distributed intersection sensors without centralising sensitive movement data**. Reviews challenges including data heterogeneity, communication overhead, and adversarial attacks.

**arXiv 2511.06363** (2025). "Privacy-Preserving Federated Learning for Fair and Efficient Urban Traffic Optimization." Proposes a federated learning framework combining GRU-based traffic prediction with reinforcement learning-driven routing, enabling **fully decentralised, privacy-preserving adaptive communication across IoT networks**. Each node trains models locally, eliminating centralised data collection. Represents the cutting edge of the optimisation-privacy integration.

### Data sovereignty

**ScienceDirect** (2025). "Enhancing data sovereignty to improve intelligent mobility services in smart cities." Examines how data sovereignty can be achieved for urban mobility users, noting that **in smart cities, data is produced and used by individuals having no ownership or control**. Designs a data control scheme applicable to intersection sensors and traffic monitoring, ensuring municipal rather than vendor control.

---

## 5. The hardware itself carries hidden environmental debt

Deploying thousands of GPU-equipped edge nodes creates environmental costs that are routinely overlooked in smart city planning. The literature reveals three compounding problems: embodied carbon in manufacturing, operational energy consumption, and end-of-life e-waste — amplified by blockchain audit mechanisms if poorly designed.

### Life cycle assessment of IoT and edge infrastructure

**Pirson, Thibault; Bol, David** (2021). "Assessing the embodied carbon footprint of IoT edge devices with a bottom-up life-cycle approach." *Journal of Cleaner Production*, 322, 128966. Presents a parametric framework for evaluating cradle-to-gate carbon footprint of IoT edge devices, finding that **LCAs for IoT devices are extremely scarce** and that environmental burdens of massive deployment are usually overlooked under the assumption that individual device impact is negligible. Provides the methodology for quantifying hardware manufacturing impacts at city scale.

**Baldini, Edoardo; Chessa, Stefano; Brogi, Antonio** (2023). "Estimating the Environmental Impact of Green IoT Deployments." *Sensors*, 23(3), 1537. Models a 30-year lifecycle for outdoor IoT deployments and finds that even solar-powered systems consume **more than 3× the energy and generate 15× greater waste volume** than baseline solutions. Notes that IoT nodes contain hazardous substances and difficult-to-recycle batteries.

**Ramadane, Mustapha; Meyer, Stefan; Bohnet, Dennis** (2024). "Environmental Impact Assessment of IoT Devices." *Procedia Computer Science*, 236, 338–347. Proposes graph-based LCA methodology exploiting the recurring nature of core IoT components (CPUs, sensors, communication modules) to streamline assessments — addressing the fact that comprehensive LCAs have been too manual and costly to perform at scale.

### Edge computing energy and sustainability

**Arroba, Patricia; Moya, José Manuel; Ayala, José L.; Buyya, Rajkumar** (2024). "Sustainable edge computing: Challenges and future directions." *Software: Practice and Experience*, 54(6). Argues that industry regulations increasingly view edge computing as a **potential environmental threat** due to energy inefficiency at the network periphery. While cloud data centres achieve PUE of ~1.55, edge deployments face suboptimal locations, higher relative cooling costs, and the need for massive infrastructure. Proposes integration with smart grids and renewable energy.

**Fraga-Lamas, Paula; Fernández-Caramés, Tiago M.; Suárez-Albela, Manuel; Castedo, Luis; González-López, Miguel** (2021). "Green IoT and Edge AI as Key Technological Enablers for a Sustainable Digital Transition." *Sensors*, 21(17), 5745. Highlights the paradox that **Edge AI's energy demands directly collide with the Green IoT vision** (green design, production, utilisation, disposal). Demonstrates through an Industry 5.0 use case how mist computing architectures can partially balance efficiency and sustainability.

### Blockchain carbon footprint

**Wendl, Mirko; Doan, My Hanh; Sassen, Remmer** (2023). "The environmental impact of cryptocurrencies using proof of work and proof of stake consensus algorithms: A systematic review." *Journal of Cleaner Production*, 388, 135773. Systematic review of 50 articles finding that **PoW generates approximately 0.86 metric tons of CO₂ per transaction**. Ethereum's transition to PoS reduced energy consumption by **99.95%**. Critical for evaluating blockchain-based audit trails: PoW is environmentally untenable for smart city infrastructure; PoS or permissioned alternatives are essential.

**Jiang, Shuanglong; Li, Jiajun; Song, Yajie** (2022). "Confronting the Carbon-Footprint Challenge of Blockchain." *Environmental Science & Technology*, 56(23), 16714–16720. Provides CO₂ emission projections demonstrating that continued PoW mechanisms would push global temperatures above 1.5°C this century. The scientific basis for requiring low-energy consensus mechanisms in any blockchain component of autonomous infrastructure.

**Kumar, Vinay; Kumar, Tanuj; Tiwari, Aviral Kumar; Chauhan, Rambir Kumar** (2023). "Impact of Proof of Work (PoW)-Based Blockchain Applications on the Environment: A Systematic Review and Research Agenda." *JRFM*, 16(4), 218. Reviews 60 articles, noting that **Bitcoin mining alone consumes more than 0.6% of global energy** and that mining hardware has 2–4 year lifespans generating significant e-waste.

### E-waste and conflict minerals

**Nkomo, Ikechukwu; Kitsios, Felix; Kamariotou, Maria** (2022). "Threats of Internet-of-Thing on Environmental Sustainability by E-Waste." *Sustainability*, 14(16), 10161. Reports that mining metals for one smartphone generates **44,400g of mine tailings**, with experts projecting a **250% increase in rare-earth extraction by 2030**. Global e-waste reached 53.6 Mt in 2019 (projected 74 Mt by 2030), with only ~17% properly recycled. The rare earth and critical mineral extraction for IoT hardware scales linearly with deployment.

**Chauhan, Amir; Saini, Naveen Kumar; Dwivedi, Ashish; Agrawal, Dindayal; Paul, Sanjoy Kumar** (2022). "The Internet of Things and the circular economy: A systematic literature review and research agenda." *Journal of Cleaner Production*, 371, 133553. Reviews 170 articles, finding that while IoT enables circularity through lifecycle monitoring, **IoT deployment itself creates linear waste streams** — devices with limited lifecycles and energy-intensive components. Essential for designing edge infrastructure for circularity rather than additional e-waste.

**Bibri, Simon Elias** (2023). "Environmentally sustainable smart cities and their converging AI, IoT, and big data technologies." *Energy Informatics*, 6, Article 259. Comprehensive interdisciplinary review finding that the infrastructure needed for sustainability monitoring **itself has significant environmental costs**, creating a paradox where technological advancement does not always promote environmental sustainability.

---

## Cross-cutting gaps and the research frontier

Several critical research gaps emerge across all five vectors that define where scholarship must advance for autonomous public infrastructure to be responsibly deployed.

The **accountability architecture gap** is the most pressing. Professional codes assume identifiable developers; algorithmic fairness research assumes auditable systems; privacy frameworks assume a data controller. In decentralised, adaptive IoT networks, all three assumptions fail simultaneously. No existing framework adequately addresses the scenario where thousands of edge nodes collectively produce emergent behaviour that no single entity designed or controls. Goetze's (2022) "moral entanglement" and Vallor and Vierkant's (2024) "vulnerability gap" point toward solutions, but neither has been operationalised for IoT infrastructure.

The **fairness-justice disconnect** between computer science and transportation scholarship is striking. Technical fairness papers (Raeis & Leon-Garcia 2021; FairSCOSCA 2026) define fairness as equalising wait times across traffic directions, while transport justice scholars (Martens 2016; Austin 2024) define it as equitable accessibility across communities. These are fundamentally different objectives, and **no paper bridges them computationally** — translating Martens's accessibility thresholds into RL reward functions, for instance.

The **speculative-to-operational pipeline** remains underdeveloped. While design fiction methods have matured substantially (Baumer et al. 2020; Wong et al. 2017), and smart city applications exist (Forlano 2014, 2019), there is limited work specifically using experiential futures for community engagement about IoT sensor deployment. This represents a productive research frontier where Candy's EXF framework (2019) could be applied to surface tensions around autonomous intersection controllers before installation.

The **sustainability blind spot** in smart city planning is severe. No comprehensive LCA exists for city-scale edge computing deployments (Pirson & Bol 2021). The combined energy cost of running edge AI inference and blockchain audit trails on the same infrastructure has not been characterised. And conflict minerals specific to IoT/edge hardware supply chains — as opposed to consumer electronics generally — remain virtually unstudied in academic literature. Meanwhile, the quantitative data is sobering: IoT deployments can generate **15× greater waste volume** than baseline alternatives (Baldini et al. 2023), edge computing is increasingly viewed as an environmental threat (Arroba et al. 2024), and PoW blockchain mechanisms are categorically incompatible with sustainability goals (Wendl et al. 2023).

## Conclusion

This survey reveals that autonomous public IoT infrastructure occupies a governance vacuum. The five research vectors are not independent problems but interconnected dimensions of a single challenge: **building public systems that are accountable without a single accountable entity, fair without agreed fairness definitions, anticipatory without established anticipatory methods, privacy-preserving while data-hungry, and sustainable while hardware-intensive**. The most promising integrative approaches combine edge-first architectures (for privacy), federated learning (for decentralised optimisation), permissioned blockchain (for auditable accountability), speculative design (for anticipatory governance), and circular economy principles (for sustainability) — but no existing work synthesises all five. The field needs frameworks that treat these as co-design constraints rather than separate research agendas.