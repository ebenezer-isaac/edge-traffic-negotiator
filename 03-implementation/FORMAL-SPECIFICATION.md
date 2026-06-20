# The Edge Negotiator: Formal Specification (parameters, algorithms, metrics, data flow)

**Status:** CANONICAL spec authority. Companion to `PROJECT-PROPOSAL.md` (direction/scope) and `METHODOLOGY-AND-IMPLEMENTATION-DESIGN.md` (build plan). This document is the single source for: every parameter (value + justification + status), every equation, every metric formula, the statistical method, and how the modules interlock at runtime. Produced 2026-06-20 from a five-specialist research pass; every external claim is cited and was web-verified unless marked otherwise.

**Value status legend:** `[D]` derived from first principles/other parameters · `[C]` literature-cited standard · `[K]` must be calibrated (procedure given) · `[E]` engineering threshold, no external standard.

---

## 0. Citation-integrity and calibration registers (read first)

**Citation integrity:**
- The conservation law is grounded in the **LWR continuity equation** (Lighthill & Whitham 1955, *Proc. R. Soc. A* 229; Richards 1956, *Oper. Res.* 4), NOT in a "Derhab 2020 (Sensors) flow-conservation" paper. That reference **could not be externally verified and appears misattributed**; a `Derhab2020FlowConserv.pdf` exists in the corpus and must be re-checked or dropped before citing. ACTION: verify or remove.
- CUSUM grounded in Page (1954) + Siegmund (1985) + Montgomery SQC. MaxPressure in Varaiya (2013). Green-wave in Morgan & Little (1964)/Little (1966). All verified (Sources, §9).

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
| `yellow` | yellow change interval | s | 3 | [D] | y = t_pr + v/(2a) = 3.28 → 3; MUTCD 4D.27 un-shortenable, 3-6 s range |
| `W_x` | intersection crossing width | m | 18 | [C] | corridor geometry |
| `L_v` | vehicle length | m | 5 | [C] | ITE/SUMO default |
| `r_ac` | all-red clearance | s | 2 | [D] | (W_x+L_v)/v = 1.65 → 2 |
| `C_opt` | Webster optimal cycle | s | ≈60 (per-cell from Y_w) | [D] | (1.5·L_lost+5)/(1−Y_w), Webster 1958 |
| `L_lost` | lost time/cycle | s | n_φ·(yellow+r_ac) | [D] | Webster |
| `min_green` | minimum green hold | s | 10 | [D] | max(7 ITE, yellow+r_ac); 10 reduces SLM call rate |
| `max_green` | maximum green hold | s | 50 | [D] | C_opt − L_lost (to-build in shield) |
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
| `max_skip` | anti-starvation skip bound | decisions | 6 | [D] | ⌈C_opt/Δ⌉, capped by pedestrian max-wait policy |
| `T_starve` | worst-case wait bound | s | ≤73 | [D] | max_skip·Δ + (min_green+yellow) |

### 1.2 Detection (conservation + CUSUM)
| Symbol | Code | Meaning | Units | Value | Status | Basis |
|---|---|---|---|---|---|---|
| `a₀` | abs_floor | constant counting-error floor | veh | 2.0 | [D] | √(1²+1²)≈1.41→2 (two ±1 count streams); FHWA ~5% free-flow count error |
| `c_r` | rel_frac | proportional flow count error | – | 0.15 | [D]/[K] | FHWA 5% free-flow + congestion margin; confirm at 95th pct of benign \|r\|/f_exp |
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
| `ev_horizon` | EV trigger arming distance | m | v_free·(min_green+yellow+processing) | [D] | green pre-positioned before arrival; MUTCD 4D.27, NTCIP 1211 |
| `incident_occ` | incident occupancy threshold | frac | 0.70 | [C] | well past HCM capacity occupancy (~0.11-0.25) = standing jam |
| `incident_speed_frac` | incident speed ceiling (×free) | – | 0.10 | [D] | ≤ walking pace = stopped, not slow queue |
| `incident_persist` | incident persistence | win | 3 | [C] | California Algorithm #8 shockwave suppression |
| `outage_persist` | missing_claim persistence | rounds | 3 | [K] | absorb transport jitter; calibrate to loss rate |
| `abnormal_k` | demand sigma multiplier | σ | 3 | [C] | one-sided 3σ SPC (FA≈0.00135) |
| `S` | EWMA span | decisions | 20 | [C] | λ_ewma=2/(S+1)≈0.095 (Roberts 1959) |
| `abnormal_persist` | demand persistence | win | 2 | [E] | guards single-tick noise |
| `escalation_cooldown` | anti-flap | rounds | 1 | [K] | Foundry serialisation bound |
| `clock_skew_bound` | max inter-junction clock skew | s | calibrate (≤0.1 LAN/≤1 WAN) | [K] | NTP max-offset |
| `sensing_latency` | sighting-vs-presence lag | s | calibrate (≈Δ) | [K] | last-step detector read |
| `tol` (corrob.) | corroboration time tolerance | s | clock_skew_bound + sensing_latency | [D] | sum of the two above |
| `route_traveltime` | upstream free-flow transit | s | Σ ℓ_k/v_free,k over upstream route | [D] | kinematics |

