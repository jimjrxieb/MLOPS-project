#!/usr/bin/env python3
"""
Combine all gap training data into a final file for ETL processing.
"""

import json
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-GP-GLUE/00-processed/benchmark-training")

def main():
    print("=" * 60)
    print("Combining Gap Training Data")
    print("=" * 60)

    all_examples = []
    sources = {}

    # Collect all today's gap training files
    gap_files = [
        ("gap_training_20260122_214847.jsonl", "Initial gap examples"),
        ("comprehensive_gap_training_20260122_215056.jsonl", "Comprehensive classification/IR/cloud/compliance"),
        ("converted_tests_20260122_223923.jsonl", "Converted test scenarios"),
    ]

    for filename, description in gap_files:
        filepath = OUTPUT_DIR / filename
        if filepath.exists():
            with open(filepath) as f:
                examples = [json.loads(line) for line in f if line.strip()]
                all_examples.extend(examples)
                sources[filename] = len(examples)
                print(f"✓ Loaded {len(examples)} from {filename}")

    # Also include the earlier scanner/k8s training data
    earlier_files = [
        ("jade_eval_training_20260122_204841.jsonl", "Scanner rules + K8s playbooks"),
    ]

    for filename, description in earlier_files:
        filepath = OUTPUT_DIR / filename
        if filepath.exists():
            with open(filepath) as f:
                examples = [json.loads(line) for line in f if line.strip()]
                all_examples.extend(examples)
                sources[filename] = len(examples)
                print(f"✓ Loaded {len(examples)} from {filename}")

    # Deduplicate by instruction+input hash
    seen = set()
    unique_examples = []
    for ex in all_examples:
        key = (ex.get('instruction', ''), ex.get('input', ''))
        if key not in seen:
            seen.add(key)
            unique_examples.append(ex)

    duplicates_removed = len(all_examples) - len(unique_examples)

    # Save combined file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"jade_gap_training_FINAL_{timestamp}.jsonl"

    with open(output_file, 'w') as f:
        for ex in unique_examples:
            f.write(json.dumps(ex) + '\n')

    # Create detailed summary
    summary = {
        "timestamp": timestamp,
        "total_examples": len(unique_examples),
        "duplicates_removed": duplicates_removed,
        "sources": sources,
        "output_file": str(output_file),
        "baseline_benchmark": {
            "model": "jade:v1.0",
            "date": "2026-01-22",
            "overall": "24.1%",
            "knowledge": "32.3%",
            "tasks": "0.0%",
            "gaps_identified": {
                "classification": "0%",
                "incident_response": "10%",
                "cloud": "20%",
                "compliance": "20%",
                "devsecops": "30%",
            }
        },
        "training_focus": [
            "Classification/Ranking (E-D-C-B-S system)",
            "Agent Routing (jsa-devsec, jsa-infrasec, jsa-monitor)",
            "Incident Response playbooks",
            "Cloud Security (AWS IAM, networking, data protection)",
            "Compliance frameworks (CIS, SOC2, PCI-DSS, NIST)",
            "Fix Generation (Trivy, Checkov, Semgrep)",
            "Log Diagnosis (30 scenarios)",
            "Agent Scenarios (10 multi-step tasks)",
        ],
        "etl_ready": True,
        "next_steps": [
            "1. Run ETL pipeline to format for LoRA training",
            "2. Fine-tune JADE with this data",
            "3. Re-run benchmarks to measure improvement",
            "4. Target: 60%+ overall accuracy"
        ]
    }

    summary_file = output_file.with_suffix('.json')
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"FINAL COMBINED TRAINING DATA")
    print(f"{'=' * 60}")
    print(f"\n✓ Total Examples: {len(unique_examples)}")
    print(f"✓ Duplicates Removed: {duplicates_removed}")
    print(f"✓ Output File: {output_file}")
    print(f"✓ Summary: {summary_file}")

    print(f"\nSource Breakdown:")
    for src, count in sources.items():
        print(f"  • {src}: {count}")

    print(f"\nReady for ETL pipeline!")


if __name__ == "__main__":
    main()
