# System Security Plan — Incident Response (IR) Family

## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** This SSP would pass a readiness review with 3-4 clarification items.
> PagerDuty, runbooks, and tabletop exercises are named. The IR plan is approved and
> distributed. Gaps: automated containment is described for one scenario only, IR-4(4)
> cross-incident correlation is not implemented, tabletop scenarios are not varied
> year-over-year, and MTTD/MTTR metrics are defined but trend data is not produced.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Final Draft — Pending ISSO Signature

---

## IR-4 — Incident Handling

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

Incident handling on the Links-Matrix Platform follows the NIST SP 800-61 phases:
Preparation → Detection and Analysis → Containment → Eradication → Recovery →
Post-Incident Activity. Each phase has assigned roles, defined actions, and a
corresponding section in the Incident Response Runbook
(`platform-gitops/docs/ir-runbook.md`, current version v1.2, reviewed 2026-03-01).

**Detection:**
Incidents are surfaced through: PagerDuty alerts from OpenSearch/GuardDuty/Falco,
direct user reports to `security@links-matrix.io`, and the SOC daily alert review.
All potential incidents are logged in Jira (`SEC-IR` project) within 15 minutes of
identification. The SOC on-call acknowledges PagerDuty P1 alerts within 15 minutes.

**Severity classification:**

| Severity | Description | Example | Initial Response SLA |
| -------- | ----------- | ------- | -------------------- |
| P1 — Critical | Active breach, data exfiltration in progress, ransomware | Cluster-admin compromise | 15 min acknowledge, 1 hr ISSO notified |
| P2 — High | Confirmed unauthorized access, credential compromise | IAM key leaked to public repo | 1 hr acknowledge, 4 hr ISSO notified |
| P3 — Medium | Suspicious activity under investigation | Anomalous API call pattern | 4 hr acknowledge, next business day ISSO |
| P4 — Low | Policy violation, failed attack attempt | Kyverno denial spike | Next business day |

**Containment:**
The IR Runbook (Section 3) documents containment procedures for the three most likely
incident types on this platform:

- **Compromised container/pod:** `kubectl delete pod <pod-name> -n <namespace>` to
  terminate; apply isolation NetworkPolicy (`platform-gitops/ir/isolate-namespace.yaml`)
  to block all egress from the namespace; take Velero snapshot before deletion for
  forensic preservation.
- **Leaked IAM credential:** `aws iam delete-access-key` (if static key) or
  `aws iam update-access-key --status Inactive`; update role trust policy to invalidate
  existing sessions; rotate Secrets Manager secrets that used the compromised role.
- **Compromised Okta account:** Suspend Okta user via Admin console or API; revoke all
  active sessions; invalidate all issued OIDC tokens by Okta session termination.

**Post-Incident:**
A post-incident review (PIR) is conducted within 5 business days of incident closure
for P1/P2 incidents and within 10 business days for P3. The PIR produces a written
report (stored in Confluence: LM-SECURITY / IR / PIR Reports) documenting: timeline,
root cause, actions taken, gaps identified, and remediation items. Remediation items
are tracked in Jira.

**Responsible Role:** SOC (detection, initial triage), IRT (containment and eradication), ISSO (escalation authority, PIR oversight), Platform Engineer (K8s containment), Cloud Security Engineer (AWS containment)

**Parameters:**
- P1 acknowledgment SLA: 15 minutes
- P1 ISSO notification SLA: 1 hour
- PIR deadline (P1/P2): 5 business days post-closure
- PIR deadline (P3): 10 business days post-closure

**Evidence / Artifacts:**
- IR Runbook v1.2 (`platform-gitops/docs/ir-runbook.md`)
- Jira `SEC-IR` project — incident ticket history (last 12 months)
- PIR reports (Confluence: LM-SECURITY / IR / PIR Reports)
- PagerDuty service `lm-security-p1` — escalation policy and on-call schedule

**Enhancements Addressed:**
- **IR-4(1):** GuardDuty and Falco trigger automated PagerDuty alerts. The isolation
  NetworkPolicy (`ir/isolate-namespace.yaml`) can be applied with a single kubectl command
  from the runbook. *(Note: fully automated containment without human approval is not yet
  implemented for any scenario — all containment steps require on-call engineer action.
  A SOAR integration is planned for Q4 2026.)*
- **IR-4(4):** Not implemented. Incidents are tracked individually in Jira but
  cross-incident correlation to identify campaign patterns is not performed. Planned
  for Q4 2026 with OpenSearch correlation rules.

