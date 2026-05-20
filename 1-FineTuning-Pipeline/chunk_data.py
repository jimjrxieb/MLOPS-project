#!/usr/bin/env python3
"""
JADE v1.0 Chunking Script - Step 2
===================================
Chunk ETL data from 02-ETL-data into 10k example files in 03-chunked-untrained

BEHAVIOR:
- Reads all .jsonl from 02-ETL-data/
- Validates and shuffles examples
- Reserves a holdout eval set (5% default) in 03-eval-holdout/
- Chunks remaining into 10k files in 03-chunked-untrained/
- Moves processed files to 03-chunked-untrained/sources/
- After chunking: zero .jsonl files remain in 02-ETL-data/

Output format:
- chunk_0019_10k.jsonl (continues from specified start)
- chunk_0020_10k.jsonl
- etc.

Usage:
    python3 chunk_data.py                          # Chunk all, auto-detect start
    python3 chunk_data.py --start-chunk 19         # Start from chunk 19
    python3 chunk_data.py --dry-run                # Preview without changes
    python3 chunk_data.py --keep                   # Don't move source files
    python3 chunk_data.py --chunk-size 5000        # Custom chunk size
    python3 chunk_data.py --shuffle                # Shuffle before chunking
    python3 chunk_data.py --holdout-pct 10         # 10% holdout eval set
    python3 chunk_data.py --force-holdout          # Recreate holdout even if exists
"""

import json
import hashlib
import random
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set

# Directories
BASE_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-data-pipeline")
ETL_DIR = BASE_DIR / "02-ETL-data"
CHUNK_DIR = BASE_DIR / "03-chunked-untrained"
HOLDOUT_DIR = BASE_DIR / "03-eval-holdout"
ARCHIVE_DIR = CHUNK_DIR / "sources"  # Move processed files here after chunking

# Default chunk size
DEFAULT_CHUNK_SIZE = 10000

# Holdout defaults
DEFAULT_HOLDOUT_PCT = 5
HOLDOUT_SEED = 42


def load_enhanced_data(files: List[Path]) -> List[Dict]:
    """Load all enhanced examples from files"""
    all_examples = []

    for filepath in files:
        with open(filepath) as f:
            for line in f:
                if line.strip():
                    try:
                        obj = json.loads(line)
                        # Validate structure
                        if "messages" in obj and len(obj["messages"]) >= 2:
                            all_examples.append(obj)
                    except json.JSONDecodeError:
                        pass

    return all_examples


def validate_example(example: Dict) -> bool:
    """Validate example has required structure"""
    messages = example.get("messages", [])

    if len(messages) < 2:
        return False

    # Check for user and assistant messages
    has_user = any(m.get("role") == "user" for m in messages)
    has_assistant = any(m.get("role") == "assistant" for m in messages)

    if not (has_user and has_assistant):
        return False

    # Check assistant has actual content
    for m in messages:
        if m.get("role") == "assistant":
            content = m.get("content", "")
            if len(content) < 20:  # Too short
                return False
            if "[NEEDS CORRECTION" in content:  # Not corrected
                return False

    return True


def chunk_examples(examples: List[Dict], chunk_size: int) -> List[List[Dict]]:
    """Split examples into chunks"""
    chunks = []

    for i in range(0, len(examples), chunk_size):
        chunk = examples[i:i + chunk_size]
        chunks.append(chunk)

    return chunks


def get_next_chunk_number() -> int:
    """Auto-detect the next chunk number from existing chunks."""
    existing = list(CHUNK_DIR.glob("chunk_*_10k.jsonl"))
    if not existing:
        return 1

    # Extract chunk numbers from filenames
    nums = []
    for f in existing:
        try:
            # chunk_0019_10k.jsonl -> 19
            num = int(f.stem.split("_")[1])
            nums.append(num)
        except (IndexError, ValueError):
            pass

    return max(nums) + 1 if nums else 1


def compute_example_hash(example: Dict) -> str:
    """Compute MD5 hash of an example's messages for dedup/identification"""
    return hashlib.md5(json.dumps(example.get("messages", []), sort_keys=True).encode()).hexdigest()


def load_holdout_hashes() -> Set[str]:
    """Load hashes of existing holdout examples to exclude from training"""
    holdout_file = HOLDOUT_DIR / "eval_set.jsonl"
    if not holdout_file.exists():
        return set()

    hashes = set()
    with open(holdout_file) as f:
        for line in f:
            if line.strip():
                try:
                    obj = json.loads(line)
                    hashes.add(compute_example_hash(obj))
                except json.JSONDecodeError:
                    pass
    return hashes


