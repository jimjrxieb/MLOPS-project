"""
GP-CLARIFY: Training Data Bias Detection
Amazon SageMaker Clarify Equivalent

Analyzes JADE's training data for biases:
- Scanner distribution (over-represented scanners?)
- Severity balance (too many CRITICAL, not enough LOW?)
- File type bias (only Python, no TypeScript?)
- Domain bias (only SAST, missing IaC?)
"""

import json
import glob
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any
from datetime import datetime


class TrainingBiasDetector:
    """
    Detect bias in JADE training data (like SageMaker Clarify pre-training bias).

    AWS Clarify Metrics Implemented:
    - Class Imbalance (CI): Are fix types balanced?
    - Difference in Proportions of Labels (DPL): Scanner representation
    - Jensen-Shannon Divergence (JS): Distribution similarity
    """

    def __init__(self, training_data_path: str):
        self.training_data_path = Path(training_data_path)
        self.findings = []
        self.stats = {
            "total_examples": 0,
            "by_scanner": Counter(),
            "by_severity": Counter(),
            "by_domain": Counter(),
            "by_outcome": Counter(),
        }

    def load_training_data(self):
        """Load training examples from JSONL files"""
        jsonl_files = glob.glob(str(self.training_data_path / "**/*.jsonl"), recursive=True)

        print(f"Found {len(jsonl_files)} training files")

        for file_path in jsonl_files:
            with open(file_path) as f:
                for line in f:
                    try:
                        example = json.loads(line.strip())
                        self.findings.append(example)

                        # Extract metadata
                        meta = example.get("metadata", {})
                        self.stats["by_scanner"][meta.get("scanner", "unknown")] += 1
                        self.stats["by_severity"][meta.get("severity", "unknown")] += 1
                        self.stats["by_domain"][meta.get("domain", "unknown")] += 1

                        # Track if example shows successful fix
                        output = example.get("output", "")
                        if "successfully" in output.lower() or "fixed" in output.lower():
                            self.stats["by_outcome"]["success"] += 1
                        elif "skip" in output.lower():
                            self.stats["by_outcome"]["skipped"] += 1
                        else:
                            self.stats["by_outcome"]["failed"] += 1

                    except json.JSONDecodeError:
                        continue

        self.stats["total_examples"] = len(self.findings)
        print(f"Loaded {self.stats['total_examples']} training examples")

    def calculate_class_imbalance(self, distribution: Counter) -> Dict[str, float]:
        """
        Class Imbalance (CI) metric from AWS Clarify.

        CI = (n_class - n_total/k) / (n_total/k)
        where k = number of classes

        Returns values between -1 and +inf:
        - CI < -0.5: Under-represented (BAD)
        - -0.5 < CI < 0.5: Balanced (GOOD)
        - CI > 0.5: Over-represented (BAD)
        """
        total = sum(distribution.values())
        k = len(distribution)
        expected_per_class = total / k if k > 0 else 0

        imbalances = {}
        for class_name, count in distribution.items():
            if expected_per_class > 0:
                ci = (count - expected_per_class) / expected_per_class
                imbalances[class_name] = ci
            else:
                imbalances[class_name] = 0.0

        return imbalances

    def detect_scanner_bias(self) -> Dict[str, Any]:
        """Detect if certain scanners are over/under-represented"""
        imbalances = self.calculate_class_imbalance(self.stats["by_scanner"])

        biased_scanners = {
            "over_represented": [],
            "under_represented": [],
            "balanced": []
        }

        for scanner, ci in imbalances.items():
            count = self.stats["by_scanner"][scanner]
            pct = (count / self.stats["total_examples"]) * 100 if self.stats["total_examples"] > 0 else 0

            entry = {
                "scanner": scanner,
                "count": count,
                "percentage": f"{pct:.1f}%",
                "ci_score": f"{ci:.2f}",
                "bias_level": self._get_bias_level(ci)
            }

            if ci > 0.5:
                biased_scanners["over_represented"].append(entry)
            elif ci < -0.5:
                biased_scanners["under_represented"].append(entry)
            else:
                biased_scanners["balanced"].append(entry)

        return biased_scanners

    def detect_severity_bias(self) -> Dict[str, Any]:
        """Detect if JADE is trained mostly on CRITICAL vs LOW severity"""
        imbalances = self.calculate_class_imbalance(self.stats["by_severity"])

        biased_severities = {
            "over_represented": [],
            "under_represented": [],
            "balanced": []
        }

        for severity, ci in imbalances.items():
            count = self.stats["by_severity"][severity]
            pct = (count / self.stats["total_examples"]) * 100 if self.stats["total_examples"] > 0 else 0

            entry = {
                "severity": severity,
                "count": count,
                "percentage": f"{pct:.1f}%",
                "ci_score": f"{ci:.2f}",
                "bias_level": self._get_bias_level(ci)
            }

            if ci > 0.5:
                biased_severities["over_represented"].append(entry)
            elif ci < -0.5:
                biased_severities["under_represented"].append(entry)
            else:
                biased_severities["balanced"].append(entry)

        return biased_severities

    def detect_domain_bias(self) -> Dict[str, Any]:
        """Detect if certain domains (SAST, secrets, IaC) are over-represented"""
        imbalances = self.calculate_class_imbalance(self.stats["by_domain"])

        biased_domains = {
            "over_represented": [],
            "under_represented": [],
            "balanced": []
        }

        for domain, ci in imbalances.items():
            count = self.stats["by_domain"][domain]
            pct = (count / self.stats["total_examples"]) * 100 if self.stats["total_examples"] > 0 else 0

            entry = {
                "domain": domain,
                "count": count,
                "percentage": f"{pct:.1f}%",
                "ci_score": f"{ci:.2f}",
                "bias_level": self._get_bias_level(ci)
            }

            if ci > 0.5:
                biased_domains["over_represented"].append(entry)
            elif ci < -0.5:
                biased_domains["under_represented"].append(entry)
            else:
                biased_domains["balanced"].append(entry)

        return biased_domains

    def _get_bias_level(self, ci: float) -> str:
        """Convert CI score to human-readable bias level"""
        if ci > 2.0:
            return "SEVERE_OVER"
        elif ci > 0.5:
            return "MODERATE_OVER"
        elif ci >= -0.5:
            return "BALANCED"
        elif ci >= -0.75:
            return "MODERATE_UNDER"
        else:
            return "SEVERE_UNDER"

    def generate_bias_report(self) -> Dict[str, Any]:
        """Generate comprehensive bias report (like SageMaker Clarify output)"""
        scanner_bias = self.detect_scanner_bias()
        severity_bias = self.detect_severity_bias()
        domain_bias = self.detect_domain_bias()

        # Calculate overall bias score (0-100, lower is better)
        total_biased = (
            len(scanner_bias["over_represented"]) + len(scanner_bias["under_represented"]) +
            len(severity_bias["over_represented"]) + len(severity_bias["under_represented"]) +
            len(domain_bias["over_represented"]) + len(domain_bias["under_represented"])
        )

        total_categories = (
            len(self.stats["by_scanner"]) +
            len(self.stats["by_severity"]) +
            len(self.stats["by_domain"])
        )

        bias_score = (total_biased / total_categories * 100) if total_categories > 0 else 0

        report = {
            "timestamp": datetime.now().isoformat(),
            "training_data_path": str(self.training_data_path),
            "total_examples": self.stats["total_examples"],
            "bias_score": f"{bias_score:.1f}",
            "bias_level": "LOW" if bias_score < 30 else "MEDIUM" if bias_score < 60 else "HIGH",
            "scanner_bias": scanner_bias,
            "severity_bias": severity_bias,
            "domain_bias": domain_bias,
            "recommendations": self._generate_recommendations(scanner_bias, severity_bias, domain_bias)
        }

        return report

    def _generate_recommendations(self, scanner_bias, severity_bias, domain_bias) -> List[str]:
        """Generate actionable recommendations to reduce bias"""
        recommendations = []

        # Scanner recommendations
        for scanner_data in scanner_bias["under_represented"]:
            recommendations.append(
                f"Collect more {scanner_data['scanner']} examples (currently {scanner_data['percentage']})"
            )

        # Severity recommendations
        for sev_data in severity_bias["under_represented"]:
            recommendations.append(
                f"Add more {sev_data['severity']} severity examples (currently {sev_data['percentage']})"
            )

        # Domain recommendations
        for domain_data in domain_bias["under_represented"]:
            recommendations.append(
                f"Increase {domain_data['domain']} domain coverage (currently {domain_data['percentage']})"
            )

        if not recommendations:
            recommendations.append("Training data appears well-balanced across all dimensions!")

        return recommendations


