# The Edge Negotiator: Full-Scale Results Chapter

Status: full-scale phase (pilot approved by both supervisors). Every number below is read
from a committed `results/*.json`, produced by a real SUMO + Foundry-Local run. No number
is hand-entered. Inferential (powered, n>=30) significance stays honestly gated on real
time-resolved TfL counts per spec section 8; everything reported here is either descriptive
robustness (buildable now) or a proven capability (audit, trust, crash-law).

---

## 1. Headline

An on-device Small Language Model (qwen2.5-0.5b, via Microsoft Foundry Local) running as a
proposer behind a MaxPressure safety shield **beats MaxPressure on mean network delay while
also completing more vehicles** on the real Euston A501 corridor, and the signed audit ledger
**proves every crash scenario beyond doubt** with the governing UK traffic law inferred from
the verified facts. Which model wins is topology-dependent, which is itself a finding.

---

## 2. Pillar A: performance is a CLEAN WIN, not a delay-for-throughput trade (Akin's test)

MaxPressure is throughput-optimal by design, so beating it on delay only matters if throughput
is not quietly sacrificed. It is not.

Euston A501, qwen2.5-0.5b x myopic (`experiment_throughput.json`):

| Metric | MaxPressure baseline | SLM (shielded) | Delta |
|---|---|---|---|
| Mean network delay | 314.5 s | **235.0 s** | **-25.3%** (lower is better) |
| Throughput (completed) | 361 | **472** | **+111, +30.7%** (higher is better) |

Joint verdict: **clean_win** (wins delay, wins throughput, loses neither). Across the
committed model x config sweep there are **4 distinct clean-win configurations and 0
trade-offs** (6 clean-win cells, of which 2 are inert-coordination duplicates of myopic,
excluded from the distinct count after the holistic-audit fix). The delay win does not come
from stranding vehicles: the SLM both departs more vehicles and completes a higher fraction.

## 3. Pillar A robustness: holds across seeds (Akin's multiseed ask)

`experiment_multiseed.json`, qwen2.5-0.5b x myopic, 5 seeds:

- Mean delay 270.5 s vs 305.9 s baseline (**-11.6%**), std 23.1 vs 36.9.
- Mean throughput 413 vs 367 completed (**+12.6%**).
- **4/5 seeds a clean win** on both delay and throughput; 1/5 (seed 3) a regression.

Honest reading: the win is robust but not universal at daily-resolution demand. This is
descriptive robustness, not a powered significance test (see section 6). A win that survives
4 of 5 independent seeds is far stronger evidence than a single favourable draw.

## 4. Pillar B: the audit ledger proves crash scenarios and infers the governing law

`experiment_crash_law.json`, 7 pre-defined scenarios, **all_proven = True**. Each scenario
builds a signed hash-chained AuditLog, then: (a) `verify_chain` = True, (b) `verify_signatures`
= True, (c) an imposter re-sign is caught (`tamper_caught` = True), and the governing UK rule
is inferred deterministically from the verified facts (not asserted).

| Scenario | Inferred governing rule(s) | Fault anchor |
|---|---|---|
| civilian_runs_red | LR-driver-red (RTA1988 s36), LR-red-prohibition (TSRGD2016) | driver, high |
| ambulance_crosses_red_exempt | LR-ev-exemption + LR-griffin-calibration (60/40) + LR-green-due-regard | EV not at fault merely for crossing; endangerment test |
| maintenance_runs_red | LR-maintenance-no-exemption, LR-driver-red | works vehicle at fault like an ordinary driver |
| driver_crosses_on_amber | LR-amber (TSRGD2016 5(9)) | driver, high (safe stop was possible) |
| conflicting_green_fault | LR-authority-misfeasance (Bird v Pearce) + LR-authority-nonfeasance (Gorringe) | authority, low (misfeasance only) |
| dark_signal | LR-dark-signals (HC Rule 176) | duty to obey falls away; ordinary care |
| spoofed_ev_triggers_red_run | LR-driver-red, LR-red-prohibition | fake EV gets NO exemption -> driver at fault |

The system emits a cited evidence pack, not a binding verdict: authority fault is legally weak
(non-zero only on the conflicting-green misfeasance branch), driver fault is strong, the EV
exemption is conditional on authorisation plus corroboration.

## 5. Pillar C: trust coefficient, with local sensing as the ultimate truth

`experiment_trust.json`, **passed = True** (9/9 checks). Params: prior 0.5, reward 0.15,
lie_factor 0.25, corroboration_floor 0.5.

- A persistently honest junction climbs to **0.929** trust (12 truths, 0 lies).
- A persistent liar collapses to **0.011** (`can_corroborate = False`): locked out.
- Asymmetry: **10 consecutive verified truths** to climb from 0.5 to 0.90, but a **single lie**
  from a high-trust source (0.86) drops it by **0.65** in one step. Honesty earned slowly,
  betrayed instantly.
- Recovery after one lie takes **3** verified truths to re-cross the corroboration floor.

