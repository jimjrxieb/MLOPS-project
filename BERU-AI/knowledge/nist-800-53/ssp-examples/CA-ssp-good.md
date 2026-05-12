# System Security Plan — Assessment, Authorization, and Monitoring (CA) Family

## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** This SSP would pass a readiness review with 3-5 clarification items.
> A 3PAO is named, monitoring tools are real, and the POA&M connection exists.
> Gaps: no specific penetration test scope documented, CA-7 strategy document is
> referenced but its contents are not summarized, enhancement CA-2(2) is thin,
> and trend data is described without being evidenced.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Final Draft — Pending ISSO Signature

---

## CA-2 — Control Assessments

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

The Links-Matrix Platform undergoes formal security control assessments on an annual
basis. The most recent assessment was conducted by Coalfire Systems (3PAO accredited
by the FedRAMP PMO) from 2026-01-15 through 2026-02-28. The assessment covered
the full Moderate baseline control set (110 controls) against the Links-Matrix
authorization boundary.

The assessment process followed a Security Assessment Plan (SAP) developed jointly
by Coalfire and the ISSO. The SAP documented the assessment scope, methodology
(document review, interviews, and technical testing), testing procedures, and schedule.
The completed Security Assessment Report (SAR) was delivered on 2026-03-01 and
identified 12 findings: 3 High, 6 Moderate, and 3 Low.

All findings from the SAR were entered into the system POA&M within 5 business days
of report delivery. The 3 High findings have been remediated and closed. The 6 Moderate
findings are in progress with target dates between 2026-06-01 and 2026-09-01.
The 3 Low findings are scheduled for remediation by end of 2026.

An annual penetration test is also included in the assessment scope. The most recent
penetration test was conducted by Coalfire's red team in January 2026. The test scope
covered the EKS cluster, application layer, and AWS account configuration.
Findings from the penetration test are incorporated into the SAR and POA&M.

The ISSO reviews the POA&M monthly and reports status to the Authorizing Official (AO)
via the monthly continuous monitoring report (see CA-7).

**Responsible Role:** ISSO (assessment owner, POA&M maintenance), CompO (evidence
packaging, 3PAO liaison)

**Parameters:**
- Assessment frequency: Annual
- Assessment organization: Coalfire Systems (FedRAMP-accredited 3PAO)
- POA&M update cadence: Monthly
- Last assessment dates: 2026-01-15 through 2026-02-28

**Evidence / Artifacts:**
- Security Assessment Plan (SAP) — 2026 engagement (retained in Confluence: LM-SECURITY / Assessments)
- Security Assessment Report (SAR) — Coalfire, delivered 2026-03-01
- POA&M — current state maintained in Confluence: LM-SECURITY / POA&M (last updated 2026-05-01)
- Penetration test report — Coalfire Red Team, January 2026
- ATO letter — issued 2026-03-15, expires 2029-03-15

**Enhancements Addressed:**
- **CA-2(1):** Coalfire Systems is an independent 3PAO accredited by the FedRAMP PMO.
  Coalfire has no implementation or operational role on the Links-Matrix Platform.
- **CA-2(2):** Annual penetration test included in the assessment scope. Conducted by
  Coalfire red team. *(Note: detailed penetration test methodology and rules of
  engagement are in the SAP but not summarized in this SSP.)*
- **CA-2(3):** Not applicable — no external organization assessments are currently
  leveraged for the Links-Matrix authorization. *(Future consideration: if a SOC 2
  Type II covering overlapping controls is obtained, ISSO will evaluate reuse.)*

---

## CA-7 — Continuous Monitoring

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

The Links-Matrix Platform continuous monitoring program is governed by the Continuous
Monitoring Strategy document (CM-STRAT-001, maintained in Confluence: LM-SECURITY /
Continuous Monitoring). The strategy defines the controls monitored, frequency, tools,
responsible parties, and reporting requirements.

**Automated Monitoring Tools:**

- **AWS Security Hub:** Aggregates findings from GuardDuty, AWS Config, Inspector, and
  Macie into a single compliance dashboard. The NIST SP 800-53 security standard is
  enabled in Security Hub, providing a per-control compliance score updated continuously.
  The ISSO reviews the Security Hub compliance score weekly.

