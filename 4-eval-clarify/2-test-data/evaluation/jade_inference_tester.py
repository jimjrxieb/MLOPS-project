#!/usr/bin/env python3
"""
JADE Inference Tester - Tests JADE's diagnostic and remediation capabilities

Flow:
1. Load faulty document/log
2. JADE identifies the problem
3. JADE provides the fix (YAML, commands, or NPC call)
4. JADE provides steps to correct
5. JADE provides confirmation plan

Usage:
    python jade_inference_tester.py --model jade:v0.8 --test-dir FAULTY
    python jade_inference_tester.py --model jade:v0.8 --file FAULTY/pod-crashloop.log
    python jade_inference_tester.py --model jade:v0.8 --interactive
"""

import os
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
import re

# Directory setup
SCRIPT_DIR = Path(__file__).parent
FAULTY_DIR = SCRIPT_DIR / "FAULTY"
RESULTS_DIR = SCRIPT_DIR / "inference-results"
NPC_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-CONSULTING/1-Security-Assessment/npcs")

# Available NPCs for JADE to recommend
AVAILABLE_NPCS = {
    "secrets": ["GitleaksNPC"],
    "sast": ["BanditNPC", "SemgrepNPC"],
    "dependencies": ["TrivyNPC", "GrypeNPC", "SnykNPC"],
    "kubernetes": ["KubescapeNPC", "PolarisNPC", "KubeBenchNPC"],
    "iac": ["CheckovNPC", "TfsecNPC"]
}

@dataclass
class InferenceTestCase:
    """Single test case for JADE inference"""
    id: str
    category: str  # logs, k8s, terraform, rego, helm, docker
    input_file: str
    input_content: str
    expected_fix_file: Optional[str] = None  # Path to FIXED version if exists
    expected_fix_content: Optional[str] = None
    severity: str = "UNKNOWN"

@dataclass
class JADEResponse:
    """Structured response from JADE"""
    problem_identification: str
    root_cause: str
    severity_assessment: str
    fix_type: str  # yaml, command, npc, script
    fix_content: str
    steps_to_correct: List[str]
    confirmation_plan: List[str]
    recommended_npcs: List[str]
    raw_response: str

@dataclass
class TestResult:
    """Result of a single inference test"""
    test_case: InferenceTestCase
    jade_response: JADEResponse
    scores: Dict[str, float]
    passed: bool
    timestamp: str

def categorize_file(filepath: Path) -> str:
    """Determine category based on file extension/content"""
    suffix = filepath.suffix.lower()
    name = filepath.name.lower()

    if filepath.parent.name == "00-logs" or ".log" in name:
        return "logs"
    elif ".rego" in name:
        return "rego"
    elif ".tf" in name:
        return "terraform"
    elif "helm" in str(filepath).lower() or "chart" in str(filepath).lower():
        return "helm"
    elif "dockerfile" in name or "docker-compose" in name:
        return "docker"
    elif suffix in [".yaml", ".yml"]:
        return "k8s"
    else:
        return "unknown"

def detect_severity(content: str) -> str:
    """Detect severity from content markers"""
    content_lower = content.lower()
    if "critical" in content_lower:
        return "CRITICAL"
    elif "high" in content_lower:
        return "HIGH"
    elif "medium" in content_lower:
        return "MEDIUM"
    elif "low" in content_lower:
        return "LOW"
    return "UNKNOWN"

def load_test_cases(faulty_dir: Path) -> List[InferenceTestCase]:
    """Load all test cases from FAULTY directory"""
    test_cases = []

    for item in faulty_dir.rglob("*"):
        if item.is_file() and not item.name.startswith("."):
            # Skip FIXED files and non-test files
            if "-FIXED" in item.name or item.suffix in [".jsonl", ".md"]:
                continue

            content = item.read_text(errors='ignore')
            category = categorize_file(item)
            severity = detect_severity(content)

            # Check for corresponding FIXED file
            fixed_file = None
            fixed_content = None

            # Try different FIXED file patterns
            possible_fixed = [
                item.with_name(item.name.replace("-FAULTY", "-FIXED")),
                item.with_name(item.stem + "-FIXED" + item.suffix),
                item.parent / (item.stem.replace("-FAULTY", "") + "-FIXED" + item.suffix)
            ]

            for pf in possible_fixed:
                if pf.exists():
                    fixed_file = str(pf)
                    fixed_content = pf.read_text(errors='ignore')
                    break

            test_case = InferenceTestCase(
                id=item.stem,
                category=category,
                input_file=str(item),
                input_content=content,
                expected_fix_file=fixed_file,
                expected_fix_content=fixed_content,
                severity=severity
            )
            test_cases.append(test_case)

    return test_cases

