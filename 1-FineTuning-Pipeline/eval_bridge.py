#!/usr/bin/env python3
"""
JADE Eval Bridge - GP-GLUE <-> GP-CLARIFY
==========================================
Run GP-CLARIFY benchmarks against a local HuggingFace merged model,
without needing Ollama or an HTTP server.

Bridges the training pipeline (GP-GLUE) to the evaluation framework
(GP-CLARIFY) so that every merged checkpoint can be scored automatically.

Usage:
    python3 eval_bridge.py --model-path /path/to/merged           # Full benchmark (65 questions)
    python3 eval_bridge.py --model-path /path/to/merged --quick   # Quick subset (~21 questions)
    python3 eval_bridge.py --model-path /path/to/merged --category cloud --category cks
    python3 eval_bridge.py --compare bridge_20260127_* bridge_20260128_*
    python3 eval_bridge.py --dry-run                               # Preview test count
    python3 eval_bridge.py --latest                                # Use last merged model from training state
"""

import json
import random
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Directories
from pipeline_config import pipeline_dir, gp_model_ops
GLUE_DIR = pipeline_dir
CLARIFY_DIR = gp_model_ops / "4-eval-clarify"
EVAL_DIR = CLARIFY_DIR / "2-test-data" / "evaluation"
RESULTS_DIR = CLARIFY_DIR / "3-results"
MODEL_VERSIONS_DIR = gp_model_ops / "3-model-registry"

# Knowledge categories -> subdirectory names
KNOWLEDGE_CATEGORIES = {
    "cloud": "01-cloud-benchmark",
    "cks": "02-cks-benchmark",
    "devsecops": "03-devsecops-benchmark",
    "compliance": "04-compliance-benchmark",
    "hardening": "05-hardening-benchmark",
    "incident-response": "06-incident-response-benchmark",
    "threat-modeling": "07-threat-modeling-benchmark",
    "cka": "08-cka-benchmark",
    "cnpa": "09-cnpa-benchmark",
    "operational": "10-operational-benchmark",
    "gemini-cks": "11-gemini-cks-benchmark",
    "gemini-cka": "12-gemini-cka-benchmark",
    "gemini-cnpa": "13-gemini-cnpa-benchmark",
    "gemini-aws": "14-gemini-aws-benchmark",
    "gemini-ops": "15-gemini-operational-benchmark",
}

# Quick mode: 3 questions per category = 21 total
QUICK_PER_CATEGORY = 3

# Generation config
MAX_NEW_TOKENS = 1024
TEMPERATURE = 0.3
TOP_P = 0.9

# Hallucination patterns (from run_benchmarks.py)
FAKE_PATTERNS = ["CIS 99.", "CVE-9999-", "NIST SP 999-"]


def load_model(model_path: str) -> Tuple:
    """Load a merged HuggingFace model for inference.

    Returns (model, tokenizer) tuple.
    """
    from unsloth import FastLanguageModel

    print(f"[MODEL] Loading {model_path}...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path,
        max_seq_length=4096,
        dtype=None,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)
    print(f"  Model loaded (4-bit quantized)")
    return model, tokenizer


def load_benchmark_questions(categories: Optional[List[str]] = None,
                             quick: bool = False) -> List[Dict]:
    """Load knowledge benchmark questions from GP-CLARIFY test data.

    Args:
        categories: List of category keys to load (None = all)
        quick: If True, sample QUICK_PER_CATEGORY questions per category

    Returns list of question dicts with category metadata.
    """
    if categories is None:
        categories = list(KNOWLEDGE_CATEGORIES.keys())

    all_questions = []

    for cat in categories:
        subdir = KNOWLEDGE_CATEGORIES.get(cat)
        if not subdir:
            print(f"  WARNING: Unknown category '{cat}', skipping")
            continue

        cat_dir = EVAL_DIR / subdir
        if not cat_dir.exists():
            print(f"  WARNING: Directory not found: {cat_dir}")
            continue

        cat_questions = []
        for jsonl_file in sorted(cat_dir.glob("*.jsonl")):
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            q = json.loads(line)
                            q["_source_file"] = jsonl_file.name
                            cat_questions.append(q)
                        except json.JSONDecodeError:
                            pass

        if quick and len(cat_questions) > QUICK_PER_CATEGORY:
            rng = random.Random(42)
            cat_questions = rng.sample(cat_questions, QUICK_PER_CATEGORY)

        all_questions.extend(cat_questions)

    return all_questions


