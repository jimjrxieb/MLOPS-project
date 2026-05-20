#!/usr/bin/env python3
"""
JADE v1.0 ETL Pipeline
======================
Extract, Transform, Load data from MULTIPLE sources to 02-ETL-data

BEHAVIOR:
- Processes ALL .jsonl files from BOTH:
  - 04-processed/ (benchmark training data, gap data)
  - 01-raw-data-lake/ (raw session data, scraped content)
- Deduplicates examples via MD5 hash
- Labels examples based on subdirectory (policy, compliance, benchmark-training, etc.)
- Moves ALL processed files to 02-ETL-data/
- After ETL: training data consolidated in 02-ETL-data/

Supported inputs:
- .jsonl files (ChatML, Alpaca, or Q&A format)
- .json files (array of objects)
- .md files (markdown documentation)
- .txt files (plain text)
- .pdf files (requires pypdf)

Output format (ChatML/messages style):
{
    "messages": [
        {"role": "system", "content": "You are JADE..."},
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": "answer"}
    ],
    "metadata": {
        "source": "filename",
        "category": "policy|compliance|benchmark|...",
        "type": "policy_generation|troubleshooting|...",
        "domain": "kubernetes|aws|opa|..."
    }
}

Usage:
    python3 etl_pipeline.py                # Process all, move files after
    python3 etl_pipeline.py --dry-run      # Preview without changes
    python3 etl_pipeline.py --keep         # Don't move source files
    python3 etl_pipeline.py --delete       # Delete source files after ETL
"""

import json
import re
import argparse
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set

# Directories
BASE_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-data-pipeline")
ETL_DIR = BASE_DIR / "02-ETL-data"

# Source directories to process (in order)
SOURCE_DIRS = [
    BASE_DIR / "04-processed",      # Benchmark training data, gap training
    BASE_DIR / "01-raw-data-lake",  # Raw session data, scraped content
]

# System prompt for JADE
JADE_SYSTEM = """You are JADE (Junior Automated DevSecOps Engineer), a security-focused AI assistant specializing in Kubernetes, cloud security, policy-as-code (OPA/Rego, Kyverno, Gatekeeper), and DevSecOps practices. Output working code directly. Be concise and accurate."""

# Category inference from subdirectory names
CATEGORY_MAP = {
    "policy": "policy",
    "benchmark-training": "benchmark",
    "compliance": "compliance",
    "cis-benchmarks": "compliance",
    "iac-examples": "iac",
    "devsecops-examples": "devsecops",
    "consultant-examples": "consultant",
    "operational": "operational",
    "claudecode-sessions": "session",
    "guides": "documentation",
    "knowledge": "documentation",
    "etl-data": "etl",
    "formatted": "formatted",
}

# Domain inference from content keywords
DOMAIN_KEYWORDS = {
    "kubernetes": ["kubernetes", "k8s", "pod", "deployment", "namespace", "kubectl", "helm"],
    "opa": ["rego", "opa", "gatekeeper", "conftest", "constraint", "deny[", "violation["],
    "aws": ["aws", "s3", "ec2", "iam", "lambda", "cloudformation", "terraform"],
    "azure": ["azure", "aks", "blob", "arm template"],
    "gcp": ["gcp", "gke", "bigquery", "cloud run"],
    "cicd": ["github actions", "gitlab", "jenkins", "pipeline", "workflow"],
    "docker": ["docker", "dockerfile", "container", "image"],
    "network": ["networkpolicy", "ingress", "egress", "firewall", "vpc"],
    "rbac": ["rbac", "clusterrole", "rolebinding", "serviceaccount"],
    "secrets": ["secret", "vault", "credential", "api key", "token"],
}


def compute_hash(messages: List[Dict]) -> str:
    """Compute MD5 hash for deduplication"""
    return hashlib.md5(json.dumps(messages, sort_keys=True).encode()).hexdigest()


def infer_category(filepath: Path, source_dir: Path) -> str:
    """Infer category from file path"""
    try:
        rel_path = filepath.relative_to(source_dir)
        parts = rel_path.parts
    except ValueError:
        parts = filepath.parts

    for part in parts:
        part_lower = part.lower()
        for key, category in CATEGORY_MAP.items():
            if key in part_lower:
                return category

    return "general"


