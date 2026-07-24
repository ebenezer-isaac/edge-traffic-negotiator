"""Powered 'why models differ' experiment: multi-seed model x topology with real behavioural
divergence (override rate) + an inferential two-way interaction test.

Two upgrades over experiment_topology (which was n=1/cell, authored-share proxy):
  1. >=2 SEEDS per (model, topology) cell -> the model x scenario INTERACTION becomes
     inferentially testable via a balanced two-way ANOVA (src/anova.py). At n=1 it was not
     (Alin & Kurt 2006).
  2. Real OVERRIDE rate from the controller event log (decision_stats):
     override_rate = slm_diverged_and_served / slm_proposal_served -- the fraction of
     SLM-authored decisions that actually differ from the MaxPressure shield's choice (a true
     policy-divergence metric, not the authored-share proxy).

Each seed's SLM delay is compared to the SAME seed's baseline. Reuses run_arm (topology-
agnostic) and experiment_topology's probe/topology helpers. Writes results/experiment_why.json
incrementally (long multi-seed run). DESCRIPTIVE demand (§8) but now with cross-seed variance,
so the interaction F-test is legitimate; absolute significance vs real demand still §8-gated.
"""
from __future__ import annotations

import argparse
import json
import os

_SRC = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(_SRC), "results")

from anova import two_way  # noqa: E402
from experiment_topology import _MODEL_IDS, _probe, _tls_count, _topologies  # noqa: E402
from experiment_traffic import NullAgent, TimingAgent, run_arm  # noqa: E402


def _std(xs):
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def _agg(xs):
    return {"mean": round(sum(xs) / len(xs), 2), "std": round(_std(xs), 2),
            "min": round(min(xs), 2), "max": round(max(xs), 2), "n": len(xs), "values": xs}


