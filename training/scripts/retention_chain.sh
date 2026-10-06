#!/bin/bash
cd "${EDGE_NEGOTIATOR_DIR:-.}"
for M in "Phi-4-mini-instruct-generic-gpu:5" "phi4mini-gen-gpu" "qwen3-0.6b-ft2" "qwen3-0.6b-ft0"; do
  SAFE="${M//:/_}"
  [ -f "results/ft_dataset/retention_$SAFE.json" ] && { echo "SKIP $M"; continue; }
  foundry model load "$M" >/dev/null 2>&1
  echo "[$(date +%H:%M)] probe $M"
  ./.venv/Scripts/python.exe src/retention_probe.py --model "$M" > "results/retention_$SAFE.log" 2>&1 \
    && echo "[$(date +%H:%M)] probe $M DONE" || echo "[$(date +%H:%M)] probe $M FAILED"
  foundry model unload "$M" >/dev/null 2>&1
done
echo "RETENTION CHAIN ALL DONE"
