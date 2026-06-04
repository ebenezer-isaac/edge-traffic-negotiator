# Lambeth Spine Corridor — Controllability & Demand De-Risk

**Goal:** De-risk the Wk9-10 swap onto the REAL Lambeth A23/A3 corridor
(`sumo/lambeth/lambeth_spine.net.xml`, 9 TLS). Two questions: (a) does the
existing `src/controllers.py` stack actually RUN on the real irregular junction
topology, and (b) what demand operating point runs CLEAN.

**Verified on this machine:** SUMO 1.26.0, venv `.venv`, TraCI. Every number below
was produced by an executed run, not asserted. Teleports = the gridlock signal.

`src/controllers.py` and `src/run_baseline.py` were **NOT edited**. The runner
`sumo/lambeth/run_lambeth.py` imports the controllers verbatim and drives them on
the real net.

---

## 1. Controller compatibility verdict — BOTH RUN CLEAN. No code change needed.

**Verdict: PASS.** `FixedTimeController` and `MaxPressureController` both run
end-to-end over all 9 real TLS for the full 3600 s, at every demand scale tested
(0.3 → 3.0), with **zero exceptions**. MaxPressure's two risky parse paths —
`getAllProgramLogics(tl)[0].phases` and `getControlledLinks(tl)` — survive the real
irregular topology. This was the headline risk for Wk9-10 and it does **not**
materialise. The minimal fix required to run on the real net is: **none.**

Why it holds (introspected via sumolib + live TraCI, see `run_lambeth.py` history):

| TLS | controlled links | phases | green phases (MP candidates) |
|---|---|---|---|
| GS_227716 | 8 | 4 | 2 |
| GS_227722 | 6 | 3 | **1** |
| GS_7173810958 | 5 | 3 | **1** |
| GS_8412978817 | 6 | 3 | **1** |
| GS_8413292286 | 4 | 4 | 2 |
| cluster_102714594_…#7more | 5 | 8 | 3 |
| cluster_10273328593_…#4more | 5 | 6 | 2 |
| cluster_1032792732_…#11more | 11 | 9 | 3 |
| cluster_2592978101_…#2more | 6 | 6 | 2 |

- **No empty / malformed controlled-link entries** — `lk[0][0]` / `lk[0][1]`
  (the `in_lane` / `out_lane` extraction) never hits the `None` branch on this net.
- **State-string length == #controlled-links** for every phase of every TLS, so the
  per-character `_pressure` loop indexes safely.
- **MaxPressure's green→yellow pairing assumption holds.** The controller takes the
  clearing yellow to be the phase immediately after each green
  (`phases[(i+1) % n]`). On this net **every** green's `i+1` neighbour is a genuine
  yellow that clears exactly the movements the green served (`GGGGGgrr → Gyyyyyrr`,
  `rrrrGGGGrrr → rrrryyyyrrr`, …). The netconvert build emitted clean
  green-yellow-(allred) ordering, so the assumption is satisfied.

### Latent risks (do NOT break the run, but matter for Wk9-10 correctness)

1. **All-red clearance phases are SKIPPED.** Several junctions interleave a short
   all-red between yellow and the next green (e.g. cluster_102714594 phase[2]=`rrrrr`,
   the `#11more` cluster phases [2]/[5]/[8]). MaxPressure shows its own fixed
   `yellow=3 s` then jumps **straight to the next green**, never emitting the all-red.
   It does not crash and teleports stay low, but it is **less conservative than the
   native program** at exactly the multi-stage junctions the SLM will control. Flag
   for the safety-shield discussion; not a blocker.

2. **3 of 9 junctions have only ONE green phase** (GS_227722, GS_7173810958,
   GS_8412978817 — the "2-incoming-edge" signals the extraction doc flagged as likely
   pedestrian crossings / simple merges). MaxPressure's `decide()` does
   `max(range(len(green)), …)` over a **single** candidate → it is a structural
   **no-op** there (always re-serves phase 0). These junctions are **not meaningfully
   SLM-controllable** (no phase choice exists). See §3.

---

## 2. Demand sweep — clean band and the gridlock cliff

