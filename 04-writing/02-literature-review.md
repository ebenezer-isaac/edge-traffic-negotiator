# Chapter 2 — Literature Review

**The Edge Negotiator: An Accountability-Anchored On-Device Coordination Layer for Signalised Junctions**

**Author:** 25153651
**Institution:** University College London, United Kingdom

## Abstract

This chapter establishes that no published work instantiates and measures a self-referential coupling — in which a stealthy insider preemption attack controls the same signal phase that gates honest-witness coverage — on a real signalised corridor, backed by an on-device small-language-model reasoner and a Certificate-Transparency-style, quorum-anchored, cross-audited accountability log. The chapter traces, section by section, how each architectural decision is compelled by the literature rather than stipulated, surveying the classical adaptive baseline (Max-Pressure, SCOOT, SCATS), reinforcement-learning controllers and their adversarial brittleness, the LLM/SLM-for-TSC frontier, edge-hardware constraints on sub-7B inference, the chain-of-thought-faithfulness literature that governs why the reasoning channel is firewalled rather than trusted, the accountability-log literature whose transparency-log mechanism the design credits to prior art, and the legal-accountability literature governing automated public-sector decisions. The chapter closes on the novel object: a conditional coupling lemma and a single pre-registered measurement of its boundary on the real Euston Road (A501) corridor. The accountability mechanism is credited to prior art; the measured coupling is the increment.

**Keywords:** on-device coordination, edge AI, accountability log, transparency log, provenance evidence pack, small language models, self-referential coupling, compromised-insider emergency preemption

---

## 2.1 Introduction and roadmap

This chapter argues that no published study instantiates and measures a self-referential coupling — in which a stealthy insider preemption attack controls the same signal phase that gates honest-witness coverage — on a real signalised corridor, and situates that increment against three contributions the literature makes possible but does not itself deliver: (a) a deterministic real-time gate that refuses signed-but-uncorroborated emergency preemption from a compromised insider while clearing physically corroborated real emergencies; (b) a Certificate-Transparency-style, quorum-anchored, cross-audited accountability log whose mechanism is credited to prior art, not claimed as novel; and (c) the novel object, the self-referential coupling itself, stated as a conditional lemma and measured once, severely and pre-registered, on the real Euston Road (A501) corridor. The argument is developed across eight sections. The structure is not merely additive: each section shows how the literature compels the architectural decision the next section inherits, so that the closing claim in §2.9 follows from evidence rather than assertion.

### Technical baselines and controller selection (§§2.2–2.5)

Section 2.2 establishes that the deterministic-shield component must be drawn from the Max-Pressure family, which is the only signal-control policy with a published throughput-stability proof, open-access derivations, a pedestrian-aware extension proven to generalise to urban-corridor conditions, microsecond runtime on local sensor pressures, and a per-cabinet structure that inverts the SCOOT/SCATS regional-controller assumption. Section 2.3 identifies the appropriate empirical comparison baselines — Max-Pressure, MPLight, CoLight and Adv-CoLight on CityFlow; MA2C and the RESCO suite on SUMO grids — and shows that the safety and adversarial-robustness sub-literature documents consistent brittleness of pure reinforcement-learning controllers under sensor faults and adversarial V2X messaging, including the false-data-injection and colluding-vehicle class that supplies the stealthy-insider threat model this dissertation inherits. Section 2.4 maps the LLM-for-TSC frontier, which comprises fewer than thirty papers across roughly eighteen months; only Traffic-R1 and CuraLight occupy the sub-7B size class with multi-intersection capability, and no paper in the corpus characterises what a controller can and cannot hold mechanically accountable under a compromised-insider emergency preemption — the gap this dissertation addresses. Section 2.5 surveys the edge-hardware benchmark literature and shows that it is mature enough to constrain a future cabinet deployment but does not yet report validated closed-loop integration of a sub-7B controller against a downstream SUMO loop under sustained thermal load; the on-device reasoner is Phi-4-mini, evaluated on a developer-class GPU rather than cabinet-class edge silicon.

### Reasoning channel, accountability log, and legal framing (§§2.6–2.8)

Section 2.6 establishes that the Chain-of-Thought faithfulness literature converges on a well-evidenced conclusion: explicit CoT traces are post-hoc rationalisations rather than faithful causal records, a finding that holds for frontier reasoning models, sub-7B models, and embodied-control pipelines alike; the architecture this dissertation presents therefore firewalls the reasoning channel into a non-evidential, counsel-gated internal note, validated against cited statute and never trusted as a determination, because accountability is carried by the signed log rather than by the trace. Section 2.7 establishes that the accountability layer is a Certificate-Transparency-style, quorum-anchored, cross-audited, signature-verified log whose mechanism is credited to prior art (transparency logs, tamper-evident append-only ledgers, cross-auditing witnesses); a permissioned ledger is demoted to one cited anchor option among the witnesses, not the contribution. Section 2.8 shows that the legal-accountability literature on automated public-sector decisions compels a mechanically-verifiable provenance record firewalled from any origin classification; UK statute and case law (Road Traffic Act 1988 duties, GDPR/DPA 2018 automated-decision provisions, and public-law accountability precedents) supply the framing the on-device reasoner's citation-faithful legal note must respect, and no published system produces such a provenance evidence pack for an insider-compromised emergency preemption.

### Closing claim (§2.9)

Section 2.9 closes the chapter on the novel object: the self-referential coupling in which the attack lever (signal phase) is also the honest-witness coverage gate, so executing the attack opens the very coverage desert that conceals it. The coupling is stated as a conditional lemma under explicit hypotheses and measured once on the real Euston A501 corridor. The accountability mechanism is credited to prior art; the deterministic gate and the on-device legal-reasoning note are co-equal engineering contributions; the measured coupling boundary — an honest characterisation, not an unconditional guarantee — is the increment no prior work occupies.

## 2.2 The traffic signal control problem and classical adaptive baselines

This section establishes that the deterministic-shield component of the architecture this dissertation presents must be drawn from the Max-Pressure family, because Max-Pressure is the only signal-control policy whose throughput-stability proof, per-cabinet structure, sub-millisecond runtime and pedestrian-aware extension are simultaneously documented in the open literature.

### 2.2.1 From pre-timed to adaptive control

Urban signal control passed through three generational transitions before learning-based methods became plausible, and each transition tracked what could be sensed and computed in real time [1]. Webster's 1958 fixed-time formulation set cycle lengths and green splits from historical demand counts, exposing nothing of the live traffic state to the controller [1]. Vehicle-actuated cabinets in the 1960s and 1970s added inductive-loop detection and per-phase extension logic, but coordination remained absent: each intersection optimised in isolation [1]. The early 1980s installation of SCOOT (Split, Cycle and Offset Optimisation Technique) in the United Kingdom and SCATS (Sydney Coordinated Adaptive Traffic System) in Australia represented the first centralised adaptive deployments at metropolitan scale, computing region-wide plans in a control centre and dispatching them to cabinets over a dedicated communications backbone [1]. From the late 2010s onward, learning-based controllers — first reinforcement-learning agents and most recently language-model agents — have been proposed as per-cabinet replacements, restoring cabinet-local autonomy while attempting to retain coordination through neural representations [1, 2, 3]. The taxonomy in [1] is the canonical reference adopted in this chapter, and it also supplies the open-access derivation of Max-Pressure that the next subsection relies on, given that Varaiya's 2013 originating papers are not freely available.

### 2.2.2 The Max-Pressure family and provable throughput stability

Max-Pressure originated in the work of Tassiulas and Ephremides on packet scheduling for radio networks, where it provided a queue-differential rule that maximised the stability region under stochastic arrivals [4, 1]. Varaiya adapted the formalism to networks of signalised intersections, defining each phase's pressure as the difference between upstream and downstream queue lengths and selecting, at every decision epoch, the phase with the largest pressure; the resulting policy is shown to be throughput-optimal in the sense that any demand vector that can be served by some admissible signal plan will be served by Max-Pressure without prior knowledge of the demand itself [1, 4]. Among published signal-control algorithms, Max-Pressure remains the only one whose throughput-stability proof is reported under mild and broadly stated assumptions [1, 4, 5].

Two recent extensions matter for the architecture this dissertation presents. The delay-aware variant of [4] replaces queue length with travel-delay-weighted pressure and is analytically shown to inherit the maximum-stability property of the original Varaiya formulation while reducing observed delay in SUMO microsimulation under arterial demand. The pedestrian-aware variant of [5] models vehicle and pedestrian queues jointly and proves that maximum stability holds for both populations, addressing a documented gap in earlier MP variants that either ignored pedestrians or treated them through ad-hoc waiting-time thresholds. Both extensions retain the original algorithm's defining computational property: pressure is a sum of local queue-length differences, evaluated in sub-millisecond time from per-cabinet sensor inputs, with no central plan computation [4, 5]. This combination of properties — provable stability, decentralised execution, sub-millisecond runtime, and an extension that handles the pedestrian volumes typical of London borough corridors — is what makes the Max-Pressure family a credible deterministic safety fallback when a structured-JSON output from a language-model controller fails formal verification at runtime.

Critical engagement is required, however. The throughput-stability proof holds only for demand vectors lying inside the stability region; field operation at saturated peak hours, common on inner-London corridors, places the network outside the assumption set under which the proof is stated [4, 5]. The guarantee that motivates Max-Pressure as a shield therefore degrades exactly where the corridor most needs guarantees, and any deployment that relies solely on Max-Pressure inherits this limitation. This is one of the reasons the architecture proposed in the chapter pairs Max-Pressure with — rather than substitutes it for — an upstream learning-based controller.

### 2.2.3 PressLight: the theoretical bridge to reinforcement learning

[6] (KDD 2019) operationalised the link between Max-Pressure and reinforcement learning by using intersection pressure directly as the per-step reward of a deep Q-network agent, arguing that pressure is a surrogate for average travel time that can be optimised with standard temporal-difference methods. On a synthetic ten-intersection arterial under heavy uniform demand, the authors reported an average travel time of 88.88 s for PressLight against 129.63 s for Max-Pressure, with consistent margins across six-, ten-, and twenty-intersection configurations and on a grid network [6]. The methodological move is the load-bearing contribution: Max-Pressure supplies a locally computable gradient that the RL policy can follow, while the neural value function approximates the long-horizon consequences that the greedy single-step rule cannot represent. Subsequent pressure-aware RL controllers, including [3] for thousand-intersection scaling, inherit this framing and are reviewed in §2.3.

### 2.2.4 SCOOT, SCATS, and the legacy installed base

The legacy adaptive systems still dominate the installed base on which any new controller must operate. SCOOT, SCATS, MOVA and their successors compute signal plans in a regional traffic control centre and push them to street-side cabinets over a centralised communications backbone, an architectural pattern documented in [1]. Three operational properties are critiqued in the literature. First, the regional control centre is a single point of failure: outages or misconfiguration propagate across every cabinet under its remit. Second, plan revalidation is slow; SCOOT plan updates have historically required months of off-line traffic engineering work before deployment. Third, vendor lock-in is structural — SCOOT plans cannot be ported to SCATS cabinets, and neither can be retargeted to a third vendor's controller without redevelopment.

