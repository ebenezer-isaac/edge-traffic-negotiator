"""Model x scenario differentiation analysis (full-scale phase, supervisor request).

WHY do models act differently across scenarios, and one model across scenarios? This module
replicates, on our committed results, the standard methodology (see docs citations):

  * disordinal INTERACTION = a rank reversal across scenarios (Loftus 1978); the headline
    visual is a slope chart.
  * SIMPSON'S PARADOX: a pooled correlation whose sign reverses within subgroups (Simpson
    1951; Yule-Simpson). We report Pearson (all) vs Pearson (congested-only) vs Spearman vs
    leave-one-out -- because an r on 4 points is otherwise uninterpretable (Agarwal 2021).
  * HELM-style WIN RATE + min-max normalised scores (Liang 2022; BIG-bench NPM 2022).
  * descriptive VARIANCE DECOMPOSITION (eta-squared for model / scenario / interaction;
    Montgomery). At n=1/cell the interaction is NOT inferentially testable -- reported as
    DESCRIPTIVE only (Alin & Kurt 2006).
  * behavioural ACTIVITY / influence: authored-rate = slm_authored / slm_calls, the fraction
    of consultations whose proposal was served; correlated with outcome (a policy-divergence
    proxy, cf. agreement/override rate, Schulman 2015).

Pure analysis: reads results/*.json, writes results/model_scenario_analysis.json. No SUMO /
no Foundry. Everything is DESCRIPTIVE (n=1 seed per cell except the 5-seed robustness axis);
no significance is claimed. Numbers come only from committed artifacts.
"""
from __future__ import annotations

