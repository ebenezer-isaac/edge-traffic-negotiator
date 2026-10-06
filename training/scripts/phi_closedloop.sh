#!/bin/bash
# Phi-ft closed-loop confirmation arm: generalist, sota config, 3 topologies x 30 disjoint seeds.
# Waits for the offline eval chain to finish (VRAM: one 3.8B model at a time).
cd "${EDGE_NEGOTIATOR_DIR:-.}"
until grep -q "EVAL CHAIN ALL DONE" ${FT_WORKSPACE:-.}/eval_chain.log 2>/dev/null; do sleep 300; done
foundry model load phi4mini-gen-gpu >/dev/null 2>&1
./.venv/Scripts/python.exe src/experiment_frontier.py \
  --models phi4mini-gen-gpu --configs sota \
  --topologies euston_peakhour bloomsbury_grid oldstreet_junction \
  --seeds 1 2 4 5 6 8 9 10 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 30 31 32 33 34 \
  > results/phi_closedloop_v1.log 2>&1
echo "PHI CLOSEDLOOP EXIT $?"
