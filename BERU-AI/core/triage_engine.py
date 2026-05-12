"""
Triage Engine — Severity + Context -> Priority + Action

Takes normalized findings and produces triage decisions:
priority (P1-P4), immediate action, remediation, NIST mapping.
"""

from typing import Any, Dict, List, Optional

from .nist_mapper import NISTMapper


# Severity + context -> priority mapping
_SEVERITY_TO_BASE_PRIORITY = {
    "CRITICAL": "P1",
    "HIGH": "P2",
    "MEDIUM": "P3",
    "LOW": "P4",
    "INFO": "P4",
    "UNKNOWN": "P3",
}

# Context keywords that escalate priority
_ESCALATION_KEYWORDS = [
    "production", "prod", "pii", "phi", "pci", "customer data",
    "database", "rds", "secrets", "credentials", "public",
    "internet-facing", "external", "0.0.0.0",
]


class TriageEngine:
    """Produce triage decisions from normalized findings."""

    def __init__(self):
        self.nist_mapper = NISTMapper()

    def triage(self, finding: Dict[str, Any],
               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Triage a single finding.

        Args:
            finding: Normalized finding from FindingsIngestion
            context: Optional environment context (e.g., {"environment": "production", "data_classification": "PII"})

        Returns:
            Triage decision dict matching beru_risk_summary.json schema
        """
        context = context or {}
        severity = finding.get("severity", "UNKNOWN")

        # Base priority from severity
        priority = _SEVERITY_TO_BASE_PRIORITY.get(severity, "P3")

        # Escalate based on context
        priority = self._apply_escalation(priority, finding, context)

        # NIST mapping
        nist_result = self.nist_mapper.map_finding(finding)

        # Build severity context string
        env = context.get("environment", "unknown")
        data_class = context.get("data_classification", "")
        severity_context = f"{severity} in {env} environment"
        if data_class:
            severity_context += f" with {data_class} workloads"

        return {
            "finding_id": finding.get("finding_id", "unknown"),
            "triage": {
                "priority": priority,
                "severity_context": severity_context,
                "blast_radius": self._assess_blast_radius(finding, context),
                "immediate_action": self._recommend_action(finding, priority),
                "remediation": self._recommend_remediation(finding),
                "nist_controls": nist_result["controls"][:5],
                "confidence": self._calculate_confidence(finding),
            },
            "ciso_summary": "",  # Populated by RiskSummaryGenerator or LLM
            "evidence": {
                "scanner": finding.get("scanner", "unknown"),
                "finding_type": finding.get("title", ""),
                "timestamp": finding.get("ingested_at", ""),
            },
        }

    def triage_batch(self, findings: List[Dict[str, Any]],
                     context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Triage a batch of findings. Returns sorted by priority (P1 first)."""
        results = [self.triage(f, context) for f in findings]
        priority_order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
        results.sort(key=lambda r: priority_order.get(r["triage"]["priority"], 4))
        return results

    def _apply_escalation(self, base_priority: str,
                          finding: Dict, context: Dict) -> str:
        """Escalate priority if context warrants it."""
        searchable = " ".join([
            finding.get("title", ""),
            finding.get("description", ""),
            context.get("environment", ""),
            context.get("data_classification", ""),
        ]).lower()

        escalate = any(kw in searchable for kw in _ESCALATION_KEYWORDS)
        if escalate and base_priority in ("P2", "P3"):
            priorities = ["P1", "P2", "P3", "P4"]
            idx = priorities.index(base_priority)
            return priorities[max(0, idx - 1)]
        return base_priority

    def _assess_blast_radius(self, finding: Dict, context: Dict) -> str:
        """Assess blast radius from finding and context."""
        parts = []
        raw = finding.get("raw_fields", {})

        # Check for resource identifiers
        for key in ["Host", "instanceId", "ResourceId", "hostname", "agent.name"]:
            if key in raw:
                parts.append(f"Affected resource: {raw[key]}")

        if context.get("environment") == "production":
            parts.append("Production environment — elevated risk")
        if context.get("data_classification"):
            parts.append(f"Data classification: {context['data_classification']}")

        return "; ".join(parts) if parts else "Blast radius requires manual assessment"

    def _recommend_action(self, finding: Dict, priority: str) -> str:
        """Recommend immediate action based on finding type."""
        title = finding.get("title", "").lower()
        scanner = finding.get("scanner", "")

        if priority == "P1":
            if "malicious" in title or "unauthorized" in title:
                return "Isolate affected resource immediately. Capture forensic snapshot before remediation. Rotate all associated credentials."
            return "Escalate to incident response team. Begin containment per IR playbook."

        if "vulnerability" in title or "cve" in title.lower():
            return "Schedule patch application within SLA window. Verify compensating controls are in place."

        if "misconfiguration" in title or "config" in title:
            return "Review current configuration against CIS benchmark. Apply hardened baseline."

        return f"Review {scanner} finding details and determine remediation path."

    def _recommend_remediation(self, finding: Dict) -> str:
        """Build remediation recommendation."""
        desc = finding.get("description", "")
        if desc:
            return f"Full remediation: {desc[:200]}"
        return "Review scanner documentation for remediation guidance."

    def _calculate_confidence(self, finding: Dict) -> float:
        """Calculate confidence score for this triage decision."""
        score = 0.5  # Base confidence

        # Higher confidence if we parsed successfully
        if finding.get("parse_status") == "ok":
            score += 0.15

        # Higher confidence if severity is known
        if finding.get("severity") != "UNKNOWN":
            score += 0.15

        # Higher confidence if we have NIST control hints
        if finding.get("nist_controls_hint"):
            score += 0.1

        # Higher confidence for known scanners
        if finding.get("scanner") != "unknown":
            score += 0.1

        return min(score, 0.95)
