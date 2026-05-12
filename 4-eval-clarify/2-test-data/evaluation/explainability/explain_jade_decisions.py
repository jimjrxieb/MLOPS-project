"""
GP-CLARIFY: JADE Decision Explainability
Amazon SageMaker Clarify Equivalent

Explains why JADE made specific decisions:
- Why did JADE skip this finding?
- Why did JADE escalate instead of fixing?
- What confidence level drove the decision?
- What features influenced the decision?
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter
from datetime import datetime


class JadeDecisionExplainer:
    """
    Explain JADE's fix/skip/escalate decisions using explainability metrics.

    Similar to SageMaker Clarify's post-training explainability:
    - Feature importance (what factors mattered most?)
    - Decision confidence (how certain was JADE?)
    - Counterfactual analysis (what would change the decision?)
    """

    def __init__(self, logs_dir: str):
        self.logs_dir = Path(logs_dir)
        self.decisions = []

    def load_decisions(self, log_type: str = "fixes"):
        """Load JADE decision logs from fixes/rescans/escalations directories."""
        log_path = self.logs_dir / log_type
        if not log_path.exists():
            print(f"Log directory not found: {log_path}")
            return

        log_files = sorted(log_path.glob("*.log"))
        print(f"Found {len(log_files)} {log_type} logs")

        for log_file in log_files:
            self._parse_log_file(log_file, log_type)

        print(f"Loaded {len(self.decisions)} decisions")

    def _parse_log_file(self, log_file: Path, decision_type: str):
        """Parse a log file to extract JADE decisions."""
        with open(log_file) as f:
            content = f.read()

        # Extract metadata from filename
        filename = log_file.stem
        parts = filename.split('_')

        decision = {
            "scanner": parts[0] if len(parts) > 0 else "unknown",
            "finding_type": parts[1] if len(parts) > 1 else "unknown",
            "slot": parts[2] if len(parts) > 2 else "unknown",
            "timestamp": parts[3] + "_" + parts[4] if len(parts) > 4 else "unknown",
            "decision_type": decision_type,
            "log_file": str(log_file),
        }

        # Parse log content for decision factors
        if "Skipped:" in content:
            skipped_match = re.search(r"Skipped:\s+(\d+)", content)
            if skipped_match:
                decision["skipped_count"] = int(skipped_match.group(1))

        if "Escalated:" in content:
            escalated_match = re.search(r"Escalated:\s+(\d+)", content)
            if escalated_match:
                decision["escalated_count"] = int(escalated_match.group(1))

        if "Fixed:" in content or "Successfully" in content:
            success_matches = content.count("Successfully")
            decision["success_count"] = success_matches

        if "Failed:" in content or "ERROR" in content:
            failure_matches = content.count("Failed:") + content.count("ERROR")
            decision["failure_count"] = failure_matches

        # Extract skip/escalation reasons
        decision["skip_reasons"] = self._extract_skip_reasons(content)
        decision["escalation_reasons"] = self._extract_escalation_reasons(content)
        decision["failure_reasons"] = self._extract_failure_reasons(content)

        self.decisions.append(decision)

    def _extract_skip_reasons(self, content: str) -> List[str]:
        """Extract reasons JADE skipped findings."""
        reasons = []

        # Common skip patterns
        if "backup path" in content.lower():
            reasons.append("backup_path_detected")
        if "false positive" in content.lower():
            reasons.append("false_positive_detected")
        if "test file" in content.lower():
            reasons.append("test_file")
        if "placeholder" in content.lower():
            reasons.append("placeholder_value")
        if "could not resolve" in content.lower():
            reasons.append("unresolvable_path")

        return reasons

    def _extract_escalation_reasons(self, content: str) -> List[str]:
        """Extract reasons JADE escalated findings."""
        reasons = []

        if "production secret" in content.lower():
            reasons.append("production_secret")
        if "high severity" in content.lower():
            reasons.append("high_severity")
        if "complex fix" in content.lower():
            reasons.append("complex_fix_required")
        if "human review" in content.lower():
            reasons.append("human_review_needed")
        if "confidence" in content.lower() and ("low" in content.lower() or "uncertain" in content.lower()):
            reasons.append("low_confidence")

        return reasons

    def _extract_failure_reasons(self, content: str) -> List[str]:
        """Extract reasons fixes failed."""
        reasons = []

        if "file not found" in content.lower() or "does not exist" in content.lower():
            reasons.append("file_not_found")
        if "permission" in content.lower():
            reasons.append("permission_error")
        if "syntax error" in content.lower():
            reasons.append("syntax_error")
        if "backup" in content.lower() and "path" in content.lower():
            reasons.append("backup_path_issue")

        return reasons

    def explain_skip_decisions(self) -> Dict[str, Any]:
        """Explain why JADE skipped findings."""
        skip_reasons = Counter()
        total_skipped = 0

        for decision in self.decisions:
            skipped = decision.get("skipped_count", 0)
            total_skipped += skipped

            for reason in decision.get("skip_reasons", []):
                skip_reasons[reason] += skipped

        return {
            "total_skipped": total_skipped,
            "skip_reasons": dict(skip_reasons.most_common()),
            "top_reason": skip_reasons.most_common(1)[0] if skip_reasons else ("none", 0),
            "reason_distribution": self._calculate_distribution(skip_reasons)
        }

    def explain_escalation_decisions(self) -> Dict[str, Any]:
        """Explain why JADE escalated findings."""
        escalation_reasons = Counter()
        total_escalated = 0

        for decision in self.decisions:
            escalated = decision.get("escalated_count", 0)
            total_escalated += escalated

            for reason in decision.get("escalation_reasons", []):
                escalation_reasons[reason] += escalated

        return {
            "total_escalated": total_escalated,
            "escalation_reasons": dict(escalation_reasons.most_common()),
            "top_reason": escalation_reasons.most_common(1)[0] if escalation_reasons else ("none", 0),
            "reason_distribution": self._calculate_distribution(escalation_reasons)
        }

    def explain_failure_patterns(self) -> Dict[str, Any]:
        """Explain why fixes failed."""
        failure_reasons = Counter()
        total_failures = 0

        for decision in self.decisions:
            failures = decision.get("failure_count", 0)
            total_failures += failures

            for reason in decision.get("failure_reasons", []):
                failure_reasons[reason] += failures

        return {
            "total_failures": total_failures,
            "failure_reasons": dict(failure_reasons.most_common()),
            "top_reason": failure_reasons.most_common(1)[0] if failure_reasons else ("none", 0),
            "reason_distribution": self._calculate_distribution(failure_reasons)
        }

    def _calculate_distribution(self, counter: Counter) -> Dict[str, float]:
        """Calculate percentage distribution."""
        total = sum(counter.values())
        if total == 0:
            return {}

        return {
            reason: f"{(count / total * 100):.1f}%"
            for reason, count in counter.items()
        }

    def get_decision_confidence_analysis(self) -> Dict[str, Any]:
        """Analyze JADE's decision confidence levels."""
        # Count decisions by type
        skip_decisions = sum(d.get("skipped_count", 0) for d in self.decisions)
        escalate_decisions = sum(d.get("escalated_count", 0) for d in self.decisions)
        success_decisions = sum(d.get("success_count", 0) for d in self.decisions)
        failure_decisions = sum(d.get("failure_count", 0) for d in self.decisions)

        total_decisions = skip_decisions + escalate_decisions + success_decisions + failure_decisions

        return {
            "total_decisions": total_decisions,
            "decision_breakdown": {
                "skipped": skip_decisions,
                "escalated": escalate_decisions,
                "fixed_successfully": success_decisions,
                "fix_failed": failure_decisions,
            },
            "decision_percentages": {
                "skip_rate": f"{(skip_decisions / total_decisions * 100):.1f}%" if total_decisions > 0 else "0%",
                "escalation_rate": f"{(escalate_decisions / total_decisions * 100):.1f}%" if total_decisions > 0 else "0%",
                "success_rate": f"{(success_decisions / total_decisions * 100):.1f}%" if total_decisions > 0 else "0%",
                "failure_rate": f"{(failure_decisions / total_decisions * 100):.1f}%" if total_decisions > 0 else "0%",
            },
            "confidence_score": self._calculate_confidence_score(
                skip_decisions, escalate_decisions, success_decisions, failure_decisions
            )
        }

    def _calculate_confidence_score(self, skipped: int, escalated: int, success: int, failed: int) -> str:
        """Calculate overall confidence score for JADE's decisions."""
        total = skipped + escalated + success + failed
        if total == 0:
            return "N/A"

        # High-confidence decisions: skips (correct avoidance) and successes
        high_confidence = skipped + success

        # Low-confidence indicators: escalations (unsure) and failures (wrong decisions)
        low_confidence = escalated + failed

        confidence_ratio = high_confidence / total if total > 0 else 0

        if confidence_ratio >= 0.85:
            return f"HIGH ({confidence_ratio:.2%})"
        elif confidence_ratio >= 0.65:
            return f"MEDIUM ({confidence_ratio:.2%})"
        else:
            return f"LOW ({confidence_ratio:.2%})"

    def generate_explainability_report(self) -> Dict[str, Any]:
        """Generate comprehensive explainability report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "logs_directory": str(self.logs_dir),
            "total_decisions_analyzed": len(self.decisions),
            "confidence_analysis": self.get_decision_confidence_analysis(),
            "skip_explanations": self.explain_skip_decisions(),
            "escalation_explanations": self.explain_escalation_decisions(),
            "failure_explanations": self.explain_failure_patterns(),
            "recommendations": self._generate_explainability_recommendations()
        }

        return report

    def _generate_explainability_recommendations(self) -> List[str]:
        """Generate recommendations based on decision analysis."""
        recommendations = []

        confidence_analysis = self.get_decision_confidence_analysis()
        skip_analysis = self.explain_skip_decisions()
        failure_analysis = self.explain_failure_patterns()

        # Check confidence score
        conf_score = confidence_analysis.get("confidence_score", "N/A")
        if "LOW" in conf_score:
            recommendations.append(
                f"JADE's confidence is {conf_score} - Consider additional training or human review for edge cases"
            )

        # Check skip reasons
        top_skip_reason = skip_analysis.get("top_reason", ("none", 0))
        if top_skip_reason[0] == "backup_path_detected":
            recommendations.append(
                f"Most skips ({top_skip_reason[1]}) are backup paths - Consider cleaning git history"
            )
        elif top_skip_reason[0] == "false_positive_detected":
            recommendations.append(
                f"Many false positives detected ({top_skip_reason[1]}) - Scanner configuration may need tuning"
            )

        # Check failure patterns
        top_failure_reason = failure_analysis.get("top_reason", ("none", 0))
        if top_failure_reason[0] == "file_not_found":
            recommendations.append(
                f"Most failures ({top_failure_reason[1]}) are file not found - Path resolution needs improvement"
            )
        elif top_failure_reason[0] == "syntax_error":
            recommendations.append(
                f"Syntax errors detected ({top_failure_reason[1]}) - Fix generation quality needs improvement"
            )

        if not recommendations:
            recommendations.append("JADE's decisions are well-explained and consistent!")

        return recommendations


def main():
    """Standalone execution for explainability analysis."""
    import argparse

    parser = argparse.ArgumentParser(
        description="GP-CLARIFY: JADE Decision Explainability (AWS SageMaker Clarify)"
    )
    parser.add_argument(
        "logs_dir",
        help="Path to JADE logs directory (e.g., logs/01-instance)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output path for explainability report (JSON)"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("GP-CLARIFY: JADE Decision Explainability")
    print("AWS SageMaker Clarify Equivalent")
    print("=" * 80)
    print()

    # Load and analyze decisions
    explainer = JadeDecisionExplainer(args.logs_dir)
    explainer.load_decisions("fixes")

    report = explainer.generate_explainability_report()

    # Print summary
    print(f"\nExplainability Analysis Complete!")
    print(f"  Total Decisions: {report['total_decisions_analyzed']}")
    print(f"  Confidence Score: {report['confidence_analysis']['confidence_score']}")
    print()

    print("Skip Decisions:")
    print(f"  Total Skipped: {report['skip_explanations']['total_skipped']}")
    print(f"  Top Reason: {report['skip_explanations']['top_reason'][0]} ({report['skip_explanations']['top_reason'][1]})")
    print()

    print("Escalation Decisions:")
    print(f"  Total Escalated: {report['escalation_explanations']['total_escalated']}")
    print(f"  Top Reason: {report['escalation_explanations']['top_reason'][0]} ({report['escalation_explanations']['top_reason'][1]})")
    print()

    print("Failure Patterns:")
    print(f"  Total Failures: {report['failure_explanations']['total_failures']}")
    print(f"  Top Reason: {report['failure_explanations']['top_reason'][0]} ({report['failure_explanations']['top_reason'][1]})")
    print()

    print("Recommendations:")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"  {i}. {rec}")
    print()

    # Save report
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to: {args.output}")

    return report


if __name__ == "__main__":
    main()
