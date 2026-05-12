# System Security Plan — Identification and Authentication (IA) Family

## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** This SSP is auditor-ready. The IA chain is explicit: IA-4 identifiers
> are the subjects that IA-2 and IA-3 authenticate, using the credentials managed by IA-5.
> Every MFA method is named with its replay-resistance property. The IA-3 service mesh gap
> is documented in the POA&M with a compensating control. Secret scanning covers both
> new commits (CI) and historical git history. Credential rotation is automated where
> possible and SLA-tracked where manual. Every enhancement addressed.

---

**System Name:** Links-Matrix Platform
**System Owner:** J. Rivera, Platform Engineering Lead (jrivera@links-matrix.io)
**ISSO:** M. Chen, Information System Security Officer (mchen@links-matrix.io)
**Prepared By:** M. Chen, ISSO
**Date:** 2026-05-01
**Review Date:** 2027-05-01 (annual) or upon significant system change
**Status:** Approved — ATO Granted 2026-03-15, expires 2029-03-15

**Control Chain Note:** IA-4 defines and manages the identifiers (who is who).
IA-2 authenticates human identifiers with a second factor before granting access.
IA-3 authenticates device and workload identifiers cryptographically before allowing
service connections. IA-5 manages the authenticators — passwords, certificates, tokens,
and secrets — that make IA-2 and IA-3 work. A weak link in any of these breaks
attribution across the whole system.

---

## IA-2 — Multi-Factor Authentication

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Low, Moderate, and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### MFA Enforcement Architecture

MFA is enforced at the Okta identity provider level — not at the application level.
No application can bypass the Okta MFA requirement because the OIDC token issued by
Okta is only valid if the session includes a satisfied MFA factor. Applications that
receive the token cannot determine whether MFA was satisfied; they only receive the
token if it was. There are zero MFA bypass conditions, network exclusions, or
IP-allowlist exceptions on any Okta Sign-On Policy for the Links-Matrix tenant.

### MFA Policy Table

| User Group | Okta Policy | Required MFA Method | Fallback Permitted | Replay-Resistant | SMS Permitted |
| ---------- | ----------- | ------------------- | ------------------ | ---------------- | ------------- |
| `links-matrix-admins` (privileged) | `lm-privileged-mfa` | FIDO2 hardware key (YubiKey 5 series) | None | **Yes** (FIDO2/WebAuthn — challenge bound to origin) | No |
| `links-matrix-users` (standard) | `lm-standard-mfa` | Okta Verify FIDO2 (WebAuthn via device biometric) | Okta Verify push (TOTP fallback — see note) | **Yes** (WebAuthn primary) | No |
| Break-glass accounts | AWS IAM hardware MFA | YubiKey TOTP (AWS IAM hardware MFA device) | None | Yes (hardware token) | No |
| CI/CD pipelines | OIDC federation (no human factor) | GitHub Actions OIDC token → AWS STS | N/A — machine identity | N/A | N/A |

> **Note on standard user TOTP fallback:** Okta Verify push with TOTP fallback is not
> fully replay-resistant (a captured OTP is valid for 30 seconds). This is a documented
> gap. The ISSO accepted this risk for standard users in `RISK-ACCEPT-IA-001` (Confluence:
> LM-SECURITY / Risk Acceptances, 2026-03-12) with a compensating control: Okta
> ThreatInsight blocks authentication attempts from IPs with a reputation score indicating
> credential stuffing. Upgrade to FIDO2 for all users is targeted for Q2 2027.

### Kubernetes API Authentication

EKS OIDC integration routes kubectl authentication through Okta:
1. Developer runs `okta-aws-cli exec` → redirected to Okta browser login
2. Okta enforces MFA per `lm-standard-mfa` or `lm-privileged-mfa` policy
3. Upon MFA success, Okta issues an OIDC ID token (1-hour expiry)
4. `aws eks get-token` exchanges the OIDC token for a K8s bearer token via STS
5. K8s API server validates the bearer token against the OIDC issuer

Static kubeconfig tokens are disabled at the API server (`--token-auth-file` not set,
verified by kube-bench check `1.2.2`). All kubectl access is per-session and
expires within 1 hour, requiring re-authentication.

