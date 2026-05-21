#!/usr/bin/env python3
"""
JADE v1.0 Model Merge Script - Step 4
======================================
Merge the final LoRA checkpoint into a full model

Pipeline:
  03-chunked-untrained/ → train_v10.py → 04-trained-data/
  v1.0/chunk_XXXX/final → merge_model.py → v1.0/jade-v1.0-merged

Usage:
    python3 merge_model.py                    # Merge from last checkpoint
    python3 merge_model.py --checkpoint path  # Merge specific checkpoint
    python3 merge_model.py --cpu              # Force CPU-only merging
    python3 merge_model.py --dry-run          # Preview without merging
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime

# Directories
from pipeline_config import cfg, gp_model_ops
_model_name = cfg["run"]["model_name"]
_version = cfg["run"]["version"]
MODEL_DIR = gp_model_ops / "3-model-registry" / _model_name / _version
STATE_FILE = MODEL_DIR / "training_state.json"
OUTPUT_DIR = MODEL_DIR / f"{_model_name}-merged"

# Model config
MAX_SEQ_LENGTH = 4096


def load_state():
    """Load training state"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def get_last_checkpoint(state):
    """Get path to last trained checkpoint"""
    checkpoint = state.get("last_checkpoint")
    if checkpoint and Path(checkpoint).exists():
        return Path(checkpoint)

    # Fallback: find the highest numbered chunk
    chunk_dirs = sorted(MODEL_DIR.glob("chunk_*/final"))
    if chunk_dirs:
        return chunk_dirs[-1]

    return None


def merge_with_unsloth(checkpoint_path, output_path):
    """Merge using unsloth (GPU-accelerated, may need 24GB+ VRAM)"""
    from unsloth import FastLanguageModel

    print(f"\n[1/3] Loading checkpoint (unsloth)...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(checkpoint_path),
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,
        load_in_4bit=False,
    )

    print(f"\n[2/3] Merging LoRA weights...")
    model = model.merge_and_unload()

    print(f"\n[3/3] Saving merged model to {output_path}...")
    output_path.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)


def merge_with_peft_cpu(checkpoint_path, output_path):
    """Merge using PEFT on CPU (slower but works with limited VRAM)"""
    import torch
    from peft import PeftModel, PeftConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # Force CPU
    device = "cpu"
    print(f"\n[1/4] Loading PEFT config...")
    peft_config = PeftConfig.from_pretrained(str(checkpoint_path))
    base_model_path = peft_config.base_model_name_or_path

    print(f"  Base model: {base_model_path}")

    print(f"\n[2/4] Loading base model on CPU (this takes a while)...")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        torch_dtype=torch.float16,
        device_map={"": device},
        low_cpu_mem_usage=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model_path)

    print(f"\n[3/4] Loading and merging LoRA adapter...")
    model = PeftModel.from_pretrained(base_model, str(checkpoint_path))
    model = model.merge_and_unload()

    print(f"\n[4/4] Saving merged model to {output_path}...")
    output_path.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_path, safe_serialization=True)
    tokenizer.save_pretrained(output_path)


def merge_16bit_gpu(checkpoint_path, output_path):
    """Merge using 16-bit loading with GPU offload"""
    from unsloth import FastLanguageModel

    print(f"\n[1/3] Loading checkpoint in 16-bit mode...")

    # Try loading with unsloth's save_pretrained_merged (more memory efficient)
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(checkpoint_path),
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,
        load_in_4bit=True,  # Load in 4-bit first
    )

    print(f"\n[2/3] Saving merged model (16-bit) to {output_path}...")
    output_path.mkdir(parents=True, exist_ok=True)

    # Use unsloth's efficient save method
    model.save_pretrained_merged(
        str(output_path),
        tokenizer,
        save_method="merged_16bit",
    )

    print(f"\n[3/3] Done!")


def main():
    parser = argparse.ArgumentParser(description='JADE v1.0 Model Merge')
    parser.add_argument('--checkpoint', type=str, help='Path to checkpoint to merge')
    parser.add_argument('--output', type=str, default=str(OUTPUT_DIR), help='Output directory')
    parser.add_argument('--cpu', action='store_true', help='Force CPU-only merging (slower but low VRAM)')
    parser.add_argument('--method', choices=['unsloth', 'peft-cpu', '16bit'], default='16bit',
                        help='Merge method: unsloth (needs 24GB+ VRAM), peft-cpu (slow), 16bit (recommended)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without merging')
    args = parser.parse_args()

    print("=" * 60)
    print("JADE v1.0 MODEL MERGE")
    print("=" * 60)

    # Load state
    state = load_state()

    # Determine checkpoint
    if args.checkpoint:
        checkpoint_path = Path(args.checkpoint)
    else:
        checkpoint_path = get_last_checkpoint(state)

    if not checkpoint_path or not checkpoint_path.exists():
        print(f"Error: No checkpoint found")
        print(f"  Checked: {args.checkpoint or 'last_checkpoint from state'}")
        print(f"\nRun train_v10.py first to create checkpoints")
        return

    output_path = Path(args.output)

    # Force CPU method if --cpu flag
    method = 'peft-cpu' if args.cpu else args.method

    print(f"\nCheckpoint: {checkpoint_path}")
    print(f"Output: {output_path}")
    print(f"Method: {method}")
    print(f"Total examples trained: {state.get('total_examples', 'unknown'):,}")

    if state.get("sessions"):
        last_session = state["sessions"][-1]
        print(f"Last chunk: {last_session.get('chunk')}")
        print(f"Final loss: {last_session.get('loss', 0):.4f}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would merge checkpoint to {output_path}")
        print(f"  Method: {method}")
        return

    # Check dependencies
    try:
        if method == 'peft-cpu':
            from peft import PeftModel
            from transformers import AutoModelForCausalLM
        else:
            from unsloth import FastLanguageModel
    except ImportError as e:
        print(f"\nError: Missing dependency - {e}")
        print("  pip install unsloth peft transformers")
        return

    # Run merge
    try:
        if method == 'unsloth':
            merge_with_unsloth(checkpoint_path, output_path)
        elif method == 'peft-cpu':
            merge_with_peft_cpu(checkpoint_path, output_path)
        elif method == '16bit':
            merge_16bit_gpu(checkpoint_path, output_path)
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"\n[OOM] GPU out of memory. Try:")
            print(f"  python3 merge_model.py --cpu       # CPU-only (slow but works)")
            print(f"  python3 merge_model.py --method 16bit  # Memory-efficient GPU merge")
            return
        raise

    # Update state
    state["merged_at"] = datetime.now().isoformat()
    state["merged_path"] = str(output_path)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

    print(f"\n{'=' * 60}")
    print("MERGE COMPLETE")
    print("=" * 60)
    print(f"Merged model: {output_path}")
    print(f"\nNext steps:")
    print(f"  python3 convert_gguf.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
