# System Security Plan — System and Communications Protection (SC) Family

## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** This SSP would pass a FedRAMP readiness review with zero major
> findings. Boundary protection operates at five concurrent layers with Kyverno enforcing
> default-deny NetworkPolicy in every namespace including kube-system. Egress is filtered
> at the FQDN level via AWS Network Firewall. K8s etcd EncryptionConfiguration is
> deployed with KMS envelope encryption for Secrets. All nine key types are inventoried
> in a table with rotation schedules and tested recovery procedures. SC-13 Semgrep rules
> run on every PR and a quarterly testssl.sh audit covers every external endpoint. The
> mTLS gap (service-to-service inside cluster) is the sole documented gap — already in
> POA&M POAM-001 targeting Q4 2026.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Approved — Active Authorization

> **Control chain:** SC-7 (boundary) restricts what traffic reaches the system.
> SC-8 (transit encryption) protects data crossing those boundaries. SC-12 (key
> management) and SC-13 (algorithm selection) underpin both SC-8 and SC-28.
> SC-28 (encryption at rest) protects data that passes through SC-7 and SC-8 and
> lands in storage. A gap at any layer propagates forward — which is why the etcd
> EncryptionConfiguration in SC-28 and the mTLS gap in SC-8 are both tracked in
> the POA&M even though multiple compensating controls exist.

---

## SC-7 — Boundary Protection

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

### Multi-Layer Boundary Architecture

The Links-Matrix Platform implements boundary protection at five concurrent layers.
Each layer enforces what the layer above it cannot — a compromise of one layer is
contained by the layers below it.

| Layer | Control | Mechanism | Default Posture |
| ----- | ------- | --------- | --------------- |
| 1 — VPC | Subnet segmentation | Public / Private App / Data subnet tiers | Separate route tables, no cross-tier default routing |
| 2 — AWS Network Firewall | FQDN egress filtering | `lm-egress-firewall` (stateful) | Deny all egress except approved FQDN list |
| 3 — Security Group | Instance-level boundary | Per-tier SGs with minimum required rules | Deny all inbound; allow only named SG-to-SG |
| 4 — Kubernetes NetworkPolicy | Pod-level boundary | Default-deny in every namespace | Deny all pod-to-pod; allow only named selectors |
| 5 — Runtime (Falco) | Unexpected network syscall | Falco rule `detect_unexpected_outbound` | Alert on outbound to IP not in approved CIDR list |

### VPC Architecture

**Production VPC (`lm-prod-vpc`, 10.0.0.0/16, us-east-1):**

| Subnet | CIDR | Contents | Route Table |
| ------ | ---- | -------- | ----------- |
| Public-A | 10.0.0.0/24 | ALB only | IGW for inbound |
| Public-B | 10.0.1.0/24 | ALB only | IGW for inbound |
| Private-App-A | 10.0.16.0/20 | EKS nodes | NAT GW → Network Firewall → Internet |
| Private-App-B | 10.0.32.0/20 | EKS nodes | NAT GW → Network Firewall → Internet |
| Data-A | 10.0.64.0/24 | RDS primary | No internet route |
| Data-B | 10.0.65.0/24 | RDS replica | No internet route |

DR VPC (`lm-dr-vpc`, 10.1.0.0/16, us-west-2) mirrors this architecture. VPC peering
between prod and DR is restricted to replication traffic only (port 5432 RDS and port
443 S3 VPC endpoint) — no open peering.

### AWS Network Firewall (Egress Filtering)

A stateful AWS Network Firewall (`lm-egress-firewall`) sits in the egress path
between the NAT gateway and the internet. The firewall uses a Suricata-compatible
rule group with a default-deny stateful rule and an approved FQDN allowlist:

**Approved egress FQDNs (allowlist in `infra-iac/network-firewall/fqdn-rules.tf`):**