### Break-Glass Access

Two break-glass AWS IAM users (`lm-break-glass-01`, `lm-break-glass-02`) are used
only in scenarios where AWS SSO/Okta is unavailable. Each has a YubiKey hardware MFA
device registered in AWS IAM. Credentials are stored in a physical safe accessible
to the ISSO and System Owner only. Any AWS API call from a break-glass user triggers:
- CloudTrail event captured immediately
- EventBridge rule → Lambda → PagerDuty P1 alert to ISSO within 5 minutes
- Slack message to `#sec-alerts` with the username, source IP, and action

Break-glass account credentials are rotated quarterly and after each use.

**Responsible Role:** ITOps (Okta policy ownership, MFA enrollment), Cloud Security Engineer (AWS IAM MFA, break-glass), ISSO (MFA policy governance, risk acceptance)

**Parameters:**
- Privileged MFA: **FIDO2 hardware key** (YubiKey 5) — no fallback, no exclusions
- Standard MFA: **Okta Verify FIDO2** (WebAuthn primary; TOTP fallback with accepted risk `RISK-ACCEPT-IA-001`)
- SMS: **Prohibited** across all policies
- kubectl token lifetime: **1 hour** (OIDC-bound)
- MFA bypass conditions: **Zero**
- Break-glass credential rotation: **Quarterly + after each use**
- Break-glass use alert SLA: **5 minutes** to PagerDuty P1

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| Okta Sign-On Policy `lm-privileged-mfa` | Okta Admin → Security → Authentication Policies | 2026-04-07 |
| Okta Sign-On Policy `lm-standard-mfa` | Okta Admin → Security → Authentication Policies | 2026-04-07 |
| CloudTrail `ConsoleLogin` sample (mfaAuthenticated: true) | S3 `lm-logs-cloudtrail/` — sample in quarterly IA review | 2026-04-07 |
| kube-bench check 1.2.2 (no static token auth) | Confluence: LM-SECURITY / kube-bench / 2026-W17.md | 2026-04-28 |
| Break-glass alert EventBridge rule | `infra-iac/monitoring/break-glass-alert.tf` | Per-commit |
| Risk acceptance `RISK-ACCEPT-IA-001` | Confluence: LM-SECURITY / Risk Acceptances | 2026-03-12 |
| Break-glass rotation log | Confluence: LM-SECURITY / IA / Break-Glass-Log.md | Quarterly |

**Test Procedure:**
1. Pull Okta Sign-On Policies for `lm-privileged-mfa` and `lm-standard-mfa` — verify
   no network exclusions, no IP allowlist bypass, and SMS is not listed as an allowed
   factor in either policy.
2. Pull a CloudTrail `ConsoleLogin` event for a privileged user — verify
   `additionalEventData.MFAUsed: Yes` and `additionalEventData.MFAIdentifier` is a
   hardware key serial (not SMS).
3. Attempt kubectl access with an expired OIDC token (>1 hour) — verify
   `Unauthorized` response and a new Okta MFA challenge is required.
4. Pull the AWS IAM MFA device list for break-glass accounts:
   `aws iam list-mfa-devices --user-name lm-break-glass-01`
   — verify a hardware MFA device is registered and `EnableDate` is within the last
   90 days (quarterly rotation confirmed).
5. Simulate a break-glass API call in a test account — verify PagerDuty P1 fires within
   5 minutes and Slack `#sec-alerts` receives the alert.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| IA-2(1) MFA to Privileged Accounts | Implemented | FIDO2 hardware key required for all `links-matrix-admins` group members. No fallback. No network exclusion. Verified by Okta policy configuration and CloudTrail login events. |
| IA-2(2) MFA to Non-Privileged Accounts | Implemented | Okta Verify FIDO2/WebAuthn required for standard users. TOTP fallback permitted with accepted risk `RISK-ACCEPT-IA-001`. SMS prohibited. No network exclusions. |
| IA-2(8) Replay Resistant | Implemented (privileged) / Accepted Risk (standard) | FIDO2 hardware key for privileged accounts is cryptographically replay-resistant (FIDO2 challenge-response bound to origin and session). Standard user TOTP fallback is not replay-resistant — accepted risk `RISK-ACCEPT-IA-001` with Okta ThreatInsight compensating control. FIDO2-for-all targeted Q2 2027. |
| IA-2(12) PIV Credentials | Not Applicable | Links-Matrix is a commercial SaaS platform, not a federal system. PIV acceptance is not required. Documented in ADR-021 (Confluence: LM-SECURITY / ADRs / ADR-021). |

