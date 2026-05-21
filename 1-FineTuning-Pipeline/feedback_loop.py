#!/usr/bin/env python3
"""
JADE Feedback Loop - GP-CLARIFY Results -> GP-GLUE Training Data
================================================================
Reads evaluation results, identifies weak categories, and exports
failed cases as new training examples for the next ETL cycle.

This closes the loop:
  Train -> Eval -> Find Gaps -> Generate Data -> Train

Usage:
    python3 feedback_loop.py --results-dir /path/to/bridge_YYYYMMDD/   # Analyze specific run
    python3 feedback_loop.py --latest                                    # Use most recent bridge run
    python3 feedback_loop.py --threshold 80                              # Categories below 80%
    python3 feedback_loop.py --export                                    # Write to 01-raw-data-lake
    python3 feedback_loop.py --dry-run                                   # Preview without writing
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Directories
from pipeline_config import pipeline_dir, gp_model_ops
GLUE_DIR = pipeline_dir
CLARIFY_DIR = gp_model_ops / "4-eval-clarify"
RESULTS_DIR = CLARIFY_DIR / "3-results"
RAW_LAKE_DIR = GLUE_DIR / "01-raw-data-lake" / "eval-gaps"

# Default threshold for identifying weak categories
DEFAULT_THRESHOLD = 80


def load_results(results_dir: Path) -> Optional[Dict]:
    """Load full_results.json from a bridge result directory."""
    results_file = results_dir / "full_results.json"
    if not results_file.exists():
        print(f"ERROR: {results_file} not found")
        return None

    with open(results_file) as f:
        return json.load(f)


def find_latest_bridge_results() -> Optional[Path]:
    """Find the most recent bridge_* result directory."""
    if not RESULTS_DIR.exists():
        return None

    bridge_dirs = sorted(RESULTS_DIR.glob("bridge_*"), reverse=True)
    for d in bridge_dirs:
        if (d / "full_results.json").exists():
            return d

    return None


def identify_gaps(results: Dict, threshold: float) -> List[Dict]:
    """Find categories scoring below the threshold.

    Returns list of gap dicts with category, accuracy, and delta from threshold.
    """
    gaps = []
    categories = results.get("knowledge", {}).get("categories", {})

    for cat, data in categories.items():
        accuracy = data.get("accuracy", 0)
        if accuracy < threshold:
            gaps.append({
                "category": cat,
                "accuracy": accuracy,
                "passed": data.get("passed", 0),
                "total": data.get("total", 0),
                "delta_from_threshold": round(threshold - accuracy, 1),
            })

    # Sort by worst-performing first
    gaps.sort(key=lambda g: g["accuracy"])
    return gaps


def extract_failed_cases(results: Dict) -> List[Dict]:
    """Extract all failed test cases with question, response, and scoring details."""
    failed = []
    detailed = results.get("detailed_results", [])

    for r in detailed:
        if not r.get("passed", True):
            failed.append({
                "id": r.get("id", "unknown"),
                "category": r.get("category", "unknown"),
                "subcategory": r.get("subcategory"),
                "rank": r.get("rank"),
                "question": r.get("question_text", ""),
                "model_response": r.get("response", ""),
                "keywords_found": r.get("keywords_found", []),
                "keywords_missing": r.get("keywords_missing", []),
                "fix_found": r.get("fix_found", False),
                "hallucination": r.get("hallucination", False),
            })

    return failed


def format_as_training_data(failed_cases: List[Dict]) -> List[Dict]:
    """Convert failed cases into ChatML training examples.

    Uses the question as the user message and constructs an ideal
    assistant response from the expected keywords/fix.
    """
    training_examples = []

    for case in failed_cases:
        # Build an ideal response hint from missing keywords
        missing = case.get("keywords_missing", [])
        question = case.get("question", "")

        if not question:
            continue

        # Create a training example with metadata for the ETL pipeline
        # The actual "correct" answer needs to be written by a human or
        # pulled from reference material. We export the structure so
        # the ETL can process it.
        example = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are JADE, a DevSecOps security expert. Output working code directly."
                },
                {
                    "role": "user",
                    "content": question
                },
                {
                    "role": "assistant",
                    "content": f"[NEEDS CORRECTION] Model failed on this question. Missing keywords: {', '.join(missing)}"
                }
            ],
            "metadata": {
                "source": "eval-gap",
                "original_id": case.get("id"),
                "category": case.get("category"),
                "subcategory": case.get("subcategory"),
                "rank": case.get("rank"),
                "keywords_missing": missing,
                "fix_needed": not case.get("fix_found", True),
                "hallucination": case.get("hallucination", False),
                "model_response": case.get("model_response", "")[:500],
            }
        }
        training_examples.append(example)

    return training_examples


def export_to_raw_lake(training_data: List[Dict], failed_cases: List[Dict],
                       gaps: List[Dict], dry_run: bool = False) -> Optional[Path]:
    """Write training data and gap report to 01-raw-data-lake/eval-gaps/.

    Returns the output directory path.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if dry_run:
        print(f"\n[DRY RUN] Would write to: {RAW_LAKE_DIR}/")
        print(f"  gap_{timestamp}.jsonl ({len(training_data)} examples)")
        print(f"  gap_report_{timestamp}.md")
        return None

    RAW_LAKE_DIR.mkdir(parents=True, exist_ok=True)

    # Write training examples
    data_file = RAW_LAKE_DIR / f"gap_{timestamp}.jsonl"
    with open(data_file, "w") as f:
        for ex in training_data:
            f.write(json.dumps(ex) + "\n")
    print(f"  Wrote {len(training_data)} examples to {data_file}")

    # Write gap report
    report_file = RAW_LAKE_DIR / f"gap_report_{timestamp}.md"
    report = generate_gap_report(gaps, failed_cases, training_data)
    with open(report_file, "w") as f:
        f.write(report)
    print(f"  Wrote gap report to {report_file}")

    return RAW_LAKE_DIR


