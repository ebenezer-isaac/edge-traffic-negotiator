#!/bin/bash
# Sequential offline evals v2: skip-if-done + SYNTHESIZED registration (builder output
# has no inference_model.json — v1 assumed it did; loto/sota 400-failed on that).
cd "${EDGE_NEGOTIATOR_DIR:-.}"
PY="./.venv/Scripts/python.exe"
CACHE="$HOME/.cache/foundry-local"
run_eval() {  # $1 = model id
  SAFE="${1//:/_}"
  [ -f "results/ft_dataset/eval_$SAFE.json" ] && { echo "[$(date +%H:%M)] eval $1 SKIP (done)"; return 0; }
  echo "[$(date +%H:%M)] eval $1"
  "$PY" src/finetune_eval.py --model "$1" --formats sota myopic prediction coordination > "results/ft_eval_$SAFE.log" 2>&1 \
    && echo "[$(date +%H:%M)] eval $1 DONE" || echo "[$(date +%H:%M)] eval $1 FAILED"
}
# 1) stock control (already done -> skips)
run_eval "Phi-4-mini-instruct-generic-gpu:5"
# 2) variants
for V in loto sota myopic prediction coordination; do
  SRC="${FT_WORKSPACE:-.}/onnx/phi4mini-$V-int4"
  until [ -f "$SRC/genai_config.json" ]; do sleep 180; done
  ID="phi4mini-$V"
  [ -d "$CACHE/$ID" ] || cp -r "$SRC" "$CACHE/$ID"
  # idempotent registration: ALWAYS write inference_model.json + WebGPU provider swap
  cat > "$CACHE/$ID/inference_model.json" << JEOF
{
  "Name": "$ID",
  "PromptTemplate": {
    "system": "<|system|>{Content}<|end|>",
    "user": "<|user|>{Content}<|end|>",
    "assistant": "<|assistant|>{Content}<|end|>",
    "prompt": "<|user|>{Content}<|end|><|assistant|>"
  }
}
JEOF
  python - "$ID" << 'PYEOF'
import json, os, sys
p = os.path.join(r'~\.cache\foundry-local', sys.argv[1], 'genai_config.json')
c = json.load(open(p))
c['model']['decoder']['session_options']['provider_options'] = [{"webgpu": {"enableGraphCapture": "0", "validationMode": "basic"}}]
json.dump(c, open(p, 'w'), indent=4)
PYEOF
  foundry model load "$ID" >/dev/null 2>&1
  run_eval "$ID"
  foundry model unload "$ID" >/dev/null 2>&1
  rm -rf "$CACHE/$ID"
done
echo "[$(date +%H:%M)] EVAL CHAIN ALL DONE"