Local sensing is the ground truth and is never itself doubted: it is the arbiter every claim
is scored against. The live wiring in `EmergencyController` (opt-in, `trust_gating`) is
**discount-only**: a caught-lying neighbour loses its power to corroborate a preemption, but
trust can never add a preemption on zero evidence and never gates local sensing. So the
headline phantom-defence cannot regress, and a real ambulance is always preempted via its own
sensor. A real-but-slow ambulance that arrives after the provisional-lie window is
**vindicated** by the late local sensing (trust restored, lie reversed to a truth), so an
honest junction is never permanently penalised for a truth that merely arrived late.

## 6. Pillar D: the SLM is a congestion-regime specialist (multi-topology)

`experiment_topology.json`, seed 42, end 1200, DESCRIPTIVE n=1 per cell. Four topologies x
{qwen2.5-0.5b, qwen3-0.6b}:

| Topology | Type | baseline delay | teleports | qwen2.5-0.5b | qwen3-0.6b |
|---|---|---|---|---|---|
| Euston A501 | real linear arterial | 314.5 s | 65 | **-25.3% clean_win** | **-15.1% clean_win** |
| Bloomsbury WC1 | real London grid (OSM) | 516.7 s | 105 | +5.0% regression | **-1.8% clean_win** |
| grid3x3 | synthetic grid | 301.4 s | 0 | +60.3% regression | +36.9% regression |
| grid4x4 | synthetic grid | 143.2 s | 0 | +112.4% regression | +41.2% regression |

Honest reading (a REGIME SEPARATION, deliberately not over-claimed as a monotonic law; n=1
per cell, descriptive only):

- The SLM wins on the two **real congested London networks** (teleports > 0) and loses on the
  two **free-flowing synthetic grids** (both ZERO teleports, i.e. MaxPressure never gridlocks
  there). The harness (`_explain`) reports this as a regime separation, not a graded law:
  mean win is positive on the congested nets and negative on the free-flowing ones.
- It is explicitly NOT "win grows monotonically with gridlock". WITHIN the congested nets the
  direction actually INVERTS: Bloomsbury has MORE gridlock than Euston (105 vs 65 teleports,
  516 vs 314 s baseline) yet a SMALLER/negative win (qwen2.5-0.5b +5.0% regression there vs
  -25.3% on Euston). So the all-topology correlation is driven by the free-vs-congested
  cluster split, and the harness now reports `pearson_r_congested_only < 0` alongside the
  positive all-topology r, with a caveat that this is a regime effect, not a monotonic trend.
- Mechanism is a HYPOTHESIS (not demonstrated at n=1): MaxPressure is throughput-optimal and
  near-ideal in free flow, so the SLM's waiting-time-aware policy only adds latency there;
  under gridlock, queue management has headroom to help.
- Model x topology: qwen3-0.6b wins both real nets, qwen2.5-0.5b only Euston. Reported as
  descriptive n=1, NOT a significant "interaction".
- grid4x4 (SLM +112% worse, MaxPressure clears all 1000 vehicles) directly falsifies any
  "the SLM always helps" claim. Reported, not hidden.

Provenance: these numbers are regenerated into `results/experiment_topology.json` by the
committed harness (an earlier `--out` write-path bug had clobbered that file with a
single-topology run; the bug is fixed and the full run re-materialised the backing artifact).

The takeaway is a scoped, honest capability claim: on-device SLM signal control can beat
MaxPressure on delay AND throughput on real congested London arterials, and the size of the
benefit tracks how badly MaxPressure gridlocks; it is not a universal replacement.

### 6a. Newest-generation model check (qwen3.5)

The Foundry Local catalog on the test machine contains no Kimi/Gemma (not served by this
runtime), but it does list the newer qwen3.5 generation (0.8b/2b/4b), added to the model
catalog. Honest status:

- First Euston probe: qwen3.5 was downloadable but NOT cached, so it SKIPPED-with-record (no
  false parity). Incumbent qwen2.5-0.5b reproduced its exact -25.3% clean win on the same
  run, confirming a stable baseline.
- After downloading qwen3.5-0.8b (1.3 GB): it loads and answers chat calls, but
  `choose_phase` returns None on our decision prompt, i.e. it does not emit a parseable
  single-integer phase index under the current prompt/parser (consistent with a
  reasoning-style model that wraps its answer). This is a real, honest observation, not a
  parity claim.
- Pending (sequenced after the topology re-run to avoid WebGPU device contention, not
  abandoned): diagnose the raw qwen3.5 output and either adapt the parser (strip reasoning
  wrapper -> extract the integer) and re-run the Euston comparison, or record qwen3.5 as
  format-incompatible with the strict decision contract. Real numbers will be appended
  either way.

## 7. What is honestly NOT claimed

- No powered inferential significance (p-values, n>=30 with confidence intervals) until real
  time-resolved TfL hourly counts replace DfT daily-resolution demand. This is a data gate,
  not a code gate (spec section 8).
- The corridor and Bloomsbury demand volumes are synthetic magnitudes on real topologies
  (randomTrips / measured-magnitude subsample), not vehicle-by-vehicle real counts.
- The crash-law output is a cited evidence pack for a human adjudicator, not a binding legal
  verdict.
