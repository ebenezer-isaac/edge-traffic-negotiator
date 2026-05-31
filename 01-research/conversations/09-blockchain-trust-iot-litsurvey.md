# Blockchain for resource-constrained IoT: a five-vector literature survey

**Blockchain integration in resource-constrained IoT systems for verifiable autonomous decision-making remains an architecturally unsolved problem, but recent literature (2023–2025) reveals converging solutions across five critical dimensions.** The central tension is clear: autonomous infrastructure like traffic signals must act in milliseconds, yet blockchain consensus operates on the order of seconds to minutes. The emerging answer—optimistic "act first, audit later" execution layered atop lightweight DLT with hardware-rooted trust—draws from advances in Rust-based ledgers, TEE-blockchain attestation, Layer 2 rollups, evolving EU AI Act mandates, and the nascent DePIN economic model. This survey catalogues **65+ sources** across these five vectors, prioritizing 2023–2025 publications, and identifies the critical research gaps that remain open.

---

## Vector 1: Lightweight DLT platforms diverge sharply on edge viability

The choice of distributed ledger platform for edge/IoT deployment is not merely a preference—it is a hard resource constraint. The literature reveals a **three-order-of-magnitude gap** between what JVM-based platforms demand and what typical IoT hardware provides, while Rust-based alternatives show promise but lack production benchmarks.

### Hyperledger Besu fails on constrained devices

**Loghin, Dinh, Maw, Chen, Teo, and Ooi (2024)** provide the most directly relevant benchmark in "Blockchain Goes Green? Part II: Characterizing the Performance and Cost of Blockchains on the Cloud and at the Edge," published in *ACM Distributed Ledger Technologies*. They performed the first extensive energy, time, and cost analysis of permissioned blockchains (Hyperledger Fabric and ConsenSys Quorum/Besu) across five hardware platforms including **Nvidia Jetson TX2 and Raspberry Pi 4**. ARM-based cloud instances (Graviton) achieved ~10% higher throughput for Fabric but 25% lower for Quorum compared to Intel Xeon, while costing 35% less. Edge devices exhibited dramatically lower performance across all metrics. This paper establishes the empirical baseline for what is achievable on constrained hardware.

The Hyperledger Besu documentation (2024–2025) itself confirms the problem: **the JVM defaults to consuming 25% of system RAM for heap alone**, meaning an 8 GB device yields only 2 GB of heap—far below the **recommended 5–8 GB heap** for even permissioned network operation. The documentation recommends OpenJ9 for memory-constrained environments (Linux x86-64 only) and explicitly states ARM64 must use OpenJDK, which has higher memory consumption. GitHub issues #3618 (2022) and #5087 (2023, reported by Ethereum core developer Martin Holst Swende) document memory leak failures even on 32 GB machines during intensive EVM operations, confirming that sub-8 GB deployment is essentially impossible for meaningful workloads.

### Hyperledger Fabric runs on edge hardware with caveats

**Sallal et al. (2021)** demonstrated practical deployment of Hyperledger Fabric 1.4 on Raspberry Pi 4 in "Hyperledger Fabric Blockchain for Securing the Edge Internet of Things" (*Sensors*, MDPI). They built custom ARM64 Docker images since **Fabric does not officially support ARM architecture**, deployed via Docker Swarm, and measured transaction throughput using Hyperledger Caliper. Performance was limited but functional. **Khan, Jayasudha, and Jagadeesan (2025)** extended this work in *Journal of VLSI Circuits and Systems*, showing that hardware cryptographic acceleration on Raspberry Pi achieves a **61% reduction in transaction validation latency** and **47% power savings** versus software-only blockchain validation for smart home access control.

**Capocasale, Bianco, and Ferraro (2022)** compared Fabric 2.2, Sawtooth 1.2, and Besu using Hyperledger Caliper in *Blockchain: Research and Applications* (Elsevier), providing multi-dimensional comparison across governance, latency, privacy, and scalability—though not on edge hardware specifically.

### Iroha 2 and Sumeragi consensus: theoretically ideal, empirically unproven

