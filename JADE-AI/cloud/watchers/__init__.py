"""
JADE Cloud Watchers
===================
Read-only cloud security monitoring (E-rank).

These watchers detect issues but do NOT fix them.
Findings are sent to JADE for analysis and proposal generation.
"""

from typing import List

CLOUD_WATCHERS = [
    "cloud_iam_watcher",
    "cloud_s3_watcher",
    "cloud_ec2_watcher",
    "cloud_vpc_watcher",
    "iac_cloudformation_watcher",
    "secrets_aws_secrets_watcher",
]


def get_available_watchers() -> List[str]:
    """Get list of available cloud watchers."""
    return CLOUD_WATCHERS.copy()
