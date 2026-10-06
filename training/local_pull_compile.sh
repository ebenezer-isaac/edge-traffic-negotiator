#!/bin/bash
# Streams each variant bf16 from gpu-host, compiles int4 locally, cleans up.
J="${JUMP_HOST}"; H="${GPU_HOST}"
S=/scratch0/$USER/edgeft
PY="${EDGE_NEGOTIATOR_DIR:-.}/.venv-olive/Scripts/python.exe"
for V in loto sota myopic prediction coordination; do
  OUT="${FT_WORKSPACE:-.}/onnx/phi4mini-$V-int4"
  [ -f "$OUT/genai_config.json" ] && { echo "[skip] $V"; continue; }
  # wait for tarball
  until ssh -o BatchMode=yes -o ConnectTimeout=25 -J "$J" "$H" "grep -q \"VARIANT $V done\" /tmp/phi_queue.log" 2>/dev/null; do sleep 120; done
  echo "[$(date +%H:%M)] streaming $V"
  WORK="$HOME/phi4-work/$V"
  rm -rf "$WORK"; mkdir -p "$WORK"
  ssh -o BatchMode=yes -o ConnectTimeout=25 -J "$J" "$H" "cat $S/phi4mini-$V-merged.tgz" | tar -xz -C "$WORK" || { echo "[$(date +%H:%M)] $V stream FAILED"; rm -rf "$WORK"; continue; }
  echo "[$(date +%H:%M)] compiling $V"
  WIN_SRC="~/phi4-work/$V/merged-bf16"
  WIN_OUT="$FT_WORKSPACE/onnx/phi4mini-$V-int4"
  "$PY" -m onnxruntime_genai.models.builder -i "$WIN_SRC" -o "$WIN_OUT" -p int4 -e cpu > "${FT_WORKSPACE:-.}/compile_$V.log" 2>&1 && echo "[$(date +%H:%M)] $V int4 OK" || echo "[$(date +%H:%M)] $V int4 FAILED"
  sed -i 's/"tokenizer_class": "TokenizersBackend"/"tokenizer_class": "GPT2Tokenizer"/' "$OUT/tokenizer_config.json" 2>/dev/null
  rm -rf "$WORK"
done
echo "[$(date +%H:%M)] PULL+COMPILE ALL DONE"
