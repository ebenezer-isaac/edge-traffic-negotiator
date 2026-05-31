# Edge Negotiator dissertation — scope lock-in

**Status:** LOCKED as of 2026-05-31. This lock-in **supersedes** the prior equity-audit lock-in (locked 2026-04-26), which is recoverable at **git commit `effd4d5`**. The authoritative source for the build is `03-implementation/PROJECT-DECISION-BRIEF.md`; where this file and that brief diverge, the brief wins. **Supervisor sign-off on this reframe is PENDING.** Do not propose alternative topics, models, hardware, corridors, or ledger platforms without re-opening this file. If a future agent disagrees with anything here, raise it explicitly with the user before acting on it.

> **Pivot notice (read first):** On 2026-05-31 the dissertation pivoted away from the Quarterly Equity Audit framing toward an **integrity / authentication** framing. Do **not** reintroduce equity audits, Gini/Rawlsian/DIR/pedestrian-parity metrics, the counterfactual demographic re-run, CoT-faithfulness as a *contribution*, incentive-compatibility as a real property, Qwen3-4B as co-primary, Z3 SMT as the core safety mechanism, Trillian Tessera as the headline comparator, or CoLLMLight/CityFlow as the build base. These are dropped or repurposed (see §9).

---

## 1. What this dissertation is

UCL MSc Systems Engineering for IoT (SEIOT) dissertation.

**Title (working):** *The Edge Negotiator: Verified-Source Cross-Junction Coordination for SLM-Driven Traffic Signal Control.*

**One-line system:** A corridor of small-language-model agents (Phi-4-mini 3.8B via Microsoft Foundry Local), one per signalised junction, that coordinate signal timing by sharing predicted traffic state with neighbours in Eclipse SUMO on a real Lambeth corridor — where every agent has a cryptographic identity, inter-junction messages are signed and verified against a permissioned-ledger registry of approved agents, a vehicle-conservation plausibility check flags physically inconsistent (spoofed or faulty) reports, a tamper-evident ledger records all decisions, and a deterministic MaxPressure shield validates or overrides every SLM decision (and runs alone at quiet, event-gated junctions).

**The one defensible claim (the thesis stakes itself on this):**
> Authenticated, plausibility-checked cross-junction coordination for SLM-driven traffic control — verifiable agent identity (signatures + on-chain registry) and a vehicle-conservation consistency check give spoofing/fault detection and a non-repudiable audit trail, **with no claim of game-theoretic incentive-compatibility.**

## 2. Supervisors

- **Dr Akin Delibasi (UCL)** — distributed systems. Reviews: SUMO experimental design, MaxPressure shield correctness, coordination logic, and statistical methodology.
- **Lee Stott (Microsoft)** — Foundry Local, Phi-4. Reviews: Phi-4-mini access via Foundry Local, cryptographic identity / Besu integration, and public-sector commercial fit. Lee provided four critique pillars (S1–S4) on the STSD coursework; their honest mapping to the *reframed* project is in §7.

## 3. Locked contributions — what we are doing

The contribution is an **integrity layer fused onto an SLM coordination platform**, demonstrated against a concrete threat model. In priority order:

1. **The integrity layer (PRIMARY contribution).** Two fused mechanisms:
   - **(a) Authentication** — each agent has an Ed25519/ECDSA identity; inter-junction messages are signed and verified against an on-chain (Hyperledger Besu) allowlist of approved agents, with `revoke()` for a compromised agent. Catches impersonation and replay.
   - **(b) Conservation-check** — a vehicle-conservation plausibility contract flags reports physically inconsistent with neighbours (did A's claimed outflow match B's observed inflow within the travel-time window?). Catches insider false-data-injection and faults.
2. **Coordination as the platform.** Phi-4-mini agents share predicted traffic state with neighbours to coordinate phase timing across the corridor; the MaxPressure shield disposes. "It coordinates" is the substrate the integrity layer secures, not the headline novelty.
3. **Three demonstrated threats.**
   - **(1) Spoofed traffic-state report — PRIMARY threat.**
   - **(2) Faulty sensor — SECONDARY threat.**
   - **(3) Sybil count-inflation — OPTIONAL, only if time allows.**

**Milestone 2 (end Wk 4)** = the "it coordinates" demo; everything after is the integrity contribution + its evaluation.

