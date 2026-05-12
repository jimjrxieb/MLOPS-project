# Risk Assessment Evidence — SC Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** Evidence collected for all five System and Communications Protection
> controls is incomplete and unverifiable. Control owners provided vague verbal assurances
> with no supporting artifacts. Tool queries returned null or error responses indicating
> network and cryptographic protection tooling is not deployed or not configured. All five
> findings are FAIL; all require POA&M items.

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

**Tool Query:** `GET /evidence/SC-7?env=bad` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "SC-7", "env": "bad", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "vpc_flow_logs_enabled": null,
    "security_groups_open_to_world": null,
    "nacl_default_deny": null,
    "error": "VPC configuration not scanned"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "We have VPCs. Flow logs — I think they're on. Security groups — we have rules
> but I haven't audited them recently. Network Firewall is on the roadmap."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | VPC configuration not scanned; flow logs unconfirmed; security group audit not run |
| Impact | High | Without boundary protection evidence, unauthorized external access paths cannot be ruled out |
| **Residual Risk** | **Critical** | Network boundary posture entirely unverifiable |

**Finding:** FAIL
**Evidence Gap:** VPC configuration not scanned. Flow log status unconfirmed. Security group open-world count unknown. NACL deny status unconfirmed. Network Firewall not deployed.

**BERU Finding:**
```
FINDING: VPC configuration has not been scanned and no boundary protection evidence can be produced for SC-7.
CONTROL: SC-7 — Boundary Protection
ENHANCEMENT: SC-7(5) — Deny by Default / Allow by Exception
STATUS: FAIL
EVIDENCE REVIEWED:
  - SecEng verbal statement (VPCs described, flow logs uncertain, Network Firewall roadmap)
  - Prowler query (VPC not scanned, all fields null)
EVIDENCE GAP: VPC configuration not scanned, flow log status unconfirmed, security group audit not run, NACL deny unconfirmed, Network Firewall not deployed
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: PlatEng (accountability) / SecEng (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Network boundary protection cannot be evidenced. VPC scanning has not been run, flow logs are unconfirmed, and the security group audit has not been performed. Run Prowler to scan VPC configuration and confirm flow log delivery before the next assessment.
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

**Tool Query:** `GET /evidence/SC-8?env=bad` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "SC-8", "env": "bad", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "tls_enforced_on_alb": null,
    "minimum_tls_version": null,
    "http_redirect_to_https": null,
    "error": "Load balancer TLS config not scanned"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "We use HTTPS. TLS version — I'm not sure if 1.3 is enforced or 1.2.
> Certificates are managed — I think ACM handles it. HTTP redirect — might
> be on. I don't have the config in front of me."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | TLS config not scanned; version unknown; HSTS and HTTP redirect unconfirmed |
| Impact | High | Weak or misconfigured TLS allows man-in-the-middle attacks on data in transit |
| **Residual Risk** | **Critical** | Transmission protection entirely unverifiable |

**Finding:** FAIL
**Evidence Gap:** ALB TLS configuration not scanned. Minimum TLS version unknown. HTTP redirect not confirmed. HSTS status unknown. Certificate expiry days not confirmed.

**BERU Finding:**
```
FINDING: Load balancer TLS configuration has not been scanned and transmission confidentiality cannot be confirmed for SC-8.
CONTROL: SC-8 — Transmission Confidentiality and Integrity
ENHANCEMENT: SC-8(1) — Cryptographic Protection
STATUS: FAIL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (HTTPS described, TLS version uncertain, ACM probable)
  - Prowler query (ALB TLS not scanned, all fields null)
EVIDENCE GAP: ALB TLS not scanned, TLS version unknown, HTTP redirect unconfirmed, HSTS status unknown, cert expiry unknown
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Transmission protection cannot be evidenced. The ALB TLS configuration has not been scanned and TLS version enforcement is unknown. Run Prowler and confirm TLS 1.3 enforcement and HSTS before the next assessment.
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

**Tool Query:** `GET /evidence/SC-12?env=bad` — simulates: gitleaks

**Tool Evidence (API Response):**
```json
{
  "control": "SC-12", "env": "bad", "tool": "gitleaks",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "key_material_in_code": null,
    "kms_usage": null,
    "error": "Key management scan not run"
  }
}
```

**Interview Response (Control Owner — CloudSec):**
> "We use KMS. Key rotation — I think it's enabled. I haven't checked recently.
> Key material in code — I hope not. Gitleaks isn't configured yet."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Key management scan not run; key material in code unknown; KMS rotation not confirmed |
| Impact | High | Key material exposure in code is a permanent compromise; rotation gaps mean stale keys protect production data |
| **Residual Risk** | **Critical** | Cryptographic key management entirely unverifiable |

