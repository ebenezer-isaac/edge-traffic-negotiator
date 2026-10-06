#!/bin/bash
cd "${EDGE_NEGOTIATOR_DIR:-.}"
for M in qwen3-0.6b-ft2 qwen3-0.6b-ft0; do
  foundry model load "$M" >/dev/null 2>&1
  echo "[$(date +%H:%M)] sota eval $M"
  ./.venv/Scripts/python.exe src/finetune_eval.py --model "$M" --formats sota > "results/ft_eval_sota_$M.log" 2>&1 \
    && echo "[$(date +%H:%M)] sota eval $M DONE" || echo "[$(date +%H:%M)] sota eval $M FAILED"
  foundry model unload "$M" >/dev/null 2>&1
done
echo "QWEN SOTA EVALS ALL DONE"