| Destination | Port | Purpose |
| ----------- | ---- | ------- |
| `*.amazonaws.com` | 443 | AWS service APIs (S3, ECR, Secrets Manager, etc.) |
| `*.okta.com` | 443 | Okta OIDC authentication |
| `*.pagerduty.com` | 443 | PagerDuty alerting |
| `*.github.com` | 443 | GitHub Actions (CI runners) |
| `acme-v02.api.letsencrypt.org` | 443 | cert-manager ACME |
| `nvd.nist.gov` | 443 | Prowler, Trivy CVE feed |
| `*.cisa.gov` | 443 | KEV feed (kev-check.yaml) |

All other outbound traffic is denied and logged to CloudWatch Logs
(`/aws/network-firewall/lm-egress-firewall`). VPC Flow Logs (`/aws/vpc/lm-prod-flowlogs`)
capture all boundary traffic at the VPC level.

### Security Groups

Security Groups follow a named-group-to-named-group model — no CIDR-based inbound rules
except the ALB SG accepting public HTTPS.

| Security Group | Inbound | Outbound |
| -------------- | ------- | -------- |
| `lm-alb-sg` | 443 from 0.0.0.0/0; 80 from 0.0.0.0/0 (redirect) | 8443 to `lm-node-sg` |
| `lm-node-sg` | 8443 from `lm-alb-sg`; 10250 from `lm-node-sg` (kubelet) | 443 to NAT GW; 5432 to `lm-rds-sg` |
| `lm-rds-sg` | 5432 from `lm-node-sg` | None |

AWS Config rule `vpc-default-security-group-closed` ensures the default VPC Security
Group has no rules. Terraform prevents any Security Group rule with `cidr_blocks = ["0.0.0.0/0"]`
on ingress (except `lm-alb-sg`) via a `deny-wildcard-ingress` Sentinel policy in
`infra-iac`.

### Kubernetes NetworkPolicy

Default-deny NetworkPolicy is deployed in **every namespace** — including `kube-system`,
`cert-manager`, `monitoring`, and `argocd`. This is enforced by Kyverno ClusterPolicy
`require-default-deny-netpol` (Enforce mode), which blocks creation of any new namespace
that does not include a corresponding default-deny NetworkPolicy within 60 seconds.

```yaml
# Default-deny template applied to all namespaces
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```

Allow rules are explicit and minimally scoped — each service's required ingress/egress
is documented in `platform-gitops/network-policies/<namespace>/`.

**Responsible Role:** Platform Engineer (NetworkPolicy, Kyverno enforcement, ingress), Cloud Security Engineer (VPC, Security Groups, Network Firewall, Falco egress rule), DevSecOps (Terraform Sentinel deny-wildcard policy)

**Parameters:**
- VPC CIDR: 10.0.0.0/16 (prod), 10.1.0.0/16 (DR)
- Egress filtering: AWS Network Firewall FQDN allowlist (7 approved destinations)
- Ingress entry points: 1 (NGINX Ingress Controller on ALB)
- Default-deny NetworkPolicy: All namespaces (Kyverno-enforced)
- VPC Flow Logs: 90-day retention, `/aws/vpc/lm-prod-flowlogs`
- Network Firewall logs: 90-day retention, `/aws/network-firewall/lm-egress-firewall`

**Evidence / Artifacts:**
- VPC and subnet Terraform (`infra-iac/vpc/main.tf`)
- Network Firewall FQDN rules (`infra-iac/network-firewall/fqdn-rules.tf`)
- Security Group Terraform (`infra-iac/security-groups/`)
- Kyverno ClusterPolicy `require-default-deny-netpol` (`platform-gitops/kyverno-policies/`)
- NetworkPolicy manifests by namespace (`platform-gitops/network-policies/`)
- Falco rule `detect_unexpected_outbound` (`platform-gitops/falco/rules/`)
- Terraform Sentinel deny-wildcard policy (`infra-iac/sentinel/deny-wildcard-ingress.sentinel`)

**Enhancements Addressed:**
- **SC-7(3):** Single NGINX Ingress Controller and single NAT gateway per environment.
  Network Firewall reduces outbound destinations to 7 approved FQDNs.
- **SC-7(4):** Network Firewall FQDN allowlist implements an explicit traffic flow policy
  for every approved external communication service. Any new external dependency requires
  a PR to `fqdn-rules.tf` before the workload can reach it.
