#!/usr/bin/env python3
"""
JADE Training Data Pipeline

Combines all training data sources, deduplicates, and formats for fine-tuning.

Sources:
- fix-attempts.jsonl (from jsa-infrasec)
- checkov-training.jsonl (from scanner generator)
- semgrep-training.jsonl (from scanner generator)
- kube-bench-training.jsonl (from scanner generator)
- trivy-training.jsonl (from scanner generator)
- k8s-failures-training.jsonl (from playbook generator)

Output:
- jade-training-v2-train.jsonl (80%)
- jade-training-v2-val.jsonl (10%)
- jade-training-v2-test.jsonl (10%)

Usage:
    python prepare_training_data.py --collect
    python prepare_training_data.py --stats
    python prepare_training_data.py --export --format alpaca
    python prepare_training_data.py --full-pipeline
"""

import argparse
import hashlib
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default paths
SCRIPT_DIR = Path(__file__).parent
DEFAULT_DATA_DIR = SCRIPT_DIR.parent / "training-data"
RESULTS_DIR = Path(__file__).parent.parent.parent / "3-results"


@dataclass
class DataSource:
    """A training data source file."""
    name: str
    path: Path
    format: str  # "fix_attempt", "alpaca", "raw"
    filter_successful: bool = False


class TrainingDataPipeline:
    """Pipeline to combine, filter, dedupe, and format training data."""

    # Known data sources
    SOURCES = [
        DataSource("fix_attempts", Path("fix-attempts.jsonl"), "fix_attempt", filter_successful=True),
        DataSource("all_scanners", Path("all-training.jsonl"), "alpaca"),
        DataSource("checkov", Path("checkov-training.jsonl"), "alpaca"),
        DataSource("semgrep", Path("semgrep-training.jsonl"), "alpaca"),
        DataSource("trivy", Path("trivy-training.jsonl"), "alpaca"),
        DataSource("kube_bench", Path("kube-bench-training.jsonl"), "alpaca"),
        DataSource("k8s_failures", Path("k8s-failures-training.jsonl"), "alpaca"),
    ]

    def __init__(
        self,
        data_dir: Path = None,
        output_dir: Path = None,
        seed: int = 42
    ):
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self.output_dir = output_dir or RESULTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.seed = seed
        random.seed(seed)

    def collect_sources(self) -> Dict[str, List[Dict]]:
        """Collect data from all available sources."""
        collected = {}

        for source in self.SOURCES:
            source_path = self.data_dir / source.path

            if not source_path.exists():
                logger.debug(f"Source not found: {source_path}")
                continue

            logger.info(f"Collecting from {source.name}: {source_path}")
            entries = self._read_jsonl(source_path)

            # Filter if needed
            if source.filter_successful and source.format == "fix_attempt":
                entries = [e for e in entries if e.get("result", {}).get("status") == "FIXED"]
                logger.info(f"  Filtered to {len(entries)} successful fixes")

            # Convert to alpaca format
            if source.format == "fix_attempt":
                entries = [self._fix_attempt_to_alpaca(e) for e in entries]

            collected[source.name] = entries
            logger.info(f"  Collected {len(entries)} entries")

        return collected

    def _read_jsonl(self, path: Path) -> List[Dict]:
        """Read JSONL file."""
        entries = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries

    def _fix_attempt_to_alpaca(self, entry: Dict) -> Dict:
        """Convert fix-attempt log to Alpaca format."""
        finding = entry.get("finding", {})
        action = entry.get("action", {})
        result = entry.get("result", {})

        scanner = finding.get("scanner", "unknown")
        rule_id = finding.get("rule_id", "unknown")
        title = finding.get("title", "Unknown issue")
        severity = finding.get("severity", "MEDIUM")

        rank = action.get("rank", "D")
        fix_detail = action.get("detail", "")
        status = result.get("status", "FIXED")

        instruction = (
            f"A {scanner} scan found rule {rule_id} violated: \"{title}\" "
            f"(severity: {severity}). How should this be fixed?"
        )

        output_parts = [
            f"This is a {rank}-rank finding that can be auto-fixed.",
            f"Status: {status}"
        ]
        if fix_detail:
            output_parts.append(f"\nFix applied:\n```\n{fix_detail}\n```")

        return {
            "instruction": instruction,
            "input": finding.get("description", ""),
            "output": "\n".join(output_parts)
        }

    def dedupe(self, entries: List[Dict]) -> Tuple[List[Dict], int]:
        """Remove duplicate entries by content hash."""
        seen_hashes = set()
        unique = []
        duplicates = 0

        for entry in entries:
            # Hash key fields
            key = json.dumps({
                "instruction": entry.get("instruction", "")[:200],
                "output": entry.get("output", "")[:200]
            }, sort_keys=True)
            content_hash = hashlib.sha256(key.encode()).hexdigest()

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique.append(entry)
            else:
                duplicates += 1

        return unique, duplicates

    def validate_entry(self, entry: Dict) -> bool:
        """Validate a training entry has required fields."""
        # Must have instruction and output
        if not entry.get("instruction"):
            return False
        if not entry.get("output"):
            return False

        # Instruction should be a question or task
        instruction = entry["instruction"].strip()
        if len(instruction) < 10:
            return False

        # Output should be substantial
        output = entry["output"].strip()
        if len(output) < 20:
            return False

        return True

    def split_data(
        self,
        entries: List[Dict],
        train_ratio: float = 0.8,
        val_ratio: float = 0.1
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Split data into train/val/test sets."""
        # Shuffle
        shuffled = entries.copy()
        random.shuffle(shuffled)

        n = len(shuffled)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        train = shuffled[:train_end]
        val = shuffled[train_end:val_end]
        test = shuffled[val_end:]

        return train, val, test

    def format_for_output(
        self,
        entries: List[Dict],
        format: str = "alpaca"
    ) -> List[Dict]:
        """Format entries for specific training format."""
        formatted = []

        for entry in entries:
            if format == "alpaca":
                # Alpaca format: instruction, input, output
                formatted.append({
                    "instruction": entry.get("instruction", ""),
                    "input": entry.get("input", ""),
                    "output": entry.get("output", "")
                })

            elif format == "sharegpt":
                # ShareGPT conversation format
                formatted.append({
                    "conversations": [
                        {"from": "human", "value": entry.get("instruction", "")},
                        {"from": "gpt", "value": entry.get("output", "")}
                    ]
                })

            elif format == "messages":
                # OpenAI messages format
                messages = [
                    {"role": "user", "content": entry.get("instruction", "")}
                ]
                if entry.get("input"):
                    messages[0]["content"] += f"\n\n{entry['input']}"
                messages.append({"role": "assistant", "content": entry.get("output", "")})
                formatted.append({"messages": messages})

            else:
                # Raw format
                formatted.append(entry)

        return formatted

    def run_full_pipeline(
        self,
        output_prefix: str = "jade-training-v2",
        format: str = "alpaca",
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Run the full pipeline: collect, filter, dedupe, split, save."""
        results = {
            "sources_collected": 0,
            "total_entries": 0,
            "duplicates_removed": 0,
            "invalid_entries": 0,
            "train_size": 0,
            "val_size": 0,
            "test_size": 0,
            "output_files": []
        }

        # Step 1: Collect from all sources
        logger.info("Step 1: Collecting from all sources...")
        collected = self.collect_sources()
        results["sources_collected"] = len(collected)

        # Combine all entries
        all_entries = []
        for source_name, entries in collected.items():
            all_entries.extend(entries)
        results["total_entries"] = len(all_entries)
        logger.info(f"  Total entries collected: {len(all_entries)}")

        if not all_entries:
            logger.warning("No training data found!")
            return results

        # Step 2: Deduplicate
        logger.info("Step 2: Deduplicating...")
        unique_entries, duplicates = self.dedupe(all_entries)
        results["duplicates_removed"] = duplicates
        logger.info(f"  Removed {duplicates} duplicates, {len(unique_entries)} remaining")

        # Step 3: Validate
        logger.info("Step 3: Validating entries...")
        valid_entries = [e for e in unique_entries if self.validate_entry(e)]
        results["invalid_entries"] = len(unique_entries) - len(valid_entries)
        logger.info(f"  Removed {results['invalid_entries']} invalid entries, {len(valid_entries)} remaining")

        # Step 4: Format
        logger.info(f"Step 4: Formatting for {format}...")
        formatted = self.format_for_output(valid_entries, format=format)

        # Step 5: Split
        logger.info("Step 5: Splitting into train/val/test...")
        train, val, test = self.split_data(formatted)
        results["train_size"] = len(train)
        results["val_size"] = len(val)
        results["test_size"] = len(test)
        logger.info(f"  Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")

        if dry_run:
            logger.info("Dry run - not writing files")
            return results

        # Step 6: Save
        logger.info("Step 6: Saving output files...")
        timestamp = datetime.now().strftime("%Y%m%d")

        splits = [
            (train, "train"),
            (val, "val"),
            (test, "test")
        ]

        for data, split_name in splits:
            output_file = self.output_dir / f"{output_prefix}-{split_name}.jsonl"
            with open(output_file, "w") as f:
                for entry in data:
                    f.write(json.dumps(entry) + "\n")
            results["output_files"].append(str(output_file))
            logger.info(f"  Saved: {output_file}")

        # Also save combined file
        combined_file = self.output_dir / f"{output_prefix}-combined.jsonl"
        with open(combined_file, "w") as f:
            for entry in formatted:
                f.write(json.dumps(entry) + "\n")
        results["output_files"].append(str(combined_file))
        logger.info(f"  Saved combined: {combined_file}")

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about available training data."""
        stats = {
            "available_sources": [],
            "missing_sources": [],
            "total_entries": 0,
            "by_source": {}
        }

        for source in self.SOURCES:
            source_path = self.data_dir / source.path

            if source_path.exists():
                entries = self._read_jsonl(source_path)
                stats["available_sources"].append(source.name)
                stats["by_source"][source.name] = len(entries)
                stats["total_entries"] += len(entries)
            else:
                stats["missing_sources"].append(source.name)
                stats["by_source"][source.name] = 0

        return stats


def main():
    parser = argparse.ArgumentParser(
        description="JADE Training Data Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python prepare_training_data.py --collect
    python prepare_training_data.py --stats
    python prepare_training_data.py --export --format alpaca
    python prepare_training_data.py --full-pipeline
    python prepare_training_data.py --full-pipeline --dry-run
        """
    )

    parser.add_argument(
        "--collect",
        action="store_true",
        help="Collect data from all sources (preview mode)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics about available training data"
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export combined data (use with --format)"
    )
    parser.add_argument(
        "--full-pipeline",
        action="store_true",
        help="Run full pipeline: collect, dedupe, split, save"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["alpaca", "sharegpt", "messages", "raw"],
        default="alpaca",
        help="Output format (default: alpaca)"
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="jade-training-v2",
        help="Output file prefix (default: jade-training-v2)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(DEFAULT_DATA_DIR),
        help=f"Training data directory (default: {DEFAULT_DATA_DIR})"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(RESULTS_DIR),
        help=f"Output directory (default: {RESULTS_DIR})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing files"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    pipeline = TrainingDataPipeline(
        data_dir=Path(args.data_dir),
        output_dir=Path(args.output_dir),
        seed=args.seed
    )

    if args.stats:
        stats = pipeline.get_stats()
        print("\n=== Training Data Statistics ===\n")
        print(f"Total entries: {stats['total_entries']}")
        print(f"\nAvailable sources: {len(stats['available_sources'])}")
        for source in stats["available_sources"]:
            print(f"  - {source}: {stats['by_source'][source]} entries")
        if stats["missing_sources"]:
            print(f"\nMissing sources:")
            for source in stats["missing_sources"]:
                print(f"  - {source}")

    elif args.collect:
        collected = pipeline.collect_sources()
        print("\n=== Collected Training Data ===\n")
        total = 0
        for source, entries in collected.items():
            print(f"{source}: {len(entries)} entries")
            total += len(entries)
        print(f"\nTotal: {total} entries")

    elif args.export or args.full_pipeline:
        results = pipeline.run_full_pipeline(
            output_prefix=args.output_prefix,
            format=args.format,
            dry_run=args.dry_run
        )
        print("\n=== Pipeline Results ===\n")
        print(f"Sources collected: {results['sources_collected']}")
        print(f"Total entries: {results['total_entries']}")
        print(f"Duplicates removed: {results['duplicates_removed']}")
        print(f"Invalid entries removed: {results['invalid_entries']}")
        print(f"\nSplit sizes:")
        print(f"  Train: {results['train_size']}")
        print(f"  Val: {results['val_size']}")
        print(f"  Test: {results['test_size']}")
        if results["output_files"]:
            print(f"\nOutput files:")
            for f in results["output_files"]:
                print(f"  - {f}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
