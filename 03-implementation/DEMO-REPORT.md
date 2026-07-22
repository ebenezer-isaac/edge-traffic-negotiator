# Trust-Preserving Coordination: Measured Fixture-Demo Results & Analysis

**Date:** 2026-06-21 · **System:** The Edge Negotiator · **Substrate:** synthetic 4-junction SUMO corridor (J0-J1-J2-J3), a **unit-test fixture only** (the evaluation substrate is the real Euston Road (A501); the headline coupling measurement on Euston is not run here).
**Reproduce:** `./.venv/Scripts/python.exe src/measure_emergency.py` (raw output: `results/emergency_metrics.json`)

> Scope note: these are **fixture-demo** figures with a deterministic StubAgent and the deterministic gate. The measured emergency-vehicle effect is **preemption on vs off** — it is NOT a coordination result and NOT an SLM result (the SLM is the deterministic stub here). The single-seed numbers are point estimates; the powered n=30 figures are the defensible ones. Read §5 before quoting any number.

---

## Abstract

This report measures, on the synthetic fixture, the deterministic gate at the centre of the trust-preserving coordination layer: that enabling emergency preemption clears a real ambulance faster than no preemption layer, and that the corroboration gate keeps the layer safe when a junction is compromised. The preemption effect: across 30 paired seeds, enabling preemption clears a real ambulance **31 s faster** (95% CI [25.4, 36.5]) than MaxPressure with no emergency layer. This is preemption on vs off, **not** a coordination effect and **not** an SLM effect. The gate result: a corroboration gate blocks a signed-but-spoofed phantom emergency, reducing cross-street delay at the attacked junction by 45% vs a trust-everything victim (mean time-loss 8.95 s vs 16.12 s) with a worst-case 3.5x smaller (20.1 s vs 69.5 s). The gate costs ~11 s of ambulance time relative to blind trust, because it waits for physical corroboration before preempting. Network-aggregate delay is insensitive (~26 s in all three conditions), an important methodological caution: a targeted attack is invisible in the network average and must be measured on the targeted subset.

---

## 1. Objective

Answer four questions with measured numbers:
1. Does enabling emergency preemption clear a real ambulance faster than MaxPressure with no emergency layer? (a preemption-on-vs-off question, not a coordination or SLM question)
2. Does a spoofed emergency from an authenticated insider succeed if the coordination channel is compromised, and what damage does it do if believed?
3. Does the corroboration gate prevent that damage, keeping coordination robust to the compromise?
4. What does the gate cost?

## 2. Method

**Scenario.** The corridor carries platooned arterial traffic plus light cross-street demand at each junction (SUMO `--scale 1.0`, seed 42). Two scripted events:
- **Sustained spoof, t = 40–100 s:** a compromised-but-approved junction J1 re-emits a *signed* emergency claim to J2 every decision cadence, for a PHANTOM ambulance that does not exist. (Re-emitted, not one-shot, so a victim keeps preempting.)
- **Real ambulance, t = 120 s:** an emergency vehicle (`vClass=emergency`) is injected eastbound and traverses J0→J1→J2→J3.

**Conditions** (identical seed/traffic; only the controller policy differs, so any delta is attributable to policy):

| Condition | Emergency preemption | Trust policy | Represents |
|---|---|---|---|
| `nopreempt` | off | n/a | plain MaxPressure ("what happens with no emergency layer") |
| `defended` | on | requires corroboration | our system |
| `naive` | on | trusts any authenticated claim | the trust-everything victim |

**Measurement.** SUMO's own per-trip output (`tripinfo`), parsed independently of anything the controller reports. `timeLoss` = seconds lost vs free-flow travel (the standard SUMO delay measure). Cross-street vehicles at the attacked junction (`cross_ns2`/`cross_sn2`, n = 32) are the safety-critical subset; arterial (n = 134) and whole-network (n = 238) are reported for context.

## 3. Results