- **SC-7(5):** Default-deny NetworkPolicy in every namespace enforced by Kyverno — deny
  by default, allow by exception, no namespace gaps.
- **SC-7(8):** Outbound internet traffic routes through NAT gateway then Network Firewall
  — a stateful, FQDN-inspecting managed interface. Unapproved outbound connections are
  blocked and logged.

---

## SC-8 — Transmission Confidentiality and Integrity

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

### External Ingress (HTTPS)

All external-facing endpoints are served over TLS. The NGINX Ingress Controller
ConfigMap enforces:

```nginx
ssl-protocols: TLSv1.2 TLSv1.3
ssl-ciphers: ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256
ssl-prefer-server-ciphers: "on"
```

TLS 1.0, TLS 1.1, SSLv3 are disabled. The above configuration is version-controlled —
weakening the cipher list requires a PR with ISSO review.

**Quarterly TLS audit:** A GitHub Actions scheduled workflow (`tls-audit.yaml`) runs
quarterly and executes `testssl.sh` against all external ingress endpoints, storing
the report in Confluence (LM-SECURITY / SC / TLS-Audit-YYYY-QQ.html). Any finding
of grade B or below creates a Jira `SEC` ticket.

**TLS audit history:**

| Quarter | Endpoints Audited | Lowest Grade | Findings | Resolved |
| ------- | ----------------- | ------------ | -------- | -------- |
| 2025-Q3 | 4 | A+ | 0 | — |
| 2025-Q4 | 4 | A | 1 (HSTS missing on staging) | 2025-12-10 |
| 2026-Q1 | 5 | A+ | 0 | — |

### Database Connections

RDS PostgreSQL enforces SSL via `rds.force_ssl=1` in the DB parameter group
(`lm-db-param-group`). Application connection strings use `sslmode=verify-full`
with the AWS RDS CA certificate bundle — server certificate is verified, not just
encryption used. The RDS CA certificate bundle is included in the application container
image at build time.

### Service-to-Service Communication

A service mesh is not currently deployed. Service-to-service communication inside
the `lm-production` namespace occurs over HTTP. This is a known gap — documented as
POA&M item POAM-001 (Linkerd service mesh, target Q4 2026). Compensating controls:
- NetworkPolicy restricts which pods can communicate (layer 4)
- All inter-service traffic stays within the private subnet (no internet exposure)
- Falco detects unexpected service connections at the syscall layer

**Responsible Role:** Platform Engineer (TLS configuration, cert-manager, NetworkPolicy), Cloud Security Engineer (RDS SSL, TLS audit workflow), DevSecOps (quarterly TLS audit review)

**Parameters:**
- Minimum TLS: 1.2 (TLS 1.3 preferred)
- TLS audit cadence: Quarterly (`tls-audit.yaml`)
- Database SSL: `sslmode=verify-full` (certificate verification enforced)
- Service-to-service mTLS: Not implemented (POA&M POAM-001, Q4 2026)
- Certificate auto-renewal: 30 days pre-expiry (cert-manager)
- Certificate expiry backstop: Prometheus alert at 14 days

**Evidence / Artifacts:**
- NGINX ConfigMap (`platform-gitops/ingress-nginx/configmap.yaml`)
- TLS audit workflow (`platform-gitops/.github/workflows/tls-audit.yaml`)
- TLS audit reports (Confluence: LM-SECURITY / SC / TLS-Audit-*)
- RDS parameter group (`infra-iac/rds/parameter-group.tf`)
- cert-manager Prometheus alert (`platform-gitops/monitoring/cert-expiry-alert.yaml`)
- POA&M POAM-001 (Confluence: LM-SECURITY / POA&M)

**Enhancements Addressed:**
- **SC-8(1):** TLS 1.2/1.3 with AEAD-only cipher suites on all external endpoints.
  Quarterly testssl.sh audit provides evidence of sustained cipher suite hygiene.
  Database connections use `sslmode=verify-full` — encryption and authentication.

---

## SC-12 — Cryptographic Key Establishment and Management

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

### Key Inventory