def build_jade_prompt(test_case: InferenceTestCase) -> str:
    """Build the inference prompt for JADE"""

    prompt = f"""You are JADE, a security-focused DevSecOps AI. Analyze the following {test_case.category} configuration/log and provide a structured remediation plan.

## INPUT ({test_case.category.upper()})

```
{test_case.input_content[:4000]}
```

## REQUIRED OUTPUT FORMAT

Provide your analysis in this EXACT format:

### 1. PROBLEM IDENTIFICATION
[What is wrong with this configuration/log? Be specific.]

### 2. ROOT CAUSE
[Why does this problem exist? What's the underlying issue?]

### 3. SEVERITY ASSESSMENT
[CRITICAL/HIGH/MEDIUM/LOW - and why]

### 4. FIX TYPE
[One of: YAML_PATCH, IMPERATIVE_COMMAND, NPC_SCAN, SCRIPT]

### 5. THE FIX
[Provide the exact fix - corrected YAML, kubectl commands, or NPC invocation]
```
[your fix here]
```

### 6. STEPS TO CORRECT
1. [Step 1]
2. [Step 2]
3. [Step 3]
...

### 7. CONFIRMATION PLAN
[How to verify the fix worked]
1. [Verification step 1]
2. [Verification step 2]
...

### 8. RECOMMENDED NPCs
[Which GP-Copilot NPCs should be run to prevent/detect this in future?]
Available: GitleaksNPC, BanditNPC, SemgrepNPC, TrivyNPC, KubescapeNPC, PolarisNPC, CheckovNPC

---
Now analyze the input and provide your structured response:
"""
    return prompt

def call_jade(prompt: str, model: str = "jade:v0.8", timeout: int = 120) -> str:
    """Call JADE via Ollama and get response"""
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
        return "ERROR: JADE response timeout"
    except Exception as e:
        return f"ERROR: {str(e)}"

def parse_jade_response(raw_response: str) -> JADEResponse:
    """Parse JADE's structured response"""

    # Default values
    problem = ""
    root_cause = ""
    severity = "UNKNOWN"
    fix_type = "unknown"
    fix_content = ""
    steps = []
    confirmation = []
    npcs = []

    # Extract sections using regex
    sections = {
        "problem": r"### 1\. PROBLEM IDENTIFICATION\n(.*?)(?=### 2|$)",
        "root_cause": r"### 2\. ROOT CAUSE\n(.*?)(?=### 3|$)",
        "severity": r"### 3\. SEVERITY ASSESSMENT\n(.*?)(?=### 4|$)",
        "fix_type": r"### 4\. FIX TYPE\n(.*?)(?=### 5|$)",
        "fix": r"### 5\. THE FIX\n(.*?)(?=### 6|$)",
        "steps": r"### 6\. STEPS TO CORRECT\n(.*?)(?=### 7|$)",
        "confirmation": r"### 7\. CONFIRMATION PLAN\n(.*?)(?=### 8|$)",
        "npcs": r"### 8\. RECOMMENDED NPCs\n(.*?)(?=---|$)"
    }

    for key, pattern in sections.items():
        match = re.search(pattern, raw_response, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1).strip()

            if key == "problem":
                problem = content
            elif key == "root_cause":
                root_cause = content
            elif key == "severity":
                # Extract severity level
                for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                    if level in content.upper():
                        severity = level
                        break
            elif key == "fix_type":
                fix_type = content.split()[0] if content else "unknown"
            elif key == "fix":
                # Extract code block
                code_match = re.search(r"```[\w]*\n(.*?)```", content, re.DOTALL)
                fix_content = code_match.group(1) if code_match else content
            elif key == "steps":
                steps = [s.strip() for s in re.findall(r"\d+\.\s*(.+)", content)]
            elif key == "confirmation":
                confirmation = [s.strip() for s in re.findall(r"\d+\.\s*(.+)", content)]
            elif key == "npcs":
                # Find NPC names
                for npc_list in AVAILABLE_NPCS.values():
                    for npc in npc_list:
                        if npc.lower() in content.lower():
                            npcs.append(npc)

    return JADEResponse(
        problem_identification=problem,
        root_cause=root_cause,
        severity_assessment=severity,
        fix_type=fix_type,
        fix_content=fix_content,
        steps_to_correct=steps,
        confirmation_plan=confirmation,
        recommended_npcs=list(set(npcs)),
        raw_response=raw_response
    )

