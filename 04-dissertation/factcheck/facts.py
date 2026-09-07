# -*- coding: utf-8 -*-
"""Deterministic fact registry: every quantity the report may quote, computed
from the committed experiment artifacts with an explicit provenance record.

Conventions (EXAMINER-REVIEW-PROMPT.md, MASTER-SPEC):
  * frontier_raw/BASELINE__<topo>__s<seed>.json is MaxPressure (served_by.slm == 0).
  * fixed-time floor lives only in experiment_fixedtime_{seed30,calibrated,guards}.json.
  * evaluation seeds = {1..30} \\ {3,7,11,29} U {31,32,33,34}  (n=30).
  * qwen3-0.6b-ft0 = stock control, ft1 = deployed fine-tuned student,
    phi4mini-gen-gpu = fine-tuned 3.8B; config 'sota' unless stated.
  * authored share = served_by.slm/decisions; acceptance = slm_proposal_served/
    slm_valid_proposals; divergence = slm_diverged_and_served/slm_proposal_served.
  * delay effect = one-sample t on per-seed RELATIVE change, CI on the same.
    Paired t on absolute delays and Wilcoxon on paired delays are also computed
    and registered separately so the report can show which convention a
    printed number follows.

Each fact: {id, value, renders:[str], prov:{artifacts:[...], method:str}}.
Renders are the exact strings the report is allowed to print for this fact
(e.g. 15.51 -> ['15.5', '+15.5']). Matching is on rendered strings.
"""
import io, os, re, json, glob, math, hashlib, statistics
import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RES = os.path.join(REPO, "03-implementation", "edge-negotiator", "results")

DISJOINT = sorted((set(range(1, 31)) - {3, 7, 11, 29}) | {31, 32, 33, 34})
ARMS = {"qwen ft": "qwen3-0.6b-ft1", "qwen stock": "qwen3-0.6b-ft0", "phi ft": "phi4mini-gen-gpu"}
TOPOS = ["euston_peakhour", "bloomsbury_grid", "oldstreet_junction",
         "bloomsbury_calibrated", "euston_peakhour_calibrated"]
UNCAL = TOPOS[:3]

_sha = {}
FACTS = []


def sha(path):
    rel = os.path.relpath(path, RES).replace("\\", "/")
    if rel not in _sha:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _sha[rel] = h.hexdigest()[:12]
    return rel


def load(path):
    return json.load(io.open(path, encoding="utf-8"))


def add(fid, value, renders, artifacts, method):
    if value is None:
        return
    if isinstance(value, np.integer):
        value = int(value)
    elif isinstance(value, (np.floating, float)):
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            return
    FACTS.append({"id": fid, "value": value, "renders": sorted(set(r for r in renders if r)),
                  "prov": {"artifacts": sorted(set(artifacts)), "method": method}})


# ---------- render helpers (null-safe) ----------
def _num(x):
    try:
        return None if x is None else float(x)
    except (TypeError, ValueError):
        return None


def r_signed(x, nd=1):
    x = _num(x)
    if x is None or math.isnan(x):
        return []
    s = f"{x:+.{nd}f}"
    return [s, s.lstrip("+"), s.replace("-", "−")]


def r_plain(x, nd=1):
    """Round-half-even (Python default) and round-half-up renders, so a tie like
    3.25 -> '3.2' and '3.3' are both accepted and both traceable."""
    x = _num(x)
    if x is None or math.isnan(x):
        return []
    from decimal import Decimal, ROUND_HALF_UP
    hu = str(Decimal(repr(x)).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))
    return sorted({f"{x:.{nd}f}", hu})


def r_pct_share(x):  # 0.6431 -> '0.64', also '64' (as a percentage in prose)
    x = _num(x)
    if x is None or math.isnan(x):
        return []
    return r_plain(x, 2) + [str(int(round(x * 100)))]


def r_p(p):
    p = _num(p)
    if p is None or math.isnan(p):
        return []
    out = []
    if p < 0.001:
        m, e = f"{p:.1e}".split("e")
        out += [m, str(int(e)), f"{float(m):.0f}", f"{p:.1e}".replace("e-0", "e-")]
    for nd in (2, 3, 4):
        s = f"{p:.{nd}f}"
        out += [s, s.lstrip("0")]
    return out


def r_int(n):
    n = _num(n)
    if n is None or math.isnan(n):
        return []
    return [str(int(n)), f"{int(n):,}", f"{int(n):,}".replace(",", "{,}")]


# ---------- artifact loaders ----------
def maxpressure():
    mp = {}
    files = []
    for f in glob.glob(os.path.join(RES, "frontier_raw", "BASELINE__*.json")):
        d = load(f)
        assert d["decision_stats"]["served_by"]["slm"] == 0, f
        mp[(d["topology"], d["seed"])] = d
        files.append(sha(f))
    return mp, files


def fixedtime():
    ft, files = {}, []
    for name in ("experiment_fixedtime_seed30.json", "experiment_fixedtime_calibrated.json",
                 "experiment_fixedtime_guards.json"):
        p = os.path.join(RES, name)
        if not os.path.exists(p):
            continue
        files.append(sha(p))
        for c in load(p)["cells"]:
            key = (c["topology"], c["seed"])
            prev = ft.get(key, {})
            prev.update(c)
            ft[key] = prev
    return ft, files


def arm_cells(model, topo, config="sota"):
    out, files = {}, []
    for f in glob.glob(os.path.join(RES, "frontier_raw", f"{model}__{topo}__{config}__s*.json")):
        d = load(f)
        if d.get("slm_delay_s") is None or d.get("model") != model or d.get("topology") != topo:
            continue
        out[d["seed"]] = d
        files.append(sha(f))
    return out, files


