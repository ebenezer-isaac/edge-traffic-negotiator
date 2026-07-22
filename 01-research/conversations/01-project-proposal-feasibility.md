> **SUPERSEDED HISTORICAL RECORD (pre-2026-05-31-pivot).** Dated measurement log / transcript kept for the audit trail; the current thesis is in specs/001-edge-negotiator/MASTER-SPEC.md (Euston A501; self-referential coupling; CT-style accountability; Phi-4-mini). Forbidden-term hits below are historical, not current claims.

Decentralized Autonomous Traffic Optimization using Blockchain-Anchored Edge AI: A Feasibility Study and Research Roadmap
Executive Summary
The convergence of Edge AI, Small Language Models (SLMs), and Distributed Ledger Technology (DLT) is reshaping the architecture of industrial IoT systems. This report provides an exhaustive technical analysis of two proposed MSc dissertation projects, with a primary focus on "The Edge Negotiator," a system designed to facilitate decentralized traffic optimization via blockchain-anchored agentic negotiation. This study evaluates the feasibility, industry alignment, and academic merit of deploying Microsoft Foundry Local, Phi-3/4 Mini models, and Nethereum on resource-constrained hardware to solve complex coordination problems in air-gapped environments.
The analysis confirms that while Option 2 ("The Offline Sentinel") offers a low-risk, implementation-heavy path suitable for demonstrating data privacy, Option 3 ("The Edge Negotiator") presents a significantly higher research value proposition. It aligns aggressively with emerging industry trends such as Decentralized Physical Infrastructure Networks (DePIN) and Agentic AI. However, the integration of blockchain into real-time control loops introduces critical latency challenges that necessitate a shift from synchronous consensus to an "Optimistic Execution with Post-Hoc Audit" architecture.
This report outlines a comprehensive architectural blueprint for the "Edge Negotiator," proposing the use of the Microsoft Agent Framework (Semantic Kernel) for inter-node reasoning and a Simulated Azure Confidential Ledger for immutable liability logging. By pivoting the blockchain’s role from a "gatekeeper" to a "black box recorder," the project can satisfy the rigorous real-time constraints of traffic management while delivering the auditability required by regulated sectors. The recommended roadmap leverages high-efficiency SLMs (Phi-3 Mini) and optimized C# integration patterns to deliver a distinct, distinction-grade dissertation within a three-month timeline.
1. Introduction: The Paradigm Shift to Local-First Industrial AI
The industrial internet is undergoing a fundamental bifurcation. For the past decade, the dominant architectural pattern has been "Cloud-Native," characterized by centralization, massive scalability, and dependency on constant connectivity. However, a counter-movement toward "Edge-Native" or "Local-First" architectures is gaining momentum, driven by the rigid constraints of regulated industries such as defense, healthcare, and critical urban infrastructure. In these sectors, the latency of a round-trip to the cloud is a safety hazard, and data sovereignty requirements often mandate that sensitive sensor data never leaves the physical premise.
1.1 The Strategic Imperative of Microsoft Foundry Local
Microsoft’s introduction of Foundry Local represents a tacit acknowledgement that the future of enterprise AI is hybrid. While large foundational models (GPT-4o) reside in the cloud, the operational edge requires Small Language Models (SLMs) that are capable of reasoning, instruction following, and function calling without internet access. Foundry Local abstracts the immense complexity of hardware acceleration—managing the interface between the model weights (GGUF or ONNX formats) and the underlying silicon (NPU, GPU, or CPU) via the ONNX Runtime.
For an MSc dissertation in the Internet of Things (IoT), adopting Foundry Local is not merely a tooling choice; it is a strategic alignment with the "thick edge" architectural pattern. It demonstrates an understanding that future IoT devices will not just be dumb sensors feeding a cloud brain, but autonomous agents capable of local semantic processing. This project aims to validate whether current SLMs, specifically the Phi-3 and Phi-4 families, possess sufficient reasoning fidelity to act as control logic for critical infrastructure when deployed on constrained hardware like the Raspberry Pi 5 or Intel NUC.
1.2 Navigating Supervisor Expectations: The Dual-Constraint Optimization
A successful dissertation must satisfy two distinct sets of criteria, represented by the academic and industrial supervisors. This duality shapes the technical direction of the proposed project.
Academic Rigor (Akin Delibasi, UCL):
The academic supervisor requires a contribution to knowledge that extends beyond a mere software demonstration. For "The Edge Negotiator," the focus must be on Distributed Systems Theory and Algorithmic Game Theory. The project cannot simply "use" blockchain; it must critically evaluate the trade-offs of decentralized consensus in real-time environments. Akin will look for a rigorous analysis of:
Latency vs. Security: Quantifying the cost of cryptographic verification in a control loop.
Consensus overhead: Measuring the CPU and RAM contention between the consensus client (Geth/Besu) and the inference engine (Phi-3).
Theoretical Validity: Justifying the negotiation algorithm—why is an Agentic LLM better than a standard PID controller or a heuristic algorithm?
Industry Relevance (Lee Stott, Microsoft):
The industrial supervisor focuses on the application of the Microsoft stack to solve high-value business problems. Lee Stott, as a Principal Cloud Advocate, is deeply invested in the developer experience of Semantic Kernel and the Microsoft Agent Framework. He will value:
Architectural Patterns: How "Local-First" AI can eventually sync with cloud services (like Azure Confidential Ledger) for global visibility.
Use Case Innovation: Moving beyond "chat" interfaces to "agentic" workflows where the AI controls physical systems (Cyber-Physical Systems).
DePIN Alignment: The project’s relevance to the burgeoning field of Decentralized Physical Infrastructure Networks, where blockchain incentivizes and secures edge compute resources.
2. Technical Landscape and Literature Review
To justify the architectural decisions for the "Edge Negotiator," we must establish the current state of the art across three domains: Edge Inference, Blockchain IoT Integration, and Autonomous Traffic Management.
2.1 Small Language Models (SLMs) at the Edge
The viability of running reasoning agents on edge devices hinges on the recent explosion in SLM efficiency. Unlike their larger counterparts, SLMs like Phi-3 Mini (3.8B) are trained on highly curated "textbook quality" data, allowing them to punch significantly above their weight class in logic and reasoning tasks, even if their world knowledge is more limited.
Quantization and Memory Bandwidth:
Running these models on edge hardware (e.g., Raspberry Pi 5 or consumer laptops) requires aggressive quantization.
INT4 Quantization: Reduces the model size by approximately 75% with negligible accuracy loss for reasoning tasks. A 3.8B parameter model at INT4 precision requires roughly 2.5 GB of VRAM/RAM.
Memory Bandwidth Utilization (MBU): On CPU-only devices, inference speed is strictly bound by memory bandwidth. The Raspberry Pi 5, with its LPDDR4X memory, offers roughly 34 GB/s bandwidth. Benchmarks suggest that Phi-3 at INT4 on a Pi 5 can achieve 2-6 tokens per second (TPS). This is a critical constraint for real-time systems; a detailed response (100 tokens) could take 20-50 seconds, which is unacceptable for traffic control. Thus, the system design must minimize token generation, relying on structured JSON outputs and short "reasoning" bursts.
ONNX Runtime (ORT) vs. Llama.cpp:
While the open-source community often defaults to llama.cpp (GGUF), Microsoft Foundry Local leverages the ONNX Runtime. ORT provides significant optimizations for the Windows ecosystem, including DirectML support, which can accelerate inference on any DirectX 12 capable GPU (including integrated Intel/AMD graphics). For the proposed project, using ORT via the Foundry SDK ensures alignment with Microsoft’s "paved path" and offers better integration with C#.NET environments compared to Python-heavy alternatives.
2.2 Blockchain in Resource-Constrained IoT
Integrating Distributed Ledger Technology (DLT) into IoT introduces the "Blockchain Trilemma" (Security, Scalability, Decentralization) into an environment already constrained by power and compute.
The Latency Mismatch:
Standard public blockchains (Ethereum Mainnet) have block times of ~12 seconds and finality times of minutes. Even high-performance private chains (like standard Geth PoA) typically run at 1-5 second block times. A traffic light decision—detecting an ambulance and switching to green—must occur in the 100-300 millisecond range to ensure safety. A naïve implementation that blocks the traffic light change until the transaction is confirmed on-chain is operationally infeasible and dangerous.
Cryptographic Overhead on ARM:
The signing of transactions (using the ECDSA algorithm on the secp256k1 curve) is computationally non-trivial for low-power ARM cores. Historical benchmarks of Nethereum (the standard.NET Ethereum library) have shown that unoptimized signing processes can take hundreds of milliseconds on constrained hardware. This CPU contention is dangerous when the same core is trying to run an LLM inference. The architecture must essentially decouple these processes—ensuring that the "heavy lifting" of the blockchain (mining/validating) does not occur on the same silicon as the "heavy lifting" of the AI (inference).
Azure Confidential Ledger (ACL) and CCF:
For enterprise scenarios, the industry standard is moving toward Confidential Consortium Framework (CCF). ACL, built on CCF, runs a permissioned ledger inside hardware-backed secure enclaves (SGX/SEV). This allows for centralized-speed throughput with decentralized verifiability. While the student cannot deploy a full SGX enclave on a Raspberry Pi, simulating this architecture using a local CCF node or a private Besu network creates a "digital twin" of a production-grade enterprise setup, which directly appeals to the Industry Supervisor’s interests.
2.3 Decentralized Traffic Control Systems
Traditional traffic management relies on centralized systems like SCATS or SCOOT, which optimize macroscopic flow but struggle with microscopic, real-time negotiation (e.g., a specific ambulance vs. a specific platoon of trucks).
Agent-Based Negotiation:
Moving to a decentralized model implies treating each intersection and vehicle as an autonomous agent. The literature on V2I (Vehicle-to-Infrastructure) communication, specifically standards like SAE J2735, defines the message formats (Basic Safety Messages). However, the logic for negotiation—determining who yields—is typically heuristic. Introducing an LLM allows for semantic negotiation. Instead of rigid rules ("Ambulance always wins"), the agents can reason: "I am an ambulance, but I am empty and returning to base. You are a bus with 50 people late for work. You go first." This nuance is the core innovation of the proposed dissertation project.
3. Comparative Analysis: Sentinel vs. Negotiator
To determine the optimal project path, we must weigh the "Safe" option against the "High-Reward" option, considering the specific constraints of a 3-month timeline and the dual supervisor requirements.
3.1 Option 2: The "Offline Sentinel" (Critique)
Concept: An air-gapped security monitor that summarizes video feeds using a local SLM.
Pros:
Low Technical Risk: The pipeline is linear: Video -> Object Detection (YOLO) -> Text Description -> SLM Summarization. This is well-trodden ground.
Privacy Narrative: The "Air-Gapped" angle is a strong, easily defensible story for GDPR and defense applications.
Foundry Alignment: It perfectly showcases the "download and run offline" capability of Foundry Local.
Cons:
Low Academic Novelty: "Video summarization" is a saturated research field. Unless the student invents a novel compression algorithm or a new way of mapping visual tokens to text, the academic contribution is thin.
Limited Complexity: Ideally, an MSc project should demonstrate complexity. Once the pipeline is built, there is little "tuning" to do other than prompt engineering.
No Blockchain: The user explicitly stated a desire to work with blockchain. Adding blockchain to this project (e.g., hashing logs) feels forced and tangential.
3.2 Option 3: The "Edge Negotiator" (Defense)
Concept: Autonomous traffic intersections using blockchain-anchored agentic negotiation.
Pros:
High Academic Novelty: It combines Game Theory (bidding), Distributed Consensus (blockchain), and LLM Reasoning. This multidisciplinary approach provides ample material for the dissertation’s "Analysis" chapters.
High Industry Relevance: It touches on DePIN, Smart Cities, and Agentic AI—three of the hottest topics in 2026.
Rich Evaluation Metrics: There are many variables to benchmark: Latency (Blockchain vs. AI), Traffic Throughput (Flow efficiency), Economic Efficiency (Gas costs vs. Time saved), and Reasoning Accuracy (Did the AI make the right choice?).
Cons:
High Implementation Risk: Integrating SUMO (Traffic Sim), Foundry Local (AI), and Nethereum (Blockchain) is a complex systems integration challenge.
Performance Trap: As noted, if the architecture is synchronous, the traffic lights will be dangerously slow.
Verdict:
Option 3 is the superior choice for a Distinction-grade dissertation, provided the "Performance Trap" is mitigated through an asynchronous architecture. It offers the "Black Box" audit trail as a killer feature—answering the "Who is liable?" question that currently stalls autonomous vehicle adoption.
4. Architectural Blueprint: The Edge Negotiator (Refined)
To make Option 3 feasible within 3 months while satisfying the rigorous requirements of real-time traffic control, we propose a refined architecture: "Optimistic Execution with Post-Hoc Audit."
4.1 System Topology
The system simulates a Cyber-Physical System (CPS) where the "Physical" layer is the SUMO simulator, and the "Cyber" layer is a network of.NET Agents.
LayerComponentTechnology StackRolePhysical (Sim)SUMO (Simulation of Urban MObility)TraCI / C#Simulates vehicles, roads, and traffic lights. Generates the "visual" state.PerceptionVirtual SensorsC# / TraCIExtracts state (e.g., "Vehicle X at -100m, Speed 50km/h") from SUMO.CognitionTraffic AgentMicrosoft Agent Framework (Semantic Kernel) + Phi-3 MiniReceives state, reasons about priority, and issues commands.ActionControllerC# / TraCIExecutes the Agent's decision (e.g., SetPhase(Green)).VerificationAudit LoggerNethereum + Besu/Geth (PoA)Hashes the {State + Decision + Reasoning} and anchors it to the ledger.
4.2 The Agentic Layer: Microsoft Agent Framework
Instead of writing monolithic code, the student will implement the system as a Multi-Agent System using the Microsoft Agent Framework (which unifies Semantic Kernel and AutoGen).
The Intersection Agent:
This agent is the "Brain" of the traffic light. It is equipped with a specific persona ("You are a safety-critical traffic controller...") and a set of Plugins (Tools):
GetTrafficState(): Returns a JSON of the current queue.
SwitchLight(direction): Changes the SUMO traffic light phase.
BroadcastBid(amount, urgency): Communicates with other agents.
The Negotiation Protocol:
When an Ambulance Agent approaches, it triggers a negotiation event.
Ambulance: Sends a structured message: {"id": "AMB-01", "type": "emergency", "urgency": 5, "destination": "Hospital_N"}.
Intersection Agent: Ingests this message into the Phi-3 context window.
Reasoning: Phi-3 evaluates the urgency against its current state.
Input: "Urgency 5 request from AMB-01. Current cross-traffic is 20 cars (Urgency 1)."
Thought Process: "Emergency urgency (5) > Aggregate commuter urgency (1). Safety protocols dictate immediate priority."
Output: Calls SwitchLight(Ambulance_Direction).
4.3 The Trust Layer: The "Black Box" Ledger
This is the critical innovation that integrates blockchain without killing performance.
The "Optimistic" Flow:
T=0ms: Perception Layer detects Ambulance.
T=50ms: Intersection Agent makes the decision (using Phi-3).
T=60ms: Controller executes SwitchLight(Green). The traffic light changes immediately.
T=65ms (Async): The Agent constructs a "Decision Proof" JSON containing:
Timestamp.
Input State Hash (The specific vehicle positions).
The Reasoning Trace (Phi-3's explanation).
The Action Taken.
T=100ms: The Agent signs this JSON with its private key (Device Identity).
T=200ms+: The signed payload is sent to the local Blockchain Node (Simulated Azure Confidential Ledger) via Nethereum.
T=5000ms: The block is mined. The decision is now immutable.
The Value Proposition:
If an accident occurs at T=70ms, investigators can look at the blockchain. They will see the exact state and reasoning the AI used. If the AI turned green without a valid reason, the immutable log proves the malfunction. This "Liability Layer" is what makes the project industry-relevant for Lee Stott.
4.4 Hardware Implementation Strategy
To simulate this realistically without buying expensive hardware:
The "Server" (Laptop): Runs the SUMO simulation, the Blockchain Node (Besu/Geth), and the "Ambulance" agents.
The "Edge Device" (Raspberry Pi 5 / Optional): Runs the Intersection Agent (Foundry Local + Phi-3).
Networking: The Laptop and Pi communicate via LAN (or Wi-Fi). The Pi controls the SUMO simulation remotely via the TraCI TCP interface.
RAM Contention Warning:
If a Raspberry Pi 5 (8GB) is used, do not run the blockchain node on it. The Phi-3 model will consume ~3GB, the OS ~1GB, and the.NET runtime ~500MB. A blockchain node can easily spike RAM usage. The Pi should act only as the signer (Light Client), submitting transactions to the node running on the Laptop.
5. Critical Challenges, Pitfalls, and Mitigations
5.1 Latency Analysis and The "Token Tax"
The Pitfall: Generating text is slow. On a Pi 5, generating a 50-word explanation might take 10 seconds.
The Mitigation: Token Economy.
Do not ask the model to "explain" in every cycle.
Use constrained generation (grammar-based sampling) to force the model to output a single token for the decision (e.g., 1 for Green, 0 for Red) or a tiny JSON {"a":"G"}.
Only trigger the "Reasoning/Explanation" generation after the decision is executed, in the background thread that prepares the blockchain log. The control loop must remain tight; the audit log can lag.
5.2 Hallucination in Control Systems
The Pitfall: Phi-3 might hallucinate a rule ("Blue cars have priority on Tuesdays").
The Mitigation: Retrieval-Augmented Generation (RAG) for Rules.
Inject the "Traffic Code" as a system prompt or via RAG.
Implement a deterministic "Safety Layer" (Guardrail) in C# code that sits between the AI and the Traffic Light. If the AI commands "Green" but the cross-traffic sensors show movement, the Guardrail overrides the AI and triggers an emergency stop. This demonstrates a "Human-in-the-Loop" (or Code-in-the-Loop) safety architecture, which is essential for certification.
5.3 Nethereum Signing Performance
The Pitfall: As identified in research snippets, Nethereum's signing speed can be a bottleneck on ARM devices if not optimized.
The Mitigation:
Use the EthECKey.SignRecoverable = true setting.
Ensure the .NET 9 runtime is used, as it has significant optimizations for ARM64 instructions (Neon) compared to older versions.
If signing is still too slow (>200ms), offload the signing to a dedicated secure element or simulate it by signing batches of decisions rather than every single micro-decision.
6. New Research Vectors: DePIN and ZKML
To elevate the dissertation from "Competent" to "Distinction," the student should frame the project within these cutting-edge narratives.
6.1 DePIN: Traffic Lights as Economic Agents
Decentralized Physical Infrastructure Networks (DePIN) utilize crypto-economic incentives to bootstrap physical networks.
Research Angle: Frame the Traffic Light not just as a controller, but as a DePIN Node. It "earns" tokens by optimizing flow and "spends" tokens to buy electricity or pay for maintenance.
Implemen

The software you are looking for is Eclipse SUMO (Simulation of Urban MObility).

It is actually listed right in the architectural blueprint you shared (specifically under Section 4.1: System Topology)! It is incredibly easy to lose track of specific tools when juggling a technology stack this dense.

Here is a quick refresher on why SUMO is the industry and academic standard for the type of Proof of Concept you are building:

Microscopic Simulation: Unlike macroscopic tools that model traffic as a continuous fluid, SUMO tracks the exact location, speed, and route of every single vehicle, pedestrian, and traffic light. Your project relies on this microscopic detail so your Phi-3 agents can negotiate priority for specific entities (like your "AMB-01" ambulance).

TraCI (Traffic Control Interface): This is the API layer that makes your "Cyber-Physical System" possible. TraCI allows you to run SUMO as a server and step through the simulation programmatically. You can use it to extract the current intersection state, feed it to your C#/.NET agents, and then send commands back to instantly alter the traffic light phases.

Open Source Ecosystem: Managed by the Eclipse Foundation and heavily utilized by the German Aerospace Center (DLR), it is entirely free and has a massive library of pre-built urban road networks you can import directly from OpenStreetMap.

Would you like me to map out how to configure the TraCI TCP connection between your C# application and the SUMO simulator so you can start building out your perception layer?



During research for this, i was told there is a opensource traffic simulator software that i can use to make poc of this. I forgot the name