Hyperledger Iroha 2 is written in Rust—among the **top three most power-efficient programming languages**, roughly 3× more efficient than Go and 2× more efficient than Java. Its Sumeragi consensus mechanism requires **3f+1 validators** (where f = simultaneous Byzantine faults tolerated), splitting validators into an active set A (2f+1) and passive observers in set B (f). A deterministic topology overlay based on the previous block hash rotates leaders. Only set A participates actively, potentially reducing communication overhead for small IoT peer networks.

**Buchnik and Wiseman (2020)** analyzed Sumeragi in "FireLedger: A High Throughput Blockchain Consensus Protocol" (*PVLDB*), noting it is "heavily inspired by BChain" but departs through leader broadcast to all nodes. **Cachin and Vukolić (2017)** positioned Sumeragi within the BFT landscape in their seminal survey "Blockchain Consensus Protocols in the Wild," confirming it operates under eventually-synchronous assumptions similar to Tendermint. However, **no independent edge/IoT benchmark of Iroha 2 exists as of 2025**—the platform was reaching RC1 stage during 2024, and independent performance validation remains a critical gap.

### Lightweight alternatives and two-tier architectures

Several 2024–2025 papers propose architectures specifically designed for IoT constraints. **Fathi et al. (2024)** introduced Light-PerIChain in *Computer Communications* (Elsevier), using performance-aware shard assignment with IBFT consensus (requiring only 2f+1 replicas). **Haque, Abbasi, et al. (2024)** proposed DPoS + sharding for IoT data management in *Scientific Reports* (Nature), categorizing devices into "streaming" (sufficient power) and "constrained" (limited power) classes. A 2025 paper in *Discover Internet of Things* (Springer) proposed a **lightweight two-tier blockchain framework**—a local immutable ledger for fast edge processing combined with a cluster-based overlay blockchain—simulated on Cooja (for constrained IoT) and NS3 (40-node overlay). A 2025 analysis in *Sensors* (MDPI) of IOTA's architectural pivot from the feeless DAG-based Tangle 2.0 to IOTA Rebased (Move VM, DPoS via Mysticeti) highlighted the tension between programmability and IoT-friendliness, reporting the Starfish protocol achieving up to **150,000 TPS**.

**Nguyen et al. (2024)** surveyed edge computing and blockchain integration in *Journal of Network and Computer Applications* (Elsevier), establishing that cloud-edge hybrid architectures are the practical near-term path: cloud handles storage and deep learning while edge manages blockchain for secure IoT connectivity.

---

## Vector 2: TEEs anchor trust but are not invulnerable

Trusted Execution Environments provide the hardware root of trust that blockchain-based IoT systems require, but recent research reveals both their power and their limitations. The literature converges on a key insight: **TEEs alone are insufficient; blockchain-based redundancy is necessary to mitigate single-TEE compromise**.

### ARM TrustZone and OP-TEE for IoT security

**Pinto and Santos (2019)** provided the definitive survey in *ACM Computing Surveys*, covering TrustZone for both Cortex-A and Cortex-M processors. They noted that TrustZone-enabled Cortex-M microcontrollers at ~$2 per unit enable secure IoT at scale, but identified critical gaps: limited memory, lack of hardware remote attestation, and side-channel vulnerabilities. **Huang, Zhang, Yan, Wei, and He (2024)** extended this with a systematic comparison of TrustZone and the newer ARM Confidential Computing Architecture (CCA), analyzing their respective security models and attestation capabilities.

**Ling, Yan, Shao, Luo, Xu, Pearson, and Fu (2021)** proposed a hybrid booting approach in *Journal of Systems Architecture* (Elsevier) combining secure boot (Secure World) and trusted boot (Normal World) on TrustZone-based IoT, with paging-based runtime integrity measurement showing negligible performance overhead on Freescale i.MX6Q.

For OP-TEE specifically, **Yuhala, Ménétrey, Felber, Pasin, and Schiavoni (2024)** presented Fortress at *ACM SAC 2024*, securing IoT peripheral I/O memory using ARM TrustZone and OP-TEE with acceptable computational overhead. **Li et al. (2024)** examined TrustZone+OP-TEE for securing PLCs in industrial control systems (arXiv:2403.05448), noting OP-TEE's dependency on Normal World components (tee-supplicant) as a potential weak point.

