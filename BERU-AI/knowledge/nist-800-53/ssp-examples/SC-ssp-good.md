# System Security Plan — System and Communications Protection (SC) Family

## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** This SSP would pass a readiness review with 4-6 clarification items.
> VPC subnets are named, Security Group rules are described, NetworkPolicy is deployed
> in most namespaces, TLS 1.2+ is enforced with cert-manager, AWS KMS CMKs are named
> for RDS and S3, and EBS volumes are encrypted. Gaps: no egress filtering (pods can
> reach any internet endpoint), service-to-service traffic inside the cluster is HTTP
> (mTLS POA&M), etcd EncryptionConfiguration is asserted but the specific resource is
> not referenced, FIPS 140-2 status is not addressed, and key recovery has never been
> tested.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Final Draft — Pending ISSO Signature

---

## SC-7 — Boundary Protection

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

The Links-Matrix Platform implements boundary protection at three layers: VPC/subnet
architecture, AWS Security Groups, and Kubernetes NetworkPolicy.

**VPC architecture:**
The platform runs in a dedicated AWS VPC (`lm-prod-vpc`, 10.0.0.0/16) with three
subnet tiers per availability zone:
- **Public subnets** (10.0.0.0/22, 10.0.4.0/22): ALB ingress controller only.
  No application workloads run in public subnets.
- **Private application subnets** (10.0.16.0/20, 10.0.32.0/20): EKS worker nodes.
  No direct internet ingress; NAT gateway for controlled egress.
- **Data subnets** (10.0.64.0/22, 10.0.68.0/22): RDS instances. No internet access.
  Reachable only from private application subnets.

**Security Group rules:**
- ALB Security Group: Inbound 443 from 0.0.0.0/0, 80 from 0.0.0.0/0 (redirect only).
  Outbound: port 8443 to worker node Security Group only.
- Worker node Security Group: No direct inbound from internet. Inbound from ALB SG on
  8443. Outbound: NAT gateway for 443 (package updates, external APIs), port 5432 to
  RDS Security Group.
- RDS Security Group: Inbound port 5432 from worker node Security Group only. No
  outbound to internet.
- VPC Flow Logs enabled on the production VPC, delivering to CloudWatch Logs
  (`/aws/vpc/lm-prod-flowlogs`), retained 90 days.

**Kubernetes NetworkPolicy:**
Default-deny NetworkPolicy is deployed in the `lm-production`, `lm-staging`, and
`lm-platform-tools` namespaces. Specific allow rules permit only required pod-to-pod
traffic. *(Note: the `kube-system` and `cert-manager` namespaces do not have
default-deny NetworkPolicy — these are shared infrastructure namespaces. This is a
partial coverage gap.)*

**Ingress:**
A single NGINX Ingress Controller (`ingress-nginx`) is the sole external entry point
for application traffic. No NodePort or LoadBalancer services expose pods directly.

**Responsible Role:** Platform Engineer (NetworkPolicy, ingress), Cloud Security Engineer (VPC, Security Groups)

**Parameters:**
- VPC CIDR: 10.0.0.0/16 (`lm-prod-vpc`)
- Ingress entry points: 1 (NGINX Ingress Controller on ALB)
- Egress: NAT gateway (outbound internet) — no egress filtering beyond Security Group
- Default-deny NetworkPolicy: Production, staging, and platform-tools namespaces

**Evidence / Artifacts:**
- VPC and subnet configuration (`infra-iac/vpc/main.tf`)
- Security Group rules (`infra-iac/security-groups/`)
- NetworkPolicy manifests (`platform-gitops/network-policies/`)
- VPC Flow Logs configuration (`infra-iac/vpc/flow-logs.tf`)
- ALB ingress controller manifest (`platform-gitops/ingress-nginx/`)

**Enhancements Addressed:**
- **SC-7(3):** Single NGINX Ingress Controller and single NAT gateway per environment
  limit the number of external network connection points.
- **SC-7(5):** Default-deny NetworkPolicy in production, staging, and platform-tools
  namespaces implements deny-by-default at the pod communication layer. *(Gap: kube-system
  and cert-manager namespaces lack default-deny NetworkPolicy.)*
- **SC-7(4):** Security Group egress rules restrict outbound traffic from worker nodes
  to the NAT gateway on port 443. *(Gap: no FQDN-level egress filtering — pods can
  reach any external HTTPS endpoint via the NAT gateway.)*
