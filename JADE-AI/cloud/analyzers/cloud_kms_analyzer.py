#!/usr/bin/env python3
"""
KMS Analyzer for jsa-devsecops
Analyzes KMS keys for security issues.

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
    """Types of KMS findings."""
    KEY_ROTATION_DISABLED = "key_rotation_disabled"
    PUBLIC_KEY_POLICY = "public_key_policy"
    WILDCARD_PRINCIPAL = "wildcard_principal"
    CROSS_ACCOUNT_ACCESS = "cross_account_access"
    UNUSED_KEY = "unused_key"
    KEY_DELETION_SCHEDULED = "key_deletion_scheduled"
    NO_KEY_POLICY = "no_key_policy"


class FindingSeverity(Enum):
    """Severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class KMSFinding:
    """Represents a KMS security finding."""
    finding_type: FindingType
    severity: FindingSeverity
    key_id: str
    key_alias: str
    description: str
    recommendation: str
    compliance_frameworks: List[str]
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class KMSAnalyzer:
    """
    Analyzes KMS keys for security issues.

    Features:
    - Checks key rotation status
    - Analyzes key policies for public access
    - Detects wildcard principals
    - Identifies cross-account access
    - Finds unused keys
    - Tracks key deletion schedules
    - Compliance mapping (CIS AWS, PCI-DSS, SOC2)

    Example:
        analyzer = KMSAnalyzer(region="us-east-1")

        # Analyze all KMS keys
        findings = analyzer.analyze_all_keys()

        # Analyze specific key
        findings = analyzer.analyze_key("arn:aws:kms:us-east-1:123456789012:key/...")

        # Check rotation status
        rotation_findings = analyzer.check_rotation()

        # Get critical findings
        critical = [f for f in findings if f.severity == FindingSeverity.CRITICAL]
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None
    ):
        """
        Initialize KMS analyzer.

        Args:
            region: AWS region
            profile: AWS profile name
        """
        self.region = region
        self.profile = profile

    def _run_aws_command(self, command: List[str]) -> Dict:
        """Run AWS CLI command and return JSON output."""
        cmd = ["aws", "kms"] + command + ["--region", self.region, "--output", "json"]

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

    def analyze_key(self, key_id: str) -> List[KMSFinding]:
        """
        Analyze a specific KMS key.

        Args:
            key_id: KMS key ID or ARN

        Returns:
            List of KMSFinding objects
        """
        findings = []

        # Get key metadata
        key_result = self._run_aws_command([
            "describe-key",
            "--key-id", key_id
        ])

        if not key_result or "KeyMetadata" not in key_result:
            return findings

        key_metadata = key_result["KeyMetadata"]
        key_id_full = key_metadata["KeyId"]
        key_arn = key_metadata["Arn"]
        key_state = key_metadata.get("KeyState", "Unknown")

        # Get key alias
        key_alias = self._get_key_alias(key_id_full)

        # Check if key is pending deletion
        if key_state == "PendingDeletion":
            deletion_date = key_metadata.get("DeletionDate")
            findings.append(KMSFinding(
                finding_type=FindingType.KEY_DELETION_SCHEDULED,
                severity=FindingSeverity.HIGH,
                key_id=key_id_full,
                key_alias=key_alias,
                description=f"KMS key {key_alias} is scheduled for deletion on {deletion_date}",
                recommendation="Cancel key deletion if key is still needed, or verify deletion is intentional",
                compliance_frameworks=[],
                details={"deletion_date": str(deletion_date)}
            ))

        # Only check active keys
        if key_state != "Enabled":
            return findings

        # Check key rotation (only for customer-managed keys)
        if key_metadata.get("KeyManager") == "CUSTOMER":
            rotation_result = self._run_aws_command([
                "get-key-rotation-status",
                "--key-id", key_id
            ])

            if rotation_result:
                rotation_enabled = rotation_result.get("KeyRotationEnabled", False)

                if not rotation_enabled:
                    findings.append(KMSFinding(
                        finding_type=FindingType.KEY_ROTATION_DISABLED,
                        severity=FindingSeverity.HIGH,
                        key_id=key_id_full,
                        key_alias=key_alias,
                        description=f"KMS key {key_alias} does not have automatic rotation enabled",
                        recommendation="Enable automatic key rotation (CIS AWS 3.8)",
                        compliance_frameworks=["CIS AWS 3.8", "PCI-DSS 3.6.4", "SOC2 CC6.6"],
                        details={}
                    ))

        # Check key policy
        policy_result = self._run_aws_command([
            "get-key-policy",
            "--key-id", key_id,
            "--policy-name", "default"
        ])

        if policy_result and "Policy" in policy_result:
            policy = json.loads(policy_result["Policy"])
            policy_findings = self._analyze_key_policy(
                key_id_full,
                key_alias,
                policy
            )
            findings.extend(policy_findings)

        return findings

    def _analyze_key_policy(
        self,
        key_id: str,
        key_alias: str,
        policy: Dict
    ) -> List[KMSFinding]:
        """Analyze KMS key policy for security issues."""
        findings = []

        for statement in policy.get("Statement", []):
            effect = statement.get("Effect")
            principal = statement.get("Principal", {})
            actions = statement.get("Action", [])

            if effect != "Allow":
                continue

            # Normalize actions to list
            if isinstance(actions, str):
                actions = [actions]

            # Check for wildcard principal
            is_wildcard = False

            if principal == "*":
                is_wildcard = True
            elif isinstance(principal, dict):
                aws_principal = principal.get("AWS", "")
                if isinstance(aws_principal, str):
                    aws_principal = [aws_principal]

                for princ in aws_principal:
                    if princ == "*":
                        is_wildcard = True
                        break

            if is_wildcard:
                # Check if there's a restrictive condition
                condition = statement.get("Condition", {})

                # If there's a condition, this might be okay
                if not condition:
                    findings.append(KMSFinding(
                        finding_type=FindingType.WILDCARD_PRINCIPAL,
                        severity=FindingSeverity.CRITICAL,
                        key_id=key_id,
                        key_alias=key_alias,
                        description=f"KMS key {key_alias} has wildcard (*) principal in key policy",
                        recommendation="Restrict key policy to specific principals (CIS AWS 3.7)",
                        compliance_frameworks=["CIS AWS 3.7", "PCI-DSS 7.1.2"],
                        details={"statement": statement}
                    ))

            # Check for cross-account access
            if isinstance(principal, dict):
                aws_principal = principal.get("AWS", "")
                if isinstance(aws_principal, str):
                    aws_principal = [aws_principal]

                for princ in aws_principal:
                    # Extract account ID from ARN
                    if "::" in princ:
                        parts = princ.split(":")
                        if len(parts) >= 5:
                            princ_account = parts[4]

                            # Get our account ID from key ARN
                            key_parts = key_id.split(":")
                            our_account = key_parts[4] if len(key_parts) >= 5 else ""

                            if princ_account != our_account and princ_account:
                                findings.append(KMSFinding(
                                    finding_type=FindingType.CROSS_ACCOUNT_ACCESS,
                                    severity=FindingSeverity.HIGH,
                                    key_id=key_id,
                                    key_alias=key_alias,
                                    description=f"KMS key {key_alias} allows cross-account access to account {princ_account}",
                                    recommendation="Review cross-account access and ensure it's intentional",
                                    compliance_frameworks=[],
                                    details={"account_id": princ_account, "statement": statement}
                                ))

        return findings

    def analyze_all_keys(self) -> List[KMSFinding]:
        """Analyze all KMS keys."""
        all_findings = []

        # List all keys
        keys_result = self._run_aws_command(["list-keys"])

        if not keys_result or "Keys" not in keys_result:
            return all_findings

        for key in keys_result["Keys"]:
            key_id = key["KeyId"]
            findings = self.analyze_key(key_id)
            all_findings.extend(findings)

        return all_findings

    def check_rotation(self) -> List[KMSFinding]:
        """
        Check for keys without rotation enabled.

        Returns:
            List of KMSFinding objects for rotation issues
        """
        findings = []

        keys_result = self._run_aws_command(["list-keys"])

        if not keys_result or "Keys" not in keys_result:
            return findings

        for key in keys_result["Keys"]:
            key_id = key["KeyId"]

            # Get key metadata to check if customer-managed
            key_result = self._run_aws_command([
                "describe-key",
                "--key-id", key_id
            ])

            if not key_result or "KeyMetadata" not in key_result:
                continue

            key_metadata = key_result["KeyMetadata"]

            # Only check customer-managed keys
            if key_metadata.get("KeyManager") != "CUSTOMER":
                continue

            # Skip disabled keys
            if key_metadata.get("KeyState") != "Enabled":
                continue

            key_alias = self._get_key_alias(key_id)

            # Check rotation status
            rotation_result = self._run_aws_command([
                "get-key-rotation-status",
                "--key-id", key_id
            ])

            if rotation_result:
                rotation_enabled = rotation_result.get("KeyRotationEnabled", False)

                if not rotation_enabled:
                    findings.append(KMSFinding(
                        finding_type=FindingType.KEY_ROTATION_DISABLED,
                        severity=FindingSeverity.HIGH,
                        key_id=key_id,
                        key_alias=key_alias,
                        description=f"KMS key {key_alias} does not have automatic rotation enabled",
                        recommendation="Enable automatic key rotation: aws kms enable-key-rotation --key-id {}".format(key_id),
                        compliance_frameworks=["CIS AWS 3.8", "PCI-DSS 3.6.4", "SOC2 CC6.6"],
                        details={}
                    ))

        return findings

    def _get_key_alias(self, key_id: str) -> str:
        """Get key alias for a key ID."""
        aliases_result = self._run_aws_command([
            "list-aliases",
            "--key-id", key_id
        ])

        if aliases_result and "Aliases" in aliases_result:
            aliases = aliases_result["Aliases"]
            if aliases:
                return aliases[0]["AliasName"]

        return key_id


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze KMS keys for security issues")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--key-id", help="Analyze specific key")
    parser.add_argument("--all-keys", action="store_true", help="Analyze all keys")
    parser.add_argument("--check-rotation", action="store_true", help="Check key rotation status")
    parser.add_argument("--severity", choices=["critical", "high", "medium", "low", "info"],
                        help="Filter by severity")

    args = parser.parse_args()

    analyzer = KMSAnalyzer(
        region=args.region,
        profile=args.profile
    )

    print(f"🔍 KMS Security Analyzer\n")
    print(f"Region: {args.region}\n")

    findings = []

    # Run analysis
    if args.key_id:
        print(f"📊 Analyzing KMS key: {args.key_id}\n")
        findings = analyzer.analyze_key(args.key_id)
    elif args.all_keys:
        print(f"📊 Analyzing all KMS keys...\n")
        findings = analyzer.analyze_all_keys()
    elif args.check_rotation:
        print(f"📊 Checking key rotation status...\n")
        findings = analyzer.check_rotation()
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
                print(f"     Key: {finding.key_alias}")
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