### TEE-blockchain integration eliminates central trust authorities

**Karanjai, Collier, Gao, Chen, Fan, Suh, Shi, and Xu (2023)** proposed DHTee at *ACM BSCI 2023*—a blockchain-backed mechanism enabling devices with heterogeneous TEEs (Intel SGX, ARM TrustZone) to establish mutual trust without a central authority. The blockchain acts as a "translator" converting TEE-specific attestation to a common format, eliminating single points of failure. **Zhang, Qin, Qu, Wang, Zhang, and Gu (2024)** introduced Janus (arXiv:2402.08908), using Physically Unclonable Functions (PUFs) plus blockchain smart contracts for decentralized TEE attestation—replacing manufacturer-controlled systems like Intel IAS with genuinely decentralized trust.

**Kalapaaking, Khalil, Rahman, Atiquzzaman, Yi, and Almashor (2023)** combined blockchain with SGX-based TEE for secure federated learning in IIoT in *IEEE Transactions on Emerging Topics in Computing*, achieving 98.5% accuracy while protecting model integrity. A 2025 paper in *Digital Communications and Networks* (Elsevier) proposed TrustChain, coupling TEE-based smart contract execution with a DAG-based ledger and VRF-based random node selection to prevent collusion.

### TrustZone vulnerabilities demand defense-in-depth

**Rodrigues, Oliveira, and Pinto (2024)** presented BUSted at *IEEE S&P 2024*, introducing a novel class of microarchitectural side-channel attacks exploiting MCU bus interconnect arbitration logic. The attack **successfully bypasses TrustZone-M isolation** on Cortex-M33 and Cortex-M23 MCUs—affecting potentially billions of IoT devices. Both STMicroelectronics and ARM acknowledged the exploit. **Pouyanrad, Alder, and Mühlberg (2024)** responded with SCFARM at *ESORICS 2024 Workshops*, a tool using symbolic execution to detect timing side channels in compiled TrustZone programs. **Muñoz, Ríos, Román, and López (2023)** provided an exhaustive vulnerability taxonomy in *Computers & Security* (Elsevier), finding that many vulnerabilities stem from improper input validation and poor memory protection in TA implementations.

**Paju, Nurmi, Savimäki, McGillion, and Brumley (2023)** analyzed 223 references in their SoK at *ARES 2023*, finding that IoT/ARM developers face severely limited tooling compared to the Intel SGX ecosystem—**no trusted containers exist for mobile/IoT platforms**, and only limited SDKs are available. This development gap directly impacts TA vulnerability rates.

---

## Vector 3: The millisecond-versus-minutes gap demands optimistic architectures

The latency requirements of autonomous infrastructure are fundamentally incompatible with any form of synchronous blockchain consensus. The literature quantifies this gap and identifies "act first, audit later" as the only viable architectural pattern.

### Traffic signals require millisecond decisions; blockchains deliver seconds

**Almomany, Jarrah, et al. (2025)** documented in *Frontiers* (PMC) that traffic signal control decisions requiring "delays even as short as a few milliseconds can lead to significant difficulties at busy intersections," implementing FPGA-based signal control achieving 7× speedup over general-purpose processors. A 2023 paper in *Sensors* (MDPI) reported that autonomous vehicles process approximately **2 GB/s of real-time data** and "cannot afford to transfer data to cloud/blockchain and wait for responses." Even optimized PBFT consensus operates on the order of seconds at scale, creating a **three to six order-of-magnitude latency gap** between what autonomous infrastructure requires and what blockchain can deliver.

**Adegboyega et al. (2024)** systematically reviewed 35 papers on Hyperledger Fabric latency for IoT in *Internet of Things* (Elsevier), confirming that even permissioned blockchains with optimized consensus face fundamental latency limitations for time-critical applications.

### Layer 2 solutions adapt the optimistic model for IoT

**Lin, Huang, Du, et al. (2023)** proposed ZK-rollup-based access control for IoT in *Sensors* (MDPI), reducing authorization time overhead by **86%** by batching multiple authorization requests into a single zero-knowledge proof. **Lavaur, Lacan, and Chanel (2022)** compared optimistic rollups (which assume transactions are honest and use fraud proofs with challenge periods) versus ZK-rollups (immediate validity proofs) for the Internet of Everything in *Sensors*, proposing tree-structured rollup architectures for heterogeneous device environments. They identified that optimistic rollups are lower complexity and easier to adapt for smart contract execution on constrained devices.

