#!/usr/bin/env python3
"""
S3 Watcher for jsa-devsecops
Monitors AWS S3 buckets for security configuration changes.

Author: jsa-devsecops
Created: 2025-12-31
"""

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class S3EventType(Enum):
    """S3 event types."""
    BUCKET_CREATED = "bucket_created"
    BUCKET_DELETED = "bucket_deleted"
    ENCRYPTION_DISABLED = "encryption_disabled"
    ENCRYPTION_ENABLED = "encryption_enabled"
    PUBLIC_ACCESS_ENABLED = "public_access_enabled"
    PUBLIC_ACCESS_DISABLED = "public_access_disabled"
    VERSIONING_DISABLED = "versioning_disabled"
    LOGGING_DISABLED = "logging_disabled"
    POLICY_MODIFIED = "policy_modified"


@dataclass
class S3Bucket:
    """S3 bucket details."""
    bucket_name: str
    creation_date: datetime
    region: str
    encryption_enabled: bool = False
    encryption_algorithm: Optional[str] = None
    versioning_enabled: bool = False
    logging_enabled: bool = False
    logging_target_bucket: Optional[str] = None
    public_access_block: Optional[Dict] = None
    bucket_policy: Optional[Dict] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class S3Event:
    """S3 change event."""
    event_type: S3EventType
    timestamp: datetime
    bucket_name: str
    details: Dict = field(default_factory=dict)
    risk_level: str = "Medium"  # Critical, High, Medium, Low


