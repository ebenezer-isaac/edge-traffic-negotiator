"""Both comparators, consistent statistics: one-sample t on per-seed relative change
(matches the reported CI) plus Wilcoxon signed-rank on the paired absolute delays."""
import json, glob, os, math
import numpy as np
from scipy import stats
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
mp = {}
for f in glob.glob(os.path.join(RES, "frontier_raw", "BASELINE__*.json")):
    d = json.load(open(f)); mp[(d["topology"], d["seed"])] = d["mean_network_delay_s"]
ft = {}
for name in ("experiment_fixedtime_seed30.json", "experiment_fixedtime_calibrated.json"):
    p = os.path.join(RES, name)
    if os.path.exists(p):
        for c in json.load(open(p))["cells"]:
            ft[(c["topology"], c["seed"])] = c["fixedtime_delay_s"]
ARMS = [("qwen3-0.6b-ft1","qwen ft"),("qwen3-0.6b-ft0","qwen stock"),("phi4mini-gen-gpu","phi ft")]
TOPS = ["euston_peakhour","bloomsbury_grid","oldstreet_junction","bloomsbury_calibrated","euston_peakhour_calibrated"]
def cells(model, topo):
    o={}
    for f in glob.glob(os.path.join(RES,"frontier_raw",f"{model}__{topo}__*.json")):
        d=json.load(open(f))
        if (d.get("topology")==topo and d.get("model")==model
                and d.get("config")=="sota" and d.get("slm_delay_s") is not None):
            o[d["seed"]]=d["slm_delay_s"]
    return o
rows=[]
for topo in TOPS:
    for model,nice in ARMS:
        c=cells(model,topo)
        if not c: continue
        rec={"topo":topo,"arm":nice}
        for lab,comp in (("MP",mp),("FT",ft)):
            seeds=sorted(s for s in c if (topo,s) in comp)
            if len(seeds)<3: rec[lab]=None; continue
            a=np.array([c[s] for s in seeds]); b=np.array([comp[(topo,s)] for s in seeds])
            rel=(a-b)/b*100; n=len(seeds); m=rel.mean(); se=rel.std(ddof=1)/math.sqrt(n)
            tc=stats.t.ppf(.975,n-1)
            rec[lab]={"n":n,"rel":round(m,2),"ci":[round(m-tc*se,2),round(m+tc*se,2)],
                      "p_t":float(stats.ttest_1samp(rel,0).pvalue),
                      "p_w":float(stats.wilcoxon(a,b).pvalue)}
        rows.append(rec)
json.dump(rows, open(os.path.join(RES,"comparator_audit.json"),"w"), indent=1)
hdr=f"{'topology':26s} {'arm':11s} | {'vs FIXED-TIME (floor)':38s} | vs MaxPressure"
print(hdr); print("-"*len(hdr)+"-"*30)
for r in rows:
    def fmt(x):
        if not x: return f"{'-- n/a':38s}"
        return f"n={x['n']:2d} {x['rel']:+7.2f} [{x['ci'][0]:+7.2f},{x['ci'][1]:+7.2f}] p={x['p_t']:.2g}"
    print(f"{r['topo']:26s} {r['arm']:11s} | {fmt(r['FT']):46s} | {fmt(r['MP'])}")
