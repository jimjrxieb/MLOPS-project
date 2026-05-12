#!/usr/bin/env python3
"""
RAG to Training Data Migration Script
Migrates processed RAG data from GP-OPENSEARCH to GP-MODEL-OPS for JADE training.

Usage:
    python3 migrate_rag_to_training.py --dry-run    # Preview what will be moved
    python3 migrate_rag_to_training.py              # Execute migration
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

# Paths
OPENSEARCH_ROOT = Path("/home/jimmie/linkops-industries/GP-copilot/GP-OPENSEARCH")
SAGEMAKER_ROOT = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS")
RAG_DATA_DIR = OPENSEARCH_ROOT / "05-ragged-data"
RAW_DATA_LAKE = SAGEMAKER_ROOT / "1-GP-GLUE" / "01-raw-data-lake"

# Categories for organization
CATEGORIES = {
    "operational": ["jsa-logs", "operational-training", "claude-as-jsa", "cycles", "escalations"],
    "claudecode-sessions": ["claudecode", "sessions", "refactor", "architecture"],
    "guides": ["guide", "troubleshooting", "configuration", "debugging"],
    "knowledge": ["k8sgpt", "scdao", "infrastructure", "remediation"],
    "policy": ["gatekeeper", "kyverno", "opa", "rego", "pss", "policy"],
    "cis-benchmarks": ["cis", "benchmark"],
    "compliance": ["soc2", "pci", "hipaa", "nist", "compliance"],
}


def categorize_file(file_path: Path) -> str:
    """Categorize file based on path and name."""
    path_str = str(file_path).lower()

    # Check categories
    for category, keywords in CATEGORIES.items():
        if any(keyword in path_str for keyword in keywords):
            return category

    # Default category
    if file_path.suffix == ".jsonl":
        return "operational"
    elif file_path.suffix == ".md":
        return "guides"
    else:
        return "other"


def count_training_examples(jsonl_file: Path) -> int:
    """Count number of training examples in JSONL file."""
    count = 0
    try:
        with open(jsonl_file, 'r') as f:
            for line in f:
                if line.strip():
                    count += 1
    except Exception:
        pass
    return count


def scan_rag_data() -> Dict[str, List[Tuple[Path, int]]]:
    """Scan 05-ragged-data for training-ready files."""
    files_by_category = defaultdict(list)

    print("🔍 Scanning GP-OPENSEARCH/05-ragged-data...")

    # Find all JSONL and MD files (excluding ChromaDB)
    for ext in [".jsonl", ".md"]:
        for file_path in RAG_DATA_DIR.rglob(f"*{ext}"):
            # Skip ChromaDB directory
            if "chroma/" in str(file_path):
                continue

            category = categorize_file(file_path)

            # Count examples if JSONL
            example_count = count_training_examples(file_path) if ext == ".jsonl" else 0

            files_by_category[category].append((file_path, example_count))

    return dict(files_by_category)


def create_migration_plan(files_by_category: Dict[str, List[Tuple[Path, int]]]) -> Dict:
    """Create detailed migration plan."""
    plan = {
        "timestamp": datetime.now().isoformat(),
        "source": str(RAG_DATA_DIR),
        "destination": str(RAW_DATA_LAKE),
        "categories": {},
        "totals": {
            "files": 0,
            "jsonl_files": 0,
            "md_files": 0,
            "training_examples": 0,
        }
    }

    for category, files in files_by_category.items():
        jsonl_files = [f for f in files if f[0].suffix == ".jsonl"]
        md_files = [f for f in files if f[0].suffix == ".md"]
        total_examples = sum(count for _, count in jsonl_files)

        plan["categories"][category] = {
            "files": len(files),
            "jsonl_files": len(jsonl_files),
            "md_files": len(md_files),
            "training_examples": total_examples,
            "file_list": [str(f.relative_to(RAG_DATA_DIR)) for f, _ in files]
        }

        plan["totals"]["files"] += len(files)
        plan["totals"]["jsonl_files"] += len(jsonl_files)
        plan["totals"]["md_files"] += len(md_files)
        plan["totals"]["training_examples"] += total_examples

    return plan


def execute_migration(files_by_category: Dict[str, List[Tuple[Path, int]]], dry_run: bool = False):
    """Execute the migration."""
    if not dry_run:
        RAW_DATA_LAKE.mkdir(parents=True, exist_ok=True)

    print(f"\n{'🔍 DRY RUN:' if dry_run else '🚀 EXECUTING:'} Migration to {RAW_DATA_LAKE}\n")

    migrated_files = []

    for category, files in sorted(files_by_category.items()):
        category_dir = RAW_DATA_LAKE / category

        if not dry_run:
            category_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📁 {category.upper()} ({len(files)} files)")
        print("─" * 80)

        for file_path, example_count in files:
            # Create destination path
            # Use original filename with timestamp prefix to avoid collisions
            timestamp = datetime.now().strftime("%Y%m%d")
            dest_filename = f"{timestamp}_{file_path.name}"
            dest_path = category_dir / dest_filename

            # Show what would be done
            size_kb = file_path.stat().st_size / 1024
            example_info = f"({example_count} examples)" if example_count > 0 else ""
            print(f"  {'→' if not dry_run else '•'} {file_path.name} {example_info}")
            print(f"    Source: {file_path.relative_to(OPENSEARCH_ROOT)}")
            print(f"    Dest:   {dest_path.relative_to(SAGEMAKER_ROOT)}")
            print(f"    Size:   {size_kb:.1f}KB")

            if not dry_run:
                # Copy file (don't move, keep original in RAG)
                shutil.copy2(file_path, dest_path)
                migrated_files.append({
                    "source": str(file_path),
                    "destination": str(dest_path),
                    "category": category,
                    "examples": example_count,
                    "size_bytes": file_path.stat().st_size
                })

    return migrated_files


def save_migration_manifest(plan: Dict, migrated_files: List[Dict]):
    """Save migration manifest for tracking."""
    manifest_path = RAW_DATA_LAKE / "migration_manifest.json"

    manifest = {
        "migration_date": datetime.now().isoformat(),
        "plan": plan,
        "migrated_files": migrated_files,
        "next_steps": [
            "Review files in 01-raw-data-lake/",
            "Run GP-GLUE preprocessing pipeline",
            "Chunk into 10k example batches",
            "Add to 03-chunked-untrained/chunk_0012_10k.jsonl, chunk_0013_10k.jsonl, etc."
        ]
    }

    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\n✅ Migration manifest saved: {manifest_path}")
    return manifest_path


def print_summary(plan: Dict):
    """Print migration summary."""
    print("\n" + "=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)

    print(f"\n📊 Overall Statistics:")
    print(f"  Total files:          {plan['totals']['files']}")
    print(f"  JSONL files:          {plan['totals']['jsonl_files']}")
    print(f"  Markdown files:       {plan['totals']['md_files']}")
    print(f"  Training examples:    {plan['totals']['training_examples']:,}")

    print(f"\n📁 By Category:")
    for category, stats in sorted(plan['categories'].items(), key=lambda x: -x[1]['training_examples']):
        print(f"\n  {category.upper()}:")
        print(f"    Files:     {stats['files']}")
        print(f"    JSONL:     {stats['jsonl_files']}")
        print(f"    MD:        {stats['md_files']}")
        print(f"    Examples:  {stats['training_examples']:,}")

    print("\n" + "=" * 80)


def main():
    import sys
    dry_run = "--dry-run" in sys.argv

    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   RAG → Training Data Migration                                         ║
║   GP-OPENSEARCH/05-ragged-data → GP-MODEL-OPS/1-GP-GLUE/01-raw-data-lake║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
""")

    # Scan RAG data
    files_by_category = scan_rag_data()

    if not files_by_category:
        print("❌ No files found in 05-ragged-data")
        return

    # Create migration plan
    plan = create_migration_plan(files_by_category)

    # Print summary
    print_summary(plan)

    # Execute migration
    if dry_run:
        print("\n🔍 DRY RUN MODE - No files will be moved")
        print("Run without --dry-run to execute migration\n")
        execute_migration(files_by_category, dry_run=True)
    else:
        print("\n⚠️  This will COPY files from GP-OPENSEARCH to GP-MODEL-OPS")
        print("Original files will remain in RAG for continued use")
        confirm = input("\nProceed with migration? (yes/no): ")

        if confirm.lower() == "yes":
            migrated_files = execute_migration(files_by_category, dry_run=False)
            manifest_path = save_migration_manifest(plan, migrated_files)

            print("\n" + "=" * 80)
            print("✅ MIGRATION COMPLETE")
            print("=" * 80)
            print(f"\n📍 Location: {RAW_DATA_LAKE}")
            print(f"📋 Manifest: {manifest_path}")
            print(f"📊 Files migrated: {len(migrated_files)}")
            print(f"📝 Training examples: {plan['totals']['training_examples']:,}")

            print("\n🔄 Next Steps:")
            print("  1. Review migrated files in 01-raw-data-lake/")
            print("  2. Run preprocessing: python3 02-preperation-factory/preprocess_pipeline.py")
            print("  3. Chunk data: python3 1-GP-GLUE/chunk_data.py")
            print("  4. Add chunks to 03-chunked-untrained/chunk_0012_10k.jsonl, etc.")
            print("  5. Train JADE v0.9 with new data")
        else:
            print("\n❌ Migration cancelled")


if __name__ == "__main__":
    main()
