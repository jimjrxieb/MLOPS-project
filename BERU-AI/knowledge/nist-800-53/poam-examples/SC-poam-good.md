# POA&M — System and Communications Protection (SC) Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** POA&M items reflect specific evidence gaps from the BERU assessment.
> Control owners are identified by role. Due dates follow severity-based priority tiers.
> Milestones cover M1 and M2 with actionable steps. Validation commands are real tool queries.
> Residual risk is acknowledged but remains generic. Status history includes opening reason.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** SC-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-032 | SC-7 — Boundary Protection | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-033 | SC-8 — Transmission Confidentiality and Integrity | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-034 | SC-12 — Cryptographic Key Establishment and Management | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-035 | SC-13 — Cryptographic Protection | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-036 | SC-28 — Protection of Information at Rest | Critical | P1 Immediate | 2026-05-17 |

---

## POAM-2026-05-032 — SC-7

```text
POAM-ID:          POAM-2026-05-032
CONTROL:          SC-7 — Boundary Protection

WEAKNESS:
  VPC configuration has not been scanned and no boundary protection evidence can be produced
  for SC-7. Flow log status is unconfirmed, security group audit has not been run, NACL deny
  rules are unconfirmed, and Network Firewall has not been deployed. PlatEng could not provide
  any artifact substantiating SSP assertions about boundary enforcement.

SYSTEM AFFECTED:  AWS VPC / Security Groups / Network ACLs / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SC-7?env=bad → prowler, status: insufficient,
                  vpc_flow_logs: unconfirmed, sg_audit: not run, nacl_deny: unconfirmed

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SC-7-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability) / SecEng (evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Run Prowler vpc_flow_logs_enabled and ec2_securitygroup_default_restrict_traffic
                  checks; export results JSON to evidence path; confirm VPC flow logs are active
                  in all regions.
  M2: 2026-05-15  Audit security group rules to confirm default SG restricts all traffic;
                  confirm NACL deny rules are in place; document Network Firewall deployment
                  plan or compensating control.

REMEDIATION APPROACH:
  Install Prowler and run the VPC and security group check suite against the AWS account.
  Export findings as JSON to the evidence path. Enable VPC flow logs for all VPCs in us-east-1
  and confirm logs are reaching the designated S3 bucket or CloudWatch log group. Audit the
  default security group in each VPC and verify it denies all inbound and outbound traffic.
  Confirm NACL rules include explicit deny entries. Document the Network Firewall deployment
  plan or produce a written compensating control if deployment is out of scope.

VALIDATION COMMAND:
  prowler aws -c vpc_flow_logs_enabled ec2_securitygroup_default_restrict_traffic --output-formats json | jq '[.[] | select(.status=="FAIL")] | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — VPC configuration not scanned; no boundary protection evidence produced
```

---

## POAM-2026-05-033 — SC-8

```text
POAM-ID:          POAM-2026-05-033
CONTROL:          SC-8 — Transmission Confidentiality and Integrity

WEAKNESS:
  Load balancer TLS configuration has not been scanned and transmission confidentiality cannot
  be confirmed for SC-8. ALB TLS version is unknown, HTTP-to-HTTPS redirect is unconfirmed,
  HSTS status is unknown, and certificate expiry has not been checked. PlatEng could not
  produce any TLS configuration artifact.

SYSTEM AFFECTED:  AWS ALB / ELB / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SC-8?env=bad → prowler, status: insufficient,
                  alb_tls: not scanned, tls_version: unknown, http_redirect: unconfirmed

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SC-8-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Run Prowler elb_ssl_listeners and elbv2_ssl_listeners checks; export results
                  JSON to evidence path; identify any listener not enforcing TLS 1.2 or higher.
  M2: 2026-05-15  Configure HTTP-to-HTTPS redirect on all ALB listeners; confirm HSTS header
                  is present in responses; verify no certificate is within 30 days of expiry.

REMEDIATION APPROACH:
  Run Prowler ELB and ALBv2 TLS checks against the AWS account. Export findings to the evidence
  path. Reconfigure any ALB listener accepting HTTP traffic to redirect to HTTPS. Set the TLS
  security policy to ELBSecurityPolicy-TLS13-1-2-2021-06 or equivalent on all HTTPS listeners.
  Add the Strict-Transport-Security header with max-age=31536000 to the ALB response headers
  policy. Use AWS Certificate Manager to review certificate expiry dates and enable auto-renewal.

VALIDATION COMMAND:
  prowler aws -c elb_ssl_listeners elbv2_ssl_listeners --output-formats json | jq '[.[] | select(.status=="FAIL")] | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — ALB TLS configuration not scanned; no transmission confidentiality evidence
```

---

## POAM-2026-05-034 — SC-12