def score_response(test_case: InferenceTestCase, response: JADEResponse) -> Dict[str, float]:
    """Score JADE's response"""
    scores = {}

    # 1. Problem identification (0-1)
    scores["problem_identified"] = 1.0 if len(response.problem_identification) > 50 else 0.5 if len(response.problem_identification) > 20 else 0.0

    # 2. Root cause analysis (0-1)
    scores["root_cause_quality"] = 1.0 if len(response.root_cause) > 30 else 0.5 if len(response.root_cause) > 10 else 0.0

    # 3. Severity accuracy (0-1)
    if test_case.severity != "UNKNOWN":
        scores["severity_accuracy"] = 1.0 if response.severity_assessment == test_case.severity else 0.0
    else:
        scores["severity_accuracy"] = 0.5  # Neutral if no expected severity

    # 4. Fix provided (0-1)
    scores["fix_provided"] = 1.0 if len(response.fix_content) > 20 else 0.0

    # 5. Fix quality - compare to expected if available (0-1)
    if test_case.expected_fix_content:
        # Check for key patterns from expected fix
        expected_lower = test_case.expected_fix_content.lower()
        fix_lower = response.fix_content.lower()

        # Count matching security patterns
        security_patterns = [
            "runasnonroot", "privileged: false", "readonlyrootfilesystem",
            "allowprivilegeescalation: false", "drop", "capabilities",
            "resources:", "limits:", "requests:", "securitycontext",
            "livenessprobe", "readinessprobe"
        ]

        matches = sum(1 for p in security_patterns if p in fix_lower and p in expected_lower)
        total_expected = sum(1 for p in security_patterns if p in expected_lower)

        scores["fix_quality"] = matches / total_expected if total_expected > 0 else 0.5
    else:
        scores["fix_quality"] = 0.5  # Neutral if no expected fix

    # 6. Steps provided (0-1)
    scores["steps_provided"] = min(1.0, len(response.steps_to_correct) / 3)

    # 7. Confirmation plan (0-1)
    scores["confirmation_plan"] = min(1.0, len(response.confirmation_plan) / 2)

    # 8. NPC recommendations (0-1)
    scores["npc_recommendations"] = 1.0 if len(response.recommended_npcs) >= 1 else 0.0

    # Overall score
    scores["overall"] = sum(scores.values()) / len(scores)

    return scores

def run_single_test(test_case: InferenceTestCase, model: str) -> TestResult:
    """Run a single inference test"""
    print(f"\n{'='*60}")
    print(f"Testing: {test_case.id}")
    print(f"Category: {test_case.category}")
    print(f"{'='*60}")

    # Build prompt and call JADE
    prompt = build_jade_prompt(test_case)
    raw_response = call_jade(prompt, model)

    # Parse response
    response = parse_jade_response(raw_response)

    # Score response
    scores = score_response(test_case, response)

    # Determine pass/fail (>0.6 overall = pass)
    passed = scores["overall"] >= 0.6

    result = TestResult(
        test_case=test_case,
        jade_response=response,
        scores=scores,
        passed=passed,
        timestamp=datetime.now().isoformat()
    )

    # Print summary
    print(f"\nProblem: {response.problem_identification[:100]}...")
    print(f"Severity: {response.severity_assessment}")
    print(f"Fix Type: {response.fix_type}")
    print(f"Steps: {len(response.steps_to_correct)}")
    print(f"NPCs: {', '.join(response.recommended_npcs) or 'None'}")
    print(f"\nScores:")
    for k, v in scores.items():
        print(f"  {k}: {v:.2f}")
    print(f"\nRESULT: {'PASS' if passed else 'FAIL'} ({scores['overall']:.2%})")

    return result

