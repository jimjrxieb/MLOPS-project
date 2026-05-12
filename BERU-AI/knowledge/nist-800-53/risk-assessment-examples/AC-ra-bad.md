# Risk Assessment Evidence — AC Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** Evidence collected for all five Access Control controls is incomplete and
> unverifiable. Control owners provided vague verbal assurances with no supporting artifacts.
> Tool queries returned empty or error responses indicating controls are not deployed or not
> configured to capture required data. All five findings are FAIL; all require POA&M items.

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

**Tool Query:** `GET /evidence/AC-2?env=bad` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "AC-2", "env": "bad", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "trail_enabled": null, "log_validation": null,
    "DeleteUser_events_90d": 0, "CreateUser_events_90d": 0,
    "last_access_review": null, "iam_credential_report": null,
    "error": "CloudTrail management events not enabled for IAM category"
  }
}
```

**Interview Response (Control Owner — ITOps):**
> "We do access reviews. The last one was a few months ago. HR sends us a list when someone
> leaves and we handle it. Service accounts need a ticket. I don't have the exact dates but
> it's all in JIRA somewhere."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | No verifiable access review; no automation evidence; terminated account status unknown |
| Impact | High | Stale credentials enable unauthorized access; privilege creep undetected across role changes |
| **Residual Risk** | **Critical** | No evidence for any SSP claim; control cannot be verified |

**Finding:** FAIL
**Evidence Gap:** No access review records produced. CloudTrail IAM events not enabled. No service account inventory. No offboarding SLA documentation.

**BERU Finding:**
```
FINDING: ITOps cannot produce access review records or automated account lifecycle evidence for AC-2.
CONTROL: AC-2 — Account Management
ENHANCEMENT: AC-2(1) — Automated System Account Management
STATUS: FAIL
EVIDENCE REVIEWED:
  - ITOps verbal statement (no artifacts provided)
  - CloudTrail query (management events not enabled for IAM category)
