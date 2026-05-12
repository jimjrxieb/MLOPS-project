# System Security Plan — Planning (PL) Family

## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** This SSP would pass a readiness review with 3-4 clarification items.
> AO signature exists, version number is present, and the annual review cadence is
> documented. Gaps: no formalized significant-change trigger with SLA (ISSO discretion),
> boundary diagram is a static PDF in Confluence rather than version-controlled alongside
> the codebase, PL-2(3) coordination relies on an email notification process without
> documented advance notice requirements, and control statements in this SSP section
> partially contain boilerplate not tailored to the Links-Matrix deployment.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Final Draft — Pending ISSO Signature

---

## PL-2 — System Security and Privacy Plans

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

The Links-Matrix Platform System Security Plan (`SSP-LM-v3.0`, Confluence:
LM-SECURITY / SSP / SSP-LM-v3.0.pdf) is the authoritative document describing
the system boundary, information types, security controls, and authorization basis.
The SSP was reviewed and approved by the Authorizing Official (AO: D. Walsh,
VP of Information Security) and the System Owner (J. Rivera, Platform Engineering Lead)
on 2026-03-15. The ISSO (M. Chen) is the plan owner responsible for maintenance.

**Authorization boundary:**
The Links-Matrix Platform authorization boundary includes: EKS cluster
(`lm-prod-cluster`) in us-east-1, EKS DR cluster (`lm-dr-cluster`) in us-west-2,
supporting AWS services (RDS, S3, Secrets Manager, CloudTrail, GuardDuty, ECR),
and all supporting platform tools (ArgoCD, Falco, OpenSearch, cert-manager, Kyverno).
The boundary excludes: end-user workstations (covered under the corporate endpoint
security authorization) and Okta (inherited external service with CSP-level controls).

**Information types (NIST SP 800-60):**
- Application operational data — Moderate (C/I/A: M/M/M)
- Platform audit logs — Moderate (C/I/A: L/H/M)
- Customer configuration data — Moderate (C/I/A: M/H/M)

**System boundary diagram:**
The boundary diagram (`SSP-LM-Boundary-v3.0.png`) is embedded in SSP-LM-v3.0
and available at Confluence: LM-SECURITY / SSP / Diagrams. The diagram was last
updated 2026-03-10 to add the us-west-2 DR cluster added in 2025-Q4.

**SSP maintenance:**
The SSP is reviewed annually in Q1. The current version is v3.0, approved 2026-03-15.
The SSP is updated when significant system changes occur — the ISSO determines whether
a change is significant enough to require an SSP update. In practice, changes that
have triggered updates include: adding a new EKS cluster (DR cluster, v3.0), adding
a new AWS service to the authorization boundary, and changing the information types
processed by the system.

**Control statement accuracy:**
The ISSO reviews the control implementation statements during the annual SSP review.
Control statements are compared against the implemented controls as observed by the
ISSO. Discrepancies identified during the annual review are corrected before AO
re-approval.

**Responsible Role:** ISSO (plan owner, annual review, change trigger determination), AO (approval), System Owner (co-approval)

**Parameters:**
- SSP version: v3.0
- Last approved: 2026-03-15 (AO + System Owner signatures)
- Annual review month: Q1 (February–March)
- Change trigger: ISSO discretion — significant system changes

**Evidence / Artifacts:**
- SSP-LM-v3.0 (Confluence: LM-SECURITY / SSP / SSP-LM-v3.0.pdf — AO-signed)
- Boundary diagram v3.0 (Confluence: LM-SECURITY / SSP / Diagrams / SSP-LM-Boundary-v3.0.png)
- SSP version history (Confluence: LM-SECURITY / SSP — version list v1.0 through v3.0)
- AO approval email (LM-SECURITY / SSP / Approvals / AO-Approval-2026-03-15.msg)

**Enhancements Addressed:**
- **PL-2(3):** Security activities that affect shared infrastructure (e.g., penetration tests,
  major configuration changes) are coordinated by the ISSO via email notification to
  affected teams before the activity begins. The Coalfire annual assessment (3PAO) is
  coordinated with the Platform Engineering team and AWS account owners prior to kick-off.
  *(Note: advance notice requirements for coordination are not formally documented —
  the timing of notification is at ISSO discretion. A penetration test might be announced
  one week or one day before testing begins, depending on scheduling.)*

---

## What Makes This GOOD (But Not Great) — Examiner's Notes

| Control | Strengths | Gaps |
| ------- | --------- | ---- |
| PL-2 | AO-signed plan with version number, named System Owner, named ISSO | Significant-change trigger is "ISSO discretion" — no SLA from system change to SSP update. Changes can slip through unrecorded. |
| PL-2 | Annual review cadence documented, version history exists on Confluence | Boundary diagram is a static PNG in Confluence — not version-controlled alongside infrastructure code. Diagram can fall out of sync with actual architecture between annual reviews. |
| PL-2 | Information types listed with NIST SP 800-60 categorization | Control statement accuracy verification is annual only. If a control changes implementation mid-year, the SSP may be inaccurate for up to 11 months. |
| PL-2(3) | Coalfire 3PAO assessment coordination is documented | No formal advance notice SLA for coordination activities — "ISSO discretion" fails during ISSO turnover or absence. No tracking mechanism to confirm coordination actually occurred for each activity. |
| Both | SSP exists and was the basis for authorization | No OSCAL-format SSP — if this system ever moves to FedRAMP, the SSP will need to be fully restructured. No machine-readable format available for automated control baseline comparison. |