---

## IA-3 — Device Identification and Authentication

**Implementation Status:** Implemented (IRSA + node identity); Partially Implemented (service-to-service mTLS — POA&M)
**Control Origination:** Hybrid (Inherited from AWS IRSA/EKS; System-Specific for workload identity and compensating controls)
**Baseline Allocation:** Moderate and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Workload Identity (AWS — IRSA)

Every Kubernetes workload that calls an AWS service authenticates using IRSA — no
static AWS access keys exist for application workloads. Implementation:

1. Each workload's K8s ServiceAccount is annotated with an IAM role ARN
   (`eks.amazonaws.com/role-arn: arn:aws:iam::998877665544:role/lm-prod-<workload>-role`)
2. The EKS OIDC provider (`oidc.eks.us-east-1.amazonaws.com/id/<cluster-id>`) issues
   a signed ServiceAccount JWT
3. AWS STS validates the JWT against the OIDC issuer and issues short-lived (1-hour)
   role credentials via `AssumeRoleWithWebIdentity`
4. The workload uses these temporary credentials — no long-lived key material is in
   the pod or image

Static access key enforcement: AWS Config custom rule `detect-static-access-keys-in-workloads`
scans IAM users tagged `workload-type: application` for access keys — any finding triggers
P1 alert. CI policy in `infra-iac` rejects any Terraform creating a `aws_iam_access_key`
for a workload user (OPA conftest rule `no-workload-static-keys`).

Current state: 0 static access keys on application workload IAM users (last Config scan:
2026-05-01).

### Worker Node Identity

EKS worker nodes authenticate to the K8s API server using node identity certificates
issued by the EKS-managed cluster CA. Node lifecycle:

1. New node receives a bootstrap token via the EC2 launch template (stored in Systems
   Manager Parameter Store — never in user data plaintext)
2. Bootstrap token is single-use and expires after **15 minutes** regardless of use
3. On successful join, the node receives a node identity certificate from the cluster CA
4. Bootstrap token is automatically revoked by the EKS control plane after first use
5. Node certificate rotation is automatic (EKS-managed, annual)

### Service-to-Service Authentication (Known Gap)

A service mesh providing mTLS is not currently deployed. This means:
- Service-to-service calls within the cluster use plaintext HTTP on the pod network
- Authentication between services relies on network identity (NetworkPolicy) rather than
  cryptographic certificate-based identity

**POA&M item `IA-3-001`** (Confluence: LM-SECURITY / POA&M):
- Target: Deploy Linkerd service mesh with `PeerAuthentication` in STRICT mTLS mode
- Target date: 2026-12-01
- Owner: Platform Engineer (J. Rivera)
- Compensating controls in place until deployment:
  1. Kubernetes NetworkPolicy default-deny (all namespaces) — only explicitly allowed pod-to-pod paths are open
  2. IRSA-based authentication for all AWS API calls — cloud services are never accessible without cryptographic identity
  3. All external-facing traffic (ingress) is TLS 1.2+ minimum (ALB + cert-manager)
  4. No service accepts unauthenticated external connections — all endpoints behind the ALB require app-layer JWT validation

**Responsible Role:** Cloud Security Engineer (IRSA, OIDC provider), Platform Engineer (node bootstrap, mTLS POA&M), ISSO (POA&M ownership)

