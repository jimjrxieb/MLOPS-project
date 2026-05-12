#!/usr/bin/env python3
"""
Generate training data specifically for JADE benchmark gaps.

Based on benchmark results:
- Classification: 0% (needs rank format + agent routing)
- Incident Response: 10%
- Cloud: 20%
- Compliance: 20%
- Fix Generation: 0%
"""

import json
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-GP-GLUE/00-processed/benchmark-training")

# ============================================================
# 1. CLASSIFICATION TRAINING DATA (Most Critical - 0%)
# ============================================================

CLASSIFICATION_EXAMPLES = [
    # D-RANK examples (automatable)
    {
        "instruction": "Classify this security finding and determine the appropriate JSA agent to handle it.",
        "input": """Scanner: trivy
Severity: CRITICAL
Finding: CVE-2024-1234 - Remote code execution in express < 4.18.0
Package: express@4.17.0
Fix Available: Yes (upgrade to 4.18.2)""",
        "output": """**Classification: D-RANK**

**Assigned Agent:** jsa-devsec

**Rationale:** This is a D-rank finding because:
1. Critical CVE with known fix (dependency upgrade)
2. Fix is deterministic - update package.json/package-lock.json
3. No human judgment needed - automated pipeline can handle

**Auto-fix:** YES - JSA will automatically update the dependency and create a PR.

**Defense Action:**
```bash
npm update express@4.18.2
```"""
    },
    {
        "instruction": "Classify this security finding and determine the appropriate JSA agent to handle it.",
        "input": """Scanner: checkov
Check ID: CKV_AWS_19
Severity: HIGH
Description: S3 bucket without encryption
Resource: aws_s3_bucket.logs
File: terraform/storage.tf:45""",
        "output": """**Classification: D-RANK**

**Assigned Agent:** jsa-infrasec

**Rationale:** This is a D-rank finding because:
1. Standard IaC misconfiguration with well-known fix
2. Encryption can be enabled without service disruption
3. Fix pattern is deterministic (add server_side_encryption_configuration block)

**Auto-fix:** YES - JSA will add encryption configuration to the Terraform resource.

**Defense Action:**
```hcl
resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```"""
    },
    {
        "instruction": "Classify this security finding and determine the appropriate JSA agent to handle it.",
        "input": """Scanner: gitleaks
Severity: CRITICAL
Description: AWS access key detected in source code
File: config/settings.py
Line: 42
Secret: AKIA...redacted...XYZ""",
        "output": """**Classification: D-RANK**

**Assigned Agent:** jsa-devsec

**Rationale:** This is a D-rank finding because:
1. Hardcoded secret with clear remediation (remove and rotate)
2. Detection is definitive (pattern-matched AWS key format)
3. Automated rotation and removal is safe

**Auto-fix:** YES - JSA will:
1. Rotate the AWS access key via AWS CLI
2. Remove the hardcoded value from code
3. Replace with environment variable reference

**Defense Action:**
```python
# Replace hardcoded secret with:
import os
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
```"""
    },
    # C-RANK examples (JADE review needed)
    {
        "instruction": "Classify this security finding and determine the appropriate JSA agent to handle it.",
        "input": """Scanner: kubescape
Severity: HIGH
Description: Pod running with privileged security context
Resource: deployment/nginx
Namespace: production
Container: nginx-proxy""",
        "output": """**Classification: C-RANK**

**Assigned Agent:** jsa-infrasec

**Rationale:** This is a C-rank finding because:
1. Privileged containers are risky but may be required for certain workloads
2. Removing privilege without analysis could break functionality
3. JADE needs to verify if privilege is actually required

**Auto-fix:** NO - Requires JADE analysis first.

**JADE Review Required:**
- Check if workload actually needs privileged access
- Identify specific capabilities needed (vs full privilege)
- Verify no security-sensitive data accessible

**Recommended Fix (if privilege not needed):**
```yaml
securityContext:
  privileged: false
  runAsNonRoot: true
  capabilities:
    drop: ["ALL"]
```"""
    },
    {
        "instruction": "Classify this security finding and determine the appropriate JSA agent to handle it.",
        "input": """Scanner: falco
Severity: CRITICAL
Description: Shell spawned in container
Resource: pod/api-server-abc123
Namespace: production
Rule: Terminal shell in container
Command: /bin/bash""",
        "output": """**Classification: C-RANK**

**Assigned Agent:** jsa-monitor

**Rationale:** This is a C-rank finding because:
1. Could indicate active compromise OR legitimate debugging
2. Requires context analysis before response
3. Wrong action could disrupt legitimate operations or miss attacker

**Auto-fix:** NO - Requires JADE investigation.

**JADE Investigation Required:**
- Who initiated the shell? (kubectl exec user)
- Is this a break-glass scenario or unauthorized access?
- Check for lateral movement attempts

**Potential Response (if malicious):**
1. Isolate pod with NetworkPolicy
2. Capture forensic data
3. Kill and recreate pod from clean image"""
    },
    # B-RANK examples (Human intervention needed)
    {
        "instruction": "Classify this security finding and determine the appropriate JSA agent to handle it.",
        "input": """Scanner: prowler
Severity: CRITICAL
Description: Root account has no MFA enabled
Resource: arn:aws:iam::123456789012:root
Account: production-main""",
        "output": """**Classification: B-RANK**

**Assigned Agent:** jsa-infrasec

**Rationale:** This is a B-rank finding because:
1. MFA setup requires physical device/authenticator app
2. Cannot be automated without human interaction
3. Root account changes have high blast radius

**Auto-fix:** NO - Human intervention required.

**Human Action Required:**
1. Log into AWS Console as root
2. Navigate to IAM → Security credentials
3. Set up virtual MFA device or hardware token
4. Store backup codes securely

**Escalation:** Page on-call security engineer for immediate action."""
    },
    {
        "instruction": "Classify this security finding and determine the appropriate JSA agent to handle it.",
        "input": """Scanner: guardduty
Severity: HIGH
Description: UnauthorizedAccess:IAMUser/MaliciousIPCaller.Custom
Resource: arn:aws:iam::123456789012:user/deploy-bot
Source IP: 185.234.xxx.xxx (known malicious)""",
        "output": """**Classification: B-RANK**

**Assigned Agent:** jsa-monitor

**Rationale:** This is a B-rank finding because:
1. Potential credential compromise requires human investigation
2. Automated credential rotation could disrupt production
3. Need to determine scope of compromise before action

**Auto-fix:** NO - Human investigation required.

**Immediate Actions:**
1. Preserve CloudTrail logs for forensics
2. Do NOT rotate credentials yet (preserves investigation)
3. Page security team for incident response

**Human Investigation Required:**
- Determine if this is a false positive (VPN, expected source?)
- Review all API calls from this user in last 24h
- Check for persistence mechanisms created"""
    },
    # E-RANK examples (fully automated, low severity)
    {
        "instruction": "Classify this security finding and determine the appropriate JSA agent to handle it.",
        "input": """Scanner: trivy
Severity: LOW
Description: Informational finding about outdated package
Package: lodash@4.17.20
Latest: lodash@4.17.21
CVE: None""",
        "output": """**Classification: E-RANK**

**Assigned Agent:** jsa-devsec

**Rationale:** This is an E-rank finding because:
1. Low severity, informational only
2. No security impact (no CVE)
3. Routine maintenance upgrade

**Auto-fix:** YES - Fully automated.

**Defense Action:**
```bash
npm update lodash
```

No human notification needed - logged for audit only."""
    },
    # S-RANK examples (Strategic/Human only)
    {
        "instruction": "Classify this security finding and determine the appropriate JSA agent to handle it.",
        "input": """Scanner: manual
Severity: CRITICAL
Description: Architecture review needed for new microservice deployment
Context: New payment service handling PCI data
Requested by: Engineering team""",
        "output": """**Classification: S-RANK**

**Assigned Agent:** None (Human architect required)

**Rationale:** This is an S-rank finding because:
1. Strategic architectural decision
2. PCI compliance implications
3. No automation can replace human security architect review

**Auto-fix:** NO - Human architect required.

**Required Review:**
1. PCI-DSS scope analysis
2. Data flow diagram review
3. Threat modeling (STRIDE)
4. Network segmentation design
5. Encryption requirements

**Escalation:** Schedule architecture review board meeting."""
    },
]