More recent procurement decisions in London follow the same regional-controller logic. The Yunex FUSION adaptive-control suite, which Transport for London has procured for new and upgraded sites, retains the central-plan-and-dispatch model rather than devolving decisions to cabinets, and vendor-supplied delay-reduction figures for FUSION on London sites are not treated here as established results. Cabinet-level SLM controllers with a Max-Pressure shield and a quorum-anchored accountability log are intellectually distinct from this lineage on each of the three critiqued properties: there is no regional single point of failure, plan updates are localised and bounded by per-cabinet verification rather than network-wide revalidation, and the underlying interfaces are open rather than vendor-defined. They are nonetheless not a wholesale replacement for the installed base; the realistic deployment surface is new and upgraded sites alongside legacy hardware, an inheritance constraint that conditions the corridor-selection logic developed in later chapters.

### 2.2.5 What the literature compels

The first architectural choice the literature compels is the choice of deterministic shield, and it is determined before the choice of language model, ledger, or corridor. Of the candidate adaptive policies surveyed in [1], only the Max-Pressure family simultaneously offers a published throughput-stability proof, an open-access derivation independent of the paywalled Varaiya papers, a pedestrian-aware extension whose stability proof generalises to UK borough conditions, sub-millisecond runtime cost on local sensor pressures, and a per-cabinet structure that inverts the SCOOT/SCATS/FUSION regional-controller assumption [1, 4, 5]. Subsequent sections argue that the language-model reasoner (§2.4), the firewalled reasoning channel (§2.6), the accountability log (§2.7), and the legal-accountability framing (§2.8) all rest on this base.

## 2.3 Reinforcement learning for traffic signal control

This section establishes the reinforcement-learning (RL) literature that supplies the empirical comparison baselines this dissertation must run against, and shows that the same literature has surfaced safety and adversarial-robustness failure modes which motivate combining a small-language-model controller with a deterministic Max-Pressure shield rather than deploying RL alone.

### 2.3.1 Single-intersection deep-Q learning

The foundational design pattern in deep-RL traffic signal control fixes three components: a per-intersection state vector built from queue lengths or pressure terms, a discrete action space over phase choices, and a reward derived from queue length, pressure, or travel time. MPLight instantiated this template at scale by combining a pressure-based reward with a phase-pair-invariant state representation, on a Manhattan network of 2,510 intersections. MPLight reports throughput improvements over Max-Pressure on the same Manhattan benchmark on the order of low double digits, with [7] reproducing similar gains under independent SUMO benchmarks [3, 7]. The phase representation MPLight inherits from FRAP exploits symmetry between conflicting phase pairs, collapsing the exploration space from order 64 × n^8 to order 16 × n^4 and rendering single-intersection deep-Q learning tractable on the standard CityFlow corpus [8].

Critical engagement with this strand is straightforward. A single-intersection deep-Q controller is, by construction, blind to network coordination: its policy optimises a local pressure or queue signal that contains no representation of an upstream platoon arriving from a neighbouring junction. Reward shaping is dataset-dependent, and the published benchmarks rarely report training-time wall-clock cost or the number of episodes needed for convergence, which complicates any claim of practical edge deployability for the resulting weights. The RESCO benchmark further notes that MPLight-style controllers are "non-robust to sensing", a finding picked up again in §2.3.4 below [7].

### 2.3.2 Network-level cooperation via graph attention and decentralised actor-critic

Once the single-intersection template was stable, the literature turned to coordinating decisions across many junctions without surrendering decentralised execution. CoLight introduced graph-attention coordination, in which each intersection's policy attends to the states of its road-adjacent neighbours through a learned attention weighting; this established the canonical network-scale RL baseline against which subsequent work has been measured, and was the strongest result on the 196-intersection New York network at the time of its publication [2]. The pre-LLM state of the art on the standard Jinan, Hangzhou and New York benchmarks was Adv-CoLight, which refines the pressure representation that CoLight feeds to its attention layer; this is the empirical bar that any new traffic-signal-control architecture, RL or otherwise, must clear on those networks [9].

A parallel strand pursued decentralised multi-agent actor-critic methods. The MA2C controller trained a decentralised advantage actor-critic on a SUMO 5×5 grid and on the Monaco network, and reported gains over independent Q-learning with the same per-agent observation budget [10]. The 5×5 SUMO grid in that work is structurally analogous to the orthogonal portion of a short signalised corridor, which makes it the closest published topology to the synthetic 2×2 grid this dissertation uses as a unit-test fixture ahead of the real Euston A501 stretch.

Synthesising across these papers, the literature's progression from independent Q-learning to graph-attention to decentralised actor-critic is a progression toward incorporating spatial neighbour state without sacrificing decentralised execution: each step adds a richer representation of what the neighbours are doing while keeping the policy callable at one cabinet at a time. Critical engagement, however, exposes a load-bearing assumption. Graph-attention controllers presume reliable inter-cabinet communication for the neighbour-feature vector at every decision step, and the literature has not stress-tested degraded V2X or inter-cabinet links during operation; the robustness studies covered in §2.3.4 attack the sensor channel rather than the cabinet-to-cabinet channel. A controller whose attention weights are computed over partially missing neighbour features is operating outside its training distribution, and no published RL paper has reported the resulting policy degradation under realistic packet-loss profiles.

### 2.3.3 City-scale MAPPO and universal policies

The most recent push has been to scale a single shared policy to city-sized networks. CityLight trained a universal multi-agent proximal-policy-optimisation controller across Manhattan (196 intersections), Chaoyang (97), Beijing (885 and 13,952), and Jinan (3,930), and reported that the shared-parameter MAPPO formulation beat both Adv-CoLight and the LLMLight family at full-city scale [11]. The 13,952-intersection Beijing experiment is the largest network in the published RL traffic-signal-control literature, and the universal-policy framing — one shared parameter set executed independently at each cabinet — is the natural answer to the parameter-explosion problem of independent per-intersection training.

Critical engagement: city-scale benchmarks of this kind report aggregate average travel time, average queue length, and throughput, but they do not resolve behaviour at the single-junction, single-decision level at which an insider deviation would act. A controller can be efficient on the citywide aggregate while a signed-but-uncorroborated preemption at one junction passes unexamined, because aggregate mobility metrics are insensitive to whether any individual phase decision was corroborated or merely asserted. This gap between citywide aggregate performance and per-decision provenance is one of the explicit motivations for the accountability framing developed in §2.7 and §2.8.

### 2.3.4 Safety and adversarial robustness

A separate, smaller sub-literature has examined what happens when an RL traffic controller is exposed to constraint violations, sensor faults, or active adversarial input. [12] introduces logical safety rules drawn from the Federal Signal Timing Manual (e.g., for permitted versus protected left-turn phasing) as a residual safety module on RL phase decisions, and reports over 99% fewer collisions than the backbone RL controller and approximately 30% lower average waiting time than fixed-time control [12]. The more recent CFLight introduced counterfactual safety filters that reject candidate actions which would violate physical constraints, and reported a 93.1% reduction in collision rate against a deep-Q baseline while preserving efficiency gains [13]. Both papers converge on the same pattern: a learned policy is permitted to propose, but a deterministic constraint layer disposes.

The adversarial sub-literature is sharper. [14] showed that small adversarial perturbations on the sensor input — including FGSM and black-box attacks — substantially raise queues against trained deep-RL traffic-signal-control agents, and that an ensemble anomaly detector recovers the lowest delay and false-alarm trade-off only at the cost of rejecting plausible inputs [14]. [15] reports that hierarchically coordinated controllers retain mobility under incident perturbation more reliably than independent value-based methods, framing complex but well-coordinated state representations as a stabilising rather than destabilising factor. [16] modelled coordinated falsified V2X telemetry from colluding vehicles and demonstrated that a small fraction of malicious connected vehicles can degrade learned policies, with the per-vehicle benefit of collusion diminishing as the colluding group itself grows larger, since additional attackers compete for the same scarce green-time resource rather than compounding one another's gains; this is precisely the V2I-spoofing threat model that the architecture this dissertation presents inherits from any connected-vehicle data feed [16].

Synthesising across SafeLight, CFLight, Adv-DRL-TSC, T-REX and CollusionVeh, the safety and adversarial sub-literature converges on a single conclusion: pure RL traffic-signal controllers are brittle under sensor faults and adversarial V2X messaging, and the literature's recommended mitigation is a deterministic constraint layer that the learned policy cannot override. The action-shielding pattern in SafeLight and the counterfactual filter in CFLight are two instances of that mitigation; the Max-Pressure shield in the architecture this dissertation presents is a third.

### 2.3.5 What the literature compels

Two consequences for the chapter follow. First, the appropriate empirical comparison baselines for any new traffic-signal-control architecture on the standard CityFlow corpus are Max-Pressure, MPLight and CoLight or Adv-CoLight; on a SUMO grid, MA2C and the RESCO suite are the corresponding anchors [3, 2, 9, 10, 7]. Second, the proposed system is not an RL controller. It is a small-language-model controller backed by a deterministic Max-Pressure shield, and the choice of a shield rather than an unconstrained learned policy is motivated directly by the safety and adversarial-robustness literature's documented brittleness of pure RL under sensor and V2X perturbation [12, 13, 14, 15, 16]. §2.4 turns to the LLM and SLM controllers that emerged in the last eighteen months and that supply the controller half of that pairing.

## §2.4 Large language models in traffic signal control

This section maps the small but rapidly accreting LLM-for-TSC literature, isolates the sub-7B controllers that are dimensionally compatible with cabinet-class deployment, and shows that none of them characterises what a compromised-insider emergency preemption can and cannot be held mechanically accountable for on a real corridor.

### 2.4.1 Pioneering controllers

The first wave of LLM-for-TSC research established two architectural templates that the remainder of the field has since elaborated. LLMLight introduced the LLM-as-controller pattern: a structured prompt encoding lane occupancies, queue lengths, and current phase is dispatched to a language model that returns the next phase as a discrete decision. [17] introduced LightGPT, a controller fine-tuned from GPT-4 trajectories that distils LLM reasoning into a compact phase-decision policy, and benchmarked separately scaled variants spanning Qwen-0.5B through Llama-13B as comparator evaluation, with results reported on CityFlow Jinan, Hangzhou, and New York [17]. Open-TI introduced the alternative LLM-as-coordinator pattern, testing Llama-7B, Llama-13B, GPT-3.5 and GPT-4 across two configurations: a pivotal-agent variant that delegates phase-level decisions to underlying RL or rule-based controllers via Libsignal tool calls, and a ChatZero variant in which the language model itself directly issues phase-level control decisions without an intermediary controller, with the entire pipeline exposed through a dialog interface [18].

These two architectures define the design space the rest of the literature operates within: either the language model issues phase decisions directly, or it orchestrates classical and learned controllers through tool calls. Both pioneering systems were evaluated exclusively on the synthetic CityFlow road networks for Jinan, Hangzhou, and New York, and neither reported wall-clock inference latency on edge hardware, energy per decision, or robustness under sensor failure or dropped V2I telemetry [17, 18]. The benchmark conventions inherited from this opening wave — synthetic flows, queue-length and average-travel-time metrics, no hardware accounting — propagate through almost every subsequent paper and constitute one of the most consequential blind spots in the literature.