import json
import os

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def _load(name: str) -> dict:
    with open(os.path.join(RESULTS, name), encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# small stats helpers (no numpy dependency; explicit + auditable)
# --------------------------------------------------------------------------- #
def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def _pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx, my = _mean(xs), _mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / (sxx ** 0.5 * syy ** 0.5)


def _rank(xs):
    # average ranks (ties shared), 1-based
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return ranks


def _spearman(xs, ys):
    if len(xs) < 2:
        return None
    return _pearson(_rank(xs), _rank(ys))


def _leave_one_out_pearson(xs, ys):
    """Pearson r with each single point dropped -> exposes leverage (Croux & Dehon)."""
    out = []
    for k in range(len(xs)):
        rx = xs[:k] + xs[k + 1:]
        ry = ys[:k] + ys[k + 1:]
        out.append(round(_pearson(rx, ry), 3) if _pearson(rx, ry) is not None else None)
    return out


# --------------------------------------------------------------------------- #
# 1. MODEL x TOPOLOGY matrix (the interaction axis) -- from experiment_topology.json
# --------------------------------------------------------------------------- #
def _topology_matrix() -> dict:
    d = _load("experiment_topology.json")
    matrix, activity, substrate = {}, {}, {}
    for c in d["cells"]:
        top = c["topology"]
        b = c["baseline"]
        stranded = (b["departed"] - b["completed"]) / b["departed"] if b["departed"] else 0.0
        substrate[top] = {"teleports": b["teleports"], "baseline_delay_s": b["delay_s"],
                          "stranded_frac": round(stranded, 3),
                          "gridlock_proxy": round(b["teleports"] + 100.0 * stranded, 1),
                          "free_flowing": b["teleports"] == 0}
        for m, mm in c["models"].items():
            if mm.get("skipped"):
                continue
            matrix.setdefault(m, {})[top] = {
                "delay_rel_pct": round((mm["delay_rel"] or 0) * 100, 1),
                "joint_verdict": mm["joint_verdict"]}
            calls = mm.get("slm_calls") or 0
            authored = mm.get("slm_authored") or 0
            activity.setdefault(m, {})[top] = {
                "slm_calls": calls, "slm_authored": authored,
                "authored_rate": round(authored / calls, 3) if calls else None}
    return {"matrix": matrix, "activity": activity, "substrate": substrate}


def _interaction(matrix: dict, scenarios: list) -> dict:
    """Detect disordinal interaction (rank reversal) between the two models across scenarios,
    and give a DESCRIPTIVE variance decomposition (eta-squared)."""
    models = list(matrix)
    # collect the shared scenarios both models cover
    shared = [s for s in scenarios if all(s in matrix[m] for m in models)]
    cells = {(m, s): matrix[m][s]["delay_rel_pct"] for m in models for s in shared}
    reversals = []
    if len(models) == 2 and len(shared) >= 2:
        a, b = models
        for i in range(len(shared)):
            for j in range(i + 1, len(shared)):
                s1, s2 = shared[i], shared[j]
                d1 = cells[(a, s1)] - cells[(b, s1)]
                d2 = cells[(a, s2)] - cells[(b, s2)]
                if d1 * d2 < 0:  # sign of (A-B) flips between s1 and s2 -> rank reversal
                    reversals.append({"scenario_1": s1, "scenario_2": s2,
                                      "winner_1": a if d1 < 0 else b,
                                      "winner_2": a if d2 < 0 else b})
    # descriptive eta-squared (n=1/cell: interaction == residual; NOT an inferential test)
    vals = list(cells.values())
    gm = _mean(vals)
    ss_total = sum((v - gm) ** 2 for v in vals) if vals else 0.0
    eta = None
    if ss_total > 0:
        row_means = {m: _mean([cells[(m, s)] for s in shared]) for m in models}
        col_means = {s: _mean([cells[(m, s)] for m in models]) for s in shared}
        ss_model = len(shared) * sum((row_means[m] - gm) ** 2 for m in models)
        ss_scn = len(models) * sum((col_means[s] - gm) ** 2 for s in shared)
        ss_inter = max(0.0, ss_total - ss_model - ss_scn)
        eta = {"model": round(ss_model / ss_total, 3),
               "scenario": round(ss_scn / ss_total, 3),
               "interaction": round(ss_inter / ss_total, 3)}
    return {"models": models, "scenarios": shared, "rank_reversals": reversals,
            "eta_squared_descriptive": eta,
            "note": ("rank reversal == disordinal interaction (Loftus 1978); eta-squared is "
                     "DESCRIPTIVE only -- at n=1/cell the interaction is not inferentially "
                     "testable (Alin & Kurt 2006), residual is folded into 'interaction'.")}


def _simpson(topo: dict) -> dict:
    """The +0.73 (all) vs -0.93 (congested) sign flip = Simpson's paradox. Report Pearson
    all + congested-only + Spearman + leave-one-out (leverage), per model and pooled."""
    substrate = topo["substrate"]
    out = {}
    pooled_x, pooled_y = [], []
    pooled_cx, pooled_cy = [], []   # pooled CONGESTED points (across models) -> the honest r
    for m, cells in topo["matrix"].items():
        xs = [substrate[s]["gridlock_proxy"] for s in cells]
        ys = [-cells[s]["delay_rel_pct"] for s in cells]     # +win = delay reduction
        cong = [(substrate[s]["gridlock_proxy"], -cells[s]["delay_rel_pct"])
                for s in cells if not substrate[s]["free_flowing"]]
        cx = [p[0] for p in cong]
        cy = [p[1] for p in cong]
        out[m] = {
            "pearson_all": round(_pearson(xs, ys), 3) if _pearson(xs, ys) is not None else None,
            "spearman_all": round(_spearman(xs, ys), 3) if _spearman(xs, ys) is not None else None,
            "pearson_congested_only": round(_pearson(cx, cy), 3) if _pearson(cx, cy) is not None else None,
            "congested_note": "per-model congested r uses only 2 points -> trivially +/-1; use pooled below",
            "leave_one_out_pearson_all": _leave_one_out_pearson(xs, ys),
            "n_points": len(xs), "n_congested": len(cx)}
        pooled_x += xs
        pooled_y += ys
        pooled_cx += cx
        pooled_cy += cy
    out["_pooled"] = {
        "pearson_all": round(_pearson(pooled_x, pooled_y), 3),
        "spearman_all": round(_spearman(pooled_x, pooled_y), 3),
        "pearson_congested_only": round(_pearson(pooled_cx, pooled_cy), 3) if _pearson(pooled_cx, pooled_cy) is not None else None,
        "n_congested_points": len(pooled_cx),
        "note": ("sign-reversing Simpson's paradox (Yule-Simpson): pooled ALL r is positive "
                 "but the within-congested r (4 pooled points) is NEGATIVE -- Bloomsbury has "
                 "more gridlock than Euston yet a smaller win. The pooled-all number is "
                 "confounded by the free-vs-congested split; the within-congested r is the "
                 "honest primary. An r on 4 points is uninterpretable alone (report Spearman "
                 "+ leave-one-out).")}
    return out


# --------------------------------------------------------------------------- #
# 2. MODEL x CONFIG matrix (Euston) -- from experiment_sweep.json
# --------------------------------------------------------------------------- #
def _config_matrix() -> dict:
    d = _load("experiment_sweep.json")
    base = (d.get("baseline") or {}).get("metrics", {}).get("mean_network_delay_s")
    cells = d.get("cells", {})
    matrix = {}
    for m, cfgs in cells.items():
        for cfg, c in cfgs.items():
            if not isinstance(c, dict) or c.get("skipped"):
                matrix.setdefault(m, {})[cfg] = {"skipped": True}
                continue
            delay = (c.get("metrics") or {}).get("mean_network_delay_s")
            rel = round((delay - base) / base * 100, 1) if (delay and base) else None
            matrix.setdefault(m, {})[cfg] = {
                "delay_s": round(delay, 1) if delay else None, "delay_rel_pct": rel,
                "status": (c.get("verdict") or {}).get("status")}
    return {"baseline_delay_s": round(base, 1) if base else None, "matrix": matrix,
            "note": "model x config on the Euston corridor (n=1 seed, descriptive)."}


# --------------------------------------------------------------------------- #
# 3. WIN RATE (HELM-style) across every scenario a model was run on
# --------------------------------------------------------------------------- #
def _win_rates(topo_matrix: dict, cfg_matrix: dict) -> dict:
    out = {}
    # topology axis
    for m, cells in topo_matrix.items():
        wins = sum(1 for s in cells if cells[s]["delay_rel_pct"] < 0)
        out.setdefault(m, {})["topology"] = {"wins": wins, "n": len(cells),
                                             "win_rate": round(wins / len(cells), 3)}
    # config axis (Euston)
    for m, cells in cfg_matrix.items():
        run = {s: c for s, c in cells.items() if not c.get("skipped") and c.get("delay_rel_pct") is not None}
        if run:
            wins = sum(1 for s in run if run[s]["delay_rel_pct"] < 0)
            out.setdefault(m, {})["config_euston"] = {"wins": wins, "n": len(run),
                                                      "win_rate": round(wins / len(run), 3)}
    return out


def analyse() -> dict:
    topo = _topology_matrix()
    scenarios = list(topo["substrate"])
    cfg = _config_matrix()
    result = {
        "experiment": "model_scenario_differentiation",
        "purpose": ("WHY models differ across scenarios (supervisor request): interaction, "
                    "Simpson's paradox, win rate, variance decomposition, activity -- "
                    "methodology-grounded, DESCRIPTIVE (n=1/cell)."),
        "topology_matrix": topo["matrix"],
        "topology_substrate": topo["substrate"],
        "topology_activity": topo["activity"],
        "interaction": _interaction(topo["matrix"], scenarios),
        "simpson": _simpson(topo),
        "config_matrix": cfg["matrix"],
        "config_baseline_delay_s": cfg["baseline_delay_s"],
        "win_rates": _win_rates(topo["matrix"], cfg["matrix"]),
        "caveats": [
            "Every cell is n=1 seed (except the separate 5-seed robustness axis). DESCRIPTIVE "
            "only; no inferential interaction test, no cross-seed CI (Agarwal 2021).",
            "Topology axis covers 2 models (qwen2.5-0.5b, qwen3-0.6b); config axis covers 4 "
            "models on Euston. Coverage differs by axis -- not a single balanced grid.",
            "A Pearson r on 4 topology points is reported only with Spearman + leave-one-out; "
            "the pooled-vs-stratified sign flip is Simpson's paradox, stratified is primary.",
        ],
    }
    return result


if __name__ == "__main__":
    r = analyse()
    out = os.path.join(RESULTS, "model_scenario_analysis.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(r, fh, indent=2)
    # console summary
    print("MODEL x TOPOLOGY (delay change %, negative = win):")
    subs = r["topology_substrate"]
    for m, cells in r["topology_matrix"].items():
        row = "  %-13s " % m + " ".join(
            "%s=%+.1f%%(%s)" % (s, cells[s]["delay_rel_pct"], cells[s]["joint_verdict"][:4])
            for s in cells)
        print(row)
    print("\nINTERACTION rank reversals:", r["interaction"]["rank_reversals"])
    print("eta^2 (descriptive):", r["interaction"]["eta_squared_descriptive"])
    print("\nSIMPSON (gridlock vs win):")
    for m, s in r["simpson"].items():
        if m == "_pooled":
            print("  POOLED pearson=%s spearman=%s" % (s["pearson_all"], s["spearman_all"]))
        else:
            print("  %-13s pearson_all=%s congested_only=%s spearman=%s LOO=%s"
                  % (m, s["pearson_all"], s["pearson_congested_only"], s["spearman_all"],
                     s["leave_one_out_pearson_all"]))
    print("\nWIN RATES:", json.dumps(r["win_rates"]))
    print("\nwrote", out)
