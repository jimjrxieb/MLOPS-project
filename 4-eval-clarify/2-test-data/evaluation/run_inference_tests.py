#!/usr/bin/env python3
"""
JADE v0.5 Inference Test Runner
================================

Tests JADE with RAG enabled using inference_tests.jsonl.
Proper Q&A format with input files and expected answers.

Test Categories:
- violation_detection: Analyze FAULTY manifests, detect issues
- fix_generation: Generate FIXED version from FAULTY
- policy_generation: Write OPA/Rego from requirements
- policy_classification: Identify which policies apply
- rego_fix: Fix broken Rego policies
- incident_response: Security incident handling
- helm_analysis: Analyze Helm charts

Usage:
    python3 run_inference_tests.py                    # Run all tests
    python3 run_inference_tests.py --category violation_detection
    python3 run_inference_tests.py --verbose          # Show detailed output
    python3 run_inference_tests.py --limit 5          # Limit tests per category
"""

import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
import requests
import numpy as np

SCRIPT_DIR = Path(__file__).parent
GP_ROOT = SCRIPT_DIR.parents[3]  # GP-copilot root
CHROMA_DIR = GP_ROOT / "GP-OPENSEARCH" / "05-ragged-data" / "chroma"
RESULTS_DIR = SCRIPT_DIR / "results"
TESTS_FILE = SCRIPT_DIR / "inference_tests.jsonl"

# Import ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    print("ERROR: ChromaDB required. Install: pip install chromadb")
    sys.exit(1)


class OllamaEmbedding:
    """Embedding function for ChromaDB"""
    def __call__(self, input: list) -> list:
        embeddings = []
        for text in input:
            try:
                resp = requests.post(
                    "http://localhost:11434/api/embeddings",
                    json={"model": "nomic-embed-text:latest", "prompt": text},
                    timeout=30
                )
                embeddings.append(resp.json()["embedding"])
            except:
                embeddings.append([0.0] * 768)
        return embeddings


def cosine_similarity(vec1: list, vec2: list) -> float:
    """Calculate cosine similarity"""
    if not vec1 or not vec2:
        return 0.0
    a, b = np.array(vec1), np.array(vec2)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


class JADEInferenceRunner:
    """Run inference tests against JADE with RAG"""

    def __init__(self, model: str = "jade:v0.5", verbose: bool = False):
        self.model = model
        self.verbose = verbose
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.embedder = OllamaEmbedding()

        self.results = {
            'timestamp': self.timestamp,
            'model': model,
            'rag_enabled': True,
            'test_type': 'inference',
            'tests': [],
            'by_category': {},
            'summary': {}
        }

        # Load tests
        self.tests = self._load_tests()
        print(f"Loaded {len(self.tests)} tests from inference_tests.jsonl")

        # Initialize RAG
        self._init_rag()

    def _load_tests(self) -> List[Dict]:
        """Load tests from JSONL file"""
        if not TESTS_FILE.exists():
            print(f"ERROR: {TESTS_FILE} not found")
            sys.exit(1)

        tests = []
        with open(TESTS_FILE) as f:
            for line in f:
                if line.strip():
                    tests.append(json.loads(line))
        return tests

    def _init_rag(self):
        """Initialize ChromaDB connection"""
        try:
            client = chromadb.PersistentClient(
                path=str(CHROMA_DIR),
                settings=Settings(anonymized_telemetry=False)
            )
            self.collection = client.get_collection(
                "jade-general",
                embedding_function=OllamaEmbedding()
            )
            print(f"RAG connected: {self.collection.count()} documents")
        except Exception as e:
            print(f"ERROR: RAG init failed: {e}")
            sys.exit(1)

    def _get_rag_context(self, query: str, n_results: int = 5) -> str:
        """Retrieve context from RAG"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=['documents', 'metadatas']
            )
            if results['documents'] and results['documents'][0]:
                return "\n---\n".join(doc[:600] for doc in results['documents'][0])
        except Exception as e:
            if self.verbose:
                print(f"    RAG error: {e}")
        return ""

    def _read_file(self, path: str) -> str:
        """Read input file relative to SCRIPT_DIR"""
        full_path = SCRIPT_DIR / path
        if not full_path.exists():
            return f"ERROR: File not found: {path}"
        return full_path.read_text()

    def _query_jade(self, prompt: str, rag_context: str = None) -> str:
        """Query JADE with optional RAG context"""
        try:
            if rag_context:
                full_prompt = f"""Reference Information:
{rag_context}

---

