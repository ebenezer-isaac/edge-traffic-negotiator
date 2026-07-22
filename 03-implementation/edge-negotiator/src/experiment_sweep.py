"""H1 HEADLINE: the MODEL x CONFIG SWEEP (MASTER-SPEC §3, §8; D-H1-perf, D-H1-scale).

Measures the on-device SLM traffic controller against the myopic MaxPressure
baseline across the full grid {model} x {config} on the REAL Euston A501 corridor,
and produces the two headline deliverables:

  * the FEASIBILITY MAP  -- for every (model, config) cell: does the SLM controller
    match/beat MaxPressure on delay, at what latency, with the audit intact;
  * the SCALE THRESHOLD  -- the SMALLEST model and SIMPLEST config (if any) that
    reaches parity-or-better. An honest negative ("no on-device model beats
    MaxPressure on delay at this pilot horizon") is a valid, distinction-grade
    result; LIMITATIONS ARE ALLOWED (§0).

MODELS (on-device only, Foundry Local; ids from `foundry cache list`), ordered
SMALLEST -> LARGEST so the scale threshold reads off the map in order:
  qwen2.5-0.5b (0.68 GB) < qwen2.5-1.5b (1.51 GB) < phi-4-mini-reasoning (3.15 GB)
  < phi-4-mini (3.72 GB).
CONFIGS ordered SIMPLEST -> RICHEST: myopic < +coordination < +prediction.

DEMAND / SATURATION (§8): base.rou.xml is the DfT-AADF-calibrated ~1 h demand that
GRIDLOCKS without a controller (24.5% completion) and needs an active controller
(MaxPressure ~96.8%). A short horizon is LIGHT (myopia does not bite, so every arm
merely matches); "beat" can only appear once demand SATURATES, so the sweep runs a
LONGER horizon than the smoke. Still PILOT-gated: the temporal profile is assumed,
so NO inferential/significance claim is made until time-resolved TfL counts land.

ROBUSTNESS. Each MODEL is gated by a per-model Foundry determinism probe (temp-0
reachability + determinism); a model that is unreachable / non-deterministic /
crashes (e.g. the WebGPU device-lost fault) SKIPS all its cells WITH A RECORDED
REASON -- never a fabricated green. Each ARM is additionally wrapped so a mid-run
failure skips only that cell. Results are written INCREMENTALLY after every cell,
so a crash mid-sweep preserves every completed cell.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from experiment_traffic import (  # noqa: E402
    CONFIGS,
    DECISION_INTERVAL_S,
    RESULTS,
    NullAgent,
    TimingAgent,
    latency_viability,
    run_arm,
    summarize_latency,
    verdict,
)

# On-device model catalog, SMALLEST -> LARGEST. model_id from `foundry cache list`
# (Foundry lazily loads a cached model on first request by this id -- verified). If
# an id is stale on a given Foundry build, that model's probe SKIPS-with-record.
MODEL_CATALOG = [
    {"alias": "qwen2.5-0.5b", "model_id": "qwen2.5-0.5b-instruct-generic-gpu:4",
     "size_gb": 0.68},
    {"alias": "qwen2.5-1.5b", "model_id": "qwen2.5-1.5b-instruct-generic-gpu:4",
     "size_gb": 1.51},
    {"alias": "phi-4-mini-reasoning", "model_id": "Phi-4-mini-reasoning-generic-gpu:3",
     "size_gb": 3.15},
    {"alias": "phi-4-mini", "model_id": "Phi-4-mini-instruct-generic-gpu:5",
     "size_gb": 3.72},
]


def _probe_model(base_url: str, model_id: str, reps: int = 3):
    """Per-MODEL precondition probe (same two-dimension contract as
    slm_agent.probe_foundry_determinism, but for an ARBITRARY model id):
    reachability + temp-0 determinism on a canned decision. Returns
    ``(SLMAgent, None)`` on success else ``(None, reason)``. NEVER raises."""
    from slm_agent import SLMAgent
    if reps < 2:
        return None, "determinism probe needs reps >= 2"
    try:
        agent = SLMAgent(base_url=base_url, model=model_id)
        agent.client.models.list()  # cheap real call: dead service fails here
    except Exception as exc:  # noqa: BLE001
        return None, f"model {model_id} not reachable ({type(exc).__name__})"
    seen: list[int] = []
    for _ in range(reps):
        try:
            phase = agent.choose_phase("PROBE", 2, [8, 0])
        except Exception as exc:  # noqa: BLE001
            return None, f"probe decision raised {type(exc).__name__}: {exc}"
        if phase is None:
            return None, "model did not answer a well-formed decision"
        seen.append(phase)
    if len(set(seen)) != 1:
        return None, f"non-deterministic at temp 0 over {reps} reps: {sorted(set(seen))}"
    return agent, None


def _discover_base():
    """Discover the live Foundry endpoint base_url (port changes across restarts)."""
    from slm_agent import discover_endpoint
    base, _model = discover_endpoint()
    return base


def _degradation_skip(calls: int, none_returns: int) -> dict | None:
    """Guard against a SILENT-DEGRADATION false green (battery FATAL).

    ``_probe_model`` runs ONCE per model, before its cells. If Foundry dies DURING
    a cell (e.g. the WebGPU device-lost fault observed this session),
    ``SLMAgent.choose_phase`` SWALLOWS the error and returns ``None`` every call --
    it NEVER raises -- so ``_run_cell``'s ``except`` is not hit and the arm
    completes with EVERY decision falling back to the MaxPressure shield. For the
    ``myopic`` config that all-shield arm is byte-identical to the NullAgent
    baseline (same net/demand/seed), so ``verdict()`` returns ``"match"`` and
    ``_scale_threshold`` would report a FALSE scale threshold at the simplest
    config. A model that simply cannot emit a valid decision is equally not a real
    SLM cell. So: if the SLM was CONSULTED (calls>0) but authored ZERO valid
    proposals (every call returned None), reclassify the cell as SKIPPED so it can
    NEVER be scored as parity. ``calls==0`` (gate never opened / light demand) is a
    distinct HONEST state, not degradation, and is left to run normally.
    """
    if calls > 0 and none_returns >= calls:
        return {"skipped": True, "degraded": True,
                "reason": (f"degraded: SLM authored 0/{calls} decisions (all None -> "
                           "all-shield; model precondition likely lost mid-run) -- "
                           "byte-identical to the baseline, cannot count as parity")}
    return None


def _run_cell(alias: str, model_id: str, agent, config: str, *, seed: int,
              end: int, gate: int, baseline: dict) -> dict:
    """Run ONE (model, config) cell and attach its verdict + latency. A mid-run
    failure that RAISES is caught and returned as a skipped cell; a mid-run failure
    that SILENTLY degrades to all-shield (choose_phase returns None) is caught by
    the degradation guard -- either way the cell can never be a false parity."""
    try:
        timing = TimingAgent(agent, forward_note=(config != "myopic"))
        arm = run_arm(f"{alias}_{config}", timing, seed=seed, end=end, gate=gate,
                      config=config)
        deg = _degradation_skip(timing.calls, timing.none_returns)
        if deg is not None:
            # Keep the observed evidence on the skip record for transparency.
            deg["model_alias"] = alias
            deg["slm_calls"] = timing.calls
            deg["slm_none_returns"] = timing.none_returns
            return deg
        arm["model"] = model_id
        arm["model_alias"] = alias
        arm["slm_calls"] = timing.calls
        arm["slm_none_returns"] = timing.none_returns
        arm["slm_proposal_served"] = arm.get("decision_stats", {}).get(
            "slm_proposal_served")
        arm["notes_forwarded"] = timing.notes_forwarded
        arm["latency"] = summarize_latency(timing.latencies_s, warmup=1)
        arm["verdict"] = verdict(baseline, arm)
        arm["latency_viability"] = latency_viability(arm["latency"])
        return arm
    except Exception as exc:  # noqa: BLE001 -- SKIP the cell, keep the sweep alive
        return {"skipped": True,
                "reason": f"cell raised {type(exc).__name__}: {str(exc)[:200]}"}


def _feasibility_map(cells: dict, models, configs) -> list:
    """Flatten cells -> a row per (model, config) with the status + key numbers."""
    rows = []
    for m in models:
        alias = m["alias"]
        for config in configs:
            cell = cells.get(alias, {}).get(config)
            if not isinstance(cell, dict) or cell.get("skipped"):
                rows.append({"model": alias, "size_gb": m["size_gb"], "config": config,
                             "status": "skipped",
                             "reason": (cell or {}).get("reason", "not run")})
                continue
            v = cell.get("verdict", {})
            co = cell.get("coordination") or {}
            lat = cell.get("latency") or {}
            rows.append({
                "model": alias, "size_gb": m["size_gb"], "config": config,
                "status": v.get("status"),
                "slm_delay_s": v.get("slm_delay_s"),
                "baseline_delay_s": v.get("baseline_delay_s"),
                "slm_relative_delay": v.get("slm_relative_delay"),
                "completed": cell.get("metrics", {}).get("completed"),
                "latency_p99_s": lat.get("p99"),
                "slm_calls": cell.get("slm_calls"),
                "slm_proposal_served": cell.get("slm_proposal_served"),
                "slm_none_returns": cell.get("slm_none_returns"),
                "coord_adjusted_decisions": co.get("coord_adjusted_decisions"),
                "pred_adjusted_decisions": co.get("pred_adjusted_decisions"),
                "verify_chain": cell.get("audit", {}).get("verify_chain"),
            })
    return rows


def _scale_threshold(cells: dict, models, configs) -> dict:
    """SMALLEST model x SIMPLEST config reaching parity-or-better (match/beat).

    Scans models smallest->largest, configs simplest->richest, and returns the
    FIRST cell whose verdict is match or slm_beats. Honest negative when none do.
    n=1 PILOT: descriptive framing for the map, NOT an inferential threshold claim.
    """
    for m in models:  # already smallest -> largest
        for config in configs:  # myopic -> coordination -> prediction
            cell = cells.get(m["alias"], {}).get(config)
            if not (isinstance(cell, dict) and not cell.get("skipped")):
                continue
            if cell.get("verdict", {}).get("status") not in ("match", "slm_beats"):
                continue
            # DEGENERATE-MATCH guard (battery MINOR): a cell where the SLM was NEVER
            # consulted (gate never opened over the horizon, slm_calls==0) matches
            # the baseline only because it IS the baseline -- the SLM never acted, so
            # it CANNOT be claimed as SLM parity. Exclude it (not expected at the
            # saturating horizon, where the gate opens constantly). A cell where the
            # SLM WAS consulted (calls>0) but the shield overrode every proposal is a
            # legitimate SLM controller result and is NOT excluded here.
            if (cell.get("slm_calls") or 0) <= 0:
                continue
            return {
                "reached": True,
                "smallest_model": m["alias"], "size_gb": m["size_gb"],
                "simplest_config": config,
                "status": cell["verdict"]["status"],
                "slm_delay_s": cell["verdict"].get("slm_delay_s"),
                "baseline_delay_s": cell["verdict"].get("baseline_delay_s"),
                "slm_calls": cell.get("slm_calls"),
                "slm_proposal_served": cell.get("slm_proposal_served"),
                "note": ("SMOKE/PILOT n=1: descriptive. A powered n>=30 sweep on "
                         "time-resolved demand is the confirmatory step (§8)."),
            }
    return {
        "reached": False,
        "smallest_model": None, "simplest_config": None,
        "note": ("HONEST NEGATIVE at this pilot horizon: no on-device model x config "
                 "cell reached parity-or-better on delay. Valid distinction-grade "
                 "result (§0/§3); a longer/full-hour saturated run + n>=30 on "
                 "time-resolved demand is the confirmatory step (§8)."),
    }


def run_sweep(models=None, configs=CONFIGS, *, seed: int = 42, end: int = 1200,
              gate: int = 2) -> dict:
    """Run the model x config sweep on Euston; write the feasibility map + scale
    threshold. ONE myopic MaxPressure baseline; every SLM cell compares to it.

    Writes results/experiment_sweep.{json,md} INCREMENTALLY (after each cell), so
    a crash mid-sweep preserves completed cells. PILOT/SMOKE n=1: descriptive only.
    """
    models = models if models is not None else MODEL_CATALOG
    result: dict = {
        "experiment": "H1_model_x_config_sweep",
        "label": "PILOT / SMOKE",
        "deliverable": "feasibility map + scale threshold (D-H1-perf, D-H1-scale)",
        "corridor": "Euston Road A501 spine (euston_spine.net.xml, 4 TLS)",
        "demand": "base.rou.xml (DfT-AADF-calibrated ~1h; saturating under a controller)",
        "baseline_controller": "myopic MaxPressure (Varaiya) -- fixed reference",
        "models": [{"alias": m["alias"], "model_id": m["model_id"],
                    "size_gb": m["size_gb"]} for m in models],
        "configs": list(configs),
        "seed": seed, "end": end, "gate": gate,
        "decision_interval_s": DECISION_INTERVAL_S,
        "caveats": [
            "PILOT: demand is DfT daily-AADF magnitude+mix; temporal profile assumed "
            "-> inferential claims GATED until time-resolved TfL counts land (§8).",
            "SMOKE: n=1 per cell -> descriptive only, NO significance claim.",
            "On-device only (Foundry Local); the audit layer is LIVE on every cell.",
            "A longer horizon than the smoke, so saturation lets 'beat' appear if any "
            "model/config achieves it; a full-hour n>=30 run is the confirmatory step.",
        ],
    }

    os.makedirs(RESULTS, exist_ok=True)
    json_path = os.path.join(RESULTS, "experiment_sweep.json")
    md_path = os.path.join(RESULTS, "experiment_sweep.md")

    def _flush():
        result["feasibility_map"] = _feasibility_map(result["cells"], models, configs)
        result["scale_threshold"] = _scale_threshold(result["cells"], models, configs)
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(render_sweep_md(result))

    # ONE baseline (no Foundry needed).
    print("[sweep] baseline: myopic MaxPressure ...", flush=True)
    result["baseline"] = run_arm("maxpressure", NullAgent(), seed=seed, end=end,
                                 gate=gate, config="myopic")
    result["cells"] = {}
    _flush()

    base_url = _discover_base()
    for m in models:
        alias, model_id = m["alias"], m["model_id"]
        result["cells"][alias] = {}
        print(f"[sweep] probing model {alias} ({model_id}) ...", flush=True)
        agent, reason = _probe_model(base_url, model_id)
        if agent is None:
            for config in configs:
                result["cells"][alias][config] = {"skipped": True,
                                                  "reason": f"model probe failed: {reason}"}
            print(f"[sweep]   SKIP all configs for {alias}: {reason}", flush=True)
            _flush()
            continue
        for config in configs:
            print(f"[sweep]   {alias} x {config} ...", flush=True)
            cell = _run_cell(alias, model_id, agent, config, seed=seed, end=end,
                             gate=gate, baseline=result["baseline"])
            result["cells"][alias][config] = cell
            if cell.get("skipped"):
                print(f"[sweep]     SKIP: {cell['reason']}", flush=True)
            else:
                v = cell.get("verdict", {})
                print(f"[sweep]     {v.get('status')} delay={v.get('slm_delay_s')}s "
                      f"P99={cell.get('latency', {}).get('p99')}s", flush=True)
            _flush()  # incremental: never lose a completed cell

    _flush()
    _print_sweep_summary(result, json_path, md_path)
    return result


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #
def _fmt(v, nd: int = 2) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def render_sweep_md(r: dict) -> str:
    lines = ["# H1 model x config sweep: feasibility map + scale threshold (Euston A501)",
             ""]
    lines.append("**PILOT / SMOKE** -- n=1 per cell. On-device SLM controller vs myopic "
                 "MaxPressure across {model} x {config}. NOT a significance claim.")
    lines.append("")
    b = r.get("baseline", {}).get("metrics", {})
    lines.append(f"- Corridor: {r['corridor']}")
    lines.append(f"- Demand: {r['demand']}")
    lines.append(f"- Baseline (myopic MaxPressure): completed={_fmt(b.get('completed'), 0)}, "
                 f"mean delay={_fmt(b.get('mean_network_delay_s'))} s, "
                 f"teleports={_fmt(b.get('teleports'), 0)}")
    lines.append(f"- Seed: {r['seed']}  |  horizon: {r['end']} s  |  gate: {r['gate']}  |  "
                 f"decision interval: {r['decision_interval_s']} s")
    lines.append("")
    lines.append("## Feasibility map (delay verdict vs MaxPressure)")
    lines.append("")
    lines.append("| Model | Size (GB) | Config | Verdict | SLM delay (s) | rel % | "
                 "completed | SLM served/calls | P99 (s) | coord/pred changed | audit |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for row in r.get("feasibility_map", []):
        if row["status"] == "skipped":
            lines.append(f"| {row['model']} | {_fmt(row.get('size_gb'), 2)} | "
                         f"{row['config']} | SKIPPED | -- | -- | -- | -- | -- | -- | "
                         f"{row.get('reason', '')[:48]} |")
            continue
        rel = row.get("slm_relative_delay")
        rel_s = _fmt(rel * 100, 1) if isinstance(rel, (int, float)) else "n/a"
        lines.append(
            f"| {row['model']} | {_fmt(row.get('size_gb'), 2)} | {row['config']} | "
            f"**{row['status']}** | {_fmt(row.get('slm_delay_s'))} | {rel_s} | "
            f"{_fmt(row.get('completed'), 0)} | "
            f"{_fmt(row.get('slm_proposal_served'), 0)}/{_fmt(row.get('slm_calls'), 0)} | "
            f"{_fmt(row.get('latency_p99_s'), 3)} | "
            f"{row.get('coord_adjusted_decisions')}/{row.get('pred_adjusted_decisions')} | "
            f"{_fmt(row.get('verify_chain'))} |")
    lines.append("")
    st = r.get("scale_threshold", {})
    lines.append("## Scale threshold")
    lines.append("")
    if st.get("reached"):
        lines.append(f"- **Reached**: smallest model **{st['smallest_model']}** "
                     f"({_fmt(st.get('size_gb'), 2)} GB) at simplest config "
                     f"**{st['simplest_config']}** -> {st['status']} "
                     f"(SLM {_fmt(st.get('slm_delay_s'))} s vs baseline "
                     f"{_fmt(st.get('baseline_delay_s'))} s)")
    else:
        lines.append(f"- **Not reached**: {st.get('note')}")
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    for c in r["caveats"]:
        lines.append(f"- {c}")
    lines.append("")
    return "\n".join(lines)


def _print_sweep_summary(r: dict, json_path: str, md_path: str) -> None:
    print("=" * 72)
    print("H1 MODEL x CONFIG SWEEP (PILOT/SMOKE): feasibility map + scale threshold")
    b = r.get("baseline", {}).get("metrics", {})
    print(f"  baseline (myopic MaxPressure): completed={b.get('completed')} "
          f"mean_delay={_fmt(b.get('mean_network_delay_s'))}s")
    for row in r.get("feasibility_map", []):
        if row["status"] == "skipped":
            print(f"  {row['model']:>22} x {row['config']:<12} SKIPPED "
                  f"({row.get('reason', '')[:40]})")
        else:
            print(f"  {row['model']:>22} x {row['config']:<12} {row['status']:<10} "
                  f"delay={_fmt(row.get('slm_delay_s'))}s "
                  f"P99={_fmt(row.get('latency_p99_s'), 3)}s "
                  f"verify_chain={_fmt(row.get('verify_chain'))}")
    st = r.get("scale_threshold", {})
    if st.get("reached"):
        print(f"  SCALE THRESHOLD: {st['smallest_model']} x {st['simplest_config']} "
              f"({st['status']})")
    else:
        print("  SCALE THRESHOLD: NOT reached (honest negative at this pilot horizon)")
    print("=" * 72)
    print(f"  wrote: {json_path}")
    print(f"  wrote: {md_path}")


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="H1 model x config sweep -> feasibility map + scale threshold "
                    "(PILOT/SMOKE; on-device Foundry Local models).")
    ap.add_argument("--end", type=int, default=1200,
                    help="sim horizon in seconds (longer than the smoke so demand "
                         "saturates; default 1200)")
    ap.add_argument("--seed", type=int, default=42, help="SUMO seed (default 42)")
    ap.add_argument("--gate", type=int, default=2, help="event-gate (default 2)")
    ap.add_argument("--models", nargs="*", default=None,
                    help="subset of model aliases to run (default: full catalog)")
    return ap


if __name__ == "__main__":
    args = _build_parser().parse_args()
    catalog = MODEL_CATALOG
    if args.models:
        catalog = [m for m in MODEL_CATALOG if m["alias"] in set(args.models)]
        if not catalog:
            print(f"no catalog models match {args.models}; "
                  f"known: {[m['alias'] for m in MODEL_CATALOG]}")
            raise SystemExit(2)
    run_sweep(models=catalog, seed=args.seed, end=args.end, gate=args.gate)