def infer_domain(content: str) -> str:
    """Infer domain from content keywords"""
    content_lower = content.lower()

    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in content_lower)
        if score > 0:
            scores[domain] = score

    if scores:
        return max(scores, key=scores.get)
    return "general"


def extract_jsonl(filepath: Path, category: str) -> List[Dict]:
    """Extract from JSONL training data with smart format detection"""
    examples = []

    with open(filepath, encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)

                # Already in ChatML messages format - preserve it
                if "messages" in obj:
                    # Strip generator lineage metadata (used for tracking, not training)
                    obj.pop("_metadata", None)

                    # Ensure metadata exists
                    if "metadata" not in obj:
                        obj["metadata"] = {}
                    obj["metadata"]["source"] = filepath.name
                    obj["metadata"]["category"] = category

                    # Infer domain from assistant content
                    for msg in obj["messages"]:
                        if msg.get("role") == "assistant":
                            obj["metadata"]["domain"] = infer_domain(msg.get("content", ""))
                            break

                    examples.append(obj)

                # Alpaca format (instruction/input/output)
                elif "instruction" in obj:
                    user_content = obj["instruction"]
                    if obj.get("input"):
                        user_content += f"\n\n{obj['input']}"

                    assistant_content = obj.get("output", "")

                    example = {
                        "messages": [
                            {"role": "system", "content": JADE_SYSTEM},
                            {"role": "user", "content": user_content},
                            {"role": "assistant", "content": assistant_content}
                        ],
                        "metadata": {
                            "source": filepath.name,
                            "category": category,
                            "domain": infer_domain(assistant_content),
                            "type": obj.get("type", "unknown")
                        }
                    }
                    examples.append(example)

                # Q&A format
                elif "question" in obj and "answer" in obj:
                    example = {
                        "messages": [
                            {"role": "system", "content": JADE_SYSTEM},
                            {"role": "user", "content": obj["question"]},
                            {"role": "assistant", "content": obj["answer"]}
                        ],
                        "metadata": {
                            "source": filepath.name,
                            "category": category,
                            "domain": infer_domain(obj["answer"])
                        }
                    }
                    examples.append(example)

                # Benchmark response format
                elif "jade_response" in obj:
                    question = obj.get("question", "")
                    response = obj.get("jade_response", "")
                    is_correct = obj.get("correct", False)

                    if question and response:
                        example = {
                            "messages": [
                                {"role": "system", "content": JADE_SYSTEM},
                                {"role": "user", "content": question},
                                {"role": "assistant", "content": response}
                            ],
                            "metadata": {
                                "source": filepath.name,
                                "category": "benchmark",
                                "domain": infer_domain(response),
                                "correct": is_correct,
                                "needs_review": not is_correct
                            }
                        }
                        examples.append(example)

            except json.JSONDecodeError:
                continue

    return examples


def extract_markdown(filepath: Path, category: str) -> List[Dict]:
    """Extract Q&A pairs from markdown documentation"""
    examples = []
    content = filepath.read_text(encoding='utf-8', errors='ignore')

    # Split by headers
    sections = re.split(r'\n##?\s+', content)

    for section in sections:
        if not section.strip():
            continue

        lines = section.strip().split('\n')
        if not lines:
            continue

        title = lines[0].strip()
        body = '\n'.join(lines[1:]).strip()

        if len(body) > 100:
            example = {
                "messages": [
                    {"role": "system", "content": JADE_SYSTEM},
                    {"role": "user", "content": f"Explain: {title}"},
                    {"role": "assistant", "content": body[:4000]}
                ],
                "metadata": {
                    "source": filepath.name,
                    "category": category,
                    "type": "documentation",
                    "domain": infer_domain(body)
                }
            }
            examples.append(example)

    return examples


def extract_text(filepath: Path, category: str) -> List[Dict]:
    """Extract from plain text files"""
    content = filepath.read_text(encoding='utf-8', errors='ignore')

    if len(content) > 100:
        return [{
            "messages": [
                {"role": "system", "content": JADE_SYSTEM},
                {"role": "user", "content": f"Summarize this content from {filepath.name}"},
                {"role": "assistant", "content": content[:4000]}
            ],
            "metadata": {
                "source": filepath.name,
                "category": category,
                "type": "documentation",
                "domain": infer_domain(content)
            }
        }]
    return []


