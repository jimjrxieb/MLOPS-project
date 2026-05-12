# Risk Assessment Evidence — AC Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Evidence collected fully supports all SSP claims. Control owners provided
> exact artifacts, dates, version numbers, and SLA metrics on first request. Tool queries
> returned complete structured data with no gaps. Every SSP claim is traceable to a specific
> artifact with a retrievable location. All five controls receive PASS findings. No POA&M
> items required. This is the evidence standard a 3PAO expects to walk in and find.

**Assessment Date:** 2026-05-10
**Assessor:** GRC Engineer (grc-engineer group — read-only)
**Framework:** NIST 800-53 Rev 5
**Graded Against:** Links-Matrix SSP (see ssp-examples/AC-ssp-great.md)

---

## AC-2 — Account Management

**Control Owner:** ISSO
**Evidence Producer:** ITOps
**Cadence:** Quarterly access review

### SSP Claim
> The SSP asserts that account lifecycle is automated via Okta SCIM to AWS IAM. Terminated users
> are disabled within 4 hours and fully deprovisioned within 24 hours. Quarterly access reviews
> are completed by ITOps, signed off by the ISSO, and stored in Confluence. Service accounts
> require ISSO approval and are inventoried in Terraform.

### Evidence Request

**Interview — Questions asked of control owner (ITOps):**
1. Show me the last completed access review — who approved it and when was it run?
2. Show me how terminated users are removed from the system. Is it automated or manual?
3. Show me the process for creating a service account — what approval and documentation is required?
4. Show me accounts inactive for more than 90 days that are still enabled.

**Tool Query:** `GET /evidence/AC-2?env=great` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "AC-2", "env": "great", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "sufficient",
  "data": {
    "trail_enabled": true, "log_validation": true,
    "DeleteUser_events_90d": 47, "CreateUser_events_90d": 63,
    "last_access_review": "2026-04-30",
    "access_review_approver": "ISSO J.Rivera",
    "iam_credential_report": "s3://links-matrix-audit/iam/credential-report-2026-04-30.csv",
    "access_keys_older_90d": 0,
    "inactive_accounts_90d": 0,
    "service_account_inventory": "terraform/iam/service-accounts.tf",
    "offboarding_sla_4h_compliance": "100%",
    "error": null
  }
}
```

**Interview Response (Control Owner — ITOps):**
> "Last access review: 2026-04-30, approved by ISSO J.Rivera. The report is in Confluence:
> IA2-quarterly-review-2026-Q1.xlsx. Automation: Okta SCIM to AWS IAM — terminations trigger
> a disable within 4 hours by policy, full deprovision within 24 hours. We had 47 DeleteUser
> events in CloudTrail over the last 90 days. Credential report is at
> s3://links-matrix-audit/iam/credential-report-2026-04-30.csv — 0 access keys older than
> 90 days. Service account inventory is in terraform/iam/service-accounts.tf, required ISSO
> ticket before any new entry merges."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — all claims confirmed by artifact and tooling

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | Automated lifecycle confirmed; 0 stale access keys; 0 inactive accounts; 100% offboarding SLA |
| Impact | Low | Quarterly review with ISSO sign-off; service account inventory in GitOps; immutable audit trail |
| **Residual Risk** | **Low** | All SSP claims verified by artifact and tool data |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: ITOps produced full access review artifact, CloudTrail IAM event data, and credential report for AC-2. All SSP claims verified.
CONTROL: AC-2 — Account Management
ENHANCEMENT: AC-2(1) — Automated System Account Management
STATUS: PASS
EVIDENCE REVIEWED:
  - ITOps interview (exact dates, artifact paths, SLA metrics produced on request)
  - CloudTrail query (trail enabled, log validation on, 47 DeleteUser + 63 CreateUser events in 90d)
  - Credential report: s3://links-matrix-audit/iam/credential-report-2026-04-30.csv
  - Access review: IA2-quarterly-review-2026-Q1.xlsx, approved 2026-04-30 by ISSO J.Rivera
  - Service account inventory: terraform/iam/service-accounts.tf
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: ISSO (accountability) / ITOps (evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Account management is fully evidenced. Automated lifecycle via Okta SCIM, zero stale credentials, 100% offboarding SLA compliance, quarterly reviews current and signed. This control is audit-ready.
```

