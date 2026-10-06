#!/bin/bash
S=/scratch0/$USER/edgeft
cd "$S"; source venv/bin/activate
for V in loto sota myopic prediction coordination; do
  while [ ! -f "out/phi-4-mini-$V/merged-bf16/config.json" ]; do sleep 60; done
  if [ ! -f "phi4mini-$V-int4/genai_config.json" ]; then
    cp hf/Phi-4-mini-instruct/*.py "out/phi-4-mini-$V/merged-bf16/" 2>/dev/null
    echo "=== $(date) compiling $V ==="
    python -m onnxruntime_genai.models.builder -i "out/phi-4-mini-$V/merged-bf16" -o "phi4mini-$V-int4" -p int4 -e cpu > "/tmp/compile_$V.log" 2>&1 && echo "=== $V int4 OK ===" || echo "=== $V int4 FAILED ==="
  fi
done
echo "=== WATCHER ALL DONE ==="
