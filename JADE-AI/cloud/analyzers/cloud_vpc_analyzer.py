#!/usr/bin/env python3
"""
VPC Analyzer for jsa-devsecops
Analyzes VPC, Security Groups, and NACLs for security issues.

Author: jsa-devsecops
Created: 2025-12-31
"""

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set


class FindingType(Enum):
    """Types of VPC findings."""
    OPEN_TO_INTERNET = "open_to_internet"
    SENSITIVE_PORT_OPEN = "sensitive_port_open"
    UNRESTRICTED_EGRESS = "unrestricted_egress"
    DEFAULT_VPC = "default_vpc"
    NO_FLOW_LOGS = "no_flow_logs"
    UNUSED_SECURITY_GROUP = "unused_security_group"
    OVERLY_PERMISSIVE_NACL = "overly_permissive_nacl"
    CIDR_OVERLAP = "cidr_overlap"
    PUBLIC_SUBNET_AUTO_ASSIGN = "public_subnet_auto_assign"


class FindingSeverity(Enum):
    """Severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class VPCFinding:
    """Represents a VPC security finding."""
    finding_type: FindingType
    severity: FindingSeverity
    resource_type: str  # SecurityGroup, VPC, NACL, Subnet
    resource_id: str
    resource_name: str
    description: str
    recommendation: str
    compliance_frameworks: List[str]
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class VPCAnalyzer:
    """
    Analyzes VPC configurations for security issues.

    Features:
    - Detects 0.0.0.0/0 ingress rules
    - Identifies open sensitive ports (SSH, RDP, databases)
    - Checks for unrestricted egress
    - Detects default VPC usage
    - Validates VPC Flow Logs
    - Finds unused security groups
    - Compliance mapping (CIS AWS, PCI-DSS, SOC2)

    Example:
        analyzer = VPCAnalyzer(region="us-east-1")

        # Analyze all security groups
        findings = analyzer.analyze_all_security_groups()

        # Analyze specific security group
        findings = analyzer.analyze_security_group("sg-1234567890abcdef0")

        # Check for open sensitive ports
        findings = analyzer.check_sensitive_ports()

        # Get critical findings
        critical = [f for f in findings if f.severity == FindingSeverity.CRITICAL]
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None
    ):
        """
        Initialize VPC analyzer.

        Args:
            region: AWS region
            profile: AWS profile name
        """
        self.region = region
        self.profile = profile

        # Sensitive ports to monitor
        self.sensitive_ports = {
            22: "SSH",
            3389: "RDP",
            3306: "MySQL",
            5432: "PostgreSQL",
            1433: "MSSQL",
            1521: "Oracle",
            27017: "MongoDB",
            6379: "Redis",
            9200: "Elasticsearch",
            5984: "CouchDB",
            7000: "Cassandra",
            8086: "InfluxDB"
        }

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

    def analyze_security_group(self, group_id: str) -> List[VPCFinding]:
        """
        Analyze a specific security group.

        Args:
            group_id: Security group ID

        Returns:
            List of VPCFinding objects
        """
        findings = []

        # Get security group details
        sg_result = self._run_aws_command([
            "describe-security-groups",
            "--group-ids", group_id
        ])

        if not sg_result or "SecurityGroups" not in sg_result:
            return findings

        sg = sg_result["SecurityGroups"][0]
        sg_name = sg.get("GroupName", "Unknown")
        vpc_id = sg.get("VpcId", "Unknown")

        # Analyze ingress rules
        for rule in sg.get("IpPermissions", []):
            # Check for 0.0.0.0/0
            ipv4_ranges = rule.get("IpRanges", [])
            for ip_range in ipv4_ranges:
                cidr = ip_range.get("CidrIp")

                if cidr == "0.0.0.0/0":
                    from_port = rule.get("FromPort")
                    to_port = rule.get("ToPort")
                    protocol = rule.get("IpProtocol", "All")

                    # Check if sensitive port is open
                    if from_port in self.sensitive_ports or to_port in self.sensitive_ports:
                        port_name = self.sensitive_ports.get(from_port) or self.sensitive_ports.get(to_port)
                        findings.append(VPCFinding(
                            finding_type=FindingType.SENSITIVE_PORT_OPEN,
                            severity=FindingSeverity.CRITICAL,
                            resource_type="SecurityGroup",
                            resource_id=group_id,
                            resource_name=sg_name,
                            description=f"Security group {sg_name} allows {port_name} (port {from_port or to_port}) from 0.0.0.0/0",
                            recommendation=f"Restrict {port_name} access to specific IP addresses (CIS AWS 5.2)",
                            compliance_frameworks=["CIS AWS 5.2", "PCI-DSS 1.3.1", "SOC2 CC6.6"],
                            details={
                                "port": from_port or to_port,
                                "protocol": protocol,
                                "port_name": port_name,
                                "vpc_id": vpc_id
                            }
                        ))
                    else:
                        # Generic 0.0.0.0/0 finding
                        findings.append(VPCFinding(
                            finding_type=FindingType.OPEN_TO_INTERNET,
                            severity=FindingSeverity.HIGH,
                            resource_type="SecurityGroup",
                            resource_id=group_id,
                            resource_name=sg_name,
                            description=f"Security group {sg_name} allows ingress from 0.0.0.0/0 on port {from_port or to_port}",
                            recommendation="Restrict ingress to specific IP ranges (CIS AWS 5.1)",
                            compliance_frameworks=["CIS AWS 5.1", "PCI-DSS 1.3.1"],
                            details={
                                "port": from_port or to_port,
                                "protocol": protocol,
                                "vpc_id": vpc_id
                            }
                        ))

            # Check for ::/0 (IPv6)
            ipv6_ranges = rule.get("Ipv6Ranges", [])
            for ip_range in ipv6_ranges:
                cidr = ip_range.get("CidrIpv6")

                if cidr == "::/0":
                    from_port = rule.get("FromPort")
                    to_port = rule.get("ToPort")

                    findings.append(VPCFinding(
                        finding_type=FindingType.OPEN_TO_INTERNET,
                        severity=FindingSeverity.HIGH,
                        resource_type="SecurityGroup",
                        resource_id=group_id,
                        resource_name=sg_name,
                        description=f"Security group {sg_name} allows IPv6 ingress from ::/0 on port {from_port or to_port}",
                        recommendation="Restrict IPv6 ingress to specific IP ranges (CIS AWS 5.1)",
                        compliance_frameworks=["CIS AWS 5.1"],
                        details={
                            "port": from_port or to_port,
                            "protocol": rule.get("IpProtocol", "All"),
                            "vpc_id": vpc_id
                        }
                    ))

        # Analyze egress rules
        for rule in sg.get("IpPermissions Egress", []):
            ipv4_ranges = rule.get("IpRanges", [])

            for ip_range in ipv4_ranges:
                cidr = ip_range.get("CidrIp")
                protocol = rule.get("IpProtocol", "All")

                # Unrestricted egress (0.0.0.0/0 on all ports)
                if cidr == "0.0.0.0/0" and protocol == "-1":
                    findings.append(VPCFinding(
                        finding_type=FindingType.UNRESTRICTED_EGRESS,
                        severity=FindingSeverity.MEDIUM,
                        resource_type="SecurityGroup",
                        resource_id=group_id,
                        resource_name=sg_name,
                        description=f"Security group {sg_name} allows unrestricted egress (0.0.0.0/0 all protocols)",
                        recommendation="Consider restricting egress to required destinations only",
                        compliance_frameworks=["PCI-DSS 1.3.4"],
                        details={"vpc_id": vpc_id}
                    ))

        return findings

    def analyze_vpc(self, vpc_id: str) -> List[VPCFinding]:
        """
        Analyze a specific VPC.

        Args:
            vpc_id: VPC ID

        Returns:
            List of VPCFinding objects
        """
        findings = []

        # Get VPC details
        vpc_result = self._run_aws_command([
            "describe-vpcs",
            "--vpc-ids", vpc_id
        ])

        if not vpc_result or "Vpcs" not in vpc_result:
            return findings

        vpc = vpc_result["Vpcs"][0]
        is_default = vpc.get("IsDefault", False)

        # Check if default VPC
        if is_default:
            findings.append(VPCFinding(
                finding_type=FindingType.DEFAULT_VPC,
                severity=FindingSeverity.MEDIUM,
                resource_type="VPC",
                resource_id=vpc_id,
                resource_name="default",
                description=f"Using default VPC {vpc_id} (create dedicated VPCs for production)",
                recommendation="Create dedicated VPCs for production workloads (CIS AWS 5.4)",
                compliance_frameworks=["CIS AWS 5.4"],
                details={"cidr_block": vpc.get("CidrBlock")}
            ))

        # Check for VPC Flow Logs
        flow_logs_result = self._run_aws_command([
            "describe-flow-logs",
            "--filter", f"Name=resource-id,Values={vpc_id}"
        ])

        has_flow_logs = False
        if flow_logs_result and "FlowLogs" in flow_logs_result:
            has_flow_logs = len(flow_logs_result["FlowLogs"]) > 0

        if not has_flow_logs:
            findings.append(VPCFinding(
                finding_type=FindingType.NO_FLOW_LOGS,
                severity=FindingSeverity.HIGH,
                resource_type="VPC",
                resource_id=vpc_id,
                resource_name=vpc.get("Tags", [{}])[0].get("Value", vpc_id),
                description=f"VPC {vpc_id} does not have Flow Logs enabled",
                recommendation="Enable VPC Flow Logs for network monitoring (CIS AWS 3.9)",
                compliance_frameworks=["CIS AWS 3.9", "PCI-DSS 10.3.3", "SOC2 CC7.2"],
                details={"cidr_block": vpc.get("CidrBlock")}
            ))

        # Check subnets for auto-assign public IP
        subnets_result = self._run_aws_command([
            "describe-subnets",
            "--filters", f"Name=vpc-id,Values={vpc_id}"
        ])

        if subnets_result and "Subnets" in subnets_result:
            for subnet in subnets_result["Subnets"]:
                if subnet.get("MapPublicIpOnLaunch", False):
                    subnet_id = subnet["SubnetId"]
                    subnet_cidr = subnet.get("CidrBlock", "Unknown")

                    findings.append(VPCFinding(
                        finding_type=FindingType.PUBLIC_SUBNET_AUTO_ASSIGN,
                        severity=FindingSeverity.MEDIUM,
                        resource_type="Subnet",
                        resource_id=subnet_id,
                        resource_name=subnet_id,
                        description=f"Subnet {subnet_id} auto-assigns public IPs (disable unless needed)",
                        recommendation="Disable auto-assign public IP for subnets (assign manually when needed)",
                        compliance_frameworks=["CIS AWS 5.3"],
                        details={"vpc_id": vpc_id, "cidr_block": subnet_cidr}
                    ))

        return findings

    def analyze_all_security_groups(self, vpc_id: str = None) -> List[VPCFinding]:
        """
        Analyze all security groups (optionally filtered by VPC).

        Args:
            vpc_id: Optional VPC ID to filter

        Returns:
            List of VPCFinding objects
        """
        all_findings = []

        # Build command
        cmd = ["describe-security-groups"]
        if vpc_id:
            cmd.extend(["--filters", f"Name=vpc-id,Values={vpc_id}"])

        sg_result = self._run_aws_command(cmd)

        if not sg_result or "SecurityGroups" not in sg_result:
            return all_findings

        for sg in sg_result["SecurityGroups"]:
            group_id = sg["GroupId"]
            findings = self.analyze_security_group(group_id)
            all_findings.extend(findings)

        return all_findings

    def analyze_all_vpcs(self) -> List[VPCFinding]:
        """Analyze all VPCs."""
        all_findings = []

        vpc_result = self._run_aws_command(["describe-vpcs"])

        if not vpc_result or "Vpcs" not in vpc_result:
            return all_findings

        for vpc in vpc_result["Vpcs"]:
            vpc_id = vpc["VpcId"]
            findings = self.analyze_vpc(vpc_id)
            all_findings.extend(findings)

        return all_findings

    def check_sensitive_ports(self) -> List[VPCFinding]:
        """
        Check for security groups with sensitive ports open to 0.0.0.0/0.

        Returns:
            List of VPCFinding objects for sensitive port exposures
        """
        findings = []

        sg_result = self._run_aws_command(["describe-security-groups"])

        if not sg_result or "SecurityGroups" not in sg_result:
            return findings

        for sg in sg_result["SecurityGroups"]:
            group_id = sg["GroupId"]
            sg_name = sg.get("GroupName", "Unknown")
            vpc_id = sg.get("VpcId", "Unknown")

            for rule in sg.get("IpPermissions", []):
                from_port = rule.get("FromPort")
                to_port = rule.get("ToPort")

                # Check if sensitive port
                if from_port not in self.sensitive_ports and to_port not in self.sensitive_ports:
                    continue

                # Check for 0.0.0.0/0
                ipv4_ranges = rule.get("IpRanges", [])
                for ip_range in ipv4_ranges:
                    if ip_range.get("CidrIp") == "0.0.0.0/0":
                        port_name = self.sensitive_ports.get(from_port) or self.sensitive_ports.get(to_port)

                        findings.append(VPCFinding(
                            finding_type=FindingType.SENSITIVE_PORT_OPEN,
                            severity=FindingSeverity.CRITICAL,
                            resource_type="SecurityGroup",
                            resource_id=group_id,
                            resource_name=sg_name,
                            description=f"{port_name} (port {from_port or to_port}) open to 0.0.0.0/0 in {sg_name}",
                            recommendation=f"Restrict {port_name} access to specific IP addresses (CIS AWS 5.2)",
                            compliance_frameworks=["CIS AWS 5.2", "PCI-DSS 1.3.1", "SOC2 CC6.6"],
                            details={
                                "port": from_port or to_port,
                                "port_name": port_name,
                                "vpc_id": vpc_id
                            }
                        ))

        return findings

    def find_unused_security_groups(self) -> List[VPCFinding]:
        """
        Find security groups not attached to any instances/ENIs.

        Returns:
            List of VPCFinding objects for unused security groups
        """
        findings = []

        # Get all security groups
        sg_result = self._run_aws_command(["describe-security-groups"])

        if not sg_result or "SecurityGroups" not in sg_result:
            return findings

        # Get all network interfaces
        eni_result = self._run_aws_command(["describe-network-interfaces"])

        # Collect security groups in use
        used_sgs = set()
        if eni_result and "NetworkInterfaces" in eni_result:
            for eni in eni_result["NetworkInterfaces"]:
                for sg in eni.get("Groups", []):
                    used_sgs.add(sg["GroupId"])

        # Find unused security groups
        for sg in sg_result["SecurityGroups"]:
            group_id = sg["GroupId"]
            sg_name = sg.get("GroupName", "Unknown")

            # Skip default security groups
            if sg_name == "default":
                continue

            if group_id not in used_sgs:
                findings.append(VPCFinding(
                    finding_type=FindingType.UNUSED_SECURITY_GROUP,
                    severity=FindingSeverity.LOW,
                    resource_type="SecurityGroup",
                    resource_id=group_id,
                    resource_name=sg_name,
                    description=f"Security group {sg_name} is not attached to any resources",
                    recommendation="Remove unused security groups to reduce attack surface",
                    compliance_frameworks=[],
                    details={"vpc_id": sg.get("VpcId")}
                ))

        return findings


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze VPC configurations for security issues")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--security-group", help="Analyze specific security group")
    parser.add_argument("--vpc", help="Analyze specific VPC")
    parser.add_argument("--all-sgs", action="store_true", help="Analyze all security groups")
    parser.add_argument("--all-vpcs", action="store_true", help="Analyze all VPCs")
    parser.add_argument("--check-sensitive-ports", action="store_true", help="Check for open sensitive ports")
    parser.add_argument("--find-unused", action="store_true", help="Find unused security groups")
    parser.add_argument("--severity", choices=["critical", "high", "medium", "low", "info"],
                        help="Filter by severity")

    args = parser.parse_args()

    analyzer = VPCAnalyzer(
        region=args.region,
        profile=args.profile
    )

    print(f"🔍 VPC Security Analyzer\n")
    print(f"Region: {args.region}\n")

    findings = []

    # Run analysis
    if args.security_group:
        print(f"📊 Analyzing security group: {args.security_group}\n")
        findings = analyzer.analyze_security_group(args.security_group)
    elif args.vpc:
        print(f"📊 Analyzing VPC: {args.vpc}\n")
        findings = analyzer.analyze_vpc(args.vpc)
    elif args.all_sgs:
        print(f"📊 Analyzing all security groups...\n")
        findings = analyzer.analyze_all_security_groups()
    elif args.all_vpcs:
        print(f"📊 Analyzing all VPCs...\n")
        findings = analyzer.analyze_all_vpcs()
    elif args.check_sensitive_ports:
        print(f"📊 Checking for open sensitive ports...\n")
        findings = analyzer.check_sensitive_ports()
    elif args.find_unused:
        print(f"📊 Finding unused security groups...\n")
        findings = analyzer.find_unused_security_groups()
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
                print(f"     Resource: {finding.resource_type} ({finding.resource_name})")
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