class S3Watcher:
    """
    Watches AWS S3 buckets for security changes.

    Features:
    - Monitor bucket encryption status
    - Detect public access configuration changes
    - Track versioning status
    - Monitor logging configuration
    - Alert on bucket policy changes

    Example:
        watcher = S3Watcher(region="us-east-1", profile="prod")

        # Watch all buckets
        events = watcher.watch_buckets()

        # Watch specific bucket
        bucket_events = watcher.watch_bucket("my-bucket")

        # Get publicly accessible buckets
        public_buckets = watcher.get_public_buckets()

        # Get unencrypted buckets
        unencrypted = watcher.get_unencrypted_buckets()
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None,
        dry_run: bool = False
    ):
        """
        Initialize S3 watcher.

        Args:
            region: AWS region
            profile: AWS profile name
            dry_run: If True, don't execute AWS API calls
        """
        self.region = region
        self.profile = profile
        self.dry_run = dry_run

        # Track S3 buckets
        self.tracked_buckets: Dict[str, S3Bucket] = {}

    def watch_buckets(self) -> List[S3Event]:
        """
        Watch all S3 buckets.

        Returns:
            List of S3Event objects
        """
        events = []

        if self.dry_run:
            return events

        # List all buckets
        buckets = self._list_buckets()

        for bucket in buckets:
            bucket_events = self.watch_bucket(bucket["Name"])
            events.extend(bucket_events)

        return events

    def watch_bucket(self, bucket_name: str) -> List[S3Event]:
        """
        Watch specific S3 bucket.

        Args:
            bucket_name: S3 bucket name

        Returns:
            List of S3Event objects
        """
        events = []

        if self.dry_run:
            return events

        # Get current bucket configuration
        current_bucket = self._get_bucket(bucket_name)
        if not current_bucket:
            return events

        # Check if bucket is tracked
        if bucket_name in self.tracked_buckets:
            previous_bucket = self.tracked_buckets[bucket_name]

            # Detect encryption changes
            if current_bucket.encryption_enabled != previous_bucket.encryption_enabled:
                if not current_bucket.encryption_enabled:
                    event = S3Event(
                        event_type=S3EventType.ENCRYPTION_DISABLED,
                        timestamp=datetime.now(),
                        bucket_name=bucket_name,
                        details={
                            "previous_algorithm": previous_bucket.encryption_algorithm
                        },
                        risk_level="High"
                    )
                    events.append(event)
                else:
                    event = S3Event(
                        event_type=S3EventType.ENCRYPTION_ENABLED,
                        timestamp=datetime.now(),
                        bucket_name=bucket_name,
                        details={
                            "algorithm": current_bucket.encryption_algorithm
                        },
                        risk_level="Low"
                    )
                    events.append(event)

            # Detect public access changes
            if current_bucket.public_access_block != previous_bucket.public_access_block:
                # Check if public access is now allowed
                if self._is_public_access_allowed(current_bucket.public_access_block):
                    event = S3Event(
                        event_type=S3EventType.PUBLIC_ACCESS_ENABLED,
                        timestamp=datetime.now(),
                        bucket_name=bucket_name,
                        details={
                            "public_access_block": current_bucket.public_access_block
                        },
                        risk_level="Critical"
                    )
                    events.append(event)
                else:
                    event = S3Event(
                        event_type=S3EventType.PUBLIC_ACCESS_DISABLED,
                        timestamp=datetime.now(),
                        bucket_name=bucket_name,
                        details={
                            "public_access_block": current_bucket.public_access_block
                        },
                        risk_level="Low"
                    )
                    events.append(event)

            # Detect versioning changes
            if current_bucket.versioning_enabled != previous_bucket.versioning_enabled:
                if not current_bucket.versioning_enabled:
                    event = S3Event(
                        event_type=S3EventType.VERSIONING_DISABLED,
                        timestamp=datetime.now(),
                        bucket_name=bucket_name,
                        details={},
                        risk_level="Medium"
                    )
                    events.append(event)

            # Detect logging changes
            if current_bucket.logging_enabled != previous_bucket.logging_enabled:
                if not current_bucket.logging_enabled:
                    event = S3Event(
                        event_type=S3EventType.LOGGING_DISABLED,
                        timestamp=datetime.now(),
                        bucket_name=bucket_name,
                        details={},
                        risk_level="Medium"
                    )
                    events.append(event)

            # Detect bucket policy changes
            if current_bucket.bucket_policy != previous_bucket.bucket_policy:
                event = S3Event(
                    event_type=S3EventType.POLICY_MODIFIED,
                    timestamp=datetime.now(),
                    bucket_name=bucket_name,
                    details={
                        "has_policy": current_bucket.bucket_policy is not None
                    },
                    risk_level=self._assess_policy_risk(current_bucket.bucket_policy)
                )
                events.append(event)

        else:
            # New bucket detected
            event = S3Event(
                event_type=S3EventType.BUCKET_CREATED,
                timestamp=datetime.now(),
                bucket_name=bucket_name,
                details={
                    "encryption_enabled": current_bucket.encryption_enabled,
                    "versioning_enabled": current_bucket.versioning_enabled,
                    "logging_enabled": current_bucket.logging_enabled
                },
                risk_level="Medium"
            )
            events.append(event)

        # Update tracked bucket
        self.tracked_buckets[bucket_name] = current_bucket

        return events

    def get_public_buckets(self) -> List[S3Bucket]:
        """
        Get buckets with public access enabled.

        Returns:
            List of S3Bucket objects
        """
        public_buckets = []

        if self.dry_run:
            return public_buckets

        for bucket_name, bucket in self.tracked_buckets.items():
            if self._is_public_access_allowed(bucket.public_access_block):
                public_buckets.append(bucket)

        return public_buckets

    def get_unencrypted_buckets(self) -> List[S3Bucket]:
        """
        Get buckets without encryption.

        Returns:
            List of S3Bucket objects
        """
        unencrypted_buckets = []

        if self.dry_run:
            return unencrypted_buckets

        for bucket_name, bucket in self.tracked_buckets.items():
            if not bucket.encryption_enabled:
                unencrypted_buckets.append(bucket)

        return unencrypted_buckets

    def _list_buckets(self) -> List[Dict]:
        """List all S3 buckets."""
        try:
            cmd = ["aws", "s3api", "list-buckets", "--output", "json"]

            if self.profile:
                cmd.extend(["--profile", self.profile])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("Buckets", [])

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return []

    def _get_bucket(self, bucket_name: str) -> Optional[S3Bucket]:
        """Get S3 bucket details."""
        try:
            # Get bucket location
            region = self._get_bucket_location(bucket_name)

            # Get encryption configuration
            encryption_config = self._get_bucket_encryption(bucket_name)
            encryption_enabled = encryption_config is not None
            encryption_algorithm = None
            if encryption_config:
                rules = encryption_config.get("Rules", [])
                if rules:
                    encryption_algorithm = rules[0].get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm")

            # Get versioning
            versioning = self._get_bucket_versioning(bucket_name)
            versioning_enabled = versioning.get("Status") == "Enabled"

            # Get logging
            logging_config = self._get_bucket_logging(bucket_name)
            logging_enabled = logging_config is not None
            logging_target_bucket = None
            if logging_config:
                logging_target_bucket = logging_config.get("TargetBucket")

            # Get public access block
            public_access_block = self._get_public_access_block(bucket_name)

            # Get bucket policy
            bucket_policy = self._get_bucket_policy(bucket_name)

            # Get tags
            tags = self._get_bucket_tags(bucket_name)

            return S3Bucket(
                bucket_name=bucket_name,
                creation_date=datetime.now(),  # Placeholder
                region=region,
                encryption_enabled=encryption_enabled,
                encryption_algorithm=encryption_algorithm,
                versioning_enabled=versioning_enabled,
                logging_enabled=logging_enabled,
                logging_target_bucket=logging_target_bucket,
                public_access_block=public_access_block,
                bucket_policy=bucket_policy,
                tags=tags
            )

        except Exception:
            pass

        return None

    def _get_bucket_location(self, bucket_name: str) -> str:
        """Get bucket region."""
        try:
            cmd = ["aws", "s3api", "get-bucket-location", "--bucket", bucket_name, "--output", "json"]

            if self.profile:
                cmd.extend(["--profile", self.profile])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                location = data.get("LocationConstraint")
                return location if location else "us-east-1"

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return "unknown"

    def _get_bucket_encryption(self, bucket_name: str) -> Optional[Dict]:
        """Get bucket encryption configuration."""
        try:
            cmd = ["aws", "s3api", "get-bucket-encryption", "--bucket", bucket_name, "--output", "json"]

            if self.profile:
                cmd.extend(["--profile", self.profile])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("ServerSideEncryptionConfiguration")

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, subprocess.CalledProcessError):
            pass

        return None

    def _get_bucket_versioning(self, bucket_name: str) -> Dict:
        """Get bucket versioning status."""
        try:
            cmd = ["aws", "s3api", "get-bucket-versioning", "--bucket", bucket_name, "--output", "json"]

            if self.profile:
                cmd.extend(["--profile", self.profile])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return json.loads(result.stdout)

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return {}

    def _get_bucket_logging(self, bucket_name: str) -> Optional[Dict]:
        """Get bucket logging configuration."""
        try:
            cmd = ["aws", "s3api", "get-bucket-logging", "--bucket", bucket_name, "--output", "json"]

            if self.profile:
                cmd.extend(["--profile", self.profile])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("LoggingEnabled")

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return None

    def _get_public_access_block(self, bucket_name: str) -> Optional[Dict]:
        """Get public access block configuration."""
        try:
            cmd = ["aws", "s3api", "get-public-access-block", "--bucket", bucket_name, "--output", "json"]

            if self.profile:
                cmd.extend(["--profile", self.profile])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("PublicAccessBlockConfiguration")

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, subprocess.CalledProcessError):
            pass

        return None

    def _get_bucket_policy(self, bucket_name: str) -> Optional[Dict]:
        """Get bucket policy."""
        try:
            cmd = ["aws", "s3api", "get-bucket-policy", "--bucket", bucket_name, "--output", "json"]

            if self.profile:
                cmd.extend(["--profile", self.profile])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                policy_str = data.get("Policy", "{}")
                return json.loads(policy_str)

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, subprocess.CalledProcessError):
            pass

        return None

    def _get_bucket_tags(self, bucket_name: str) -> Dict[str, str]:
        """Get bucket tags."""
        try:
            cmd = ["aws", "s3api", "get-bucket-tagging", "--bucket", bucket_name, "--output", "json"]

            if self.profile:
                cmd.extend(["--profile", self.profile])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                tags = data.get("TagSet", [])
                return {tag["Key"]: tag["Value"] for tag in tags}

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, subprocess.CalledProcessError):
            pass

        return {}

    def _is_public_access_allowed(self, public_access_block: Optional[Dict]) -> bool:
        """Check if public access is allowed."""
        if not public_access_block:
            return True  # No block = public access allowed

        # If any block setting is False, public access is potentially allowed
        return not all([
            public_access_block.get("BlockPublicAcls", False),
            public_access_block.get("IgnorePublicAcls", False),
            public_access_block.get("BlockPublicPolicy", False),
            public_access_block.get("RestrictPublicBuckets", False)
        ])

    def _assess_policy_risk(self, policy: Optional[Dict]) -> str:
        """Assess risk level of bucket policy."""
        if not policy:
            return "Low"

        statements = policy.get("Statement", [])

        for statement in statements:
            if statement.get("Effect") == "Allow":
                principal = statement.get("Principal", {})

                # Check for public principal
                if principal == "*" or principal.get("AWS") == "*":
                    return "Critical"

        return "Medium"


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Watch AWS S3 for changes")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--bucket", help="Specific bucket to watch")
    parser.add_argument("--check-public", action="store_true", help="Check for public buckets")
    parser.add_argument("--check-unencrypted", action="store_true", help="Check for unencrypted buckets")

    args = parser.parse_args()

    watcher = S3Watcher(region=args.region, profile=args.profile)

    print(f"🪣 S3 Watcher - Region: {args.region}\n")

    # Watch specific bucket
    if args.bucket:
        print(f"📊 Watching bucket: {args.bucket}\n")
        events = watcher.watch_bucket(args.bucket)
    else:
        print("📊 Watching all buckets...\n")
        events = watcher.watch_buckets()

    # Display events
    if events:
        print(f"🔔 Found {len(events)} S3 events:\n")
        for i, event in enumerate(events, 1):
            print(f"{i}. [{event.risk_level.upper()}] {event.event_type.value}")
            print(f"   Bucket: {event.bucket_name}")
            print(f"   Details: {event.details}")
            print()

    # Check public buckets
    if args.check_public:
        print("\n🔍 Checking for public buckets...\n")
        public_buckets = watcher.get_public_buckets()

        if public_buckets:
            print(f"⚠️  Found {len(public_buckets)} public buckets:\n")
            for bucket in public_buckets:
                print(f"- {bucket.bucket_name}")
                print(f"  Public Access Block: {bucket.public_access_block}")
                print()
        else:
            print("✅ No public buckets detected")

    # Check unencrypted buckets
    if args.check_unencrypted:
        print("\n🔍 Checking for unencrypted buckets...\n")
        unencrypted = watcher.get_unencrypted_buckets()

        if unencrypted:
            print(f"⚠️  Found {len(unencrypted)} unencrypted buckets:\n")
            for bucket in unencrypted:
                print(f"- {bucket.bucket_name}")
                print()
        else:
            print("✅ All buckets are encrypted")
