# Models: downloading and serving the fine-tuned controllers on Foundry Local

The fine-tuned models are published as assets on the
[v1.0 release](https://github.com/ebenezer-isaac/edge-traffic-negotiator/releases/tag/v1.0).
Each zip is a ready-to-serve Foundry Local custom model: int4 ONNX weights, tokenizer,
`genai_config.json` set to the WebGPU provider, and an `inference_model.json` with the chat template.

| Asset | Model id | What it is |
|---|---|---|
| `qwen3-0.6b-ft1.zip` (~390 MB) | `qwen3-0.6b-ft1` | Qwen3-0.6B, QLoRA fine-tuned on 14,493 delay-aware (`sota` format) decisions, 2 epochs, about 3.9 h on an RTX 2060. **The student behind the dissertation's headline results** (all closed-loop `ft1` runs in `results/`). |
| `qwen3-0.6b-ft2.zip` (~390 MB) | `qwen3-0.6b-ft2` | Qwen3-0.6B fine-tuned on all four prompt formats (59,533 rows), about 13.5 h on the same RTX 2060. The generalist used for the offline 4-format table. |
| `qwen3-0.6b-ft0.zip` (~390 MB) | `qwen3-0.6b-ft0` | **Stock** Qwen3-0.6B compiled through the identical int4 pipeline. This is the fair control for every fine-tune comparison. |
| `phi4mini-gen-gpu.zip.001`, `.002` (~2.4 GB total) | `phi4mini-gen-gpu` | Phi-4-mini (3.8B), fine-tuned on all four formats on an RTX 4090; served on the RTX 2060. Split into two parts because of GitHub's 2 GiB asset limit. |
| `qwen3-0.6b-lora-v1.zip`, `qwen3-0.6b-lora-v2.zip` | n/a | The LoRA adapters for `ft1` and `ft2` (apply to `Qwen/Qwen3-0.6B`). |
| `ft_dataset_train.jsonl.gz` | n/a | The 59,533-row distillation training set (the 5,580-row holdout is in `results/ft_dataset/holdout.jsonl`). |

Tested with Foundry Local 0.8.119 on Windows with an NVIDIA RTX 2060 (WebGPU). Newer preview
releases renamed `foundry service ...` to `foundry server ...` and `foundry model run` to
`foundry run`; other platforms and versions are untested.

Why not the catalog `qwen3-0.6b`? On the RTX 2060 the catalog WebGPU build of Qwen3-0.6B emits
garbage tokens . `ft0` is the same stock weights through the
pipeline that works, and it is the control the dissertation compares against.

The same models are on Hugging Face, one repo each:
[ft1](https://huggingface.co/ebnezr-isaac/qwen3-0.6b-traffic-signal-ft1),
[ft2](https://huggingface.co/ebnezr-isaac/qwen3-0.6b-traffic-signal-ft2),
[ft0](https://huggingface.co/ebnezr-isaac/qwen3-0.6b-traffic-signal-ft0-stock),
[Phi-4-mini](https://huggingface.co/ebnezr-isaac/phi-4-mini-traffic-signal), and the
[dataset](https://huggingface.co/datasets/ebnezr-isaac/traffic-signal-distillation).

## Install one

```bash
# 1. where Foundry Local keeps its models; it prints e.g. "Cache directory path: %USERPROFILE%\.cache\foundry-local"
foundry cache location

# 2a. from Hugging Face, into a subfolder named after the model id
pip install -U huggingface_hub
hf download ebnezr-isaac/qwen3-0.6b-traffic-signal-ft1 --local-dir "<cache folder>/qwen3-0.6b-ft1"

# 2b. or from the GitHub Release (the zip already contains the qwen3-0.6b-ft1/ folder)
curl -LO https://github.com/ebenezer-isaac/edge-traffic-negotiator/releases/download/v1.0/qwen3-0.6b-ft1.zip
tar -xf qwen3-0.6b-ft1.zip -C "<cache folder>"

# 3. load it and check it is listed
foundry model load qwen3-0.6b-ft1
foundry service ps
```

On Windows, use the built-in `tar` (PowerShell or cmd), which reads zip files. Git Bash's `tar` does not.

Then drive a simulation with it:

```bash
python run.py --controller slm --model qwen3-0.6b-ft1
```

For the split Phi asset, join the parts first: `copy /b phi4mini-gen-gpu.zip.001+phi4mini-gen-gpu.zip.002 phi4mini-gen-gpu.zip`
on Windows, or `cat phi4mini-gen-gpu.zip.0* > phi4mini-gen-gpu.zip` elsewhere.

## Build your own

The chain is QLoRA fine-tune → merge to bf16 → int4 ONNX with the ONNX Runtime GenAI builder →
register with Foundry Local:

```bash
pip install -r training/requirements.txt
python src/finetune_train.py                      # FT_BASE_MODEL, FT_OUT_DIR env vars override defaults
python -m onnxruntime_genai.models.builder -i train-out/merged-bf16 -o my-model -p int4 -e cpu
```

The builder writes no `inference_model.json`, and Foundry Local refuses the model without it. It
also writes a CPU provider. `training/eval_chain.sh` shows the two files to add: the chat template,
and a `genai_config.json` provider switch to WebGPU. `docs/finetune-to-foundry.md` records the full
history, including what failed.

## Note on the real-demand sweep labels

`realdemand/results/scoot_sweep_v2.json` was produced in October 2026 with freshly rebuilt artifacts
whose names were swapped. Its arm `slm:qwen3-0.6b-ft1` is the **v2 generalist** (`ft2` above), and
`slm:qwen3-0.6b-ft2` is the **v1 sota model** (`ft1` above). Hashes and a held-out behavioural check
confirm this. `realdemand/README.md` reports those arms by training run.
