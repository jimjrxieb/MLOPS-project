#!/usr/bin/env python3
"""
Generate comprehensive training data to fill JADE benchmark gaps.

Target: 200+ high-quality examples per critical gap area.
"""

import json
import random
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-GP-GLUE/00-processed/benchmark-training")

# ============================================================
# CLASSIFICATION - RANK SYSTEM (Most Critical Gap: 0%)
# ============================================================

SCANNERS = ["trivy", "checkov", "semgrep", "gitleaks", "kubescape", "falco", "prowler", "guardduty", "snyk", "kube-bench"]
SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

# E-RANK scenarios (fully automated, low risk)
E_RANK_SCENARIOS = [
    {
        "scanner": "trivy",
        "finding": "Outdated package with no CVE",
        "details": "Package lodash@4.17.20 can be updated to 4.17.21. No security vulnerabilities.",
        "rationale": "Informational upgrade with no security impact",
        "agent": "jsa-devsec"
    },
    {
        "scanner": "checkov",
        "finding": "Missing description tag on resource",
        "details": "aws_s3_bucket.backup missing Description tag",
        "rationale": "Cosmetic/documentation issue only",
        "agent": "jsa-infrasec"
    },
    {
        "scanner": "semgrep",
        "finding": "Code style suggestion",
        "details": "Consider using f-strings instead of .format()",
        "rationale": "Non-security code quality suggestion",
        "agent": "jsa-devsec"
    },
    {
        "scanner": "kubescape",
        "finding": "Pod missing recommended labels",
        "details": "Pod test-app missing app.kubernetes.io/version label",
        "rationale": "Best practice but not security critical",
        "agent": "jsa-infrasec"
    },
    {
        "scanner": "trivy",
        "finding": "Development dependency with low CVE",
        "details": "dev-dependency eslint has LOW severity CVE, not in production",
        "rationale": "Dev-only dependency with minimal risk",
        "agent": "jsa-devsec"
    },
]

# D-RANK scenarios (automated with known fix patterns)
D_RANK_SCENARIOS = [
    {
        "scanner": "trivy",
        "finding": "Critical CVE with available fix",
        "details": "express@4.17.0 has CVE-2024-1234 (RCE). Fix: upgrade to 4.18.2",
        "rationale": "Deterministic fix available - dependency upgrade",
        "agent": "jsa-devsec"
    },
    {
        "scanner": "checkov",
        "finding": "S3 bucket without encryption",
        "details": "CKV_AWS_19: aws_s3_bucket.logs missing server-side encryption",
        "rationale": "Standard IaC fix with known remediation pattern",
        "agent": "jsa-infrasec"
    },
    {
        "scanner": "gitleaks",
        "finding": "Hardcoded AWS access key",
        "details": "AWS access key AKIA... detected in config.py:42",
        "rationale": "Hardcoded secret with clear remediation (rotate + remove)",
        "agent": "jsa-devsec"
    },
    {
        "scanner": "semgrep",
        "finding": "SQL injection vulnerability",
        "details": "cursor.execute with string concatenation in api/users.py:78",
        "rationale": "Code fix with well-known parameterized query pattern",
        "agent": "jsa-devsec"
    },
    {
        "scanner": "checkov",
        "finding": "Security group allows all traffic",
        "details": "CKV_AWS_23: ingress from 0.0.0.0/0 on all ports",
        "rationale": "Standard network security fix",
        "agent": "jsa-infrasec"
    },
    {
        "scanner": "trivy",
        "finding": "High CVE in production dependency",
        "details": "axios@0.21.0 has HIGH CVE-2021-3749. Fix: 0.21.2",
        "rationale": "Production dependency with available patch",
        "agent": "jsa-devsec"
    },
    {
        "scanner": "kubescape",
        "finding": "Container running as root",
        "details": "Pod nginx-deployment runs as root (UID 0)",
        "rationale": "Standard security context fix",
        "agent": "jsa-infrasec"
    },
    {
        "scanner": "checkov",
        "finding": "RDS without encryption",
        "details": "CKV_AWS_16: aws_db_instance.main storage not encrypted",
        "rationale": "Standard encryption enablement",
        "agent": "jsa-infrasec"
    },
    {
        "scanner": "semgrep",
        "finding": "XSS vulnerability",
        "details": "Unsanitized output in template at views/user.html:55",
        "rationale": "Known fix pattern - escape output",
        "agent": "jsa-devsec"
    },
    {
        "scanner": "gitleaks",
        "finding": "GitHub personal access token",
        "details": "GitHub token ghp_... in .env.example",
        "rationale": "Secret exposure with clear remediation",
        "agent": "jsa-devsec"
    },
]