**Finding:** FAIL
**Evidence Gap:** Key management scan not run. Key material in code status unknown. KMS usage not confirmed. Rotation enforcement not confirmed. Terraform key policy not produced.

**BERU Finding:**
```
FINDING: Key management scan has not been run and KMS usage and rotation enforcement cannot be confirmed for SC-12.
CONTROL: SC-12 — Cryptographic Key Establishment and Management
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - CloudSec verbal statement (KMS described, rotation uncertain, Gitleaks not configured)
  - Gitleaks query (key management scan not run, all fields null)
EVIDENCE GAP: Key management scan not run, key material in code status unknown, KMS rotation not confirmed, Terraform key policy not produced
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: CloudSec (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Cryptographic key management cannot be evidenced. Gitleaks is not configured and KMS rotation has not been confirmed. Configure Gitleaks and confirm KMS rotation enforcement before the next assessment.
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

**Tool Query:** `GET /evidence/SC-13?env=bad` — simulates: gitleaks

**Tool Evidence (API Response):**
```json
{
  "control": "SC-13", "env": "bad", "tool": "gitleaks",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "weak_cipher_patterns": null,
    "approved_algorithms": null,
    "error": "Cryptographic protection scan not run"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "We use strong encryption. AES-256 I believe. TLS — should be 1.2 or 1.3.
> I don't have a formal cipher policy document. Gitleaks isn't set up for
> cipher pattern detection."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Cryptographic scan not run; cipher policy not documented; weak cipher pattern count unknown |
| Impact | High | Weak ciphers in production code allow decryption of sensitive data |
| **Residual Risk** | **Critical** | Cryptographic protection posture entirely unverifiable |

**Finding:** FAIL
**Evidence Gap:** Cryptographic scan not run. Weak cipher pattern count unknown. Approved algorithm list not produced. Cipher policy document not available.

**BERU Finding:**
```
FINDING: Cryptographic protection scan has not been run and no cipher policy or approved algorithm list exists for SC-13.
CONTROL: SC-13 — Cryptographic Protection
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - SecEng verbal statement (AES-256 described, TLS version uncertain, no cipher policy)
  - Gitleaks query (cryptographic scan not run, all fields null)
EVIDENCE GAP: Cryptographic scan not run, weak cipher pattern count unknown, approved algorithm list not produced, cipher policy not available
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: SecEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Cryptographic protection cannot be evidenced. No cipher policy document exists and no scan has been run to detect weak cipher usage. Create the cipher policy, run the scan, and confirm minimum TLS 1.3 before the next assessment.
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

**Tool Query:** `GET /evidence/SC-28?env=bad` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "SC-28", "env": "bad", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "s3_buckets_encrypted": null,
    "ebs_volumes_encrypted": null,
    "rds_encrypted": null,
    "error": "Encryption posture scan not available"
  }
}
```

**Interview Response (Control Owner — CloudSec):**
> "Everything should be encrypted. S3 has encryption on — I set it up. EBS —
> most volumes are encrypted. RDS — I'd have to check. I don't have the KMS
> key ARNs in front of me."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Encryption scan not available; S3, EBS, RDS encryption status all unconfirmed; KMS ARNs unknown |
| Impact | Critical | Unencrypted data at rest is exposed if storage media is accessed or exfiltrated |
| **Residual Risk** | **Critical** | Data-at-rest encryption posture entirely unverifiable |

**Finding:** FAIL
**Evidence Gap:** Encryption posture scan not available. S3, EBS, and RDS encryption status all unconfirmed. KMS key ARNs not produced. Secrets Manager encryption not confirmed.

**BERU Finding:**
```
FINDING: Encryption posture scan is not available and S3, EBS, and RDS encryption status cannot be confirmed for SC-28.
CONTROL: SC-28 — Protection of Information at Rest
ENHANCEMENT: SC-28(1) — Cryptographic Protection
STATUS: FAIL
EVIDENCE REVIEWED:
  - CloudSec verbal statement (encryption described for S3, EBS and RDS uncertain)
  - Prowler query (encryption scan not available, all encryption fields null)
EVIDENCE GAP: Encryption scan not available, S3/EBS/RDS status unconfirmed, KMS ARNs not produced, Secrets Manager encryption not confirmed
RISK:
  Likelihood: High
  Impact: Critical
  Residual Risk: Critical
CONTROL OWNER: CloudSec (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Data-at-rest encryption cannot be evidenced. No encryption scan has been run and KMS key ARNs are unknown. Run Prowler to confirm encryption posture for S3, EBS, and RDS before the next assessment.
```