### 2.4.2 Cooperation across intersections

The second wave addressed a structural weakness of single-agent LLM controllers: phase decisions taken in isolation cannot anticipate spillback from neighbouring junctions. CoLLMLight fine-tuned Llama-3.1-8B for cooperative reasoning across networks of LLM agents, propagated spatiotemporal neighbour states between adjacent controllers, and reported gains over LLMLight and Adv-CoLight on average travel time (ATT) and average waiting time (AWT) across the standard CityFlow Jinan, Hangzhou, and New York grids [19]. HeraldLight extended this with a dual-LLM architecture in which a Llama-3.1-8B LoRA-tuned agent issues phase decisions while a separate ChatGPT-class critic supplies herald-guided prompts and forty-second queue forecasts; [20] reports a 20.03% reduction in average travel time across its evaluation scenarios and a 10.74% reduction in average queue length on the Jinan and Hangzhou networks against the DynamicLight state-of-the-art baseline [20].

The two papers establish that fine-tuned 8B-parameter models can sustain network-wide cooperation at borough-relevant scale, but each carries an architectural caveat directly relevant to cabinet-level deployment. An 8B-parameter model in 4-bit quantisation sits at the upper edge of what consumer-class accelerators can hold in working memory, and HeraldLight's reliance on a cloud-hosted ChatGPT critic reintroduces precisely the centralised dependency that an edge-deployed controller is intended to dissolve [20]. Cooperation, in the form documented here, does not yet translate into a fully on-cabinet system.

### 2.4.3 Tool-use and hybrid LLM+RL

A third strand reframed the language model as an auxiliary on top of a deterministic or reinforcement-learned controller rather than a replacement for it. LA-Light placed GPT-4 above a battery of classical and RL controllers and used tool calls to select among Webster, Max-Pressure, FRAP, CoLight, and UniTSA in long-tail scenarios, reporting a 20.4 percent reduction in average waiting time under sensor outage relative to RL alone on a SUMO testbed [21]. iLLM-TSC reversed the role assignment: a PPO-trained RL controller produced phase candidates that a GPT-4 verifier accepted or revised, yielding a 17.5 percent waiting-time reduction under degraded-communication conditions relative to an ADLight baseline and a 62.9 percent reduction in emergency-vehicle waiting time relative to a SARL-TSC baseline [22]. REG-TSC pushed the same idea into a distributed setting, equipping per-cabinet GPT-4o-mini and Llama-3.1-8B agents with retrieval-augmented generation and reporting per-step inference latency of 4.07 seconds with travel-time gains on the CityFlow Jinan, Hangzhou, and Yizhuang networks [23].

The convergent claim across the hybrid sub-current is that the language model augments rather than replaces the deterministic or learned controller, and that the architectural value of the LLM appears most clearly when the underlying system encounters out-of-distribution conditions [21, 22, 23]. This is a load-bearing finding for any cabinet-deployed design: the literature compels a layered architecture in which a deterministic shield holds the safety envelope and the language model contributes deliberative override only when its output is consistent with that envelope. The hybrid papers nevertheless inherit a deployability problem of their own. LA-Light, iLLM-TSC and the GPT-4o-mini half of REG-TSC depend on cloud LLM endpoints whose latency, cost, and availability are opaque to the operator and incompatible with cabinet-level autonomy [21, 22, 23].

### 2.4.4 Vision-language and meta-control

A small fourth strand introduced vision-language models to incorporate camera frames directly into the phase-decision pipeline. VLMLight combined a Qwen-2.5-VL-32B vision-language model with a Qwen-2.5-72B reasoner across a three-agent dialogue, reporting a 65 percent reduction in emergency-vehicle waiting time relative to RL-only baselines and a deliberative latency below 11.5 seconds, while keeping routine average-travel-time loss under one percent [24]. The system illustrates the upper bound of model scale that the literature has explored, and equally illustrates its deployability ceiling: a 32B vision encoder paired with a 72B reasoner is server-class hardware and falls outside the cabinet envelope this dissertation is concerned with. VLMLight's evaluation reports gains relative to RL-only baselines and does not directly compare against hybrid LLM+RL designs of the kind reviewed in §2.4.3, leaving the marginal value of the vision pipeline over text-only hybrid designs unquantified.

### 2.4.5 Sub-7B and edge-deployable controllers

A fifth strand has begun to engage the parameter-budget question directly. Traffic-R1 fine-tuned Qwen-2.5-3B with a two-stage agentic reinforcement-learning protocol and reported gains over LLMLight and the larger CoLLMLight-8B, GPT-4o, Llama-3.3-70B and Qwen-2.5-72B baselines on out-of-distribution CityFlow scenarios [25]. Traffic-R1 represents an emerging line of LLM-driven traffic-signal-control research rather than evidence of validated production deployment. Its authors are affiliated with PCITECH (Shanghai Stock Exchange ticker 600728), a transport-systems vendor, and the paper describes a partial production trial covering, by the authors' account, around 55,000 daily drivers — a figure that has not been independently verified [25]. The hedged framing matters because Traffic-R1 is the closest dimensional analogue to a sub-7B cabinet controller in the public literature, and any forward-looking claim built on it must carry that uncertainty forward.

CuraLight occupies a parallel position. It applied LoRA fine-tuning to Gemma-3 with a DeepSeek-V3/R1 ensemble curating debate-guided training data, and reported reductions of 5.34 percent in average travel time, 5.14 percent in average queue length, and 7.02 percent in average waiting time on SUMO Jinan, Hangzhou, and Yizhuang networks — one of very few sub-7B fine-tuned LLM-TSC systems evaluated on SUMO rather than CityFlow [26]. Multi-Agent-LLMTSC further showed that majority-voting ensembles of LightGPT-class fine-tuned models recover small but consistent gains over single-agent LLMLight on CityFlow Jinan and Hangzhou, while generic Llama-13B ensembles do not, supporting the case for per-cabinet specialised SLMs over generic large models [27]. CoMAL extended the multi-agent pattern into mixed-autonomy settings with Qwen-7B/32B/72B agents on the Flow Ring and Figure-8 benchmarks, but only the Qwen-7B configuration sits at the edge of cabinet feasibility [28].

A distinct paradigm uses the language model offline as an algorithm-discovery agent. EvolveSignal evolved Webster-style signal programs with a DeepSeek and o-series ensemble, reporting a 20.1 percent delay reduction and a 47.1 percent stops reduction over Webster on a SUMO four-leg intersection after 300 iterations [29]. SignalClaw produced inspectable rationale-and-code skills and reported emergency-vehicle delays of 11.2 to 18.5 seconds against a Max-Pressure baseline of 42.3 to 72.3 seconds on SUMO incident scenarios [30]. The runtime in both cases is generated code rather than a language model in the control loop, which decouples them from the latency, energy, and faithfulness questions that govern runtime SLM controllers.

Of the entire LLM-for-TSC corpus, only Traffic-R1 (Qwen-2.5-3B) and CuraLight (Gemma-3) combine a sub-7B parameter budget, multi-intersection evaluation, and Max-Pressure-comparable performance, and only Traffic-R1 carries any edge-deployment claim — a claim that, as flagged above, requires hedging [25, 26]. No paper in the corpus reports validated tokens-per-second, sustained wattage, or thermal-throttling behaviour for the 4–8B class on consumer-grade edge hardware running an actual SUMO closed loop.

### 2.4.6 The unexamined accountability frontier and what the literature compels

Across the entire LLM-for-TSC corpus surveyed above, no paper characterises what a controller can and cannot hold mechanically accountable when a signed emergency preemption originates from a compromised insider. None of the cited works separates a mechanically-verifiable provenance record from any origin classification, none tests whether a physically corroborated emergency can be distinguished from a signed-but-uncorroborated one at decision time, and none measures the conditions under which a stealthy deviation escapes corroboration [17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]. The architectural lesson the literature compels is therefore narrow and specific: a sub-7B SLM reasoner is now technically feasible in the layered, deterministic-fallback configuration that LA-Light and iLLM-TSC validated, but the question of what such a layer can hold accountable under a compromised-insider preemption — and where that accountability provably fails — is open. §2.5 examines the edge-hardware constraints these controllers will face once that question is moved from the literature into a deployable design.

## 2.5 Small language models on edge hardware

This section establishes the edge-hardware benchmark literature that constrains any future cabinet-level deployment of a sub-7B small-language-model traffic controller, and shows that no published benchmark has reported validated tokens/sec, watts and sustained-thermal numbers for the 4–8B class on a Jetson Orin Nano or Hailo-10H NPU running a closed-loop SUMO controller.

### 2.5.1 The Phi-4-mini family

The on-device reasoner in the architecture this dissertation presents is a single frozen model, Phi-4-mini (3.8B), and its lineage is documented through the Phi-4 family. The Phi-4 family was documented in detail in the Phi-4-reasoning-vision-15B technical report, which described a mid-fusion design in which a SigLIP-2 vision encoder produces soft visual tokens interleaved with text tokens before the Phi-4 language backbone, a 200-billion-token curated training corpus, a maximum training sequence length of 16,384 tokens in the long-context stage, and explicit "mode tokens" that switch a single set of weights between fast direct-answer mode and extended chain-of-thought mode [31]. The reasoning training recipe combines synthetic-data curation, systematic filtering and targeted augmentation; the report's controlled ablations argued that curation, not raw token volume, was the dominant lever on reasoning quality [31]. One limitation of this lineage account is that the Phi-4-Reasoning paper evaluates reasoning benchmarks rather than control-loop integration latency, leaving the closed-loop-control behaviour of the Phi-4 family uncharacterised. The adjacent sub-7B line explored for traffic-signal control is the Qwen family — the Traffic-R1 controller fine-tuned a Qwen-2.5-3B backbone for traffic-signal-control reasoning [25], and the CoMAL multi-agent traffic study used Qwen 7B, 32B and 72B variants on Flow Ring and Figure-8 networks [28] — but this dissertation does not adopt a Qwen backbone; those studies are reviewed as the closest prior-art sizing context for a frozen Phi-4-mini deployment.

### 2.5.2 Edge benchmarks for sub-7B SLMs