### 1.4 Metrics + statistics + calibration
| Symbol | Meaning | Units | Value | Status | Basis |
|---|---|---|---|---|---|
| `n_boot` | BCa bootstrap resamples | – | 10000 | [C] | Efron 1987 |
| `n_perm` | permutation draws | – | 10000 | [C] | Good 2005; +1 Phipson-Smyth 2010 |
| `alpha` | significance level | – | 0.05 | [C] | standard |
| `power` | target power 1−β | – | 0.80 | [C] | Cohen 1988 |
| `MDE` | min detectable effect (paired) | metric units | (z_{1−α/2}+z_{1−β})·sd_diff/√n = 0.511·sd_diff (n=30) | [D] | paired-design power |
| `seeds` | paired seeds | – | 30 | [C]/[D] | de-risk power finding |
| `J` | EV injections per seed | – | 6 | [D]/[U] | n_eff≥60 at ρ≈0.3 (re-derive after pilot) |
| `tol_rec` | recovery tolerance | frac | 0.10 | [E] | queue within 10% of baseline |
| `k_rec` | recovery persistence | cycles | 3 | [E] | sustained return |
| `W_base` | pre-incident baseline window | cycles | 10 | [E] | stable baseline |
| `λ` (sweep) | lie magnitude / band | – | {0.25,0.5,0.75,1,1.25,1.5,2,2.5,3} | [D] | detectability-envelope x-axis |
| `ρ_knee` | recall-collapse recovery threshold | – | 0.5 | [E] | half-maximum knee |
| GEH<5 | demand-calibration acceptance | – | ≥85% of links | [C] | DfT TAG M3.1 |

---

## 2. Control + coordination (equations)

**(1) MaxPressure pressure** of green phase i over served movements M(i):
`P_i = Σ_{l∈M(i)} ( n_in(l) − n_out(l) )`  (unit movement weights; Varaiya 2013 throughput-optimal). Decision: `i* = argmax_i P_i`, re-evaluated when the green has held `min_green`.

**(2) Yellow / (3) all-red:** `yellow = t_pr + v/(2a)`; `r_ac = (W_x+L_v)/v`.
**(4) Webster cycle:** `C_opt = (1.5·L_lost + 5)/(1 − Y_w)`, `L_lost = n_φ·(yellow+r_ac)`, `Y_w` = Σ critical flow ratios (site-measured).
**(5/6):** `min_green = max(7, yellow+r_ac)`; `max_green = C_opt − L_lost`.

**(7) Platoon arrival:** `t_arrive = t_release + ℓ_e/v_free`. **(8) Offset:** `offset_AB = (ℓ_e/v_free) mod C_opt` (Morgan & Little 1964). **(9) Horizon:** `H = C_opt`.

**(10) Channel-B coordinated score:** `adj_halting_i = green_halting_i + λ·incoming_per_phase_i`; `coord_choice = (mp_choice if λ=0 else argmax_i adj_halting_i)`. λ=0 short-circuits to a byte-exact MaxPressure ablation (FR-8).

**Anti-starvation:** `max_skip = ⌈C_opt/Δ⌉ = 6`; worst-case wait `T_starve ≤ max_skip·Δ + (min_green+yellow) = 73 s`.

---

## 3. Detection (conservation + CUSUM)

**Mass-balance residual** (integral LWR form):
`r = entered − exited − (storage_now − storage_prev)`, units veh. `entered` over the sender's window [t_send−W, t_send]; `exited`, `storage` at receiver `now` (travel-time alignment). r>0 sustained = over-claim (spoof); r<0 = under-report (fault).

**Adaptive band:** `band = a₀ + c_r·f_exp + c_s·√s`, `f_exp = max(entered,exited)`, `s = max(storage_now, storage_prev)`. Normalised residual `z = r/band` (band>0 since a₀>0).

