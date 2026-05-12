# System Security Plan — Risk Assessment (RA) Family

## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** This SSP would pass a readiness review with 4-5 clarification items.
> A NIST SP 800-30 risk assessment exists, is signed, and has a risk register. Trivy and
> Amazon Inspector are named with specific scan cadences and SLAs. POA&M exists with
> target dates and owners. Gaps: risk assessment was not updated after the Q4 2025 DR
> cluster addition (significant change not captured), RA-5(5) authenticated scanning is
> partial (worker nodes use Inspector but EKS API-level findings use unauthenticated
> surface scan), RA-5(11) CVD/security.txt does not exist, and POA&M has 3 items with
> overdue target dates that have not been formally re-baselined.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Final Draft — Pending ISSO Signature

---

## RA-3 — Risk Assessment

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

A formal risk assessment for the Links-Matrix Platform was completed using the
NIST SP 800-30 methodology. The assessment (`RA-LM-v2.0`, Confluence: LM-SECURITY /
Risk / RA-LM-v2.0.pdf) was approved by the ISSO (M. Chen) on 2026-02-10 and
reviewed by the System Owner (J. Rivera). It covers the system as described in
SSP-LM-v3.0.

**Methodology:**
- Threat sources: adversarial (external threat actors, insider threat), accidental
  (misconfiguration, operator error), environmental (cloud provider outage)
- Threat events mapped using MITRE ATT&CK (Enterprise matrix, cloud sub-techniques)
- Likelihood ratings: Very Low / Low / Moderate / High / Very High
- Impact ratings: Very Low / Low / Moderate / High / Very High
- Overall risk = Likelihood × Impact (5×5 matrix)

**Top identified risks (current assessment):**

| Risk ID | Threat Event | Likelihood | Impact | Risk Level | Status |
| ------- | ------------ | ---------- | ------ | ---------- | ------ |
| RISK-001 | Supply chain compromise via container image | Moderate | High | High | Mitigating (Trivy CI, ECR scan) |
| RISK-002 | Credential compromise — IAM key leaked to GitHub | High | High | High | Mitigating (gitleaks, IRSA) |
| RISK-003 | Insider threat — privileged user data exfiltration | Low | High | Moderate | Mitigating (CloudTrail, least privilege) |
| RISK-004 | Ransomware via compromised workload | Low | Very High | High | Mitigating (Velero, S3 Object Lock, network isolation) |
| RISK-005 | DDoS affecting platform availability | Moderate | Moderate | Moderate | Accepted (AWS Shield Standard) |

**Risk register:**
The risk register is maintained in Jira (`SEC-RISK` project). Each risk has an owner,
current status, treatment plan, and target remediation date. The register is reviewed
by the ISSO quarterly.

**Review cadence:**
The risk assessment is reviewed annually (Q1) and updated when significant changes
occur. The ISSO determines whether a system change is significant enough to trigger
an out-of-cycle update.

*(Note: the DR cluster (`lm-dr-cluster`) was added in us-west-2 in Q4 2025. This
constitutes a boundary change that should have triggered a risk assessment update —
the update has not yet been completed and is tracked in Jira `SEC-RISK-042`.)*

**Responsible Role:** ISSO (assessment owner, risk register review), System Owner (risk acceptance authority for Moderate and above), Cloud Security Engineer (threat modeling input)

**Parameters:**
- Methodology: NIST SP 800-30
- Annual review: Q1 (February)
- Risk register location: Jira `SEC-RISK` project
- Significant-change trigger: ISSO discretion

**Evidence / Artifacts:**
- `RA-LM-v2.0` (Confluence: LM-SECURITY / Risk / RA-LM-v2.0.pdf — ISSO-signed)
- Jira `SEC-RISK` project — risk register (current)
- MITRE ATT&CK Navigator export (Confluence: LM-SECURITY / Risk / attack-navigator-lm.json)

---

## RA-5 — Vulnerability Monitoring and Scanning

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

Vulnerability scanning on the Links-Matrix Platform uses multiple tools covering
container images, cloud infrastructure, and Kubernetes configuration.

**Scanning tools and cadence:**