def generate_response(model, tokenizer, question: str) -> str:
    """Generate a response from the local model.

    Uses the JADE system prompt and chat template.
    """
    messages = [
        {"role": "system", "content": "You are JADE, a DevSecOps security expert. Output working code directly."},
        {"role": "user", "content": question},
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=MAX_NEW_TOKENS,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
    )

    # Decode only the generated tokens (skip prompt)
    generated = outputs[0][inputs["input_ids"].shape[1]:]
    response = tokenizer.decode(generated, skip_special_tokens=True)

    return response.strip()


def score_knowledge_response(question: Dict, response: str) -> Dict:
    """Score a knowledge response using keyword matching.

    Replicates GP-CLARIFY scoring logic from run_benchmarks.py.
    """
    result = {
        "id": question.get("id", "unknown"),
        "category": question.get("category", "unknown"),
        "subcategory": question.get("subcategory"),
        "rank": question.get("rank"),
        "passed": False,
        "keywords_found": [],
        "keywords_missing": [],
        "fix_found": False,
        "hallucination": False,
    }

    response_lower = response.lower()
    expected_keywords = question.get("expected_keywords", [])
    grading = question.get("grading", {})
    keywords_required = grading.get("keywords_required", len(expected_keywords) // 2)

    # Keyword matching (case-insensitive substring)
    for keyword in expected_keywords:
        if keyword.lower() in response_lower:
            result["keywords_found"].append(keyword)
        else:
            result["keywords_missing"].append(keyword)

    # Fix validation — check each word of the expected fix independently
    # to avoid brittle exact-substring failures when Katie uses correct
    # terms in a different order or format
    expected_fix = question.get("expected_fix_contains")
    if expected_fix:
        fix_lower = expected_fix.lower()
        # Exact substring match first
        if fix_lower in response_lower:
            result["fix_found"] = True
        else:
            # Fallback: check if all significant words (3+ chars) appear
            fix_words = [w for w in fix_lower.split() if len(w) >= 3]
            if fix_words:
                found_count = sum(1 for w in fix_words if w in response_lower)
                result["fix_found"] = found_count >= len(fix_words) * 0.7
            else:
                result["fix_found"] = False

    # Pass/fail
    keywords_pass = len(result["keywords_found"]) >= keywords_required
    fix_required = grading.get("fix_required", False)
    fix_pass = (not fix_required) or result["fix_found"]
    result["passed"] = keywords_pass and fix_pass

    # Keyword score (0-1)
    if expected_keywords:
        result["keyword_score"] = len(result["keywords_found"]) / len(expected_keywords)
    else:
        result["keyword_score"] = 1.0

    # Hallucination detection
    for pattern in FAKE_PATTERNS:
        if pattern in response:
            result["hallucination"] = True
            break

    return result


def run_benchmark(model_path: str, categories: Optional[List[str]] = None,
                  quick: bool = False, dry_run: bool = False) -> Dict:
    """Run full benchmark pipeline: load model, generate, score, report.

    Returns results dict.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "quick" if quick else "full"

    print("=" * 60)
    print(f"JADE EVAL BRIDGE - {mode.upper()} BENCHMARK")
    print("=" * 60)
    print(f"Model: {model_path}")
    print(f"Mode: {mode}")
    print(f"Categories: {categories or 'all'}")
    print(f"Timestamp: {timestamp}")
    print()

    # Load questions
    print("[1/4] Loading benchmark questions...")
    questions = load_benchmark_questions(categories, quick)
    print(f"  Loaded {len(questions)} questions")

    if not questions:
        print("  ERROR: No questions found")
        return {}

    # Show breakdown
    cat_counts = {}
    for q in questions:
        cat = q.get("category", "unknown")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    for cat, count in sorted(cat_counts.items()):
        print(f"    {cat}: {count}")

    if dry_run:
        print(f"\n[DRY RUN] Would generate {len(questions)} responses")
        print(f"[DRY RUN] Estimated time: ~{len(questions) * 15 // 60} minutes (15s/question)")
        return {"dry_run": True, "questions": len(questions), "categories": cat_counts}

    # Load model
    print(f"\n[2/4] Loading model...")
    model, tokenizer = load_model(model_path)

    # Generate and score
    print(f"\n[3/4] Generating responses and scoring...")
    results_by_category = {}
    all_results = []
    total_passed = 0
    total_hallucinations = 0

    for i, question in enumerate(questions):
        cat = question.get("category", "unknown")
        qid = question.get("id", f"q-{i}")

        print(f"  [{i+1}/{len(questions)}] {qid}...", end=" ", flush=True)

        response = generate_response(model, tokenizer, question["question"])
        score = score_knowledge_response(question, response)
        score["response"] = response
        score["question_text"] = question["question"]

        status = "PASS" if score["passed"] else "FAIL"
        kw = f"{len(score['keywords_found'])}/{len(score['keywords_found']) + len(score['keywords_missing'])}"
        print(f"{status} (keywords: {kw})")

        if score["passed"]:
            total_passed += 1
        if score["hallucination"]:
            total_hallucinations += 1

        all_results.append(score)

        # Group by category
        if cat not in results_by_category:
            results_by_category[cat] = {"total": 0, "passed": 0, "results": []}
        results_by_category[cat]["total"] += 1
        if score["passed"]:
            results_by_category[cat]["passed"] += 1
        results_by_category[cat]["results"].append(score)

    # Compute summary
    accuracy = (total_passed / len(questions) * 100) if questions else 0

    # Check for previous results to compare
    comparison = _get_comparison(accuracy)

    results = {
        "model_path": model_path,
        "timestamp": timestamp,
        "mode": mode,
        "knowledge": {
            "categories": {
                cat: {"total": data["total"], "passed": data["passed"],
                      "accuracy": round(data["passed"] / data["total"] * 100, 1) if data["total"] else 0}
                for cat, data in results_by_category.items()
            },
            "summary": {
                "total": len(questions),
                "passed": total_passed,
                "accuracy": round(accuracy, 1),
                "hallucinations": total_hallucinations,
            }
        },
        "comparison_to_previous": comparison,
        "detailed_results": all_results,
    }

    # Save results
    print(f"\n[4/4] Saving results...")
    output_dir = save_results(results, timestamp)
    print(f"  Saved to: {output_dir}")

    # Print summary
    print(f"\n{'=' * 60}")
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Overall: {total_passed}/{len(questions)} ({accuracy:.1f}%)")
    print(f"Hallucinations: {total_hallucinations}")
    print()
    print(f"{'Category':<25} {'Passed':>8} {'Total':>8} {'Accuracy':>10}")
    print("-" * 55)
    for cat in sorted(results_by_category.keys()):
        data = results_by_category[cat]
        acc = data["passed"] / data["total"] * 100 if data["total"] else 0
        print(f"{cat:<25} {data['passed']:>8} {data['total']:>8} {acc:>9.1f}%")

    if comparison:
        print()
        delta = comparison.get("delta", 0)
        direction = "+" if delta > 0 else ""
        print(f"vs. Previous: {direction}{delta:.1f}% ({comparison.get('previous_accuracy', 0):.1f}% -> {accuracy:.1f}%)")
        if comparison.get("regressed_categories"):
            print(f"Regressed: {', '.join(comparison['regressed_categories'])}")

    print("=" * 60)

    return results


def save_results(results: Dict, timestamp: str) -> Path:
    """Save results to GP-CLARIFY 3-results/ directory."""
    output_dir = RESULTS_DIR / f"bridge_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # full_results.json
    with open(output_dir / "full_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # jade_responses.jsonl (compact, one per line)
    with open(output_dir / "jade_responses.jsonl", "w") as f:
        for r in results.get("detailed_results", []):
            compact = {
                "id": r["id"],
                "category": r["category"],
                "rank": r.get("rank"),
                "question": r.get("question_text", ""),
                "response": r.get("response", ""),
                "passed": r["passed"],
                "keyword_score": r.get("keyword_score", 0),
                "hallucination": r.get("hallucination", False),
            }
            f.write(json.dumps(compact) + "\n")

    # summary.md
    summary = results.get("knowledge", {}).get("summary", {})
    cats = results.get("knowledge", {}).get("categories", {})

    md_lines = [
        f"# JADE Eval Bridge Results",
        f"",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Model**: {results.get('model_path', 'unknown')}",
        f"**Mode**: {results.get('mode', 'unknown')}",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Tests | {summary.get('total', 0)} |",
        f"| Passed | {summary.get('passed', 0)} |",
        f"| Failed | {summary.get('total', 0) - summary.get('passed', 0)} |",
        f"| **Accuracy** | **{summary.get('accuracy', 0):.1f}%** |",
        f"| Hallucinations | {summary.get('hallucinations', 0)} |",
        f"",
        f"## By Category",
        f"",
        f"| Category | Passed | Total | Accuracy |",
        f"|----------|--------|-------|----------|",
    ]

    for cat in sorted(cats.keys()):
        data = cats[cat]
        md_lines.append(
            f"| {cat} | {data['passed']} | {data['total']} | {data['accuracy']:.1f}% |"
        )

    comp = results.get("comparison_to_previous")
    if comp:
        md_lines.extend([
            f"",
            f"## Comparison to Previous",
            f"",
            f"- Previous accuracy: {comp.get('previous_accuracy', 0):.1f}%",
            f"- Current accuracy: {summary.get('accuracy', 0):.1f}%",
            f"- Delta: {comp.get('delta', 0):+.1f}%",
        ])
        if comp.get("regressed_categories"):
            md_lines.append(f"- Regressed categories: {', '.join(comp['regressed_categories'])}")

    with open(output_dir / "summary.md", "w") as f:
        f.write("\n".join(md_lines) + "\n")

    return output_dir


def _get_comparison(current_accuracy: float) -> Optional[Dict]:
    """Find the most recent bridge result to compare against."""
    if not RESULTS_DIR.exists():
        return None

    bridge_dirs = sorted(RESULTS_DIR.glob("bridge_*"), reverse=True)
    # Skip the current run (not saved yet)
    for d in bridge_dirs:
        results_file = d / "full_results.json"
        if results_file.exists():
            try:
                with open(results_file) as f:
                    prev = json.load(f)
                prev_acc = prev.get("knowledge", {}).get("summary", {}).get("accuracy", 0)
                prev_cats = prev.get("knowledge", {}).get("categories", {})

                # Find regressed categories
                regressed = []
                for cat, data in prev_cats.items():
                    prev_cat_acc = data.get("accuracy", 0)
                    # We can't compare per-category here since current isn't saved yet
                    # Just note the previous for reference
                    pass

                return {
                    "previous_run": d.name,
                    "previous_accuracy": prev_acc,
                    "current_accuracy": current_accuracy,
                    "delta": round(current_accuracy - prev_acc, 1),
                    "regressed_categories": regressed,
                }
            except (json.JSONDecodeError, KeyError):
                continue

    return None


def compare_versions(run_a: str, run_b: str):
    """Compare two bridge result directories side by side."""
    dir_a = _find_result_dir(run_a)
    dir_b = _find_result_dir(run_b)

    if not dir_a or not dir_b:
        print(f"Could not find results for: {run_a if not dir_a else run_b}")
        return

    with open(dir_a / "full_results.json") as f:
        results_a = json.load(f)
    with open(dir_b / "full_results.json") as f:
        results_b = json.load(f)

    summary_a = results_a.get("knowledge", {}).get("summary", {})
    summary_b = results_b.get("knowledge", {}).get("summary", {})
    cats_a = results_a.get("knowledge", {}).get("categories", {})
    cats_b = results_b.get("knowledge", {}).get("categories", {})

    print("=" * 70)
    print(f"COMPARISON: {dir_a.name} vs {dir_b.name}")
    print("=" * 70)
    print(f"  Model A: {results_a.get('model_path', '?')}")
    print(f"  Model B: {results_b.get('model_path', '?')}")
    print()
    print(f"{'Metric':<25} {'A':>10} {'B':>10} {'Delta':>10}")
    print("-" * 60)
    print(f"{'Total':.<25} {summary_a.get('total', 0):>10} {summary_b.get('total', 0):>10}")
    print(f"{'Passed':.<25} {summary_a.get('passed', 0):>10} {summary_b.get('passed', 0):>10}")

    acc_a = summary_a.get("accuracy", 0)
    acc_b = summary_b.get("accuracy", 0)
    delta = acc_b - acc_a
    print(f"{'Accuracy':.<25} {acc_a:>9.1f}% {acc_b:>9.1f}% {delta:>+9.1f}%")
    print()

    # Per category
    all_cats = sorted(set(list(cats_a.keys()) + list(cats_b.keys())))
    print(f"{'Category':<25} {'A':>10} {'B':>10} {'Delta':>10}")
    print("-" * 60)
    for cat in all_cats:
        a_acc = cats_a.get(cat, {}).get("accuracy", 0)
        b_acc = cats_b.get(cat, {}).get("accuracy", 0)
        d = b_acc - a_acc
        marker = " <<" if d < -5 else ""
        print(f"{cat:<25} {a_acc:>9.1f}% {b_acc:>9.1f}% {d:>+9.1f}%{marker}")

    print("=" * 70)


def _find_result_dir(name: str) -> Optional[Path]:
    """Find a result directory by name or partial match."""
    # Exact match
    exact = RESULTS_DIR / name
    if exact.exists():
        return exact

    # Glob match
    matches = sorted(RESULTS_DIR.glob(f"*{name}*"))
    if matches:
        return matches[-1]  # Most recent

    return None


def get_latest_merged_model() -> Optional[str]:
    """Find the latest merged model from training state."""
    # Check all version dirs for training_state.json
    if not MODEL_VERSIONS_DIR.exists():
        return None

    latest_time = None
    latest_path = None

    for version_dir in MODEL_VERSIONS_DIR.iterdir():
        state_file = version_dir / "training_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                merged = state.get("last_merged")
                if merged and Path(merged).exists():
                    sessions = state.get("sessions", [])
                    if sessions:
                        completed = sessions[-1].get("completed_at", "")
                        if latest_time is None or completed > latest_time:
                            latest_time = completed
                            latest_path = merged
            except (json.JSONDecodeError, KeyError):
                continue

    return latest_path


def main():
    parser = argparse.ArgumentParser(
        description="JADE Eval Bridge - Run GP-CLARIFY benchmarks on local models")
    parser.add_argument("--model-path", type=str,
                        help="Path to merged HuggingFace model directory")
    parser.add_argument("--latest", action="store_true",
                        help="Use the latest merged model from training state")
    parser.add_argument("--category", type=str, action="append",
                        help="Run specific categories (can repeat). Default: all")
    parser.add_argument("--quick", action="store_true",
                        help=f"Quick mode: {QUICK_PER_CATEGORY} questions per category")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview test count without running")
    parser.add_argument("--compare", nargs=2, metavar=("RUN_A", "RUN_B"),
                        help="Compare two result directories")
    parser.add_argument("--list-results", action="store_true",
                        help="List all bridge results")
    args = parser.parse_args()

    # Compare mode
    if args.compare:
        compare_versions(args.compare[0], args.compare[1])
        return

    # List results mode
    if args.list_results:
        bridge_dirs = sorted(RESULTS_DIR.glob("bridge_*"))
        if not bridge_dirs:
            print("No bridge results found")
            return
        print(f"{'Run':<35} {'Accuracy':>10} {'Questions':>10} {'Mode':>8}")
        print("-" * 70)
        for d in bridge_dirs:
            rf = d / "full_results.json"
            if rf.exists():
                with open(rf) as f:
                    r = json.load(f)
                s = r.get("knowledge", {}).get("summary", {})
                print(f"{d.name:<35} {s.get('accuracy', 0):>9.1f}% {s.get('total', 0):>10} {r.get('mode', '?'):>8}")
        return

    # Determine model path
    model_path = args.model_path
    if args.latest:
        model_path = get_latest_merged_model()
        if not model_path:
            print("No merged model found in training state")
            print("Train a chunk first: python3 train_v10.py")
            return
        print(f"[LATEST] Using: {model_path}")

    if not model_path and not args.dry_run:
        print("Error: --model-path or --latest required")
        print("Usage: python3 eval_bridge.py --model-path /path/to/merged")
        print("       python3 eval_bridge.py --latest")
        return

    # Dry run doesn't need a model
    if args.dry_run:
        model_path = model_path or "(not specified)"

    # Run benchmark
    run_benchmark(
        model_path=model_path,
        categories=args.category,
        quick=args.quick,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