```text
POAM-ID:          POAM-2026-05-034
CONTROL:          SC-12 — Cryptographic Key Establishment and Management

WEAKNESS:
  Key management scan has not been run and KMS usage and rotation enforcement cannot be confirmed
  for SC-12. Key material in source code status is unknown, KMS automatic rotation is not
  confirmed, and no Terraform key policy artifact has been produced. CloudSec could not provide
  any key management evidence.

SYSTEM AFFECTED:  AWS KMS / Links-Matrix source repositories

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SC-12?env=bad → gitleaks, status: insufficient,
                  key_material_in_code: unknown, kms_rotation: unconfirmed

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SC-12-2026-05-10/

REMEDIATION OWNER: CloudSec (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Run gitleaks on all Links-Matrix repositories; export report JSON to evidence
                  path; confirm no AWS access keys or KMS key material are present in source code.
  M2: 2026-05-15  Enable automatic rotation on all customer-managed KMS keys; produce Terraform
                  aws_kms_key resource artifact confirming enable_key_rotation=true for each key.

REMEDIATION APPROACH:
  Run gitleaks in detect mode across all Links-Matrix source repositories to identify any
  committed key material. Export the report JSON to the evidence path and remediate any
  findings by rotating exposed keys and removing secrets from history. For KMS, run
  aws kms list-keys and check rotation status on each customer-managed key. Enable automatic
  annual rotation via the KMS console or Terraform. Produce the Terraform aws_kms_key resource
  definitions as policy artifacts and store them in the evidence path.

VALIDATION COMMAND:
  gitleaks detect --source . --no-git --report-format json --report-path /tmp/sc12-report.json; jq '. | length' /tmp/sc12-report.json

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Key management scan not run; no KMS rotation or code-secret evidence produced
```

---

## POAM-2026-05-035 — SC-13

```text
POAM-ID:          POAM-2026-05-035
CONTROL:          SC-13 — Cryptographic Protection

WEAKNESS:
  Cryptographic protection scan has not been run and no cipher policy or approved algorithm list
  exists for SC-13. Weak cipher pattern count is unknown, an approved algorithm list has not been
  produced, and no cipher policy document is available. SecEng could not confirm the cryptographic
  standards in use.

SYSTEM AFFECTED:  Links-Matrix source repositories / application layer

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SC-13?env=bad → gitleaks, status: insufficient,
                  weak_cipher_count: unknown, approved_algorithm_list: not produced

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SC-13-2026-05-10/

REMEDIATION OWNER: SecEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Run gitleaks on all Links-Matrix repositories to detect weak cipher patterns
                  and hardcoded cryptographic keys; export report JSON to evidence path.
  M2: 2026-05-15  Produce the approved algorithm list (AES-256, RSA-2048+, SHA-256+, TLS 1.2+)
                  as a policy document; store in Confluence and link from evidence path.

REMEDIATION APPROACH:
  Run gitleaks across all Links-Matrix source repositories to detect references to weak ciphers
  (MD5, SHA1, DES, RC4) and hardcoded cryptographic keys. Export findings to the evidence path
  and remediate each occurrence. Produce a cipher policy document that specifies approved
  algorithms (AES-256 for symmetric encryption, RSA-2048 minimum for asymmetric, SHA-256
  minimum for hashing, TLS 1.2 minimum for transport). Store the policy in Confluence and
  obtain SecEng sign-off. Wire a Semgrep rule to the CI pipeline to block new commits
  introducing banned cipher usage.

VALIDATION COMMAND:
  gitleaks detect --source . --report-format json --report-path /tmp/sc13-report.json; jq '. | length' /tmp/sc13-report.json

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Cryptographic scan not run; no cipher policy or approved algorithm list produced
```

---

## POAM-2026-05-036 — SC-28

```text
POAM-ID:          POAM-2026-05-036
CONTROL:          SC-28 — Protection of Information at Rest

WEAKNESS:
  Encryption posture scan is not available and S3, EBS, and RDS encryption status cannot be
  confirmed for SC-28. KMS ARNs have not been produced, Secrets Manager encryption is not
  confirmed, and no at-rest encryption policy document exists. CloudSec could not produce any
  encryption evidence.

SYSTEM AFFECTED:  AWS S3 / EBS / RDS / Secrets Manager / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SC-28?env=bad → prowler, status: insufficient,
                  s3_encryption: unconfirmed, ebs_encryption: unconfirmed, rds_encryption: unconfirmed

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SC-28-2026-05-10/

REMEDIATION OWNER: CloudSec (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Run Prowler s3_bucket_default_encryption and kms_key_rotation_enabled checks;
                  export results JSON to evidence path; identify any unencrypted S3 bucket or
                  KMS key without rotation enabled.
  M2: 2026-05-15  Enable default encryption on all S3 buckets using KMS CMK; confirm EBS volumes
                  and RDS instances are encrypted; verify Secrets Manager secrets use KMS CMK
                  encryption and export KMS ARNs to evidence path.

REMEDIATION APPROACH:
  Run Prowler S3 and KMS encryption checks against the AWS account. Export findings to the
  evidence path. Enable default S3 bucket encryption using a KMS CMK for all buckets. For
  EBS, enable account-level encryption by default via the EC2 console. For RDS, verify
  encryption-at-rest is enabled on all instances and enable it on any unencrypted instance
  via a snapshot-and-restore operation. For Secrets Manager, confirm each secret uses a KMS
  CMK rather than the default AWS managed key. Export the KMS ARN list as a JSON artifact
  to the evidence path.

VALIDATION COMMAND:
  prowler aws -c s3_bucket_default_encryption kms_key_rotation_enabled --output-formats json | jq '[.[] | select(.status=="FAIL")] | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Encryption scan not available; S3/EBS/RDS/Secrets Manager status unconfirmed
```
