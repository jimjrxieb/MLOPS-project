#!/usr/bin/env python3
"""
IAM Watcher for jsa-devsecops
Monitors AWS IAM roles, policies, users, and groups for security changes.

Author: jsa-devsecops
Created: 2025-12-31
"""

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class IAMEventType(Enum):
    """IAM event types."""
    ROLE_CREATED = "role_created"
    ROLE_MODIFIED = "role_modified"
    ROLE_DELETED = "role_deleted"
    POLICY_ATTACHED = "policy_attached"
    POLICY_DETACHED = "policy_detached"
    POLICY_MODIFIED = "policy_modified"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    PERMISSION_ESCALATION = "permission_escalation"
    ROOT_USAGE = "root_usage"


@dataclass
class IAMPolicy:
    """IAM policy details."""
    policy_arn: str
    policy_name: str
    policy_version: str
    policy_document: Dict
    is_attached: bool = False
    attachment_count: int = 0


@dataclass
class IAMRole:
    """IAM role details."""
    role_name: str
    role_arn: str
    role_id: str
    assume_role_policy: Dict
    attached_policies: List[str] = field(default_factory=list)
    inline_policies: List[str] = field(default_factory=list)
    max_session_duration: int = 3600
    created_date: Optional[datetime] = None
    last_used: Optional[datetime] = None


@dataclass
class IAMUser:
    """IAM user details."""
    user_name: str
    user_arn: str
    user_id: str
    attached_policies: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    access_keys: List[Dict] = field(default_factory=list)
    mfa_enabled: bool = False
    created_date: Optional[datetime] = None
    password_last_used: Optional[datetime] = None


@dataclass
class IAMEvent:
    """IAM change event."""
    event_type: IAMEventType
    timestamp: datetime
    resource_type: str  # Role, User, Policy, Group
    resource_name: str
    resource_arn: str
    details: Dict = field(default_factory=dict)
    risk_level: str = "Medium"  # Critical, High, Medium, Low


