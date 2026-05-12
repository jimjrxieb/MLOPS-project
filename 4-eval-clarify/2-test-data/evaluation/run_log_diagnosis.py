#!/usr/bin/env python3
"""
JADE Log Diagnosis Test Runner

Reads log_diagnosis_tests.jsonl and tests JADE's ability to:
1. Diagnose problems from logs
2. Recommend fixes
3. Suggest appropriate NPCs

Usage:
    python run_log_diagnosis.py --model jade:v0.8
    python run_log_diagnosis.py --model jade:v0.8 --limit 5
    python run_log_diagnosis.py --model jade:v0.8 --id diag-001
"""

import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
import re

SCRIPT_DIR = Path(__file__).parent
FAULTY_DIR = SCRIPT_DIR / "FAULTY"
TESTS_FILE = FAULTY_DIR / "log_diagnosis_tests.jsonl"
RESULTS_DIR = SCRIPT_DIR / "diagnosis-results"


def load_tests(tests_file: Path) -> list:
    """Load test cases from JSONL"""
    tests = []
    with open(tests_file) as f:
        for line in f:
            line = line.strip()
            if line:
                tests.append(json.loads(line))
    return tests


def load_full_log(log_file: str) -> str:
    """Load the full log file content"""
    full_path = FAULTY_DIR / log_file
    if full_path.exists():
        return full_path.read_text()[:8000]  # Limit to 8k chars
    return ""


def build_prompt(test: dict, include_full_log: bool = False) -> str:
    """Build the prompt for JADE"""

    log_content = test.get("log_snippet", "")
    if include_full_log and test.get("log_file"):
        full_log = load_full_log(test["log_file"])
        if full_log:
            log_content = full_log

    prompt = f"""You are JADE, a DevSecOps AI. Analyze this log and answer the question.

## LOG ({test.get('category', 'unknown').upper()})
```
{log_content}
```

## QUESTION
{test['question']}

## REQUIRED FORMAT
Answer in this exact format:

DIAGNOSIS: [One sentence explaining what's wrong]

SEVERITY: [CRITICAL/HIGH/MEDIUM/LOW]

FIX TYPE: [command/yaml/code/incident_response]

ACTIONS:
1. [First action]
2. [Second action]
3. [Third action]

RECOMMENDED NPCs: [List NPCs that should be run, e.g., TrivyNPC, KubescapeNPC]
"""
    return prompt


def call_jade(prompt: str, model: str, timeout: int = 120) -> str:
    """Call JADE via Ollama"""
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "ERROR: Timeout"
    except Exception as e:
        return f"ERROR: {e}"


def parse_response(response: str) -> dict:
    """Parse JADE's structured response"""
    parsed = {
        "diagnosis": "",
        "severity": "",
        "fix_type": "",
        "actions": [],
        "npcs": []
    }

    # Extract diagnosis
    diag_match = re.search(r"DIAGNOSIS:\s*(.+?)(?=\n|SEVERITY|$)", response, re.IGNORECASE | re.DOTALL)
    if diag_match:
        parsed["diagnosis"] = diag_match.group(1).strip()

    # Extract severity
    sev_match = re.search(r"SEVERITY:\s*(CRITICAL|HIGH|MEDIUM|LOW)", response, re.IGNORECASE)
    if sev_match:
        parsed["severity"] = sev_match.group(1).upper()

    # Extract fix type
    fix_match = re.search(r"FIX TYPE:\s*(\w+)", response, re.IGNORECASE)
    if fix_match:
        parsed["fix_type"] = fix_match.group(1).lower()

    # Extract actions
    actions = re.findall(r"\d+\.\s*(.+?)(?=\n\d+\.|\nRECOMMENDED|$)", response, re.DOTALL)
    parsed["actions"] = [a.strip() for a in actions if a.strip()]

    # Extract NPCs
    npc_match = re.search(r"RECOMMENDED NPCs?:\s*(.+?)(?=\n\n|$)", response, re.IGNORECASE | re.DOTALL)
    if npc_match:
        npc_text = npc_match.group(1)
        # Find NPC names (ending in NPC)
        npcs = re.findall(r"(\w+NPC)", npc_text)
        parsed["npcs"] = list(set(npcs))

    return parsed