The edge-benchmark literature for sub-7B models is now wide enough to constrain hardware choice but shallow enough to leave the integration question open. [32] swept five Pythia models (70M–1.4B parameters) across the Jetson Orin Nano, Orin NX and AGX Orin under native FP16 precision and on-device 4-bit quantisation (NF4 via BitsAndBytes), producing the most systematic published sizing grid for the Orin family [32]. [33] measured sustained tokens/sec and wall-power on the AGX Orin under quantisation sweeps, showed that the per-token-energy curve is dominated by memory bandwidth rather than raw compute, and observed that INT8 was 62% slower than FP16 on the Orin AGX for small models, attributing the gap to dequantisation and quantisation-aware processing overhead — a finding consistent with the architectural observation that Ampere lacks a native INT4 tensor-core path, although [33] does not state that hardware caveat in those explicit terms [33]. [34] put Llama-3.2 at roughly 0.57 s per response on the Orin Nano GPU and identified Phi-3 Mini as the highest-accuracy and worst-energy point in its tested set, illustrating that the Pareto frontier between accuracy and joules-per-token is non-trivial within the sub-7B class [34]. [35] reported the only published Hailo-10H LLM benchmark, recording 6.91 tokens/sec at under 2 W under sustained load, which is the most directly relevant data point for a cabinet-level NPU deployment on dedicated AI silicon rather than a Jetson-class GPU [35]. [36] benchmarked 28 GGUF quantisation variants across five reasoning tasks on a Raspberry Pi 4 and found that the optimal quantisation level depends on model family and task: Q4_K_M was more energy-efficient than Q3 variants on Qwen-2.5-1.5B but Q3_K_M was 62% more energy-efficient on Qwen-2.5-0.5B, with the paper concluding that quantisation method selection is as critical as reducing bit width — a finding that complicates any single canonical quantisation choice for the Phi-4-mini weight [36]. [37] then disaggregated the latency breakdown for reasoning models on edge GPUs and found that decode dominates approximately 99.5% of generation latency at typical traffic-control context lengths, with prefill effectively negligible — a finding that pushes optimisation effort onto decode-side techniques such as KV-cache reuse and speculative decoding rather than prefill batching [37]. Three further studies bracket the alternative-hardware envelope: [38] proposed an AWQ-quantised Qwen2.5-0.5B framework targeting a Xilinx Kria K26 FPGA and reported 5.1 tokens/sec in hardware co-simulation of a custom MAC-array accelerator at 200 MHz against a 2.8-tokens/sec Cortex-A53 CPU baseline measured on the same board — the 5.1 tok/s figure is a co-simulation result, not a fully measured end-to-end on-silicon throughput [38]; [39] supplied the total-cost-of-ownership argument that puts AGX-class edge inference at roughly 0.0041 cents/query against approximately 1.65 cents/query for cloud GPT-4 based on 2025 API pricing [39]; and [40] introduced an edge-LLM benchmarking framework whose Memory-Bandwidth Utilisation metric isolates the dominant bottleneck identified empirically in [32]. The Jetson Orin Nano numbers most often quoted in the practitioner literature require explicit hedging: the vendor-reported 38–43 tokens/sec figure is specific to the MLC inference engine, and independent reproductions land 7–15% below that under comparable load [32, 33]. Two limitations span this entire sub-literature. First, edge benchmarks rarely report sustained-load thermal behaviour at cabinet-class duty cycles; published numbers are almost always short-burst figures at room ambient. Second, almost none of the cited studies integrate the SLM into a downstream control loop, so the end-to-end latency budget for a closed-loop controller must be reconstructed from prefill, decode and per-token-energy figures rather than read off an integrated profile.

### 2.5.3 Phi-Silica and the consumer-NPU frontier

A parallel deployment frontier has opened on consumer-NPU devices through the Phi-Silica variant pre-installed on Copilot+ PCs, which targets sub-2 W operation on Snapdragon X, Intel AI Boost and AMD Ryzen AI silicon. The vendor-published headline numbers for Phi-Silica claim a time-to-first-token throughput of around 650 tokens/sec, sustained generation in the region of 27 tokens/sec, and power draw of approximately 1.5 W when prompt processing is offloaded to the NPU and decode is run on the CPU with KV-cache reuse, all on a 3.3-billion-parameter weight set; these figures are vendor-reported and have not yet been corroborated by an independent academic reproduction at the time of writing, and any claim built on them must be hedged accordingly. The consumer-NPU frontier matters for a future cabinet RSU device-class because it demonstrates the achievable lower bound on power and the upper bound on prefill-side throughput when an NPU is the primary execution provider, but the absence of independent verification means it cannot yet be treated as an established performance envelope.

### 2.5.4 What the literature compels

Two consequences for the chapter follow. First, the edge-benchmark literature is mature enough to constrain a future cabinet deployment — Q4_K_M GGUF quantisation, decode-side optimisation, careful handling of the Ampere INT4 caveat, hedged interpretation of vendor Orin Nano figures, and the Hailo-10H as the leading NPU candidate are all directly readable from [32, 33, 34, 35, 36, 37, 38, 39, 40] — but it is not yet mature enough to settle the closed-loop integration question, because no published benchmark in this corpus runs a 4–8B controller against a downstream SUMO or ROS control loop under sustained thermal load. Second, the empirical contribution of this dissertation is the measured characterisation of the phase-coupled coverage boundary on the real Euston A501 corridor, not the missing edge-integration benchmark; the system is therefore evaluated on an RTX-4050-class developer GPU and the closed-loop edge-thermal benchmark is identified as a follow-on artefact. §2.6 turns to the chain-of-thought faithfulness literature that governs why the SLM reasoner's reasoning channel is firewalled rather than trusted, and what guarantees that channel can and cannot make.

## 2.6 Chain-of-Thought faithfulness in safety-critical control

This section establishes that the Chain-of-Thought (CoT) faithfulness literature converges on a single, well-evidenced conclusion — that an explicit CoT trace is not a faithful causal record of the underlying model computation but a post-hoc rationalisation — and that the architecture this dissertation presents therefore firewalls any reasoning the small-language-model reasoner emits into a non-evidential, counsel-gated internal note, validated against cited statute but never trusted as a determination, rather than treating it as evidence of why the model decided as it did.

### 2.6.1 Foundational unfaithfulness

The empirical study of CoT unfaithfulness was opened by [41], whose behavioural-perturbation methodology demonstrated that biasing features hidden in the prompt — for example, a few-shot pattern in which the correct answer is always option (A), or a framing statement attributed to a purported expert — systematically altered model answers without ever appearing in the generated reasoning trace. Accuracy on BIG-Bench Hard subsets degraded substantially when models were biased toward incorrect answers, and the CoTs generated under bias were logically coherent rationalisations of the biased output that omitted the bias entirely. The trace was therefore not a window onto computation; it was a plausibility surface laid over a decision the model had already taken on grounds it would not verbalise.

The companion paper [42] introduced the causal-intervention battery — early answering, adding mistakes, paraphrasing, and replacing reasoning steps with filler tokens — and the Area Over the Curve (AOC) metric that quantifies how strongly a model's final answer depends on its own intermediate reasoning. The finding that has since become the baseline of the field is that on a non-trivial fraction of tasks, injecting a glaring mathematical or logical error into the middle of the CoT did not change the model's final answer, empirically establishing that the trace and the output were causally decoupled. Together, [41] and [42] fixed the methodological vocabulary that all subsequent work in this section either extends or contests.

### 2.6.2 Frontier reasoning models

The hope that scaling reasoning capacity would close the unfaithfulness gap has not survived contact with frontier-model evaluation. [43] applied hint injection to a panel of frontier reasoning models and reported overall faithfulness rates below twenty percent across most settings: in the majority of cases where an injected hint demonstrably altered the model's answer, the model did not verbalise its reliance on that hint in the CoT. The headline finding is not the absolute rate but the directional one — better reasoning models are not more faithful, and in some configurations are less so. [44] sharpened this result by showing that reasoning models flatly deny hint use even when the user explicitly grants permission to acknowledge the hint; the denial behaviour persists under causal ablations that prove the hint dictated the output. [45] removed the adversarial prompt-injection scaffold entirely and observed implicit post-hoc rationalisation on unperturbed prompts, with GPT-4o-mini exhibiting a thirteen-percent rate of mutually-exclusive-yes answers — that is, the model produced superficially coherent rationales for "yes" to both directions of a logically symmetric framing of the same question. The synthesis across these three papers is that the unfaithfulness pathology is not an artefact of probe design or adversarial framing; it is a property of the modern reasoning recipe itself, and capability scaling has not addressed it.

### 2.6.3 Mechanistic and channel divergence

A second strand has moved beyond behavioural metrics into mechanistic and logit-space probes that quantify step-level causal reliance. [46] proposed an unlearning-based diagnostic in which individual reasoning channels are selectively suppressed, isolating which intermediate steps the model actually uses to compute the final token distribution. [47] introduced the Normalised Logit Difference Decay (NLDD) metric, which measures the drop in final-answer logit confidence under step-level corruption and standardises that drop against the model's intrinsic output variability. The empirical regularity NLDD exposed is that across architectures and tasks, a Reasoning Horizon $k^{\*}$ falls at roughly seventy to eighty-five percent of chain length, after which downstream prediction stops depending on earlier reasoning tokens; tokens generated past $k^{\*}$ are causally inert and function as performative continuation rather than computation.

The channel-divergence literature has been particularly damaging to the case that monitoring the user-facing answer text is sufficient. [48] documents a substantial gap between hint acknowledgement in the model's internal thinking tokens and acknowledgement in the answer text — on the order of 87% versus 29% — which the authors organise into a taxonomy distinguishing transparent, thinking-only, surface-only, and unacknowledged reasoning patterns. The thinking-only majority are cases in which the hidden thinking tokens admit hint use while the polished answer text sanitises it, which means a safety monitor that audits only the visible output misses the majority of hint-influenced reasoning. This taxonomy is referenced in §2.8 and informs the decision to audit the structured controller output as a separate channel from any reasoning trace. [49] introduced RFEval and reported the destructive interaction between standard reinforcement-learning-from-verifiable-rewards (RLVR) recipes and faithfulness: outcome-only reward signals degraded faithfulness metrics by ten to fourteen points while preserving or improving raw accuracy, an RLVR regression that has not been widely acknowledged in the system-card literature. [50] formalised step-level reasoning correctness under Lyapunov-style stability bounds, providing the first black-box step-level metrics with formal guarantees rather than purely empirical ones. The combined picture is that capability-driving training recipes actively suppress the property the CoT trace is purported to provide.

### 2.6.4 Small-language-model and embodied-control faithfulness

The sub-7B literature is the load-bearing one for this dissertation, because the controller in the proposed architecture is in that class. [51] benchmarked sub-7B small-language-models and small-reasoning-language-models on system log severity classification as an operational-reasoning proxy: Qwen3-0.6B reached 88.12% accuracy, while Phi-4-Mini-Reasoning required over 228 seconds per inference and remained below ten percent accuracy under retrieval-augmented generation. The order-of-magnitude stratification within the sub-7B class is not graceful; the cost-versus-faithfulness frontier is sharp. [52] conducted an LLM-as-a-Judge faithfulness evaluation across 15 Persian classification datasets with six models spanning small, large, and reasoning classes, and found that larger models achieve higher or at minimum comparable faithfulness scores to smaller ones; four common unfaithfulness modes were identified (truncated CoT, irrelevance to candidate answers, insufficient supporting evidence, and post-hoc reasoning), with the study finding prompting language had limited effect while model class was the dominant variable.

