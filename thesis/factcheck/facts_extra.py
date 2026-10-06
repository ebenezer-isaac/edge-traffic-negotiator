# -*- coding: utf-8 -*-
"""Additional fact families. register(ns) receives facts.py's globals so the
same helpers, loaders and conventions are used. Kept separate only to keep
facts.py readable."""
import os, io, json, glob, math, statistics, re
import numpy as np
from scipy import stats


def register(ns):
    add, RES, sha, load, r_signed, r_plain, r_int, r_p = (ns[k] for k in ("add", "RES", "sha", "load", "r_signed", "r_plain", "r_int", "r_p"))
    rel_stats, register_effect, arm_cells, DISJOINT = ns["rel_stats"], ns["register_effect"], ns["arm_cells"], ns["DISJOINT"]
    mp, mp_files = ns["maxpressure"]()
    ft, ft_files = ns["fixedtime"]()
    POWERED = list(range(1, 31))

    # --- powered stock arms (catalogue models, seeds 1..30) vs both comparators ---
    for model in ("qwen2.5-0.5b", "qwen3-0.6b", "phi-4-mini", "qwen3-1.7b"):
        for topo in ("oldstreet_junction", "euston_peakhour"):
            for cfg in ("sota", "myopic", "prediction", "coordination"):
                cells, files = arm_cells(model, topo, cfg)
                seeds = [s for s in POWERED if s in cells and (topo, s) in mp]
                if len(seeds) < 20:
                    continue
                a = [cells[s]["slm_delay_s"] for s in seeds]
                register_effect(f"stock.{model}.{topo}.{cfg}.vsMP", rel_stats(a, [mp[(topo, s)]["mean_network_delay_s"] for s in seeds]), files + mp_files, f"catalogue stock {model} {cfg} vs MaxPressure, {topo}, seeds 1..30")
                seeds_ft = [s for s in seeds if (topo, s) in ft]
                if len(seeds_ft) >= 20:
                    register_effect(f"stock.{model}.{topo}.{cfg}.vsFT", rel_stats([cells[s]["slm_delay_s"] for s in seeds_ft], [ft[(topo, s)]["fixedtime_delay_s"] for s in seeds_ft]), files + ft_files, f"catalogue stock {model} {cfg} vs fixed-time, {topo}, seeds 1..30")
    # range of stock-arm effects on euston peak-hour vs FT (7.4% to 19.7%, three of eight significant)
    rels, sig = [], 0
    for model in ("qwen2.5-0.5b", "qwen3-0.6b", "phi-4-mini", "qwen3-1.7b"):
        for cfg in ("sota", "myopic"):
            cells, _ = arm_cells(model, "euston_peakhour", cfg)
            seeds = [s for s in POWERED if s in cells and ("euston_peakhour", s) in ft]
            if len(seeds) >= 20:
                st = rel_stats([cells[s]["slm_delay_s"] for s in seeds], [ft[("euston_peakhour", s)]["fixedtime_delay_s"] for s in seeds])
                rels.append(st["rel"]); sig += st["p_t1"] < 0.05
    if rels:
        add("stock.euston_peakhour.vsFT.rel_min", min(rels), r_signed(min(rels), 1), [], "min over 8 stock arms (4 models x sota/myopic) of rel vs FT")
        add("stock.euston_peakhour.vsFT.rel_max", max(rels), r_signed(max(rels), 1), [], "max over 8 stock arms of rel vs FT")
        add("stock.euston_peakhour.vsFT.n_sig", sig, r_int(sig), [], "arms with one-sample t p<.05")
        add("stock.euston_peakhour.vsFT.n_arms", len(rels), r_int(len(rels)), [], "stock arms considered")

    # --- serving-artifact provenance: catalogue qwen3-0.6b vs pipeline-compiled ft0 on shared seeds ---
    for topo in ("euston_peakhour", "oldstreet_junction", "bloomsbury_grid"):
        cat, fc = arm_cells("qwen3-0.6b", topo, "sota"); comp, fk = arm_cells("qwen3-0.6b-ft0", topo, "sota")
        seeds = [s for s in DISJOINT if s in cat and s in comp and (topo, s) in mp]
        if len(seeds) >= 10:
            a = [cat[s]["slm_delay_s"] for s in seeds]; b = [comp[s]["slm_delay_s"] for s in seeds]; m = [mp[(topo, s)]["mean_network_delay_s"] for s in seeds]
            sa, sb = rel_stats(a, m), rel_stats(b, m)
            add(f"provenance.{topo}.n_shared", len(seeds), r_int(len(seeds)), fc + fk, "seeds shared by catalogue and compiled arms within the disjoint set")
            add(f"provenance.{topo}.catalogue.vsMP.rel", sa["rel"], r_signed(sa["rel"], 1), fc + mp_files, "catalogue qwen3-0.6b vs MaxPressure on shared seeds")
            add(f"provenance.{topo}.compiled.vsMP.rel", sb["rel"], r_signed(sb["rel"], 1), fk + mp_files, "pipeline-compiled ft0 vs MaxPressure on shared seeds")
            add(f"provenance.{topo}.gap_points_vsMP", sa["rel"] - sb["rel"], r_plain(abs(sa["rel"] - sb["rel"]), 1) + r_int(round(abs(sa["rel"] - sb["rel"]))), fc + fk, "catalogue minus compiled, points (vs MP)")
            hh = rel_stats(a, b)
            add(f"provenance.{topo}.catalogue_vs_compiled.p_t1", hh["p_t1"], r_p(hh["p_t1"]), fc + fk, "catalogue vs compiled head-to-head p (one-sample t on rel)")
            add(f"provenance.{topo}.catalogue_vs_compiled.rel", hh["rel"], r_signed(hh["rel"], 1), fc + fk, "catalogue vs compiled head-to-head rel %")
            if all((topo, s) in ft for s in seeds):
                f_ = [ft[(topo, s)]["fixedtime_delay_s"] for s in seeds]
                fa, fb = rel_stats(a, f_), rel_stats(b, f_)
                add(f"provenance.{topo}.catalogue.vsFT.rel", fa["rel"], r_signed(fa["rel"], 1), fc + ft_files, "catalogue vs fixed-time on shared seeds")
                add(f"provenance.{topo}.compiled.vsFT.rel", fb["rel"], r_signed(fb["rel"], 1), fk + ft_files, "compiled vs fixed-time on shared seeds")
                add(f"provenance.{topo}.gap_points_vsFT", fa["rel"] - fb["rel"], r_plain(abs(fa["rel"] - fb["rel"]), 1), fc + fk, "catalogue minus compiled, points (vs FT)")

    # --- phi-4-mini-reasoning latency probe ---
    for f in glob.glob(os.path.join(RES, "frontier_raw", "phi-4-mini-reasoning__*.json")):
        d = load(f); ls = d.get("latency_summary") or {}
        if ls:
            add(f"reasoning.{d['topology']}.{d['config']}.p99", ls["p99"], r_plain(ls["p99"], 1) + r_plain(ls["p99"], 2), [sha(f)], "phi-4-mini-reasoning latency_summary.p99 s")
            add(f"reasoning.{d['topology']}.{d['config']}.p50", ls["p50"], r_plain(ls["p50"], 1) + r_plain(ls["p50"], 2), [sha(f)], "phi-4-mini-reasoning latency_summary.p50 s")

    # --- teacher cross-audit agreement ---
    def label_map(path):
        d = load(path)
        if isinstance(d, dict) and "choices" in d:
            return {str(k): v for k, v in d["choices"].items()}
        if isinstance(d, dict):
            out = {}
            for k, v in d.items():
                if isinstance(v, dict):
                    for key in ("phase", "choice", "label", "answer"):
                        if key in v:
                            out[str(k)] = v[key]; break
                elif isinstance(v, (int, float)):
                    out[str(k)] = v
            return out
        if isinstance(d, list):
            out = {}
            for i, item in enumerate(d):
                if isinstance(item, dict):
                    k = str(item.get("id", i))
                    for key in ("phase", "choice", "label", "answer"):
                        if key in item:
                            out[k] = item[key]; break
            return out
        return {}
    checks = []
    for chk in sorted(glob.glob(os.path.join(RES, "ft_dataset", "fablecheck_*.json")) + glob.glob(os.path.join(RES, "ft_dataset", "sonnetcheckp_*.json"))):
        name = os.path.basename(chk)
        batch = re.search(r"_(\d+)\.json$", name).group(1)
        lab = os.path.join(RES, "ft_dataset", ("labelsp_" if "sonnetcheckp" in name else "labels_") + batch + ".json")
        if not os.path.exists(lab):
            continue
        c = label_map(chk); l = label_map(lab)
        common = [k for k in c if k in l]
        if not common:
            continue
        agree = sum(1 for k in common if int(c[k]) == int(l[k])) / len(common) * 100
        checks.append((agree, len(common)))
        add(f"teacher.audit.{name}.agree_pct", agree, r_plain(agree, 1), [sha(chk), sha(lab)], f"share of {len(common)} states where the second frontier model's choice equals the teacher label")
        add(f"teacher.audit.{name}.n", len(common), r_int(len(common)), [sha(chk), sha(lab)], "states compared")
    if checks:
        tot = sum(n for _, n in checks); agg = sum(a * n for a, n in checks) / tot
        add("teacher.audit.agree_pct_overall", agg, r_plain(agg, 1), [], "pooled agreement over all audit samples")
        add("teacher.audit.n_total", tot, r_int(tot), [], "total states cross-checked")
        add("teacher.audit.agree_min", min(a for a, _ in checks), r_plain(min(a for a, _ in checks), 1), [], "lowest per-sample agreement")
        add("teacher.audit.agree_max", max(a for a, _ in checks), r_plain(max(a for a, _ in checks), 1), [], "highest per-sample agreement")
        add("teacher.audit.n_samples", len(checks), r_int(len(checks)), [], "audit samples")

    # --- decision battery agreement ---
    p = os.path.join(RES, "decision_battery_full.json")
    if os.path.exists(p):
        d = load(p); a = [sha(p)]
        cloud, local = [], []
        for m, v in d["scores"].items():
            pct = v["agree"] / v["wellformed"] * 100
            add(f"battery.{m}.agree_pct", pct, r_plain(pct, 1) + r_int(round(pct)) + r_int(math.floor(pct)), a, f"scores.{m}.agree/wellformed x100")
            add(f"battery.{m}.n", v["wellformed"], r_int(v["wellformed"]), a, "states scored")
            (local if m.startswith("local:") else cloud).append(pct)
        add("battery.cloud.min", min(cloud), r_int(math.floor(min(cloud))) + r_int(round(min(cloud))), a, "min cloud agreement %")
        add("battery.cloud.max", max(cloud), r_int(math.floor(max(cloud))) + r_int(round(max(cloud))), a, "max cloud agreement %")
        add("battery.local.min", min(local), r_int(math.floor(min(local))) + r_int(round(min(local))), a, "min local agreement %")
        add("battery.local.max", max(local), r_int(math.floor(max(local))) + r_int(round(max(local))), a, "max local agreement %")

    # --- horizon probe per seed ---
    p = os.path.join(RES, "bloomsbury_horizon_probe.json")
    if os.path.exists(p):
        d = load(p); a = [sha(p)]
        for r in d:
            add(f"calib.horizon.{r['end']}.s{r['seed']}.teleports", r["teleports"], r_int(r["teleports"]), a, f"seed {r['seed']} end {r['end']} teleports")
            add(f"calib.horizon.{r['end']}.s{r['seed']}.completion_pct", r["completion_pct"], r_plain(r["completion_pct"], 1), a, f"seed {r['seed']} end {r['end']} completion_pct")
        for end in (1200, 3600):
            add(f"calib.horizon.{end}.end", end, r_int(end), a, "horizon steps")
        t1 = np.mean([r["teleports"] for r in d if r["end"] == 1200]); t3 = np.mean([r["teleports"] for r in d if r["end"] == 3600])
        add("calib.horizon.teleport_ratio", t3 / t1, r_plain(t3 / t1, 1) + r_int(round(t3 / t1)), a, "mean teleports at 3600 / at 1200")

    # --- MaxPressure guard metrics for every topology present (incl. daily-demand corridor and grids) ---
    topos = sorted({t for (t, s) in mp})
    for topo in topos:
        rows = [mp[(topo, s)]["metrics"] for s in DISJOINT if (topo, s) in mp]
        if not rows:
            rows = [mp[k]["metrics"] for k in mp if k[0] == topo]
        comp = np.array([r["completed"] for r in rows], float); loaded = np.array([r["loaded"] for r in rows], float)
        add(f"mpall.{topo}.loaded", loaded.mean(), r_int(round(loaded.mean())), mp_files, f"MaxPressure loaded, {topo}")
        add(f"mpall.{topo}.completion_pct", (comp / loaded).mean() * 100, r_plain((comp / loaded).mean() * 100, 1) + r_int(round((comp / loaded).mean() * 100)), mp_files, f"MaxPressure completion %, {topo}, n={len(rows)}")
        add(f"mpall.{topo}.n", len(rows), r_int(len(rows)), mp_files, "cells")

    # --- head-to-head per-seed extremes ---
    for topo in ns["TOPOS"]:
        a, fa = arm_cells("qwen3-0.6b-ft1", topo); b, fb = arm_cells("qwen3-0.6b-ft0", topo)
        seeds = [s for s in DISJOINT if s in a and s in b]
        if len(seeds) >= 3:
            rel = np.array([(a[s]["slm_delay_s"] - b[s]["slm_delay_s"]) / b[s]["slm_delay_s"] * 100 for s in seeds])
            add(f"h2h.qwen_ft_vs_stock.{topo}.seed_min", rel.min(), r_signed(rel.min(), 1), fa + fb, "most favourable single-seed rel %")
            add(f"h2h.qwen_ft_vs_stock.{topo}.seed_max", rel.max(), r_signed(rel.max(), 1), fa + fb, "least favourable single-seed rel %")
            add(f"h2h.qwen_ft_vs_stock.{topo}.rel_abs", abs(rel.mean()), r_plain(abs(rel.mean()), 1), fa + fb, "|mean rel| unsigned")
            # fine-tuned vs floor: seeds beating the floor
            if all((topo, s) in ft for s in seeds):
                rf = np.array([(a[s]["slm_delay_s"] - ft[(topo, s)]["fixedtime_delay_s"]) / ft[(topo, s)]["fixedtime_delay_s"] * 100 for s in seeds])
                add(f"arm.qwen_ft.{topo}.vsFT.wins", int((rf < 0).sum()), r_int((rf < 0).sum()), fa + ft_files, "seeds where ft beats the fixed-time floor")
                add(f"arm.qwen_ft.{topo}.vsFT.median", float(np.median(rf)), r_signed(float(np.median(rf)), 1), fa + ft_files, "median per-seed rel vs FT")

    # --- derived counts ---
    add("derived.cells_14x30", 14 * 30, r_int(420), [], "14 arm-by-topology cells x 30 seeds")

    # --- exploratory sweep (experiment_frontier.json): per-topology best stock arm vs MaxPressure ---
    p = os.path.join(RES, "experiment_frontier.json")
    if os.path.exists(p):
        d = load(p); a = [sha(p)]
        best, allarms = {}, {}
        for cfg, blk in d["by_config"].items():
            for cell in blk.get("cells", []):
                for topo, t in cell.get("topologies", {}).items():
                    m = (t.get("delay_rel_pct") or {}).get("mean")
                    if m is None:
                        continue
                    allarms.setdefault(topo, []).append(m)
                    if topo not in best or m < best[topo][0]:
                        best[topo] = (m, cell["model"], cfg)
        for topo, (m, model, cfg) in best.items():
            add(f"sweep.best.{topo}.rel_vsMP", m, r_signed(m, 1) + r_signed(round(m), 0) + r_int(round(m)), a, f"exploratory sweep: best (lowest mean delay_rel_pct vs MaxPressure) arm on {topo} = {model}/{cfg}; comparator is the MaxPressure BASELINE, 3 seeds")
            add(f"sweep.allarms_mean.{topo}.rel_vsMP", float(np.mean(allarms[topo])), r_signed(float(np.mean(allarms[topo])), 1), a, f"exploratory sweep: mean over all arms of mean delay_rel_pct vs MaxPressure on {topo}")
        # stock catalogue arms only (exclude fine-tuned students that share the raw dir)
        def is_stock(name):
            return not re.search(r"ft\d|gen-gpu", name)
        best_s, all_s = {}, {}
        for cfg, blk in d["by_config"].items():
            for cell in blk.get("cells", []):
                if not is_stock(cell["model"]):
                    continue
                for topo, t in cell.get("topologies", {}).items():
                    m = (t.get("delay_rel_pct") or {}).get("mean")
                    if m is None:
                        continue
                    all_s.setdefault(topo, []).append(m)
                    if topo not in best_s or m < best_s[topo][0]:
                        best_s[topo] = (m, cell["model"], cfg)
        for topo, (m, model, cfg) in best_s.items():
            add(f"sweep.stockbest.{topo}.rel_vsMP", m, r_signed(m, 1) + r_signed(round(m), 0) + r_int(round(m)) + r_plain(abs(m), 1), a, f"exploratory sweep, STOCK catalogue arms only: best mean delay_rel_pct vs MaxPressure on {topo} = {model}/{cfg}, 3 seeds")
            add(f"sweep.stockall_mean.{topo}.rel_vsMP", float(np.mean(all_s[topo])), r_signed(float(np.mean(all_s[topo])), 1) + r_signed(round(float(np.mean(all_s[topo]))), 0), a, f"exploratory sweep, stock arms: mean over arms of mean delay_rel_pct vs MaxPressure on {topo} (n arms={len(all_s[topo])})")
        add("sweep.comparator", 0, ["MaxPressure"], a, "experiment_frontier delay_rel_pct is relative to the MaxPressure BASELINE cells (frontier_raw/BASELINE__*); no fixed-time floor exists for grid3x3/grid4x4")

    # --- original three-seed fixed-time probe (experiment_fixedtime.json): MaxPressure vs fixed-time incl. grids ---
    p = os.path.join(RES, "experiment_fixedtime.json")
    if os.path.exists(p):
        d = load(p); a = [sha(p)] + mp_files
        cells = d.get("cells", [])
        by = {}
        for c in cells:
            if "fixedtime_delay_s" in c:
                by.setdefault(c["topology"], {})[c["seed"]] = c["fixedtime_delay_s"]
        for topo, seeds in by.items():
            ss = [s for s in seeds if (topo, s) in mp]
            if len(ss) >= 2:
                st = rel_stats([mp[(topo, s)]["mean_network_delay_s"] for s in ss], [seeds[s] for s in ss])
                add(f"mpfloor3.{topo}.rel", st["rel"], r_signed(st["rel"], 1) + r_signed(round(st["rel"]), 0) + r_int(round(st["rel"])), a, f"three-seed probe: MaxPressure vs fixed-time on {topo}, seeds {ss}")
                add(f"mpfloor3.{topo}.n", len(ss), r_int(len(ss)), a, "seeds in the three-seed probe")

    # --- generic numeric-leaf registration for remaining experiment JSONs (backtrace by JSON path) ---
    GENERIC = ["experiment_topology.json", "experiment_topology_gated.json", "experiment_topology_gate12.json",
               "experiment_sweep.json", "experiment_multiseed.json", "experiment_seed30_powered.json",
               "experiment_powered_gate.json", "comparator_audit.json", "closedloop_ci.json",
               "calibration_euston_peakhour.json", "experiment_anchor.json", "experiment_accident.json",
               "experiment_vehicle_auth.json", "experiment_jobA.json", "experiment_why.json",
               "experiment_throughput.json", "experiment_frontier.json", "experiment1_slm_vs_rule.json",
               "experiment_trust.json"]
    def walk(o, path, a, fn):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, path + [str(k)], a, fn)
        elif isinstance(o, list):
            if len(o) <= 60:
                for i, v in enumerate(o):
                    walk(v, path + [str(i)], a, fn)
        elif isinstance(o, (int, float)) and not isinstance(o, bool):
            renders = r_plain(o, 1) + r_plain(o, 2) + r_plain(o, 3) + r_signed(o, 1) + r_signed(o, 2)
            if float(o).is_integer():
                renders += r_int(o)
            elif abs(o) >= 10:
                renders += r_signed(round(o), 0) + r_int(round(o))
            if 0 <= o <= 1:
                renders += r_plain(o * 100, 1) + r_int(round(o * 100))
            add(f"json.{fn}." + ".".join(path), o, renders, a, f"{fn} at {'/'.join(path)}")
    for fn in GENERIC:
        p = os.path.join(RES, fn)
        if os.path.exists(p):
            try:
                walk(load(p), [], [sha(p)], fn)
            except Exception as e:  # keep the harness deterministic and loud
                add(f"json.{fn}.ERROR", 0, [], [sha(p)], f"could not walk: {e}")
