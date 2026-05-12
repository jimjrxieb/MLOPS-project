# Risk Assessment Evidence — SC Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Evidence collected fully supports all SSP claims. Control owners provided
> exact artifacts, dates, version numbers, and metrics on first request. Tool queries returned
> complete structured data with no gaps. Every SSP claim is traceable to a specific artifact
> with a retrievable location. All five controls receive PASS findings. No POA&M items required.
> This is the evidence standard a 3PAO expects to walk in and find.

**Assessment Date:** 2026-05-10
**Assessor:** GRC Engineer (grc-engineer group — read-only)
**Framework:** NIST 800-53 Rev 5
**Graded Against:** Links-Matrix SSP (see ssp-examples/SC-ssp-great.md)

---

## SC-7 — Boundary Protection

**Control Owner:** PlatEng
**Evidence Producer:** SecEng
**Cadence:** Continuous

### SSP Claim
> The SSP asserts that VPC flow logs are enabled and delivered to S3. Security groups have
> 0 open-world ingress rules. NACL default deny is configured. AWS Network Firewall and
> Kyverno NetworkPolicy admission enforcement provide layered boundary controls.

### Evidence Request

**Interview — Questions asked of control owner (SecEng):**
1. Show me VPC flow logs and security group audit.
2. Show me your network boundary controls.

