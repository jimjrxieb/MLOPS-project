#!/usr/bin/env python3
"""
JADE Training Script - Llama 3.2 3B
=============================
Fine-tune JADE on 10k chunked data from 03-chunked-untrained using Llama 3.2 3B.

Optimized for RTX 5080 16GB.
"""

import json
import shutil
import argparse
import os
import subprocess
import gc
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Check dependencies before importing
try:
    import torch
    from datasets import Dataset
    from unsloth import FastLanguageModel, is_bfloat16_supported
    from trl import SFTTrainer
    from transformers import TrainingArguments
    HAS_TRAINING_DEPS = True
except ImportError:
    HAS_TRAINING_DEPS = False

# Directories
BASE_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-FineTuning-Pipeline")
GP_ROOT = Path("/home/jimmie/linkops-industries/GP-copilot")
CHUNK_DIR = BASE_DIR / "03-chunked-untrained"
HOLDOUT_DIR = BASE_DIR / "03-eval-holdout"
TRAINED_DIR = BASE_DIR / "04-trained-data"
MODEL_BASE_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/3-model-registry")
LLAMA_CPP_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/llama.cpp")
CLARIFY_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/4-eval-clarify")
REPORTS_DIR = GP_ROOT / "GP-S3" / "3-mlops-reports" / "3-trained-data"

# Default version for Llama 3B
DEFAULT_VERSION = "v1.1-3b"

# Base model
BASE_MODEL = "unsloth/Llama-3.2-3B-Instruct"

# Model configuration
MAX_SEQ_LENGTH = 2048
LORA_R = 64
LORA_ALPHA = 128
LORA_DROPOUT = 0

# Training configuration
BATCH_SIZE = 4
GRADIENT_ACCUM_STEPS = 8  # Effective batch: 32
LEARNING_RATE = 2e-5
WARMUP_RATIO = 0.03
EPOCHS_PER_CHUNK = 2
LOGGING_STEPS = 1
SAVE_STEPS = 500

# JADE System Prompt
JADE_SYSTEM = "You are JADE (Junior Automated DevSecOps Engineer), a security-focused AI assistant specializing in Kubernetes, cloud security, policy-as-code (OPA/Rego, Kyverno, Gatekeeper), and DevSecOps practices. You have C-rank authority ceiling but S-rank architectural intelligence. Provide expert-depth analysis with junior-level execution commands."


def get_model_dir(version: str) -> Path:
    return MODEL_BASE_DIR / version


def get_state_file(version: str) -> Path:
    return get_model_dir(version) / "training_state.json"


def load_state(version: str) -> Dict:
    state_file = get_state_file(version)
    if state_file.exists():
        with open(state_file) as f:
            return json.load(f)

    return {
        "version": version,
        "started_at": None,
        "base_model": BASE_MODEL,
        "chunks_completed": [],
        "current_chunk": None,
        "total_examples": 0,
        "last_merged": None,
        "sessions": []
    }


def save_state(state: Dict, version: str):
    model_dir = get_model_dir(version)
    model_dir.mkdir(parents=True, exist_ok=True)
    with open(get_state_file(version), 'w') as f:
        json.dump(state, f, indent=2)


def get_available_chunks() -> List[Path]:
    if not CHUNK_DIR.exists():
        return []
    # Priority to _v2 chunks then original 10k/5k chunks, then others
    chunks = sorted(CHUNK_DIR.glob("chunk_*_v2.jsonl"))
    chunks.extend(sorted(CHUNK_DIR.glob("chunk_*_10k.jsonl")))
    chunks.extend(sorted(CHUNK_DIR.glob("chunk_*_5k.jsonl")))
    chunks.extend(sorted(CHUNK_DIR.glob("*.jsonl")))
    
    seen = set()
    unique_chunks = []
    for c in chunks:
        if c.name not in seen and not c.name.startswith("."):
            unique_chunks.append(c)
            seen.add(c.name)
    return unique_chunks


def get_next_chunk(state: Dict) -> Optional[Path]:
    available = get_available_chunks()
    completed = set(state.get("chunks_completed", []))

    for chunk in available:
        if chunk.name not in completed:
            return chunk

    return None


