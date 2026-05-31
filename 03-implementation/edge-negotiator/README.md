# edge-negotiator — implementation

Build for *The Edge Negotiator: Verified-Source Cross-Junction Coordination for SLM-Driven Traffic Signal Control*. See `../PROJECT-DECISION-BRIEF.md` for the locked design and `../../00-SCOPE-LOCKIN.md` for scope.

## Status (Wk 1-2 grid pipeline)

- ✅ 2×2 SUMO grid scenario (`sumo/`) — 4 signalised junctions (`A0,A1,B0,B1`), seeded random demand.
- ✅ Deterministic controllers (`src/controllers.py`) — **MaxPressure** (baseline + safety shield) and Fixed-time.
- ✅ End-to-end TraCI runner (`src/run_baseline.py`) — verified: MaxPressure beats fixed-time (lower waiting, higher throughput).
- ⏳ Next: SLM junction agent (Phi-4-mini via Foundry Local, terse `{"phase": N}` output) + hybrid SLM-proposes/shield-disposes loop.

## Setup

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # sumo-rl, web3, openai, foundry-local-sdk
```
Requires **SUMO 1.20+** with `SUMO_HOME` set, and **Microsoft Foundry Local** (for the SLM agent).

## Run the baselines

```bash
.venv/Scripts/python src/run_baseline.py --controller maxpressure
.venv/Scripts/python src/run_baseline.py --controller fixed --gui   # watch it
```

## Regenerate the scenario (deterministic, seed 42)

```bash
cd sumo/networks
netgenerate --grid --grid.number 2 --grid.length 200 --grid.attach-length 60 \
  --no-turnarounds --default.lanenumber 1 --tls.set A0,A1,B0,B1 -o grid2x2.net.xml
python "$SUMO_HOME/tools/randomTrips.py" -n grid2x2.net.xml -r grid2x2.rou.xml -e 1000 --period 1.0 --seed 42 --validate
```

## Layout

```
edge-negotiator/
├── sumo/
│   ├── grid2x2.sumocfg
│   └── networks/        grid2x2.net.xml, grid2x2.rou.xml
├── src/
│   ├── controllers.py   MaxPressure + FixedTime
│   └── run_baseline.py  TraCI runner + metrics (tripinfo)
└── requirements.txt
```

> Foundry Local model cache is on **C:** (`C:\Users\Ebenezer\.cache\foundry-local`) to keep large weights off the E: drive.
