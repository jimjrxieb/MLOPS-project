# Risk Assessment Evidence — AC Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** Evidence collected is partially sufficient. Control owners named specific
> tools and processes but could not produce exact artifacts, dates, or metrics. Tool queries
> returned partial data — some booleans confirmed but key counts and timestamps absent. All
> five controls receive PARTIAL findings requiring POA&M items to close the evidence gaps
> before the next audit cycle.

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

**Tool Query:** `GET /evidence/AC-2?env=good` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "AC-2", "env": "good", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "partial",
  "data": {
    "trail_enabled": true, "log_validation": true,
    "DeleteUser_events_90d": 12, "CreateUser_events_90d": 18,
    "last_access_review": null,
    "iam_credential_report": "exists — last export date not retrievable via current permissions",
    "inactive_accounts_90d": null,
    "error": "Access review records not indexed in CloudTrail — manual artifact required"
  }
}
```

**Interview Response (Control Owner — ITOps):**
> "We run quarterly access reviews. ITOps does them and the ISSO signs off. CloudTrail is
> enabled for IAM events. The last review was Q1 but I don't have the exact date handy.
> Okta handles account disabling when HR marks someone terminated — it's automated. Service
> accounts go through a Jira ticket but I'd need to pull the template to show you the fields."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — automation confirmed in principle, review cadence unconfirmed by artifact

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | CloudTrail enabled and IAM events present; access review cadence unverified by record |
| Impact | Medium | Automation partially confirmed; gap in review artifact means privilege creep may go undetected |
| **Residual Risk** | **High** | Control likely functioning but not fully evidenced for audit |

**Finding:** PARTIAL
**Evidence Gap:** Last access review date not confirmed. Credential report export date unavailable. Inactive account count not retrieved. No Q1 review artifact produced.

**BERU Finding:**
```
FINDING: ITOps confirmed quarterly access review process and Okta automation but could not produce the Q1 2026 review artifact or exact timestamp for AC-2.
CONTROL: AC-2 — Account Management
ENHANCEMENT: AC-2(1) — Automated System Account Management
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - ITOps verbal statement (process described, no artifact produced)
  - CloudTrail query (trail enabled, IAM events present, 12 DeleteUser + 18 CreateUser events in 90d)