---

## AC-3 — Access Enforcement

**Control Owner:** PlatEng
**Evidence Producer:** PlatEng / SecEng
**Cadence:** Continuous (policy-as-code)

### SSP Claim
> The SSP asserts that RBAC is enforced via Kubernetes RBAC policies with no wildcard roles.
> Kyverno admission control blocks ClusterAdmin bindings. Access enforcement is tested
> continuously in CI and audited quarterly by SecEng.

### Evidence Request

**Interview — Questions asked of control owner (PlatEng):**
1. Show me your Kubernetes RBAC configuration — are any ClusterAdmin bindings active?
2. Show me the Kyverno admission policy that enforces RBAC restrictions.
3. Show me how access enforcement is validated — is there a CI gate?

**Tool Query:** `GET /evidence/AC-3?env=great` — simulates: kubescape

**Tool Evidence (API Response):**
```json
{
  "control": "AC-3", "env": "great", "tool": "kubescape",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "sufficient",
  "data": {
    "rbac_scan_run": true,
    "kubescape_score": 94,
    "wildcard_roles": 0,
    "clusteradmin_bindings": 0,
    "kyverno_policy_deployed": true,
    "kyverno_policy_name": "restrict-clusteradmin-binding.yaml",
    "last_quarterly_audit": "2026-04-01",
    "ci_gate_active": true,
    "error": null
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "Kubescape score 94/100. 0 wildcard roles. 0 ClusterAdmin bindings. Kyverno policy
> restrict-clusteradmin-binding.yaml enforces this at admission — it's in platform-gitops/policies/.
> Last RBAC review was 2026-04-01, report is at platform-gitops/security/rbac-audit-2026-Q1.md.
> The CI gate runs kubescape on every PR to the platform-gitops repo."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — RBAC clean state confirmed by scan; Kyverno policy named and located; CI gate active

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | Kubescape confirms 0 wildcard roles and 0 ClusterAdmin bindings; admission control enforced at API |
| Impact | Low | Continuous enforcement via admission control means misconfiguration is blocked before it reaches production |
| **Residual Risk** | **Low** | All SSP claims verified by automated scan and quarterly audit artifact |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: Kubescape scan confirms 0 wildcard roles and 0 ClusterAdmin bindings for AC-3. Kyverno admission control and CI gate are active. All SSP claims verified.
CONTROL: AC-3 — Access Enforcement
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - PlatEng interview (Kubescape score, policy name, quarterly audit date produced)
  - Kubescape query (score 94/100, 0 wildcard roles, 0 ClusterAdmin bindings, Kyverno deployed)
  - Kyverno policy: restrict-clusteradmin-binding.yaml (platform-gitops/policies/)
  - RBAC quarterly audit: platform-gitops/security/rbac-audit-2026-Q1.md (2026-04-01)
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Access enforcement is fully implemented and continuously verified. Zero wildcard roles, zero ClusterAdmin bindings, Kyverno admission control blocking violations at the API level. This control is audit-ready.
```

---

## AC-5 — Separation of Duties

**Control Owner:** ISSO
**Evidence Producer:** CompO
**Cadence:** Annual + change-triggered

### SSP Claim
> The SSP asserts that development and production environments are separated by RBAC at the
> namespace level. No developer has write access to production namespaces. A separation of
> duties matrix is maintained in Confluence and reviewed annually by the ISSO.

### Evidence Request

**Interview — Questions asked of control owner (ISSO):**
1. Show me your separation of duties matrix — who has access to what and where is it documented?
2. Show me evidence that developers cannot deploy directly to production.
3. Show me the last annual SoD review record.

**Tool Query:** `GET /evidence/AC-5?env=great` — simulates: kubescape