def extract_pdf(filepath: Path, category: str) -> List[Dict]:
    """Extract from PDF files"""
    try:
        from pypdf import PdfReader
    except ImportError:
        print(f"  [SKIP] PDF {filepath.name} - install pypdf")
        return []

    examples = []
    try:
        reader = PdfReader(filepath)

        for i, page in enumerate(reader.pages[:20]):
            text = page.extract_text()
            if text and len(text) > 200:
                example = {
                    "messages": [
                        {"role": "system", "content": JADE_SYSTEM},
                        {"role": "user", "content": f"What does page {i+1} of {filepath.name} cover?"},
                        {"role": "assistant", "content": text[:3000]}
                    ],
                    "metadata": {
                        "source": filepath.name,
                        "category": category,
                        "type": "documentation",
                        "page": i + 1,
                        "domain": infer_domain(text)
                    }
                }
                examples.append(example)
    except Exception as e:
        print(f"  [ERROR] PDF {filepath.name}: {e}")

    return examples


def process_file(filepath: Path, source_dir: Path) -> List[Dict]:
    """Process a single file based on extension"""
    suffix = filepath.suffix.lower()
    category = infer_category(filepath, source_dir)

    if suffix == ".jsonl":
        return extract_jsonl(filepath, category)
    elif suffix == ".json":
        try:
            content = json.loads(filepath.read_text())
            if isinstance(content, list):
                # Convert to JSONL-like processing
                examples = []
                for obj in content:
                    if isinstance(obj, dict):
                        if "messages" in obj:
                            obj["metadata"] = obj.get("metadata", {})
                            obj["metadata"]["source"] = filepath.name
                            obj["metadata"]["category"] = category
                            examples.append(obj)
                return examples
        except json.JSONDecodeError:
            pass
        return []
    elif suffix == ".md":
        return extract_markdown(filepath, category)
    elif suffix == ".txt":
        return extract_text(filepath, category)
    elif suffix == ".pdf":
        return extract_pdf(filepath, category)
    else:
        return []


def validate_example(ex: Dict) -> bool:
    """Validate an example has required structure"""
    if "messages" not in ex:
        return False

    messages = ex["messages"]
    if not isinstance(messages, list) or len(messages) < 2:
        return False

    # Must have at least user and assistant
    roles = [m.get("role") for m in messages]
    if "user" not in roles or "assistant" not in roles:
        return False

    # Assistant content must not be empty
    for m in messages:
        if m.get("role") == "assistant":
            if not m.get("content", "").strip():
                return False

    return True


