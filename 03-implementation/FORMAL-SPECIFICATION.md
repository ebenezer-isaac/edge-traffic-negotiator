# The Edge Negotiator: Formal Specification (parameters, algorithms, metrics, data flow)

**Status:** Parameter/algorithm spec. The single source of truth for direction, scope, and framing is `MASTER-SPEC.md`; this document is the detailed reference for every parameter (value + justification + status), every equation, every metric formula, the statistical method, and how the modules interlock at runtime. Companion to `PROJECT-PROPOSAL.md` (the earlier proposal) and `METHODOLOGY-AND-IMPLEMENTATION-DESIGN.md` (build plan). Produced 2026-06-20 from a five-specialist research pass; every external claim is cited and was web-verified unless marked otherwise. Where any framing here conflicts with `MASTER-SPEC.md`, the latter governs.

**Value status legend:** `[D]` derived from first principles/other parameters · `[C]` literature-cited standard · `[K]` must be calibrated (procedure given) · `[E]` engineering threshold, no external standard.

---

## In plain terms (read this first)

This document is the engineering rulebook: it fixes *every number* the system uses (timings, thresholds, statistical settings), says where each number comes from, and shows how the pieces fit together at run time. If the proposal is "what we are building and why", this is "exactly how, with all the constants nailed down". Each value is tagged `[D]` derived, `[C]` cited from the literature, `[K]` must be calibrated from data, or `[E]` an engineering choice. Specialist terms are translated in [`GLOSSARY.md`](GLOSSARY.md).

## 0. Citation-integrity and calibration registers (read first)

**Citation integrity (re-verified 2026-06-20, 201-agent fact-check):**
- The conservation law's primary grounding is the **LWR continuity equation** (Lighthill & Whitham 1955, *Proc. R. Soc. A* 229; Richards 1956, *Oper. Res.* 4, both verified). **Derhab et al. 2020** (*Sensors* 20(21):6106, DOI 10.3390/s20216106) is a verified, correctly-described precedent: it uses relaxed flow-conservation as a one-class detector for selective-routing attacks in wireless sensor networks. We cite it for the conservation-residual idea and adopt LWR for the physics; the honest gap is the domain (WSN routing → vehicle flow). (An earlier draft wrongly flagged this citation as unverifiable; that flag was the error, not the citation.)
- CUSUM concept grounded in Page (1954); the **tabular recursion** is Page (1961)/Lucas (1982)/Hawkins-Olwell (1998); ARL via Siegmund (1985) + Montgomery SQC. MaxPressure in Varaiya (2013); note our `P_i` is the simplified halting-count form, not Varaiya's saturation-flow/turning-ratio-weighted rule (§2). Green-wave concept in Morgan & Little (1964)/Little (1966); the closed-form offset is a modern simplification of their MILP framework. All papers verified (Sources, §10).

**Must-calibrate parameters `[K]` (no guessed values ship):** `coord_weight (λ)`, `shield_margin`, `gate`, `processing`, `outage_persist`, `escalation_cooldown`, `clock_skew_bound`, `sensing_latency`, and the empirical confirmation of `rel_frac` and CUSUM `h`. Each has a procedure below. The dissertation must report the calibrated value + the benign run it was selected on.

**Unverified assumptions `[U]`:** intra-seed EV correlation `ρ≈0.3` (planning value, re-derive from a pilot); corroboration assumes at most single-junction compromise (≥2-key collusion explicitly out of scope).

---

## 1. Master parameter table

Units: s=seconds, m=metres, m/s, m/s², veh=vehicles, win=windows/decision-rounds, –=dimensionless.