**Tool Evidence (API Response):**
```json
{
  "control": "AC-5", "env": "great", "tool": "kubescape",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:10:00Z", "status": "sufficient",
  "data": {
    "sod_violations": 0,
    "privileged_ns_count": 2,
    "dev_prod_namespace_separation": true,
    "developer_prod_write_access": false,
    "sod_matrix_artifact": "Confluence: rbac-sod-matrix-v2.md",
    "last_annual_review_date": "2026-01-15",
    "last_annual_review_approver": "ISSO M.Chen",
    "error": null
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "0 SoD violations in Kubescape. Dev and prod are in separate namespaces — Kubescape
> confirms no developer has write access to prod namespaces. The role separation matrix is
> in Confluence: rbac-sod-matrix-v2.md, last updated 2026-01-10. Annual review completed
> 2026-01-15, signed by me (M.Chen). The ArgoCD pipeline is the only deployment path
> to production — developers cannot deploy directly."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — namespace separation confirmed; SoD matrix produced with version and date; annual review dated and signed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 0 SoD violations; developer prod write access blocked and confirmed by scan; deployment gate enforced |
| Impact | Low | Technical separation enforced at namespace RBAC level; documentation current and signed |
| **Residual Risk** | **Low** | All SSP claims verified by scan and artifact |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: Kubescape confirms 0 SoD violations and no developer write access to production namespaces for AC-5. SoD matrix and annual review artifact produced.
CONTROL: AC-5 — Separation of Duties
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - ISSO interview (SoD matrix location, review date, approver produced)
  - Kubescape query (0 violations, dev/prod namespace separation confirmed, 0 developer prod write access)
  - SoD matrix: Confluence: rbac-sod-matrix-v2.md (updated 2026-01-10)
  - Annual review: 2026-01-15, signed by ISSO M.Chen
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: ISSO (accountability) / CompO (evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Separation of duties is fully implemented and documented. Kubescape confirms technical enforcement and the SoD matrix with signed annual review is current. This control is audit-ready.
```

---

## AC-6 — Least Privilege

**Control Owner:** CloudSec
**Evidence Producer:** CloudSec
**Cadence:** Quarterly access review

### SSP Claim
> The SSP asserts that all IAM policies are scanned quarterly by Prowler. Wildcard action and
> star-resource policies are prohibited by SCP. Only two break-glass admin accounts exist,
> both MFA-protected and CloudTrail-alerted. Permission boundaries are enforced on all roles.

### Evidence Request

**Interview — Questions asked of control owner (CloudSec):**
1. Show me your last Prowler IAM scan — how many wildcard policies exist?
2. Show me the SCP that prohibits wildcard policies.
3. Show me the break-glass account inventory and MFA enforcement evidence.

**Tool Query:** `GET /evidence/AC-6?env=great` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "AC-6", "env": "great", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:15:00Z", "status": "sufficient",
  "data": {
    "iam_policies_scanned": 94,
    "wildcard_action_policies": 0,
    "star_resource_policies": 0,
    "admin_users_count": 2,
    "admin_users_mfa_enforced": true,
    "permission_boundaries_enforced": true,
    "roles_without_boundary": 0,
    "scp_artifact": "infra-iac/org-policies/scp-deny-wildcard-iam.json",
    "last_privilege_review": "2026-04-15",
    "privilege_review_artifact": "s3://links-matrix-audit/iam/privilege-review-2026-Q1.pdf",
    "error": null
  }
}
```

**Interview Response (Control Owner — CloudSec):**
> "94 IAM policies scanned, 0 wildcard action policies, 0 star-resource policies. 2 admin
> accounts (break-glass only), both MFA required and CloudTrail-alerted via CloudWatch alarm
> lm-priv-function-alarm. Permission boundaries enforced on all roles — 0 roles without
> boundary. SCP is at infra-iac/org-policies/scp-deny-wildcard-iam.json. Last privilege
> review was 2026-04-15, artifact at s3://links-matrix-audit/iam/privilege-review-2026-Q1.pdf."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — Prowler scan clean; 0 wildcards; break-glass inventory produced; permission boundaries confirmed; SCP located

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 0 wildcard policies; permission boundaries on all roles; SCP enforces org-level deny |
| Impact | Low | Break-glass accounts limited to 2 with MFA required and CloudTrail alerting on every use |
| **Residual Risk** | **Low** | All SSP claims verified by automated scan and named artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: Prowler scan of 94 IAM policies confirms 0 wildcard action policies and 0 star-resource policies for AC-6. Break-glass inventory, SCP, and privilege review artifact all produced.
CONTROL: AC-6 — Least Privilege
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - CloudSec interview (exact scan counts, SCP path, privilege review artifact produced)
  - Prowler query (94 policies scanned, 0 wildcard actions, 0 star-resource, permission boundaries enforced)
  - SCP: infra-iac/org-policies/scp-deny-wildcard-iam.json
  - Privilege review: s3://links-matrix-audit/iam/privilege-review-2026-Q1.pdf (2026-04-15)
  - Break-glass: 2 accounts, MFA enforced, CloudWatch alarm lm-priv-function-alarm active
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: CloudSec (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Least privilege is fully enforced and evidenced. Zero wildcard IAM policies, permission boundaries on all roles, SCP enforcement at org level, and break-glass accounts limited with MFA and alerting. This control is audit-ready.
```

