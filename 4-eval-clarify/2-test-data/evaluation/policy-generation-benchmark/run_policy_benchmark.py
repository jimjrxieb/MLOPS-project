#!/usr/bin/env python3
"""
JADE Policy Generation Benchmark

Tests JADE's ability to generate correct Rego policies in breach response scenarios.
Compares JADE output to reference policies.

Usage:
    python3 run_policy_benchmark.py                    # Run full benchmark
    python3 run_policy_benchmark.py --limit 5         # Test first 5 scenarios
    python3 run_policy_benchmark.py --verbose         # Show JADE responses
    python3 run_policy_benchmark.py --compare-only    # Skip JADE, just compare existing results
"""

import json
import os
import sys
import argparse
import requests
import re
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

# Paths
SCRIPT_DIR = Path(__file__).parent
BENCHMARK_FILE = SCRIPT_DIR / "breach_scenarios.jsonl"
REFERENCE_POLICIES_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/4-GP-CLARIFY/2-test-data/inference-tests/policies/all-policies")
FIXED_POLICIES_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/4-GP-CLARIFY/2-test-data/inference-tests/FAULTYFIXED")
RESULTS_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/4-GP-CLARIFY/3-results")


def ask_jade(prompt: str, model: str = "jade:v1.0", timeout: int = 120) -> str:
    """Query JADE via Ollama API."""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}  # Low temp for consistent policy output
            },
            timeout=timeout
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.Timeout:
        return "[ERROR: Timeout]"
    except Exception as e:
        return f"[ERROR: {e}]"


def extract_rego_from_response(response: str) -> str:
    """Extract Rego code block from JADE response."""
    # Try to find ```rego or ``` code blocks
    patterns = [
        r'```rego\n(.*?)```',
        r'```\n(.*?)```',
        r'```(.*?)```',
    ]

    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            code = match.group(1).strip()
            # Verify it looks like Rego (has package or deny/violation)
            if 'package' in code or 'deny' in code or 'violation' in code:
                return code

    # Fallback: look for package...deny or violation block without backticks
    for rule_type in ['deny', 'violation', 'warn']:
        package_match = re.search(
            rf'(package\s+\w+[\w.]*.*?{rule_type}\[.*?\]\s*\{{.*?\}})',
            response, re.DOTALL
        )
        if package_match:
            return package_match.group(1).strip()

    return ""


def load_reference_policy(policy_name: str, policy_type: str) -> str:
    """Load the reference policy for comparison."""
    if policy_type == "fix":
        policy_path = FIXED_POLICIES_DIR / policy_name
    else:
        policy_path = REFERENCE_POLICIES_DIR / policy_name

    if policy_path.exists():
        with open(policy_path) as f:
            return f.read().strip()
    return ""


def normalize_rego(code: str) -> str:
    """Normalize Rego code for comparison (remove comments, extra whitespace)."""
    # Remove comments
    lines = []
    for line in code.split('\n'):
        # Remove inline comments
        if '#' in line:
            line = line.split('#')[0]
        line = line.strip()
        if line:
            lines.append(line)
    return '\n'.join(lines)


def compare_policies(jade_rego: str, reference_rego: str) -> dict:
    """Compare JADE's generated policy to reference."""
    # Normalize both
    jade_norm = normalize_rego(jade_rego)
    ref_norm = normalize_rego(reference_rego)

    # Check key elements - accept both deny[] and violation[] (Gatekeeper vs Conftest)
    result = {
        "has_package": "package" in jade_rego,
        "has_deny_rule": any(x in jade_rego for x in ["deny[", "violation[", "warn["]),
        "has_msg_assignment": any(x in jade_rego for x in ["msg :=", 'msg = "', 'msg = sprintf', '"msg":', "'msg':"]),
        "has_input_check": "input." in jade_rego,
        "similarity_score": 0.0,
        "exact_match": False,
        "functional_match": False,
    }

    # Similarity score
    result["similarity_score"] = SequenceMatcher(None, jade_norm, ref_norm).ratio()

    # Exact match (normalized)
    result["exact_match"] = jade_norm == ref_norm

    # Functional match: has core elements
    # Check if key patterns from reference exist in JADE output
    ref_patterns = []
    if "privileged" in ref_norm:
        ref_patterns.append("privileged")
    if "hostNetwork" in ref_norm:
        ref_patterns.append("hostNetwork")
    if "hostPID" in ref_norm:
        ref_patterns.append("hostPID")
    if "hostIPC" in ref_norm:
        ref_patterns.append("hostIPC")
    if "latest" in ref_norm:
        ref_patterns.append("latest")
    if "sha256" in ref_norm:
        ref_patterns.append("sha256")
    if "limits.cpu" in ref_norm or "limits.memory" in ref_norm:
        ref_patterns.append("limits")
    if "runAsUser" in ref_norm or "runAsNonRoot" in ref_norm:
        ref_patterns.append("runAs")
    if "hostPath" in ref_norm:
        ref_patterns.append("hostPath")
    if "docker.sock" in ref_norm:
        ref_patterns.append("docker.sock")

    if ref_patterns:
        matches = sum(1 for p in ref_patterns if p.lower() in jade_norm.lower())
        pattern_score = matches / len(ref_patterns)
    else:
        pattern_score = 0.5  # Default if no specific patterns

    # Functional match: has structure + most key patterns
    result["functional_match"] = (
        result["has_package"] and
        result["has_deny_rule"] and
        result["has_msg_assignment"] and
        (pattern_score >= 0.5 or result["similarity_score"] >= 0.6)
    )

    return result


