#!/bin/bash
cd "${EDGE_NEGOTIATOR_DIR:-.}"
./.venv/Scripts/python.exe src/calibrate_demand.py --topology bloomsbury_grid \
  --fracs 0.25 0.40 0.55 --seeds 1 2 4 2>&1
