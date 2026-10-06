#!/bin/bash
# Coordination variant: stream from gpu-host -> extract C: -> compile int4 on C: -> junction on E:
J="${JUMP_HOST}"; H="${GPU_HOST}"
S=/scratch0/$USER/edgeft
PY="${EDGE_NEGOTIATOR_DIR:-.}/.venv-olive/Scripts/python.exe"
V=coordination
WORK="$HOME/phi4-work/$V"
OUT_C="$HOME/phi4-int4/phi4mini-$V-int4"
rm -rf "$WORK" "$OUT_C"; mkdir -p "$WORK" $HOME/phi4-int4
echo "[$(date +%H:%M)] streaming $V to C:"
ssh -o BatchMode=yes -o ConnectTimeout=25 -J "$J" "$H" "cat $S/phi4mini-$V-merged.tgz" | tar -xz -C "$WORK" || { echo "STREAM FAILED"; exit 2; }
echo "[$(date +%H:%M)] compiling $V int4 on C:"
"$PY" -m onnxruntime_genai.models.builder -i "~/phi4-work/$V/merged-bf16" -o "~/phi4-int4/phi4mini-$V-int4" -p int4 -e cpu > "${FT_WORKSPACE:-.}/compile_$V.log" 2>&1 || { echo "COMPILE FAILED"; tail -5 "${FT_WORKSPACE:-.}/compile_$V.log"; exit 3; }
sed -i 's/"tokenizer_class": "TokenizersBackend"/"tokenizer_class": "GPT2Tokenizer"/' "$OUT_C/tokenizer_config.json" 2>/dev/null
rm -rf "$WORK"
cmd //c "mklink /J $FT_WORKSPACE\onnx\phi4mini-$V-int4 ~\phi4-int4\phi4mini-$V-int4" || echo "JUNCTION FAILED (create manually)"
echo "[$(date +%H:%M)] $V int4 DONE on C: + junction on E:"
