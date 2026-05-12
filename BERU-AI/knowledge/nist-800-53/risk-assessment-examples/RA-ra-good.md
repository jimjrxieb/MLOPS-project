# Risk Assessment Evidence — RA Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** Evidence collected is partially sufficient. Control owners named specific
> tools and processes but could not produce exact artifacts, dates, or complete metrics. Tool
> queries returned partial data — some booleans confirmed but key counts and timestamps absent.
> All three controls receive PARTIAL findings requiring POA&M items to close the evidence gaps
> before the next audit cycle.

**Assessment Date:** 2026-05-10
**Assessor:** GRC Engineer (grc-engineer group — read-only)
**Framework:** NIST 800-53 Rev 5
**Graded Against:** Links-Matrix SSP (see ssp-examples/RA-ssp-great.md)

---

## RA-3 — Risk Assessment

**Control Owner:** ISSO
**Evidence Producer:** ISSO
**Cadence:** Annual + significant change

### SSP Claim
> The SSP asserts that an annual risk assessment is conducted covering all 323 FedRAMP
> Moderate controls. Security Hub has three standards enabled: NIST-800-53-r5, CIS-AWS-1.4,
> and FSBP. The risk register (v3.2) is maintained in Confluence and reviewed 2026-04-01.
> The next assessment is scheduled for 2027-04-01.

### Evidence Request

**Interview — Questions asked of control owner (ISSO):**
1. Show me your risk register — last update date and approver.
2. Show me Security Hub standards enabled.

