#!/usr/bin/env python3
"""
S3 Analyzer for jsa-devsecops
Analyzes S3 buckets for security issues.

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
    """Types of S3 findings."""
    PUBLIC_ACCESS_ENABLED = "public_access_enabled"
    ENCRYPTION_DISABLED = "encryption_disabled"
    VERSIONING_DISABLED = "versioning_disabled"
    LOGGING_DISABLED = "logging_disabled"
    PUBLIC_BUCKET_POLICY = "public_bucket_policy"
    PUBLIC_ACL = "public_acl"
    MFA_DELETE_DISABLED = "mfa_delete_disabled"
    NO_LIFECYCLE_POLICY = "no_lifecycle_policy"
    INSECURE_TRANSPORT = "insecure_transport"
    CROSS_REGION_REPLICATION_DISABLED = "cross_region_replication_disabled"


class FindingSeverity(Enum):
    """Severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class S3Finding:
    """Represents an S3 security finding."""
    finding_type: FindingType
    severity: FindingSeverity
    bucket_name: str
    description: str
    recommendation: str
    compliance_frameworks: List[str]
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class S3Analyzer:
    """
    Analyzes S3 buckets for security issues.

    Features:
    - Detects public access configuration
    - Checks encryption status (SSE-S3, SSE-KMS)
    - Validates versioning enabled
    - Checks access logging
    - Analyzes bucket policies for public access
    - Validates ACLs
    - Checks MFA Delete
    - Compliance mapping (CIS AWS, PCI-DSS, SOC2)

    Example:
        analyzer = S3Analyzer(region="us-east-1")

        # Analyze all buckets
        findings = analyzer.analyze_all_buckets()

        # Analyze specific bucket
        findings = analyzer.analyze_bucket("my-bucket")

        # Check for public buckets
        public_findings = analyzer.check_public_access()

        # Get critical findings
        critical = [f for f in findings if f.severity == FindingSeverity.CRITICAL]
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None
    ):
        """
        Initialize S3 analyzer.

        Args:
            region: AWS region
            profile: AWS profile name
        """
        self.region = region
        self.profile = profile

    def _run_aws_s3api(self, command: List[str]) -> Dict:
        """Run AWS S3 API command and return JSON output."""
        cmd = ["aws", "s3api"] + command + ["--output", "json"]

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

    def _run_aws_s3(self, command: List[str]) -> str:
        """Run AWS S3 command and return output."""
        cmd = ["aws", "s3"] + command

        if self.profile:
            cmd.extend(["--profile", self.profile])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return result.stdout

            return ""

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    def analyze_bucket(self, bucket_name: str) -> List[S3Finding]:
        """
        Analyze a specific S3 bucket.

        Args:
            bucket_name: S3 bucket name

        Returns:
            List of S3Finding objects
        """
        findings = []

        # Check encryption
        encryption_result = self._run_aws_s3api([
            "get-bucket-encryption",
            "--bucket", bucket_name
        ])

        if not encryption_result or "ServerSideEncryptionConfiguration" not in encryption_result:
            findings.append(S3Finding(
                finding_type=FindingType.ENCRYPTION_DISABLED,
                severity=FindingSeverity.HIGH,
                bucket_name=bucket_name,
                description=f"Bucket {bucket_name} does not have encryption enabled",
                recommendation="Enable default encryption (SSE-S3 or SSE-KMS) (CIS AWS 2.1.1)",
                compliance_frameworks=["CIS AWS 2.1.1", "PCI-DSS 3.4", "SOC2 CC6.6"],
                details={}
            ))

        # Check versioning
        versioning_result = self._run_aws_s3api([
            "get-bucket-versioning",
            "--bucket", bucket_name
        ])

        if versioning_result:
            versioning_status = versioning_result.get("Status")
            if versioning_status != "Enabled":
                findings.append(S3Finding(
                    finding_type=FindingType.VERSIONING_DISABLED,
                    severity=FindingSeverity.MEDIUM,
                    bucket_name=bucket_name,
                    description=f"Bucket {bucket_name} does not have versioning enabled",
                    recommendation="Enable versioning for data protection (CIS AWS 2.1.3)",
                    compliance_frameworks=["CIS AWS 2.1.3", "PCI-DSS 10.5.3"],
                    details={"status": versioning_status or "Disabled"}
                ))

            # Check MFA Delete
            mfa_delete = versioning_result.get("MFADelete")
            if mfa_delete != "Enabled":
                findings.append(S3Finding(
                    finding_type=FindingType.MFA_DELETE_DISABLED,
                    severity=FindingSeverity.MEDIUM,
                    bucket_name=bucket_name,
                    description=f"Bucket {bucket_name} does not have MFA Delete enabled",
                    recommendation="Enable MFA Delete for critical buckets (CIS AWS 2.1.3)",
                    compliance_frameworks=["CIS AWS 2.1.3"],
                    details={}
                ))

        # Check logging
        logging_result = self._run_aws_s3api([
            "get-bucket-logging",
            "--bucket", bucket_name
        ])

        if not logging_result or "LoggingEnabled" not in logging_result:
            findings.append(S3Finding(
                finding_type=FindingType.LOGGING_DISABLED,
                severity=FindingSeverity.MEDIUM,
                bucket_name=bucket_name,
                description=f"Bucket {bucket_name} does not have access logging enabled",
                recommendation="Enable access logging for audit trail (CIS AWS 3.3)",
                compliance_frameworks=["CIS AWS 3.3", "PCI-DSS 10.2.1", "SOC2 CC7.2"],
                details={}
            ))

        # Check public access block
        public_access_result = self._run_aws_s3api([
            "get-public-access-block",
            "--bucket", bucket_name
        ])

        if public_access_result and "PublicAccessBlockConfiguration" in public_access_result:
            config = public_access_result["PublicAccessBlockConfiguration"]

            # All four settings should be True
            if not all([
                config.get("BlockPublicAcls", False),
                config.get("IgnorePublicAcls", False),
                config.get("BlockPublicPolicy", False),
                config.get("RestrictPublicBuckets", False)
            ]):
                findings.append(S3Finding(
                    finding_type=FindingType.PUBLIC_ACCESS_ENABLED,
                    severity=FindingSeverity.CRITICAL,
                    bucket_name=bucket_name,
                    description=f"Bucket {bucket_name} allows public access (one or more Block Public Access settings disabled)",
                    recommendation="Enable all Block Public Access settings (CIS AWS 2.1.5)",
                    compliance_frameworks=["CIS AWS 2.1.5", "PCI-DSS 1.3.1", "SOC2 CC6.6"],
                    details={"config": config}
                ))
        else:
            # No public access block = public access allowed
            findings.append(S3Finding(
                finding_type=FindingType.PUBLIC_ACCESS_ENABLED,
                severity=FindingSeverity.CRITICAL,
                bucket_name=bucket_name,
                description=f"Bucket {bucket_name} has no Block Public Access configuration",
                recommendation="Enable Block Public Access (CIS AWS 2.1.5)",
                compliance_frameworks=["CIS AWS 2.1.5", "PCI-DSS 1.3.1", "SOC2 CC6.6"],
                details={}
            ))

        # Check bucket policy
        policy_result = self._run_aws_s3api([
            "get-bucket-policy",
            "--bucket", bucket_name
        ])

        if policy_result and "Policy" in policy_result:
            policy = json.loads(policy_result["Policy"])
            policy_findings = self._analyze_bucket_policy(bucket_name, policy)
            findings.extend(policy_findings)

        # Check ACL
        acl_result = self._run_aws_s3api([
            "get-bucket-acl",
            "--bucket", bucket_name
        ])

        if acl_result and "Grants" in acl_result:
            for grant in acl_result["Grants"]:
                grantee = grant.get("Grantee", {})
                grantee_type = grantee.get("Type")
                uri = grantee.get("URI", "")

                # Check for public ACL grants
                if grantee_type == "Group" and ("AllUsers" in uri or "AuthenticatedUsers" in uri):
                    findings.append(S3Finding(
                        finding_type=FindingType.PUBLIC_ACL,
                        severity=FindingSeverity.CRITICAL,
                        bucket_name=bucket_name,
                        description=f"Bucket {bucket_name} has public ACL grant to {uri}",
                        recommendation="Remove public ACL grants (CIS AWS 2.1.5)",
                        compliance_frameworks=["CIS AWS 2.1.5", "PCI-DSS 1.3.1"],
                        details={"grant": grant}
                    ))

        # Check lifecycle policy
        lifecycle_result = self._run_aws_s3api([
            "get-bucket-lifecycle-configuration",
            "--bucket", bucket_name
        ])

        if not lifecycle_result or "Rules" not in lifecycle_result:
            findings.append(S3Finding(
                finding_type=FindingType.NO_LIFECYCLE_POLICY,
                severity=FindingSeverity.LOW,
                bucket_name=bucket_name,
                description=f"Bucket {bucket_name} does not have lifecycle policies configured",
                recommendation="Configure lifecycle policies to manage object storage classes and expiration",
                compliance_frameworks=[],
                details={}
            ))

        return findings

    def _analyze_bucket_policy(self, bucket_name: str, policy: Dict) -> List[S3Finding]:
        """Analyze bucket policy for public access."""
        findings = []

        for statement in policy.get("Statement", []):
            effect = statement.get("Effect")
            principal = statement.get("Principal", {})

            if effect != "Allow":
                continue

            # Check for public principal
            is_public = False

            if principal == "*":
                is_public = True
            elif isinstance(principal, dict):
                aws_principal = principal.get("AWS", "")
                if aws_principal == "*":
                    is_public = True

            if is_public:
                # Check if there's a restrictive condition
                condition = statement.get("Condition", {})

                # If SecureTransport is enforced, this is okay
                if "Bool" in condition and "aws:SecureTransport" in condition["Bool"]:
                    continue

                findings.append(S3Finding(
                    finding_type=FindingType.PUBLIC_BUCKET_POLICY,
                    severity=FindingSeverity.CRITICAL,
                    bucket_name=bucket_name,
                    description=f"Bucket {bucket_name} has public bucket policy (Principal: *)",
                    recommendation="Restrict bucket policy to specific principals (CIS AWS 2.1.5)",
                    compliance_frameworks=["CIS AWS 2.1.5", "PCI-DSS 1.3.1"],
                    details={"statement": statement}
                ))

            # Check for insecure transport (HTTP allowed)
            if "Condition" in statement:
                condition = statement["Condition"]
                bool_conditions = condition.get("Bool", {})
                secure_transport = bool_conditions.get("aws:SecureTransport")

                # Deny if SecureTransport is False
                if effect == "Deny" and secure_transport == "false":
                    # This is good - enforces HTTPS
                    pass
                elif effect == "Allow" and "aws:SecureTransport" not in bool_conditions:
                    # Allow without SecureTransport check = HTTP allowed
                    findings.append(S3Finding(
                        finding_type=FindingType.INSECURE_TRANSPORT,
                        severity=FindingSeverity.MEDIUM,
                        bucket_name=bucket_name,
                        description=f"Bucket {bucket_name} policy does not enforce secure transport (HTTPS)",
                        recommendation="Add condition to deny requests over HTTP (aws:SecureTransport=false)",
                        compliance_frameworks=["PCI-DSS 4.1", "SOC2 CC6.6"],
                        details={"statement": statement}
                    ))

        return findings

    def analyze_all_buckets(self) -> List[S3Finding]:
        """Analyze all S3 buckets."""
        all_findings = []

        # List all buckets
        buckets_result = self._run_aws_s3api(["list-buckets"])

        if not buckets_result or "Buckets" not in buckets_result:
            return all_findings

        for bucket in buckets_result["Buckets"]:
            bucket_name = bucket["Name"]
            findings = self.analyze_bucket(bucket_name)
            all_findings.extend(findings)

        return all_findings

    def check_public_access(self) -> List[S3Finding]:
        """
        Check for buckets with public access enabled.

        Returns:
            List of S3Finding objects for public access issues
        """
        findings = []

        buckets_result = self._run_aws_s3api(["list-buckets"])

        if not buckets_result or "Buckets" not in buckets_result:
            return findings

        for bucket in buckets_result["Buckets"]:
            bucket_name = bucket["Name"]

            # Check public access block
            public_access_result = self._run_aws_s3api([
                "get-public-access-block",
                "--bucket", bucket_name
            ])

            if public_access_result and "PublicAccessBlockConfiguration" in public_access_result:
                config = public_access_result["PublicAccessBlockConfiguration"]

                if not all([
                    config.get("BlockPublicAcls", False),
                    config.get("IgnorePublicAcls", False),
                    config.get("BlockPublicPolicy", False),
                    config.get("RestrictPublicBuckets", False)
                ]):
                    findings.append(S3Finding(
                        finding_type=FindingType.PUBLIC_ACCESS_ENABLED,
                        severity=FindingSeverity.CRITICAL,
                        bucket_name=bucket_name,
                        description=f"Bucket {bucket_name} allows public access",
                        recommendation="Enable all Block Public Access settings (CIS AWS 2.1.5)",
                        compliance_frameworks=["CIS AWS 2.1.5", "PCI-DSS 1.3.1", "SOC2 CC6.6"],
                        details={"config": config}
                    ))
            else:
                # No public access block = public
                findings.append(S3Finding(
                    finding_type=FindingType.PUBLIC_ACCESS_ENABLED,
                    severity=FindingSeverity.CRITICAL,
                    bucket_name=bucket_name,
                    description=f"Bucket {bucket_name} has no Block Public Access configuration",
                    recommendation="Enable Block Public Access (CIS AWS 2.1.5)",
                    compliance_frameworks=["CIS AWS 2.1.5"],
                    details={}
                ))

        return findings

    def check_encryption(self) -> List[S3Finding]:
        """
        Check for buckets without encryption.

        Returns:
            List of S3Finding objects for encryption issues
        """
        findings = []

        buckets_result = self._run_aws_s3api(["list-buckets"])

        if not buckets_result or "Buckets" not in buckets_result:
            return findings

        for bucket in buckets_result["Buckets"]:
            bucket_name = bucket["Name"]

            encryption_result = self._run_aws_s3api([
                "get-bucket-encryption",
                "--bucket", bucket_name
            ])

            if not encryption_result or "ServerSideEncryptionConfiguration" not in encryption_result:
                findings.append(S3Finding(
                    finding_type=FindingType.ENCRYPTION_DISABLED,
                    severity=FindingSeverity.HIGH,
                    bucket_name=bucket_name,
                    description=f"Bucket {bucket_name} does not have encryption enabled",
                    recommendation="Enable default encryption (SSE-S3 or SSE-KMS) (CIS AWS 2.1.1)",
                    compliance_frameworks=["CIS AWS 2.1.1", "PCI-DSS 3.4", "SOC2 CC6.6"],
                    details={}
                ))

        return findings


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze S3 buckets for security issues")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--bucket", help="Analyze specific bucket")
    parser.add_argument("--all-buckets", action="store_true", help="Analyze all buckets")
    parser.add_argument("--check-public", action="store_true", help="Check for public buckets")
    parser.add_argument("--check-encryption", action="store_true", help="Check for unencrypted buckets")
    parser.add_argument("--severity", choices=["critical", "high", "medium", "low", "info"],
                        help="Filter by severity")

    args = parser.parse_args()

    analyzer = S3Analyzer(
        region=args.region,
        profile=args.profile
    )

    print(f"🔍 S3 Security Analyzer\n")
    print(f"Region: {args.region}\n")

    findings = []

    # Run analysis
    if args.bucket:
        print(f"📊 Analyzing bucket: {args.bucket}\n")
        findings = analyzer.analyze_bucket(args.bucket)
    elif args.all_buckets:
        print(f"📊 Analyzing all S3 buckets...\n")
        findings = analyzer.analyze_all_buckets()
    elif args.check_public:
        print(f"📊 Checking for public buckets...\n")
        findings = analyzer.check_public_access()
    elif args.check_encryption:
        print(f"📊 Checking for unencrypted buckets...\n")
        findings = analyzer.check_encryption()
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
                print(f"     Bucket: {finding.bucket_name}")
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