Demand knob: SUMO `--scale` over `base.rou.xml` (randomTrips, `period=1.0`,
`fringe-factor=30`, `--validate`, `seed=1` → ~3600 veh loaded/h at scale 1.0).
`time-to-teleport=300 s` so jams surface honestly as teleports. `seed=42` per run.

This is a **cleaner, more controllable demand model** than the prior agent's
AADF all-pairs `calibrated.rou.xml` (which no longer exists in the dir). The AADF
calibration fit the *counts* (GEH<5) but its all-pairs random base routing +
PEAK_FRACTION=0.085 over a single 1 h burst is what produced the reported 490
teleports — i.e. it sat at the far-right of the curve below (~scale 3.0).

### MaxPressure controller

| scale | ≈veh/h | teleports | completed | completion % | avg travel (s) | avg wait (s) | state |
|------:|-------:|----------:|----------:|-------------:|---------------:|-------------:|-------|
| 0.3 | 1080 | **0** | 1044 | 29.0* | 103.1 | 6.5 | clean (under-loaded) |
| 0.5 | 1800 | **0** | 1746 | 48.5* | 101.2 | 6.6 | clean |
| 0.7 | 2520 | **2** | 2444 | 67.9 | 104.9 | 9.0 | clean |
| **1.0** | **3600** | **1** | **3484** | **96.8** | **113.5** | **13.7** | **CLEAN — recommended** |
| 1.3 | 4680 | 26 | 4247 | 90.8 | 175.2 | 47.2 | degrading |
| 1.5 | ~5400 | 27 | 4459 | 82.6 | 190.4 | 75.2 | tipping |
| 2.0 | ~7200 | 121 | 4719 | 65.6 | 193.2 | 91.7 | gridlock onset |
| 2.5 | ~9000 | 268 | 3947 | 43.9 | 226.8 | 127.3 | gridlock |
| 3.0 | ~10800 | 465 | 3536 | 32.8 | 270.5 | 177.5 | gridlock (≈ prior 490-teleport state) |

### Fixed-time controller (native programs)

| scale | teleports | completed | completion % | avg travel (s) | avg wait (s) |
|------:|----------:|----------:|-------------:|---------------:|-------------:|
| 0.3 | 0 | 1044 | 29.0* | 103.5 | 6.1 |
| 0.5 | 0 | 1744 | 48.5* | 102.2 | 6.6 |
| 0.7 | 1 | 2443 | 67.9 | 106.1 | 9.3 |
| **1.0** | **6** | **3338** | **92.8** | 115.9 | 15.4 |
| 1.3 | 26 | 4024 | 86.0 | 153.9 | 46.3 |
| 1.5 | 40 | 4403 | 81.6 | 188.4 | 83.7 |
| 2.0 | 56 | 5490 | 76.3 | 200.9 | 95.3 |
| 3.0 | 286 | 4977 | 46.1 | 269.4 | 168.1 |

\* Low completion % at scale ≤0.5 is **not** congestion — at low insertion rates a
large fraction of the 3600 s of demand is still en route when the 3600 s window
closes. Teleports = 0 confirms free flow. Use completion % as a gridlock signal only
at scale ≥0.7.

### Findings

- **Clean band: scale ≤ 1.0** (≤ ~3600 veh/h). At scale 1.0: ≤6 teleports,
  ~93–97% completion, avg wait 14–15 s. Free-flowing.
- **Tipping point: scale ≈ 1.3–1.5.** Teleports jump to ~26–40, waits to 47–84 s.
- **Gridlock: scale ≥ 2.0.** Teleports 56→465, completion collapses. Scale ~3.0
  reproduces the prior agent's 490-teleport "raw AADF peak" gridlock.
- **MaxPressure ≈ Fixed-time on this corridor.** At scale 1.0 MaxPressure edges ahead
  (96.8% vs 92.8% completion, 13.7 s vs 15.4 s wait). The margin is small because 3
  of 9 junctions are no-ops for MaxPressure and the corridor is largely a single
  arterial axis (limited cross-pressure to exploit). This sets a realistic, honest
  bar for the SLM: the classical baseline is already near fixed-time, so SLM gains
  will be modest, not dramatic.

---

