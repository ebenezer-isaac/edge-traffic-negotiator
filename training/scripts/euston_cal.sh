#!/bin/bash
cd "${EDGE_NEGOTIATOR_DIR:-.}"
./.venv/Scripts/python.exe src/calibrate_demand.py --topology euston_peakhour \
  --fracs 0.50 0.65 0.80 --seeds 1 2 4 2>&1