# C-RANK scenarios (JADE review needed)
C_RANK_SCENARIOS = [
    {
        "scanner": "kubescape",
        "finding": "Privileged container in production",
        "details": "deployment/nginx-proxy has privileged: true",
        "rationale": "May be required for workload - needs JADE analysis",
        "agent": "jsa-infrasec"
    },
    {
        "scanner": "falco",
        "finding": "Shell spawned in container",
        "details": "Terminal shell /bin/bash in pod/api-server-abc123",
        "rationale": "Could be debugging or compromise - needs investigation",
        "agent": "jsa-monitor"
    },
    {
        "scanner": "checkov",
        "finding": "Lambda with VPC access to RDS",
        "details": "Lambda function has network path to production database",
        "rationale": "May be intentional - architecture review needed",
        "agent": "jsa-infrasec"
    },
    {
        "scanner": "kubescape",
        "finding": "Pod with host network access",
        "details": "daemonset/monitoring uses hostNetwork: true",
        "rationale": "Monitoring may legitimately need host access",
        "agent": "jsa-infrasec"
    },
    {
        "scanner": "falco",
        "finding": "Process writing to /etc",
        "details": "Process in container modified /etc/passwd",
        "rationale": "Suspicious but could be legitimate configuration",
        "agent": "jsa-monitor"
    },
    {
        "scanner": "guardduty",
        "finding": "Unusual API call pattern",
        "details": "User calling AssumeRole across multiple accounts rapidly",
        "rationale": "Could be automation or lateral movement attempt",
        "agent": "jsa-monitor"
    },
    {
        "scanner": "checkov",
        "finding": "IAM role with sts:AssumeRole wildcard",
        "details": "Role can assume any role in account",
        "rationale": "May be deployment role - needs context",
        "agent": "jsa-infrasec"
    },
]

# B-RANK scenarios (Human intervention required)
B_RANK_SCENARIOS = [
    {
        "scanner": "prowler",
        "finding": "Root account without MFA",
        "details": "AWS account root has no MFA configured",
        "rationale": "MFA setup requires physical device/human",
        "agent": "jsa-infrasec"
    },
    {
        "scanner": "guardduty",
        "finding": "Credential compromise indicator",
        "details": "UnauthorizedAccess:IAMUser/MaliciousIPCaller from known bad IP",
        "rationale": "Potential compromise requires human investigation",
        "agent": "jsa-monitor"
    },
    {
        "scanner": "falco",
        "finding": "Potential data exfiltration",
        "details": "Large outbound data transfer to unknown IP",
        "rationale": "Possible breach - human forensics required",
        "agent": "jsa-monitor"
    },
    {
        "scanner": "manual",
        "finding": "Third-party vendor security review",
        "details": "New SaaS vendor requesting API access to production",
        "rationale": "Business decision requiring human judgment",
        "agent": "jsa-infrasec"
    },
    {
        "scanner": "prowler",
        "finding": "Missing CloudTrail in region",
        "details": "No CloudTrail configured in ap-southeast-2",
        "rationale": "Requires AWS organization-level decision",
        "agent": "jsa-infrasec"
    },
    {
        "scanner": "kube-bench",
        "finding": "etcd not encrypted at rest",
        "details": "Kubernetes etcd storage unencrypted (CIS 1.2.32)",
        "rationale": "Cluster-level change with significant impact",
        "agent": "jsa-infrasec"
    },
]

# S-RANK scenarios (Strategic/Human only)
S_RANK_SCENARIOS = [
    {
        "scanner": "manual",
        "finding": "New PCI compliance scope",
        "details": "Payment service handling credit card data needs architecture review",
        "rationale": "Strategic architectural decision",
        "agent": None  # Human architect
    },
    {
        "scanner": "manual",
        "finding": "Security incident post-mortem",
        "details": "Production breach requires RCA and remediation plan",
        "rationale": "Executive-level response required",
        "agent": None
    },
    {
        "scanner": "manual",
        "finding": "Compliance framework selection",
        "details": "Choose between SOC 2 Type I vs Type II certification",
        "rationale": "Business strategy decision",
        "agent": None
    },
    {
        "scanner": "manual",
        "finding": "Zero trust architecture migration",
        "details": "Planning migration from perimeter to zero trust model",
        "rationale": "Multi-year strategic initiative",
        "agent": None
    },
]

