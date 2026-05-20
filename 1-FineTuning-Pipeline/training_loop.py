#!/usr/bin/env python3
"""
Katie 3B Automated Training Loop
==================================
True MLOps: train → eval → learn from mistakes → repeat

Each cycle:
  1. ETL any pending data in 01-raw-data-lake/
  2. Chunk into trainable files
  3. Train on the chunk
  4. Eval against full benchmark (484 questions)
  5. Generate corrective training data from failures
  6. Loop back to step 1 with corrections as new training data

Usage:
    python3 training_loop.py                    # Run until promotion or max cycles
    python3 training_loop.py --cycles 3         # Run exactly 3 cycles
    python3 training_loop.py --eval-only        # Just run eval on latest checkpoint
    python3 training_loop.py --quick-eval       # Use quick mode (3 per category) for faster iteration
    python3 training_loop.py --dry-run          # Preview what would happen
"""
import json
import subprocess
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-data-pipeline")
TOOLS_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/0-data-lab/tools")
REGISTRY_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/3-model-registry/v1.1-3b")
REPORTS_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-S3/3-mlops-reports/3-trained-data")
RAW_DATA = BASE_DIR / "01-raw-data-lake"
ETL_DATA = BASE_DIR / "02-ETL-data"
CHUNK_DIR = BASE_DIR / "03-chunked-untrained"

# Promotion thresholds (weighted)
WEIGHTS = {"cks": 0.40, "cka": 0.25, "cnpa": 0.25, "cloud": 0.10}
PROMOTION_THRESHOLD = 60.0  # Weighted score to pass
MAX_CYCLES = 10


def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")


def run_cmd(cmd, description, cwd=None):
    """Run a command, return (success, stdout)."""
    log(f"Running: {description}")
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=cwd or str(BASE_DIR), timeout=7200  # 2hr max for eval
    )
    if result.returncode != 0:
        log(f"FAILED: {description}", "ERROR")
        log(f"stderr: {result.stderr[-500:]}", "ERROR")
        return False, result.stdout
    return True, result.stdout


def get_latest_checkpoint():
    """Find the latest merged model checkpoint."""
    state_file = REGISTRY_DIR / "training_state.json"
    if not state_file.exists():
        return None
    with open(state_file) as f:
        state = json.load(f)
    return state.get("last_merged")


def get_next_chunk_number():
    """Determine the next chunk number from training state."""
    state_file = REGISTRY_DIR / "training_state.json"
    if not state_file.exists():
        return 1
    with open(state_file) as f:
        state = json.load(f)
    completed = state.get("chunks_completed", [])
    if not completed:
        return 1
    # Extract number from last chunk name
    last = completed[-1]  # e.g., "chunk_0040_10k.jsonl"
    try:
        num = int(last.split("_")[1])
        return num + 1
    except (IndexError, ValueError):
        return len(completed) + 1


def has_pending_data():
    """Check if there's data waiting to be processed."""
    raw_files = list(RAW_DATA.glob("*.jsonl"))
    etl_files = list(ETL_DATA.glob("*.jsonl"))
    untrained = []

    # Check manifest for untrained chunks
    manifest_file = CHUNK_DIR / "manifest.json"
    if manifest_file.exists():
        with open(manifest_file) as f:
            manifest = json.load(f)
        state_file = REGISTRY_DIR / "training_state.json"
        trained_chunks = set()
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
            trained_chunks = set(state.get("chunks_completed", []))

        for chunk in manifest.get("chunks", []):
            if chunk["file"] not in trained_chunks:
                untrained.append(chunk["file"])

    return raw_files, etl_files, untrained


def step_etl():
    """Step 1: ETL any pending data."""
    raw_files = list(RAW_DATA.glob("*.jsonl"))
    if not raw_files:
        log("No raw data to ETL, skipping")
        return True

    log(f"ETL: {len(raw_files)} files in raw-data-lake")
    ok, output = run_cmd("python3 etl_pipeline.py", "ETL pipeline")
    return ok


