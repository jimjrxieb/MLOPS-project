# Risk Assessment Evidence — IA Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** Evidence collected is partially sufficient. Control owners named specific
> tools and processes but could not produce exact artifacts, dates, or complete metrics. Tool
> queries returned partial data — some booleans confirmed but key counts and timestamps absent.
> All four controls receive PARTIAL findings requiring POA&M items to close the evidence gaps
> before the next audit cycle.

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

**Tool Query:** `GET /evidence/IA-2?env=good` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "IA-2", "env": "good", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "partial",
  "data": {
    "mfa_enforced_via_scp": true,
    "console_login_events_90d": null,
    "mfa_not_used_logins": null,
    "note": "SCP in place. ConsoleLogin event counts not queryable at current access level."
  }
}
```

**Interview Response (Control Owner — ITOps):**
> "SCP is in place — it's the org-level MFA enforcement. Okta handles MFA. The
> ConsoleLogin events are in CloudTrail but I can't pull the count right now
> — you'd need higher permissions. No bypasses that I know of."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — SCP MFA enforcement confirmed; ConsoleLogin event count and bypass attempt count not retrievable at assessor permission level

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | SCP MFA enforcement confirmed; ConsoleLogin counts inaccessible; bypass attempt count unknown |
| Impact | Medium | SCP enforcement reduces risk but bypass attempt visibility gap means anomaly detection cannot be confirmed |
| **Residual Risk** | **High** | MFA enforcement partially evidenced; bypass attempt count must be produced for full credit |

**Finding:** PARTIAL
**Evidence Gap:** ConsoleLogin event count not retrievable. MFA bypass attempt count not produced. SCP ID not confirmed. MFA type (FIDO2/WebAuthn) not confirmed.

**BERU Finding:**
```
FINDING: SCP MFA enforcement is confirmed for IA-2 but ConsoleLogin event counts and bypass attempt counts are not accessible at assessor permission level.
CONTROL: IA-2 — Identification and Authentication (Organizational Users)
ENHANCEMENT: IA-2(1) — Multi-Factor Authentication to Privileged Accounts
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - ITOps verbal statement (SCP described, ConsoleLogin counts unavailable)
  - CloudTrail query (mfa_enforced_via_scp true, ConsoleLogin counts inaccessible)
EVIDENCE GAP: ConsoleLogin event count not retrievable, bypass attempt count not produced, SCP ID not confirmed, MFA type not confirmed
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: ITOps (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: MFA enforcement via SCP is confirmed but the ConsoleLogin event counts and bypass attempt evidence cannot be produced at the current assessor permission level. Provide the SCP ID and a CloudTrail query result showing 0 bypass attempts to close this finding.
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

**Tool Query:** `GET /evidence/IA-3?env=good` — simulates: kubescape

**Tool Evidence (API Response):**
```json
{
  "control": "IA-3", "env": "good", "tool": "kubescape",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "partial",
  "data": {
    "mtls_enabled": true,
    "workload_identity": "service accounts present",
    "spiffe_ids": null
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "Istio is deployed and mTLS is on. I believe it's STRICT mode but I'd need to
> check the PeerAuthentication policy. Service accounts are assigned. SPIFFE IDs
> — I think SPIRE is configured but I'm not 100% sure. IRSA is set up for most
> workloads."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — mTLS enabled; STRICT mode and SPIFFE ID assignment not confirmed; IRSA coverage not confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | mTLS confirmed enabled; STRICT mode unconfirmed; SPIFFE IDs null; IRSA coverage partial |
| Impact | Medium | Without confirmed STRICT mode, permissive mTLS allows unauthenticated workload connections |
| **Residual Risk** | **High** | Workload identity partially confirmed but STRICT mode and SPIFFE gaps must be closed |

**Finding:** PARTIAL
**Evidence Gap:** mTLS STRICT mode not confirmed. SPIFFE ID assignment not confirmed. IRSA coverage for all workloads not confirmed.

**BERU Finding:**
```
FINDING: mTLS is enabled for IA-3 but STRICT mode and SPIFFE ID assignment are not confirmed via Kubescape scan.
CONTROL: IA-3 — Device Identification and Authentication
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (Istio deployed, STRICT mode uncertain, SPIRE uncertain)
  - Kubescape query (mtls_enabled true, workload_identity service accounts, spiffe_ids null)
EVIDENCE GAP: mTLS STRICT mode not confirmed, SPIFFE IDs null, IRSA coverage not confirmed for all workloads
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: mTLS is enabled but STRICT mode must be confirmed. Produce the Istio PeerAuthentication policy showing STRICT mode and confirm SPIFFE ID assignment for all pods to close this finding.
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

**Tool Query:** `GET /evidence/IA-4?env=good` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "IA-4", "env": "good", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:10:00Z", "status": "partial",
  "data": {
    "identifier_review_last_run": "quarterly — date unconfirmed",
    "inactive_identifiers_gt90d": null,
    "orphaned_identifiers": null,
    "note": "Review process described verbally. No artifact produced."
  }
}
```

**Interview Response (Control Owner — ITOps):**
> "We do quarterly reviews. The ISSO signs off. I don't have the specific date
> for Q1 — it was done but the artifact is in Confluence somewhere. Orphaned
> identifiers — the credential report would show that but I'd need to generate it."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — quarterly review process described; review date, orphaned identifier count, and credential report not produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Review process confirmed verbally; specific date and artifact not produced; orphaned count unknown |
| Impact | Medium | Without the credential report, orphaned identifier count is unverifiable |
| **Residual Risk** | **High** | Review process described but artifact gap means accountability is unverifiable |

**Finding:** PARTIAL
**Evidence Gap:** Q1 review artifact not produced. Orphaned identifier count not confirmed. Inactive identifier count not produced. Naming policy document not provided.

**BERU Finding:**
```
FINDING: Quarterly identifier review process is described for IA-4 but the Q1 artifact, orphaned identifier count, and credential report were not produced.
CONTROL: IA-4 — Identifier Management
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - ITOps verbal statement (review described, Q1 artifact in Confluence but not retrieved)
  - CloudTrail query (review date unconfirmed, inactive and orphaned counts null)
