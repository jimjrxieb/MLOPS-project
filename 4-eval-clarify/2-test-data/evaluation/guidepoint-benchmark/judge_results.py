#!/usr/bin/env python3
"""
Claude Code Judge - Evaluates JADE vs Haiku benchmark responses

Takes benchmark results and has Claude evaluate each response based on:
1. Correctness - Did they answer correctly?
2. NPC Knowledge - Did they mention the right GP-CONSULTING tools?
3. Workflow - Did they explain the correct scan→fix→verify workflow?
4. Practicality - Is the answer operationally useful?

Usage:
    python3 judge_results.py results/benchmark_YYYYMMDD_HHMMSS.json

    # Output markdown report
    python3 judge_results.py results/benchmark_*.json --markdown
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    import anthropic
except ImportError:
    print("Installing anthropic...")
    os.system("pip install anthropic")
    import anthropic


SCRIPT_DIR = Path(__file__).parent


JUDGE_PROMPT = """You are evaluating responses from two AI models on DevSecOps security questions.

## Question
{question}

## Expected Elements
{expected_elements}

## Expected Workflow
{expected_workflow}

## Scoring Rubric
{scoring_rubric}

---

## Model A Response (JADE - 7B specialized model)
{jade_response}

---

## Model B Response (Haiku - general purpose model)
{haiku_response}

---

## Your Task
Score each response on a 0-10 scale for these criteria:

1. **Correctness** (0-10): Is the technical content accurate?
2. **NPC Knowledge** (0-10): Did they correctly reference the GP-CONSULTING NPCs/tools?
3. **Workflow** (0-10): Did they explain the proper scan→fix→verify workflow?
4. **Practicality** (0-10): Is this answer operationally useful for a real DevSecOps engineer?

Then provide:
- **Winner**: "JADE", "HAIKU", or "TIE"
- **Explanation**: 1-2 sentences on why

Return your evaluation as JSON:
```json
{{
  "jade_scores": {{
    "correctness": <0-10>,
    "npc_knowledge": <0-10>,
    "workflow": <0-10>,
    "practicality": <0-10>,
    "total": <0-40>
  }},
  "haiku_scores": {{
    "correctness": <0-10>,
    "npc_knowledge": <0-10>,
    "workflow": <0-10>,
    "practicality": <0-10>,
    "total": <0-40>
  }},
  "winner": "<JADE|HAIKU|TIE>",
  "explanation": "<why>"
}}
```

Be fair but strict. Award points for:
- Mentioning specific NPCs by name (e.g., "gitleaks_npc.py", "KubeBenchNPC")
- Explaining the correct workflow order
- Practical, actionable advice
- Understanding of the GP-CONSULTING toolkit

