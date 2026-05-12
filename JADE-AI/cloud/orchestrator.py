"""
JADE Cloud Security Orchestrator
=================================
Central orchestration point for all cloud security operations.

JADE uses this to:
1. WATCH cloud resources (E-rank, automatic)
2. ANALYZE findings (D-rank, automatic)
3. PROPOSE fixes (C-rank, JADE decides)
4. REQUEST approval (B-rank, human required)
5. EXECUTE fixes (only after human approval)

This enforces the authority model where cloud changes
ALWAYS require human approval.

Author: GP-Copilot
Created: 2026-02-08
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger("jade.cloud.orchestrator")


class CloudAction(Enum):
    """Cloud action types with authority levels."""
    WATCH = "watch"      # E-rank: Read-only monitoring
    ANALYZE = "analyze"  # D-rank: Classify findings
    ALERT = "alert"      # C-rank: Send notification
    PROPOSE = "propose"  # C-rank: Generate fix proposal
    FIX = "fix"          # B-rank: Execute remediation (requires approval)


class CloudProvider(Enum):
    """Supported cloud providers."""
    AWS = "aws"
    # GCP = "gcp"    # Future
    # AZURE = "azure"  # Future


@dataclass
class CloudFinding:
    """A cloud security finding."""
    id: str
    provider: CloudProvider
    service: str  # iam, s3, ec2, vpc
    severity: str
    title: str
    description: str
    resource_arn: str
    region: str
    account_id: str
    recommendation: str
    auto_fixable: bool = False
    fix_proposal: Optional[str] = None
    requires_approval: bool = True  # Always true for cloud
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "provider": self.provider.value,
            "service": self.service,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "resource_arn": self.resource_arn,
            "region": self.region,
            "account_id": self.account_id,
            "recommendation": self.recommendation,
            "auto_fixable": self.auto_fixable,
            "fix_proposal": self.fix_proposal,
            "requires_approval": self.requires_approval,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class FixProposal:
    """A proposed fix awaiting human approval."""
    id: str
    finding_id: str
    provider: CloudProvider
    service: str
    action_type: str  # terraform_pr, cli_command, console_steps
    description: str
    terraform_code: Optional[str] = None
    cli_commands: Optional[List[str]] = None
    console_steps: Optional[List[str]] = None
    risk_level: str = "MEDIUM"
    requires_approval: bool = True
    approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "finding_id": self.finding_id,
            "provider": self.provider.value,
            "service": self.service,
            "action_type": self.action_type,
            "description": self.description,
            "terraform_code": self.terraform_code,
            "cli_commands": self.cli_commands,
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
            "approved": self.approved,
            "approved_by": self.approved_by,
            "created_at": self.created_at.isoformat(),
        }


class CloudOrchestrator:
    """
    JADE's cloud security orchestrator.

    Manages the full lifecycle of cloud security:
    1. Watch - Continuous monitoring for issues
    2. Analyze - Classify and prioritize findings
    3. Propose - Generate fix proposals
    4. Alert - Notify humans of issues
    5. Execute - Apply fixes (only after approval)
    """

    def __init__(self):
        self.logger = logging.getLogger("jade.cloud.orchestrator")
        self.findings: List[CloudFinding] = []
        self.proposals: List[FixProposal] = []
        self._watchers = {}
        self._analyzers = {}
        self._fixers = {}

    def _load_watchers(self):
        """Lazy-load cloud watchers."""
        if self._watchers:
            return

        try:
            from .watchers.cloud_iam_watcher import IAMWatcher
            from .watchers.cloud_s3_watcher import S3Watcher
            from .watchers.cloud_ec2_watcher import EC2Watcher
            from .watchers.cloud_vpc_watcher import VPCWatcher

            self._watchers = {
                "iam": IAMWatcher(),
                "s3": S3Watcher(),
                "ec2": EC2Watcher(),
                "vpc": VPCWatcher(),
            }
            self.logger.info(f"Loaded {len(self._watchers)} cloud watchers")
        except ImportError as e:
            self.logger.warning(f"Could not load cloud watchers: {e}")

    def watch(
        self,
        services: Optional[List[str]] = None,
        regions: Optional[List[str]] = None
    ) -> List[CloudFinding]:
        """
        Watch cloud resources for security issues.

        This is E-rank (automatic) - read-only monitoring.

        Args:
            services: Specific services to watch (None = all)
            regions: AWS regions to scan (None = default region)

        Returns:
            List of CloudFinding objects
        """
        self._load_watchers()
        self.findings = []

        services = services or list(self._watchers.keys())

        self.logger.info(f"Watching cloud services: {services}")

        for service in services:
            if service not in self._watchers:
                continue

            try:
                watcher = self._watchers[service]
                # Each watcher returns findings
                service_findings = watcher.watch(regions=regions)

                for f in service_findings:
                    self.findings.append(CloudFinding(
                        id=f.get("id", f"{service}-{datetime.now().timestamp()}"),
                        provider=CloudProvider.AWS,
                        service=service,
                        severity=f.get("severity", "MEDIUM"),
                        title=f.get("title", "Unknown"),
                        description=f.get("description", ""),
                        resource_arn=f.get("resource_arn", ""),
                        region=f.get("region", "us-east-1"),
                        account_id=f.get("account_id", ""),
                        recommendation=f.get("recommendation", ""),
                        auto_fixable=f.get("auto_fixable", False),
                    ))

            except Exception as e:
                self.logger.error(f"Watcher {service} failed: {e}")

        self.logger.info(f"Found {len(self.findings)} cloud findings")
        return self.findings

    def propose_fix(self, finding: CloudFinding) -> Optional[FixProposal]:
        """
        Generate a fix proposal for a finding.

        This is C-rank - JADE decides whether to propose.
        The proposal still requires human approval to execute.

        Args:
            finding: The finding to fix

        Returns:
            FixProposal or None if no fix available
        """
        self.logger.info(f"Generating fix proposal for {finding.id}")

        proposal = None

        if finding.service == "iam":
            proposal = self._propose_iam_fix(finding)
        elif finding.service == "s3":
            proposal = self._propose_s3_fix(finding)
        elif finding.service == "ec2":
            proposal = self._propose_ec2_fix(finding)
        elif finding.service == "vpc":
            proposal = self._propose_vpc_fix(finding)

        if proposal:
            self.proposals.append(proposal)
            finding.fix_proposal = proposal.id

        return proposal

    def _propose_iam_fix(self, finding: CloudFinding) -> FixProposal:
        """Generate IAM fix proposal."""
        # Generate Terraform code for IAM fix
        terraform = f'''# Fix for: {finding.title}
# Resource: {finding.resource_arn}
# Generated by JADE - Requires human approval

# TODO: Implement specific IAM fix based on finding type
# Common fixes:
# - Remove wildcard permissions
# - Add MFA requirement
# - Reduce privilege scope

resource "aws_iam_policy" "remediation" {{
  name        = "jade-remediation-{finding.id[:8]}"
  description = "JADE-generated remediation for {finding.title}"

  policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [
      {{
        Effect   = "Deny"
        Action   = ["*"]
        Resource = ["*"]
        Condition = {{
          Bool = {{
            "aws:MultiFactorAuthPresent" = "false"
          }}
        }}
      }}
    ]
  }})
}}
'''

        return FixProposal(
            id=f"proposal-{finding.id}",
            finding_id=finding.id,
            provider=CloudProvider.AWS,
            service="iam",
            action_type="terraform_pr",
            description=f"Terraform PR to fix: {finding.title}",
            terraform_code=terraform,
            cli_commands=[
                f"# Alternative CLI fix:",
                f"aws iam put-user-policy --user-name <user> --policy-name jade-fix --policy-document file://policy.json",
            ],
            risk_level="HIGH" if "admin" in finding.title.lower() else "MEDIUM",
        )

    def _propose_s3_fix(self, finding: CloudFinding) -> FixProposal:
        """Generate S3 fix proposal."""
        bucket_name = finding.resource_arn.split(":")[-1] if finding.resource_arn else "unknown"

        terraform = f'''# Fix for: {finding.title}
# Bucket: {bucket_name}
# Generated by JADE - Requires human approval

resource "aws_s3_bucket_public_access_block" "fix" {{
  bucket = "{bucket_name}"

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}

resource "aws_s3_bucket_server_side_encryption_configuration" "fix" {{
  bucket = "{bucket_name}"

  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "AES256"
    }}
  }}
}}
'''

        return FixProposal(
            id=f"proposal-{finding.id}",
            finding_id=finding.id,
            provider=CloudProvider.AWS,
            service="s3",
            action_type="terraform_pr",
            description=f"Terraform PR to secure bucket: {bucket_name}",
            terraform_code=terraform,
            cli_commands=[
                f"aws s3api put-public-access-block --bucket {bucket_name} --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true",
            ],
            risk_level="HIGH" if "public" in finding.title.lower() else "MEDIUM",
        )

    def _propose_ec2_fix(self, finding: CloudFinding) -> FixProposal:
        """Generate EC2 fix proposal."""
        return FixProposal(
            id=f"proposal-{finding.id}",
            finding_id=finding.id,
            provider=CloudProvider.AWS,
            service="ec2",
            action_type="cli_command",
            description=f"CLI commands to fix: {finding.title}",
            cli_commands=[
                f"# Review and apply as needed:",
                f"aws ec2 describe-instances --instance-ids <instance-id>",
                f"# Then apply appropriate security group changes",
            ],
            risk_level="MEDIUM",
        )

    def _propose_vpc_fix(self, finding: CloudFinding) -> FixProposal:
        """Generate VPC fix proposal."""
        return FixProposal(
            id=f"proposal-{finding.id}",
            finding_id=finding.id,
            provider=CloudProvider.AWS,
            service="vpc",
            action_type="terraform_pr",
            description=f"Terraform PR to fix: {finding.title}",
            terraform_code=f'''# Fix for: {finding.title}
# Generated by JADE - Requires human approval

# Review VPC security group rules and network ACLs
# Common fixes:
# - Restrict 0.0.0.0/0 ingress
# - Enable VPC flow logs
# - Add network ACL deny rules
''',
            risk_level="HIGH",
        )

    def alert(
        self,
        finding: CloudFinding,
        channel: str = "slack",
        proposal: Optional[FixProposal] = None
    ) -> Dict[str, Any]:
        """
        Send alert about a cloud finding.

        This is C-rank - JADE decides to alert.

        Args:
            finding: The finding to alert on
            channel: Alert channel (slack, email, pagerduty)
            proposal: Optional fix proposal to include

        Returns:
            Alert result
        """
        self.logger.info(f"Alerting on {finding.id} via {channel}")

        alert_message = {
            "type": "cloud_security_alert",
            "finding": finding.to_dict(),
            "proposal": proposal.to_dict() if proposal else None,
            "action_required": "Human approval needed for remediation",
            "approval_link": f"/api/cloud/proposals/{proposal.id}/approve" if proposal else None,
        }

        # TODO: Actually send to Slack/email/PagerDuty
        # For now, just return the message structure

        return {
            "status": "alert_queued",
            "channel": channel,
            "message": alert_message,
        }

    def execute_fix(
        self,
        proposal_id: str,
        approved_by: str
    ) -> Dict[str, Any]:
        """
        Execute an approved fix.

        This is B-rank - requires human approval.
        Will NOT execute without valid approval.

        Args:
            proposal_id: ID of the approved proposal
            approved_by: Who approved (for audit)

        Returns:
            Execution result
        """
        # Find the proposal
        proposal = next((p for p in self.proposals if p.id == proposal_id), None)

        if not proposal:
            return {"status": "error", "message": "Proposal not found"}

        if not proposal.approved:
            return {
                "status": "error",
                "message": "Proposal not approved - cannot execute",
                "requires": "Human approval via /api/cloud/proposals/{id}/approve"
            }

        self.logger.info(f"Executing approved fix {proposal_id} (approved by {approved_by})")

        # TODO: Actually execute the fix
        # For now, return what would happen

        return {
            "status": "executed",
            "proposal_id": proposal_id,
            "approved_by": approved_by,
            "action_type": proposal.action_type,
            "message": f"Would execute: {proposal.description}",
        }

    def approve_proposal(
        self,
        proposal_id: str,
        approved_by: str
    ) -> Dict[str, Any]:
        """
        Approve a fix proposal for execution.

        Args:
            proposal_id: Proposal to approve
            approved_by: Who is approving

        Returns:
            Approval result
        """
        proposal = next((p for p in self.proposals if p.id == proposal_id), None)

        if not proposal:
            return {"status": "error", "message": "Proposal not found"}

        proposal.approved = True
        proposal.approved_by = approved_by
        proposal.approved_at = datetime.now()

        self.logger.info(f"Proposal {proposal_id} approved by {approved_by}")

        return {
            "status": "approved",
            "proposal_id": proposal_id,
            "approved_by": approved_by,
            "can_execute": True,
        }

    def get_pending_proposals(self) -> List[FixProposal]:
        """Get proposals awaiting approval."""
        return [p for p in self.proposals if not p.approved]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of cloud security state."""
        findings_by_service = {}
        findings_by_severity = {}

        for f in self.findings:
            findings_by_service[f.service] = findings_by_service.get(f.service, 0) + 1
            findings_by_severity[f.severity] = findings_by_severity.get(f.severity, 0) + 1

        return {
            "total_findings": len(self.findings),
            "by_service": findings_by_service,
            "by_severity": findings_by_severity,
            "pending_proposals": len(self.get_pending_proposals()),
            "approved_proposals": len([p for p in self.proposals if p.approved]),
        }


# Singleton
_orchestrator: Optional[CloudOrchestrator] = None


def get_cloud_orchestrator() -> CloudOrchestrator:
    """Get the cloud orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = CloudOrchestrator()
    return _orchestrator
