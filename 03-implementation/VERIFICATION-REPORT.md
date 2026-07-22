# Verification Report — Spec Corpus Fact-Check

Generated 2026-06-20. Method: 201 Sonnet sub-agents, ~4.77M tokens, web-verified citations, independently recomputed math, read code against claims, cross-checked all three canonical docs and the eight legacy spike docs. Adversarial refute pass on everything marked "verified."

Scope checked: PROJECT-PROPOSAL.md, METHODOLOGY-AND-IMPLEMENTATION-DESIGN.md, FORMAL-SPECIFICATION.md, the corridor build code, the existing controller code, and the eight Jun 4-5 spike docs (consistency only).

Coverage gap: the jargon glossary and the adversarial refute pass on ~24 lower-risk items did not run — the session hit its token limit (resets 21:10 London). Those re-run after reset. Everything below is from passes that completed.

---

## CORRECTIONS APPLIED (2026-06-20, after this report)

All §A-§G items with a single right answer were corrected in place. The five §H judgment calls were decided by the author and applied:
1. **Webster** — recomputed with start-up lost time (l₁=2 s/phase): L_lost=14, C_opt≈78, max_green=64, max_skip=8, T_starve≤93 (superseded 2026-07-22: now pinned max_skip=3, T_starve≤43 per MASTER-SPEC §0/§6.8) (FORMAL-SPEC §1.1, §2).
2. **Xiao2026** — dropped; the residual-detection-floor non-claim is now argued from first principles (band/CUSUM-reference) in FORMAL-SPEC §5, PROPOSAL §3/§6, METHODOLOGY §4.3.
3. **cooperative_naive** — reframed as "representative of the trust-everything class CoLLMLight exemplifies" across all three docs.
4. **AETT** — standardised on the horizon-penalised mean (METHODOLOGY §5.2 now matches FORMAL-SPEC §6).
5. **Legacy spike docs** — the eight Jun 4-5 docs were deleted from the working tree (git retains them); canonical docs no longer reference them.

Also applied: the three broken internal cross-refs repointed; Derhab2020 flag removed (it is real and correctly described); n_eff corrected to 72; min_green relabelled as a policy override of the 7 s formula floor; CUSUM combined false-alarm interval corrected to ~30 min; the ev_horizon formula reconciled to one definition; competitor facts fixed (SafeLight rule-based override, LA-Light multi-junction, REG-TSC/VLMLight emergency handling + simulator + training, MaxPressure simplified-form note); over-attributed citations softened with correct primary sources (Efron for BCa, Page-1961/Lucas for tabular CUSUM, MUTCD subsection, etc.); the one-sided corroboration window fixed to two-sided; shield_margin guessed default removed; MUST/SHOULD and file-placement contradictions resolved.

The original findings below are preserved as the audit trail.

---

## Headline finding

**No fabricated external literature.** Every academic paper cited is real and correctly attributed on author/year/venue, with minor exceptions noted below. That is the important result: the corpus is not built on invented sources.

**The real problem is over-attribution**, not fabrication: real papers cited for specific numbers, formulas, or scope claims they do not actually contain. This is the exact failure mode an examiner probes. Plus a handful of genuine arithmetic/definition errors, several internal contradictions between the canonical docs, and the legacy spike docs openly contradicting the locked direction.

### Confidence scorecard

| Dimension | Checked | Clean | Needs correction | Notes |
|---|---|---|---|---|
| External citations exist | 58 | 58 | 0 | All real papers |
| Citation attribution correct | 58 | ~50 | ~8 | Wrong year/subsection/venue on a few |
| Citation supports the claim | 58 | 33 | 25 | Over-attribution is the pattern |
| Math derivations | 39 | 16 exact, 19 approx | 4 | 2 distinct real errors |
| Competitor specs | 20 | 7 | 13 | Scope/emergency/training mischaracterised |
| Code vs claims | 9 | 6 | 2 partial, 1 unverifiable | Diagnostics accurate |
| Cross-doc consistency | — | — | 21 | 8 high severity |