All cryptographic keys used by the Links-Matrix Platform are inventoried in
`platform-gitops/risk/key-inventory.md`. The table below is the current inventory:

| Key Name | Type | Storage | Algorithm | Rotation Schedule | Rotation Method | Recovery Procedure |
| -------- | ---- | ------- | --------- | ---------------- | --------------- | ------------------ |
| `lm-rds-cmk` | Symmetric DEK | AWS KMS (`mrk-def456`) | AES-256 | Annual | Automatic (KMS) | KMS key replica in us-west-2; tested 2026-02-15 |
| `lm-s3-cmk` | Symmetric DEK | AWS KMS (`mrk-abc123`) | AES-256 | Annual | Automatic (KMS) | KMS key replica in us-west-2; tested 2026-02-15 |
| `lm-ebs-cmk` | Symmetric DEK | AWS KMS (`mrk-ghi789`) | AES-256 | Annual | Automatic (KMS) | EBS snapshot re-encryption; tested 2026-02-15 |
| `lm-secrets-cmk` | Symmetric DEK | AWS KMS (`mrk-jkl012`) | AES-256 | Annual | Automatic (KMS) | Secrets Manager backup; tested 2026-02-15 |
| `lm-etcd-cmk` | Envelope key | AWS KMS (`mrk-mno345`) | AES-256 | Annual | Automatic (KMS) | Re-encrypt procedure in runbook; tested 2026-02-15 |
| TLS ingress certs | Asymmetric | Kubernetes Secret + cert-manager | RSA-4096 | ~90 days | Automatic (ACME) | Re-issue via cert-manager; tested in DR exercise |
| Code signing key (Cosign) | Asymmetric | AWS Secrets Manager (`lm-cosign-key`) | ECDSA P-384 | Annual | Manual (Jira `SEC` label: `key-rotation`) | Key re-generation procedure; tested 2025-Q4 |
| OIDC signing key (EKS) | Asymmetric | EKS-managed | RSA-2048 | Managed by AWS | Automatic (EKS) | EKS key rotation API; recovery via EKS docs |
| Break-glass YubiKey | Hardware key | Physical (ISSO custody) | FIDO2 | When personnel changes | Manual | Replacement YubiKey in physical safe (LM-OPS-SAFE-01) |

### Key Access Controls

All AWS KMS CMKs have key policies restricting usage to:
- The `lm-prod` AWS account (`arn:aws:iam::123456789012:root`)
- Specific IAM roles that require encrypt/decrypt access (e.g., `lm-prod-cluster-node-role` for etcd)
- The ISSO and Cloud Security Engineer for key administration

No key allows `kms:*` to `*`. Key deletion (`ScheduleKeyDeletion`) requires MFA and
generates a PagerDuty P1 alert to the ISSO within 5 minutes (CloudTrail → CloudWatch
alert → PagerDuty).

### Key Recovery Testing

Key recovery is tested annually as part of the DR failover exercise (CP-10). The 2026
DR exercise (2026-02-15) validated:
- RDS CMK replica in us-west-2 successfully used to decrypt DR RDS instance
- S3 CMK replica used to access DR S3 bucket data
- EBS CMK replica used to mount encrypted EBS snapshot from DR worker node
- etcd CMK: re-encryption procedure tested against a non-production cluster

Recovery test results: `platform-gitops/cp/dr-exercise-2026-results.md` — all key
recovery steps completed successfully with documented timings.

**Responsible Role:** Cloud Security Engineer (KMS CMKs, key policies, CloudTrail alerts), Platform Engineer (cert-manager, etcd EncryptionConfiguration, code signing), ISSO (break-glass YubiKey custody, annual recovery test sign-off)

**Parameters:**
- KMS CMK rotation: Annual (automatic, all 5 CMKs)
- TLS cert rotation: ~90 days (ACME, automatic)
- Code signing key rotation: Annual (manual, Jira-tracked)
- Key recovery testing: Annual (DR exercise)
- ScheduleKeyDeletion alert: PagerDuty P1 to ISSO within 5 minutes

