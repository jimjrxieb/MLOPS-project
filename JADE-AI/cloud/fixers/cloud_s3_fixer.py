#!/usr/bin/env python3
"""
S3 Fixer for jsa-devsecops
Automatically fixes S3 bucket security issues.

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
    ENABLE_ENCRYPTION = "enable_encryption"
    ENABLE_VERSIONING = "enable_versioning"
    ENABLE_LOGGING = "enable_logging"
    ENABLE_PUBLIC_ACCESS_BLOCK = "enable_public_access_block"
    ENABLE_MFA_DELETE = "enable_mfa_delete"


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
    bucket_name: str
    description: str
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class S3Fixer:
    """
    Automatically fixes S3 bucket security issues.

    Features:
    - Enable default encryption (SSE-S3 or SSE-KMS)
    - Enable versioning
    - Enable access logging
    - Enable Block Public Access
    - Enable MFA Delete (requires root credentials)

    Example:
        fixer = S3Fixer(region="us-east-1", dry_run=True)

        # Enable encryption
        result = fixer.enable_encryption("my-bucket", "AES256")

        # Enable versioning
        result = fixer.enable_versioning("my-bucket")

        # Enable Block Public Access
        result = fixer.enable_public_access_block("my-bucket")
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None,
        dry_run: bool = True
    ):
        """
        Initialize S3 fixer.

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

            if result.returncode == 0:
                if result.stdout:
                    return json.loads(result.stdout)
                return {"Success": True}

            return {"Error": result.stderr}

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            return {"Error": str(e)}

    def enable_encryption(
        self,
        bucket_name: str,
        sse_algorithm: str = "AES256",
        kms_master_key_id: str = None
    ) -> FixResult:
        """
        Enable default encryption for S3 bucket.

        Args:
            bucket_name: S3 bucket name
            sse_algorithm: "AES256" (SSE-S3) or "aws:kms" (SSE-KMS)
            kms_master_key_id: KMS key ID (required if sse_algorithm is aws:kms)

        Returns:
            FixResult
        """
        if self.dry_run:
            return FixResult(
                fix_type=FixType.ENABLE_ENCRYPTION,
                status=FixStatus.SKIPPED,
                bucket_name=bucket_name,
                description=f"[DRY-RUN] Would enable {sse_algorithm} encryption for bucket {bucket_name}",
                details={"dry_run": True, "algorithm": sse_algorithm}
            )

        try:
            # Build encryption configuration
            encryption_config = {
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": sse_algorithm
                        },
                        "BucketKeyEnabled": True
                    }
                ]
            }

            if sse_algorithm == "aws:kms" and kms_master_key_id:
                encryption_config["Rules"][0]["ApplyServerSideEncryptionByDefault"]["KMSMasterKeyID"] = kms_master_key_id

            result = self._run_aws_command([
                "put-bucket-encryption",
                "--bucket", bucket_name,
                "--server-side-encryption-configuration", json.dumps(encryption_config)
            ])

            if "Error" not in result:
                return FixResult(
                    fix_type=FixType.ENABLE_ENCRYPTION,
                    status=FixStatus.SUCCESS,
                    bucket_name=bucket_name,
                    description=f"Enabled {sse_algorithm} encryption for bucket {bucket_name}",
                    details={"algorithm": sse_algorithm}
                )
            else:
                return FixResult(
                    fix_type=FixType.ENABLE_ENCRYPTION,
                    status=FixStatus.FAILED,
                    bucket_name=bucket_name,
                    description=f"Failed to enable encryption: {result['Error']}",
                    details={"error": result["Error"]}
                )

        except Exception as e:
            return FixResult(
                fix_type=FixType.ENABLE_ENCRYPTION,
                status=FixStatus.FAILED,
                bucket_name=bucket_name,
                description=f"Exception: {str(e)}",
                details={"error": str(e)}
            )

    def enable_versioning(self, bucket_name: str) -> FixResult:
        """
        Enable versioning for S3 bucket.

        Args:
            bucket_name: S3 bucket name

        Returns:
            FixResult
        """
        if self.dry_run:
            return FixResult(
                fix_type=FixType.ENABLE_VERSIONING,
                status=FixStatus.SKIPPED,
                bucket_name=bucket_name,
                description=f"[DRY-RUN] Would enable versioning for bucket {bucket_name}",
                details={"dry_run": True}
            )

        try:
            result = self._run_aws_command([
                "put-bucket-versioning",
                "--bucket", bucket_name,
                "--versioning-configuration", "Status=Enabled"
            ])

            if "Error" not in result:
                return FixResult(
                    fix_type=FixType.ENABLE_VERSIONING,
                    status=FixStatus.SUCCESS,
                    bucket_name=bucket_name,
                    description=f"Enabled versioning for bucket {bucket_name}",
                    details={}
                )
            else:
                return FixResult(
                    fix_type=FixType.ENABLE_VERSIONING,
                    status=FixStatus.FAILED,
                    bucket_name=bucket_name,
                    description=f"Failed to enable versioning: {result['Error']}",
                    details={"error": result["Error"]}
                )

        except Exception as e:
            return FixResult(
                fix_type=FixType.ENABLE_VERSIONING,
                status=FixStatus.FAILED,
                bucket_name=bucket_name,
                description=f"Exception: {str(e)}",
                details={"error": str(e)}
            )

    def enable_logging(
        self,
        bucket_name: str,
        target_bucket: str,
        target_prefix: str = "logs/"
    ) -> FixResult:
        """
        Enable access logging for S3 bucket.

        Args:
            bucket_name: S3 bucket name
            target_bucket: Target bucket for logs
            target_prefix: Prefix for log objects

        Returns:
            FixResult
        """
        if self.dry_run:
            return FixResult(
                fix_type=FixType.ENABLE_LOGGING,
                status=FixStatus.SKIPPED,
                bucket_name=bucket_name,
                description=f"[DRY-RUN] Would enable logging for bucket {bucket_name} to {target_bucket}",
                details={"dry_run": True, "target_bucket": target_bucket}
            )

        try:
            logging_config = {
                "LoggingEnabled": {
                    "TargetBucket": target_bucket,
                    "TargetPrefix": target_prefix
                }
            }

            result = self._run_aws_command([
                "put-bucket-logging",
                "--bucket", bucket_name,
                "--bucket-logging-status", json.dumps(logging_config)
            ])

            if "Error" not in result:
                return FixResult(
                    fix_type=FixType.ENABLE_LOGGING,
                    status=FixStatus.SUCCESS,
                    bucket_name=bucket_name,
                    description=f"Enabled logging for bucket {bucket_name} to {target_bucket}",
                    details={"target_bucket": target_bucket, "prefix": target_prefix}
                )
            else:
                return FixResult(
                    fix_type=FixType.ENABLE_LOGGING,
                    status=FixStatus.FAILED,
                    bucket_name=bucket_name,
                    description=f"Failed to enable logging: {result['Error']}",
                    details={"error": result["Error"]}
                )

        except Exception as e:
            return FixResult(
                fix_type=FixType.ENABLE_LOGGING,
                status=FixStatus.FAILED,
                bucket_name=bucket_name,
                description=f"Exception: {str(e)}",
                details={"error": str(e)}
            )

    def enable_public_access_block(self, bucket_name: str) -> FixResult:
        """
        Enable Block Public Access for S3 bucket.

        Args:
            bucket_name: S3 bucket name

        Returns:
            FixResult
        """
        if self.dry_run:
            return FixResult(
                fix_type=FixType.ENABLE_PUBLIC_ACCESS_BLOCK,
                status=FixStatus.SKIPPED,
                bucket_name=bucket_name,
                description=f"[DRY-RUN] Would enable Block Public Access for bucket {bucket_name}",
                details={"dry_run": True}
            )

        try:
            # Enable all Block Public Access settings
            public_access_config = {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True
            }

            result = self._run_aws_command([
                "put-public-access-block",
                "--bucket", bucket_name,
                "--public-access-block-configuration", json.dumps(public_access_config)
            ])

            if "Error" not in result:
                return FixResult(
                    fix_type=FixType.ENABLE_PUBLIC_ACCESS_BLOCK,
                    status=FixStatus.SUCCESS,
                    bucket_name=bucket_name,
                    description=f"Enabled Block Public Access for bucket {bucket_name}",
                    details={}
                )
            else:
                return FixResult(
                    fix_type=FixType.ENABLE_PUBLIC_ACCESS_BLOCK,
                    status=FixStatus.FAILED,
                    bucket_name=bucket_name,
                    description=f"Failed to enable Block Public Access: {result['Error']}",
                    details={"error": result["Error"]}
                )

        except Exception as e:
            return FixResult(
                fix_type=FixType.ENABLE_PUBLIC_ACCESS_BLOCK,
                status=FixStatus.FAILED,
                bucket_name=bucket_name,
                description=f"Exception: {str(e)}",
                details={"error": str(e)}
            )


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix S3 bucket security issues")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--dry-run", action="store_true", help="Don't execute changes")
    parser.add_argument("--enable-encryption", help="Bucket name to enable encryption")
    parser.add_argument("--sse-algorithm", choices=["AES256", "aws:kms"], default="AES256",
                        help="Encryption algorithm")
    parser.add_argument("--kms-key-id", help="KMS key ID (if using aws:kms)")
    parser.add_argument("--enable-versioning", help="Bucket name to enable versioning")
    parser.add_argument("--enable-logging", help="Bucket name to enable logging")
    parser.add_argument("--target-bucket", help="Target bucket for logs")
    parser.add_argument("--enable-public-access-block", help="Bucket name to enable Block Public Access")

    args = parser.parse_args()

    fixer = S3Fixer(
        region=args.region,
        profile=args.profile,
        dry_run=args.dry_run
    )

    print(f"🔧 S3 Security Fixer\n")
    print(f"Region: {args.region}")
    print(f"Dry-run: {args.dry_run}\n")

    results = []

    # Execute fixes
    if args.enable_encryption:
        print(f"📊 Enabling encryption for bucket {args.enable_encryption}...\n")
        result = fixer.enable_encryption(args.enable_encryption, args.sse_algorithm, args.kms_key_id)
        results.append(result)

    elif args.enable_versioning:
        print(f"📊 Enabling versioning for bucket {args.enable_versioning}...\n")
        result = fixer.enable_versioning(args.enable_versioning)
        results.append(result)

    elif args.enable_logging and args.target_bucket:
        print(f"📊 Enabling logging for bucket {args.enable_logging}...\n")
        result = fixer.enable_logging(args.enable_logging, args.target_bucket)
        results.append(result)

    elif args.enable_public_access_block:
        print(f"📊 Enabling Block Public Access for bucket {args.enable_public_access_block}...\n")
        result = fixer.enable_public_access_block(args.enable_public_access_block)
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
            print(f"   Bucket: {result.bucket_name}")
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
