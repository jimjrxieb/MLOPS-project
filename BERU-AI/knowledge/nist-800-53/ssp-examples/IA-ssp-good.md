# System Security Plan — Identification and Authentication (IA) Family

## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** This SSP would pass a readiness review with 3-5 clarification items.
> Okta, IRSA, Secrets Manager, and cert-manager are all named. MFA is enforced, not just
> available. Gaps: IA-3 has no bidirectional/mTLS coverage (service mesh not deployed),
> IA-5 secret scanning is pre-commit only with no retroactive history scan,
> IA-4(4) user-status categorization is not implemented, and IA-2(8) replay-resistance
> is asserted but not evidenced for non-privileged accounts.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Final Draft — Pending ISSO Signature

---

## IA-2 — Multi-Factor Authentication

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

MFA is enforced for all Links-Matrix Platform access through Okta as the authoritative
identity provider. Enforcement is policy-based — users cannot authenticate without
satisfying the MFA requirement regardless of browser, network, or client.

**MFA enforcement policies (Okta Sign-On Policies):**

- **Privileged access policy (`lm-privileged-mfa`):** Applied to users in the
  `links-matrix-admins` Okta group. Requires FIDO2 hardware key (YubiKey 5 series).
  TOTP and SMS are not permitted for this group. No network exclusions — MFA required
  from any location including corporate network.

- **Standard access policy (`lm-standard-mfa`):** Applied to all other users. Requires
  Okta Verify push notification (TOTP fallback permitted; SMS not permitted). No
  network exclusions.

**Kubernetes API access:** EKS OIDC authentication via `okta-aws-cli` requires a valid
Okta session with MFA satisfied before an OIDC token is issued. Static kubeconfig tokens
are not distributed — the cluster API server has `--token-auth-file` disabled.

**Break-glass accounts:** Two break-glass IAM users (`lm-break-glass-01`, `lm-break-glass-02`)
have hardware MFA devices (YubiKey) attached in AWS IAM. Break-glass use triggers a
CloudTrail alarm and PagerDuty P1 alert to the ISSO within 5 minutes.

**Responsible Role:** ITOps (Okta policy ownership), Cloud Security Engineer (AWS IAM MFA, break-glass)

**Parameters:**
- Privileged MFA method: FIDO2 hardware key (YubiKey 5) — no fallback
- Standard MFA method: Okta Verify push (TOTP fallback; SMS prohibited)
- MFA network exclusions: None — enforced from all locations
- Break-glass MFA: Hardware key required; use alerts P1 to ISSO

**Evidence / Artifacts:**
- Okta Sign-On Policy configuration (`lm-privileged-mfa`, `lm-standard-mfa`) — Okta Admin console
- AWS IAM MFA device list for break-glass accounts (`aws iam list-mfa-devices`)
- CloudTrail authentication log sample showing `mfaAuthenticated: true`
- Break-glass PagerDuty alert configuration (`infra-iac/monitoring/break-glass-alert.tf`)

**Enhancements Addressed:**
- **IA-2(1):** FIDO2 hardware key required for all privileged account logins. No bypass conditions.
- **IA-2(2):** Okta Verify push required for all non-privileged account logins. SMS prohibited.
- **IA-2(8):** FIDO2 (WebAuthn) for privileged accounts is replay-resistant by design — challenge-response bound to origin, no replayable OTP. *(Note: Okta Verify push for standard accounts uses a time-bounded push notification — not fully replay-resistant in the FIDO2 sense. Upgrade path to FIDO2 for all users is in the IA roadmap.)*
- **IA-2(12):** Not applicable — Links-Matrix is a commercial cloud system, not a federal PIV-required environment. Documented in ADR-021.

---

## IA-3 — Device Identification and Authentication

**Implementation Status:** Implemented

**Control Origination:** Hybrid (Inherited from AWS IRSA; System-Specific for K8s workload identity)

**Implementation Description:**

Device and workload identity on the Links-Matrix Platform is implemented through
two mechanisms:

**AWS workload identity (IRSA):**
All Kubernetes workloads that access AWS services authenticate using IAM Roles for
Service Accounts (IRSA). Each workload's ServiceAccount has an `eks.amazonaws.com/role-arn`
annotation linking it to a specific IAM role. The EKS OIDC provider
(`oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE`)
issues signed OIDC tokens that AWS STS validates before allowing role assumption.
No static IAM access keys are used by application workloads. This is enforced by
CI policy: the `infra-iac` repo rejects any Terraform creating an access key for
an application IAM user.

**Worker node authentication:**
EKS worker nodes authenticate to the cluster API server using a node identity certificate
issued by the EKS-managed CA. Node bootstrap tokens are single-use and automatically
revoked after the first successful join. The `aws-auth` ConfigMap maps node IAM roles
to K8s RBAC groups — node identity is verified cryptographically, not by network location.

