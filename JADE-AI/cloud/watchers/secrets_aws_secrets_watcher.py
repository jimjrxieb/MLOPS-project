#!/usr/bin/env python3
"""
AWS Secrets Manager Watcher for jsa-devsecops
Monitors AWS Secrets Manager for secret rotation and security events.

Author: jsa-devsecops
Created: 2025-12-31
"""

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


class AWSSecretEventType(Enum):
    """Types of AWS Secrets Manager events."""
    SECRET_ROTATION_DUE = "secret_rotation_due"
    SECRET_ROTATION_FAILED = "secret_rotation_failed"
    SECRET_NOT_ROTATED = "secret_not_rotated"
    SECRET_ACCESSED = "secret_accessed"
    SECRET_DELETED = "secret_deleted"
    SECRET_UPDATED = "secret_updated"
    SECRET_CREATED = "secret_created"
    ROTATION_DISABLED = "rotation_disabled"
    KMS_KEY_MISSING = "kms_key_missing"
    REPLICA_REGION_MISMATCH = "replica_region_mismatch"
    SECRET_VERSION_DEPRECATED = "secret_version_deprecated"


@dataclass
class AWSSecret:
    """Represents an AWS Secrets Manager secret."""
    arn: str
    name: str
    description: str
    rotation_enabled: bool
    rotation_lambda_arn: Optional[str] = None
    rotation_rules: Dict = field(default_factory=dict)
    last_rotated_date: Optional[datetime] = None
    last_accessed_date: Optional[datetime] = None
    last_changed_date: Optional[datetime] = None
    kms_key_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class AWSSecretEvent:
    """Represents an AWS Secrets Manager security event."""
    event_type: AWSSecretEventType
    timestamp: datetime
    secret_arn: str
    secret_name: str
    details: Dict
    risk_level: str  # Critical, High, Medium, Low
    recommendation: str = ""