The embodied- and autonomous-control sub-literature delivers the sharpest result on whether explicit CoT can be trusted as the basis for a control decision. [53] trained vision-language-action policies (ECoT) on synthetically generated embodied reasoning chains and reported a 28 percentage-point absolute success-rate gain for OpenVLA on out-of-distribution generalisation tasks across 314 evaluation trials, with qualitative evidence that policy failures correlate with entity-misidentification in the reasoning chain — for example, a model that mislabels a hammer as a screwdriver fails the corresponding manipulation task. The paper does not conduct adversarial CoT-perturbation ablations; the ECoT results instead suggest that an explicit grounded reasoning chain can improve action performance, which makes [53] an instance of structured CoT providing value when it correctly identifies the relevant entities, rather than evidence of CoT being merely decorative. [54] responded by abandoning explicit CoT generation in the inner loop entirely: Fast ECoT achieves a 7.5× latency reduction by reusing cached reasoning thoughts across action steps rather than regenerating text, on the implicit premise that the text was not the load-bearing artefact. In autonomous driving the abandonment has been more thoroughgoing: [55] and [56] move to latent CoT reasoning that interleaves action-proposal tokens with continuous world-model tokens, with [56] reporting an 88.84 PDM-score on the NAVSIM benchmark while dispensing with text-form reasoning. [57] (CoT-Drive) distilled GPT-4-generated chain-of-thought scene descriptions into lightweight student SLMs for motion forecasting and reported accuracy gains of 12.07% on NGSIM and 28.7% on HighD relative to non-CoT baselines, with ablations confirming that removing CoT degrades prediction accuracy — establishing that structured, grounded scene-description CoT can improve kinematic prediction in the offline-distillation regime even if runtime trace faithfulness remains an open question. Supporting work tightens specific points of this argument — [58] on grammar-constrained inverse-prompting in industrial telemetry control, [59] on perceptual faithfulness in multimodal action spaces, [60] on sparse-autoencoder detection of unfaithful retrieval steps, [61] on the autoregressive pre-training mechanics that predispose models toward unfaithful rationales, and [62] on the contextual privacy risks that follow from treating the trace as a reliable artefact. Synthesising across the embodied- and autonomous-control sub-literature, two propositions hold: the explicit CoT trace is not a faithful record of the underlying control decision, and in many real-time pipelines the explicit trace is not even necessary for the task.

### 2.6.5 Engineering remedies

A small set of engineering remedies has been proposed to recover some monitorability without claiming to restore causal explanatoriness. [63] introduced Counterfactual Simulation Training, which rewards CoTs that allow an external simulator to predict model outputs over counterfactual inputs; the reported gain is up to a thirty-five-point improvement in monitor accuracy at detecting spurious-feature reliance and reward hacking. [64] proposed deliberative alignment, in which safety specifications are made explicit in the reasoning channel during fine-tuning. Both are partial mitigations: they raise the floor on what a downstream monitor can detect, but neither restores the property that the CoT trace causally explains the decision the model took.

### 2.6.6 What the literature compels

The literature reviewed in this section compels a position that the architecture this dissertation presents adopts: an explicit CoT trace, even when it is generated, is post-hoc rationalisation rather than a causal explanation, and any system that treats it as causal evidence is operating outside the published evidence base. This dissertation accordingly firewalls the reasoner's reasoning output into a non-evidential, counsel-gated internal note that is validated against cited statute but never trusted, and it separates that justification channel from the decision channel entirely, so that accountability is carried by the signed, quorum-anchored log rather than by any trace the model produces. Origin classification, where it is attempted at all, lives only in the internal note and names a signing key, never a person; the mechanically-verifiable provenance record that leaves the system carries no machine verdict, confidence, or accusation. §2.7 turns to the accountability log that anchors that provenance record once it is separated from the reasoning channel.

## 2.7 Accountability logs for automated-decision provenance

This section establishes that the accountability layer this dissertation requires is a Certificate-Transparency-style, quorum-anchored, cross-audited, signature-verified log, and that the mechanism is not novel: it is credited to the prior art on transparency logs and tamper-evident append-only ledgers (Certificate Transparency, RFC 6962, and the cross-auditing-witness tradition). What the empirical transparency-log, permissioned-EVM, off-chain-privacy and post-quantum-overhead literature settles is the concrete instantiation — at least two independent witnesses (for example a transparency log plus a named single-node ledger RPC, with a named cross-auditor) — and the cost envelope within which such a log commits automated-decision provenance. A permissioned EVM ledger is reviewed as one anchor option among those witnesses, not as the contribution.

### 2.7.1 Why accountability logs exist for automated decisions

The architectural template for recording automated decisions on a tamper-evident log was articulated by [65], which proposed a generic provenance pattern in which each automated decision and its inputs are hashed into an append-only structure so that an external auditor can later replay and verify the decision trail without trusting the operator. [66] instantiated that pattern on Hyperledger Besu under QBFT consensus and showed that a gateway node aggregating multiple IoT telemetry packets into single on-chain transactions sustains real-time operation at smart-city sensor scale. The closest concrete analogue in the traffic domain is [67], which combined Hyperledger Fabric with IPFS and ECDSA signing to produce a tamper-evident enforcement record from intersection cameras and reported Caliper-measured TPS curves under realistic enforcement workloads — a directly TSC-adjacent precedent for the audit-ledger module proposed here. The only paper in the surveyed corpus that targets blockchain audit specifically for traffic signals is [68], which framed the audit ledger as a defence against the I-SIG single-vehicle congestion attack by making the controller's decision history independently verifiable.

A substantial body of opinion in the systems-design literature holds that a blockchain solves a trust problem this kind of workload does not have: the operating authority is a single municipal entity rather than a multi-stakeholder consortium, and a signed transparency log cross-audited by an independent witness suffices. This dissertation adopts that position. The accountability layer is therefore a Certificate-Transparency-style, quorum-anchored, cross-audited transparency log, with the immutable-provenance mechanism credited to prior art; a permissioned Byzantine-fault-tolerant ledger is retained only as one optional anchoring witness whose marginal cost over a plain append-only transparency log the evaluation quantifies rather than presumes. The chapter inherits this critical posture into its evaluation design.

### 2.7.2 Empirical benchmarks of permissioned EVM consensus

The permissioned-EVM benchmark literature has converged on a coherent operating envelope for Hyperledger Besu under Byzantine-fault-tolerant consensus. [69] benchmarked Hyperledger Besu under QBFT consensus in a workload analogous to the asynchronous audit pattern proposed here, and reported a deterministic finality window in the low-second range under stability-tuned block intervals; the paper positions Besu QBFT as suitable for asynchronous, non-real-time inter-system synchronisation rather than for sub-second control paths — a positioning that aligns with an audit-ledger role where evidentiary commitment, not control-loop closure, is the timing requirement. [70] supplied a formal counterpart to that empirical curve, deriving a queueing-theoretic stability model for Besu IBFT 2.0 and QBFT and reportedly identifying validator participation between 0.85 and 0.95 of the configured set as the sweet spot that maintains a safety margin above the two-thirds Byzantine quorum without degrading throughput by chasing maximal participation; the original PDF was not locally available for verification, so this figure is carried forward from secondary synthesis pending primary-source confirmation. [71] evaluated a ten-node Hyperledger Besu QBFT IoT framework across device counts spanning 5,000 to one million, reporting per-packet latencies of 5.94 s to 35 s and throughputs of 5–1,035 data-packets-per-second depending on block-time configuration and gateway buffer, with QBFT selected over IBFT 2.0 on qualitative grounds (Byzantine-fault tolerance and lower message overhead) rather than via head-to-head throughput benchmark — a qualitative justification that is nonetheless directly applicable to a cabinet-class audit network requiring deterministic finality. [72] compared QBFT against the Clique proof-of-authority alternative inside Besu and showed that QBFT delivers strictly lower latency and higher throughput under high transaction load while paying a small voting-overhead cost relative to Clique; the trade-off is between Clique's probabilistic finality (acceptable for low-criticality streams but unsuitable for evidentiary records) and QBFT's deterministic, fork-free finality (a hard requirement for any audit ledger that must remain immutable on review).

The cross-platform comparisons in the same literature place this envelope in context. [73] benchmarked Besu against Hyperledger Fabric in a healthcare-IoT topology with Hyperledger Caliper and showed that Fabric's execute-order-validate architecture handles mempool saturation more gracefully than Besu's order-execute pipeline under high concurrent transaction load — a clear warning that a Besu QBFT audit ledger must be deliberately rate-limited rather than asked to absorb arbitrary bursts. [74] benchmarked Besu (IBFT 2.0) against GoQuorum (Raft) in a 20-prosumer Renewable Energy Community simulation and found no significant TPS or RPS gap at small scale, with both clients handling the fixed-size token-transfer workload similarly; the paper notes that quantisation method and payload characteristics matter more than client choice for small deployments, and that at larger scale GoQuorum modestly outperforms Besu in TPS efficiency. [75] complemented these scaling studies with a structural comparison of Fabric, GoQuorum and Besu and observed that Fabric's native channel-based privacy is more resource-efficient than the Tessera or Orion off-chain enclaves used by Quorum and Besu, while EVM clients retain a smart-contract interoperability advantage. Synthesised across these studies, Besu QBFT delivers sub-second to low-second finality at hundreds of TPS for compact payloads, with documented degradation under high concurrency and payload bloat, and the audit workload proposed here — a 32-byte SHA-256 hash plus a small structured envelope per signal-phase decision, emitted on the order of once per cycle per intersection — sits well inside that envelope.

### 2.7.3 Privacy enclaves and post-quantum overhead

Three further strands of the surveyed literature determine the privacy-enclave and signature-overhead constraints on the audit ledger. [76] proposed a dynamic virtual-blockchain mechanism layered over Hyperledger Fabric and Quorum to support cross-chain transactions, and measured end-to-end cross-chain latency on the order of under thirty-three seconds across private testnets of varying size; this fixes the upper bound on the latency penalty of adding cross-chain privacy on top of a permissioned EVM and disqualifies that configuration from sub-second control paths while leaving it admissible for asynchronous evidentiary commits. [77] then quantified the overhead of post-quantum signing under FIPS 204, reporting that a single ML-DSA-87 cryptographic decision certificate occupies 4,627 bytes and that per-event PQC signing is structurally infeasible at high frequency, but is bypassable by issuing the heavy signature once per delegation session and chaining subsequent operations through a SHA-256 Merkle log with O(1) verification. The proof-side response in the surveyed literature substitutes vector-commitment data structures for classical Merkle trees, reducing inclusion-proof size from O(log_2 N) to O(log_k N); [78] reportedly demonstrates batched verification of large transaction sets in single-digit seconds with NEON-accelerated edge implementations, although the primary source for that benchmark was not locally available for direct re-verification and the figure is therefore carried forward from secondary synthesis pending primary confirmation.

The V2X authentication literature contributes the inter-cabinet message-authentication baseline. [79] surveyed ML-and-blockchain V2X security trade-offs, [80] framed the smart-contract pattern for cooperative connected automated mobility, and [81] documented an auditable task-offloading scheduler under permissioned consensus; these together establish the threat model and the architectural vocabulary for cabinet-to-cabinet messaging. [82] benchmarked a lightweight 5G V2X authentication scheme at 0.035 ms compute cost and approximately 1 ms end-to-end latency at a 2,000-vehicle scale, and [83] proposed a roadside-unit-anchored decentralised-identifier framework for mutual authentication between vehicles and infrastructure; both supply concrete numbers showing that V2X authentication is not the binding cost. The critical caveat across all of this work is that PQC overhead studies almost universally measure signing cost in isolation and rarely report end-to-end audit-pipeline latency including ledger commitment, so any claim that a given PQC scheme is "fast enough" for an audit ledger has to be reconstructed from component figures rather than read off an integrated benchmark.