**Service-to-service authentication:**
A service mesh is not currently deployed on the Links-Matrix Platform. Service-to-service
calls within the cluster rely on Kubernetes NetworkPolicy microsegmentation (restricting
which pods can reach which endpoints) rather than mTLS mutual authentication. This is
a known gap relative to IA-3(1) — bidirectional cryptographic authentication between
services is not implemented. This is documented as POA&M item `IA-3-001` with a target
of deploying Linkerd in Q4 2026.

**Responsible Role:** Platform Engineer (IRSA, node identity, NetworkPolicy), Cloud Security Engineer (EKS OIDC provider configuration)

**Parameters:**
- AWS workload identity: IRSA (OIDC-based, no static access keys)
- Node bootstrap: Single-use token, auto-revoked post-join
- Service-to-service mTLS: Not implemented (POA&M `IA-3-001`, target Q4 2026)

**Evidence / Artifacts:**
- IRSA role annotation on ServiceAccount manifests (`platform-gitops/serviceaccounts/`)
- EKS OIDC provider configuration (`infra-iac/eks/oidc.tf`)
- AWS Config custom rule: `detect-static-access-keys-in-workloads` (0 findings)
- POA&M item `IA-3-001` (Confluence: LM-SECURITY / POA&M)

**Enhancements Addressed:**
- **IA-3(1):** Not fully implemented. IRSA provides cryptographic workload-to-AWS authentication (one-way from K8s to AWS). Bidirectional mTLS between services within the cluster is not deployed. This is documented in POA&M `IA-3-001` with target Q4 2026. NetworkPolicy provides compensating network-layer control.

---

## IA-4 — Identifier Management

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

**Human identifiers:**
All human user identifiers are provisioned through Okta as the authoritative identity
source. Each identifier is linked to a named individual via the Workday HRIS integration.
Generic or shared accounts are prohibited by policy (IAM-POL-003, Confluence:
LM-SECURITY / Policies / IAM-POL-003). The Okta Admin console is configured to
require a unique email address per user — duplicate email address registration is
technically blocked.

Identifiers are deactivated within 2 hours of employment termination via the Workday→Okta
SCIM integration (see AC-2). Identifiers are not deleted for 30 days post-deactivation
to preserve audit trail linkage. After 30 days, the identifier is permanently deleted.

Identifier reuse: Okta user objects are permanently deleted after 30 days — the username
(email address) is not reissued to a different person for a minimum of 6 months after
deletion. This is enforced by IT Operations procedure (ITO-PROC-012) and verified at
each quarterly access review.

Inactive identifier disabling: Okta lifecycle rule disables identifiers with no
authentication activity for 30 days (see AC-2).

**Service account identifiers:**
Kubernetes ServiceAccounts follow the naming convention `<workload>-sa` (e.g.,
`lm-api-sa`, `lm-worker-sa`). Each ServiceAccount manifest includes required annotations:
`secteam.io/owner` (team name) and `secteam.io/purpose` (function description).
Generic names (`default`, `app`, `service`) are blocked by Kyverno policy
`require-sa-annotation` (Enforce mode). AWS IAM role names for workloads follow the
convention `lm-<environment>-<workload>-role`.

**Responsible Role:** ISSO (identifier policy), ITOps (Okta provisioning, inactivity enforcement), Platform Engineer (K8s ServiceAccount naming)

**Parameters:**
- Identifier uniqueness: Enforced technically (Okta unique email requirement)
- Offboarding deactivation SLA: 2 hours (Workday→Okta SCIM)
- Inactivity disable period: 30 days
- Identifier retention post-deactivation: 30 days (audit trail)
- Identifier reuse prevention: 6 months minimum after permanent deletion

**Evidence / Artifacts:**
- Okta user provisioning workflow (Workday SCIM integration config)
- IAM Policy IAM-POL-003 prohibiting shared accounts (Confluence: LM-SECURITY / Policies)
- Kyverno `require-sa-annotation` policy enforcing ServiceAccount naming
- Quarterly access review records (Confluence: LM-SECURITY / Access Reviews)
- IT Operations procedure ITO-PROC-012 (identifier reuse prevention)

**Enhancements Addressed:**
- **IA-4(4):** Not implemented. User status categorization (employee vs. contractor vs. vendor) is tracked in Workday but not reflected in Okta identifier attributes or group membership. Access policy does not currently differentiate by worker category. This is a process maturity gap documented for the next annual review — not currently a POA&M item as access policy is role-based rather than worker-type-based.

---

## IA-5 — Authenticator Management

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

**Password policy:**
Okta enforces the following password policy (`lm-password-policy`) for all human
accounts: minimum 16 characters, no character class requirements (length-only
per NIST SP 800-63B), password checked against the HaveIBeenPwned breach corpus
at set time (Okta ThreatInsight integration), no maximum age (NIST-aligned), 10 password
history enforced (no reuse of last 10 passwords).

