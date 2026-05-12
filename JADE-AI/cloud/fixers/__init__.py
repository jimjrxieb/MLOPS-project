"""
JADE Cloud Fixers
=================
Cloud security remediation (B-rank - requires human approval).

These fixers generate remediation proposals but do NOT auto-execute.
All cloud fixes require human approval before execution.

Authority Model:
- Generate proposal: C-rank (JADE can do)
- Execute fix: B-rank (human approval required)
"""

CLOUD_FIXERS = [
    "cloud_iam_fixer",
    "cloud_s3_fixer",
    "cloud_ec2_fixer",
    "cloud_vpc_fixer",
    "iac_cloudformation_fixer",
]

# All cloud fixers require human approval
REQUIRES_APPROVAL = True