---

## AC-17 — Remote Access

**Control Owner:** PlatEng
**Evidence Producer:** SecEng
**Cadence:** Annual + change-triggered

### SSP Claim
> The SSP asserts that MFA is required for all remote access. VPN session logs are captured
> in CloudTrail. A remote access policy document (v3.1) is maintained in Confluence and
> reviewed annually. Zero unauthorized remote access attempts occurred in the last 90 days.

### Evidence Request

**Interview — Questions asked of control owner (SecEng):**
1. Show me your remote access policy — what MFA types are permitted and what are the session controls?
2. Show me VPN session logs for the last 30 days.
3. Show me how remote access is terminated when an employee is offboarded.

**Tool Query:** `GET /evidence/AC-17?env=great` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "AC-17", "env": "great", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:20:00Z", "status": "sufficient",
  "data": {
    "vpn_session_logs": true,
    "vpn_session_count_90d": 1247,
    "unauthorized_access_attempts_90d": 0,
    "remote_access_policy_artifact": "Confluence: LM-SECURITY / Policies / RAP-001",
    "policy_version": "v3.1",
    "policy_review_date": "2026-03-15",
    "policy_reviewer": "ISSO M.Chen",
    "mfa_enforced": true,
    "mfa_type": "FIDO2/WebAuthn",
    "session_auto_termination_minutes": 240,
    "error": null
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "Remote access policy v3.1, reviewed 2026-03-15 by ISSO M.Chen — it's in Confluence at
> LM-SECURITY / Policies / RAP-001. MFA is required via FIDO2/WebAuthn for all VPN sessions.
> 1,247 VPN sessions in the last 90 days, 0 unauthorized access attempts. Sessions
> auto-terminate at 4 hours. When an employee is offboarded, Okta SCIM revokes their VPN
> certificate within 2 hours of the HR termination event — same SLA as account disable.
> CloudTrail captures all VPN session start/end events."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 1,247 VPN sessions logged; 0 unauthorized attempts; policy v3.1 produced with review date; MFA type confirmed; session termination SLA confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | FIDO2/WebAuthn MFA required; 0 unauthorized attempts in 90 days; session auto-termination at 4 hours |
| Impact | Low | Full session logging in CloudTrail; policy current and signed; offboarding SLA matches account lifecycle |
| **Residual Risk** | **Low** | All SSP claims verified by CloudTrail data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: CloudTrail confirms 1,247 VPN sessions and 0 unauthorized access attempts over 90 days for AC-17. Remote access policy v3.1, MFA type, and session controls fully evidenced.
CONTROL: AC-17 — Remote Access
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - SecEng interview (policy version, review date, session count, MFA type, offboarding SLA produced)
  - CloudTrail query (1,247 VPN sessions in 90d, 0 unauthorized attempts, MFA enforced, session termination 240 min)
  - Remote access policy: Confluence: LM-SECURITY / Policies / RAP-001 (v3.1, reviewed 2026-03-15)
  - MFA: FIDO2/WebAuthn enforced for all sessions
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: PlatEng (accountability) / SecEng (evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Remote access controls are fully implemented and evidenced. FIDO2/WebAuthn MFA, 1,247 logged sessions with zero unauthorized attempts, policy current and signed, and offboarding integration confirmed. This control is audit-ready.
```
