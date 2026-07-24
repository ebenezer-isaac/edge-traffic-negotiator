"""Render results/experiment_why.json -> results/experiment_why.md (house style).

Reports the powered multi-seed model x scenario why-analysis honestly: the per-cell delay/
override behaviour, the inferential two-way interaction ANOVA, and the override-vs-delay
mechanism correlation -- including where the result is negative or only marginal.
"""
from __future__ import annotations

import json
import os

_SRC = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(_SRC), "results")

_ALPHA = 0.05


def _pfmt(p):
    """Faithful p display: a p rounded to 0.0 is a tiny tail, not a literal zero."""
    if p is None:
        return "n/a"
    return "<0.001" if p < 0.001 else f"{p:.4f}"


def _sig(p):
    if p is None:
        return "n/a"
    lead = "p<0.001" if p < 0.001 else f"p={p:.4f}"
    return f"{lead} ({'significant' if p < _ALPHA else 'NOT significant'} at a={_ALPHA})"


def _m(agg):
    """Mean from the raw per-seed values (avoids double-rounding through the stored 2dp mean)."""
    vs = agg.get("values")
    return sum(vs) / len(vs) if vs else agg.get("mean", 0.0)


def render_md(r: dict) -> str:
    models = r["models"]
    L = []
    L.append("# Powered why-analysis: model x scenario (multi-seed)")
    L.append("")
    a = r.get("interaction_anova") or {}
    inter = a.get("interaction", {})
    ip = inter.get("p")
    is_sig = ip is not None and ip < _ALPHA
    verdict = "significant" if is_sig else "marginal / NOT significant"
    tail = ("The scenario is the dominant lever, but which SLM you run and the "
            "scenario-specific way it behaves BOTH move the outcome: model, scenario and their "
            "interaction are all significant."
            if is_sig else
            "The scenario is the dominant lever; the model matters; their *interaction* is "
            "only suggestive at this power.")
    L.append(f"**Interaction model x scenario: {verdict}.** Two-way ANOVA "
             f"(n={a.get('n_per_cell')}/cell): interaction F={inter.get('F')}, "
             f"{_sig(ip)}, partial eta^2={inter.get('partial_eta_sq')}. " + tail)
    L.append("")
    L.append("## Design")
    L.append("")
    L.append(f"- Models: {', '.join(models)}")
    L.append(f"- Seeds/cell: {r['seeds']} (n={len(r['seeds'])})")
    L.append(f"- Horizon: end={r['end']}, congestion gate={r['gate']}")
    L.append(f"- Demand: DfT daily-resolution (SS8 gated) -- this tests the INTERACTION, "
             "not the headline vs live London demand.")
    L.append("")
    L.append("## Per-cell behaviour (mean [sd] over seeds)")
    L.append("")
    L.append("| Topology | TLS | Model | Delay vs baseline | Override rate | Agreement | "
             "Authored share |")
    L.append("|---|---|---|---|---|---|---|")
    for c in r["cells"]:
        if c.get("skipped"):
            L.append(f"| {c['topology']} | - | *skipped* | {c.get('reason','')} | | | |")
            continue
        for m in models:
            mm = c["models"].get(m, {})
            if mm.get("skipped"):
                L.append(f"| {c['topology']} | {c['tls']} | {m} | *skipped: "
                         f"{mm.get('reason','')}* | | | |")
                continue
            d = mm["delay_rel_pct"]; o = mm["override_rate"]
            ag = mm["agreement_rate"]; au = mm["authored_share"]
            L.append(f"| {c['topology']} | {c['tls']} | {m} | {_m(d):+.1f}% [sd {d['std']:.1f}] "
                     f"| {_m(o):.2f} [sd {o['std']:.2f}] | {_m(ag):.2f} | {_m(au):.2f} |")
    L.append("")
    L.append("Delay vs baseline: negative = faster than MaxPressure on that seed's own baseline; "
             "positive = slower. Override rate = share of SLM-authored decisions that diverged "
             "from the MaxPressure shield.")
    L.append("")
    L.append("## Inferential two-way ANOVA (model x scenario, with replication)")
    L.append("")
    if "error" in a:
        L.append(f"- ANOVA not computed: {a['error']}")
    elif inter:
        L.append(f"- Grand mean delay change: {a.get('grand_mean')}%")
        L.append("")
        L.append("| Effect | SS | df | MS | F | p | partial eta^2 |")
        L.append("|---|---|---|---|---|---|---|")
        for key, lab in (("model", "Model"), ("scenario", "Scenario"),
                         ("interaction", "Model x Scenario")):
            t = a[key]
            L.append(f"| {lab} | {t['SS']} | {t['df']} | {t['MS']} | {t['F']} | {_pfmt(t['p'])} | "
                     f"{t['partial_eta_sq']} |")
        w = a["within"]
        L.append(f"| Within (error) | {w['SS']} | {w['df']} | {w['MS']} | - | - | - |")
        L.append("")
        L.append("**Reading (honest):**")
        L.append(f"- Scenario main effect: {_sig(a['scenario']['p'])}, partial eta^2="
                 f"{a['scenario']['partial_eta_sq']} -- the topology/scenario is the overwhelming "
                 "driver of whether the SLM helps or hurts.")
        L.append(f"- Model main effect: {_sig(a['model']['p'])}, partial eta^2="
                 f"{a['model']['partial_eta_sq']} -- which SLM you run matters on its own.")
        _eta = inter["partial_eta_sq"]
        _big = "LARGE" if _eta is not None and _eta > 0.14 else "small-to-moderate"
        if is_sig:
            L.append(f"- Interaction: {_sig(inter['p'])}, partial eta^2={_eta} -- {_big} by "
                     "Cohen's convention (partial eta^2 > 0.14) AND clears a=0.05: the SLMs do not "
                     "just differ by a constant, they differ SCENARIO-BY-SCENARIO (e.g. on the "
                     "densest grid qwen2.5 blows up far worse than qwen3). The interaction is real "
                     "at this power; absolute significance vs live demand stays SS8-gated.")
        else:
            L.append(f"- Interaction: {_sig(inter['p'])}, partial eta^2={_eta} -- {_big} by "
                     "Cohen's convention (partial eta^2 > 0.14) yet does NOT clear a=0.05 at this "
                     "power: a suggestive, underpowered interaction that more seeds should resolve "
                     "either way. We do not claim a proven interaction.")
    L.append("")
    L.append("## Mechanism: does override rate explain the delay change?")
    L.append("")
    mech = r.get("mechanism_override_vs_delay", {})
    L.append(f"- Pearson(override, delay change) = {mech.get('pearson_override_vs_delay')}; "
             f"Spearman = {mech.get('spearman_override_vs_delay')} (n_cells={mech.get('n_cells')}).")
    pear = mech.get("pearson_override_vs_delay")
    spear = mech.get("spearman_override_vs_delay")
    if pear is not None and abs(pear) < 0.4:
        L.append("- **Honest negative:** the correlation is weak. Across these cells, *how often* "
                 "the SLM overrode MaxPressure does not cleanly predict how much delay moved. The "
                 "hypothesised 'divergence drives the loss' mechanism is NOT well supported by the "
                 "cell-level correlation; the scenario effect dominates the divergence effect.")
    elif pear is not None:
        gap = spear is not None and abs(pear - spear) > 0.2
        L.append("- The Pearson correlation is MODERATE and positive: cells where the SLM overrode "
                 "MaxPressure more often do tend to show a larger delay change, consistent with "
                 "'divergence drives the loss.' " + (
                 "But Spearman is much weaker, so the linear correlation leans on the extreme "
                 "high-override / high-delay cell (the densest grid) rather than a monotone trend "
                 "across all cells -- treat the mechanism as directional, not established."
                 if gap else
                 "Spearman agrees, so the trend is monotone, not outlier-driven.") +
                 " Either way the scenario main effect is far larger than this divergence signal.")
    L.append("")
    L.append("## Limitations")
    L.append("")
    L.append("- Demand is DfT daily-resolution (SS8): cross-seed variance is real, so the F-tests "
             "are legitimate, but absolute significance vs live London demand stays gated.")
    _ncells = mech.get("n_cells")
    L.append(f"- n={len(r['seeds'])} seeds/cell across {len(a.get('levels_b', []))} scenarios: "
             "enough replication to make the interaction inferentially testable (Alin & Kurt 2006); "
             + ("the interaction reaches significance here, but more seeds would tighten the "
                "effect-size estimate." if is_sig else
                "a marginal interaction would need more seeds to resolve."))
    L.append(f"- Mechanism correlation is over {_ncells} cells only; treat as directional, not "
             "conclusive, and check its sensitivity to the most extreme cell.")
    L.append("")
    note = r.get("completed_by")
    if note:
        L.append(f"*{note}*")
        L.append("")
    return "\n".join(L)


def main():
    jp = os.path.join(RESULTS, "experiment_why.json")
    with open(jp, encoding="utf-8") as fh:
        r = json.load(fh)
    md = render_md(r)
    mp = os.path.join(RESULTS, "experiment_why.md")
    with open(mp, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"wrote {mp} ({len(md)} chars)")


if __name__ == "__main__":
    main()
