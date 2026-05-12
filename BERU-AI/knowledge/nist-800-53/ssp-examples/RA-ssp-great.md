# System Security Plan — Risk Assessment (RA) Family

## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** This SSP would pass a FedRAMP readiness review with zero major
> findings. The risk assessment is updated automatically when boundary-affecting IaC
> merges occur. Vulnerability scanning covers every boundary component with authenticated
> depth, continuous CVE feed, and CISA KEV as a mandatory-escalation override. POA&M
> items are trend-tracked quarterly — open vs. closed rates show the risk posture is
> improving. RA-5(11) CVD policy with security.txt and a researcher acknowledgment log
> closes the external disclosure gap. Risk responses are linked from the risk register
> to the specific POA&M item or risk acceptance, so auditors can follow the full chain
> from identified risk to disposition.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Approved — Active Authorization

> **Control chain:** RA-3 identifies risks → RA-5 detects vulnerabilities that feed
> the risk register → RA-7 documents the disposition of each finding. CA-7 continuous
> monitoring produces the signals RA-5 acts on. SI-2 (remediation) is the execution
> arm of RA-7 mitigate decisions. POA&M items created by RA-7 are tracked as CA-7
> continuous monitoring artifacts.

---

## RA-3 — Risk Assessment

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

### Risk Assessment Document

The Links-Matrix Platform risk assessment (`RA-LM-v3.0`, Confluence: LM-SECURITY /
Risk / RA-LM-v3.0.pdf and `platform-gitops/risk/ra-lm-v3.0.md` in git) was completed
using NIST SP 800-30 Rev 1 methodology. Approved by: ISSO (M. Chen) and System Owner
(J. Rivera) on 2026-03-01. The risk assessment is the direct input to control selection
in SSP-LM-v4.0 — control families are selected and scoped based on the identified
threats and risk ratings.

### Threat Identification Methodology

Threats are enumerated from three sources, cross-referenced with MITRE ATT&CK (Enterprise,
Cloud, Kubernetes sub-techniques):

1. **NIST SP 800-30 threat source catalog** — adversarial, accidental, structural, environmental
2. **MITRE ATT&CK Navigator** — threat scenario coverage map (`platform-gitops/risk/attack-navigator-lm.json`, updated quarterly)
3. **Prior incident data** — IR PIR reports (last 24 months) feed identified threat events

Likelihood ratings use a 5-point scale (Very Low / Low / Moderate / High / Very High)
based on threat capability × intent × system exposure. Impact ratings use FIPS 199
impact levels (Low / Moderate / High) per information type affected.

### Risk Register

The risk register is maintained in two synchronized forms:
- **Structured source:** `platform-gitops/risk/risk-register.md` (version-controlled, PR-reviewed)
- **Operational view:** Jira `SEC-RISK` project (linked to source via GitHub Actions sync)

**Current risk register (top risks):**

| Risk ID | Threat Event | ATT&CK Technique | Likelihood | Impact | Risk Level | Response | POA&M / Accept |
| ------- | ------------ | ---------------- | ---------- | ------ | ---------- | -------- | -------------- |
| RISK-001 | Supply chain compromise — malicious image | T1195.002 | Moderate | High | High | Mitigate | Trivy CI, ECR scanning, image signing (Cosign) |
| RISK-002 | Credential compromise — IAM key exfiltration | T1552.001 | High | High | High | Mitigate | gitleaks, IRSA no-static-key enforcement |
| RISK-003 | Insider threat — privileged data exfiltration | T1078.004 | Low | High | Moderate | Mitigate | CloudTrail, least privilege, SoD AC-5 |
| RISK-004 | Ransomware via compromised workload | T1486 | Low | Very High | High | Mitigate | Velero, S3 Object Lock Compliance, IR-4 isolation scripts |
| RISK-005 | DDoS — platform availability | T1498 | Moderate | Moderate | Moderate | Accept | AWS Shield Standard (RA-ACCEPT-001) |
| RISK-006 | Kubernetes API server exposure | T1133 | Low | High | Moderate | Mitigate | Private endpoint, OIDC auth, no public kubeconfig |
| RISK-007 | Secrets in git history | T1552.003 | Moderate | High | High | Mitigate | truffleHog quarterly history scan, gitleaks CI |

