# System Security Plan — Assessment, Authorization, and Monitoring (CA) Family

## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** This SSP is auditor-ready. CA-2 and CA-7 are explicitly linked —
> the assessment produces findings, the findings feed the POA&M, and the continuous
> monitoring program tracks whether those controls stay healthy between assessments.
> Every enhancement addressed, every parameter named, every artifact located.

---

**System Name:** Links-Matrix Platform
**System Owner:** J. Rivera, Platform Engineering Lead (jrivera@links-matrix.io)
**ISSO:** M. Chen, Information System Security Officer (mchen@links-matrix.io)
**Prepared By:** M. Chen, ISSO
**Date:** 2026-05-01
**Review Date:** 2027-05-01 (annual) or upon significant system change
**Status:** Approved — ATO Granted 2026-03-15, expires 2029-03-15

**Control Relationship Note:** CA-2 and CA-7 form a closed loop on this system.
CA-2 produces the formal assessment record and POA&M that establishes the ATO.
CA-7 continuously monitors whether the controls that passed CA-2 remain effective
between assessments. Findings from CA-7 feed back into the POA&M. When the POA&M
closes items, CA-7 metrics confirm the control is healthy before the item is formally
closed. This loop is the operational definition of "authorization to operate."

---

## CA-2 — Control Assessments

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Low, Moderate, and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Assessment Program Summary

| Attribute | Detail |
| --------- | ------ |
| Assessment organization | Coalfire Systems, Inc. — FedRAMP-accredited 3PAO (PMO ID: 3PAO-0042) |
| Assessment frequency | Annual (FedRAMP Moderate requirement); significant change assessments triggered per SSP change policy |
| Most recent assessment | 2026-01-15 through 2026-02-28 |
| Assessment report delivered | 2026-03-01 |
| ATO issued | 2026-03-15 |
| ATO expiration | 2029-03-15 |
| Control baseline assessed | NIST SP 800-53 Rev 5 Moderate (110 controls, full boundary) |
| Next scheduled assessment | 2027-01 (date TBD by ISSO and Coalfire by 2026-11-01) |

### Assessment Plan (SAP)

The Security Assessment Plan for the 2026 engagement was developed jointly by the ISSO
and Coalfire between 2025-11-01 and 2025-12-15. The SAP is document `SAP-LM-2026`
retained in Confluence (LM-SECURITY / Assessments / 2026). It documents:

- **Assessment scope:** Full authorization boundary (EKS cluster `lm-prod-eks-us-east-1`,
  supporting AWS services, Okta tenant, AWS Client VPN endpoint). No systems were excluded
  without documented rationale.
- **Assessment methodology:** Three methods per NIST SP 800-53A — examine (document review),
  interview (key personnel), and test (technical validation). All 110 controls received
  at least examine and interview; 67 controls received technical testing.
- **Rules of engagement for penetration testing:** Scope limited to production-equivalent
  pre-prod environment (`lm-preprod`) with production data excluded. Active exploitation
  permitted. Social engineering excluded. Emergency stop contact: J. Rivera (ISSO backup).
- **Schedule:** Document review Jan 15–22; interviews Jan 23–31; technical testing Feb 1–14;
  pen test Feb 15–21; report draft Feb 22–28.
- **Assessor independence:** Coalfire personnel have no employment, contractual, or financial
  relationship with Links-Matrix beyond this assessment engagement. ISSO confirmed no
  organizational conflict of interest in writing before engagement start.

### Assessment Report (SAR) Summary

The SAR (`SAR-LM-2026`, delivered 2026-03-01) identified the following findings:

| Severity | Count | Remediated | In Progress | Accepted Risk | Not Started |
| -------- | ----- | ---------- | ----------- | ------------- | ----------- |
| High | 3 | 3 | 0 | 0 | 0 |
| Moderate | 6 | 2 | 4 | 0 | 0 |
| Low | 3 | 0 | 2 | 1 | 0 |
| **Total** | **12** | **5** | **6** | **1** | **0** |

The 1 accepted risk (Low, finding ID `SAR-LM-2026-L3`) relates to a legacy application
endpoint that cannot enforce HSTS due to a third-party integration constraint. Risk
acceptance is documented in `RISK-ACCEPT-2026-001` signed by the System Owner and ISSO,
with a compensating control (WAF rule blocking HTTP-to-HTTPS redirect bypass) in place.

All 12 findings were entered into the POA&M within 3 business days of SAR delivery
(by 2026-03-06). Current POA&M status is tracked in Confluence (LM-SECURITY / POA&M)
and reviewed monthly by the ISSO.

### Penetration Test