**Mazzante, Mostarda, Navarra, and Sestili (2024)** designed a state channel specifically for IoT at *3PGCIC 2024* (Springer) that **does not require monitoring or synchronizing with the main blockchain**—devices process transactions off-chain using interactive consistency protocols, only interacting with the blockchain at channel open/close. **Bigiotti, Mostarda, Navarra, Pinna, Tonelli, and Vaccargiu (2025)** demonstrated cross-chain state channels for environmental IoT at *AINA 2025*, processing sensor readings off-chain with on-chain settlement for non-repudiation.

### Asynchronous consensus offers a middle path

**Xiao, Zhang, Jin, et al. (2024)** introduced FlexBFT in *Applied Sciences* (MDPI)—an "optimistic asynchronous consensus" that runs a fast partially-synchronous path when network conditions are good and gracefully transitions to an asynchronous slow path during instability, achieving **31.6% lower latency** than baseline BFT. A 2025 paper in *Sensors* proposed RWA-BFT, a reputation-weighted asynchronous BFT scaling to 500 nodes with dual-layer consensus that outperforms both HoneyBadger-BFT and PBFT. A comprehensive 2024 review in *Sensors* surveyed DAG-based asynchronous protocols (Tusk, Bullshark) that separate communication from ordering layers—conceptually parallel to separating execution ("act first") from verification ("audit later").

A 2025 paper in *IoT* (MDPI), "Using Blockchain Ledgers to Record AI Decisions in IoT," proposed logging each AI inference (inputs, model ID, output) to a permissioned blockchain via cryptographically signed smart contract submissions, explicitly aligning with EU AI Act Article 12's logging mandate. A 2024 paper in *Journal of Grid Computing* (Springer) proposed the Smart Traffic Management System (STMS) combining blockchain, IoT, edge computing, and TD3 reinforcement learning, where edge nodes perform real-time traffic analysis while blockchain ensures post-hoc data integrity—an explicit act-first-audit-later implementation.

---

## Vector 4: Liability frameworks are catching up to autonomous reality

The legal and regulatory landscape for autonomous infrastructure is rapidly evolving, with the EU AI Act establishing the most comprehensive framework and the "ethical black box" concept maturing from analogy to demonstrated technology.

### The EU AI Act explicitly targets traffic management AI

AI systems managing road traffic are **explicitly listed as high-risk in the EU AI Act's Annex III** under the "critical infrastructure" category, as documented by Taylor Wessing (2024–2025) and Bird & Bird (2023–2024). This means autonomous traffic signal systems face the full force of regulatory requirements: transparency logs, conformity assessments, human oversight, continuous monitoring, bias testing, and third-party auditing. Most obligations take effect by August 2026.

**Buiten, de Streel, and Peitz (2023)** analyzed liability allocation along the AI value chain in *Computer Law and Security Report*, finding that strict liability is the appropriate rule for novel AI risks and identifying the "problem of many hands" in AI development. **Buiten (2024)** extended this in *European Journal of Law and Economics*, proposing that liability standards should align with relative control and awareness of risk. **Giannini and Kwik (2023)** compared criminal liability frameworks across Singapore, France, and the UK in *Criminal Law Forum*, identifying how classical negligence concepts (foreseeability, awareness) break down when AI causes harm. **Gless and Ligeti (2024)** analyzed EU criminal liability for driving automation in *New Journal of European Criminal Law*, noting that AI systems "cannot meaningfully decide to comply with or violate the law."

**Botero Arcila (2025)** at Mozilla Foundation directly named "a municipality making use of AI to control traffic through variable speed limits and road closures" as a liability scenario, providing a framework for how liability flows from AI developers to municipal operators to affected citizens. The Brookings Institution (MacCarthy and Merrill, 2025) proposed a **federal victim compensation fund** for autonomous vehicle incidents, arguing that fault-based insurance frameworks are ill-suited to autonomous technology—a model potentially applicable to autonomous infrastructure.

### The blockchain black box moves from concept to flight