### 1.1 Control + signal timing
| Symbol | Meaning | Units | Value (50 km/h arterial) | Status | Basis |
|---|---|---|---|---|---|
| `v` | design/approach speed | m/s | 13.9 | [C] | operating point (pre-registered) |
| `t_pr` | perception-reaction time | s | 1.0 | [C] | ITE/NCHRP 03-95 |
| `a` | comfortable deceleration | m/s² | 3.05 | [C] | ITE (10 ft/s²) |
| `yellow` | yellow change interval | s | 3 | [D] | y = t_pr + v/(2a) = 3.28 → 3; un-shortenable per MUTCD 4D.27; 3-6 s range per MUTCD 4D.26/4F.17 |
| `W_x` | intersection crossing width | m | 18 | [C] | corridor geometry |
| `L_v` | vehicle length | m | 5 | [C] | ITE/SUMO default |
| `r_ac` | all-red clearance | s | 2 | [D] | (W_x+L_v)/v = 1.65 → 2 |
| `l₁` | start-up lost time/phase | s | 2 | [C] | Webster 1958 / HCM acceleration delay at green onset |
| `C_opt` | Webster optimal cycle | s | ≈78 (at Y_w=0.667; calibrate) | [D] | (1.5·L_lost+5)/(1−Y_w), Webster 1958 |
| `L_lost` | lost time/cycle | s | n_φ·(l₁+yellow+r_ac)=14 | [D] | Webster; start-up + change interval, no end-gain credit (conservative) |
| `min_green` | minimum green hold | s | 10 | [E] | formula max(7 ITE, yellow+r_ac)=7; raised to 10 [E] to reduce SLM call rate |
| `max_green` | maximum green hold | s | 64 | [D] | C_opt − L_lost (to-build in shield) |
| `decision_interval` (Δ) | re-evaluation period | s | 10 (= min_green) | [D] | structural: re-decide once min_green elapses |
| `gate` | event-gate total halting to consult SLM | veh | 2 | [K]/[E] | compute-economy; sweep {1,2,3,5} |
| **Coordination** | | | | | |
| `coord_weight` (λ) | Channel-B coordination weight | – | calibrate; report 0 & selected | [K] | sweep {0,0.25,0.5,1,2}; smallest λ with Holm-sig delay gain, no benign regress |
| `ℓ_e` | connecting-edge length | m | per edge | [C] | SUMO net |
| `v_free` | free-flow speed on edge | m/s | per edge (getMaxSpeed) | [C] | SUMO |
| `t_arrive` | platoon arrival time | s | t_release + ℓ_e/v_free | [D] | kinematics |
| `offset_AB` | green-wave offset | s | (ℓ_e/v_free) mod C_opt | [D] | Morgan & Little 1964 |
| `H` | coordination look-ahead horizon | s | = C_opt (≈60) | [D] | one cycle |
| **Shield** | | | | | |
| `shield_margin` | pressure-floor veto tolerance | veh | calibrate; report 0 baseline | [K] | sweep {0,2,4,8,16}; largest passing benign never-regress |
| `max_skip` | anti-starvation skip bound | decisions | 3 | [D]/PINNED | PINNED anti-starvation shield value (MASTER-SPEC §0 / §6.8); the ⌈C_opt/Δ⌉=⌈78/10⌉=8 cycle figure is a looser upper bound now superseded by the tighter pinned 3 |
| `T_starve` | worst-case wait bound | s | ≤43 | [D] | max_skip·Δ + (min_green+yellow) = 3·10+13 |

### 1.2 Detection (conservation + CUSUM)
| Symbol | Code | Meaning | Units | Value | Status | Basis |
|---|---|---|---|---|---|---|
| `a₀` | abs_floor | constant counting-error floor | veh | 2.0 | [D] | √(1²+1²)≈1.41→2 (two ±1 count streams) |
| `c_r` | rel_frac | proportional flow count error | – | 0.15 | [D]/[K] | ~5% free-flow count error (FHWA-sponsored detector evaluations, e.g. TTI FHWA/TX-03/2119-1) + congestion margin; confirm at 95th pct of benign \|r\|/f_exp |
| `c_s` | storage_uncert | snapshot noise coeff (×√s) | – | 1.0 | [D] | Poisson Var=mean ⇒ σ=√s; admit ±1σ |
| `k` | slack | CUSUM reference value | bands | 0.5 | [D] | k=δ/2 for smallest detectable shift δ=1 band; Page/Montgomery |
| `h` | h | CUSUM decision threshold | bands | 3.0 | [D]/[K] | Siegmund ARL₀≈120 win/arm, ARL₁≈6 win; confirm benign ARL₀ |
| `θ_occ` | spillback_occupancy | jam occupancy threshold | frac | 0.55 | [C] | Greenshields ρ_crit=ρ_jam/2 → crit occ ~0.5 + margin |
| `φ_v` | spillback_speed_frac | jam speed fraction | – | 0.30 | [C] | congested-branch speed ≈20-35% free |
| `w₀` | warmup_windows | priming windows | win | 3 | [D] | storage_prev + log fill + start-up transient |
| `W` | window | counting window | s | 30 | [D] | W ≳ L/v_free (14-29 s for demo edges) |
| `retain` | retain | log retention | s | 4·W=120 | [D] | covers publish→reconcile lag (sender/receiver window match) |

