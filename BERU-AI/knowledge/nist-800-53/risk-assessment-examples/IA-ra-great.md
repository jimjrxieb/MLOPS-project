# Risk Assessment Evidence — IA Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Evidence collected fully supports all SSP claims. Control owners provided
> exact artifacts, dates, version numbers, and metrics on first request. Tool queries returned
> complete structured data with no gaps. Every SSP claim is traceable to a specific artifact
> with a retrievable location. All four controls receive PASS findings. No POA&M items required.
> This is the evidence standard a 3PAO expects to walk in and find.

**Assessment Date:** 2026-05-10
**Assessor:** GRC Engineer (grc-engineer group — read-only)
**Framework:** NIST 800-53 Rev 5
**Graded Against:** Links-Matrix SSP (see ssp-examples/IA-ssp-great.md)

---

## IA-2 — Identification and Authentication (Organizational Users)

**Control Owner:** ITOps
**Evidence Producer:** ITOps
**Cadence:** Continuous (IdP policy enforcement)

### SSP Claim
> The SSP asserts that MFA is enforced for all organizational users via SCP p-abc123def456
> at the AWS Organizations level. All console logins require FIDO2/WebAuthn via Okta Verify.
> ConsoleLogin events in CloudTrail confirm 0 MFA bypass attempts in the last 90 days.

### Evidence Request

**Interview — Questions asked of control owner (ITOps):**
1. Show me MFA enforcement — SCP or IdP policy?
2. Show me ConsoleLogin events with any MFA bypass attempts.

**Tool Query:** `GET /evidence/IA-2?env=great` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "IA-2", "env": "great", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "sufficient",
  "data": {
    "mfa_enforced_via_scp": true,
    "scp_id": "p-abc123def456",
    "console_login_events_90d": 2341,
    "mfa_not_used_logins": 0,
    "phishing_resistant_mfa": true,
    "mfa_type": "FIDO2/WebAuthn via Okta Verify"
  }
}
```

**Interview Response (Control Owner — ITOps):**
> "SCP p-abc123def456 enforces MFA at org level — any console login without MFA
> is denied by the SCP. 2,341 ConsoleLogin events in 90 days, 0 with MFA bypass.
> MFA type is FIDO2/WebAuthn via Okta Verify — phishing resistant. Credential report
> at s3://links-matrix-audit/iam/credential-report-2026-04-30.csv confirms 0 console
> access without MFA."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — SCP ID confirmed; 2,341 ConsoleLogin events with 0 bypass; FIDO2/WebAuthn type confirmed; phishing resistance confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | SCP enforced with ID confirmed; 2,341 logins with 0 bypass; FIDO2 phishing-resistant MFA |
| Impact | Low | Org-level SCP means even admin accounts cannot bypass MFA; phishing-resistant authentication type |
| **Residual Risk** | **Low** | All SSP claims verified by CloudTrail data and SCP configuration |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: SCP p-abc123def456 confirmed; 2,341 ConsoleLogin events with 0 MFA bypass; FIDO2/WebAuthn enforced for IA-2.
CONTROL: IA-2 — Identification and Authentication (Organizational Users)
ENHANCEMENT: IA-2(1) — Multi-Factor Authentication to Privileged Accounts
STATUS: PASS
EVIDENCE REVIEWED:
  - ITOps interview (SCP ID, event counts, MFA type, credential report path produced)
  - CloudTrail query (SCP p-abc123def456, 2341 ConsoleLogin events, 0 MFA bypass, FIDO2/WebAuthn)
  - Credential report: s3://links-matrix-audit/iam/credential-report-2026-04-30.csv
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: ITOps (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: MFA enforcement is fully evidenced. SCP p-abc123def456 enforces FIDO2/WebAuthn at the org level with 2,341 logins and zero bypass attempts. This control is audit-ready.
```

---

## IA-3 — Device Identification and Authentication

**Control Owner:** PlatEng
**Evidence Producer:** PlatEng
**Cadence:** Continuous (mTLS/workload identity)