def generate_classification_example(rank: str, scenario: dict) -> dict:
    """Generate a classification training example."""
    severity = random.choice(["CRITICAL", "HIGH"] if rank in ["D", "C", "B"] else ["LOW", "INFO"] if rank == "E" else ["CRITICAL"])

    input_text = f"""Scanner: {scenario['scanner']}
Severity: {severity}
Finding: {scenario['finding']}
Details: {scenario['details']}"""

    agent_text = f"**Assigned Agent:** {scenario['agent']}" if scenario['agent'] else "**Assigned Agent:** None (Human architect required)"

    auto_fix = "YES" if rank in ["E", "D"] else "NO"

    output_text = f"""**Classification: {rank}-RANK**

{agent_text}

**Rationale:** This is a {rank}-rank finding because:
{scenario['rationale']}

**Auto-fix:** {auto_fix}"""

    return {
        "instruction": "Classify this security finding and determine the appropriate JSA agent to handle it.",
        "input": input_text,
        "output": output_text
    }


def generate_classification_data(count: int = 150) -> list:
    """Generate classification training examples."""
    examples = []

    # Proportions based on typical distribution
    rank_distribution = [
        ("E", E_RANK_SCENARIOS, 0.15),
        ("D", D_RANK_SCENARIOS, 0.35),
        ("C", C_RANK_SCENARIOS, 0.25),
        ("B", B_RANK_SCENARIOS, 0.20),
        ("S", S_RANK_SCENARIOS, 0.05),
    ]

    for rank, scenarios, proportion in rank_distribution:
        num_examples = int(count * proportion)
        for _ in range(num_examples):
            scenario = random.choice(scenarios)
            examples.append(generate_classification_example(rank, scenario))

    return examples


# ============================================================
# INCIDENT RESPONSE (Critical Gap: 10%)
# ============================================================

IR_SCENARIOS = [
    {
        "type": "cryptomining",
        "alert": "GuardDuty detected cryptomining activity on EC2 instance",
        "response": """**Incident: Cryptojacking**

**Immediate Containment (< 5 min):**
1. Isolate instance: `aws ec2 modify-instance-attribute --instance-id <id> --groups sg-isolated`
2. Stop (don't terminate): `aws ec2 stop-instances --instance-id <id>`
3. Snapshot for forensics

**Investigation:**
- How did attacker gain access? (IMDS? SSH? Application vuln?)
- Check for persistence mechanisms
- Review CloudTrail for lateral movement

**Eradication:**
- Terminate compromised instance
- Deploy from clean AMI
- Rotate all credentials"""
    },
    {
        "type": "data_breach",
        "alert": "Unauthorized S3 access to PII bucket from unknown IP",
        "response": """**Incident: Data Breach**

**Immediate Containment:**
1. Block IP in bucket policy
2. Enable S3 Block Public Access
3. Revoke any leaked credentials

**Investigation:**
- Enumerate all objects accessed (S3 access logs)
- Identify initial access vector
- Determine affected customers

**Regulatory:**
- GDPR: 72-hour notification deadline
- Engage legal counsel immediately
- Preserve evidence chain of custody"""
    },
    {
        "type": "ransomware",
        "alert": "Mass file encryption detected in container",
        "response": """**Incident: Ransomware**

**Immediate Containment:**
1. Network isolate affected pods immediately
2. Preserve encrypted samples for analysis
3. Check for lateral movement indicators

**DO NOT:**
- Pay ransom (no guarantee of decryption)
- Delete encrypted files (may contain recovery data)
- Rebuild without understanding vector

**Recovery:**
- Restore from known-good backups
- Verify backup integrity before restore
- Rebuild from scratch if backup compromised"""
    },
    {
        "type": "credential_compromise",
        "alert": "IAM access key used from malicious IP",
        "response": """**Incident: Credential Compromise**

**Immediate Actions:**
1. DO NOT rotate yet (preserve investigation)
2. Increase logging verbosity
3. Monitor for additional suspicious activity

**Investigation First:**
- What actions were taken with credential?
- Was persistence established?
- Are other credentials compromised?

**After Investigation:**
- Rotate affected credentials
- Enable MFA on affected accounts
- Review IAM policies for over-permission"""
    },
    {
        "type": "supply_chain",
        "alert": "Malicious code injected via compromised CI/CD token",
        "response": """**Incident: Supply Chain Compromise**

**Immediate Containment:**
1. Revoke compromised token immediately
2. Rollback production to last known-good
3. Lock repository with branch protection

**Audit:**
- Review all commits since compromise
- Check for backdoors/persistence
- Identify all affected builds

**Remediation:**
- Require signed commits
- Implement code signing
- Add multi-party approval for releases"""
    },
]