### 1.3 Triggers + corroboration
| Symbol | Meaning | Units | Value | Status | Basis |
|---|---|---|---|---|---|
| `processing` | SLM round-trip budget | s | 1.0 | [K] | Foundry p95 (de-risk ~0.5 s; 1.0 conservative) |
| `ev_horizon` | EV trigger arming distance | m | v_free·(min_green+yellow+processing) | [D] | kinematic derivation (green pre-positioned before arrival); MUTCD 4D.27 preemption framework, NTCIP 1211 EVP messaging for context only |
| `incident_occ` | incident occupancy threshold | frac | 0.70 | [C] | well past capacity occupancy (~0.11-0.25, incident-detection literature: California algorithm family, FHWA Traffic Detector Handbook) = standing jam |
| `incident_speed_frac` | incident speed ceiling (×free) | – | 0.10 | [D] | ≤ walking pace = stopped, not slow queue |
| `incident_persist` | incident persistence | win | 3 | [E] | persistence guard against transient queues; value engineering-set (California-family algorithms use persistence logic but do not specify 3) |
| `outage_persist` | missing_claim persistence | rounds | 3 | [K] | absorb transport jitter; calibrate to loss rate |
| `abnormal_k` | demand sigma multiplier | σ | 3 | [C]/[E] | one-sided 3σ SPC (FA≈0.00135 under Gaussian; halting counts are Poisson/neg-binomial so realised FA is 2-4× higher; treat 0.00135 as a floor) |
| `S` | EWMA span | decisions | 20 | [E] | λ_ewma=2/(S+1)≈0.095; EWMA concept from Roberts 1959, the span↔λ conversion is a later moving-average convention; S=20 engineering-set |
| `abnormal_persist` | demand persistence | win | 2 | [E] | guards single-tick noise |
| `escalation_cooldown` | anti-flap | rounds | 1 | [K] | Foundry serialisation bound |
| `clock_skew_bound` | max inter-junction clock skew | s | calibrate (≤0.1 LAN/≤1 WAN) | [K] | NTP max-offset |
| `sensing_latency` | sighting-vs-presence lag | s | calibrate (≈Δ) | [K] | last-step detector read |
| `tol` (corrob.) | corroboration time tolerance | s | clock_skew_bound + sensing_latency | [D] | sum of the two above |
| `route_traveltime` | upstream free-flow transit | s | Σ ℓ_k/v_free,k over upstream route | [D] | kinematics |

### 1.4 Metrics + statistics + calibration
| Symbol | Meaning | Units | Value | Status | Basis |
|---|---|---|---|---|---|
| `n_boot` | BCa bootstrap resamples | – | 10000 | [E] | BCa method = Efron 1987 / DiCiccio-Efron 1996; resample count is a modern compute convention (Efron-Tibshirani 1993 suggested ≥1000 for CIs), not from Efron 1987 |
| `n_perm` | Monte-Carlo permutation draws | – | 10000 | [E] | Good 2005; (B+1)/(m+1) for sampled (not exhaustive) permutations, Phipson-Smyth 2010 |
| `alpha` | significance level | – | 0.05 | [C] | standard |
| `power` | target power 1−β | – | 0.80 | [C] | Cohen 1988 |
| `MDE` | min detectable effect (paired) | metric units | (z_{1−α/2}+z_{1−β})·sd_diff/√n = 0.511·sd_diff (n=30) | [D] | paired-design power |
| `seeds` | paired seeds | – | 30 | [C]/[D] | de-risk power finding |
| `J` | EV injections per seed | – | 6 | [D]/[U] | n_eff≥60 at ρ≈0.3 (re-derive after pilot) |
| `tol_rec` | recovery tolerance | frac | 0.10 | [E] | queue within 10% of baseline |
| `k_rec` | recovery persistence | cycles | 3 | [E] | sustained return |
| `W_base` | pre-incident baseline window | cycles | 10 | [E] | stable baseline |
| `λ` (sweep) | lie magnitude / band | – | {0.25,0.5,0.75,1,1.25,1.5,2,2.5,3} | [D] | free-deviation-boundary / deviation-magnitude x-axis |
| `ρ_knee` | recall-collapse recovery threshold | – | 0.5 | [E] | half-maximum knee |
| GEH<5 | demand-calibration acceptance | – | ≥85% of links | [C] | DfT TAG M3.1 |

---

## 2. Control + coordination (equations)

**(1) MaxPressure pressure** of green phase i over served movements M(i):
`P_i = Σ_{l∈M(i)} ( n_in(l) − n_out(l) )`. This is the **simplified halting-count form we implement** (unit weights). Varaiya's (2013) throughput-optimality proof is for the full rule, which weights each movement by its saturation flow rate and discounts downstream queues by turning ratios: `P^φ = Σ [x(l,m) − Σ_n x(m,n)·r(m,n)]·c(l,m)`. We adopt the unit-weight approximation (standard in SUMO MaxPressure baselines) and do not claim the formal stability guarantee transfers unchanged. Decision: `i* = argmax_i P_i`, re-evaluated when the green has held `min_green`.

