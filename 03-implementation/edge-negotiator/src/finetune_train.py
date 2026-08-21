"""QLoRA fine-tune of Qwen3-0.6B on the Claude-distilled traffic-decision dataset
(MASTER-SPEC §14.3 steps 4-5). Runs in the DEDICATED training venv
(e:/ft-workspace/.venv-train — torch 2.6.0+cu124, transformers 4.x, peft, trl,
bitsandbytes), NOT the project venv. Serving stays Foundry Local; this script only
produces the merged bf16 checkpoint that the ort-genai model builder then compiles
to int4 ONNX (the pinned FT-0 compile path).

PINNED FORMAT (must match serving byte-for-byte):
  * ChatML rendered MANUALLY (not via apply_chat_template) so the trained prompt
    region equals what Foundry Local's inference_model.json PromptTemplate emits:
    <|im_start|>system\n{sys}<|im_end|>\n<|im_start|>user\n{usr}<|im_end|>\n<|im_start|>assistant\n
  * The system prompt in train.jsonl already carries the trailing " /no_think"
    (the live qwen3 think_suffix).
  * Assistant completion = Qwen3's no-think convention: an EMPTY think block, then
    exactly {"phase": N} (unquoted int - SLMAgent._parse's primary regex), then EOS.
  * Completion-only loss (prompt tokens masked at -100).

VRAM: 4-bit NF4 base (bitsandbytes, works on Turing sm_75) + LoRA r=16 keeps this
well under the RTX 2060's 6GB even with Foundry Local idle-resident. Unload any
GPU-loaded Foundry models before training.
"""
from __future__ import annotations

import argparse
import json
import os

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
                          Trainer, TrainingArguments)

FTDIR = os.environ.get("FT_DATA_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "ft_dataset")
BASE = os.environ.get("FT_BASE_MODEL", r"e:\ft-workspace\hf\Qwen3-0.6B")
OUT = os.environ.get("FT_OUT_DIR", r"e:\ft-workspace\train-out")

IM_START, IM_END = "<|im_start|>", "<|im_end|>"
EMPTY_THINK = "<think>\n\n</think>\n\n"


def _family():
    """Template family from the base checkpoint name (portability across students)."""
    b = BASE.lower()
    if "phi" in b:
        return "phi"
    if "qwen3" in b:
        return "qwen3"
    return "chatml"  # qwen2.5 and other ChatML models, no think block


def render(messages):
    """(prompt_text, completion_text) matching how each family is SERVED.

    qwen3: ChatML; system keeps the trailing " /no_think" (the live think_suffix fires
      for any served id containing "qwen3"); completion opens with an empty think block.
    chatml (qwen2.5): ChatML; the " /no_think" baked into the dataset system prompts is
      STRIPPED (serving never appends it for non-qwen3 ids); no think block.
    phi (phi-4-mini): <|system|>..<|end|><|user|>..<|end|><|assistant|> layout; suffix
      stripped; no think block.
    """
    fam = _family()
    sys_c = next(m["content"] for m in messages if m["role"] == "system")
    usr_c = next(m["content"] for m in messages if m["role"] == "user")
    asst = next(m["content"] for m in messages if m["role"] == "assistant")
    if fam != "qwen3" and sys_c.endswith(" /no_think"):
        sys_c = sys_c[: -len(" /no_think")]
    if fam == "phi":
        prompt = f"<|system|>{sys_c}<|end|><|user|>{usr_c}<|end|><|assistant|>"
        completion = f"{asst}<|end|>"
    else:
        prompt = (f"{IM_START}system\n{sys_c}{IM_END}\n"
                  f"{IM_START}user\n{usr_c}{IM_END}\n"
                  f"{IM_START}assistant\n")
        completion = (f"{EMPTY_THINK}{asst}{IM_END}" if fam == "qwen3"
                      else f"{asst}{IM_END}")
    return prompt, completion


def load_split(name):
    rows = []
    with open(os.path.join(FTDIR, f"{name}.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            rows.append(json.loads(line))
    return rows


def build_dataset(rows, tokenizer, max_len=512):
    feats = []
    for r in rows:
        prompt, completion = render(r["messages"])
        p_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        c_ids = tokenizer(completion, add_special_tokens=False)["input_ids"]
        ids = (p_ids + c_ids)[:max_len]
        labels = ([-100] * len(p_ids) + c_ids)[:max_len]
        feats.append({"input_ids": ids, "labels": labels,
                      "attention_mask": [1] * len(ids)})
    return Dataset.from_list(feats)


class PadCollator:
    def __init__(self, pad_id):
        self.pad_id = pad_id

    def __call__(self, batch):
        width = max(len(b["input_ids"]) for b in batch)
        out = {"input_ids": [], "labels": [], "attention_mask": []}
        for b in batch:
            pad = width - len(b["input_ids"])
            out["input_ids"].append(b["input_ids"] + [self.pad_id] * pad)
            out["labels"].append(b["labels"] + [-100] * pad)
            out["attention_mask"].append(b["attention_mask"] + [0] * pad)
        return {k: torch.tensor(v) for k, v in out.items()}


def main(epochs=2, lr=2e-4, rank=16, batch=8, accum=2, max_len=512, seed=42):
    os.makedirs(OUT, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(BASE)
    train_rows = load_split("train")
    print(f"train examples: {len(train_rows)}", flush=True)

    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.float16,
                             bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(BASE, quantization_config=bnb,
                                                 torch_dtype=torch.float16,
                                                 device_map={"": 0})
    model = prepare_model_for_kbit_training(model)
    lora = LoraConfig(r=rank, lora_alpha=2 * rank, lora_dropout=0.05,
                      task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                      "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    ds = build_dataset(train_rows, tok, max_len=max_len)
    args = TrainingArguments(
        output_dir=os.path.join(OUT, "checkpoints"), num_train_epochs=epochs,
        per_device_train_batch_size=batch, gradient_accumulation_steps=accum,
        learning_rate=lr, lr_scheduler_type="cosine", warmup_ratio=0.03,
        logging_steps=25, save_strategy="epoch", seed=seed, fp16=True,
        report_to=[], dataloader_pin_memory=False)
    trainer = Trainer(model=model, args=args, train_dataset=ds,
                      data_collator=PadCollator(tok.pad_token_id))
    trainer.train()
    adapter_dir = os.path.join(OUT, "adapter")
    model.save_pretrained(adapter_dir)
    tok.save_pretrained(adapter_dir)
    print(f"adapter saved -> {adapter_dir}", flush=True)


def merge():
    """Merge the LoRA adapter into a bf16 checkpoint (NEVER export from 4-bit)."""
    from peft import PeftModel
    base = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16,
                                                device_map="cpu")
    merged = PeftModel.from_pretrained(base, os.path.join(OUT, "adapter"))
    merged = merged.merge_and_unload()
    out = os.path.join(OUT, "merged-bf16")
    merged.save_pretrained(out)
    AutoTokenizer.from_pretrained(BASE).save_pretrained(out)
    print(f"merged bf16 checkpoint -> {out}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="QLoRA fine-tune qwen3-0.6b (§14.3 step 4).")
    ap.add_argument("--step", choices=["train", "merge"], required=True)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--accum", type=int, default=2)
    ns = ap.parse_args()
    if ns.step == "train":
        main(epochs=ns.epochs, lr=ns.lr, rank=ns.rank, batch=ns.batch, accum=ns.accum)
    else:
        merge()
