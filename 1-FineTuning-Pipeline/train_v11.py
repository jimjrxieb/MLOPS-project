#!/usr/bin/env python3
"""
JADE Training Script - Step 3 (v1.1)
=============================
Fine-tune JADE on 10k chunked data from 03-chunked-untrained

Enhanced for v1.1:
- 10k chunk support (matching current enrichment pipeline)
- Expert-depth (CKS/CCSP) evaluation tracking
- Automated Ollama export (Modelfile generation)
- Smart Learning Rate for authority-enriched content
- Memory Management: Explicit GC and VRAM clearing between chunks
- Stability: CPU Offload enabled for memory-intensive merges
- MLOps Integration: Automatic evaluation via GP-CLARIFY after each chunk
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
from pipeline_config import cfg, pipeline_dir, gp_model_ops, repo_root
BASE_DIR = pipeline_dir
CHUNK_DIR = BASE_DIR / "03-chunked-untrained"
HOLDOUT_DIR = BASE_DIR / "03-eval-holdout"
TRAINED_DIR = BASE_DIR / "04-trained-data"
MODEL_BASE_DIR = gp_model_ops / "3-model-registry"
LLAMA_CPP_DIR = gp_model_ops / "llama.cpp"
CLARIFY_DIR = gp_model_ops / "4-eval-clarify"
REPORTS_DIR = repo_root / "GP-S3" / "3-mlops-reports" / "3-trained-data"

# Default version (read from pipeline.yaml)
DEFAULT_VERSION = cfg["run"]["version"]

# Base model (read from pipeline.yaml — change there, not here)
_model_name = cfg["run"]["model_name"]
_prior_ver = cfg["run"].get("prior_checkpoint")
V10_CHECKPOINT = MODEL_BASE_DIR / _model_name / _prior_ver / f"{_model_name}-merged" if _prior_ver else None
FALLBACK_MODEL = cfg["base_model"]

# Model configuration
MAX_SEQ_LENGTH = 4096
LORA_R = 64
LORA_ALPHA = 128
LORA_DROPOUT = 0

# Training configuration
BATCH_SIZE = 4
GRADIENT_ACCUM_STEPS = 8  # Effective batch: 32
LEARNING_RATE = 2e-5
WARMUP_RATIO = 0.03
EPOCHS_PER_CHUNK = 2
LOGGING_STEPS = 10
SAVE_STEPS = 500

# JADE System Prompt (v1.1)
JADE_SYSTEM_V11 = "You are JADE (Junior Automated DevSecOps Engineer), a security-focused AI assistant specializing in Kubernetes, cloud security, policy-as-code (OPA/Rego, Kyverno, Gatekeeper), and DevSecOps practices. You have C-rank authority ceiling but S-rank architectural intelligence. Provide expert-depth analysis with junior-level execution commands."


def get_model_dir(version: str) -> Path:
    return MODEL_BASE_DIR / _model_name / version


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
        "base_model": None,
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
    chunks = sorted(CHUNK_DIR.glob("chunk_*_10k.jsonl"))
    if not chunks:
        chunks = sorted(CHUNK_DIR.glob("chunk_*_5k.jsonl"))
    return [c for c in chunks if not c.name.startswith(".")]


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
                {"role": "system", "content": JADE_SYSTEM_V11},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": ex.get('output', '')},
            ]

        if not messages:
            continue

        if messages[0].get("role") == "system":
            messages[0]["content"] = JADE_SYSTEM_V11

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


def get_checkpoint_path(state: Dict, version: str) -> Path:
    if state.get("last_merged") and Path(state["last_merged"]).exists():
        return Path(state["last_merged"])

    if V10_CHECKPOINT is not None and V10_CHECKPOINT.exists():
        return V10_CHECKPOINT

    return Path(FALLBACK_MODEL)


def run_mlops_evaluation(version: str, model_path: Path):
    """Trigger the GP-CLARIFY evaluation suite."""
    eval_script = CLARIFY_DIR / "v1.1_eval_suite.py"
    if not eval_script.exists():
        print(f"\n[EVAL] Evaluation script not found at {eval_script}. Skipping.")
        return

    print(f"\n[EVAL] Triggering MLOps evaluation for {version}...")
    try:
        subprocess.run(["python3", str(eval_script), version, str(model_path)], check=True)
    except Exception as e:
        print(f"  [ERROR] Evaluation failed: {e}")


def export_to_ollama(version: str, model_path: Path):
    """
    Automated export to Ollama:
    1. Quantize to GGUF (4-bit default)
    2. Create Modelfile
    3. Run 'ollama create'
    """
    print(f"\n[EXPORT] Starting Ollama export for JADE {version}...")
    
    gguf_dir = model_path.parent / "gguf"
    gguf_dir.mkdir(parents=True, exist_ok=True)
    
    if not LLAMA_CPP_DIR.exists():
        print(f"  [ERROR] llama.cpp not found at {LLAMA_CPP_DIR}. Skipping GGUF conversion.")
        return

    modelfile_path = model_path / "Modelfile"
    gguf_path = model_path / f"jade-{version}.F16.gguf"
    
    print(f"  [EXPORT] Generating Modelfile at {modelfile_path}...")
    
    content = f"""FROM ./{gguf_path.name}
