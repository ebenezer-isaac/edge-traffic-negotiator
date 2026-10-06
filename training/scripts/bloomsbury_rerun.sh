#!/bin/bash
cd "${EDGE_NEGOTIATOR_DIR:-.}"
until grep -q "CALIBRATION DONE" ${FT_WORKSPACE:-.}/bloomsbury_calibrate.log 2>/dev/null; do sleep 60; done
# 1. pick the calibrated demand + install it as a NEW topology (old cells stay valid)
./.venv/Scripts/python.exe - << 'PY'
import json, os, shutil, io
r = json.load(open('results/bloomsbury_calibration.json'))
# prefer completion closest to 85% with low teleports
best = min(r, key=lambda x: abs(x['completion_pct'] - 85) + x['teleports'])
src = f"sumo/bloomsbury/_cal_{int(best['frac']*100)}.rou.xml"
dst = "sumo/bloomsbury/bloomsbury_light.rou.xml"
shutil.copyfile(src, dst)
print(f"CHOSE frac={best['frac']} trips={best['trips']} completion={best['completion_pct']}% teleports={best['teleports']}")
p = 'src/experiment_topology.py'
s = io.open(p, encoding='utf-8').read()
anchor = """        {"label": "oldstreet_junction","""
add = '''        {"label": "bloomsbury_calibrated",
         "structure": "REAL London grid (Bloomsbury WC1), DEMAND-CALIBRATED so the "
                      "network clears in the horizon (the uncalibrated bloomsbury_grid "
                      "runs oversaturated: ~14%% completion, ~120 teleports)",
         "net": os.path.join(_SUMO, "bloomsbury", "bloomsbury.net.xml"),
         "routes": os.path.join(_SUMO, "bloomsbury", "bloomsbury_light.rou.xml")},
''' + anchor
if 'bloomsbury_calibrated' not in s:
    s = s.replace(anchor, add, 1)
    io.open(p, 'w', encoding='utf-8').write(s)
    print("topology installed")
PY
# 2. re-run the closed-loop arms on the calibrated map
for M in qwen3-0.6b-ft1 qwen3-0.6b-ft0 phi4mini-gen-gpu; do
  foundry model load "$M" >/dev/null 2>&1
  echo "[$(date +%H:%M)] calibrated-bloomsbury $M"
  ./.venv/Scripts/python.exe src/experiment_frontier.py --models "$M" --configs sota \
    --topologies bloomsbury_calibrated \
    --seeds 1 2 4 5 6 8 9 10 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 30 31 32 33 34 \
    > "results/bloom_cal_$M.log" 2>&1 \
    && echo "[$(date +%H:%M)] calibrated-bloomsbury $M DONE" || echo "[$(date +%H:%M)] calibrated-bloomsbury $M FAILED"
  foundry model unload "$M" >/dev/null 2>&1
done
echo "BLOOMSBURY RERUN ALL DONE"
