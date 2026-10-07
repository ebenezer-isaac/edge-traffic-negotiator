# Real-demand check: Euston Road with measured TfL counts

The dissertation's Euston Road (A501) peak-hour runs were scaled to the busiest hour of a one-day DfT
manual survey (2,461 vehicles at 18:00, about 6.3% of the road's published annual average daily flow), with no measured
24-hour shape. (An earlier daily-demand model had assumed 8.5% of daily traffic in the busiest
hour.) After submission, Transport for London released
hourly SCOOT vehicle counts for the corridor in response to an information request, handled under the
Environmental Information Regulations (TfL ref. 1453-2627):
three ordinary weekdays, 12–14 May 2026 (Tuesday to Thursday).

This folder re-runs the controller comparison with that measured hourly profile.

## What the data shows

- The corridor is flat across the day, not peaked. The busiest hour carries about 5.0% of daily
  flow, and the peak-to-mean hourly ratio is 1.21. From 07:00 to 19:00 the three on-corridor
  SCOOT sites sit between about 3,800 and 4,200 vehicles per hour combined.

## How the scenarios are built

The measured hourly shape is kept, and its size is anchored to the dissertation's corridor model:
the busiest hour of the three-day average (06:00) is set to 80% of the peak-hour model's demand
(the "lightened" Euston version, where traffic can clear), and every other hour scales in
proportion (`frac` in each cell; single-day hours can run slightly above 0.80). Each of the 72
hours (24 × 3 days) is simulated once (seed 1) for 1,200 s per controller. The baseline arm is
SUMO's default program for the network. On this corridor SUMO generated **vehicle-actuated**
programs (greens stretched between 5 and 50 s while vehicles keep arriving), not a fixed timetable;
the dissertation called this baseline fixed-time, which is wrong for Euston. A true fixed-time arm
(`run_scoot_fixedtime_static.py`: the same programs switched to static, identical phases and
durations) is reported alongside it.

## Results (delay-aware prompt)

`run_scoot_sweep_sota.py` serves every model the delay-aware ("sota") prompt that the headline
student was trained on. Recompute this table with `python realdemand/summarise_sota.py`.

| Controller | Mean delay | Median vs SUMO default | Hours with less delay than SUMO default | Median vs MaxPressure | Teleports (sum) |
|---|---|---|---|---|---|
| SUMO default (vehicle-actuated) | 98.8 s | — | — | −7.4% | 157 |
| Fixed timetable (same programs, static) | 96.4 s | +9.1% | 13 | −1.9% | 17 |
| MaxPressure | 110.6 s | +8.0% | 8 | — | 121 |
| Qwen3-0.6B fine-tuned, v1 (headline student) | 113.9 s | +9.9% | 6 | +1.1% | 236 |
| Qwen3-0.6B fine-tuned, v2 (generalist) | 113.3 s | +8.7% | 6 | +1.0% | 252 |
| Phi-4-mini fine-tuned | 113.3 s | +9.8% | 6 | +0.8% | 232 |
| Phi-4-mini stock | 120.5 s | +12.0% | 7 | +3.5% | 276 |
| Claude Sonnet 5.5 (cloud reference, same loop) | 103.9 s | +9.3% | 6 | +0.8% | 115 |
| Claude Haiku 4.5 (stopped at 33 of 72 hours) | 104.3 s | +10.2% | 5 of 33 | +1.4% | 61 |

- The actuated SUMO default came out ahead of MaxPressure in 64 of 72 hours; in each of the other
  eight its own run had vehicles removed from gridlock (four of them 20 or more). The static fixed
  timetable lost to the actuated default in 59 of 72 hours but never jammed, giving the lowest
  72-hour mean; the adaptive controllers beat it in only 23 to 29 hours.
- Every cell uses the same seed and nested demand subsampling, so hours with near-identical demand
  often give identical runs (59 distinct default-plan results in 72 hours).
- The fine-tuned models behave as near copies of MaxPressure: the fairness timer (anti-starvation)
  serves about 43% of decisions, and when the model's own choice is served it differs from
  MaxPressure's only 4–5% of the time. Their mean gap to MaxPressure comes from the few hours in
  which they jammed.
- Claude Sonnet 5.5 was run once per hour through the identical loop (same prompt, shield and
  timer) using the Claude Code CLI (`run_scoot_sweep_claude.py`). In the 66 hours where neither it
  nor the v1 student jammed, the two were almost identical (98.2 s vs 99.7 s); its lower mean comes
  from avoiding three of the student's six jams (20 or more vehicles removed). Jam onset is
  sensitive to small differences and each hour ran once, so that may be chance. Every reply is in
  `results/claude_replies.zip`. Claude runs are not deterministic.

The local Foundry cache used for these runs had the two Qwen students' names swapped (`model_id`
"qwen3-0.6b-ft2" in `scoot_sweep_sota.json` is v1). The arm labels (`sota:qwen3-0.6b-v1/-v2`) are by
training run and were checked by md5 against the released v1 build. With the released names, the
script defaults (`QWEN_V1_ID=qwen3-0.6b-ft1`, `QWEN_V2_ID=qwen3-0.6b-ft2`) are correct.

