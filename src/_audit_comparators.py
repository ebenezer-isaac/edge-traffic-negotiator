"""Recompute every closed-loop cell against BOTH comparators: MaxPressure and fixed-time."""
import json, glob, os, math
import numpy as np
from scipy import stats

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")

# MaxPressure per (topology, seed)
mp = {}
for f in glob.glob(os.path.join(RES, "frontier_raw", "BASELINE__*.json")):
    d = json.load(open(f))
    mp[(d["topology"], d["seed"])] = d["mean_network_delay_s"]

# fixed-time per (topology, seed) from both artifacts
ft = {}
for name in ("experiment_fixedtime_seed30.json", "experiment_fixedtime_calibrated.json"):
    p = os.path.join(RES, name)
    if os.path.exists(p):
        for c in json.load(open(p))["cells"]:
            ft[(c["topology"], c["seed"])] = c["fixedtime_delay_s"]

ARMS = ["qwen3-0.6b-ft1", "qwen3-0.6b-ft0", "phi4mini-gen-gpu"]
TOPS = ["euston_peakhour", "bloomsbury_grid", "oldstreet_junction",
        "bloomsbury_calibrated", "euston_peakhour_calibrated"]

def arm_cells(model, topo):
    out = {}
    for f in glob.glob(os.path.join(RES, "frontier_raw", f"{model}__{topo}__*.json")):
        d = json.load(open(f))
        if d.get("topology") != topo or d.get("model") != model:
            continue
        if d.get("slm_delay_s") is None:
            continue
        out[d["seed"]] = d["slm_delay_s"]
    return out

def stat_block(arm_delay, comp, seeds):
    a = np.array([arm_delay[s] for s in seeds], float)
    b = np.array([comp[(topo, s)] for s in seeds], float)
    rel = (a - b) / b * 100.0
    n = len(seeds)
    m = rel.mean()
    se = rel.std(ddof=1) / math.sqrt(n)
    tcrit = stats.t.ppf(0.975, n - 1)
    tp = stats.ttest_rel(a, b).pvalue
    try:
        wp = stats.wilcoxon(a, b).pvalue
    except Exception:
        wp = float("nan")
    return n, m, m - tcrit * se, m + tcrit * se, tp, wp

print(f"{'arm':18s} {'topology':26s} {'comp':6s} {'n':>3s} {'rel%':>8s} {'95% CI':>20s} {'p_t':>9s} {'p_wil':>9s}")
print("-" * 112)
for topo in TOPS:
    for model in ARMS:
        cells = arm_cells(model, topo)
        if not cells:
            continue
        for label, comp in (("MP", mp), ("FT", ft)):
            seeds = sorted(s for s in cells if (topo, s) in comp)
            if len(seeds) < 3:
                print(f"{model:18s} {topo:26s} {label:6s}  -- no comparator ({len(seeds)} seeds)")
                continue
            n, m, lo, hi, tp, wp = stat_block(cells, comp, seeds)
            print(f"{model:18s} {topo:26s} {label:6s} {n:3d} {m:+8.2f} [{lo:+7.2f},{hi:+7.2f}] {tp:9.4g} {wp:9.4g}")
    print()

# head-to-head ft vs stock on each topology
print("=== head-to-head: qwen ft1 vs qwen stock (ft0 is the STOCK arm? verify) ===")
for topo in TOPS:
    a = arm_cells("qwen3-0.6b-ft1", topo)
    b = arm_cells("qwen3-0.6b-ft0", topo)
    seeds = sorted(set(a) & set(b))
    if len(seeds) < 3:
        continue
    x = np.array([a[s] for s in seeds]); y = np.array([b[s] for s in seeds])
    rel = (x - y) / y * 100
    n = len(seeds); m = rel.mean(); se = rel.std(ddof=1)/math.sqrt(n)
    tc = stats.t.ppf(0.975, n-1)
    print(f"{topo:26s} n={n:3d} rel={m:+7.2f} [{m-tc*se:+7.2f},{m+tc*se:+7.2f}] "
          f"p={stats.ttest_rel(x,y).pvalue:.3g} wins={int((rel<0).sum())}/{n}")
