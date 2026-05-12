#!/usr/bin/env python3
"""
JADE Inference Test with Claude Code as Judge

Flow:
1. Load FAULTY test case (log or config)
2. Send to jade:v0.8 for diagnosis/fix
3. Send jade's response to Claude for evaluation
4. Claude judges: PASS/FAIL with reasoning

Usage:
    python run_claude_judge.py --model jade:v0.8 --id diag-021
    python run_claude_judge.py --model jade:v0.8 --limit 5
"""

import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
import os

SCRIPT_DIR = Path(__file__).parent
FAULTY_DIR = SCRIPT_DIR / "FAULTY"
TESTS_FILE = FAULTY_DIR / "log_diagnosis_tests.jsonl"
RESULTS_DIR = SCRIPT_DIR / "claude-judge-results"


def load_tests(tests_file: Path) -> list:
    """Load test cases from JSONL"""
    tests = []
    with open(tests_file) as f:
        for line in f:
            line = line.strip()
            if line:
                tests.append(json.loads(line))
    return tests


def load_full_content(log_file: str) -> str:
    """Load full file content"""
    full_path = FAULTY_DIR / log_file
    if full_path.exists():
        return full_path.read_text()[:8000]
    return ""


def call_jade(prompt: str, model: str, timeout: int = 120) -> str:
    """Call jade via Ollama"""
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


