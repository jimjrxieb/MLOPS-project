#!/usr/bin/env python3
"""
GuardDuty Analyzer for jsa-devsecops
Analyzes GuardDuty for threat detection and security issues.

Author: jsa-devsecops
Created: 2025-12-31
"""

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class FindingType(Enum):
    """Types of GuardDuty findings."""
    GUARDDUTY_DISABLED = "guardduty_disabled"
    HIGH_SEVERITY_FINDING = "high_severity_finding"
    CRITICAL_SEVERITY_FINDING = "critical_severity_finding"
    UNRESOLVED_FINDINGS = "unresolved_findings"
    NO_S3_PROTECTION = "no_s3_protection"
    NO_EKS_PROTECTION = "no_eks_protection"


class FindingSeverity(Enum):
    """Severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class GuardDutyFinding:
    """Represents a GuardDuty security finding."""
    finding_type: FindingType
    severity: FindingSeverity
    detector_id: str
    description: str
    recommendation: str
    compliance_frameworks: List[str]
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class GuardDutyAnalyzer:
    """
    Analyzes GuardDuty for threat detection and security issues.

    Features:
    - Checks if GuardDuty is enabled
    - Analyzes high/critical findings
    - Validates S3 Protection
    - Checks EKS Protection
    - Reviews unresolved findings
    - Compliance mapping (CIS AWS, PCI-DSS, SOC2)

    Example:
        analyzer = GuardDutyAnalyzer(region="us-east-1")

        # Analyze GuardDuty configuration
        findings = analyzer.analyze_guardduty()

        # Check for critical findings
        critical_findings = analyzer.check_critical_findings()

        # Get unresolved findings
        unresolved = analyzer.get_unresolved_findings()
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None
    ):
        """
        Initialize GuardDuty analyzer.

        Args:
            region: AWS region
            profile: AWS profile name
        """
        self.region = region
        self.profile = profile

    def _run_aws_command(self, command: List[str]) -> Dict:
        """Run AWS CLI command and return JSON output."""
        cmd = ["aws", "guardduty"] + command + ["--region", self.region, "--output", "json"]

        if self.profile:
            cmd.extend(["--profile", self.profile])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)

            return {}

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return {}

    def analyze_guardduty(self) -> List[GuardDutyFinding]:
        """
        Analyze GuardDuty configuration.

        Returns:
            List of GuardDutyFinding objects
        """
        findings = []

        # List detectors
        detectors_result = self._run_aws_command(["list-detectors"])

        if not detectors_result or "DetectorIds" not in detectors_result:
            findings.append(GuardDutyFinding(
                finding_type=FindingType.GUARDDUTY_DISABLED,
                severity=FindingSeverity.CRITICAL,
                detector_id="N/A",
                description="GuardDuty is not enabled in this region",
                recommendation="Enable GuardDuty for threat detection (CIS AWS 4.1)",
                compliance_frameworks=["CIS AWS 4.1", "PCI-DSS 11.4", "SOC2 CC7.2"],
                details={}
            ))
            return findings

        detector_ids = detectors_result.get("DetectorIds", [])

        if not detector_ids:
            findings.append(GuardDutyFinding(
                finding_type=FindingType.GUARDDUTY_DISABLED,
                severity=FindingSeverity.CRITICAL,
                detector_id="N/A",
                description="GuardDuty is not enabled in this region",
                recommendation="Enable GuardDuty: aws guardduty create-detector --enable",
                compliance_frameworks=["CIS AWS 4.1", "PCI-DSS 11.4", "SOC2 CC7.2"],
                details={}
            ))
            return findings

        # Analyze each detector
        for detector_id in detector_ids:
            detector_findings = self._analyze_detector(detector_id)
            findings.extend(detector_findings)

        return findings

    def _analyze_detector(self, detector_id: str) -> List[GuardDutyFinding]:
        """Analyze a specific GuardDuty detector."""
        findings = []

        # Get detector details
        detector_result = self._run_aws_command([
            "get-detector",
            "--detector-id", detector_id
        ])

        if not detector_result:
            return findings

        # Check if detector is enabled
        status = detector_result.get("Status", "DISABLED")
        if status != "ENABLED":
            findings.append(GuardDutyFinding(
                finding_type=FindingType.GUARDDUTY_DISABLED,
                severity=FindingSeverity.CRITICAL,
                detector_id=detector_id,
                description=f"GuardDuty detector {detector_id} is disabled",
                recommendation="Enable GuardDuty detector: aws guardduty update-detector --detector-id {} --enable".format(detector_id),
                compliance_frameworks=["CIS AWS 4.1"],
                details={}
            ))
            return findings

        # Check S3 Protection
        data_sources = detector_result.get("DataSources", {})
        s3_logs = data_sources.get("S3Logs", {})
        s3_status = s3_logs.get("Status", "DISABLED")

        if s3_status != "ENABLED":
            findings.append(GuardDutyFinding(
                finding_type=FindingType.NO_S3_PROTECTION,
                severity=FindingSeverity.MEDIUM,
                detector_id=detector_id,
                description=f"GuardDuty S3 Protection is not enabled for detector {detector_id}",
                recommendation="Enable S3 Protection to monitor S3 data events",
                compliance_frameworks=["SOC2 CC7.2"],
                details={}
            ))

        # Check Kubernetes/EKS Protection
        kubernetes = data_sources.get("Kubernetes", {})
        audit_logs = kubernetes.get("AuditLogs", {})
        k8s_status = audit_logs.get("Status", "DISABLED")

        if k8s_status != "ENABLED":
            findings.append(GuardDutyFinding(
                finding_type=FindingType.NO_EKS_PROTECTION,
                severity=FindingSeverity.MEDIUM,
                detector_id=detector_id,
                description=f"GuardDuty EKS Protection is not enabled for detector {detector_id}",
                recommendation="Enable EKS Protection if using EKS clusters",
                compliance_frameworks=[],
                details={}
            ))

        return findings

    def check_critical_findings(self, days: int = 30) -> List[GuardDutyFinding]:
        """
        Check for critical GuardDuty findings.

        Args:
            days: Number of days to look back

        Returns:
            List of GuardDutyFinding objects for critical findings
        """
        findings = []

        # List detectors
        detectors_result = self._run_aws_command(["list-detectors"])

        if not detectors_result or "DetectorIds" not in detectors_result:
            return findings

        detector_ids = detectors_result.get("DetectorIds", [])

        for detector_id in detector_ids:
            # List findings
            findings_result = self._run_aws_command([
                "list-findings",
                "--detector-id", detector_id,
                "--finding-criteria", json.dumps({
                    "Criterion": {
                        "severity": {
                            "Gte": 7  # High and Critical (7.0 - 10.0)
                        },
                        "updatedAt": {
                            "Gte": int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                        }
                    }
                })
            ])

            if not findings_result or "FindingIds" not in findings_result:
                continue

            finding_ids = findings_result.get("FindingIds", [])

            if not finding_ids:
                continue

            # Get finding details
            details_result = self._run_aws_command([
                "get-findings",
                "--detector-id", detector_id,
                "--finding-ids"] + finding_ids
            )

            if details_result and "Findings" in details_result:
                for gd_finding in details_result["Findings"]:
                    severity_score = gd_finding.get("Severity", 0)
                    finding_type_str = gd_finding.get("Type", "Unknown")
                    title = gd_finding.get("Title", "Unknown")
                    description = gd_finding.get("Description", "No description")

                    # Map GuardDuty severity to our severity
                    if severity_score >= 8:
                        severity = FindingSeverity.CRITICAL
                        finding_type = FindingType.CRITICAL_SEVERITY_FINDING
                    else:
                        severity = FindingSeverity.HIGH
                        finding_type = FindingType.HIGH_SEVERITY_FINDING

                    findings.append(GuardDutyFinding(
                        finding_type=finding_type,
                        severity=severity,
                        detector_id=detector_id,
                        description=f"GuardDuty {finding_type_str}: {title}",
                        recommendation=f"Investigate and remediate: {description}",
                        compliance_frameworks=["CIS AWS 4.1", "PCI-DSS 11.4"],
                        details={
                            "finding_id": gd_finding.get("Id"),
                            "severity_score": severity_score,
                            "type": finding_type_str,
                            "resource": gd_finding.get("Resource", {})
                        }
                    ))

        return findings

    def get_unresolved_findings(self, days: int = 90) -> List[GuardDutyFinding]:
        """
        Get unresolved GuardDuty findings.

        Args:
            days: Number of days to look back

        Returns:
            List of GuardDutyFinding objects for unresolved findings
        """
        findings = []

        # List detectors
        detectors_result = self._run_aws_command(["list-detectors"])

        if not detectors_result or "DetectorIds" not in detectors_result:
            return findings

        detector_ids = detectors_result.get("DetectorIds", [])

        for detector_id in detector_ids:
            # List active findings
            findings_result = self._run_aws_command([
                "list-findings",
                "--detector-id", detector_id,
                "--finding-criteria", json.dumps({
                    "Criterion": {
                        "updatedAt": {
                            "Lte": int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                        }
                    }
                })
            ])

            if not findings_result or "FindingIds" not in findings_result:
                continue

            finding_ids = findings_result.get("FindingIds", [])

            if finding_ids:
                findings.append(GuardDutyFinding(
                    finding_type=FindingType.UNRESOLVED_FINDINGS,
                    severity=FindingSeverity.MEDIUM,
                    detector_id=detector_id,
                    description=f"GuardDuty has {len(finding_ids)} unresolved findings older than {days} days",
                    recommendation="Review and resolve old GuardDuty findings",
                    compliance_frameworks=["PCI-DSS 11.5.1"],
                    details={"count": len(finding_ids), "age_days": days}
                ))

        return findings


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze GuardDuty for security issues")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--check-config", action="store_true", help="Check GuardDuty configuration")
    parser.add_argument("--check-critical", action="store_true", help="Check for critical findings")
    parser.add_argument("--check-unresolved", action="store_true", help="Check for unresolved findings")
    parser.add_argument("--days", type=int, default=30, help="Days to look back for findings")
    parser.add_argument("--severity", choices=["critical", "high", "medium", "low", "info"],
                        help="Filter by severity")

    args = parser.parse_args()

    analyzer = GuardDutyAnalyzer(
        region=args.region,
        profile=args.profile
    )

    print(f"🔍 GuardDuty Security Analyzer\n")
    print(f"Region: {args.region}\n")

    findings = []

    # Run analysis
    if args.check_config:
        print(f"📊 Analyzing GuardDuty configuration...\n")
        findings = analyzer.analyze_guardduty()
    elif args.check_critical:
        print(f"📊 Checking for critical GuardDuty findings (last {args.days} days)...\n")
        findings = analyzer.check_critical_findings(days=args.days)
    elif args.check_unresolved:
        print(f"📊 Checking for unresolved findings (older than {args.days} days)...\n")
        findings = analyzer.get_unresolved_findings(days=args.days)
    else:
        parser.print_help()
        exit(0)

    # Filter by severity
    if args.severity:
        severity_filter = FindingSeverity(args.severity)
        findings = [f for f in findings if f.severity == severity_filter]

    # Display results
    if not findings:
        print("✅ No security findings detected\n")
    else:
        print(f"📋 Security Findings ({len(findings)}):\n")

        # Group by severity
        findings_by_severity = {
            FindingSeverity.CRITICAL: [],
            FindingSeverity.HIGH: [],
            FindingSeverity.MEDIUM: [],
            FindingSeverity.LOW: [],
            FindingSeverity.INFO: []
        }

        for finding in findings:
            findings_by_severity[finding.severity].append(finding)

        # Display by severity
        severity_icons = {
            FindingSeverity.CRITICAL: "🔴",
            FindingSeverity.HIGH: "🟠",
            FindingSeverity.MEDIUM: "🟡",
            FindingSeverity.LOW: "🟢",
            FindingSeverity.INFO: "ℹ️ "
        }

        for severity in [FindingSeverity.CRITICAL, FindingSeverity.HIGH, FindingSeverity.MEDIUM, FindingSeverity.LOW, FindingSeverity.INFO]:
            severity_findings = findings_by_severity[severity]
            if not severity_findings:
                continue

            print(f"{severity_icons[severity]} {severity.value.upper()} ({len(severity_findings)} findings):\n")

            for i, finding in enumerate(severity_findings, 1):
                print(f"  {i}. {finding.finding_type.value.upper()}")
                print(f"     Description: {finding.description}")
                print(f"     💡 Recommendation: {finding.recommendation}")
                if finding.compliance_frameworks:
                    print(f"     📋 Compliance: {', '.join(finding.compliance_frameworks)}")
                print()

        # Summary
        print(f"📊 Summary:")
        print(f"  Total Findings: {len(findings)}")
        print(f"  Critical: {len(findings_by_severity[FindingSeverity.CRITICAL])}")
        print(f"  High: {len(findings_by_severity[FindingSeverity.HIGH])}")
        print(f"  Medium: {len(findings_by_severity[FindingSeverity.MEDIUM])}")
        print(f"  Low: {len(findings_by_severity[FindingSeverity.LOW])}")
        print()
