#!/usr/bin/env python3
"""
GuidePoint Domain Benchmark: JADE vs Haiku

Compares jade:v1.0 against claude-3-haiku on:
1. Domain knowledge (OPA, K8s, IaC, CI/CD)
2. Operational knowledge (GP-CONSULTING NPCs and workflows)

The key test: Does the model know HOW to use GP-CONSULTING tools?
JADE should know this from training. Haiku gets context but has to learn on the fly.

Usage:
    # Run full benchmark (both question sets)
    python3 run_benchmark.py

    # Run only operational questions (NPC knowledge)
    python3 run_benchmark.py --operational-only

    # Run only domain questions (generic knowledge)
    python3 run_benchmark.py --domain-only

    # Limit questions
    python3 run_benchmark.py --limit 5
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("Installing requests...")
    os.system("pip install requests")
    import requests

try:
    import anthropic
except ImportError:
    print("Installing anthropic...")
    os.system("pip install anthropic")
    import anthropic


SCRIPT_DIR = Path(__file__).parent
DOMAIN_QUESTIONS_FILE = SCRIPT_DIR / "guidepoint_questions.json"
OPERATIONAL_QUESTIONS_FILE = SCRIPT_DIR / "operational_questions.json"
RESULTS_DIR = SCRIPT_DIR / "results"


# GP-CONSULTING NPC Inventory - provided to both models for fairness
# But JADE should already know this from training!
GP_CONSULTING_CONTEXT = """
You are JSA (JADE Secure Agent), a 24/7 DevSecOps automation agent.

You have access to GP-CONSULTING toolkit organized in phases:

## Phase 1: Scanner NPCs (GP-CONSULTING/1-Security-Assessment/npcs/)
- secrets/gitleaks_npc.py - Detect hardcoded secrets
- sast/bandit_npc.py - Python SAST
- sast/semgrep_npc.py - Multi-language SAST
- dependencies/trivy_npc.py - Container/SCA scanning
- dependencies/grype_npc.py - Vulnerability scanning
- dependencies/snyk_npc.py - Commercial SCA
- kubernetes/kube_bench_npc.py - CIS benchmarks for K8s
- kubernetes/kubescape_npc.py - K8s security posture
- kubernetes/polaris_npc.py - K8s best practices
- iac/checkov_npc.py - Terraform/CloudFormation
- iac/tfsec_npc.py - Terraform security
- iac/conftest_npc.py - OPA policy testing
- cloud/prowler_npc.py - AWS security auditing
- diagnostics/kubectl_diagnostics_npc.py - K8s diagnostics
- diagnostics/log_watcher_npc.py - Real-time log monitoring

## Phase 2: Fixer NPCs (GP-CONSULTING/2-App-Sec-Fixes/npcs/)
- secrets/secrets_fixer_npc.py - Remove secrets, update .gitignore
- sast/code_fixer_npc.py - Fix SAST findings
- dependencies/dependency_fixer_npc.py - Upgrade vulnerable packages
- kubernetes/kubernetes_fixer_npc.py - Fix K8s misconfigs
- kubernetes/network_policy_generator_npc.py - Generate NetworkPolicies
- gha/gha_scanner_npc.py - Scan GitHub Actions workflows
- gha/gha_fixer_npc.py - Fix GHA security issues
- gha/gha_template_npc.py - Secure workflow templates
- iac/conftest_fixer_npc.py - Fix OPA policy violations
- integrations/smart_rescan_npc.py - Verify fixes by rescanning

## Phase 3: Hardening NPCs (GP-CONSULTING/3-Hardening/npcs/)
- generators/gatekeeper_generator_npc.py - Generate Gatekeeper constraints
- generators/kyverno_generator_npc.py - Generate Kyverno policies
- generators/conftest_generator_npc.py - Generate Conftest policies
- policy/opa_policy_tester_npc.py - Test OPA/Rego policies
- policy/policy_mutator_npc.py - Generate policy mutations
- admission/gatekeeper_deployer_npc.py - Deploy Gatekeeper
- compliance/compliance_mapper_npc.py - Map to CIS/SOC2/PCI
- troubleshooting/k8s_troubleshooter_npc.py - Debug K8s issues
- sbom/syft_npc.py - Generate SBOM
- sbom/cyclonedx_npc.py - Generate CycloneDX SBOM

## Orchestrators
- ScanOrchestrator - Runs all scanner NPCs in parallel
- FixOrchestrator - Routes findings to appropriate fixer NPCs
- RankClassifier - Classifies findings as E/D/C/B/S rank

## Workflow
1. SCAN: ScanOrchestrator runs scanner NPCs
2. CLASSIFY: RankClassifier assigns ranks (E=auto-fix, C=needs approval, B/S=escalate)
3. FIX: FixOrchestrator runs appropriate fixer NPCs
4. VERIFY: SmartRescanNPC confirms fixes

## Integrations
- slack_approval_npc.py - C-rank approval workflow
- github_api_npc.py - Post results to PRs

## Response Format by Rank
When answering, consider the task's difficulty rank and respond accordingly:

