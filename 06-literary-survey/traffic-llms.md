# Section A — Annotated literature table

| Short-tag | Title | Year | Direct PDF URL | LLM/SLM used | Baselines compared | Dataset/simulator | Key empirical claim | Relevance to Edge Negotiator |
|---|---|---|---|---|---|---|---|---|
| LLMLight | LLMLight: Large Language Models as Traffic Signal Control Agents | 2024 (KDD'25) | https://arxiv.org/pdf/2312.16044 | GPT-3.5/4, Llama-2 7/13/70B, Qwen2 0.5/7/72B; LightGPT (FT) | FixedTime, MaxPressure, MPLight, AttendLight, PressLight, CoLight, Eff-/Adv-CoLight | CityFlow — Jinan(12), Hangzhou(16), NY(196) | LightGPT-Llama-13B matches/beats Adv-CoLight on ATT; LightGPT-Qwen-0.5B beats Llama-70B unfine-tuned | Foundational LLM-as-controller; LightGPT-0.5B/8B variants are quantization-ready for cabinet hardware |
| CoLLMLight | Cooperative LLM Agents for Network-Wide TSC | 2025 | https://arxiv.org/pdf/2503.11739 | Llama-3.1-8B FT (CoLLMLight-8B); also Llama-3.3-70B, Qwen-2.5-72B, GPT-4o | FixedTime, MaxPressure, MPLight, CoLight, Adv-CoLight, LLMLight | CityFlow Jinan/Hangzhou/NY | Beats LLMLight + Adv-CoLight on ATT/AQL across all settings via spatiotemporal neighbour passing | Direct template for multi-LLM borough coordination; 8B FT model is borderline-edge |
| Traffic-R1 | Reinforced LLMs Bring Human-Like Reasoning to TSC | 2025 | https://arxiv.org/pdf/2508.02344 | **Qwen2.5-3B** + 2-stage agentic RL (STPO) | FixedTime, MaxPressure, MPLight, CoLight, Adv-CoLight, LLMLight, CoLLMLight-8B, GPT-4o, Llama-3.3-70B, Qwen-2.5-72B | CityFlow Jinan/Hangzhou/NY + 6-week real city A/B (10 ints, 55k drivers/day) | **>30% improvement on OOD vs LLMLight; >5% queue cut in real production** | Closest analogue to Edge Negotiator: 3B SLM, edge-targeted, multi-intersection, real deployment |
| HeraldLight | Dual-LLM Architecture with Herald-Guided Prompts | 2025 | https://arxiv.org/pdf/2511.00136 | Llama-3.1-8B (LoRA) Agent + ChatGPT Critic | LLMLight, Adv-CoLight, MPLight, RL/transport SOTA | CityFlow Jinan/Hangzhou/NY (224 ints) | **−20.03% ATT, −10.74% AQL** vs SOTA; 40-s queue forecast horizon | Demonstrates LLM control at 196-int NY scale comparable to a borough |
| CuraLight | Debate-Guided Data Curation for LLM TSC | 2026 | https://arxiv.org/pdf/2604.05663 | Gemma-3 LoRA + DeepSeek-V3/R1 ensemble | Transport, RL, LLMLight | SUMO Jinan/Hangzhou/Yizhuang | −5.34% ATT, −5.14% AQL, −7.02% AWT; ~28.5% over base Gemma-3 | One of few SUMO + sub-7B FT works |
| LA-Light | LLM-Assisted Light: Tool-Using LLM for Long-Tail TSC | 2024 | https://arxiv.org/pdf/2403.08337 | GPT-4 + tool calls to RL/rule controllers | Webster, MaxPressure, FRAP, CoLight, UniTSA | SUMO/TSHub, sensor-failure + emergency scenarios | Reduces avg waiting time **20.4%** under sensor outage vs RL | Template for hybrid LLM+classical fallback architecture |
| iLLM-TSC | Integration of RL + LLM for Policy Improvement | 2024 | https://arxiv.org/pdf/2407.06025 | GPT-4 verifier on top of PPO RL | FixedTime, RL, EMVLight, SARL-TSC | SUMO/TSHub; packet-loss + emergency | **−17.5% wait under degraded comms; −62.9% emergency wait vs SARL** | Direct precedent for RL-primary + LLM-override safety pattern |
| VLMLight | Vision-Language Meta-Control with Dual-Branch Reasoning | NeurIPS 2025 | https://arxiv.org/pdf/2505.19486 | Qwen2.5-VL-32B + Qwen2.5-72B (3-agent dialogue) | FixTime, Webster, MaxPressure; IntelliLight, UniTSA, A-CATs, 3DQN-TSCC, CCDA, PPO | Image-SUMO sim, Songdo, Yau Ma Tei, Massy | **−65% emergency wait** vs RL-only; <11.5 s deliberative latency; <1% routine ATT loss | Validates dual-branch (fast classical + slow LLM) — same pattern as Edge Negotiator's MaxPressure fallback |
| Virtual Traffic Police | LLM-Augmented Hierarchical TSC for Incidents | 2026 | https://arxiv.org/pdf/2601.15816 | GPT-4 + RAG + verifier (TLRS) | RL, MaxPressure, FixedTime, LLMLight, LA-Light | SUMO incident networks | Higher reliability/lower delay vs LLMLight under incidents | Hierarchical "augment-not-replace" controller; aligns with deterministic-fallback ethos |
| Open-TI/ChatZero | Open Traffic Intelligence Agent | 2024 | https://arxiv.org/pdf/2401.00211 | GPT-3.5/4, Llama2-7B/13B as ChatZero meta-agent | RL/rule TSC inside Open-TI | CityFlow Hangzhou (4 configs × 5 runs) | GPT-4 ChatZero best on ATT/throughput; Llama-7B viable | Documents Llama-7B-class models running TSC dialog loop |
| Masri-Vehicles | LLMs as Traffic Control Systems | 2025 | https://www.mdpi.com/2624-8921/7/1/11/pdf | GPT-4o-mini FT, Gemini, Llama (CoT) | Rule-based qualitative | Custom Python 4-leg sim | F1 0.84, ROUGE-L 0.91–0.95 on conflict/priority/wait optimisation | Sub-7B class FT model controlling intersection (single int) |
| Multi-Agent-LLMTSC | From Single Agent to Multi-Agent: Improving TSC | 2024 | https://arxiv.org/pdf/2406.13693 | LightGPT-style FT LLM ensemble (1/5/10) | MPLight, LLMLight, Llama-13B | CityFlow Jinan(12), Hangzhou(16) | Majority-voting helps FT LightGPT but not generic Llama-13B | Justifies per-cabinet local SLM agents with voting |
| REG-TSC | RAG-Enhanced Distributed LLM Agents w/ Emergency | 2025 | https://arxiv.org/pdf/2510.26242 | Distributed LLM agents w/ RAG (GPT-4o-mini, Llama-3.1-8B) | MPLight, AttendLight, PressLight, CoLight, Eff/Adv-CoLight, LLMLight | CityFlow Jinan/Hangzhou/Yizhuang | **4.07 s/timestep** inference; ATTE −54 s in Jinan1; AWTE −69.99% in Yizhuang2 | Per-step latency numbers for distributed LLM-per-cabinet design |
| CoMAL | Collaborative Multi-Agent LLMs for Mixed Autonomy | 2024 | https://arxiv.org/pdf/2410.14368 | Qwen-7B/32B/72B (Perception+Memory+Collab+Reasoning+Exec) | RL on Flow benchmarks | Flow (Ring, Figure-8) | Avg velocity & stability gains over RL | Sub-7B Qwen agents in multi-agent coordination |
| EvolveSignal | LLM as Algorithm-Discovery Agent for Signals | 2025 | https://arxiv.org/pdf/2509.03335 | DeepSeek-V3/R1 + o4-mini-high/o3 ensemble | Webster | SUMO 4-leg, 1800 s | **−20.1% delay, −47.1% stops** vs Webster after 300 generations | LLM-generated *code* (offline) — contrasts with Edge Negotiator's runtime LLM |
| SignalClaw | LLM as Evolutionary Skill Generator | 2026 | https://arxiv.org/pdf/2604.05535 | LLM-generated skills (rationale+code) | MaxPressure, DQN, LLMLight, Traffic-R1, FRAP, MetaLight, EvolveSignal | SUMO + TraCI events | Emergency delay 11.2–18.5 s vs MaxPressure 42.3–72.3, DQN 78.5–95.3 | Inspectable-skill paradigm — relevant to dissertation's auditable-decision angle |
| CoLight | Network-Level Cooperation for TSC | 2019 | https://arxiv.org/pdf/1905.05717 | n/a (GAT-DQN) | Individual + concat RL | CityFlow Hangzhou/Jinan/NY | First GAT-RL TSC; SOTA on 196-int NY at the time | Standard RL baseline anchor |
| MPLight | Toward A Thousand Lights | AAAI 2020 | https://ojs.aaai.org/index.php/AAAI/article/download/5744/5600 | n/a (FRAP+pressure DQN) | MaxPressure, FixedTime | Manhattan 2510 signals | **~13% travel time over MaxPressure; scales to 2510 ints** | Pressure-RL baseline; demonstrates scale |
| PressLight | Learning Max Pressure for Arterial Coordination | KDD 2019 | https://faculty.ist.psu.edu/jessieli/Publications/2019-KDD-presslight.pdf | n/a (DQN with MP-reward) | MaxPressure, LIT | Synthetic, Hangzhou, Atlanta | ATT 88.88 s vs MaxPressure 129.63 s on 10-int arterial | Theoretical bridge MaxPressure↔RL |
| FRAP | Learning Phase Competition for TSC | CIKM 2019 | https://arxiv.org/pdf/1905.04722 | n/a (phase-pair invariant DQN) | Standard RL/rule | Hangzhou/Jinan/Atlanta | Symmetry-invariant; reduces exploration 64×n⁸→16×n⁴ | Standard RL backbone (used by MPLight) |
| CityFlow | CityFlow Multi-Agent Traffic Simulator | WWW 2019 | https://arxiv.org/pdf/1905.05217 | — | SUMO | — | ~25× faster than SUMO on 30×30 net | Defines the Jinan/Hangzhou/NY benchmark used by every LLM-TSC paper |
| RESCO | RL Benchmarks for TSC | NeurIPS 2021 | https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/file/f0935e4cd5920aa6c7c996a5ee53a70f-Paper-round1.pdf | — | IDQN, IPPO, MPLight, FMA2C, FixedTime, MaxPressure, MaxWave | SUMO Cologne/Ingolstadt/SLC | Reproduces MPLight ~11% gain over MP; flags non-robustness to sensing | SUMO-based RL benchmark — closer to dissertation's SUMO Lambeth setup |
| Adv-XLight | Efficient Pressure: Representation for RL TSC | 2022 | https://arxiv.org/pdf/2112.10107 | — | MPLight, CoLight | CityFlow Jinan/Hangzhou/NY | Adv-CoLight = pre-LLM SOTA on the 3 standard nets | Strongest non-LLM baseline LLM-TSC papers must beat |
| CityLight | Universal MAPPO TSC at Real City Scale | 2024 | https://arxiv.org/pdf/2406.02126 | — | FixedTime, MaxPressure, FRAP, MPLight, CoLight, Eff-MPLight, Adv-CoLight, GPLight, LLMLight | Manhattan(196), Chaoyang(97), Beijing(885/13952), Jinan(3930) | Beats LLMLight at full-city scale via MAPPO | Reference for borough-scale coordination metrics |
| Survey-TSC | A Survey on Traffic Signal Control Methods (Wei et al.) | 2019/21 | https://arxiv.org/pdf/1904.08117 | — | Webster/GreenWave/MaxBand/SCOOT/SCATS/MaxPressure | — | Canonical taxonomy + open derivation of MaxPressure | Provides the open-text MaxPressure derivation since Varaiya'13 is paywalled |
| MA2C-TSC | Multi-Agent DRL for Large-Scale TSC | IEEE TITS 2020 | https://arxiv.org/pdf/1903.04527 | — | IQL, IA2C, MaxPressure | SUMO 5×5 grid, Monaco | Decentralised MA2C beats IQL on 5×5 grid | The 5×5 SUMO grid is structurally identical to dissertation's Lambeth grid |
| MP-Delay | Novel Max Pressure Algorithm Based on Delay | 2022 | https://arxiv.org/pdf/2202.03290 | — | Original MP variants | SUMO | Provable throughput stability with delay-aware pressure | Open-access stand-in for paywalled Varaiya'13 fallback formalism |
| MP-Pedestrian | MP for Signals Considering Pedestrian Queues | 2024 | https://arxiv.org/pdf/2406.19305 | — | Classical MP | Theoretical | Extends formal stability proofs | Relevant to UK borough setting w/ heavy pedestrian volumes |
| Edge-Orin-Bench | LLMs on Small Resource-Constrained Systems | 2024 | https://arxiv.org/pdf/2412.15352 | Pythia 70M–1.4B | — | Orin Nano 4/8GB, Orin NX 8/16GB, AGX 32GB; FP32→INT4 | Cabinet-class tokens/sec, J/token, peak memory profiles | Hardware sizing grid for cabinet selection |
| Edge-AGX-Power | Performance & Power of LLM Inferencing on Edge Accelerators | 2025 | https://arxiv.org/pdf/2506.09554 | Llama-3.1, Phi-2 2.7B, DeepSeek-R1-Qwen 2.7–32.8B | INT4/INT8/FP16 | AGX Orin 64GB, 15/30/50W/MAXN | INT4 *slows* small LLMs on Ampere (no native INT4) | Critical caveat for Phi-4-mini quantization choice |
| Edge-First | Edge-First LLM Inference: Models, Metrics, Tradeoffs | 2025 | https://arxiv.org/pdf/2505.16508 | Qwen2.5 0.5–32B, GPT-4 cloud | — | AGX Orin vs Nano vs cloud | **0.0041¢/query AGX vs 1.65¢/query GPT-4 cloud**; AGX 1.49–3.25× faster, 1.7–3.91× more power than Nano | TCO argument for borough deployment |
| Edge-SLM-Energy | Energy Footprint & Efficiency of SLMs on Edges | 2025 | https://arxiv.org/pdf/2511.11624 | Llama-3.2 1B, Phi-3 Mini, TinyLlama, Gemma-2 | RPi 5, Jetson Nano, Orin Nano CPU/GPU | MMLU | **Llama-3.2 0.57 s on Orin Nano GPU; 7.4–8.7 W; Phi-3 Mini = best accuracy / worst energy** | Decisive empirical table for the dissertation's hardware-model match |
| Edge-Hailo | LLM Inference at the Edge: Mobile/NPU/GPU Sustained Load | 2026 | https://arxiv.org/pdf/2603.23640 | Qwen-2.5-1.5B 4-bit | RPi5+Hailo-10H, S24 Ultra, iPhone 16 Pro, RTX 4050 | — | **Hailo-10H 6.91 tok/s @ 1.87 W; mobiles thermal-throttle ~50%; Hailo within 9% of GPU on J/token** | Only published Hailo-10H LLM benchmark — directly informs RSU hardware choice |
| Edge-Quant | Sustainable LLM Inference: Quantized Variants on Edge | 2025 | https://arxiv.org/pdf/2504.03360 | Gemma-2 2B, Llama-3.2 1B, Qwen-2.5 0.5/1.5B; 28 GGUF variants | Edge SBC | — | Q4_K_M typically best accuracy/energy/latency knee | Direct guidance for Phi-4-mini & Qwen3-4B GGUF choice |
| Edge-Reason | EdgeReasoning: Reasoning LLM on Edge GPUs | 2025 | https://arxiv.org/pdf/2511.01866 | DeepSeek-R1-Distill-Qwen 1.5/14B, Llama-8B; AWQ W4A16 | Jetson Orin | — | Decode dominates >99.5% of inference; AWQ −1.04% (1.5B), −6.16% (Llama-8B) accuracy | Reasoning-vs-non-reasoning trade-off for cabinet CoT |
| FPGA-Qwen | On-Device Qwen2.5: Compression + HW Acceleration | 2025 | https://arxiv.org/pdf/2504.17376 | Qwen2.5-0.5B | Xilinx Kria K26 SoM | — | 55.08% compression; **5.1 tok/s vs 2.8 baseline** | Alternative FPGA cabinet path |
| ELIB | Edge LLM Benchmarking framework | 2025 | https://arxiv.org/pdf/2508.11269 | various | various edge | — | Proposes Memory-Bandwidth Utilisation metric | Methodology for Edge Negotiator's hardware evaluation |
| SafeLight | Safety-Enhanced Residual RL for Collision-Free TSC | AAAI 2023 | https://arxiv.org/pdf/2211.10871 | — | 3DQN, IPPO | RESCO + synthetic SUMO | Drives intersection collisions to ~0; SafeLight-Act fastest | Action-shielding fallback pattern for the dissertation |
| Adv-DRL-TSC | Adversarial Attacks & Defense in DRL TSC | 2021 | https://escholarship.org/uc/item/7d7669z3 | — | DRL TSC agents | SUMO | FGSM/black-box attacks substantially raise queues; ensemble anomaly detector lowest delay/false-alarm | Justifies adversarial-robustness chapter |
| CollusionVeh | Attacking DRL TSC with Colluding Vehicles | 2021 | https://arxiv.org/pdf/2111.02845 | — | DRL TSC | SUMO | Coordinated falsified V2X telemetry breaks DRL; effect decreases with fleet size | Direct V2I-spoofing threat model — motivates blockchain audit |
| T-REX | Robustness of RL-TSC under Incidents | 2025 | https://arxiv.org/pdf/2506.13836 | — | IDQN, IPPO, MPLight | SUMO real + synthetic | Sharp degradation under sensor faults; complex states more brittle | Benchmarks fallback-trigger conditions |
| CFLight | Counterfactual Learning for Safer TSC | 2026 | https://arxiv.org/pdf/2512.09368 | — | DQN, SafeLight | SUMO | **−93.1% collision rate vs DQN** with efficiency gains | Recent post-SafeLight safety SOTA |
| CoT-Faith | Reasoning Models Don't Always Say What They Think | 2025 | https://arxiv.org/pdf/2505.05410 | Claude-3.7-Sonnet, DeepSeek-R1 | hint-injection | — | **CoT faithfulness <20%** for several hint types; outcome RL plateaus | The strongest open-empirical paper to motivate the dissertation's CoT-faithfulness perturbation experiment |
| BC-TSC | Blockchain-Based Architecture for TSC | 2019 | https://arxiv.org/pdf/1906.02628 | — | I-SIG controller | — | Mitigates I-SIG single-vehicle congestion attack | Only paper that *directly* targets blockchain audit for traffic signals |
| BC-AI-Decision | Blockchain Ledgers to Record AI Decisions in IoT | 2025 | https://www.mdpi.com/2624-831X/6/3/37/pdf | — | — | Hyperledger Fabric / Quorum sim | Permissioned-chain AI-decision provenance design w/ TPS/latency estimates | Architectural template for the audit ledger module |
| BC-Enforce | Blockchain-Enabled Transparent Traffic Enforcement | 2024 | https://www.frontiersin.org/journals/sustainable-cities/articles/10.3389/frsc.2024.1426036/full | — | — | Hyperledger Fabric + IPFS, ECDSA | Caliper TPS/latency curves for intersection-camera audit at municipal scale | Closest analogue to dissertation's permissioned audit ledger |
| SALT-V | Lightweight Authentication for 5G V2X | 2025 | https://arxiv.org/pdf/2511.11028 | — | Pure ECDSA | — | **0.035 ms compute (57× ECDSA), 1 ms e2e, 41 B overhead, 2000-vehicle linear scale** | Concrete V2I auth latency for cabinet ingest |
| BeACONS | Blockchain Authentication & Comms for IoV | 2024 | https://arxiv.org/pdf/2405.08651 | — | — | RSU-anchored simulation | DID/credential mutual auth at RSUs against eavesdrop/spoof | RSU-bound identity layer for V2I telemetry |
| BC-V2X-Sec | ML+Blockchain for Secure V2X (survey) | 2025 | https://www.mdpi.com/1424-8220/25/15/4793/pdf | — | — | — | Synthesises ML+DLT V2X security trade-offs | Threat-model background chapter |
| BC-CCAM | Blockchain & Smart Contracts for CCAM | 2024 | https://www.mdpi.com/1424-8220/24/19/6273/pdf | — | — | — | V2I logging/liability architecture | Smart-contract-for-intersection telemetry framing |
| BC-Offload | Blockchain Task Offloading for Smart Transport | 2025 | https://www.mdpi.com/1424-8220/25/17/5555/pdf | — | — | PoS permissioned | Adaptive utilisation under packet-loss; O(K log K) scheduling | Decentralised auditable scheduling pattern |

# Section B — Ranked benchmark landscape of LLM-for-traffic systems

| System | Model size | Edge-deployable? | Largest network tested | Best metric reported | Comparable to MaxPressure? |
|---|---|---|---|---|---|
| **Traffic-R1** | Qwen-2.5-3B (FT, RL) | **Yes** — author claims mobile-class; <2 s on Tesla T40 | NY 196 ints + 10-int real-city A/B (55k drivers/day) | >5% queue cut in production; >30% over LLMLight on OOD; halves operator load | **Yes** — beats MaxPressure on Jinan/Hangzhou/NY |
| **HeraldLight** | Llama-3.1-8B (LoRA) + ChatGPT critic | Borderline (8B Q4 fits 8GB VRAM; critic is cloud) | NY 196 ints (224 total) | −20.03% ATT, −10.74% AQL vs SOTA | **Yes** — outperforms MaxPressure & Adv-CoLight |
| **CoLLMLight** | Llama-3.1-8B FT | Borderline 8B | NY 28×7 = 196 | Beats LLMLight + Adv-CoLight on ATT/AQL/AWT | **Yes** |
| **LLMLight / LightGPT** | LightGPT-Llama-13B; FT-Qwen-0.5B variant | Qwen-0.5B variant: yes; 13B: borderline | NY 196 | LightGPT ATT ≈ Adv-CoLight on Jinan-1 (~270 s) vs Random ~530 s | **Yes** |
| **CuraLight** | Gemma-3 (LoRA) | Yes (Gemma-3 has 1B/4B variants) | Multi-int Jinan/Hangzhou/Yizhuang (SUMO) | −5.34% ATT, −5.14% AQL, −7.02% AWT vs SOTA | **Yes** |
| **VLMLight** | Qwen-2.5-VL-32B + Qwen-2.5-72B | **No** — 72B is server-class | Multi-int Songdo/YMT/Massy | −65% emergency wait vs RL; <11.5 s deliberative latency | **Yes** — beats FixTime/Webster/MaxPressure |
| **REG-TSC** | GPT-4o-mini + Llama-3.1-8B (distributed RAG) | Llama-3.1-8B node: borderline | Multi-int Jinan/Hangzhou/Yizhuang | 4.07 s/timestep; ATTE −54 s Jinan1; AWTE −69.99% Yizhuang2 | Unknown (vs MPLight/CoLight only) |
| **iLLM-TSC** | GPT-4 verifier + RL | **No** (GPT-4 cloud); RL part yes | Single 4-way SUMO | −17.5% wait under packet loss; −62.9% emergency wait | Indirect (RL beats MaxPressure baselines) |
| **LA-Light** | GPT-4 + tools | **No** | Single 4-way SUMO/TSHub | −20.4% wait under sensor outage | **Yes** — beats Webster, MaxPressure |
| **Virtual Traffic Police** | GPT-4 + RAG | **No** | Multi-int SUMO with incidents | Higher reliability/lower delay vs LLMLight under incidents | **Yes** — augments MP/fixed-time |
| **Open-TI/ChatZero** | GPT-4, Llama2-7B/13B | Llama-7B: borderline | CityFlow Hangzhou | GPT-4 best on ATT/throughput; Llama-7B viable | Unknown |
| **SignalClaw** | LLM-generated *skills* (offline) | Yes — runtime is generated code | SUMO incident scenarios | Emergency delay 11.2–18.5 s vs MaxPressure 42.3–72.3 | **Yes** |
| **EvolveSignal** | DeepSeek/o-series ensemble (offline) | Yes — runtime is Python program | Single 4-leg SUMO | −20.1% delay, −47.1% stops vs Webster | Indirect (Webster baseline) |
| **CoMAL** | Qwen-7B/32B/72B | Qwen-7B: borderline | Flow Ring/Figure-8 | Stability gains vs RL baselines | Unknown |
| **Multi-Agent Voting** | LightGPT FT (≤13B) ensemble | Borderline | CityFlow Jinan(12)/Hangzhou(16) | Small consistent ATT gain over single-agent LLMLight | **Yes** (transitive) |
| **Masri-Vehicles** | GPT-4o-mini FT, Gemini, Llama | GPT-4o-mini cloud; Llama variant edge | Single 4-leg | F1 0.84, ROUGE-L 0.91–0.95 (task-level) | Qualitative only |
| **Adv-CoLight (RL ref)** | n/a (GAT-DQN) | Yes | NY 196 | Pre-LLM SOTA on Jinan/Hangzhou/NY | **Yes** |
| **MPLight (RL ref)** | n/a | Yes | Manhattan 2510 ints | ~13% over MaxPressure (RESCO reproduces ~11%) | **Yes** (explicitly) |

**Pattern:** Only **Traffic-R1 (3B)** and **CuraLight (Gemma-3)** combine three desirable properties — sub-7B, multi-intersection, MaxPressure-comparable — and only Traffic-R1 has any edge-deployment claim. None reports validated tokens/sec, watts, or thermal numbers for the exact 4–8 B class on a Jetson Orin Nano or Hailo-10H NPU running an actual SUMO loop.

# Section C — Gap analysis and dissertation novelty claim

The literature shows three unambiguous frontiers, but **none of them intersect at the point Edge Negotiator occupies**.

**Frontier 1 — Sub-7B SLM as runtime traffic controller** is now established. Traffic-R1 (Qwen-2.5-3B), CuraLight (Gemma-3), HeraldLight (Llama-3.1-8B) and LLMLight's LightGPT-0.5B variant prove sub-7B/8B models can match Adv-CoLight on standard CityFlow benchmarks. **However, every one of these papers either (a) runs the model on a cloud-class GPU (T40, A100) or merely *claims* edge feasibility, or (b) when the model is actually placed on edge hardware (Edge-Orin-Bench, Edge-SLM-Energy, Edge-Hailo), the workload is generic MMLU/WikiText, not a closed-loop traffic-signal task.** No published paper reports tokens/sec, watts, P99 phase-decision latency, or thermal-throttling behaviour for Qwen3-4B or Phi-4-mini executing CoT phase decisions on a Jetson Orin Nano, Hailo-10H, or Coral-class device inside a SUMO loop.

**Frontier 2 — Borough-scale realistic networks.** CityLight, HeraldLight, Traffic-R1 push to NY-196 and Beijing-13952, but always on CityFlow synthetic flows from Hangzhou/Jinan/NY. **No LLM-TSC paper uses a real UK borough OSM extract (Lambeth/Southwark) in SUMO with calibrated TfL counts.** The closest SUMO grids are MA2C's synthetic 5×5 and RESCO's Cologne/Ingolstadt.

**Frontier 3 — Safety + auditability.** SafeLight, CFLight (action shielding), iLLM-TSC and LA-Light (LLM with classical fallback), SALT-V (V2I auth) and BC-Enforce (Hyperledger audit) each cover one slice. **No paper combines (i) a *deterministic* MaxPressure shield that overrides SLM output in real time, (ii) a permissioned-blockchain audit of every accepted/rejected SLM decision, and (iii) an empirical CoT-faithfulness test (à la Anthropic 2505.05410) under safety-critical perturbation of the traffic state.**

The unoccupied intersection — and Edge Negotiator's novelty — is therefore the joint tuple **(sub-7B SLM ∈ {Qwen3-4B, Phi-4-mini}) × (consumer-grade edge hardware: Jetson Orin Nano/Hailo-10H) × (real Lambeth/Southwark 5×5 km SUMO grid) × (deterministic MaxPressure fallback) × (permissioned blockchain audit ledger) × (CoT-faithfulness evaluation under adversarial perturbation)**. Each axis exists in prior work; their conjunction does not.

# Section D — Plain download list

https://arxiv.org/pdf/2312.16044
https://arxiv.org/pdf/2503.11739
https://arxiv.org/pdf/2508.02344
https://arxiv.org/pdf/2511.00136
https://arxiv.org/pdf/2604.05663
https://arxiv.org/pdf/2403.08337
https://arxiv.org/pdf/2407.06025
https://arxiv.org/pdf/2505.19486
https://arxiv.org/pdf/2601.15816
https://arxiv.org/pdf/2401.00211
https://www.mdpi.com/2624-8921/7/1/11/pdf
https://arxiv.org/pdf/2406.13693
https://arxiv.org/pdf/2510.26242
https://arxiv.org/pdf/2410.14368
https://arxiv.org/pdf/2509.03335
https://arxiv.org/pdf/2604.05535
https://arxiv.org/pdf/1905.05717
https://ojs.aaai.org/index.php/AAAI/article/download/5744/5600
https://faculty.ist.psu.edu/jessieli/Publications/2019-KDD-presslight.pdf
https://arxiv.org/pdf/1905.04722
https://arxiv.org/pdf/1905.05217
https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/file/f0935e4cd5920aa6c7c996a5ee53a70f-Paper-round1.pdf
https://arxiv.org/pdf/2112.10107
https://arxiv.org/pdf/2406.02126
https://arxiv.org/pdf/1904.08117
https://arxiv.org/pdf/1903.04527
https://arxiv.org/pdf/2202.03290
https://arxiv.org/pdf/2406.19305
https://arxiv.org/pdf/2412.15352
https://arxiv.org/pdf/2506.09554
https://arxiv.org/pdf/2505.16508
https://arxiv.org/pdf/2511.11624
https://arxiv.org/pdf/2603.23640
https://arxiv.org/pdf/2504.03360
https://arxiv.org/pdf/2511.01866
https://arxiv.org/pdf/2504.17376
https://arxiv.org/pdf/2508.11269
https://arxiv.org/pdf/2211.10871
https://escholarship.org/uc/item/7d7669z3
https://arxiv.org/pdf/2111.02845
https://arxiv.org/pdf/2506.13836
https://arxiv.org/pdf/2512.09368
https://arxiv.org/pdf/2505.05410
https://arxiv.org/pdf/1906.02628
https://www.mdpi.com/2624-831X/6/3/37/pdf
https://www.frontiersin.org/journals/sustainable-cities/articles/10.3389/frsc.2024.1426036/full
https://arxiv.org/pdf/2511.11028
https://arxiv.org/pdf/2405.08651
https://www.mdpi.com/1424-8220/25/15/4793/pdf
https://www.mdpi.com/1424-8220/24/19/6273/pdf
https://www.mdpi.com/1424-8220/25/17/5555/pdf
https://faculty.ist.psu.edu/jessieli/Publications/2018-KDD-IntelliLight.pdf
https://arxiv.org/pdf/2503.20205