def create_holdout(examples: List[Dict], pct: int, seed: int,
                   source_files: List[str], force: bool = False) -> List[Dict]:
    """Split examples into holdout eval set and training set.

    Returns the training examples (holdout is written to disk).
    If holdout already exists and force=False, filters out holdout examples
    from the input and returns the rest.
    """
    holdout_file = HOLDOUT_DIR / "eval_set.jsonl"
    manifest_file = HOLDOUT_DIR / "manifest.json"

    if holdout_file.exists() and not force:
        # Holdout exists — filter it out of current examples
        print(f"\n[HOLDOUT] Existing eval set found ({holdout_file})")
        holdout_hashes = load_holdout_hashes()
        print(f"  Loaded {len(holdout_hashes)} holdout hashes")

        train_examples = []
        excluded = 0
        for ex in examples:
            if compute_example_hash(ex) in holdout_hashes:
                excluded += 1
            else:
                train_examples.append(ex)

        print(f"  Excluded {excluded} holdout examples from training data")
        print(f"  Training examples: {len(train_examples)}")
        return train_examples

    # Create new holdout
    print(f"\n[HOLDOUT] Creating eval holdout set ({pct}%, seed={seed})...")
    rng = random.Random(seed)
    shuffled = examples.copy()
    rng.shuffle(shuffled)

    split_idx = max(1, int(len(shuffled) * (pct / 100)))
    holdout_examples = shuffled[:split_idx]
    train_examples = shuffled[split_idx:]

    print(f"  Holdout: {len(holdout_examples)} examples ({pct}%)")
    print(f"  Training: {len(train_examples)} examples ({100 - pct}%)")

    # Write holdout
    HOLDOUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(holdout_file, "w") as f:
        for ex in holdout_examples:
            f.write(json.dumps(ex) + "\n")

    # Write manifest
    manifest = {
        "created": datetime.now().isoformat(),
        "holdout_pct": pct,
        "seed": seed,
        "num_examples": len(holdout_examples),
        "total_before_split": len(examples),
        "source_files": source_files,
    }
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"  Written to: {holdout_file}")
    print(f"  Manifest: {manifest_file}")

    return train_examples


