# System Security Plan — Incident Response (IR) Family

## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** This SSP is auditor-ready. IR-8 is the approved plan; IR-4 is
> the evidence that the plan is executable. MTTD and MTTR are measured, trended, and
> reported quarterly. Automated containment is implemented for the top three incident
> types. Tabletop scenarios rotate annually. Breach notification timelines are explicitly
> enumerated — not delegated to Legal to determine under pressure. Every gap has a
> compensating control or a POA&M entry.

---

**System Name:** Links-Matrix Platform
**System Owner:** J. Rivera, Platform Engineering Lead (jrivera@links-matrix.io)
**ISSO:** M. Chen, Information System Security Officer (mchen@links-matrix.io)
**Prepared By:** M. Chen, ISSO
**Date:** 2026-05-01
**Review Date:** 2027-05-01 (annual) or upon significant system change
**Status:** Approved — ATO Granted 2026-03-15, expires 2029-03-15

**Control Relationship Note:** IR-8 is the plan. IR-4 is the proof the plan works.
An IR plan with no exercise history, no incident ticket trail, and no metrics is a
document, not a capability. The quarterly MTTD/MTTR report and the annual tabletop
results are the evidence that IR-8 produces a functioning IR-4 program.

---

## IR-4 — Incident Handling

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Moderate and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Incident Handling Phases

Incident handling follows NIST SP 800-61 Rev 2 phases, each with defined entry
criteria, required actions, responsible roles, and exit criteria documented in the
IR Runbook (`platform-gitops/docs/ir-runbook.md`, v2.3, updated 2026-03-15).

### Severity Classification and SLAs

| Severity | Criteria | Examples | Acknowledge | ISSO Notify | Containment Target | PIR Deadline |
| -------- | -------- | -------- | ----------- | ----------- | ------------------ | ------------ |
| P1 — Critical | Active breach, exfiltration in progress, ransomware, cluster-admin compromise | GuardDuty `UnauthorizedAccess:IAMUser/ConsoleLoginSuccess.B`; Falco `CRITICAL` rule firing | **15 min** | **1 hour** | **1 hour** | 3 business days |
| P2 — High | Confirmed unauthorized access, leaked credential, data integrity violation | IAM key in public repo; failed MFA brute force >20 attempts | **1 hour** | **4 hours** | **4 hours** | 5 business days |
| P3 — Medium | Suspicious activity, unconfirmed compromise, policy violation at scale | Kyverno violation spike >50 in 1 hour; anomalous cross-namespace pod communication | **4 hours** | Next business day | **24 hours** | 10 business days |
| P4 — Low | Single policy violation, failed attack with no success indicators | Single Kyverno denial; failed kubectl from unexpected IP (one attempt) | Next business day | Weekly summary | Best effort | Not required |

### Automated Containment

Automated containment scripts are maintained in `platform-gitops/ir/` and tested
quarterly as part of the tabletop exercise. Each script is idempotent — safe to run
multiple times without side effects.

| Incident Type | Automated Action | Script | Trigger Condition | Human Approval Required |
| ------------- | ---------------- | ------ | ----------------- | ----------------------- |
| Compromised pod (Falco CRITICAL) | Apply `isolate-pod` NetworkPolicy (deny all ingress/egress to pod label); take Velero snapshot; send forensic capture to S3 | `ir/isolate-pod.sh <namespace> <pod-name>` | Falco `CRITICAL` alert (manual trigger by SOC on-call) | SOC on-call (no management approval needed for P1) |
| Leaked IAM credential detected | Deactivate access key via AWS CLI; update role trust policy to add deny condition for existing sessions; post Slack alert to `#sec-incidents` | `ir/revoke-iam-key.sh <key-id> <role-arn>` | GuardDuty `CredentialAccess:IAMUser/AnomalousBehavior` or GitGuardian webhook | SOC on-call |
| Compromised Okta account | Suspend user; revoke all sessions via Okta API; log session count revoked | `ir/suspend-okta-user.sh <email>` | Okta ThreatInsight high-risk event or SOC detection | SOC on-call |
| Node compromise suspected | Cordon node (`kubectl cordon <node>`); drain non-critical workloads; trigger Systems Manager Session Manager session for forensic capture | `ir/cordon-node.sh <node-name>` | Falco `unexpected-privileged-process-on-node` (manual trigger) | Platform Engineer on-call + ISSO notify |
| Break-glass account used | Immediate PagerDuty P1; ISSO Slack DM; begin 30-day audit log review | Automated via EventBridge rule (no manual trigger) | CloudTrail `ConsoleLogin` from `lm-break-glass-*` | ISSO reviews — no approval needed for alert |

