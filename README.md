# Edge Traffic Negotiator

A small language model (SLM) proposes traffic-signal phases for London junctions. It runs entirely
on a 6 GB consumer GPU through [Foundry Local](https://learn.microsoft.com/azure/ai-foundry/foundry-local/).
A deterministic safety shield sits underneath it, and every decision is written to a signed,
hash-chained audit log. Everything here runs in the [SUMO](https://eclipse.dev/sumo/) traffic
simulator.

This is the code, data, results and write-up of an MSc dissertation (UCL, Systems Engineering for the
Internet of Things, 2026), developed through UCL's Industry Exchange Network with Microsoft.

## Quickstart

No GPU needed for the first run. Python 3.11–3.13; SUMO is installed from pip.

```bash
git clone https://github.com/ebenezer-isaac/edge-traffic-negotiator
cd edge-traffic-negotiator
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python run.py                   # MaxPressure on the Bloomsbury network, about 10 s
```

```
Running maxpressure on bloomsbury_calibrated (seed 1, 1200 s)...

  vehicles completed   601 / 686
  mean delay           158.0 s
  teleports (gridlock) 0
  audit entries        441  chain ok=True  signatures ok=True  merkle proof ok=True
```

**Add a language model.** Install [Foundry Local](https://learn.microsoft.com/azure/ai-foundry/foundry-local/get-started), then:

```bash
foundry model run phi-4-mini    # downloads ~3.7 GB the first time; Ctrl+C once it is loaded
python run.py --controller slm --model phi-4-mini
```

**Use the fine-tuned 0.6B model** from the dissertation: download it from the
[release](https://github.com/ebenezer-isaac/edge-traffic-negotiator/releases/tag/v1.0) and follow
[docs/MODELS.md](docs/MODELS.md). It is about 390 MB.

```bash
python run.py --controller slm --model qwen3-0.6b-ft1
```

Other networks: `--topology euston_peakhour_calibrated`, `oldstreet_junction`, `grid4x4` and more
(`python run.py --help`). Run the test suite with `pytest` (about 2 minutes, 819 tests).

## How it works

1. **The SLM proposes.** Every 10 simulated seconds each junction describes its queues to the model
   in a short text prompt and asks for the next green phase as JSON.
2. **The shield bounds it.** The model can only pick from conflict-free phases. A missing or malformed
   answer falls back to [MaxPressure](https://doi.org/10.1016/j.trc.2013.08.014), a classical
   adaptive controller, and an anti-starvation timer stops any approach waiting forever. The shield
   guarantees a legal, well-formed phase. It does not guarantee good performance: a valid but poor
   proposal is still served.
3. **The audit trail records it.** Each decision (state, model proposal, shield proposal, what was
   served, who authored it) is signed with the junction's Ed25519 key and hash-chained into a
   Merkle-verifiable log, so a run can be reconstructed afterwards.

## Results in brief

All results are from simulation. The dissertation ([thesis/](thesis/)) has the full analysis,
confidence intervals and limitations.

- On a London grid (Bloomsbury, from OpenStreetMap) with demand set so the network can clear, the
  fine-tuned Qwen3-0.6B cut mean delay by **18.3%** against the identically compiled stock model and
  won on all 30 seeds (one demand pattern, varied driver behaviour). Fine-tuned Qwen3-0.6B and
  Phi-4-mini both matched MaxPressure to within 0.03% and beat a fixed-time plan by 8.8%.
- The 0.6B and 3.8B students landed within ±0.38% of each other on that grid.
- On the Euston Road (A501) corridor the approach did not help. Stock models were 7–20% worse than
  fixed-time, and fine-tuning did not fix the average.
- Re-running Euston with **measured TfL hourly counts** (post-submission) showed a flat, all-day load.
  No SLM beat MaxPressure; the best matched it on median delay. See [realdemand/](realdemand/).

## Repository map

| Path | Contents |
|---|---|
| `run.py` | One-command entry point (any controller, any network) |
| `src/` | Controllers, shield, SLM client, audit log, experiments, analysis |
| `tests/` | pytest suite |
| `sumo/` | Networks and demand: Bloomsbury, Old Street, Euston Road, synthetic grids |
| `results/` | Every experiment's output, including raw per-run JSON (`frontier_raw/`) and the distillation dataset |
| `realdemand/` | The TfL SCOOT real-demand re-run |
| `training/` | Fine-tuning, int4 compile and Foundry Local registration scripts, with logs |
| `thesis/` | Dissertation LaTeX source, submitted PDF, and the fact-check harness that traces every number to a result file |
| `article/` | Short article version |
| `docs/` | Specification, glossary, models guide, experiment reports, project history |
| `research/` | Literature analysis and UK traffic-law notes |
| `media/` | Demo videos |

## Limitations

- Simulation only. No field trial, no hardware-in-the-loop test and no signal-safety certification.
- Turning proportions at junctions are modelled, not measured; TfL's SCOOT data does not record them.
- The audit layer produces a cited evidence pack for a crash inquiry. It is not a legal verdict.
- `results/frontier_raw/BASELINE__*.json` files are MaxPressure runs, not fixed-time; see
  `results/comparator_audit.json`.

## Licence

Code: MIT. Dissertation, article and documents: CC BY 4.0. Third-party data keeps its own licence
(OpenStreetMap ODbL, DfT Open Government Licence): see [NOTICE.md](NOTICE.md).

AI tools (Anthropic Claude) were used to help write code and documents in this project. All results
come from the simulation outputs in `results/`.