## 4. Locked architectural substrate — do not vary

| Layer | Locked choice | Note |
|---|---|---|
| Coordination base | **sumo-rl** (MIT, arbitrary nets) | Reimplement the neighbour-message algorithm; do **not** port CoLLMLight (CityFlow-welded; algorithm reference only) |
| SLM | **Phi-4-mini (3.8B) via Microsoft Foundry Local**, INT4, inference-only | Qwen3-4B is an *optional late ablation only* (see §9), not co-primary |
| SLM output | **Terse action only (`{"phase": N}`), no chain-of-thought** | Justified by CoT-faithfulness literature + latency budget (see §5) |
| SLM role | **Hybrid: SLM proposes, MaxPressure shield disposes; event-gated (skip quiet junctions)** | Shield runs alone at quiet junctions |
| Deterministic shield | **MaxPressure** (Varaiya formulation) — validates/overrides every SLM decision | This is the **safety layer** (replaces the old Z3 SMT mechanism) |
| Identity | **Ed25519/ECDSA signatures + small on-chain allowlist + `revoke()`** | DID/VC is future work only |
| Ledger | **Hyperledger Besu QBFT (Docker), web3.py** — registry + audit log + conservation-check contract | Async only, never in the control loop |
| Plausibility contract | **Vehicle-conservation reconciliation** (outflow vs neighbour inflow within travel-time window) | Flags inconsistent reports |
| Fast path | **Signed messages over MQTT** (signed-MQTT bus) | Real-time; verify signature vs registry |
| Ledger comparison | **"Besu permissioned ledger vs plain signed append-only log"** | Replaces the old Trillian Tessera headline comparator |
| Corridor | **Real Lambeth corridor (Brixton → Elephant & Castle), ~10–13 junctions; ~6 SLM-controlled** (headroom to 8–10), rest on MaxPressure | DfT AADF anchors + assumed peak profile + SUMO `routeSampler`/calibrators (cite method) |
| Simulator | **Eclipse SUMO, Python TraCI** | Pause sim during inference |

**Hardware:** developer laptop with **RTX 4050 (8GB VRAM)**. Phi-4-mini runs INT4, **inference-only, no training on the laptop**. No edge hardware (Jetson, Hailo) is in scope.

**Baselines / metrics (for grounding the eval):** Fixed-time (Webster), MaxPressure, uncoordinated-SLM vs coordinated-SLM (optional CoLight). Traffic metrics: average travel time, average queue, throughput. Detection metrics: precision/recall/F1 at a fixed false-alarm rate, detection latency in control cycles. Integrity overhead: signing latency, ledger commit latency, Besu-vs-plain-signed-log comparison. Stats: BCa bootstrap, Holm–Bonferroni (existing plan reused).

## 5. Design justification — why terse output (no CoT)

The SLM emits a single terse phase decision with **no chain-of-thought, by design**. This is compelled by the faithfulness literature in Lit-Review §2.6: explicit CoT traces are **post-hoc rationalisations, not faithful causal records** (Turpin et al. 2023; Lanham et al. 2023; consistent across the sub-7B corpus). Emitting reasoning would add latency and token cost while providing **no trustworthy interpretability benefit**. Accountability is provided **structurally** — by the signed, tamper-evident audit log — not by the model's self-narration. This **repurposes the already-written CoT lit-review chapter as architectural justification**, *not* as a separate contribution or experiment.

## 6. Honesty clauses — what we CAN and CANNOT claim

**CAN claim:**
- Message authenticity from a currently-approved registered member.
- Tamper-evident on-chain registration/revocation **+ a non-repudiable audit trail** (provenance, non-repudiation, identity registry).
- Detection of *inconsistent* (uncoordinated-spoof or faulty) neighbour reports.
- "Small off-the-shelf SLMs can coordinate a corridor" vs baselines.

**CANNOT claim:**
- That the blockchain "creates trust" or "prevents lying." **The ledger provides provenance / non-repudiation + an identity registry, NOT truth** — it faithfully records garbage-in.
- **Incentive-compatibility** — type-incoherent for frozen LLMs. The Tian2025 *Scientific Reports* paper is **motivation only**.
- Which of two disagreeing junctions is the wrong one.
- Defence against a **coordinated, conservation-respecting attacker** — the `Xiao2026` limit: a conservation-respecting attack **evades the consistency check**. This is an acknowledged limit and is precisely what motivates the auth layer as the complement. We cite this limit ourselves.