**Evidence / Artifacts:**
- Key inventory (`platform-gitops/risk/key-inventory.md`)
- KMS CMK key policies (`infra-iac/kms/`)
- CloudTrail KMS alert rule (`infra-iac/monitoring/kms-deletion-alert.tf`)
- Key recovery test results (`platform-gitops/cp/dr-exercise-2026-results.md`)
- `cmk-backing-key-rotation-enabled` AWS Config rule findings (0 non-compliant)
- Code signing key rotation Jira tickets (`SEC` project, label: `key-rotation`)

**Enhancements Addressed:**
- **SC-12(1):** All five KMS CMKs have multi-region replicas in us-west-2. Key recovery
  procedure tested annually in the DR exercise — tested most recently 2026-02-15 with
  documented pass results.
- **SC-12(2):** AWS KMS generates symmetric DEKs using FIPS 140-2 Level 2 validated
  hardware. Key material never leaves KMS in plaintext — all encrypt/decrypt operations
  happen within the KMS service boundary.
- **SC-12(3):** TLS certificate private keys are generated by cert-manager within the
  cluster and stored in Kubernetes Secrets. Secrets are envelope-encrypted in etcd
  using `lm-etcd-cmk` via EncryptionConfiguration (see SC-28).

---

## SC-13 — Cryptographic Protection

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

### Approved Algorithm Inventory

The Links-Matrix Platform cryptographic policy (`KM-POL-001`, Confluence: LM-SECURITY
/ Policies / KM-POL-001) specifies the following approved and prohibited algorithms:

**Approved algorithms:**

| Use Case | Algorithm | Key Length / Digest | Notes |
| -------- | --------- | ------------------- | ----- |
| Symmetric encryption (data at rest) | AES-GCM | 256-bit | Authenticated encryption |
| Symmetric encryption (transit) | AES-GCM, ChaCha20-Poly1305 | 256-bit | TLS 1.3 cipher suites |
| Hashing (integrity) | SHA-256, SHA-384 | — | SHA-512 also permitted |
| Asymmetric (TLS certificates) | RSA | 4096-bit minimum | ECDSA P-384 preferred for new certs |
| Asymmetric (code signing) | ECDSA | P-384 | Cosign with EC key |
| Key agreement | ECDHE | P-256 or P-384 | TLS forward secrecy |
| Password hashing | Argon2id | m=65536, t=3, p=4 | Application layer |
| HMAC (token signatures) | HMAC-SHA256 | 256-bit | JWT signing |

**Prohibited algorithms (any use — immediately reportable):**

| Algorithm | Reason | Detection |
| --------- | ------ | --------- |
| MD5 | Collision attacks feasible (Flame malware, 2012) | Semgrep `weak-crypto.yaml` rule |
| SHA-1 | Collision attacks demonstrated (SHAttered, 2017) | Semgrep `weak-crypto.yaml` rule |
| DES / 3DES | Brute-forceable / SWEET32 | Semgrep; testssl.sh audit |
| RC4 | Statistical biases; real-world attacks demonstrated | TLS config review; testssl.sh |
| RSA < 2048-bit | Below NIST minimum key length since 2011 | Semgrep; cert expiry monitoring |
| NULL/EXPORT ciphers | No encryption | TLS cipher suite config (blocked) |

### CI Enforcement

A Semgrep rule set (`platform-gitops/.semgrep/weak-crypto.yaml`) runs on every PR
to `platform-gitops`, `lm-app`, and `infra-iac` repositories as a required check.
The rule set detects: `hashlib.md5`, `hashlib.sha1`, `MD5Digest`, `SHA1`, import of
`des` / `rc4` libraries, and RSA key generation with `key_size < 2048`. Any finding
blocks PR merge.

Semgrep finding history (last 90 days): 0 weak-crypto findings merged to main.

### FIPS 140-2 Status

FIPS 140-2 validated cryptography is not required for this system — Links-Matrix is
a commercial cloud system not processing CUI or classified information. Documented in
ADR-019 (`platform-gitops/docs/decisions/ADR-019-fips-not-required.md`). AWS KMS
operations use FIPS 140-2 validated hardware by default regardless. If scope changes
to require CUI processing, ADR-019 requires revisitation and a POA&M for FIPS-mode
library enablement in the application runtime.