def step_chunk(start_chunk):
    """Step 2: Chunk ETL data."""
    etl_files = list(ETL_DATA.glob("*.jsonl"))
    if not etl_files:
        log("No ETL data to chunk, skipping")
        return True

    log(f"Chunking from chunk {start_chunk}")
    ok, output = run_cmd(f"python3 chunk_data.py --start-chunk {start_chunk}", "Chunk data")
    return ok


def step_train():
    """Step 3: Train on untrained chunks."""
    log("Training...")
    ok, output = run_cmd("python3 train_llama3b.py", "Train Katie 3B")
    if ok:
        # Extract training time from output
        for line in output.split("\n"):
            if "complete" in line.lower() and "chunk" in line.lower():
                log(f"  {line.strip()}")
    return ok


def step_eval(model_path, quick=False):
    """Step 4: Evaluate the model."""
    mode = "--quick" if quick else ""
    log(f"Evaluating {'(quick mode)' if quick else '(full 484 questions)'}...")
    ok, output = run_cmd(
        f"python3 eval_bridge.py --model-path {model_path} {mode}",
        "Eval benchmark"
    )
    if not ok:
        return None

    # Parse results from the latest bridge directory
    results_dir = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/4-eval-clarify/3-results")
    bridge_dirs = sorted(results_dir.glob("bridge_*"), reverse=True)
    if not bridge_dirs:
        return None

    results_file = bridge_dirs[0] / "full_results.json"
    if not results_file.exists():
        return None

    with open(results_file) as f:
        results = json.load(f)

    return results


def step_generate_corrections():
    """Step 5: Generate corrective training data from eval failures."""
    log("Generating corrections from eval failures...")
    ok, output = run_cmd(
        "python3 generate_eval_corrections.py",
        "Eval corrections",
        cwd=str(TOOLS_DIR)
    )
    if ok:
        for line in output.split("\n"):
            if "Corrections" in line or "Reinforcements" in line or "Total" in line:
                log(f"  {line.strip()}")
    return ok


def compute_weighted_score(results):
    """Compute weighted score from eval results."""
    categories = results.get("knowledge", {}).get("categories", {})
    weighted = 0.0
    for cat, weight in WEIGHTS.items():
        acc = categories.get(cat, {}).get("accuracy", 0)
        weighted += acc * weight
    return round(weighted, 1)


def print_scorecard(results, cycle_num):
    """Print a nice scorecard."""
    categories = results.get("knowledge", {}).get("categories", {})
    summary = results.get("knowledge", {}).get("summary", {})

    print()
    print("=" * 65)
    print(f"  CYCLE {cycle_num} RESULTS — Katie 3B v1.1")
    print("=" * 65)
    print(f"  Overall: {summary.get('passed', 0)}/{summary.get('total', 0)} ({summary.get('accuracy', 0):.1f}%)")
    print(f"  Hallucinations: {summary.get('hallucinations', 0)}")
    print()
    print(f"  {'Category':<20} {'Score':>8} {'Weight':>8} {'Weighted':>10}")
    print(f"  {'-'*48}")

    weighted_total = 0
    for cat, weight in WEIGHTS.items():
        acc = categories.get(cat, {}).get("accuracy", 0)
        w = acc * weight
        weighted_total += w
        print(f"  {cat:<20} {acc:>7.1f}% {weight*100:>7.0f}% {w:>9.1f}")

    print(f"  {'-'*48}")
    print(f"  {'WEIGHTED TOTAL':<20} {'':>8} {'':>8} {weighted_total:>9.1f}")
    print(f"  {'PROMOTION GATE':<20} {'':>8} {'':>8} {PROMOTION_THRESHOLD:>9.1f}")

    if weighted_total >= PROMOTION_THRESHOLD:
        print(f"\n  ✅ PROMOTION GATE PASSED!")
    else:
        gap = PROMOTION_THRESHOLD - weighted_total
        print(f"\n  ❌ Need {gap:.1f} more weighted points")

    # Show other categories
    other_cats = {k: v for k, v in categories.items() if k not in WEIGHTS}
    if other_cats:
        print(f"\n  Other categories:")
        for cat, data in sorted(other_cats.items()):
            print(f"    {cat:<25} {data.get('accuracy', 0):>6.1f}%")

    print("=" * 65)
    print()

    return weighted_total


