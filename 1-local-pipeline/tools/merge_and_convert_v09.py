#!/usr/bin/env python3
"""
JADE v0.9 Training Data Converter & Merger
Converts RAG content, operational logs, and documents to Alpaca training format.
Adds GuidePoint consultant-level examples.

Usage:
    python3 merge_and_convert_v09.py --dry-run
    python3 merge_and_convert_v09.py
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set
from collections import defaultdict

# Paths
SAGEMAKER_ROOT = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS")
RAW_DATA_LAKE = SAGEMAKER_ROOT / "1-GP-GLUE" / "01-raw-data-lake"
FORMATTED_DATA = SAGEMAKER_ROOT / "1-GP-GLUE" / "02-formatted-data"
CHUNKED_UNTRAINED = SAGEMAKER_ROOT / "1-GP-GLUE" / "03-chunked-untrained"

# Format converters
def convert_rag_content_to_alpaca(entry: Dict) -> Dict:
    """Convert RAG content format to Alpaca."""
    try:
        # RAG content format: {"content": "...", "metadata": {...}}
        content = entry.get("content", "")
        metadata = entry.get("metadata", {})

        # Extract topic from metadata or content
        topic = metadata.get("topic", "security analysis")

        # Create instruction from content
        if len(content) > 500:
            instruction = f"Explain {topic} in detail"
            output = content
            input_text = ""
        else:
            instruction = f"What is {topic}?"
            output = content
            input_text = ""

        return {
            "instruction": instruction,
            "input": input_text,
            "output": output,
            "metadata": metadata
        }
    except Exception as e:
        print(f"Error converting RAG content: {e}")
        return None


def convert_operational_log_to_alpaca(entry: Dict) -> List[Dict]:
    """Convert operational log to training examples."""
    try:
        # Operational log format: {"timestamp": "...", "action": "...", "finding": {...}}
        action = entry.get("action", "")
        finding = entry.get("finding", {})
        scanner = finding.get("scanner", "")

        if not action or not scanner:
            return []

        examples = []

        # Example 1: Scan result interpretation
        if action == "escalated":
            examples.append({
                "instruction": f"Analyze this {scanner} finding and determine the action",
                "input": json.dumps(finding, indent=2),
                "output": f"This finding requires escalation to a human reviewer because it is classified as {entry.get('rank', 'B')}-rank. The issue is complex and requires expert judgment for remediation.",
                "metadata": {
                    "domain": "scan-analysis",
                    "task_type": "escalation-decision",
                    "skill_level": entry.get("rank", "B") + "-rank",
                    "scanner": scanner
                }
            })

        # Example 2: Fix decision
        elif action == "fixed":
            examples.append({
                "instruction": f"How do you fix this {scanner} finding?",
                "input": json.dumps(finding, indent=2),
                "output": f"Fix applied successfully using automated remediation. The issue was addressed by modifying the configuration to comply with security best practices.",
                "metadata": {
                    "domain": "fix-execution",
                    "task_type": "automated-remediation",
                    "skill_level": "D-rank",
                    "scanner": scanner
                }
            })

        return examples
    except Exception as e:
        print(f"Error converting operational log: {e}")
        return []


def convert_chat_messages_to_alpaca(entry: Dict) -> Dict:
    """Convert chat format to Alpaca."""
    try:
        # Chat format: {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
        messages = entry.get("messages", [])

        if len(messages) < 2:
            return None

        user_msg = next((m for m in messages if m.get("role") == "user"), None)
        assistant_msg = next((m for m in messages if m.get("role") == "assistant"), None)

        if not user_msg or not assistant_msg:
            return None

        return {
            "instruction": user_msg.get("content", ""),
            "input": "",
            "output": assistant_msg.get("content", ""),
            "metadata": entry.get("metadata", {})
        }
    except Exception as e:
        print(f"Error converting chat messages: {e}")
        return None


def convert_to_alpaca(entry: Dict, format_type: str) -> List[Dict]:
    """Convert entry to Alpaca format based on type."""
    if format_type == "alpaca":
        # Already in Alpaca format
        return [entry] if "instruction" in entry else []

    elif format_type == "chat-messages":
        result = convert_chat_messages_to_alpaca(entry)
        return [result] if result else []

    elif format_type == "rag-content":
        result = convert_rag_content_to_alpaca(entry)
        return [result] if result else []

    elif format_type == "operational-log":
        return convert_operational_log_to_alpaca(entry)

    else:
        # Try to infer format
        if "messages" in entry:
            result = convert_chat_messages_to_alpaca(entry)
            return [result] if result else []
        elif "content" in entry and "metadata" in entry:
            result = convert_rag_content_to_alpaca(entry)
            return [result] if result else []
        elif "action" in entry and "finding" in entry:
            return convert_operational_log_to_alpaca(entry)
        else:
            # Already Alpaca or unknown
            return [entry] if "instruction" in entry else []


def detect_format(entry: Dict) -> str:
    """Detect entry format."""
    if "instruction" in entry and "output" in entry:
        return "alpaca"
    elif "messages" in entry:
        return "chat-messages"
    elif "content" in entry and "metadata" in entry:
        return "rag-content"
    elif "action" in entry and "finding" in entry:
        return "operational-log"
    elif "timestamp" in entry and "cycle_id" in entry:
        return "operational-log"
    else:
        return "unknown"


def compute_hash(example: Dict) -> str:
    """Compute hash of example for deduplication."""
    # Use instruction + output for hash
    key = f"{example.get('instruction', '')}{example.get('output', '')}"
    return hashlib.md5(key.encode()).hexdigest()


def process_file(file_path: Path) -> List[Dict]:
    """Process a single JSONL file."""
    examples = []

    try:
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue

                try:
                    entry = json.loads(line)
                    format_type = detect_format(entry)
                    converted = convert_to_alpaca(entry, format_type)
                    examples.extend(converted)

                except json.JSONDecodeError as e:
                    print(f"  ⚠️  JSON error at {file_path.name}:{line_num} - {e}")
                except Exception as e:
                    print(f"  ⚠️  Conversion error at {file_path.name}:{line_num} - {e}")

    except Exception as e:
        print(f"  ❌ Error reading {file_path.name}: {e}")

    return examples


def merge_and_convert(dry_run: bool = False):
    """Merge all training data and convert to Alpaca format."""
    print("="*80)
    print("JADE v0.9 Training Data Conversion & Merge")
    print("="*80)

    all_examples = []
    seen_hashes: Set[str] = set()
    stats = defaultdict(int)

    # Process each category
    categories = ["operational", "claudecode-sessions", "policy", "cis-benchmarks",
                  "compliance", "guides", "knowledge"]

    for category in categories:
        category_dir = RAW_DATA_LAKE / category

        if not category_dir.exists():
            print(f"\n⚠️  Category not found: {category}")
            continue

        print(f"\n📁 Processing {category.upper()}...")
        category_examples = []

        # Find all JSONL files
        jsonl_files = list(category_dir.glob("*.jsonl"))

        for file_path in jsonl_files:
            examples = process_file(file_path)

            # Deduplicate
            before_count = len(examples)
            unique_examples = []
            for ex in examples:
                ex_hash = compute_hash(ex)
                if ex_hash not in seen_hashes:
                    seen_hashes.add(ex_hash)
                    unique_examples.append(ex)
                    stats["total"] += 1
                    stats[category] += 1
                else:
                    stats["duplicates"] += 1

            category_examples.extend(unique_examples)

            if unique_examples:
                print(f"  ✅ {file_path.name}: {len(unique_examples)} examples "
                      f"({before_count - len(unique_examples)} duplicates)")

        all_examples.extend(category_examples)
        print(f"  📊 {category}: {len(category_examples):,} examples")

    print(f"\n{'='*80}")
    print(f"CONVERSION SUMMARY")
    print(f"{'='*80}")
    print(f"Total examples:     {stats['total']:,}")
    print(f"Duplicates removed: {stats['duplicates']:,}")
    print(f"\nBy Category:")
    for cat in categories:
        if stats[cat] > 0:
            print(f"  {cat:20s}: {stats[cat]:,}")

    if dry_run:
        print(f"\n🔍 DRY RUN - No files written")
        return

    # Save merged data
    FORMATTED_DATA.mkdir(parents=True, exist_ok=True)
    output_file = FORMATTED_DATA / f"jade_v09_training_{datetime.now().strftime('%Y%m%d')}.jsonl"

    with open(output_file, 'w') as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + '\n')

    print(f"\n✅ Saved: {output_file}")
    print(f"📊 Total examples: {len(all_examples):,}")

    return output_file, all_examples


def main():
    import sys
    dry_run = "--dry-run" in sys.argv

    output_file, examples = merge_and_convert(dry_run=dry_run)

    if not dry_run and examples:
        print(f"\n🔄 Next Steps:")
        print(f"  1. Review merged file: {output_file}")
        print(f"  2. Generate additional examples (IaC, DevSecOps, consultant)")
        print(f"  3. Run chunking: python3 chunk_training_data.py")
        print(f"  4. Train JADE v0.9")


if __name__ == "__main__":
    main()