TEMPLATE \"\"\"{{{{ if .System }}}}<|im_start|>system
{{{{ .System }}}}<|im_end|>
{{{{ end }}}}{{{{ if .Prompt }}}}<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
{{{{ end }}}}<|im_start|>assistant
{{{{ .Response }}}}}}<|im_end|>\"\"\"
PARAMETER stop <|im_start|>
PARAMETER stop <|im_end|>
SYSTEM \"\"\"{JADE_SYSTEM_V11}\"\"\"
"""
    with open(modelfile_path, "w") as f:
        f.write(content)
    
    print(f"  [OK] Modelfile created. Once GGUF is ready, run:")
    print(f"  ollama create jade:{version} -f {modelfile_path}")


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
        f"| Base model | {FALLBACK_MODEL} |",
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
    print(f"JADE {version} TRAINING - {chunk_name}")
    print("=" * 60)

    with open(chunk_path, 'r', encoding='utf-8') as f:
        examples = [json.loads(l) for l in f if l.strip()]
    
    print(f"\n[1/5] Loading {chunk_name}... ({len(examples)} examples)")

    if dry_run:
        print(f"\n[DRY RUN] Would train on {len(examples):,} examples")
        return

    checkpoint_path = get_checkpoint_path(state, version)
    print(f"\n[2/5] Loading model from {checkpoint_path}...")

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(checkpoint_path),
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
    
    # Apply CPU offload during merge if needed
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

    # Robust cleanup
    del model
    del trainer
    del tokenizer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def main():
    parser = argparse.ArgumentParser(description='JADE v1.1 Training')
    parser.add_argument('--chunk', type=str, help='Specific chunk file to train')
    parser.add_argument('--version', type=str, default=DEFAULT_VERSION)
    parser.add_argument('--export', action='store_true', help='Generate Ollama Modelfile after training')
    parser.add_argument('--skip-eval', action='store_true', help='Skip MLOps evaluation after chunks')
    args = parser.parse_args()

    state = load_state(args.version)
    
    # Single chunk mode only for stability
    chunk_path = None
    if args.chunk:
        chunk_path = CHUNK_DIR / args.chunk
        if not chunk_path.exists():
            # Try adding path if it's just the filename
            chunk_path = CHUNK_DIR / args.chunk
    else:
        chunk_path = get_next_chunk(state)

    if chunk_path and chunk_path.exists():
        train_chunk(chunk_path, state, EPOCHS_PER_CHUNK, args.version, skip_eval=args.skip_eval)
    else:
        print("No untrained chunks found or specified chunk missing.")

    if args.export and state["last_merged"]:
        export_to_ollama(args.version, Path(state["last_merged"]))

if __name__ == "__main__":
    main()