**Tool Query:** `GET /evidence/SC-7?env=great` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "SC-7", "env": "great", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "sufficient",
  "data": {
    "vpc_flow_logs_enabled": true,
    "vpc_flow_log_destination": "s3://links-matrix-vpc-flows/",
    "security_groups_open_to_world": 0,
    "nacl_default_deny": true,
    "waf_enabled": true,
    "network_policy_enforced": true,
    "boundary_controls": ["AWS Network Firewall", "Kyverno NetworkPolicy admission"]
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "VPC flow logs enabled — destination is s3://links-matrix-vpc-flows/, aggregated
> every 1 minute. 0 security groups with 0.0.0.0/0 ingress — confirmed by last
> Prowler run. NACL default deny is on for all production subnets. AWS Network
> Firewall is deployed in the inspection VPC. Kyverno NetworkPolicy admission
> policy is network-policy-enforce.yaml in platform-gitops."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — VPC flow logs to S3 confirmed; 0 open-world SGs; NACL default deny; AWS Network Firewall; Kyverno NetworkPolicy admission

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 0 open-world SGs; NACL default deny; Network Firewall in inspection VPC; Kyverno admission |
| Impact | Low | Layered boundary controls with flow logging; S3 destination for audit trail |
| **Residual Risk** | **Low** | All SSP claims verified by Prowler data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 0 open-world SGs, NACL default deny, VPC flow logs to S3, AWS Network Firewall, and Kyverno admission confirmed for SC-7.
CONTROL: SC-7 — Boundary Protection
ENHANCEMENT: SC-7(5) — Deny by Default / Allow by Exception
STATUS: PASS
EVIDENCE REVIEWED:
  - SecEng interview (flow log destination, SG count, NACL status, Network Firewall VPC, Kyverno policy name produced)
  - Prowler query (flow logs to s3://links-matrix-vpc-flows/, 0 open-world SGs, NACL deny, Network Firewall, Kyverno)
  - Flow log destination: s3://links-matrix-vpc-flows/
  - Boundary controls: AWS Network Firewall (inspection VPC) + Kyverno network-policy-enforce.yaml
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: PlatEng (accountability) / SecEng (evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Network boundary protection is fully implemented. Zero open-world security groups, NACL default deny, AWS Network Firewall, and Kyverno admission control provide layered boundary enforcement. This control is audit-ready.
```

---

## SC-8 — Transmission Confidentiality and Integrity

**Control Owner:** PlatEng
**Evidence Producer:** PlatEng
**Cadence:** Continuous; annual cert audit

### SSP Claim
> The SSP asserts that TLS 1.3 is enforced on all ALBs with HTTP-to-HTTPS redirect.
> HSTS is enabled. ACM certificates auto-renew with at least 47 days before expiry.
> Istio mTLS is in STRICT mode for all service-to-service communication.

### Evidence Request

**Interview — Questions asked of control owner (PlatEng):**
1. Show me TLS version enforcement and certificate management.

**Tool Query:** `GET /evidence/SC-8?env=great` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "SC-8", "env": "great", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "sufficient",
  "data": {
    "tls_enforced_on_alb": true,
    "minimum_tls_version": "TLSv1.3",
    "http_redirect_to_https": true,
    "hsts_enabled": true,
    "cert_expiry_days_min": 47,
    "acm_cert_auto_renew": true,
    "istio_mtls_mode": "STRICT"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "TLS 1.3 enforced on all ALBs — confirmed by last Prowler run. HTTP-to-HTTPS
> redirect on all listeners. HSTS enabled via ALB response header policy. ACM
> auto-renews — minimum cert expiry is 47 days before auto-renew triggers. Istio
> mTLS is STRICT — PeerAuthentication policy is in platform-gitops/policies/ia/
> peer-authentication-strict.yaml."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — TLS 1.3 on all ALBs; HTTP redirect; HSTS; ACM auto-renew; 47-day minimum; Istio mTLS STRICT

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | TLS 1.3 enforced; HTTP redirect on all listeners; HSTS enabled; mTLS STRICT for service-to-service |
| Impact | Low | Strongest available TLS version; automated certificate management prevents expiry; mTLS at service mesh layer |
| **Residual Risk** | **Low** | All SSP claims verified by Prowler data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: TLS 1.3 enforced on all ALBs, HTTP redirect, HSTS, ACM auto-renew, and Istio mTLS STRICT confirmed for SC-8.
CONTROL: SC-8 — Transmission Confidentiality and Integrity
ENHANCEMENT: SC-8(1) — Cryptographic Protection
STATUS: PASS
EVIDENCE REVIEWED:
  - PlatEng interview (TLS version, redirect status, HSTS, ACM config, Istio policy path produced)
  - Prowler query (TLSv1.3, http_redirect true, HSTS true, cert_expiry 47 days min, ACM auto-renew, STRICT mTLS)
  - Istio mTLS policy: platform-gitops/policies/ia/peer-authentication-strict.yaml
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Transmission confidentiality is fully implemented. TLS 1.3 on all ALBs, HTTP redirect, HSTS, ACM auto-renewal, and Istio mTLS STRICT. This control is audit-ready.
```

---

## SC-12 — Cryptographic Key Establishment and Management

**Control Owner:** CloudSec
**Evidence Producer:** CloudSec
**Cadence:** Continuous (rotation schedule)

### SSP Claim
> The SSP asserts that no key material exists in code — confirmed by Gitleaks. All data
> is encrypted using AWS KMS. Key rotation is enforced with an annual rotation period.
> Key policy is defined in terraform/kms/keys.tf.

### Evidence Request

**Interview — Questions asked of control owner (CloudSec):**
1. Show me KMS key rotation policy and which keys protect which data.

**Tool Query:** `GET /evidence/SC-12?env=great` — simulates: gitleaks

**Tool Evidence (API Response):**
```json
{
  "control": "SC-12", "env": "great", "tool": "gitleaks",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:10:00Z", "status": "sufficient",
  "data": {
    "key_material_in_code": false,
    "kms_usage": true,
    "key_rotation_enforced": true,
    "rotation_period_days": 365,
    "kms_key_policy": "terraform/kms/keys.tf",
    "hardware_hsm": false
  }
}
```

**Interview Response (Control Owner — CloudSec):**
> "0 key material in code — Gitleaks confirms. All data encrypted with AWS KMS.
> Rotation: 365-day annual rotation enforced — confirmed by KMS key metadata.
> Key policy is in terraform/kms/keys.tf — one key per data classification level.
> Data-key mapping: S3 → lm-s3-key, RDS → lm-rds-key, Secrets Manager → lm-sm-key,
> EBS → lm-ebs-key."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 0 key material in code; KMS confirmed; annual rotation enforced; Terraform policy artifact named; key-to-data mapping produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 0 key material in code; KMS with 365-day rotation; Terraform-managed key policies |
| Impact | Low | Separate keys per data classification; automated rotation; Terraform audit trail |
| **Residual Risk** | **Low** | All SSP claims verified by Gitleaks data and Terraform artifact |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 0 key material in code, KMS with 365-day rotation, Terraform policy artifact, and key-to-data mapping confirmed for SC-12.
CONTROL: SC-12 — Cryptographic Key Establishment and Management
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - CloudSec interview (0 key material, KMS usage, rotation period, Terraform path, key-to-data mapping produced)
  - Gitleaks query (key_material_in_code false, kms_usage true, rotation_period 365 days, Terraform policy)
  - KMS key policy: terraform/kms/keys.tf
  - Key mapping: lm-s3-key, lm-rds-key, lm-sm-key, lm-ebs-key
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: CloudSec (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Cryptographic key management is fully implemented. Zero key material in code, KMS with 365-day rotation, separate keys per data classification, and Terraform-managed policies. This control is audit-ready.
```

---

## SC-13 — Cryptographic Protection

**Control Owner:** SecEng
**Evidence Producer:** SecEng
**Cadence:** Annual cipher suite audit

### SSP Claim
> The SSP asserts that approved algorithms are AES-256-GCM, RSA-2048, and ECDSA-P256.
> Minimum TLS version is 1.3. Zero weak cipher patterns exist in code — confirmed by
> Gitleaks. The cipher suite policy is documented in Confluence: sc13-cipher-policy-v2.md.

### Evidence Request

**Interview — Questions asked of control owner (SecEng):**
1. Show me your approved cipher suite list and where it is enforced.

**Tool Query:** `GET /evidence/SC-13?env=great` — simulates: gitleaks

**Tool Evidence (API Response):**
```json
{
  "control": "SC-13", "env": "great", "tool": "gitleaks",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:15:00Z", "status": "sufficient",
  "data": {
    "weak_cipher_patterns": 0,
    "approved_algorithms": ["AES-256-GCM", "RSA-2048", "ECDSA-P256"],
    "tls_min_version": "1.3",
    "fips_mode": false,
    "cipher_suite_policy": "Confluence: sc13-cipher-policy-v2.md"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "0 weak cipher patterns — Gitleaks confirms. Approved algorithms: AES-256-GCM,
> RSA-2048, ECDSA-P256. Minimum TLS 1.3 enforced via ALB security policy
> ELBSecurityPolicy-TLS13-1-2-2021-06. Cipher suite policy is at Confluence:
> sc13-cipher-policy-v2.md, reviewed 2026-03-01."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 0 weak cipher patterns; all three approved algorithms confirmed; TLS 1.3 minimum; cipher policy named with review date

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 0 weak ciphers in code; all three approved algorithms confirmed; TLS 1.3 minimum enforced |
| Impact | Low | Cipher policy documented and reviewed; ALB security policy enforces at load balancer level |
| **Residual Risk** | **Low** | All SSP claims verified by Gitleaks data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 0 weak cipher patterns, all three approved algorithms, TLS 1.3 minimum, and cipher policy document confirmed for SC-13.
CONTROL: SC-13 — Cryptographic Protection
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - SecEng interview (0 weak ciphers, algorithm list, TLS min version, ALB policy name, cipher policy location produced)
  - Gitleaks query (0 weak_cipher_patterns, AES-256-GCM/RSA-2048/ECDSA-P256, TLS 1.3, cipher policy in Confluence)
  - Cipher suite policy: Confluence: sc13-cipher-policy-v2.md (reviewed 2026-03-01)
  - ALB enforcement: ELBSecurityPolicy-TLS13-1-2-2021-06
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: SecEng (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Cryptographic protection is fully evidenced. Zero weak ciphers, approved algorithm list documented, TLS 1.3 minimum enforced at ALB, and cipher policy current. This control is audit-ready.
```

---

## SC-28 — Protection of Information at Rest

**Control Owner:** CloudSec
**Evidence Producer:** CloudSec
**Cadence:** Continuous

### SSP Claim
> The SSP asserts that all S3 buckets use SSE-KMS encryption, all EBS volumes are encrypted,
> all RDS instances are encrypted with a specific KMS key ARN, and AWS Secrets Manager uses
> KMS. KMS key rotation is enabled.

### Evidence Request

**Interview — Questions asked of control owner (CloudSec):**
1. Show me encryption-at-rest status for S3, EBS, and RDS.
2. Show me KMS key IDs.

**Tool Query:** `GET /evidence/SC-28?env=great` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "SC-28", "env": "great", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:20:00Z", "status": "sufficient",
  "data": {
    "s3_buckets_encrypted": true,
    "s3_encryption_type": "SSE-KMS",
    "ebs_volumes_encrypted": true,
    "rds_encrypted": true,
    "rds_kms_key_id": "arn:aws:kms:us-east-1:123456789012:key/mrk-abc123",
    "secrets_manager_kms": true,
    "kms_key_rotation_enabled": true
  }
}
```

**Interview Response (Control Owner — CloudSec):**
> "All S3 buckets use SSE-KMS — confirmed by Prowler. All EBS volumes encrypted —
> enforced via Terraform aws_ebs_encryption_by_default. All RDS instances encrypted
> with KMS key arn:aws:kms:us-east-1:123456789012:key/mrk-abc123. Secrets Manager
> uses KMS lm-sm-key. KMS key rotation is enabled on all keys — annual rotation."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — S3 SSE-KMS; EBS encrypted; RDS encrypted with KMS ARN confirmed; Secrets Manager KMS; rotation enabled

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | All three data stores encrypted with KMS; rotation enabled; specific key ARNs confirmed |
| Impact | Low | Encrypted by default via Terraform; all data stores covered including Secrets Manager |
| **Residual Risk** | **Low** | All SSP claims verified by Prowler data and KMS configuration |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: S3 SSE-KMS, EBS encrypted, RDS KMS ARN confirmed, Secrets Manager KMS, and key rotation enabled for SC-28.
CONTROL: SC-28 — Protection of Information at Rest
ENHANCEMENT: SC-28(1) — Cryptographic Protection
STATUS: PASS
EVIDENCE REVIEWED:
  - CloudSec interview (S3 SSE-KMS, EBS Terraform default, RDS KMS ARN, Secrets Manager KMS, rotation produced)
  - Prowler query (s3 SSE-KMS, ebs encrypted, rds encrypted, rds KMS ARN, secrets_manager KMS, rotation enabled)
  - RDS KMS key: arn:aws:kms:us-east-1:123456789012:key/mrk-abc123
  - EBS encryption: Terraform aws_ebs_encryption_by_default
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: CloudSec (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Data at rest is fully encrypted. All S3, EBS, RDS, and Secrets Manager resources use KMS encryption with rotation enabled and specific key ARNs confirmed. This control is audit-ready.
```
