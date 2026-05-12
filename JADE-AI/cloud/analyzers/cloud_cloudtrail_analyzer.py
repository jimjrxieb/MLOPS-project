#!/usr/bin/env python3
"""
CloudTrail Analyzer for jsa-devsecops
Analyzes CloudTrail for logging and security issues.

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
    """Types of CloudTrail findings."""
    NO_TRAILS = "no_trails"
    TRAIL_NOT_LOGGING = "trail_not_logging"
    NO_LOG_FILE_VALIDATION = "no_log_file_validation"
    NO_ENCRYPTION = "no_encryption"
    NO_CLOUDWATCH_LOGS = "no_cloudwatch_logs"
    BUCKET_NOT_SECURE = "bucket_not_secure"
    NOT_MULTI_REGION = "not_multi_region"
    NO_MANAGEMENT_EVENTS = "no_management_events"
    NO_DATA_EVENTS = "no_data_events"


class FindingSeverity(Enum):
    """Severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class CloudTrailFinding:
    """Represents a CloudTrail security finding."""
    finding_type: FindingType
    severity: FindingSeverity
    trail_name: str
    trail_arn: str
    description: str
    recommendation: str
    compliance_frameworks: List[str]
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class CloudTrailAnalyzer:
    """
    Analyzes CloudTrail for logging and security issues.

    Features:
    - Checks if CloudTrail is enabled
    - Validates log file validation
    - Checks encryption at rest (KMS)
    - Validates CloudWatch Logs integration
    - Checks multi-region trails
    - Analyzes S3 bucket security
    - Compliance mapping (CIS AWS, PCI-DSS, SOC2)

    Example:
        analyzer = CloudTrailAnalyzer(region="us-east-1")

        # Analyze all trails
        findings = analyzer.analyze_all_trails()

        # Analyze specific trail
        findings = analyzer.analyze_trail("my-trail")

        # Check for enabled trails
        findings = analyzer.check_enabled_trails()

        # Get critical findings
        critical = [f for f in findings if f.severity == FindingSeverity.CRITICAL]
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None
    ):
        """
        Initialize CloudTrail analyzer.

        Args:
            region: AWS region
            profile: AWS profile name
        """
        self.region = region
        self.profile = profile

    def _run_aws_cloudtrail(self, command: List[str]) -> Dict:
        """Run AWS CloudTrail command and return JSON output."""
        cmd = ["aws", "cloudtrail"] + command + ["--region", self.region, "--output", "json"]

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

    def analyze_trail(self, trail_name: str) -> List[CloudTrailFinding]:
        """
        Analyze a specific CloudTrail trail.

        Args:
            trail_name: CloudTrail trail name

        Returns:
            List of CloudTrailFinding objects
        """
        findings = []

        # Get trail details
        trail_result = self._run_aws_cloudtrail([
            "describe-trails",
            "--trail-name-list", trail_name
        ])

        if not trail_result or "trailList" not in trail_result:
            return findings

        if not trail_result["trailList"]:
            return findings

        trail = trail_result["trailList"][0]
        trail_arn = trail.get("TrailARN", "Unknown")

        # Check if trail is logging
        status_result = self._run_aws_cloudtrail([
            "get-trail-status",
            "--name", trail_name
        ])

        if status_result:
            is_logging = status_result.get("IsLogging", False)

            if not is_logging:
                findings.append(CloudTrailFinding(
                    finding_type=FindingType.TRAIL_NOT_LOGGING,
                    severity=FindingSeverity.CRITICAL,
                    trail_name=trail_name,
                    trail_arn=trail_arn,
                    description=f"CloudTrail {trail_name} is not logging",
                    recommendation="Start logging: aws cloudtrail start-logging --name {}".format(trail_name),
                    compliance_frameworks=["CIS AWS 3.1", "PCI-DSS 10.2.1", "SOC2 CC7.2"],
                    details={}
                ))

        # Check log file validation
        log_file_validation = trail.get("LogFileValidationEnabled", False)
        if not log_file_validation:
            findings.append(CloudTrailFinding(
                finding_type=FindingType.NO_LOG_FILE_VALIDATION,
                severity=FindingSeverity.HIGH,
                trail_name=trail_name,
                trail_arn=trail_arn,
                description=f"CloudTrail {trail_name} does not have log file validation enabled",
                recommendation="Enable log file validation (CIS AWS 3.2)",
                compliance_frameworks=["CIS AWS 3.2", "PCI-DSS 10.5.2"],
                details={}
            ))

        # Check encryption
        kms_key_id = trail.get("KmsKeyId")
        if not kms_key_id:
            findings.append(CloudTrailFinding(
                finding_type=FindingType.NO_ENCRYPTION,
                severity=FindingSeverity.HIGH,
                trail_name=trail_name,
                trail_arn=trail_arn,
                description=f"CloudTrail {trail_name} logs are not encrypted with KMS",
                recommendation="Enable KMS encryption for CloudTrail logs (CIS AWS 3.7)",
                compliance_frameworks=["CIS AWS 3.7", "PCI-DSS 3.4", "SOC2 CC6.6"],
                details={}
            ))

        # Check CloudWatch Logs integration
        cloudwatch_log_group = trail.get("CloudWatchLogsLogGroupArn")
        if not cloudwatch_log_group:
            findings.append(CloudTrailFinding(
                finding_type=FindingType.NO_CLOUDWATCH_LOGS,
                severity=FindingSeverity.MEDIUM,
                trail_name=trail_name,
                trail_arn=trail_arn,
                description=f"CloudTrail {trail_name} is not integrated with CloudWatch Logs",
                recommendation="Enable CloudWatch Logs integration for real-time monitoring (CIS AWS 3.4)",
                compliance_frameworks=["CIS AWS 3.4", "SOC2 CC7.2"],
                details={}
            ))

        # Check if multi-region
        is_multi_region = trail.get("IsMultiRegionTrail", False)
        if not is_multi_region:
            findings.append(CloudTrailFinding(
                finding_type=FindingType.NOT_MULTI_REGION,
                severity=FindingSeverity.MEDIUM,
                trail_name=trail_name,
                trail_arn=trail_arn,
                description=f"CloudTrail {trail_name} is not multi-region (only logs current region)",
                recommendation="Enable multi-region trail (CIS AWS 3.1)",
                compliance_frameworks=["CIS AWS 3.1"],
                details={}
            ))

        # Check S3 bucket security
        s3_bucket_name = trail.get("S3BucketName")
        if s3_bucket_name:
            bucket_findings = self._analyze_s3_bucket(trail_name, trail_arn, s3_bucket_name)
            findings.extend(bucket_findings)

        # Check event selectors
        event_selectors_result = self._run_aws_cloudtrail([
            "get-event-selectors",
            "--trail-name", trail_name
        ])

        if event_selectors_result and "EventSelectors" in event_selectors_result:
            event_selectors = event_selectors_result["EventSelectors"]

            # Check if management events are logged
            logs_management_events = False
            logs_data_events = False

            for selector in event_selectors:
                if selector.get("IncludeManagementEvents", False):
                    logs_management_events = True

                if selector.get("DataResources"):
                    logs_data_events = True

            if not logs_management_events:
                findings.append(CloudTrailFinding(
                    finding_type=FindingType.NO_MANAGEMENT_EVENTS,
                    severity=FindingSeverity.HIGH,
                    trail_name=trail_name,
                    trail_arn=trail_arn,
                    description=f"CloudTrail {trail_name} is not logging management events",
                    recommendation="Enable management event logging (CIS AWS 3.1)",
                    compliance_frameworks=["CIS AWS 3.1"],
                    details={}
                ))

        return findings

    def _analyze_s3_bucket(
        self,
        trail_name: str,
        trail_arn: str,
        bucket_name: str
    ) -> List[CloudTrailFinding]:
        """Analyze CloudTrail S3 bucket security."""
        findings = []

        # Check bucket public access block
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
                findings.append(CloudTrailFinding(
                    finding_type=FindingType.BUCKET_NOT_SECURE,
                    severity=FindingSeverity.CRITICAL,
                    trail_name=trail_name,
                    trail_arn=trail_arn,
                    description=f"CloudTrail S3 bucket {bucket_name} allows public access",
                    recommendation="Enable Block Public Access on CloudTrail S3 bucket (CIS AWS 3.3)",
                    compliance_frameworks=["CIS AWS 3.3", "PCI-DSS 10.5.2"],
                    details={"bucket_name": bucket_name}
                ))
        else:
            # No public access block = insecure
            findings.append(CloudTrailFinding(
                finding_type=FindingType.BUCKET_NOT_SECURE,
                severity=FindingSeverity.CRITICAL,
                trail_name=trail_name,
                trail_arn=trail_arn,
                description=f"CloudTrail S3 bucket {bucket_name} has no Block Public Access configuration",
                recommendation="Enable Block Public Access (CIS AWS 3.3)",
                compliance_frameworks=["CIS AWS 3.3"],
                details={"bucket_name": bucket_name}
            ))

        return findings

    def analyze_all_trails(self) -> List[CloudTrailFinding]:
        """Analyze all CloudTrail trails."""
        all_findings = []

        trails_result = self._run_aws_cloudtrail(["describe-trails"])

        if not trails_result or "trailList" not in trails_result:
            # No trails found
            all_findings.append(CloudTrailFinding(
                finding_type=FindingType.NO_TRAILS,
                severity=FindingSeverity.CRITICAL,
                trail_name="N/A",
                trail_arn="N/A",
                description="No CloudTrail trails configured in this region",
                recommendation="Create at least one CloudTrail trail (CIS AWS 3.1)",
                compliance_frameworks=["CIS AWS 3.1", "PCI-DSS 10.2.1", "SOC2 CC7.2"],
                details={}
            ))
            return all_findings

        if not trails_result["trailList"]:
            all_findings.append(CloudTrailFinding(
                finding_type=FindingType.NO_TRAILS,
                severity=FindingSeverity.CRITICAL,
                trail_name="N/A",
                trail_arn="N/A",
                description="No CloudTrail trails configured",
                recommendation="Create at least one CloudTrail trail (CIS AWS 3.1)",
                compliance_frameworks=["CIS AWS 3.1", "PCI-DSS 10.2.1", "SOC2 CC7.2"],
                details={}
            ))
            return all_findings

        for trail in trails_result["trailList"]:
            trail_name = trail["Name"]
            findings = self.analyze_trail(trail_name)
            all_findings.extend(findings)

        return all_findings

    def check_enabled_trails(self) -> List[CloudTrailFinding]:
        """
        Check for enabled CloudTrail trails.

        Returns:
            List of CloudTrailFinding objects for disabled trails
        """
        findings = []

        trails_result = self._run_aws_cloudtrail(["describe-trails"])

        if not trails_result or "trailList" not in trails_result:
            findings.append(CloudTrailFinding(
                finding_type=FindingType.NO_TRAILS,
                severity=FindingSeverity.CRITICAL,
                trail_name="N/A",
                trail_arn="N/A",
                description="No CloudTrail trails configured",
                recommendation="Create CloudTrail trail (CIS AWS 3.1)",
                compliance_frameworks=["CIS AWS 3.1"],
                details={}
            ))
            return findings

        if not trails_result["trailList"]:
            findings.append(CloudTrailFinding(
                finding_type=FindingType.NO_TRAILS,
                severity=FindingSeverity.CRITICAL,
                trail_name="N/A",
                trail_arn="N/A",
                description="No CloudTrail trails configured",
                recommendation="Create CloudTrail trail (CIS AWS 3.1)",
                compliance_frameworks=["CIS AWS 3.1"],
                details={}
            ))
            return findings

        for trail in trails_result["trailList"]:
            trail_name = trail["Name"]
            trail_arn = trail.get("TrailARN", "Unknown")

            # Check status
            status_result = self._run_aws_cloudtrail([
                "get-trail-status",
                "--name", trail_name
            ])

            if status_result:
                is_logging = status_result.get("IsLogging", False)

                if not is_logging:
                    findings.append(CloudTrailFinding(
                        finding_type=FindingType.TRAIL_NOT_LOGGING,
                        severity=FindingSeverity.CRITICAL,
                        trail_name=trail_name,
                        trail_arn=trail_arn,
                        description=f"CloudTrail {trail_name} is not logging",
                        recommendation="Start logging: aws cloudtrail start-logging --name {}".format(trail_name),
                        compliance_frameworks=["CIS AWS 3.1", "PCI-DSS 10.2.1"],
                        details={}
                    ))

        return findings


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze CloudTrail for security issues")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--trail-name", help="Analyze specific trail")
    parser.add_argument("--all-trails", action="store_true", help="Analyze all trails")
    parser.add_argument("--check-enabled", action="store_true", help="Check for enabled trails")
    parser.add_argument("--severity", choices=["critical", "high", "medium", "low", "info"],
                        help="Filter by severity")

    args = parser.parse_args()

    analyzer = CloudTrailAnalyzer(
        region=args.region,
        profile=args.profile
    )

    print(f"🔍 CloudTrail Security Analyzer\n")
    print(f"Region: {args.region}\n")

    findings = []

    # Run analysis
    if args.trail_name:
        print(f"📊 Analyzing trail: {args.trail_name}\n")
        findings = analyzer.analyze_trail(args.trail_name)
    elif args.all_trails:
        print(f"📊 Analyzing all CloudTrail trails...\n")
        findings = analyzer.analyze_all_trails()
    elif args.check_enabled:
        print(f"📊 Checking for enabled trails...\n")
        findings = analyzer.check_enabled_trails()
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
                print(f"     Trail: {finding.trail_name}")
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