**Responsible Role:** DevSecOps (Semgrep CI rule), Platform Engineer (TLS cipher suite config), Cloud Security Engineer (quarterly TLS audit, KMS algorithm validation), ISSO (algorithm policy)

**Parameters:**
- Approved symmetric: AES-256-GCM, ChaCha20-Poly1305
- Approved asymmetric: RSA-4096 minimum; ECDSA P-384 preferred
- Approved hash: SHA-256, SHA-384
- Password hashing: Argon2id
- Prohibited: MD5, SHA-1, DES, 3DES, RC4, RSA < 2048-bit, NULL/EXPORT
- CI enforcement: Semgrep `weak-crypto.yaml` (blocks merge on violation)
- FIPS 140-2: Not required (ADR-019)

**Evidence / Artifacts:**
- Cryptographic policy KM-POL-001 (Confluence: LM-SECURITY / Policies)
- Semgrep weak-crypto rule (`platform-gitops/.semgrep/weak-crypto.yaml`)
- Semgrep CI workflow and finding history (GitHub Actions)
- Quarterly TLS audit reports (Confluence: LM-SECURITY / SC / TLS-Audit-*)
- ADR-019 (`platform-gitops/docs/decisions/ADR-019-fips-not-required.md`)

---

## SC-28 — Protection of Information at Rest

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

### Encryption at Rest Inventory

Every storage layer within the Links-Matrix authorization boundary is encrypted.
The table below is the authoritative encryption inventory:

| Data Store | Service | Encryption | Key | CMK? | Enforcement |
| ---------- | ------- | ---------- | --- | ---- | ----------- |
| Application data | S3 `lm-app-data-*` | SSE-KMS | `lm-s3-cmk` | Yes | Bucket policy denies unencrypted PutObject |
| Database | RDS PostgreSQL `lm-db-prod` | AES-256 | `lm-rds-cmk` | Yes | Terraform enforces at creation |
| DB backups | RDS automated snapshots | AES-256 | `lm-rds-cmk` (inherited) | Yes | Inherited from source instance |
| K8s Secrets (etcd) | EKS etcd | AES-256 envelope | `lm-etcd-cmk` (KMS) | Yes | EncryptionConfiguration resource |
| Persistent Volumes | EBS (ebs-csi-driver) | AES-256 | `lm-ebs-cmk` | Yes | StorageClass `encrypted: "true"` + CMK |
| Worker node root volumes | EBS | AES-256 | `lm-ebs-cmk` | Yes | Launch template `encrypted: true` + CMK |
| Backup storage | S3 Velero bucket | SSE-KMS | `lm-s3-cmk` | Yes | Bucket policy denies unencrypted PutObject |
| Image registry | ECR `lm-ecr-prod` | AES-256 | AWS-managed | No | ECR default; CMK upgrade planned |
| Secrets storage | AWS Secrets Manager | AES-256 | `lm-secrets-cmk` | Yes | Terraform enforces CMK at creation |
| Log archive | S3 `lm-log-archive-*` | SSE-KMS | `lm-s3-cmk` | Yes | Bucket policy denies unencrypted PutObject |

ECR does not use a CMK — the AWS-managed ECR key does not provide key custody evidence.
This is a Low risk acceptance (RA-ACCEPT-003, planned) — ECR stores images, not customer
data, and images are additionally validated via Cosign signature verification at deploy time.

### Kubernetes etcd Encryption

EKS EncryptionConfiguration is deployed on the `lm-prod-cluster` and `lm-dr-cluster`
API servers (`platform-gitops/cluster/encryption-config.yaml`). The configuration
uses the `kms` provider with `lm-etcd-cmk`:

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources: [secrets, configmaps]
    providers:
      - kms:
          name: lm-etcd-kms
          endpoint: unix:///var/run/kmsplugin/socket.sock
          cachesize: 1000
          timeout: 3s
      - identity: {}
