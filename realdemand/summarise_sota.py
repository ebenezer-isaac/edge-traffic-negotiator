"""Summarise the corrected real-demand runs (delay-aware prompt) against fixed-time and MaxPressure.

Reads results/scoot_fixedtime.json, the MaxPressure arm of results/scoot_sweep_v2.json,
results/scoot_sweep_sota.json, results/scoot_sweep_sonnet.json, results/scoot_sweep_haiku_partial.json
and results/scoot_config_null_full72.json. Standard library only.

    python realdemand/summarise_sota.py
"""
import json
import os
import statistics as st

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def load(name):
    with open(os.path.join(R, name), encoding="utf-8") as fh:
        return json.load(fh)


def key(c):
    return f"{c['day']}|{c['hour']:02d}"


FT = {key(c): c for c in load("scoot_fixedtime.json")["cells"].values()}
MP = {k.split("|", 1)[1]: c for k, c in load("scoot_sweep_v2.json")["cells"].items() if k.startswith("maxpressure|")}
STc = {key(c): c for c in load("scoot_fixedtime_static.json")["cells"].values()}
arms = {"SUMO default (vehicle-actuated)": FT, "fixed timetable (static)": STc, "maxpressure": MP}
sota = load("scoot_sweep_sota.json")["cells"]
for a in sorted({c["arm"] for c in sota.values()}):
    arms[a] = {key(c): c for c in sota.values() if c["arm"] == a}
arms["sota:claude-sonnet-5-5"] = {key(c): c for c in load("scoot_sweep_sonnet.json")["cells"].values() if "delay_s" in c}
arms["sota:claude-haiku-4-5 (partial)"] = {key(c): c for c in load("scoot_sweep_haiku_partial.json")["cells"].values() if "delay_s" in c}
null = load("scoot_config_null_full72.json")
for cfg in ("coordination", "prediction"):
    arms[f"{cfg}, no model"] = {k.split("|", 1)[1]: v for k, v in null.items() if k.startswith(cfg + "|")}

print(f"{'controller':34s}  n  mean_s  tp  vsFT_med  <FT  vsMP_med  <MP  own_choice_vs_MP%")
for name, d in arms.items():
    ks = [k for k in d if k in FT and k in MP]
    vf = [(d[k]["delay_s"] - FT[k]["delay_s"]) / FT[k]["delay_s"] * 100 for k in ks]
    vm = [(d[k]["delay_s"] - MP[k]["delay_s"]) / MP[k]["delay_s"] * 100 for k in ks]
    ds = [d[k]["decision_stats"] for k in ks if d[k].get("decision_stats")]
    div = (100 * sum(x["slm_diverged_and_served"] for x in ds) / sum(x["served_by"]["slm"] for x in ds)) if ds else float("nan")
    print(f"{name:34s} {len(ks):2d} {st.mean(d[k]['delay_s'] for k in ks):7.1f} {sum(d[k].get('teleports', 0) for k in ks):4d}"
          f" {st.median(vf):+8.1f} {sum(x < 0 for x in vf):4d} {st.median(vm):+8.1f} {sum(x < 0 for x in vm):4d} {div:10.1f}")
