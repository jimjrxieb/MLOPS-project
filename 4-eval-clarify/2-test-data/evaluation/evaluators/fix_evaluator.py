#!/usr/bin/env python3
"""
GP-CLARIFY: Fix Quality Evaluator
==================================
Tests JADE's ability to identify and fix security issues in FAULTY→FIXED pairs.

Workflow:
1. Load FAULTY YAML/Rego file
2. Ask JADE to identify issues
3. Compare identified issues to annotated issues
4. Ask JADE to produce a fix
5. Compare JADE's fix to the FIXED version
6. Score both identification and fix quality

Usage:
    python3 fix_evaluator.py --model jade:v0.4 --test-dir ../2-test-data/integration-tests/helm-charts/faulty-examples
    python3 fix_evaluator.py --model jade:v0.4 --single 01-insecure-deployment
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from difflib import SequenceMatcher
import argparse


class FixEvaluator:
    """Evaluate JADE's ability to identify and fix security issues."""

    # Known issue patterns to look for in FAULTY files (from comments)
    ISSUE_PATTERNS = [
        r"BUG\s*#?\d*:?\s*(.+?)(?:\n|$)",
        r"#\s*\d+\.\s*(.+?)(?:\n|$)",
        r"Issues?:\s*\n((?:\s*#?\s*\d+[.):]\s*.+\n)+)",
    ]

    # Security keywords that indicate issues were identified
    SECURITY_KEYWORDS = [
        "privileged", "root", "hostNetwork", "hostPID", "hostIPC",
        "capabilities", "allowPrivilegeEscalation", "securityContext",
        "runAsNonRoot", "runAsUser", "readOnlyRootFilesystem",
        "resources", "limits", "requests", "memory", "cpu",
        "livenessProbe", "readinessProbe", "healthcheck",
        "secret", "password", "credential", "hardcoded",
        "latest", "tag", "digest", "image",
        "affinity", "antiAffinity", "topology",
        "networkPolicy", "ingress", "egress",
    ]

    def __init__(self, model: str = "jade:v0.4", timeout: int = 120):
        self.model = model
        self.timeout = timeout
        self.results = []

    def load_faulty_fixed_pair(self, test_dir: Path) -> Tuple[str, str, List[str]]:
        """Load FAULTY and FIXED files from a test directory."""
        faulty_files = list(test_dir.glob("*-FAULTY.*"))
        fixed_files = list(test_dir.glob("*-FIXED.*"))

        if not faulty_files or not fixed_files:
            raise FileNotFoundError(f"Missing FAULTY or FIXED file in {test_dir}")

        faulty_path = faulty_files[0]
        fixed_path = fixed_files[0]

        with open(faulty_path) as f:
            faulty_content = f.read()

        with open(fixed_path) as f:
            fixed_content = f.read()

        # Extract expected issues from FAULTY file comments
        expected_issues = self._extract_expected_issues(faulty_content)

        return faulty_content, fixed_content, expected_issues

    def _extract_expected_issues(self, content: str) -> List[str]:
        """Extract annotated issues from FAULTY file comments."""
        issues = []

        for pattern in self.ISSUE_PATTERNS:
            matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                # Clean up the issue text
                issue = match.strip().strip('#').strip()
                if issue and len(issue) > 5:
                    issues.append(issue)

        return issues

    def ask_jade_identify(self, faulty_content: str) -> Tuple[str, List[str]]:
        """Ask JADE to identify security issues in the faulty content."""
        prompt = f"""Analyze the following Kubernetes manifest for security issues.
List each security issue you find with a brief explanation.
Be specific about what is wrong and why it's a security concern.

```yaml
{faulty_content}
```

Respond with a numbered list of issues found."""

        response = self._query_model(prompt)
        identified_issues = self._parse_identified_issues(response)

        return response, identified_issues

    def ask_jade_fix(self, faulty_content: str) -> str:
        """Ask JADE to fix the security issues."""
        prompt = f"""Fix all security issues in the following Kubernetes manifest.
Apply security best practices including:
- Non-root user
- Resource limits
- Security context
- Health probes
- No hardcoded secrets

Return ONLY the fixed YAML, no explanations.

```yaml
{faulty_content}
```"""

        response = self._query_model(prompt)
        return self._extract_yaml_from_response(response)

    def _query_model(self, prompt: str) -> str:
        """Query the JADE model via ollama."""
        try:
            result = subprocess.run(
                ["ollama", "run", self.model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return "[TIMEOUT]"
        except Exception as e:
            return f"[ERROR: {e}]"

    def _parse_identified_issues(self, response: str) -> List[str]:
        """Parse identified issues from JADE's response."""
        issues = []

        # Look for numbered items
        numbered = re.findall(r"^\s*\d+[.)]\s*(.+?)$", response, re.MULTILINE)
        issues.extend(numbered)

        # Look for bullet points
        bullets = re.findall(r"^\s*[-*]\s*(.+?)$", response, re.MULTILINE)
        issues.extend(bullets)

        return issues

    def _extract_yaml_from_response(self, response: str) -> str:
        """Extract YAML content from JADE's response."""
        # Try to find YAML code block
        yaml_match = re.search(r"```ya?ml?\n(.*?)```", response, re.DOTALL)
        if yaml_match:
            return yaml_match.group(1).strip()

        # If no code block, assume entire response is YAML
        # Remove any non-YAML preamble
        lines = response.split("\n")
        yaml_lines = []
        in_yaml = False

        for line in lines:
            if line.strip().startswith(("apiVersion:", "kind:", "metadata:")):
                in_yaml = True
            if in_yaml:
                yaml_lines.append(line)

        return "\n".join(yaml_lines) if yaml_lines else response

    def score_identification(self, expected: List[str], identified: List[str]) -> Dict[str, Any]:
        """Score how well JADE identified the expected issues."""
        if not expected:
            return {"score": 0, "reason": "No expected issues to compare"}

        # Check for keyword overlap
        expected_keywords = set()
        for issue in expected:
            for keyword in self.SECURITY_KEYWORDS:
                if keyword.lower() in issue.lower():
                    expected_keywords.add(keyword.lower())

        identified_keywords = set()
        for issue in identified:
            for keyword in self.SECURITY_KEYWORDS:
                if keyword.lower() in issue.lower():
                    identified_keywords.add(keyword.lower())

        if not expected_keywords:
            return {"score": 0.5, "reason": "Could not extract keywords from expected issues"}

        overlap = expected_keywords & identified_keywords
        precision = len(overlap) / len(identified_keywords) if identified_keywords else 0
        recall = len(overlap) / len(expected_keywords)
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "score": round(f1 * 100, 1),
            "precision": round(precision * 100, 1),
            "recall": round(recall * 100, 1),
            "expected_keywords": list(expected_keywords),
            "identified_keywords": list(identified_keywords),
            "overlap": list(overlap),
            "issues_expected": len(expected),
            "issues_identified": len(identified),
        }

    def score_fix_quality(self, expected_fix: str, jade_fix: str) -> Dict[str, Any]:
        """Score how well JADE's fix matches the expected fix."""
        if not jade_fix or jade_fix.startswith("["):
            return {"score": 0, "reason": "JADE did not produce a valid fix"}

        # Text similarity
        similarity = SequenceMatcher(None, expected_fix, jade_fix).ratio()

        # Check for key security improvements
        security_improvements = {
            "runAsNonRoot": "runAsNonRoot" in jade_fix,
            "runAsUser": "runAsUser" in jade_fix and "runAsUser: 0" not in jade_fix,
            "readOnlyRootFilesystem": "readOnlyRootFilesystem: true" in jade_fix,
            "allowPrivilegeEscalation": "allowPrivilegeEscalation: false" in jade_fix,
            "resources_limits": "limits:" in jade_fix and ("cpu:" in jade_fix or "memory:" in jade_fix),
            "no_privileged": "privileged: true" not in jade_fix,
            "no_hostNetwork": "hostNetwork: true" not in jade_fix,
            "has_probes": "livenessProbe" in jade_fix or "readinessProbe" in jade_fix,
            "no_latest_tag": ":latest" not in jade_fix.lower(),
            "secretRef": "secretKeyRef" in jade_fix or "secretRef" in jade_fix,
        }

        improvements_found = sum(security_improvements.values())
        improvements_total = len(security_improvements)

        # Combined score: 60% similarity, 40% security improvements
        combined_score = (similarity * 60) + (improvements_found / improvements_total * 40)

        return {
            "score": round(combined_score, 1),
            "text_similarity": round(similarity * 100, 1),
            "security_improvements": security_improvements,
            "improvements_found": improvements_found,
            "improvements_total": improvements_total,
        }

    def evaluate_single(self, test_dir: Path) -> Dict[str, Any]:
        """Evaluate JADE on a single FAULTY→FIXED pair."""
        test_name = test_dir.name
        print(f"\n{'='*60}")
        print(f"Evaluating: {test_name}")
        print(f"{'='*60}")

        try:
            faulty, fixed, expected_issues = self.load_faulty_fixed_pair(test_dir)
        except FileNotFoundError as e:
            return {"test": test_name, "error": str(e)}

        print(f"  Expected issues: {len(expected_issues)}")
        for i, issue in enumerate(expected_issues[:5], 1):
            print(f"    {i}. {issue[:60]}...")

        # Phase 1: Identification
        print("\n  Phase 1: Issue Identification...")
        jade_response, identified = self.ask_jade_identify(faulty)
        identification_score = self.score_identification(expected_issues, identified)
        print(f"    Identified: {len(identified)} issues")
        print(f"    Score: {identification_score['score']}%")

        # Phase 2: Fix Generation
        print("\n  Phase 2: Fix Generation...")
        jade_fix = self.ask_jade_fix(faulty)
        fix_score = self.score_fix_quality(fixed, jade_fix)
        print(f"    Text similarity: {fix_score.get('text_similarity', 0)}%")
        print(f"    Security improvements: {fix_score.get('improvements_found', 0)}/{fix_score.get('improvements_total', 0)}")
        print(f"    Combined score: {fix_score['score']}%")

        result = {
            "test": test_name,
            "timestamp": datetime.now().isoformat(),
            "model": self.model,
            "expected_issues": expected_issues,
            "identification": {
                "jade_response": jade_response[:500] + "..." if len(jade_response) > 500 else jade_response,
                "issues_found": identified,
                "score": identification_score,
            },
            "fix_generation": {
                "jade_fix_preview": jade_fix[:500] + "..." if len(jade_fix) > 500 else jade_fix,
                "score": fix_score,
            },
            "overall_score": round((identification_score["score"] + fix_score["score"]) / 2, 1),
        }

        self.results.append(result)
        return result

    def evaluate_all(self, test_base_dir: Path) -> List[Dict[str, Any]]:
        """Evaluate JADE on all FAULTY→FIXED pairs in a directory."""
        test_dirs = [d for d in test_base_dir.iterdir() if d.is_dir()]

        print(f"\nFound {len(test_dirs)} test cases")

        for test_dir in sorted(test_dirs):
            self.evaluate_single(test_dir)

        return self.results

    def generate_report(self) -> Dict[str, Any]:
        """Generate summary report of all evaluations."""
        if not self.results:
            return {"error": "No results to report"}

        valid_results = [r for r in self.results if "error" not in r]

        if not valid_results:
            return {"error": "All tests failed"}

        avg_overall = sum(r["overall_score"] for r in valid_results) / len(valid_results)
        avg_identification = sum(r["identification"]["score"]["score"] for r in valid_results) / len(valid_results)
        avg_fix = sum(r["fix_generation"]["score"]["score"] for r in valid_results) / len(valid_results)

        return {
            "timestamp": datetime.now().isoformat(),
            "model": self.model,
            "total_tests": len(self.results),
            "passed_tests": len(valid_results),
            "failed_tests": len(self.results) - len(valid_results),
            "average_scores": {
                "overall": round(avg_overall, 1),
                "identification": round(avg_identification, 1),
                "fix_quality": round(avg_fix, 1),
            },
            "grade": self._calculate_grade(avg_overall),
            "results": self.results,
        }

    def _calculate_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return "A (Excellent)"
        elif score >= 80:
            return "B (Good)"
        elif score >= 70:
            return "C (Satisfactory)"
        elif score >= 60:
            return "D (Needs Improvement)"
        else:
            return "F (Failing)"


def main():
    parser = argparse.ArgumentParser(
        description="GP-CLARIFY: Fix Quality Evaluator"
    )
    parser.add_argument(
        "--model", "-m",
        default="jade:v0.4",
        help="Model to evaluate (default: jade:v0.4)"
    )
    parser.add_argument(
        "--test-dir", "-t",
        default="../2-test-data/integration-tests/helm-charts/faulty-examples",
        help="Directory containing FAULTY→FIXED test pairs"
    )
    parser.add_argument(
        "--single", "-s",
        help="Evaluate single test case (subdirectory name)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output path for evaluation report (JSON)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout per query in seconds (default: 120)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("GP-CLARIFY: Fix Quality Evaluator")
    print("=" * 70)
    print(f"Model: {args.model}")
    print(f"Test directory: {args.test_dir}")

    evaluator = FixEvaluator(model=args.model, timeout=args.timeout)
    test_base = Path(args.test_dir)

    if args.single:
        # Single test case
        test_dir = test_base / args.single
        if not test_dir.exists():
            print(f"Error: Test case not found: {test_dir}")
            return 1
        evaluator.evaluate_single(test_dir)
    else:
        # All test cases
        evaluator.evaluate_all(test_base)

    # Generate report
    report = evaluator.generate_report()

    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"  Total tests: {report.get('total_tests', 0)}")
    print(f"  Passed: {report.get('passed_tests', 0)}")
    print(f"  Failed: {report.get('failed_tests', 0)}")
    print()
    print("  Average Scores:")
    avg = report.get("average_scores", {})
    print(f"    Overall:        {avg.get('overall', 0)}%")
    print(f"    Identification: {avg.get('identification', 0)}%")
    print(f"    Fix Quality:    {avg.get('fix_quality', 0)}%")
    print()
    print(f"  Grade: {report.get('grade', 'N/A')}")
    print("=" * 70)

    # Save report
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