def format_for_training(examples: List[Dict], tokenizer) -> List[Dict]:
    formatted = []

    for ex in examples:
        messages = ex.get('messages', [])

        # Convert instruction/input/output (Alpaca) format to messages
        if not messages and 'instruction' in ex:
            user_content = ex['instruction']
            if ex.get('input'):
                user_content += f"\n\n{ex['input']}"
            messages = [
                {"role": "system", "content": JADE_SYSTEM},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": ex.get('output', '')},
            ]

        if not messages:
            continue

        if messages[0].get("role") == "system":
            messages[0]["content"] = JADE_SYSTEM

        try:
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False
            )
            formatted.append({"text": text})
        except Exception:
            continue

    return formatted


def get_checkpoint_path(state: Dict) -> str:
    if state.get("last_merged") and Path(state["last_merged"]).exists():
        return state["last_merged"]
    return BASE_MODEL


def run_mlops_evaluation(version: str, model_path: Path):
    """Trigger the GP-CLARIFY evaluation suite."""
    # Using the baseline script we moved to raw-data-lake (as a proxy for now or specialized eval)
    # But standard pipeline uses v1.1_eval_suite.py
    eval_script = CLARIFY_DIR / "v1.1_eval_suite.py"
    if not eval_script.exists():
        print(f"\n[EVAL] Evaluation script not found at {eval_script}. Skipping.")
        return

    print(f"\n[EVAL] Triggering MLOps evaluation for {version}...")
    try:
        # We need to ensure the eval suite can handle the model path
        subprocess.run(["python3", str(eval_script), version, str(model_path)], check=True)
    except Exception as e:
        print(f"  [ERROR] Evaluation failed: {e}")


