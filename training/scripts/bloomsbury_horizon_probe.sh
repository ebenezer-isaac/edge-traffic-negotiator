#!/bin/bash
cd "${EDGE_NEGOTIATOR_DIR:-.}"
# Diagnostic: does a longer horizon let Bloomsbury clear? 3 seeds, baseline only.
./.venv/Scripts/python.exe - << 'PY'
import sys, json
sys.path.insert(0, 'src')
from experiment_traffic import NullAgent, run_arm
from experiment_topology import _topologies
t = [x for x in _topologies() if x['label'] == 'bloomsbury_grid'][0]
out = []
for end in (1200, 3600):
    for s in (1, 2, 4):
        r = run_arm(f'probe_{end}_s{s}', NullAgent(), seed=s, end=end, gate=2,
                    config='myopic', net=t['net'], routes=t['routes'])
        m = r['metrics']
        pct = m['completed'] / m['loaded'] * 100
        out.append({'end': end, 'seed': s, 'loaded': m['loaded'], 'completed': m['completed'],
                    'completion_pct': round(pct, 1), 'teleports': m['teleports'],
                    'delay_s': round(m['mean_network_delay_s'], 1)})
        print(f"end={end} s={s}: loaded={m['loaded']} completed={m['completed']} "
              f"({pct:.1f}%) teleports={m['teleports']} delay={m['mean_network_delay_s']:.1f}s", flush=True)
json.dump(out, open('results/bloomsbury_horizon_probe.json', 'w'), indent=2)
print('PROBE DONE')
PY