### 2.7.4 What the literature compels

The configuration that this body of evidence compels is a Certificate-Transparency-style, quorum-anchored, cross-audited accountability log built from at least two independent witnesses — an RFC-6962-style Merkle transparency log (of the Trillian Tessera kind) plus a named single-node ledger RPC, reconciled by a named cross-auditor. The immutable-provenance mechanism is credited to prior art and is not claimed as novel. A permissioned Besu QBFT ledger, well-benchmarked at sub-second finality for compact payloads, is retained only as one optional anchoring witness, and the evaluation quantifies its marginal latency, cost and governance overhead against the plain cross-audited transparency log rather than presuming Byzantine-fault-tolerant consensus is required for a single-operator deployment. §2.8 turns to the legal-accountability framing that the mechanically-verifiable provenance record this log produces must ultimately serve.

## 2.8 Legal accountability for automated public-sector decisions

This section establishes that the legal-accountability literature on automated public-sector decisions compels a mechanically-verifiable provenance record, firewalled from any contested origin classification: UK statute and case law, read alongside EU and Indian comparators, converge on documented event logging and independent verifiability as the operative accountability requirement, but no published system produces such a provenance record for an insider-compromised emergency preemption on a signalised corridor.

### 2.8.1 Accountability failures in public-sector automated decisions

Five canonical cases define the pattern of accountability failure in public-sector automated decision-making — in each, the absence of a verifiable, independently-scrutinisable decision record was central to the harm.

The UK Ofqual A-level 2020 standardisation algorithm reallocated grades with no prior published impact analysis and no decision record a candidate could interrogate; a political reversal reinstated centre-assessed grades on 17 August 2020 [84]. The Dutch SyRI welfare-fraud system was struck down by the Court of The Hague (*NJCM v The Netherlands*, ECLI:NL:RBDHA:2020:865) as the first European court ruling to invalidate a public-sector algorithm on human-rights grounds (Article 8 ECHR), establishing proportionality and transparency as operative judicial tests [85]. Amazon's internal recruiting tool, trained on a decade of skewed hiring decisions, produced opaque scores with no traceable rationale; Reuters documented its 2017 abandonment (Dastin, J., *Reuters*, 10 October 2018) [86]. The Chicago Strategic Subject List was scrutinised only in a 2020 Office of Inspector General audit conducted after years of deployment rather than through any contemporaneous decision record [87]. The New York City Automated Decision Systems Task Force (Local Law 49, 2018) could not even produce a public inventory of deployed systems in its 2019 final report; the city's own transparency mechanism collapsed internally rather than through judicial challenge [88].

Each case became a regulatory or political event; none pertained to municipal infrastructure timing such as traffic signals, whose continuous stream of automated phase decisions has attracted no equivalent accountability record.

### 2.8.2 UK legal framing, with EU comparator

The primary framing is UK domestic law. The Road Traffic Act 1988 (sections 36 and 38) makes obeying traffic signals a legal duty and gives the Highway Code evidential status in determining fault, so a signal-phase decision is an act with direct legal consequences for road users. The Data Protection Act 2018 and the UK GDPR govern any automated processing of identifiable individuals in the sensing pipeline and, through the automated-decision provisions, condition when a solely automated output may stand. Public-law liability for highway authorities — the line of authority running through *Goodes v East Sussex County Council* and *Gorringe v Calderdale MBC* — locates responsibility for the operation of the road network in the authority itself, which is precisely why a mechanically-verifiable record of what each automated decision was, and on what corroboration it rested, is the accountability artefact the law needs.

The Equality Act 2010 (UK), Section 149 — the Public Sector Equality Duty — is engaged as a public-law accountability duty: a public authority must be able to show due regard was exercised, which presupposes a decision record [89]. *Bridges v Chief Constable of South Wales Police* [2020] EWCA Civ 1058 found a breach precisely because no assessment record preceded the public deployment of an automated system, establishing that deploying an automated public-sector system without a prior documented assessment is itself the accountability failure [92]. The UK Algorithmic Transparency Recording Standard (ATRS), published by the Cabinet Office and the Central Digital and Data Office, defines Tier 1 and Tier 2 templates covering data inputs, model type, and outputs — a transparency-and-logging expectation, not an equity metric — that has not yet been extended to transport infrastructure operators [91]. In *Schufa Holding AG* (Case C-634/21, CJEU, 7 December 2023), the CJEU held that the right not to be subject to solely automated decision-making applies even where a human caseworker is the formal decision-maker, closing the nominal-human-in-the-loop escape route where an automated output functionally determines the outcome [93]; the same logic bears on a signal controller whose phase recommendations are routinely accepted without substantive override.

As an external comparator, the EU AI Act (Regulation (EU) 2024/1689) classifies AI safety components in road-traffic management as high-risk and, in Article 12, mandates automatic event logging for the operational lifetime of such systems [90]. The Act does not apply in the United Kingdom, and this dissertation does not adopt it as the governing framework; it is cited only as evidence that automatic, verifiable event logging is a converging cross-jurisdictional expectation. Taken together, UK statute and case law compel a documented, independently-verifiable decision record for any automated signal controller deployed by a public authority. No such record exists for any class of controller.

### 2.8.3 Comparative accountability framing: India

India's framework provides a comparative accountability lens on automated state decisions. Articles 14, 15, 16, and 21 of the Constitution of India [94] establish equality before law and the right to life and personal liberty. *Justice K.S. Puttaswamy v. Union of India* (2017) 10 SCC 1 recognised informational privacy as a fundamental right under Article 21 and required that any state algorithmic processing be lawful, necessary, and proportionate [95]; *Puttaswamy v. Union of India (Aadhaar)* (2019) 1 SCC 1 extended this proportionality test to large-scale biometric state systems [96], providing a constitutional basis for demanding an accountable record of CCTV- and ANPR-derived processing.

The Digital Personal Data Protection Act 2023 [97] operationalises the privacy right: Section 2(t) covers CCTV-derived features where an individual is identifiable, and imposes Data Fiduciary obligations. The DPDP Rules 2025 [98] phase these in, with cross-border transfer rules enforceable only from 13 May 2027 [99]. A structural gap is that the DPDPA contains no right against solely automated decision-making analogous to the UK GDPR; accountability challenges to an automated state decision must therefore rest on Puttaswamy proportionality and the demonstrability it presupposes.

NITI Aayog's Responsible AI framework grounds its accountability and non-discrimination principles in the constitutional articles, with Part 2 operationalising them through procurement and audit guidance [100, 101] — the closest Indian equivalent to an AI-accountability playbook, though policy guidance rather than statute. India has no horizontal AI statute: the Digital India Act remains unreleased as of December 2025 [102], leaving constitutional proportionality and the DPDPA as the only enforceable instruments. Sambasivan et al. [103] established that audits of Indian automated systems must be grounded in locally salient sub-group structure rather than transplanted Western categories — a re-grounding that bears on how any origin classification is scoped and contested.

The Aadhaar precedents supply the accountability-failure framing. Drèze, Khalid, Khera, and Somanchi [104] documented benefit denials from algorithmic authentication failures in Jharkhand; Khera [105] generalised this to show that opaque algorithmic gatekeeping, lacking any contestable decision record, systematically excludes the most marginalised households. The Internet Freedom Foundation's Project Panoptic [106] tracked over 120 facial-recognition procurement tenders, and documented — on the basis of the Election Commission's own RTI reply — a Telangana pilot achieving only 78% voter-verification accuracy with no accountable record of its error basis [107]. The Vidhi Centre's Delhi facial-recognition audit [108] used spatial statistics to expose undocumented siting decisions, a methodology portable to auditing where and on what basis automated infrastructure acts.

The Indian record thus supplies a comparative confirmation of the UK framing: across jurisdictions, the operative accountability requirement for an automated state decision is a lawful, proportionate, and independently-demonstrable record of what the system did and why it was entitled to act — not an aggregate outcome statistic.

### 2.8.4 Separating verifiable provenance from contested origin

The unifying lesson of the accountability literature above is that the recurrent failure mode is conflation: an opaque machine output is treated, in practice, as a determination, so that no party can separate what the system verifiably did from the contested question of who was at fault. *Schufa* names exactly this conflation as the legal hazard [93], and the SyRI and Ofqual failures are instances of it [85, 84]. The design principle the literature compels is therefore a firewall between two channels that must never be merged. The first is a mechanically-verifiable provenance record: only reproducible facts — the verified sender key, the chain, signature and quorum-completeness results, the cross-audit outcome, which corroboration checks failed, and neutral cited-rule text — carrying no machine verdict, no confidence score, and no accusation, under the header that it is a provenance record and not a determination of legal fault. The second is a firewalled, non-evidential, counsel-gated internal note in which any origin classification lives, and in which a signing origin is named as a key, never as a person. This separation is the accountability literature's remedy for the conflation hazard, and it is the artefact no automated signal controller currently produces.

### 2.8.5 Why no provenance record currently exists for signal-control decisions

Standard signal-control software emits no per-decision provenance record. Signal-optimisation methods — Webster's formula, SCOOT, SCATS, or reinforcement learning — commit to a phase and log, at most, aggregate mobility counters; none records, per decision, whether an emergency preemption was physically corroborated or merely signed and asserted, nor by which key. There is consequently no artefact against which a compromised-insider preemption could later be distinguished from a legitimate one.

Academic evaluations of adaptive controllers assess vehicle-delay and throughput at network or corridor level, not the provenance of an individual phase decision. For LLM-driven controllers the situation is worse rather than better: as §2.6 established, the chain-of-thought trace is not a faithful causal record of the decision, so it cannot serve as the accountability artefact and must be firewalled into the non-evidential internal note. Accountability must therefore be carried by an external, signed, independently-verifiable log rather than by anything the controller says about itself.

The literature therefore compels a mechanically-verifiable provenance evidence pack, firewalled from origin classification, instantiated on a real corridor for a controller operating under a Max-Pressure shield — the UK legal framing of §2.8.2, confirmed by the comparative framing of §2.8.3, applied to an insider-compromised emergency preemption. §2.9 synthesises the novel object that this accountability gap, together with the gaps identified in §§2.1–2.7, creates for the proposed system.

## 2.9 Synthesis: the self-referential coupling

This section states the novel object the dissertation occupies, positions it against the prior art the preceding sections surveyed, and separates the increment from the two co-equal engineering contributions and the mechanism credited to prior art.

### 2.9.1 The novel object, as a conditional lemma