EVIDENCE GAP: No access review records, no offboarding SLA documentation, no service account inventory, no CloudTrail IAM event evidence
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: ISSO (accountability) / ITOps (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Access control records for account management are absent. We cannot confirm that terminated employee accounts are disabled or that quarterly reviews are occurring — this is a critical audit finding and an active credential risk.
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

**Tool Query:** `GET /evidence/AC-3?env=bad` — simulates: kubescape

**Tool Evidence (API Response):**
```json
{
  "control": "AC-3", "env": "bad", "tool": "kubescape",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "rbac_scan_run": false,
    "wildcard_roles": null,
    "error": "Kubescape not deployed"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "We have Kubernetes RBAC set up. Users get the roles they need. I'd have to check what
> the current bindings are but we don't give out ClusterAdmin to anyone."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | No RBAC audit run; current bindings unverified; Kubescape not deployed |
| Impact | High | Unauthorized cluster-wide access possible if RBAC misconfigured |
| **Residual Risk** | **Critical** | Zero verifiable evidence of access enforcement |

**Finding:** FAIL
**Evidence Gap:** Kubescape not deployed — no RBAC scan results. No Kyverno policy artifact. No ClusterAdmin binding audit.

**BERU Finding:**
```
FINDING: Kubescape is not deployed and no RBAC audit evidence is available for AC-3.
CONTROL: AC-3 — Access Enforcement
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (no artifacts)
  - Kubescape query (tool not deployed)
EVIDENCE GAP: No RBAC scan results, no Kyverno policy artifact, no ClusterAdmin binding audit
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Kubernetes access enforcement cannot be verified — no RBAC audit tool is deployed. Without automated policy scanning, unauthorized privilege escalation could occur without detection.
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

**Tool Query:** `GET /evidence/AC-5?env=bad` — simulates: kubescape

**Tool Evidence (API Response):**
```json
{
  "control": "AC-5", "env": "bad", "tool": "kubescape",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "sod_violations": null,
    "privileged_ns_count": null,
    "error": "Separation of duties scan not run"
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "Developers don't have prod access. We keep environments separate. The SoD matrix
> is somewhere in Confluence but I'd need to find the link."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Verbal separation claim; no RBAC evidence; SoD matrix not produced |
| Impact | High | Developer access to prod enables unauthorized change and insider risk |
| **Residual Risk** | **High** | Claim unverifiable without artifact |

**Finding:** FAIL
**Evidence Gap:** No SoD matrix produced. No RBAC scan showing namespace separation. No annual review record.

**BERU Finding:**
```
FINDING: No separation of duties matrix or RBAC audit evidence produced for AC-5.
CONTROL: AC-5 — Separation of Duties
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - ISSO verbal statement (no artifacts)
  - Kubescape query (scan not run)
EVIDENCE GAP: No SoD matrix, no RBAC namespace separation evidence, no annual review record
RISK:
  Likelihood: Medium
  Impact: High
  Residual Risk: High
CONTROL OWNER: ISSO (accountability) / CompO (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Separation of duties for environment access cannot be confirmed. Without documented role separation, developer access to production is an unquantified risk with potential for unauthorized change or insider threat.
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

**Tool Query:** `GET /evidence/AC-6?env=bad` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "AC-6", "env": "bad", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "iam_policies_scanned": 0,
    "wildcard_action_policies": null,
    "star_resource_policies": null,
    "admin_users_count": null,
    "error": "Prowler IAM scan not run — no results available"
  }
}
```

**Interview Response (Control Owner — CloudSec):**
> "We try to keep permissions minimal. Prowler is on the roadmap. We don't give out
> admin access to most people."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Prowler not run; wildcard policy count unknown; no SCP artifact |
| Impact | High | Overprivileged IAM = blast radius of any compromised credential is unbounded |
| **Residual Risk** | **Critical** | No evidence least privilege is enforced |

**Finding:** FAIL
**Evidence Gap:** Prowler not run — no IAM policy scan results. No SCP artifact. No break-glass account inventory.

**BERU Finding:**
```
FINDING: Prowler has not been run and no IAM least-privilege evidence is available for AC-6.
CONTROL: AC-6 — Least Privilege
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - CloudSec verbal statement (no artifacts)
  - Prowler query (scan not run)
EVIDENCE GAP: No Prowler scan results, no SCP enforcement artifact, no break-glass account inventory
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: CloudSec (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: IAM least privilege is unverifiable — no policy scanning tool has been run. Overprivileged accounts are the leading cause of cloud breaches. This control requires immediate evidence before the next audit.
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

**Tool Query:** `GET /evidence/AC-17?env=bad` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "AC-17", "env": "bad", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "vpn_session_logs": false,
    "remote_access_policy_artifact": null,
    "error": "No remote access session events found in trail scope"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "We use VPN. People need to authenticate to get in. MFA is configured somewhere
> but I'd have to check the exact settings."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | No VPN session logs; MFA configuration unconfirmed; no policy artifact |
| Impact | High | Unmonitored remote access enables credential stuffing and unauthorized entry |
| **Residual Risk** | **Critical** | Remote access posture completely unverifiable |

**Finding:** FAIL
**Evidence Gap:** No VPN session logs in CloudTrail scope. No remote access policy artifact produced. MFA enforcement unconfirmed.

**BERU Finding:**
```
FINDING: No VPN session logs or remote access policy evidence available for AC-17.
CONTROL: AC-17 — Remote Access
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - SecEng verbal statement (no artifacts)
  - CloudTrail query (VPN session events not in scope)
EVIDENCE GAP: No VPN session logs, no remote access policy document, no MFA enforcement confirmation
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: PlatEng (accountability) / SecEng (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Remote access controls are unverified. No VPN session logs, no MFA confirmation, and no policy document were produced. This leaves remote access pathways completely unauditable and represents a direct threat to the authorization boundary.
```