### Significant-Change Triggers (Automated)

Risk assessment currency is enforced by the same `ssp-freshness-check.yaml` workflow
that monitors PL-2. When the workflow detects a new boundary component not in the
current risk register, it creates a Jira ticket (`SEC-RISK` project, label:
`risk-assessment-update`, priority: High) assigned to the ISSO with a 30-day SLA.

Additionally, the following changes trigger a mandatory risk assessment update task:

| Change Type | Trigger | SLA |
| ----------- | ------- | --- |
| New AWS service in boundary | Terraform merge to `boundary-services.tf` | 30 days |
| New information type (FIPS 199 change) | DLP policy update | 15 days |
| New external interconnection | ISA/MOU signed | 15 days |
| New CVE class affecting architecture | CISA KEV listing for component in boundary | 48 hours (risk register annotation, not full assessment) |
| Annual comprehensive review | February each year | Complete by March AO re-approval |

**Annual review history:**

| Year | Completed | Approver | Significant Changes Since Prior |
| ---- | --------- | -------- | ------------------------------- |
| 2024 | 2024-03-01 | ISSO M. Chen | Initial assessment (ATO basis) |
| 2025 | 2025-03-15 | ISSO M. Chen | GuardDuty ML added; IAM key scanner deployed |
| 2026 | 2026-03-01 | ISSO M. Chen + System Owner J. Rivera | DR cluster added (us-west-2); RA-LM v3.0 |

**Responsible Role:** ISSO (assessment owner, register review), Cloud Security Engineer (ATT&CK Navigator updates, threat modeling input), System Owner (risk acceptance authority ≥ High)

**Parameters:**
- Methodology: NIST SP 800-30 Rev 1
- ATT&CK framework: Enterprise + Cloud + Kubernetes sub-techniques
- Annual review: February (complete by March AO re-approval)
- Significant-change trigger: Automated (ssp-freshness-check) + defined change types (table above)
- Risk register location: `platform-gitops/risk/risk-register.md` (authoritative), Jira `SEC-RISK` (operational)

**Evidence / Artifacts:**
- `RA-LM-v3.0` source (`platform-gitops/risk/ra-lm-v3.0.md`, git tag `ra-v3.0`)
- `RA-LM-v3.0` human-readable (Confluence: LM-SECURITY / Risk / RA-LM-v3.0.pdf — signed)
- Risk register (`platform-gitops/risk/risk-register.md` — current)
- MITRE ATT&CK Navigator export (`platform-gitops/risk/attack-navigator-lm.json`)
- Annual review history (Confluence: LM-SECURITY / Risk / Assessment-History)

---

## RA-5 — Vulnerability Monitoring and Scanning

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

### Scan Coverage Map

Every component within the Links-Matrix Platform authorization boundary is covered
by at least one scanning tool. The table below maps each boundary component category
to its scanning tools, cadence, and authentication method.

| Component | Tool | Cadence | Auth Method | Output |
| --------- | ---- | ------- | ----------- | ------ |
| Container images (new PRs) | Trivy (CI) | Every PR | ECR authenticated | PR block on Critical/High |
| Container images (running) | Trivy weekly CronJob | Weekly (Sun 02:00 UTC) | ECR authenticated | Jira `SEC-VULN` |
| Container images (registry) | Amazon Inspector + ECR Enhanced Scan | Continuous + on push | AWS IAM (Inspector agent) | Security Hub |
| EKS worker nodes (OS/packages) | Amazon Inspector agent | Continuous | IAM agent on node | Security Hub |
| Kubernetes config (CIS benchmark) | kube-bench | Weekly CronJob | K8s API (ServiceAccount) | Jira `SEC-VULN` |
| AWS account configuration | Prowler | Weekly | IAM role (read-only) | Security Hub + Jira `SEC-VULN` |
| AWS Config compliance | AWS Config managed rules | Continuous | AWS Config service | Security Hub |
| Web application (DAST) | OWASP ZAP | Quarterly | Authenticated session (Okta) | Jira `SEC-VULN` |
| IaC (Terraform) | Checkov (CI) | Every PR to `infra-iac` | N/A (static) | PR block on High |
| Git history (secrets) | truffleHog | Quarterly scheduled + every PR | GitHub token | Jira `SEC-VULN` |