### SSP Claim
> The SSP asserts that all Kubernetes workloads use mTLS in STRICT mode via Istio service mesh.
> SPIFFE IDs are assigned to all pods via SPIRE. AWS workloads use EC2 Instance Profiles
> for node identity. Workload identity is managed via AWS IRSA (IAM Roles for Service Accounts).

### Evidence Request

**Interview — Questions asked of control owner (PlatEng):**
1. Show me how workload identity is established for Kubernetes pods.

**Tool Query:** `GET /evidence/IA-3?env=great` — simulates: kubescape

**Tool Evidence (API Response):**
```json
{
  "control": "IA-3", "env": "great", "tool": "kubescape",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "sufficient",
  "data": {
    "mtls_enabled": true,
    "mtls_mode": "STRICT (Istio)",
    "spiffe_ids": true,
    "workload_identity_provider": "SPIRE + AWS IRSA",
    "node_identity": "EC2 Instance Profile per node role"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "Istio mTLS is in STRICT mode — PeerAuthentication policy is in
> platform-gitops/policies/ia/peer-authentication-strict.yaml. SPIFFE IDs are
> assigned to all pods via SPIRE — workload identity is spiffe://links-matrix.io/.
> IRSA is configured for all service accounts that call AWS APIs — Terraform at
> terraform/iam/irsa-bindings.tf. EC2 Instance Profiles provide node-level
> identity — one role per node group."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — mTLS STRICT mode confirmed; SPIFFE IDs confirmed; IRSA and EC2 Instance Profiles confirmed; policy artifacts named

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | Istio STRICT mode confirmed; SPIFFE IDs on all pods; IRSA for all API-calling workloads |
| Impact | Low | Mutual authentication enforced for all workload-to-workload communication; policy in git |
| **Residual Risk** | **Low** | All SSP claims verified by Kubescape data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: Istio mTLS STRICT mode, SPIFFE IDs, IRSA, and EC2 Instance Profiles all confirmed for IA-3.
CONTROL: IA-3 — Device Identification and Authentication
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - PlatEng interview (STRICT mode policy path, SPIFFE ID prefix, IRSA Terraform path produced)
  - Kubescape query (mtls STRICT, spiffe_ids true, SPIRE + AWS IRSA, EC2 Instance Profile per node)
  - mTLS policy: platform-gitops/policies/ia/peer-authentication-strict.yaml
  - IRSA bindings: terraform/iam/irsa-bindings.tf
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Workload identity is fully implemented. Istio mTLS STRICT, SPIFFE IDs on all pods, IRSA for all AWS API workloads, and EC2 Instance Profiles for node identity. This control is audit-ready.
```

---

## IA-4 — Identifier Management

**Control Owner:** ISSO
**Evidence Producer:** ITOps
**Cadence:** Quarterly identifier review

### SSP Claim
> The SSP asserts that user identifiers are reviewed quarterly. The last review was 2026-04-30,
> approved by the ISSO. Zero inactive identifiers (>90 days), zero orphaned identifiers,
> and zero shared identifiers exist. Naming conventions are documented in IAM-NAMING-POLICY-v1.2.pdf.

### Evidence Request

**Interview — Questions asked of control owner (ITOps):**
1. Show me your identifier review — any orphaned or shared identifiers?

