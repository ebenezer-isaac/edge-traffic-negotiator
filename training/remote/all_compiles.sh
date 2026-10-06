#!/bin/bash
S=/scratch0/$USER/edgeft
cd "$S"
# dedicated compile venv (transformers 5 pairing, mirrors the proven local setup)
if [ ! -f venv-compile/bin/activate ]; then
  python3 -m venv venv-compile
  source venv-compile/bin/activate
  pip install -q --upgrade pip
  pip install -q torch --index-url https://download.pytorch.org/whl/cpu
  pip install -q "transformers>=5" onnxruntime-genai onnx onnxruntime requests
else
  source venv-compile/bin/activate
fi
python -c "import transformers, onnxruntime_genai; print('compile venv:', transformers.__version__)"
build() {
  rm -f "$1"/*.py
  python - "$1" << 'PY'
import json, sys
p = sys.argv[1] + '/config.json'
c = json.load(open(p)); c.pop('auto_map', None); json.dump(c, open(p, 'w'), indent=2)
PY
  echo "[$(date +%H:%M:%S)] building $2"
  if python -m onnxruntime_genai.models.builder -i "$1" -o "$2" -p int4 -e cpu >> /tmp/compiler.log 2>&1; then
    echo "[$(date +%H:%M:%S)] $2 OK"
  else
    echo "[$(date +%H:%M:%S)] $2 FAILED"
  fi
}
[ -f phi4mini-stock-int4/genai_config.json ] || build hf/Phi-4-mini-instruct phi4mini-stock-int4
for V in loto sota myopic prediction coordination; do
  while [ ! -f "out/phi-4-mini-$V/merged-bf16/config.json" ]; do sleep 60; done
  sleep 20
  [ -f "phi4mini-$V-int4/genai_config.json" ] || build "out/phi-4-mini-$V/merged-bf16" "phi4mini-$V-int4"
done
echo "[$(date +%H:%M:%S)] ALL COMPILES DONE"