**E-D Rank (Automated):** These tasks can be auto-fixed by JSA agents.
- Identify which specific JSA agent/NPC handles this
- Show the exact command or workflow that would be triggered
- Explain the automated fix

**C Rank (JADE Decides):** You decide using your RAG knowledge.
- Simulate the fix/approval process
- Show what actions you would take
- Explain your reasoning

**B-S Rank (Human Required):** Escalate with analysis.
- Provide parallel suggestion fixes
- Show prevention plan
- Explain why human judgment is needed

Answer questions by explaining which NPCs you would use and the workflow.
"""


class BenchmarkRunner:
    """Runs benchmark comparing JADE vs Haiku on GP-CONSULTING knowledge."""

    def __init__(
        self,
        jade_model: str = "jade:v1.0",
        haiku_model: str = "claude-3-haiku-20240307",
        ollama_url: str = "http://localhost:11434",
        verbose: bool = False,
        include_context: bool = True,
    ):
        self.jade_model = jade_model
        self.haiku_model = haiku_model
        self.ollama_url = ollama_url
        self.verbose = verbose
        self.include_context = include_context

        # Initialize Anthropic client
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if self.anthropic_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key)
        else:
            self.anthropic_client = None
            print("[WARN] ANTHROPIC_API_KEY not set - Haiku tests will be skipped")

        # Load questions
        self.domain_questions = self._load_questions(DOMAIN_QUESTIONS_FILE)
        self.operational_questions = self._load_questions(OPERATIONAL_QUESTIONS_FILE)

        # Results storage
        self.results = {
            "benchmark_name": "GuidePoint Domain + Operational Benchmark",
            "timestamp": datetime.now().isoformat(),
            "jade_model": jade_model,
            "haiku_model": haiku_model,
            "context_provided": include_context,
            "questions": [],
        }

    def _load_questions(self, filepath: Path) -> List[Dict]:
        """Load questions from JSON file."""
        if not filepath.exists():
            print(f"[WARN] Questions file not found: {filepath}")
            return []

        with open(filepath) as f:
            data = json.load(f)
            return data.get("questions", [])

    def _build_prompt(self, question: Dict, question_type: str) -> str:
        """Build prompt with optional GP-CONSULTING context."""
        if question_type == "operational":
            # Operational questions - always include context
            base_prompt = question.get("scenario", question.get("question", ""))
            return f"{GP_CONSULTING_CONTEXT}\n\n## Question\n{base_prompt}"
        else:
            # Domain questions - test raw knowledge
            if self.include_context:
                return f"{GP_CONSULTING_CONTEXT}\n\n## Question\n{question['question']}"
            else:
                return question["question"]

    def query_jade(self, prompt: str, timeout: int = 120) -> Dict[str, Any]:
        """Query jade:v0.8 via Ollama."""
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.jade_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 2000,
                    }
                },
                timeout=timeout,
            )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("response", ""),
                    "elapsed_seconds": elapsed,
                    "model": self.jade_model,
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "elapsed_seconds": elapsed,
                    "model": self.jade_model,
                }

        except requests.Timeout:
            return {
                "success": False,
                "error": f"Timeout after {timeout}s",
                "elapsed_seconds": timeout,
                "model": self.jade_model,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "elapsed_seconds": time.time() - start_time,
                "model": self.jade_model,
            }

    def query_haiku(self, prompt: str) -> Dict[str, Any]:
        """Query Claude Haiku via Anthropic API."""
        if not self.anthropic_client:
            return {
                "success": False,
                "error": "Anthropic client not initialized",
                "model": self.haiku_model,
            }

        start_time = time.time()

        try:
            response = self.anthropic_client.messages.create(
                model=self.haiku_model,
                max_tokens=2000,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            elapsed = time.time() - start_time

            return {
                "success": True,
                "response": response.content[0].text,
                "elapsed_seconds": elapsed,
                "model": self.haiku_model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "elapsed_seconds": time.time() - start_time,
                "model": self.haiku_model,
            }

    def run_question(self, question: Dict, question_type: str) -> Dict[str, Any]:
        """Run a single question against both models."""
        q_id = question.get("id", "unknown")
        domain = question.get("domain", "unknown")

        # Build prompt
        prompt = self._build_prompt(question, question_type)

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Question: {q_id} ({domain}) - {question_type}")
            print(f"{'='*60}")

        # Query JADE
        print(f"  [{q_id}] Querying JADE...", end=" ", flush=True)
        jade_result = self.query_jade(prompt)
        jade_status = "OK" if jade_result["success"] else "FAIL"
        print(f"{jade_status} ({jade_result.get('elapsed_seconds', 0):.1f}s)")

        if self.verbose and jade_result["success"]:
            print(f"  JADE: {jade_result['response'][:300]}...")

        # Query Haiku
        if self.anthropic_client:
            print(f"  [{q_id}] Querying Haiku...", end=" ", flush=True)
            haiku_result = self.query_haiku(prompt)
            haiku_status = "OK" if haiku_result["success"] else "FAIL"
            print(f"{haiku_status} ({haiku_result.get('elapsed_seconds', 0):.1f}s)")

            if self.verbose and haiku_result["success"]:
                print(f"  Haiku: {haiku_result['response'][:300]}...")
        else:
            haiku_result = {"success": False, "error": "Skipped", "model": self.haiku_model}
            print(f"  [{q_id}] Haiku: SKIPPED")

        return {
            "question_id": q_id,
            "question_type": question_type,
            "domain": domain,
            "prompt": prompt[:500] + "..." if len(prompt) > 500 else prompt,
            "expected_npcs": question.get("expected_npcs", question.get("expected_elements", [])),
            "expected_workflow": question.get("expected_workflow", ""),
            "scoring": question.get("scoring", question.get("scoring_rubric", {})),
            "jade_response": jade_result,
            "haiku_response": haiku_result,
        }

    def run_benchmark(
        self,
        operational_only: bool = False,
        domain_only: bool = False,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run the benchmark."""
        questions = []

        if not domain_only:
            for q in self.operational_questions:
                q["_type"] = "operational"
                questions.append(q)

        if not operational_only:
            for q in self.domain_questions:
                q["_type"] = "domain"
                questions.append(q)

        if limit:
            questions = questions[:limit]

        print(f"\n{'#'*60}")
        print(f"GuidePoint Security Domain Benchmark")
        print(f"JADE: {self.jade_model} vs Haiku: {self.haiku_model}")
        print(f"Questions: {len(questions)} ({len([q for q in questions if q['_type']=='operational'])} operational, {len([q for q in questions if q['_type']=='domain'])} domain)")
        print(f"Context provided to both: {self.include_context}")
        print(f"{'#'*60}\n")

        # Run questions
        for i, question in enumerate(questions, 1):
            q_type = question.pop("_type")
            print(f"\n[{i}/{len(questions)}] {question.get('id', 'unknown')}: {question.get('domain', 'unknown')}")
            result = self.run_question(question, q_type)
            self.results["questions"].append(result)

        # Calculate summary
        self.results["summary"] = self._calculate_summary()

        # Save results
        results_file = self._save_results()

        return self.results, results_file

    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics."""
        jade_success = sum(1 for q in self.results["questions"] if q["jade_response"]["success"])
        haiku_success = sum(1 for q in self.results["questions"] if q["haiku_response"]["success"])
        total = len(self.results["questions"])

        operational = [q for q in self.results["questions"] if q["question_type"] == "operational"]
        domain = [q for q in self.results["questions"] if q["question_type"] == "domain"]

        jade_times = [q["jade_response"]["elapsed_seconds"] for q in self.results["questions"] if q["jade_response"]["success"]]
        haiku_times = [q["haiku_response"]["elapsed_seconds"] for q in self.results["questions"] if q["haiku_response"]["success"]]

        return {
            "total_questions": total,
            "operational_questions": len(operational),
            "domain_questions": len(domain),
            "jade_success_rate": jade_success / total if total > 0 else 0,
            "haiku_success_rate": haiku_success / total if total > 0 else 0,
            "jade_avg_time": sum(jade_times) / len(jade_times) if jade_times else 0,
            "haiku_avg_time": sum(haiku_times) / len(haiku_times) if haiku_times else 0,
            "domains_tested": list(set(q["domain"] for q in self.results["questions"])),
        }

    def _save_results(self) -> Path:
        """Save results to JSON file."""
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = RESULTS_DIR / f"benchmark_{timestamp}.json"

        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\n{'='*60}")
        print(f"Results saved to: {results_file}")
        print(f"{'='*60}")

        summary = self.results["summary"]
        print(f"\nSUMMARY:")
        print(f"  Total: {summary['total_questions']} ({summary['operational_questions']} operational, {summary['domain_questions']} domain)")
        print(f"  JADE Success: {summary['jade_success_rate']*100:.0f}% (avg {summary['jade_avg_time']:.1f}s)")
        print(f"  Haiku Success: {summary['haiku_success_rate']*100:.0f}% (avg {summary['haiku_avg_time']:.1f}s)")
        print(f"\nNext: Run 'python3 judge_results.py {results_file}' to have Claude Code evaluate responses")

        return results_file


def main():
    parser = argparse.ArgumentParser(description="GuidePoint Domain Benchmark")
    parser.add_argument("--jade-model", default="jade:v1.0", help="JADE model name")
    parser.add_argument("--haiku-model", default="claude-3-haiku-20240307", help="Haiku model")
    parser.add_argument("--operational-only", action="store_true", help="Only NPC knowledge questions")
    parser.add_argument("--domain-only", action="store_true", help="Only domain knowledge questions")
    parser.add_argument("--limit", type=int, help="Limit number of questions")
    parser.add_argument("--no-context", action="store_true", help="Don't provide GP-CONSULTING context")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama URL")

    args = parser.parse_args()

    runner = BenchmarkRunner(
        jade_model=args.jade_model,
        haiku_model=args.haiku_model,
        ollama_url=args.ollama_url,
        verbose=args.verbose,
        include_context=not args.no_context,
    )

    runner.run_benchmark(
        operational_only=args.operational_only,
        domain_only=args.domain_only,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