All scripts are version-controlled in `platform-gitops/ir/`, require the `iam:PassRole`
permission on the `lm-ir-responder` IAM role (restricted to SOC and IRT members), and
log their execution to S3 `lm-audit-reports/ir-actions/` with timestamp, executor, and
affected resource.

### Evidence Preservation

Before any destructive containment action (pod deletion, node drain), a forensic snapshot
is taken:
- **Kubernetes:** Velero backup of the affected namespace (`velero backup create
  forensic-<incident-id> --include-namespaces <ns>`)
- **AWS:** EBS snapshot of any affected node volumes; CloudTrail and VPC Flow Log
  export for the 24-hour window around detection
- **Logs:** OpenSearch export of all events for affected principals in the 72-hour
  window; stored in S3 `lm-audit-reports/ir-forensics/<incident-id>/`

Forensic evidence is retained for a minimum of 2 years (or the duration of any
associated legal hold, whichever is longer).

### Post-Incident Reviews and Metrics

A PIR is conducted for all P1, P2, and P3 incidents within the SLA above. The PIR
template (`platform-gitops/docs/pir-template.md`) requires:
- Incident timeline (detection → containment → eradication → recovery) with exact timestamps
- Root cause (5-whys or equivalent)
- Gaps in detection, containment, or recovery identified
- Remediation items with owners and target dates (tracked in Jira `SEC-IR`)
- Update requirements for the IR Runbook or IRP

**MTTD/MTTR metrics** are calculated from Jira `SEC-IR` ticket timestamps
(created = detection time; resolved = recovery confirmed) and reported quarterly:

| Quarter | P1/P2 Incidents | Avg MTTD | Avg MTTR | SLA Met (P1 contain) |
| ------- | --------------- | -------- | -------- | -------------------- |
| Q1 2026 | 2 (both P2) | 8 min | 3.5 hr | 2/2 ✅ |
| Q4 2025 | 1 (P2) | 12 min | 4.2 hr | 1/1 ✅ |
| Q3 2025 | 0 | — | — | N/A |
| Q2 2025 | 1 (P2) | 22 min | 6.1 hr | 1/1 ✅ |

Metrics are included in the monthly CA-7 continuous monitoring report distributed to
the AO. MTTD trend (improving: 22 min → 8 min over 12 months) is evidence of program
maturity, documented in the Q1 2026 PIR summary.

### Cross-Incident Correlation (IR-4(4))

OpenSearch correlation rules (deployed in `platform-gitops/monitoring/ir-correlations/`)
surface cross-incident patterns:

- **Credential replay pattern:** Three or more P3/P4 events involving the same IAM
  role ARN within a 7-day window → auto-escalate all to P2 and create a correlation
  Jira ticket linking the individual incidents
- **Multi-vector reconnaissance:** Failed auth attempt (Okta) + K8s `secrets:get`
  attempt (denied by RBAC) + CloudTrail `GetSecretValue` AccessDenied within 30 minutes
  by the same principal → P1 escalation
- **Post-incident regression:** Any alert type that previously generated a P2 incident
  firing again within 90 days of that incident's PIR closure → P2 auto-escalation +
  ISSO notification that a remediaton may not have held

Correlation rules are reviewed and tuned quarterly by the ISSO and SOC Lead.

**Responsible Role:** SOC (detection, triage, automated containment execution), IRT (eradication, recovery), ISSO (P1/P2 escalation authority, PIR oversight, metrics reporting), Platform Engineer (K8s containment), Cloud Security Engineer (AWS containment, forensic capture)

