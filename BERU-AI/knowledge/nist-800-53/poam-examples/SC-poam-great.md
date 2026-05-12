# POA&M — System and Communications Protection (SC) Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Auditor-ready POA&M. All deficiencies are numbered within each weakness.
> Remediation owners are split between evidence producer and sign-off authority. Due dates
> follow severity-based priority tiers. Milestones include M1, M2, and M3 with exact dated
> actions. Validation commands include expected output. Residual risk identifies the specific
> remaining gap after remediation. Status history shows full progression from OPEN to CLOSED.

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
  Five deficiencies identified on Links-Matrix (AWS VPC / Security Groups / NACLs):
  (1) VPC flow logs not enabled — no traffic visibility or audit trail at the network boundary;
      Prowler vpc_flow_logs_enabled check cannot be satisfied.
  (2) Security group audit not run — default VPC security group restriction status is unknown;
      ec2_securitygroup_default_restrict_traffic check produces no evidence.
  (3) NACL deny rules unconfirmed — no artifact confirms explicit inbound/outbound deny entries
      exist at the subnet boundary.
  (4) Network Firewall not deployed — no IDS/IPS at the VPC perimeter; SSP asserts Network
      Firewall as a boundary control but no deployment record exists.
  (5) No boundary protection evidence package — PlatEng verbal statement only; no JSON scan
      output, no Terraform resource artifact, no architecture diagram produced.

SYSTEM AFFECTED:  Links-Matrix (AWS VPC, Security Groups, NACLs, Network Firewall)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SC-7?env=bad → tool: prowler, status: insufficient,
                  vpc_flow_logs: not enabled, sg_audit: not run, nacl_deny: unconfirmed,
                  network_firewall: not deployed, error: "no boundary protection evidence".
                  PlatEng interview: no scan output or architecture artifact produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SC-7-2026-05-10/SC-7-finding.json