No components within the authorization boundary are excluded from scanning.
The EKS control plane is managed by AWS — AWS is responsible for control plane
patch management (documented in the AWS Shared Responsibility Model). This is the
only out-of-scope component and the rationale is documented in `platform-gitops/risk/scan-exclusions.md`.

### CVE Database Currency (RA-5(2))

| Tool | CVE Feed Source | Update Cadence |
| ---- | --------------- | -------------- |
| Amazon Inspector | NVD + AWS threat intelligence | Continuous (real-time) |
| ECR Enhanced Scan | Snyk vulnerability database | Continuous (on new CVE) |
| Trivy | ghcr.io/aquasecurity/trivy-db | Downloaded fresh per scan invocation |
| Prowler | NIST NVD API | Per weekly run |
| Checkov | Checkov rule updates | Per CI invocation (latest rule version) |

### CISA KEV Override

Any CVE listed on the CISA Known Exploited Vulnerabilities catalog that affects
a component within the Links-Matrix authorization boundary triggers an immediate
escalation — regardless of CVSS score or standard SLA:

- A GitHub Actions workflow (`kev-check.yaml`) runs daily, pulling the CISA KEV JSON
  feed and comparing it against the running image SBOMs (`platform-gitops/sbom/`).
- A KEV match creates a Jira `SEC-VULN` ticket with priority **Critical**, label
  `kev-match`, and assigns it to the Cloud Security Engineer and ISSO.
- SLA for KEV findings: **48 hours to patch or implement compensating control**
  (regardless of the standard Critical 15-day SLA).

### Remediation SLAs

| Severity | Standard SLA | KEV Override SLA | Escalation at |
| -------- | ----------- | ---------------- | ------------- |
| Critical | 15 days | 48 hours | 10 days (ISSO alert) |
| High | 30 days | 48 hours | 21 days (ISSO alert) |
| Medium | 90 days | N/A | 75 days (team lead alert) |
| Low | 180 days or risk-accept | N/A | Quarterly review |

### Vulnerability Trend (Last 4 Quarters)

| Quarter | Critical Open (EOQ) | High Open (EOQ) | New Critical | Closed Critical | KEV Matches |
| ------- | ------------------- | --------------- | ------------ | --------------- | ----------- |
| 2025-Q2 | 4 | 18 | 6 | 4 | 1 (patched in 36 hrs) |
| 2025-Q3 | 2 | 11 | 3 | 5 | 0 |
| 2025-Q4 | 1 | 8 | 2 | 3 | 1 (patched in 41 hrs) |
| 2026-Q1 | 0 | 6 | 1 | 2 | 0 |

Critical count trend: 4 → 2 → 1 → 0. Vulnerability backlog is decreasing quarter
over quarter — evidence that the remediation program is effective, not just scanning.

### Public Disclosure Program (RA-5(11))

The Links-Matrix Platform maintains a coordinated vulnerability disclosure (CVD) policy:

- **`security.txt`** published at `https://links-matrix.io/.well-known/security.txt`
  per RFC 9116, containing: contact (`security@links-matrix.io`), encryption key
  (PGP public key for encrypted disclosure), expires field (annual), and policy URL.
- **CVD policy** (Confluence: LM-SECURITY / CVD / CVD-Policy-v1.0.pdf) defines:
  disclosure timeline (90-day default from report to public disclosure), safe harbor
  statement, scope (Links-Matrix Platform authorization boundary), out-of-scope items
  (third-party services, end-user workstations).
- **Researcher acknowledgment log** (`platform-gitops/security/cvd-log.md`):
  records each reported finding, triage status, and resolution date.

**CVD log (last 12 months):**