def run(models=("qwen2.5-0.5b", "qwen3-0.6b"), seeds=(42, 7, 123), end=1200, gate=2) -> dict:
    tops = _topologies()
    agents = {m: _probe(m) for m in models}
    os.makedirs(RESULTS, exist_ok=True)
    jp = os.path.join(RESULTS, "experiment_why.json")

    cells = []                       # per (topology) row
    anova_cells = {}                 # {(model, topology): [delay_rel per seed]}
    override_cells = {}              # {(model, topology): [override_rate per seed]}

    def _flush(partial_note):
        out = {"experiment": "H1_why_multiseed", "models": list(models),
               "seeds": list(seeds), "end": end, "gate": gate, "cells": cells,
               "note": partial_note}
        with open(jp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)

    for top in tops:
        label, net, routes = top["label"], top["net"], top["routes"]
        if not (os.path.exists(net) and os.path.exists(routes)):
            cells.append({"topology": label, "skipped": True, "reason": "net/routes missing"})
            _flush("partial (in progress)")
            continue
        n_tls = _tls_count(net)
        # per-seed baselines
        base_delay = {}
        for s in seeds:
            b = run_arm(f"why_{label}_mp_s{s}", NullAgent(), seed=s, end=end, gate=gate,
                        config="myopic", net=net, routes=routes)
            base_delay[s] = b["metrics"]["mean_network_delay_s"]
        row = {"topology": label, "tls": n_tls,
               "baseline_delay": _agg([base_delay[s] for s in seeds]), "models": {}}
        for m in models:
            agent, reason = agents[m]
            if agent is None:
                row["models"][m] = {"skipped": True, "reason": reason}
                continue
            rels, overrides, authored, agree = [], [], [], []
            for s in seeds:
                timing = TimingAgent(agent, forward_note=False)
                slm = run_arm(f"why_{label}_{m}_s{s}", timing, seed=s, end=end, gate=gate,
                              config="myopic", net=net, routes=routes)
                d = slm["metrics"]["mean_network_delay_s"]
                rel = (d - base_delay[s]) / base_delay[s] * 100.0 if base_delay[s] else 0.0
                ds = slm.get("decision_stats", {})
                served = ds.get("slm_proposal_served", 0) or 0
                diverged = ds.get("slm_diverged_and_served", 0) or 0
                agreed = ds.get("slm_agreed_with_shield", 0) or 0
                valid = ds.get("slm_valid_proposals", 0) or 0
                rels.append(round(rel, 2))
                overrides.append(round(diverged / served, 4) if served else 0.0)
                agree.append(round(agreed / served, 4) if served else 0.0)
                authored.append(round(served / valid, 4) if valid else 0.0)
            row["models"][m] = {
                "delay_rel_pct": _agg(rels),
                "override_rate": _agg(overrides),      # of SLM-authored, share that overrode MP
                "agreement_rate": _agg(agree),         # of SLM-authored, share equal to MP
                "authored_share": _agg(authored),      # of valid proposals, share served
            }
            anova_cells[(m, label)] = rels
            override_cells[(m, label)] = overrides
        cells.append(row)
        _flush("partial (in progress)")

    # Inferential interaction test (balanced two-way ANOVA) -- only if every cell replicated.
    live_models = [m for m in models if agents[m][0] is not None]
    live_tops = [c["topology"] for c in cells if not c.get("skipped")
                 and all((m, c["topology"]) in anova_cells for m in live_models)]
    anova_res = None
    if len(live_models) >= 2 and len(live_tops) >= 2 and len(seeds) >= 2:
        sub = {(m, t): anova_cells[(m, t)] for m in live_models for t in live_tops}
        try:
            anova_res = two_way(sub, live_models, live_tops)
        except Exception as exc:  # noqa: BLE001
            anova_res = {"error": str(exc)}

    # override_rate vs delay_rel across all cells (mechanism correlation)
    ov, dl = [], []
    for (m, t), rr in override_cells.items():
        ov.append(sum(rr) / len(rr))
        dl.append(sum(anova_cells[(m, t)]) / len(anova_cells[(m, t)]))
    from model_scenario_analysis import _pearson, _spearman
    mech = {"pearson_override_vs_delay": round(_pearson(ov, dl), 3) if _pearson(ov, dl) is not None else None,
            "spearman_override_vs_delay": round(_spearman(ov, dl), 3) if _spearman(ov, dl) is not None else None,
            "n_cells": len(ov),
            "reading": ("Correlational only (per-cell mean override rate vs per-cell mean delay "
                        "change, across all model x scenario cells): a POSITIVE value means cells "
                        "where the SLM diverged from MaxPressure more often tend to show a larger "
                        "delay change. Read strength from BOTH coefficients -- a large Pearson-"
                        "minus-Spearman gap indicates the linear correlation is outlier-driven, "
                        "not a monotone trend. Does not establish causation.")}

    result = {
        "experiment": "H1_why_multiseed",
        "models": list(models), "seeds": list(seeds), "end": end, "gate": gate,
        "cells": cells,
        "interaction_anova": anova_res,
        "mechanism_override_vs_delay": mech,
        "note": ("POWERED (>=2 seeds/cell): the model x scenario interaction is now "
                 "inferentially tested (two-way ANOVA). Demand is still DfT daily-resolution "
                 "(§8), so cross-SEED variance is real but absolute significance vs live "
                 "London demand remains gated; this tests the interaction, not the headline."),
    }
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    _print(result)
    return result


def _print(r):
    print("POWERED why-analysis (mean delay change % [std] per cell):")
    for c in r["cells"]:
        if c.get("skipped"):
            print(f"  {c['topology']:16s} SKIP"); continue
        for m, mm in c["models"].items():
            if mm.get("skipped"):
                print(f"  {c['topology']:16s} {m:13s} SKIP"); continue
            d = mm["delay_rel_pct"]; o = mm["override_rate"]
            print(f"  {c['topology']:16s} {m:13s} delay={d['mean']:+.1f}% [sd {d['std']:.1f}] "
                  f"override={o['mean']:.2f}")
    a = r.get("interaction_anova")
    if a and "interaction" in a:
        print(f"\nINTERACTION (two-way ANOVA, n={a['n_per_cell']}/cell): "
              f"F={a['interaction']['F']} p={a['interaction']['p']} "
              f"partial_eta2={a['interaction']['partial_eta_sq']}")
        print(f"  model:    F={a['model']['F']} p={a['model']['p']}")
        print(f"  scenario: F={a['scenario']['F']} p={a['scenario']['p']}")
    print("\nMECHANISM override vs delay:", r["mechanism_override_vs_delay"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Powered multi-seed why-models-differ analysis.")
    ap.add_argument("--models", nargs="*", default=["qwen2.5-0.5b", "qwen3-0.6b"])
    ap.add_argument("--seeds", nargs="*", type=int, default=[42, 7, 123])
    ap.add_argument("--end", type=int, default=1200)
    ns = ap.parse_args()
    run(models=tuple(ns.models), seeds=tuple(ns.seeds), end=ns.end)