REMEDIATION OWNER: PlatEng (VPC flow logs and SG remediation) / SecEng (NACL and Network Firewall sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Enable VPC flow logs for all VPCs in us-east-1 targeting the designated S3
                  bucket; run Prowler vpc_flow_logs_enabled check and export results JSON to
                  evidence path; confirm flow log records appear within 10 minutes of test traffic.
  M2: 2026-05-14  Audit default security group in each VPC and remove all inbound/outbound rules
                  to enforce deny-all; run Prowler ec2_securitygroup_default_restrict_traffic and
                  export results; confirm NACL rules include explicit deny entries at boundary subnets.
  M3: 2026-05-16  Deploy AWS Network Firewall to the VPC perimeter or produce written compensating
                  control with ISSO sign-off; confirm Prowler vpc_flow_logs_enabled and
                  ec2_securitygroup_default_restrict_traffic both return 0 FAIL results.

REMEDIATION APPROACH:
  Step 1: In AWS Console → VPC → Flow Logs, enable flow logs for each VPC targeting
  s3://links-matrix-flowlogs/. Set filter to ALL traffic and format to Parquet. Confirm by
  running:
    aws ec2 describe-flow-logs --filter Name=resource-id,Values=<vpc-id>
  and verifying FlowLogStatus is ACTIVE.
  Step 2: Run Prowler vpc_flow_logs_enabled to confirm all VPCs have flow logs. For each VPC
  without flow logs, enable immediately. Export results JSON to evidence path.
  Step 3: For each VPC, retrieve the default security group and remove all inbound and outbound
  rules: aws ec2 revoke-security-group-ingress and revoke-security-group-egress. Run Prowler
  ec2_securitygroup_default_restrict_traffic to confirm 0 failures.
  Step 4: Review NACL rules for each subnet boundary. Confirm an explicit deny rule exists as
  the lowest-priority rule for inbound and outbound. Document NACL rule IDs in evidence path.
  Step 5: If Network Firewall deployment is in scope, follow AWS docs to deploy a firewall
  endpoint in the inspection VPC. If out of scope, produce a written compensating control
  document with ISSO sign-off referencing the SG and NACL controls as equivalent boundary
  enforcement.

VALIDATION COMMAND:
  prowler aws -c vpc_flow_logs_enabled ec2_securitygroup_default_restrict_traffic --output-formats json | jq '[.[] | select(.status=="FAIL")] | length'
  Expected output: 0

RESIDUAL RISK AFTER REMEDIATION:
  Network Firewall not deployed — SG and NACL controls provide boundary enforcement but lack
  layer-7 inspection and IDS/IPS capability. Residual risk: Low-Medium pending firewall deployment.

STATUS HISTORY:
  2026-05-10 OPEN — VPC flow logs not enabled. Security group audit not run.
             NACL deny rules unconfirmed. Network Firewall not deployed.
             No boundary protection evidence produced by PlatEng.
  2026-05-12 IN PROGRESS — M1 complete: VPC flow logs enabled in us-east-1.
             Flow log records confirmed within 8 minutes of test traffic.
             Prowler vpc_flow_logs_enabled: 0 FAIL.
  2026-05-14 IN PROGRESS — M2 complete: Default SG rules removed from all VPCs.
             Prowler ec2_securitygroup_default_restrict_traffic: 0 FAIL.
             NACL explicit deny rules confirmed on all boundary subnets.
  2026-05-16 IN PROGRESS — M3 complete: Compensating control document produced
             with ISSO sign-off (Network Firewall deferred to Q3 2026 budget cycle).
  2026-05-17 CLOSED — BERU re-ran GET /evidence/SC-7?env=great → status: sufficient.
             Validation command returned 0. Evidence artifact stored.
```

---

## POAM-2026-05-033 — SC-8

```text
POAM-ID:          POAM-2026-05-033
CONTROL:          SC-8 — Transmission Confidentiality and Integrity

WEAKNESS:
  Five deficiencies identified on Links-Matrix (AWS ALB / ELB):
  (1) ALB TLS not scanned — Prowler elb_ssl_listeners and elbv2_ssl_listeners checks have not
      been run; current TLS configuration is completely unverified.
  (2) TLS version unknown — no evidence confirms listeners enforce TLS 1.2 or higher; SSP
      asserts TLS 1.3 but no listener policy artifact was produced.
  (3) HTTP redirect unconfirmed — no artifact confirms all HTTP listeners redirect to HTTPS;
      cleartext traffic paths may exist.
  (4) HSTS status unknown — no evidence confirms the Strict-Transport-Security header is
      present in ALB responses; browser caching of HTTPS cannot be enforced.
  (5) Certificate expiry unchecked — no ACM certificate expiry review has been performed;
      a certificate within 30 days of expiry would create a service disruption risk.

SYSTEM AFFECTED:  Links-Matrix (AWS ALB, ELB, ACM certificates)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SC-8?env=bad → tool: prowler, status: insufficient,
                  alb_tls: not scanned, tls_version: unknown, http_redirect: unconfirmed,
                  hsts: unknown, cert_expiry: unchecked.
                  PlatEng interview: no TLS configuration artifact produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SC-8-2026-05-10/SC-8-finding.json

REMEDIATION OWNER: PlatEng (ALB configuration and TLS enforcement) / SecEng (cert expiry sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Run Prowler elb_ssl_listeners and elbv2_ssl_listeners checks; export results
                  JSON to evidence path; identify any listener not enforcing TLS 1.2+.
  M2: 2026-05-14  Configure HTTP-to-HTTPS redirect on all ALB listeners; set TLS security policy
                  to ELBSecurityPolicy-TLS13-1-2-2021-06 on all HTTPS listeners; enable HSTS
                  response headers policy on each ALB.
  M3: 2026-05-16  Review ACM certificate expiry dates for all certificates attached to ALBs;
                  confirm auto-renewal is enabled on all; SecEng signs off on certificate inventory
                  artifact stored in evidence path.

REMEDIATION APPROACH:
  Step 1: Run Prowler ELB checks: prowler aws -c elb_ssl_listeners elbv2_ssl_listeners. Export
  JSON results to evidence path. Identify all listeners with FAIL status.
  Step 2: For each ALB with an HTTP listener, add a redirect action to the listener rule:
  Protocol=HTTPS, Port=443, StatusCode=HTTP_301. Confirm via AWS CLI:
    aws elbv2 describe-listeners --load-balancer-arn <arn> | jq '.Listeners[].Protocol'
  Step 3: Update HTTPS listener security policy to ELBSecurityPolicy-TLS13-1-2-2021-06.
  Confirm by checking the SslPolicy field on each listener.
  Step 4: Create an ALB response headers policy with Strict-Transport-Security: max-age=31536000;
  includeSubDomains and attach it to all HTTPS listeners.
  Step 5: Run aws acm list-certificates and check NotAfter for each certificate. Confirm
  RenewalEligibility=ELIGIBLE and HasAdditionalSubjectAlternativeNames confirms full coverage.

VALIDATION COMMAND:
  prowler aws -c elb_ssl_listeners elbv2_ssl_listeners --output-formats json | jq '[.[] | select(.status=="FAIL")] | length'
  Expected output: 0

RESIDUAL RISK AFTER REMEDIATION:
  Internal service-to-service traffic within the VPC not covered by ALB TLS checks — mTLS
  between microservices requires a separate Istio or ACM Private CA implementation.
  Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — ALB TLS not scanned. TLS version unknown. HTTP redirect unconfirmed.
             HSTS status unknown. Certificate expiry unchecked.
  2026-05-12 IN PROGRESS — M1 complete: Prowler ELB checks run.
             3 listeners identified with TLS policy below TLS 1.2.
  2026-05-14 IN PROGRESS — M2 complete: HTTP-to-HTTPS redirect enabled on all ALBs.
             TLS security policy updated to TLS13-1-2-2021-06. HSTS policy attached.
  2026-05-16 IN PROGRESS — M3 complete: ACM certificate inventory reviewed.
             All 7 certificates have auto-renewal enabled. SecEng signed off.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/SC-8?env=great → status: sufficient.
             Validation command returned 0. Evidence artifact stored.
```

---

## POAM-2026-05-034 — SC-12

```text
POAM-ID:          POAM-2026-05-034
CONTROL:          SC-12 — Cryptographic Key Establishment and Management

WEAKNESS:
  Four deficiencies identified on Links-Matrix (AWS KMS / source repositories):
  (1) Key management scan not run — gitleaks has not been executed on any Links-Matrix repository;
      presence of key material in source code is completely unknown.
  (2) Key material in code status unknown — no scan result exists to confirm AWS access keys,
      KMS key IDs, or private key PEM blocks are absent from git history.
  (3) KMS rotation not confirmed — no artifact confirms automatic annual rotation is enabled on
      customer-managed keys; aws kms get-key-rotation-status has not been run.
  (4) Terraform key policy not produced — no aws_kms_key resource definition or key policy JSON
      has been exported as a compliance artifact; SSP assertions about key policy controls are
      unsubstantiated.

SYSTEM AFFECTED:  Links-Matrix (AWS KMS, source repositories, Terraform IaC)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SC-12?env=bad → tool: gitleaks, status: insufficient,
                  key_material_in_code: unknown, kms_rotation: unconfirmed,
                  terraform_key_policy: not produced.
                  CloudSec interview: no key management evidence produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SC-12-2026-05-10/SC-12-finding.json

REMEDIATION OWNER: CloudSec (KMS rotation and Terraform policy) / SecEng (scan sign-off and key revocation)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Run gitleaks detect on all Links-Matrix repositories in no-git mode; export
                  report JSON to evidence path; confirm 0 findings or remediate exposed secrets
                  and rotate affected keys.
  M2: 2026-05-14  Run aws kms list-keys and aws kms get-key-rotation-status for each
                  customer-managed key; enable automatic rotation on any key where it is
                  disabled; export key rotation status JSON to evidence path.
  M3: 2026-05-16  Export Terraform aws_kms_key resource definitions for all customer-managed
                  keys showing enable_key_rotation=true and key_policy JSON; store artifacts
                  in evidence path with CloudSec sign-off.

REMEDIATION APPROACH:
  Step 1: Install gitleaks (latest release from GitHub). Run:
    gitleaks detect --source . --no-git --report-format json --report-path /tmp/sc12-report.json
  across each Links-Matrix repository. Review report for AWS_ACCESS_KEY_ID, private key PEM
  patterns, and KMS key ID patterns. For each finding, rotate the exposed secret immediately,
  remove it from git history using git-filter-repo, and store the report in evidence path.
  Step 2: Run:
    aws kms list-keys | jq -r '.Keys[].KeyId'
  For each key ID, run:
    aws kms get-key-rotation-status --key-id <id>
  Enable rotation on any key returning KeyRotationEnabled=false:
    aws kms enable-key-rotation --key-id <id>
  Export the full rotation status JSON for all keys to evidence path.
  Step 3: From Terraform state, export aws_kms_key resources:
    terraform show -json | jq '.values.root_module.resources[] | select(.type=="aws_kms_key")'
  Store the JSON as a policy artifact in evidence path with CloudSec sign-off.

VALIDATION COMMAND:
  gitleaks detect --source . --no-git --report-format json --report-path /tmp/sc12-report.json; jq '. | length' /tmp/sc12-report.json
  Expected output: 0

RESIDUAL RISK AFTER REMEDIATION:
  KMS key deletion protection is not enforced by SCP — a misconfigured IAM policy could
  schedule key deletion without additional approval. SCP enforcement of kms:ScheduleKeyDeletion
  is a planned follow-on action. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — gitleaks not run. Key material in code status unknown.
             KMS rotation not confirmed. Terraform key policy not produced.
  2026-05-12 IN PROGRESS — M1 complete: gitleaks scan complete across 12 repositories.
             2 findings (stale dev access keys in .env.example files). Keys rotated.
             Files purged from git history. Rescan returned 0 findings.
  2026-05-14 IN PROGRESS — M2 complete: KMS rotation status checked for all 9 CMKs.
             4 keys had rotation disabled. Rotation enabled on all 4. Export stored.
  2026-05-16 IN PROGRESS — M3 complete: Terraform aws_kms_key definitions exported.
             All 9 keys show enable_key_rotation=true. CloudSec signed off.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/SC-12?env=great → status: sufficient.
             Validation command returned 0. Evidence artifact stored.
```

---

## POAM-2026-05-035 — SC-13

```text
POAM-ID:          POAM-2026-05-035
CONTROL:          SC-13 — Cryptographic Protection

WEAKNESS:
  Four deficiencies identified on Links-Matrix (source repositories / application layer):
  (1) Cryptographic scan not run — gitleaks has not been executed to detect weak cipher patterns
      or hardcoded cryptographic secrets in any repository.
  (2) Weak cipher pattern count unknown — no scan result exists to confirm MD5, SHA1, DES, or
      RC4 references are absent from application code.
  (3) Approved algorithm list not produced — no policy document specifying approved algorithms
      (AES-256, RSA-2048+, SHA-256+, TLS 1.2+) has been published or linked from the SSP.
  (4) Cipher policy not available — SecEng could not produce a cipher policy document; no
      Semgrep CI gate blocks future introduction of banned cipher usage.

SYSTEM AFFECTED:  Links-Matrix (source repositories, application layer, CI pipeline)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SC-13?env=bad → tool: gitleaks, status: insufficient,
                  weak_cipher_count: unknown, approved_algorithm_list: not produced,
                  cipher_policy: not available.
                  SecEng interview: no cryptographic evidence produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SC-13-2026-05-10/SC-13-finding.json

REMEDIATION OWNER: SecEng (cipher policy and CI gate) / AppSec (code remediation and scan sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Run gitleaks detect across all Links-Matrix repositories to identify weak
                  cipher patterns and hardcoded cryptographic material; export report JSON to
                  evidence path; confirm finding count or remediate each identified pattern.
  M2: 2026-05-14  Produce the approved algorithm list document (AES-256, RSA-2048+, SHA-256+,
                  TLS 1.2+) in Confluence; obtain SecEng sign-off; link from evidence path
                  and SSP section SC-13.
  M3: 2026-05-16  Wire Semgrep rule p/cryptography to the CI pipeline to block merges
                  introducing banned cipher usage; confirm gate rejects a test commit using MD5;
                  export CI configuration as artifact to evidence path.

REMEDIATION APPROACH:
  Step 1: Run gitleaks:
    gitleaks detect --source . --report-format json --report-path /tmp/sc13-report.json
  Review report for patterns matching MD5, SHA1, DES, RC4, or hardcoded key material.
  For each finding, replace the weak cipher with an approved algorithm (SHA-256 for MD5/SHA1,
  AES-256 for DES, TLS 1.2+ for RC4) and remove secrets from git history.
  Step 2: SecEng drafts the cipher policy document in Confluence. Minimum content:
    - Approved symmetric: AES-256-GCM
    - Approved asymmetric: RSA-2048, ECDSA P-256
    - Approved hashing: SHA-256, SHA-384, SHA-512
    - Approved transport: TLS 1.2 minimum, TLS 1.3 preferred
    - Banned: MD5, SHA1, DES, 3DES, RC4, RSA-1024
  ISSO and SecEng sign off. Store signed copy in evidence path.
  Step 3: Add Semgrep job to the CI pipeline referencing ruleset p/cryptography. Configure
  the job to fail on any match. Test by committing a file containing hashlib.md5() and
  confirming the pipeline rejects the PR. Store CI configuration YAML in evidence path.

VALIDATION COMMAND:
  gitleaks detect --source . --report-format json --report-path /tmp/sc13-report.json; jq '. | length' /tmp/sc13-report.json
  Expected output: 0

RESIDUAL RISK AFTER REMEDIATION:
  Third-party libraries may use deprecated algorithms internally — Semgrep CI gate does not
  scan vendored dependencies. Trivy dependency scan is a planned follow-on action for
  transitive cipher risk. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — gitleaks not run. Weak cipher count unknown.
             Approved algorithm list not produced. Cipher policy not available.
  2026-05-12 IN PROGRESS — M1 complete: gitleaks scan complete across 12 repositories.
             3 findings (MD5 usage in legacy hash utility, SHA1 in one API client).
             Replaced with SHA-256. Rescan returned 0 findings.
  2026-05-14 IN PROGRESS — M2 complete: Approved algorithm list published in Confluence.
             SecEng and ISSO signed off. Linked from SSP SC-13 section.
  2026-05-16 IN PROGRESS — M3 complete: Semgrep p/cryptography gate wired to CI.
             Test commit with hashlib.md5() rejected by pipeline. CI config exported.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/SC-13?env=great → status: sufficient.
             Validation command returned 0. Evidence artifact stored.
```

---

## POAM-2026-05-036 — SC-28

```text
POAM-ID:          POAM-2026-05-036
CONTROL:          SC-28 — Protection of Information at Rest

WEAKNESS:
  Five deficiencies identified on Links-Matrix (AWS S3 / EBS / RDS / Secrets Manager):
  (1) Encryption scan not available — Prowler s3_bucket_default_encryption and
      kms_key_rotation_enabled checks have not been run; encryption posture is completely
      unknown.
  (2) S3 encryption status unconfirmed — no artifact confirms all S3 buckets have default
      encryption enabled with a KMS CMK; AWS-managed key (SSE-S3) may be in use.
  (3) EBS and RDS encryption unconfirmed — no aws ec2 describe-volumes or
      aws rds describe-db-instances output confirms encryption-at-rest on any volume or
      database instance.
  (4) KMS ARNs not produced — no JSON artifact lists the KMS key ARNs protecting each
      data store; auditor cannot verify CMK vs AWS-managed key usage.
  (5) Secrets Manager encryption not confirmed — no evidence confirms Secrets Manager secrets
      use a KMS CMK rather than the default AWS managed key.

SYSTEM AFFECTED:  Links-Matrix (AWS S3, EBS, RDS, Secrets Manager, KMS)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SC-28?env=bad → tool: prowler, status: insufficient,
                  s3_encryption: unconfirmed, ebs_encryption: unconfirmed,
                  rds_encryption: unconfirmed, kms_arns: not produced,
                  secrets_manager_encryption: unconfirmed.
                  CloudSec interview: no encryption evidence produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SC-28-2026-05-10/SC-28-finding.json

REMEDIATION OWNER: CloudSec (S3/EBS/RDS/Secrets Manager remediation) / SecEng (KMS CMK policy sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Run Prowler s3_bucket_default_encryption and kms_key_rotation_enabled checks;
                  export results JSON to evidence path; identify all S3 buckets without CMK
                  encryption and all KMS keys without rotation enabled.
  M2: 2026-05-14  Enable KMS CMK default encryption on all S3 buckets; confirm EBS account-level
                  encryption is enabled; verify all RDS instances are encrypted; export KMS ARN
                  JSON artifact mapping each data store to its key ARN.
  M3: 2026-05-16  Confirm all Secrets Manager secrets use a KMS CMK (not the default AWS managed
                  key); re-encrypt any secret using the default key; SecEng signs off on KMS
                  ARN inventory stored in evidence path.

REMEDIATION APPROACH:
  Step 1: Run Prowler S3 and KMS checks:
    prowler aws -c s3_bucket_default_encryption kms_key_rotation_enabled --output-formats json
  Export JSON results to evidence path. Review all FAIL items.
  Step 2: For each S3 bucket without CMK encryption, apply default encryption:
    aws s3api put-bucket-encryption --bucket <name> --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"<cmk-arn>"}}]}'
  Step 3: Enable EBS encryption by default at the account level:
    aws ec2 enable-ebs-encryption-by-default
  Confirm with:
    aws ec2 get-ebs-encryption-by-default
  and verifying EbsEncryptionByDefault=true.
  Step 4: For each RDS instance, run:
    aws rds describe-db-instances | jq '.DBInstances[] | {id: .DBInstanceIdentifier, encrypted: .StorageEncrypted}'
  For any unencrypted instance, take a snapshot, restore with encryption enabled, and promote
  the encrypted instance.
  Step 5: For each Secrets Manager secret, check the KmsKeyId field:
    aws secretsmanager list-secrets | jq '.SecretList[] | {name: .Name, kms: .KmsKeyId}'
  For any secret using the default key (aws/secretsmanager), update to use the CMK:
    aws secretsmanager update-secret --secret-id <name> --kms-key-id <cmk-arn>
  Export the full KMS ARN mapping JSON to evidence path with SecEng sign-off.