**Parameters:**
- P1 acknowledge SLA: **15 minutes**; containment target: **1 hour**
- P2 acknowledge SLA: **1 hour**; containment target: **4 hours**
- PIR deadline P1/P2: **3/5 business days**
- MTTD target (P1/P2): **<15 minutes** (current: 8 min — Q1 2026)
- MTTR target (P1/P2): **<4 hours** (current: 3.5 hr — Q1 2026)
- Forensic evidence retention: **2 years** minimum

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| IR Runbook v2.3 | `platform-gitops/docs/ir-runbook.md` | 2026-03-15 |
| Automated containment scripts | `platform-gitops/ir/*.sh` | Per-commit |
| Jira `SEC-IR` project (incident tickets, last 12 months) | Jira project SEC-IR | Continuous |
| PIR reports (all P1/P2/P3, last 12 months) | Confluence: LM-SECURITY / IR / PIR Reports | Per incident |
| MTTD/MTTR quarterly metrics | Confluence: LM-SECURITY / IR / Metrics-2026-Q1.md | 2026-04-07 |
| OpenSearch IR correlation rules | `platform-gitops/monitoring/ir-correlations/` | Per-commit |
| Forensic evidence S3 bucket | S3 `lm-audit-reports/ir-forensics/` | Per incident |
| IR script execution audit log | S3 `lm-audit-reports/ir-actions/` | Per script execution |

**Test Procedure:**
1. Pull Jira `SEC-IR` for the last 12 months — select any P1/P2 ticket. Verify it has:
   a detection timestamp, a containment timestamp, an eradication timestamp, a recovery
   timestamp, and a PIR link. Verify the containment-to-detection delta meets the SLA.
2. Run `ir/isolate-pod.sh` against a test pod in `lm-staging` — verify a Velero backup
   is created, a deny-all NetworkPolicy is applied to the pod's label selector, and an
   execution record appears in S3 `lm-audit-reports/ir-actions/` within 60 seconds.
3. Pull the MTTD/MTTR quarterly metrics report — verify it covers Q1 2026 and at
   least two prior quarters, showing trend direction.
4. Pull the OpenSearch IR correlation rules — verify the credential replay rule is
   active (not disabled) and the threshold values match the documented parameters.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| IR-4(1) Automated Incident Handling | Implemented | Five automated containment scripts in `platform-gitops/ir/`: pod isolation (with Velero snapshot), IAM key revocation, Okta account suspension, node cordon, and break-glass alerting. All scripts log to S3 audit trail. Triggered by SOC on-call without management approval for P1. No external SOAR required — scripts are the automation layer. |
| IR-4(4) Information Correlation | Implemented | Three OpenSearch correlation rules: credential replay pattern (7-day window), multi-vector reconnaissance (30-minute window), and post-incident regression (90-day window). Rules reviewed quarterly. Cross-incident Jira links maintained for all correlated events. MTTD trend data demonstrates correlation is improving detection speed. |

---

## IR-8 — Incident Response Plan

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Low, Moderate, and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Plan Summary

| Attribute | Detail |
| --------- | ------ |
| Document | Links-Matrix Incident Response Plan `IRP-LM-v2.3` |
| Location | Confluence: LM-SECURITY / IR / IRP-LM-v2.3.pdf (version history preserved) |
| Approved by | M. Chen (ISSO) + J. Rivera (System Owner) + R. Patel (CISO) |
| Approval date | 2026-03-15 |
| Next scheduled review | 2027-03-01 (annual) |
| Basis | NIST SP 800-61 Rev 2 |
| Current version | v2.3 (v2.2 → v2.3: added multi-vector reconnaissance correlation; updated breach notification to enumerate GDPR 72-hour window explicitly) |

### Plan Structure and Contents

The IRP is organized into 8 sections, each with a designated owner who is responsible
for keeping their section current:

| Section | Owner | Contents |
| ------- | ----- | -------- |
| 1 — Purpose and Scope | ISSO | Authorization boundary, information types, regulatory context |
| 2 — IR Team Roles | ISSO | Named roles with current personnel, backup contacts, and escalation chain |
| 3 — Phase Procedures | SOC Lead | Detection, analysis, containment, eradication, recovery — step by step |
| 4 — Severity and SLAs | ISSO | Classification matrix, response SLAs, escalation thresholds |
| 5 — Communication Matrix | ISSO + Legal | Who is notified at each severity, external communication approval authority |
| 6 — Breach Notification | Legal (primary) + ISSO | Regulatory timelines, notification templates, evidence packaging |
| 7 — Evidence Preservation | Platform Engineer | Forensic procedures, retention requirements, chain of custody |
| 8 — Metrics and Improvement | ISSO | MTTD/MTTR definitions, quarterly reporting, PIR process |