**Secrets management:**
All application secrets (database credentials, API keys, third-party tokens) are stored
in AWS Secrets Manager. Pods access secrets via IRSA — the `lm-api-sa` ServiceAccount
assumes the `lm-api-secrets-read` IAM role, which has `secretsmanager:GetSecretValue`
on specific secret ARNs only. Secrets are never mounted as environment variables;
they are retrieved at runtime via the AWS Secrets Manager SDK or via the Secrets Store
CSI Driver (`platform-gitops/secrets-store/`).

**Secret rotation:**
Database credentials (`lm-db-password`) rotate automatically every 30 days via
AWS Secrets Manager automatic rotation (Lambda rotation function). Third-party API
keys are rotated manually on a 90-day schedule tracked in Jira (`SEC` project,
label: `secret-rotation`). A monthly reminder is auto-created by a GitHub Actions
scheduled workflow.

**Certificate management:**
cert-manager is deployed in the cluster (`platform-gitops/cert-manager/`) and issues
TLS certificates for all ingress endpoints from Let's Encrypt (ACME). Certificates
auto-renew 30 days before expiry. A Prometheus alert fires if any cert-manager
certificate object shows `NotAfter` within 14 days (as a backstop if auto-renew fails).

**Secret scanning (CI):**
gitleaks is run as a required CI check on every PR to `platform-gitops` and `infra-iac`.
A gitleaks finding blocks merge. The pre-commit hook (`detect-secrets`) is recommended
for developers but not enforced at the workstation level.

**Responsible Role:** ITOps (Okta password policy), Cloud Security Engineer (Secrets Manager, rotation), Platform Engineer (cert-manager, Secrets Store CSI), DevSecOps (gitleaks CI integration)

**Parameters:**
- Password minimum length: 16 characters
- Password history: 10 (no reuse)
- Breach corpus check: Enabled (Okta ThreatInsight / HIBP)
- DB credential rotation: 30 days (automatic)
- Third-party API key rotation: 90 days (manual, Jira-tracked)
- Certificate auto-renewal lead time: 30 days before expiry
- Certificate expiry backstop alert: 14 days before expiry

**Evidence / Artifacts:**
- Okta password policy `lm-password-policy` (Okta Admin console)
- AWS Secrets Manager rotation configuration for `lm-db-password`
- Secrets Store CSI Driver manifests (`platform-gitops/secrets-store/`)
- cert-manager Prometheus alert rule (`platform-gitops/monitoring/cert-expiry-alert.yaml`)
- gitleaks CI workflow (`platform-gitops/.github/workflows/pr-checks.yaml`)
- Jira `SEC` project — `secret-rotation` label tickets (last 90 days)

**Enhancements Addressed:**
- **IA-5(1):** Okta enforces 16-character minimum, breach corpus check, and 10-password history. No character complexity theater. NIST SP 800-63B aligned.
- **IA-5(2):** cert-manager issues certificates from Let's Encrypt (publicly trusted CA). Private key access restricted to cert-manager service account. *(Note: internal service-to-service certificates from a private CA are not issued — relevant if mTLS is deployed per IA-3 POA&M item.)*
- **IA-5(6):** All production secrets stored in AWS Secrets Manager. No secrets in environment variables or ConfigMaps. Secrets Store CSI Driver used for pod-level secret injection.
- **IA-5(7):** gitleaks CI blocks secrets in new commits. *(Note: retroactive scan of full git history has not been performed — historical embedded credentials may exist. Scheduled for Q3 2026.)*
- **IA-5(11):** FIDO2 hardware keys (YubiKey) used for privileged account authentication (see IA-2). Not yet deployed for all standard users.

---

## What Makes This GOOD (But Not Great) — Examiner's Notes

| Control | Strengths | Gaps |
| ------- | --------- | ---- |
| IA-2 | FIDO2 for privileged named, push MFA for standard, SMS prohibited, break-glass alert defined | IA-2(8) replay-resistance gap for standard accounts (Okta push is not FIDO2); no authentication log sample showing actual second-factor challenge |
| IA-3 | IRSA with OIDC specifics, node bootstrap lifecycle, mTLS gap honestly disclosed in POA&M | The POA&M item is the right call but it means IA-3(1) is unimplemented — compensating NetworkPolicy control is weaker than bidirectional auth |
| IA-4 | Naming convention, Kyverno enforcement, 30-day inactivity, 6-month reuse prevention | IA-4(4) not implemented — contractor/employee distinction in identifiers is a gap; the "not a POA&M item" rationale is thin |
| IA-5 | Real rotation schedule, Secrets Manager, cert-manager, gitleaks in CI | Retroactive git history scan not done — historical secrets exposure unquantified; pre-commit hook recommended but not enforced; third-party API rotation is manual Jira-tracked (can slip) |
| All | IA chain is implicitly honored | No explicit acknowledgment that IA-4 identifiers feed IA-2/IA-3 authentication and IA-5 credential binding |
