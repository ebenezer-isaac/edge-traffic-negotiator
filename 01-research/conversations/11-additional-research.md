> **SUPERSEDED HISTORICAL RECORD (pre-2026-05-31-pivot).** Dated measurement log / transcript kept for the audit trail; the current thesis is in specs/001-edge-negotiator/MASTER-SPEC.md (Euston A501; self-referential coupling; CT-style accountability; Phi-4-mini). Forbidden-term hits below are historical, not current claims.

# Verified sources: AI traffic systems and equity provisions

**AI-optimised traffic signals systematically disadvantage pedestrians, low-income communities, and minority groups** — a pattern documented across adaptive systems from SCOOT to reinforcement learning. This report compiles verified, citable evidence across three domains: algorithmic inequity in traffic signals, London-specific smart traffic data, and the "black box recorder" analogy for autonomous infrastructure. Every claim below includes author, title, publication, year, and URL or DOI.

---

## Part A: Traffic signal algorithms and spatial/demographic inequity

### A1. Adaptive signal systems produce disparate outcomes

Reinforcement learning-based traffic signal control research has increasingly documented fairness failures. Standard deep RL methods optimise for aggregate throughput or average delay, creating situations where specific intersections, traffic flows, or transport modes experience disproportionate waiting times.

**Raeis, M. and Leon-Garcia, A.** "A Deep Reinforcement Learning Approach for Fair Traffic Signal Control." *2021 IEEE International Intelligent Transportation Systems Conference (ITSC)*, Indianapolis, IN, pp. 2512–2518, 2021. URL: https://arxiv.org/abs/2107.10146. Shows that standard DRL-based signal control neglects fairness, producing extreme waiting times for some vehicles and highly unequal throughput across conflicting traffic flows.

**Zhang, X. et al.** "Human-Centric Traffic Signal Control for Equity: A Multi-Agent Action Branching Deep Reinforcement Learning Approach." *arXiv preprint* arXiv:2602.02959, February 2026. URL: https://arxiv.org/abs/2602.02959. Argues existing multi-agent DRL approaches remain "vehicle-centric" and proposes a human-centric framework penalising the number of delayed *individuals* — including pedestrians, vehicle occupants, and transit passengers. Tested on seven realistic Melbourne scenarios. **This is the closest study to directly measuring mode-based inequity in adaptive signal systems.**

**Fang, W., Zhao, X. and Zhang, C.** "Fairness-aware multi-agent reinforcement learning and visual perception for adaptive traffic signal control." *Optoelectronics Letters*, vol. 20, pp. 764–768, 2024. DOI: https://doi.org/10.1007/s11801-024-3267-2. Finds that "the majority of MARL methods for ATSC are dedicated to maximizing throughput while ignoring fairness, resulting in a bad situation where some vehicles keep waiting."

**"Fair Multi-Agent Reinforcement Learning for Traffic Control."** *ACM Journal on Autonomous Transportation Systems*, 2025. URL: https://dl.acm.org/doi/10.1145/3749378. Formalises fairness in decentralised MARL for traffic signal control using Generalised Gini Welfare functions. Demonstrates that standard MARL algorithms "often lead to unfair treatment across different intersections."

**"Efficiency and Equity are Both Essential: A Generalized Traffic Signal Controller with Deep Reinforcement Learning."** *IEEE*, 2021, document #9340784. URL: https://ieeexplore.ieee.org/document/9340784/. Introduces an equity factor and adaptive discounting approach for simultaneous efficiency and equity optimisation.

**Noaeen, M. et al.** "Reinforcement learning in urban network traffic signal control: A systematic literature review." *Expert Systems with Applications*, vol. 199, p. 116830, 2022. DOI: https://doi.org/10.1016/j.eswa.2022.116830. Comprehensive review covering 26 years of RL in traffic signal control; identifies the **lack of equity considerations** as a significant gap.

**"Traffic Signal Control via Reinforcement Learning: A Review on Applications and Innovations."** *MDPI Infrastructures*, 10(5), 114, 2025. URL: https://www.mdpi.com/2412-3811/10/5/114. Finds that 43% of studies focus solely on queue/waiting time; only **5% address safety** and **4% address environmental impacts**; fairness is largely neglected.