---

## IR-8 — Incident Response Plan

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

The Links-Matrix Incident Response Plan (`IRP-LM-v2.1`, Confluence: LM-SECURITY / IR /
IRP-LM-v2.1.pdf) is the governing document for the IR program. It was approved by the
ISSO (M. Chen) and System Owner (J. Rivera) on 2026-03-01 and is reviewed annually.

**Plan contents:**
- Roles and responsibilities (ISSO, SOC, IRT, Platform Engineer, Cloud Security, Legal, PR)
- Incident classification and severity matrix
- Phase-by-phase response procedures (aligned with NIST SP 800-61)
- Communication and escalation matrix — who is notified at each severity level
- Evidence preservation procedures
- Breach notification procedures (see IR-8(1))
- Metrics: MTTD (mean time to detect), MTTR (mean time to resolve), incidents by severity
- Annual review and testing schedule

**Distribution:**
The IRP is distributed to all personnel with IR responsibilities upon approval and
when updated. Distribution is tracked via a Confluence page acknowledgment — each
named role must confirm receipt in Confluence within 5 business days of publication.
Last distribution acknowledgment completed: 2026-03-10.

**Annual tabletop exercise:**
An annual tabletop exercise is conducted in Q1 of each year. The 2026 exercise
(2026-02-20) tested a simulated credential compromise scenario — an IAM key leaked
to a public GitHub repository. Participants: ISSO, SOC lead, Platform Engineer,
Cloud Security Engineer, Legal counsel. Exercise findings: (1) Okta session invalidation
steps were unclear in the runbook — updated in v2.1; (2) Legal notification threshold
for breach was not well understood by the SOC — breach notification section expanded.
Exercise report stored in Confluence: LM-SECURITY / IR / Tabletop-2026.pdf.

**Breach notification (IR-8(1)):**
The IRP Section 6 documents breach notification procedures:
- Notification to affected individuals: Within 30 days of breach determination
- Notification to FTC (if applicable): As required under applicable law
- Internal notification chain: Legal → CISO → System Owner → ISSO (within 2 hours
  of breach determination)
- Regulatory notification: Legal counsel determines applicable requirements and timelines
  based on data types involved

**Responsible Role:** ISSO (plan owner, annual review), Legal (breach notification), SOC Lead (distribution coordination)

**Parameters:**
- IRP version: v2.1
- Last approved: 2026-03-01 (ISSO + System Owner signatures)
- Annual review month: February
- Tabletop exercise cadence: Annual (Q1)
- Distribution acknowledgment deadline: 5 business days post-publication

**Evidence / Artifacts:**
- IRP-LM-v2.1 (Confluence: LM-SECURITY / IR / IRP-LM-v2.1.pdf — signed)
- Distribution acknowledgment records (Confluence: LM-SECURITY / IR / IRP-Distribution-2026.md)
- 2026 Tabletop Exercise Report (Confluence: LM-SECURITY / IR / Tabletop-2026.pdf)
- PagerDuty on-call schedule aligned with IRP roles

**Enhancements Addressed:**
- **IR-8(1):** Breach notification procedures in IRP Section 6 include: internal notification
  chain, 30-day individual notification window, and Legal-led regulatory determination.
  *(Note: specific regulatory notification timelines for GDPR (72 hours) and state breach
  laws are not individually enumerated in the plan — Legal determines applicable requirements
  at time of incident. This is a process gap if the platform ever processes EU personal data.)*

---

## What Makes This GOOD (But Not Great) — Examiner's Notes

| Control | Strengths | Gaps |
| ------- | --------- | ---- |
| IR-4 | Severity table, 3 containment runbooks, PIR process | Automated containment not implemented — all steps require human action; IR-4(4) cross-incident correlation is a future item |
| IR-4 | PIR deadlines defined (5 and 10 business days) | No MTTD/MTTR trend data — metrics defined but not measured and reported |
| IR-8 | Approved plan with version number, distribution tracking, tabletop with findings | Tabletop tests one scenario annually — same credential scenario year over year does not test K8s-specific or data exfiltration scenarios |
| IR-8 | Breach notification section exists | GDPR 72-hour window not enumerated — "Legal determines" is accurate but leaves a gap if Legal is unavailable during an incident |
| Both | IR-4 runbook references IR-8 plan | No metrics trend (MTTD/MTTR by quarter) — plan says metrics are tracked but no evidence they are actually measured |