The 2026 penetration test was conducted by Coalfire's red team (lead: Senior Penetration
Tester, OSCP certified) from 2026-02-15 through 2026-02-21 against the `lm-preprod`
environment (production-equivalent configuration, no live customer data).

| Test Domain | Findings | Severity Distribution |
| ----------- | -------- | --------------------- |
| Network / perimeter | 2 findings | 1 Moderate (exposed debug endpoint), 1 Low (TLS cipher downgrade possible) |
| Application layer | 3 findings | 1 High (IDOR on user resource endpoint), 2 Moderate (missing rate limiting, verbose error messages) |
| Cloud configuration | 1 finding | 1 High (overly permissive S3 bucket policy in preprod mirroring prod config) |
| Kubernetes cluster | 2 findings | 1 High (privileged container in a non-production namespace), 2 Low |
| Social engineering | Not in scope | — |

The 3 High findings were remediated in production within 14 days of report delivery
(by 2026-03-07) with remediation evidence provided to Coalfire for closure confirmation.
Remediation confirmation received 2026-03-10.

### Significant Change Assessment Policy

The ISSO assesses whether a significant change to the authorization boundary triggers
a required assessment update per the Change Assessment Policy (`CAP-001`, Confluence:
LM-SECURITY / Policies). Significant changes include: adding a new AWS service processing
sensitive data, adding a new K8s cluster, changing the identity provider, or changing
the network boundary. The ISSO makes the determination within 10 business days of a
change request and documents the decision in the change record.

**Responsible Role:** ISSO (assessment owner, POA&M, SAP/SAR custody), CompO (evidence
packaging, 3PAO logistics), System Owner (risk acceptance sign-off)

**Parameters:**
- Assessment frequency: **Annual** (FedRAMP Moderate requirement)
- Assessment organization independence: **FedRAMP-accredited 3PAO** (Coalfire, PMO ID 3PAO-0042)
- Significant change assessment determination: **Within 10 business days** of change request
- High finding remediation SLA: **30 days** from SAR delivery
- Moderate finding remediation SLA: **90 days** from SAR delivery (or accepted risk documented)
- POA&M entry deadline: **Within 3 business days** of SAR delivery

**Evidence / Artifacts:**

| Artifact | Location | Date |
| -------- | -------- | ---- |
| Security Assessment Plan SAP-LM-2026 | Confluence: LM-SECURITY / Assessments / 2026 / SAP-LM-2026.pdf | 2025-12-15 (signed) |
| Security Assessment Report SAR-LM-2026 | Confluence: LM-SECURITY / Assessments / 2026 / SAR-LM-2026.pdf | 2026-03-01 (delivered) |
| Penetration test report (Coalfire red team) | Confluence: LM-SECURITY / Assessments / 2026 / pentest-report-2026.pdf | 2026-02-28 |
| High-finding remediation evidence (3 items) | Confluence: LM-SECURITY / Assessments / 2026 / remediation-evidence/ | 2026-03-07 |
| Coalfire remediation closure confirmation | Confluence: LM-SECURITY / Assessments / 2026 / closure-confirmation-2026-03-10.pdf | 2026-03-10 |
| POA&M (current) | Confluence: LM-SECURITY / POA&M | Reviewed 2026-05-01 |
| Risk acceptance RISK-ACCEPT-2026-001 | Confluence: LM-SECURITY / Risk Acceptances | 2026-03-12 (signed SO + ISSO) |
| ATO letter | Confluence: LM-SECURITY / Authorization / ATO-2026-03-15.pdf | 2026-03-15 |
| Change Assessment Policy CAP-001 | Confluence: LM-SECURITY / Policies / CAP-001 | 2026-01-10 (last reviewed) |

**Test Procedure:**
1. Pull the SAR from Confluence — verify it was authored by Coalfire (not Links-Matrix
   staff), covers all 110 Moderate baseline controls, and was delivered within 30 days
   of assessment completion.
2. Pull the POA&M — verify every finding from the SAR has a corresponding POA&M entry
   with an assigned owner and target remediation date. Verify no High findings are open
   beyond the 30-day SLA.
3. Pull the penetration test report — verify the scope matches the authorization boundary
   (or the preprod equivalent), and that all High findings are either closed with
   remediation evidence or have an accepted-risk document.
4. For the 1 accepted risk (RISK-ACCEPT-2026-001) — verify it has System Owner and ISSO
   signatures and a compensating control documented.
