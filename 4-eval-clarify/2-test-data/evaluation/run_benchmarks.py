#!/usr/bin/env python3
"""
JADE Benchmark Runner

Runs knowledge and task benchmarks against JADE and generates a scorecard.

Usage:
    python run_benchmarks.py --category all
    python run_benchmarks.py --category cloud --category cks
    python run_benchmarks.py --task-only
    python run_benchmarks.py --knowledge-only
"""

import argparse
import json
import os
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


# Benchmark categories mapping
KNOWLEDGE_CATEGORIES = {
    "cloud": "01-cloud-benchmark",
    "cks": "02-cks-benchmark",
    "devsecops": "03-devsecops-benchmark",
    "compliance": "04-compliance-benchmark",
    "hardening": "05-hardening-benchmark",
    "incident-response": "06-incident-response-benchmark",
    "threat-modeling": "07-threat-modeling-benchmark",
}

TASK_CATEGORIES = {
    "fix-generation": "fix-generation",
    "policy-generation": "policy-generation",
    "classification": "classification",
}


class BenchmarkRunner:
    """Runs benchmarks against JADE model."""

    def __init__(self, jade_endpoint: str = None, jade_model: str = None,
                 results_dir: Path = None, model_path: str = None):
        self.jade_endpoint = jade_endpoint or os.environ.get("JADE_ENDPOINT", "http://localhost:11434")
        self.jade_model = jade_model or os.environ.get("JADE_MODEL", "jade:v1.0")
        self.results_dir = results_dir or Path(__file__).parent.parent.parent / "3-results"
        self.base_dir = Path(__file__).parent.parent

        # Local model support (bypasses Ollama)
        self.use_local = False
        self._local_model = None
        self._local_tokenizer = None
        if model_path:
            self._load_local_model(model_path)

    def _load_local_model(self, model_path: str):
        """Load a local HuggingFace model for inference."""
        from unsloth import FastLanguageModel

        print(f"[MODEL] Loading local model: {model_path}")
        self._local_model, self._local_tokenizer = FastLanguageModel.from_pretrained(
            model_name=model_path,
            max_seq_length=4096,
            dtype=None,
            load_in_4bit=True,
        )
        FastLanguageModel.for_inference(self._local_model)
        self.use_local = True
        self.jade_model = model_path
        print(f"  Loaded (4-bit quantized)")

    def _query_local(self, prompt: str) -> str:
        """Generate response from locally loaded model."""
        messages = [
            {"role": "system", "content": "You are JADE, a DevSecOps security expert. Output working code directly."},
            {"role": "user", "content": prompt},
        ]

        formatted = self._local_tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)

        inputs = self._local_tokenizer(formatted, return_tensors="pt").to(self._local_model.device)
        outputs = self._local_model.generate(
            **inputs,
            max_new_tokens=1024,
            temperature=0.3,
            top_p=0.9,
            do_sample=True,
            pad_token_id=self._local_tokenizer.eos_token_id,
        )
        generated = outputs[0][inputs["input_ids"].shape[1]:]
        return self._local_tokenizer.decode(generated, skip_special_tokens=True).strip()

    def load_questions(self, category: str) -> list[dict]:
        """Load all questions for a knowledge category."""
        category_dir = self.base_dir / "evaluation" / KNOWLEDGE_CATEGORIES.get(category, category)
        questions = []

        if not category_dir.exists():
            print(f"Warning: Category directory not found: {category_dir}")
            return questions

        for jsonl_file in category_dir.glob("*.jsonl"):
            with open(jsonl_file) as f:
                for line in f:
                    if line.strip():
                        questions.append(json.loads(line))

        return questions

    def load_task_tests(self, task_type: str) -> list[dict]:
        """Load all task tests for a task category."""
        task_dir = self.base_dir / "evaluation" / "task-tests" / TASK_CATEGORIES.get(task_type, task_type)
        tests = []

        if not task_dir.exists():
            print(f"Warning: Task directory not found: {task_dir}")
            return tests

        # Load input files
        for input_file in task_dir.rglob("input-*.json"):
            with open(input_file) as f:
                test = json.load(f)
                test["_input_path"] = str(input_file)

                # Find matching expected file
                expected_pattern = input_file.stem.replace("input-", "expected-")
                for ext in [".tf", ".py", ".yaml", ".json"]:
                    expected_path = input_file.parent / f"{expected_pattern}{ext}"
                    if expected_path.exists():
                        test["_expected_path"] = str(expected_path)
                        with open(expected_path) as ef:
                            test["_expected_content"] = ef.read()
                        break

                tests.append(test)

        # Load JSONL files (for classification)
        for jsonl_file in task_dir.rglob("*.jsonl"):
            with open(jsonl_file) as f:
                for line in f:
                    if line.strip():
                        tests.append(json.loads(line))

        return tests

    def query_jade(self, prompt: str) -> str:
        """Query JADE model and return response.

        Dispatches to local model if --model-path was provided,
        otherwise queries Ollama HTTP endpoint.
        """
        if self.use_local:
            return self._query_local(prompt)

        try:
            import requests

            response = requests.post(
                f"{self.jade_endpoint}/api/generate",
                json={
                    "model": self.jade_model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120,
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            print(f"Error querying JADE: {e}")
            return f"ERROR: {e}"

    def score_knowledge_response(self, question: dict, response: str) -> dict:
        """Score a knowledge question response."""
        result = {
            "id": question["id"],
            "category": question["category"],
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
        keywords_required = question.get("grading", {}).get("keywords_required", len(expected_keywords) // 2)

        # Check keywords
        for keyword in expected_keywords:
            if keyword.lower() in response_lower:
                result["keywords_found"].append(keyword)
            else:
                result["keywords_missing"].append(keyword)

        # Check fix if required
        expected_fix = question.get("expected_fix_contains")
        if expected_fix:
            result["fix_found"] = expected_fix.lower() in response_lower

        # Determine pass/fail
        keywords_pass = len(result["keywords_found"]) >= keywords_required
        fix_pass = not question.get("grading", {}).get("fix_required") or result["fix_found"]

        result["passed"] = keywords_pass and fix_pass

        # Simple hallucination check - look for fake CVEs, controls, etc.
        fake_patterns = ["CIS 99.", "CVE-9999-", "NIST SP 999-"]
        for pattern in fake_patterns:
            if pattern in response:
                result["hallucination"] = True
                break

        return result

    def score_task_response(self, test: dict, response: str) -> dict:
        """Score a task test response."""
        result = {
            "id": test["id"],
            "task_type": test.get("scanner", "unknown"),
            "passed": False,
            "syntax_valid": False,
            "semantic_correct": False,
        }

        # Basic syntax validation based on file type
        expected_content = test.get("_expected_content", "")

        if ".tf" in test.get("_expected_path", ""):
            # Terraform validation - check for required resource types
            result["syntax_valid"] = "resource" in response or "module" in response
        elif ".py" in test.get("_expected_path", ""):
            # Python validation - try to compile
            try:
                compile(response, "<string>", "exec")
                result["syntax_valid"] = True
            except SyntaxError:
                result["syntax_valid"] = False
        elif ".yaml" in test.get("_expected_path", ""):
            # YAML validation
            try:
                import yaml
                yaml.safe_load(response)
                result["syntax_valid"] = True
            except:
                result["syntax_valid"] = False

        # Semantic validation - check for key elements from expected
        if expected_content:
            # Extract validation criteria from comments
            key_elements = []
            for line in expected_content.split("\n"):
                if "Must" in line and "#" in line:
                    key_elements.append(line.split("Must")[-1].strip())

            matches = sum(1 for elem in key_elements if elem.lower() in response.lower())
            result["semantic_correct"] = matches >= len(key_elements) // 2

        result["passed"] = result["syntax_valid"] and result["semantic_correct"]

        return result

    def score_classification_response(self, test: dict, response: str) -> dict:
        """Score a classification test response."""
        result = {
            "id": test["id"],
            "expected_rank": test.get("expected_rank"),
            "expected_agent": test.get("expected_agent"),
            "predicted_rank": None,
            "predicted_agent": None,
            "rank_correct": False,
            "agent_correct": False,
            "passed": False,
        }

        response_upper = response.upper()

        # Extract predicted rank
        for rank in ["S", "A", "B", "C", "D", "E"]:
            if f"{rank}-RANK" in response_upper or f"RANK: {rank}" in response_upper or f"RANK {rank}" in response_upper:
                result["predicted_rank"] = rank
                break

        # Extract predicted agent
        for agent in ["jsa-devsec", "jsa-infrasec", "jsa-monitor"]:
            if agent in response.lower():
                result["predicted_agent"] = agent
                break

        result["rank_correct"] = result["predicted_rank"] == result["expected_rank"]
        result["agent_correct"] = result["predicted_agent"] == result["expected_agent"]
        result["passed"] = result["rank_correct"] and result["agent_correct"]

        return result

    def run_knowledge_benchmarks(self, categories: list[str] = None,
                                quick: bool = False) -> dict:
        """Run knowledge benchmarks for specified categories.

        If quick=True, sample 3 questions per category for a fast check.
        """
        if categories is None or "all" in categories:
            categories = list(KNOWLEDGE_CATEGORIES.keys())

        results = {
            "type": "knowledge",
            "timestamp": datetime.now().isoformat(),
            "categories": {},
            "summary": {"total": 0, "passed": 0, "failed": 0, "hallucinations": 0},
        }

        for category in categories:
            print(f"\n=== Running {category} knowledge benchmark ===")
            questions = self.load_questions(category)

            if quick and len(questions) > 3:
                rng = random.Random(42)
                questions = rng.sample(questions, 3)
                print(f"  (quick mode: {len(questions)} questions sampled)")

            category_results = {
                "questions": [],
                "summary": {"total": 0, "passed": 0, "failed": 0},
            }

            for q in questions:
                print(f"  Testing: {q['id']}")
                response = self.query_jade(q["question"])
                score = self.score_knowledge_response(q, response)
                score["response"] = response[:500]  # Truncate for storage
                category_results["questions"].append(score)

                category_results["summary"]["total"] += 1
                if score["passed"]:
                    category_results["summary"]["passed"] += 1
                else:
                    category_results["summary"]["failed"] += 1

                if score.get("hallucination"):
                    results["summary"]["hallucinations"] += 1

            results["categories"][category] = category_results
            results["summary"]["total"] += category_results["summary"]["total"]
            results["summary"]["passed"] += category_results["summary"]["passed"]
            results["summary"]["failed"] += category_results["summary"]["failed"]

        return results

    def run_task_benchmarks(self, task_types: list[str] = None) -> dict:
        """Run task benchmarks for specified types."""
        if task_types is None or "all" in task_types:
            task_types = list(TASK_CATEGORIES.keys())

        results = {
            "type": "task",
            "timestamp": datetime.now().isoformat(),
            "task_types": {},
            "summary": {"total": 0, "passed": 0, "failed": 0},
        }

        for task_type in task_types:
            print(f"\n=== Running {task_type} task benchmark ===")
            tests = self.load_task_tests(task_type)

            task_results = {
                "tests": [],
                "summary": {"total": 0, "passed": 0, "failed": 0},
            }

            for test in tests:
                print(f"  Testing: {test['id']}")

                # Build prompt based on test type
                if "classification" in task_type:
                    prompt = f"Classify this security finding and determine the appropriate rank (E/D/C/B/S) and JSA agent:\n\n{json.dumps(test.get('finding', test), indent=2)}"
                    response = self.query_jade(prompt)
                    score = self.score_classification_response(test, response)
                else:
                    prompt = test.get("instructions", f"Fix this issue:\n{json.dumps(test, indent=2)}")
                    response = self.query_jade(prompt)
                    score = self.score_task_response(test, response)

                score["response"] = response[:500]
                task_results["tests"].append(score)

                task_results["summary"]["total"] += 1
                if score["passed"]:
                    task_results["summary"]["passed"] += 1
                else:
                    task_results["summary"]["failed"] += 1

            results["task_types"][task_type] = task_results
            results["summary"]["total"] += task_results["summary"]["total"]
            results["summary"]["passed"] += task_results["summary"]["passed"]
            results["summary"]["failed"] += task_results["summary"]["failed"]

        return results

    def generate_scorecard(self, knowledge_results: dict, task_results: dict) -> str:
        """Generate a markdown scorecard."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        scorecard = f"""# JADE Benchmark Results

**Date**: {timestamp}
**Model**: {self.jade_model}

## Summary

| Metric | Knowledge | Tasks | Overall |
|--------|-----------|-------|---------|
| Total Tests | {knowledge_results['summary']['total']} | {task_results['summary']['total']} | {knowledge_results['summary']['total'] + task_results['summary']['total']} |
| Passed | {knowledge_results['summary']['passed']} | {task_results['summary']['passed']} | {knowledge_results['summary']['passed'] + task_results['summary']['passed']} |
| Failed | {knowledge_results['summary']['failed']} | {task_results['summary']['failed']} | {knowledge_results['summary']['failed'] + task_results['summary']['failed']} |
| Pass Rate | {knowledge_results['summary']['passed'] / max(knowledge_results['summary']['total'], 1) * 100:.1f}% | {task_results['summary']['passed'] / max(task_results['summary']['total'], 1) * 100:.1f}% | {(knowledge_results['summary']['passed'] + task_results['summary']['passed']) / max(knowledge_results['summary']['total'] + task_results['summary']['total'], 1) * 100:.1f}% |
| Hallucinations | {knowledge_results['summary'].get('hallucinations', 0)} | - | {knowledge_results['summary'].get('hallucinations', 0)} |

## Knowledge Benchmarks by Category

| Category | Passed | Total | Rate |
|----------|--------|-------|------|
"""

        for category, data in knowledge_results.get("categories", {}).items():
            s = data["summary"]
            rate = s["passed"] / max(s["total"], 1) * 100
            scorecard += f"| {category.title()} | {s['passed']} | {s['total']} | {rate:.1f}% |\n"

        scorecard += """
## Task Benchmarks by Type

| Task Type | Passed | Total | Rate |
|-----------|--------|-------|------|
"""

        for task_type, data in task_results.get("task_types", {}).items():
            s = data["summary"]
            rate = s["passed"] / max(s["total"], 1) * 100
            scorecard += f"| {task_type.replace('-', ' ').title()} | {s['passed']} | {s['total']} | {rate:.1f}% |\n"

        # Add recommendations based on results
        scorecard += """
## Recommendations

"""

        # Find weak categories
        weak_categories = []
        for category, data in knowledge_results.get("categories", {}).items():
            s = data["summary"]
            if s["total"] > 0 and s["passed"] / s["total"] < 0.6:
                weak_categories.append(category)

        if weak_categories:
            scorecard += f"- **Add training data for**: {', '.join(weak_categories)}\n"

        if knowledge_results["summary"].get("hallucinations", 0) > 0:
            scorecard += "- **Address hallucinations**: Review training data for accuracy\n"

        for task_type, data in task_results.get("task_types", {}).items():
            s = data["summary"]
            if s["total"] > 0 and s["passed"] / s["total"] < 0.6:
                scorecard += f"- **Improve {task_type}**: Add more examples to training data\n"

        return scorecard

    def save_results(self, results: dict, scorecard: str):
        """Save results to the results directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_subdir = self.results_dir / f"benchmark_{timestamp}"
        results_subdir.mkdir(parents=True, exist_ok=True)

        # Save full results
        with open(results_subdir / "full_results.json", "w") as f:
            json.dump(results, f, indent=2)

        # Save scorecard
        with open(results_subdir / "summary.md", "w") as f:
            f.write(scorecard)

        print(f"\nResults saved to: {results_subdir}")
        return results_subdir


def main():
    parser = argparse.ArgumentParser(description="Run JADE benchmarks")
    parser.add_argument(
        "--category",
        action="append",
        default=[],
        help="Knowledge categories to test (can specify multiple, or 'all')",
    )
    parser.add_argument(
        "--task",
        action="append",
        default=[],
        help="Task types to test (can specify multiple, or 'all')",
    )
    parser.add_argument("--knowledge-only", action="store_true", help="Run only knowledge benchmarks")
    parser.add_argument("--task-only", action="store_true", help="Run only task benchmarks")
    parser.add_argument("--jade-endpoint", help="JADE API endpoint URL")
    parser.add_argument("--model-path", help="Path to local HuggingFace model (bypasses Ollama)")
    parser.add_argument("--quick", action="store_true", help="Quick mode: 3 questions per category")
    parser.add_argument("--dry-run", action="store_true", help="Load tests but don't query JADE")

    args = parser.parse_args()

    runner = BenchmarkRunner(jade_endpoint=args.jade_endpoint, model_path=args.model_path)

    # Determine what to run
    categories = args.category if args.category else ["all"]
    task_types = args.task if args.task else ["all"]

    knowledge_results = {"summary": {"total": 0, "passed": 0, "failed": 0, "hallucinations": 0}, "categories": {}}
    task_results = {"summary": {"total": 0, "passed": 0, "failed": 0}, "task_types": {}}

    if args.dry_run:
        print("=== DRY RUN MODE ===")
        print(f"Would test knowledge categories: {categories}")
        print(f"Would test task types: {task_types}")

        # Just load and count tests
        for cat in (list(KNOWLEDGE_CATEGORIES.keys()) if "all" in categories else categories):
            questions = runner.load_questions(cat)
            print(f"  {cat}: {len(questions)} questions")

        for task in (list(TASK_CATEGORIES.keys()) if "all" in task_types else task_types):
            tests = runner.load_task_tests(task)
            print(f"  {task}: {len(tests)} tests")

        return

    # Run benchmarks
    if not args.task_only:
        knowledge_results = runner.run_knowledge_benchmarks(categories, quick=args.quick)

    if not args.knowledge_only:
        task_results = runner.run_task_benchmarks(task_types)

    # Generate and save results
    scorecard = runner.generate_scorecard(knowledge_results, task_results)
    print("\n" + scorecard)

    combined_results = {
        "knowledge": knowledge_results,
        "tasks": task_results,
    }
    runner.save_results(combined_results, scorecard)


if __name__ == "__main__":
    main()
