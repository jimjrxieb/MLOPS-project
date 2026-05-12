"""
Hybrid Rank Classifier
Combines rule-based and ML-based classification for optimal accuracy

The hybrid approach:
1. Rule-based first pass (fast, interpretable)
2. ML second pass when rule confidence < threshold
3. Ensemble voting when both disagree
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add GP-CONSULTING to path for rule classifier
GP_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(GP_ROOT / "GP-CONSULTING" / "3-Runtime-Scans-NPC"))

from .rank_classifier_ml import MLRankClassifier, Rank


@dataclass
class HybridClassificationResult:
    """Result from hybrid classifier with full provenance"""
    rank: Rank
    confidence: float
    source: str  # "rule", "ml", "ensemble"
    rule_rank: Optional[Rank]
    rule_confidence: float
    ml_rank: Optional[Rank]
    ml_confidence: float
    reason: str
    auto_fixable: bool
    requires_approval: bool
    escalate: bool
    suggested_action: str
    fix_complexity: str


class HybridRankClassifier:
    """
    Combines rule-based and ML classification for security findings.

    Strategy:
    - Use rule-based first (fast, interpretable, handles known patterns)
    - Fall back to ML when:
      - Rule confidence is low (< threshold)
      - Finding doesn't match known patterns
      - C-rank ambiguous cases (where JADE fallback was used before)
    - Use ensemble (voting) when both methods disagree significantly
    """

    def __init__(
        self,
        ml_model_path: Path = None,
        rule_confidence_threshold: float = 0.75,
        ml_confidence_threshold: float = 0.70,
        use_ensemble: bool = True
    ):
        """
        Initialize hybrid classifier.

        Args:
            ml_model_path: Path to trained sklearn model (optional)
            rule_confidence_threshold: Use ML when rule confidence below this
            ml_confidence_threshold: Trust ML when confidence above this
            use_ensemble: Whether to use voting when methods disagree
        """
        self.rule_threshold = rule_confidence_threshold
        self.ml_threshold = ml_confidence_threshold
        self.use_ensemble = use_ensemble

        # Initialize rule-based classifier
        try:
            from rank_classifier import RankClassifier, ClassificationResult
            self.rule_classifier = RankClassifier(use_jade_fallback=False)
            self.RuleResult = ClassificationResult
        except ImportError:
            print("Warning: Could not import rule classifier, using ML only")
            self.rule_classifier = None

        # Initialize ML classifier
        self.ml_classifier = None
        if ml_model_path and ml_model_path.exists():
            self.ml_classifier = MLRankClassifier.load(ml_model_path)
        else:
            # Try default path
            default_path = GP_ROOT / "GP-MODEL-OPS" / "1-GP-GLUE" / "rank-training-data" / "rank_classifier.joblib"
            if default_path.exists():
                self.ml_classifier = MLRankClassifier.load(default_path)

    def classify(self, finding: Dict[str, Any]) -> HybridClassificationResult:
        """
        Classify a security finding using hybrid approach.

        Args:
            finding: Security finding dict

        Returns:
            HybridClassificationResult with full provenance
        """
        rule_rank = None
        rule_confidence = 0.0
        rule_result = None
        ml_rank = None
        ml_confidence = 0.0
        ml_result = None

        # Step 1: Rule-based classification
        if self.rule_classifier:
            rule_result = self.rule_classifier.classify(finding)
            rule_rank = rule_result.rank
            rule_confidence = rule_result.confidence

        # Step 2: ML classification (if available)
        if self.ml_classifier:
            ml_result = self.ml_classifier.predict(finding)
            ml_rank = ml_result.rank
            ml_confidence = ml_result.confidence

        # Step 3: Decision logic
        final_rank, source, reason = self._decide(
            rule_rank, rule_confidence,
            ml_rank, ml_confidence,
            finding
        )

        # Build result with full provenance
        return self._build_result(
            final_rank=final_rank,
            source=source,
            reason=reason,
            rule_rank=rule_rank,
            rule_confidence=rule_confidence,
            ml_rank=ml_rank,
            ml_confidence=ml_confidence,
            rule_result=rule_result
        )

    def _decide(
        self,
        rule_rank: Optional[Rank],
        rule_conf: float,
        ml_rank: Optional[Rank],
        ml_conf: float,
        finding: Dict
    ) -> Tuple[Rank, str, str]:
        """
        Decide final rank based on rule and ML outputs.

        Returns:
            Tuple of (final_rank, source, reason)
        """
        # Case 1: Only rule-based available
        if rule_rank and not ml_rank:
            return rule_rank, "rule", f"Rule-based classification: {rule_rank.value}"

        # Case 2: Only ML available
        if ml_rank and not rule_rank:
            if ml_conf >= self.ml_threshold:
                return ml_rank, "ml", f"ML classification (conf: {ml_conf:.0%})"
            else:
                # Low confidence, default to C-rank (needs review)
                return Rank.C, "ml", f"ML low confidence ({ml_conf:.0%}), defaulting to C-rank"

        # Case 3: Both available
        if rule_rank and ml_rank:
            # If they agree, high confidence
            if rule_rank == ml_rank:
                combined_conf = (rule_conf + ml_conf) / 2
                return rule_rank, "ensemble", f"Both agree: {rule_rank.value} (conf: {combined_conf:.0%})"

            # Rule is high confidence - trust it
            if rule_conf >= self.rule_threshold:
                return rule_rank, "rule", f"High-confidence rule: {rule_rank.value} ({rule_conf:.0%})"

            # ML is high confidence and rule is low
            if ml_conf >= self.ml_threshold and rule_conf < self.rule_threshold:
                return ml_rank, "ml", f"ML override: {ml_rank.value} (rule conf: {rule_conf:.0%})"

            # Both medium confidence but disagree - use ensemble voting
            if self.use_ensemble:
                return self._ensemble_vote(rule_rank, rule_conf, ml_rank, ml_conf)

            # Default: trust rule-based (more interpretable)
            return rule_rank, "rule", f"Default to rule: {rule_rank.value}"

        # Case 4: Neither available (shouldn't happen)
        return Rank.C, "default", "No classifier available, defaulting to C-rank"

    def _ensemble_vote(
        self,
        rule_rank: Rank,
        rule_conf: float,
        ml_rank: Rank,
        ml_conf: float
    ) -> Tuple[Rank, str, str]:
        """
        Weighted voting between rule and ML classifiers.
        """
        # Calculate weighted scores for each rank
        ranks = [Rank.E, Rank.D, Rank.C, Rank.B, Rank.S]
        scores = {r: 0.0 for r in ranks}

        # Rule vote (weighted by confidence)
        scores[rule_rank] += rule_conf

        # ML vote (weighted by confidence)
        scores[ml_rank] += ml_conf

        # Find winner
        winner = max(scores, key=scores.get)
        total_conf = scores[winner] / (rule_conf + ml_conf)

        return winner, "ensemble", f"Ensemble vote: {winner.value} (weighted conf: {total_conf:.0%})"

    def _build_result(
        self,
        final_rank: Rank,
        source: str,
        reason: str,
        rule_rank: Optional[Rank],
        rule_confidence: float,
        ml_rank: Optional[Rank],
        ml_confidence: float,
        rule_result=None
    ) -> HybridClassificationResult:
        """Build final result with actions based on rank."""

        # Use rule result's action mapping if available
        if rule_result:
            auto_fixable = rule_result.auto_fixable
            requires_approval = rule_result.requires_approval
            escalate = rule_result.escalate
            suggested_action = rule_result.suggested_action
            fix_complexity = rule_result.fix_complexity
        else:
            # Default action mapping
            if final_rank in [Rank.E, Rank.D]:
                auto_fixable = True
                requires_approval = False
                escalate = False
                suggested_action = "auto_fix"
                fix_complexity = "trivial" if final_rank == Rank.E else "simple"
            elif final_rank == Rank.C:
                auto_fixable = True
                requires_approval = True
                escalate = False
                suggested_action = "request_approval"
                fix_complexity = "moderate"
            else:  # B or S
                auto_fixable = False
                requires_approval = False
                escalate = True
                suggested_action = "escalate"
                fix_complexity = "complex" if final_rank == Rank.B else "architectural"

        # Combine confidence
        confidence = max(rule_confidence, ml_confidence) if source == "ensemble" else (
            rule_confidence if source == "rule" else ml_confidence
        )

        return HybridClassificationResult(
            rank=final_rank,
            confidence=confidence,
            source=source,
            rule_rank=rule_rank,
            rule_confidence=rule_confidence,
            ml_rank=ml_rank,
            ml_confidence=ml_confidence,
            reason=reason,
            auto_fixable=auto_fixable,
            requires_approval=requires_approval,
            escalate=escalate,
            suggested_action=suggested_action,
            fix_complexity=fix_complexity
        )

    def classify_batch(
        self,
        findings: List[Dict[str, Any]]
    ) -> List[HybridClassificationResult]:
        """Classify multiple findings."""
        return [self.classify(f) for f in findings]

    def get_stats(
        self,
        results: List[HybridClassificationResult]
    ) -> Dict[str, Any]:
        """Get classification statistics."""
        stats = {
            "total": len(results),
            "by_rank": {"E": 0, "D": 0, "C": 0, "B": 0, "S": 0},
            "by_source": {"rule": 0, "ml": 0, "ensemble": 0, "default": 0},
            "auto_fixable": 0,
            "requires_approval": 0,
            "escalate": 0,
            "avg_confidence": 0.0
        }

        if not results:
            return stats

        for r in results:
            stats["by_rank"][r.rank.value] += 1
            stats["by_source"][r.source] += 1
            if r.auto_fixable:
                stats["auto_fixable"] += 1
            if r.requires_approval:
                stats["requires_approval"] += 1
            if r.escalate:
                stats["escalate"] += 1
            stats["avg_confidence"] += r.confidence

        stats["avg_confidence"] /= len(results)
        return stats


# CLI for testing
if __name__ == "__main__":
    import json

    classifier = HybridRankClassifier()

    # Test findings
    test_findings = [
        {
            "scanner": "gitleaks",
            "rule_id": "generic-api-key",
            "severity": "HIGH",
            "description": "API key detected in source code",
            "file": "config.py"
        },
        {
            "scanner": "trivy",
            "rule_id": "CVE-2024-1234",
            "severity": "CRITICAL",
            "description": "Remote code execution in lodash",
            "file": "package.json",
            "fixed_version": "4.17.21"
        },
        {
            "scanner": "kubescape",
            "rule_id": "C-0017",
            "severity": "MEDIUM",
            "description": "Container running as root",
            "file": "deployment.yaml"
        },
        {
            "scanner": "prowler",
            "rule_id": "iam-policy-too-permissive",
            "severity": "CRITICAL",
            "description": "IAM policy allows * on all resources",
            "file": "iam.tf"
        },
    ]

    print("=" * 70)
    print("HybridRankClassifier Test")
    print("=" * 70)

    results = []
    for finding in test_findings:
        result = classifier.classify(finding)
        results.append(result)

        print(f"\n{finding['scanner']}: {finding['rule_id']}")
        print(f"  Final Rank: {result.rank.value} ({result.confidence:.0%})")
        print(f"  Source: {result.source}")
        print(f"  Rule: {result.rule_rank.value if result.rule_rank else 'N/A'} ({result.rule_confidence:.0%})")
        print(f"  ML: {result.ml_rank.value if result.ml_rank else 'N/A'} ({result.ml_confidence:.0%})")
        print(f"  Action: {result.suggested_action}")
        print(f"  Reason: {result.reason}")

    print("\n" + "=" * 70)
    stats = classifier.get_stats(results)
    print(f"Summary:")
    print(f"  By Rank: {stats['by_rank']}")
    print(f"  By Source: {stats['by_source']}")
    print(f"  Auto-fixable: {stats['auto_fixable']}/{stats['total']}")
    print(f"  Avg Confidence: {stats['avg_confidence']:.0%}")