---

## A. The three "hallucinations" are broken internal cross-references, not fake papers

All three are pointers to internal doc sections that were renamed or deleted, masquerading as citations. No external fabrication.

1. **`SPECIFICATION §3`** (METHODOLOGY line ~553) — SPECIFICATION.md was superseded/removed. The surviving FORMAL-SPECIFICATION.md §3 is about detection, not the no-training/8GB constraint cited. The constraint is real and lives in PROJECT-PROPOSAL §3.
2. **`SPECIFICATION §12`** (METHODOLOGY line ~599) — FORMAL-SPECIFICATION.md only has §0–§9; there is no §12. The "honesty boundary" concept is real and lives in PROJECT-PROPOSAL §11.
3. **`Integration TODO #3`** (METHODOLOGY lines ~257) — cited as if a source; it is an internal TODO. The underlying implementation (reconcile_silent_neighbours, sensor_outage trigger) does exist in code.

Also wrong-section (suspicious, not fake): `SPECIFICATION §9` should be §4/§8; `SPECIFICATION §10` serialisation fact is right but the 18–20 throughput number is from DE-RISK/slm_bench, not §10; `DERISK Integration TODO #4` cited for its own resolution which lives in METHODOLOGY.

**Fix:** repoint or relabel these as internal design notes, not citations. Low risk, mechanical.

## B. A false alarm I previously raised — Derhab2020 is real

My FORMAL-SPECIFICATION §0 said Derhab2020 "could not be externally verified and appears misattributed." **That was wrong.** The deep pass (conf 0.95) confirms: Derhab et al. 2020, "...", MDPI *Sensors* 20(21):6106, DOI 10.3390/s20216106 — real, and my description (relaxed flow-conservation as a one-class detector for selective-routing attacks in WSNs, two-hop monitoring to avoid the upstream-node effect) is accurate. The only honest caveat is the domain stretch (WSN routing → vehicle flow), which the PROJECT-PROPOSAL table already states correctly as the reason we don't adopt it directly.

**Fix:** remove the incorrect "unverifiable/misattributed" flag in FORMAL-SPEC §0. Keep LWR (Lighthill-Whitham 1955 / Richards 1956 — both verified, conf 0.97) as the primary physics grounding; cite Derhab2020 honestly as the WSN precedent we port from.

## C. Genuine errors to correct

### Math (2 distinct real errors + 2 propagation issues)

- **EV effective sample size** (FORMAL-SPEC §1.4 vs §6): three different values for the same inputs — 60, 67, and implied 72. The Kish formula n_eff = nJ/(1+(J−1)ρ) with n=30, J=6, ρ=0.3 gives **exactly 72**, not 67 or 60. Also the minimum J to clear n_eff≥60 is **J=4** (63.2), not J=6. *Fix: state n_eff=72 at J=6; note J=4 already clears 60, J=6 is headroom. Reconcile both sections.*
- **min_green** (FORMAL-SPEC §1.1 vs §2): presented as if the formula `max(7, yellow+r_ac)` yields 10. It yields **7**. The value 10 is a policy override ("reduce SLM call rate"), not a formula result. *Fix: relabel 10 as an [E] engineering override on top of the 7 s floor, not a derivation.*
- **CUSUM "~1 h between false alarms"** (FORMAL-SPEC §3): the combined two-sided ARL₀ ≈ 60 windows × 30 s = **30 min**, not 1 h. The 1 h figure is the one-sided per-arm number (119 × 30 s). *Fix: state combined ≈ 30 min; reserve ~1 h for the per-arm figure if used.* Also the label "limit form" for the ARL₀ substitution is wrong — it is the "in-control form" (Δ⁺ = −0.5, not 0).
- **CUSUM ARL₁ = 6 windows**: `ceil(h/(δ−k))=6` is the zero-noise deterministic minimum, not the Siegmund expected detection time (which is ~6.36 → 7). Right ballpark, mislabelled as Siegmund. *Fix: relabel as a conservative lower bound, or quote Siegmund's 6.4.*

