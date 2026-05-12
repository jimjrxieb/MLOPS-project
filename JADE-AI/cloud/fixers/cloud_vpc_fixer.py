#!/usr/bin/env python3
"""
VPC Fixer for jsa-devsecops
Automatically fixes VPC and Security Group security issues.

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


class FixType(Enum):
    """Types of fixes."""
    REMOVE_0000_INGRESS = "remove_0000_ingress"
    ENABLE_FLOW_LOGS = "enable_flow_logs"
    DELETE_UNUSED_SG = "delete_unused_sg"
    DISABLE_AUTO_ASSIGN_PUBLIC_IP = "disable_auto_assign_public_ip"


class FixStatus(Enum):
    """Fix operation status."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FixResult:
    """Result of a fix operation."""
    fix_type: FixType
    status: FixStatus
    resource_type: str
    resource_id: str
    description: str
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class VPCFixer:
    """
    Automatically fixes VPC and Security Group security issues.

    Features:
    - Remove 0.0.0.0/0 ingress rules from security groups
    - Enable VPC Flow Logs
    - Delete unused security groups
    - Disable auto-assign public IP on subnets

    Example:
        fixer = VPCFixer(region="us-east-1", dry_run=True)

        # Remove 0.0.0.0/0 ingress
        result = fixer.remove_public_ingress("sg-1234567890abcdef0", port=22)

        # Enable VPC Flow Logs
        result = fixer.enable_flow_logs("vpc-1234567890abcdef0", "my-flow-logs", "arn:...")

        # Delete unused security group
        result = fixer.delete_security_group("sg-1234567890abcdef0")
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None,
        dry_run: bool = True
    ):
        """
        Initialize VPC fixer.

        Args:
            region: AWS region
            profile: AWS profile name
            dry_run: If True, don't execute changes
        """
        self.region = region
        self.profile = profile
        self.dry_run = dry_run

    def _run_aws_command(self, command: List[str]) -> Dict:
        """Run AWS CLI command and return JSON output."""
        if self.dry_run:
            return {"DryRun": True}

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

            if result.returncode == 0:
                if result.stdout:
                    return json.loads(result.stdout)
                return {"Success": True}

            return {"Error": result.stderr}

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            return {"Error": str(e)}

    def remove_public_ingress(
        self,
        security_group_id: str,
        port: int = None,
        protocol: str = "tcp"
    ) -> FixResult:
        """
        Remove 0.0.0.0/0 ingress rule from security group.

        Args:
            security_group_id: Security group ID
            port: Port to remove (if None, removes all 0.0.0.0/0 rules)
            protocol: Protocol (tcp, udp, icmp, -1 for all)

        Returns:
            FixResult
        """
        if self.dry_run:
            return FixResult(
                fix_type=FixType.REMOVE_0000_INGRESS,
                status=FixStatus.SKIPPED,
                resource_type="SecurityGroup",
                resource_id=security_group_id,
                description=f"[DRY-RUN] Would remove 0.0.0.0/0 ingress on port {port or 'all'}",
                details={"dry_run": True, "port": port}
            )

        try:
            # Revoke ingress rule
            cmd = [
                "revoke-security-group-ingress",
                "--group-id", security_group_id,
                "--ip-permissions"
            ]

            ip_permission = {
                "IpProtocol": protocol,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
            }

            if port:
                ip_permission["FromPort"] = port
                ip_permission["ToPort"] = port

            cmd.append(json.dumps([ip_permission]))

            result = self._run_aws_command(cmd)

            if "Error" not in result:
                return FixResult(
                    fix_type=FixType.REMOVE_0000_INGRESS,
                    status=FixStatus.SUCCESS,
                    resource_type="SecurityGroup",
                    resource_id=security_group_id,
                    description=f"Removed 0.0.0.0/0 ingress on port {port or 'all'}",
                    details={"port": port, "protocol": protocol}
                )
            else:
                return FixResult(
                    fix_type=FixType.REMOVE_0000_INGRESS,
                    status=FixStatus.FAILED,
                    resource_type="SecurityGroup",
                    resource_id=security_group_id,
                    description=f"Failed to remove ingress: {result['Error']}",
                    details={"error": result["Error"]}
                )

        except Exception as e:
            return FixResult(
                fix_type=FixType.REMOVE_0000_INGRESS,
                status=FixStatus.FAILED,
                resource_type="SecurityGroup",
                resource_id=security_group_id,
                description=f"Exception: {str(e)}",
                details={"error": str(e)}
            )

    def enable_flow_logs(
        self,
        vpc_id: str,
        log_group_name: str,
        iam_role_arn: str
    ) -> FixResult:
        """
        Enable VPC Flow Logs.

        Args:
            vpc_id: VPC ID
            log_group_name: CloudWatch Logs log group name
            iam_role_arn: IAM role ARN for Flow Logs

        Returns:
            FixResult
        """
        if self.dry_run:
            return FixResult(
                fix_type=FixType.ENABLE_FLOW_LOGS,
                status=FixStatus.SKIPPED,
                resource_type="VPC",
                resource_id=vpc_id,
                description=f"[DRY-RUN] Would enable Flow Logs for VPC {vpc_id}",
                details={"dry_run": True, "log_group": log_group_name}
            )

        try:
            result = self._run_aws_command([
                "create-flow-logs",
                "--resource-type", "VPC",
                "--resource-ids", vpc_id,
                "--traffic-type", "ALL",
                "--log-destination-type", "cloud-watch-logs",
                "--log-group-name", log_group_name,
                "--deliver-logs-permission-arn", iam_role_arn
            ])

            if "Error" not in result and result.get("Unsuccessful", []) == []:
                return FixResult(
                    fix_type=FixType.ENABLE_FLOW_LOGS,
                    status=FixStatus.SUCCESS,
                    resource_type="VPC",
                    resource_id=vpc_id,
                    description=f"Enabled Flow Logs for VPC {vpc_id}",
                    details={"log_group": log_group_name}
                )
            else:
                error = result.get("Error", "Flow logs creation failed")
                return FixResult(
                    fix_type=FixType.ENABLE_FLOW_LOGS,
                    status=FixStatus.FAILED,
                    resource_type="VPC",
                    resource_id=vpc_id,
                    description=f"Failed to enable Flow Logs: {error}",
                    details={"error": str(error)}
                )

        except Exception as e:
            return FixResult(
                fix_type=FixType.ENABLE_FLOW_LOGS,
                status=FixStatus.FAILED,
                resource_type="VPC",
                resource_id=vpc_id,
                description=f"Exception: {str(e)}",
                details={"error": str(e)}
            )

    def delete_security_group(self, security_group_id: str) -> FixResult:
        """
        Delete unused security group.

        Args:
            security_group_id: Security group ID

        Returns:
            FixResult
        """
        if self.dry_run:
            return FixResult(
                fix_type=FixType.DELETE_UNUSED_SG,
                status=FixStatus.SKIPPED,
                resource_type="SecurityGroup",
                resource_id=security_group_id,
                description=f"[DRY-RUN] Would delete security group {security_group_id}",
                details={"dry_run": True}
            )

        try:
            result = self._run_aws_command([
                "delete-security-group",
                "--group-id", security_group_id
            ])

            if "Error" not in result:
                return FixResult(
                    fix_type=FixType.DELETE_UNUSED_SG,
                    status=FixStatus.SUCCESS,
                    resource_type="SecurityGroup",
                    resource_id=security_group_id,
                    description=f"Deleted security group {security_group_id}",
                    details={}
                )
            else:
                return FixResult(
                    fix_type=FixType.DELETE_UNUSED_SG,
                    status=FixStatus.FAILED,
                    resource_type="SecurityGroup",
                    resource_id=security_group_id,
                    description=f"Failed to delete: {result['Error']}",
                    details={"error": result["Error"]}
                )

        except Exception as e:
            return FixResult(
                fix_type=FixType.DELETE_UNUSED_SG,
                status=FixStatus.FAILED,
                resource_type="SecurityGroup",
                resource_id=security_group_id,
                description=f"Exception: {str(e)}",
                details={"error": str(e)}
            )

    def disable_auto_assign_public_ip(self, subnet_id: str) -> FixResult:
        """
        Disable auto-assign public IP on subnet.

        Args:
            subnet_id: Subnet ID

        Returns:
            FixResult
        """
        if self.dry_run:
            return FixResult(
                fix_type=FixType.DISABLE_AUTO_ASSIGN_PUBLIC_IP,
                status=FixStatus.SKIPPED,
                resource_type="Subnet",
                resource_id=subnet_id,
                description=f"[DRY-RUN] Would disable auto-assign public IP for subnet {subnet_id}",
                details={"dry_run": True}
            )

        try:
            result = self._run_aws_command([
                "modify-subnet-attribute",
                "--subnet-id", subnet_id,
                "--no-map-public-ip-on-launch"
            ])

            if "Error" not in result:
                return FixResult(
                    fix_type=FixType.DISABLE_AUTO_ASSIGN_PUBLIC_IP,
                    status=FixStatus.SUCCESS,
                    resource_type="Subnet",
                    resource_id=subnet_id,
                    description=f"Disabled auto-assign public IP for subnet {subnet_id}",
                    details={}
                )
            else:
                return FixResult(
                    fix_type=FixType.DISABLE_AUTO_ASSIGN_PUBLIC_IP,
                    status=FixStatus.FAILED,
                    resource_type="Subnet",
                    resource_id=subnet_id,
                    description=f"Failed to disable: {result['Error']}",
                    details={"error": result["Error"]}
                )

        except Exception as e:
            return FixResult(
                fix_type=FixType.DISABLE_AUTO_ASSIGN_PUBLIC_IP,
                status=FixStatus.FAILED,
                resource_type="Subnet",
                resource_id=subnet_id,
                description=f"Exception: {str(e)}",
                details={"error": str(e)}
            )


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix VPC and Security Group security issues")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--dry-run", action="store_true", help="Don't execute changes")
    parser.add_argument("--remove-public-ingress", help="Security group ID to fix")
    parser.add_argument("--port", type=int, help="Port to remove (optional)")
    parser.add_argument("--enable-flow-logs", help="VPC ID to enable Flow Logs")
    parser.add_argument("--log-group-name", help="CloudWatch Logs log group name")
    parser.add_argument("--iam-role-arn", help="IAM role ARN for Flow Logs")
    parser.add_argument("--delete-sg", help="Security group ID to delete")
    parser.add_argument("--disable-auto-ip", help="Subnet ID to disable auto-assign public IP")

    args = parser.parse_args()

    fixer = VPCFixer(
        region=args.region,
        profile=args.profile,
        dry_run=args.dry_run
    )

    print(f"🔧 VPC Security Fixer\n")
    print(f"Region: {args.region}")
    print(f"Dry-run: {args.dry_run}\n")

    results = []

    # Execute fixes
    if args.remove_public_ingress:
        print(f"📊 Removing 0.0.0.0/0 ingress from {args.remove_public_ingress}...\n")
        result = fixer.remove_public_ingress(args.remove_public_ingress, args.port)
        results.append(result)

    elif args.enable_flow_logs and args.log_group_name and args.iam_role_arn:
        print(f"📊 Enabling Flow Logs for VPC {args.enable_flow_logs}...\n")
        result = fixer.enable_flow_logs(args.enable_flow_logs, args.log_group_name, args.iam_role_arn)
        results.append(result)

    elif args.delete_sg:
        print(f"📊 Deleting security group {args.delete_sg}...\n")
        result = fixer.delete_security_group(args.delete_sg)
        results.append(result)

    elif args.disable_auto_ip:
        print(f"📊 Disabling auto-assign public IP for subnet {args.disable_auto_ip}...\n")
        result = fixer.disable_auto_assign_public_ip(args.disable_auto_ip)
        results.append(result)

    else:
        parser.print_help()
        exit(0)

    # Display results
    if results:
        print(f"📋 Fix Results ({len(results)}):\n")

        for i, result in enumerate(results, 1):
            status_icon = {
                FixStatus.SUCCESS: "✅",
                FixStatus.PARTIAL: "⚠️ ",
                FixStatus.FAILED: "❌",
                FixStatus.SKIPPED: "⏭️ "
            }[result.status]

            print(f"{i}. {status_icon} {result.fix_type.value.upper()}")
            print(f"   Resource: {result.resource_type} ({result.resource_id})")
            print(f"   Description: {result.description}")
            print()

        # Summary
        success_count = len([r for r in results if r.status == FixStatus.SUCCESS])
        failed_count = len([r for r in results if r.status == FixStatus.FAILED])
        skipped_count = len([r for r in results if r.status == FixStatus.SKIPPED])

        print(f"📊 Summary:")
        print(f"  Total Fixes: {len(results)}")
        print(f"  Success: {success_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Skipped: {skipped_count}")
        print()