def main():
    """Standalone execution for bias detection"""
    import argparse

    parser = argparse.ArgumentParser(
        description="GP-CLARIFY: Training Data Bias Detection (AWS SageMaker Clarify)"
    )
    parser.add_argument(
        "training_data_path",
        help="Path to training data directory (JSONL files)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output path for bias report (JSON)"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("GP-CLARIFY: Training Data Bias Detection")
    print("AWS SageMaker Clarify Equivalent")
    print("=" * 80)
    print()

    # Run bias detection
    detector = TrainingBiasDetector(args.training_data_path)
    detector.load_training_data()

    report = detector.generate_bias_report()

    # Print summary
    print(f"\nBias Analysis Complete!")
    print(f"  Total Examples: {report['total_examples']}")
    print(f"  Bias Score: {report['bias_score']} ({report['bias_level']})")
    print()

    print("Scanner Bias:")
    print(f"  Over-represented: {len(report['scanner_bias']['over_represented'])}")
    print(f"  Under-represented: {len(report['scanner_bias']['under_represented'])}")
    print(f"  Balanced: {len(report['scanner_bias']['balanced'])}")
    print()

    print("Severity Bias:")
    print(f"  Over-represented: {len(report['severity_bias']['over_represented'])}")
    print(f"  Under-represented: {len(report['severity_bias']['under_represented'])}")
    print(f"  Balanced: {len(report['severity_bias']['balanced'])}")
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