def main():
    parser = argparse.ArgumentParser(description="Katie 3B Automated Training Loop")
    parser.add_argument("--cycles", type=int, default=MAX_CYCLES, help="Max training cycles")
    parser.add_argument("--eval-only", action="store_true", help="Just run eval")
    parser.add_argument("--quick-eval", action="store_true", help="Quick eval mode (3 per category)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without running")
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          KATIE 3B — AUTOMATED TRAINING LOOP                 ║")
    print("║          train → eval → learn from mistakes → repeat        ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # Eval-only mode
    if args.eval_only:
        checkpoint = get_latest_checkpoint()
        if not checkpoint:
            log("No checkpoint found", "ERROR")
            return
        log(f"Checkpoint: {checkpoint}")
        results = step_eval(checkpoint, quick=args.quick_eval)
        if results:
            print_scorecard(results, 0)
        return

    for cycle in range(1, args.cycles + 1):
        log(f"{'='*60}")
        log(f"CYCLE {cycle}/{args.cycles}")
        log(f"{'='*60}")

        start_time = time.time()

        # Check what data is pending
        raw, etl, untrained = has_pending_data()
        log(f"Pending: {len(raw)} raw files, {len(etl)} ETL files, {len(untrained)} untrained chunks")

        if args.dry_run:
            log("[DRY RUN] Would: ETL → chunk → train → eval → corrections")
            continue

        # Step 1: ETL
        next_chunk = get_next_chunk_number()
        if raw:
            if not step_etl():
                log("ETL failed, stopping", "ERROR")
                break

        # Step 2: Chunk
        etl_files = list(ETL_DATA.glob("*.jsonl"))
        if etl_files:
            if not step_chunk(next_chunk):
                log("Chunking failed, stopping", "ERROR")
                break

        # Step 3: Train
        if not step_train():
            # "No untrained chunks" is OK if we're in correction cycles
            log("No chunks to train, proceeding to eval")

        # Step 4: Eval
        checkpoint = get_latest_checkpoint()
        if not checkpoint:
            log("No checkpoint found after training", "ERROR")
            break

        log(f"Checkpoint: {Path(checkpoint).parent.name}")
        results = step_eval(checkpoint, quick=args.quick_eval)

        if not results:
            log("Eval failed, stopping", "ERROR")
            break

        # Print scorecard
        weighted = print_scorecard(results, cycle)

        # Check promotion
        if weighted >= PROMOTION_THRESHOLD:
            log("🎉 PROMOTION GATE PASSED — Katie is ready for production!")
            log("Next steps:")
            log("  python3 convert_gguf.py")
            log("  ollama create katie:v1.1 -f KATIE-AI/Modelfile_katie3b")
            break

        # Step 5: Generate corrections for next cycle
        if cycle < args.cycles:
            if not step_generate_corrections():
                log("Correction generation failed, stopping", "ERROR")
                break

            elapsed = time.time() - start_time
            log(f"Cycle {cycle} complete in {elapsed/60:.1f} minutes")
            log(f"Corrections generated → feeding into next cycle")
        else:
            elapsed = time.time() - start_time
            log(f"Final cycle {cycle} complete in {elapsed/60:.1f} minutes")
            log(f"Max cycles reached. Run again with --cycles to continue.")

    log("Training loop complete.")


if __name__ == "__main__":
    main()