# Agent routing examples
AGENT_ROUTING_EXAMPLES = [
    {
        "instruction": "Determine which JSA agent should handle this request.",
        "input": "Scan my Python code for security vulnerabilities",
        "output": """**Assigned Agent:** jsa-devsec

**Rationale:** Code scanning is the DevSecOps domain. jsa-devsec handles:
- Static code analysis (SAST)
- Dependency scanning
- Secret detection
- CI/CD pipeline security

**Recommended Tools:** semgrep, bandit, gitleaks"""
    },
    {
        "instruction": "Determine which JSA agent should handle this request.",
        "input": "Check if my Kubernetes cluster is CIS compliant",
        "output": """**Assigned Agent:** jsa-infrasec

**Rationale:** Kubernetes compliance is the Infrastructure Security domain. jsa-infrasec handles:
- Kubernetes security scanning
- CIS benchmark compliance
- Infrastructure hardening
- Admission control policies

**Recommended Tools:** kube-bench, kubescape"""
    },
    {
        "instruction": "Determine which JSA agent should handle this request.",
        "input": "Set up continuous monitoring for suspicious container activity",
        "output": """**Assigned Agent:** jsa-monitor

**Rationale:** Continuous monitoring is the Security Operations domain. jsa-monitor handles:
- Runtime security monitoring
- Anomaly detection
- Alert correlation
- Incident detection

**Recommended Tools:** falco, prometheus, grafana"""
    },
    {
        "instruction": "Determine which JSA agent should handle this request.",
        "input": "Fix the Checkov findings in my Terraform code",
        "output": """**Assigned Agent:** jsa-devsec

**Rationale:** IaC scanning in CI is the DevSecOps domain. jsa-devsec handles:
- Terraform security scanning
- IaC remediation
- Pre-commit policy enforcement

**Recommended Tools:** checkov, tfsec, conftest"""
    },
    {
        "instruction": "Determine which JSA agent should handle this request.",
        "input": "Investigate the GuardDuty alert about malicious IP access",
        "output": """**Assigned Agent:** jsa-monitor

**Rationale:** Alert investigation is the Security Operations domain. jsa-monitor handles:
- Cloud security alerts
- Threat investigation
- Forensic data collection
- Incident response coordination

**Recommended Tools:** guardduty, cloudtrail, athena"""
    },
    {
        "instruction": "Determine which JSA agent should handle this request.",
        "input": "Deploy a Gatekeeper policy to block privileged containers",
        "output": """**Assigned Agent:** jsa-infrasec

**Rationale:** Admission control is the Infrastructure Security domain. jsa-infrasec handles:
- OPA/Gatekeeper policies
- Kubernetes admission webhooks
- Policy enforcement

**Recommended Tools:** gatekeeper, kubectl, opa"""
    },
]