| Report Date | Reporter | Severity | Finding | Resolved | Disclosed |
| ----------- | -------- | -------- | ------- | -------- | --------- |
| 2026-02-14 | External (anonymous) | Medium | Open redirect in auth callback | 2026-02-28 | Coordinated (2026-03-15) |
| 2025-10-03 | External (named, rewarded) | High | SSRF in image proxy | 2025-10-20 | Coordinated (2026-01-03) |

**Responsible Role:** DevSecOps (CI scanning, kube-bench, truffleHog, SBOM maintenance), Cloud Security Engineer (Inspector, Prowler, KEV workflow, CVD triage), Platform Engineer (kube-bench CronJob, ZAP quarterly), ISSO (SLA oversight, KEV escalation)

**Parameters:**
- Critical SLA: 15 days (KEV override: 48 hours)
- High SLA: 30 days (KEV override: 48 hours)
- KEV check cadence: Daily (automated, `kev-check.yaml`)
- DAST cadence: Quarterly (authenticated)
- CVD contact: `security@links-matrix.io`
- CVD disclosure timeline: 90 days default

**Evidence / Artifacts:**
- Trivy CI workflow (`platform-gitops/.github/workflows/pr-checks.yaml`)
- Amazon Inspector findings (AWS Security Hub)
- Trivy weekly CronJob + SBOM store (`platform-gitops/security/trivy-weekly.yaml`, `platform-gitops/sbom/`)
- kube-bench CronJob (`platform-gitops/security/kube-bench-weekly.yaml`)
- KEV check workflow (`platform-gitops/.github/workflows/kev-check.yaml`)
- Scan exclusions document (`platform-gitops/risk/scan-exclusions.md`)
- `security.txt` (`https://links-matrix.io/.well-known/security.txt`)
- CVD Policy (Confluence: LM-SECURITY / CVD / CVD-Policy-v1.0.pdf)
- CVD log (`platform-gitops/security/cvd-log.md`)
- Vulnerability trend report (Confluence: LM-SECURITY / Vuln / Trend-2026-Q1.pdf)

---

## RA-7 — Risk Response

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

### Risk Response Framework

All identified risks (from RA-3 risk assessment and RA-5 vulnerability scans) receive
an explicit documented disposition. Leaving a finding without a disposition is not
permitted — the weekly vulnerability triage meeting (DevSecOps + Cloud Security + ISSO)
ensures every new finding is assigned a response within 5 business days of discovery.

**Response options and authority:**

| Response | Definition | Authority Level |
| -------- | ---------- | --------------- |
| Mitigate | Implement control to reduce likelihood or impact to acceptable level | Engineer-level (tracked in Jira) |
| Accept | Formally accept residual risk with documented rationale and compensating controls | ISSO (Low/Moderate), System Owner (High), CISO + AO (Critical) |
| Transfer | Shift risk to third party (insurance, contract) | System Owner + Legal |
| Avoid | Eliminate the system component or capability that introduces the risk | System Owner |

### Risk Acceptance Process

Risk acceptances require:
1. Written risk acceptance memo (template: `platform-gitops/risk/templates/risk-accept.md`)
2. Named compensating controls with evidence pointers
3. Signed by authority appropriate to risk level (table above)
4. Expiry date (maximum 1 year; Critical acceptances require CISO re-evaluation at 6 months)
5. Stored in `platform-gitops/risk/acceptances/` (version-controlled) and Confluence

**Current risk acceptances:**

| Accept ID | Risk | Compensating Controls | Accepted By | Expiry |
| --------- | ---- | --------------------- | ----------- | ------ |
| RA-ACCEPT-001 | RISK-005 — DDoS (AWS Shield Standard) | AWS Shield Standard, ALB rate limiting, CloudFront WAF | System Owner J. Rivera | 2027-03-01 |
| RA-ACCEPT-002 | IA-2(8) gap — Okta push not FIDO2 | Device-bound push, ISSO alert on new enrollment, upgrade roadmap | ISSO M. Chen | 2026-12-31 |

### POA&M

