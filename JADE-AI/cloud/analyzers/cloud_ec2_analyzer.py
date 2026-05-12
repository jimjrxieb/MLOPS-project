#!/usr/bin/env python3
"""
EC2 Analyzer for jsa-devsecops
Analyzes EC2 instances for security issues.

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
    """Types of EC2 findings."""
    IMDSV1_ENABLED = "imdsv1_enabled"
    PUBLIC_IP_ASSIGNED = "public_ip_assigned"
    NO_IAM_ROLE = "no_iam_role"
    UNENCRYPTED_VOLUME = "unencrypted_volume"
    PUBLIC_AMI = "public_ami"
    OVERLY_PERMISSIVE_SG = "overly_permissive_sg"
    OUTDATED_AMI = "outdated_ami"
    NO_DETAILED_MONITORING = "no_detailed_monitoring"
    USER_DATA_SECRETS = "user_data_secrets"


class FindingSeverity(Enum):
    """Severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class EC2Finding:
    """Represents an EC2 security finding."""
    finding_type: FindingType
    severity: FindingSeverity
    instance_id: str
    instance_name: str
    description: str
    recommendation: str
    compliance_frameworks: List[str]
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class EC2Analyzer:
    """
    Analyzes EC2 instances for security issues.

    Features:
    - Detects IMDSv1 usage (enforce IMDSv2)
    - Identifies public IP assignments
    - Checks for IAM instance profiles
    - Validates EBS encryption
    - Detects public AMIs
    - Analyzes security group associations
    - Compliance mapping (CIS AWS, PCI-DSS, SOC2)

    Example:
        analyzer = EC2Analyzer(region="us-east-1")

        # Analyze all instances
        findings = analyzer.analyze_all_instances()

        # Analyze specific instance
        findings = analyzer.analyze_instance("i-1234567890abcdef0")

        # Check for IMDSv1
        imds_findings = analyzer.check_imdsv1()

        # Get critical findings
        critical = [f for f in findings if f.severity == FindingSeverity.CRITICAL]
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None
    ):
        """
        Initialize EC2 analyzer.

        Args:
            region: AWS region
            profile: AWS profile name
        """
        self.region = region
        self.profile = profile

    def _run_aws_command(self, command: List[str]) -> Dict:
        """Run AWS CLI command and return JSON output."""
        cmd = ["aws", "ec2"] + command + ["--region", self.region, "--output", "json"]

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

    def analyze_instance(self, instance_id: str) -> List[EC2Finding]:
        """
        Analyze a specific EC2 instance.

        Args:
            instance_id: EC2 instance ID

        Returns:
            List of EC2Finding objects
        """
        findings = []

        # Get instance details
        instances_result = self._run_aws_command([
            "describe-instances",
            "--instance-ids", instance_id
        ])

        if not instances_result or "Reservations" not in instances_result:
            return findings

        for reservation in instances_result["Reservations"]:
            for instance in reservation.get("Instances", []):
                instance_name = self._get_instance_name(instance)

                # Check IMDS version
                metadata_options = instance.get("MetadataOptions", {})
                http_tokens = metadata_options.get("HttpTokens", "optional")

                if http_tokens == "optional":
                    # IMDSv1 is allowed
                    findings.append(EC2Finding(
                        finding_type=FindingType.IMDSV1_ENABLED,
                        severity=FindingSeverity.HIGH,
                        instance_id=instance_id,
                        instance_name=instance_name,
                        description=f"Instance {instance_name} allows IMDSv1 (SSRF vulnerability)",
                        recommendation="Enable IMDSv2 (HttpTokens=required) to prevent SSRF attacks (CIS AWS 5.6)",
                        compliance_frameworks=["CIS AWS 5.6"],
                        details={"metadata_options": metadata_options}
                    ))

                # Check for public IP
                public_ip = instance.get("PublicIpAddress")
                if public_ip:
                    findings.append(EC2Finding(
                        finding_type=FindingType.PUBLIC_IP_ASSIGNED,
                        severity=FindingSeverity.MEDIUM,
                        instance_id=instance_id,
                        instance_name=instance_name,
                        description=f"Instance {instance_name} has public IP {public_ip}",
                        recommendation="Avoid public IPs - use NAT Gateway or VPN for outbound access",
                        compliance_frameworks=["CIS AWS 5.3"],
                        details={"public_ip": public_ip}
                    ))

                # Check for IAM instance profile
                if "IamInstanceProfile" not in instance:
                    findings.append(EC2Finding(
                        finding_type=FindingType.NO_IAM_ROLE,
                        severity=FindingSeverity.MEDIUM,
                        instance_id=instance_id,
                        instance_name=instance_name,
                        description=f"Instance {instance_name} has no IAM instance profile (may use access keys)",
                        recommendation="Attach IAM instance profile instead of using access keys (CIS AWS 1.19)",
                        compliance_frameworks=["CIS AWS 1.19", "PCI-DSS 8.2.1"],
                        details={}
                    ))

                # Check EBS encryption
                unencrypted_volumes = []
                for bdm in instance.get("BlockDeviceMappings", []):
                    if "Ebs" in bdm:
                        volume_id = bdm["Ebs"].get("VolumeId")
                        if volume_id:
                            # Check volume encryption
                            volume_info = self._run_aws_command([
                                "describe-volumes",
                                "--volume-ids", volume_id
                            ])

                            if volume_info and "Volumes" in volume_info:
                                for volume in volume_info["Volumes"]:
                                    if not volume.get("Encrypted", False):
                                        unencrypted_volumes.append(volume_id)

                if unencrypted_volumes:
                    findings.append(EC2Finding(
                        finding_type=FindingType.UNENCRYPTED_VOLUME,
                        severity=FindingSeverity.HIGH,
                        instance_id=instance_id,
                        instance_name=instance_name,
                        description=f"Instance {instance_name} has {len(unencrypted_volumes)} unencrypted EBS volume(s)",
                        recommendation="Enable EBS encryption for all volumes (CIS AWS 2.2.1)",
                        compliance_frameworks=["CIS AWS 2.2.1", "PCI-DSS 3.4", "SOC2 CC6.6"],
                        details={"unencrypted_volumes": unencrypted_volumes}
                    ))

                # Check AMI
                ami_id = instance.get("ImageId")
                if ami_id:
                    ami_info = self._run_aws_command([
                        "describe-images",
                        "--image-ids", ami_id
                    ])

                    if ami_info and "Images" in ami_info:
                        for ami in ami_info["Images"]:
                            # Check if AMI is public
                            if ami.get("Public", False):
                                findings.append(EC2Finding(
                                    finding_type=FindingType.PUBLIC_AMI,
                                    severity=FindingSeverity.MEDIUM,
                                    instance_id=instance_id,
                                    instance_name=instance_name,
                                    description=f"Instance {instance_name} uses public AMI {ami_id}",
                                    recommendation="Use private AMIs or vetted marketplace AMIs for production",
                                    compliance_frameworks=[],
                                    details={"ami_id": ami_id, "ami_name": ami.get("Name", "Unknown")}
                                ))

                            # Check AMI age (>90 days is outdated)
                            creation_date_str = ami.get("CreationDate")
                            if creation_date_str:
                                try:
                                    creation_date = datetime.fromisoformat(creation_date_str.replace("Z", "+00:00"))
                                    age_days = (datetime.now(creation_date.tzinfo) - creation_date).days

                                    if age_days > 90:
                                        findings.append(EC2Finding(
                                            finding_type=FindingType.OUTDATED_AMI,
                                            severity=FindingSeverity.MEDIUM,
                                            instance_id=instance_id,
                                            instance_name=instance_name,
                                            description=f"Instance {instance_name} uses AMI that is {age_days} days old",
                                            recommendation="Regularly update AMIs to include latest security patches",
                                            compliance_frameworks=[],
                                            details={"ami_id": ami_id, "age_days": age_days}
                                        ))
                                except (ValueError, TypeError):
                                    pass

                # Check security groups
                security_groups = instance.get("SecurityGroups", [])
                for sg in security_groups:
                    sg_id = sg["GroupId"]

                    # Quick check for overly permissive SGs
                    sg_info = self._run_aws_command([
                        "describe-security-groups",
                        "--group-ids", sg_id
                    ])

                    if sg_info and "SecurityGroups" in sg_info:
                        for sg_data in sg_info["SecurityGroups"]:
                            # Check for 0.0.0.0/0 ingress
                            for rule in sg_data.get("IpPermissions", []):
                                for ip_range in rule.get("IpRanges", []):
                                    if ip_range.get("CidrIp") == "0.0.0.0/0":
                                        findings.append(EC2Finding(
                                            finding_type=FindingType.OVERLY_PERMISSIVE_SG,
                                            severity=FindingSeverity.HIGH,
                                            instance_id=instance_id,
                                            instance_name=instance_name,
                                            description=f"Instance {instance_name} uses security group {sg_id} with 0.0.0.0/0 ingress",
                                            recommendation="Restrict security group ingress to specific IP ranges (CIS AWS 5.1)",
                                            compliance_frameworks=["CIS AWS 5.1", "PCI-DSS 1.3.1"],
                                            details={"security_group_id": sg_id, "security_group_name": sg_data.get("GroupName")}
                                        ))
                                        break  # Only report once per SG

                # Check detailed monitoring
                monitoring_state = instance.get("Monitoring", {}).get("State", "disabled")
                if monitoring_state != "enabled":
                    findings.append(EC2Finding(
                        finding_type=FindingType.NO_DETAILED_MONITORING,
                        severity=FindingSeverity.LOW,
                        instance_id=instance_id,
                        instance_name=instance_name,
                        description=f"Instance {instance_name} does not have detailed monitoring enabled",
                        recommendation="Enable detailed monitoring for better visibility (1-minute metrics)",
                        compliance_frameworks=["SOC2 CC7.2"],
                        details={}
                    ))

        return findings

    def analyze_all_instances(self, vpc_id: str = None) -> List[EC2Finding]:
        """
        Analyze all EC2 instances (optionally filtered by VPC).

        Args:
            vpc_id: Optional VPC ID to filter instances

        Returns:
            List of EC2Finding objects
        """
        all_findings = []

        # Build command
        cmd = ["describe-instances"]
        filters = []

        if vpc_id:
            filters.append(f"Name=vpc-id,Values={vpc_id}")

        # Exclude terminated instances
        filters.append("Name=instance-state-name,Values=pending,running,stopping,stopped")

        if filters:
            cmd.extend(["--filters"] + filters)

        instances_result = self._run_aws_command(cmd)

        if not instances_result or "Reservations" not in instances_result:
            return all_findings

        # Analyze each instance
        for reservation in instances_result["Reservations"]:
            for instance in reservation.get("Instances", []):
                instance_id = instance["InstanceId"]
                findings = self.analyze_instance(instance_id)
                all_findings.extend(findings)

        return all_findings

    def check_imdsv1(self) -> List[EC2Finding]:
        """
        Check for instances using IMDSv1.

        Returns:
            List of EC2Finding objects for IMDSv1 issues
        """
        findings = []

        instances_result = self._run_aws_command([
            "describe-instances",
            "--filters", "Name=instance-state-name,Values=running"
        ])

        if not instances_result or "Reservations" not in instances_result:
            return findings

        for reservation in instances_result["Reservations"]:
            for instance in reservation.get("Instances", []):
                instance_id = instance["InstanceId"]
                instance_name = self._get_instance_name(instance)

                metadata_options = instance.get("MetadataOptions", {})
                http_tokens = metadata_options.get("HttpTokens", "optional")

                if http_tokens == "optional":
                    findings.append(EC2Finding(
                        finding_type=FindingType.IMDSV1_ENABLED,
                        severity=FindingSeverity.HIGH,
                        instance_id=instance_id,
                        instance_name=instance_name,
                        description=f"Instance {instance_name} allows IMDSv1",
                        recommendation="Enable IMDSv2: aws ec2 modify-instance-metadata-options --instance-id {} --http-tokens required".format(instance_id),
                        compliance_frameworks=["CIS AWS 5.6"],
                        details={"metadata_options": metadata_options}
                    ))

        return findings

    def check_public_instances(self) -> List[EC2Finding]:
        """
        Check for instances with public IPs.

        Returns:
            List of EC2Finding objects for public IP assignments
        """
        findings = []

        instances_result = self._run_aws_command([
            "describe-instances",
            "--filters", "Name=instance-state-name,Values=running"
        ])

        if not instances_result or "Reservations" not in instances_result:
            return findings

        for reservation in instances_result["Reservations"]:
            for instance in reservation.get("Instances", []):
                public_ip = instance.get("PublicIpAddress")

                if public_ip:
                    instance_id = instance["InstanceId"]
                    instance_name = self._get_instance_name(instance)

                    findings.append(EC2Finding(
                        finding_type=FindingType.PUBLIC_IP_ASSIGNED,
                        severity=FindingSeverity.MEDIUM,
                        instance_id=instance_id,
                        instance_name=instance_name,
                        description=f"Instance {instance_name} has public IP {public_ip}",
                        recommendation="Avoid public IPs - use NAT Gateway or VPN",
                        compliance_frameworks=["CIS AWS 5.3"],
                        details={"public_ip": public_ip}
                    ))

        return findings

    def _get_instance_name(self, instance: Dict) -> str:
        """Extract instance name from tags."""
        tags = instance.get("Tags", [])
        for tag in tags:
            if tag["Key"] == "Name":
                return tag["Value"]

        return instance["InstanceId"]


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze EC2 instances for security issues")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--instance-id", help="Analyze specific instance")
    parser.add_argument("--vpc-id", help="Analyze instances in VPC")
    parser.add_argument("--all-instances", action="store_true", help="Analyze all instances")
    parser.add_argument("--check-imdsv1", action="store_true", help="Check for IMDSv1 usage")
    parser.add_argument("--check-public", action="store_true", help="Check for public instances")
    parser.add_argument("--severity", choices=["critical", "high", "medium", "low", "info"],
                        help="Filter by severity")

    args = parser.parse_args()

    analyzer = EC2Analyzer(
        region=args.region,
        profile=args.profile
    )

    print(f"🔍 EC2 Security Analyzer\n")
    print(f"Region: {args.region}\n")

    findings = []

    # Run analysis
    if args.instance_id:
        print(f"📊 Analyzing instance: {args.instance_id}\n")
        findings = analyzer.analyze_instance(args.instance_id)
    elif args.all_instances:
        print(f"📊 Analyzing all EC2 instances...\n")
        findings = analyzer.analyze_all_instances(vpc_id=args.vpc_id)
    elif args.check_imdsv1:
        print(f"📊 Checking for IMDSv1 usage...\n")
        findings = analyzer.check_imdsv1()
    elif args.check_public:
        print(f"📊 Checking for public instances...\n")
        findings = analyzer.check_public_instances()
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
                print(f"     Instance: {finding.instance_name} ({finding.instance_id})")
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