**Winfield and Jirotka (2017)** established the foundational "ethical black box" (EBB) concept at *TAROS 2017*, proposing that autonomous systems should carry flight-data-recorder equivalents. Winfield, van Maris, Salvini, and Jirotka (2022) followed with a draft open standard (arXiv:2205.06564). **White and Caiazza (2019)** proposed the "Black Block Recorder"—immutabilizing robot log records via blockchain integrity proofs and distributed ledgers to prevent post-mortem tampering.

Stanford University researchers (~2020) developed a distributed "black box" audit trail specification for connected vehicles using distributed hash tables, parity systems, and public blockchain. Most recently, the **University of Southampton and Minima Blockchain (March 2026)** demonstrated the world's first blockchain-based "black box" system running on autonomous drone hardware during live flight, achieving **500× performance gain** and **up to 10,000% energy efficiency improvement** by running blockchain directly on a microprocessor SoC—the Integritas platform provides proof of accountability aligned with EU AI Act requirements.

The OECD's 2025 issues note "Artificial Intelligence for Advancing Smart Cities" documented Barcelona's AI governance principle that **"responsibility remains with the city, not the algorithm"**—establishing that municipalities cannot delegate accountability to AI systems. **Wolniak and Stecuła (2024)** reviewed AI barriers in smart cities in *Smart Cities* (MDPI), identifying accountability gaps, algorithmic bias, and citizen participation as persistent challenges.

---

## Vector 5: DePIN economics could bootstrap traffic infrastructure networks

The DePIN sector grew from **$3.1B to $11.8B market capitalization** between April 2023 and March 2024 (326% increase), with over **13 million devices** actively participating in DePIN networks daily as of 2024. However, applying DePIN models to traffic management remains entirely conceptual—no published research deploys token incentives for traffic light or signal infrastructure specifically.

### Academic foundations for DePIN are solidifying

**Ballandies et al. (2024)** proposed the first comprehensive DePIN taxonomy at *IEEE ICBC 2024*, identifying 8 components and 41 attributes across three dimensions: distributed ledger technology, cryptoeconomic design, and physical infrastructure. A companion 2024 paper in *IEEE Network* presented a five-layer architecture (physical, data, governance, blockchain, application) and four design principles. **Ballandies et al. (2025)** refined classification in arXiv:2501.17416, distinguishing DePIN-LI (location-independent, fungible resources) from DePIN-LD (location-dependent, non-fungible)—traffic infrastructure falls firmly in the DePIN-LD category where geographic placement is critical.

A 2025 scoping review in *Frontiers in Blockchain* formalized the **"DePIN Flywheel"**: token incentives drive supply growth, which improves network quality, which attracts demand, which captures value, which strengthens rewards. The review analyzed Burn-and-Mint Equilibrium (BME) mechanisms, staking/slashing, and multi-token frameworks across Helium, Filecoin, Render, Akash, and Hivemapper. The critical finding: **the "demand bottleneck" is DePIN's existential challenge**—sustainability requires converting non-Web3 users into paying customers. **Chiu, Mahajan, Ballandies, and Kalabić (2024)** positioned DePIN as an evolution of participatory sensing in arXiv:2405.16495, developing formal threat models for malicious data submission, Sybil attacks, and free-riding.

### Closest existing analogs: vehicles and maps, not traffic lights