The POA&M is maintained in `platform-gitops/risk/poam.md` (git source, authoritative)
with a rendered view in Confluence (LM-SECURITY / POA&M). Each entry follows the
FedRAMP POA&M column schema: weakness, control, risk level, responsible party,
scheduled completion, delay rationale (if applicable), and milestone table.

The ISSO reviews the POA&M monthly. A GitHub Actions workflow (`poam-staleness-check.yaml`)
runs weekly and alerts the ISSO if any POA&M item has a scheduled completion date
within 14 days without a recent status update — preventing silent slippage.

**Current POA&M:**

| Item ID | Finding | Control | Risk Level | Owner | Target Date | Status |
| ------- | ------- | ------- | ---------- | ----- | ----------- | ------ |
| POAM-001 | mTLS service-to-service not deployed | IA-3(1) | Moderate | Platform Eng | 2026-12-31 | On track — Linkerd PoC complete |
| POAM-002 | IR-4(4) cross-incident correlation | IR-4(4) | Low | Cloud Security | 2026-12-31 | On track — OpenSearch rules drafted |
| POAM-003 | IA-4(4) userType attribute not in Okta | IA-4(4) | Low | ITOps | 2026-09-30 | On track |
| POAM-004 | Retroactive git history scan (truffleHog) | IA-5(7) | Moderate | DevSecOps | 2026-06-30 | On track — scan scheduled 2026-06-01 |

**POA&M trend (quarterly):**

| Quarter | Items Opened | Items Closed | Net Change | Overdue at EOQ |
| ------- | ------------ | ------------ | ---------- | -------------- |
| 2025-Q2 | 3 | 1 | +2 | 0 |
| 2025-Q3 | 2 | 3 | -1 | 0 |
| 2025-Q4 | 1 | 2 | -1 | 0 |
| 2026-Q1 | 0 | 2 | -2 | 0 |

Total open items: 4. Overdue items: 0. Trend: net reduction in open POA&M items
for three consecutive quarters. The closure rate exceeds the opening rate — evidence
that the risk program is converging, not accumulating.

### Risk Register ↔ POA&M Traceability

Every open POAM item links back to a specific risk register entry (RA-3) and a specific
scan finding (RA-5). Auditors can follow the full chain:

```
RA-5 finding (Trivy/Inspector) → RA-3 risk register entry (RISK-XXX)
  → RA-7 response decision (mitigate/accept)
    → POA&M item (POAM-XXX) with milestone and target date
      → CA-7 continuous monitoring metric (monthly POAM status)
        → AO briefing (quarterly risk posture report)
```

**Responsible Role:** ISSO (POA&M owner, risk acceptance ≤ Moderate, monthly review), System Owner (High risk acceptance, AO briefing), CISO (Critical risk acceptance, co-sign), Cloud Security Engineer (weekly vuln triage, KEV escalation), DevSecOps (finding triage, closure evidence)

**Parameters:**
- Finding disposition SLA: 5 business days from discovery
- Risk acceptance maximum period: 1 year (Critical: 6-month re-evaluation)
- POA&M review cadence: Monthly (ISSO), quarterly (System Owner + AO briefing)
- POA&M staleness alert: 14 days before target date with no status update
- Response authority: tiered by risk level (table above)

**Evidence / Artifacts:**
- POA&M source (`platform-gitops/risk/poam.md` — current)
- POA&M Confluence view (LM-SECURITY / POA&M — rendered, updated on merge)
- Risk acceptances (`platform-gitops/risk/acceptances/` — RA-ACCEPT-001, RA-ACCEPT-002)
- POA&M staleness check workflow (`platform-gitops/.github/workflows/poam-staleness-check.yaml`)
- Quarterly risk posture report (Confluence: LM-SECURITY / Risk / Posture-2026-Q1.pdf)
- Weekly vuln triage meeting notes (Confluence: LM-SECURITY / Vuln / Triage-Notes)

---

## Test Procedures

### RA-3 Test Procedure

**Objective:** Verify the risk assessment is current, approved, and accurately reflects the deployed system.