def generate_ir_examples(count: int = 50) -> list:
    """Generate incident response training examples."""
    examples = []

    # Direct scenario examples
    for scenario in IR_SCENARIOS:
        examples.append({
            "instruction": "How should I respond to this security incident?",
            "input": scenario["alert"],
            "output": scenario["response"]
        })

    # Triage process examples
    triage_examples = [
        {
            "instruction": "What are the first steps when triaging a security alert?",
            "input": "I received a GuardDuty alert about unusual API activity.",
            "output": """**Alert Triage Process:**

1. **Validate (2 min):** Is this a known false positive? Is the source reliable?
2. **Scope (5 min):** What resources are affected? Production or dev?
3. **Severity (2 min):** Data sensitivity? Business impact? Spread potential?
4. **Contain (if needed):** If active threat, isolate immediately
5. **Escalate:** E/D → JSA auto. C → JADE review. B/S → Human page."""
        },
        {
            "instruction": "How do I determine the severity of a security incident?",
            "input": "An attacker has accessed one of our staging servers.",
            "output": """**Severity Assessment:**

**Ask These Questions:**
1. Is production affected? (Higher severity)
2. Is customer data accessible? (Higher severity)
3. Can attacker pivot to other systems? (Higher severity)
4. Is the attack ongoing? (Higher urgency)
5. What's the attacker's dwell time? (Longer = more damage)

**Staging Server Assessment:**
- Lower severity if truly isolated
- Check for shared credentials with prod
- Verify network segmentation
- Check for sensitive data in staging"""
        },
    ]
    examples.extend(triage_examples)

    # Containment examples
    containment_examples = [
        {
            "instruction": "How do I contain a compromised Kubernetes pod?",
            "input": "A pod in production appears to be compromised. How do I contain it?",
            "output": """**Pod Containment Steps:**

1. **Network Isolation (Immediate):**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: quarantine-pod
spec:
  podSelector:
    matchLabels:
      app: compromised-app
  policyTypes:
  - Ingress
  - Egress
  egress: []  # Block all outbound
  ingress: []  # Block all inbound
```

2. **Preserve Evidence:**
```bash
kubectl logs <pod> > incident-logs.txt
kubectl exec <pod> -- cat /etc/passwd > passwd-dump.txt
```

3. **Scale Down (don't delete):**
```bash
kubectl scale deployment/<name> --replicas=0
```

4. **DO NOT kubectl delete** - preserves forensic data"""
        },
    ]
    examples.extend(containment_examples)

    return examples


# ============================================================
# CLOUD SECURITY (Gap: 20%)
# ============================================================

