"""
JADE Rank Decision Capability
Provides ML-enhanced security finding classification for JADE

This capability bridges the ML module with JADE's decision flow:
- Integrates sklearn classifiers with rule-based classification
- Provides confidence-calibrated rank predictions
- Enables learning from operational feedback
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Relative imports (now part of ml module)
from .hybrid_classifier import HybridRankClassifier
from .rank_classifier_ml import Rank


@dataclass
class RankDecision:
    """A rank decision with full context for JADE reasoning"""
    finding_id: str
    rank: str  # E/D/C/B/S
    confidence: float
    decision_source: str  # "rule", "ml", "ensemble"
    action: str  # "auto_fix", "request_approval", "escalate"
    reasoning: str
    fix_complexity: str
    requires_human: bool
    model_version: str = "hybrid-v1"


class RankDecisionCapability:
    """
    JADE capability for ML-enhanced rank classification.

    Used by JADE to make intelligent decisions about:
    - Which findings to auto-fix (E-D rank)
    - Which findings need approval (C rank)
    - Which findings to escalate (B-S rank)
    """

    def __init__(
        self,
        model_path: Path = None,
        enable_learning: bool = True,
        confidence_threshold: float = 0.70
    ):
        """
        Initialize rank decision capability.

        Args:
            model_path: Path to trained sklearn model
            enable_learning: Whether to log decisions for future training
            confidence_threshold: Minimum confidence for autonomous decisions
        """
        self.confidence_threshold = confidence_threshold
        self.enable_learning = enable_learning

        # Initialize hybrid classifier
        self.classifier = HybridRankClassifier(
            ml_model_path=model_path,
            rule_confidence_threshold=0.75,
            ml_confidence_threshold=confidence_threshold,
            use_ensemble=True
        )

        # Decision log for learning
        self.decision_log: List[Dict] = []

        # Statistics tracking
        self.stats = {
            "total_decisions": 0,
            "by_rank": {"E": 0, "D": 0, "C": 0, "B": 0, "S": 0},
            "by_source": {"rule": 0, "ml": 0, "ensemble": 0},
            "auto_fixed": 0,
            "escalated": 0,
            "awaiting_approval": 0
        }

    def decide(self, finding: Dict[str, Any]) -> RankDecision:
        """
        Make a rank decision for a security finding.

        Args:
            finding: Security finding dict from scanner

        Returns:
            RankDecision with full reasoning
        """
        # Generate finding ID if not present
        finding_id = finding.get("id") or self._generate_finding_id(finding)

        # Get classification
        result = self.classifier.classify(finding)

        # Build decision
        decision = RankDecision(
            finding_id=finding_id,
            rank=result.rank.value,
            confidence=result.confidence,
            decision_source=result.source,
            action=result.suggested_action,
            reasoning=result.reason,
            fix_complexity=result.fix_complexity,
            requires_human=result.escalate or result.requires_approval
        )

        # Update stats
        self._update_stats(decision)

        # Log for learning
        if self.enable_learning:
            self._log_decision(finding, decision)

        return decision

    def decide_batch(self, findings: List[Dict[str, Any]]) -> List[RankDecision]:
        """Make rank decisions for multiple findings."""
        return [self.decide(f) for f in findings]

    def get_action_groups(
        self,
        decisions: List[RankDecision]
    ) -> Dict[str, List[RankDecision]]:
        """
        Group decisions by action for JADE to process.

        Returns:
            Dict with keys: "auto_fix", "request_approval", "escalate"
        """
        groups = {
            "auto_fix": [],       # E-D rank (immediate action)
            "request_approval": [],  # C rank (needs human approval)
            "escalate": []         # B-S rank (human review required)
        }

        for d in decisions:
            groups[d.action].append(d)

        return groups

    def should_proceed_autonomously(self, decisions: List[RankDecision]) -> bool:
        """
        Determine if JADE can proceed without human intervention.

        Returns True if all findings are E-D rank with high confidence.
        """
        if not decisions:
            return True

        for d in decisions:
            # Need human if any finding requires it
            if d.requires_human:
                return False

            # Need human if confidence is too low
            if d.confidence < self.confidence_threshold:
                return False

            # Need human for C+ rank
            if d.rank in ["C", "B", "S"]:
                return False

        return True

    def get_escalation_summary(
        self,
        decisions: List[RankDecision]
    ) -> str:
        """
        Generate summary for human escalation.

        Used when JADE needs to notify humans about B-S rank findings.
        """
        groups = self.get_action_groups(decisions)
        escalations = groups["escalate"]
        approvals = groups["request_approval"]

        if not escalations and not approvals:
            return "No escalations required. All findings can be auto-fixed."

        lines = []

        if escalations:
            lines.append(f"## Escalations ({len(escalations)} findings)")
            for d in escalations:
                lines.append(f"- [{d.rank}] {d.finding_id}: {d.reasoning}")

        if approvals:
            lines.append(f"\n## Pending Approval ({len(approvals)} findings)")
            for d in approvals:
                lines.append(f"- [{d.rank}] {d.finding_id}: {d.reasoning}")

        return "\n".join(lines)

    def get_stats_summary(self) -> Dict[str, Any]:
        """Get statistics summary for reporting."""
        total = self.stats["total_decisions"]
        if total == 0:
            return {"message": "No decisions made yet"}

        return {
            "total_decisions": total,
            "rank_distribution": self.stats["by_rank"],
            "decision_sources": self.stats["by_source"],
            "automation_rate": (
                (self.stats["auto_fixed"]) /
                total * 100 if total else 0
            ),
            "human_intervention_rate": (
                (self.stats["escalated"] + self.stats["awaiting_approval"]) /
                total * 100 if total else 0
            )
        }

    def record_feedback(
        self,
        finding_id: str,
        actual_rank: str,
        feedback_source: str = "human"
    ):
        """
        Record feedback on a decision for model improvement.

        Args:
            finding_id: The finding that was classified
            actual_rank: The correct rank (from human review)
            feedback_source: Who provided the feedback
        """
        # Find the decision in the log
        for entry in self.decision_log:
            if entry["decision"]["finding_id"] == finding_id:
                entry["feedback"] = {
                    "actual_rank": actual_rank,
                    "source": feedback_source,
                    "timestamp": datetime.now().isoformat(),
                    "was_correct": entry["decision"]["rank"] == actual_rank
                }
                break

    def export_training_data(self, output_path: Path = None) -> List[Dict]:
        """
        Export logged decisions as training data.

        Returns examples in format compatible with RankClassifierTrainer.
        """
        training_examples = []

        for entry in self.decision_log:
            # Use feedback if available, otherwise use decision
            if entry.get("feedback"):
                rank = entry["feedback"]["actual_rank"]
                source = f"feedback_{entry['feedback']['source']}"
            else:
                rank = entry["decision"]["rank"]
                source = f"decision_{entry['decision']['decision_source']}"

            training_examples.append({
                "finding": entry["finding"],
                "rank": rank,
                "source": source,
                "timestamp": entry["timestamp"]
            })

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                for ex in training_examples:
                    f.write(json.dumps(ex) + "\n")

        return training_examples

    def _generate_finding_id(self, finding: Dict) -> str:
        """Generate unique ID for a finding."""
        scanner = finding.get("scanner", "unknown")
        rule = finding.get("rule_id", "unknown")
        file = finding.get("file", "unknown")
        return f"{scanner}:{rule}:{Path(file).name}"

    def _update_stats(self, decision: RankDecision):
        """Update statistics counters."""
        self.stats["total_decisions"] += 1
        self.stats["by_rank"][decision.rank] += 1
        self.stats["by_source"][decision.decision_source] += 1

        if decision.action == "auto_fix":
            self.stats["auto_fixed"] += 1
        elif decision.action == "escalate":
            self.stats["escalated"] += 1
        elif decision.action == "request_approval":
            self.stats["awaiting_approval"] += 1

    def _log_decision(self, finding: Dict, decision: RankDecision):
        """Log decision for future training."""
        self.decision_log.append({
            "finding": finding,
            "decision": asdict(decision),
            "timestamp": datetime.now().isoformat()
        })


# Tool wrapper for AgenticEngine integration
def create_rank_decision_tool(capability: RankDecisionCapability):
    """
    Create a tool definition for the AgenticEngine.

    This allows JADE to use rank classification in its reasoning loop.
    """
    def execute_rank_decision(finding: Dict = None, findings: List[Dict] = None) -> Dict:
        if findings:
            decisions = capability.decide_batch(findings)
            return {
                "decisions": [asdict(d) for d in decisions],
                "groups": {
                    k: [asdict(d) for d in v]
                    for k, v in capability.get_action_groups(decisions).items()
                },
                "can_proceed_autonomously": capability.should_proceed_autonomously(decisions),
                "summary": capability.get_escalation_summary(decisions)
            }
        elif finding:
            decision = capability.decide(finding)
            return {
                "decision": asdict(decision),
                "can_proceed_autonomously": not decision.requires_human
            }
        else:
            return {"error": "No finding or findings provided"}

    return {
        "name": "classify_finding",
        "description": "Classify a security finding into E/D/C/B/S rank and determine action",
        "parameters": {
            "finding": {
                "type": "object",
                "description": "Single security finding to classify"
            },
            "findings": {
                "type": "array",
                "description": "Multiple findings to classify in batch"
            }
        },
        "execute": execute_rank_decision
    }


# CLI for testing
if __name__ == "__main__":
    cap = RankDecisionCapability()

    # Test findings
    test_findings = [
        {
            "scanner": "gitleaks",
            "rule_id": "generic-api-key",
            "severity": "HIGH",
            "description": "API key detected",
            "file": "config.py"
        },
        {
            "scanner": "trivy",
            "rule_id": "CVE-2024-1234",
            "severity": "CRITICAL",
            "description": "RCE vulnerability",
            "file": "package.json",
            "fixed_version": "4.17.21"
        },
        {
            "scanner": "prowler",
            "rule_id": "iam-policy",
            "severity": "CRITICAL",
            "description": "IAM wildcard permissions",
            "file": "iam.tf"
        }
    ]

    print("=" * 60)
    print("JADE Rank Decision Capability Test")
    print("=" * 60)

    decisions = cap.decide_batch(test_findings)
    for d in decisions:
        print(f"\n{d.finding_id}")
        print(f"  Rank: {d.rank} (conf: {d.confidence:.0%})")
        print(f"  Action: {d.action}")
        print(f"  Source: {d.decision_source}")
        print(f"  Human needed: {d.requires_human}")

    print("\n" + "=" * 60)
    groups = cap.get_action_groups(decisions)
    print(f"Auto-fix: {len(groups['auto_fix'])}")
    print(f"Approval needed: {len(groups['request_approval'])}")
    print(f"Escalate: {len(groups['escalate'])}")
    print(f"\nCan proceed autonomously: {cap.should_proceed_autonomously(decisions)}")

    print("\n" + "=" * 60)
    print("Stats:", cap.get_stats_summary())