**(2) Yellow / (3) all-red:** `yellow = t_pr + v/(2a)`; `r_ac = (W_x+L_v)/v`.
**(4) Webster cycle:** `C_opt = (1.5·L_lost + 5)/(1 − Y_w)`, `L_lost = n_φ·(l₁ + yellow + r_ac)` with start-up lost time `l₁=2 s/phase` (Webster 1958), `Y_w` = Σ critical flow ratios (site-measured; 0.667 is the planning value, calibrate). At n_φ=2, Y_w=0.667: L_lost=14, C_opt≈78.
**(5/6):** `min_green = max(7, yellow+r_ac) = 7 s` (ITE floor binds); raised to 10 s as an engineering policy to reduce SLM call rate (not a formula output). `max_green = C_opt − L_lost = 64 s`.

**(7) Platoon arrival:** `t_arrive = t_release + ℓ_e/v_free`. **(8) Offset:** `offset_AB = (ℓ_e/v_free) mod C_opt` (Morgan & Little 1964). **(9) Horizon:** `H = C_opt`.

**(10) Channel-B coordinated score:** `adj_halting_i = green_halting_i + λ·incoming_per_phase_i`; `coord_choice = (mp_choice if λ=0 else argmax_i adj_halting_i)`. λ=0 short-circuits to a byte-exact MaxPressure ablation (FR-8). Per MASTER-SPEC §8 the coordination term is an **inert structural zero**, reported as such and NOT an experimental benefit; any delay effect is not a headline claim (no traffic-performance benefit is claimed).

**Anti-starvation:** `max_skip = 3` (PINNED anti-starvation shield value, MASTER-SPEC §0 / §6.8; the ⌈C_opt/Δ⌉=⌈78/10⌉=8 cycle figure is a looser upper bound now superseded by the tighter pinned 3); worst-case wait `T_starve ≤ max_skip·Δ + (min_green+yellow) = 3·10+13 = 43 s`.

---

## 3. Detection (conservation + CUSUM)

**Mass-balance residual** (integral LWR form):
`r = entered − exited − (storage_now − storage_prev)`, units veh. `entered` over the sender's window [t_send−W, t_send]; `exited`, `storage` at receiver `now` (travel-time alignment). r>0 sustained = over-claim (spoof); r<0 = under-report (fault).

**Adaptive band:** `band = a₀ + c_r·f_exp + c_s·√s`, `f_exp = max(entered,exited)`, `s = max(storage_now, storage_prev)`. Normalised residual `z = r/band` (band>0 since a₀>0).

**Tabular CUSUM:** `S_hi = max(0, S_hi + z − k)`, `S_lo = max(0, S_lo − z − k)`; flag when `S_hi>h` (inflated) or `S_lo>h` (under_reported); reset firing arm on flag.

**ARL derivation (Siegmund, b = h+1.166):** `ARL(Δ) ≈ (exp(−2·Δ⁺·b) + 2·Δ⁺·b − 1)/(2·Δ⁺²)`, `Δ⁺ = Δ − k`.
- In-control (Δ=0): ARL₀ ≈ 119 win/arm (one-sided) ≈ **~60 win combined** (two independent arms). At W=30 s that is **~30 min between false alarms for the combined detector** (the ~1 h figure applies only to a single one-sided arm: 119·30 s).
- Out-of-control (δ=1 band): the deterministic zero-noise bound is `⌈h/(δ−k)⌉ = ⌈3/0.5⌉ = 6 win`; the Siegmund expected detection time is ARL₁ ≈ 6.4 → **~7 win**. So h=3 detects a sustained 1-band spoof in ~6-7 windows. Raising h trades ARL₀↑ for ARL₁↑; confirm benign ARL₀ ≥ target on the 30 benign seeds.

**Spillback gate:** jam iff `occupancy ≥ θ_occ (0.55) AND mean_speed ≤ φ_v·free_speed (0.30·free)`; a spillback window is reconciled but NOT fed to the CUSUM (storage changes faster than the snapshot tracks). Warm-up `w₀=3` windows never flag.

---

## 4. Triggers + corroboration

Two regimes per tick: NORMAL (no trigger → MaxPressure decides, coordination advisory) or TRIGGERED (SLM proposes, shield disposes). Trigger priority: `emergency_vehicle > incident > conservation_anomaly > sensor_outage > abnormal_demand`.