- **SC-7(8):** Outbound internet traffic from worker nodes flows through the NAT gateway —
  a single, logged egress point. *(Note: NAT gateway is not an authenticated proxy —
  outbound connections are not inspected for content or destination FQDN.)*

---

## SC-8 — Transmission Confidentiality and Integrity

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

**External ingress (HTTPS):**
All external-facing endpoints are served over HTTPS via the NGINX Ingress Controller.
TLS certificates are issued by cert-manager using Let's Encrypt (ACME). The Ingress
resource annotation `nginx.ingress.kubernetes.io/ssl-protocols: TLSv1.2 TLSv1.3`
enforces TLS 1.2 as the minimum version. TLS 1.0 and 1.1 are disabled. HTTP requests
are redirected to HTTPS via `nginx.ingress.kubernetes.io/ssl-redirect: "true"`.

**Cipher suites (ingress):**
```
TLS_AES_256_GCM_SHA384 (TLS 1.3)
TLS_CHACHA20_POLY1305_SHA256 (TLS 1.3)
ECDHE-RSA-AES256-GCM-SHA384 (TLS 1.2)
ECDHE-RSA-AES128-GCM-SHA256 (TLS 1.2)
```
RC4, 3DES, NULL, and EXPORT cipher suites are disabled.

**Certificate management:**
cert-manager auto-renews certificates 30 days before expiry. A Prometheus alert fires
if any Certificate object shows `NotAfter` within 14 days.

**Database connections:**
RDS PostgreSQL (`lm-db-prod`) requires SSL on all connections. The `rds.force_ssl`
parameter is set to `1` in the DB parameter group (`lm-db-param-group`). Application
connection strings include `sslmode=require`.

**Service-to-service:**
A service mesh is not deployed. Service-to-service communication inside the
`lm-production` namespace occurs over HTTP. This is a known gap relative to SC-8 /
IA-3(1) — documented as POA&M item `POAM-001` (mTLS target: Linkerd, Q4 2026).
NetworkPolicy microsegmentation provides a compensating network-layer control.

**Responsible Role:** Platform Engineer (cert-manager, ingress TLS config, NetworkPolicy), Cloud Security Engineer (RDS SSL enforcement), DevSecOps (Prometheus cert-expiry alert)

**Parameters:**
- Minimum TLS version: 1.2 (TLS 1.3 preferred)
- HTTP-to-HTTPS redirect: Enforced at ingress
- Certificate auto-renewal lead time: 30 days
- Certificate expiry backstop alert: 14 days
- Database SSL: Enforced (`rds.force_ssl=1`)
- Service-to-service mTLS: Not implemented (POA&M POAM-001, target Q4 2026)

**Evidence / Artifacts:**
- NGINX Ingress Controller ConfigMap (`platform-gitops/ingress-nginx/configmap.yaml`)
- cert-manager Prometheus alert (`platform-gitops/monitoring/cert-expiry-alert.yaml`)
- RDS parameter group (`infra-iac/rds/parameter-group.tf`)
- POA&M item POAM-001 (Confluence: LM-SECURITY / POA&M)

**Enhancements Addressed:**
- **SC-8(1):** TLS 1.2/1.3 with strong cipher suites on all external ingress endpoints.
  RC4, 3DES, NULL cipher suites explicitly disabled. cert-manager automated renewal
  with Prometheus backstop alert.

---

## SC-12 — Cryptographic Key Establishment and Management

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

**AWS KMS (data encryption keys):**
AWS KMS customer-managed keys (CMKs) are used for S3 and RDS encryption:
- `lm-s3-cmk` (Key ID: `mrk-abc123...`): S3 bucket encryption for `lm-app-data-*`
  buckets. Annual automatic rotation enabled.
- `lm-rds-cmk` (Key ID: `mrk-def456...`): RDS storage encryption for `lm-db-prod`.
  Annual automatic rotation enabled.

Both CMKs have key policies restricting usage to the `lm-prod` AWS account.
CloudTrail logs all KMS API events (Encrypt, Decrypt, GenerateDataKey) to S3.

**TLS certificate keys:**
cert-manager issues TLS certificates from Let's Encrypt (ACME). Private keys are
generated by cert-manager and stored as Kubernetes Secrets. Private keys never leave
the cluster — cert-manager handles the ACME challenge entirely in-cluster.