# ============================================================
# 2. INCIDENT RESPONSE TRAINING DATA (10% - Critical Gap)
# ============================================================

INCIDENT_RESPONSE_EXAMPLES = [
    {
        "instruction": "How should I respond to this security incident?",
        "input": "GuardDuty detected cryptomining activity on one of our EC2 instances. Instance ID: i-0abc123def456. Region: us-east-1.",
        "output": """**Incident Classification:** Cryptojacking - Active Compromise

**Severity:** HIGH - Immediate response required

**Containment Steps (Execute Immediately):**
1. **Isolate the instance:**
   ```bash
   aws ec2 modify-instance-attribute --instance-id i-0abc123def456 \
     --groups sg-isolated-incident
   ```

2. **Stop but DO NOT terminate (preserve forensics):**
   ```bash
   aws ec2 stop-instances --instance-id i-0abc123def456
   ```

3. **Create snapshot for forensics:**
   ```bash
   aws ec2 create-snapshot --volume-id <root-volume-id> \
     --description "Incident-response-cryptojack-$(date +%Y%m%d)"
   ```

**Investigation:**
- Review CloudTrail for IAM activity
- Check Instance Metadata Service access logs
- Identify initial access vector (SSH? IMDS? Application vulnerability?)

**Eradication:**
- Terminate compromised instance
- Deploy fresh instance from clean AMI
- Rotate all credentials that touched this instance

**Post-Incident:**
- Update security groups to restrict outbound
- Enable GuardDuty findings export to S3
- Review IAM roles attached to instance"""
    },
    {
        "instruction": "How should I respond to this security incident?",
        "input": "Our CI/CD pipeline was compromised. An attacker pushed malicious code through a stolen developer token. The code reached production.",
        "output": """**Incident Classification:** Supply Chain Compromise - Code Injection

**Severity:** CRITICAL - Production impact

**Immediate Containment:**
1. **Revoke compromised token immediately:**
   ```bash
   gh auth token --delete <token-id>
   # Or in GitHub: Settings > Developer settings > Personal access tokens
   ```

2. **Lock down the repository:**
   ```bash
   gh repo edit --enable-branch-protection main
   # Require signed commits, reviews
   ```

3. **Rollback production:**
   ```bash
   kubectl rollout undo deployment/<affected-deployment>
   # Or: git revert to last known-good commit
   ```

**Investigation:**
- Audit all commits since token compromise
- Review which secrets the attacker could access
- Check for persistence (backdoors, additional tokens)

**Eradication:**
- Force rotate all CI/CD secrets
- Invalidate all existing developer tokens
- Redeploy from verified clean commit

**Post-Incident:**
- Implement signed commits requirement
- Add code signing to CI/CD pipeline
- Require MFA for all developer accounts
- Set up secret scanning in pre-receive hooks"""
    },
    {
        "instruction": "How should I respond to this security incident?",
        "input": "We detected unauthorized access to our S3 bucket containing customer PII. CloudTrail shows ListBucket and GetObject from an unknown IP.",
        "output": """**Incident Classification:** Data Breach - PII Exposure

**Severity:** CRITICAL - Regulatory notification may be required

**Immediate Containment:**
1. **Block the IP immediately:**
   ```bash
   aws s3api put-bucket-policy --bucket <bucket-name> --policy '{
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Deny",
       "Principal": "*",
       "Action": "s3:*",
       "Resource": ["arn:aws:s3:::<bucket>/*"],
       "Condition": {
         "IpAddress": {"aws:SourceIp": "<attacker-ip>"}
       }
     }]
   }'
   ```

2. **Revoke public access:**
   ```bash
   aws s3api put-public-access-block --bucket <bucket-name> \
     --public-access-block-configuration \
     BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
   ```

**Investigation:**
- Enumerate all objects accessed (S3 access logs)
- Determine how access was obtained (leaked creds? misconfigured bucket?)
- Identify affected customers

**Regulatory:**
- If PII confirmed accessed: initiate breach notification process
- Document timeline for compliance (GDPR: 72 hours, CCPA: expeditiously)
- Engage legal counsel

**Eradication:**
- Rotate all S3 access credentials
- Enable server-side encryption
- Configure bucket to require HTTPS only"""
    },
    {
        "instruction": "What are the first 5 steps when triaging a security alert?",
        "input": "I received an alert about potential lateral movement in our Kubernetes cluster.",
        "output": """**Alert Triage Steps:**

**1. Validate the Alert (2 min)**
- Check if this is a known false positive pattern
- Verify the alert source is functioning correctly
- Confirm the affected resource exists

**2. Assess Scope (5 min)**
- Which pods/nodes are involved?
- What namespace?
- Is this production or development?

**3. Determine Severity (2 min)**
Based on:
- Data sensitivity (PII, secrets, customer data?)
- Business impact (revenue-generating service?)
- Blast radius (can it spread further?)

**4. Initial Containment Decision (1 min)**
- If active threat: isolate immediately with NetworkPolicy
- If unclear: increase monitoring, don't alert attacker

**5. Escalation (1 min)**
- E/D rank: JSA handles autonomously
- C rank: JADE reviews before action
- B/S rank: Page human immediately

**For Lateral Movement Specifically:**
```yaml
# Emergency NetworkPolicy - block all egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: emergency-isolate
spec:
  podSelector:
    matchLabels:
      compromised: "true"
  policyTypes:
  - Egress
  egress: []  # Block all
```"""
    },
]