**Predicates** (J = junction, e = edge, gi = served phase):
- **EV:** `EV(J) = {vid : vClass(vid)=="emergency" on an in-edge}`; fire iff `∃vid: d(vid) ≤ ev_horizon OR halted on approach`. Latch per (J,vid) until the EV clears all J edges. `source ∈ {local_sensing, advance_claim}`.
- **incident:** `green(e,gi) AND occ(e) ≥ 0.70 AND spd(e) ≤ 0.10·free(e)` sustained ≥3 windows.
- **sensor_outage:** approved neighbour, `observed_inflow>0 AND missing_claim ≥3 rounds`.
- **abnormal_demand:** EWMA(span 20) + `H_t > μ + 3σ` sustained ≥2 windows, after warm-up.
- **conservation_anomaly:** a flagged Detection this round with reason ∈ {inflated, under_reported}; handling = zero the flagged neighbour's `incoming_per_phase` before recompute.

**EV corroboration (anti-spoof core):** each junction U keeps a signed append-only sighting log `Sighting(ev_id, edge_id, t_sighted, sig_U)` of its OWN vClass=emergency detections, published as signed telemetry.
`corroborated(e, J, now) ⇔ ∃U on route(e), ∃s∈SightingLog[U]: verify(s.sig_U) AND is_approved(U) AND s.ev_id==e.ev_id AND s.edge_id upstream of J on route AND (now − route_traveltime(U,J) − tol) ≤ s.t_sighted ≤ (now + tol)`. (Both bounds widened by `tol`; a one-sided window would falsely deny corroboration when the upstream clock runs fast.)
`admissible_ev(trig) ⇔ source=="local_sensing" OR (source=="advance_claim" AND auth_valid AND corroborated)`. Inadmissible (phantom) → shield returns mp_choice (no preemption). Limit: mid-corridor entry gets local-only preemption; ≥2-key collusion out of scope.

---

## 5. Threat model + attacks

**Attacker tiers:** (T1) outsider no-key → auth `unknown_sender`/`bad_signature`, IN scope; (T2) Dolev-Yao network adversary → replay-dedup + crypto, IN scope, residual = cross-restart replay (build item: persisted per-sender high-water-mark); (T3) single compromised insider (one key) → conservation residual, IN scope for supra-tolerance + phantom-emergency, sub-tolerance evades (stated); (T4) ≥2-key conservation-respecting collusion → by construction the colluders keep the mass-balance residual inside the band (one inflates a claim, the other supplies a matching fake observation), so the residual is statistically indistinguishable from benign traffic and recall→0; OUT of scope, contained by key revocation + audit, not detection; (T5) compromised admin key → OUT of scope, single point of total failure.

**Attack injection (compose over `MaliciousPublisher`, never edit the bus):**
| Attack | Parameters | Ground-truth window | Expected outcome |
|---|---|---|---|
| phantom-preemption | uncorroborated `ev_claim{approach,eta}` | tick t0, malicious | auth admits; corroboration withholds preemption |
| phantom-incident | `incident_edge`, no matching obs | tick t0 | conservation `missing_observation` (FN possible if no reconciled edge; report) |
| count-inflation | `release = true + λ·band`, λ-sweep | tick=index(λ) | `inflated` once λ>1; recall climbs 0→1 across λ=1 |
| sub-tolerance lie | `release = true + δ`, 0<δ≤tol | tick t0 | `ok` (undetected by design: δ within band keeps \|z\|≤1, below CUSUM reference k=0.5; this is the honest residual-detection floor) |
| replay | resend captured (sender,t,payload,sig) | replayed tick | in-session `replay`; cross-restart NOT defended (residual) |
| impersonation | sign as victim with wrong key | tick t0 | `bad_signature`, latency 0 |

**Fair victim (`cooperative_naive`):** representative of the trust-everything cooperative class CoLLMLight exemplifies (CoLLMLight shares state via a graph, not signed messages; we model the same trust over an explicit channel). Identical control + coordination; bypasses ONLY signature verify + registry + conservation. Acceptance: no-attack defended-vs-victim benign delta within MDE / non-significant (else reported as overhead). Single approved insider (T3) is the adversary, not an outsider.

---

## 6. Metrics, statistics, calibration, power

**Traffic (full-population tripinfo):** throughput `|C|`; completion_rate `|C|/|D|`; mean_network_delay `Σ_{i∈D} d_i / |D|`; matched_diff over `C_A∩C_B`. **Emergency:** AETT = horizon-penalised mean over departed EVs (stranded EV contributes `T_end − T_dep`); AEWT = mean SUMO `waitingTime` (speed<0.1) over EVs; ECR = `|E∩C|/|E∩D|`. **Incident recovery:** IRT = first-passage of `q_a(τ) ≤ (1+tol_rec)·q_base for k_rec consecutive cycles`, baseline = mean over `W_base` pre-incident cycles, right-censored at horizon.