Deduct points for:
- Generic answers that don't reference the tools
- Incorrect workflow order
- Hallucinated or wrong tool names
- Overly verbose without substance
"""


class BenchmarkJudge:
    """Uses Claude to evaluate benchmark responses."""

    def __init__(self, results_file: Path):
        self.results_file = results_file
        self.results = self._load_results()

        # Initialize Anthropic client
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable required")

        self.client = anthropic.Anthropic(api_key=self.anthropic_key)

        # Evaluation results
        self.evaluations = []

    def _load_results(self) -> Dict:
        """Load benchmark results."""
        with open(self.results_file) as f:
            return json.load(f)

    def evaluate_question(self, question_result: Dict) -> Dict:
        """Have Claude evaluate a single question's responses."""
        q_id = question_result["question_id"]

        # Skip if either model failed
        if not question_result["jade_response"].get("success"):
            return {"question_id": q_id, "error": "JADE failed", "skipped": True}
        if not question_result["haiku_response"].get("success"):
            return {"question_id": q_id, "error": "Haiku failed", "skipped": True}

        # Build judge prompt
        prompt = JUDGE_PROMPT.format(
            question=question_result.get("prompt", "")[:2000],
            expected_elements=json.dumps(question_result.get("expected_npcs", []), indent=2),
            expected_workflow=question_result.get("expected_workflow", "N/A"),
            scoring_rubric=json.dumps(question_result.get("scoring", {}), indent=2),
            jade_response=question_result["jade_response"]["response"][:3000],
            haiku_response=question_result["haiku_response"]["response"][:3000],
        )

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",  # Use Sonnet for judging
                max_tokens=1000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                evaluation = json.loads(response_text[json_start:json_end])
            else:
                evaluation = {"error": "Could not parse JSON", "raw": response_text}

            evaluation["question_id"] = q_id
            evaluation["domain"] = question_result.get("domain")
            evaluation["question_type"] = question_result.get("question_type")

            return evaluation

        except Exception as e:
            return {"question_id": q_id, "error": str(e)}

    def run_evaluation(self) -> Dict:
        """Evaluate all questions."""
        questions = self.results.get("questions", [])

        print(f"\n{'#'*60}")
        print(f"Claude Code Judge - Evaluating {len(questions)} questions")
        print(f"{'#'*60}\n")

        for i, question in enumerate(questions, 1):
            q_id = question.get("question_id", "unknown")
            print(f"[{i}/{len(questions)}] Evaluating {q_id}...", end=" ", flush=True)

            evaluation = self.evaluate_question(question)
            self.evaluations.append(evaluation)

            if evaluation.get("skipped"):
                print("SKIPPED")
            elif evaluation.get("error"):
                print(f"ERROR: {evaluation['error']}")
            else:
                winner = evaluation.get("winner", "?")
                jade_total = evaluation.get("jade_scores", {}).get("total", 0)
                haiku_total = evaluation.get("haiku_scores", {}).get("total", 0)
                print(f"Winner: {winner} (JADE: {jade_total}/40, Haiku: {haiku_total}/40)")

        # Calculate overall results
        summary = self._calculate_summary()

        return {
            "benchmark_file": str(self.results_file),
            "evaluation_timestamp": datetime.now().isoformat(),
            "questions": self.evaluations,
            "summary": summary,
        }

    def _calculate_summary(self) -> Dict:
        """Calculate overall benchmark summary."""
        valid_evals = [e for e in self.evaluations if not e.get("skipped") and not e.get("error")]

        if not valid_evals:
            return {"error": "No valid evaluations"}

        jade_wins = sum(1 for e in valid_evals if e.get("winner") == "JADE")
        haiku_wins = sum(1 for e in valid_evals if e.get("winner") == "HAIKU")
        ties = sum(1 for e in valid_evals if e.get("winner") == "TIE")

        jade_totals = [e.get("jade_scores", {}).get("total", 0) for e in valid_evals]
        haiku_totals = [e.get("haiku_scores", {}).get("total", 0) for e in valid_evals]

        # By category
        jade_correctness = [e.get("jade_scores", {}).get("correctness", 0) for e in valid_evals]
        jade_npc = [e.get("jade_scores", {}).get("npc_knowledge", 0) for e in valid_evals]
        jade_workflow = [e.get("jade_scores", {}).get("workflow", 0) for e in valid_evals]
        jade_practical = [e.get("jade_scores", {}).get("practicality", 0) for e in valid_evals]

        haiku_correctness = [e.get("haiku_scores", {}).get("correctness", 0) for e in valid_evals]
        haiku_npc = [e.get("haiku_scores", {}).get("npc_knowledge", 0) for e in valid_evals]
        haiku_workflow = [e.get("haiku_scores", {}).get("workflow", 0) for e in valid_evals]
        haiku_practical = [e.get("haiku_scores", {}).get("practicality", 0) for e in valid_evals]

        # By question type
        operational = [e for e in valid_evals if e.get("question_type") == "operational"]
        domain = [e for e in valid_evals if e.get("question_type") == "domain"]

        return {
            "total_evaluated": len(valid_evals),
            "skipped": len(self.evaluations) - len(valid_evals),
            "jade_wins": jade_wins,
            "haiku_wins": haiku_wins,
            "ties": ties,
            "jade_win_rate": jade_wins / len(valid_evals) if valid_evals else 0,
            "haiku_win_rate": haiku_wins / len(valid_evals) if valid_evals else 0,
            "jade_avg_total": sum(jade_totals) / len(jade_totals) if jade_totals else 0,
            "haiku_avg_total": sum(haiku_totals) / len(haiku_totals) if haiku_totals else 0,
            "by_category": {
                "jade": {
                    "correctness": sum(jade_correctness) / len(jade_correctness) if jade_correctness else 0,
                    "npc_knowledge": sum(jade_npc) / len(jade_npc) if jade_npc else 0,
                    "workflow": sum(jade_workflow) / len(jade_workflow) if jade_workflow else 0,
                    "practicality": sum(jade_practical) / len(jade_practical) if jade_practical else 0,
                },
                "haiku": {
                    "correctness": sum(haiku_correctness) / len(haiku_correctness) if haiku_correctness else 0,
                    "npc_knowledge": sum(haiku_npc) / len(haiku_npc) if haiku_npc else 0,
                    "workflow": sum(haiku_workflow) / len(haiku_workflow) if haiku_workflow else 0,
                    "practicality": sum(haiku_practical) / len(haiku_practical) if haiku_practical else 0,
                },
            },
            "operational_questions": {
                "jade_wins": sum(1 for e in operational if e.get("winner") == "JADE"),
                "haiku_wins": sum(1 for e in operational if e.get("winner") == "HAIKU"),
                "ties": sum(1 for e in operational if e.get("winner") == "TIE"),
            },
            "domain_questions": {
                "jade_wins": sum(1 for e in domain if e.get("winner") == "JADE"),
                "haiku_wins": sum(1 for e in domain if e.get("winner") == "HAIKU"),
                "ties": sum(1 for e in domain if e.get("winner") == "TIE"),
            },
        }

    def save_results(self, evaluation: Dict) -> Path:
        """Save evaluation results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = SCRIPT_DIR / "results" / f"evaluation_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(evaluation, f, indent=2)

        print(f"\nEvaluation saved to: {output_file}")
        return output_file

    def print_report(self, evaluation: Dict):
        """Print formatted evaluation report."""
        summary = evaluation["summary"]

        print(f"\n{'='*60}")
        print(f"BENCHMARK EVALUATION REPORT")
        print(f"{'='*60}")

        print(f"\n## Overall Results")
        print(f"Questions Evaluated: {summary['total_evaluated']}")
        print(f"Skipped: {summary['skipped']}")

        print(f"\n## Head-to-Head")
        print(f"JADE Wins:  {summary['jade_wins']} ({summary['jade_win_rate']*100:.0f}%)")
        print(f"Haiku Wins: {summary['haiku_wins']} ({summary['haiku_win_rate']*100:.0f}%)")
        print(f"Ties:       {summary['ties']}")

        print(f"\n## Average Scores (out of 40)")
        print(f"JADE:  {summary['jade_avg_total']:.1f}")
        print(f"Haiku: {summary['haiku_avg_total']:.1f}")

        print(f"\n## By Category (out of 10)")
        print(f"{'Category':<15} {'JADE':>8} {'Haiku':>8} {'Winner':>10}")
        print(f"{'-'*43}")
        cats = ["correctness", "npc_knowledge", "workflow", "practicality"]
        for cat in cats:
            jade_score = summary['by_category']['jade'].get(cat, 0)
            haiku_score = summary['by_category']['haiku'].get(cat, 0)
            winner = "JADE" if jade_score > haiku_score else "Haiku" if haiku_score > jade_score else "Tie"
            print(f"{cat:<15} {jade_score:>8.1f} {haiku_score:>8.1f} {winner:>10}")

        print(f"\n## By Question Type")
        print(f"Operational (NPC Knowledge):")
        op = summary['operational_questions']
        print(f"  JADE: {op['jade_wins']} | Haiku: {op['haiku_wins']} | Ties: {op['ties']}")

        print(f"Domain (Technical Knowledge):")
        dom = summary['domain_questions']
        print(f"  JADE: {dom['jade_wins']} | Haiku: {dom['haiku_wins']} | Ties: {dom['ties']}")

        # Determine overall winner
        print(f"\n{'='*60}")
        if summary['jade_wins'] > summary['haiku_wins']:
            print(f"OVERALL WINNER: JADE ({summary['jade_wins']}-{summary['haiku_wins']}-{summary['ties']})")
        elif summary['haiku_wins'] > summary['jade_wins']:
            print(f"OVERALL WINNER: HAIKU ({summary['haiku_wins']}-{summary['jade_wins']}-{summary['ties']})")
        else:
            print(f"OVERALL: TIE ({summary['jade_wins']}-{summary['haiku_wins']}-{summary['ties']})")
        print(f"{'='*60}\n")

    def generate_markdown(self, evaluation: Dict) -> str:
        """Generate markdown report."""
        summary = evaluation["summary"]

        md = f"""# GuidePoint Domain Benchmark: JADE vs Haiku

