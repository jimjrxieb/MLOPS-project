#!/usr/bin/env python3
"""
AWS CLI Operations Training Data Generator
============================================
Priority 4: AWS CLI commands and service terminology.

Targets: aws iam, instance profile, NAT gateway, bucket policy,
credential-report, Security Groups, NACLs, VPC architecture.

Output: ChatML JSONL → 1-data-pipeline/01-raw-data-lake/
"""
import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "1-data-pipeline" / "01-raw-data-lake"
OUTPUT_FILE = OUTPUT_DIR / "aws_cli_ops.jsonl"

SYSTEM_PROMPT = "You are JADE, an AWS Solutions Architect and security expert. Provide exact AWS CLI commands with all required flags. Use canonical AWS service names and terminology. Always show the full aws cli command."

def msg(system, user, assistant):
    return {"messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant}
    ]}

def generate_iam_examples():
    examples = []
    scenarios = [
        {
            "q": "How do you find all IAM users with access keys older than 90 days?",
            "a": """Use the IAM credential report to find stale access keys:

```bash
# Generate the credential report
aws iam generate-credential-report

# Download and parse the credential report
aws iam get-credential-report --output text --query Content | base64 -d | \\
  awk -F',' 'NR>1 {if($9=="true" && $11!="N/A") print $1, $11}' | \\
  while read user date; do
    age=$(( ($(date +%s) - $(date -d "$date" +%s)) / 86400 ))
    if [ "$age" -gt 90 ]; then
      echo "STALE: $user - key age: ${age} days"
    fi
  done

# Alternative: list access keys per user
aws iam list-users --query 'Users[*].UserName' --output text | tr '\\t' '\\n' | \\
  while read user; do
    aws iam list-access-keys --user-name "$user" \\
      --query 'AccessKeyMetadata[?Status==`Active`].[AccessKeyId,CreateDate]' \\
      --output text
  done
```

**Best practice:** Automate this check with AWS Config rule `access-keys-rotated` with maxAccessKeyAge=90. Enforce key rotation via SCP (Service Control Policy) in AWS Organizations."""
        },
        {
            "q": "An IAM policy has 'Action': '*' and 'Resource': '*'. What is the risk and how do you fix it?",
            "a": """This is an overly permissive wildcard policy equivalent to full admin access. It violates the principle of least privilege.

**Risk:**
- Full access to all AWS services and all resources
- Can create/delete IAM users, modify billing, delete S3 buckets
- If credentials leak, attacker has complete account control

**Find overly permissive policies:**
```bash
# List all policies and check for wildcards
aws iam list-policies --scope Local --query 'Policies[*].[PolicyName,Arn]' --output text | \\
  while read name arn; do
    version=$(aws iam get-policy --policy-arn "$arn" --query 'Policy.DefaultVersionId' --output text)
    doc=$(aws iam get-policy-version --policy-arn "$arn" --version-id "$version" --query 'PolicyVersion.Document' --output json)
    if echo "$doc" | grep -q '"Action": "\\*"'; then
      echo "WILDCARD POLICY: $name ($arn)"
    fi
  done
```

**Fix — replace with specific actions and specific resources:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-app-bucket",
        "arn:aws:s3:::my-app-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/my-table"
    }
  ]
}
```

**Key principles:**
- Use specific actions (never `"*"`)
- Use specific resources (never `"*"` — scope to ARNs)
- Use IAM Access Analyzer to identify unused permissions
- Apply permission boundaries to limit maximum possible permissions"""
        },
        {
            "q": "Why should EC2 instances use IAM roles instead of access keys? Show the setup.",
            "a": """EC2 instances should use IAM roles via instance profiles, never embedded access keys.

**Why access keys are dangerous on EC2:**
- Hardcoded in code or environment variables — leaked in git, logs, backups
- No automatic rotation — manual process, often forgotten
- No audit trail for which instance used them
- If instance is compromised, keys work from anywhere

**Why IAM roles are better:**
- No credentials stored on the instance — temporary credentials auto-generated
- Automatic rotation — STS issues new credentials every few hours
- Instance-scoped — credentials only work from that instance
- Full CloudTrail audit trail

**Setup an instance profile with IAM role:**
```bash
# Create the IAM role with a trust policy for EC2
aws iam create-role \\
  --role-name MyAppRole \\
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach permissions to the role
aws iam attach-role-policy \\
  --role-name MyAppRole \\
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Create the instance profile
aws iam create-instance-profile \\
  --instance-profile-name MyAppProfile

# Add the role to the instance profile
aws iam add-role-to-instance-profile \\
  --instance-profile-name MyAppProfile \\
  --role-name MyAppRole

# Launch EC2 with the instance profile
aws ec2 run-instances \\
  --image-id ami-0abcdef1234567890 \\
  --instance-type t3.medium \\
  --iam-instance-profile Name=MyAppProfile \\
  --subnet-id subnet-abc123
```

**On the instance, credentials are automatic:**
```bash
# AWS SDK automatically uses instance profile credentials
# No need to set AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY
aws s3 ls s3://my-bucket/  # Just works

# Credentials come from the instance metadata service
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/MyAppRole
```

The instance profile provides temporary credentials via STS with automatic rotation. No secrets to manage, no keys to rotate, no credentials to leak."""
        },
    ]
    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def generate_networking_examples():
    examples = []
    scenarios = [
        {
            "q": "Explain the difference between NACLs and Security Groups in AWS.",
            "a": """NACLs and Security Groups are both network firewalls but operate at different levels:

**Security Groups (instance level, stateful):**
- Attached to ENIs (network interfaces) on EC2, RDS, Lambda, etc.
- **Stateful** — if inbound is allowed, outbound response is automatic
- **Allow rules only** — no deny rules, default deny for inbound
- Evaluated as a group — all rules checked, any match = allow

```bash
# Create a Security Group
aws ec2 create-security-group \\
  --group-name web-sg \\
  --description "Web server security group" \\
  --vpc-id vpc-abc123

# Allow HTTPS from specific CIDR
aws ec2 authorize-security-group-ingress \\
  --group-id sg-abc123 \\
  --protocol tcp \\
  --port 443 \\
  --cidr 10.0.0.0/16
```

**NACLs (subnet level, stateless):**
- Applied to entire subnets
- **Stateless** — must explicitly allow both inbound AND outbound
- **Allow AND deny rules** — rules processed in order by number
- First matching rule wins (unlike Security Groups)

```bash
# Create a NACL
aws ec2 create-network-acl --vpc-id vpc-abc123

# Add inbound rule (allow HTTPS)
aws ec2 create-network-acl-entry \\
  --network-acl-id acl-abc123 \\
  --rule-number 100 \\
  --protocol tcp \\
  --port-range From=443,To=443 \\
  --cidr-block 0.0.0.0/0 \\
  --rule-action allow \\
  --ingress

# Add outbound rule (required because stateless)
aws ec2 create-network-acl-entry \\
  --network-acl-id acl-abc123 \\
  --rule-number 100 \\
  --protocol tcp \\
  --port-range From=1024,To=65535 \\
  --cidr-block 0.0.0.0/0 \\
  --rule-action allow \\
  --egress
```

| Feature | Security Group | NACL |
|---------|---------------|------|
| Level | Instance level | Subnet level |
| State | Stateful | Stateless |
| Rules | Allow only | Allow and deny |
| Processing | All rules evaluated | First match wins |
| Default | Deny all inbound | Allow all |
| Use case | Per-instance firewall | Subnet-wide guardrail |

**Best practice:** Use Security Groups as your primary firewall (instance level). Use NACLs as a coarse subnet-level backup for defense in depth."""
        },
        {
            "q": "Design a secure 3-tier VPC architecture with public, private, and database subnets.",
            "a": """Three-tier VPC with proper network isolation:

```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=prod-vpc}]'

# Public subnet (ALB, bastion)
aws ec2 create-subnet --vpc-id vpc-abc --cidr-block 10.0.1.0/24 --availability-zone us-east-1a --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=public-1a}]'

# Private subnet (application servers)
aws ec2 create-subnet --vpc-id vpc-abc --cidr-block 10.0.10.0/24 --availability-zone us-east-1a --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=private-1a}]'

# Database subnet (RDS, ElastiCache)
aws ec2 create-subnet --vpc-id vpc-abc --cidr-block 10.0.20.0/24 --availability-zone us-east-1a --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=database-1a}]'

# Internet Gateway (for public subnet)
aws ec2 create-internet-gateway
aws ec2 attach-internet-gateway --internet-gateway-id igw-abc --vpc-id vpc-abc

# NAT Gateway (for private subnet outbound)
aws ec2 allocate-address --domain vpc
aws ec2 create-nat-gateway --subnet-id subnet-public-1a --allocation-id eipalloc-abc

# Route tables
# Public: 0.0.0.0/0 → Internet Gateway
# Private: 0.0.0.0/0 → NAT Gateway (outbound only)
# Database: no internet route (fully isolated)
```

**Architecture:**
```
Internet
  ↕
Internet Gateway
  ↕
┌─────────────────────────────────────────┐
│ Public Subnet (10.0.1.0/24)             │
│ - ALB (Application Load Balancer)       │
│ - Bastion host (SSH jump box)           │
│ - NAT Gateway                           │
└─────────────────────────────────────────┘
  ↕ (Security Groups)
┌─────────────────────────────────────────┐
│ Private Subnet (10.0.10.0/24)           │
│ - Application servers (EC2/ECS/EKS)     │
│ - Outbound via NAT Gateway only         │
│ - No direct internet access             │
└─────────────────────────────────────────┘
  ↕ (Security Groups)
┌─────────────────────────────────────────┐
│ Database Subnet (10.0.20.0/24)          │
│ - RDS (publicly_accessible = false)     │
│ - ElastiCache                           │
│ - No internet access at all             │
│ - NACLs: only allow from private subnet │
└─────────────────────────────────────────┘
```

**Security Groups:**
- ALB SG: inbound 443 from 0.0.0.0/0
- App SG: inbound 8080 from ALB SG only
- DB SG: inbound 5432 from App SG only
- NACLs on database subnet: deny all except from 10.0.10.0/24"""
        },
    ]
    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def generate_s3_rds_examples():
    examples = []
    scenarios = [
        {
            "q": "How do you ensure an RDS instance is not publicly accessible?",
            "a": """Verify and enforce private RDS access:

```bash
# Check current RDS instances for public accessibility
aws rds describe-db-instances \\
  --query 'DBInstances[*].[DBInstanceIdentifier,PubliclyAccessible,Endpoint.Address]' \\
  --output table

# If publicly accessible, modify to private
aws rds modify-db-instance \\
  --db-instance-identifier my-database \\
  --no-publicly-accessible \\
  --apply-immediately

# Ensure RDS is in a private subnet
aws rds describe-db-subnet-groups \\
  --db-subnet-group-name my-db-subnet-group
```

**Allow Lambda in VPC to access private RDS:**
```bash
# Lambda must be in the same VPC
aws lambda update-function-configuration \\
  --function-name my-function \\
  --vpc-config SubnetIds=subnet-private-1a,subnet-private-1b,SecurityGroupIds=sg-lambda

# Lambda SG needs outbound to RDS port
aws ec2 authorize-security-group-ingress \\
  --group-id sg-rds \\
  --protocol tcp \\
  --port 5432 \\
  --source-group sg-lambda
```

**Key settings:**
- `PubliclyAccessible: false` — no public IP assigned
- Place in private subnet (no internet gateway route)
- Security group: only allow inbound from application security group
- No public IP means no direct internet access, even if security group allows it"""
        },
        {
            "q": "How do you configure cross-account S3 access for a Lambda function?",
            "a": """Cross-account S3 access requires IAM roles and bucket policies:

**Account A (owns the S3 bucket):**
```bash
# Add a bucket policy allowing Account B's role
aws s3api put-bucket-policy --bucket my-data-bucket --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::222222222222:role/LambdaRole"
      },
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-data-bucket",
        "arn:aws:s3:::my-data-bucket/*"
      ]
    }
  ]
}'
```

**Account B (runs the Lambda):**
```bash
# Create a role with trust policy for Lambda
aws iam create-role --role-name LambdaRole --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}'

# Attach S3 read permissions
aws iam put-role-policy --role-name LambdaRole --policy-name S3CrossAccountRead --policy-document '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::my-data-bucket",
      "arn:aws:s3:::my-data-bucket/*"
    ]
  }]
}'
```

**Cross-account access requires BOTH:**
1. The bucket policy in Account A (resource policy) must allow Account B's role
2. The IAM role in Account B must have permission to access S3

Neither alone is sufficient. This is the AWS trust policy + resource policy model for cross-account access."""
        },
    ]
    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def main():
    all_examples = []

    print("[1/3] Generating IAM/CLI examples...")
    all_examples.extend(generate_iam_examples())

    print("[2/3] Generating VPC/networking examples...")
    all_examples.extend(generate_networking_examples())

    print("[3/3] Generating S3/RDS examples...")
    all_examples.extend(generate_s3_rds_examples())

    random.shuffle(all_examples)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\nGenerated {len(all_examples)} AWS CLI ops examples")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