**Detection (window-labelled, positive = injected attack active on edge that window):** precision `TP/(TP+FP)`, recall `TP/(TP+FN)`, F1 `2PR/(P+R)`, latency = first-detect − first-malicious cycle, false_alarm_rate `FP/(FP+TN)`. **Safety:** false_preemption_rate, shield_veto_rate, anti_starvation_violations (target 0), safe_but_suboptimal_rate. **Overhead:** sign/verify/commit latency (median + p95, right-skewed).

**Free-deviation boundary (measured characterisation):** `recall(λ)`, `latency(λ)`, λ = deviation/band; the recall-collapse point `λ* = sup{λ: recall(λ)<0.5}` with BCa CI (or logistic half-max fit). This is the deviation-magnitude axis; the headline object is the phase-coupled coverage threshold on the real corridor (§8, MASTER-SPEC). Not a detection ROC.

**Statistics:** primary family {mean_network_delay, completion_rate, throughput} Holm-corrected together (confirmatory); others exploratory with CIs. BCa bootstrap (method: Efron 1987 / DiCiccio-Efron 1996; n_boot=10000), paired Monte-Carlo permutation with the (B+1)/(m+1) correction for sampled permutations (Phipson-Smyth 2010; n_perm=10000), Holm-Bonferroni (1979), effect size = Cliff's delta (Cliff 1993) reported with a BCa CI, EV analysis = seed-random-intercept mixed model (within-seed EV correlation). All paired on seed.

**Power:** `MDE = (z_{1−α/2}+z_{1−β})·sd_diff/√n = 0.5115·sd_diff` at n=30 (t-correction df=29 → ×2.899/2.802 ≈ +3.5%, giving 0.529·sd_diff). A null = "below MDE = X", not "no effect". EV effective sample size (Kish): `n_eff = n·J/(1+(J−1)·ρ)`; at n=30, ρ≈0.3, J=4 already gives n_eff=63 (clears the ≥60 target), and **J=6 gives n_eff=72** (headroom). (re-derive ρ after pilot).

**Calibration:** `GEH = √(2(M−C)²/(M+C))` per link, accept GEH<5 for ≥85% of links (DfT TAG M3.1); demand-scale sweep 0.3-3.0 with the GEH-passing point marked; pre-register the operating point in the green-wave-headroom regime before unblinding.

---

## 7. System integration: config, per-tick data flow, module specs

### 7.1 Config object (single source of runtime parameters)
A frozen `EdgeNegotiatorConfig` dataclass carries every parameter in §1 with its default and validation at the boundary (finite, ranges). Calibrated `[K]` params are loaded from a per-scenario config file written by the calibration step; nothing is hard-coded at a call site. The config records, per parameter, its status `[D/C/K/E]` and provenance so a result is reproducible from `(config, seed, model_hash)`.

### 7.2 Per-tick data flow (what executes, with module I/O)
For each SLM junction, each simulated second:
```
step():
  flow window: snapshot vehicle ids on watched edges (getLastStepVehicleIDs) -> FlowWindow.observe
  refresh _edge_meta: (occupancy/100, mean_speed, free_speed) per watched edge
  advance signal timing (min_green/yellow/all-red owned here; SLM cannot touch)

decide(tl, st)  [only when min_green elapsed]:
  1. mp_choice = MaxPressure argmax P_i                         [controllers._pressure]
  2. if quiet (Σ green_halting < gate): return mp_choice
  3. publish signed toward-message; read VERIFIED inbox          [message_bus: sig+registry+replay]
     reconcile claims vs observed -> detections (CUSUM)          [flow_conservation.update_many]
     publish own EV sightings (signed)                           [sighting log]
  4. trig = evaluate_trigger(detections, _edge_meta, EV scan, EWMA)   [highest priority]
  5. NORMAL (trig is None): coord_choice via Eq.(10); proposal = SLM advisory;
                            used = proposal or coord_choice; return shield_validate(used, mp, None)
  6. TRIGGERED: emergency_note = build_prompt(trig, evidence);
                proposal = SLM.choose_phase(...);
                candidate = proposal or rule_fallback(trig);
                applied  = shield_validate(candidate, mp, trig);   [V1,V_starve,V3 corrob,V4,V5]
                log_escalation(escalation_changed_decisions if applied != mp);
                return applied
```
At λ=0, no trigger, no SLM override: reduces exactly to `mp_choice`.