def run_interactive(model: str):
    """Interactive mode - paste content and get JADE analysis"""
    print("\n" + "="*60)
    print("JADE Inference Tester - Interactive Mode")
    print("="*60)
    print(f"Model: {model}")
    print("Paste your faulty config/log, then type 'END' on a new line.")
    print("Type 'quit' to exit.\n")

    while True:
        print("\n> Enter content to analyze:")
        lines = []
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            if line.strip().lower() == "quit":
                print("Goodbye!")
                return
            lines.append(line)

        content = "\n".join(lines)
        if not content.strip():
            print("No content provided.")
            continue

        # Create test case
        test_case = InferenceTestCase(
            id="interactive",
            category="unknown",
            input_file="<stdin>",
            input_content=content,
            severity=detect_severity(content)
        )

        # Run test
        result = run_single_test(test_case, model)

        # Show full response
        print("\n" + "="*60)
        print("JADE's Full Response:")
        print("="*60)
        print(result.jade_response.raw_response)

def main():
    parser = argparse.ArgumentParser(description="JADE Inference Tester")
    parser.add_argument("--model", default="jade:v0.8", help="JADE model to test")
    parser.add_argument("--test-dir", type=Path, default=FAULTY_DIR, help="Directory with test files")
    parser.add_argument("--file", type=Path, help="Single file to test")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--category", help="Filter by category: logs, k8s, terraform, rego, helm, docker")
    parser.add_argument("--limit", type=int, help="Limit number of tests")
    parser.add_argument("--output", type=Path, help="Output results file")

    args = parser.parse_args()

    # Create results directory
    RESULTS_DIR.mkdir(exist_ok=True)

    if args.interactive:
        run_interactive(args.model)
        return

    if args.file:
        # Single file test
        content = args.file.read_text()
        test_case = InferenceTestCase(
            id=args.file.stem,
            category=categorize_file(args.file),
            input_file=str(args.file),
            input_content=content,
            severity=detect_severity(content)
        )
        result = run_single_test(test_case, args.model)
        results = [result]
    else:
        # Load all test cases
        print(f"Loading test cases from: {args.test_dir}")
        test_cases = load_test_cases(args.test_dir)

        # Filter by category if specified
        if args.category:
            test_cases = [tc for tc in test_cases if tc.category == args.category]

        # Limit if specified
        if args.limit:
            test_cases = test_cases[:args.limit]

        print(f"Found {len(test_cases)} test cases")

        # Run tests
        results = []
        for tc in test_cases:
            result = run_single_test(tc, args.model)
            results.append(result)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print(f"Total: {total}")
    print(f"Passed: {passed} ({passed/total:.1%})")
    print(f"Failed: {total - passed} ({(total-passed)/total:.1%})")

    # Category breakdown
    by_category = {}
    for r in results:
        cat = r.test_case.category
        if cat not in by_category:
            by_category[cat] = {"passed": 0, "total": 0}
        by_category[cat]["total"] += 1
        if r.passed:
            by_category[cat]["passed"] += 1

    print("\nBy Category:")
    for cat, stats in sorted(by_category.items()):
        pct = stats["passed"] / stats["total"] * 100
        print(f"  {cat}: {stats['passed']}/{stats['total']} ({pct:.0f}%)")

    # Average scores
    print("\nAverage Scores:")
    all_scores = {}
    for r in results:
        for k, v in r.scores.items():
            if k not in all_scores:
                all_scores[k] = []
            all_scores[k].append(v)

    for k, v in sorted(all_scores.items()):
        avg = sum(v) / len(v)
        print(f"  {k}: {avg:.2f}")

    # Save results
    output_file = args.output or RESULTS_DIR / f"inference_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    with open(output_file, "w") as f:
        for r in results:
            record = {
                "test_id": r.test_case.id,
                "category": r.test_case.category,
                "passed": r.passed,
                "scores": r.scores,
                "problem": r.jade_response.problem_identification[:200],
                "severity": r.jade_response.severity_assessment,
                "fix_type": r.jade_response.fix_type,
                "steps_count": len(r.jade_response.steps_to_correct),
                "npcs": r.jade_response.recommended_npcs,
                "timestamp": r.timestamp
            }
            f.write(json.dumps(record) + "\n")

    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()