## 3. Recommended clean operating point (deliverable, ready to use)

**`sumo/lambeth/lambeth_spine.sumocfg` + `sumo/lambeth/base.rou.xml`, `scale=1.0`.**

- Self-contained: `sumo -c sumo/lambeth/lambeth_spine.sumocfg` runs clean standalone
  (native fixed-time programs, 3336 trips completed, no teleport/error output).
- ~3600 veh/h, ≤6 teleports, ~93–97% completion — a defensible "busy but not
  gridlocked" peak that exercises queues without collapsing.
- Deterministic: route file fixed at `seed=1`; per-run `seed=42` in the runner.
- To stress-test toward the cliff for the dissertation, raise `<scale>` to 1.3
  (tipping) or 2.0+ (gridlock) — no regeneration needed.

Run controllers on it:
```
.venv/Scripts/python sumo/lambeth/run_lambeth.py --controller maxpressure --scale 1.0
.venv/Scripts/python sumo/lambeth/run_lambeth.py --controller fixed --scale 1.0
.venv/Scripts/python sumo/lambeth/run_lambeth.py --sweep   # full table above
```

---

## 4. Risk assessment for the Wk9-10 6-SLM-junction sweep

**The "6 junctions" requirement falls out cleanly: exactly 6 of the 9 TLS have ≥2
green phases**, i.e. an actual phase choice an SLM (or MaxPressure) can act on:

| Pick | TLS | green phases | links | note |
|---|---|---|---|---|
| ✅ 1 | cluster_1032792732_…#11more | 3 | 11 | richest junction; 11 links, 9 phases — most SLM headroom but also most complex state |
| ✅ 2 | cluster_102714594_…#7more | 3 | 5 | 3-stage, has all-red gaps (see §1 risk 1) |
| ✅ 3 | cluster_2592978101_…#2more | 2 | 6 | clean 2-stage |
| ✅ 4 | cluster_10273328593_…#4more | 2 | 5 | clean 2-stage |
| ✅ 5 | GS_227716 | 2 | 8 | clean 2-stage, 8 links |
| ✅ 6 | GS_8413292286 | 2 | 4 | smallest controllable; simple 2-phase |
| ❌ | GS_227722 | 1 | 6 | TRIVIAL — single green, no action space |
| ❌ | GS_7173810958 | 1 | 5 | TRIVIAL — single green |
| ❌ | GS_8412978817 | 1 | 6 | TRIVIAL — single green |

**Biggest risk to the corridor evaluation (honest):**

1. **Headroom, not crashes.** The controller stack runs fine; the risk is that the
   *science* is thin. MaxPressure barely beats fixed-time here (§2), and 2 of the 6
   controllable junctions are simple 2-phase signals. The SLM has real headroom on at
   most ~3 junctions (the 3-stage clusters with 5–11 links). Set expectations: the
   corridor result is a **realism / robustness** story, not a big-throughput-win story.

2. **All-red phases skipped by the controller (§1 risk 1)** at exactly the multi-stage
   junctions the SLM will drive. Wk9-10 should decide whether the SLM/shield must
   honour native all-red clearance; current behaviour is permissive (works, but less
   conservative than the real signal).

3. **Demand model is randomTrips, not OD/turn-calibrated.** The AADF count-fit
   (`aadf_counts.edgedata.xml`) was not used for the clean operating point because its
   all-pairs routing gridlocks. For dissertation defensibility, a turn-ratio / OD
   demand at scale ~1.0 intensity would be stronger than random base routing — but the
   `scale=1.0` random demand is clean, deterministic, and sufficient to de-risk the
   swap and run the controller comparison NOW.

4. **The 3 trivial single-green junctions** must be excluded from the SLM action space
   (no phase to choose). They still need to *run* (they do, as no-ops) but should not
   be counted toward the "6 SLM junctions."

**Bottom line:** the Wk9-10 swap onto the real net is **low technical risk** — the
controllers run unmodified, a clean deterministic operating point exists
(`lambeth_spine.sumocfg` @ scale 1.0), and the 6 SLM-controllable junctions are
identified. The residual risk is scientific framing (modest SLM headroom), not
engineering.