# ============================================================
# 3. CLOUD SECURITY TRAINING DATA (20% - Gap)
# ============================================================

CLOUD_SECURITY_EXAMPLES = [
    {
        "instruction": "What is the security risk and how do I fix it?",
        "input": """AWS Security Group allows SSH (port 22) from 0.0.0.0/0:

resource "aws_security_group" "web" {
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}""",
        "output": """**Risk:** PUBLIC INTERNET SSH ACCESS - HIGH

Opening SSH to the public internet (0.0.0.0/0) creates these risks:
- **Brute force attacks**: Automated bots continuously scan for open SSH
- **Credential stuffing**: Compromised passwords tried across services
- **Zero-day exploitation**: Any SSH vulnerability becomes immediately exploitable

**Fix:**
```hcl
resource "aws_security_group" "web" {
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]  # Internal network only
    description = "SSH from VPN/internal only"
  }
}
```

**Better Alternatives:**
1. **AWS Systems Manager Session Manager** (no open ports needed)
2. **Bastion host** in private subnet with MFA
3. **VPN connection** with specific CIDR blocks
4. **AWS Client VPN** for remote access"""
    },
    {
        "instruction": "What is the security risk and how do I fix it?",
        "input": """IAM policy grants wildcard permissions:

{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "*",
    "Resource": "*"
  }]
}""",
        "output": """**Risk:** OVERLY PERMISSIVE IAM - CRITICAL

Wildcard permissions violate least privilege principle:
- **Credential theft impact**: Attacker gets full account access
- **Blast radius**: Can affect ALL AWS services and resources
- **Compliance violation**: Fails CIS, SOC2, PCI-DSS controls

**Fix - Apply Least Privilege:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "s3:GetObject",
      "s3:PutObject"
    ],
    "Resource": "arn:aws:s3:::my-bucket/*"
  }]
}
```

**Best Practices:**
1. Use specific actions (not `*`)
2. Use specific resources (not `*`)
3. Add conditions (IP, MFA, time-based)
4. Use IAM Access Analyzer to right-size permissions
5. Review with `aws iam simulate-principal-policy`"""
    },
    {
        "instruction": "Explain the difference between Security Groups and NACLs in AWS.",
        "input": "When should I use Security Groups vs Network ACLs for network security?",
        "output": """**Security Groups vs Network ACLs (NACLs):**

| Feature | Security Groups | NACLs |
|---------|-----------------|-------|
| **Level** | Instance level | Subnet level |
| **State** | Stateful (return traffic auto-allowed) | Stateless (explicit rules for both) |
| **Rules** | Allow only | Allow AND Deny |
| **Evaluation** | All rules evaluated | Rules evaluated in order |
| **Default** | Deny all inbound, allow all outbound | Allow all |

**When to Use Security Groups:**
- Per-instance firewall rules
- Application-level access control
- When you need stateful connections
- Most common use case

**When to Use NACLs:**
- Subnet-level blocking (e.g., block known malicious IPs)
- Defense in depth (backup to security groups)
- When you need explicit DENY rules
- Compliance requirements for subnet isolation

**Best Practice - Use Both:**
```
Internet → NACL (subnet defense) → Security Group (instance defense) → Instance
```

NACLs act as first line, Security Groups as second."""
    },
    {
        "instruction": "What is the security risk and how do I fix it?",
        "input": """RDS instance is publicly accessible:

resource "aws_db_instance" "main" {
  identifier           = "production-db"
  publicly_accessible  = true
  skip_final_snapshot  = true
}""",
        "output": """**Risk:** PUBLIC DATABASE - CRITICAL

A publicly accessible RDS instance:
- Exposes database directly to internet attacks
- Allows SQL injection attempts from anywhere
- Violates compliance (PCI-DSS, HIPAA)

**Fix:**
```hcl
resource "aws_db_instance" "main" {
  identifier           = "production-db"
  publicly_accessible  = false
  skip_final_snapshot  = false  # Keep snapshots!

  # Place in private subnet
  db_subnet_group_name = aws_db_subnet_group.private.name

  # Restrict security group
  vpc_security_group_ids = [aws_security_group.db.id]
}

resource "aws_security_group" "db" {
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]  # App servers only
  }
}
```

**Architecture:**
```
Internet → ALB → App (private subnet) → RDS (private subnet)
                    ↑ no direct path to DB
```"""
    },
]