VALIDATION COMMAND:
  prowler aws -c s3_bucket_default_encryption kms_key_rotation_enabled --output-formats json | jq '[.[] | select(.status=="FAIL")] | length'
  Expected output: 0

RESIDUAL RISK AFTER REMEDIATION:
  EBS snapshots shared with other accounts are not covered by the Prowler checks — snapshot
  encryption sharing controls require a separate aws ec2 describe-snapshot-attribute audit.
  Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Encryption scan not available. S3 encryption unconfirmed.
             EBS and RDS encryption unconfirmed. KMS ARNs not produced.
             Secrets Manager encryption not confirmed.
  2026-05-12 IN PROGRESS — M1 complete: Prowler S3 and KMS checks run.
             6 S3 buckets using SSE-S3 instead of CMK. 4 KMS keys without rotation.
             Results JSON stored in evidence path.
  2026-05-14 IN PROGRESS — M2 complete: CMK encryption applied to all 6 S3 buckets.
             EBS account-level encryption enabled. All 8 RDS instances confirmed encrypted.
             KMS ARN mapping JSON exported for all data stores.
  2026-05-16 IN PROGRESS — M3 complete: 3 Secrets Manager secrets re-encrypted with CMK.
             All 11 secrets now use CMK. SecEng signed off on KMS ARN inventory.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/SC-28?env=great → status: sufficient.
             Validation command returned 0. Evidence artifact stored.
```
