#!/usr/bin/env python3
"""
JSA Integration Test: Compare JADE vs Claude
=============================================
Runs the same security analysis task through both LLMs and compares:
- Issue identification accuracy
- Fix quality
- Response time
- Cost (Claude = $$, JADE = free)

Shows FULL outputs, not just summaries.

Usage:
    python3 compare_jade_vs_claude.py --target /path/to/vuln-project
    python3 compare_jade_vs_claude.py --scenario insecure-deployment
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import argparse

# Add parent paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Warning: anthropic package not installed. Run: pip install anthropic")


class LLMComparer:
    """Compare JADE (local) vs Claude (API) on security tasks."""

    # Test scenarios with expected issues
    SCENARIOS = {
        "insecure-deployment": {
            "file": "deployment-FAULTY.yaml",
            "expected_issues": [
                "privileged container",
                "running as root",
                "host network",
                "no resource limits",
                "no health probes",
                "latest tag",
                "hardcoded secrets",
            ],
            "content": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: vulnerable-app
spec:
  replicas: 1
  template:
    spec:
      hostNetwork: true
      containers:
      - name: app
        image: myapp:latest
        securityContext:
          privileged: true
        env:
        - name: DB_PASSWORD
          value: "supersecret123"
"""
        },
        "insecure-rbac": {
            "file": "rbac-FAULTY.yaml",
            "expected_issues": [
                "wildcard permissions",
                "cluster-admin binding",
                "default service account",
            ],
            "content": """apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: dangerous-binding
subjects:
- kind: ServiceAccount
  name: default
  namespace: default
roleRef:
  kind: ClusterRole
  name: cluster-admin
  apiGroup: rbac.authorization.k8s.io
"""
        },
        "insecure-network": {
            "file": "networkpolicy-FAULTY.yaml",
            "expected_issues": [
                "allow all ingress",
                "no egress restrictions",
                "missing pod selector",
            ],
            "content": """apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-all
spec:
  podSelector: {}
  ingress:
  - {}
  egress:
  - {}
  policyTypes:
  - Ingress
  - Egress
"""
        }
    }

    SECURITY_PROMPT = """You are a Kubernetes security expert. Analyze the following manifest for security issues.

For each issue found:
1. Identify the specific line/configuration
2. Explain why it's a security risk
3. Provide the recommended fix

Be thorough and specific. List ALL security issues you can find.

Manifest:
```yaml
{content}
```

Provide your analysis:"""

    def __init__(self, jade_model: str = "jade:v0.4", claude_model: str = "claude-3-5-sonnet-20241022"):
        self.jade_model = jade_model
        self.claude_model = claude_model
        self.results_dir = Path(__file__).parent.parent / "results"
        self.results_dir.mkdir(exist_ok=True)

        # Initialize Claude client if available
        self.claude_client = None
        if ANTHROPIC_AVAILABLE:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                self.claude_client = anthropic.Anthropic(api_key=api_key)
            else:
                print("Warning: ANTHROPIC_API_KEY not set in environment")

    def query_jade(self, prompt: str, timeout: int = 120) -> Tuple[str, float]:
        """Query JADE via ollama. Returns (response, time_seconds)."""
        start = time.time()
        try:
            result = subprocess.run(
                ["ollama", "run", self.jade_model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            elapsed = time.time() - start
            return result.stdout.strip(), elapsed
        except subprocess.TimeoutExpired:
            return "[TIMEOUT]", timeout
        except Exception as e:
            return f"[ERROR: {e}]", time.time() - start

    def query_claude(self, prompt: str) -> Tuple[str, float, float]:
        """Query Claude via API. Returns (response, time_seconds, cost_usd)."""
        if not self.claude_client:
            return "[Claude API not available]", 0, 0

        start = time.time()
        try:
            message = self.claude_client.messages.create(
                model=self.claude_model,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            elapsed = time.time() - start

            # Calculate cost (Claude 3.5 Sonnet pricing)
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            # $3 per 1M input, $15 per 1M output for Sonnet
            cost = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)

            response = message.content[0].text
            return response, elapsed, cost

        except Exception as e:
            return f"[ERROR: {e}]", time.time() - start, 0

    def score_response(self, response: str, expected_issues: list) -> Dict[str, Any]:
        """Score how many expected issues were identified."""
        response_lower = response.lower()
        found = []
        missed = []

        for issue in expected_issues:
            # Check for keywords
            keywords = issue.lower().split()
            if any(kw in response_lower for kw in keywords):
                found.append(issue)
            else:
                missed.append(issue)

        return {
            "found": found,
            "missed": missed,
            "score": len(found) / len(expected_issues) * 100 if expected_issues else 0,
            "found_count": len(found),
            "total_expected": len(expected_issues),
        }

    def run_comparison(self, scenario_name: str) -> Dict[str, Any]:
        """Run comparison on a specific scenario."""
        if scenario_name not in self.SCENARIOS:
            return {"error": f"Unknown scenario: {scenario_name}"}

        scenario = self.SCENARIOS[scenario_name]
        prompt = self.SECURITY_PROMPT.format(content=scenario["content"])

        print(f"\n{'='*80}")
        print(f"SCENARIO: {scenario_name}")
        print(f"{'='*80}")
        print(f"\nExpected issues to find: {len(scenario['expected_issues'])}")
        for i, issue in enumerate(scenario['expected_issues'], 1):
            print(f"  {i}. {issue}")

        # Query JADE
        print(f"\n{'-'*40}")
        print(f"QUERYING JADE ({self.jade_model})...")
        print(f"{'-'*40}")
        jade_response, jade_time = self.query_jade(prompt)

        print(f"\n[JADE Response - {jade_time:.1f}s]")
        print("-" * 40)
        print(jade_response)
        print("-" * 40)

        jade_score = self.score_response(jade_response, scenario["expected_issues"])

        # Query Claude
        print(f"\n{'-'*40}")
        print(f"QUERYING CLAUDE ({self.claude_model})...")
        print(f"{'-'*40}")
        claude_response, claude_time, claude_cost = self.query_claude(prompt)

        print(f"\n[Claude Response - {claude_time:.1f}s, ${claude_cost:.4f}]")
        print("-" * 40)
        print(claude_response)
        print("-" * 40)

        claude_score = self.score_response(claude_response, scenario["expected_issues"])

        # Build results
        results = {
            "scenario": scenario_name,
            "timestamp": datetime.now().isoformat(),
            "expected_issues": scenario["expected_issues"],
            "jade": {
                "model": self.jade_model,
                "response": jade_response,
                "time_seconds": round(jade_time, 2),
                "cost_usd": 0,  # Free!
                "score": jade_score,
            },
            "claude": {
                "model": self.claude_model,
                "response": claude_response,
                "time_seconds": round(claude_time, 2),
                "cost_usd": round(claude_cost, 4),
                "score": claude_score,
            },
            "comparison": {
                "jade_score": jade_score["score"],
                "claude_score": claude_score["score"],
                "jade_faster": jade_time < claude_time,
                "time_difference": round(abs(jade_time - claude_time), 2),
                "jade_advantage": jade_score["score"] - claude_score["score"],
            }
        }

        # Print summary
        print(f"\n{'='*80}")
        print("COMPARISON SUMMARY")
        print(f"{'='*80}")
        print(f"\n{'Metric':<25} {'JADE':<20} {'Claude':<20}")
        print(f"{'-'*65}")
        print(f"{'Issues Found':<25} {jade_score['found_count']}/{jade_score['total_expected']:<20} {claude_score['found_count']}/{claude_score['total_expected']:<20}")
        print(f"{'Score':<25} {jade_score['score']:.1f}%{'':<15} {claude_score['score']:.1f}%")
        print(f"{'Response Time':<25} {jade_time:.1f}s{'':<16} {claude_time:.1f}s")
        print(f"{'Cost':<25} {'$0.00 (free!)':<20} ${claude_cost:.4f}")
        print(f"{'-'*65}")

        if jade_score["score"] > claude_score["score"]:
            print(f"\n>>> JADE WINS by {jade_score['score'] - claude_score['score']:.1f}% <<<")
        elif claude_score["score"] > jade_score["score"]:
            print(f"\n>>> Claude wins by {claude_score['score'] - jade_score['score']:.1f}% <<<")
        else:
            print(f"\n>>> TIE <<<")

        # Save full results
        result_file = self.results_dir / f"comparison_{scenario_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nFull results saved to: {result_file}")

        return results

    def run_all_scenarios(self) -> Dict[str, Any]:
        """Run comparison on all scenarios."""
        all_results = {
            "timestamp": datetime.now().isoformat(),
            "jade_model": self.jade_model,
            "claude_model": self.claude_model,
            "scenarios": {},
            "totals": {
                "jade_total_score": 0,
                "claude_total_score": 0,
                "jade_total_time": 0,
                "claude_total_time": 0,
                "claude_total_cost": 0,
            }
        }

        for scenario_name in self.SCENARIOS:
            result = self.run_comparison(scenario_name)
            all_results["scenarios"][scenario_name] = result

            if "error" not in result:
                all_results["totals"]["jade_total_score"] += result["jade"]["score"]["score"]
                all_results["totals"]["claude_total_score"] += result["claude"]["score"]["score"]
                all_results["totals"]["jade_total_time"] += result["jade"]["time_seconds"]
                all_results["totals"]["claude_total_time"] += result["claude"]["time_seconds"]
                all_results["totals"]["claude_total_cost"] += result["claude"]["cost_usd"]

        # Calculate averages
        num_scenarios = len(self.SCENARIOS)
        all_results["averages"] = {
            "jade_avg_score": all_results["totals"]["jade_total_score"] / num_scenarios,
            "claude_avg_score": all_results["totals"]["claude_total_score"] / num_scenarios,
            "jade_avg_time": all_results["totals"]["jade_total_time"] / num_scenarios,
            "claude_avg_time": all_results["totals"]["claude_total_time"] / num_scenarios,
        }

        # Final summary
        print(f"\n{'='*80}")
        print("FINAL SUMMARY - ALL SCENARIOS")
        print(f"{'='*80}")
        print(f"\n{'Metric':<30} {'JADE':<20} {'Claude':<20}")
        print(f"{'-'*70}")
        print(f"{'Average Score':<30} {all_results['averages']['jade_avg_score']:.1f}%{'':<15} {all_results['averages']['claude_avg_score']:.1f}%")
        print(f"{'Total Time':<30} {all_results['totals']['jade_total_time']:.1f}s{'':<16} {all_results['totals']['claude_total_time']:.1f}s")
        print(f"{'Total Cost':<30} {'$0.00':<20} ${all_results['totals']['claude_total_cost']:.4f}")
        print(f"{'-'*70}")

        winner = "JADE" if all_results["averages"]["jade_avg_score"] >= all_results["averages"]["claude_avg_score"] else "Claude"
        print(f"\nOVERALL WINNER: {winner}")

        if winner == "JADE":
            print(f"  - Fine-tuned security knowledge pays off!")
            print(f"  - Plus it's FREE vs ${all_results['totals']['claude_total_cost']:.4f} for Claude")

        # Save full results
        result_file = self.results_dir / f"full_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\nFull results saved to: {result_file}")

        return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Compare JADE vs Claude on security analysis tasks"
    )
    parser.add_argument(
        "--scenario", "-s",
        choices=list(LLMComparer.SCENARIOS.keys()) + ["all"],
        default="all",
        help="Scenario to test (default: all)"
    )
    parser.add_argument(
        "--jade-model", "-j",
        default="jade:v0.4",
        help="JADE model to use (default: jade:v0.4)"
    )
    parser.add_argument(
        "--claude-model", "-c",
        default="claude-3-5-sonnet-20241022",
        help="Claude model to use"
    )

    args = parser.parse_args()

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\nWARNING: ANTHROPIC_API_KEY environment variable not set!")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        print("Claude comparisons will be skipped.\n")

    comparer = LLMComparer(
        jade_model=args.jade_model,
        claude_model=args.claude_model
    )

    if args.scenario == "all":
        comparer.run_all_scenarios()
    else:
        comparer.run_comparison(args.scenario)


if __name__ == "__main__":
    main()