**Parameters:**
- IRSA token lifetime: **1 hour** (STS temporary credentials)
- Bootstrap token lifetime: **15 minutes** (auto-revoke after use)
- Static access keys on workload IAM users: **0** (Config rule enforced)
- mTLS status: **POA&M `IA-3-001`**, target 2026-12-01

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| IRSA ServiceAccount annotations | `platform-gitops/serviceaccounts/*.yaml` | Per-commit |
| EKS OIDC provider configuration | `infra-iac/eks/oidc.tf` + AWS Console → EKS → cluster → Configuration | Per-commit |
| AWS Config rule `detect-static-access-keys-in-workloads` | AWS Console → Config → Rules | 2026-05-01 (0 findings) |
| OPA conftest rule `no-workload-static-keys` | `infra-iac/policy/no-workload-static-keys.rego` | Per-commit |
| CloudTrail `AssumeRoleWithWebIdentity` sample | S3 `lm-logs-cloudtrail/` | 2026-04-07 |
| Bootstrap token configuration (SSM Parameter Store) | `infra-iac/eks/launch-template.tf` | Per-commit |
| POA&M item `IA-3-001` | Confluence: LM-SECURITY / POA&M | 2026-05-01 |

**Test Procedure:**
1. Pull all ServiceAccount manifests from `platform-gitops/serviceaccounts/` — verify
   every application ServiceAccount has an `eks.amazonaws.com/role-arn` annotation.
2. Verify zero static access keys on workload users: `aws configservice get-compliance-details-by-config-rule --config-rule-name detect-static-access-keys-in-workloads` — expect `COMPLIANT` for all resources.
3. Pull a CloudTrail event for `AssumeRoleWithWebIdentity` — verify the `principalId`
   includes the service account name and namespace (format: `system:serviceaccount:<ns>:<sa>`).
4. Pull the bootstrap token configuration — verify `--bootstrap-kubeconfig` points to
   SSM Parameter Store, not a plaintext value in user data.
5. Pull POA&M `IA-3-001` — verify it has a target date, assigned owner, and monthly
   milestone updates showing progress toward Linkerd deployment.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| IA-3(1) Cryptographic Bidirectional Authentication | Partially Implemented | IRSA provides cryptographic workload-to-AWS bidirectional authentication (OIDC assertion from K8s, STS validation). Node-to-API-server authentication uses mutual TLS (EKS-managed). Service-to-service within the cluster does not use mTLS — this is POA&M `IA-3-001` (target 2026-12-01) with NetworkPolicy and IRSA as compensating controls. |

---

## IA-4 — Identifier Management

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Low, Moderate, and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Identifier Uniqueness and Lifecycle

**Human identifiers:**
Every human user has a single, unique identifier (email address) in Okta, linked to
a named individual via the Workday HRIS SCIM integration. The Okta tenant is configured
to reject duplicate email addresses at account creation — this is a technical enforcement,
not a policy-only requirement.

Shared accounts are technically prevented: the Okta Sign-On Policy requires a per-user
MFA enrollment, which cannot be shared. A shared password with one MFA device means
only one person can log in at a time — any concurrent session from a second IP triggers
an Okta ThreatInsight anomaly.

**Identifier lifecycle SLAs:**

| Event | Action | SLA | Mechanism |
| ----- | ------ | --- | --------- |
| New hire | Identifier created | Within 4 hours of Workday activation | SCIM auto-provisioning |
| Role change | Group membership updated | Within 1 business day | SCIM attribute sync |
| Employment termination | Identifier suspended | Within 2 hours | SCIM auto-deprovisioning |
| Identifier suspended 30 days | Permanent deletion | Day 30 (automated) | Okta lifecycle rule |
| Identifier inactive 30 days | Disabled | Day 30 (automated) | Okta lifecycle rule |
| Deleted identifier reuse | Prohibited | 12 months after permanent deletion | IT Operations procedure ITO-PROC-012 + Okta email uniqueness enforcement |

**User status categorization (IA-4(4)):**
Okta user profiles include a `userType` attribute sourced from Workday with the
following values: `employee`, `contractor`, `vendor`, `service-account`. This attribute:
- Is populated automatically via the Workday SCIM integration for human identities
- Drives Okta group membership (`lm-employees`, `lm-contractors`, `lm-vendors`)
- Is reflected in OIDC ID token claims (`userType` claim) consumed by the Links-Matrix
  API for access logging purposes
- Allows audit queries to filter by worker category without manual HR cross-referencing

