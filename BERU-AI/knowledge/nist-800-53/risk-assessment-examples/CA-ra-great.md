# Risk Assessment Evidence — CA Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Evidence collected fully supports all SSP claims. Control owners provided
> exact artifacts, dates, version numbers, and metrics on first request. Tool queries returned
> complete structured data with no gaps. Every SSP claim is traceable to a specific artifact
> with a retrievable location. Both controls receive PASS findings. No POA&M items required.
> This is the evidence standard a 3PAO expects to walk in and find.

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

**Tool Query:** `GET /evidence/CA-2?env=great` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "CA-2", "env": "great", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "sufficient",
  "data": {
    "assessment_findings": 7,
    "last_assessment_date": "2026-04-01",
    "remediated_30d": 4,
    "open_findings": 7,
    "poam_linked": true,
    "assessor": "3PAO — Coalfire (contract 2026-001)"
  }
}
```

**Interview Response (Control Owner — CompO):**
> "Assessment was conducted by Coalfire — contract 2026-001 — completed 2026-04-01.
> Scope: all 323 FedRAMP Moderate controls. 7 findings were generated; all are linked
> to POA&M items in GP-S3/3POA/POAM-2026-Q1.xlsx — each row has an assessment finding ID,
> remediation owner, and target date. 4 of 7 have been remediated as of today;
> 3 remain open with accepted risk. Assessment report is at
> s3://links-matrix-audit/ca2-assessment-2026-04.pdf."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — Coalfire named as 3PAO; 7 findings confirmed; POA&M linkage demonstrated; assessment report in S3

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 3PAO assessment completed; 7 findings with POA&M linkage; 4 remediated; 3 open with accepted risk |
| Impact | Low | Assessment scope covers all 323 controls; findings tracked and managed; report retrievable |
| **Residual Risk** | **Low** | All SSP claims verified by assessment artifacts and POA&M linkage |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: Coalfire 3PAO assessment completed 2026-04-01 with 7 findings all linked to POA&M items for CA-2. 4 remediated, 3 open with accepted risk.
CONTROL: CA-2 — Control Assessments
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - CompO interview (assessor name, contract, finding count, POA&M linkage, report location produced)
  - Semgrep query (7 findings, 2026-04-01 date, POA&M linked, Coalfire 3PAO confirmed)
  - Assessment report: s3://links-matrix-audit/ca2-assessment-2026-04.pdf
  - POA&M: GP-S3/3POA/POAM-2026-Q1.xlsx (finding ID, owner, target date for each finding)
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: ISSO (accountability) / CompO (evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Security assessment is fully evidenced. 3PAO Coalfire completed the assessment with 7 findings, all linked to POA&M items, 4 remediated, and the assessment report is retrievable. This control is audit-ready.
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

**Tool Query:** `GET /evidence/CA-7?env=great` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "CA-7", "env": "great", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "sufficient",
  "data": {
    "ci_scan_runs_30d": 183,
    "monitoring_artifact": "s3://links-matrix-audit/ca7-monthly-2026-04.pdf",
    "report_to_isso": true,
    "report_cadence": "monthly",
    "dashboards": ["Security Hub", "Semgrep Cloud", "Splunk gp_vulnerability"]
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "183 Semgrep CI scans in the last 30 days — runs on every push and PR. Monthly
> report to the AO is at s3://links-matrix-audit/ca7-monthly-2026-04.pdf — April
> report was delivered 2026-05-01. All three dashboards are live: Security Hub at
> aws.amazon.com/securityhub, Semgrep Cloud at semgrep.dev/links-matrix, and Splunk
> gp_vulnerability. I can provide access links for each."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 183 CI scans confirmed; monthly report in S3; AO report delivered; all three dashboards named and accessible

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 183 CI scans; monthly AO report delivered; three dashboards active; continuous posture visibility |
| Impact | Low | AO receives monthly reports; ISSO tracks posture across three integrated dashboards |
| **Residual Risk** | **Low** | All SSP claims verified by Semgrep data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 183 Semgrep CI scans in 30 days; monthly AO report produced; all three dashboards confirmed for CA-7.
CONTROL: CA-7 — Continuous Monitoring
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - ISSO interview (CI scan count, AO report S3 path, three dashboard names and links produced)
  - Semgrep query (183 CI scan runs, monitoring artifact in S3, report_to_isso true, all three dashboards)
  - AO monthly report: s3://links-matrix-audit/ca7-monthly-2026-04.pdf (delivered 2026-05-01)
  - Dashboards: Security Hub, Semgrep Cloud (semgrep.dev/links-matrix), Splunk gp_vulnerability
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: ISSO (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Continuous monitoring is fully implemented. 183 CI scans per month, monthly AO reports with S3 archival, and three active dashboards provide complete security posture visibility. This control is audit-ready.
```
