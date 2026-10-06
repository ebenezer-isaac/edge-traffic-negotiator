#!/bin/bash
cd "${EDGE_NEGOTIATOR_DIR:-.}"
until grep -q "TRUST-FT CHAIN ALL DONE" ${FT_WORKSPACE:-.}/trust_ft_chain.log 2>/dev/null; do sleep 300; done
for M in "Phi-4-mini-instruct-generic-gpu:5" "phi4mini-gen-gpu" "qwen3-0.6b-ft2" "qwen3-0.6b-ft0"; do
  foundry model load "$M" >/dev/null 2>&1
  echo "[$(date +%H:%M)] lee-retest $M"
  ./.venv/Scripts/python.exe src/experiment_slm_auth_lee.py --model "$M" > "results/slm_auth_lee_${M//:/_}.out" 2>&1 \
    && echo "[$(date +%H:%M)] lee-retest $M DONE" || echo "[$(date +%H:%M)] lee-retest $M FAILED"
  foundry model unload "$M" >/dev/null 2>&1
done
echo "LEE RETEST ALL DONE"
