#!/bin/bash
# Chained after the generalist run: LOTO + 4 format specialists for phi-4-mini.
set -e
S=/scratch0/$USER/edgeft
cd "$S"
# wait for the generalist to finish
echo "queue: waiting for generalist ALL DONE marker..."
while ! grep -q "ALL DONE" /tmp/phi_train.log 2>/dev/null; do sleep 120; done
echo "=== $(date) queue start ==="
source venv/bin/activate
export FT_BASE_MODEL="$S/hf/Phi-4-mini-instruct"
# build variant datasets
python - << 'PY'
import json, os
os.makedirs('ft_variants', exist_ok=True)
rows = [json.loads(l) for l in open('ft_dataset/train.jsonl', encoding='utf-8')]
hold = open('ft_dataset/holdout.jsonl', encoding='utf-8').read()
def emit(name, rs):
    d = f'ft_variants/{name}'; os.makedirs(d, exist_ok=True)
    with open(f'{d}/train.jsonl', 'w', encoding='utf-8') as f:
        for r in rs: f.write(json.dumps(r) + '\n')
    open(f'{d}/holdout.jsonl', 'w', encoding='utf-8').write(hold)
    print(name, len(rs))
emit('loto', [r for r in rows if r['topology'] != 'oldstreet_junction'])
for fmt in ('sota', 'myopic', 'prediction', 'coordination'):
    emit(fmt, [r for r in rows if r['format'] == fmt])
PY
# sequential runs
for V in loto sota myopic prediction coordination; do
  echo "=== $(date) VARIANT $V start ==="
  export FT_DATA_DIR="$S/ft_variants/$V"
  export FT_OUT_DIR="$S/out/phi-4-mini-$V"
  python finetune_train.py --step train
  python finetune_train.py --step merge
  cp -r "$FT_OUT_DIR/adapter" "$HOME/phi4mini-$V-adapter" || true
  tar -C "$FT_OUT_DIR" -czf "$S/phi4mini-$V-merged.tgz" merged-bf16 || true
  echo "=== $(date) VARIANT $V done ==="
done
echo "=== $(date) QUEUE ALL DONE ==="