**Tool Query:** `GET /evidence/IA-4?env=great` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "IA-4", "env": "great", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:10:00Z", "status": "sufficient",
  "data": {
    "identifier_review_last_run": "2026-04-30",
    "review_approver": "ISSO",
    "inactive_identifiers_gt90d": 0,
    "orphaned_identifiers": 0,
    "shared_identifiers": 0,
    "review_artifact": "Confluence: IA4-quarterly-review-2026-Q1.xlsx",
    "naming_convention_policy": "IAM-NAMING-POLICY-v1.2.pdf"
  }
}
```

**Interview Response (Control Owner — ITOps):**
> "Q1 identifier review completed 2026-04-30, approved by ISSO. Artifact is in
> Confluence: IA4-quarterly-review-2026-Q1.xlsx. Credential report shows 0 inactive
> identifiers >90 days, 0 orphaned, 0 shared. Naming convention policy is
> IAM-NAMING-POLICY-v1.2.pdf — stored in Confluence under Policies."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — Q1 review artifact produced; ISSO approval confirmed; 0 inactive, orphaned, and shared identifiers; naming policy named

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | Q1 review current with ISSO approval; 0 orphaned and shared identifiers; naming policy enforced |
| Impact | Low | Quarterly review cadence prevents credential accumulation; naming policy enables rapid identification |
| **Residual Risk** | **Low** | All SSP claims verified by CloudTrail data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: Q1 identifier review 2026-04-30 confirms 0 inactive, orphaned, and shared identifiers for IA-4. Artifact and naming policy produced.
CONTROL: IA-4 — Identifier Management
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - ITOps interview (review date, approver, artifact location, naming policy name produced)
  - CloudTrail query (review 2026-04-30, ISSO approver, 0 inactive/orphaned/shared, artifact in Confluence)
  - Review artifact: Confluence: IA4-quarterly-review-2026-Q1.xlsx
  - Naming policy: IAM-NAMING-POLICY-v1.2.pdf
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: ISSO (accountability) / ITOps (evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Identifier management is fully evidenced. Q1 review current with ISSO approval, zero orphaned or shared identifiers, and naming convention policy documented. This control is audit-ready.
```

---

## IA-5 — Authenticator Management

**Control Owner:** ITOps
**Evidence Producer:** ITOps / SecEng
**Cadence:** Continuous + rotation schedule

### SSP Claim
> The SSP asserts that no secrets exist in git repositories — confirmed by Gitleaks CI gate
> running on every push. Secrets are rotated on a 90-day schedule enforced via AWS Secrets
> Manager. Pre-commit hooks prevent secret commits. The credential report confirms 0 access
> keys older than 90 days.

### Evidence Request

**Interview — Questions asked of control owner (ITOps):**
1. Show me your secret rotation schedule and last rotation.
2. Show me Gitleaks CI gate configuration.

**Tool Query:** `GET /evidence/IA-5?env=great` — simulates: gitleaks

**Tool Evidence (API Response):**
```json
{
  "control": "IA-5", "env": "great", "tool": "gitleaks",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:15:00Z", "status": "sufficient",
  "data": {
    "secrets_found": 0,
    "rotation_schedule": "90 days — enforced via AWS Secrets Manager",
    "pre_commit_hook": true,
    "ci_gate_blocks_on_secret": true,
    "credential_report": "s3://links-matrix-audit/iam/credential-report-2026-04-30.csv"
  }
}
```

**Interview Response (Control Owner — ITOps):**
> "0 secrets found in git — Gitleaks CI gate blocks on any secret detection. Pre-commit
> hooks are deployed to all repos via the developer setup script. 90-day rotation is
> enforced automatically in AWS Secrets Manager — rotation Lambda fires on schedule.
> Credential report at s3://links-matrix-audit/iam/credential-report-2026-04-30.csv
> confirms 0 access keys older than 90 days."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 0 secrets in git; CI gate blocking confirmed; pre-commit hooks on all repos; 90-day rotation enforced; credential report produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 0 secrets in git; CI gate blocks on detection; rotation enforced by Secrets Manager Lambda |
| Impact | Low | Pre-commit hooks prevent credential commits; automated rotation means stale credentials cannot persist |
| **Residual Risk** | **Low** | All SSP claims verified by Gitleaks data and credential report |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 0 secrets in git, CI gate blocking, pre-commit hooks on all repos, and 90-day enforced rotation confirmed for IA-5.
CONTROL: IA-5 — Authenticator Management
ENHANCEMENT: IA-5(1) — Password-Based Authentication
STATUS: PASS
EVIDENCE REVIEWED:
  - ITOps interview (0 secrets, pre-commit deployment method, rotation Lambda, credential report path produced)
  - Gitleaks query (0 secrets, rotation enforced, pre_commit_hook true, ci_gate_blocks_on_secret true)
  - Credential report: s3://links-matrix-audit/iam/credential-report-2026-04-30.csv (0 keys >90 days)
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: ITOps (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Authenticator management is fully evidenced. Zero secrets in git, blocking CI gate, pre-commit hooks on all repos, and automated 90-day rotation. This control is audit-ready.
```
