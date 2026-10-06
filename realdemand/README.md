# Real-demand check: Euston Road with measured TfL counts

The dissertation's Euston Road (A501) runs used real DfT traffic volumes but an **assumed** hourly
shape (8.5% of daily traffic in the busiest hour). After submission, Transport for London released
hourly SCOOT vehicle counts for the corridor in response to an information request, handled under the
Environmental Information Regulations (TfL ref. 1453-2627):
three ordinary weekdays, 12–14 May 2026 (Tuesday to Thursday).

This folder re-runs the controller comparison with that measured hourly profile.

## What the data shows

- The corridor is flat across the day, not peaked. The busiest hour carries about 5.0% of daily
  flow, and the peak-to-mean hourly ratio is 1.21. From 07:00 to 19:00 the three on-corridor
  detectors sit between about 3,800 and 4,200 vehicles per hour combined.
- The measurement period overlaps HS2 construction at the corridor's western end (Hampstead Road
  closures, May–June 2026), which may contribute to the flat profile.

## What the experiment shows

72 scenarios per controller (24 hours × 3 days, each simulated for 1,200 s at that hour's measured
demand). All numbers below are compared with MaxPressure in the same hour.

| Controller | Median delay vs MaxPressure | Mean delay vs MaxPressure | Teleports (MaxPressure: 121) |
|---|---|---|---|
| Phi-4-mini, stock | +0.00% | +0.10% | 157 |
| Phi-4-mini, fine-tuned | +0.01% | +6.72% | 221 |
| Qwen3-0.6B, fine-tuned v2 generalist (sweep arm `qwen3-0.6b-ft1`) | +1.57% | +5.05% | 186 |
| Qwen3-0.6B, fine-tuned v1 sota model, the dissertation's headline student (sweep arm `qwen3-0.6b-ft2`) | +0.74% | +8.56% | 296 |

The two Qwen arm names in the results file are swapped relative to the dissertation's naming:
the October rebuild registered the v2 generalist as `ft1` and the v1 model as `ft2`. Hashes and a
held-out check confirm this (see `docs/MODELS.md`). The table labels the rows by training run.

No SLM beat MaxPressure on this corridor. Stock Phi-4-mini came closest: its delay was identical to
MaxPressure's in 29 of 72 hours, and it completed about as many vehicles, but it still had more
teleports (vehicles SUMO removes from a jam). Every fine-tuned model completed fewer vehicles than
MaxPressure (11–14 fewer per hour on average, out of about 441).

### Against a fixed-time plan

`run_scoot_fixedtime.py` re-runs the same 72 demand files under SUMO's default fixed-time signal
programs for the network. These are not TfL's real signal plans. Before running, it reproduces
three MaxPressure cells exactly, which confirms the demand files match the sweep.

| Controller | Median change in delay vs fixed-time | Hours better than fixed-time (of 72) |
|---|---|---|
| MaxPressure | +8.0% | 8 |
| Phi-4-mini, stock | +7.6% | 8 |
| Phi-4-mini, fine-tuned | +9.0% | 8 |
| Qwen3-0.6B v1 (headline student; sweep arm `ft2`) | +10.3% | 8 |
| Qwen3-0.6B v2 generalist (sweep arm `ft1`) | +12.1% | 6 |

On this corridor the fixed-time plan beat every adaptive controller, MaxPressure included. It
also completed the most vehicles: 454.7 per run, against 440.6 for MaxPressure.

## Limits

- Simulation only (SUMO).
- SCOOT records how many vehicles pass each detector, not where they turn, so turning proportions
  and the direction split are still modelled.
- Only the three detectors on the modelled spine anchor the profile.

## Files

| File | What it is |
|---|---|
| `run_scoot_sweep.py` | The sweep driver. Resumable; writes after every cell. |
| `scoot_analysis.py` | Turns the raw SCOOT CSV into `results/corridor_profile.json`. |
| `results/corridor_profile.json` | The measured 24-hour corridor profile (derived aggregate). |
| `results/scoot_sweep_v2.json` | All 360 cells (5 controllers × 72). |
| `logs/` | Run logs from the sweep. |

## Re-running

The raw TfL CSV is not redistributed. You can request the same data from TfL (ref. 1453-2627), or use the derived profile.

```bash
# MaxPressure baseline for all 72 cells
SCOOT_CSV="/path/to/1453-2627 Scoot Data.csv" SWEEP_REFSCALE=0.80 python realdemand/run_scoot_sweep.py
# add an SLM arm (Foundry Local running, model loaded)
SCOOT_CSV=... SWEEP_REFSCALE=0.80 python realdemand/run_scoot_sweep.py --slm qwen3-0.6b-ft1
```

Recompute the table above from the results file:

```bash
python realdemand/summarise.py
```