**Date**: {evaluation['evaluation_timestamp'][:10]}
**Benchmark File**: {evaluation['benchmark_file']}

## Summary

| Metric | JADE | Haiku | Winner |
|--------|------|-------|--------|
| Wins | {summary['jade_wins']} | {summary['haiku_wins']} | {'JADE' if summary['jade_wins'] > summary['haiku_wins'] else 'Haiku' if summary['haiku_wins'] > summary['jade_wins'] else 'Tie'} |
| Win Rate | {summary['jade_win_rate']*100:.0f}% | {summary['haiku_win_rate']*100:.0f}% | |
| Avg Score | {summary['jade_avg_total']:.1f}/40 | {summary['haiku_avg_total']:.1f}/40 | |

## Scores by Category

| Category | JADE | Haiku | Winner |
|----------|------|-------|--------|
"""
        cats = ["correctness", "npc_knowledge", "workflow", "practicality"]
        for cat in cats:
            jade = summary['by_category']['jade'].get(cat, 0)
            haiku = summary['by_category']['haiku'].get(cat, 0)
            winner = "JADE" if jade > haiku else "Haiku" if haiku > jade else "Tie"
            md += f"| {cat.replace('_', ' ').title()} | {jade:.1f}/10 | {haiku:.1f}/10 | {winner} |\n"

        md += f"""