## 7. Stott's four critiques — honest mapping to the *reframed* project

> **The pivot moves away from the old S2 (equity-audit) focus toward integrity / authentication.** This is exactly why **supervisor sign-off is a PENDING open item**: the equity answer no longer stands, and we do not pretend it does.

| Pillar | Old answer (DROPPED) | Honest new mapping |
|---|---|---|
| **S1** — CoT exposure risks in safety-critical control | Discussion-chapter faithfulness probe | **Answered by design:** terse, no-CoT output; accountability via signed audit log (§5). Strengthened, not weakened. |
| **S2** — Operationalising fairness / equity audits | Equity-audit primary + counterfactual re-run | **No longer answered.** The pivot deliberately drops equity audits. **This is the open item requiring supervisor sign-off** — we do not claim the old equity answer still holds. |
| **S3** — Evidential basis for cited production deployments | Hedged prompt5 framings | **Still answered.** Cited-claim hygiene preserved — see §8 (Traffic-R1 hedge in particular). |
| **S4** — Performance / governance trade-offs of the blockchain audit layer | Besu QBFT + Tessera side-by-side | **Re-answered:** Besu kept async (registry + audit + conservation contract, never in the control loop); comparison is now **"Besu permissioned ledger vs plain signed append-only log."** |

## 8. Cited-claim hygiene — Traffic-R1 (PRESERVED)

Wherever **Traffic-R1 (Zou et al. 2025)** is cited, the hedge still applies and is mandatory:
- Frame as an example of **emerging** LLM-TSC research, **not** as evidence of verified production deployment.
- Note the **PCITECH vendor-academic affiliation**.
- **Do not** cite the "55,000 daily drivers" figure as established fact.

## 9. The 90-day Study Away from India constraint (PRESERVED)

The student will spend up to 90 days of dissertation work remotely from India under UCL Academic Manual §3.5.2.

- **Highest-risk compliance issue:** Graduate Route eligibility (Immigration Rules Appendix Graduate GR 6.1). A 90-day absence on a 12-month MSc may disqualify Graduate Route unless treated as a permitted study-abroad programme. **Verify with UCL Student Immigration Compliance Team (immigration.compliance@ucl.ac.uk) before any travel commitment.**
- **Why the reframed topic still fits this constraint:** the entire empirical build is **SUMO-on-a-laptop**. The new integrity/coordination build is **laptop-only** (RTX 4050, inference-only, Docker for Besu) and remains fully London-resource-independent — it carries the same Study-Away fit as the superseded scope.

## 10. Out of scope — explicitly not doing

Do not revisit without re-opening this file:

- **Incentive-compatibility as a real property** (type-incoherent for frozen LLMs; Tian2025 is motivation only).
- **The Quarterly Equity Audit Protocol** and all equity metrics (Gini, Rawlsian max-min, DIR, pedestrian parity) and the **counterfactual demographic re-run**.
- **CoT-faithfulness as a contribution** (repurposed as design justification only — §5).
- **CityFlow** and porting **CoLLMLight** code (algorithm reference only; build on sumo-rl).
- **Training models on the laptop** (Phi-4-mini is inference-only, INT4).
- **Edge hardware** (Jetson, Hailo, NPU/Copilot+).
- **Z3 SMT** as the core safety mechanism (MaxPressure shield is the safety layer).
- **Trillian Tessera** as the headline ledger comparator (comparison is now Besu vs plain signed log).
- **Qwen3-4B as co-primary** (optional late model-agnostic ablation only, if a clean 1–2 week buffer exists).

## 11. Re-opening conditions

Reopen this file (and treat its contents as up-for-revision) if and only if:

- A supervisor explicitly asks for a topic change in writing **(note: supervisor sign-off on this very reframe is currently pending — resolving it may revise §7/§3)**.
- A material defect is discovered in any locked architectural choice (e.g., Foundry Local cannot serve Phi-4-mini at all, or Besu cannot meet the async audit budget).
- The coordination + integrity pipeline fails to produce results within a reasonable window of starting implementation (then reassess scope).
- The student withdraws from Study Away to India.

Anything else is scope creep. Honour the lock-in.
