import json, os, sys
_SRC = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,_SRC)
RESULTS = os.path.join(os.path.dirname(_SRC), "results")
from experiment_topology import _topologies
from experiment_fixedtime import _run_fixedtime
TARGETS=["euston_peakhour","bloomsbury_grid","oldstreet_junction"]
SEEDS=[31,32,33,34]
gate_dir=os.path.join(_SRC,"..","sumo","euston"); os.makedirs(gate_dir,exist_ok=True)
tops={t["label"]:t for t in _topologies()}
p=os.path.join(RESULTS,"experiment_fixedtime_seed30.json")
d=json.load(open(p))
have={(c["topology"],c["seed"]) for c in d["cells"]}
for lab in TARGETS:
    t=tops[lab]
    for s in SEEDS:
        if (lab,s) in have: continue
        m=_run_fixedtime(t["label"],t["net"],t["routes"],s,1200,gate_dir)
        d["cells"].append({"topology":lab,"seed":s,"fixedtime_delay_s":m["mean_network_delay_s"],
                           "teleports":m.get("teleports"),"completed":m.get("completed"),"loaded":m.get("loaded")})
        print(f"  {lab:22s} s{s:<3d} delay={m['mean_network_delay_s']:8.2f}s tel={m.get('teleports')}",flush=True)
d["seeds"]=sorted({c["seed"] for c in d["cells"]})
d["note"]="seeds 31-34 added so every arm comparison is n=30 on the training-disjoint seed set"
json.dump(d,open(p,"w"),indent=2)
print("DONE cells=",len(d["cells"]),flush=True)