| Metric | `nopreempt` (MaxPressure only) | `defended` (gate) | `naive` (victim) |
|---|---|---|---|
| **Ambulance corridor duration (s)** | 141.0 | **133.0** | 122.0 |
| Ambulance time-loss (s) | 38.05 | 30.90 | 19.75 |
| Ambulance waiting time (s) | 11.0 | 0.0 | 0.0 |
| **Cross-street @J2 mean time-loss (s)** | 6.43 | **8.95** | 16.12 |
| Cross-street @J2 **max** time-loss (s) | 20.08 | **20.08** | 69.46 |
| Cross-street @J2 total time-loss (s) | 205.81 | 286.34 | 515.87 |
| Network mean time-loss (s) | 25.51 | 26.57 | 26.00 |
| Trips completed | 238 | 238 | 238 |

**Derived comparisons:**
- **Real-EV preemption benefit** (`nopreempt − defended`): −8.0 s duration (−5.7%), −7.15 s time-loss, −11 s waiting. Preemption helps the ambulance.
- **Attack harm on the victim** (`naive − defended`, cross-J2): +7.17 s mean time-loss per vehicle (+80%), worst case +49.4 s (69.5 vs 20.1 s), total +229.5 s. The gate avoids all of this.
- **Cost of the gate** (`defended − naive`, ambulance): +11.0 s. The gate is more conservative because it waits for corroboration before preempting.

### Powered replication (n = 30 paired seeds, 95% bootstrap CI)

The single-seed numbers above were replicated across 30 seeds (paired; `python src/measure_emergency.py --multi --seeds=30`, raw output `results/emergency_metrics_n30.txt`). Every effect's CI excludes zero:

| Effect (paired delta) | Mean (s) | 95% CI |
|---|---|---|
| EV preemption benefit (nopreempt − defended) | **31.1** | [25.4, 36.5] |
| Cost of the gate (defended − naive) | **8.0** | [3.7, 12.5] |
| Attack harm avoided, cross-J2 mean (naive − defended) | **4.63** | [3.25, 5.99] |
| Attack worst-case avoided, cross-J2 max (naive − defended) | **16.05** | [11.51, 20.44] |

Note the EV benefit is **much larger across seeds (31 s) than in the single seed reported above (8 s)**: seed 42 happened to be a low-congestion case where preemption barely helped. This is exactly why the powered run matters and why the single-seed figure must not be quoted alone.

## 4. What happens during the run, and why

**t = 40-100 s: the attack.** J1 signs phantom claims to J2.
- In `defended`, J2 authenticates each (valid signature, approved member) but finds no independent sighting and senses no vehicle, so **preemption is withheld** every time; J2 keeps running MaxPressure. Its cross street is unaffected by the attack (cross-J2 numbers match `nopreempt` exactly in this window; max 20.08 s in both).
- In `naive`, J2 trusts the signed claim and **preempts the arterial repeatedly**, starving the N2/S2 cross street. The result is the measured damage: mean cross-J2 time-loss rises from 8.95 s to 16.12 s and one cross vehicle loses **69.5 s** (vs a 20.1 s worst case when defended). *Why:* the spoof holds the arterial green while cross vehicles accumulate; with no corroboration check there is nothing to stop it.

**t = 120 s onward: the real ambulance.** It is sensed locally at each junction as it arrives (J0 ≈ 141 s, J1 ≈ 161 s, J2 ≈ 184 s, J3 ≈ 213 s in the GUI trace) and preempted. Downstream junctions also receive advance claims; in `defended` they act on them only once corroborated (an upstream junction genuinely saw the vehicle), in `naive` they act immediately.
- `defended` clears the ambulance in 133 s vs 141 s for `nopreempt` (preemption works).
- `naive` clears it faster still (122 s) *because* it preempts on the advance claim without waiting for corroboration. **This is the central tradeoff:** the same trust that lets the spoof through also shaves latency off a genuine claim. The gate trades ~11 s of ambulance time for immunity to the spoof.

### What went right
- Enabling preemption **clears the ambulance** (−5.7% corridor time, −11 s waiting vs no preemption; −31 s in the powered run). This is a preemption effect, not a coordination or SLM effect.
- The gate property holds: the spoof is **refused**, and protection is quantified, not asserted (cross-J2 mean delay 45% lower than the victim, worst case 3.5x smaller).
- The defence is **automatic** and needs no knowledge of intent: it withholds on any uncorroborated claim, phantom or merely unconfirmed.

