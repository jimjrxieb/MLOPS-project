#!/usr/bin/env python3
"""
EC2 Fixer for jsa-devsecops
Automatically fixes EC2 instance security issues.

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
    ENABLE_IMDSV2 = "enable_imdsv2"
    ENABLE_DETAILED_MONITORING = "enable_detailed_monitoring"
    ENABLE_TERMINATION_PROTECTION = "enable_termination_protection"


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
    instance_id: str
    description: str
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class EC2Fixer:
    """
    Automatically fixes EC2 instance security issues.

    Features:
    - Enable IMDSv2 (disable IMDSv1)
    - Enable detailed monitoring
    - Enable termination protection

    Note: Volume encryption and IAM role attachment require
    more complex workflows (snapshot, re-create, attach).

    Example:
        fixer = EC2Fixer(region="us-east-1", dry_run=True)

        # Enable IMDSv2
        result = fixer.enable_imdsv2("i-1234567890abcdef0")

        # Enable detailed monitoring
        result = fixer.enable_detailed_monitoring("i-1234567890abcdef0")

        # Enable termination protection
        result = fixer.enable_termination_protection("i-1234567890abcdef0")
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None,
        dry_run: bool = True
    ):
        """
        Initialize EC2 fixer.

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

    def enable_imdsv2(self, instance_id: str) -> FixResult:
        """
        Enable IMDSv2 (require tokens) for EC2 instance.

        Args:
            instance_id: EC2 instance ID

        Returns:
            FixResult
        """
        if self.dry_run:
            return FixResult(
                fix_type=FixType.ENABLE_IMDSV2,
                status=FixStatus.SKIPPED,
                instance_id=instance_id,
                description=f"[DRY-RUN] Would enable IMDSv2 for instance {instance_id}",
                details={"dry_run": True}
            )

        try:
            result = self._run_aws_command([
                "modify-instance-metadata-options",
                "--instance-id", instance_id,
                "--http-tokens", "required",
                "--http-put-response-hop-limit", "1"
            ])

            if "Error" not in result:
                return FixResult(
                    fix_type=FixType.ENABLE_IMDSV2,
                    status=FixStatus.SUCCESS,
                    instance_id=instance_id,
                    description=f"Enabled IMDSv2 for instance {instance_id}",
                    details={}
                )
            else:
                return FixResult(
                    fix_type=FixType.ENABLE_IMDSV2,
                    status=FixStatus.FAILED,
                    instance_id=instance_id,
                    description=f"Failed to enable IMDSv2: {result['Error']}",
                    details={"error": result["Error"]}
                )

        except Exception as e:
            return FixResult(
                fix_type=FixType.ENABLE_IMDSV2,
                status=FixStatus.FAILED,
                instance_id=instance_id,
                description=f"Exception: {str(e)}",
                details={"error": str(e)}
            )

    def enable_detailed_monitoring(self, instance_id: str) -> FixResult:
        """
        Enable detailed monitoring for EC2 instance.

        Args:
            instance_id: EC2 instance ID

        Returns:
            FixResult
        """
        if self.dry_run:
            return FixResult(
                fix_type=FixType.ENABLE_DETAILED_MONITORING,
                status=FixStatus.SKIPPED,
                instance_id=instance_id,
                description=f"[DRY-RUN] Would enable detailed monitoring for instance {instance_id}",
                details={"dry_run": True}
            )

        try:
            result = self._run_aws_command([
                "monitor-instances",
                "--instance-ids", instance_id
            ])

            if "Error" not in result:
                return FixResult(
                    fix_type=FixType.ENABLE_DETAILED_MONITORING,
                    status=FixStatus.SUCCESS,
                    instance_id=instance_id,
                    description=f"Enabled detailed monitoring for instance {instance_id}",
                    details={}
                )
            else:
                return FixResult(
                    fix_type=FixType.ENABLE_DETAILED_MONITORING,
                    status=FixStatus.FAILED,
                    instance_id=instance_id,
                    description=f"Failed to enable monitoring: {result['Error']}",
                    details={"error": result["Error"]}
                )

        except Exception as e:
            return FixResult(
                fix_type=FixType.ENABLE_DETAILED_MONITORING,
                status=FixStatus.FAILED,
                instance_id=instance_id,
                description=f"Exception: {str(e)}",
                details={"error": str(e)}
            )

    def enable_termination_protection(self, instance_id: str) -> FixResult:
        """
        Enable termination protection for EC2 instance.

        Args:
            instance_id: EC2 instance ID

        Returns:
            FixResult
        """
        if self.dry_run:
            return FixResult(
                fix_type=FixType.ENABLE_TERMINATION_PROTECTION,
                status=FixStatus.SKIPPED,
                instance_id=instance_id,
                description=f"[DRY-RUN] Would enable termination protection for instance {instance_id}",
                details={"dry_run": True}
            )

        try:
            result = self._run_aws_command([
                "modify-instance-attribute",
                "--instance-id", instance_id,
                "--disable-api-termination"
            ])

            if "Error" not in result:
                return FixResult(
                    fix_type=FixType.ENABLE_TERMINATION_PROTECTION,
                    status=FixStatus.SUCCESS,
                    instance_id=instance_id,
                    description=f"Enabled termination protection for instance {instance_id}",
                    details={}
                )
            else:
                return FixResult(
                    fix_type=FixType.ENABLE_TERMINATION_PROTECTION,
                    status=FixStatus.FAILED,
                    instance_id=instance_id,
                    description=f"Failed to enable termination protection: {result['Error']}",
                    details={"error": result["Error"]}
                )

        except Exception as e:
            return FixResult(
                fix_type=FixType.ENABLE_TERMINATION_PROTECTION,
                status=FixStatus.FAILED,
                instance_id=instance_id,
                description=f"Exception: {str(e)}",
                details={"error": str(e)}
            )


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix EC2 instance security issues")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--dry-run", action="store_true", help="Don't execute changes")
    parser.add_argument("--enable-imdsv2", help="Instance ID to enable IMDSv2")
    parser.add_argument("--enable-monitoring", help="Instance ID to enable detailed monitoring")
    parser.add_argument("--enable-termination-protection", help="Instance ID to enable termination protection")

    args = parser.parse_args()

    fixer = EC2Fixer(
        region=args.region,
        profile=args.profile,
        dry_run=args.dry_run
    )

    print(f"🔧 EC2 Security Fixer\n")
    print(f"Region: {args.region}")
    print(f"Dry-run: {args.dry_run}\n")

    results = []

    # Execute fixes
    if args.enable_imdsv2:
        print(f"📊 Enabling IMDSv2 for instance {args.enable_imdsv2}...\n")
        result = fixer.enable_imdsv2(args.enable_imdsv2)
        results.append(result)

    elif args.enable_monitoring:
        print(f"📊 Enabling detailed monitoring for instance {args.enable_monitoring}...\n")
        result = fixer.enable_detailed_monitoring(args.enable_monitoring)
        results.append(result)

    elif args.enable_termination_protection:
        print(f"📊 Enabling termination protection for instance {args.enable_termination_protection}...\n")
        result = fixer.enable_termination_protection(args.enable_termination_protection)
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
            print(f"   Instance: {result.instance_id}")
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