### 7.3 Per-module spec requirements (inputs → outputs → invariants)
| Module | Consumes | Produces | Invariant |
|---|---|---|---|
| `MaxPressureController` | TraCI halting per lane | `mp_choice`, timing transitions | throughput-optimal base; owns min_green/yellow/all-red |
| `MessageBus` | signed NeighborMessage | verified inbox; `rejected` log | only adjacency+approved+sig-valid+non-replayed delivered |
| `FlowWindow` | per-tick edge vid sets | entered/exited/storage over window | distinct-vehicle counts; retain≥4W |
| `FlowConservationDetector` | EdgeMeasurement | EdgeVerdict (flagged, reason, latency) | spillback/warmup never flag; ARL₀≥target |
| `EmergencyController` (NEW) | mp_choice, detections, _edge_meta, inbox, EV scan | `trig`, `applied`, escalation log | TRIGGERED proposal is executed candidate; shield can veto; λ=0 ⇒ MaxPressure |
| `_shield_validate` (NEW) | candidate, mp_choice, trig | safe executed phase | V1 validity, V_starve, V3 corroborated-EV-only, V4 conservation, V5 pressure-floor |
| `_admissible_ev` (NEW) | trig (source, auth_valid, corroborated) | bool | phantom EV never enforced |
| `emergency_metrics` (NEW) | RunRecord + escalation log | AETT/AEWT/ECR/IRT/false_preemption | population-safe, censored |
| `stats` | per-seed paired metrics | BCa CI + perm p + Holm + Cliff's δ | paired on seed; primary family FWER-controlled |

### 7.4 Build status (code map)
- **Built + tested:** MaxPressure, MessageBus (auth+replay), FlowWindow, FlowConservationDetector (CUSUM), conservation (stateless offline), metrics (traffic), stats, evaluation harness, identity/registry, permissioned-ledger/messaging anchor spikes (demoted to the cited-prior-art anchor option).
- **To build (MUST):** `EmergencyController` + `_shield_validate` (V_starve anti-starvation, V3 corroboration gate, V5 pressure floor with calibrated `shield_margin`), `_admissible_ev` + signed sighting log, the 5 trigger evaluators, `emergency_metrics`, `cooperative_naive` victim, `attacks_live` (ev_claim/incident_claim/λ-sweep injectors), the λ-reparameterised free-deviation-boundary sweep + recall-collapse estimator, Cliff's delta + mixed-effects, MDE reporter, max_green enforcement, cross-restart replay high-water-mark, spillback-cap, payload size/depth bound.

---

## 8. Formal system properties

Testable, canonical statements of the properties invoked informally elsewhere in this document (the threat model, §5; the trigger predicates, §4; the shield, §7.2-7.3) and in `PROJECT-PROPOSAL.md` §5. Parameters in `[K: ...]` are calibrated/pre-registered per §0, not asserted values. Where a parameter already has a value in §1, that value is authoritative and cited here, not restated.

**Robust degradation (testable systems property).** Under any single authenticated-but-compromised neighbour input (spoofed claim, inflated or under-reported release, replay, silence):
- R1 Detection: a deviation exceeding the plausibility band (`band`, §3) is flagged within `[K: D]` decision windows (measured as detection latency vs lie magnitude). The CUSUM zero-noise bound is `⌈h/(δ-k)⌉=6` windows and the Siegmund expected value is ≈6.4 windows for a sustained 1-band lie (§3, §9 relationship), so `D` is calibrated around that order of magnitude, not asserted independently.
- R2 Containment: a flagged input's influence on control is zeroed (the conservation_anomaly handling in §4 discounts the flagged neighbour's contribution to zero before recompute), and uncorroborated preemption claims are refused at all times (`admissible_ev`, §4).
- R3 Bounded degradation: performance under attack stays within a pre-registered margin `[K: epsilon]` of the local-control (MaxPressure-only, λ=0) fallback. `epsilon` is a new calibrated parameter, not yet in the §1 master table; it is a build item pending the exploit-then-defend calibration run, not a guessed value.
- R4 Safety invariance: the safety floor (below) holds at every tick, attacked or not.
- Honest bounds: a within-band lie is undetected by construction (R3/R4 still bound its harm; see the sub-tolerance-lie row of the attack table, §5); in-band collusion defeats R1 and is out of scope (T4, §5), contained by revoke + audit, not detection.

**Ambiguous case (deterministic escalation predicate).** A tick escalates to the SLM iff:
- A1 the conservation/CUSUM detector (§3) flags a neighbour claim this window, or
- A2 an authenticated emergency/incident claim has partial evidence (corroboration present but below the hard-accept threshold, or stale/inconsistent, e.g. a sighting older than the route travel-time tolerance `tol`, §4), or
- A3 two authenticated reports about the same edge contradict beyond the tolerance band (`tol`, §4).