def call_claude_judge(test: dict, jade_response: str, timeout: int = 60) -> dict:
    """
    Call Claude Code to judge jade's response.
    Uses 'claude' CLI if available, otherwise returns manual review needed.
    """

    judge_prompt = f"""You are evaluating JADE's security diagnosis. Be a strict but fair judge.

## TEST CASE
- ID: {test['id']}
- Category: {test['category']}
- Severity: {test['severity']}
- Question: {test['question']}

## EXPECTED (Ground Truth)
- Diagnosis: {test.get('expected_diagnosis', 'N/A')}
- Fix Type: {test.get('expected_fix_type', 'N/A')}
- Actions: {test.get('expected_actions', [])}
- NPCs: {test.get('expected_npcs', [])}

## JADE'S RESPONSE
{jade_response[:4000]}

## YOUR TASK
Evaluate if JADE's response is correct. Consider:
1. Did JADE identify the core problem correctly?
2. Are the recommended actions appropriate and would they fix the issue?
3. Is the severity assessment reasonable?
4. Would following JADE's advice resolve the security issue?

Respond in this EXACT format:
VERDICT: PASS or FAIL
SCORE: 0-100
REASONING: One paragraph explaining your judgment
DIAGNOSIS_CORRECT: YES or NO or PARTIAL
ACTIONS_HELPFUL: YES or NO or PARTIAL
"""

    # Try using claude CLI
    try:
        result = subprocess.run(
            ["claude", "-p", judge_prompt],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return parse_claude_verdict(result.stdout.strip())
    except FileNotFoundError:
        # Claude CLI not available, return for manual review
        return {
            "verdict": "MANUAL_REVIEW",
            "score": -1,
            "reasoning": "Claude CLI not available. Manual review required.",
            "diagnosis_correct": "UNKNOWN",
            "actions_helpful": "UNKNOWN",
            "raw_response": ""
        }
    except subprocess.TimeoutExpired:
        return {
            "verdict": "TIMEOUT",
            "score": -1,
            "reasoning": "Claude judge timed out",
            "diagnosis_correct": "UNKNOWN",
            "actions_helpful": "UNKNOWN",
            "raw_response": ""
        }
    except Exception as e:
        return {
            "verdict": "ERROR",
            "score": -1,
            "reasoning": str(e),
            "diagnosis_correct": "UNKNOWN",
            "actions_helpful": "UNKNOWN",
            "raw_response": ""
        }


def parse_claude_verdict(response: str) -> dict:
    """Parse Claude's structured verdict"""
    result = {
        "verdict": "UNKNOWN",
        "score": 0,
        "reasoning": "",
        "diagnosis_correct": "UNKNOWN",
        "actions_helpful": "UNKNOWN",
        "raw_response": response[:1000]
    }

    lines = response.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith("VERDICT:"):
            v = line.replace("VERDICT:", "").strip().upper()
            result["verdict"] = "PASS" if "PASS" in v else "FAIL"
        elif line.startswith("SCORE:"):
            try:
                result["score"] = int(line.replace("SCORE:", "").strip().split()[0])
            except:
                pass
        elif line.startswith("REASONING:"):
            result["reasoning"] = line.replace("REASONING:", "").strip()
        elif line.startswith("DIAGNOSIS_CORRECT:"):
            result["diagnosis_correct"] = line.replace("DIAGNOSIS_CORRECT:", "").strip().upper()
        elif line.startswith("ACTIONS_HELPFUL:"):
            result["actions_helpful"] = line.replace("ACTIONS_HELPFUL:", "").strip().upper()

    return result


def run_test(test: dict, model: str) -> dict:
    """Run a single test with Claude as judge"""
    print(f"\n{'='*60}")
    print(f"Test: {test['id']} ({test['category']})")
    print(f"Question: {test['question'][:60]}...")
    print(f"{'='*60}")

    # Load full content if available
    content = test.get("log_snippet", "")
    if test.get("log_file"):
        full_content = load_full_content(test["log_file"])
        if full_content:
            content = full_content

    # Build prompt for jade
    jade_prompt = f"""You are JADE, a DevSecOps AI. Analyze this and provide your diagnosis and fix.

## INPUT ({test.get('category', 'security').upper()})
```
{content}
```

## QUESTION
{test['question']}

Provide:
1. DIAGNOSIS - What's wrong?
2. SEVERITY - How critical?
3. ACTIONS - Step-by-step fix commands
4. RECOMMENDED TOOLS - Which scanners/NPCs to use
"""

    print("Calling jade...")
    jade_response = call_jade(jade_prompt, model)

    if jade_response.startswith("ERROR"):
        print(f"jade error: {jade_response}")
        return {
            "test_id": test["id"],
            "category": test["category"],
            "jade_response": jade_response,
            "verdict": "ERROR",
            "score": 0,
            "reasoning": jade_response,
            "timestamp": datetime.now().isoformat()
        }

    print(f"jade response: {len(jade_response)} chars")
    print(f"Preview: {jade_response[:200]}...")

    # Call Claude to judge
    print("\nCalling Claude judge...")
    verdict = call_claude_judge(test, jade_response)

    print(f"\nCLAUDE VERDICT: {verdict['verdict']}")
    print(f"SCORE: {verdict['score']}")
    print(f"REASONING: {verdict['reasoning'][:200]}...")

    return {
        "test_id": test["id"],
        "category": test["category"],
        "severity": test["severity"],
        "question": test["question"],
        "jade_response": jade_response[:2000],
        "verdict": verdict["verdict"],
        "score": verdict["score"],
        "reasoning": verdict["reasoning"],
        "diagnosis_correct": verdict["diagnosis_correct"],
        "actions_helpful": verdict["actions_helpful"],
        "timestamp": datetime.now().isoformat()
    }


def main():
    parser = argparse.ArgumentParser(description="JADE Test with Claude Judge")
    parser.add_argument("--model", default="jade:v0.8", help="Model to test")
    parser.add_argument("--limit", type=int, help="Limit number of tests")
    parser.add_argument("--id", help="Run specific test by ID")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--output", type=Path, help="Output file")

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
    print("Judge: Claude Code")

    # Run tests
    results = []
    for test in tests:
        result = run_test(test, args.model)
        results.append(result)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY (Claude Judge)")
    print("="*60)

    passed = sum(1 for r in results if r["verdict"] == "PASS")
    failed = sum(1 for r in results if r["verdict"] == "FAIL")
    other = len(results) - passed - failed

    print(f"Total: {len(results)}")
    print(f"PASS: {passed}")
    print(f"FAIL: {failed}")
    if other > 0:
        print(f"Other (timeout/error/manual): {other}")

    if passed + failed > 0:
        print(f"Pass Rate: {passed/(passed+failed):.0%}")

    # Average score
    scores = [r["score"] for r in results if r["score"] >= 0]
    if scores:
        print(f"Average Score: {sum(scores)/len(scores):.1f}/100")

    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    output_file = args.output or RESULTS_DIR / f"claude_judge_{args.model.replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    with open(output_file, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
