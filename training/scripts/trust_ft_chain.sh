#!/bin/bash
cd "${EDGE_NEGOTIATOR_DIR:-.}"
for M in qwen3-0.6b-ft1 qwen3-0.6b-ft0 phi4mini-gen-gpu; do
  foundry model load "$M" >/dev/null 2>&1
  echo "[$(date +%H:%M)] trust-traffic $M"
  ./.venv/Scripts/python.exe src/experiment_trust_traffic.py --model "$M" --seeds 42 123 31 > "results/trust_ft_$M.out" 2>&1 \
    && echo "[$(date +%H:%M)] trust-traffic $M DONE" || echo "[$(date +%H:%M)] trust-traffic $M FAILED"
  foundry model unload "$M" >/dev/null 2>&1
done
echo "TRUST-FT CHAIN ALL DONE"