**Tabular CUSUM:** `S_hi = max(0, S_hi + z − k)`, `S_lo = max(0, S_lo − z − k)`; flag when `S_hi>h` (inflated) or `S_lo>h` (under_reported); reset firing arm on flag.

**ARL derivation (Siegmund, b = h+1.166):** `ARL(Δ) ≈ (exp(−2·Δ⁺·b) + 2·Δ⁺·b − 1)/(2·Δ⁺²)`, `Δ⁺ = Δ − k`.
- In-control (Δ=0): ARL₀ ≈ 119 win/arm ≈ **~60 win combined** ≈ ~1 h between false alarms at W=30 s.
- Out-of-control (δ=1 band): ARL₁ ≈ **6 win** = ⌈h/(δ−k)⌉ = ⌈3/0.5⌉. So h=3 detects a sustained 1-band spoof in ~6 windows. Raising h trades ARL₀↑ for ARL₁↑; confirm benign ARL₀ ≥ target on the 30 benign seeds.

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
`corroborated(e, J, now) ⇔ ∃U on route(e), ∃s∈SightingLog[U]: verify(s.sig_U) AND is_approved(U) AND s.ev_id==e.ev_id AND s.edge_id upstream of J on route AND (now − route_traveltime(U,J) − tol) ≤ s.t_sighted ≤ now`.
`admissible_ev(trig) ⇔ source=="local_sensing" OR (source=="advance_claim" AND auth_valid AND corroborated)`. Inadmissible (phantom) → shield returns mp_choice (no preemption). Limit: mid-corridor entry gets local-only preemption; ≥2-key collusion out of scope.

---

## 5. Threat model + attacks

**Attacker tiers:** (T1) outsider no-key → auth `unknown_sender`/`bad_signature`, IN scope; (T2) Dolev-Yao network adversary → replay-dedup + crypto, IN scope, residual = cross-restart replay (build item: persisted per-sender high-water-mark); (T3) single compromised insider (one key) → conservation residual, IN scope for supra-tolerance + phantom-emergency, sub-tolerance evades (stated); (T4) ≥2-key conservation-respecting collusion → recall=0 by design (Xiao2026), OUT of scope, contained by revoke+audit; (T5) compromised admin key → OUT of scope, single point of total failure.

**Attack injection (compose over `MaliciousPublisher`, never edit the bus):**
| Attack | Parameters | Ground-truth window | Expected verdict |
|---|---|---|---|
| phantom-preemption | uncorroborated `ev_claim{approach,eta}` | tick t0, malicious | auth admits; corroboration withholds preemption |
| phantom-incident | `incident_edge`, no matching obs | tick t0 | conservation `missing_observation` (FN possible if no reconciled edge; report) |
| count-inflation | `release = true + λ·band`, λ-sweep | tick=index(λ) | `inflated` once λ>1; recall climbs 0→1 across λ=1 |
| sub-tolerance lie | `release = true + δ`, 0<δ≤tol | tick t0 | `ok` (undetected by design, Xiao2026 floor) |
| replay | resend captured (sender,t,payload,sig) | replayed tick | in-session `replay`; cross-restart NOT defended (residual) |
| impersonation | sign as victim with wrong key | tick t0 | `bad_signature`, latency 0 |

**Fair victim (`cooperative_naive`):** identical control + coordination; bypasses ONLY signature verify + registry + conservation. Acceptance: no-attack defended-vs-victim benign delta within MDE / non-significant (else reported as overhead). Single approved insider (T3) is the adversary, not an outsider.

---

## 6. Metrics, statistics, calibration, power

**Traffic (full-population tripinfo):** throughput `|C|`; completion_rate `|C|/|D|`; mean_network_delay `Σ_{i∈D} d_i / |D|`; matched_diff over `C_A∩C_B`. **Emergency:** AETT = horizon-penalised mean over departed EVs (stranded EV contributes `T_end − T_dep`); AEWT = mean SUMO `waitingTime` (speed<0.1) over EVs; ECR = `|E∩C|/|E∩D|`. **Incident recovery:** IRT = first-passage of `q_a(τ) ≤ (1+tol_rec)·q_base for k_rec consecutive cycles`, baseline = mean over `W_base` pre-incident cycles, right-censored at horizon.

**Detection (window-labelled, positive = injected attack active on edge that window):** precision `TP/(TP+FP)`, recall `TP/(TP+FN)`, F1 `2PR/(P+R)`, latency = first-detect − first-malicious cycle, false_alarm_rate `FP/(FP+TN)`. **Safety:** false_preemption_rate, shield_veto_rate, anti_starvation_violations (target 0), safe_but_suboptimal_rate. **Overhead:** sign/verify/commit latency (median + p95, right-skewed).