Each section owner reviews their section when a significant change affects it and at
the annual review. Section owners sign off on their section in the Confluence version
history. The ISSO performs a full IRP review annually and after any P1 incident or
significant architecture change.

### Distribution and Acknowledgment

The IRP is distributed to all personnel with IR responsibilities upon each version update.
Distribution is tracked in Confluence (LM-SECURITY / IR / IRP-Distribution-Tracker.md).
Each named role acknowledges receipt via a Confluence page reaction within 5 business days.
Unacknowledged distributions trigger a Jira ticket assigned to the role's manager.

Current distribution status (v2.3, distributed 2026-03-16):
- ISSO: ✅ Acknowledged 2026-03-16
- SOC Lead: ✅ Acknowledged 2026-03-17
- SOC On-call (3 members): ✅ All acknowledged by 2026-03-20
- Platform Engineer Lead: ✅ Acknowledged 2026-03-17
- Cloud Security Engineer: ✅ Acknowledged 2026-03-18
- Legal Counsel: ✅ Acknowledged 2026-03-19
- CISO: ✅ Acknowledged 2026-03-16
- System Owner: ✅ Acknowledged 2026-03-16

### Annual Tabletop Exercise

Tabletop scenarios rotate annually to ensure different incident types and response
vectors are exercised. A scenario is not repeated for at least 3 years.

| Year | Scenario | Participants | Gaps Identified | Runbook Updates |
| ---- | -------- | ------------ | --------------- | --------------- |
| 2026 | Ransomware via supply chain — malicious image pushed to ECR, deployed to prod | ISSO, SOC, Platform, Cloud Sec, Legal | Image signing not enforced at deployment time; Legal breach notification threshold unclear | Added `verify-image-signatures` Kyverno policy; expanded Section 6 with explicit timelines |
| 2025 | Leaked IAM credential — developer commits AWS key to public repo | ISSO, SOC, Cloud Sec, Legal | Runbook step for trust policy invalidation was missing; Legal notification trigger was ambiguous | Added `ir/revoke-iam-key.sh`; updated Section 5 communication matrix |
| 2024 | Compromised cluster-admin — attacker escalates via RBAC misconfiguration | ISSO, SOC, Platform, Legal | No forensic snapshot procedure before pod deletion | Added Velero pre-deletion snapshot to all containment runbooks |

The 2026 tabletop (2026-02-18) exercise report is at Confluence: LM-SECURITY / IR /
Tabletop-2026.pdf. All gap remediations from 2026 exercise are closed (verified 2026-04-01).
The 2027 scenario is planned: simulated insider threat — malicious admin with legitimate
cluster-admin access exfiltrating data over a 30-day window.

### Breach Notification Procedures (IR-8(1))

Breach notification timelines are explicitly enumerated in IRP Section 6 — not
left to Legal to determine under incident pressure. The following timelines apply
based on data types processed:

| Regulation | Trigger | Notification Target | Timeline | Initiator |
| ---------- | ------- | ------------------- | -------- | --------- |
| GDPR (if EU personal data involved) | Breach confirmed | Supervisory Authority (lead DPA) | **72 hours** from awareness | ISSO + Legal |
| GDPR | Breach confirmed, high risk to individuals | Affected individuals | **Without undue delay** | Legal |
| California CCPA/CPRA | CA resident PII breach | California AG (if >500 CA residents) | **Most expedient time** (no hard deadline) | Legal |
| FedRAMP (if applicable) | Security incident | FedRAMP PMO + AO | **1 hour** (major incident) | ISSO |
| Contractual (customer agreements) | Breach confirmed | Affected customers | **Per contract** (review customer MSAs) | Legal + Account team |
| Internal | Any P1 or confirmed P2 | CISO + System Owner + Legal | **2 hours** from P1 declaration | ISSO |

Breach notification decision tree, pre-drafted notification templates, and regulatory
contact information are in IRP Appendix B. Legal counsel is on the PagerDuty escalation
path for all P1 incidents (auto-notified by PagerDuty within 1 hour of P1 declaration).

**Responsible Role:** ISSO (plan owner, annual review, version control), Legal (breach notification authority, Section 6 owner), SOC Lead (Section 3 owner, tabletop facilitation)