# ============================================================
# 4. COMPLIANCE TRAINING DATA (20% - Gap)
# ============================================================

COMPLIANCE_EXAMPLES = [
    {
        "instruction": "What CIS control does this finding violate and how do I remediate it?",
        "input": "CIS AWS Benchmark 2.1.1: Ensure S3 bucket access logging is enabled",
        "output": """**CIS Control:** 2.1.1 - S3 Bucket Access Logging

**Control Description:**
S3 bucket access logging provides detailed records for access requests, useful for security audits and forensic investigations.

**Why It Matters:**
- Without logging, you can't detect unauthorized access
- Compliance frameworks require audit trails
- Incident response needs access logs

**Remediation:**
```hcl
# Create logging bucket
resource "aws_s3_bucket" "logs" {
  bucket = "my-access-logs-bucket"
}

# Enable versioning on logs bucket
resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable logging on target bucket
resource "aws_s3_bucket_logging" "main" {
  bucket = aws_s3_bucket.main.id
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "access-logs/"
}
```

**Verification:**
```bash
aws s3api get-bucket-logging --bucket my-bucket
```

**Maps To:**
- SOC 2: CC6.1 (Logical Access Controls)
- PCI-DSS: 10.2 (Audit Trails)
- NIST: AU-2 (Audit Events)"""
    },
    {
        "instruction": "How do I achieve SOC 2 compliance for encryption at rest?",
        "input": "Our auditor asked about encryption at rest controls for SOC 2 Type II.",
        "output": """**SOC 2 Trust Services Criteria:** CC6.1 - Logical and Physical Access Controls

**Requirement:** Data at rest must be encrypted to prevent unauthorized access.

**AWS Implementation:**

**1. S3 Encryption:**
```hcl
resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.main.arn
    }
    bucket_key_enabled = true
  }
}
```

**2. RDS Encryption:**
```hcl
resource "aws_db_instance" "main" {
  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn
}
```

**3. EBS Encryption (default):**
```bash
aws ec2 enable-ebs-encryption-by-default --region us-east-1
```

**Evidence for Auditor:**
- KMS key policies showing key management controls
- AWS Config rules showing encryption compliance
- Screenshots of encrypted resource settings

**Continuous Monitoring:**
```hcl
resource "aws_config_config_rule" "s3_encrypted" {
  name = "s3-bucket-server-side-encryption-enabled"
  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED"
  }
}
```"""
    },
    {
        "instruction": "What NIST 800-53 control addresses this requirement?",
        "input": "We need to implement audit logging for all administrative actions.",
        "output": """**NIST 800-53 Control:** AU-2 (Audit Events)

**Control Description:**
The organization determines that the information system is capable of auditing organizationally-defined auditable events.

**Implementation for AWS:**

**1. CloudTrail (API Logging):**
```hcl
resource "aws_cloudtrail" "main" {
  name                          = "org-audit-trail"
  s3_bucket_name               = aws_s3_bucket.audit.id
  include_global_service_events = true
  is_multi_region_trail        = true
  enable_log_file_validation   = true

  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }
}
```

**2. CloudWatch Logs for Applications:**
```hcl
resource "aws_cloudwatch_log_group" "app" {
  name              = "/app/admin-actions"
  retention_in_days = 365  # NIST requires 1 year minimum
}
```

**3. VPC Flow Logs (Network):**
```hcl
resource "aws_flow_log" "main" {
  vpc_id          = aws_vpc.main.id
  traffic_type    = "ALL"
  log_destination = aws_cloudwatch_log_group.vpc.arn
}
```

**Related Controls:**
- AU-3: Content of Audit Records
- AU-6: Audit Review, Analysis, and Reporting
- AU-9: Protection of Audit Information
- AU-11: Audit Record Retention"""
    },
]