EVIDENCE GAP: Q1 access review artifact not produced, credential report export date unavailable, inactive account count not retrieved
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: ISSO (accountability) / ITOps (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Account management is partially evidenced — CloudTrail confirms IAM activity and the team describes an automated offboarding process, but no signed quarterly access review record was produced. An auditor would flag this as an open finding. Retrieve and archive the Q1 review artifact to close.
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

**Tool Query:** `GET /evidence/AC-3?env=good` — simulates: kubescape

**Tool Evidence (API Response):**
```json
{
  "control": "AC-3", "env": "good", "tool": "kubescape",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "partial",
  "data": {
    "rbac_scan_run": true,
    "kubescape_score": null,
    "wildcard_roles": 3,
    "clusteradmin_bindings": null,
    "kyverno_policy_deployed": true,
    "last_quarterly_audit": null,
    "error": "ClusterAdmin binding count not accessible at grc-engineer permission level"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "Kubescape runs in the cluster. We had 3 wildcard roles flagged but they're being reviewed.
> No ClusterAdmin bindings that I know of. Kyverno has an admission policy for that — I can
> pull the name but the full YAML is in the GitOps repo."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — Kyverno deployed and Kubescape running; wildcard roles flagged and under review; ClusterAdmin binding count not confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Kubescape deployed and running; 3 wildcard roles flagged; ClusterAdmin count unconfirmed |
| Impact | High | Wildcard roles and unverified ClusterAdmin bindings represent exploitable privilege escalation paths |
| **Residual Risk** | **High** | Partial tooling confirmed but open wildcard role findings and missing ClusterAdmin audit |

**Finding:** PARTIAL
**Evidence Gap:** Wildcard role remediation status not confirmed. ClusterAdmin binding count not available at assessor permission level. Quarterly audit date not provided.

**BERU Finding:**
```
FINDING: Kubescape is deployed and Kyverno is active for AC-3, but 3 wildcard roles are flagged as under review and ClusterAdmin binding count could not be confirmed.
CONTROL: AC-3 — Access Enforcement
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (tool names and process described)
  - Kubescape query (scan confirmed running, 3 wildcard roles flagged, ClusterAdmin count inaccessible)
EVIDENCE GAP: Wildcard role remediation status not confirmed, ClusterAdmin binding audit not available, quarterly audit date not produced
RISK:
  Likelihood: Medium
  Impact: High
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Access enforcement infrastructure is in place but the 3 open wildcard roles must be resolved or formally accepted as exceptions before this control can be considered fully implemented. Provide the ClusterAdmin binding audit and remediation timeline to close.
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

**Tool Query:** `GET /evidence/AC-5?env=good` — simulates: kubescape

**Tool Evidence (API Response):**
```json
{
  "control": "AC-5", "env": "good", "tool": "kubescape",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:10:00Z", "status": "partial",
  "data": {
    "sod_violations": 0,
    "privileged_ns_count": 2,
    "dev_prod_namespace_separation": true,
    "sod_matrix_artifact": null,
    "last_annual_review_date": null,
    "error": "SoD matrix document location not indexed — manual artifact required"
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "Dev and prod are in separate namespaces. Developers can't deploy to prod directly — they
> use the CI/CD pipeline. The SoD matrix is in Confluence but it was last updated a while
> back. I'd need to pull the link. The annual review happened but I don't have the date in
> front of me."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — namespace separation confirmed by scan; SoD matrix and review date not produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Namespace separation confirmed; SoD matrix currency unverified; annual review date unknown |
| Impact | Medium | Technical separation in place; documentation gap means intent cannot be confirmed as current |
| **Residual Risk** | **High** | Separation implemented but documented control cannot be verified for review currency |

**Finding:** PARTIAL
**Evidence Gap:** SoD matrix not produced. Annual review date not confirmed. Matrix update date unknown — may be stale.

**BERU Finding:**
```
FINDING: Kubescape confirms 0 SoD violations and namespace separation for AC-5, but the SoD matrix document and annual review record were not produced.
CONTROL: AC-5 — Separation of Duties
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - ISSO verbal statement (separation described, SoD matrix location not provided)
  - Kubescape query (0 violations, dev/prod namespace separation confirmed)
EVIDENCE GAP: SoD matrix document not produced, annual review date not confirmed, matrix currency unknown
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: ISSO (accountability) / CompO (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Technical separation of duties is confirmed by scanning, but the SoD documentation cannot be verified as current. Produce the Confluence link and the most recent annual review record to close this finding.
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

**Tool Query:** `GET /evidence/AC-6?env=good` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "AC-6", "env": "good", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:15:00Z", "status": "partial",
  "data": {
    "iam_policies_scanned": 94,
    "wildcard_action_policies": 3,
    "star_resource_policies": null,
    "admin_users_count": null,
    "permission_boundaries_enforced": true,
    "scp_artifact": null,
    "last_scan_date": null,
    "error": "Break-glass inventory and star-resource count require elevated read permissions"
  }
}
```

**Interview Response (Control Owner — CloudSec):**
> "Prowler is configured. It found some wildcard policies — 3 of them — but we're working
> on justifying them. Permission boundaries are on most roles. There's an SCP but I'd need
> to pull the policy document. Break-glass accounts have MFA but I don't have the exact
> count here."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — Prowler running and permission boundaries confirmed; 3 wildcard policies open; SCP and break-glass inventory not produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Prowler active and scanning; 3 wildcard policies under review; permission boundaries confirmed |
| Impact | High | Wildcard policies represent unbounded blast radius for any compromised role; break-glass count unverified |
| **Residual Risk** | **High** | Partial enforcement confirmed; open wildcard findings and missing inventory require resolution |

**Finding:** PARTIAL
**Evidence Gap:** 3 wildcard action policies open with no remediation date. Star-resource count unavailable. SCP artifact not produced. Break-glass account inventory not produced.

**BERU Finding:**
```
FINDING: Prowler is running and scanned 94 IAM policies for AC-6, but 3 wildcard action policies are open and the SCP artifact and break-glass inventory were not produced.
CONTROL: AC-6 — Least Privilege
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - CloudSec verbal statement (Prowler running, permission boundaries confirmed)
  - Prowler query (94 policies scanned, 3 wildcard action policies flagged, permission boundaries enforced)
EVIDENCE GAP: 3 wildcard policies unresolved, star-resource count unavailable, SCP artifact not produced, break-glass account inventory not produced
RISK:
  Likelihood: Medium
  Impact: High
  Residual Risk: High
CONTROL OWNER: CloudSec (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: IAM least privilege tooling is in place and scanning, but open wildcard findings must be remediated or formally accepted as exceptions. Produce the SCP document and break-glass inventory to fully evidence the SSP claims.
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

**Tool Query:** `GET /evidence/AC-17?env=good` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "AC-17", "env": "good", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:20:00Z", "status": "partial",
  "data": {
    "vpn_session_logs": true,
    "vpn_session_count_90d": null,
    "unauthorized_access_attempts_90d": null,
    "remote_access_policy_artifact": null,
    "mfa_enforced": true,
    "policy_version": null,
    "error": "VPN session count and policy document require additional query scope"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "The remote access policy exists in Confluence. We require MFA for VPN. Session logs are
> in CloudTrail but I'd need to pull the specific query. The policy was reviewed recently
> but I don't have the version number or review date on me."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — MFA enforced and VPN logs confirmed present; session count and policy version not produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | MFA confirmed; VPN logs present but session count unverified; policy version unknown |
| Impact | Medium | Remote access controlled by MFA; gap in session count means anomaly detection cannot be confirmed |
| **Residual Risk** | **High** | Access method confirmed but monitoring evidence and policy currency unverified |

**Finding:** PARTIAL
**Evidence Gap:** VPN session count for 90 days not retrieved. Unauthorized access attempt count not available. Remote access policy version and review date not produced.

**BERU Finding:**
```
FINDING: CloudTrail confirms VPN session logs exist and MFA is enforced for AC-17, but session count, unauthorized attempt count, and policy version were not produced.
CONTROL: AC-17 — Remote Access
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - SecEng verbal statement (MFA described, policy location referenced but not produced)
  - CloudTrail query (VPN session logs confirmed present, MFA enforcement confirmed)
EVIDENCE GAP: VPN session count unavailable, unauthorized access attempt count unavailable, remote access policy version and review date not produced
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability) / SecEng (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Remote access controls are partially evidenced — MFA and logging are confirmed in place, but the session count and policy document version were not produced. Pull the CloudTrail VPN query and the Confluence policy link to close this finding before the next audit.
```