```

This means every Secret and ConfigMap object is envelope-encrypted using `lm-etcd-cmk`
before being written to etcd. Verification command:

```bash
# Verify a Secret is encrypted in etcd (not base64 plaintext)
ETCDCTL_API=3 etcdctl get /registry/secrets/lm-production/lm-db-credentials \
  --endpoints=https://etcd:2379 --cacert /etc/kubernetes/pki/etcd/ca.crt \
  --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key \
  | strings | head -20
# Expected: first bytes show 'k8s:enc:kms:v1:' prefix — not base64 plaintext
```

### S3 Encryption Enforcement

All data S3 buckets have a bucket policy denying unencrypted PutObject:

```json
{
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:PutObject",
  "Resource": "arn:aws:s3:::lm-app-data-primary/*",
  "Condition": {
    "StringNotEquals": {
      "s3:x-amz-server-side-encryption": "aws:kms"
    }
  }
}
```

This applies to all `lm-app-data-*` and `lm-log-archive-*` buckets. The Velero S3
bucket has the same policy. This is enforced via Terraform; any bucket missing this
policy fails the `s3-deny-unencrypted-putobject` AWS Config custom rule.

### AWS Config Monitoring

The following Config rules enforce encryption at rest:

| Config Rule | Scope | Current Status |
| ----------- | ----- | -------------- |
| `encrypted-volumes` | All EBS volumes in `lm-prod` | Compliant (0 violations) |
| `rds-storage-encrypted` | All RDS instances | Compliant |
| `s3-bucket-server-side-encryption-enabled` | All S3 buckets | Compliant |
| `s3-deny-unencrypted-putobject` (custom) | All `lm-*` S3 buckets | Compliant |
| `secretsmanager-using-cmk` (custom) | Secrets Manager secrets | Compliant |

**Responsible Role:** Cloud Security Engineer (KMS CMKs, S3 bucket policies, Config rules, Secrets Manager), Platform Engineer (etcd EncryptionConfiguration, EBS StorageClass, PV encryption), DevSecOps (Terraform encryption enforcement)

**Parameters:**
- etcd encryption: KMS envelope (`lm-etcd-cmk`) — Secrets and ConfigMaps
- S3 encryption: SSE-KMS (`lm-s3-cmk`) — enforce via bucket policy
- RDS encryption: AES-256 (`lm-rds-cmk`) — enforced at Terraform creation
- EBS encryption: AES-256 (`lm-ebs-cmk`) — nodes and PVs
- Secrets Manager: AES-256 (`lm-secrets-cmk`)
- ECR: AWS-managed key (CMK upgrade planned — Low risk acceptance)

**Evidence / Artifacts:**
- Encryption inventory (`platform-gitops/risk/encryption-inventory.md`)
- etcd EncryptionConfiguration (`platform-gitops/cluster/encryption-config.yaml`)
- S3 bucket policy Terraform (`infra-iac/s3/bucket-policies.tf`)
- EBS StorageClass manifest (`platform-gitops/storage-class/ebs-encrypted-cmk.yaml`)
- Worker node launch template (`infra-iac/eks/launch-template.tf`)
- AWS Config rule findings (Security Hub: filter ProductName = Config, 0 non-compliant)
- Secrets Manager CMK configuration (`infra-iac/secrets-manager/`)

**Enhancements Addressed:**
- **SC-28(1):** Customer-managed KMS keys (CMKs) used for all primary storage tiers:
  RDS, S3 (data and logs), EBS (nodes and PVs), Secrets Manager, and etcd (via KMS
  envelope encryption). Key custody is evidenced by CloudTrail KMS API logs. ECR uses
  AWS-managed key — documented low-risk exception.

---

## Test Procedures

### SC-7 Test Procedure

```bash
# Verify default-deny NetworkPolicy in every namespace
for ns in $(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'); do
  echo -n "Namespace $ns: "
  kubectl get networkpolicy default-deny-all -n "$ns" &>/dev/null \
    && echo "PASS" || echo "FAIL — missing default-deny"
done
# Expected: PASS for every namespace

# Verify Network Firewall is in the egress path
aws network-firewall describe-firewall --firewall-name lm-egress-firewall \
  --query 'Firewall.FirewallStatus.SyncStates'
# Expected: all AZs in READY state

# Verify no NodePort services expose pods directly
kubectl get services -A --field-selector spec.type=NodePort
# Expected: No resources found.
```

### SC-8 Test Procedure

```bash
# Verify TLS 1.0 and 1.1 are disabled on all external endpoints
testssl.sh --protocols --quiet https://links-matrix.io 2>&1 | grep -E "TLSv1\.0|TLSv1\.1"
# Expected: both listed as "not offered"

# Verify RDS SSL enforcement
aws rds describe-db-parameters --db-parameter-group-name lm-db-param-group \
  --query "Parameters[?ParameterName=='rds.force_ssl'].ParameterValue"
# Expected: ["1"]
```

### SC-12 Test Procedure

```bash
# Verify all KMS CMKs have annual rotation enabled
for key_id in mrk-def456 mrk-abc123 mrk-ghi789 mrk-jkl012 mrk-mno345; do
  aws kms get-key-rotation-status --key-id "$key_id" \
    --query 'KeyRotationEnabled'
done
# Expected: true for all keys

# Verify ScheduleKeyDeletion CloudWatch alarm exists
aws cloudwatch describe-alarms --alarm-name-prefix lm-kms-deletion \
  --query 'MetricAlarms[*].AlarmName'
# Expected: lm-kms-deletion-alert
```

### SC-28 Test Procedure

```bash
# Verify S3 bucket policy denies unencrypted uploads (attempt should fail)
aws s3api put-object --bucket lm-app-data-primary \
  --key test-unencrypted.txt --body /dev/null
# Expected: An error occurred (AccessDenied) — bucket policy rejected unencrypted PUT

# Verify etcd Secrets are KMS-encrypted (not base64 plaintext)
kubectl get secret lm-db-credentials -n lm-production \
  -o jsonpath='{.metadata.annotations}'
# Expected: includes 'encryption.kubernetes.io/provider: kms' annotation

# Verify all EBS volumes are encrypted
aws ec2 describe-volumes \
  --filters "Name=tag:kubernetes.io/cluster/lm-prod-cluster,Values=owned" \
  --query 'Volumes[?Encrypted==`false`].VolumeId'
# Expected: [] (empty — all volumes encrypted)
```

**Pass criteria:** All namespaces have default-deny NetworkPolicy, no NodePort services,
Network Firewall READY, TLS 1.0/1.1 not offered, RDS force_ssl=1, all KMS CMKs rotate
annually, S3 denies unencrypted PUT, etcd Secrets show KMS annotation, zero unencrypted
EBS volumes.

---

## What Makes This GREAT — Examiner's Notes

| Control | What Elevates It |
| ------- | ---------------- |
| SC-7 | Five-layer boundary table — auditors see exactly what each layer catches and how layers compensate for each other. Kyverno-enforced default-deny covers every namespace including kube-system — no gaps. Good SSPs say "most namespaces." Great SSPs say "all namespaces, enforced by policy engine." |
| SC-7 | Network Firewall FQDN allowlist with 7 named destinations — egress is not just "go through NAT gateway." Any new external API call requires a code review and merge to add the FQDN. The allowlist is the enforcement mechanism AND the documentation. |
| SC-8 | Quarterly testssl.sh audit with grade history — cipher suite hygiene is a recurring measurement, not a point-in-time assertion. The staging HSTS finding (2025-Q4) and resolution date shows the process working. |
| SC-12 | 9-row key inventory table with KMS key IDs, rotation schedules, rotation methods, and recovery procedure with test dates. Good SSPs name two keys. Great SSPs name every key, where it lives, how it rotates, and when recovery was last tested. |
| SC-28 | etcd EncryptionConfiguration deployed with KMS envelope key and a verification command. This is the most commonly missing SC-28 element — K8s Secrets in base64 in etcd is the silent failure mode. The test procedure shows exactly how to verify it works. |
| SC-28 | 10-row encryption inventory table covering every storage tier including ECR (with documented low-risk exception). Good SSPs cover S3 and RDS. Great SSPs cover etcd, EBS nodes, PVs, Secrets Manager, and log archive — and explain why ECR is the exception. |