# ============================================================
# 5. FIX GENERATION TRAINING DATA (0% - Critical)
# ============================================================

FIX_GENERATION_EXAMPLES = [
    {
        "instruction": "Generate a fix for this Trivy finding.",
        "input": """Scanner: trivy
Finding: CVE-2024-1234
Severity: CRITICAL
Package: express@4.17.0
Description: Remote code execution vulnerability
Fix Version: 4.18.2
File: package.json""",
        "output": """**Fix for CVE-2024-1234 (express RCE)**

Update package.json:
```json
{
  "dependencies": {
    "express": "^4.18.2"
  }
}
```

Commands to apply:
```bash
# Update package
npm install express@4.18.2

# Verify fix
npm audit

# Run tests to ensure compatibility
npm test

# Commit
git add package.json package-lock.json
git commit -m "fix(deps): upgrade express to 4.18.2 (CVE-2024-1234)"
```

**Verification:**
```bash
trivy fs . --severity CRITICAL | grep CVE-2024-1234
# Should return no results
```"""
    },
    {
        "instruction": "Generate a fix for this Checkov finding.",
        "input": """Scanner: checkov
Check ID: CKV_AWS_23
Severity: HIGH
Description: Ensure security group does not have unrestricted ingress
Resource: aws_security_group.web
File: main.tf:45""",
        "output": """**Fix for CKV_AWS_23 (Unrestricted Security Group)**

Before (insecure):
```hcl
resource "aws_security_group" "web" {
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

After (secure):
```hcl
resource "aws_security_group" "web" {
  name        = "web-sg"
  description = "Security group for web servers"
  vpc_id      = aws_vpc.main.id

  # Only allow HTTPS from internet
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from internet"
  }

  # Allow HTTP redirect
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP redirect to HTTPS"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "web-sg"
  }
}
```

**Verification:**
```bash
checkov -f main.tf --check CKV_AWS_23
# Should PASS
```"""
    },
    {
        "instruction": "Generate a fix for this Semgrep finding.",
        "input": """Scanner: semgrep
Rule: python.django.security.injection.sql
Severity: HIGH
Description: SQL injection vulnerability detected
File: api/users.py
Line: 78
Code: cursor.execute("SELECT * FROM users WHERE id = " + user_id)""",
        "output": """**Fix for SQL Injection (Semgrep)**

Before (vulnerable):
```python
# api/users.py:78
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE id = " + user_id)
    return cursor.fetchone()
```

After (secure - parameterized query):
```python
# api/users.py:78
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()
```

**Or with Django ORM (recommended):**
```python
from django.contrib.auth.models import User

def get_user(user_id):
    return User.objects.filter(id=user_id).first()
```

**Why this fix works:**
- Parameterized queries separate SQL logic from data
- Database driver handles escaping
- Prevents `' OR '1'='1` type attacks

**Verification:**
```bash
semgrep --config=p/python-django-security api/users.py
# Should show no SQL injection findings
```"""
    },
]


