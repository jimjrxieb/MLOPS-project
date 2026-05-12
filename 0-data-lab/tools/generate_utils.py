"""
generate_utils.py — Shared utilities for training data generators.

Solves two gaps:
1. DATA LINEAGE — every example gets _metadata with source, timestamp, domain
2. DATA VERSIONING — every generation run writes a manifest (hashes, counts, config)

Usage in generators:
    from generate_utils import write_training_data

    # Replace this:
    #   with open(OUTPUT_FILE, "w") as f:
    #       for ex in all_examples:
    #           f.write(json.dumps(ex) + "\\n")

    # With this:
    write_training_data(
        examples=all_examples,
        output_file=OUTPUT_FILE,
        generator="generate_cka_admin_ops.py",
        domain="CKA",
    )

The _metadata field is stripped by etl_pipeline.py before training.
The manifest is git-tracked for reproducibility.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# Manifest directory — one manifest per generation run
MANIFEST_DIR = Path(__file__).resolve().parent.parent.parent / "0-data-lab" / "manifests"


def add_lineage(
    example: Dict[str, Any],
    generator: str,
    domain: str,
    version: str = "1.0",
) -> Dict[str, Any]:
    """
    Add _metadata to a training example for lineage tracking.

    The _metadata field is NOT part of training data — it's stripped
    by etl_pipeline.py during normalization. It exists only for tracking
    which generator produced which example and when.

    Args:
        example: ChatML dict with "messages" key
        generator: Script name (e.g., "generate_cka_admin_ops.py")
        domain: Training domain (CKS, CKA, CKAD, CNPA, OPS, Cloud, etc.)
        version: Generator version (bump when you change the generator logic)

    Returns:
        Same example with _metadata added
    """
    example["_metadata"] = {
        "generator": generator,
        "domain": domain,
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return example


def write_training_data(
    examples: List[Dict[str, Any]],
    output_file: Path,
    generator: str,
    domain: str,
    version: str = "1.0",
    add_metadata: bool = True,
) -> Dict[str, Any]:
    """
    Write training examples to JSONL with lineage metadata and a generation manifest.

    Args:
        examples: List of ChatML dicts
        output_file: Path to output JSONL file
        generator: Script name for lineage
        domain: Training domain for lineage
        version: Generator version
        add_metadata: Whether to add _metadata to each example (default True)

    Returns:
        Manifest dict (also written to disk)
    """
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Add lineage metadata to each example
    if add_metadata:
        for ex in examples:
            add_lineage(ex, generator=generator, domain=domain, version=version)

    # Write JSONL
    with open(output_file, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    # Compute file hash for versioning
    file_hash = _sha256(output_file)

    # Domain distribution in this batch
    domain_counts = {}
    if add_metadata:
        for ex in examples:
            d = ex.get("_metadata", {}).get("domain", "unknown")
            domain_counts[d] = domain_counts.get(d, 0) + 1

    # Build manifest
    manifest = {
        "generator": generator,
        "domain": domain,
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_file": str(output_file),
        "output_file_name": output_file.name,
        "examples_count": len(examples),
        "file_sha256": file_hash,
        "file_size_bytes": output_file.stat().st_size,
        "domain_distribution": domain_counts,
    }

    # Write manifest
    _write_manifest(manifest, generator)

    # Print summary
    print(f"\nGenerated {len(examples)} {domain} examples")
    print(f"Output: {output_file}")
    print(f"SHA256: {file_hash[:16]}...")
    print(f"Manifest: {MANIFEST_DIR / _manifest_filename(generator)}")

    return manifest


def _sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _manifest_filename(generator: str) -> str:
    """Generate manifest filename from generator name."""
    base = generator.replace(".py", "").replace("/", "_")
    return f"{base}.manifest.json"


def _write_manifest(manifest: Dict[str, Any], generator: str):
    """Write generation manifest to manifests/ directory."""
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest_file = MANIFEST_DIR / _manifest_filename(generator)

    # Append to history (keep last 10 runs)
    history = []
    if manifest_file.exists():
        try:
            with open(manifest_file) as f:
                existing = json.load(f)
            if isinstance(existing, list):
                history = existing[-9:]  # Keep last 9, add current = 10
            else:
                history = [existing]  # Migrate old single-manifest format
        except (json.JSONDecodeError, KeyError):
            history = []

    history.append(manifest)

    with open(manifest_file, "w") as f:
        json.dump(history, f, indent=2)


def get_latest_manifest(generator: str) -> Optional[Dict[str, Any]]:
    """Get the most recent manifest for a generator."""
    manifest_file = MANIFEST_DIR / _manifest_filename(generator)
    if not manifest_file.exists():
        return None
    try:
        with open(manifest_file) as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            return data[-1]
        return data
    except (json.JSONDecodeError, KeyError):
        return None


def print_all_manifests():
    """Print summary of all generation manifests — useful for auditing."""
    if not MANIFEST_DIR.exists():
        print("No manifests found. Run generators with write_training_data() first.")
        return

    print(f"{'Generator':<40} {'Examples':>8} {'Domain':<10} {'Last Run':<20} {'SHA256':<16}")
    print("-" * 100)

    for mf in sorted(MANIFEST_DIR.glob("*.manifest.json")):
        try:
            with open(mf) as f:
                data = json.load(f)
            latest = data[-1] if isinstance(data, list) else data
            print(
                f"{latest['generator']:<40} "
                f"{latest['examples_count']:>8} "
                f"{latest['domain']:<10} "
                f"{latest['generated_at'][:19]:<20} "
                f"{latest['file_sha256'][:16]}"
            )
        except Exception as e:
            print(f"{mf.name:<40} ERROR: {e}")


if __name__ == "__main__":
    print_all_manifests()