CLOUD_EXAMPLES = [
    # AWS IAM
    {
        "instruction": "What is the security risk with this IAM configuration?",
        "input": """IAM Policy:
{
  "Effect": "Allow",
  "Action": "*",
  "Resource": "*"
}""",
        "output": """**Risk: WILDCARD PERMISSIONS - CRITICAL**

This policy grants full access to ALL AWS services and resources.

**Impacts:**
- Credential theft = full account compromise
- Violates least privilege (CIS, SOC2, PCI-DSS)
- Unlimited blast radius

**Fix:**
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject"
  ],
  "Resource": "arn:aws:s3:::my-bucket/*"
}
```

Use specific actions and specific resources."""
    },
    {
        "instruction": "What is the security risk with this IAM configuration?",
        "input": """Trust Policy allows any account to assume role:
{
  "Effect": "Allow",
  "Principal": {"AWS": "*"},
  "Action": "sts:AssumeRole"
}""",
        "output": """**Risk: OPEN TRUST POLICY - CRITICAL**

Any AWS account can assume this role, including attackers.

**Fix:**
```json
{
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
  "Action": "sts:AssumeRole",
  "Condition": {
    "StringEquals": {
      "sts:ExternalId": "unique-secret-id"
    }
  }
}
```

Always specify trusted principals and use external ID."""
    },
    # AWS Networking
    {
        "instruction": "What is the security risk with this security group?",
        "input": """Security group allows SSH from anywhere:
ingress {
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
}""",
        "output": """**Risk: PUBLIC SSH ACCESS - HIGH**

SSH open to internet enables:
- Brute force attacks
- Credential stuffing
- Exploitation of SSH vulnerabilities

**Fix:**
```hcl
ingress {
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = ["10.0.0.0/8"]  # Internal only
}
```

**Better alternatives:**
1. AWS Systems Manager Session Manager (no ports)
2. Bastion host with MFA
3. VPN connection"""
    },
    {
        "instruction": "What is the difference between Security Groups and NACLs?",
        "input": "When should I use Security Groups vs Network ACLs?",
        "output": """**Security Groups vs NACLs:**

| Feature | Security Groups | NACLs |
|---------|----------------|-------|
| Level | Instance | Subnet |
| State | Stateful | Stateless |
| Rules | Allow only | Allow + Deny |
| Default | Deny all | Allow all |

**Use Security Groups for:**
- Per-instance access control
- Application-level rules
- Most common use cases

**Use NACLs for:**
- Subnet-level blocking
- Explicit deny rules
- Defense in depth"""
    },
    # AWS Data Protection
    {
        "instruction": "What is the security risk with this S3 configuration?",
        "input": """S3 bucket has no encryption:
resource "aws_s3_bucket" "data" {
  bucket = "customer-data-bucket"
  # No encryption configuration
}""",
        "output": """**Risk: UNENCRYPTED DATA AT REST - HIGH**

**Impacts:**
- Data exposure if bucket misconfigured
- Compliance violation (PCI, HIPAA, SOC2)
- No protection against physical access

**Fix:**
```hcl
resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.main.arn
    }
  }
}
```

Use KMS for key management and audit trail."""
    },
    {
        "instruction": "What is the security risk with this RDS configuration?",
        "input": """RDS instance is publicly accessible:
resource "aws_db_instance" "main" {
  publicly_accessible = true
}""",
        "output": """**Risk: PUBLIC DATABASE - CRITICAL**

Database exposed to:
- SQL injection from anywhere
- Brute force authentication
- Data exfiltration

**Fix:**
```hcl
resource "aws_db_instance" "main" {
  publicly_accessible = false
  db_subnet_group_name = aws_db_subnet_group.private.name
  vpc_security_group_ids = [aws_security_group.db.id]
}
```

Place in private subnet, restrict to app servers only."""
    },
]