def rel_stats(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    rel = (a - b) / b * 100.0
    n = len(rel); m = rel.mean(); se = rel.std(ddof=1) / math.sqrt(n)
    tc = stats.t.ppf(0.975, n - 1)
    return {"n": n, "rel": m, "lo": m - tc * se, "hi": m + tc * se,
            "p_t1": stats.ttest_1samp(rel, 0).pvalue,
            "p_tpaired_abs": stats.ttest_rel(a, b).pvalue,
            "p_w": stats.wilcoxon(a, b).pvalue if np.any(a != b) else float("nan"),
            "median": float(np.median(rel)), "wins": int((rel < 0).sum()),
            "mean_a": a.mean(), "mean_b": b.mean(), "abs_diff": (a - b).mean(),
            "abs_rel": (a.mean() - b.mean()) / b.mean() * 100.0}


def register_effect(prefix, st, arts, method):
    add(prefix + ".rel", st["rel"], r_signed(st["rel"], 1) + r_signed(st["rel"], 2) + r_plain(abs(st["rel"]), 1), arts, method + "; mean per-seed relative change % (unsigned render allowed)")
    hw = (st["hi"] - st["lo"]) / 2
    alt_lo = round(st["rel"], 1) - round(hw, 1); alt_hi = round(st["rel"], 1) + round(hw, 1)
    add(prefix + ".ci_lo", st["lo"], r_signed(st["lo"], 1) + r_signed(st["lo"], 2) + r_signed(alt_lo, 1), arts, method + "; 95% CI lower (one-sample t on rel; alt render = round(mean)-round(halfwidth))")
    add(prefix + ".ci_hi", st["hi"], r_signed(st["hi"], 1) + r_signed(st["hi"], 2) + r_signed(alt_hi, 1), arts, method + "; 95% CI upper (alt render = round(mean)+round(halfwidth))")
    add(prefix + ".p_t1", st["p_t1"], r_p(st["p_t1"]), arts, method + "; one-sample t on rel, p")
    add(prefix + ".p_tpaired_abs", st["p_tpaired_abs"], r_p(st["p_tpaired_abs"]), arts, method + "; paired t on absolute delays, p")
    add(prefix + ".p_w", st["p_w"], r_p(st["p_w"]) if not math.isnan(st["p_w"]) else [], arts, method + "; Wilcoxon signed-rank on paired delays, p")
    add(prefix + ".median", st["median"], r_signed(st["median"], 1), arts, method + "; median per-seed rel %")
    add(prefix + ".wins", st["wins"], r_int(st["wins"]), arts, method + "; seeds with rel<0")
    add(prefix + ".n", st["n"], r_int(st["n"]), arts, method + "; n seeds")
    add(prefix + ".abs_rel", st["abs_rel"], r_signed(st["abs_rel"], 1), arts, method + "; relative change of MEANS (absolute convention)")
    add(prefix + ".abs_diff_s", st["abs_diff"], r_signed(st["abs_diff"], 1), arts, method + "; mean absolute delay difference s")


def build():
    FACTS.clear()
    mp, mp_files = maxpressure()
    ft, ft_files = fixedtime()

    # --- seeds / horizon constants ---
    add("seeds.disjoint_n", len(DISJOINT), r_int(30), [], "|{1..30} \\ {3,7,11,29} U {31..34}|")
    add("seeds.pooled_n", 90, r_int(90), [], "3 topologies x 30 seeds")
    any_mp = next(iter(mp.values()))
    add("sim.steps", any_mp["metrics"]["sim_steps"], r_int(any_mp["metrics"]["sim_steps"]), mp_files[:1], "BASELINE metrics.sim_steps")

    # --- MaxPressure vs fixed-time per topology (tab:mpfloor) ---
    for topo in TOPOS:
        seeds = [s for s in DISJOINT if (topo, s) in mp and (topo, s) in ft]
        if len(seeds) < 3:
            continue
        a = [mp[(topo, s)]["mean_network_delay_s"] for s in seeds]
        b = [ft[(topo, s)]["fixedtime_delay_s"] for s in seeds]
        st = rel_stats(a, b)
        arts = mp_files + ft_files
        register_effect(f"mpfloor.{topo}", st, arts, f"MaxPressure vs fixed-time, {topo}, disjoint seeds")
        add(f"mpfloor.{topo}.mp_mean_s", st["mean_a"], r_plain(st["mean_a"], 1), arts, "mean MaxPressure delay s over disjoint seeds")
        add(f"mpfloor.{topo}.ft_mean_s", st["mean_b"], r_plain(st["mean_b"], 1), arts, "mean fixed-time delay s over disjoint seeds")
        rel = (np.array(a) - np.array(b)) / np.array(b) * 100
        add(f"mpfloor.{topo}.max_seed_rel", rel.max(), r_signed(rel.max(), 1), arts, "largest single-seed rel %")

    # --- closed-loop arms vs both comparators, authorship, guards ---
    for label, model in ARMS.items():
        for topo in TOPOS:
            cells, files = arm_cells(model, topo)
            seeds = [s for s in DISJOINT if s in cells]
            if len(seeds) < 3:
                continue
            arts = files + mp_files + ft_files
            a = [cells[s]["slm_delay_s"] for s in seeds]
            key = f"arm.{label.replace(' ', '_')}.{topo}"
            if all((topo, s) in ft for s in seeds):
                register_effect(key + ".vsFT", rel_stats(a, [ft[(topo, s)]["fixedtime_delay_s"] for s in seeds]), arts, f"{label} vs fixed-time, {topo}")
            if all((topo, s) in mp for s in seeds):
                register_effect(key + ".vsMP", rel_stats(a, [mp[(topo, s)]["mean_network_delay_s"] for s in seeds]), arts, f"{label} vs MaxPressure, {topo}")
            ds = [cells[s]["decision_stats"] for s in seeds]
            dec = np.array([d["decisions"] for d in ds], float)
            slm = np.array([d["served_by"]["slm"] for d in ds], float)
            shield = np.array([d["served_by"]["shield"] for d in ds], float)
            anti = np.array([d["served_by"]["anti_starvation"] for d in ds], float)
            valid = np.array([d["slm_valid_proposals"] for d in ds], float)
            served = np.array([d["slm_proposal_served"] for d in ds], float)
            div = np.array([d["slm_diverged_and_served"] for d in ds], float)
            auth = (slm / dec).mean(); asr = (anti / dec).mean(); shr = (shield / dec).mean()
            acc = np.nanmean(np.where(valid > 0, served / np.where(valid > 0, valid, 1), np.nan))
            dv = np.nanmean(np.where(served > 0, div / np.where(served > 0, served, 1), np.nan))
            m = "mean over disjoint seeds of per-seed ratio; " + f"{label} {topo} config sota"
            add(key + ".authored_share", auth, r_pct_share(auth), files, m + "; served_by.slm/decisions")
            add(key + ".floor_share", asr, r_pct_share(asr) + r_plain(asr * 100, 1), files, m + "; anti_starvation/decisions (also as %)")
            add(key + ".shield_share_pct", shr * 100, r_plain(shr * 100, 2), files, m + "; shield/decisions as %")
            add(key + ".shield_total", shield.sum(), r_int(shield.sum()), files, "total shield substitutions over disjoint seeds")
            add(key + ".shield_worst_seed_pct", (shield / dec).max() * 100, r_plain((shield / dec).max() * 100, 2), files, "worst single-seed shield share %")
            add(key + ".acceptance", acc, r_pct_share(acc), files, m + "; slm_proposal_served/slm_valid_proposals")
            add(key + ".divergence", dv, r_pct_share(dv), files, m + "; slm_diverged_and_served/slm_proposal_served")
            met = [cells[s]["metrics"] for s in seeds]
            comp = np.array([x["completed"] for x in met], float); loaded = np.array([x["loaded"] for x in met], float)
            add(key + ".loaded", loaded.mean(), r_int(round(loaded.mean())), files, "metrics.loaded (constant per topology)")
            add(key + ".completion_pct", (comp / loaded).mean() * 100, r_plain((comp / loaded).mean() * 100, 1) + r_int(round((comp / loaded).mean() * 100)), files, "mean completed/loaded %")
            add(key + ".completed_mean", comp.mean(), r_int(round(comp.mean())), files, "mean completed vehicles")
            add(key + ".teleports", np.mean([x["teleports"] for x in met]), r_plain(np.mean([x["teleports"] for x in met]), 1) + r_plain(np.mean([x["teleports"] for x in met]), 2), files, "mean teleports")
            add(key + ".undeparted", np.mean([x["undeparted"] for x in met]), r_plain(np.mean([x["undeparted"] for x in met]), 1) + r_int(round(np.mean([x["undeparted"] for x in met]))), files, "mean undeparted")
            # latency variants
            p50s = [cells[s]["latency_summary"]["p50"] for s in seeds if cells[s].get("latency_summary")]
            p99s = [cells[s]["latency_summary"]["p99"] for s in seeds if cells[s].get("latency_summary")]
            mxs = [cells[s]["latency_summary"]["max"] for s in seeds if cells[s].get("latency_summary")]
            if p50s:
                add(key + ".lat.p50_median_of_cells", statistics.median(p50s), r_plain(statistics.median(p50s), 2), files, "median over cells of per-cell p50 s")
                add(key + ".lat.p50_min", min(p50s), r_plain(min(p50s), 2), files, "min per-cell p50 s")
                add(key + ".lat.p50_max", max(p50s), r_plain(max(p50s), 2), files, "max per-cell p50 s")
                add(key + ".lat.p99_max", max(p99s), r_plain(max(p99s), 2), files, "worst per-cell p99 s")
                add(key + ".lat.worst_call", max(mxs), r_plain(max(mxs), 2), files, "max single latency s")
            # valid proposals / decisions totals (stock calibrated: 484 of 546)
            add(key + ".valid_proposals_mean", valid.mean(), r_int(round(valid.mean())), files, "mean slm_valid_proposals")
            add(key + ".decisions_mean", dec.mean(), r_int(round(dec.mean())), files, "mean decisions")

        # pooled n=90 over uncalibrated topologies
        a, bft, bmp = [], [], []
        for topo in UNCAL:
            cells, _ = arm_cells(model, topo)
            for s in DISJOINT:
                if s in cells and (topo, s) in ft and (topo, s) in mp:
                    a.append(cells[s]["slm_delay_s"]); bft.append(ft[(topo, s)]["fixedtime_delay_s"]); bmp.append(mp[(topo, s)]["mean_network_delay_s"])
        if len(a) >= 30:
            register_effect(f"arm.{label.replace(' ', '_')}.pooled.vsFT", rel_stats(a, bft), mp_files + ft_files, f"{label} pooled 3 topologies vs fixed-time")
            register_effect(f"arm.{label.replace(' ', '_')}.pooled.vsMP", rel_stats(a, bmp), mp_files + ft_files, f"{label} pooled 3 topologies vs MaxPressure")

    # per-arm latency pooled over the three uncalibrated topologies and over all five
    for label, model in ARMS.items():
        for scope, tl in (("uncal", UNCAL), ("all", TOPOS)):
            p50s, p99s, mxs, pooled = [], [], [], []
            for topo in tl:
                cells, files = arm_cells(model, topo)
                for s in DISJOINT:
                    c = cells.get(s)
                    if c and c.get("latency_summary"):
                        p50s.append(c["latency_summary"]["p50"]); p99s.append(c["latency_summary"]["p99"]); mxs.append(c["latency_summary"]["max"])
                        pooled.extend(c.get("latencies_s") or [])
            if p50s:
                k = f"lat.{label.replace(' ', '_')}.{scope}"
                add(k + ".p50_median_of_cells", statistics.median(p50s), r_plain(statistics.median(p50s), 2), [], f"{label} {scope}: median of per-cell p50")
                add(k + ".p50_mean_of_cells", statistics.mean(p50s), r_plain(statistics.mean(p50s), 2), [], f"{label} {scope}: mean of per-cell p50")
                add(k + ".p50_pooled", float(np.median(pooled)), r_plain(float(np.median(pooled)), 2), [], f"{label} {scope}: median of all pooled call latencies")
                add(k + ".p50_min", min(p50s), r_plain(min(p50s), 2), [], f"{label} {scope}: min per-cell p50")
                add(k + ".p50_max", max(p50s), r_plain(max(p50s), 2), [], f"{label} {scope}: max per-cell p50")
                add(k + ".p99_max", max(p99s), r_plain(max(p99s), 2), [], f"{label} {scope}: worst per-cell p99")
                add(k + ".worst_call", max(mxs), r_plain(max(mxs), 2), [], f"{label} {scope}: max single call")
                add(k + ".calls_over_10s", int(sum(1 for x in pooled if x > 10)), r_int(sum(1 for x in pooled if x > 10)), [], f"{label} {scope}: calls exceeding 10 s")

    # --- head-to-head fine-tuned vs stock (same seeds) ---
    for topo in TOPOS:
        a, files_a = arm_cells("qwen3-0.6b-ft1", topo); b, files_b = arm_cells("qwen3-0.6b-ft0", topo)
        seeds = [s for s in DISJOINT if s in a and s in b]
        if len(seeds) >= 3:
            register_effect(f"h2h.qwen_ft_vs_stock.{topo}", rel_stats([a[s]["slm_delay_s"] for s in seeds], [b[s]["slm_delay_s"] for s in seeds]), files_a + files_b, f"qwen ft vs qwen stock, {topo}")
        c, files_c = arm_cells("phi4mini-gen-gpu", topo)
        seeds = [s for s in DISJOINT if s in c and s in b]
        if len(seeds) >= 3:
            register_effect(f"h2h.phi_ft_vs_stock.{topo}", rel_stats([c[s]["slm_delay_s"] for s in seeds], [b[s]["slm_delay_s"] for s in seeds]), files_c + files_b, f"phi ft vs qwen stock, {topo}")
        seeds = [s for s in DISJOINT if s in c and s in a]
        if len(seeds) >= 3:
            register_effect(f"h2h.phi_vs_qwen_ft.{topo}", rel_stats([c[s]["slm_delay_s"] for s in seeds], [a[s]["slm_delay_s"] for s in seeds]), files_c + files_a, f"phi ft vs qwen ft, {topo}")
        # floor share stock minus MP paired
        if b and all((topo, s) in mp for s in seeds):
            pass

    # floor-share differences stock vs MaxPressure, paired per seed (4 to 18 points)
    for topo in TOPOS:
        b, fb = arm_cells("qwen3-0.6b-ft0", topo)
        seeds = [s for s in DISJOINT if s in b and (topo, s) in mp]
        if len(seeds) >= 3:
            fs = np.array([b[s]["decision_stats"]["served_by"]["anti_starvation"] / b[s]["decision_stats"]["decisions"] for s in seeds])
            fm = np.array([mp[(topo, s)]["decision_stats"]["served_by"]["anti_starvation"] / mp[(topo, s)]["decision_stats"]["decisions"] for s in seeds])
            d = (fs - fm) * 100
            add(f"floor.stock_minus_mp.{topo}.points", d.mean(), r_plain(d.mean(), 1) + r_int(round(d.mean())), fb + mp_files, "stock floor share minus MaxPressure floor share, points, paired")
            add(f"floor.stock_minus_mp.{topo}.p", stats.ttest_1samp(d, 0).pvalue, r_p(stats.ttest_1samp(d, 0).pvalue), fb + mp_files, "one-sample t on paired floor-share difference")
        fm_all = [mp[(topo, s)]["decision_stats"]["served_by"]["anti_starvation"] / mp[(topo, s)]["decision_stats"]["decisions"] for s in DISJOINT if (topo, s) in mp]
        if fm_all:
            add(f"floor.mp.{topo}.share", np.mean(fm_all), r_pct_share(np.mean(fm_all)) + r_plain(np.mean(fm_all) * 100, 1), mp_files, "MaxPressure arm anti-starvation share")

    # --- fixed-time guard metrics per topology ---
    for topo in TOPOS:
        rows = [ft[(topo, s)] for s in DISJOINT if (topo, s) in ft and "completed" in ft[(topo, s)]]
        if rows:
            comp = np.array([r["completed"] for r in rows], float); loaded = np.array([r["loaded"] for r in rows], float)
            add(f"ftfloor.{topo}.loaded", loaded.mean(), r_int(round(loaded.mean())), ft_files, "fixed-time loaded vehicles")
            add(f"ftfloor.{topo}.completion_pct", (comp / loaded).mean() * 100, r_plain((comp / loaded).mean() * 100, 1), ft_files, "fixed-time completed/loaded %")
            add(f"ftfloor.{topo}.completed_mean", comp.mean(), r_int(round(comp.mean())), ft_files, "fixed-time mean completed")
            add(f"ftfloor.{topo}.teleports", np.mean([r["teleports"] for r in rows]), r_plain(np.mean([r["teleports"] for r in rows]), 1), ft_files, "fixed-time mean teleports")
            if all("undeparted" in r for r in rows):
                add(f"ftfloor.{topo}.undeparted", np.mean([r["undeparted"] for r in rows]), r_int(round(np.mean([r["undeparted"] for r in rows]))) + r_plain(np.mean([r["undeparted"] for r in rows]), 1), ft_files, "fixed-time mean undeparted")
        mrows = [mp[(topo, s)]["metrics"] for s in DISJOINT if (topo, s) in mp]
        if mrows:
            comp = np.array([r["completed"] for r in mrows], float); loaded = np.array([r["loaded"] for r in mrows], float)
            add(f"mp.{topo}.completion_pct", (comp / loaded).mean() * 100, r_plain((comp / loaded).mean() * 100, 1), mp_files, "MaxPressure completed/loaded %")
            add(f"mp.{topo}.completed_mean", comp.mean(), r_int(round(comp.mean())), mp_files, "MaxPressure mean completed")
            add(f"mp.{topo}.teleports", np.mean([r["teleports"] for r in mrows]), r_plain(np.mean([r["teleports"] for r in mrows]), 1), mp_files, "MaxPressure mean teleports")
            add(f"mp.{topo}.undeparted", np.mean([r["undeparted"] for r in mrows]), r_int(round(np.mean([r["undeparted"] for r in mrows]))) + r_plain(np.mean([r["undeparted"] for r in mrows]), 1), mp_files, "MaxPressure mean undeparted")
            add(f"mp.{topo}.loaded", loaded.mean(), r_int(round(loaded.mean())), mp_files, "loaded vehicles")

    # --- LQF baseline ---
    p = os.path.join(RES, "experiment_lqf.json")
    if os.path.exists(p):
        lq = load(p); arts = [sha(p)] + mp_files + ft_files
        by = {}
        for c in lq["cells"]:
            by[(c["topology"], c["seed"])] = c["lqf_delay_s"]
        for topo in TOPOS:
            seeds = [s for s in DISJOINT if (topo, s) in by and (topo, s) in mp]
            if len(seeds) >= 3:
                register_effect(f"lqf.{topo}.vsMP", rel_stats([by[(topo, s)] for s in seeds], [mp[(topo, s)]["mean_network_delay_s"] for s in seeds]), arts, f"LQF vs MaxPressure {topo}")
            seeds = [s for s in DISJOINT if (topo, s) in by and (topo, s) in ft]
            if len(seeds) >= 3:
                register_effect(f"lqf.{topo}.vsFT", rel_stats([by[(topo, s)] for s in seeds], [ft[(topo, s)]["fixedtime_delay_s"] for s in seeds]), arts, f"LQF vs fixed-time {topo}")

    # --- offline evaluation (tab:offline-full) ---
    evals = {"Qwen3-0.6B stock": "eval_qwen3-0.6b-ft0.json", "Qwen3-0.6B generalist ft": "eval_qwen3-0.6b-ft2.json",
             "Qwen3-0.6B sota-only ft1": "eval_qwen3-0.6b-ft1.json", "Qwen3-0.6B ft1 gpu": "eval_qwen3-0.6b-ft1gpu.json",
             "Qwen3-0.6B catalogue": "eval_qwen3-0.6b-generic-gpu_2.json",
             "Phi-4-mini stock": "eval_Phi-4-mini-instruct-generic-gpu_5.json", "Phi-4-mini generalist ft": "eval_phi4mini-gen-gpu.json",
             "Phi-4-mini LOTO": "eval_phi4mini-loto.json", "Phi-4-mini sota-specialist": "eval_phi4mini-sota.json",
             "Phi-4-mini myopic-specialist": "eval_phi4mini-myopic.json", "Phi-4-mini prediction-specialist": "eval_phi4mini-prediction.json",
             "Phi-4-mini coordination-specialist": "eval_phi4mini-coordination.json"}
    acc = {}
    for row, fn in evals.items():
        p = os.path.join(RES, "ft_dataset", fn)
        if not os.path.exists(p):
            continue
        d = load(p); a = [sha(p)]
        for fmt, v in d["formats"].items():
            acc[(row, fmt)] = v["accuracy"] * 100
            add(f"offline.{row}.{fmt}.acc", v["accuracy"] * 100, r_plain(v["accuracy"] * 100, 1) + r_plain(v["accuracy"] * 100, 2), a, f"{fn} formats.{fmt}.accuracy x100")
            add(f"offline.{row}.{fmt}.strict_json", v["strict_json_rate"] * 100, r_plain(v["strict_json_rate"] * 100, 1) + r_int(round(v["strict_json_rate"] * 100)), a, f"{fn} strict_json_rate x100")
            add(f"offline.{row}.{fmt}.n", v["n"], r_int(v["n"]), a, f"{fn} formats.{fmt}.n")
    # derived offline facts
    def dacc(r1, r2, fmt):
        return acc[(r1, fmt)] - acc[(r2, fmt)]
    for fmt in ("myopic", "sota", "prediction", "coordination"):
        if ("Qwen3-0.6B generalist ft", fmt) in acc and ("Qwen3-0.6B stock", fmt) in acc:
            add(f"offline.gain.qwen.{fmt}", dacc("Qwen3-0.6B generalist ft", "Qwen3-0.6B stock", fmt), r_signed(dacc("Qwen3-0.6B generalist ft", "Qwen3-0.6B stock", fmt), 1), [], "qwen generalist ft minus stock, points")
            add(f"offline.gain.phi.{fmt}", dacc("Phi-4-mini generalist ft", "Phi-4-mini stock", fmt), r_signed(dacc("Phi-4-mini generalist ft", "Phi-4-mini stock", fmt), 1), [], "phi generalist ft minus stock, points")
            add(f"offline.gap.phi_minus_qwen_ft.{fmt}", dacc("Phi-4-mini generalist ft", "Qwen3-0.6B generalist ft", fmt), r_signed(dacc("Phi-4-mini generalist ft", "Qwen3-0.6B generalist ft", fmt), 1) + r_plain(abs(dacc("Phi-4-mini generalist ft", "Qwen3-0.6B generalist ft", fmt)), 1), [], "3.8B minus 0.6B generalist, points")
    if ("Qwen3-0.6B generalist ft", "myopic") in acc:
        p_hat = 0.88; n = 1510
        add("offline.se_two_prop", math.sqrt(2 * p_hat * (1 - p_hat) / n) * 100, r_plain(math.sqrt(2 * p_hat * (1 - p_hat) / n) * 100, 1), [], "two-proportion SE at p=.88, n=1510, points")

    # --- dataset build ---
    p = os.path.join(RES, "ft_dataset", "build_stats.json")
    if os.path.exists(p):
        b = load(p); a = [sha(p)]
        add("dataset.accepted", b["accepted"], r_int(b["accepted"]), a, "build_stats.accepted")
        rej = sum(b["rejected"].values())
        add("dataset.rejected", rej, r_int(rej), a, "sum build_stats.rejected")
        for k, v in b["by_format"].items():
            add(f"dataset.by_format.{k}", v, r_int(v), a, f"build_stats.by_format.{k}")
    tot_states = 0
    for fn, k in (("states_unique.json", "sota_myopic"), ("states_unique_pred.json", "prediction"), ("states_unique_coord.json", "coordination")):
        p = os.path.join(RES, "ft_dataset", fn)
        if os.path.exists(p):
            d = load(p); a = [sha(p)]
            add(f"dataset.states.{k}", d["n"], r_int(d["n"]), a, f"{fn} n unique states"); tot_states += d["n"]
            add(f"dataset.holdout_states.{k}", d["n_holdout"], r_int(d["n_holdout"]), a, f"{fn} n_holdout")
            add("dataset.holdout_mod", d["holdout_mod"], r_int(d["holdout_mod"]), a, "holdout_mod")
    if tot_states:
        add("dataset.states.total", tot_states, r_int(tot_states), [], "sum of unique states over the three pools")
    for fn, k in (("holdout.jsonl", "holdout"), ("train.jsonl", "train")):
        p = os.path.join(RES, "ft_dataset", fn)
        if os.path.exists(p):
            n = sum(1 for _ in io.open(p, encoding="utf-8"))
            add(f"dataset.{k}_rows", n, r_int(n), [sha(p)], f"line count of {fn}")

    # --- retention (MMLU sample) ---
    ret = {"phi stock": "retention_Phi-4-mini-instruct-generic-gpu_5.json", "phi ft": "retention_phi4mini-gen-gpu.json",
           "qwen stock": "retention_qwen3-0.6b-ft0.json", "qwen ft2": "retention_qwen3-0.6b-ft2.json"}
    rv = {}
    for k, fn in ret.items():
        p = os.path.join(RES, "ft_dataset", fn)
        if os.path.exists(p):
            d = load(p); rv[k] = d
            add(f"retention.{k}.acc", d["accuracy"] * 100, r_plain(d["accuracy"] * 100, 1), [sha(p)], f"{fn} accuracy x100")
            add(f"retention.{k}.n", d["n"], r_int(d["n"]), [sha(p)], f"{fn} n")
    if "phi stock" in rv and "phi ft" in rv:
        p1, p2, n = rv["phi stock"]["accuracy"], rv["phi ft"]["accuracy"], rv["phi stock"]["n"]
        pp = (p1 + p2) / 2; z = (p1 - p2) / math.sqrt(2 * pp * (1 - pp) / n); pz = 2 * (1 - stats.norm.cdf(abs(z)))
        add("retention.phi.z", z, r_plain(z, 2), [], "two-proportion z, stock vs ft, n=200 each")
        add("retention.phi.p", pz, r_p(pz), [], "two-sided p for that z")

    # --- authorisation re-test ---
    auth = {"phi stock": "slm_auth_lee_Phi-4-mini-instruct-generic-gpu_5.json", "phi ft": "slm_auth_lee_phi4mini-gen-gpu.json",
            "qwen stock": "slm_auth_lee_qwen3-0.6b-ft0.json", "qwen ft2": "slm_auth_lee_qwen3-0.6b-ft2.json"}
    for k, fn in auth.items():
        p = os.path.join(RES, fn)
        if not os.path.exists(p):
            continue
        d = load(p); a = [sha(p)]
        add(f"auth.dataset_size", d["dataset_size"], r_int(d["dataset_size"]), a, "dataset_size")
        for arm, v in d["arms"].items():
            add(f"auth.{k}.{arm}.class_acc", v["class_accuracy"] * 100, r_plain(v["class_accuracy"] * 100, 1), a, f"{fn} arms.{arm}.class_accuracy x100")
            add(f"auth.{k}.{arm}.dangerous", v["dangerous_false_grants"], r_int(v["dangerous_false_grants"]), a, f"{fn} dangerous_false_grants")
            add(f"auth.{k}.{arm}.parse_fail", v["parse_fail"], r_int(v["parse_fail"]), a, f"{fn} parse_fail")
            fnr = _num(v.get("false_negative_rate")); fpr = _num(v.get("false_positive_rate"))
            if fnr is not None:
                add(f"auth.{k}.{arm}.fnr", fnr, r_plain(fnr, 1) + r_int(round(fnr * 100)), a, "false_negative_rate")
            if fpr is not None:
                add(f"auth.{k}.{arm}.fpr", fpr, r_plain(fpr, 2), a, "false_positive_rate")

    # --- emergency preemption ---
    p = os.path.join(RES, "emergency_metrics_n30.json")
    if os.path.exists(p):
        d = load(p); a = [sha(p)]
        for k in ("ev_benefit_s", "gate_cost_s", "attack_harm_avoided_s", "attack_worstcase_avoided_s"):
            add(f"ev.{k}.mean", d[k]["mean"], r_plain(d[k]["mean"], 1), a, f"{k}.mean")
            add(f"ev.{k}.ci_lo", d[k]["ci95"][0], r_plain(d[k]["ci95"][0], 1), a, f"{k}.ci95[0]")
            add(f"ev.{k}.ci_hi", d[k]["ci95"][1], r_plain(d[k]["ci95"][1], 1), a, f"{k}.ci95[1]")
        add("ev.n", d["n_seeds"], r_int(d["n_seeds"]), a, "n_seeds")

    # --- trust battery ---
    p = os.path.join(RES, "experiment_trust.json")
    if os.path.exists(p):
        d = load(p); a = [sha(p)]
        for name, traj in d.get("trajectories", {}).items():
            add(f"trust.traj.{name}.final", traj[-1], r_plain(traj[-1], 3) + r_plain(traj[-1], 2), a, f"trajectories.{name}[-1]")
            add(f"trust.traj.{name}.len", len(traj) - 1, r_int(len(traj) - 1), a, f"steps in trajectories.{name}")
        for k, v in d.get("params", {}).items():
            add(f"trust.param.{k}", v, r_plain(v, 2) + r_plain(v, 1), a, f"params.{k}")
        for k, v in d.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                add(f"trust.{k}", v, r_plain(v, 3) + r_plain(v, 2) + r_int(v) if float(v).is_integer() else r_plain(v, 3) + r_plain(v, 2), a, f"experiment_trust.{k}")
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    if isinstance(v2, (int, float)) and not isinstance(v2, bool):
                        add(f"trust.{k}.{k2}", v2, r_plain(v2, 3) + r_plain(v2, 2) + (r_int(v2) if float(v2).is_integer() else []), a, f"experiment_trust.{k}.{k2}")
    for model in ("qwen3-0.6b-ft1", "qwen3-0.6b-ft0", "phi4mini-gen-gpu"):
        p = os.path.join(RES, f"experiment_trust_traffic_{model}.json")
        if not os.path.exists(p):
            continue
        d = load(p); a = [sha(p)]
        for cell, v in d["cells"].items():
            topo, scen = cell.split("::")
            base = f"trusttraffic.{model}.{topo}.{scen}"
            add(base + ".delay_rel", v["mean_delay_rel_pct"], r_signed(v["mean_delay_rel_pct"], 1), a, f"{cell} mean_delay_rel_pct")
            if v.get("mean_lies_caught") is not None:
                add(base + ".caught", v["mean_lies_caught"], r_int(round(v["mean_lies_caught"])) + r_plain(v["mean_lies_caught"], 1), a, f"{cell} mean_lies_caught")
            if v.get("mean_liar_final_trust") is not None:
                add(base + ".final_trust", v["mean_liar_final_trust"], r_plain(v["mean_liar_final_trust"], 2) + r_plain(v["mean_liar_final_trust"], 3), a, f"{cell} mean_liar_final_trust")
            if v.get("mean_lies_injected") is not None:
                add(base + ".injected", v["mean_lies_injected"], r_int(round(v["mean_lies_injected"])), a, f"{cell} mean_lies_injected")
            add(base + ".n", v["n"], r_int(v["n"]), a, f"{cell} n")
        for topo in sorted({c.split("::")[0] for c in d["cells"]}):
            h = d["cells"].get(f"{topo}::honest"); bl = d["cells"].get(f"{topo}::blatant"); st = d["cells"].get(f"{topo}::stealth")
            if h and bl:
                add(f"trusttraffic.{model}.{topo}.blatant_minus_honest", bl["mean_delay_rel_pct"] - h["mean_delay_rel_pct"], r_signed(bl["mean_delay_rel_pct"] - h["mean_delay_rel_pct"], 1) + r_signed(bl["mean_delay_rel_pct"] - h["mean_delay_rel_pct"], 2), a, "blatant minus honest delay points")
            if h and st:
                add(f"trusttraffic.{model}.{topo}.stealth_minus_honest", st["mean_delay_rel_pct"] - h["mean_delay_rel_pct"], r_signed(st["mean_delay_rel_pct"] - h["mean_delay_rel_pct"], 1), a, "stealth minus honest delay points")

    # --- calibration probes ---
    p = os.path.join(RES, "bloomsbury_horizon_probe.json")
    if os.path.exists(p):
        d = load(p); a = [sha(p)]
        for end in (1200, 3600):
            rows = [r for r in d if r["end"] == end]
            add(f"calib.horizon.{end}.completion_pct", np.mean([r["completion_pct"] for r in rows]), r_plain(np.mean([r["completion_pct"] for r in rows]), 1) + r_int(round(np.mean([r["completion_pct"] for r in rows]))), a, f"mean completion_pct at end={end}")
            add(f"calib.horizon.{end}.teleports", np.mean([r["teleports"] for r in rows]), r_int(round(np.mean([r["teleports"] for r in rows]))) + r_plain(np.mean([r["teleports"] for r in rows]), 1), a, f"mean teleports at end={end}")
            add(f"calib.horizon.{end}.loaded", rows[0]["loaded"], r_int(rows[0]["loaded"]), a, "loaded")
    for fn in ("calibration_bloomsbury_grid.json", "calibration_euston_peakhour.json"):
        p = os.path.join(RES, fn)
        if os.path.exists(p):
            d = load(p); a = [sha(p)]
            for c in d["cells"]:
                k = f"calib.{d['topology']}.frac{int(round(c['frac'] * 100))}"
                add(k + ".completion_pct", c["completion_pct"], r_plain(c["completion_pct"], 1), a, f"{fn} frac={c['frac']} completion_pct")
                add(k + ".trips", c["trips"], r_int(c["trips"]), a, f"{fn} frac={c['frac']} trips")
                add(k + ".teleports", c["teleports"], r_plain(c["teleports"], 1) + r_int(round(c["teleports"])), a, f"{fn} teleports")
                add(k + ".frac_pct", c["frac"] * 100, r_int(round(c["frac"] * 100)), a, "frac x100")

    # --- failure forensics ---
    p = os.path.join(RES, "failure_forensics.json")
    if os.path.exists(p):
        d = load(p); a = [sha(p)]
        add("forensics.n_cells", d["n_cells"], r_int(d["n_cells"]), a, "n_cells")
        n_cat = len(d["catastrophic_cells"])
        add("forensics.n_catastrophic", n_cat, r_int(n_cat), a, "len(catastrophic_cells)")
        add("forensics.pct_catastrophic", n_cat / d["n_cells"] * 100, r_plain(n_cat / d["n_cells"] * 100, 1), a, "catastrophic share %")
        add("forensics.threshold", d["threshold_rel_pct"], r_int(d["threshold_rel_pct"]), a, "threshold_rel_pct")
        by_model = {}
        for c in d["catastrophic_cells"]:
            by_model[c["model"]] = by_model.get(c["model"], 0) + 1
            k = f"forensics.cell.{c['model']}.{c['topology']}.s{c['seed']}"
            add(k + ".rel", c["delay_rel_pct"], r_signed(c["delay_rel_pct"], 1), a, "delay_rel_pct")
            add(k + ".override", c["override_rate"], r_plain(c["override_rate"], 3), a, "override_rate (=divergence)")
            add(k + ".authored", c["authored_share"], r_plain(c["authored_share"], 3), a, "authored_share field (acceptance)")
            for f2, v in c.items():
                if isinstance(v, bool) or f2 in ("delay_rel_pct", "override_rate", "authored_share"):
                    continue
                if isinstance(v, (int, float)):
                    add(k + "." + f2, v, r_int(v) + r_plain(v, 1) + r_plain(v, 2) + r_plain(v, 3), a, f2)
                elif isinstance(v, dict):
                    for f3, v3 in v.items():
                        if isinstance(v3, (int, float)) and not isinstance(v3, bool):
                            add(k + "." + f2 + "." + f3, v3, r_int(v3) + r_plain(v3, 1) + r_plain(v3, 2), a, f2 + "." + f3)
        for m, n in by_model.items():
            add(f"forensics.by_model.{m}", n, r_int(n), a, f"catastrophic cells for {m}")
        pairs = d.get("catastrophic_pairs_cross_arm", [])
        add("forensics.n_pairs", len(pairs), r_int(len(pairs)), a, "len(catastrophic_pairs_cross_arm)")
        add("forensics.n_pairs_two_arms", sum(1 for x in pairs if x["n_catastrophic_arms"] == 2), r_int(sum(1 for x in pairs if x["n_catastrophic_arms"] == 2)), a, "pairs with two catastrophic arms")
        add("forensics.audit_chain_failures", len(d.get("audit_chain_failures", [])), r_int(len(d.get("audit_chain_failures", []))), a, "len(audit_chain_failures)")
        for s in d.get("arm_topology_summary", []):
            k = f"forensics.summary.{s['model']}.{s['topology']}"
            for f2 in ("rel_mean", "rel_median", "authored_mean", "override_mean", "antistarv_mean", "teleports_mean"):
                if f2 in s:
                    add(k + "." + f2, s[f2], r_plain(s[f2], 2) + r_plain(s[f2], 1) + r_plain(s[f2], 3), a, f2)

    # catastrophic counts per arm and topology from raw cells (>= +20% vs MP), incl calibrated
    for label, model in ARMS.items():
        for topo in TOPOS:
            cells, files = arm_cells(model, topo)
            seeds = [s for s in DISJOINT if s in cells and (topo, s) in mp]
            if seeds:
                n = sum(1 for s in seeds if (cells[s]["slm_delay_s"] - mp[(topo, s)]["mean_network_delay_s"]) / mp[(topo, s)]["mean_network_delay_s"] * 100 >= 20)
                add(f"catastrophic.{label.replace(' ', '_')}.{topo}", n, r_int(n), files + mp_files, f"{label} {topo}: seeds with rel vs MP >= +20%")

    # shared-cell agreement between the two fine-tuned students (90 cells)
    ident, close, differ = 0, 0, 0
    for topo in UNCAL:
        a, _ = arm_cells("qwen3-0.6b-ft1", topo); c, _ = arm_cells("phi4mini-gen-gpu", topo)
        for s in DISJOINT:
            if s in a and s in c:
                da, dc = a[s]["slm_delay_s"], c[s]["slm_delay_s"]
                if da == dc: ident += 1
                elif abs(da - dc) / dc * 100 <= 0.5: close += 1
                else: differ += 1
    add("convergence.identical", ident, r_int(ident), [], "ft1 vs phi cells with bit-identical mean delay (3 uncal topologies)")
    add("convergence.within_0_5pt", close, r_int(close), [], "cells agreeing within 0.5% but not identical")
    add("convergence.differ", differ, r_int(differ), [], "remaining cells")
    add("convergence.total", ident + close + differ, r_int(ident + close + differ), [], "shared cells")

    # --- ANOVA (experiment_why) ---
    p = os.path.join(RES, "experiment_why.json")
    if os.path.exists(p):
        d = load(p); a = [sha(p)]
        def walk(o, path):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, path + [k])
            elif isinstance(o, (int, float)) and not isinstance(o, bool):
                key = ".".join(path)
                if any(t in key.lower() for t in ("anova", "eta", "f_", "f.", "pvalue", "p_value", "interaction", "partial")):
                    add("why." + key, o, r_plain(o, 2) + r_plain(o, 3) + r_plain(o, 1), a, "experiment_why.json " + key)
        walk({k: v for k, v in d.items() if k != "cells"}, [])

    # --- crash law ---
    p = os.path.join(RES, "experiment_crash_law.json")
    if os.path.exists(p):
        d = load(p); a = [sha(p)]
        add("crashlaw.n_scenarios", d["n_scenarios"], r_int(d["n_scenarios"]), a, "n_scenarios")
        add("crashlaw.all_proven", int(bool(d["all_proven"])), ["True"] if d["all_proven"] else ["False"], a, "all_proven")
        for i, s in enumerate(d["scenarios"]):
            h = s["audit_log"][0]["hash"] if s.get("audit_log") else ""
            add(f"crashlaw.scenario{i}.{s['name']}.hash", h, [h, h[:8], h[:8] + "..."], a, f"scenarios[{i}].audit_log[0].hash")

    # --- decision battery ---
    p = os.path.join(RES, "decision_battery_full.json")
    if os.path.exists(p):
        d = load(p); a = [sha(p)]
        def walk2(o, path):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk2(v, path + [k])
            elif isinstance(o, (int, float)) and not isinstance(o, bool) and len(path) <= 4:
                add("battery." + ".".join(path), o, r_plain(o, 2) + r_plain(o, 1) + (r_int(o) if float(o).is_integer() else []) + (r_int(round(o * 100)) if 0 <= o <= 1 else []), a, "decision_battery_full.json " + ".".join(path))
        walk2(d, [])

    import facts_extra
    facts_extra.register(globals())
    return FACTS


if __name__ == "__main__":
    facts = build()
    out = os.path.join(HERE, "facts.json")
    json.dump({"artifact_sha256_12": _sha, "facts": facts}, io.open(out, "w", encoding="utf-8"), indent=0)
    print("facts:", len(facts), "artifacts hashed:", len(_sha))
