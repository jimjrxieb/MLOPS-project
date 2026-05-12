# Risk Assessment Evidence — SC Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** Evidence collected is partially sufficient. Control owners named specific
> tools and processes but could not produce exact artifacts, dates, or complete metrics. Tool
> queries returned partial data — some booleans confirmed but key counts and specific values
> absent. All five controls receive PARTIAL findings requiring POA&M items to close the
> evidence gaps before the next audit cycle.

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

**Tool Query:** `GET /evidence/SC-7?env=good` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "SC-7", "env": "good", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "partial",
  "data": {
    "vpc_flow_logs_enabled": true,
    "security_groups_open_to_world": 2,
    "nacl_default_deny": null,
    "note": "Flow logs enabled. 2 SGs with 0.0.0.0/0 ingress — justification not documented"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "VPC flow logs are on. There are 2 security groups with 0.0.0.0/0 ingress —
> one is for the public ALB and one I need to review. NACL — I believe default
> deny is on but I haven't verified it recently. Network Firewall is configured
> but I don't have the rule count."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — VPC flow logs enabled; 2 open-world SGs confirmed; NACL deny status unconfirmed; Network Firewall exists but configuration not produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Flow logs enabled; 2 SGs with 0.0.0.0/0 ingress need justification; NACL status unknown |
| Impact | Medium | One of 2 open-world SGs is unexplained; NACL status gap means default posture is unconfirmed |
| **Residual Risk** | **High** | Partial boundary protection confirmed; open SG and NACL gaps must close |

**Finding:** PARTIAL
**Evidence Gap:** 2 open-world SGs without documented justification. NACL default deny not confirmed. Network Firewall rule count and configuration not produced.

**BERU Finding:**
```
FINDING: VPC flow logs are enabled for SC-7 but 2 open-world SGs are not justified and NACL default deny is not confirmed.
CONTROL: SC-7 — Boundary Protection
ENHANCEMENT: SC-7(5) — Deny by Default / Allow by Exception
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - SecEng verbal statement (flow logs on, 2 SGs described, NACL uncertain, Network Firewall present)
  - Prowler query (vpc_flow_logs true, 2 SGs open-world, nacl_default_deny null)
EVIDENCE GAP: 2 open-world SGs without justification, NACL default deny not confirmed, Network Firewall configuration not produced
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability) / SecEng (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: VPC flow logs are running but 2 open-world security groups need justification and NACL deny posture must be confirmed. Document the SG justifications and confirm NACL configuration to close this finding.
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

**Tool Query:** `GET /evidence/SC-8?env=good` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "SC-8", "env": "good", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "partial",
  "data": {
    "tls_enforced_on_alb": true,
    "minimum_tls_version": "TLSv1.2",
    "http_redirect_to_https": null,
    "note": "TLS 1.2 enforced. HTTP redirect not confirmed on all listeners."
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "TLS is enforced on the ALB. I think it's TLS 1.2 — we haven't upgraded to 1.3
> yet. HTTP redirect — most listeners redirect, but there may be one that doesn't.
> HSTS — I believe it's on via the ALB header. ACM handles certs automatically."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — TLS enforced on ALB; version is 1.2 not the SSP-claimed 1.3; HTTP redirect not confirmed on all listeners; HSTS not confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | TLS enforced but at 1.2 not 1.3; HTTP redirect gap exists; HSTS unconfirmed |
| Impact | Medium | TLS 1.2 has known downgrade vulnerabilities; HTTP listeners may expose cleartext traffic |
| **Residual Risk** | **High** | TLS enforcement confirmed but below SSP claim; upgrade and redirect gaps must close |

**Finding:** PARTIAL
**Evidence Gap:** TLS version is 1.2 not 1.3 as claimed in SSP. HTTP redirect not confirmed on all listeners. HSTS not confirmed. Certificate minimum days before expiry not confirmed.

**BERU Finding:**
```
FINDING: TLS is enforced on ALB at version 1.2 for SC-8 but the SSP claims 1.3; HTTP redirect and HSTS are not confirmed.
CONTROL: SC-8 — Transmission Confidentiality and Integrity
ENHANCEMENT: SC-8(1) — Cryptographic Protection
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (TLS on, 1.2 not 1.3, redirect mostly on, HSTS probable)
  - Prowler query (tls_enforced true, TLSv1.2 not TLSv1.3, http_redirect null)
EVIDENCE GAP: TLS version 1.2 not 1.3 as SSP claims, HTTP redirect not on all listeners, HSTS not confirmed, cert expiry days not confirmed
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: TLS is enforced but at version 1.2 instead of the SSP-claimed 1.3. Upgrade to TLS 1.3, confirm HTTP redirect on all listeners, and enable HSTS to close this finding.
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

**Tool Query:** `GET /evidence/SC-12?env=good` — simulates: gitleaks

**Tool Evidence (API Response):**
```json
{
  "control": "SC-12", "env": "good", "tool": "gitleaks",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:10:00Z", "status": "partial",
  "data": {
    "key_material_in_code": false,
    "kms_usage": true,
    "key_rotation_enforced": null,
    "note": "No raw keys found. KMS used but rotation policy not confirmed."
  }
}
```

**Interview Response (Control Owner — CloudSec):**
> "No key material in code — Gitleaks confirms. KMS is used. Key rotation — I
> believe it's enabled but I haven't checked the specific policy recently.
> The Terraform file for KMS exists but I don't have the exact path."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — no key material in code confirmed; KMS usage confirmed; rotation enforcement not confirmed; Terraform artifact path not produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | No key material in code; KMS in use; rotation enforcement unconfirmed |
| Impact | Medium | Without confirmed rotation, KMS keys could remain unchanged beyond acceptable periods |
| **Residual Risk** | **High** | Key management partially confirmed; rotation and Terraform artifact gaps must close |

**Finding:** PARTIAL
**Evidence Gap:** KMS key rotation enforcement not confirmed. Terraform key policy path not produced. Key-to-data mapping not produced.

**BERU Finding:**
```
FINDING: No key material found in code and KMS is confirmed for SC-12 but rotation enforcement and Terraform artifact are not produced.
CONTROL: SC-12 — Cryptographic Key Establishment and Management
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - CloudSec verbal statement (no key material, KMS confirmed, rotation uncertain, Terraform path unknown)
  - Gitleaks query (key_material_in_code false, kms_usage true, rotation null)
EVIDENCE GAP: KMS key rotation not confirmed, Terraform key policy path not produced, key-to-data mapping not produced
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: CloudSec (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Key management is partially evidenced. Confirm KMS rotation policy is enabled and produce the Terraform key policy path to close this finding.
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

**Tool Query:** `GET /evidence/SC-13?env=good` — simulates: gitleaks

**Tool Evidence (API Response):**
```json
{
  "control": "SC-13", "env": "good", "tool": "gitleaks",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:15:00Z", "status": "partial",
  "data": {
    "weak_cipher_patterns": 1,
    "approved_algorithms": ["AES-256", "RSA-2048"],
    "note": "One deprecated cipher usage found in legacy service"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "We found one weak cipher in a legacy service — it's on the remediation list.
> Approved algorithms are AES-256 and RSA-2048. ECDSA is used somewhere but
> I don't have the full list. The cipher policy is in Confluence but I don't
> have the link."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — approved algorithms partially confirmed; 1 weak cipher found in legacy service; cipher policy location not provided; ECDSA-P256 not confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | 1 weak cipher in production legacy service; cipher policy not linked; ECDSA not confirmed |
| Impact | Medium | Weak cipher in legacy service may be exploited for decryption |
| **Residual Risk** | **High** | Partial cipher compliance; weak cipher remediation and policy location must close |

**Finding:** PARTIAL
**Evidence Gap:** 1 weak cipher pattern in legacy service not remediated. Cipher policy Confluence link not provided. ECDSA-P256 not confirmed. Minimum TLS version 1.3 not confirmed.

**BERU Finding:**
```
FINDING: 1 weak cipher pattern found in legacy service for SC-13; cipher policy link and ECDSA-P256 not confirmed.
CONTROL: SC-13 — Cryptographic Protection
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - SecEng verbal statement (1 weak cipher acknowledged, partial algorithm list, cipher policy location unknown)
  - Gitleaks query (1 weak cipher, AES-256 and RSA-2048 confirmed, note: legacy service)
EVIDENCE GAP: 1 weak cipher unresolved, cipher policy link not provided, ECDSA-P256 not confirmed, TLS 1.3 minimum not confirmed
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: SecEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: One weak cipher in a legacy service must be remediated. Provide the Confluence cipher policy link and confirm ECDSA-P256 and TLS 1.3 minimum enforcement to close this finding.
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

**Tool Query:** `GET /evidence/SC-28?env=good` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "SC-28", "env": "good", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:20:00Z", "status": "partial",
  "data": {
    "s3_buckets_encrypted": true,
    "ebs_volumes_encrypted": null,
    "rds_encrypted": true,
    "note": "S3 and RDS encrypted. EBS encryption status not confirmed."
  }
}
```

**Interview Response (Control Owner — CloudSec):**
> "S3 and RDS are encrypted. EBS — most volumes should be encrypted but I
> haven't run the audit recently. KMS key IDs — I'd have to look them up
> in the console. Secrets Manager — I believe it's using KMS."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — S3 and RDS encryption confirmed; EBS encryption not confirmed; KMS key ARNs not produced; Secrets Manager encryption not confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | S3 and RDS encrypted; EBS status unknown; KMS ARNs not produced |
| Impact | High | Unencrypted EBS volumes would expose data if the volume is accessed outside the instance |
| **Residual Risk** | **High** | Partial encryption confirmed; EBS and KMS ARN gaps must close |

**Finding:** PARTIAL
**Evidence Gap:** EBS volume encryption status not confirmed. KMS key ARNs not produced. Secrets Manager encryption not confirmed.

**BERU Finding:**
```
FINDING: S3 and RDS encryption confirmed for SC-28 but EBS volume encryption status and KMS key ARNs are not produced.
CONTROL: SC-28 — Protection of Information at Rest
ENHANCEMENT: SC-28(1) — Cryptographic Protection
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - CloudSec verbal statement (S3 and RDS encrypted, EBS uncertain, KMS ARNs unknown)
  - Prowler query (s3 encrypted true, ebs null, rds encrypted true)
EVIDENCE GAP: EBS volume encryption status not confirmed, KMS key ARNs not produced, Secrets Manager encryption not confirmed
RISK:
  Likelihood: Medium
  Impact: High
  Residual Risk: High
CONTROL OWNER: CloudSec (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: S3 and RDS encryption are confirmed but EBS is unverified. Run Prowler to confirm EBS encryption status and produce the KMS key ARNs to fully evidence SC-28.
```