def main():
    parser = argparse.ArgumentParser(description="JADE v1.0 Chunking Script")
    parser.add_argument("--file", type=str, help="Process specific file only")
    parser.add_argument("--start-chunk", type=int, default=None,
                        help="Starting chunk number (default: auto-detect from existing)")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE,
                        help=f"Examples per chunk (default: {DEFAULT_CHUNK_SIZE})")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle examples before chunking")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--keep", action="store_true", help="Don't move source files after chunking")
    parser.add_argument("--holdout-pct", type=int, default=DEFAULT_HOLDOUT_PCT,
                        help=f"Percent of data to hold out for eval (default: {DEFAULT_HOLDOUT_PCT})")
    parser.add_argument("--holdout-seed", type=int, default=HOLDOUT_SEED,
                        help=f"Random seed for holdout split (default: {HOLDOUT_SEED})")
    parser.add_argument("--force-holdout", action="store_true",
                        help="Recreate holdout set even if one already exists")
    parser.add_argument("--no-holdout", action="store_true",
                        help="Skip holdout split (backwards compat)")
    args = parser.parse_args()

    # Determine starting chunk number
    if args.start_chunk is not None:
        start_chunk = args.start_chunk
    else:
        start_chunk = get_next_chunk_number()

    print("=" * 60)
    print("JADE v1.0 Chunking Script")
    print("=" * 60)
    print(f"Source: {ETL_DIR}")
    print(f"Output: {CHUNK_DIR}")
    if not args.keep:
        print(f"Archive: {ARCHIVE_DIR}")
    print(f"Chunk size: {args.chunk_size}")
    print(f"Starting chunk: {start_chunk:04d}")
    print("=" * 60 + "\n")

    # Find files to process
    if args.file:
        files = [ETL_DIR / args.file]
    else:
        # Find all JSONL files, prioritize by name pattern
        all_files = list(ETL_DIR.glob("*.jsonl"))
        # Filter out checkpoint files
        all_files = [f for f in all_files if not f.name.startswith(".")]
        # Sort: jade_v09 first, then enhanced, then others
        files = sorted(all_files, key=lambda f: (
            0 if "jade_v09" in f.name else
            1 if "enhanced" in f.name else
            2 if "augmented" in f.name else 3
        ))

    if not files:
        print(f"No data files found in {ETL_DIR}")
        print("Run etl_pipeline.py and enhance_examples.py first")
        return

    print(f"Files to process: {len(files)}")
    for f in files:
        print(f"  - {f.name}")

    # Load all examples
    print("\nLoading examples...")
    all_examples = load_enhanced_data(files)
    print(f"  Loaded: {len(all_examples)}")

    # Validate
    print("\nValidating...")
    valid_examples = [ex for ex in all_examples if validate_example(ex)]
    invalid = len(all_examples) - len(valid_examples)
    print(f"  Valid: {len(valid_examples)}")
    print(f"  Invalid (skipped): {invalid}")

    if not valid_examples:
        print("\nNo valid examples to chunk")
        return

    # === HOLDOUT SPLIT ===
    if not args.no_holdout:
        source_names = [f.name for f in files]
        train_examples = create_holdout(
            valid_examples,
            pct=args.holdout_pct,
            seed=args.holdout_seed,
            source_files=source_names,
            force=args.force_holdout,
        )
    else:
        print("\n[HOLDOUT] Skipped (--no-holdout)")
        train_examples = valid_examples

    # Shuffle if requested
    if args.shuffle:
        print("\nShuffling...")
        random.shuffle(train_examples)

    # Chunk
    print(f"\nChunking into {args.chunk_size}-example files...")
    chunks = chunk_examples(train_examples, args.chunk_size)
    print(f"  Created {len(chunks)} chunks")

    if args.dry_run:
        print("\n[DRY RUN] Would create:")
        for i, chunk in enumerate(chunks):
            chunk_num = start_chunk + i
            print(f"  chunk_{chunk_num:04d}_10k.jsonl ({len(chunk)} examples)")
        if not args.no_holdout:
            holdout_count = len(valid_examples) - len(train_examples)
            print(f"\n[DRY RUN] Holdout: {holdout_count} examples in 03-eval-holdout/")
        print(f"[DRY RUN] Would move {len(files)} files to {ARCHIVE_DIR}")
        return

    # Write chunks
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    print("\nWriting chunks...")
    chunk_files_created = []
    for i, chunk in enumerate(chunks):
        chunk_num = start_chunk + i
        chunk_file = CHUNK_DIR / f"chunk_{chunk_num:04d}_10k.jsonl"

        with open(chunk_file, "w") as f:
            for ex in chunk:
                f.write(json.dumps(ex) + "\n")

        chunk_files_created.append({
            "file": chunk_file.name,
            "examples": len(chunk),
            "trained": False
        })
        print(f"  ✅ {chunk_file.name} ({len(chunk)} examples)")

    # Load existing manifest or create new
    manifest_file = CHUNK_DIR / "manifest.json"
    if manifest_file.exists():
        with open(manifest_file) as f:
            manifest = json.load(f)
        # Append new chunks
        manifest["chunks"].extend(chunk_files_created)
        manifest["total_examples"] += len(train_examples)
        manifest["num_chunks"] = len(manifest["chunks"])
        manifest.setdefault("source_files", []).extend([f.name for f in files])
        manifest["last_updated"] = datetime.now().isoformat()
        print(f"\n[MANIFEST] Appended {len(chunk_files_created)} chunks to existing manifest")
    else:
        manifest = {
            "created": datetime.now().isoformat(),
            "total_examples": len(train_examples),
            "chunk_size": args.chunk_size,
            "num_chunks": len(chunks),
            "chunks": chunk_files_created,
            "source_files": [f.name for f in files]
        }
        print(f"\n[MANIFEST] Created new manifest with {len(chunk_files_created)} chunks")

    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)

    # Move ALL source files from 02-ETL-data to archive
    if not args.keep:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_subdir = ARCHIVE_DIR / timestamp
        archive_subdir.mkdir(parents=True, exist_ok=True)

        # Move processed JSONL files
        print(f"\n[ARCHIVE] Moving source files to {archive_subdir}...")
        for filepath in files:
            try:
                dest = archive_subdir / filepath.name
                shutil.move(str(filepath), str(dest))
                print(f"  ✅ Moved {filepath.name}")
            except Exception as e:
                print(f"  ❌ {filepath.name}: {e}")

        # Also move any subdirectories (like sources/)
        for item in ETL_DIR.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                try:
                    dest = archive_subdir / item.name
                    shutil.move(str(item), str(dest))
                    print(f"  ✅ Moved directory {item.name}/")
                except Exception as e:
                    print(f"  ❌ {item.name}/: {e}")

        print(f"[OK] All files moved to {archive_subdir}")

    # Check remaining files
    remaining = list(ETL_DIR.glob("*.jsonl"))
    remaining = [f for f in remaining if not f.name.startswith(".")]
    remaining_dirs = [d for d in ETL_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print("=" * 60)
    print(f"Total valid examples: {len(valid_examples)}")
    if not args.no_holdout:
        holdout_count = len(valid_examples) - len(train_examples)
        print(f"Holdout eval set: {holdout_count} ({args.holdout_pct}%)")
    print(f"Training examples chunked: {len(train_examples)}")
    print(f"New chunks created: {len(chunks)}")
    print(f"Chunk range: {start_chunk:04d} - {start_chunk + len(chunks) - 1:04d}")
    print(f"Output: {CHUNK_DIR}")

    if remaining or remaining_dirs:
        print(f"\n[WARN] {len(remaining)} files, {len(remaining_dirs)} dirs still in 02-ETL-data/")
    else:
        print(f"\n[OK] 02-ETL-data/ is clean (all files moved)")

    # Show next training suggestion
    next_chunk = start_chunk
    print(f"\nTo start training:")
    print(f"  python3 train_v10.py --chunk {next_chunk}")
    print("=" * 60)


if __name__ == "__main__":
    main()