EVIDENCE GAP: Q1 review artifact not produced, orphaned identifier count not confirmed, inactive identifier count null, naming policy not provided
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: ISSO (accountability) / ITOps (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Identifier management review process is described but not evidenced. Produce the Q1 2026 review artifact, generate the IAM credential report, and confirm zero orphaned and shared identifiers to close this finding.
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

**Tool Query:** `GET /evidence/IA-5?env=good` — simulates: gitleaks

**Tool Evidence (API Response):**
```json
{
  "control": "IA-5", "env": "good", "tool": "gitleaks",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:15:00Z", "status": "partial",
  "data": {
    "secrets_found": 2,
    "secrets_rotated": null,
    "rotation_schedule": "90 days — not enforced",
    "note": "2 secrets found in history — rotation not confirmed"
  }
}
```

**Interview Response (Control Owner — ITOps):**
> "Gitleaks runs in CI. There were 2 secrets found — they're from old commits. The
> rotation schedule is 90 days but it's not automated yet. Pre-commit hooks — they're
> configured on some repos. AWS Secrets Manager is used for most secrets but not all."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — Gitleaks running; 2 secrets found in history; rotation schedule not enforced; pre-commit hooks partial; Secrets Manager coverage partial

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Gitleaks running but 2 secrets found; rotation not automated; pre-commit hooks partial |
| Impact | High | 2 secrets in git history must be treated as compromised; non-automated rotation means stale credentials persist |
| **Residual Risk** | **High** | Gitleaks active but open secret findings and non-enforced rotation require immediate remediation |

**Finding:** PARTIAL
**Evidence Gap:** 2 secrets found in git history with rotation not confirmed. 90-day rotation not automated. Pre-commit hooks not on all repos. Secrets Manager coverage not confirmed for all secrets.

**BERU Finding:**
```
FINDING: Gitleaks found 2 secrets in git history for IA-5 and secret rotation is not enforced; pre-commit hooks are partial.
CONTROL: IA-5 — Authenticator Management
ENHANCEMENT: IA-5(1) — Password-Based Authentication
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - ITOps verbal statement (Gitleaks running, 2 old secrets, rotation manual, hooks partial)
  - Gitleaks query (2 secrets found in history, rotation not enforced, secrets_rotated null)
EVIDENCE GAP: 2 secrets in git history not confirmed rotated, rotation schedule not automated, pre-commit hooks not universal, Secrets Manager coverage partial
RISK:
  Likelihood: Medium
  Impact: High
  Residual Risk: High
CONTROL OWNER: ITOps (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Gitleaks is running but 2 secrets found in git history must be rotated immediately. Automate the 90-day rotation via Secrets Manager and deploy pre-commit hooks to all repos to close this finding.
```