## By Question Type

### Operational (GP-CONSULTING NPC Knowledge)
- JADE: {summary['operational_questions']['jade_wins']} wins
- Haiku: {summary['operational_questions']['haiku_wins']} wins
- Ties: {summary['operational_questions']['ties']}

### Domain (Technical Security Knowledge)
- JADE: {summary['domain_questions']['jade_wins']} wins
- Haiku: {summary['domain_questions']['haiku_wins']} wins
- Ties: {summary['domain_questions']['ties']}

## Key Insight

{"JADE excels at operational/NPC knowledge - the 'judo' specialization pays off!" if summary['operational_questions']['jade_wins'] > summary['operational_questions']['haiku_wins'] else "Haiku's broader knowledge helps even with context provided."}

## Question Details

"""
        for q in evaluation["questions"]:
            if q.get("skipped") or q.get("error"):
                continue
            md += f"""### {q['question_id']} ({q.get('domain', 'unknown')})
- **Winner**: {q.get('winner', '?')}
- **JADE**: {q.get('jade_scores', {}).get('total', 0)}/40
- **Haiku**: {q.get('haiku_scores', {}).get('total', 0)}/40
- **Reason**: {q.get('explanation', 'N/A')}

"""

        return md


def main():
    parser = argparse.ArgumentParser(description="Claude Code Judge")
    parser.add_argument("results_file", type=Path, help="Benchmark results JSON file")
    parser.add_argument("--markdown", action="store_true", help="Output markdown report")

    args = parser.parse_args()

    if not args.results_file.exists():
        print(f"Results file not found: {args.results_file}")
        sys.exit(1)

    judge = BenchmarkJudge(args.results_file)
    evaluation = judge.run_evaluation()

    # Save results
    output_file = judge.save_results(evaluation)

    # Print report
    judge.print_report(evaluation)

    # Generate markdown if requested
    if args.markdown:
        md = judge.generate_markdown(evaluation)
        md_file = output_file.with_suffix(".md")
        with open(md_file, "w") as f:
            f.write(md)
        print(f"Markdown report: {md_file}")


if __name__ == "__main__":
    main()
