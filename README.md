# The Edge Negotiator

An on-device Small Language Model (Microsoft Foundry Local) traffic-signal controller for the real Euston Road (A501) corridor in central London, studied against the MaxPressure baseline, while providing a cryptographically-provable, tamper-evident audit of what and how happened during an accident. The thesis question: **is such a controller even possible, and at what model scale and configuration does it become possible?** It is an exploratory feasibility and scale-threshold study; limitations are explicitly allowed, and a negative or a scale-threshold is a valid result.

The single source of truth for direction, scope, and framing is [`specs/001-edge-negotiator/MASTER-SPEC.md`](specs/001-edge-negotiator/MASTER-SPEC.md). A claim is not settled until its acceptance gate (MASTER-SPEC §12) passes over a real run.

## The two coupled halves

- **H1 — performance.** Can an on-device SLM controller (`choose_phase`) match or beat MaxPressure on delay, throughput, and per-decision latency on the real Euston stretch? The model is an experimental variable across the Foundry Local on-device catalog {phi-4-mini, phi-4-mini-reasoning, qwen2.5-0.5b, qwen2.5-1.5b}, on-device only, no cloud. The deliverable is a feasibility map over model x configuration {myopic, +coordination, +prediction} plus a scale threshold. This headline traffic comparison is the next run and is NOT yet executed; no number for it may be quoted.
- **H2 — trust.** Is every decision provably auditable, so an accident is mechanically reconstructable? A signed, hash-chained AuditLog + Merkle commitment + quorum external anchor (≥2 witnesses) + named cross-auditor + a deterministic origin classification + an evidence-pack-not-verdict forensic channel let an investigator reconstruct, from cryptographically-verified records alone, what happened, how, and which signing key drove each decision. The accountability mechanism is Certificate-Transparency-style and credited to prior art, not claimed novel. The audit's measured blind spot (the self-referential coupling, MASTER-SPEC §4.5) and the SLM legal-reasoning note's measured negative on Job A are reported honestly.

## Repository layout

- **`03-implementation/edge-negotiator/`** — the system and its experiments: `src/` (controllers, message bus, audit log, assessment, SLM agent, experiment runners), `tests/`, `sumo/` (the corridor nets), `fixtures/` (hash-pinned test fixtures), `results/` (measured outputs), `ground_rules.yaml` and `anchor.md` (hash-pinned prerequisite artifacts).
- **`03-implementation/`** (top level) — the reference docs: [`FORMAL-SPECIFICATION.md`](03-implementation/FORMAL-SPECIFICATION.md) (every parameter, equation, metric, and statistical method), [`GROUND-RULES-POLICY.md`](03-implementation/GROUND-RULES-POLICY.md) (the numbered decision policy base both the rule engine and the SLM reason against), and [`GLOSSARY.md`](03-implementation/GLOSSARY.md) (plain-language translations).
- **`specs/001-edge-negotiator/`** — [`MASTER-SPEC.md`](specs/001-edge-negotiator/MASTER-SPEC.md) (the SSOT, including the §10 hash-pin registry and the §12 acceptance gates), [`spec.md`](specs/001-edge-negotiator/spec.md) (the stakeholder WHAT and WHY), and `_hardening-log.md` (the forward build log).
- **`01-research/uk-traffic-law.md`** — the cited UK-law knowledge base that grounds the fault rules and the legal framing.

## Running the tests and experiments

From `03-implementation/edge-negotiator/`, with SUMO and `SUMO_HOME` configured and a Python virtual environment:

```
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # POSIX: .venv/bin/python
```

- **Test suite:** `.venv/Scripts/python.exe -m pytest tests/`
- **Fixture emergency demo (deterministic gate):** `.venv/Scripts/python.exe src/measure_emergency.py` (add `--multi --seeds=30` for the powered paired-seed run).
- **Demand sweep:** `.venv/Scripts/python.exe src/experiment_demand_sweep.py`
- **SLM controller metrics sweep (H1):** `.venv/Scripts/python.exe src/run_slm_metrics.py` — gated by the Foundry determinism probe; an unreachable or non-deterministic model records an honest SKIP rather than a degraded result.
- **SLM-vs-rule disambiguation (Job B):** `.venv/Scripts/python.exe src/experiment_slm_vs_rule.py`
- **SLM legal-reasoning note (Job A):** `.venv/Scripts/python.exe src/experiment_jobA.py`

Experiments that require the real Foundry Local model, the committed Euston net, the policy corpus, or a quorum anchor fail loud: they SKIP-with-a-record or ABORT rather than emit a silently-degraded green result. A recorded SKIP or a reported negative is an honest outcome.
