#!/usr/bin/env python3
"""
Security Hub Analyzer for jsa-devsecops
Analyzes AWS Security Hub for compliance and security findings.

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
    """Types of Security Hub findings."""
    SECURITYHUB_DISABLED = "securityhub_disabled"
    NO_STANDARDS_ENABLED = "no_standards_enabled"
    CRITICAL_FINDINGS = "critical_findings"
    HIGH_FINDINGS = "high_findings"
    FAILED_CONTROLS = "failed_controls"
    UNRESOLVED_FINDINGS = "unresolved_findings"


class FindingSeverity(Enum):
    """Severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecurityHubFinding:
    """Represents a Security Hub finding."""
    finding_type: FindingType
    severity: FindingSeverity
    hub_arn: str
    description: str
    recommendation: str
    compliance_frameworks: List[str]
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class SecurityHubAnalyzer:
    """
    Analyzes AWS Security Hub for compliance and security findings.

    Features:
    - Checks if Security Hub is enabled
    - Validates enabled standards (CIS, PCI-DSS, AWS Foundational)
    - Analyzes critical/high findings
    - Reviews failed controls
    - Tracks unresolved findings
    - Compliance mapping (CIS AWS, PCI-DSS, SOC2)

    Example:
        analyzer = SecurityHubAnalyzer(region="us-east-1")

        # Analyze Security Hub configuration
        findings = analyzer.analyze_securityhub()

        # Check for critical findings
        critical_findings = analyzer.check_critical_findings()

        # Get failed controls
        failed = analyzer.get_failed_controls()
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None
    ):
        """
        Initialize Security Hub analyzer.

        Args:
            region: AWS region
            profile: AWS profile name
        """
        self.region = region
        self.profile = profile

    def _run_aws_command(self, command: List[str]) -> Dict:
        """Run AWS CLI command and return JSON output."""
        cmd = ["aws", "securityhub"] + command + ["--region", self.region, "--output", "json"]

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

    def analyze_securityhub(self) -> List[SecurityHubFinding]:
        """
        Analyze Security Hub configuration.

        Returns:
            List of SecurityHubFinding objects
        """
        findings = []

        # Check if Security Hub is enabled
        hub_result = self._run_aws_command(["describe-hub"])

        if not hub_result or "HubArn" not in hub_result:
            findings.append(SecurityHubFinding(
                finding_type=FindingType.SECURITYHUB_DISABLED,
                severity=FindingSeverity.CRITICAL,
                hub_arn="N/A",
                description="AWS Security Hub is not enabled in this region",
                recommendation="Enable Security Hub for centralized security findings (CIS AWS 4.16)",
                compliance_frameworks=["CIS AWS 4.16", "PCI-DSS 11.4", "SOC2 CC7.2"],
                details={}
            ))
            return findings

        hub_arn = hub_result.get("HubArn", "Unknown")

        # Check enabled standards
        standards_result = self._run_aws_command(["get-enabled-standards"])

        if not standards_result or "StandardsSubscriptions" not in standards_result:
            findings.append(SecurityHubFinding(
                finding_type=FindingType.NO_STANDARDS_ENABLED,
                severity=FindingSeverity.HIGH,
                hub_arn=hub_arn,
                description="No security standards are enabled in Security Hub",
                recommendation="Enable at least CIS AWS Foundations Benchmark and AWS Foundational Security Best Practices",
                compliance_frameworks=["CIS AWS 4.16"],
                details={}
            ))
            return findings

        standards = standards_result.get("StandardsSubscriptions", [])

        if not standards:
            findings.append(SecurityHubFinding(
                finding_type=FindingType.NO_STANDARDS_ENABLED,
                severity=FindingSeverity.HIGH,
                hub_arn=hub_arn,
                description="No security standards are enabled in Security Hub",
                recommendation="Enable CIS AWS Foundations, AWS Foundational Security Best Practices, and PCI-DSS",
                compliance_frameworks=["CIS AWS 4.16"],
                details={}
            ))
        else:
            # List enabled standards
            enabled_standard_names = []
            for standard in standards:
                standard_arn = standard.get("StandardsArn", "")
                if "cis" in standard_arn.lower():
                    enabled_standard_names.append("CIS AWS Foundations")
                elif "aws-foundational" in standard_arn.lower():
                    enabled_standard_names.append("AWS Foundational Security Best Practices")
                elif "pci-dss" in standard_arn.lower():
                    enabled_standard_names.append("PCI-DSS")

            # Recommend missing standards
            if not any("CIS" in name for name in enabled_standard_names):
                findings.append(SecurityHubFinding(
                    finding_type=FindingType.NO_STANDARDS_ENABLED,
                    severity=FindingSeverity.MEDIUM,
                    hub_arn=hub_arn,
                    description="CIS AWS Foundations Benchmark is not enabled",
                    recommendation="Enable CIS AWS Foundations Benchmark standard",
                    compliance_frameworks=["CIS AWS 4.16"],
                    details={"enabled_standards": enabled_standard_names}
                ))

        return findings

    def check_critical_findings(self, days: int = 30) -> List[SecurityHubFinding]:
        """
        Check for critical Security Hub findings.

        Args:
            days: Number of days to look back

        Returns:
            List of SecurityHubFinding objects for critical findings
        """
        findings = []

        # Check if Security Hub is enabled
        hub_result = self._run_aws_command(["describe-hub"])

        if not hub_result or "HubArn" not in hub_result:
            return findings

        hub_arn = hub_result.get("HubArn", "Unknown")

        # Get critical findings
        findings_result = self._run_aws_command([
            "get-findings",
            "--filters", json.dumps({
                "SeverityLabel": [{"Value": "CRITICAL", "Comparison": "EQUALS"}],
                "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
                "UpdatedAt": [{
                    "Start": (datetime.now() - timedelta(days=days)).isoformat() + "Z",
                    "End": datetime.now().isoformat() + "Z"
                }]
            })
        ])

        if findings_result and "Findings" in findings_result:
            critical_findings = findings_result["Findings"]

            if critical_findings:
                findings.append(SecurityHubFinding(
                    finding_type=FindingType.CRITICAL_FINDINGS,
                    severity=FindingSeverity.CRITICAL,
                    hub_arn=hub_arn,
                    description=f"Security Hub has {len(critical_findings)} CRITICAL findings in the last {days} days",
                    recommendation="Review and remediate critical Security Hub findings immediately",
                    compliance_frameworks=["CIS AWS 4.16", "PCI-DSS 11.5.1"],
                    details={
                        "count": len(critical_findings),
                        "sample_types": list(set([f.get("Types", ["Unknown"])[0] for f in critical_findings[:5]]))
                    }
                ))

        # Get high findings
        findings_result = self._run_aws_command([
            "get-findings",
            "--filters", json.dumps({
                "SeverityLabel": [{"Value": "HIGH", "Comparison": "EQUALS"}],
                "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
                "UpdatedAt": [{
                    "Start": (datetime.now() - timedelta(days=days)).isoformat() + "Z",
                    "End": datetime.now().isoformat() + "Z"
                }]
            })
        ])

        if findings_result and "Findings" in findings_result:
            high_findings = findings_result["Findings"]

            if high_findings:
                findings.append(SecurityHubFinding(
                    finding_type=FindingType.HIGH_FINDINGS,
                    severity=FindingSeverity.HIGH,
                    hub_arn=hub_arn,
                    description=f"Security Hub has {len(high_findings)} HIGH severity findings in the last {days} days",
                    recommendation="Review and remediate high severity findings",
                    compliance_frameworks=["CIS AWS 4.16", "PCI-DSS 11.5.1"],
                    details={
                        "count": len(high_findings),
                        "sample_types": list(set([f.get("Types", ["Unknown"])[0] for f in high_findings[:5]]))
                    }
                ))

        return findings

    def get_failed_controls(self) -> List[SecurityHubFinding]:
        """
        Get failed Security Hub controls.

        Returns:
            List of SecurityHubFinding objects for failed controls
        """
        findings = []

        # Check if Security Hub is enabled
        hub_result = self._run_aws_command(["describe-hub"])

        if not hub_result or "HubArn" not in hub_result:
            return findings

        hub_arn = hub_result.get("HubArn", "Unknown")

        # Get enabled standards
        standards_result = self._run_aws_command(["get-enabled-standards"])

        if not standards_result or "StandardsSubscriptions" not in standards_result:
            return findings

        standards = standards_result.get("StandardsSubscriptions", [])

        for standard in standards:
            standard_arn = standard.get("StandardsSubscriptionArn", "")

            # Get controls for this standard
            controls_result = self._run_aws_command([
                "describe-standards-controls",
                "--standards-subscription-arn", standard_arn
            ])

            if controls_result and "Controls" in controls_result:
                controls = controls_result["Controls"]

                # Count failed controls
                failed_controls = [c for c in controls if c.get("ControlStatus") == "FAILED"]

                if failed_controls:
                    standard_name = standard.get("StandardsArn", "Unknown").split("/")[-1]

                    findings.append(SecurityHubFinding(
                        finding_type=FindingType.FAILED_CONTROLS,
                        severity=FindingSeverity.HIGH,
                        hub_arn=hub_arn,
                        description=f"Security Hub standard {standard_name} has {len(failed_controls)} failed controls",
                        recommendation=f"Review and remediate failed controls in {standard_name}",
                        compliance_frameworks=["CIS AWS 4.16"],
                        details={
                            "standard_name": standard_name,
                            "failed_count": len(failed_controls),
                            "total_count": len(controls),
                            "sample_controls": [c.get("ControlId") for c in failed_controls[:5]]
                        }
                    ))

        return findings

    def get_unresolved_findings(self, days: int = 90) -> List[SecurityHubFinding]:
        """
        Get unresolved Security Hub findings.

        Args:
            days: Number of days threshold for "old" findings

        Returns:
            List of SecurityHubFinding objects for unresolved findings
        """
        findings = []

        # Check if Security Hub is enabled
        hub_result = self._run_aws_command(["describe-hub"])

        if not hub_result or "HubArn" not in hub_result:
            return findings

        hub_arn = hub_result.get("HubArn", "Unknown")

        # Get old unresolved findings
        findings_result = self._run_aws_command([
            "get-findings",
            "--filters", json.dumps({
                "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
                "CreatedAt": [{
                    "End": (datetime.now() - timedelta(days=days)).isoformat() + "Z"
                }]
            }),
            "--max-results", "100"
        ])

        if findings_result and "Findings" in findings_result:
            old_findings = findings_result["Findings"]

            if old_findings:
                findings.append(SecurityHubFinding(
                    finding_type=FindingType.UNRESOLVED_FINDINGS,
                    severity=FindingSeverity.MEDIUM,
                    hub_arn=hub_arn,
                    description=f"Security Hub has {len(old_findings)} unresolved findings older than {days} days",
                    recommendation="Review and resolve old Security Hub findings",
                    compliance_frameworks=["PCI-DSS 11.5.1"],
                    details={"count": len(old_findings), "age_days": days}
                ))

        return findings


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Security Hub for compliance issues")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--check-config", action="store_true", help="Check Security Hub configuration")
    parser.add_argument("--check-critical", action="store_true", help="Check for critical findings")
    parser.add_argument("--check-failed-controls", action="store_true", help="Check for failed controls")
    parser.add_argument("--check-unresolved", action="store_true", help="Check for unresolved findings")
    parser.add_argument("--days", type=int, default=30, help="Days to look back for findings")
    parser.add_argument("--severity", choices=["critical", "high", "medium", "low", "info"],
                        help="Filter by severity")

    args = parser.parse_args()

    analyzer = SecurityHubAnalyzer(
        region=args.region,
        profile=args.profile
    )

    print(f"🔍 Security Hub Analyzer\n")
    print(f"Region: {args.region}\n")

    findings = []

    # Run analysis
    if args.check_config:
        print(f"📊 Analyzing Security Hub configuration...\n")
        findings = analyzer.analyze_securityhub()
    elif args.check_critical:
        print(f"📊 Checking for critical findings (last {args.days} days)...\n")
        findings = analyzer.check_critical_findings(days=args.days)
    elif args.check_failed_controls:
        print(f"📊 Checking for failed controls...\n")
        findings = analyzer.get_failed_controls()
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