Contractor and vendor identifiers are granted time-limited access: Okta accounts for
contractors have a `passwordExpiration` configured at the contract end date. Vendor
accounts expire 90 days after provisioning unless renewed by ISSO written approval.

**Service account and workload identifiers:**
All Kubernetes ServiceAccounts follow the naming convention `lm-<environment>-<workload>-sa`
(e.g., `lm-prod-api-sa`). AWS IAM roles follow `lm-<env>-<workload>-role`. This convention
is enforced by Kyverno policy `require-sa-annotation` and OPA conftest rule
`workload-naming-convention`.

Each ServiceAccount manifest in `platform-gitops/serviceaccounts/` includes:
- `secteam.io/owner`: owning team name
- `secteam.io/purpose`: single-sentence function description
- `secteam.io/created`: creation date
- `secteam.io/reviewed`: last quarterly review date

A CI job (`sa-review-age-check.yaml`) flags any ServiceAccount not reviewed in 90+ days
in a Jira `SEC` ticket.

**Responsible Role:** ISSO (identifier policy, IA-4(4) attribute governance), ITOps (Okta provisioning, lifecycle rules), Platform Engineer (K8s SA naming, annotation enforcement)

**Parameters:**
- Identifier provisioning SLA (new hire): **4 hours**
- Identifier suspension SLA (termination): **2 hours**
- Inactivity disable period: **30 days**
- Identifier retention post-suspension: **30 days**
- Identifier reuse prevention: **12 months** after permanent deletion
- Contractor account expiry: **Contract end date** (auto-set at provisioning)
- Vendor account expiry: **90 days** (renewable with ISSO approval)
- ServiceAccount review cadence: **Quarterly** (flagged at 90+ days)

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| Okta `userType` attribute configuration | Okta Admin → Directory → Profile Editor | 2026-04-07 |
| Workday→Okta SCIM integration (attribute mapping) | Okta Admin → Applications → Workday | 2026-04-07 |
| Okta group membership (`lm-employees`, `lm-contractors`, `lm-vendors`) | Okta Admin → Directory → Groups | Continuous |
| Okta lifecycle rules (inactivity, deletion schedule) | Okta Admin → Workflow → Lifecycle Management | 2026-04-07 |
| IT Operations procedure ITO-PROC-012 (reuse prevention) | Confluence: LM-SECURITY / Policies / ITO-PROC-012 | 2026-01-10 |
| Kyverno `require-sa-annotation` policy | `platform-gitops/kyverno/require-sa-annotation.yaml` | Per-commit |
| ServiceAccount review age CI job | `platform-gitops/.github/workflows/sa-review-age-check.yaml` | Per-run (weekly) |
| Quarterly access review records | Confluence: LM-SECURITY / Access Reviews | 2026-04-07 |

**Test Procedure:**
1. Pull the Okta user list and verify: zero accounts with identical email addresses;
   zero accounts without a `userType` attribute; zero accounts without a linked Workday
   employee record (orphaned accounts).
2. Pull the Okta lifecycle rule configuration — verify the inactivity-disable rule
   is set to 30 days and the deletion-after-suspension rule is set to 30 days.
3. Pull a terminated employee from the last 90 days — verify their Okta account was
   suspended within 2 hours and deleted within 32 days of the Workday termination event.
4. Pull all ServiceAccount manifests from `platform-gitops/serviceaccounts/` — verify
   every manifest has `secteam.io/owner`, `secteam.io/purpose`, `secteam.io/created`,
   and `secteam.io/reviewed` annotations. Verify no `secteam.io/reviewed` date is
   older than 90 days.
5. Verify contractor account expiry: pull Okta accounts in the `lm-contractors` group
   and confirm each has a `passwordExpiration` set to the contract end date.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| IA-4(4) Identify User Status | Implemented | Okta `userType` attribute (`employee`/`contractor`/`vendor`/`service-account`) populated via Workday SCIM. Drives group membership and access policy. Reflected in OIDC claims for audit attribution. Contractor accounts auto-expire at contract end date; vendor accounts expire at 90 days. Status is machine-readable — audit queries can filter by type without manual HR lookup. |

---

## IA-5 — Authenticator Management

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Low, Moderate, and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Credential Inventory and Rotation Schedule