def generate_all_training_data():
    """Generate all gap-filling training data."""
    all_examples = []

    # Classification examples (most critical)
    print(f"Adding {len(CLASSIFICATION_EXAMPLES)} classification examples...")
    all_examples.extend(CLASSIFICATION_EXAMPLES)

    # Agent routing examples
    print(f"Adding {len(AGENT_ROUTING_EXAMPLES)} agent routing examples...")
    all_examples.extend(AGENT_ROUTING_EXAMPLES)

    # Incident response examples
    print(f"Adding {len(INCIDENT_RESPONSE_EXAMPLES)} incident response examples...")
    all_examples.extend(INCIDENT_RESPONSE_EXAMPLES)

    # Cloud security examples
    print(f"Adding {len(CLOUD_SECURITY_EXAMPLES)} cloud security examples...")
    all_examples.extend(CLOUD_SECURITY_EXAMPLES)

    # Compliance examples
    print(f"Adding {len(COMPLIANCE_EXAMPLES)} compliance examples...")
    all_examples.extend(COMPLIANCE_EXAMPLES)

    # Fix generation examples
    print(f"Adding {len(FIX_GENERATION_EXAMPLES)} fix generation examples...")
    all_examples.extend(FIX_GENERATION_EXAMPLES)

    return all_examples


def save_training_data(examples: list, output_dir: Path):
    """Save training data to JSONL file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"gap_training_{timestamp}.jsonl"

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')

    # Create summary
    summary = {
        "timestamp": timestamp,
        "total_examples": len(examples),
        "by_type": {
            "classification": len(CLASSIFICATION_EXAMPLES),
            "agent_routing": len(AGENT_ROUTING_EXAMPLES),
            "incident_response": len(INCIDENT_RESPONSE_EXAMPLES),
            "cloud_security": len(CLOUD_SECURITY_EXAMPLES),
            "compliance": len(COMPLIANCE_EXAMPLES),
            "fix_generation": len(FIX_GENERATION_EXAMPLES),
        },
        "output_file": str(output_file),
        "gaps_addressed": [
            "Classification (0% → target 80%)",
            "Incident Response (10% → target 60%)",
            "Cloud Security (20% → target 60%)",
            "Compliance (20% → target 60%)",
            "Fix Generation (0% → target 50%)",
        ]
    }

    summary_file = output_file.with_suffix('.json')
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    return output_file, summary


if __name__ == "__main__":
    print("=" * 60)
    print("JADE Gap Training Data Generator")
    print("=" * 60)

    examples = generate_all_training_data()
    output_file, summary = save_training_data(examples, OUTPUT_DIR)

    print(f"\n✓ Generated {summary['total_examples']} training examples")
    print(f"✓ Saved to: {output_file}")
    print(f"\nBreakdown:")
    for gap_type, count in summary['by_type'].items():
        print(f"  - {gap_type}: {count} examples")

    print(f"\nGaps addressed:")
    for gap in summary['gaps_addressed']:
        print(f"  • {gap}")
