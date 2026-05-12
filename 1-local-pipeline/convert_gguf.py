#!/usr/bin/env python3
"""
JADE v1.0 GGUF Conversion Script - Step 5
==========================================
Convert merged model to GGUF format for Ollama

Pipeline:
  v1.0/jade-v1.0-merged → convert_gguf.py → v1.0/jade-v1.0.gguf

Requires: llama.cpp (for convert.py and quantize)

Usage:
    python3 convert_gguf.py                    # Convert with Q4_K_M quantization
    python3 convert_gguf.py --quant Q8_0       # Use different quantization
    python3 convert_gguf.py --no-quant         # Skip quantization (F16)
    python3 convert_gguf.py --dry-run          # Preview without converting
"""

import os
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Directories
MODEL_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/3-jade-model-versions/v1.0")
STATE_FILE = MODEL_DIR / "training_state.json"
MERGED_DIR = MODEL_DIR / "jade-v1.0-merged"

# llama.cpp location
LLAMA_CPP = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/llama.cpp")
CONVERT_SCRIPT = LLAMA_CPP / "convert_hf_to_gguf.py"
QUANTIZE_BIN = LLAMA_CPP / "build" / "bin" / "llama-quantize"

# Quantization options
QUANT_TYPES = ["Q4_K_M", "Q5_K_M", "Q8_0", "F16"]
DEFAULT_QUANT = "Q4_K_M"


def load_state():
    """Load training state"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def check_llama_cpp():
    """Check if llama.cpp is available"""
    issues = []

    if not LLAMA_CPP.exists():
        issues.append(f"llama.cpp not found at {LLAMA_CPP}")
        issues.append("Clone it: git clone https://github.com/ggerganov/llama.cpp")

    if not CONVERT_SCRIPT.exists():
        issues.append(f"Convert script not found: {CONVERT_SCRIPT}")

    if not QUANTIZE_BIN.exists():
        issues.append(f"Quantize binary not found: {QUANTIZE_BIN}")
        issues.append("Build it: cd llama.cpp && mkdir build && cd build && cmake .. && make -j")

    return issues


def main():
    parser = argparse.ArgumentParser(description='JADE v1.0 GGUF Conversion')
    parser.add_argument('--input', type=str, default=str(MERGED_DIR), help='Path to merged model')
    parser.add_argument('--quant', type=str, default=DEFAULT_QUANT, choices=QUANT_TYPES, help='Quantization type')
    parser.add_argument('--no-quant', action='store_true', help='Skip quantization (F16 only)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without converting')
    args = parser.parse_args()

    print("=" * 60)
    print("JADE v1.0 GGUF CONVERSION")
    print("=" * 60)

    input_path = Path(args.input)
    quant_type = "F16" if args.no_quant else args.quant

    # Output paths
    f16_path = MODEL_DIR / "jade-v1.0-f16.gguf"
    final_path = MODEL_DIR / f"jade-v1.0-{quant_type.lower()}.gguf"

    print(f"\nInput: {input_path}")
    print(f"Quantization: {quant_type}")
    print(f"Output: {final_path}")

    # Check input exists
    if not input_path.exists():
        print(f"\nError: Merged model not found at {input_path}")
        print("Run merge_model.py first")
        return

    # Check llama.cpp
    issues = check_llama_cpp()
    if issues:
        print("\nError: llama.cpp setup issues:")
        for issue in issues:
            print(f"  - {issue}")
        return

    if args.dry_run:
        print(f"\n[DRY RUN] Would convert to GGUF:")
        print(f"  1. Convert to F16: {f16_path}")
        if quant_type != "F16":
            print(f"  2. Quantize to {quant_type}: {final_path}")
        return

    # Step 1: Convert to GGUF (F16)
    print(f"\n[1/2] Converting to GGUF (F16)...")
    cmd = [
        "python3", str(CONVERT_SCRIPT),
        str(input_path),
        "--outfile", str(f16_path),
        "--outtype", "f16"
    ]
    print(f"  Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Error: {result.stderr}")
        return
    print(f"  Created: {f16_path}")

    # Step 2: Quantize (if not F16)
    if quant_type != "F16":
        print(f"\n[2/2] Quantizing to {quant_type}...")
        cmd = [
            str(QUANTIZE_BIN),
            str(f16_path),
            str(final_path),
            quant_type
        ]
        print(f"  Running: {' '.join(cmd)}")

        # Set LD_LIBRARY_PATH so llama-quantize can find libllama.so
        env = os.environ.copy()
        lib_path = str(LLAMA_CPP / "build" / "bin")
        env["LD_LIBRARY_PATH"] = f"{lib_path}:{env.get('LD_LIBRARY_PATH', '')}"

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            print(f"  Error: {result.stderr}")
            return
        print(f"  Created: {final_path}")

        # Clean up F16 if we quantized
        if f16_path.exists() and final_path.exists():
            f16_path.unlink()
            print(f"  Removed intermediate: {f16_path}")
    else:
        final_path = f16_path

    # Update state
    state = load_state()
    state["gguf_path"] = str(final_path)
    state["gguf_quant"] = quant_type
    state["converted_at"] = datetime.now().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

    # Get file size
    size_gb = final_path.stat().st_size / (1024**3)

    print(f"\n{'=' * 60}")
    print("CONVERSION COMPLETE")
    print("=" * 60)
    print(f"GGUF file: {final_path}")
    print(f"Size: {size_gb:.2f} GB")
    print(f"\nNext steps:")
    print(f"  ollama create jade:v1.0 -f Modelfile")
    print("=" * 60)


if __name__ == "__main__":
    main()