Helium (400,000+ active hotspots, 576 TB data offloaded in Q4 2024, migrated from custom blockchain to Solana in April 2023) provides the canonical DePIN case study. Its "Lazy Claiming" architecture (oracles track earnings off-chain; users claim on-demand) and Proof of Coverage mechanism (beaconing every 6 hours with cryptographic witness verification) offer directly transferable design patterns. DIMO (280,000+ vehicles on Polygon) gives vehicles on-chain identity as "digital twins," while Hivemapper (330M+ km mapped on Solana, surpassing Google Street View's early pace) demonstrates decentralized road data collection.

**peaq Network** (mainnet November 2024, 2M+ devices, partnerships with Bosch, Continental, Airbus, Deutsche Telekom) is purpose-built for the "Machine Economy" where vehicles, robots, and sensors act as autonomous economic agents. Its modular functions—Self-Sovereign Machine IDs, machine payments, role-based access, data verification—are the closest existing platform to the concept of traffic lights as economic agents.

### Infrastructure as autonomous economic agents

**Xu et al. (2026)** proposed "The Agent Economy" (arXiv:2602.14219), a five-layer architecture for autonomous AI agents as economic peers to humans, with DePIN protocols as the physical infrastructure layer. W3C DIDs provide identity, account abstraction enables economic settlement, and "Agentic DAOs" govern collective behavior. A 2025 survey (arXiv:2601.04583) reviewed 317 works on agent-blockchain interoperability, contributing a five-part taxonomy of integration patterns from read-only analytics to multi-agent workflows. A 2025 paper in *Scientific Reports* (Nature) demonstrated a blockchain framework achieving **3× throughput increase and 30% latency reduction** with 98.2% threat detection for smart city applications including traffic management.

**Caprolu, Raponi, and Di Pietro (2025)** provided the first dedicated security and privacy analysis of DePIN in *LNCS* (Springer), identifying unique attack surfaces in permissionless physical infrastructure networks. Legal analysis by Aurum Law (2025) outlined token classification uncertainty, AML compliance, GDPR constraints, and governance liability as barriers to public infrastructure DePIN deployment.

---

## Critical research gaps and cross-cutting synthesis

Five significant gaps emerge from this survey that represent high-value research opportunities at the intersection of these vectors.

**No integrated benchmark exists for lightweight DLT + TEE on IoT hardware.** While Fabric has been tested on Raspberry Pi and TEEs have been characterized on Cortex-M, no study combines a lightweight blockchain platform (especially Iroha 2) with TrustZone/OP-TEE on the same constrained device to measure combined resource consumption and security properties.

**The "act first, audit later" pattern lacks formal security analysis for safety-critical infrastructure.** Optimistic rollup challenge periods (typically 7 days) designed for DeFi require fundamental rethinking for traffic systems where incorrect decisions can cause immediate physical harm. No framework exists for determining appropriate challenge periods, evidence requirements, or dispute resolution mechanisms for autonomous physical infrastructure.

**Traffic infrastructure as DePIN-LD economic agents is entirely uncharted.** Despite mature DePIN taxonomies, tokenomics models, and agent-economy architectures, no research applies these to government-owned, safety-critical infrastructure. The economics of tokenizing public infrastructure differ fundamentally from consumer-deployed hardware—involving public procurement law, municipal liability, and regulatory compliance that existing DePIN models do not address.

**TEE-anchored blockchain attestation for autonomous decision accountability is underexplored.** The combination of TEE-based secure decision execution, blockchain-based immutable logging (the "ethical black box"), and EU AI Act compliance requirements creates a natural system architecture that no paper has fully specified for smart city infrastructure.

**Legal frameworks have not addressed the specific scenario of token-incentivized autonomous public infrastructure.** The EU AI Act covers high-risk AI in critical infrastructure, and DePIN legal analyses address token classification—but the intersection (a municipally deployed, token-incentivized, autonomously acting traffic management system) creates novel legal questions about liability allocation, regulatory jurisdiction, and democratic accountability that no current framework resolves.

## Conclusion

The literature reveals a field converging on a recognizable architecture: **Rust-based lightweight ledgers running on TEE-equipped edge devices, executing optimistic local decisions with asynchronous blockchain audit trails, governed by crypto-economic incentives and subject to evolving AI liability frameworks**. Each vector has matured substantially between 2023 and 2025—Fabric runs on Raspberry Pi, TrustZone-blockchain attestation eliminates central authorities, state channels enable IoT without continuous blockchain synchronization, the EU AI Act mandates decision logging for traffic AI, and DePIN economics have been validated at 13-million-device scale.

Yet no paper synthesizes all five vectors into a unified system. The two-tier architecture—local lightweight ledger at the edge for millisecond decisions, overlay blockchain for cryptographic audit and economic settlement—emerges as the most promising integration pattern. Traffic signals acting as TEE-secured, token-incentivized autonomous agents that log decisions to an immutable blockchain black box represents a feasible but unbuilt system. The research community has constructed all the necessary components; the integration challenge—and the legal framework to govern it—remains the frontier.