| Tool | Scope | Cadence | Output |
| ---- | ----- | ------- | ------ |
| Trivy (CI) | Container images on PR | Every PR to `platform-gitops` | PR check — blocks merge on Critical/High |
| Amazon Inspector | ECR images, EKS worker nodes (agent) | Continuous (on push + new CVE) | Security Hub findings |
| kube-bench | CIS Kubernetes benchmark | Weekly CronJob | Jira `SEC-VULN` tickets |
| Trivy (weekly) | All running pod images in `lm-prod-cluster` | Weekly CronJob (Sunday 02:00 UTC) | Jira `SEC-VULN` tickets |
| Prowler | AWS account configuration | Weekly | Security Hub + Jira `SEC-VULN` |

**Remediation SLAs:**

| Severity | SLA from Discovery | Escalation |
| -------- | ---------------- | ---------- |
| Critical | 15 days | Auto-escalates to ISSO at 10 days if not assigned |
| High | 30 days | Reviewed at weekly vulnerability triage |
| Medium | 90 days | Reviewed at monthly vulnerability triage |
| Low | 180 days or risk-accepted | Reviewed at quarterly risk register review |

**Scan scope:**
All components within the Links-Matrix Platform authorization boundary are in scope.
No components are formally excluded. The Trivy weekly CronJob uses `kubectl get pods -A`
to enumerate running images and scans each unique image digest.

**CVE database updates:**
Amazon Inspector updates its CVE database continuously as NVD and vendor advisories
are published. Trivy downloads the latest vulnerability database at the start of each
scan run.

**Responsible Role:** DevSecOps (Trivy CI, weekly CronJob), Cloud Security Engineer (Amazon Inspector, Prowler), Platform Engineer (kube-bench CronJob)

**Parameters:**
- Critical SLA: 15 days
- High SLA: 30 days
- Continuous scanning: Amazon Inspector (ECR + EKS worker nodes)
- Weekly scheduled scans: Trivy full-cluster, kube-bench, Prowler

**Evidence / Artifacts:**
- Trivy CI workflow (`platform-gitops/.github/workflows/pr-checks.yaml`)
- Amazon Inspector findings (AWS Security Hub — filter: ProductName = "Inspector")
- Weekly Trivy CronJob manifest (`platform-gitops/security/trivy-weekly.yaml`)
- Jira `SEC-VULN` project — open findings by severity (last 90 days)
- Prowler report (Confluence: LM-SECURITY / Vuln / Prowler-2026-04.pdf)

**Enhancements Addressed:**
- **RA-5(2):** Amazon Inspector updates CVE definitions continuously. Trivy fetches
  the latest database on each scan invocation. No scheduled CVE refresh gap.
- **RA-5(3):** All boundary components are in scope. The weekly Trivy CronJob enumerates
  running images dynamically — no static exclusion list. *(Note: EKS control plane
  components managed by AWS are not scanned by the organization — AWS is responsible
  for control plane patch management.)*
- **RA-5(5):** Amazon Inspector uses an agent on EKS worker nodes for authenticated
  OS-level scanning. Trivy CI and weekly scans are image-based (authenticated to ECR).
  *(Note: EKS API-server configuration findings from kube-bench are derived from the
  Kubernetes API, not from privileged node access — this is a partial authenticated
  coverage gap for control-plane-level findings.)*
- **RA-5(11):** Not implemented. No CVD policy or `security.txt` file is published.
  External researchers have no documented channel to report vulnerabilities. Planned
  for Q3 2026.

---

## RA-7 — Risk Response

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

All identified risks and vulnerability findings are formally responded to through
a documented decision process. Risk responses follow NIST SP 800-39 categories:
mitigate, accept, transfer, or avoid.

**Response authority by risk level:**

| Risk Level | Response Authority |
| ---------- | ------------------ |
| Critical | CISO + System Owner (joint sign-off) |
| High | System Owner + ISSO |
| Moderate | ISSO |
| Low | ISSO or delegated Cloud Security Engineer |

**Risk acceptance:**
Risks accepted without full mitigation require a written risk acceptance memo
documenting: risk description, residual risk level, compensating controls,
accepting authority signature, and review date (maximum 1 year before re-evaluation).
Risk acceptances are stored in Confluence (LM-SECURITY / Risk / Acceptances).

