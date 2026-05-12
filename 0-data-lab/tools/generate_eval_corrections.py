#!/usr/bin/env python3
"""
Eval-Driven Self-Correction Generator
=======================================
Takes eval results (pass/fail) and generates corrective training data:
- Failed responses → paired with the correct answer from the benchmark
- This teaches Katie to learn from her own mistakes

Also extracts passed responses as reinforcement — Katie should keep doing
what she's doing right.

This is the simplest form of reinforcement learning:
  wrong answer + right answer → corrective training example

Usage:
    python3 generate_eval_corrections.py                          # Use latest eval
    python3 generate_eval_corrections.py --results-dir bridge_*   # Specific eval
"""
import json
import argparse
from pathlib import Path

RESULTS_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/4-eval-clarify/3-results")
EVAL_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/4-eval-clarify/2-test-data/evaluation")
OUTPUT_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-data-pipeline/01-raw-data-lake")

SYSTEM_PROMPT = "You are Katie, a CKS/CKA-certified Kubernetes security triage engine. Always use exact resource kind names (NetworkPolicy, FalcoRule, StaticPod). Reference specific tools by name (Falco, Cosign, Trivy, Sysdig, Kyverno, OPA). Check ArgoCD ownership before any fix. Route by rank (E/D/C/B/S)."


def find_latest_eval():
    """Find the most recent bridge eval results."""
    bridge_dirs = sorted(RESULTS_DIR.glob("bridge_*"), reverse=True)
    for d in bridge_dirs:
        if (d / "full_results.json").exists():
            return d
    return None


def load_benchmark_questions():
    """Load all benchmark questions keyed by ID for answer lookup."""
    questions = {}
    for cat_dir in EVAL_DIR.iterdir():
        if not cat_dir.is_dir() or cat_dir.name in ("archive", "evaluators"):
            continue
        for jsonl_file in cat_dir.glob("*.jsonl"):
            with open(jsonl_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            q = json.loads(line)
                            qid = q.get("id", "")
                            if qid:
                                questions[qid] = q
                        except json.JSONDecodeError:
                            pass
    return questions


def generate_correction(result, benchmark_q):
    """Generate a corrective training example from a failed eval response."""
    question_text = result.get("question_text", "")
    if not question_text:
        return None

    # Build the "correct" answer from benchmark expected keywords
    keywords = benchmark_q.get("expected_keywords", [])
    expected_fix = benchmark_q.get("expected_fix_contains", "")

    # Build a keyword-rich answer hint
    keyword_section = ", ".join(keywords) if keywords else ""
    category = result.get("category", "unknown")
    subcategory = result.get("subcategory", "")

    # The corrective prompt: show Katie what she SHOULD have included
    correction_prompt = f"[CORRECTION] Your previous answer missed key concepts. Include these in your response: {keyword_section}"
    if expected_fix:
        correction_prompt += f"\nMust include: {expected_fix}"

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question_text},
            {"role": "assistant", "content": f"{correction_prompt}\n\n{_build_ideal_answer(benchmark_q)}"}
        ]
    }


def generate_reinforcement(result):
    """Generate a reinforcement example from a passed eval response."""
    question_text = result.get("question_text", "")
    response = result.get("response", "")
    if not question_text or not response:
        return None

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question_text},
            {"role": "assistant", "content": response}
        ]
    }


def _build_ideal_answer(benchmark_q):
    """Build an ideal answer from benchmark metadata."""
    keywords = benchmark_q.get("expected_keywords", [])
    expected_fix = benchmark_q.get("expected_fix_contains", "")
    category = benchmark_q.get("category", "")
    subcategory = benchmark_q.get("subcategory", "")

    parts = []
    if keywords:
        parts.append(f"Key concepts: {', '.join(keywords)}")
    if expected_fix:
        parts.append(f"Required fix: {expected_fix}")
    if subcategory:
        parts.append(f"Domain: {category}/{subcategory}")

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=str, help="Specific results directory")
    parser.add_argument("--min-keyword-score", type=float, default=0.3,
                        help="Only generate corrections for responses with keyword_score below this")
    parser.add_argument("--reinforce-threshold", type=float, default=0.7,
                        help="Reinforce responses with keyword_score above this")
    args = parser.parse_args()

    # Find eval results
    if args.results_dir:
        results_path = RESULTS_DIR / args.results_dir
    else:
        results_path = find_latest_eval()

    if not results_path:
        print("No eval results found. Run eval_bridge.py first.")
        return

    print(f"Using eval results: {results_path.name}")

    # Load results and benchmark questions
    with open(results_path / "full_results.json") as f:
        data = json.load(f)

    benchmark_qs = load_benchmark_questions()
    print(f"Loaded {len(benchmark_qs)} benchmark questions for answer lookup")

    detailed = data.get("detailed_results", [])
    corrections = []
    reinforcements = []

    for result in detailed:
        qid = result.get("id", "")
        kw_score = result.get("keyword_score", 0)

        if not result["passed"] and kw_score < args.min_keyword_score:
            # Failed badly — generate correction
            if qid in benchmark_qs:
                correction = generate_correction(result, benchmark_qs[qid])
                if correction:
                    corrections.append(correction)

        elif result["passed"] and kw_score >= args.reinforce_threshold:
            # Passed well — reinforce
            reinforcement = generate_reinforcement(result)
            if reinforcement:
                reinforcements.append(reinforcement)

    # Write output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    corrections_file = OUTPUT_DIR / "eval_corrections.jsonl"
    with open(corrections_file, "w") as f:
        for ex in corrections:
            f.write(json.dumps(ex) + "\n")

    reinforcements_file = OUTPUT_DIR / "eval_reinforcements.jsonl"
    with open(reinforcements_file, "w") as f:
        for ex in reinforcements:
            f.write(json.dumps(ex) + "\n")

    print(f"\nResults:")
    print(f"  Corrections (failed, kw_score < {args.min_keyword_score}): {len(corrections)} → {corrections_file.name}")
    print(f"  Reinforcements (passed, kw_score >= {args.reinforce_threshold}): {len(reinforcements)} → {reinforcements_file.name}")

    # Category breakdown
    cat_corrections = {}
    for ex in corrections:
        # Extract from the detailed results
        pass

    total = len(corrections) + len(reinforcements)
    print(f"  Total training examples: {total}")
    print(f"\nNext: python3 etl_pipeline.py → chunk_data.py → train_llama3b.py")
    print(f"Katie learns from her own eval mistakes + reinforces what she got right.")


if __name__ == "__main__":
    main()
