# Risk Assessment Evidence — CA Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** Evidence collected is partially sufficient. Control owners named specific
> tools and processes but could not produce exact artifacts, dates, or complete metrics. Tool
> queries returned partial data — some booleans confirmed but key counts and timestamps absent.
> Both controls receive PARTIAL findings requiring POA&M items to close the evidence gaps
> before the next audit cycle.

**Assessment Date:** 2026-05-10
**Assessor:** GRC Engineer (grc-engineer group — read-only)
**Framework:** NIST 800-53 Rev 5
**Graded Against:** Links-Matrix SSP (see ssp-examples/CA-ssp-great.md)

---

## CA-2 — Control Assessments

**Control Owner:** ISSO
**Evidence Producer:** CompO
**Cadence:** Annual (FedRAMP); event-triggered

### SSP Claim
> The SSP asserts that annual security assessments are conducted by a qualified third-party
> assessor (3PAO). All findings are linked to POA&M items with remediation timelines.
> The most recent assessment was conducted in 2026 by Coalfire under contract 2026-001.
> Assessment scope covers all 323 FedRAMP Moderate controls.

### Evidence Request

**Interview — Questions asked of control owner (CompO):**
1. Show me the last assessment scope, assessor, and findings.
2. Show me how findings link to POA&M items.

**Tool Query:** `GET /evidence/CA-2?env=good` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "CA-2", "env": "good", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "partial",
  "data": {
    "assessment_findings": 23,
    "last_assessment_date": "2025",
    "remediated": null,
    "note": "Findings exist but remediation tracking not linked"
  }
}
```

**Interview Response (Control Owner — CompO):**
> "We had an assessment in 2025 — a third party did it. There were 23 findings. Some
> are in JIRA but I don't have the specific ticket mapping. The assessor was a 3PAO
> — I believe Coalfire but I'd have to confirm. The report is in SharePoint somewhere."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — 23 findings confirmed; assessor name unconfirmed; assessment date imprecise; POA&M linkage not produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Assessment occurred and findings were produced; assessor name unconfirmed; precise date and POA&M linkage missing |
| Impact | Medium | Finding count known but remediation status and tracking are unverifiable without artifact |
| **Residual Risk** | **High** | Assessment partially evidenced; POA&M linkage gap means remediation accountability cannot be confirmed |

**Finding:** PARTIAL
**Evidence Gap:** Assessor name unconfirmed. Assessment date imprecise. Assessment report not produced. POA&M linkage for 23 findings not demonstrated.

**BERU Finding:**
```
FINDING: CompO confirmed 23 assessment findings exist for CA-2 but assessor name, precise date, report artifact, and POA&M linkage were not produced.
CONTROL: CA-2 — Control Assessments
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - CompO verbal statement (finding count described, assessor name uncertain, report location unknown)
  - Semgrep query (23 findings, 2025 date, remediation tracking null)
EVIDENCE GAP: Assessor name unconfirmed, assessment date imprecise, report not produced, POA&M linkage for all 23 findings not demonstrated
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: ISSO (accountability) / CompO (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: A security assessment occurred and findings were generated, but the evidence package is incomplete. Produce the assessment report, confirm the 3PAO name, and demonstrate POA&M linkage for all 23 findings to close this gap.
```

---

## CA-7 — Continuous Monitoring

**Control Owner:** ISSO
**Evidence Producer:** ISSO / SecEng
**Cadence:** Continuous; monthly report to AO

### SSP Claim
> The SSP asserts that continuous monitoring is implemented via Semgrep CI scans running
> on every code push. Monthly reports are provided to the Authorizing Official. Security
> posture is tracked across three dashboards: Security Hub, Semgrep Cloud, and Splunk
> gp_vulnerability.

### Evidence Request

**Interview — Questions asked of control owner (ISSO):**
1. Show me your continuous monitoring dashboard.
2. Show me the monthly report to the Authorizing Official.

**Tool Query:** `GET /evidence/CA-7?env=good` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "CA-7", "env": "good", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "partial",
  "data": {
    "ci_scan_runs_30d": 47,
    "monitoring_artifact": "CI results in GitHub Actions",
    "report_to_isso": false
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "Semgrep runs on every push — 47 scans in the last 30 days. Results are in GitHub
> Actions. The dashboard is in Security Hub. Monthly report to the AO — we do it
> but I don't have the last artifact handy. The Splunk gp_vulnerability dashboard
> exists but I'd need to send the link."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — Semgrep CI scans running; AO monthly report not produced; report not sent to ISSO per tool data; dashboard links not provided

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Semgrep scans running on push; AO reporting gap means oversight is unverifiable; dashboard links not confirmed |
| Impact | Medium | CI monitoring active but AO cannot exercise authorization oversight without monthly reports |
| **Residual Risk** | **High** | Continuous scanning confirmed but AO reporting and dashboard access not evidenced |

**Finding:** PARTIAL
**Evidence Gap:** AO monthly report not produced. Report not sent to ISSO per tool data. Dashboard links for Security Hub and Splunk gp_vulnerability not provided.

**BERU Finding:**
```
FINDING: Semgrep CI scans run 47 times in 30 days for CA-7 but the AO monthly report and dashboard links were not produced.
CONTROL: CA-7 — Continuous Monitoring
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - ISSO verbal statement (Semgrep CI described, AO report mentioned but not produced)
  - Semgrep query (47 CI scan runs, results in GitHub Actions, report_to_isso false)
EVIDENCE GAP: AO monthly report not produced, report not sent to ISSO confirmed by tool, dashboard links for Security Hub and Splunk not provided
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: ISSO (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Semgrep CI scanning is running but the continuous monitoring reporting loop is incomplete. Produce the AO monthly report, configure report distribution to the ISSO, and provide the dashboard links to close this finding.
```