Current risk acceptances:

| Risk Accept ID | Risk | Compensating Control | Accepted By | Expiry |
| -------------- | ---- | -------------------- | ----------- | ------ |
| RA-ACCEPT-001 | RISK-005 (DDoS, AWS Shield Standard) | AWS Shield Standard, rate limiting at ALB | System Owner | 2027-02-10 |
| RA-ACCEPT-002 | IA-2(8) gap — Okta push not FIDO2 | Push notification bound to enrolled device + ISSO alert on new enrollment | ISSO | 2026-12-31 |

**POA&M:**
The POA&M (`POAM-LM-v4.0`, Confluence: LM-SECURITY / POA&M) tracks all open risks
that cannot be immediately mitigated. Each item has: finding source, risk level,
responsible party, milestone description, and target date. The ISSO reviews the
POA&M monthly and updates target dates when slippage occurs with documented rationale.

Current POA&M summary:

| Finding | Risk Level | Owner | Target Date | Status |
| ------- | ---------- | ----- | ----------- | ------ |
| IA-3(1) — mTLS not implemented | Moderate | Platform Eng | 2026-12-31 | On track (Linkerd eval in progress) |
| IR-4(4) — cross-incident correlation | Low | Cloud Security | 2026-12-31 | On track |
| RA-5(11) — no CVD policy | Low | DevSecOps | 2026-09-30 | On track |
| RA-3 update (DR cluster) | Moderate | ISSO | 2026-05-31 | Overdue (was 2026-04-30) |
| IA-4(4) — userType attribute | Low | ITOps | 2026-09-30 | On track |

*(Note: POA&M item for RA-3 DR cluster update slipped from 2026-04-30 to 2026-05-31.
The target date was extended by ISSO decision — documented in POA&M notes. This is
one of three items that have slipped target dates in the last 6 months.)*

**Responsible Role:** ISSO (POA&M owner, risk acceptance authority for Moderate), System Owner (High/Critical risk acceptance), CISO (Critical risk acceptance), DevSecOps (vulnerability finding triage)

**Parameters:**
- POA&M review cadence: Monthly (ISSO)
- Risk acceptance maximum period: 1 year before re-evaluation
- Critical risk escalation: CISO + System Owner joint sign-off
- POA&M version: v4.0

**Evidence / Artifacts:**
- `POAM-LM-v4.0` (Confluence: LM-SECURITY / POA&M — current)
- Risk acceptance memos (Confluence: LM-SECURITY / Risk / Acceptances — RA-ACCEPT-001, RA-ACCEPT-002)
- Monthly POA&M review notes (Confluence: LM-SECURITY / POA&M / Review-Notes)
- Jira `SEC-RISK` project — risk response decisions linked to risk register items

---

## What Makes This GOOD (But Not Great) — Examiner's Notes

| Control | Strengths | Gaps |
| ------- | --------- | ---- |
| RA-3 | NIST SP 800-30 methodology named, MITRE ATT&CK used, top risks in table, ISSO-signed | Risk assessment not updated after DR cluster addition (boundary change) — SSP and risk assessment diverged for 5+ months |
| RA-3 | Risk register in Jira with owners and treatment status | "ISSO discretion" for significant-change trigger — same weakness as PL-2. No automated detection that a boundary change occurred. |
| RA-5 | 5-tool inventory with cadence, SLAs defined by severity, continuous Inspector coverage | RA-5(11) CVD/security.txt not implemented — external researchers have no responsible disclosure channel |
| RA-5 | Dynamic image enumeration (kubectl-based) prevents static exclusion list drift | kube-bench control-plane findings are not fully authenticated — partial gap for RA-5(5) |
| RA-7 | Authority table by risk level, risk acceptance memos with expiry, POA&M monthly review | 3 POA&M items with slipped target dates — pattern of slippage without root cause analysis or escalation |
| RA-7 | Risk acceptances have compensating controls documented | No CISA KEV integration — a KEV-listed vulnerability could sit in the 30-day High SLA queue rather than triggering immediate escalation |