Every credential type on the Links-Matrix Platform has a defined rotation schedule,
a rotation mechanism (automatic or manual with SLA), and a monitoring control that
detects missed rotations.

| Credential Type | Location | Rotation Period | Mechanism | Monitoring |
| --------------- | -------- | --------------- | --------- | ---------- |
| Database passwords (`lm-db-password`) | AWS Secrets Manager | 30 days | **Automatic** (Lambda rotation function) | Secrets Manager rotation status; Config rule `secretsmanager-rotation-enabled-check` |
| Third-party API keys (Stripe, SendGrid, etc.) | AWS Secrets Manager | 90 days | Manual (Jira `SEC` ticket auto-created 14 days before expiry) | GitHub Actions weekly `secret-rotation-check.yaml` — creates P2 ticket if overdue |
| TLS certificates (ingress, internal) | cert-manager + ACM | Auto-renew 30 days before expiry | **Automatic** (ACME/Let's Encrypt via cert-manager) | Prometheus alert if cert `NotAfter` <14 days; ACM expiry notification at 45 and 30 days |
| AWS IAM OIDC (IRSA) | EKS-managed | 1 hour (STS temp credentials) | **Automatic** (STS token expiry) | N/A — ephemeral by design |
| Break-glass IAM user credentials | Physical safe (ISSO custody) | 90 days + after each use | Manual (ISSO performs rotation) | Quarterly reminder in ISSO calendar; post-use rotation tracked in break-glass log |
| K8s ServiceAccount tokens | EKS-managed (bound tokens) | 1 hour (bound token expiry) | **Automatic** (TokenRequest API) | N/A — ephemeral by design |
| FIDO2 hardware keys (YubiKey) | User custody (privileged accounts) | On loss/compromise or annual review | Manual (ITOps re-enrollment) | Annual MFA device audit (Okta Admin → Reports) |
| etcd encryption keys | AWS KMS (`lm-cmk-etcd`) | Annual KMS key rotation | **Automatic** (KMS key rotation enabled) | KMS key rotation status (Config rule `kms-cmk-backing-key-rotation-enabled`) |

### Password Policy

Okta enforces `lm-password-policy` (NIST SP 800-63B aligned):

| Setting | Value | Rationale |
| ------- | ----- | --------- |
| Minimum length | 16 characters | Length is the primary strength factor |
| Maximum length | 128 characters (Okta limit) | Support for passphrases |
| Character complexity | None required | Complexity rules reduce entropy; length is sufficient |
| Breach corpus check | Enabled — HIBP integration via Okta ThreatInsight | Prevents use of known-compromised passwords at set time |
| Password reuse | Last 12 passwords prohibited | Prevents cycling through known passwords |
| Maximum age | None (NIST-aligned — no forced periodic rotation) | Forced rotation drives weak passwords; breach detection is the trigger |
| Change trigger | Compromised credential detection → forced reset | Rotation on evidence of compromise, not calendar |

### Secrets Management

All application secrets are stored in AWS Secrets Manager. No exceptions:

- **Not permitted:** environment variables, ConfigMaps, image layers, source code, CI logs
- **Enforced by:**
  - Kyverno policy `deny-env-secrets` (Enforce): rejects any pod spec with
    `valueFrom.secretKeyRef` referencing a secret with `type: Opaque` and
    `data` keys matching credential patterns
  - gitleaks CI gate (blocks PR merge on detected credentials)
  - Semgrep SAST rule `detect-hardcoded-credentials` (blocks PR merge)
  - Pre-commit `detect-secrets` hook (developer workstation — enforced via
    `platform-gitops/.pre-commit-config.yaml` required in developer onboarding checklist)

Secrets are injected into pods via the **Secrets Store CSI Driver**
(`platform-gitops/secrets-store/`), which mounts secrets as files from Secrets Manager.
Secrets are never passed as environment variables to containers.

### Secret Scanning (New Commits and Historical)

| Scope | Tool | Cadence | Action on Finding |
| ----- | ---- | ------- | ----------------- |
| New PR commits | gitleaks (CI required gate) | Every PR | Block merge; author notified; ISSO alerted if severity HIGH |
| Developer workstation | detect-secrets (pre-commit hook) | Every commit attempt | Block commit; show finding inline |
| Full git history (retroactive) | gitleaks + truffleHog (both) | Quarterly (scheduled CI job) | Jira `SEC` ticket created; ISSO review within 5 business days |
| Container images in ECR | Trivy secret scan (`--scanners secret`) | On every image push + weekly | Critical finding → CI pipeline block + PagerDuty P2 |
| S3 buckets | Amazon Macie | Continuous | High-severity finding → PagerDuty P1 + ISSO email |

**Retroactive history scan status:** Last full scan run 2026-04-01. Result: 2 historical
findings identified — both were test credentials committed in 2024, never used in production,
now invalidated. Findings documented in Jira `SEC-1901` and `SEC-1902` (both closed).

### Certificate Management

cert-manager manages all TLS certificates for cluster-internal and ingress endpoints.
Certificate lifecycle:

- Issuance: Let's Encrypt (ACME HTTP-01 challenge) for public endpoints;
  cluster-internal self-signed CA (`lm-internal-ca` ClusterIssuer) for internal services
- Auto-renewal: cert-manager renews 30 days before expiry automatically
- Monitoring: Two-layer alert:
  1. Prometheus alert `cert-expiry-warning` fires if any `Certificate` object has
     `NotAfter` within **14 days** (backstop if auto-renew fails) → PagerDuty P1
  2. ACM certificates (ALB): AWS sends expiry notifications at **45 days** and **30 days**
     before expiry → ISSO email

Certificate private keys are stored in Kubernetes Secrets with restricted RBAC — only
the cert-manager ServiceAccount and the workload ServiceAccount for the specific service
have `get` access to the certificate Secret. No wildcard secret access in any namespace.

**Responsible Role:** ITOps (Okta password policy, MFA device management), Cloud Security Engineer (Secrets Manager rotation, KMS, Macie), Platform Engineer (cert-manager, Secrets Store CSI, CI gates), DevSecOps (gitleaks, Semgrep, secret scanning pipeline)

**Parameters:**
- Password minimum length: **16 characters**; breach corpus check: **Enabled**
- DB credential rotation: **30 days** (automatic)
- Third-party API key rotation: **90 days** (manual, 14-day pre-expiry Jira ticket)
- Certificate auto-renewal lead time: **30 days**; backstop alert: **14 days**
- Retroactive git history secret scan: **Quarterly**
- Container image secret scan: **On every push** (CI blocking)

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| Okta password policy `lm-password-policy` | Okta Admin → Security → Authenticators | 2026-04-07 |
| Secrets Manager rotation config for `lm-db-password` | `infra-iac/secrets/db-rotation.tf` + AWS Console | Per-commit |
| Secret rotation schedule and Jira tickets | GitHub Actions: `secret-rotation-check.yaml` + Jira `SEC` | Weekly |
| Kyverno `deny-env-secrets` policy | `platform-gitops/kyverno/deny-env-secrets.yaml` | Per-commit |
| Secrets Store CSI Driver manifests | `platform-gitops/secrets-store/` | Per-commit |
| gitleaks CI workflow | `platform-gitops/.github/workflows/pr-checks.yaml` | Per-commit |
| Retroactive history scan report Q1 2026 | Confluence: LM-SECURITY / IA / Secret-Scan-2026-Q1.md | 2026-04-01 |
| cert-manager Prometheus alert rule | `platform-gitops/monitoring/cert-expiry-alert.yaml` | Per-commit |
| AWS Config rule `secretsmanager-rotation-enabled-check` | AWS Console → Config → Rules | 2026-05-01 (compliant) |
| Macie S3 scan findings | AWS Console → Macie → Findings | Continuous |

**Test Procedure:**
1. Attempt to deploy a pod with a secret passed as an environment variable
   (`env.valueFrom.secretKeyRef`) — verify Kyverno `deny-env-secrets` blocks admission.
2. Commit a test file containing a mock AWS access key pattern to a test branch —
   verify gitleaks blocks the PR from merging.
3. Pull the Secrets Manager rotation configuration for `lm-db-password`:
   `aws secretsmanager describe-secret --secret-id lm-db-password`
   — verify `RotationEnabled: true` and `LastRotatedDate` is within 30 days.
4. Pull all cert-manager `Certificate` objects:
   `kubectl get certificate -A -o custom-columns=NAME:.metadata.name,EXPIRY:.status.notAfter`
   — verify no certificate expires within 14 days.
5. Pull the retroactive history scan report from Confluence — verify it was run within
   the last 90 days and all findings are either closed or have open Jira tickets with
   assigned owners.
6. Pull the Jira `SEC` project filtered by label `secret-rotation` — verify no rotation
   is overdue (all tickets show completion before the due date).

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| IA-5(1) Password-Based Authentication | Implemented | Okta `lm-password-policy`: 16-character minimum, breach corpus check (HIBP via ThreatInsight), 12-password history, no forced rotation (NIST SP 800-63B aligned), breach detection triggers forced reset. |
| IA-5(2) PKI Certificates | Implemented | cert-manager issues certificates from Let's Encrypt (public endpoints) and cluster-internal CA (internal services). Private keys stored in K8s Secrets with restricted RBAC. Auto-renewal 30 days before expiry. |
| IA-5(6) Protection of Authenticators | Implemented | All production secrets in AWS Secrets Manager. Secrets Store CSI Driver for pod injection (never environment variables). Break-glass credentials in physical safe (ISSO custody). FIDO2 private keys in hardware — never extractable. Kyverno `deny-env-secrets` blocks plaintext secret delivery to pods. |
| IA-5(7) No Embedded Unencrypted Static Authenticators | Implemented | gitleaks CI gate blocks new credential commits. Semgrep SAST `detect-hardcoded-credentials` rule blocks. Retroactive git history scans quarterly. Trivy secret scan on every image push. Macie on S3 buckets continuously. Last retroactive scan (2026-04-01): 2 historical findings — both invalidated and Jira-closed. |
| IA-5(11) Hardware-Based Authentication | Implemented (privileged) | FIDO2 YubiKey 5 required for all `links-matrix-admins` group members and break-glass AWS IAM accounts. Not yet deployed for standard users — accepted risk `RISK-ACCEPT-IA-001`; target Q2 2027. |

---

## What Makes This GREAT — Side-by-Side

| Dimension | Bad | Good | Great |
| --------- | --- | ---- | ----- |
| **MFA enforcement proof** | "Required" (asserted) | Policy names cited | MFA policy table with replay-resistance column; zero bypass conditions stated explicitly; CloudTrail log sample referenced; kube-bench check 1.2.2 confirms no static tokens |
| **IA-2(8) replay-resistance** | Not mentioned | Gap acknowledged, risk accepted | Risk acceptance document cited (`RISK-ACCEPT-IA-001`) with compensating control (ThreatInsight) and upgrade target date (Q2 2027) |
| **IA-3 service mesh gap** | Not mentioned | POA&M item created | POA&M item with 4 named compensating controls; mTLS status explicitly stated; auditor knows exactly what is and is not implemented |
| **IA-4(4) user status** | Not mentioned | "Not implemented — future review" | Fully implemented: `userType` Okta attribute, Workday SCIM mapping, 4 group types, OIDC claim propagation, contractor auto-expiry at contract end, vendor 90-day expiry |
| **Secret scanning scope** | Not mentioned | gitleaks in CI (new commits) | 5-mechanism table: CI (new commits), pre-commit (workstation), quarterly retroactive history scan, container image scan on push, Macie on S3; last retroactive scan results cited |
| **Credential rotation** | "Periodically" | Schedule described in prose | 8-row credential inventory table: type, location, period, mechanism (auto vs. manual), and monitoring control per credential class |
| **Secrets delivery to pods** | "Stored securely" | Secrets Store CSI mentioned | Kyverno `deny-env-secrets` (Enforce) blocks env-var delivery at admission; CSI Driver is the only permitted injection path; test procedure verifies block |
| **IA chain** | Never acknowledged | Implicitly connected | Explicitly in header: IA-4 identifiers → IA-2/IA-3 authentication → IA-5 credential binding |