### What went wrong / was weaker than hoped
- **The single-seed EV benefit is small (8 s).** The corridor at scale 1.0 is under-saturated, so even without preemption the ambulance is rarely blocked. The powered run (31 s mean benefit) better represents the effect; seed 42 was a low-congestion outlier. Preemption matters most under congestion, which this single seed does not exercise.
- **The gate costs EV latency (133 vs 122 s).** Requiring corroboration delays preemption at each junction until the vehicle is physically confirmed. This is a real, measured cost of the robustness policy, not a free lunch.
- **Network-aggregate delay barely moves** (25.5-26.6 s across all three). A targeted attack that doubles delay on one cross street is **invisible** in the network mean. Reporting only aggregate metrics would have hidden the entire result.

### Why these outcomes
The gate's behaviour follows directly from `_admissible_ev`: local sensing is trusted, an advance claim needs corroboration. That single rule produces both the win (spoof blocked) and the cost (slower genuine preemption), because it cannot tell a phantom from an unconfirmed-but-real claim. By design it requires evidence, not intent.

## 5. Limitations and threats to validity

1. **Single seed, single run per condition.** These are point estimates with no confidence intervals. Differences of ~1 s (e.g. the network aggregate) are within run-to-run noise and must not be over-read.
2. **Under-saturated regime.** scale 1.0 keeps the corridor free-flowing, suppressing both the EV benefit and the network-level visibility of the attack. A saturated sweep is needed to size the effects where they matter.
3. **Conflated policy axes.** `naive` differs from `defended` in *two* ways (no corroboration AND immediate advance-claim preemption), so the "naive faster EV" result mixes the gate's cost with the advance-claim policy. A clean ablation would vary one axis at a time.
4. **Stub agent.** The SLM is the deterministic stub; admissibility is decided by the deterministic shield, so the corroboration result is identical with Phi-4-mini, but SLM determinism on the real prompts is not exercised here.
5. **Localised metric choice.** We pre-selected the J2 cross street as the attack target; in a blind evaluation the attacked location must be identified from the attack spec, not chosen post-hoc.

## 6. How to improve (and why)

| Improvement | How | Why |
|---|---|---|
| Statistical power | Run n = 30 paired seeds; report BCa confidence intervals + paired permutation p-values (the existing stats stack) | Turn point estimates into defensible claims; a 7 s mean delta needs a CI to mean anything |
| Free-deviation boundary | Sweep the deviation magnitude (claim size as multiples of the tolerance band) and plot recall/latency vs magnitude; on Euston, measure the phase-coupled coverage threshold | Map which stealthy conservation-consistent deviations escape (the measured characterisation, not a single attack, and not a detection ROC) |
| Stronger regime | Repeat under a saturated demand sweep (scale 0.3→3.0) | Where the EV benefit and attack harm are large and network-visible |
| Isolate the tradeoff | Add a 4th condition: corroboration-gated but advance-claim-preempting | Separate the gate's EV-latency cost from the advance-claim policy |
| Real SLM | Re-run with Phi-4-mini on Foundry Local; measure temp-0 agreement | Validate determinism on the longer emergency prompts |
| Worst-case safety | Report the *distribution* of cross-street worst-case delay across seeds, not just the mean | The 69 s spike is the safety-critical number; the mean understates tail risk |

## 7. Conclusion

On the fixture, enabling emergency preemption clears a real ambulance faster than MaxPressure with no emergency layer: 31 s mean benefit across 30 seeds (95% CI [25.4, 36.5]). This is a preemption-on-vs-off effect only; it is not attributable to coordination (the coordination term is an inert structural zero) and not to the SLM (the deterministic stub decides admissibility here, so the result is identical with Phi-4-mini).

The gate result is the point of the demo: the corroboration gate refuses a signed-but-spoofed sustained preemption that would otherwise nearly double the attacked cross street's delay (69 s worst-case vs 20 s when defended), while a genuine corroborated preemption still clears. The gate costs ~11 s of ambulance time relative to blind trust, a real and measured tradeoff. Both effects are localised and invisible in the network aggregate. This fixture demo exercises the mechanism; it is not the dissertation's headline. The headline is the measured characterisation of the free-deviation boundary and the self-referential coupling on the real Euston Road (A501) corridor, and the SLM's self-contained citation-faithful contribution, neither of which is run here.