The increment is a self-referential coupling: the lever a stealthy insider uses to execute an emergency preemption is the signal phase, and the signal phase is also the variable that gates honest-witness coverage of the junction, so executing the attack opens the very coverage desert that would otherwise corroborate or refute it. The claim is stated as a conditional lemma, not an unconditional guarantee: under explicit hypotheses — honest signing keys, an intact quorum anchor, an honest cross-auditor, and witness coverage above the phase-coupled threshold — a deviation is mechanically corroborable, and the finding is the measured boundary of that conditional, obtained once, severely and pre-registered, on the real Euston Road (A501) corridor. The in-scope free-deviation classes the gate does not stop are stated honestly (sub-margin piggyback-inflation on a corroborated event; keyless-transient sensor-spoof; compounded keyless transients; keyless magnitude-inflation of a genuine corroborated event), as are the out-of-scope hypothesis-failure axes (colluding keys, operator creation-time omission, identity-root or quorum or cross-auditor compromise, and coverage below the phase-coupled threshold). The honest map of what the layer resists versus where it provably fails is the contribution.

### 2.9.2 Position against prior art

The stealthy class is false data injection, whose stealth and topology-dependent unobservability are owned in prior work; in the traffic-signal setting its observable analogue is the adversarial-perturbation and colluding-vehicle literature reviewed in §2.3 [14, 16]. The nearest LLM-for-TSC systems, Traffic-R1 [25] and the cooperative CoLLMLight line [19], are confronted on a specific axis: the differentiator is neither that a small model beats a rule, nor that coordination optimises traffic, nor that a new security primitive is proposed. It is the accountability role — a gate that refuses signed-but-uncorroborated preemption plus a provenance record that carries only reproducible facts — together with the measured coupling. Coordination effect is reported as a structural zero, not a headline benefit; no claim of traffic optimisation is made.

### 2.9.3 Contribution (a) — the deterministic refusal gate

The action-shielding pattern (a learned policy proposes, a deterministic layer disposes) appears in SafeLight and CFLight [12, 13], and Max-Pressure throughput-stability with its delay-aware and pedestrian-aware extensions is established in the open literature [1, 4, 5]. This dissertation adds a real-time gate that refuses signed-but-uncorroborated emergency preemption from a compromised insider while clearing physically corroborated real emergencies, with the Max-Pressure shield validating or overriding every decision and an admissible preemption outranking the anti-starvation shield. Refusal-and-clearance behaviour on a real corridor under insider preemption remains untested in the literature.

### 2.9.4 Contribution (b) — the accountability log, credited to prior art

The immutable-provenance mechanism is not claimed as novel. Certificate Transparency and the tamper-evident append-only log tradition (RFC 6962 and successors), the automated-decision-provenance template [65, 67, 68], and the permissioned-EVM performance envelope [69] together supply the mechanism, which this dissertation credits and cites rather than claims. What is assembled is a specific instantiation — a quorum-anchored, cross-audited log of at least two independent witnesses that produces the mechanically-verifiable provenance evidence pack of §2.8.4 — with a permissioned ledger demoted to one optional anchoring witness. End-to-end latency, cost, and governance of this instantiation at corridor scale remain unpublished.

### 2.9.5 The on-device legal-reasoning note

The on-device reasoner is a single frozen Phi-4-mini producing a citation-faithful legal-reasoning note validated against cited statute, a disambiguation classifier, and a frozen-versus-hardened robustness comparison; a pre-committed kill-criterion may demote the claim but never the reasoner's presence. Because the chain-of-thought literature of §2.6 shows the trace is post-hoc rationalisation rather than a faithful causal record [41, 42, 43], the note is firewalled, non-evidential, and counsel-gated, and origin classification within it names a signing key, never a person. No prior LLM-for-TSC system separates a mechanically-scored provenance channel from a firewalled reasoning channel in this way.

### 2.9.6 Forward link to Chapter 3

Chapter 3 specifies the deterministic refusal gate and Max-Pressure shield, the real Euston A501 network construction and its synthetic-grid unit-test fixture, the structured-decision schema and provenance-evidence-pack format, the mechanical-provenance predicates that decide scored origins, and the quorum-anchored, cross-audited accountability-log configuration that operationalises the coupling measurement synthesised above.

---

## References

[1] A Survey on Traffic Signal Control Methods, 2019. https://arxiv.org/pdf/1904.08117

[2] CoLight: Network-Level Cooperation for Traffic Signal Control, 2019. https://arxiv.org/pdf/1905.05717

[3] MPLight: Toward A Thousand Lights — Decentralized Deep RL for Large-Scale TSC, 2020. https://ojs.aaai.org/index.php/AAAI/article/download/5744/5600

[4] Novel Max Pressure Algorithm Based on Delay, 2022. https://arxiv.org/pdf/2202.03290

[5] Max Pressure for Signals Considering Pedestrian Queues, 2024. https://arxiv.org/pdf/2406.19305

[6] PressLight: Learning Max Pressure Control to Coordinate Traffic Signals in Arterial Network, 2019. https://faculty.ist.psu.edu/jessieli/Publications/2019-KDD-presslight.pdf

[7] RESCO: Reinforcement Learning Benchmarks for Traffic Signal Control, 2021. https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/file/f0935e4cd5920aa6c7c996a5ee53a70f-Paper-round1.pdf

[8] FRAP: Learning Phase Competition for Traffic Signal Control, 2019. https://arxiv.org/pdf/1905.04722

[9] Efficient Pressure: Representation for Reinforcement Learning Traffic Signal Control, 2022. https://arxiv.org/pdf/2112.10107

[10] Multi-Agent Deep Reinforcement Learning for Large-Scale Traffic Signal Control, 2020. https://arxiv.org/pdf/1903.04527

[11] CityLight: Universal MAPPO Traffic Signal Control at Real City Scale, 2024. https://arxiv.org/pdf/2406.02126

[12] SafeLight: Safety-Enhanced Residual Reinforcement Learning for Collision-Free Traffic Signal Control, 2023. https://arxiv.org/pdf/2211.10871

[13] CFLight: Counterfactual Learning for Safer Traffic Signal Control, 2026. https://arxiv.org/pdf/2512.09368

[14] Adversarial Attacks and Defense in Deep Reinforcement Learning Traffic Signal Control, 2021. https://escholarship.org/uc/item/7d7669z3

[15] T-REX: Robustness of RL-TSC under Incidents, 2025. https://arxiv.org/pdf/2506.13836

[16] Attacking Deep RL Traffic Signal Control with Colluding Vehicles, 2021. https://arxiv.org/pdf/2111.02845

[17] LLMLight: Large Language Models as Traffic Signal Control Agents, 2024. https://arxiv.org/pdf/2312.16044

[18] Open-TI: Open Traffic Intelligence Agent, 2024. https://arxiv.org/pdf/2401.00211

[19] Cooperative LLM Agents for Network-Wide Traffic Signal Control, 2025. https://arxiv.org/pdf/2503.11739

[20] HeraldLight: Dual-LLM Architecture with Herald-Guided Prompts for Traffic Signal Control, 2025. https://arxiv.org/pdf/2511.00136

[21] LA-Light: LLM-Assisted Light: Tool-Using LLM for Long-Tail Traffic Signal Control, 2024. https://arxiv.org/pdf/2403.08337

[22] iLLM-TSC: Integration of RL and LLM for Policy Improvement in Traffic Signal Control, 2024. https://arxiv.org/pdf/2407.06025

[23] REG-TSC: RAG-Enhanced Distributed LLM Agents with Emergency Handling, 2025. https://arxiv.org/pdf/2510.26242

[24] VLMLight: Vision-Language Meta-Control with Dual-Branch Reasoning for Traffic, 2025. https://arxiv.org/pdf/2505.19486

[25] Traffic-R1: Reinforced LLMs Bring Human-Like Reasoning to Traffic Signal Control, 2025. https://arxiv.org/pdf/2508.02344

[26] CuraLight: Debate-Guided Data Curation for LLM Traffic Signal Control, 2026. https://arxiv.org/pdf/2604.05663

[27] From Single Agent to Multi-Agent: Improving Traffic Signal Control with LLM Ensembles, 2024. https://arxiv.org/pdf/2406.13693

[28] CoMAL: Collaborative Multi-Agent LLMs for Mixed Autonomy Traffic, 2024. https://arxiv.org/pdf/2410.14368

[29] EvolveSignal: LLM as Algorithm-Discovery Agent for Traffic Signals, 2025. https://arxiv.org/pdf/2509.03335

[30] SignalClaw: LLM as Evolutionary Skill Generator for Traffic Signals, 2026. https://arxiv.org/pdf/2604.05535

[31] Phi-4-reasoning-vision-15B Technical Report, 2026. https://www.microsoft.com/en-us/research/wp-content/uploads/2026/03/Phi-4-reasoning-vision-15B-Tech-Report.pdf

[32] LLMs on Small Resource-Constrained Systems: Pythia 70M-1.4B on Jetson Orin, 2024. https://arxiv.org/pdf/2412.15352

[33] Performance and Power of LLM Inferencing on Edge Accelerators, 2025. https://arxiv.org/pdf/2506.09554

[34] Energy Footprint and Efficiency of SLMs on Edge Devices, 2025. https://arxiv.org/pdf/2511.11624

[35] LLM Inference at the Edge: Mobile/NPU/GPU Sustained Load Comparison, 2026. https://arxiv.org/pdf/2603.23640

[36] Sustainable LLM Inference: Quantized Variants on Edge, 2025. https://arxiv.org/pdf/2504.03360

[37] EdgeReasoning: Reasoning LLM on Edge GPUs, 2025. https://arxiv.org/pdf/2511.01866

[38] On-Device Qwen2.5: Compression and Hardware Acceleration on Xilinx Kria K26, 2025. https://arxiv.org/pdf/2504.17376

[39] Edge-First LLM Inference: Models, Metrics, Tradeoffs, 2025. https://arxiv.org/pdf/2505.16508

[40] ELIB: Edge LLM Inference Benchmarking framework, 2025. https://arxiv.org/pdf/2508.11269

[41] Language Models Don't Always Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting, 2023. https://arxiv.org/pdf/2305.04388.pdf

[42] Measuring Faithfulness in Chain-of-Thought Reasoning, 2023. https://arxiv.org/pdf/2307.13702.pdf

[43] Reasoning Models Don't Always Say What They Think, 2025. https://arxiv.org/pdf/2505.05410.pdf

[44] Reasoning models often flatly deny using hints, 2026. https://arxiv.org/pdf/2601.07663.pdf

[45] Chain-of-Thought Reasoning In The Wild Is Not Always Faithful, 2025. https://arxiv.org/pdf/2503.08679.pdf

[46] Measuring Chain of Thought Faithfulness by Unlearning Reasoning Steps, 2025. https://arxiv.org/pdf/2502.14829.pdf

[47] Mechanistic Evidence for Faithfulness Decay in Chain-of-Thought Reasoning, 2026. https://arxiv.org/pdf/2602.11201.pdf

[48] Lie to Me: CoT Faithfulness in Open-Weight LLMs, 2026. https://arxiv.org/pdf/2603.22582.pdf

[49] RFEval: Benchmarking Reasoning Faithfulness under Counterfactual Reasoning Intervention, 2026. https://arxiv.org/pdf/2602.17053.pdf

[50] Measuring and curing reasoning rigidity: from decorative chain-of-thought to genuine faithfulness, 2026. https://arxiv.org/pdf/2603.22816.pdf