**Tool Query:** `GET /evidence/RA-3?env=good` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "RA-3", "env": "good", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "partial",
  "data": {
    "security_hub_enabled": true,
    "risk_register_artifact": "exists but not linked to SSP",
    "last_assessment_date": "2025 — specific date not available"
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "Security Hub is enabled. The risk register is in Confluence but I don't have
> the link handy. The last assessment was in 2025 — I'd need to look up the
> exact date. Security Hub standards — I know NIST-800-53 is on but the others
> I'd have to check."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — Security Hub enabled; risk register exists but not linked; assessment date imprecise; Security Hub standards partially confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Security Hub enabled; risk register exists; assessment date and standards not fully confirmed |
| Impact | Medium | Partial risk visibility; register currency unconfirmed; Security Hub standards coverage uncertain |
| **Residual Risk** | **High** | Risk assessment infrastructure present but evidence package insufficient |

**Finding:** PARTIAL
**Evidence Gap:** Risk register link not provided. Assessment date imprecise. Security Hub standards (CIS-AWS-1.4 and FSBP) not confirmed. Approver not named.

**BERU Finding:**
```
FINDING: Security Hub is enabled for RA-3 but the risk register link is not provided and the assessment date is imprecise.
CONTROL: RA-3 — Risk Assessment
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - ISSO verbal statement (Security Hub enabled, risk register in Confluence, date uncertain)
  - Prowler query (security_hub_enabled true, risk_register exists but not linked, date 2025 imprecise)
EVIDENCE GAP: Risk register link not provided, assessment date imprecise, CIS-AWS-1.4 and FSBP standards not confirmed, approver not named
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: ISSO (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Security Hub is running but the risk assessment evidence package is incomplete. Provide the Confluence risk register link, confirm all three Security Hub standards, and produce the 2025 assessment artifact with approver to close this finding.
```

---

## RA-5 — Vulnerability Monitoring and Scanning

**Control Owner:** SecEng
**Evidence Producer:** SecEng
**Cadence:** Continuous; monthly report

### SSP Claim
> The SSP asserts that Trivy scans all container images on every push and daily schedule.
> 47 images are scanned. The last scan on 2026-05-09 shows 0 critical CVEs and 2 high CVEs.
> Remediation SLAs are Critical: 7 days, High: 30 days, Medium: 90 days.
> SBOM is generated for all images. Scan results are in S3.

### Evidence Request

**Interview — Questions asked of control owner (SecEng):**
1. Show me your vulnerability scan results — critical/high CVE counts open.
2. Show me your patch SLA.

**Tool Query:** `GET /evidence/RA-5?env=good` — simulates: trivy

**Tool Evidence (API Response):**
```json
{
  "control": "RA-5", "env": "good", "tool": "trivy",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "partial",
  "data": {
    "images_scanned": 12,
    "cve_critical": 3,
    "cve_high": 17,
    "scan_schedule": "on push — not scheduled",
    "remediation_sla": null,
    "note": "Scan runs on push. 3 critical CVEs open with no SLA."
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "Trivy runs on push — 12 images scanned. There are 3 critical CVEs open and 17
> high. We haven't defined a formal patch SLA yet. SBOM — Trivy can generate it
> but I haven't confirmed it's configured. Daily schedule is on the backlog."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — Trivy running on push; 12 of 47 images scanned; 3 critical CVEs open (SSP claims 0); no patch SLA; no SBOM confirmation

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Trivy running but 3 critical CVEs open; no patch SLA means remediation timeline is undefined |
| Impact | High | 3 critical CVEs with no SLA means critical vulnerabilities may persist indefinitely |
| **Residual Risk** | **High** | Vulnerability scanning active but critical CVEs open and SLA absent |

**Finding:** PARTIAL
**Evidence Gap:** 3 critical CVEs open without SLA. Only 12 of 47 images scanned. Daily schedule not configured. SBOM not confirmed. S3 scan artifact not produced.

**BERU Finding:**
```
FINDING: Trivy scans 12 images on push for RA-5 but 3 critical CVEs are open without a patch SLA and 35 images are not scanned.
CONTROL: RA-5 — Vulnerability Monitoring and Scanning
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - SecEng verbal statement (Trivy running, critical CVEs open, SLA not defined)
  - Trivy query (12 images, 3 critical CVEs, 17 high, on-push only, no SLA)
EVIDENCE GAP: 3 critical CVEs without SLA, only 12 of 47 images scanned, daily schedule not configured, SBOM not confirmed, S3 artifact not produced
RISK:
  Likelihood: Medium
  Impact: High
  Residual Risk: High
CONTROL OWNER: SecEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Vulnerability scanning is running but below the SSP claim. 3 critical CVEs are open without a patch SLA. Define the SLA, expand scanning to all 47 images, and configure the daily schedule to close this finding.
```

---

## RA-7 — Risk Response

**Control Owner:** ISSO
**Evidence Producer:** ISSO / CompO
**Cadence:** Ongoing (POA&M tracking)

### SSP Claim
> The SSP asserts that open findings are tracked in the POA&M. 12 open findings exist with
> 0 overdue remediations and 0 critical open. Risk response SLAs are Critical: 14 days,
> High: 30 days, Medium: 90 days. The POA&M is maintained in GP-S3/3POA/POAM-2026-Q1.xlsx
> and signed by the ISSO 2026-04-05.

### Evidence Request

**Interview — Questions asked of control owner (ISSO):**
1. Show me your open POA&M items and overdue remediations.
2. Show me risk response SLAs.

**Tool Query:** `GET /evidence/RA-7?env=good` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "RA-7", "env": "good", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:10:00Z", "status": "partial",
  "data": {
    "open_findings_count": null,
    "overdue_remediations": null,
    "risk_response_artifact": "POA&M document exists — not current",
    "note": "Risk response process described verbally. Tracking artifact outdated."
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "We have a POA&M. It's in a spreadsheet but it hasn't been updated since Q4 2025.
> Open findings — I'd have to count them. Overdue items — there might be some.
> SLA — Critical 14 days, High 30 days is the target but it's not formally documented."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — POA&M exists; not current; open finding count unknown; overdue remediations unknown; SLA described verbally but not documented

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | POA&M exists but outdated; open finding count unknown; SLA not formally documented |
| Impact | Medium | Stale POA&M means remediation accountability is not current; overdue items may exist |
| **Residual Risk** | **High** | Risk response tracking exists but currency and SLA formalization gaps must close |

**Finding:** PARTIAL
**Evidence Gap:** POA&M not current — not updated since Q4 2025. Open finding count not confirmed. Overdue remediation count unknown. SLA not formally documented.

**BERU Finding:**
```
FINDING: POA&M exists for RA-7 but is not current (last updated Q4 2025) and open finding count and SLAs are not confirmed.
CONTROL: RA-7 — Risk Response
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - ISSO verbal statement (POA&M in spreadsheet, outdated, SLA described verbally)
  - Prowler query (risk_response_artifact exists but not current, open_findings null, overdue null)
EVIDENCE GAP: POA&M not current (Q4 2025), open finding count not confirmed, overdue remediations unknown, SLA not formally documented
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: ISSO (accountability) / CompO (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Risk response tracking exists but the POA&M is stale. Update the POA&M to Q1 2026, document the SLAs formally, and produce the ISSO-signed artifact to close this finding.
```