### Webster lost-time — FLAG, do not silently fix (it cascades)

The refute pass (conf 0.72) found `L_lost = n_φ·(yellow + r_ac)` **omits start-up lost time** (~2 s/phase, the dominant term in Webster's actual definition). Correcting it changes L_lost, which changes C_opt (60 s), which changes max_green (50), max_skip (6), and T_starve (73). This is not mechanical — it needs your calibration intent. **Decision needed** (see §H).

### Competitor specs (13 overstated — the ones that will be challenged)

- **SafeLight** — the doc's implied contrast "we have a deterministic shield, they're purely learned" is **false**. SafeLight has a rule-based safety override (from the Federal signal-timing manual) that overrides unsafe RL actions — structurally our shield. Also it does not use the RESCO benchmark (if the doc says so). *Differentiate instead on: training required + no adversarial/spoofed-input defence.* Material — it removes a differentiation claim.
- **LA-Light** — described as "single junction"; it tests **18 Shanghai intersections** (multi-junction), on SUMO. *Fix the scope claim.*
- **REG-TSC** — implied to lack emergency handling; emergency-vehicle prioritisation is a **headline result** (83% wait reduction). Uses **SUMO** not CityFlow; model is **fine-tuned (LoRA) on-prem**, not frozen cloud. *Fix all three; keep the accurate "no compromised-input robustness" contrast.*
- **VLMLight** — handles emergencies (65% wait reduction); its RL branch **is trained** (so "frozen/no-training analogue" is half-wrong); uses **SUMO**; "32B+72B" should be Qwen2.5-VL-32B + Qwen2.5-**72B (text-only)**; AgentCheck **gates the LLM** (rejects LLM actions, falls back to RL), it does not override the classical path.
- **MaxPressure (Varaiya 2013)** — `P_i = Σ(n_in − n_out)` drops the **saturation-flow rates and turning ratios** that Varaiya's real rule (and its throughput-optimality proof) depend on. *Fix: label our form as "the simplified halting-count pressure we implement," and note Varaiya's full rule weights by saturation flow and turning ratios.*
- **CoLLMLight** — training is **SFT** (the repo also has an optional PPO refinement stage, so "PPO" isn't pure fabrication, but the paper narrative is SFT). More important: CoLLMLight has **no inter-agent message passing** — agents read shared CityFlow state directly. So "trust-everything peer messaging" is architecturally inapplicable, and "cooperative_naive is a faithful reimplementation of CoLLMLight" **will not survive review**. *Reframe (see §H).* The "exceeds edge budget" and "benign-case tie" claims must be stated as our own design target / our own experimental result, not as properties of CoLLMLight.

### Xiao2026 — real paper, wrong domain — FLAG

arXiv:2602.10162 (Xiao & Weng, ASU, Feb 2026) is real but is about **AC power-grid state estimation**, not traffic. It has no cryptographic keys, no collusion model, and never claims "recall=0 by design." Our use of it to assert a formal ≥2-key-collusion recall=0 bound for traffic coordination is an over-extension. **Decision needed** (see §H).

## D. Over-attribution — real papers cited for things they don't state

These are all real, correctly-attributed papers used to ground a specific number/formula the paper does not contain. Fix by softening to "consistent with / motivated by" and adding the correct primary source.

- **Cliff 1993** supports Cliff's delta but **not BCa CIs** — add Efron 1987 / DiCiccio-Efron 1996 for the CI method.
- **Page 1954** proposed CUSUM in general but **not the tabular recursion** — add Page 1961 / Lucas 1982 / Hawkins-Olwell 1998; k=δ/2 traces to Bagshaw-Johnson 1974 / Moustakides, not Page.
- **Efron 1987** introduced BCa but **does not specify n_boot=10000** (that is a modern convention; Efron-Tibshirani 1993 suggested 1000). Page range 171–185 vs 171–200 is contested.
- **Phipson & Smyth 2010** — the (B+1)/(m+1) correction is for **Monte-Carlo (random) permutations, not exhaustive "exact" tests**; our doc inverts their terminology. n_perm=10000 is not their recommendation.
- **Roberts 1959** supports EWMA but **not the λ=2/(S+1) span formula** (later convention).
- **Morgan & Little 1964 / Little 1966** are MILP green-wave optimisation; the closed-form `offset = (ℓ/v) mod C` is a **modern simplification**, not their stated formula.
- **MUTCD 4D.27** has the "un-shortenable yellow" rule, but the **3–6 s range is in 4D.26 / 4F.17** — fix the subsection.
- **NTCIP 1211** is a messaging standard; it **does not contain** the kinematic `ev_horizon` formula — cite it only for EVP messaging context.
- **HCM 7.1** uses density, not detector occupancy; the 0.11–0.25 / 0.70 occupancy figures belong to **incident-detection literature** (California algorithm family, FHWA Traffic Detector Handbook), not HCM.
- **California AID Algorithm #8** — `incident_persist=3` is **unattested** in the source (it specifies 5-min shockwave suppression). Relabel as an [E] engineering choice.
- **Greenshields 1935** supports ρ_crit=ρ_jam/2; "TRB EC149" is a separate **2008** compendium — split the two.
- **FHWA Traffic Detector Handbook** — the 5% count-error anchor for c_r=0.15 is in **associated TTI evaluation reports**, not the handbook itself.
- **Chen et al. NDSS 2018** is a concrete CV congestion-attack exemplar, **not a formal threat-model taxonomy** — don't pair it with Dolev-Yao as a taxonomy source.
- **proofmember23** — the **"3–5×" figure is not in the paper**; it uses SHA-256/Merkle/BBS, **not Ed25519**. Reframe as our own decision motivated by their finding that VC verification is costly on constrained devices.

## E. Canon-internal contradictions (must fix — these are between the three load-bearing docs)

1. **ev_horizon formula** (HIGH): METHODOLOGY says `v_free·2·decision_interval` (≈278 m); FORMAL-SPEC says `v_free·(min_green+yellow+processing)` (≈195 m). 43% apart. *Pick the principled spec formula; make METHODOLOGY match.*
2. **AETT definition** (HIGH): METHODOLOGY = plain mean of EV trip duration; FORMAL-SPEC = horizon-penalised mean over departed EVs (stranded EV penalised). Different quantities when an EV fails to clear. *Decision needed (the penalised form is more rigorous).*
3. **Derhab2020** (HIGH): PROPOSAL cites it as solid prior art; FORMAL-SPEC flags it unverifiable. Resolved by §B above (remove the flag).
4. **shield_margin** (MED): METHODOLOGY gives "default e.g. 8"; FORMAL-SPEC marks it [K] no-guessed-value-ships. *Remove the "8" default.*
5. **conservation_anomaly in the shield** (MED): the §1.3 V5 acceptance list omits conservation_anomaly though the priority list includes it. *Clarify shield behaviour for that trigger.*
6. **NaiveCooperativeController file** (MED): §4.5 says run_emergency.py; §8 says run_coordinated.py. *Pick one.*
7. **fused spoof experiment** (MED): listed as the MUST headline in §7 but a SHOULD in §9. *Align priority.*
8. **fair-victim depends on causal coordination** (MED): the benign "tie" claim assumes coordination is causal, but the as-built coord term is inert (Bug B1). *The B1 fix is a prerequisite for the fair-victim experiment — state it as such.*

## F. Legacy spike docs contradict canon (your earlier concern about future-agent hallucination)

The eight Jun 4-5 docs were NOT removed in the consolidation and now openly contradict the locked direction:

- The **permissioned-ledger spike docs / INTEGRATION-PLAYBOOK** frame a permissioned distributed ledger as the **production path** ("swap Registry → distributed-ledger registry", "production consensus validated"). Canon demotes that path to a cited-prior-art anchor option; the accountability mechanism is credited to Certificate-Transparency-style anchoring (RFC 6962 and successors), not claimed novel. (HIGH)
- **COORDINATION-ALGORITHM-SPEC** frames the SLM as a **co-equal proposer on every tick** and Channel-B as an **always-on override**. Canon: SLM is a guarded exception handler; Channel-B is advisory in NORMAL, override scoped to TRIGGERED. (HIGH ×2)
- **COORDINATION-ALGORITHM-SPEC §5** pre-registers a **5–15% travel-time win** as the primary hypothesis. Canon: performance is a secondary honestly-reported axis. (MED)
- **THREAT-MODEL-ANALYSIS** describes the conservation check as **stateless, no cross-tick accumulation**. Canon ships the CUSUM-augmented detector. (MED)
- The **ledger / MQTT spike docs** call the ledger the **"trust path."** Canon non-claim: the ledger records garbage faithfully, it does not create trust. (LOW)

**Decision needed:** delete from the working tree (kept in git) or add a "SUPERSEDED — see canon, may contradict" banner to each. (see §H)

## G. Latent bugs to fix when building (not doc errors, but caught here)

- **Corroboration window is one-sided** (FORMAL-SPEC §2.1): `(now − route_traveltime − tol) ≤ t_sighted ≤ now` widens only the lower bound. A fast upstream clock (t_sighted > now) fails the upper bound and corroboration is wrongly denied. *Add `≤ now + tol`.*
- **Counting-window annotation** (FORMAL-SPEC): "L = 14–29 m for demo edges" should be **14–29 s** (traversal times). Conclusion W=30 s is correct; the parenthetical units are wrong.
- **Abnormal-demand FP rate**: the 0.135% (3σ) figure assumes Gaussian counts; real halting counts are Poisson/negative-binomial, so the true FP rate is 2–4× higher, and persist=2 does not square under autocorrelation. *Add the caveat; the detector is not yet built.*

## H. Decisions I need from you

Everything in §A, §C-math (except Webster), §C-competitors (factual), §D, and §E.1/3/4/5/6/7 I can correct now — they have a single unambiguous right answer. These need your call first:

1. **Webster lost-time**: add start-up lost time (~2 s/phase) and recompute C_opt → max_green → max_skip → T_starve? Or keep current numbers and add a footnote that we use a clearance-only lost-time approximation? (Affects 4 derived constants.)
2. **Xiao2026**: soften to "by analogy with the power-grid FDI detection-limit literature (Xiao & Weng 2026), a physics-consistent injection has a residual-detection floor; we adopt this qualitatively as a stated non-claim, not a transferred formal result"? Or drop it and state the non-claim from first principles?
3. **cooperative_naive framing**: reframe from "faithful CoLLMLight reimplementation" to "a cooperative controller representative of the trust-everything class CoLLMLight exemplifies; we add a signed message bus as the attack surface that class implicitly trusts"? (Recommended — the faithful claim won't survive.)
4. **AETT**: standardise on the horizon-penalised mean (handles stranded EVs honestly)? (Recommended.)
5. **Legacy spike docs**: delete from working tree (git keeps them) or banner them as superseded? (You earlier wanted superseded docs gone to stop future-agent hallucination — that argues for delete.)

## I. Deferred (session token limit, resets 21:10)

- Jargon glossary (every domain term → plain-but-precise explanation) — re-run after reset.
- Adversarial refute pass on ~24 lower-risk citations — re-run after reset.
- Doc readability rewrite (natural reading language, citations kept) — after the §H decisions, so I'm not polishing prose around items still in flux.
