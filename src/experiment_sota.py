"""SOTA delay-aware MYOPIC controller vs vanilla myopic vs MaxPressure (H1).

Answers a focused question: can a literature-grounded, DELAY-AWARE myopic SLM
controller beat the MaxPressure baseline more robustly than the vanilla queue-only
myopic SLM -- especially where vanilla myopic only MATCHED?

The SOTA controller is still MYOPIC (own-junction information only). It adds two
levers the LLM-TSC literature shows MaxPressure structurally lacks, both aimed at
DELAY (not throughput):
  * waiting-time priority  (LLMLight, arXiv:2312.16044): serve phases whose vehicles
    have ALREADY waited long, which MaxPressure -- memoryless on waiting time --
    ignores;
  * switching hysteresis / stop reduction (EvolveSignal, arXiv:2509.03335): keep the
    current phase unless another is clearly worse-off, cutting the stops that extra
    switches cause.
Implemented as HybridController(delay_aware=True) + SLMAgent's SYSTEM_DELAY_AWARE
prompt fed a per-phase {queue, mean_wait, current} context. Everything else (the
MaxPressure shield, anti-starvation, the served-phase audit) is unchanged.

Per model: ONE shared myopic MaxPressure baseline, then the SLM under config
``myopic`` (vanilla, queue-only) and config ``sota`` (delay-aware). Reports each
arm's delay verdict vs the baseline and the sota-minus-myopic delta, so a genuine
improvement from the technique is visible. PILOT/SMOKE n=1, descriptive per §8.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from experiment_sweep import MODEL_CATALOG, _degradation_skip, _probe_model  # noqa: E402
from experiment_traffic import (  # noqa: E402
    DECISION_INTERVAL_S, RESULTS, NullAgent, TimingAgent, latency_viability, run_arm,
    summarize_latency, verdict,
)

# Focused default set (fast, real-time-viable models across the size range + the
# case that only MATCHED under vanilla myopic, phi-4-mini). Reasoning model excluded
# (latency-gated elsewhere). Override with --models.
DEFAULT_ALIASES = ["qwen3-0.6b", "qwen2.5-0.5b", "qwen3-1.7b", "phi-4-mini"]


def _discover_base():
    from slm_agent import discover_endpoint
    return discover_endpoint()[0]


def _run_slm(alias, model_id, agent, config, *, seed, end, gate, baseline):
    """One SLM arm (config myopic or sota) with the degradation guard applied."""
    timing = TimingAgent(agent)  # phase_context path forwards regardless of note flag
    arm = run_arm(f"{alias}_{config}", timing, seed=seed, end=end, gate=gate,
                  config=config)
    deg = _degradation_skip(timing.calls, timing.none_returns)
    if deg is not None:
        deg.update({"model_alias": alias, "slm_calls": timing.calls,
                    "slm_none_returns": timing.none_returns})
        return deg
    arm.update({"model": model_id, "model_alias": alias, "slm_calls": timing.calls,
                "slm_none_returns": timing.none_returns,
                "slm_proposal_served": arm.get("decision_stats", {}).get(
                    "slm_proposal_served"),
                "latency": summarize_latency(timing.latencies_s, warmup=1)})
    arm["verdict"] = verdict(baseline, arm)
    arm["latency_viability"] = latency_viability(arm["latency"])
    return arm


def _delta(sota, myopic):
    """sota-minus-myopic delay delta + whether the technique moved the verdict up."""
    def _d(a):
        return (a.get("verdict", {}) or {}).get("slm_delay_s") if isinstance(a, dict) else None
    ds, dm = _d(sota), _d(myopic)
    rank = {"slm_loses": 0, "match": 1, "slm_beats": 2}
    vs = (sota.get("verdict", {}) or {}).get("status") if isinstance(sota, dict) else None
    vm = (myopic.get("verdict", {}) or {}).get("status") if isinstance(myopic, dict) else None
    # A lift requires BOTH arms to have a REAL verdict (a skipped/degraded myopic arm
    # has none, so a merely-losing sota must NOT be reported as "lifted").
    lifted = (vs in rank and vm in rank and rank[vs] > rank[vm])
    return {
        "myopic_status": vm, "sota_status": vs,
        "myopic_delay_s": dm, "sota_delay_s": ds,
        "sota_minus_myopic_s": (ds - dm) if (ds is not None and dm is not None) else None,
        "sota_improved_delay": (ds is not None and dm is not None and ds < dm),
        "sota_lifted_verdict": lifted,
    }


def run(aliases=None, *, seed: int = 42, end: int = 1200, gate: int = 2,
        max_probe_latency_s: float = 3.0) -> dict:
    aliases = aliases or DEFAULT_ALIASES
    by = {m["alias"]: m for m in MODEL_CATALOG}
    models = [by[a] for a in aliases if a in by]
    result: dict = {
        "experiment": "H1_sota_delayaware_myopic_vs_maxpressure",
        "label": "PILOT / SMOKE",
        "technique": ("delay-aware myopic: waiting-time priority (LLMLight) + switching "
                      "hysteresis (EvolveSignal); own-junction info only"),
        "corridor": "Euston Road A501 spine (euston_spine.net.xml, 4 TLS)",
        "baseline_controller": "myopic MaxPressure (Varaiya)",
        "seed": seed, "end": end, "gate": gate,
        "decision_interval_s": DECISION_INTERVAL_S,
        "caveats": [
            "PILOT n=1, DfT daily-AADF demand (temporal profile assumed) -> "
            "DESCRIPTIVE only, NO significance claim (§8).",
            "SOTA arm is still MYOPIC (own-junction only): the levers are waiting-time "
            "priority + switching hysteresis, not coordination or prediction.",
            "Audit live on every arm; degraded (all-shield) arms are skip-recorded.",
        ],
    }
    result["baseline"] = run_arm("maxpressure", NullAgent(), seed=seed, end=end,
                                 gate=gate, config="myopic")
    base = _discover_base()
    cells: dict = {}
    for m in models:
        alias, mid = m["alias"], m["model_id"]
        agent, reason, lat = _probe_model(base, mid)
        if agent is None:
            cells[alias] = {"skipped": True, "reason": f"probe failed: {reason}"}
            continue
        if lat is not None and lat > max_probe_latency_s:
            cells[alias] = {"skipped": True, "latency_gated": True,
                            "measured_latency_s": lat,
                            "reason": f"probe latency ~{lat:.1f}s > {max_probe_latency_s}s"}
            continue
        myopic = _run_slm(alias, mid, agent, "myopic", seed=seed, end=end, gate=gate,
                          baseline=result["baseline"])
        sota = _run_slm(alias, mid, agent, "sota", seed=seed, end=end, gate=gate,
                        baseline=result["baseline"])
        cells[alias] = {"size_gb": m["size_gb"], "myopic": myopic, "sota": sota,
                        "delta": _delta(sota, myopic)}
    result["cells"] = cells
    result["summary"] = _summary(cells)

    os.makedirs(RESULTS, exist_ok=True)
    jp = os.path.join(RESULTS, "experiment_sota.json")
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    mp = os.path.join(RESULTS, "experiment_sota.md")
    with open(mp, "w", encoding="utf-8") as fh:
        fh.write(render_md(result))
    _print_summary(result, jp, mp)
    return result


def _summary(cells: dict) -> dict:
    ran = {k: v for k, v in cells.items() if isinstance(v, dict) and "delta" in v}
    improved = [k for k, v in ran.items() if v["delta"]["sota_improved_delay"]]
    lifted = [k for k, v in ran.items() if v["delta"]["sota_lifted_verdict"]]
    sota_beats = [k for k, v in ran.items() if v["delta"]["sota_status"] == "slm_beats"]
    return {
        "models_run": sorted(ran),
        "sota_improved_delay_over_myopic": sorted(improved),
        "sota_lifted_verdict_over_myopic": sorted(lifted),
        "sota_beats_maxpressure": sorted(sota_beats),
        "note": ("Descriptive pilot: 'improved' = lower delay than vanilla myopic for "
                 "the same model; 'lifted verdict' = moved loses->match or match->beats."),
    }


def _fmt(v, nd=2):
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def render_md(r: dict) -> str:
    b = r["baseline"]["metrics"]
    lines = ["# H1 SOTA: delay-aware myopic SLM vs vanilla myopic vs MaxPressure", ""]
    lines.append("**PILOT / SMOKE**, n=1. Technique: " + r["technique"] + ".")
    lines.append("")
    lines.append(f"- Baseline myopic MaxPressure: delay {_fmt(b.get('mean_network_delay_s'))} s, "
                 f"completed {_fmt(b.get('completed'), 0)}")
    lines.append(f"- Seed {r['seed']}, horizon {r['end']} s, gate {r['gate']}")
    lines.append("")
    lines.append("| Model | Size | myopic (vanilla) | sota (delay-aware) | sota vs myopic |")
    lines.append("|---|---|---|---|---|")
    for alias, c in r["cells"].items():
        if c.get("skipped"):
            lines.append(f"| {alias} | -- | SKIPPED: {c.get('reason','')[:40]} | | |")
            continue
        d = c["delta"]
        my = f"{d['myopic_status']} ({_fmt(d['myopic_delay_s'])}s)"
        so = f"{d['sota_status']} ({_fmt(d['sota_delay_s'])}s)"
        dd = (f"{_fmt(d['sota_minus_myopic_s'])}s"
              + (" IMPROVED" if d["sota_improved_delay"] else "")
              + (" LIFTED" if d["sota_lifted_verdict"] else ""))
        lines.append(f"| {alias} | {_fmt(c.get('size_gb'))} | {my} | {so} | {dd} |")
    lines.append("")
    s = r["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- SOTA improved delay over vanilla myopic for: "
                 f"{s['sota_improved_delay_over_myopic'] or 'none'}")
    lines.append(f"- SOTA lifted the verdict (loses->match or match->beats) for: "
                 f"{s['sota_lifted_verdict_over_myopic'] or 'none'}")
    lines.append(f"- SOTA beats MaxPressure for: {s['sota_beats_maxpressure'] or 'none'}")
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    for c in r["caveats"]:
        lines.append(f"- {c}")
    lines.append("")
    return "\n".join(lines)


def _print_summary(r: dict, jp: str, mp: str) -> None:
    print("=" * 72)
    print("H1 SOTA delay-aware myopic vs MaxPressure (PILOT/SMOKE)")
    b = r["baseline"]["metrics"]
    print(f"  baseline MaxPressure delay={_fmt(b.get('mean_network_delay_s'))}s")
    for alias, c in r["cells"].items():
        if c.get("skipped"):
            print(f"  {alias:>16}: SKIP ({c.get('reason','')[:44]})")
            continue
        d = c["delta"]
        print(f"  {alias:>16}: myopic={d['myopic_status']}({_fmt(d['myopic_delay_s'])}s) "
              f"sota={d['sota_status']}({_fmt(d['sota_delay_s'])}s) "
              f"delta={_fmt(d['sota_minus_myopic_s'])}s"
              + (" IMPROVED" if d["sota_improved_delay"] else "")
              + (" LIFTED" if d["sota_lifted_verdict"] else ""))
    s = r["summary"]
    print(f"  sota beats MaxPressure: {s['sota_beats_maxpressure'] or 'none'}")
    print(f"  sota lifted verdict:    {s['sota_lifted_verdict_over_myopic'] or 'none'}")
    print("=" * 72)
    print(f"  wrote: {jp}")
    print(f"  wrote: {mp}")


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="SOTA delay-aware myopic vs MaxPressure")
    ap.add_argument("--end", type=int, default=1200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--gate", type=int, default=2)
    ap.add_argument("--models", nargs="*", default=None)
    return ap


if __name__ == "__main__":
    a = _build_parser().parse_args()
    run(aliases=a.models, seed=a.seed, end=a.end, gate=a.gate)