def load_scenarios(filepath: Path, limit: int = None) -> list:
    """Load benchmark scenarios from JSONL."""
    scenarios = []
    with open(filepath) as f:
        for line in f:
            if line.strip():
                scenarios.append(json.loads(line))
                if limit and len(scenarios) >= limit:
                    break
    return scenarios


def run_benchmark(model: str = "jade:v1.0", limit: int = None, verbose: bool = False) -> dict:
    """Run the policy generation benchmark."""
    scenarios = load_scenarios(BENCHMARK_FILE, limit)

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_safe = model.replace(":", "_").replace("/", "_")
    output_dir = RESULTS_DIR / f"policy_benchmark_{model_safe}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"JADE Policy Generation Benchmark")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"Scenarios: {len(scenarios)}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")

    results = []
    passed = 0

    for i, scenario in enumerate(scenarios, 1):
        sid = scenario["id"]
        category = scenario["category"]
        prompt = scenario["scenario"]
        expected = scenario["expected_policy"]
        policy_type = scenario["policy_type"]

        print(f"[{i}/{len(scenarios)}] {sid} ({category})...", end=" ", flush=True)

        # Ask JADE
        jade_response = ask_jade(prompt, model)

        if jade_response.startswith("[ERROR"):
            print(f"ERROR")
            result = {
                "id": sid,
                "category": category,
                "passed": False,
                "error": jade_response,
                "jade_response": "",
                "jade_rego": "",
                "comparison": {}
            }
        else:
            # Extract Rego from response
            jade_rego = extract_rego_from_response(jade_response)

            # Load reference
            ref_rego = load_reference_policy(expected, policy_type)

            # Compare
            comparison = compare_policies(jade_rego, ref_rego)
            is_pass = comparison["functional_match"]

            if is_pass:
                passed += 1
                status = "PASS"
            else:
                status = "FAIL"

            print(f"{status} (sim={comparison['similarity_score']:.2f})")

            result = {
                "id": sid,
                "category": category,
                "rank": scenario["rank"],
                "policy_type": policy_type,
                "expected_policy": expected,
                "passed": is_pass,
                "jade_response": jade_response,
                "jade_rego": jade_rego,
                "reference_rego": ref_rego,
                "comparison": comparison
            }

            if verbose:
                print(f"    Rego extracted: {len(jade_rego)} chars")
                print(f"    Has: pkg={comparison['has_package']} deny={comparison['has_deny_rule']} msg={comparison['has_msg_assignment']}")

        results.append(result)

    # Save results
    results_file = output_dir / "jade_policy_results.jsonl"
    with open(results_file, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Calculate stats
    total = len(results)
    accuracy = (passed / total * 100) if total > 0 else 0

    # By category
    by_category = {}
    for r in results:
        cat = r["category"]
        if cat not in by_category:
            by_category[cat] = {"total": 0, "passed": 0}
        by_category[cat]["total"] += 1
        if r.get("passed"):
            by_category[cat]["passed"] += 1

    # By policy type
    by_type = {}
    for r in results:
        ptype = r.get("policy_type", "unknown")
        if ptype not in by_type:
            by_type[ptype] = {"total": 0, "passed": 0}
        by_type[ptype]["total"] += 1
        if r.get("passed"):
            by_type[ptype]["passed"] += 1

    summary = {
        "model": model,
        "timestamp": timestamp,
        "total_scenarios": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy_percent": round(accuracy, 2),
        "by_category": by_category,
        "by_policy_type": by_type
    }

    summary_file = output_dir / "summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Passed: {passed}/{total} ({accuracy:.1f}%)")
    print(f"\nBy Policy Type:")
    for ptype, stats in by_type.items():
        pct = (stats['passed']/stats['total']*100) if stats['total'] > 0 else 0
        print(f"  {ptype}: {stats['passed']}/{stats['total']} ({pct:.0f}%)")
    print(f"\nFailed Scenarios:")
    for r in results:
        if not r.get("passed"):
            print(f"  - {r['id']}: {r['category']}")
    print(f"{'='*60}")
    print(f"Results: {output_dir}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="JADE Policy Generation Benchmark")
    parser.add_argument("--model", default="jade:v1.0", help="Ollama model to test")
    parser.add_argument("--limit", type=int, help="Limit number of scenarios")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    run_benchmark(model=args.model, limit=args.limit, verbose=args.verbose)


if __name__ == "__main__":
    main()
