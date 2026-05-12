# Risk Assessment Evidence — CA Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** Evidence collected for both Security Assessment and Authorization controls
> is incomplete and unverifiable. Control owners provided vague verbal assurances with no
> supporting artifacts. Tool queries returned null or error responses indicating assessment
> infrastructure is not deployed or not configured. Both findings are FAIL; both require
> POA&M items.

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

**Tool Query:** `GET /evidence/CA-2?env=bad` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "CA-2", "env": "bad", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "assessment_findings": null,
    "last_assessment_date": null,
    "error": "No code assessment results available"
  }
}
```

**Interview Response (Control Owner — CompO):**
> "We had an assessment. It was done by a third party. I don't have the specific
> report handy — I'd have to get it from the ISSO. Findings are tracked somewhere
> in JIRA."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | No assessment findings produced; assessor name not confirmed; POA&M linkage not demonstrated |
| Impact | High | Without an evidenced assessment, the entire authorization basis is unverifiable |
| **Residual Risk** | **Critical** | No evidence a qualifying assessment has occurred |

**Finding:** FAIL
**Evidence Gap:** No assessment report produced. Assessor not named. Assessment date not confirmed. POA&M linkage not demonstrated.

**BERU Finding:**
```
FINDING: CompO cannot produce the security assessment report, assessor name, or POA&M linkage for CA-2.
CONTROL: CA-2 — Control Assessments
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - CompO verbal statement (assessment described, no artifacts produced)
  - Semgrep query (assessment_findings null, last_assessment_date null)
EVIDENCE GAP: No assessment report, assessor not named, assessment date not confirmed, POA&M linkage not demonstrated
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: ISSO (accountability) / CompO (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: The security assessment cannot be evidenced. No report, no assessor name, and no POA&M linkage were produced. Without a verified assessment, the authorization basis is not supportable. This is a critical gap for any FedRAMP or NIST authorization.
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

**Tool Query:** `GET /evidence/CA-7?env=bad` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "CA-7", "env": "bad", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "ci_scan_runs_30d": 0,
    "monitoring_artifact": null,
    "error": "Semgrep CI gate not configured"
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "We monitor continuously. The team runs scans. I don't have the dashboard link
> right now and the monthly report to the AO — I'd have to pull that."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Semgrep CI gate not configured; 0 scans in 30 days; no AO report produced |
| Impact | High | Without continuous monitoring, vulnerabilities accumulate undetected and the AO cannot exercise oversight |
| **Residual Risk** | **Critical** | Continuous monitoring infrastructure is absent |

**Finding:** FAIL
**Evidence Gap:** Semgrep CI gate not configured. Zero scans in 30 days. No monitoring dashboard. No AO monthly report.

**BERU Finding:**
```
FINDING: Semgrep CI gate is not configured and no continuous monitoring artifacts were produced for CA-7.
CONTROL: CA-7 — Continuous Monitoring
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - ISSO verbal statement (monitoring described, no artifacts produced)
  - Semgrep query (CI gate not configured, 0 scans in 30 days, monitoring_artifact null)
EVIDENCE GAP: Semgrep CI gate not configured, 0 scans, no monitoring dashboard, no AO monthly report
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: ISSO (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Continuous monitoring is absent. The Semgrep CI gate is not configured, no scans have run in 30 days, and no monthly report to the Authorizing Official was produced. FedRAMP requires continuous monitoring; this finding will block authorization if not remediated.
```