**AWS Config rule:**
`cmk-backing-key-rotation-enabled` is deployed and produces a finding if KMS CMK
automatic rotation is disabled on any key in the `lm-prod` account.

**Key management policy:**
Formal key management policy (`KM-POL-001`, Confluence: LM-SECURITY / Policies /
KM-POL-001) documents: key types, storage requirements, rotation schedules, and
access controls. Policy reviewed annually by ISSO.

**Responsible Role:** Cloud Security Engineer (AWS KMS CMKs, key policy), Platform Engineer (cert-manager TLS keys), ISSO (key management policy)

**Parameters:**
- RDS CMK rotation: Annual (automatic, AWS KMS)
- S3 CMK rotation: Annual (automatic, AWS KMS)
- TLS certificate rotation: Automatic (cert-manager, ~90-day Let's Encrypt lifetime)
- Key storage: AWS KMS (data keys), Kubernetes Secrets (TLS private keys)

**Evidence / Artifacts:**
- AWS KMS CMK configuration (`infra-iac/kms/`)
- `cmk-backing-key-rotation-enabled` Config rule findings
- CloudTrail KMS event log sample
- Key management policy KM-POL-001 (Confluence: LM-SECURITY / Policies)

**Enhancements Addressed:**
- **SC-12(1):** AWS KMS CMKs for S3 and RDS provide key custody with annual rotation.
  *(Gap: key recovery procedure for KMS CMK deletion has not been tested. The procedure
  exists in the runbook but has never been exercised — an untested recovery procedure
  is a gap.)*
- **SC-12(2):** AWS KMS generates symmetric data encryption keys using FIPS 140-2 validated
  hardware — key material never leaves AWS KMS in plaintext.
- **SC-12(3):** TLS certificate private keys are generated by cert-manager within the
  cluster and are not exported. *(Note: private key material is stored in Kubernetes Secrets,
  which are base64-encoded in etcd — see SC-28 for etcd encryption status.)*

---

## SC-13 — Cryptographic Protection

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

The Links-Matrix Platform uses NIST-approved cryptographic algorithms throughout.
The approved algorithm list is documented in the key management policy (KM-POL-001).

**Approved algorithms:**
- **Symmetric encryption:** AES-256 (AES-256-GCM for authenticated encryption)
- **Hashing:** SHA-256, SHA-384 (for TLS, signing, integrity checks)
- **Asymmetric:** RSA-4096 (for TLS certificates), ECDSA P-256 (for code signing)
- **Password hashing:** Argon2id (application layer)

**Deprecated algorithms (prohibited):**
MD5, SHA-1, DES, 3DES, RC4, RSA < 2048-bit are prohibited by KM-POL-001. A Semgrep
SAST rule (`platform-gitops/.semgrep/weak-crypto.yaml`) runs on every PR to
`platform-gitops` and `lm-app` repositories, blocking merge if weak hash functions
(MD5, SHA1) are detected in application code.

**TLS cipher suites:**
As documented in SC-8 — RC4, 3DES, NULL, and EXPORT suites are disabled on all
external endpoints. The NGINX configuration is version-controlled and any weakening
of the cipher suite configuration fails CI.

*(Note: FIPS 140-2 validated cryptography is not required for this system — Links-Matrix
is a commercial cloud system not subject to FedRAMP CUI requirements. This is documented
in ADR-019. If the system scope changes to include CUI, FIPS validation will be required.)*

**Responsible Role:** DevSecOps (Semgrep SAST rule), Platform Engineer (TLS cipher suite configuration), ISSO (algorithm policy)

**Parameters:**
- Approved symmetric: AES-256-GCM
- Approved hash: SHA-256, SHA-384
- Approved asymmetric: RSA-4096, ECDSA P-256
- Prohibited: MD5, SHA-1, DES, 3DES, RC4, RSA < 2048-bit
- FIPS 140-2 requirement: Not applicable (ADR-019)

**Evidence / Artifacts:**
- Key management policy KM-POL-001 (algorithm list section)
- Semgrep SAST rule (`platform-gitops/.semgrep/weak-crypto.yaml`)
- Semgrep CI workflow (`platform-gitops/.github/workflows/pr-checks.yaml`)

---

## SC-28 — Protection of Information at Rest

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

**S3 (object storage):**
All `lm-app-data-*` S3 buckets have default encryption set to SSE-KMS using `lm-s3-cmk`.
Terraform enforces this at bucket creation (`infra-iac/s3/`). *(Note: a bucket policy
denying unencrypted PutObject requests is defined on the `lm-app-data-primary` bucket
but not on all data buckets — some DR buckets rely on default encryption only.)*

**RDS (database):**
`lm-db-prod` has storage encryption enabled using `lm-rds-cmk`. Automated backups
(RDS snapshots) inherit the CMK encryption. Read replicas (if created) inherit encryption
from the source instance.

**EBS (persistent volumes):**
EKS worker node root volumes are encrypted using the AWS-managed EBS key (not a CMK).
PersistentVolumes provisioned via the `ebs-csi-driver` StorageClass have encryption
enabled by default (`encrypted: "true"` in the StorageClass manifest).

**Kubernetes etcd:**
EKS-managed clusters encrypt etcd storage at the AWS infrastructure layer using
AWS-managed keys. *(Note: Kubernetes-level EncryptionConfiguration — which encrypts
Secret objects within etcd using a KMS envelope key — is not configured on the
Links-Matrix cluster. K8s Secrets are base64-encoded in etcd at the application layer.
etcd disk-level encryption by AWS provides physical access protection but does not
prevent an authorized K8s API user from reading Secrets. This is a gap relative to
SC-28(1) for Secret objects specifically.)*

**AWS Config monitoring:**
AWS Config rules `encrypted-volumes`, `rds-storage-encrypted`, and
`s3-bucket-server-side-encryption-enabled` are deployed in the `lm-prod` account.
Any non-compliant resource creates a Security Hub finding.

**Responsible Role:** Cloud Security Engineer (S3, RDS encryption), Platform Engineer (EBS StorageClass, etcd gap awareness), DevSecOps (AWS Config rules)

**Parameters:**
- S3 encryption: SSE-KMS (`lm-s3-cmk`)
- RDS encryption: SSE-KMS (`lm-rds-cmk`)
- EBS encryption: Enabled (AWS-managed key for nodes, CMK not configured for EBS)
- etcd encryption: AWS infrastructure-layer only (K8s EncryptionConfiguration not deployed)
- Backup encryption: RDS snapshots inherit CMK; Velero backups to S3 inherit SSE-KMS

**Evidence / Artifacts:**
- S3 bucket encryption configuration (`infra-iac/s3/`)
- RDS encryption configuration (`infra-iac/rds/main.tf`)
- EBS StorageClass manifest (`platform-gitops/storage-class/ebs-encrypted.yaml`)
- AWS Config rules for encryption compliance

**Enhancements Addressed:**
- **SC-28(1):** S3 and RDS use customer-managed KMS keys (CMKs) providing key custody
  evidence and annual rotation. *(Gap: EBS worker node volumes use AWS-managed key,
  not a CMK — no key custody evidence for node storage. K8s etcd EncryptionConfiguration
  not deployed — Secrets are not envelope-encrypted at the K8s layer.)*

---

## What Makes This GOOD (But Not Great) — Examiner's Notes

| Control | Strengths | Gaps |
| ------- | --------- | ---- |
| SC-7 | VPC subnets named and tiered, Security Group rules described, default-deny NetworkPolicy in production | No egress filtering — pods can reach any internet endpoint via NAT gateway; kube-system and cert-manager namespaces lack default-deny |
| SC-7 | VPC Flow Logs enabled with 90-day retention | SC-7(8) NAT gateway is not an authenticated proxy — outbound traffic is logged at IP level but not inspected for destination |
| SC-8 | TLS 1.2/1.3, specific cipher suites listed, cert-manager with Prometheus backstop | Service-to-service inside cluster is HTTP (POA&M POAM-001) — any internal network attacker sees all inter-service traffic in plaintext |
| SC-12 | CMKs named with Key IDs, annual rotation enabled, AWS Config rule enforces rotation | Key recovery never tested — the procedure exists but an untested recovery is not a recovery |
| SC-13 | Specific algorithm list, Semgrep rule in CI blocking weak hashes | No periodic cipher suite audit of all endpoints — individual services added without review could introduce weak suites |
| SC-28 | S3 and RDS use CMKs, EBS encryption enabled, Config rules monitoring | K8s etcd EncryptionConfiguration not deployed — Secrets base64 in etcd is a material gap; DR S3 buckets lack deny-unencrypted PutObject bucket policy |