### Prompt styles with neighbour notes and predictions (pilot)

On six hard hours (`run_config_pilot.py`, `null_config_control.py`): with the coordination prompt,
Claude Sonnet 5.5's results were identical to the same controller with no model at all; with the
prediction prompt, the models added at most a few seconds either way. Over all 72 hours the
no-model prediction controller averaged 105.9 s (median −0.3% vs MaxPressure) and the no-model
coordination controller 110.3 s. `run_downstream_pilot.py` adds exit-lane queues to the prompt on
the same six hours; results were mixed.

## First run (basic prompt, superseded)

`scoot_sweep_v2.json` / `run_scoot_sweep.py` was the first real-demand sweep. Its MaxPressure arm
is the reference used everywhere above, but its model arms were accidentally served the basic
queue-only prompt, which the headline student was never trained on. They are kept for the record.
In that run the two Qwen arm names are swapped relative to the dissertation (`qwen3-0.6b-ft1` = v2,
`qwen3-0.6b-ft2` = v1; see `docs/MODELS.md`). The SUMO-default arm (`run_scoot_fixedtime.py`,
`scoot_fixedtime.json`; vehicle-actuated on this network) re-runs the same 72 demand files and reproduces MaxPressure cells exactly
before starting.

## Limits

- Simulation only (SUMO); one seed per hour; the baselines are SUMO's default (actuated) programs and a static copy of them, not plans tuned for the site.
- SCOOT records how many vehicles pass each detector, not where they turn, so turning proportions
  and the direction split are still modelled, and the overall volume is anchored to the model.
- Only the three SCOOT sites on the modelled spine anchor the profile.

## Files

| File | What it is |
|---|---|
| `scoot_analysis.py` | Pass over the raw SCOOT CSV. Its per-detector output `scoot_summary.json` is git-ignored and must not be published; `results/corridor_profile.json` holds only the three-site aggregates. |
| `run_scoot_sweep.py` | First sweep driver (MaxPressure + basic-prompt model arms). |
| `run_scoot_fixedtime.py` | SUMO-default (vehicle-actuated) arm on the same demand files. |
| `run_scoot_fixedtime_static.py` | True fixed-time arm: the same programs converted to static. |
| `run_scoot_sweep_sota.py` | Corrected model arms with the delay-aware prompt (Foundry Local). |
| `run_scoot_sweep_claude.py` | Claude reference arms via the Claude Code CLI (`CLAUDE_ARM_MODEL`). |
| `run_config_pilot.py`, `null_config_control.py` | Coordination / prediction pilot and its no-model control (`--all` for 72 hours). |
| `run_downstream_pilot.py` | Exit-lane-queue prompt pilot. |
| `summarise.py`, `summarise_sota.py` | Recompute the tables. |
| `results/` | All result files, `corridor_profile.json` and `claude_replies.zip`. |
| `logs/` | Run logs. |

## Re-running

The raw TfL CSV is not redistributed. You can request the same data from TfL (ref. 1453-2627), or
reuse the demand fractions stored in `results/scoot_sweep_v2.json` (every script above regenerates
the route files from those with the same seed and checks two MaxPressure cells reproduce exactly).

```bash
# corrected model arms (Foundry Local running; released model names)
python realdemand/run_scoot_sweep_sota.py
# Claude reference arm (Claude Code CLI installed and signed in; on Windows set CLAUDE_BIN to claude.exe)
CLAUDE_ARM_MODEL=claude-sonnet-5-5 python realdemand/run_scoot_sweep_claude.py
# tables
python realdemand/summarise_sota.py
```