def score_response(test: dict, parsed: dict) -> dict:
    """Score JADE's response against expected"""
    scores = {}

    # 1. Diagnosis quality (keyword matching)
    expected_diag = test.get("expected_diagnosis", "").lower()
    actual_diag = parsed.get("diagnosis", "").lower()

    # Key terms from expected diagnosis
    key_terms = [w for w in expected_diag.split() if len(w) > 4]
    matches = sum(1 for t in key_terms if t in actual_diag)
    scores["diagnosis"] = min(1.0, matches / max(len(key_terms), 1))

    # 2. Severity match
    expected_sev = test.get("severity", "").upper()
    actual_sev = parsed.get("severity", "").upper()
    scores["severity"] = 1.0 if expected_sev == actual_sev else 0.0

    # 3. Fix type match
    expected_fix = test.get("expected_fix_type", "").lower()
    actual_fix = parsed.get("fix_type", "").lower()
    scores["fix_type"] = 1.0 if expected_fix in actual_fix or actual_fix in expected_fix else 0.0

    # 4. Actions coverage
    expected_actions = test.get("expected_actions", [])
    actual_actions = " ".join(parsed.get("actions", [])).lower()

    action_matches = 0
    for exp_action in expected_actions:
        # Check if key words from expected action appear
        key_words = [w for w in exp_action.lower().split() if len(w) > 3]
        if any(kw in actual_actions for kw in key_words):
            action_matches += 1

    scores["actions"] = action_matches / max(len(expected_actions), 1)

    # 5. NPC recommendations
    expected_npcs = set(test.get("expected_npcs", []))
    actual_npcs = set(parsed.get("npcs", []))

    if expected_npcs:
        overlap = len(expected_npcs & actual_npcs)
        scores["npcs"] = overlap / len(expected_npcs)
    else:
        scores["npcs"] = 1.0 if not actual_npcs else 0.5

    # Overall score
    weights = {"diagnosis": 0.3, "severity": 0.1, "fix_type": 0.1, "actions": 0.3, "npcs": 0.2}
    scores["overall"] = sum(scores[k] * weights[k] for k in weights)

    return scores


def run_test(test: dict, model: str, include_full_log: bool = False) -> dict:
    """Run a single test"""
    print(f"\n{'='*60}")
    print(f"Test: {test['id']} ({test['category']})")
    print(f"Question: {test['question'][:80]}...")
    print(f"{'='*60}")

    # Build prompt and call JADE
    prompt = build_prompt(test, include_full_log)
    response = call_jade(prompt, model)

    # Parse response
    parsed = parse_response(response)

    # Score
    scores = score_response(test, parsed)

    # Print results
    print(f"\nJADE Diagnosis: {parsed['diagnosis'][:100]}...")
    print(f"Severity: {parsed['severity']} (expected: {test.get('severity', 'N/A')})")
    print(f"Fix Type: {parsed['fix_type']} (expected: {test.get('expected_fix_type', 'N/A')})")
    print(f"Actions: {len(parsed['actions'])} provided")
    print(f"NPCs: {parsed['npcs']}")

    print(f"\nScores:")
    for k, v in scores.items():
        status = "✓" if v >= 0.6 else "✗"
        print(f"  {status} {k}: {v:.2f}")

    passed = scores["overall"] >= 0.6
    print(f"\nRESULT: {'PASS' if passed else 'FAIL'} ({scores['overall']:.0%})")

    return {
        "test_id": test["id"],
        "category": test["category"],
        "passed": passed,
        "scores": scores,
        "parsed_response": parsed,
        "raw_response": response[:500],
        "timestamp": datetime.now().isoformat()
    }


def main():
    parser = argparse.ArgumentParser(description="JADE Log Diagnosis Tester")
    parser.add_argument("--model", default="jade:v0.8", help="Model to test")
    parser.add_argument("--limit", type=int, help="Limit number of tests")
    parser.add_argument("--id", help="Run specific test by ID")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--full-log", action="store_true", help="Include full log file")
    parser.add_argument("--output", type=Path, help="Output results file")

    args = parser.parse_args()

    # Load tests
    tests = load_tests(TESTS_FILE)
    print(f"Loaded {len(tests)} test cases")

    # Filter
    if args.id:
        tests = [t for t in tests if t["id"] == args.id]
    if args.category:
        tests = [t for t in tests if t["category"] == args.category]
    if args.limit:
        tests = tests[:args.limit]

    print(f"Running {len(tests)} tests with model: {args.model}")

    # Run tests
    results = []
    for test in tests:
        result = run_test(test, args.model, args.full_log)
        results.append(result)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    print(f"Total: {total}")
    print(f"Passed: {passed} ({passed/total:.0%})")
    print(f"Failed: {total - passed}")

    # By category
    by_cat = {}
    for r in results:
        cat = r["category"]
        if cat not in by_cat:
            by_cat[cat] = {"passed": 0, "total": 0}
        by_cat[cat]["total"] += 1
        if r["passed"]:
            by_cat[cat]["passed"] += 1

    print("\nBy Category:")
    for cat, stats in sorted(by_cat.items()):
        pct = stats["passed"] / stats["total"] * 100
        print(f"  {cat}: {stats['passed']}/{stats['total']} ({pct:.0f}%)")

    # Average scores
    print("\nAverage Scores:")
    all_scores = {}
    for r in results:
        for k, v in r["scores"].items():
            if k not in all_scores:
                all_scores[k] = []
            all_scores[k].append(v)

    for k, v in sorted(all_scores.items()):
        avg = sum(v) / len(v)
        print(f"  {k}: {avg:.2f}")

    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    output_file = args.output or RESULTS_DIR / f"diagnosis_{args.model.replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    with open(output_file, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
