# edge-negotiator — implementation

Implementation of **The Edge Negotiator**. The canonical specification (single source of truth) is [`specs/001-edge-negotiator/MASTER-SPEC.md`](../../specs/001-edge-negotiator/MASTER-SPEC.md); the project overview is the [top-level README](../../README.md).

The thesis: is an on-device Foundry-Local SLM traffic-signal controller that matches or beats the MaxPressure baseline on the real Euston Road (A501), while providing a cryptographically-provable tamper-evident accident audit, even possible, and at what model scale/config? Two coupled halves: **H1 performance** and **H2 trust**.

## Components

- **Controllers** (`src/controllers.py`) — MaxPressure (baseline + safety shield) and Fixed-time.
- **SLM controller** (`src/slm_agent.py`) — on-device phase choice (`choose_phase`) via Foundry Local; the H1 system-under-test. Model is an experimental variable.
- **Shielded loop** (`src/hybrid_controller.py`, `src/coordinated_controller.py`, `src/emergency_controller.py`) — the SLM proposes, the deterministic gate (Ed25519 auth + conservation/CUSUM + corroboration + anti-starvation) disposes.
- **Integrated system** (`src/system.py`) — orchestrates a run on the Euston substrate with the audit layer injected.
- **Provable audit (H2)** — signed hash-chained log (`src/audit_log.py`), permissioned identity/registry (`src/identity.py`, `src/registry.py`), post-incident origin classification + evidence-pack (`src/assessment.py`).
- **SLM legal-reasoning note (H2 support)** (`src/legal_corpus.py`, `src/slm_agent.py`) — CAG reason-then-classify over the policy base; measured negative, reported honestly.

## Substrate

Real Euston Road (A501) signalised stretch under `sumo/euston/` (`euston_spine.net.xml`, `euston.sumocfg`, DfT-AADF-calibrated `base.rou.xml`). The synthetic 2×2 grid is a unit-test fixture only.

## Setup

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```
Requires **SUMO 1.20+** with `SUMO_HOME` set, and **Microsoft Foundry Local** for the SLM (model cache kept on C: to keep weights off E:).

## Run

```bash
# full test suite (deterministic; SLM/SUMO-dependent tests skip when unavailable)
.venv/Scripts/python -m pytest tests/ -q

# H2 trust: Job-A SLM legal-reasoning eval (measured negative)
.venv/Scripts/python src/experiment_jobA.py

# emergency-preemption + audit demonstration
.venv/Scripts/python src/measure_emergency.py
.venv/Scripts/python src/run_attacks.py
```

The **H1 headline experiment** — the SLM controller (`slm_agent.choose_phase`) against the MaxPressure baseline (`controllers.py`) on the real Euston stretch — runs via `src/experiment_sweep.py` (the model × config feasibility map + scale threshold) and `src/experiment_traffic.py` (the single-config / config-arm harness). **Pilot result** (`results/experiment_sweep.md`, n=1/cell, descriptive per §8): on-device SLM control **beats** myopic MaxPressure on delay under saturation; the scale threshold is the smallest model (`qwen2.5-0.5b`) at the simplest config (myopic), −25% mean delay, audit live per cell, latency under the 10 s interval. `+coordination` is causally inert on this substrate (reported, not claimed as a gain); the reasoning model is latency-gated. The powered n≥30 inferential runs are honestly gated until time-resolved TfL demand (`src/experiment_powered_gate.py`). The H2 trust half runs via `src/experiment_accident.py` (D-accident: reconstruct + tamper-caught), `src/experiment_vehicle_auth.py` (multi-authorised-vehicle authorisation), and `src/experiment_anchor.py` (D-anchor salted-root ≥2-witness cross-audit, honestly labelled not-externally-anchored).

Every claim is settled only when its MASTER-SPEC §12 acceptance gate passes over a real run OR is honestly gated with a recorded reason; results are written under `results/`.