def main():
    parser = argparse.ArgumentParser(description="JADE v1.0 ETL Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing or moving")
    parser.add_argument("--keep", action="store_true", help="Don't move source files after ETL")
    parser.add_argument("--delete", action="store_true", help="Delete source files after ETL")
    parser.add_argument("--file", type=str, help="Process specific file only")
    args = parser.parse_args()

    print("=" * 60)
    print("JADE v1.0 ETL Pipeline")
    print("=" * 60)
    print("Source directories:")
    for src_dir in SOURCE_DIRS:
        exists = "✓" if src_dir.exists() else "✗"
        print(f"  {exists} {src_dir}")
    print(f"Output: {ETL_DIR}")
    if not args.keep:
        print(f"Mode: {'DELETE' if args.delete else 'MOVE'} source files after ETL")
    print("=" * 60 + "\n")

    # Find files to process from ALL source directories
    files_with_source = []  # List of (filepath, source_dir) tuples

    for source_dir in SOURCE_DIRS:
        if not source_dir.exists():
            print(f"[SKIP] {source_dir} does not exist")
            continue

        if args.file:
            files_with_source.append((source_dir / args.file, source_dir))
        else:
            for ext in ["*.jsonl", "*.json", "*.md", "*.txt", "*.pdf"]:
                for f in source_dir.rglob(ext):
                    # Skip hidden files
                    if not f.name.startswith("."):
                        files_with_source.append((f, source_dir))

    # Sort by filepath
    files_with_source = sorted(files_with_source, key=lambda x: str(x[0]))

    print(f"Found {len(files_with_source)} files to process\n")

    # Process files
    all_examples = []
    seen_hashes: Set[str] = set()
    file_stats = {}
    duplicates = 0
    invalid = 0

    for filepath, source_dir in files_with_source:
        try:
            rel_path = filepath.relative_to(source_dir)
            display_path = f"{source_dir.name}/{rel_path}"
        except ValueError:
            display_path = str(filepath)

        print(f"Processing: {display_path}")

        raw_examples = process_file(filepath, source_dir)
        valid_count = 0

        for ex in raw_examples:
            # Validate
            if not validate_example(ex):
                invalid += 1
                continue

            # Deduplicate
            h = compute_hash(ex["messages"])
            if h in seen_hashes:
                duplicates += 1
                continue

            seen_hashes.add(h)
            all_examples.append(ex)
            valid_count += 1

        print(f"  -> {valid_count} valid examples (from {len(raw_examples)} raw)")
        file_stats[display_path] = valid_count

    print(f"\n{'='*60}")
    print(f"Total valid examples: {len(all_examples)}")
    print(f"Duplicates removed: {duplicates}")
    print(f"Invalid removed: {invalid}")
    print(f"{'='*60}")

    if args.dry_run:
        print("\n[DRY RUN] Would write to 02-ETL-data/")
        print(f"\nTop 10 files by examples:")
        for f, count in sorted(file_stats.items(), key=lambda x: -x[1])[:10]:
            print(f"  {count:5d}  {f}")

        # Category breakdown
        categories = {}
        for ex in all_examples:
            c = ex.get("metadata", {}).get("category", "unknown")
            categories[c] = categories.get(c, 0) + 1

        print(f"\nBy category:")
        for c, count in sorted(categories.items(), key=lambda x: -x[1]):
            print(f"  {count:5d}  {c}")

        # Domain breakdown
        domains = {}
        for ex in all_examples:
            d = ex.get("metadata", {}).get("domain", "unknown")
            domains[d] = domains.get(d, 0) + 1

        print(f"\nBy domain:")
        for d, count in sorted(domains.items(), key=lambda x: -x[1]):
            print(f"  {count:5d}  {d}")

        return

    # Write output
    ETL_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = ETL_DIR / f"jade_v10_etl_{timestamp}.jsonl"

    with open(output_file, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\n[OK] Written {len(all_examples)} examples to {output_file.name}")

    # Move/delete source files
    if not args.keep and all_examples:
        if args.delete:
            print(f"\n[CLEANUP] Deleting {len(files_with_source)} source files...")
            for filepath, _ in files_with_source:
                try:
                    filepath.unlink()
                except Exception as e:
                    print(f"  [ERROR] {filepath.name}: {e}")
            print(f"[OK] Deleted source files")
        else:
            # Move source files to ETL_DIR/sources/ for record keeping
            sources_archive = ETL_DIR / "sources" / timestamp
            print(f"\n[ARCHIVE] Moving {len(files_with_source)} source files to {sources_archive}...")
            sources_archive.mkdir(parents=True, exist_ok=True)

            for filepath, source_dir in files_with_source:
                try:
                    # Preserve directory structure under sources/
                    rel_path = filepath.relative_to(source_dir)
                    dest = sources_archive / source_dir.name / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(filepath), str(dest))
                except Exception as e:
                    print(f"  [ERROR] {filepath.name}: {e}")

            print(f"[OK] Archived source files to {sources_archive}")

            # Clean up empty directories in source dirs
            for source_dir in SOURCE_DIRS:
                if source_dir.exists():
                    for dirpath in sorted(source_dir.rglob("*"), reverse=True):
                        if dirpath.is_dir():
                            try:
                                dirpath.rmdir()  # Only removes if empty
                            except OSError:
                                pass  # Not empty, skip

    # Final summary
    print(f"\n{'='*60}")
    print("ETL COMPLETE")
    print(f"{'='*60}")

    # Check remaining files in source dirs
    for source_dir in SOURCE_DIRS:
        if source_dir.exists():
            remaining = list(source_dir.rglob("*.jsonl"))
            if remaining:
                print(f"\n[WARN] {len(remaining)} .jsonl files still in {source_dir.name}/")
            else:
                print(f"\n[OK] {source_dir.name}/ is clean (no .jsonl files)")


if __name__ == "__main__":
    main()
