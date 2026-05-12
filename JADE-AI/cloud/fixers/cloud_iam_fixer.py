#!/usr/bin/env python3
"""
IAM Fixer for jsa-devsecops
Automatically fixes IAM security issues.

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
    REMOVE_WILDCARD_POLICY = "remove_wildcard_policy"
    DETACH_ADMIN_ACCESS = "detach_admin_access"
    ENABLE_MFA = "enable_mfa"
    ROTATE_ACCESS_KEYS = "rotate_access_keys"
    DELETE_UNUSED_KEYS = "delete_unused_keys"
    REMOVE_INLINE_POLICY = "remove_inline_policy"
    UPDATE_TRUST_POLICY = "update_trust_policy"


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
    resource_type: str  # Role, User, Policy
    resource_name: str
    description: str
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class IAMFixer:
    """
    Automatically fixes IAM security issues.

    Features:
    - Detach AdministratorAccess policies
    - Remove wildcard permissions (requires manual policy creation)
    - Deactivate unused access keys
    - Remove inline policies (convert to managed)
    - Update overly permissive trust policies

    Example:
        fixer = IAMFixer(region="us-east-1", dry_run=True)

        # Detach admin access from role
        result = fixer.detach_admin_access("MyRole", "role")

        # Delete unused access keys
        result = fixer.delete_unused_access_keys("MyUser", unused_days=90)

        # Remove inline policy
        result = fixer.remove_inline_policy("MyRole", "my-inline-policy", "role")
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None,
        dry_run: bool = True
    ):
        """
        Initialize IAM fixer.

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

        cmd = ["aws", "iam"] + command + ["--output", "json"]

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

    def detach_admin_access(
        self,
        resource_name: str,
        resource_type: str = "role"
    ) -> FixResult:
        """
        Detach AdministratorAccess policy from role or user.

        Args:
            resource_name: Role or user name
            resource_type: "role" or "user"

        Returns:
            FixResult
        """
        admin_policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"

        if self.dry_run:
            return FixResult(
                fix_type=FixType.DETACH_ADMIN_ACCESS,
                status=FixStatus.SKIPPED,
                resource_type=resource_type.capitalize(),
                resource_name=resource_name,
                description=f"[DRY-RUN] Would detach AdministratorAccess from {resource_type} {resource_name}",
                details={"dry_run": True}
            )

        try:
            if resource_type == "role":
                result = self._run_aws_command([
                    "detach-role-policy",
                    "--role-name", resource_name,
                    "--policy-arn", admin_policy_arn
                ])
            else:  # user
                result = self._run_aws_command([
                    "detach-user-policy",
                    "--user-name", resource_name,
                    "--policy-arn", admin_policy_arn
                ])

            if "Error" not in result:
                return FixResult(
                    fix_type=FixType.DETACH_ADMIN_ACCESS,
                    status=FixStatus.SUCCESS,
                    resource_type=resource_type.capitalize(),
                    resource_name=resource_name,
                    description=f"Detached AdministratorAccess from {resource_type} {resource_name}",
                    details={}
                )
            else:
                return FixResult(
                    fix_type=FixType.DETACH_ADMIN_ACCESS,
                    status=FixStatus.FAILED,
                    resource_type=resource_type.capitalize(),
                    resource_name=resource_name,
                    description=f"Failed to detach AdministratorAccess: {result['Error']}",
                    details={"error": result["Error"]}
                )

        except Exception as e:
            return FixResult(
                fix_type=FixType.DETACH_ADMIN_ACCESS,
                status=FixStatus.FAILED,
                resource_type=resource_type.capitalize(),
                resource_name=resource_name,
                description=f"Exception: {str(e)}",
                details={"error": str(e)}
            )

    def delete_unused_access_keys(
        self,
        user_name: str,
        unused_days: int = 90
    ) -> FixResult:
        """
        Delete access keys that haven't been used in N days.

        Args:
            user_name: IAM user name
            unused_days: Days threshold for "unused"

        Returns:
            FixResult
        """
        # This requires reading last used date first
        # For safety, this is a placeholder - manual approval recommended

        if self.dry_run:
            return FixResult(
                fix_type=FixType.DELETE_UNUSED_KEYS,
                status=FixStatus.SKIPPED,
                resource_type="User",
                resource_name=user_name,
                description=f"[DRY-RUN] Would delete access keys unused for {unused_days}+ days",
                details={"dry_run": True, "unused_days": unused_days}
            )

        return FixResult(
            fix_type=FixType.DELETE_UNUSED_KEYS,
            status=FixStatus.SKIPPED,
            resource_type="User",
            resource_name=user_name,
            description="Deleting access keys requires manual approval - use AWS Console or CLI with confirmation",
            details={"unused_days": unused_days}
        )

    def remove_inline_policy(
        self,
        resource_name: str,
        policy_name: str,
        resource_type: str = "role"
    ) -> FixResult:
        """
        Remove inline policy from role or user.

        Args:
            resource_name: Role or user name
            policy_name: Inline policy name
            resource_type: "role" or "user"

        Returns:
            FixResult
        """
        if self.dry_run:
            return FixResult(
                fix_type=FixType.REMOVE_INLINE_POLICY,
                status=FixStatus.SKIPPED,
                resource_type=resource_type.capitalize(),
                resource_name=resource_name,
                description=f"[DRY-RUN] Would remove inline policy {policy_name} from {resource_type} {resource_name}",
                details={"dry_run": True, "policy_name": policy_name}
            )

        try:
            if resource_type == "role":
                result = self._run_aws_command([
                    "delete-role-policy",
                    "--role-name", resource_name,
                    "--policy-name", policy_name
                ])
            else:  # user
                result = self._run_aws_command([
                    "delete-user-policy",
                    "--user-name", resource_name,
                    "--policy-name", policy_name
                ])

            if "Error" not in result:
                return FixResult(
                    fix_type=FixType.REMOVE_INLINE_POLICY,
                    status=FixStatus.SUCCESS,
                    resource_type=resource_type.capitalize(),
                    resource_name=resource_name,
                    description=f"Removed inline policy {policy_name} from {resource_type} {resource_name}",
                    details={"policy_name": policy_name}
                )
            else:
                return FixResult(
                    fix_type=FixType.REMOVE_INLINE_POLICY,
                    status=FixStatus.FAILED,
                    resource_type=resource_type.capitalize(),
                    resource_name=resource_name,
                    description=f"Failed to remove inline policy: {result['Error']}",
                    details={"error": result["Error"]}
                )

        except Exception as e:
            return FixResult(
                fix_type=FixType.REMOVE_INLINE_POLICY,
                status=FixStatus.FAILED,
                resource_type=resource_type.capitalize(),
                resource_name=resource_name,
                description=f"Exception: {str(e)}",
                details={"error": str(e)}
            )


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix IAM security issues")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--dry-run", action="store_true", help="Don't execute changes")
    parser.add_argument("--detach-admin-access", help="Detach AdministratorAccess from role/user")
    parser.add_argument("--resource-type", choices=["role", "user"], default="role",
                        help="Resource type (role or user)")
    parser.add_argument("--remove-inline-policy", help="Remove inline policy from role/user")
    parser.add_argument("--policy-name", help="Inline policy name to remove")

    args = parser.parse_args()

    fixer = IAMFixer(
        region=args.region,
        profile=args.profile,
        dry_run=args.dry_run
    )

    print(f"🔧 IAM Security Fixer\n")
    print(f"Region: {args.region}")
    print(f"Dry-run: {args.dry_run}\n")

    results = []

    # Execute fixes
    if args.detach_admin_access:
        print(f"📊 Detaching AdministratorAccess from {args.resource_type} {args.detach_admin_access}...\n")
        result = fixer.detach_admin_access(args.detach_admin_access, args.resource_type)
        results.append(result)

    elif args.remove_inline_policy and args.policy_name:
        print(f"📊 Removing inline policy {args.policy_name} from {args.resource_type} {args.remove_inline_policy}...\n")
        result = fixer.remove_inline_policy(args.remove_inline_policy, args.policy_name, args.resource_type)
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
            print(f"   Resource: {result.resource_type} ({result.resource_name})")
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