- **AWS GuardDuty:** Enabled in both us-east-1 and us-west-2. Provides continuous
  ML-based threat detection against CloudTrail, VPC Flow Logs, and DNS logs.
  High-severity GuardDuty findings trigger PagerDuty alerts to the SOC.

- **AWS Config:** Continuous configuration compliance monitoring with 18 custom Config
  rules mapped to Links-Matrix security requirements. Non-compliant resources trigger
  a CloudWatch alarm routed to the SOC on-call.

- **ArgoCD:** Detects GitOps drift — any manual change to a K8s resource managed by
  ArgoCD generates a drift alert in the ArgoCD UI and a Slack notification to
  `#platform-alerts`. Drift is remediated within 4 hours per the GitOps runbook.

- **kube-bench:** Runs CIS Kubernetes Benchmark checks weekly via a CronJob. Results
  are posted to Confluence (LM-SECURITY / kube-bench Reports). Failures trigger
  a Jira ticket in the `PLAT-SEC` project.

**Reporting:**
The ISSO produces a monthly Continuous Monitoring Report distributed to the AO and
System Owner. The report covers: Security Hub compliance score, open GuardDuty findings,
Config rule compliance status, ArgoCD drift events, kube-bench results, and POA&M status.
Reports are retained in Confluence (LM-SECURITY / CM Reports).

**POA&M Integration:**
Findings from continuous monitoring that represent new control gaps are added to the
POA&M within 10 business days of identification. The ISSO reviews the POA&M monthly
against continuous monitoring data to verify open items are progressing.

**Responsible Role:** ISSO (strategy ownership, monthly report, POA&M integration),
SOC (GuardDuty and Security Hub alert triage), Platform Engineer (ArgoCD drift monitoring,
kube-bench), Cloud Security Engineer (Config rules, GuardDuty configuration)

**Parameters:**
- Monthly continuous monitoring report: Distributed by the 5th of each month
- Security Hub review: Weekly (ISSO)
- ArgoCD drift remediation SLA: 4 hours
- kube-bench cadence: Weekly

**Evidence / Artifacts:**
- Continuous Monitoring Strategy CM-STRAT-001 (Confluence: LM-SECURITY / Continuous Monitoring)
- Security Hub compliance dashboard (AWS Console — NIST 800-53 standard enabled)
- Monthly CM report for April 2026 (Confluence: LM-SECURITY / CM Reports / 2026-04)
- kube-bench weekly report (Confluence: LM-SECURITY / kube-bench Reports)
- POA&M with CM-sourced findings tagged (Confluence: LM-SECURITY / POA&M)

**Enhancements Addressed:**
- **CA-7(1):** AWS Security Hub with the NIST 800-53 standard provides an independent
  automated view of control status that supplements the ISSO's own monitoring.
  *(Note: Security Hub is not fully independent — it monitors the same AWS account.
  For a higher independence posture, a cross-account Security Hub aggregator is planned.)*
- **CA-7(4):** GuardDuty provides continuous threat intelligence-backed risk monitoring.
  High-severity findings are reviewed by the ISSO as part of the monthly CM report.
  *(Note: a formal threat intelligence feed integrated with the risk register is not
  yet implemented — this is a POA&M item targeted for Q4 2026.)*

---

## What Makes This GOOD (But Not Great) — Examiner's Notes

| Control | Strengths | Gaps |
| ------- | --------- | ---- |
| CA-2 | 3PAO named (Coalfire), assessment dates specific, finding counts quantified (3H/6M/3L), POA&M status described | Pen test methodology not documented in SSP; no rules of engagement summary; CA-2(2) is a note rather than an implementation statement |
| CA-2 | POA&M remediation dates cited | No risk acceptance documented for the 6 open Moderate findings — are they accepted or just in progress? |
| CA-7 | 5 tools named with specific functions, monthly report cadence, ArgoCD drift SLA | CA-7(1) independence caveat is honest but unresolved; cross-account Security Hub aggregator is "planned" without a POA&M entry |
| CA-7 | Monitoring feeds POA&M within 10 business days | No metrics trend data — no way to show whether posture is improving or degrading over time |
| Both | Connection between CA-2 findings and CA-7 monitoring is described | No formal mapping showing which CA-7 metrics correspond to which controls assessed in CA-2 — the feedback loop is prose, not structure |