class AWSSecretsWatcher:
    """
    Monitors AWS Secrets Manager for secret rotation and security events.

    Features:
    - Secret rotation tracking
    - Rotation failure detection
    - KMS key validation
    - Access pattern monitoring
    - Secret lifecycle tracking
    - Compliance checks (rotation policies)

    Example:
        watcher = AWSSecretsWatcher(region="us-east-1")

        # Watch a specific secret
        events = watcher.watch_secret("my-database-password")

        # Watch all secrets
        events = watcher.watch_all_secrets()

        # Check rotation status
        rotation_events = watcher.check_rotation_status()

        # Find secrets without rotation
        unrotated = watcher.find_unrotated_secrets()
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: Optional[str] = None,
        rotation_threshold_days: int = 90
    ):
        """
        Initialize AWS Secrets Manager watcher.

        Args:
            region: AWS region
            profile: AWS profile name
            rotation_threshold_days: Days before rotation is recommended
        """
        self.region = region
        self.profile = profile
        self.rotation_threshold_days = rotation_threshold_days
        self.secret_state: Dict[str, AWSSecret] = {}

    def _run_aws_command(self, command: List[str]) -> Dict:
        """Run AWS CLI command and return JSON output."""
        cmd = ["aws", "secretsmanager"] + command + [
            "--region", self.region,
            "--output", "json"
        ]

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

    def watch_secret(self, secret_name: str) -> List[AWSSecretEvent]:
        """
        Watch a specific secret for changes and security events.

        Args:
            secret_name: Secret name or ARN

        Returns:
            List of AWSSecretEvent objects
        """
        events = []

        # Describe the secret
        result = self._run_aws_command([
            "describe-secret",
            "--secret-id", secret_name
        ])

        if not result:
            return events

        # Extract secret details
        arn = result.get("ARN", "")
        name = result.get("Name", secret_name)
        description = result.get("Description", "")
        rotation_enabled = result.get("RotationEnabled", False)
        rotation_lambda_arn = result.get("RotationLambdaARN")
        rotation_rules = result.get("RotationRules", {})
        kms_key_id = result.get("KMSKeyId")
        tags = {tag["Key"]: tag["Value"] for tag in result.get("Tags", [])}

        # Parse dates
        last_rotated_date = None
        last_accessed_date = None
        last_changed_date = None

        if "LastRotatedDate" in result:
            last_rotated_date = datetime.fromtimestamp(result["LastRotatedDate"])

        if "LastAccessedDate" in result:
            last_accessed_date = datetime.fromtimestamp(result["LastAccessedDate"])

        if "LastChangedDate" in result:
            last_changed_date = datetime.fromtimestamp(result["LastChangedDate"])

        # Create secret object
        secret = AWSSecret(
            arn=arn,
            name=name,
            description=description,
            rotation_enabled=rotation_enabled,
            rotation_lambda_arn=rotation_lambda_arn,
            rotation_rules=rotation_rules,
            last_rotated_date=last_rotated_date,
            last_accessed_date=last_accessed_date,
            last_changed_date=last_changed_date,
            kms_key_id=kms_key_id,
            tags=tags
        )

        # Check if secret was in previous state
        if arn in self.secret_state:
            old_secret = self.secret_state[arn]

            # Detect rotation status change
            if old_secret.rotation_enabled != secret.rotation_enabled:
                if not secret.rotation_enabled:
                    events.append(AWSSecretEvent(
                        event_type=AWSSecretEventType.ROTATION_DISABLED,
                        timestamp=datetime.now(),
                        secret_arn=arn,
                        secret_name=name,
                        details={},
                        risk_level="High",
                        recommendation="Rotation was disabled - re-enable automatic rotation"
                    ))

            # Detect secret update
            if old_secret.last_changed_date and secret.last_changed_date:
                if secret.last_changed_date > old_secret.last_changed_date:
                    events.append(AWSSecretEvent(
                        event_type=AWSSecretEventType.SECRET_UPDATED,
                        timestamp=datetime.now(),
                        secret_arn=arn,
                        secret_name=name,
                        details={
                            "changed_at": secret.last_changed_date.isoformat()
                        },
                        risk_level="Low",
                        recommendation="Secret was updated - verify this was intentional"
                    ))

        # Check rotation status
        if not rotation_enabled:
            events.append(AWSSecretEvent(
                event_type=AWSSecretEventType.ROTATION_DISABLED,
                timestamp=datetime.now(),
                secret_arn=arn,
                secret_name=name,
                details={},
                risk_level="High",
                recommendation="Enable automatic rotation for this secret"
            ))
        elif last_rotated_date:
            days_since_rotation = (datetime.now() - last_rotated_date).days

            if days_since_rotation > self.rotation_threshold_days:
                events.append(AWSSecretEvent(
                    event_type=AWSSecretEventType.SECRET_ROTATION_DUE,
                    timestamp=datetime.now(),
                    secret_arn=arn,
                    secret_name=name,
                    details={
                        "days_since_rotation": days_since_rotation,
                        "threshold": self.rotation_threshold_days,
                        "last_rotated": last_rotated_date.isoformat()
                    },
                    risk_level="High",
                    recommendation=f"Secret has not been rotated in {days_since_rotation} days"
                ))
        else:
            # Rotation enabled but never rotated
            events.append(AWSSecretEvent(
                event_type=AWSSecretEventType.SECRET_NOT_ROTATED,
                timestamp=datetime.now(),
                secret_arn=arn,
                secret_name=name,
                details={},
                risk_level="High",
                recommendation="Rotation is enabled but secret has never been rotated"
            ))

        # Check for KMS key
        if not kms_key_id:
            events.append(AWSSecretEvent(
                event_type=AWSSecretEventType.KMS_KEY_MISSING,
                timestamp=datetime.now(),
                secret_arn=arn,
                secret_name=name,
                details={},
                risk_level="Medium",
                recommendation="Secret is not encrypted with a customer-managed KMS key"
            ))

        # Update state
        self.secret_state[arn] = secret

        return events

    def watch_all_secrets(self) -> List[AWSSecretEvent]:
        """
        Watch all secrets in the region.

        Returns:
            List of AWSSecretEvent objects
        """
        all_events = []

        # List all secrets
        result = self._run_aws_command(["list-secrets"])

        if not result or "SecretList" not in result:
            return all_events

        for secret in result["SecretList"]:
            secret_name = secret.get("Name", "")
            if secret_name:
                events = self.watch_secret(secret_name)
                all_events.extend(events)

        return all_events

    def check_rotation_status(self) -> List[AWSSecretEvent]:
        """
        Check rotation status for all secrets.

        Returns:
            List of AWSSecretEvent objects for rotation issues
        """
        events = []

        result = self._run_aws_command(["list-secrets"])

        if not result or "SecretList" not in result:
            return events

        for secret in result["SecretList"]:
            name = secret.get("Name", "")
            arn = secret.get("ARN", "")
            rotation_enabled = secret.get("RotationEnabled", False)

            if not rotation_enabled:
                events.append(AWSSecretEvent(
                    event_type=AWSSecretEventType.ROTATION_DISABLED,
                    timestamp=datetime.now(),
                    secret_arn=arn,
                    secret_name=name,
                    details={},
                    risk_level="High",
                    recommendation=f"Enable rotation: aws secretsmanager rotate-secret --secret-id {name}"
                ))

        return events

    def find_unrotated_secrets(self, days: int = 90) -> List[AWSSecretEvent]:
        """
        Find secrets that haven't been rotated in N days.

        Args:
            days: Number of days threshold

        Returns:
            List of AWSSecretEvent objects
        """
        events = []

        result = self._run_aws_command(["list-secrets"])

        if not result or "SecretList" not in result:
            return events

        threshold_date = datetime.now() - timedelta(days=days)

        for secret in result["SecretList"]:
            name = secret.get("Name", "")
            arn = secret.get("ARN", "")
            last_rotated_timestamp = secret.get("LastRotatedDate")

            if last_rotated_timestamp:
                last_rotated = datetime.fromtimestamp(last_rotated_timestamp)

                if last_rotated < threshold_date:
                    days_since = (datetime.now() - last_rotated).days
                    events.append(AWSSecretEvent(
                        event_type=AWSSecretEventType.SECRET_ROTATION_DUE,
                        timestamp=datetime.now(),
                        secret_arn=arn,
                        secret_name=name,
                        details={
                            "days_since_rotation": days_since,
                            "last_rotated": last_rotated.isoformat()
                        },
                        risk_level="High",
                        recommendation=f"Rotate secret (last rotated {days_since} days ago)"
                    ))

        return events

    def check_rotation_failures(self) -> List[AWSSecretEvent]:
        """
        Check for recent rotation failures using CloudWatch Logs.

        Returns:
            List of AWSSecretEvent objects
        """
        # This would require CloudWatch Logs integration
        # Placeholder for future implementation
        return []


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitor AWS Secrets Manager")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--watch-secret", help="Watch a specific secret")
    parser.add_argument("--watch-all", action="store_true", help="Watch all secrets")
    parser.add_argument("--check-rotation", action="store_true", help="Check rotation status")
    parser.add_argument("--find-unrotated", type=int, metavar="DAYS",
                        help="Find secrets not rotated in N days")

    args = parser.parse_args()

    watcher = AWSSecretsWatcher(
        region=args.region,
        profile=args.profile
    )

    print(f"🔍 AWS Secrets Manager Watcher\n")
    print(f"Region: {args.region}\n")

    events = []

    # Run requested checks
    if args.watch_secret:
        print(f"📊 Watching secret: {args.watch_secret}\n")
        events = watcher.watch_secret(args.watch_secret)
    elif args.watch_all:
        print(f"📊 Watching all secrets...\n")
        events = watcher.watch_all_secrets()
    elif args.check_rotation:
        print(f"📊 Checking rotation status...\n")
        events = watcher.check_rotation_status()
    elif args.find_unrotated:
        print(f"📊 Finding secrets not rotated in {args.find_unrotated} days...\n")
        events = watcher.find_unrotated_secrets(days=args.find_unrotated)
    else:
        parser.print_help()
        exit(0)

    # Display results
    if not events:
        print("✅ No security events detected\n")
    else:
        print(f"📋 Security Events ({len(events)}):\n")

        # Group by risk level
        events_by_risk = {
            "Critical": [],
            "High": [],
            "Medium": [],
            "Low": []
        }

        for event in events:
            events_by_risk[event.risk_level].append(event)

        # Display by risk level
        risk_icons = {
            "Critical": "🔴",
            "High": "🟠",
            "Medium": "🟡",
            "Low": "🟢"
        }

        for risk_level in ["Critical", "High", "Medium", "Low"]:
            risk_events = events_by_risk[risk_level]
            if not risk_events:
                continue

            print(f"{risk_icons[risk_level]} {risk_level.upper()} ({len(risk_events)} events):\n")

            for i, event in enumerate(risk_events, 1):
                print(f"  {i}. {event.event_type.value.upper()}")
                print(f"     Secret: {event.secret_name}")
                print(f"     ARN: {event.secret_arn}")
                print(f"     💡 {event.recommendation}")
                if event.details:
                    print(f"     Details: {json.dumps(event.details, indent=6)}")
                print()

        # Summary
        print(f"📊 Summary:")
        print(f"  Total Events: {len(events)}")
        print(f"  Critical: {len(events_by_risk['Critical'])}")
        print(f"  High: {len(events_by_risk['High'])}")
        print(f"  Medium: {len(events_by_risk['Medium'])}")
        print(f"  Low: {len(events_by_risk['Low'])}")
        print()
