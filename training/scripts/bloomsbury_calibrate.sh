#!/bin/bash
cd "${EDGE_NEGOTIATOR_DIR:-.}"
./.venv/Scripts/python.exe - << 'PY'
"""Demand-calibrate bloomsbury_grid, mirroring the Old Street treatment:
subsample randomTrips output until the network CLEARS in the horizon
(target >=80% completion, teleports ~0), so mean delay is a well-posed
comparison rather than a gridlock-regime artefact."""
import sys, os, re, json, random
sys.path.insert(0, 'src')
from experiment_traffic import NullAgent, run_arm

SRC = 'sumo/bloomsbury/bloomsbury.rou.xml'
raw = open(SRC, encoding='utf-8').read()
head, rest = raw.split('<routes', 1)
body = '<routes' + rest
items = re.findall(r'<(?:vehicle|trip)\b.*?(?:/>|</(?:vehicle|trip)>)', body, re.S)
print(f'source trips: {len(items)}', flush=True)
open_tag = body[:body.index('>') + 1]

results = []
for frac in (0.25, 0.40, 0.55):
    rng = random.Random(7)
    keep = sorted(rng.sample(range(len(items)), int(len(items) * frac)))
    out = head + open_tag + '\n' + '\n'.join(items[i] for i in keep) + '\n</routes>\n'
    path = f'sumo/bloomsbury/_cal_{int(frac*100)}.rou.xml'
    open(path, 'w', encoding='utf-8').write(out)
    comp = []
    for s in (1, 2, 4):
        r = run_arm(f'cal{frac}_s{s}', NullAgent(), seed=s, end=1200, gate=2,
                    config='myopic', net='sumo/bloomsbury/bloomsbury.net.xml', routes=path)
        m = r['metrics']
        comp.append((m['loaded'], m['completed'], m['completed']/m['loaded']*100,
                     m['teleports'], m['mean_network_delay_s']))
    avg_pct = sum(c[2] for c in comp)/len(comp); avg_tp = sum(c[3] for c in comp)/len(comp)
    print(f'frac={frac:.2f} n={len(keep)} loaded={comp[0][0]} completion={avg_pct:.1f}% '
          f'teleports={avg_tp:.1f} delay={sum(c[4] for c in comp)/len(comp):.1f}s', flush=True)
    results.append({'frac': frac, 'trips': len(keep), 'completion_pct': round(avg_pct,1),
                    'teleports': round(avg_tp,1)})
json.dump(results, open('results/bloomsbury_calibration.json','w'), indent=2)
print('CALIBRATION DONE', flush=True)
PY