Fully corroborated and zero-evidence claims never escalate; they resolve deterministically in NORMAL regime. The SLM output is a proposal, the shield (§7.2-7.3) validates it against the safety floor below. This predicate is the compact formal gate for the five trigger evaluators of §4 (`emergency_vehicle`, `incident`, `sensor_outage`, `abnormal_demand`, `conservation_anomaly`); `METHODOLOGY-AND-IMPLEMENTATION-DESIGN.md` §2 gives the per-trigger implementation detail.

**Safety floor (invariant set, SLM-independent).** The executed action always satisfies:
- S1 min/max green bounds (`min_green=10`, `max_green=64`, §1.1/§2).
- S2 protected yellow + all-red clearance on every transition (`yellow=3`, `r_ac=2`, §1.1/§2).
- S3 anti-starvation: no approach skipped more than `max_skip=3` consecutive decisions (PINNED per MASTER-SPEC §0 / §6.8; §1.1/§2; worst-case wait `T_starve≤43 s`, §1.1/§2); a corroborated emergency may defer it by at most one min_green+yellow.
- S4 preemption only for corroborated emergencies (`admissible_ev`, §4).

A violating SLM proposal is replaced by the deterministic choice (`_shield_validate`, §7.2-7.3).

---

## 9. Relationships (the couplings)
`yellow,r_ac → L_lost → C_opt → {max_green}; max_skip PINNED=3 (MASTER-SPEC §0/§6.8; not purely C_opt-derived) → T_starve`; `min_green = Δ`; `yellow+r_ac ≤ min_green`; `k = δ/2`, detection latency ≈ 6-7 win (`⌈h/(δ−k)⌉=6` zero-noise bound, Siegmund expected ≈6.4), ARL₀ via Siegmund; `band ≈ 1σ benign residual` so z is standardised and CUSUM tables apply; `λ` couples coordination to local queue (0 = decoupled); `shield_margin` bounds SLM↔MaxPressure divergence (orthogonal to λ); `ev_horizon = v_free·(min_green+yellow+processing)`; `tol = clock_skew_bound + sensing_latency`; the same signed `release` feeds both conservation and coordination (unification 1); the conservation flag is the SLM escalation trigger (unification 2, formalised as predicate A1 in §8).

---

## 10. Sources (verified this pass)
- Varaiya 2013, Max pressure control, Transp. Res. C 36:177-195.
- Webster 1958, Traffic Signal Settings, RRTP 39.
- ITE/NCHRP 03-95, change-interval; Gates et al. 2012 TRR 2298.
- Morgan & Little 1964, Oper. Res. 12(6):896-912; Little 1966, Oper. Res. 14(4):568-594.
- Lighthill & Whitham 1955 Proc. R. Soc. A 229; Richards 1956 Oper. Res. 4 (LWR conservation).
- Page 1954 Biometrika 41 (CUSUM concept); tabular CUSUM = Page 1961 / Lucas 1982 / Hawkins-Olwell 1998; k=δ/2 = Bagshaw-Johnson 1974 / Moustakides 1986; Siegmund 1985 Sequential Analysis; Montgomery, Intro. to SQC (ARL).
- Greenshields 1935 (HRB Proc. 14:448-477, fundamental diagram ρ_crit=ρ_jam/2); TRB EC149 is a separate 2008 Greenshields-symposium compendium. FHWA-sponsored detector evaluations (~5% free-flow count error; the figure sits in associated TTI reports, not the Detector Handbook proper).
- MUTCD 4D.27 (preemption, un-shortenable yellow) and 4D.26/4F.17 (3-6 s change-interval range); NTCIP 1211 (EVP messaging, not the ev_horizon formula); California AID algorithm family (persistence logic; value 3 engineering-set); HCM (density-based, not occupancy thresholds); Roberts 1959 (EWMA concept).
- BCa method = Efron 1987 JASA 82 (main article 171-185; with discussion 171-200) / DiCiccio-Efron 1996; resample count is a compute convention. Holm 1979 Scand. J. Statist. 6:65-70; Cliff 1993 Psych. Bull. 114(3):494-509 (Cliff's delta only); Phipson & Smyth 2010 (sampled-permutation +1); Pinheiro & Bates 2000 (mixed models); Cohen 1988 (power); DfT TAG M3.1 (GEH).
- Dolev & Yao 1983 IEEE TIT 29(2):198-208 (formal adversary model); Chen et al. NDSS 2018 (a concrete CV congestion-attack exemplar, not a formal taxonomy).
- Derhab et al. 2020 Sensors 20(21):6106 (WSN flow-conservation detector, ported in concept).
