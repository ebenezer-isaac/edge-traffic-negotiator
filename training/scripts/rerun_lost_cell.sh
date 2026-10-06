#!/bin/bash
cd "${EDGE_NEGOTIATOR_DIR:-.}"
until grep -q "EVAL CHAIN ALL DONE" ${FT_WORKSPACE:-.}/eval_chain.log 2>/dev/null; do sleep 300; done
rm -f results/frontier_raw/qwen3-0.6b-ft0__bloomsbury_grid__sota__s30.json
foundry model load qwen3-0.6b-ft0 >/dev/null 2>&1
./.venv/Scripts/python.exe src/experiment_frontier.py --models qwen3-0.6b-ft0 --configs sota --topologies bloomsbury_grid --seeds 30 > results/rerun_lost_cell.log 2>&1
grep -E "measured|FAIL|error" results/rerun_lost_cell.log | tail -3