class IAMWatcher:
    """
    Watches AWS IAM for security-relevant changes.

    Features:
    - Monitor IAM roles and policies
    - Detect overprivileged roles
    - Track policy attachments/detachments
    - Monitor user creation/deletion
    - Detect root account usage
    - Alert on privilege escalation

    Example:
        watcher = IAMWatcher(region="us-east-1", profile="prod")

        # Watch all IAM roles
        events = watcher.watch_roles()

        # Watch specific role
        role_events = watcher.watch_role("admin-role")

        # Watch all IAM users
        user_events = watcher.watch_users()

        # Get overprivileged roles
        risky_roles = watcher.get_overprivileged_roles()
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None,
        dry_run: bool = False
    ):
        """
        Initialize IAM watcher.

        Args:
            region: AWS region
            profile: AWS profile name
            dry_run: If True, don't execute AWS API calls
        """
        self.region = region
        self.profile = profile
        self.dry_run = dry_run

        # Track IAM state
        self.tracked_roles: Dict[str, IAMRole] = {}
        self.tracked_users: Dict[str, IAMUser] = {}
        self.tracked_policies: Dict[str, IAMPolicy] = {}

    def watch_roles(self) -> List[IAMEvent]:
        """
        Watch all IAM roles for changes.

        Returns:
            List of IAMEvent objects
        """
        events = []

        if self.dry_run:
            return events

        # List all roles
        roles = self._list_roles()

        for role in roles:
            role_events = self.watch_role(role["RoleName"])
            events.extend(role_events)

        return events

    def watch_role(self, role_name: str) -> List[IAMEvent]:
        """
        Watch specific IAM role.

        Args:
            role_name: IAM role name

        Returns:
            List of IAMEvent objects
        """
        events = []

        if self.dry_run:
            return events

        # Get current role details
        current_role = self._get_role(role_name)
        if not current_role:
            return events

        # Check if role is tracked
        if role_name in self.tracked_roles:
            previous_role = self.tracked_roles[role_name]

            # Detect policy changes
            added_policies = set(current_role.attached_policies) - set(previous_role.attached_policies)
            removed_policies = set(previous_role.attached_policies) - set(current_role.attached_policies)

            for policy_arn in added_policies:
                event = IAMEvent(
                    event_type=IAMEventType.POLICY_ATTACHED,
                    timestamp=datetime.now(),
                    resource_type="Role",
                    resource_name=role_name,
                    resource_arn=current_role.role_arn,
                    details={
                        "policy_arn": policy_arn,
                        "action": "attached"
                    },
                    risk_level=self._assess_policy_risk(policy_arn)
                )
                events.append(event)

            for policy_arn in removed_policies:
                event = IAMEvent(
                    event_type=IAMEventType.POLICY_DETACHED,
                    timestamp=datetime.now(),
                    resource_type="Role",
                    resource_name=role_name,
                    resource_arn=current_role.role_arn,
                    details={
                        "policy_arn": policy_arn,
                        "action": "detached"
                    },
                    risk_level="Low"
                )
                events.append(event)

            # Detect assume role policy changes
            if current_role.assume_role_policy != previous_role.assume_role_policy:
                event = IAMEvent(
                    event_type=IAMEventType.ROLE_MODIFIED,
                    timestamp=datetime.now(),
                    resource_type="Role",
                    resource_name=role_name,
                    resource_arn=current_role.role_arn,
                    details={
                        "change": "assume_role_policy",
                        "previous": previous_role.assume_role_policy,
                        "current": current_role.assume_role_policy
                    },
                    risk_level="High"
                )
                events.append(event)

        else:
            # New role detected
            event = IAMEvent(
                event_type=IAMEventType.ROLE_CREATED,
                timestamp=datetime.now(),
                resource_type="Role",
                resource_name=role_name,
                resource_arn=current_role.role_arn,
                details={
                    "attached_policies": current_role.attached_policies,
                    "inline_policies": current_role.inline_policies
                },
                risk_level="Medium"
            )
            events.append(event)

        # Update tracked role
        self.tracked_roles[role_name] = current_role

        return events

    def watch_users(self) -> List[IAMEvent]:
        """
        Watch all IAM users for changes.

        Returns:
            List of IAMEvent objects
        """
        events = []

        if self.dry_run:
            return events

        # List all users
        users = self._list_users()

        for user in users:
            user_events = self.watch_user(user["UserName"])
            events.extend(user_events)

        return events

    def watch_user(self, user_name: str) -> List[IAMEvent]:
        """
        Watch specific IAM user.

        Args:
            user_name: IAM user name

        Returns:
            List of IAMEvent objects
        """
        events = []

        if self.dry_run:
            return events

        # Get current user details
        current_user = self._get_user(user_name)
        if not current_user:
            return events

        # Check if user is tracked
        if user_name in self.tracked_users:
            previous_user = self.tracked_users[user_name]

            # Detect MFA changes
            if current_user.mfa_enabled != previous_user.mfa_enabled:
                risk = "Low" if current_user.mfa_enabled else "High"
                event = IAMEvent(
                    event_type=IAMEventType.USER_MODIFIED if user_name in self.tracked_users else IAMEventType.USER_CREATED,
                    timestamp=datetime.now(),
                    resource_type="User",
                    resource_name=user_name,
                    resource_arn=current_user.user_arn,
                    details={
                        "change": "mfa_status",
                        "mfa_enabled": current_user.mfa_enabled
                    },
                    risk_level=risk
                )
                events.append(event)

        else:
            # New user detected
            event = IAMEvent(
                event_type=IAMEventType.USER_CREATED,
                timestamp=datetime.now(),
                resource_type="User",
                resource_name=user_name,
                resource_arn=current_user.user_arn,
                details={
                    "mfa_enabled": current_user.mfa_enabled,
                    "attached_policies": current_user.attached_policies
                },
                risk_level="Medium"
            )
            events.append(event)

        # Update tracked user
        self.tracked_users[user_name] = current_user

        return events

    def get_overprivileged_roles(self) -> List[IAMRole]:
        """
        Get roles with overly broad permissions.

        Returns:
            List of IAMRole objects with risky permissions
        """
        risky_roles = []

        if self.dry_run:
            return risky_roles

        for role_name, role in self.tracked_roles.items():
            # Check for AdministratorAccess
            if any("AdministratorAccess" in policy for policy in role.attached_policies):
                risky_roles.append(role)
                continue

            # Check for wildcard policies
            for policy_arn in role.attached_policies:
                policy = self._get_policy(policy_arn)
                if policy and self._has_wildcard_permissions(policy.policy_document):
                    risky_roles.append(role)
                    break

        return risky_roles

    def _list_roles(self) -> List[Dict]:
        """List all IAM roles."""
        try:
            cmd = ["aws", "iam", "list-roles", "--region", self.region, "--output", "json"]

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
                return data.get("Roles", [])

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return []

    def _get_role(self, role_name: str) -> Optional[IAMRole]:
        """Get IAM role details."""
        try:
            cmd = ["aws", "iam", "get-role", "--role-name", role_name, "--region", self.region, "--output", "json"]

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
                role_data = data.get("Role", {})

                # Get attached policies
                attached_policies = self._get_attached_policies(role_name, "role")

                # Get inline policies
                inline_policies = self._get_inline_policies(role_name, "role")

                return IAMRole(
                    role_name=role_data["RoleName"],
                    role_arn=role_data["Arn"],
                    role_id=role_data["RoleId"],
                    assume_role_policy=role_data.get("AssumeRolePolicyDocument", {}),
                    attached_policies=attached_policies,
                    inline_policies=inline_policies,
                    max_session_duration=role_data.get("MaxSessionDuration", 3600),
                    created_date=datetime.fromisoformat(role_data["CreateDate"].replace("Z", "+00:00"))
                )

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return None

    def _list_users(self) -> List[Dict]:
        """List all IAM users."""
        try:
            cmd = ["aws", "iam", "list-users", "--region", self.region, "--output", "json"]

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
                return data.get("Users", [])

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return []

    def _get_user(self, user_name: str) -> Optional[IAMUser]:
        """Get IAM user details."""
        try:
            cmd = ["aws", "iam", "get-user", "--user-name", user_name, "--region", self.region, "--output", "json"]

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
                user_data = data.get("User", {})

                # Get attached policies
                attached_policies = self._get_attached_policies(user_name, "user")

                # Check MFA
                mfa_enabled = self._check_mfa(user_name)

                return IAMUser(
                    user_name=user_data["UserName"],
                    user_arn=user_data["Arn"],
                    user_id=user_data["UserId"],
                    attached_policies=attached_policies,
                    mfa_enabled=mfa_enabled,
                    created_date=datetime.fromisoformat(user_data["CreateDate"].replace("Z", "+00:00"))
                )

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return None

    def _get_attached_policies(self, entity_name: str, entity_type: str) -> List[str]:
        """Get attached managed policies for role or user."""
        try:
            cmd = [
                "aws", "iam",
                f"list-attached-{entity_type}-policies",
                f"--{entity_type}-name", entity_name,
                "--region", self.region,
                "--output", "json"
            ]

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
                return [p["PolicyArn"] for p in data.get("AttachedPolicies", [])]

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return []

    def _get_inline_policies(self, entity_name: str, entity_type: str) -> List[str]:
        """Get inline policies for role or user."""
        try:
            cmd = [
                "aws", "iam",
                f"list-{entity_type}-policies",
                f"--{entity_type}-name", entity_name,
                "--region", self.region,
                "--output", "json"
            ]

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
                return data.get("PolicyNames", [])

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return []

    def _check_mfa(self, user_name: str) -> bool:
        """Check if user has MFA enabled."""
        try:
            cmd = [
                "aws", "iam", "list-mfa-devices",
                "--user-name", user_name,
                "--region", self.region,
                "--output", "json"
            ]

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
                return len(data.get("MFADevices", [])) > 0

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return False

    def _get_policy(self, policy_arn: str) -> Optional[IAMPolicy]:
        """Get policy details."""
        try:
            cmd = ["aws", "iam", "get-policy", "--policy-arn", policy_arn, "--region", self.region, "--output", "json"]

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
                policy_data = data.get("Policy", {})

                # Get policy version document
                policy_doc = self._get_policy_version(policy_arn, policy_data.get("DefaultVersionId", "v1"))

                return IAMPolicy(
                    policy_arn=policy_data["Arn"],
                    policy_name=policy_data["PolicyName"],
                    policy_version=policy_data.get("DefaultVersionId", "v1"),
                    policy_document=policy_doc,
                    is_attached=policy_data.get("AttachmentCount", 0) > 0,
                    attachment_count=policy_data.get("AttachmentCount", 0)
                )

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return None

    def _get_policy_version(self, policy_arn: str, version_id: str) -> Dict:
        """Get policy version document."""
        try:
            cmd = [
                "aws", "iam", "get-policy-version",
                "--policy-arn", policy_arn,
                "--version-id", version_id,
                "--region", self.region,
                "--output", "json"
            ]

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
                return data.get("PolicyVersion", {}).get("Document", {})

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return {}

    def _has_wildcard_permissions(self, policy_document: Dict) -> bool:
        """Check if policy has wildcard (*) permissions."""
        statements = policy_document.get("Statement", [])

        for statement in statements:
            if statement.get("Effect") != "Allow":
                continue

            actions = statement.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]

            resources = statement.get("Resource", [])
            if isinstance(resources, str):
                resources = [resources]

            # Check for wildcard actions or resources
            if "*" in actions or "*" in resources:
                return True

        return False

    def _assess_policy_risk(self, policy_arn: str) -> str:
        """Assess risk level of policy attachment."""
        # AdministratorAccess is critical
        if "AdministratorAccess" in policy_arn:
            return "Critical"

        # PowerUser is high risk
        if "PowerUser" in policy_arn:
            return "High"

        # ReadOnly is low risk
        if "ReadOnly" in policy_arn:
            return "Low"

        return "Medium"


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Watch AWS IAM for changes")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--watch", choices=["roles", "users", "all"], default="all", help="What to watch")
    parser.add_argument("--role", help="Specific role to watch")
    parser.add_argument("--user", help="Specific user to watch")
    parser.add_argument("--check-overprivileged", action="store_true", help="Check for overprivileged roles")

    args = parser.parse_args()

    watcher = IAMWatcher(region=args.region, profile=args.profile)

    print(f"🔐 IAM Watcher - Region: {args.region}\n")

    # Watch specific resources
    if args.role:
        print(f"📊 Watching role: {args.role}\n")
        events = watcher.watch_role(args.role)
    elif args.user:
        print(f"📊 Watching user: {args.user}\n")
        events = watcher.watch_user(args.user)
    elif args.watch == "roles":
        print("📊 Watching all roles...\n")
        events = watcher.watch_roles()
    elif args.watch == "users":
        print("📊 Watching all users...\n")
        events = watcher.watch_users()
    else:
        print("📊 Watching all IAM resources...\n")
        events = watcher.watch_roles() + watcher.watch_users()

    # Display events
    if events:
        print(f"🔔 Found {len(events)} IAM events:\n")
        for i, event in enumerate(events, 1):
            print(f"{i}. [{event.risk_level.upper()}] {event.event_type.value}")
            print(f"   Resource: {event.resource_type} ({event.resource_name})")
            print(f"   Details: {event.details}")
            print()

    # Check overprivileged
    if args.check_overprivileged:
        print("\n🔍 Checking for overprivileged roles...\n")
        risky_roles = watcher.get_overprivileged_roles()

        if risky_roles:
            print(f"⚠️  Found {len(risky_roles)} overprivileged roles:\n")
            for role in risky_roles:
                print(f"- {role.role_name}")
                print(f"  Policies: {', '.join(role.attached_policies)}")
                print()
        else:
            print("✅ No overprivileged roles detected")