5. Pull the ATO letter — verify issuance date and expiration date are present and the
   issuing AO's name and title are on the document.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| CA-2(1) Independent Assessors | Implemented | Coalfire Systems is a FedRAMP-accredited 3PAO (PMO ID 3PAO-0042) with no implementation or operational role on the Links-Matrix Platform. Organizational conflict of interest was confirmed in writing by the ISSO before engagement start. Documentation retained in SAP-LM-2026. |
| CA-2(2) Specialized Assessments | Implemented | Annual penetration test is included in the assessment engagement scope. Coalfire red team (OSCP-certified lead) conducted external, application, cloud, and K8s testing from 2026-02-15 to 2026-02-21. Rules of engagement documented in SAP-LM-2026. Findings incorporated into the SAR and POA&M. Next pen test scheduled for January 2027 as part of the 2027 assessment engagement. |
| CA-2(3) Leveraging Results from External Organizations | Not Applicable — current cycle | No external organization assessments currently cover overlapping controls in a form meeting FedRAMP reuse requirements. The ISSO will evaluate whether a future SOC 2 Type II engagement can be leveraged for overlapping controls before the 2027 assessment. Decision will be documented in the 2027 SAP. |

---

## CA-7 — Continuous Monitoring

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Low, Moderate, and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Continuous Monitoring Strategy

The Links-Matrix Continuous Monitoring Strategy (`CM-STRAT-002`, Confluence: LM-SECURITY /
Continuous Monitoring / CM-STRAT-002.md, last reviewed 2026-04-01) defines the full
monitoring program. It specifies:

- Controls monitored continuously vs. on a scheduled cadence
- Metrics tracked per control family
- Responsible parties for each monitoring domain
- Escalation thresholds and response procedures
- Reporting format and distribution for the monthly CM report
- Integration with the POA&M and the CA-2 assessment cycle

The strategy was reviewed and approved by the ISSO and System Owner at ATO issuance
(2026-03-15) and is reviewed annually thereafter or when a significant change occurs.

### Monitoring Tool Coverage

Each monitoring tool is explicitly mapped to the CA-2 controls it tracks, so there are
no controls that pass assessment but drift unchecked between annual assessments.

| Tool | Controls Monitored | Cadence | Responsible | Alert Path |
| ---- | ------------------ | ------- | ----------- | ---------- |
| AWS Security Hub (NIST 800-53 standard) | AC, AU, CM, IA, SC, SI — 78 of 110 controls | Continuous (re-evaluates on resource change) | Cloud Security Engineer | Security Hub finding → EventBridge → PagerDuty P2 |
| AWS Config (18 custom rules) | CM-2, CM-6, CM-7, SC-7, SC-8, AC-3, AC-6 specific rules | Continuous (on resource change) | Cloud Security Engineer | Config non-compliance → CloudWatch alarm → PagerDuty P2 |
| Amazon GuardDuty | AU-6/CA-7 threat detection (CloudTrail, VPC, DNS) | Continuous | SOC | High finding → PagerDuty P1; Medium → PagerDuty P2 |
| ArgoCD drift detection | CM-2, CM-3 (GitOps state) | Continuous (on K8s resource change) | Platform Engineer | Drift alert → Slack `#platform-alerts` → Jira `PLAT-SEC` |
| kube-bench (CIS K8s Benchmark) | CM-6, AC-3, SC-7, SC-8 (K8s layer) | Weekly (Sunday 02:00 UTC) | Platform Engineer | Failures → Jira `PLAT-SEC` ticket |
| Prowler (AWS CIS + NIST mapping) | AC-6, IA-2, AU-2, SC-28, CM-7 (AWS layer) | Weekly (Saturday 03:00 UTC) | Cloud Security Engineer | New HIGH findings → Jira `CLOUD-SEC` ticket |
| Trivy (image scanning) | SI-2, SI-3 (container vulnerability) | On every image push + weekly full scan | DevSecOps | Critical CVE → CI pipeline block + PagerDuty P2 |
| Falco (runtime behavioral) | SI-3, SI-4, AU-12 (runtime events) | Continuous | SOC | CRITICAL/ERROR priority → PagerDuty P1 |
| IAM Access Analyzer | AC-6, AC-3 (IAM least privilege) | Continuous (re-evaluates on policy change) | Cloud Security Engineer | External access finding → PagerDuty P1 |
| Certificate expiry monitor | SC-8, SC-12 (TLS cert health) | Daily check; 30-day and 7-day pre-expiry alerts | Platform Engineer | 30 days → Slack `#platform-alerts`; 7 days → PagerDuty P1 |

### Continuous Monitoring Metrics

The following metrics are tracked in the monthly CM report and trended over time.
Trend data is retained for the life of the ATO to demonstrate posture trajectory to the AO.