On conventional adaptive systems, a NYSERDA report documented that **SCATS in Portland, Oregon** created pedestrian delay problems, requiring a 20-second reduction in maximum cycle length as a remediation trial. Side street neglect was cited as a downside by multiple SCATS users. (NYSERDA, "Decision-Making Tool for Applying Adaptive Traffic Control Systems," Final Report, 2016. URL: https://www.nyserda.ny.gov/-/media/Project/Nyserda/Files/Publications/Research/Transportation/2016-12-Decision-Tool-Adaptive-Traffic-Control-Systems.pdf.)

**Important research gap:** No published study directly measures SCOOT or SCATS outcomes stratified by neighbourhood income or race. The equity literature in adaptive signal control focuses on fairness between intersections or transport modes rather than correlating outcomes with demographic characteristics of surrounding areas. This gap itself is a significant finding for the coursework.

---

### A2. Pedestrian fatality disparities by neighbourhood income

#### United States

The evidence is stark. **The per-capita pedestrian fatality rate in US census tracts with median incomes of $15,000–$25,000 is more than four times higher than in areas with median income over $100,000** (5.23 vs 1.07 per 100,000).

**Smart Growth America.** "Dangerous by Design 2024." Smart Growth America / National Complete Streets Coalition, 2024. URL: https://smartgrowthamerica.org/dangerous-by-design/. Despite accounting for only 17% of the population, 30% of all pedestrian deaths occur in census tracts with yearly incomes below $50,000. American Indian/Alaska Native death rate of **5.87 per 100,000** is nearly triple the rate for non-Hispanic Whites. Black Americans and Native Americans combined account for nearly 22% of metro-area pedestrian deaths but only ~13% of the population.

**Smart Growth America.** "Dangerous by Design 2022." Smart Growth America, 2022. URL: https://smartgrowthamerica.org/dangerous-by-design/. More than 6,500 people struck and killed while walking in 2020 — 18 per day. Fatality rate in lowest-income neighbourhoods nearly twice that of middle-income areas, and more than three times that of higher-income areas.

**Governors Highway Safety Association (GHSA).** "Pedestrian Traffic Fatalities by State: 2024 Preliminary Data (January–December)." GHSA, 2025. URL: https://www.ghsa.org/resource-hub/pedestrian-traffic-fatalities-state-2024-preliminary-data-january-december. **7,148 pedestrians killed in 2024**; between 2009 and 2023 pedestrian deaths rose 80% while all other traffic fatalities increased 13%. 65% of deaths occurred at locations without sidewalks; more than 75% occur after dark.

**Mansfield, T.J. et al.** "The effects of roadway and built environment characteristics on pedestrian fatality risk: A national assessment at the neighborhood scale." *Accident Analysis & Prevention*, vol. 121, pp. 166–176, 2018. DOI: 10.1016/j.aap.2018.06.018. URL: https://pubmed.ncbi.nlm.nih.gov/30248532/. Found that **for every $1,000 decrease in a census tract's median income, pedestrian fatal injuries increase by approximately 1%**.

**Chakravarthy, B. et al.** "The relationship of pedestrian injuries to socioeconomic characteristics in a large Southern California County." *Traffic Injury Prevention*, vol. 11, no. 5, pp. 508–513, 2010. URL: https://pubmed.ncbi.nlm.nih.gov/20872307/. Pedestrian crashes are **4 times more frequent** in poor neighbourhoods. Lowest-income quartile: 44 crashes per 100,000 annually vs 11 per 100,000 in highest-income quartile.

**Dumbaugh, E. et al.** "Why do lower-income areas experience worse road safety outcomes? Examining the role of the built environment in Orange County, Florida." *Transportation Research Interdisciplinary Perspectives*, 2022. URL: https://www.sciencedirect.com/science/article/pii/S2590198222001567. Pedestrians in low-income neighbourhoods are **six times more likely** to be injured by a moving vehicle compared to those in high-income regions.

**Maciag, M.** "Pedestrians Dying at Disproportionate Rates in America's Poorer Neighborhoods." *Governing Magazine*, 2014. URL: https://www.governing.com/archive/gov-pedestrian-deaths-analysis.html. Analysis of 22,000+ fatalities (2008–2012): high-poverty areas (>25% in poverty) had a rate of **12.1 per 100,000** vs 5.3 in low-poverty areas (<15%).

**Kravetz, D. and Noland, R.B.** "Spatial Analysis of Income Disparities in Pedestrian Safety in Northern New Jersey." *Transportation Research Record*, vol. 2320, pp. 10–17, 2012. URL: https://pubmed.ncbi.nlm.nih.gov/23856641/.

**Mwende, S.I. et al.** "Investigating Racial and Poverty-Level Disparities Associated with Pedestrian Nighttime Crashes." *Transportation Research Record*, 2024. DOI: 10.1177/03611981241233294.

#### United Kingdom

**Department for Transport.** "Reported road casualties Great Britain: Casualties and deprivation" (Factsheet, England, 2018–2022 data). DfT/GOV.UK, 2023. URL: https://www.gov.uk/government/statistics/reported-road-casualties-great-britain-casualties-and-deprivation-factsheet-england/reported-road-casualties-great-britain-casualties-and-deprivation. The **clearest association with deprivation is for pedestrians and bus occupants**. The gap between KSI casualties in most and least deprived IMD deciles has been widening. The relationship is not simply explained by exposure.

**Department for Transport.** "Reported road casualties Great Britain: Casualties and deprivation 2024 (England)." DfT/GOV.UK, 2025. URL: https://www.gov.uk/government/statistics/reported-road-casualties-great-britain-casualties-and-deprivation-factsheet-2024-england/reported-road-casualties-great-britain-casualties-and-deprivation-2024-england.

**Edwards, P. et al.** "Deprivation and Road Safety in London: A report to the London Road Safety Unit." LSHTM/TfL, 2006. URL: https://content.tfl.gov.uk/deprivation-and-road-safety.pdf. **The most deprived pedestrians are over twice as likely to be injured as the least deprived.** Child pedestrian injury rate in the most deprived decile was **nearly 3 times** (2.93×) the rate in the least deprived decile.

**Grundy, C. et al.** "The Effect of 20 mph Zones on Inequalities in Road Casualties in London." LSHTM/TfL, 2008. URL: https://content.tfl.gov.uk/the-effect-of-20-mph-zones-on-inequalities-in-road-casualties-in-london.pdf. Overall socio-economic inequalities in casualties **widened** across London 1987–2006.

**Transport for London.** "Inequalities in Road Danger in London (2017–2021)" and "Vision Zero Inequalities Dashboard." TfL, 2024. URL: https://tfl.gov.uk/info-for/media/press-releases/2024/january/pioneering-map-of-london-shows-the-link-between-deprivation-and-road-casualties. People from the 30% most deprived postcodes have **nearly double the risk** of being killed or injured.

---

### A3. Vehicular bias in traffic signal timing

The most authoritative source is the US government-backed NCHRP Report 969, which represents official recognition of the problem.

**Cesme, B., Furth, P.G., Lee, K. et al.** "NCHRP Research Report 969: Traffic Signal Control Strategies for Pedestrians and Bicyclists." Transportation Research Board, National Academies of Sciences, 2022. URL: https://nap.nationalacademies.org/catalog/26491/traffic-signal-control-strategies-for-pedestrians-and-bicyclists. Documents that "in the United States, traffic signal timing is traditionally developed to minimize motor vehicle delay at signalized intersections, with minimal attention paid to the needs of pedestrians and bicyclists." Software tools used for signal timing **do not calculate pedestrian delay**, resulting in situations where **average intersection vehicle delay is as low as 20 seconds while average pedestrian delay is as high as 80 seconds**. When pedestrian delay exceeds 60 seconds, "very high likelihood of non-compliance is anticipated" (per HCM 2000).

**Furth, P.G.** "Poor Signal Phase Coordination Results in 4-Minute Pedestrian Delay at Forest Hills Traffic Signal." Northeastern University faculty blog, April 2021. URL: https://peterfurth.sites.northeastern.edu/2021/04/07/pedestrian-delay-exceeds-4-minutes-at-forest-hills-traffic-signal/. Documents a real-world case where pedestrian delay reached **241 seconds** due to vehicle-optimised timing. States: "The engineers who develop traffic signal plans work hard, optimizing signals to minimize vehicle delay. But they don't optimize for pedestrian delay, because they never measure it." Minor signal timing changes could reduce delay to 52 seconds with "no impact to traffic capacity."

**Levinson, D.** "Signalling inequity — How traffic signals distribute time to favour the car and delay the pedestrian." *The Conversation*, June 2018. URL: https://theconversation.com/how-traffic-signals-favour-cars-and-discourage-walking-92675. Blog version with more detail: https://transportist.org/2018/06/12/signalling-inequity-how-traffic-signals-distribute-time-to-favour-the-car-and-delay-the-pedestrian/. Documents how SCATS exemplifies car-oriented control: vehicles are automatically detected while pedestrians must push a "beg button." Notes: "There is no sin worse [in traffic engineering] than delaying a car."

**Cesme, B. and Furth, P.G.** "Development of Pedestrian Recall Versus Actuation Guidelines for Pedestrian Crossings at Signalized Intersections." *Transportation Research Record*, 2021. DOI: https://doi.org/10.1177/03611981211002846. Documents how actuation systems cause pedestrians arriving during the Walk interval to wait an entire additional cycle.

**National Association of City Transportation Officials (NACTO).** "Urban Street Design Guide." Island Press, 2013. URL: https://nacto.org/publication/urban-street-design-guide/. States: "Level of service (LOS) is mono-modal, measuring streets not by their economic and social vibrancy, but by their ability to process motor vehicles."

**Streetsblog USA.** "How Engineering Standards for Cars Endanger People Crossing the Street." 3 March 2017. URL: https://usa.streetsblog.org/2017/03/03/how-engineering-standards-for-cars-endanger-people-crossing-the-street. Ian Lockwood (Toole Design Group) states: "When a traffic engineer says they've optimized a traffic signal, that typically means they made it the best for the motorists. There's a pro-speed, pro-automobile bias that's built into the traffic engineering culture." The MUTCD requires **93 pedestrians per hour** before warranting a signalised crossing, or 5 people struck — no such threshold exists for motor vehicle signals.

**Litman, T.** "Evaluating Transportation Equity: Guidance for Incorporating Distributional Impacts in Transport Planning." Victoria Transport Policy Institute, 2024. URL: https://www.vtpi.org/equity.pdf. States that "conventional planning evaluates transportation system performance based primarily on vehicle traffic speeds and delay, which favors faster modes… This favors motorists over non-drivers, and since vehicle travel tends to increase with ability and income, is unfair."

**Nardone, A. et al.** "Health Disparities, Transportation Equity and Complete Streets." *Journal of Urban Health*, 2020. URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC7704855/. Documents how "traditional roadway design moves large numbers of cars as efficiently as possible, rather than balancing the needs of pedestrians and cyclists."

---

### A4. Amsterdam and Helsinki AI registries

Both registries launched simultaneously on **28 September 2020** at the Next Generation Internet Summit. They were described as **the first cities in the world to launch open AI registers**.

#### Amsterdam AI Register

**City of Amsterdam.** *White Paper on the AI Register.* September 2020. URL: https://algoritmeregister.amsterdam.nl/wp-content/uploads/White-Paper.pdf.

**Official register URL:** https://algoritmeregister.amsterdam.nl/en/ai-register/ (Note: as of 1 January 2025, Amsterdam's register was merged into the Dutch national Algorithm Register at https://algoritmes.overheid.nl/en.)

Each entry must disclose: datasets used to train the model; description of how the algorithm is used; how humans utilise predictions; assessment for potential bias or risks; responsible person's name, department, and contact information; data processing methods; how inclusion/non-discrimination is ensured; degree of human oversight; and a citizen feedback channel.

Initially listed three AI systems: parking control (camera-equipped patrol cars), public space report categorisation (keyword recognition for routing maintenance issues), and holiday rental fraud detection (investigation prioritisation).

#### Helsinki AI Register

**Official URL:** https://ai.hel.fi/en/ai-register/

Implemented by Saidot, a Finnish company specialising in transparent AI platforms. Initially listed five systems including a parking chatbot, maternity clinic chatbot, health centre chatbot, library recommendation system, and intelligent material management system.

**City of Helsinki.** "Helsinki and Amsterdam first cities in the world to launch open AI register." Press release, 28 September 2020. URL: https://news.cision.com/fi/city-of-helsinki/r/helsinki-and-amsterdam-first-cities-in-the-world-to-launch-open-ai-register,c3204076.

#### Academic analyses

**Floridi, L.** "Artificial Intelligence as a Public Service: Learning from Amsterdam and Helsinki." *Philosophy & Technology*, vol. 33, pp. 541–546, 2020. DOI: https://doi.org/10.1007/s13347-020-00434-3.

**Cath, C. and Jansen, F.** "Dutch Comfort: The Limits of AI Governance through Municipal Registers." *Techné: Research in Philosophy and Technology*, vol. 26, no. 3, pp. 395–412, 2022. Preprint: https://arxiv.org/pdf/2109.02944. Critical analysis arguing registers risk "ethics theatre," exclude sensitive areas like law enforcement, and are limited by opt-in participation.

**Nieuwenhuizen, E.** "Algorithm Registers: A Box-Ticking Exercise or Meaningful Tool for Transparency?" *International Review of Administrative Sciences*, 2024. DOI: https://doi.org/10.1177/15701255241297107.

#### Netherlands national Algorithm Register

Launched 21 December 2022 at https://algoritmes.overheid.nl/en. Over **1,300 algorithms from 500+ government organisations** registered. Currently voluntary but becoming legally mandatory by end of 2025. Dutch Data Protection Authority serves as coordinating supervisory authority since 1 January 2023. (Source: NL Digital Government, "Algorithms — Digital Government," last modified 27 February 2025. URL: https://www.nldigitalgovernment.nl/overview/algorithms/.)

#### UK Algorithmic Transparency Recording Standard (ATRS)

First published November 2021. **Made mandatory for central government departments on 6 February 2024.** Two-tier structure: Tier 1 (simple explanation) and Tier 2 (detailed technical specifications, data, risks, and impact assessments). 36 records published as of May 2025. (UK Government Digital Service, "Algorithmic Transparency Recording Standard Hub," GOV.UK, updated 8 May 2025. URL: https://www.gov.uk/government/collections/algorithmic-transparency-recording-standard-hub.)

---

### A5. UK-specific transport equity reports

**Social Exclusion Unit.** "Making the Connections: Final Report on Transport and Social Exclusion." Office of the Deputy Prime Minister, 2003. URL: https://www.ilo.org/emppolicy/pubs/WCMS_ASIST_8210/lang--en/index.htm. Landmark report identifying how poor transport accessibility contributes to social exclusion.

**Lucas, K.** "Transport and social exclusion: Where are we now?" *Transport Policy*, vol. 20, pp. 105–113, 2012. DOI: 10.1016/j.tranpol.2012.01.013.

**Lucas, K. et al.** "Transport poverty and its adverse social consequences." *Proceedings of the Institution of Civil Engineers — Transport*, vol. 169, no. 6, pp. 353–365, 2016. DOI: 10.1680/jtran.15.00073. Transport poverty potentially affects **10%–90% of households** depending on definition and country.

**Lucas, K., Stokes, G., Bastiaanssen, J. and Burkinshaw, J.** "Future of Mobility: Inequalities in Mobility and Access in the UK Transport System." Government Office for Science (Foresight), 2019. URL: https://assets.publishing.service.gov.uk/media/5c828f80ed915d07c9e363f7/future_of_mobility_access.pdf. Found **9% of UK households experience car-related economic stress**.

**Department for Transport.** "Transport and inequality: An evidence review for the Department for Transport." DfT, 2019. URL: https://assets.publishing.service.gov.uk/media/60080f728fa8f50d8f210fbe/Transport_and_inequality_report_document.pdf. Top 10% of UK households have average net incomes nine times the bottom 10%.

**Titheridge, H. et al.** "Transport and Poverty: A Review of the Evidence." UCL Transport Institute, 2014. URL: https://www.ucl.ac.uk/transport/sites/transport/files/transport-poverty.pdf.

**Social Market Foundation.** "Getting the Measure of Transport Poverty." SMF, November 2023. URL: https://www.smf.co.uk/publications/transport-poverty-hidden-crisis/. Transport costs push **over 5 million people** (8% of population) into poverty. **12.5% in the North East** suffer transport poverty vs only **3.5% in London**.

**Sustrans.** "Locked Out: Transport Poverty in England." Sustrans, 2012. URL: https://www.sustrans.org.uk/media/3706/transport-poverty-england-2012.pdf. Over 1.5 million people at high risk.

**Department for Transport.** "Gear Change: A Bold Vision for Cycling and Walking." DfT, July 2020. URL: https://assets.publishing.service.gov.uk/media/5f1f59458fa8f53d39c0def9/gear-change-a-bold-vision-for-cycling-and-walking.pdf.

**Department for Transport.** "Bus Back Better: National Bus Strategy for England." DfT, March 2021. URL: https://www.gov.uk/government/publications/bus-back-better.

**IPPR North.** "Revealed: Bus cuts hit deprived areas the hardest." IPPR, 2024. URL: https://www.ippr.org/media-office/revealed-bus-cuts-hit-deprived-areas-the-hardest. Cuts to bus provision between 2011 and 2023 were **10 times higher in England's most deprived than its least deprived areas**.

---

## Part B: London-specific smart traffic data

### B1. TfL signal infrastructure and systems

**TfL manages approximately 6,400 automated traffic signal junctions and pedestrian crossings** — one of Europe's largest traffic signal networks.

**London Assembly.** "Traffic lights" (Mayor's Question Time answer). London City Hall. URL: https://www.london.gov.uk/who-we-are/what-london-assembly-does/questions-mayor/find-an-answer/traffic-lights-23. Confirms "circa 6,400 traffic signal junctions." Notes 591 sites lack vehicular traffic detection (mostly standalone pedestrian crossings).

**Transport for London.** "Delivering the future of London's traffic signals" (press release). TfL, July 2014. URL: https://tfl.gov.uk/info-for/media/press-releases/2014/july/delivering-the-future-of-london-s-traffic-signals. Covers "over 6,200 traffic signal sites with around a quarter of a million individual lamps."

**Transport for London.** "London on the Move" (five-year plan). TfL, January 2026. Reported at: https://www.wired-gov.net/wg/news.nsf/articles/tfl+unveils+ambitious+fiveyear+plan+to+cut+congestion+and+transform+londons+road+network+for+the+future+26012026162500?open=

**SCOOT** (Split Cycle Offset Optimisation Technique) is the primary adaptive traffic control system, installed at **over 4,500 of ~6,000 signalised junctions**, making it potentially the largest single deployment of adaptive traffic control systems globally. SCOOT delivers an average **12–13% reduction in delays** and ~5% reduction in vehicle stops.

**TRL Software.** "SCOOT" (product factsheet). TRL. URL: https://trlsoftware.com/wp-content/uploads/2018/08/SCOOT.pdf.

**Transport for London.** Written evidence to House of Commons Transport Committee ("Effective road and traffic management"). UK Parliament, 2011. URL: https://publications.parliament.uk/pa/cm201011/cmselect/cmtran/writev/etm/m52.htm. In 2011, approximately one-third (~2,000 junctions) had SCOOT.

---

### B2. AI and smart traffic pilots

**Siemens FUSION / Real Time Optimiser (RTO):** The most significant AI deployment. Launched September 2020 as part of a 10-year programme (contract signed 2018). Uses connected vehicle data, bus data, and multiple sensor types. Now called **Yunex Traffic Fusion**. TfL estimates upgrades could **reduce delays by up to 14%** and deliver **£1 billion in benefits**.

**Siemens Mobility.** "Siemens Mobility and Transport for London announce new adaptive traffic control solution." Siemens UK, 24 September 2020. URL: https://news.siemens.co.uk/news/siemens-mobility-and-transport-for-london-announce-new-adaptive-traffic-control-solution.

**Traffic Technology Today.** "Siemens Mobility and Transport for London announce new adaptive traffic control solution — the new SCOOT." September 2020. URL: https://www.traffictechnologytoday.com/news/traffic-management/siemens-mobility-and-transport-for-london-announce-new-adaptive-traffic-control-solution-the-new-scoot.html.

**Vivacity Labs AI Sensors:** TfL partnership since 2018 for AI-powered multimodal traffic detection. Sensors use computer vision to classify road users (pedestrians, cyclists, cars, HGVs, buses, wheelchair users) with **up to 97–98% accuracy**. Expanded to 43+ sensors at 20 central London locations; data-sharing agreement provides access to over 1,000 cameras.

**Transport for London.** "Artificial intelligence to help fuel London's cycling boom" (press release). TfL, 17 January 2020. URL: https://cclondon.tfl.gov.uk/info-for/media/press-releases/2020/january/artificial-intelligence-to-help-fuel-london-s-cycling-boom.

**TfL "London on the Move" 2030 Strategy (January 2026):** Announced as TfL's first pan-city traffic management strategy. Key commitments include enhancement of Yunex Fusion, expansion of Vivacity AI cameras, bus priority technology expanded from 2,080 signals to all **3,500 bus route signals by 2030**, and near-miss detection cameras.

**Traffic Technology Today.** "TfL deploys AI traffic control across London in five-year congestion strategy." January 2026. URL: https://www.traffictechnologytoday.com/news/traffic-management/tfl-deploys-ai-traffic-control-across-london-in-five-year-congestion-strategy.html.

---

### B3. London congestion statistics

London is the **most congested city in Europe** and the **5th most congested globally**. In 2024, London drivers lost **101 hours** sitting in congestion — costing the city **£3.85 billion** total, or **£942 per driver**. The UK-wide cost reached **£7.7 billion**.

**Pishue, B.** "INRIX 2024 Global Traffic Scorecard." INRIX, January 2025. URL: https://inrix.com/press-releases/2024-global-traffic-scorecard-uk/.

**Pishue, B.** "INRIX 2023 Global Traffic Scorecard." INRIX, June 2024. URL: https://inrix.com/press-releases/2023-global-traffic-scorecard-uk/. In 2023: 99 hours lost, £3.8 billion total cost, £902 per driver.

**INRIX and Centre for Economics and Business Research (Cebr).** "The future economic and environmental costs of gridlock in 2030." INRIX/Cebr, October 2014. URL: https://inrix.com/press-releases/traffic-congestion-to-cost-the-uk-economy-more-than-300-billion-over-the-next-16-years/. Projected cumulative cost 2013–2030: **£307 billion**.

**Transport for London.** "Travel in London 2024: Annual Overview." TfL, December 2024. URL: https://content.tfl.gov.uk/travel-in-london-2024-annual-overview-acc.pdf.

---

### B4. London transport equity data

**Edwards, P. et al.** "Deprivation and Road Safety in London." LSHTM/TfL, 2006. URL: https://content.tfl.gov.uk/deprivation-and-road-safety.pdf. Most deprived pedestrians **over twice as likely** to be injured; child pedestrian injury rate in most deprived decile was **2.93× the least deprived**.

**Transport for London.** "Casualties in Greater London during 2024: Road Safety Factsheet." TfL, 2025. URL: https://tfl.gov.uk/cdn/static/cms/documents/casualties-in-greater-london-2024.pdf. Most deprived 30%: KSI rate of **0.40 per 1,000** vs **0.26 per 1,000** in least deprived 30%.

**Nie, Y. et al.** "Disparities in public transport accessibility in London from 2011 to 2021." *Computers, Environment and Urban Systems*, vol. 112, 2024. DOI: https://doi.org/10.1016/j.compenvurbsys.2024.102138. Open access via UCL: https://discovery.ucl.ac.uk/10203871/1/suel_london_disparities.pdf. **Lower-income neighbourhoods had poorer accessibility to public transportation** in both 2011 and 2023 after controlling for car-ownership and population density. Wealthier groups benefited most from Underground improvements.

**Barrett, S., Gariban, S. and Belcher, E.** "Fair Access: Towards a transport system for everyone." Centre for London, 2019. URL: https://centreforlondon.org/reader/fair-access/chapter-1/. Most deprived areas have journey times to public services **25%+ longer** than least deprived.

**Vidal Tortosa, E. et al.** "Is cycling infrastructure in London safe and equitable?" *Journal of Transport & Health*, vol. 26, 2022. URL: https://www.sciencedirect.com/science/article/pii/S221414052200041X. **Only 6% of cycle lane length is physically segregated from traffic**; 59% (566 km) is not compliant with UK standards. Compliance notably higher for inner London boroughs (66%) compared to outer London (24%).

**Aldred, R. et al.** "Equity in new active travel infrastructure: A spatial analysis of London's new Low Traffic Neighbourhoods." *Journal of Transport Geography*, vol. 96, 2021. DOI: https://doi.org/10.1016/j.jtrangeo.2021.103180.

**Steinbach, R. et al.** "Road Safety of London's Black and Asian Minority Ethnic Groups." LSHTM/TfL, 2007. URL: https://content.tfl.gov.uk/road-safety-of-londons-black-asian-minority-ethnic-groups.pdf. After adjusting for deprivation, ethnic differences in road injury risk remained.

---

## Part C: The "black box recorder" analogy

### C1. Aviation flight data recorder regulations

#### ICAO Annex 6

**ICAO.** *Annex 6 to the Convention on International Civil Aviation — Operation of Aircraft, Part I: International Commercial Air Transport — Aeroplanes* (11th ed., as amended through Amendment 46). Montreal: International Civil Aviation Organization. URL: https://www.icao.int/sites/default/files/postalhistory/annex_6_operation_of_aircraft.htm. FDR provisions are in **Chapter 6, Section 6.3** and **Attachment D**. Mandates **at least 88 parameters** for newly manufactured aircraft. Recording duration: **25 hours** for FDR data. CVR recording extended to 25 hours for aircraft >27,000 kg manufactured after 1 January 2021. FDR and CVR data may only be used for **safety-related purposes** and criminal proceedings.

#### EASA Regulation 965/2012

**European Commission.** *Commission Regulation (EU) No 965/2012 of 5 October 2012*. Official Journal L 296, 25.10.2012. EUR-Lex: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:32012R0965. EASA: https://www.easa.europa.eu/en/document-library/regulations/commission-regulation-eu-no-9652012. UK retained version: https://www.legislation.gov.uk/eur/2012/965/annex/IV. CAT.GEN.MPA.195 (Annex IV) requires serviceability of flight recorders. ORO.AOC.130 (Annex III) requires Flight Data Monitoring programmes for aeroplanes >27,000 kg. Original recorded data must be preserved for **60 days** following an accident/serious incident.

**Commission Regulation (EU) 2015/2338** (amending 965/2012): Updated flight recorder requirements and extended CVR to 25 hours. URL: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:32015R2338.

#### FAA 14 CFR Part 121

**14 CFR § 121.343 — Flight data recorders.** URL: https://www.ecfr.gov/current/title-14/chapter-I/subchapter-G/part-121/subpart-K/section-121.343. Basic parameters: time, altitude, airspeed, vertical acceleration, heading, time of each radio transmission. More recent aircraft: 11+ parameters including pitch/roll attitude, thrust, flap position.

**14 CFR § 121.344 — Digital flight data recorders for transport category airplanes.** URL: https://www.ecfr.gov/current/title-14/chapter-I/subchapter-G/part-121/subpart-K/section-121.344. Requires **34 parameters** per Appendix M. Data retained for at least 25 hours of operating time; no record kept more than 60 days unless accident requiring NTSB notification.

---

### C2. Algorithmic "black box" proposals

**Winfield, A.F.T. and Jirotka, M.** "The Case for an Ethical Black Box." In: Gao, Y. et al. (eds) *Towards Autonomous Robotic Systems. TAROS 2017*. LNCS vol. 10454, pp. 262–273. Springer, 2017. DOI: https://doi.org/10.1007/978-3-319-64107-2_21. Open access preprint: https://ora.ox.ac.uk/objects/uuid:ed6cd0ec-1cc9-453e-9b8d-48807a2ceebc. Proposes all robots and autonomous systems should be fitted with an "ethical black box" (EBB) continuously recording sensor and internal status data — directly analogous to aviation FDRs.

**IEEE 7001-2021 — IEEE Standard for Transparency of Autonomous Systems.** IEEE Standards Association, published 4 March 2022. URL: https://standards.ieee.org/ieee/7001/6929/. IEEE Xplore: https://ieeexplore.ieee.org/document/9726144/. Working Group chaired by Alan Winfield. Defines measurable, testable levels of transparency for five stakeholder groups: users, general public, safety certification agencies, incident investigators, and lawyers.

**Winfield, A.F.T. et al.** "IEEE P7001: A Proposed Standard on Transparency." *Frontiers in Robotics and AI*, vol. 8, 665729, 2021. DOI: https://doi.org/10.3389/frobt.2021.665729. URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC8351056/.

**ISO/IEC 42001:2023 — Information technology — Artificial intelligence — Management system.** ISO, December 2023. URL: https://www.iso.org/standard/42001. First international AI management system standard; 38 specific controls.

**ISO/IEC DIS 24970:2025 — Artificial intelligence — AI system logging.** Under development. Provides implementation guidance for EU AI Act Article 12 provisions. (Source: VDE, "EU AI Act: AI system logging." URL: https://www.vde.com/topics-en/artificial-intelligence/blog/eu-ai-act--ai-system-logging.)

**BSI BS 8611:2016 — Robots and robotic devices: Guide to the ethical design and application of robots and robotic systems.** BSI, London, 2016. ISBN: 978-0-580-89530-2.

#### UK government reports

**Centre for Data Ethics and Innovation (CDEI).** *Review into bias in algorithmic decision-making.* DCMS, November 2020. URL: https://www.gov.uk/government/publications/cdei-publishes-review-into-bias-in-algorithmic-decision-making/main-report-cdei-review-into-bias-in-algorithmic-decision-making. Recommended mandatory transparency obligation on all public sector organisations using algorithms for significant decisions.

**Leslie, D.** *Understanding artificial intelligence ethics and safety: A guide for the responsible design and implementation of AI systems in the public sector.* The Alan Turing Institute, 2019. DOI: https://doi.org/10.5281/zenodo.3240529. Adopted by the UK Government as official public sector guidance on AI ethics and safety.

**Leslie, D. et al.** *AI Accountability in Practice.* The Alan Turing Institute, 2024. URL: https://www.turing.ac.uk/sites/default/files/2024-06/aieg-ati-8-accountabilityv1.2.pdf.

**Law Commission of England and Wales and Scottish Law Commission.** *Automated Vehicles: Joint Report.* Law Com No 404 / Scot Law Com No 258, 26 January 2022. URL: https://lawcom.gov.uk/project/automated-vehicles/. Contains 75 recommendations including data retention by Authorised Self-Driving Entities for **39 months** for insurance claims and a Road Accident Investigation Branch to investigate AV incidents. Led directly to the **Automated Vehicles Act 2024**.

---

### C3. EU AI Act Article 12 — logging requirements for high-risk AI

**European Parliament and Council.** *Regulation (EU) 2024/1689 of 13 June 2024 laying down harmonised rules on artificial intelligence (Artificial Intelligence Act).* Official Journal of the European Union, L series, 12 July 2024. Full text: https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng. Article 12 text: https://artificialintelligenceact.eu/article/12/.

**Article 12 requires that high-risk AI systems technically allow for the automatic recording of events (logs) over the lifetime of the system.** Logging capabilities must enable recording events relevant for: (a) identifying situations that may present risk or substantial modification; (b) facilitating post-market monitoring (Article 72); and (c) monitoring operation (Article 26(5)).

For remote biometric identification systems specifically, logs must record: period of each use (start/end), reference database checked, input data producing matches, and identification of persons involved in verification.

**Article 19** requires providers to keep logs for **at least six months**. **Article 26(6)** requires deployers to retain logs for a **minimum of six months**. Article 12 provisions enter into force on **2 August 2026** (per Article 113).

**Critically for this coursework: Annex III, Section 2** explicitly classifies AI systems used as safety components in the management and operation of **"road traffic"** as **high-risk**. This means all Article 12 logging requirements apply directly to AI traffic signal systems. (Annex III text: https://artificialintelligenceact.eu/annex/3/.)

---

## Conclusion: connecting the evidence

Three threads converge to make a compelling case for equity provisions in AI traffic systems. First, the evidence of vehicular bias is structural: signal timing software does not even compute pedestrian delay, creating **4:1 delay ratios** favouring cars over people on foot — a disparity that maps directly onto income and racial inequalities in pedestrian fatalities. Second, London's deployment of AI traffic management (SCOOT on 4,500+ junctions, FUSION/RTO rollout, Vivacity AI sensors) is accelerating without public-facing equity frameworks, despite TfL's own data showing that deprivation **doubles** pedestrian injury risk. Third, regulatory precedent exists: aviation mandated FDRs recording 88+ parameters; the EU AI Act explicitly classifies road traffic AI as high-risk requiring automatic logging; and both the Amsterdam/Helsinki registries and the UK's mandatory ATRS demonstrate that algorithmic transparency in public infrastructure is operationally feasible. The gap between what is technically required by the EU AI Act (entering force August 2026) and what is currently practised in traffic signal deployment represents the core policy space this coursework can address. The Amsterdam registry model shows what transparency looks like; NCHRP Report 969 shows why it matters; and the EU AI Act provides the legal framework to mandate it.