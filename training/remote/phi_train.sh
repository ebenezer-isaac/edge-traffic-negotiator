#!/bin/bash
# Edge Negotiator: phi-4-mini QLoRA on the full 4-format dataset (gpu-host, RTX 4090)
# Runs entirely in /scratch0 (fast, wiped at session end); results copied to $HOME.
set -e
S=/scratch0/$USER/edgeft
mkdir -p "$S" && cd "$S"
echo "=== $(date) setup start ==="
# 1. venv + stack
if [ ! -d venv ]; then python3 -m venv venv; fi
source venv/bin/activate
pip install -q --upgrade pip
pip install -q torch --index-url https://download.pytorch.org/whl/cu124
pip install -q "numpy<2.2" "transformers>=4.51,<5" peft datasets accelerate bitsandbytes huggingface_hub
echo "=== $(date) stack installed ==="
python -c "import torch; print('cuda:', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# 2. base checkpoint
if [ ! -f hf/Phi-4-mini-instruct/config.json ]; then
  mkdir -p hf
  python -c "from huggingface_hub import snapshot_download; snapshot_download('microsoft/Phi-4-mini-instruct', local_dir='hf/Phi-4-mini-instruct')"
fi
echo "=== $(date) checkpoint ready ==="
# 3. dataset + training script from staged home bundle
cp -r "$HOME/edge-ft-bundle/ft_dataset" .
cp "$HOME/edge-ft-bundle/finetune_train.py" .
# 4. train (family-aware script: phi template, /no_think stripped)
export FT_BASE_MODEL="$S/hf/Phi-4-mini-instruct"
export FT_OUT_DIR="$S/out/phi-4-mini"
export FT_DATA_DIR="$S/ft_dataset"
echo "=== $(date) TRAINING START ==="
python finetune_train.py --step train
echo "=== $(date) TRAINING DONE, merging ==="
python finetune_train.py --step merge
echo "=== $(date) MERGE DONE, archiving to home ==="
# 5. persist: adapter (small) to home; merged tarball to home if quota allows, else stays in scratch for scp
cp -r "$S/out/phi-4-mini/adapter" "$HOME/phi4mini-ft-adapter" || true
tar -C "$S/out/phi-4-mini" -czf "$S/phi4mini-merged-bf16.tgz" merged-bf16 && \
  (cp "$S/phi4mini-merged-bf16.tgz" "$HOME/" && echo "merged tarball in HOME" || echo "HOME copy failed (quota?) - tarball remains in $S")
echo "=== $(date) ALL DONE ==="