| Metric | Target | April 2026 Actual | Trend (3 months) |
| ------ | ------ | ----------------- | ---------------- |
| Security Hub NIST 800-53 compliance score | ≥90% | 94% | ↑ (was 88% in Feb) |
| Open GuardDuty High findings | 0 | 0 | Stable |
| Open GuardDuty Medium findings (unacknowledged >48h) | 0 | 1 | ↓ (was 3 in Feb) |
| AWS Config non-compliant rules | 0 | 0 | Stable |
| ArgoCD drift events (unresolved >4h) | 0 | 0 | Stable |
| kube-bench CIS Level 1 failures | 0 | 2 | ↓ (was 5 in Feb, both in PLAT-SEC backlog) |
| Open Critical CVEs in deployed images | 0 | 0 | Stable |
| Open POA&M items (total) | Decreasing | 7 (was 12 at ATO) | ↓ improving |
| High POA&M items open >30 days past SLA | 0 | 0 | Stable |

### Monthly Continuous Monitoring Report

The ISSO produces a monthly CM report by the 5th of each month. The report is distributed
to:
- Authorizing Official (AO): direct email + uploaded to FedRAMP secure repository
- System Owner: J. Rivera (email)
- CISO: email
- Compliance Officer: email

The report format follows FedRAMP's monthly reporting template and includes: executive
summary, metric scorecard (table above), open POA&M items with current status, new findings
since last report, and a recommendation section. Reports are archived in S3
`lm-audit-reports/cm-monthly/` with 7-year retention.

The April 2026 report is available at S3 `lm-audit-reports/cm-monthly/2026-04.pdf`.

### POA&M Integration

New findings from continuous monitoring tools that represent control gaps are assessed
by the ISSO and, if confirmed, added to the POA&M within **5 business days**. Each
POA&M entry includes:
- Finding source (tool name + rule ID)
- Affected control ID
- Finding description and evidence
- Assigned owner (by role + name)
- Target remediation date (based on severity SLA)
- Milestone history (updated monthly)

When a POA&M item is remediated, the corresponding CA-7 metric must show compliant
status for **two consecutive monthly reports** before the item is formally closed.
This prevents premature closure of items that regressed after initial fix.

### Threat Intelligence Integration

The ISSO subscribes to the following threat intelligence sources that inform CA-7
risk monitoring:

- **CISA Known Exploited Vulnerabilities (KEV) catalog:** Checked weekly via automated
  script (`kev-check.sh` in `platform-gitops/tools/`). If a KEV-listed CVE matches a
  deployed component, a Jira `SEC` ticket is auto-created with P1 priority regardless
  of Trivy severity rating.
- **CISA advisories and alerts:** ISSO subscribes to CISA email alerts. Relevant
  advisories are assessed within 5 business days and documented in the CM report if they
  affect the control posture.
- **GuardDuty threat intelligence:** AWS-managed threat intel feeds are enabled by
  default in GuardDuty. No additional configuration required.

**Responsible Role:** ISSO (strategy ownership, monthly report, POA&M integration,
threat intel assessment), Cloud Security Engineer (Security Hub, Config, GuardDuty,
Prowler, IAM Access Analyzer), Platform Engineer (ArgoCD, kube-bench, certificate monitor),
SOC (GuardDuty alert triage, Falco), DevSecOps (Trivy image scanning)

**Parameters:**
- Monthly CM report delivery: **By the 5th of each month**
- New finding POA&M entry deadline: **Within 5 business days** of identification
- POA&M closure confirmation: **Two consecutive monthly reports** showing compliant metric
- ArgoCD drift remediation SLA: **4 hours**
- KEV match response: **P1 Jira ticket auto-created** (same-day ISSO review)
- Security Hub NIST 800-53 compliance score target: **≥90%**
- CM strategy review cadence: **Annual** (or significant change)

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| Continuous Monitoring Strategy CM-STRAT-002 | Confluence: LM-SECURITY / Continuous Monitoring / CM-STRAT-002.md | 2026-04-01 |
| Monthly CM report April 2026 | S3 `lm-audit-reports/cm-monthly/2026-04.pdf` | 2026-05-04 (distributed) |
| CM report archive (all months since ATO) | S3 `lm-audit-reports/cm-monthly/` | Continuous |
| Security Hub NIST 800-53 compliance dashboard | AWS Console → Security Hub → Standards | Continuous |
| AWS Config rule compliance status | AWS Console → Config → Rules | Continuous |
| GuardDuty active findings | AWS Console → GuardDuty → Findings | Continuous |
| kube-bench weekly report | Confluence: LM-SECURITY / kube-bench Reports / 2026-W17.md | 2026-04-28 |
| Prowler weekly report | S3 `lm-audit-reports/prowler/2026-04-26.json` | 2026-04-26 |
| Metric trend data (Feb–Apr 2026) | Confluence: LM-SECURITY / CM Metrics / 2026-Q1-Q2-trend.md | 2026-05-01 |
| POA&M current state | Confluence: LM-SECURITY / POA&M | 2026-05-01 |
| KEV check script and last run output | `platform-gitops/tools/kev-check.sh` + Jira `SEC` project | 2026-04-28 |