**Parameters:**
- IRP version: **v2.3** (approved 2026-03-15)
- Annual review month: **March**
- Tabletop cadence: **Annual** (February); scenarios rotate — no repeat within 3 years
- Distribution acknowledgment deadline: **5 business days**
- GDPR notification window: **72 hours** (explicitly enumerated in Section 6)
- FedRAMP major incident notification: **1 hour**
- Internal P1 notification: **2 hours** from declaration

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| IRP-LM-v2.3 (signed by ISSO, SO, CISO) | Confluence: LM-SECURITY / IR / IRP-LM-v2.3.pdf | 2026-03-15 |
| IRP version history (v1.0 through v2.3) | Confluence page history | Continuous |
| Distribution tracker v2.3 | Confluence: LM-SECURITY / IR / IRP-Distribution-Tracker.md | 2026-03-20 (all acknowledged) |
| Tabletop 2026 exercise report | Confluence: LM-SECURITY / IR / Tabletop-2026.pdf | 2026-02-18 |
| Tabletop 2025 exercise report | Confluence: LM-SECURITY / IR / Tabletop-2025.pdf | 2025-02-14 |
| Tabletop gap remediation tracker | Jira `SEC-IR` filter: label `tabletop-remediation` | 2026-04-01 (all 2026 gaps closed) |
| Breach notification templates | IRP Appendix B (Confluence) | 2026-03-15 |

**Test Procedure:**
1. Pull IRP-LM-v2.3 — verify ISSO, System Owner, and CISO signatures and a
   2026 approval date. Verify the document version matches the distribution tracker.
2. Pull the distribution tracker — verify all named roles acknowledged within 5
   business days of the 2026-03-16 distribution date.
3. Pull the 2026 tabletop report — verify it documents: scenario, participants,
   identified gaps, remediation actions, and owners. Pull the Jira `SEC-IR` tickets
   tagged `tabletop-remediation` — verify all 2026 gaps are closed.
4. Pull IRP Section 6 — verify GDPR 72-hour notification window is explicitly
   stated alongside the supervisory authority contact. Verify pre-drafted notification
   templates exist in Appendix B.
5. Verify tabletop scenario history — confirm the 2024, 2025, and 2026 scenarios are
   different (no repeat). Confirm the 2027 planned scenario is documented.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| IR-8(1) Breaches | Implemented | IRP Section 6 explicitly enumerates breach notification timelines: GDPR (72 hours to supervisory authority), CCPA (most expedient time), FedRAMP (1 hour for major incidents), internal P1 (2 hours). Pre-drafted notification templates in Appendix B. Legal counsel is on the PagerDuty P1 escalation path — auto-notified within 1 hour of declaration. No regulatory timeline is left to be "determined at time of incident." |

---

## What Makes This GREAT — Side-by-Side

| Dimension | Bad | Good | Great |
| --------- | --- | ---- | ----- |
| **Containment specificity** | "Contain the incident" | 3 runbook scenarios named | 5-scenario automated containment table: script name, trigger, affected resource, human approval required |
| **Automated containment** | Not mentioned | "SOAR planned Q4 2026" | 5 scripts in `platform-gitops/ir/`, tested quarterly, log to S3, executable by SOC on-call without management approval for P1 |
| **MTTD/MTTR** | Not measured | "Defined but not trended" | 4-quarter metrics table in the SSP; trend shows MTTD improving from 22 min to 8 min; reported to AO in monthly CA-7 report |
| **IR-4(4) correlation** | Not mentioned | "Planned Q4 2026" | 3 named OpenSearch correlation rules with trigger conditions, escalation logic, and quarterly review cadence |
| **Tabletop scenarios** | "Annual exercise" | Same credential scenario annually | Rotating 3-year scenario history table (2024–2026); 2027 scenario pre-planned; gap remediation tracked in Jira with closed-ticket evidence |
| **Breach notification** | "Addressed in plan" | "Legal determines applicable requirements" | Regulation-by-regulation table: GDPR 72hr, CCPA, FedRAMP 1hr, internal 2hr — no runtime determination under pressure |
| **IRP structure** | "Document exists" | Version, approval, distribution tracked | Section ownership table; each section has a named owner accountable for currency; version history on Confluence page |
| **Evidence preservation** | Not mentioned | "Velero snapshot" mentioned | Explicit forensic chain: Velero namespace backup + EBS snapshot + 72-hour log export, all to S3 `lm-audit-reports/ir-forensics/<incident-id>/`, 2-year retention |
