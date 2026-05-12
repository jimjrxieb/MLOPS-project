"""
JADE Cloud Analyzers
====================
Cloud security analysis (D-rank).

Analyzers classify and enrich findings from watchers.
"""

CLOUD_ANALYZERS = [
    "cloud_iam_analyzer",
    "cloud_s3_analyzer",
    "cloud_ec2_analyzer",
    "cloud_vpc_analyzer",
    "cloud_cloudtrail_analyzer",
    "cloud_config_analyzer",
    "cloud_guardduty_analyzer",
    "cloud_kms_analyzer",
    "cloud_securityhub_analyzer",
    "iac_cloudformation_analyzer",
]
