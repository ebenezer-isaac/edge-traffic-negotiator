#!/bin/bash
cd "${EDGE_NEGOTIATOR_DIR:-.}"
SEEDS="1 2 4 5 6 8 9 10 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 30 31 32 33 34"
for M in qwen3-0.6b-ft1 qwen3-0.6b-ft0; do
  foundry model load "$M" >/dev/null 2>&1
  echo "[$(date +%H:%M)] euston-calibrated $M START"
  ./.venv/Scripts/python.exe src/experiment_frontier.py --models "$M" --configs sota \
    --topologies euston_peakhour_calibrated --seeds $SEEDS 2>&1 \
    && echo "[$(date +%H:%M)] euston-calibrated $M DONE" || echo "[$(date +%H:%M)] euston-calibrated $M FAILED"
  foundry model unload "$M" >/dev/null 2>&1
done
echo "EUSTON CALIBRATED RERUN ALL DONE"