def write_training_report(chunk_name: str, num_examples: int, state: Dict,
                          version: str, merged_path: str, train_time: float):
    """Write training report to GP-S3/3-mlops-reports/3-trained-data/"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = REPORTS_DIR / f"training-{version}-{timestamp}.md"

    completed = state.get("chunks_completed", [])
    total_chunks = len(get_available_chunks()) + len(completed)
    remaining = total_chunks - len(completed)
    progress_pct = (len(completed) / total_chunks * 100) if total_chunks > 0 else 0

    lines = [
        f"# Training Report — {version}",
        f"",
        f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Chunk:** {chunk_name}",
        f"**Status:** COMPLETE",
        f"",
        f"## This Chunk",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Chunk | {chunk_name} |",
        f"| Examples trained | {num_examples:,} |",
        f"| Epochs | {EPOCHS_PER_CHUNK} |",
        f"| Training time | {train_time:.1f}s ({train_time/60:.1f}m) |",
        f"| Merged to | `{merged_path}` |",
        f"",
        f"## Cumulative Progress",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Base model | {BASE_MODEL} |",
        f"| Chunks completed | {len(completed)} / {total_chunks} |",
        f"| Chunks remaining | {remaining} |",
        f"| Progress | {progress_pct:.0f}% |",
        f"| Total examples trained | {state.get('total_examples', 0):,} |",
        f"| Last merged checkpoint | `{state.get('last_merged', 'N/A')}` |",
        f"",
        f"## Training Config",
        f"",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| LoRA r | {LORA_R} |",
        f"| LoRA alpha | {LORA_ALPHA} |",
        f"| Batch size | {BATCH_SIZE} |",
        f"| Gradient accum | {GRADIENT_ACCUM_STEPS} |",
        f"| Effective batch | {BATCH_SIZE * GRADIENT_ACCUM_STEPS} |",
        f"| Learning rate | {LEARNING_RATE} |",
        f"| Max seq length | {MAX_SEQ_LENGTH} |",
        f"| Warmup ratio | {WARMUP_RATIO} |",
        f"",
        f"## Chunks Completed",
        f"",
    ]
    for i, c in enumerate(completed, 1):
        lines.append(f"{i}. {c}")

    lines.append("")

    with open(report_file, 'w') as f:
        f.write('\n'.join(lines))

    print(f"  [REPORT] {report_file}")


def train_chunk(chunk_path: Path, state: Dict, epochs: int, version: str,
                dry_run: bool = False, skip_eval: bool = False):
    chunk_name = chunk_path.name
    model_dir = get_model_dir(version)
    train_start = datetime.now()

    print("=" * 60)
    print(f"JADE {version} TRAINING (Llama 3.2 3B) - {chunk_name}")
    print("=" * 60)

    with open(chunk_path, 'r', encoding='utf-8') as f:
        examples = [json.loads(l) for l in f if l.strip()]

    print(f"\n[1/5] Loading {chunk_name}... ({len(examples)} examples)")

    if dry_run:
        print(f"\n[DRY RUN] Would train on {len(examples):,} examples")
        state.setdefault("chunks_completed", []).append(chunk_name)
        return

    checkpoint_path = get_checkpoint_path(state)
    print(f"\n[2/5] Loading model from {checkpoint_path}...")

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=checkpoint_path,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,
        load_in_4bit=True,
        device_map="auto"
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                       "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    print(f"\n[3/5] Formatting dataset...")
    formatted = format_for_training(examples, tokenizer)
    dataset = Dataset.from_dict({"text": [ex["text"] for ex in formatted]})

    print(f"\n[4/5] Configuring trainer...")
    chunk_tag = chunk_name.replace(".jsonl", "")
    output_dir = model_dir / chunk_tag

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUM_STEPS,
        learning_rate=LEARNING_RATE,
        lr_scheduler_type="cosine",
        warmup_ratio=WARMUP_RATIO,
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        logging_steps=LOGGING_STEPS,
        save_strategy="no",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        args=training_args,
    )

    print(f"\n[5/5] Training...")
    trainer.train()

    merged_path = output_dir / "merged"
    print(f"\n[MERGE] Saving merged 16bit model to {merged_path}...")
    
    model.save_pretrained_merged(
        str(merged_path), 
        tokenizer, 
        save_method="merged_16bit",
    )

    state["chunks_completed"].append(chunk_name)
    state["total_examples"] += len(formatted)
    state["last_merged"] = str(merged_path)
    save_state(state, version)

    version_trained_dir = TRAINED_DIR / version
    version_trained_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(chunk_path), str(version_trained_dir / chunk_name))

    train_elapsed = (datetime.now() - train_start).total_seconds()
    print(f"\n[OK] Chunk {chunk_name} complete. ({train_elapsed/60:.1f}m)")

    write_training_report(chunk_name, len(formatted), state, version,
                          str(merged_path), train_elapsed)

    if not skip_eval:
        run_mlops_evaluation(version, merged_path)

    # Cleanup
    del model
    del trainer
    del tokenizer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def main():
    parser = argparse.ArgumentParser(description='JADE Llama 3.2 3B Training')
    parser.add_argument('--chunk', type=str, help='Specific chunk file to train')
    parser.add_argument('--version', type=str, default=DEFAULT_VERSION)
    parser.add_argument('--skip-eval', action='store_true', help='Skip MLOps evaluation after chunks')
    parser.add_argument('--loop', action='store_true', help='Train all remaining chunks in a loop')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be trained')
    parser.add_argument('--status', action='store_true', help='Show training progress')
    args = parser.parse_args()

    state = load_state(args.version)
    
    if args.status:
        completed = state.get("chunks_completed", [])
        available = get_available_chunks()
        print(f"JADE {args.version} Status:")
        print(f"  Chunks completed: {len(completed)}")
        print(f"  Chunks remaining: {len(available) - len(completed) if available else 0}")
        print(f"  Total examples:   {state.get('total_examples', 0):,}")
        return

    if args.loop:
        while True:
            chunk_path = get_next_chunk(state)
            if not chunk_path:
                print("No more chunks to train.")
                break
            train_chunk(chunk_path, state, EPOCHS_PER_CHUNK, args.version, dry_run=args.dry_run, skip_eval=args.skip_eval)
    else:
        chunk_path = None
        if args.chunk:
            chunk_path = CHUNK_DIR / args.chunk
        else:
            chunk_path = get_next_chunk(state)

        if chunk_path and chunk_path.exists():
            train_chunk(chunk_path, state, EPOCHS_PER_CHUNK, args.version, dry_run=args.dry_run, skip_eval=args.skip_eval)
        else:
            print("No untrained chunks found or specified chunk missing.")

if __name__ == "__main__":
    main()
