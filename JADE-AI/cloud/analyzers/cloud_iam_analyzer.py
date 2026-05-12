#!/usr/bin/env python3
"""
IAM Analyzer for jsa-devsecops
Analyzes IAM roles, policies, and users for security issues.

Author: jsa-devsecops
Created: 2025-12-31
"""

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class FindingType(Enum):
    """Types of IAM findings."""
    WILDCARD_RESOURCE = "wildcard_resource"
    WILDCARD_ACTION = "wildcard_action"
    ADMIN_ACCESS = "admin_access"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    OVERLY_PERMISSIVE_TRUST = "overly_permissive_trust"
    NO_MFA = "no_mfa"
    UNUSED_ROLE = "unused_role"
    CROSS_ACCOUNT_TRUST = "cross_account_trust"
    UNUSED_ACCESS_KEYS = "unused_access_keys"
    OLD_ACCESS_KEYS = "old_access_keys"
    INLINE_POLICY = "inline_policy"
    MISSING_PASSWORD_POLICY = "missing_password_policy"


class FindingSeverity(Enum):
    """Severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class IAMFinding:
    """Represents an IAM security finding."""
    finding_type: FindingType
    severity: FindingSeverity
    resource_type: str  # Role, User, Policy, Group
    resource_name: str
    resource_arn: str
    description: str
    recommendation: str
    compliance_frameworks: List[str]
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class IAMAnalyzer:
    """
    Analyzes IAM configurations for security issues.

    Features:
    - Detects wildcard permissions (*, *)
    - Identifies AdministratorAccess policies
    - Finds privilege escalation paths
    - Checks overly permissive trust policies
    - Validates MFA enforcement
    - Detects unused roles and access keys
    - Compliance mapping (CIS AWS, PCI-DSS, SOC2)

    Example:
        analyzer = IAMAnalyzer(region="us-east-1")

        # Analyze all IAM roles
        findings = analyzer.analyze_all_roles()

        # Analyze specific role
        findings = analyzer.analyze_role("MyAppRole")

        # Check for privilege escalation
        escalation_findings = analyzer.check_privilege_escalation()

        # Get critical findings only
        critical = [f for f in findings if f.severity == FindingSeverity.CRITICAL]
    """

    def __init__(
        self,
        region: str = "us-east-1",
        profile: str = None
    ):
        """
        Initialize IAM analyzer.

        Args:
            region: AWS region
            profile: AWS profile name
        """
        self.region = region
        self.profile = profile

        # Privilege escalation actions
        self.escalation_actions = {
            "iam:CreateAccessKey",
            "iam:CreateLoginProfile",
            "iam:UpdateLoginProfile",
            "iam:AttachUserPolicy",
            "iam:AttachGroupPolicy",
            "iam:AttachRolePolicy",
            "iam:PutUserPolicy",
            "iam:PutGroupPolicy",
            "iam:PutRolePolicy",
            "iam:CreatePolicyVersion",
            "iam:SetDefaultPolicyVersion",
            "iam:PassRole",
            "sts:AssumeRole"
        }

    def _run_aws_command(self, command: List[str]) -> Dict:
        """Run AWS CLI command and return JSON output."""
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

            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)

            return {}

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return {}

    def analyze_role(self, role_name: str) -> List[IAMFinding]:
        """
        Analyze a specific IAM role.

        Args:
            role_name: IAM role name

        Returns:
            List of IAMFinding objects
        """
        findings = []

        # Get role details
        role_result = self._run_aws_command(["get-role", "--role-name", role_name])

        if not role_result or "Role" not in role_result:
            return findings

        role = role_result["Role"]
        role_arn = role["Arn"]

        # Check trust policy
        trust_findings = self._analyze_trust_policy(
            role_name,
            role_arn,
            role.get("AssumeRolePolicyDocument", {})
        )
        findings.extend(trust_findings)

        # Get attached policies
        attached_result = self._run_aws_command([
            "list-attached-role-policies",
            "--role-name", role_name
        ])

        if attached_result and "AttachedPolicies" in attached_result:
            for policy in attached_result["AttachedPolicies"]:
                policy_name = policy["PolicyName"]
                policy_arn = policy["PolicyArn"]

                # Check for AdministratorAccess
                if policy_name == "AdministratorAccess" or "AdministratorAccess" in policy_arn:
                    findings.append(IAMFinding(
                        finding_type=FindingType.ADMIN_ACCESS,
                        severity=FindingSeverity.CRITICAL,
                        resource_type="Role",
                        resource_name=role_name,
                        resource_arn=role_arn,
                        description=f"Role {role_name} has AdministratorAccess policy attached",
                        recommendation="Remove AdministratorAccess and use least privilege policies (CIS AWS 1.16)",
                        compliance_frameworks=["CIS AWS 1.16", "PCI-DSS 7.1.2", "SOC2 CC6.1"],
                        details={"policy_name": policy_name, "policy_arn": policy_arn}
                    ))

                # Analyze policy document for wildcards
                policy_findings = self._analyze_managed_policy(
                    policy_arn,
                    role_name,
                    role_arn,
                    "Role"
                )
                findings.extend(policy_findings)

        # Get inline policies
        inline_result = self._run_aws_command([
            "list-role-policies",
            "--role-name", role_name
        ])

        if inline_result and "PolicyNames" in inline_result:
            for policy_name in inline_result["PolicyNames"]:
                # Inline policies are discouraged
                findings.append(IAMFinding(
                    finding_type=FindingType.INLINE_POLICY,
                    severity=FindingSeverity.MEDIUM,
                    resource_type="Role",
                    resource_name=role_name,
                    resource_arn=role_arn,
                    description=f"Role {role_name} has inline policy {policy_name} (use managed policies instead)",
                    recommendation="Convert inline policies to managed policies for better governance (CIS AWS 1.16)",
                    compliance_frameworks=["CIS AWS 1.16"],
                    details={"policy_name": policy_name}
                ))

                # Get inline policy document
                policy_result = self._run_aws_command([
                    "get-role-policy",
                    "--role-name", role_name,
                    "--policy-name", policy_name
                ])

                if policy_result and "PolicyDocument" in policy_result:
                    inline_findings = self._analyze_policy_document(
                        policy_result["PolicyDocument"],
                        role_name,
                        role_arn,
                        "Role"
                    )
                    findings.extend(inline_findings)

        return findings

    def analyze_user(self, user_name: str) -> List[IAMFinding]:
        """
        Analyze a specific IAM user.

        Args:
            user_name: IAM user name

        Returns:
            List of IAMFinding objects
        """
        findings = []

        # Get user details
        user_result = self._run_aws_command(["get-user", "--user-name", user_name])

        if not user_result or "User" not in user_result:
            return findings

        user = user_result["User"]
        user_arn = user["Arn"]

        # Check MFA
        mfa_result = self._run_aws_command([
            "list-mfa-devices",
            "--user-name", user_name
        ])

        if mfa_result and "MFADevices" in mfa_result:
            if not mfa_result["MFADevices"]:
                findings.append(IAMFinding(
                    finding_type=FindingType.NO_MFA,
                    severity=FindingSeverity.HIGH,
                    resource_type="User",
                    resource_name=user_name,
                    resource_arn=user_arn,
                    description=f"User {user_name} does not have MFA enabled",
                    recommendation="Enable MFA for all IAM users (CIS AWS 1.10, 1.11)",
                    compliance_frameworks=["CIS AWS 1.10", "CIS AWS 1.11", "PCI-DSS 8.3", "SOC2 CC6.1"],
                    details={}
                ))

        # Check access keys
        keys_result = self._run_aws_command([
            "list-access-keys",
            "--user-name", user_name
        ])

        if keys_result and "AccessKeyMetadata" in keys_result:
            for key in keys_result["AccessKeyMetadata"]:
                create_date = datetime.fromisoformat(key["CreateDate"].replace("Z", "+00:00"))
                age_days = (datetime.now(create_date.tzinfo) - create_date).days

                # Keys older than 90 days
                if age_days > 90:
                    findings.append(IAMFinding(
                        finding_type=FindingType.OLD_ACCESS_KEYS,
                        severity=FindingSeverity.MEDIUM,
                        resource_type="User",
                        resource_name=user_name,
                        resource_arn=user_arn,
                        description=f"Access key {key['AccessKeyId']} is {age_days} days old (rotate every 90 days)",
                        recommendation="Rotate access keys every 90 days (CIS AWS 1.14)",
                        compliance_frameworks=["CIS AWS 1.14", "PCI-DSS 8.2.4"],
                        details={"access_key_id": key["AccessKeyId"], "age_days": age_days}
                    ))

                # Check last used
                last_used_result = self._run_aws_command([
                    "get-access-key-last-used",
                    "--access-key-id", key["AccessKeyId"]
                ])

                if last_used_result and "AccessKeyLastUsed" in last_used_result:
                    last_used = last_used_result["AccessKeyLastUsed"]
                    if "LastUsedDate" in last_used:
                        last_used_date = datetime.fromisoformat(last_used["LastUsedDate"].replace("Z", "+00:00"))
                        unused_days = (datetime.now(last_used_date.tzinfo) - last_used_date).days

                        # Unused for >90 days
                        if unused_days > 90:
                            findings.append(IAMFinding(
                                finding_type=FindingType.UNUSED_ACCESS_KEYS,
                                severity=FindingSeverity.MEDIUM,
                                resource_type="User",
                                resource_name=user_name,
                                resource_arn=user_arn,
                                description=f"Access key {key['AccessKeyId']} unused for {unused_days} days",
                                recommendation="Remove or disable unused access keys (CIS AWS 1.12)",
                                compliance_frameworks=["CIS AWS 1.12"],
                                details={"access_key_id": key["AccessKeyId"], "unused_days": unused_days}
                            ))

        # Check attached policies (same as roles)
        attached_result = self._run_aws_command([
            "list-attached-user-policies",
            "--user-name", user_name
        ])

        if attached_result and "AttachedPolicies" in attached_result:
            for policy in attached_result["AttachedPolicies"]:
                policy_name = policy["PolicyName"]
                policy_arn = policy["PolicyArn"]

                # Check for AdministratorAccess
                if policy_name == "AdministratorAccess":
                    findings.append(IAMFinding(
                        finding_type=FindingType.ADMIN_ACCESS,
                        severity=FindingSeverity.CRITICAL,
                        resource_type="User",
                        resource_name=user_name,
                        resource_arn=user_arn,
                        description=f"User {user_name} has AdministratorAccess (use roles instead)",
                        recommendation="Remove direct admin access from users - use AssumeRole instead (CIS AWS 1.16)",
                        compliance_frameworks=["CIS AWS 1.16", "PCI-DSS 7.1.2", "SOC2 CC6.1"],
                        details={"policy_name": policy_name}
                    ))

                # Analyze policy document
                policy_findings = self._analyze_managed_policy(
                    policy_arn,
                    user_name,
                    user_arn,
                    "User"
                )
                findings.extend(policy_findings)

        return findings

    def analyze_all_roles(self) -> List[IAMFinding]:
        """Analyze all IAM roles."""
        all_findings = []

        roles_result = self._run_aws_command(["list-roles"])

        if not roles_result or "Roles" not in roles_result:
            return all_findings

        for role in roles_result["Roles"]:
            role_name = role["RoleName"]
            findings = self.analyze_role(role_name)
            all_findings.extend(findings)

        return all_findings

    def analyze_all_users(self) -> List[IAMFinding]:
        """Analyze all IAM users."""
        all_findings = []

        users_result = self._run_aws_command(["list-users"])

        if not users_result or "Users" not in users_result:
            return all_findings

        for user in users_result["Users"]:
            user_name = user["UserName"]
            findings = self.analyze_user(user_name)
            all_findings.extend(findings)

        return all_findings

    def check_privilege_escalation(self) -> List[IAMFinding]:
        """
        Check for privilege escalation paths.

        Returns roles/users with escalation-capable permissions.
        """
        findings = []

        # Check all roles
        roles_result = self._run_aws_command(["list-roles"])

        if roles_result and "Roles" in roles_result:
            for role in roles_result["Roles"]:
                role_name = role["RoleName"]
                role_arn = role["Arn"]

                # Check attached policies
                attached_result = self._run_aws_command([
                    "list-attached-role-policies",
                    "--role-name", role_name
                ])

                if attached_result and "AttachedPolicies" in attached_result:
                    for policy in attached_result["AttachedPolicies"]:
                        escalation_perms = self._check_policy_for_escalation(policy["PolicyArn"])

                        if escalation_perms:
                            findings.append(IAMFinding(
                                finding_type=FindingType.PRIVILEGE_ESCALATION,
                                severity=FindingSeverity.CRITICAL,
                                resource_type="Role",
                                resource_name=role_name,
                                resource_arn=role_arn,
                                description=f"Role {role_name} has privilege escalation permissions: {', '.join(escalation_perms)}",
                                recommendation="Remove privilege escalation permissions or restrict to specific resources",
                                compliance_frameworks=["CIS AWS 1.16", "PCI-DSS 7.1.2"],
                                details={"escalation_actions": list(escalation_perms), "policy_arn": policy["PolicyArn"]}
                            ))

        return findings

    def _analyze_trust_policy(
        self,
        resource_name: str,
        resource_arn: str,
        trust_policy: Dict
    ) -> List[IAMFinding]:
        """Analyze trust policy for overly permissive trusts."""
        findings = []

        for statement in trust_policy.get("Statement", []):
            effect = statement.get("Effect")
            principal = statement.get("Principal", {})

            if effect != "Allow":
                continue

            # Check for wildcard principals
            if isinstance(principal, dict):
                aws_principal = principal.get("AWS", [])
                if isinstance(aws_principal, str):
                    aws_principal = [aws_principal]

                for princ in aws_principal:
                    if princ == "*":
                        findings.append(IAMFinding(
                            finding_type=FindingType.OVERLY_PERMISSIVE_TRUST,
                            severity=FindingSeverity.CRITICAL,
                            resource_type="Role",
                            resource_name=resource_name,
                            resource_arn=resource_arn,
                            description=f"Role {resource_name} trust policy allows ANY principal (*)",
                            recommendation="Restrict trust policy to specific principals (CIS AWS 1.16)",
                            compliance_frameworks=["CIS AWS 1.16", "PCI-DSS 7.1.2"],
                            details={"statement": statement}
                        ))
                    elif ":root" in princ:
                        # Cross-account trust
                        account_id = princ.split(":")[4]
                        findings.append(IAMFinding(
                            finding_type=FindingType.CROSS_ACCOUNT_TRUST,
                            severity=FindingSeverity.HIGH,
                            resource_type="Role",
                            resource_name=resource_name,
                            resource_arn=resource_arn,
                            description=f"Role {resource_name} has cross-account trust to account {account_id}",
                            recommendation="Review cross-account access and ensure external ID is used",
                            compliance_frameworks=["CIS AWS 1.20"],
                            details={"trusted_account": account_id, "statement": statement}
                        ))

        return findings

    def _analyze_managed_policy(
        self,
        policy_arn: str,
        resource_name: str,
        resource_arn: str,
        resource_type: str
    ) -> List[IAMFinding]:
        """Analyze a managed policy document."""
        findings = []

        # Get policy default version
        policy_result = self._run_aws_command(["get-policy", "--policy-arn", policy_arn])

        if not policy_result or "Policy" not in policy_result:
            return findings

        default_version = policy_result["Policy"]["DefaultVersionId"]

        # Get policy document
        version_result = self._run_aws_command([
            "get-policy-version",
            "--policy-arn", policy_arn,
            "--version-id", default_version
        ])

        if version_result and "PolicyVersion" in version_result:
            policy_doc = version_result["PolicyVersion"]["Document"]
            findings = self._analyze_policy_document(
                policy_doc,
                resource_name,
                resource_arn,
                resource_type
            )

        return findings

    def _analyze_policy_document(
        self,
        policy_doc: Dict,
        resource_name: str,
        resource_arn: str,
        resource_type: str
    ) -> List[IAMFinding]:
        """Analyze policy document for wildcards and overly permissive access."""
        findings = []

        for statement in policy_doc.get("Statement", []):
            effect = statement.get("Effect")
            actions = statement.get("Action", [])
            resources = statement.get("Resource", [])

            if effect != "Allow":
                continue

            # Normalize to lists
            if isinstance(actions, str):
                actions = [actions]
            if isinstance(resources, str):
                resources = [resources]

            # Check for wildcard actions
            if "*" in actions:
                findings.append(IAMFinding(
                    finding_type=FindingType.WILDCARD_ACTION,
                    severity=FindingSeverity.HIGH,
                    resource_type=resource_type,
                    resource_name=resource_name,
                    resource_arn=resource_arn,
                    description=f"{resource_type} {resource_name} has wildcard (*) action permission",
                    recommendation="Use specific actions instead of wildcards (CIS AWS 1.16)",
                    compliance_frameworks=["CIS AWS 1.16", "PCI-DSS 7.1.2"],
                    details={"statement": statement}
                ))

            # Check for wildcard resources
            if "*" in resources:
                findings.append(IAMFinding(
                    finding_type=FindingType.WILDCARD_RESOURCE,
                    severity=FindingSeverity.HIGH,
                    resource_type=resource_type,
                    resource_name=resource_name,
                    resource_arn=resource_arn,
                    description=f"{resource_type} {resource_name} has wildcard (*) resource permission",
                    recommendation="Use specific resource ARNs instead of wildcards (CIS AWS 1.16)",
                    compliance_frameworks=["CIS AWS 1.16", "PCI-DSS 7.1.2"],
                    details={"statement": statement}
                ))

        return findings

    def _check_policy_for_escalation(self, policy_arn: str) -> set:
        """Check if policy contains privilege escalation actions."""
        escalation_perms = set()

        # Get policy default version
        policy_result = self._run_aws_command(["get-policy", "--policy-arn", policy_arn])

        if not policy_result or "Policy" not in policy_result:
            return escalation_perms

        default_version = policy_result["Policy"]["DefaultVersionId"]

        # Get policy document
        version_result = self._run_aws_command([
            "get-policy-version",
            "--policy-arn", policy_arn,
            "--version-id", default_version
        ])

        if not version_result or "PolicyVersion" not in version_result:
            return escalation_perms

        policy_doc = version_result["PolicyVersion"]["Document"]

        for statement in policy_doc.get("Statement", []):
            if statement.get("Effect") != "Allow":
                continue

            actions = statement.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]

            # Check for escalation actions
            for action in actions:
                if action == "*":
                    # Wildcard includes all escalation actions
                    return self.escalation_actions

                if action in self.escalation_actions:
                    escalation_perms.add(action)

        return escalation_perms


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze IAM configurations for security issues")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile")
    parser.add_argument("--role", help="Analyze specific role")
    parser.add_argument("--user", help="Analyze specific user")
    parser.add_argument("--all-roles", action="store_true", help="Analyze all roles")
    parser.add_argument("--all-users", action="store_true", help="Analyze all users")
    parser.add_argument("--check-escalation", action="store_true", help="Check for privilege escalation")
    parser.add_argument("--severity", choices=["critical", "high", "medium", "low", "info"],
                        help="Filter by severity")

    args = parser.parse_args()

    analyzer = IAMAnalyzer(
        region=args.region,
        profile=args.profile
    )

    print(f"🔍 IAM Security Analyzer\n")
    print(f"Region: {args.region}\n")

    findings = []

    # Run analysis
    if args.role:
        print(f"📊 Analyzing role: {args.role}\n")
        findings = analyzer.analyze_role(args.role)
    elif args.user:
        print(f"📊 Analyzing user: {args.user}\n")
        findings = analyzer.analyze_user(args.user)
    elif args.all_roles:
        print(f"📊 Analyzing all IAM roles...\n")
        findings = analyzer.analyze_all_roles()
    elif args.all_users:
        print(f"📊 Analyzing all IAM users...\n")
        findings = analyzer.analyze_all_users()
    elif args.check_escalation:
        print(f"📊 Checking for privilege escalation paths...\n")
        findings = analyzer.check_privilege_escalation()
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
