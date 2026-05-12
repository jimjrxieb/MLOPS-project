#!/usr/bin/env python3
"""
CloudFormation Fixer for jsa-devsecops
Automatically fixes common CloudFormation security issues.

Author: jsa-devsecops
Created: 2025-12-31
"""

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
import yaml


class FixType(Enum):
    """Types of fixes."""
    ENABLE_ENCRYPTION = "enable_encryption"
    RESTRICT_SECURITY_GROUP = "restrict_security_group"
    REMOVE_PUBLIC_ACCESS = "remove_public_access"
    ENABLE_LOGGING = "enable_logging"
    RESTRICT_IAM_POLICY = "restrict_iam_policy"
    UPDATE_SSL_POLICY = "update_ssl_policy"


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
    file_path: Path
    resource_type: str
    logical_id: str
    description: str
    backup_path: Optional[Path] = None
    error_message: str = ""


class CloudFormationFixer:
    """
    Automatically fixes CloudFormation security issues.

    Features:
    - Enable S3/RDS encryption
    - Restrict security groups
    - Remove public access flags
    - Enable logging
    - Update TLS policies

    Example:
        fixer = CloudFormationFixer(template_dir="/infra/cloudformation")

        # Fix all encryption issues
        results = fixer.fix_encryption()

        # Fix all issues (dry-run)
        fixer = CloudFormationFixer(template_dir="/infra", dry_run=True)
        results = fixer.fix_all()
    """

    def __init__(
        self,
        template_dir: Path = None,
        template_file: Path = None,
        backup_dir: Path = None,
        dry_run: bool = False
    ):
        """
        Initialize CloudFormation fixer.

        Args:
            template_dir: Directory containing CloudFormation templates
            template_file: Single template file to fix
            backup_dir: Backup directory
            dry_run: If True, don't modify files
        """
        self.template_dir = template_dir or Path.cwd()
        self.template_file = template_file
        self.backup_dir = backup_dir or (self.template_dir / ".cfn-backups")
        self.dry_run = dry_run

        if not self.dry_run:
            self.backup_dir.mkdir(exist_ok=True, parents=True)

    def fix_all(self) -> List[FixResult]:
        """Fix all supported security issues."""
        results = []

        results.extend(self.fix_encryption())
        results.extend(self.fix_public_access())
        results.extend(self.fix_logging())
        results.extend(self.fix_ssl_policies())

        return results

    def fix_encryption(self) -> List[FixResult]:
        """Fix all encryption issues."""
        results = []

        templates = self._get_templates()

        for template_file in templates:
            template_data = self._load_template(template_file)
            if not template_data:
                continue

            modified = False

            # Fix S3 encryption
            s3_results = self._fix_s3_encryption(template_data)
            if s3_results:
                modified = True
                results.extend([(template_file, r) for r in s3_results])

            # Fix RDS encryption
            rds_results = self._fix_rds_encryption(template_data)
            if rds_results:
                modified = True
                results.extend([(template_file, r) for r in rds_results])

            # Fix EBS encryption
            ebs_results = self._fix_ebs_encryption(template_data)
            if ebs_results:
                modified = True
                results.extend([(template_file, r) for r in ebs_results])

            # Save template if modified
            if modified and not self.dry_run:
                self._save_template(template_file, template_data)

        # Update file paths in results
        final_results = []
        for template_file, result in results:
            result.file_path = template_file
            final_results.append(result)

        return final_results

    def fix_public_access(self) -> List[FixResult]:
        """Fix public access issues."""
        results = []

        templates = self._get_templates()

        for template_file in templates:
            template_data = self._load_template(template_file)
            if not template_data:
                continue

            modified = False

            # Fix RDS public access
            rds_results = self._fix_rds_public_access(template_data)
            if rds_results:
                modified = True
                results.extend([(template_file, r) for r in rds_results])

            # Fix S3 public access
            s3_results = self._fix_s3_public_access(template_data)
            if s3_results:
                modified = True
                results.extend([(template_file, r) for r in s3_results])

            # Save template if modified
            if modified and not self.dry_run:
                self._save_template(template_file, template_data)

        # Update file paths
        final_results = []
        for template_file, result in results:
            result.file_path = template_file
            final_results.append(result)

        return final_results

    def fix_logging(self) -> List[FixResult]:
        """Enable logging configurations."""
        results = []

        templates = self._get_templates()

        for template_file in templates:
            template_data = self._load_template(template_file)
            if not template_data:
                continue

            modified = False

            # Fix S3 logging
            s3_results = self._fix_s3_logging(template_data)
            if s3_results:
                modified = True
                results.extend([(template_file, r) for r in s3_results])

            # Save template if modified
            if modified and not self.dry_run:
                self._save_template(template_file, template_data)

        # Update file paths
        final_results = []
        for template_file, result in results:
            result.file_path = template_file
            final_results.append(result)

        return final_results

    def fix_ssl_policies(self) -> List[FixResult]:
        """Update insecure SSL/TLS policies."""
        results = []

        templates = self._get_templates()

        for template_file in templates:
            template_data = self._load_template(template_file)
            if not template_data:
                continue

            modified = False

            # Fix ALB listener SSL policies
            alb_results = self._fix_alb_ssl_policy(template_data)
            if alb_results:
                modified = True
                results.extend([(template_file, r) for r in alb_results])

            # Save template if modified
            if modified and not self.dry_run:
                self._save_template(template_file, template_data)

        # Update file paths
        final_results = []
        for template_file, result in results:
            result.file_path = template_file
            final_results.append(result)

        return final_results

    def _fix_s3_encryption(self, template_data: Dict) -> List[FixResult]:
        """Enable S3 bucket encryption."""
        results = []

        resources = template_data.get("Resources", {})

        for logical_id, resource in resources.items():
            if resource.get("Type") != "AWS::S3::Bucket":
                continue

            properties = resource.get("Properties", {})

            if "BucketEncryption" not in properties:
                # Add encryption
                properties["BucketEncryption"] = {
                    "ServerSideEncryptionConfiguration": [
                        {
                            "ServerSideEncryptionByDefault": {
                                "SSEAlgorithm": "AES256"
                            }
                        }
                    ]
                }

                results.append(FixResult(
                    fix_type=FixType.ENABLE_ENCRYPTION,
                    status=FixStatus.SUCCESS,
                    file_path=Path(),  # Will be set later
                    resource_type="AWS::S3::Bucket",
                    logical_id=logical_id,
                    description="Enabled server-side encryption for S3 bucket"
                ))

        return results

    def _fix_rds_encryption(self, template_data: Dict) -> List[FixResult]:
        """Enable RDS storage encryption."""
        results = []

        resources = template_data.get("Resources", {})

        for logical_id, resource in resources.items():
            if resource.get("Type") != "AWS::RDS::DBInstance":
                continue

            properties = resource.get("Properties", {})

            if "StorageEncrypted" not in properties or not properties.get("StorageEncrypted"):
                properties["StorageEncrypted"] = True

                results.append(FixResult(
                    fix_type=FixType.ENABLE_ENCRYPTION,
                    status=FixStatus.SUCCESS,
                    file_path=Path(),
                    resource_type="AWS::RDS::DBInstance",
                    logical_id=logical_id,
                    description="Enabled storage encryption for RDS instance"
                ))

        return results

    def _fix_ebs_encryption(self, template_data: Dict) -> List[FixResult]:
        """Enable EBS volume encryption."""
        results = []

        resources = template_data.get("Resources", {})

        for logical_id, resource in resources.items():
            if resource.get("Type") != "AWS::EC2::Volume":
                continue

            properties = resource.get("Properties", {})

            if "Encrypted" not in properties or not properties.get("Encrypted"):
                properties["Encrypted"] = True

                results.append(FixResult(
                    fix_type=FixType.ENABLE_ENCRYPTION,
                    status=FixStatus.SUCCESS,
                    file_path=Path(),
                    resource_type="AWS::EC2::Volume",
                    logical_id=logical_id,
                    description="Enabled encryption for EBS volume"
                ))

        return results

    def _fix_rds_public_access(self, template_data: Dict) -> List[FixResult]:
        """Disable RDS public accessibility."""
        results = []

        resources = template_data.get("Resources", {})

        for logical_id, resource in resources.items():
            if resource.get("Type") != "AWS::RDS::DBInstance":
                continue

            properties = resource.get("Properties", {})

            if properties.get("PubliclyAccessible"):
                properties["PubliclyAccessible"] = False

                results.append(FixResult(
                    fix_type=FixType.REMOVE_PUBLIC_ACCESS,
                    status=FixStatus.SUCCESS,
                    file_path=Path(),
                    resource_type="AWS::RDS::DBInstance",
                    logical_id=logical_id,
                    description="Disabled public accessibility for RDS instance"
                ))

        return results

    def _fix_s3_public_access(self, template_data: Dict) -> List[FixResult]:
        """Enable S3 public access block."""
        results = []

        resources = template_data.get("Resources", {})

        for logical_id, resource in resources.items():
            if resource.get("Type") != "AWS::S3::Bucket":
                continue

            properties = resource.get("Properties", {})

            if "PublicAccessBlockConfiguration" not in properties:
                properties["PublicAccessBlockConfiguration"] = {
                    "BlockPublicAcls": True,
                    "BlockPublicPolicy": True,
                    "IgnorePublicAcls": True,
                    "RestrictPublicBuckets": True
                }

                results.append(FixResult(
                    fix_type=FixType.REMOVE_PUBLIC_ACCESS,
                    status=FixStatus.SUCCESS,
                    file_path=Path(),
                    resource_type="AWS::S3::Bucket",
                    logical_id=logical_id,
                    description="Enabled public access block for S3 bucket"
                ))

        return results

    def _fix_s3_logging(self, template_data: Dict) -> List[FixResult]:
        """Enable S3 access logging."""
        results = []

        resources = template_data.get("Resources", {})

        for logical_id, resource in resources.items():
            if resource.get("Type") != "AWS::S3::Bucket":
                continue

            properties = resource.get("Properties", {})

            if "LoggingConfiguration" not in properties:
                # Add placeholder logging config
                # User must provide actual log bucket
                results.append(FixResult(
                    fix_type=FixType.ENABLE_LOGGING,
                    status=FixStatus.PARTIAL,
                    file_path=Path(),
                    resource_type="AWS::S3::Bucket",
                    logical_id=logical_id,
                    description="S3 bucket requires logging configuration",
                    error_message="Manual action required: Add LoggingConfiguration with DestinationBucketName"
                ))

        return results

    def _fix_alb_ssl_policy(self, template_data: Dict) -> List[FixResult]:
        """Update ALB listener SSL policy to TLS 1.2+."""
        results = []

        resources = template_data.get("Resources", {})

        for logical_id, resource in resources.items():
            if resource.get("Type") != "AWS::ElasticLoadBalancingV2::Listener":
                continue

            properties = resource.get("Properties", {})
            protocol = properties.get("Protocol", "")

            if protocol == "HTTPS":
                ssl_policy = properties.get("SslPolicy", "")

                # Update to TLS 1.2 policy
                if "TLS" not in ssl_policy or "1-2" not in ssl_policy:
                    properties["SslPolicy"] = "ELBSecurityPolicy-TLS-1-2-2017-01"

                    results.append(FixResult(
                        fix_type=FixType.UPDATE_SSL_POLICY,
                        status=FixStatus.SUCCESS,
                        file_path=Path(),
                        resource_type="AWS::ElasticLoadBalancingV2::Listener",
                        logical_id=logical_id,
                        description="Updated SSL policy to TLS 1.2 or higher"
                    ))

        return results

    def _get_templates(self) -> List[Path]:
        """Get list of CloudFormation template files."""
        if self.template_file:
            return [self.template_file]

        templates = list(self.template_dir.glob("**/*.yaml")) + \
                   list(self.template_dir.glob("**/*.yml")) + \
                   list(self.template_dir.glob("**/*.json"))

        # Filter for CloudFormation templates
        cfn_templates = []
        for template in templates:
            data = self._load_template(template)
            if data and ("AWSTemplateFormatVersion" in data or "Resources" in data):
                cfn_templates.append(template)

        return cfn_templates

    def _load_template(self, template_path: Path) -> Optional[Dict]:
        """Load CloudFormation template."""
        try:
            content = template_path.read_text()

            if template_path.suffix == ".json":
                return json.loads(content)
            else:
                return yaml.safe_load(content)
        except Exception:
            return None

    def _save_template(self, template_path: Path, template_data: Dict):
        """Save CloudFormation template."""
        # Backup original
        backup_path = self._backup_file(template_path)

        # Save modified template
        if template_path.suffix == ".json":
            template_path.write_text(json.dumps(template_data, indent=2))
        else:
            template_path.write_text(yaml.dump(template_data, default_flow_style=False, sort_keys=False))

    def _backup_file(self, file_path: Path) -> Path:
        """Create backup of file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.bak"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(file_path, backup_path)

        return backup_path


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix CloudFormation security issues")
    parser.add_argument("--template-dir", help="Directory containing CloudFormation templates")
    parser.add_argument("--template", help="Single template file to fix")
    parser.add_argument("--fix-type", choices=["encryption", "public-access", "logging", "ssl", "all"],
                        default="all", help="Type of fixes to apply")
    parser.add_argument("--dry-run", action="store_true", help="Don't modify files")
    parser.add_argument("--backup-dir", help="Backup directory")

    args = parser.parse_args()

    template_dir = Path(args.template_dir) if args.template_dir else None
    template_file = Path(args.template) if args.template else None
    backup_dir = Path(args.backup_dir) if args.backup_dir else None

    fixer = CloudFormationFixer(
        template_dir=template_dir,
        template_file=template_file,
        backup_dir=backup_dir,
        dry_run=args.dry_run
    )

    print(f"☁️  CloudFormation Fixer\n")
    print(f"Dry-run: {args.dry_run}\n")

    # Run fixes
    if args.fix_type == "encryption":
        results = fixer.fix_encryption()
    elif args.fix_type == "public-access":
        results = fixer.fix_public_access()
    elif args.fix_type == "logging":
        results = fixer.fix_logging()
    elif args.fix_type == "ssl":
        results = fixer.fix_ssl_policies()
    else:
        results = fixer.fix_all()

    # Display results
    print(f"📊 Fix Summary:")
    print(f"  Total fixes attempted: {len(results)}")
    print(f"  Success: {len([r for r in results if r.status == FixStatus.SUCCESS])}")
    print(f"  Partial: {len([r for r in results if r.status == FixStatus.PARTIAL])}")
    print(f"  Failed: {len([r for r in results if r.status == FixStatus.FAILED])}")
    print(f"  Skipped: {len([r for r in results if r.status == FixStatus.SKIPPED])}\n")

    if results:
        print(f"🔍 Fix Details:\n")
        for i, result in enumerate(results, 1):
            status_icon = {
                FixStatus.SUCCESS: "✅",
                FixStatus.PARTIAL: "⚠️ ",
                FixStatus.FAILED: "❌",
                FixStatus.SKIPPED: "⏭️ "
            }[result.status]

            print(f"{i}. {status_icon} {result.description}")
            print(f"   Resource: {result.resource_type} ({result.logical_id})")
            print(f"   File: {result.file_path}")

            if result.error_message:
                print(f"   Note: {result.error_message}")

            print()
