# UCL training bundle (Edge Negotiator fine-tune axis) — 2x RTX 6000 edition

Session start: Sunday midnight. Everything here is plain PyTorch — no Foundry, no SUMO.
All MEASURED results happen back on the local machine (Foundry Local serving); this box
only produces checkpoints.

DECISION ALREADY TAKEN (2026-08-08): generalists only — the 4-format generalist matched
the sota specialist offline (97.68% vs 97.42%), so do NOT train format specialists.
Queue = 3 student generalists + the leave-one-topology-out probe.

## Dual-GPU parallel plan (2x RTX 6000)

Run two trainings at once, one per GPU, via CUDA_VISIBLE_DEVICES:

```bash
# GPU 0: phi-4-mini (longest — start first)     GPU 1: qwen3-1.7b
CUDA_VISIBLE_DEVICES=0 FT_BASE_MODEL=$PWD/hf/Phi-4-mini-instruct  FT_OUT_DIR=$PWD/out/phi-4-mini  python finetune_train.py --step train &
CUDA_VISIBLE_DEVICES=1 FT_BASE_MODEL=$PWD/hf/Qwen3-1.7B           FT_OUT_DIR=$PWD/out/qwen3-1.7b  python finetune_train.py --step train &
wait
# then GPU 0: qwen2.5-0.5b                      GPU 1: LOTO probe (qwen3-0.6b base, Old St held out)
CUDA_VISIBLE_DEVICES=0 FT_BASE_MODEL=$PWD/hf/Qwen2.5-0.5B-Instruct FT_OUT_DIR=$PWD/out/qwen2.5-0.5b python finetune_train.py --step train &
python filter_loto.py oldstreet_junction && mkdir -p ft_dataset_loto && cp ft_dataset/train_no_oldstreet_junction.jsonl ft_dataset_loto/train.jsonl && cp ft_dataset/holdout.jsonl ft_dataset_loto/
CUDA_VISIBLE_DEVICES=1 FT_BASE_MODEL=$PWD/hf/Qwen3-0.6B FT_DATA_DIR=$PWD/ft_dataset_loto FT_OUT_DIR=$PWD/out/qwen3-0.6b-loto python finetune_train.py --step train &
wait
# merges (CPU, quick) — run for all four out dirs
for d in phi-4-mini qwen3-1.7b qwen2.5-0.5b qwen3-0.6b-loto; do
  case $d in phi-4-mini) B=Phi-4-mini-instruct;; qwen3-1.7b) B=Qwen3-1.7B;; qwen2.5-0.5b) B=Qwen2.5-0.5B-Instruct;; *) B=Qwen3-0.6B;; esac
  FT_BASE_MODEL=$PWD/hf/$B FT_OUT_DIR=$PWD/out/$d ${d:+FT_DATA_DIR=$PWD/ft_dataset} python finetune_train.py --step merge
done
```

Also download Qwen/Qwen3-0.6B into hf/ for the LOTO run. On 24-48GB cards the pinned
batch settings are conservative; you may raise --batch to 16 for the small models.
Estimated wall-clock with parallelism: ~6-9h total for all four.

## Setup (once, ~10 min)

```bash
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt          # torch CUDA wheel appropriate to the box's driver
mkdir -p hf out
# pull base checkpoints (bf16 safetensors + tokenizer):
for M in Qwen/Qwen2.5-0.5B-Instruct Qwen/Qwen3-1.7B microsoft/Phi-4-mini-instruct; do
  huggingface-cli download "$M" --local-dir "hf/$(basename $M)"
done
```

## Runs (sequential; ~1h + ~8h + ~12h at 16GB)

The script reads env vars: FT_BASE_MODEL (base checkpoint dir), FT_OUT_DIR (output),
FT_DATA_DIR (this bundle's `ft_dataset/` with train.jsonl/holdout.jsonl).
Template handling is automatic per family (qwen3 = ChatML + empty-think + /no_think kept;
qwen2.5 = ChatML, /no_think stripped; phi = <|system|>/<|user|>/<|assistant|>, stripped).

```bash
export FT_DATA_DIR=$PWD/ft_dataset

FT_BASE_MODEL=$PWD/hf/Qwen2.5-0.5B-Instruct FT_OUT_DIR=$PWD/out/qwen2.5-0.5b \
  python finetune_train.py --step train && \
FT_BASE_MODEL=$PWD/hf/Qwen2.5-0.5B-Instruct FT_OUT_DIR=$PWD/out/qwen2.5-0.5b \
  python finetune_train.py --step merge

FT_BASE_MODEL=$PWD/hf/Qwen3-1.7B FT_OUT_DIR=$PWD/out/qwen3-1.7b \
  python finetune_train.py --step train && \
FT_BASE_MODEL=$PWD/hf/Qwen3-1.7B FT_OUT_DIR=$PWD/out/qwen3-1.7b \
  python finetune_train.py --step merge

FT_BASE_MODEL=$PWD/hf/Phi-4-mini-instruct FT_OUT_DIR=$PWD/out/phi-4-mini \
  python finetune_train.py --step train && \
FT_BASE_MODEL=$PWD/hf/Phi-4-mini-instruct FT_OUT_DIR=$PWD/out/phi-4-mini \
  python finetune_train.py --step merge
```

Optional (queue if time remains):
- Leave-one-topology-out probe: filter Old Street rows out of train.jsonl
  (`python filter_loto.py oldstreet_junction`) then retrain qwen3-0.6b base.
- Format specialists: only if the local v1-vs-v2 verdict demanded them (check with Ebenezer).

phi-4-mini notes: needs transformers >= 4.49 (pinned); if tokenizer pad==eos issues
appear, the requirements pin the patched revision. Batch 8 fits 16GB for all three; if
phi OOMs, drop --batch to 4 and double --accum.

## Bring back

Only `out/*/merged-bf16/` directories (each ~1-8GB). Adapters + logs too if convenient.
Local machine then runs: Olive/ort-genai int4 compile -> Foundry cache -> offline eval ->
closed-loop sweeps. No numbers from this box are ever reported.