def generate_cloud_examples(count: int = 50) -> list:
    """Generate cloud security training examples."""
    return CLOUD_EXAMPLES * (count // len(CLOUD_EXAMPLES) + 1)


# ============================================================
# COMPLIANCE (Gap: 20%)
# ============================================================

COMPLIANCE_EXAMPLES = [
    # CIS
    {
        "instruction": "What CIS control does this finding violate?",
        "input": "CIS AWS 2.1.1: S3 bucket access logging is not enabled",
        "output": """**CIS Control 2.1.1:** S3 Bucket Access Logging

**Requirement:** All S3 buckets must have access logging enabled.

**Why:** Audit trail for security investigations and compliance.

**Fix:**
```hcl
resource "aws_s3_bucket_logging" "main" {
  bucket        = aws_s3_bucket.main.id
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "s3-access/"
}
```

**Maps to:** SOC 2 CC6.1, PCI-DSS 10.2, NIST AU-2"""
    },
    {
        "instruction": "What CIS control does this finding violate?",
        "input": "CIS AWS 1.4: Root account has no MFA enabled",
        "output": """**CIS Control 1.4:** Root Account MFA

**Requirement:** Root account must have MFA enabled.

**Why:** Root has unrestricted access - MFA prevents credential compromise.

**Manual Steps:**
1. Log into AWS Console as root
2. IAM → Security Credentials
3. Assign MFA device (virtual or hardware)
4. Store backup codes securely

**Note:** Cannot be automated - requires human action."""
    },
    # SOC 2
    {
        "instruction": "How do I meet SOC 2 encryption requirements?",
        "input": "Auditor asking about encryption at rest for SOC 2 Type II",
        "output": """**SOC 2 CC6.1:** Logical and Physical Access Controls

**Encryption Requirements:**
1. **S3:** SSE-KMS enabled
2. **RDS:** Storage encryption enabled
3. **EBS:** Default encryption enabled
4. **DynamoDB:** Encryption enabled

**Evidence for auditor:**
- AWS Config rules showing compliance
- KMS key policies
- Encryption status screenshots

**Terraform for S3:**
```hcl
resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}
```"""
    },
    # PCI-DSS
    {
        "instruction": "What PCI-DSS requirement does this violate?",
        "input": "Credit card data stored in plain text in database",
        "output": """**PCI-DSS Requirement 3.4:** Render PAN unreadable

**Requirement:** Primary Account Numbers (PAN) must be rendered unreadable anywhere stored.

**Acceptable Methods:**
1. Strong one-way hash (SHA-256 minimum)
2. Truncation (keep only last 4 digits)
3. Index tokens
4. Strong encryption with key management

**Fix:**
```python
# Use tokenization service
from stripe import Token
token = stripe.Token.create(card=card_data)
# Store token.id, not raw card data
```

**Never store:** Full PAN, CVV, PIN, magnetic stripe data"""
    },
    # NIST
    {
        "instruction": "What NIST control addresses logging requirements?",
        "input": "We need to implement audit logging for administrative actions.",
        "output": """**NIST 800-53 AU-2:** Audit Events

**Requirement:** System must be capable of auditing defined events.

**AWS Implementation:**
1. **CloudTrail:** All API calls
2. **CloudWatch Logs:** Application events
3. **VPC Flow Logs:** Network traffic
4. **S3 Access Logs:** Object access

**Retention:** 1 year minimum (AU-11)

**Related Controls:**
- AU-3: Content of audit records
- AU-6: Audit review and analysis
- AU-9: Protection of audit information"""
    },
]

def generate_compliance_examples(count: int = 50) -> list:
    """Generate compliance training examples."""
    return COMPLIANCE_EXAMPLES * (count // len(COMPLIANCE_EXAMPLES) + 1)


# ============================================================
# MAIN GENERATOR
# ============================================================

def main():
    print("=" * 60)
    print("Comprehensive JADE Gap Training Data Generator")
    print("=" * 60)

    all_examples = []

    # Classification (most critical - 0%)
    print("\n[1/4] Generating classification examples...")
    classification = generate_classification_data(150)
    all_examples.extend(classification)
    print(f"  ✓ {len(classification)} classification examples")

    # Incident Response (10%)
    print("\n[2/4] Generating incident response examples...")
    ir = generate_ir_examples(50)
    all_examples.extend(ir)
    print(f"  ✓ {len(ir)} incident response examples")

    # Cloud Security (20%)
    print("\n[3/4] Generating cloud security examples...")
    cloud = generate_cloud_examples(50)
    all_examples.extend(cloud)
    print(f"  ✓ {len(cloud)} cloud security examples")

    # Compliance (20%)
    print("\n[4/4] Generating compliance examples...")
    compliance = generate_compliance_examples(50)
    all_examples.extend(compliance)
    print(f"  ✓ {len(compliance)} compliance examples")

    # Shuffle and save
    random.shuffle(all_examples)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"comprehensive_gap_training_{timestamp}.jsonl"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        for example in all_examples:
            f.write(json.dumps(example) + '\n')

    # Summary
    summary = {
        "timestamp": timestamp,
        "total_examples": len(all_examples),
        "breakdown": {
            "classification": len(classification),
            "incident_response": len(ir),
            "cloud_security": len(cloud),
            "compliance": len(compliance),
        },
        "output_file": str(output_file),
    }

    summary_file = output_file.with_suffix('.json')
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"✓ Generated {len(all_examples)} total training examples")
    print(f"✓ Saved to: {output_file}")
    print(f"\nBreakdown by gap area:")
    for area, count in summary['breakdown'].items():
        print(f"  • {area}: {count}")


if __name__ == "__main__":
    main()