**Detectability envelope:** `recall(λ)`, `latency(λ)`, λ = lie/band; knee `λ* = sup{λ: recall(λ)<0.5}` with BCa CI (or logistic half-max fit).

**Statistics:** primary family {mean_network_delay, completion_rate, throughput} Holm-corrected together (confirmatory); others exploratory with CIs. BCa bootstrap (Efron 1987, n_boot=10000), paired permutation (Phipson-Smyth +1, n_perm=10000), Holm-Bonferroni (1979), effect size = Cliff's delta with BCa CI, EV analysis = seed-random-intercept mixed model (within-seed EV correlation). All paired on seed.

**Power:** `MDE = (z_{1−α/2}+z_{1−β})·sd_diff/√n = 0.511·sd_diff` at n=30 (use t-correction → ×2.896/2.802 ≈ +3%). A null = "below MDE = X", not "no effect". J=6 EV injections/seed for n_eff≈67 at ρ≈0.3 (re-derive after pilot).

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
- **Built + tested:** MaxPressure, MessageBus (auth+replay), FlowWindow, FlowConservationDetector (CUSUM), conservation (stateless offline), metrics (traffic), stats, evaluation harness, identity/registry, Besu/QBFT/MQTT spikes.
- **To build (MUST):** `EmergencyController` + `_shield_validate` (V_starve anti-starvation, V3 corroboration gate, V5 pressure floor with calibrated `shield_margin`), `_admissible_ev` + signed sighting log, the 5 trigger evaluators, `emergency_metrics`, `cooperative_naive` victim, `attacks_live` (ev_claim/incident_claim/λ-sweep injectors), the λ-reparameterised detectability envelope + knee estimator, Cliff's delta + mixed-effects, MDE reporter, max_green enforcement, cross-restart replay high-water-mark, spillback-cap, payload size/depth bound.

---

## 8. Relationships (the couplings)
`yellow,r_ac → L_lost → C_opt → {max_green, max_skip → T_starve}`; `min_green = Δ`; `yellow+r_ac ≤ min_green`; `k = δ/2`, latency `= ⌈h/(δ−k)⌉ = 6 win`, ARL₀ via Siegmund; `band ≈ 1σ benign residual` so z is standardised and CUSUM tables apply; `λ` couples coordination to local queue (0 = decoupled); `shield_margin` bounds SLM↔MaxPressure divergence (orthogonal to λ); `ev_horizon = v_free·(min_green+yellow+processing)`; `tol = clock_skew_bound + sensing_latency`; the same signed `release` feeds both conservation and coordination (unification 1); the conservation flag is the SLM escalation trigger (unification 2).

---

## 9. Sources (verified this pass)
- Varaiya 2013, Max pressure control, Transp. Res. C 36:177-195.
- Webster 1958, Traffic Signal Settings, RRTP 39.
- ITE/NCHRP 03-95, change-interval; Gates et al. 2012 TRR 2298.
- Morgan & Little 1964, Oper. Res. 12(6):896-912; Little 1966, Oper. Res. 14(4):568-594.
- Lighthill & Whitham 1955 Proc. R. Soc. A 229; Richards 1956 Oper. Res. 4 (LWR conservation).
- Page 1954 Biometrika 41; Siegmund 1985 Sequential Analysis; Montgomery, Intro. to SQC (CUSUM/ARL).
- Greenshields 1935; TRB EC149 (fundamental diagram, ρ_crit=ρ_jam/2). FHWA Traffic Detector Handbook (count error).
- NTCIP 1211; MUTCD 4D.27/4G; California AID algorithm; HCM 7.1; Roberts 1959 (EWMA).
- Efron 1987 JASA 82:171-185 (BCa); Holm 1979 Scand. J. Statist. 6:65-70; Cliff 1993 Psych. Bull. 114(3):494; Phipson & Smyth 2010 (perm +1); Pinheiro & Bates 2000 (mixed models); Cohen 1988 (power); DfT TAG M3.1 (GEH).
- Dolev & Yao 1983 IEEE TIT 29(2):198-208; Chen et al. NDSS 2018 (CV congestion attack); Xiao & Weng 2026 arXiv:2602.10162 (residual-detection limit).
- ACTION: re-verify or drop the corpus "Derhab2020FlowConserv" item before citing it for flow conservation.
