"""
JADE Cloud Security Module
==========================
Cloud security operations managed by JADE (C-rank supervisor).

This module handles:
- AWS security monitoring (IAM, S3, EC2, VPC)
- Cloud drift detection
- CloudFormation/Terraform security
- AWS Secrets Manager monitoring

Authority Model:
- WATCH operations: E-rank (automatic)
- ANALYZE operations: D-rank (automatic)
- FIX operations: B-rank (requires human approval)

JADE orchestrates cloud security but does NOT auto-fix.
All cloud remediations require human approval via:
- Slack notification with fix proposal
- Terraform PR generation
- Manual approval workflow

Author: GP-Copilot
Created: 2026-02-08
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger("jade.cloud")

# Cloud domains
CLOUD_DOMAINS = [
    "aws-iam",
    "aws-s3",
    "aws-ec2",
    "aws-vpc",
    "aws-secrets",
    "cloudformation",
]

# Authority levels for cloud operations
CLOUD_AUTHORITY = {
    "watch": "E",      # Automatic - read-only detection
    "analyze": "D",    # Automatic - classification
    "alert": "C",      # JADE decides to alert
    "fix": "B",        # Human approval required
    "destroy": "S",    # Human only
}


def get_cloud_domains() -> List[str]:
    """Get list of cloud domains JADE manages."""
    return CLOUD_DOMAINS.copy()


def get_authority_for_action(action: str) -> str:
    """Get required authority level for a cloud action."""
    return CLOUD_AUTHORITY.get(action, "B")