{prompt}"""
            else:
                full_prompt = prompt

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 2048}
                },
                timeout=120
            )
            return response.json().get("response", "").strip()
        except Exception as e:
            return f"ERROR: {e}"

    def _evaluate_keywords(self, response: str, expected: List[str]) -> Tuple[float, List[str]]:
        """Check how many expected keywords are in response"""
        if not expected:
            return 1.0, []

        response_lower = response.lower()
        found = [kw for kw in expected if kw.lower() in response_lower]
        score = len(found) / len(expected)
        return score, found

    def _evaluate_test(self, test: Dict) -> Dict:
        """Run and evaluate a single test"""
        test_id = test.get('id', 'unknown')
        category = test.get('category', 'unknown')
        prompt = test.get('prompt', '')

        # Build the full prompt with input file if specified
        input_file = test.get('input_file')
        if input_file:
            file_content = self._read_file(input_file)
            if file_content.startswith("ERROR"):
                return {
                    'id': test_id,
                    'category': category,
                    'passed': False,
                    'score': 0.0,
                    'error': file_content
                }

            # Determine file type for context
            if input_file.endswith(('.yaml', '.yml')):
                full_prompt = f"{prompt}\n\n```yaml\n{file_content}\n```"
            elif input_file.endswith('.tf'):
                full_prompt = f"{prompt}\n\n```hcl\n{file_content}\n```"
            elif input_file.endswith('.rego'):
                full_prompt = f"{prompt}\n\n```rego\n{file_content}\n```"
            elif 'Dockerfile' in input_file:
                full_prompt = f"{prompt}\n\n```dockerfile\n{file_content}\n```"
            else:
                full_prompt = f"{prompt}\n\n```\n{file_content}\n```"
        else:
            full_prompt = prompt

        # Get RAG context
        rag_query = f"{category} {prompt} {test.get('expected_keywords', [])}"
        rag_context = self._get_rag_context(rag_query[:500])

        # Query JADE
        response = self._query_jade(full_prompt, rag_context=rag_context)

        # Evaluate based on category
        score = 0.0
        details = {}

        # Check expected keywords
        expected_keywords = test.get('expected_keywords', [])
        kw_score, found_keywords = self._evaluate_keywords(response, expected_keywords)
        details['keyword_score'] = kw_score
        details['found_keywords'] = found_keywords

        # Check expected violations (for violation_detection)
        expected_violations = test.get('expected_violations', [])
        if expected_violations:
            viol_score, found_violations = self._evaluate_keywords(response, expected_violations)
            details['violation_score'] = viol_score
            details['found_violations'] = found_violations
            score = (kw_score + viol_score) / 2
        else:
            score = kw_score

        # Check expected fixes (for fix_generation)
        expected_fixes = test.get('expected_fixes', [])
        if expected_fixes:
            fix_score, found_fixes = self._evaluate_keywords(response, expected_fixes)
            details['fix_score'] = fix_score
            details['found_fixes'] = found_fixes
            score = (score + fix_score) / 2

        # Check expected policies (for policy_classification)
        expected_policies = test.get('expected_policies', [])
        if expected_policies:
            pol_score, found_policies = self._evaluate_keywords(response, expected_policies)
            details['policy_score'] = pol_score
            details['found_policies'] = found_policies
            score = (score + pol_score) / 2

        # Check expected actions (for incident_response)
        expected_actions = test.get('expected_actions', [])
        if expected_actions:
            act_score, found_actions = self._evaluate_keywords(response, expected_actions)
            details['action_score'] = act_score
            details['found_actions'] = found_actions
            score = (score + act_score) / 2

        # Determine pass/fail threshold based on rank
        rank = test.get('rank', 'D')
        threshold = {'D': 0.4, 'C': 0.5, 'B': 0.5, 'A': 0.6, 'S': 0.6}.get(rank, 0.5)
        passed = score >= threshold

        return {
            'id': test_id,
            'category': category,
            'rank': rank,
            'prompt': prompt[:100],
            'input_file': input_file,
            'jade_response': response[:1500],
            'passed': passed,
            'score': score,
            'threshold': threshold,
            'details': details,
            'rag_used': bool(rag_context)
        }

    def run_all(self, category_filter: str = None, limit: int = None) -> Dict:
        """Run all inference tests"""
        print("\n" + "="*70)
        print("JADE v0.5 INFERENCE TEST SUITE (RAG-Enabled)")
        print("="*70)
        print(f"Model: {self.model}")
        print(f"RAG: Enabled ({self.collection.count()} documents)")
        print(f"Tests: {len(self.tests)}")
        if category_filter:
            print(f"Filter: {category_filter}")
        if limit:
            print(f"Limit: {limit} per category")
        print("="*70 + "\n")

        # Group tests by category
        by_category = {}
        for test in self.tests:
            cat = test.get('category', 'unknown')
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(test)

        # Run tests
        for category, tests in sorted(by_category.items()):
            if category_filter and category != category_filter:
                continue

            if limit:
                tests = tests[:limit]

            print(f"\n[{category.upper()}] Running {len(tests)} tests")
            print("-" * 50)

            category_results = []
            for test in tests:
                if self.verbose:
                    print(f"  Testing: {test.get('id', 'unknown')}...")

                result = self._evaluate_test(test)
                category_results.append(result)
                self.results['tests'].append(result)

                status = "PASS" if result['passed'] else "FAIL"
                print(f"  {status}: {result['id']} (score: {result['score']:.2f})")

            # Category summary
            passed = sum(1 for r in category_results if r['passed'])
            total = len(category_results)
            pct = (passed / total * 100) if total > 0 else 0

            self.results['by_category'][category] = {
                'passed': passed,
                'total': total,
                'pass_rate': pct
            }

            print(f"\n  {category}: {passed}/{total} ({pct:.1f}%)")

        # Overall summary
        total_passed = sum(1 for r in self.results['tests'] if r['passed'])
        total_tests = len(self.results['tests'])

        self.results['summary'] = {
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_tests - total_passed,
            'pass_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0
        }

        return self.results

    def save_results(self) -> Path:
        """Save results"""
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        result_dir = RESULTS_DIR / f"inference_{self.timestamp}"
        result_dir.mkdir(exist_ok=True)

        # Full results
        with open(result_dir / "full_results.json", 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        # Summary markdown
        with open(result_dir / "summary.md", 'w') as f:
            f.write("# JADE v0.5 Inference Test Results\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Model**: {self.model}\n")
            f.write(f"**RAG**: Enabled\n\n")

            f.write("## Summary\n\n")
            f.write("| Metric | Value |\n|--------|-------|\n")
            f.write(f"| Total Tests | {self.results['summary']['total_tests']} |\n")
            f.write(f"| Passed | {self.results['summary']['total_passed']} |\n")
            f.write(f"| Failed | {self.results['summary']['total_failed']} |\n")
            f.write(f"| **Pass Rate** | **{self.results['summary']['pass_rate']:.1f}%** |\n\n")

            f.write("## By Category\n\n")
            f.write("| Category | Passed | Total | Rate |\n|----------|--------|-------|------|\n")
            for cat, data in sorted(self.results['by_category'].items()):
                f.write(f"| {cat} | {data['passed']} | {data['total']} | {data['pass_rate']:.1f}% |\n")

            f.write("\n## Failed Tests\n\n")
            for test in self.results['tests']:
                if not test['passed']:
                    f.write(f"- **{test['id']}** ({test['category']}): score={test['score']:.2f}\n")

        # JADE responses
        with open(result_dir / "jade_responses.jsonl", 'w') as f:
            for test in self.results['tests']:
                f.write(json.dumps({
                    'id': test['id'],
                    'category': test['category'],
                    'prompt': test.get('prompt', ''),
                    'jade_response': test['jade_response'],
                    'passed': test['passed'],
                    'score': test['score']
                }) + '\n')

        print(f"\nResults saved to: {result_dir}")
        return result_dir

    def print_summary(self):
        """Print summary"""
        print("\n" + "="*70)
        print("INFERENCE TEST SUMMARY")
        print("="*70)
        print(f"\n  Model: {self.model}")
        print(f"  RAG: Enabled")
        s = self.results['summary']
        print(f"\n  Overall: {s['total_passed']}/{s['total_tests']} ({s['pass_rate']:.1f}%)")
        print(f"\n  By Category:")
        for cat, data in sorted(self.results['by_category'].items()):
            bar = "#" * int(data['pass_rate'] / 10) + "." * (10 - int(data['pass_rate'] / 10))
            print(f"    {cat:22s}: [{bar}] {data['passed']:2d}/{data['total']:2d} ({data['pass_rate']:5.1f}%)")
        print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(description='JADE v0.5 Inference Test Runner')
    parser.add_argument('--category', '-c', type=str, help='Run specific category only')
    parser.add_argument('--limit', '-l', type=int, help='Limit tests per category')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--model', type=str, default='jade:v0.5', help='Model to test')

    args = parser.parse_args()

    runner = JADEInferenceRunner(model=args.model, verbose=args.verbose)
    runner.run_all(category_filter=args.category, limit=args.limit)
    runner.save_results()
    runner.print_summary()

    return 0


if __name__ == "__main__":
    sys.exit(main())