**Test Procedure:**
1. Pull the CM strategy (`CM-STRAT-002`) — verify it names each monitoring tool, the
   controls it covers, and the responsible party. Verify its last-reviewed date is within
   12 months.
2. Pull the most recent monthly CM report from S3 — verify it was delivered by the 5th
   of the reporting month, contains the metric scorecard, and was distributed to the AO.
3. Pull Security Hub in the AWS console — verify the NIST 800-53 standard is enabled
   and the compliance score is ≥90%. Pull one non-compliant finding and verify there
   is a corresponding POA&M entry or documented justification.
4. Pull the POA&M — select any finding sourced from a CA-7 monitoring tool. Verify it
   has an assigned owner, a target date, and monthly milestone updates. Verify no High
   findings are open past their 30-day remediation SLA.
5. Run `kev-check.sh` manually — verify it queries the CISA KEV catalog and compares
   against the current deployed image manifest. Verify the output is consistent with
   the most recent Jira `SEC` ticket log.
6. Pull the metric trend table — verify data exists for at least three consecutive months
   and shows directionality (improving, stable, or degrading with explanation).

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| CA-7(1) Independent Assessment | Implemented | AWS Security Hub (NIST 800-53 standard) provides an automated independent view of control status evaluated against AWS-managed assessment rules — not self-assessed by the Links-Matrix team. Prowler (run separately from the production account by the Cloud Security Engineer, not the Platform team operating the system) provides a second independent layer. Findings feed the monthly CM report reviewed by the AO. |
| CA-7(4) Risk Monitoring | Implemented | CISA KEV catalog checked weekly via automated script; new KEV matches create P1 Jira tickets for same-day ISSO review. CISA advisories reviewed within 5 business days. GuardDuty provides continuous AWS-managed threat intelligence. Threat intelligence findings are included in the monthly CM report under the "Risk Environment" section. Formal integration with a commercial threat intelligence platform is in the CM roadmap (target: Q1 2027, no current POA&M item — enhancement of existing capability, not remediation of a gap). |

---

## What Makes This GREAT — Side-by-Side

| Dimension | Bad | Good | Great |
| --------- | --- | ---- | ----- |
| **Assessor independence** | "Security team reviews controls" (self-assessment) | "Coalfire Systems" named | Coalfire named + PMO ID + conflict-of-interest confirmation in writing documented in SAP |
| **Assessment scope** | Not defined | "Full Moderate baseline (110 controls)" | Full baseline + methodology per control (examine/interview/test) + 67 of 110 received technical testing — auditor can verify coverage |
| **Finding quantification** | Not mentioned | "3H/6M/3L" | Full table: High/Moderate/Low × Remediated/In Progress/Accepted/Not Started — status verifiable against POA&M |
| **Penetration test** | Not mentioned | "Annual pen test included" — no detail | Scope, assessor credential (OSCP), test domain table with findings by domain, High remediation timeline, closure confirmation date |
| **Risk acceptance** | Not mentioned | Not mentioned | Specific finding ID, signed by SO + ISSO, compensating control documented — auditor can pull it |
| **CA-7 tools** | "Cloud security tools" | 5 tools named with function | 10-tool coverage table: tool, controls monitored, cadence, owner, alert path — no control is unmonitored |
| **Metrics trend** | Not mentioned | "Improving" (assertion) | 9-row metric table with target, April actual, and 3-month trend arrows — posture trajectory is evidenced, not claimed |
| **POA&M closure gate** | Not mentioned | "Added within 10 days" | Two consecutive monthly reports showing compliant status required before closure — prevents regression-then-close |
| **Threat intelligence** | Not mentioned | "GuardDuty provides threat detection" | Three named sources (CISA KEV, CISA advisories, GuardDuty), automated KEV check script, P1 ticket on KEV match, 5-day advisory review SLA |
| **CA-2 ↔ CA-7 link** | None | "CA-7 findings feed POA&M" (prose) | Explicit strategy doc maps each CA-7 tool to the CA-2 controls it monitors; POA&M closure requires CA-7 metric confirmation — the loop is structural, not narrative |