def generate_gap_report(gaps: List[Dict], failed_cases: List[Dict],
                        training_data: List[Dict]) -> str:
    """Generate a markdown gap analysis report."""
    lines = [
        "# JADE Evaluation Gap Report",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Failed Cases**: {len(failed_cases)}",
        f"**Training Examples Exported**: {len(training_data)}",
        "",
    ]

    if gaps:
        lines.extend([
            "## Weak Categories",
            "",
            "| Category | Accuracy | Passed | Total | Gap |",
            "|----------|----------|--------|-------|-----|",
        ])
        for g in gaps:
            lines.append(
                f"| {g['category']} | {g['accuracy']:.1f}% | {g['passed']} | {g['total']} | -{g['delta_from_threshold']:.1f}% |"
            )
        lines.append("")

    # Failed cases by category
    by_cat = {}
    for case in failed_cases:
        cat = case.get("category", "unknown")
        by_cat.setdefault(cat, []).append(case)

    lines.extend([
        "## Failed Cases by Category",
        "",
    ])

    for cat in sorted(by_cat.keys()):
        cases = by_cat[cat]
        lines.extend([
            f"### {cat} ({len(cases)} failures)",
            "",
        ])
        for case in cases[:5]:  # Show first 5 per category
            lines.extend([
                f"- **{case['id']}** (rank: {case.get('rank', '?')})",
                f"  - Missing: {', '.join(case.get('keywords_missing', []))}",
                f"  - Hallucination: {'YES' if case.get('hallucination') else 'no'}",
                "",
            ])
        if len(cases) > 5:
            lines.append(f"  ... and {len(cases) - 5} more\n")

    lines.extend([
        "## Next Steps",
        "",
        "1. Review exported gap examples in `01-raw-data-lake/eval-gaps/`",
        "2. Replace `[NEEDS CORRECTION]` assistant responses with correct answers",
        "3. Run ETL pipeline: `python3 etl_pipeline.py`",
        "4. Chunk: `python3 chunk_data.py`",
        "5. Train: `python3 train_v10.py`",
        "6. Re-evaluate: `python3 eval_bridge.py --latest`",
        "",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="JADE Feedback Loop - Find eval gaps and generate training data")
    parser.add_argument("--results-dir", type=str,
                        help="Path to a bridge result directory (e.g., bridge_20260127_*)")
    parser.add_argument("--latest", action="store_true",
                        help="Use the most recent bridge result")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help=f"Accuracy threshold for flagging weak categories (default: {DEFAULT_THRESHOLD})")
    parser.add_argument("--export", action="store_true",
                        help="Export failed cases to 01-raw-data-lake/eval-gaps/")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing files")
    args = parser.parse_args()

    # Find results directory
    if args.results_dir:
        results_dir = Path(args.results_dir)
        if not results_dir.exists():
            # Try as a glob in RESULTS_DIR
            matches = sorted(RESULTS_DIR.glob(f"*{args.results_dir}*"))
            if matches:
                results_dir = matches[-1]
            else:
                print(f"ERROR: Results directory not found: {args.results_dir}")
                return
    elif args.latest:
        results_dir = find_latest_bridge_results()
        if not results_dir:
            print("No bridge results found")
            print("Run eval_bridge.py first: python3 eval_bridge.py --latest")
            return
    else:
        print("ERROR: Specify --results-dir or --latest")
        print("Usage: python3 feedback_loop.py --latest --export")
        return

    print("=" * 60)
    print("JADE FEEDBACK LOOP")
    print("=" * 60)
    print(f"Results: {results_dir}")
    print(f"Threshold: {args.threshold}%")
    print()

    # Load results
    results = load_results(results_dir)
    if not results:
        return

    # Show overall accuracy
    summary = results.get("knowledge", {}).get("summary", {})
    print(f"Overall: {summary.get('passed', 0)}/{summary.get('total', 0)} "
          f"({summary.get('accuracy', 0):.1f}%)")
    print()

    # Find gaps
    gaps = identify_gaps(results, args.threshold)
    if gaps:
        print(f"Found {len(gaps)} categories below {args.threshold}% threshold:")
        for g in gaps:
            print(f"  {g['category']}: {g['accuracy']:.1f}% (need +{g['delta_from_threshold']:.1f}%)")
    else:
        print(f"All categories above {args.threshold}% threshold")

    # Extract failed cases
    failed = extract_failed_cases(results)
    print(f"\nTotal failed cases: {len(failed)}")

    if not failed:
        print("No failures to process")
        return

    # Breakdown
    by_cat = {}
    for case in failed:
        cat = case.get("category", "unknown")
        by_cat.setdefault(cat, []).append(case)

    print("\nFailures by category:")
    for cat in sorted(by_cat.keys()):
        halluc = sum(1 for c in by_cat[cat] if c.get("hallucination"))
        extra = f" ({halluc} hallucinations)" if halluc else ""
        print(f"  {cat}: {len(by_cat[cat])}{extra}")

    # Export
    if args.export or args.dry_run:
        print(f"\n[EXPORT] Converting {len(failed)} failed cases to training format...")
        training_data = format_as_training_data(failed)
        print(f"  Generated {len(training_data)} training examples")

        output = export_to_raw_lake(training_data, failed, gaps, dry_run=args.dry_run)

        if output:
            print(f"\nExported to: {output}")
            print(f"\nNext steps:")
            print(f"  1. Review and correct [NEEDS CORRECTION] examples")
            print(f"  2. python3 etl_pipeline.py  (process new data)")
            print(f"  3. python3 chunk_data.py    (chunk for training)")
            print(f"  4. python3 train_v10.py     (train on new data)")
    else:
        print(f"\nRun with --export to write training data to {RAW_LAKE_DIR}")

    print("=" * 60)


if __name__ == "__main__":
    main()