**Step 1 — Confirm assessment currency:**
```bash
# Check git tag on current risk assessment
git -C platform-gitops log --oneline ra-v3.0 -1
# Expected: commit dated 2026-03 or later

# Verify risk register reflects current boundary components
grep -c "RISK-" platform-gitops/risk/risk-register.md
# Expected: count matches or exceeds number of threat scenarios in RA-LM-v3.0
```

**Step 2 — Verify MITRE ATT&CK coverage:**
```bash
# Confirm ATT&CK navigator export exists and is recent
git -C platform-gitops log --oneline risk/attack-navigator-lm.json -1
# Expected: updated within last 90 days (quarterly update cadence)
```

### RA-5 Test Procedure

**Objective:** Verify all boundary components are scanned and findings are tracked.

**Step 1 — Confirm scan scope completeness:**
```bash
# Get all running images in cluster
kubectl get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}' \
  | sort -u > /tmp/running-images.txt

# Compare against last Trivy weekly report
# (Manual: confirm every image in running-images.txt appears in the last Trivy CronJob output)
```

**Step 2 — Verify KEV workflow ran today:**
```bash
gh run list --workflow=kev-check.yaml --repo platform-gitops \
  --limit 1 --json conclusion,createdAt
# Expected: conclusion: "success", createdAt: today
```

**Step 3 — Verify SBOM exists for all running images:**
```bash
ls platform-gitops/sbom/ | wc -l
# Expected: count >= number of unique images in running-images.txt
```

**Step 4 — Verify security.txt is accessible:**
```bash
curl -s https://links-matrix.io/.well-known/security.txt | grep "Contact:"
# Expected: Contact: mailto:security@links-matrix.io
```

### RA-7 Test Procedure

**Objective:** Verify all open findings have a documented disposition and POA&M items are current.

```bash
# Confirm no POA&M items are overdue
python3 platform-gitops/risk/tools/poam-check.py --check-overdue
# Expected: 0 overdue items

# Verify most recent weekly vuln triage occurred on schedule
gh run list --workflow=poam-staleness-check.yaml --repo platform-gitops \
  --limit 1 --json conclusion,createdAt
# Expected: conclusion: "success", createdAt: within last 7 days

# Confirm risk acceptance expiry dates are not past
grep "Expiry:" platform-gitops/risk/acceptances/*.md | grep -v "20[2-9][7-9]"
# Expected: no entries (all expiries are in the future)
```

**Pass criteria:** Risk assessment git tag post-dates last significant boundary change,
all running images appear in SBOM, KEV workflow passing daily, no overdue POA&M items,
no expired risk acceptances.

---

## What Makes This GREAT — Examiner's Notes

| Control | What Elevates It |
| ------- | ---------------- |
| RA-3 | Risk register is version-controlled in git with MITRE ATT&CK technique IDs — every risk maps to a named threat event, not a category. Significant-change triggers are automated (same ssp-freshness-check as PL-2) — the DR cluster addition would have been detected in hours, not 5 months. |
| RA-3 | Annual review history table with 3 years of assessment dates, approvers, and what changed — auditors can see the assessment program is sustained, not just initiated. |
| RA-5 | Coverage map table — every boundary component class has a named tool, cadence, authentication method, and output destination. No ambiguity about what is and isn't scanned. |
| RA-5 | CISA KEV override with daily automated check and 48-hour SLA — known-exploited vulnerabilities get a hard-accelerated lane, not the standard queue. KEV match history shows two matches resolved within 48 hours. |
| RA-5 | Vulnerability trend table showing 4 quarters of Critical/High counts — the backlog is decreasing. Good SSPs say "we scan." Great SSPs prove the scanning is effective. |
| RA-5(11) | CVD policy + security.txt + researcher acknowledgment log — the full responsible disclosure stack. Good SSPs note the gap. Great SSPs close it and show the history of external reports received. |
| RA-7 | Full traceability chain: RA-5 finding → RA-3 risk register → RA-7 disposition → POA&M → CA-7 metric → AO briefing. Auditors can follow a single finding from discovery to closure without leaving the git repo. |
| RA-7 | POA&M trend showing zero overdue items across four quarters and a net-reducing backlog. The trend proves the risk response program produces results, not just documentation. |
