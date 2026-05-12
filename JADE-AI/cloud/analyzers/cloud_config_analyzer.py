#!/usr/bin/env python3
"""
AWS Config Analyzer for jsa-devsecops
Analyzes AWS Config for compliance and configuration tracking.

Author: jsa-devsecops
Created: 2025-12-31
"""

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class FindingType(Enum):
    """Types of AWS Config findings."""
    CONFIG_DISABLED = "config_disabled"
    NO_RECORDER = "no_recorder"
    RECORDER_NOT_RECORDING = "recorder_not_recording"
    NO_DELIVERY_CHANNEL = "no_delivery_channel"
    NO_SNS_NOTIFICATIONS = "no_sns_notifications"
    NO_COMPLIANCE_RULES = "no_compliance_rules"
    NON_COMPLIANT_RESOURCES = "non_compliant_resources"


class FindingSeverity(Enum):
    """Severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ConfigFinding:
    """Represents an AWS Config finding."""
    finding_type: FindingType
    severity: FindingSeverity
    recorder_name: str
    description: str
    recommendation: str
    compliance_frameworks: List[str]
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class ConfigAnalyzer:
    """
    Analyzes AWS Config for compliance and configuration tracking.

    Features:
    - Checks if AWS Config is enabled
    - Validates configuration recorder
    - Checks delivery channel
    - Validates SNS notifications
    - Analyzes Config Rules
    - Reviews non-compliant resources
    - Compliance mapping (CIS AWS, PCI-DSS, SOC2)

    Example:
        analyzer = ConfigAnalyzer(region="us-east-1")

        # Analyze AWS Config configuration
        findings = analyzer.analyze_config()

        # Check for non-compliant resources
        non_compliant = analyzer.check_non_compliant_resources()

        # Get Config Rules status
        rules_status = analyzer.get_config_rules_status()
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None
    ):
        """
        Initialize AWS Config analyzer.

        Args:
            region: AWS region
            profile: AWS profile name
        """
        self.region = region
        self.profile = profile

    def _run_aws_command(self, command: List[str]) -> Dict:
        """Run AWS CLI command and return JSON output."""
        cmd = ["aws", "configservice"] + command + ["--region", self.region, "--output", "json"]

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

    def analyze_config(self) -> List[ConfigFinding]:
        """
        Analyze AWS Config configuration.

        Returns:
            List of ConfigFinding objects
        """
        findings = []

        # Check for configuration recorders
        recorders_result = self._run_aws_command(["describe-configuration-recorders"])

        if not recorders_result or "ConfigurationRecorders" not in recorders_result:
            findings.append(ConfigFinding(
                finding_type=FindingType.CONFIG_DISABLED,
                severity=FindingSeverity.CRITICAL,
                recorder_name="N/A",
                description="AWS Config is not enabled in this region",
                recommendation="Enable AWS Config for configuration tracking and compliance (CIS AWS 3.5)",
                compliance_frameworks=["CIS AWS 3.5", "PCI-DSS 10.5.5", "SOC2 CC7.2"],
                details={}
            ))
            return findings

        recorders = recorders_result.get("ConfigurationRecorders", [])

        if not recorders:
            findings.append(ConfigFinding(
                finding_type=FindingType.NO_RECORDER,
                severity=FindingSeverity.CRITICAL,
                recorder_name="N/A",
                description="No configuration recorder found in AWS Config",
                recommendation="Create AWS Config configuration recorder (CIS AWS 3.5)",
                compliance_frameworks=["CIS AWS 3.5"],
                details={}
            ))
            return findings

        # Analyze each recorder
        for recorder in recorders:
            recorder_findings = self._analyze_recorder(recorder)
            findings.extend(recorder_findings)

        return findings

    def _analyze_recorder(self, recorder: Dict) -> List[ConfigFinding]:
        """Analyze a specific configuration recorder."""
        findings = []

        recorder_name = recorder.get("name", "Unknown")

        # Check if recording all resource types
        recording_group = recorder.get("recordingGroup", {})
        all_supported = recording_group.get("allSupported", False)

        if not all_supported:
            findings.append(ConfigFinding(
                finding_type=FindingType.RECORDER_NOT_RECORDING,
                severity=FindingSeverity.MEDIUM,
                recorder_name=recorder_name,
                description=f"Config recorder {recorder_name} is not recording all resource types",
                recommendation="Enable recording of all supported resource types (CIS AWS 3.5)",
                compliance_frameworks=["CIS AWS 3.5"],
                details={"recording_group": recording_group}
            ))

        # Check recorder status
        status_result = self._run_aws_command([
            "describe-configuration-recorder-status"
        ])

        if status_result and "ConfigurationRecordersStatus" in status_result:
            for status in status_result["ConfigurationRecordersStatus"]:
                if status.get("name") == recorder_name:
                    recording = status.get("recording", False)

                    if not recording:
                        findings.append(ConfigFinding(
                            finding_type=FindingType.RECORDER_NOT_RECORDING,
                            severity=FindingSeverity.CRITICAL,
                            recorder_name=recorder_name,
                            description=f"Config recorder {recorder_name} is not actively recording",
                            recommendation="Start Config recorder: aws configservice start-configuration-recorder --configuration-recorder-name {}".format(recorder_name),
                            compliance_frameworks=["CIS AWS 3.5"],
                            details={}
                        ))

        # Check delivery channel
        channels_result = self._run_aws_command(["describe-delivery-channels"])

        if not channels_result or "DeliveryChannels" not in channels_result:
            findings.append(ConfigFinding(
                finding_type=FindingType.NO_DELIVERY_CHANNEL,
                severity=FindingSeverity.HIGH,
                recorder_name=recorder_name,
                description="No delivery channel configured for AWS Config",
                recommendation="Configure delivery channel for Config snapshots (CIS AWS 3.6)",
                compliance_frameworks=["CIS AWS 3.6"],
                details={}
            ))
        else:
            channels = channels_result.get("DeliveryChannels", [])

            if not channels:
                findings.append(ConfigFinding(
                    finding_type=FindingType.NO_DELIVERY_CHANNEL,
                    severity=FindingSeverity.HIGH,
                    recorder_name=recorder_name,
                    description="No delivery channel configured",
                    recommendation="Configure delivery channel (CIS AWS 3.6)",
                    compliance_frameworks=["CIS AWS 3.6"],
                    details={}
                ))
            else:
                # Check SNS topic
                for channel in channels:
                    sns_topic = channel.get("snsTopicARN")
                    if not sns_topic:
                        findings.append(ConfigFinding(
                            finding_type=FindingType.NO_SNS_NOTIFICATIONS,
                            severity=FindingSeverity.MEDIUM,
                            recorder_name=recorder_name,
                            description=f"Delivery channel {channel.get('name', 'Unknown')} has no SNS topic configured",
                            recommendation="Configure SNS topic for Config change notifications",
                            compliance_frameworks=["SOC2 CC7.2"],
                            details={}
                        ))

        return findings

    def check_non_compliant_resources(self) -> List[ConfigFinding]:
        """
        Check for non-compliant resources.

        Returns:
            List of ConfigFinding objects for non-compliant resources
        """
        findings = []

        # Get Config Rules
        rules_result = self._run_aws_command(["describe-config-rules"])

        if not rules_result or "ConfigRules" not in rules_result:
            findings.append(ConfigFinding(
                finding_type=FindingType.NO_COMPLIANCE_RULES,
                severity=FindingSeverity.MEDIUM,
                recorder_name="N/A",
                description="No AWS Config Rules configured for compliance checking",
                recommendation="Configure Config Rules for automated compliance checks",
                compliance_frameworks=["CIS AWS 3.5"],
                details={}
            ))
            return findings

        rules = rules_result.get("ConfigRules", [])

        if not rules:
            findings.append(ConfigFinding(
                finding_type=FindingType.NO_COMPLIANCE_RULES,
                severity=FindingSeverity.MEDIUM,
                recorder_name="N/A",
                description="No Config Rules configured",
                recommendation="Configure Config Rules for compliance",
                compliance_frameworks=["CIS AWS 3.5"],
                details={}
            ))
            return findings

        # Check compliance for each rule
        for rule in rules:
            rule_name = rule.get("ConfigRuleName", "Unknown")

            # Get compliance status
            compliance_result = self._run_aws_command([
                "describe-compliance-by-config-rule",
                "--config-rule-names", rule_name
            ])

            if compliance_result and "ComplianceByConfigRules" in compliance_result:
                for compliance in compliance_result["ComplianceByConfigRules"]:
                    compliance_type = compliance.get("Compliance", {}).get("ComplianceType", "UNKNOWN")

                    if compliance_type == "NON_COMPLIANT":
                        findings.append(ConfigFinding(
                            finding_type=FindingType.NON_COMPLIANT_RESOURCES,
                            severity=FindingSeverity.HIGH,
                            recorder_name="N/A",
                            description=f"Config Rule {rule_name} has non-compliant resources",
                            recommendation=f"Remediate non-compliant resources for rule {rule_name}",
                            compliance_frameworks=["CIS AWS 3.5", "PCI-DSS 11.5.1"],
                            details={"rule_name": rule_name}
                        ))

        return findings

    def get_config_rules_status(self) -> List[ConfigFinding]:
        """
        Get AWS Config Rules status.

        Returns:
            List of ConfigFinding objects for Config Rules issues
        """
        findings = []

        # Get Config Rules
        rules_result = self._run_aws_command(["describe-config-rules"])

        if not rules_result or "ConfigRules" not in rules_result:
            findings.append(ConfigFinding(
                finding_type=FindingType.NO_COMPLIANCE_RULES,
                severity=FindingSeverity.MEDIUM,
                recorder_name="N/A",
                description="No AWS Config Rules configured",
                recommendation="Configure Config Rules for automated compliance monitoring",
                compliance_frameworks=["CIS AWS 3.5"],
                details={}
            ))
            return findings

        rules = rules_result.get("ConfigRules", [])

        if not rules:
            findings.append(ConfigFinding(
                finding_type=FindingType.NO_COMPLIANCE_RULES,
                severity=FindingSeverity.MEDIUM,
                recorder_name="N/A",
                description="No Config Rules configured",
                recommendation="Configure managed or custom Config Rules",
                compliance_frameworks=["CIS AWS 3.5"],
                details={}
            ))

        return findings


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze AWS Config for compliance issues")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--check-config", action="store_true", help="Check AWS Config configuration")
    parser.add_argument("--check-non-compliant", action="store_true", help="Check for non-compliant resources")
    parser.add_argument("--check-rules", action="store_true", help="Check Config Rules status")
    parser.add_argument("--severity", choices=["critical", "high", "medium", "low", "info"],
                        help="Filter by severity")

    args = parser.parse_args()

    analyzer = ConfigAnalyzer(
        region=args.region,
        profile=args.profile
    )

    print(f"🔍 AWS Config Analyzer\n")
    print(f"Region: {args.region}\n")

    findings = []

    # Run analysis
    if args.check_config:
        print(f"📊 Analyzing AWS Config configuration...\n")
        findings = analyzer.analyze_config()
    elif args.check_non_compliant:
        print(f"📊 Checking for non-compliant resources...\n")
        findings = analyzer.check_non_compliant_resources()
    elif args.check_rules:
        print(f"📊 Checking Config Rules status...\n")
        findings = analyzer.get_config_rules_status()
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