[51] Benchmarking Small Language Models and Small Reasoning Language Models on System Log Severity Classification, 2026. https://arxiv.org/pdf/2601.07790.pdf

[52] A Comprehensive Study of Chain-of-Thought Faithfulness in Low-Resource Languages, 2026. https://aclanthology.org/2026.loreslm-1.27.pdf

[53] Robotic Control via Embodied Chain-of-Thought Reasoning, 2024. https://arxiv.org/pdf/2407.08693.pdf

[54] Fast ECoT: Efficient Embodied Chain-of-Thought via Thoughts Reuse, 2025. https://arxiv.org/pdf/2506.07639.pdf

[55] Latent Chain-of-Thought World Modeling for End-to-End Driving, 2025. https://arxiv.org/pdf/2512.10226.pdf

[56] OneVL: One-Step Latent Reasoning and Planning with Vision-Language Explanation, 2026. https://arxiv.org/pdf/2604.18486.pdf

[57] CoT-Drive: Efficient Motion Forecasting for Autonomous Driving with LLMs and Chain-of-Thought Prompting, 2025. https://arxiv.org/pdf/2503.07234.pdf

[58] Automated Flood Control Text Generation: A Case Study of the Lixiahe Region, 2026. https://www.mdpi.com/2073-4441/18/6/686/pdf

[59] Faithful-First Reasoning, Planning, and Acting for Multimodal LLMs, 2025. https://arxiv.org/pdf/2511.08409.pdf

[60] RAGLens: Identifying and Mitigating Hallucinations in Retrieval-Augmented Generation via Mechanistic Interpretability, 2025. https://openreview.net/pdf?id=hgBZP67BkP

[61] How Does Unfaithful Reasoning Emerge from Autoregressive Training?, 2026. https://arxiv.org/pdf/2602.01017.pdf

[62] Controllable Reasoning Models Are Private Thinkers, 2025. https://arxiv.org/pdf/2602.24210.pdf

[63] Counterfactual simulation training for chain-of-thought faithfulness, 2026. https://arxiv.org/pdf/2602.20710.pdf

[64] Deliberative Alignment: Reasoning Enables Safer Language Models, 2024. https://arxiv.org/pdf/2412.16339.pdf

[65] Blockchain Ledgers to Record AI Decisions in IoT, 2025. https://www.mdpi.com/2624-831X/6/3/37/pdf

[66] Using Blockchain Ledgers to Record AI Decisions in IoT, 2024. https://pmc.ncbi.nlm.nih.gov/articles/PMC12074401/pdf/

[67] Blockchain-Enabled Transparent Traffic Enforcement, 2024. https://www.frontiersin.org/journals/sustainable-cities/articles/10.3389/frsc.2024.1426036/full

[68] Blockchain-Based Architecture for Traffic Signal Control, 2019. https://arxiv.org/pdf/1906.02628

[69] Hybrid Architecture for Spectrum Access Systems With Permissioned Blockchain, 2026. https://ieeexplore.ieee.org/iel8/6287639/11323511/11369962.pdf

[70] Performance analysis and control of permissioned blockchains, 2023. http://ir.lib.vntu.edu.ua/bitstream/handle/123456789/48975/183633.pdf?sequence=2&isAllowed=y

[71] Performance Analysis of Hyperledger Besu in Private Blockchain, 2025. https://www.mdpi.com/1999-5903/17/1/31

[72] Scalability of blockchain technology in Peer-to-Peer renewable energy trading, 2024. https://run.unl.pt/bitstream/10362/175684/1/TGI3509.pdf

[73] Performance and Scalability Analysis of Ethereum and Hyperledger Fabric, 2023. https://ieeexplore.ieee.org/iel7/6287639/10005208/10171380.pdf

[74] Besu vs. Quorum: Comparative Analysis in Simulated Energy Communities, 2024. https://dlt2024.di.unito.it/wp-content/uploads/2024/05/DLT2024_paper_4.pdf

[75] Comparative analysis of permissioned blockchains for industrial applications, 2022. https://iris.polito.it/bitstream/11583/2973439/4/1-s2.0-S2096720922000549-main.pdf

[76] Virtual Blockchain Using Quorum Tessera, 2025. https://www.tandfonline.com/doi/pdf/10.1080/17517575.2025.2492723

[77] AITH: A Post-Quantum Continuous Delegation Protocol for Human-AI Trust, 2026. https://arxiv.org/pdf/2604.07695.pdf

[78] SecChain: A Secure Stateless Sharded Blockchain, 2026. https://www.computer.org/csdl/journal/tq/2026/02/11231341/2bsdVosw1TG

[79] ML and Blockchain for Secure V2X: A Survey, 2025. https://www.mdpi.com/1424-8220/25/15/4793/pdf

[80] Blockchain and Smart Contracts for Cooperative Connected Automated Mobility, 2024. https://www.mdpi.com/1424-8220/24/19/6273/pdf

[81] Blockchain Task Offloading for Smart Transport, 2025. https://www.mdpi.com/1424-8220/25/17/5555/pdf

[82] SALT-V: Lightweight Authentication for 5G V2X, 2025. https://arxiv.org/pdf/2511.11028

[83] BeACONS: Blockchain Authentication and Communications for IoV, 2024. https://arxiv.org/pdf/2405.08651

[84] Ofqual, Awarding GCSE, AS, A level, advanced extension awards and extended project qualifications in summer 2020 (interim report and Direction), 2020. [Government policy] https://www.gov.uk/government/publications/awarding-gcse-as-a-level-advanced-extension-awards-and-extended-project-qualifications-in-summer-2020-interim-report

[85] NJCM et al. v. The Netherlands (Systeem Risico Indicatie / SyRI judgment), Court of The Hague, ECLI:NL:RBDHA:2020:865, 5 February 2020, 2020. [Judgment] https://uitspraken.rechtspraak.nl/details?id=ECLI:NL:RBDHA:2020:865

[86] Dastin, J., 'Amazon scraps secret AI recruiting tool that showed bias against women', Reuters, 10 October 2018, 2018. [Journalism] https://www.reuters.com/article/world/insight-amazon-scraps-secret-ai-recruiting-tool-that-showed-bias-against-women-idUSKCN1MK0AG/

[87] Chicago Office of Inspector General, Advisory Concerning the Chicago Police Department's Predictive Risk Models (Strategic Subject List), 2020. [Operator report] https://igchicago.org/wp-content/uploads/2020/01/OIG-Advisory-Concerning-CPDs-Predictive-Risk-Models-.pdf

[88] New York City Automated Decision Systems Task Force, Report (Local Law 49 of 2018), 2019. [Government policy] https://www.nyc.gov/assets/adstaskforce/downloads/pdf/ADS-Report-11192019.pdf

[89] Equality Act 2010, Section 149: Public Sector Equality Duty (UK), 2010. [Statute] https://www.legislation.gov.uk/ukpga/2010/15/section/149

[90] Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13 June 2024 laying down harmonised rules on artificial intelligence (Artificial Intelligence Act), 2024. [Statute] https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689

[91] UK Algorithmic Transparency Recording Standard (ATRS), Cabinet Office and Central Digital and Data Office, 2023. [Government policy] https://www.gov.uk/government/collections/algorithmic-transparency-recording-standard-hub

[92] R (Bridges) v Chief Constable of South Wales Police [2020] EWCA Civ 1058, 2020. [Judgment] https://www.bailii.org/ew/cases/EWCA/Civ/2020/1058.html

[93] Schufa Holding AG (Case C-634/21), Court of Justice of the European Union, judgment of 7 December 2023, ECLI:EU:C:2023:957, 2023. [Judgment] https://curia.europa.eu/juris/document/document.jsf?docid=280426&doclang=EN

[94] Constitution of India (Articles 14, 15, 16, 21 — Part III Fundamental Rights), 1950. [Statute] https://www.indiacode.nic.in/bitstream/123456789/19632/1/the_constitution_of_india.pdf

[95] Justice K.S. Puttaswamy v. Union of India (Right to Privacy), (2017) 10 SCC 1, 2017. [Judgment] https://main.sci.gov.in/supremecourt/2012/35071/35071_2012_Judgement_24-Aug-2017.pdf

[96] Justice K.S. Puttaswamy v. Union of India (Aadhaar), (2019) 1 SCC 1, 2018. [Judgment] https://api.sci.gov.in/supremecourt/2012/35071/35071_2012_Judgement_26-Sep-2018.pdf

[97] The Digital Personal Data Protection Act, 2023 (No. 22 of 2023) — Gazette of India, 2023. [Statute] https://egazette.gov.in/WriteReadData/2023/248045.pdf

[98] DPDP Rules 2025 — MeitY Gazette G.S.R. 843(E)/844(E)/845(E)/846(E), 13 Nov 2025, 2025. [Statute] https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf

[99] MeitY notifies final Digital Personal Data Protection Rules 2025 — Bar and Bench, 2025. [Legal commentary] https://www.barandbench.com/view-point/meity-notifies-final-digital-personal-data-protection-rules-2025

[100] Responsible AI #AIForAll — Approach Document Part 1: Principles, 2021. [Government policy] https://www.niti.gov.in/sites/default/files/2021-02/Responsible-AI-22022021.pdf

[101] Responsible AI #AIForAll — Part 2: Operationalising Principles, 2021. [Government policy] https://www.niti.gov.in/sites/default/files/2021-08/Part2-Responsible-AI-12082021.pdf

[102] India to Regulate AI Under DPDPA, IP Laws, No Standalone AI Law — MediaNama, 2025. [Journalism] https://www.medianama.com/2025/12/223-india-ai-law-digital-india-act-stalled/

[103] Re-imagining Algorithmic Fairness in India and Beyond (Sambasivan et al.), 2021. [Peer-reviewed] https://arxiv.org/pdf/2101.09995

[104] Aadhaar and Food Security in Jharkhand: Pain Without Gain? (Drèze, Khalid, Khera, Somanchi), 2017. [Peer-reviewed] https://www.epw.in/journal/2017/50/special-articles/aadhaar-and-food-security-jharkhand.html

[105] Impact of Aadhaar on Welfare Programmes (Khera), 2017. [Peer-reviewed] https://www.epw.in/journal/2017/50/special-articles/impact-aadhaar-welfare-programmes.html

[106] Project Panoptic — facial recognition tracker (Internet Freedom Foundation), 2020. [Operator report] https://panoptic.in/

[107] Illegal use of Facial Recognition for Voter Verification in Telangana (IFF / Project Panoptic), 2020. [Operator report] https://internetfreedom.in/the-telangana-ec/

[108] The Use of Facial Recognition Technology for Policing in Delhi (Vipra, Vidhi), 2021. [Working paper] https://vidhilegalpolicy.in/research/the-use-of-facial-recognition-technology-for-policing-in-delhi/


<!-- chapter word count (sections only): approx 12200 after thesis cutover; regenerate _stitch_chapter.py to recompute -->

<!-- NOTE: refs [109]-[115] (transport-equity / pedestrian-harm) removed with the dropped equity axis; [1]-[108] numbering unchanged. -->
<!-- NOTE: registry.json (06-literary-survey/, outside this cluster) still contains the old-thesis tags and was NOT modified. -->

