# Risk Assessment Evidence — RA Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Evidence collected fully supports all SSP claims. Control owners provided
> exact artifacts, dates, version numbers, and metrics on first request. Tool queries returned
> complete structured data with no gaps. Every SSP claim is traceable to a specific artifact
> with a retrievable location. All three controls receive PASS findings. No POA&M items
> required. This is the evidence standard a 3PAO expects to walk in and find.

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

**Tool Query:** `GET /evidence/RA-3?env=great` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "RA-3", "env": "great", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "sufficient",
  "data": {
    "security_hub_enabled": true,
    "security_hub_standards": ["NIST-800-53-r5", "CIS-AWS-1.4", "FSBP"],
    "risk_register_artifact": "Confluence: risk-register-v3.2 (reviewed 2026-04-01)",
    "last_assessment_date": "2026-04-01",
    "next_assessment_date": "2027-04-01",
    "assessment_scope": "All 323 FedRAMP Moderate controls"
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "Security Hub is enabled with all three standards: NIST-800-53-r5, CIS-AWS-1.4, and FSBP.
> Risk register v3.2 is at Confluence: risk-register-v3.2, reviewed 2026-04-01 by me
> (ISSO M.Chen) and the SO K.Patel. Assessment scope is all 323 FedRAMP Moderate controls.
> Next assessment is 2027-04-01. The risk register identifies 12 open risks with owners
> and remediation dates."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — Security Hub with all three standards; risk register v3.2 produced with review date; assessment dates confirmed; scope confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | All three Security Hub standards enabled; risk register current with ISSO + SO review |
| Impact | Low | Full 323-control scope; 12 risks with owners and remediation dates; next assessment scheduled |
| **Residual Risk** | **Low** | All SSP claims verified by Prowler data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: Security Hub with 3 standards, risk register v3.2 reviewed 2026-04-01, and 323-control scope confirmed for RA-3.
CONTROL: RA-3 — Risk Assessment
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - ISSO interview (Security Hub standards named, risk register location and review date, scope, next assessment date produced)
  - Prowler query (security_hub enabled, 3 standards confirmed, risk_register v3.2 reviewed 2026-04-01, scope 323 controls)
  - Risk register: Confluence: risk-register-v3.2 (reviewed 2026-04-01 by ISSO M.Chen + SO K.Patel)
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: ISSO (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Risk assessment is fully evidenced. Security Hub running all three standards, risk register current with management sign-off, and annual assessment cycle documented. This control is audit-ready.
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

**Tool Query:** `GET /evidence/RA-5?env=great` — simulates: trivy

**Tool Evidence (API Response):**
```json
{
  "control": "RA-5", "env": "great", "tool": "trivy",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "sufficient",
  "data": {
    "images_scanned": 47,
    "cve_critical": 0,
    "cve_high": 2,
    "scan_schedule": "push + daily scheduled",
    "last_scan": "2026-05-09T02:00:00Z",
    "remediation_sla": "Critical: 7d, High: 30d, Medium: 90d",
    "sbom_generated": true,
    "report_artifact": "s3://links-matrix-audit/trivy/2026-05-09-scan.json"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "47 images scanned on push and daily schedule. Last scan 2026-05-09T02:00:00Z —
> 0 critical CVEs, 2 high CVEs. Both high CVEs have remediation tickets in JIRA
> with 30-day SLA — both within SLA window. SLAs: Critical 7 days, High 30 days,
> Medium 90 days — documented in Confluence: vuln-sla-policy-v2.md. SBOM generated
> for all images. Scan report at s3://links-matrix-audit/trivy/2026-05-09-scan.json."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 47 images scanned; 0 critical CVEs; 2 high within SLA; daily schedule confirmed; SBOM generated; S3 artifact produced; SLA document named

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 47 images scanned on push + daily; 0 critical CVEs; 2 high within SLA; automated SBOM |
| Impact | Low | Complete image coverage; SLA documented and enforced; S3 artifact provides audit trail |
| **Residual Risk** | **Low** | All SSP claims verified by Trivy data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 47 images scanned with 0 critical CVEs; 2 high within SLA; SBOM generated; S3 artifact produced for RA-5.
CONTROL: RA-5 — Vulnerability Monitoring and Scanning
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - SecEng interview (image count, CVE counts, JIRA ticket status, SLA policy location, SBOM, S3 path produced)
  - Trivy query (47 images, 0 critical, 2 high, push+daily schedule, SBOM true, S3 artifact)
  - Scan artifact: s3://links-matrix-audit/trivy/2026-05-09-scan.json
  - SLA policy: Confluence: vuln-sla-policy-v2.md (Critical 7d, High 30d, Medium 90d)
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: SecEng (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Vulnerability monitoring is fully implemented. 47 images scanned, 0 critical CVEs, SLA documented and enforced, SBOM generated, and S3 audit artifact available. This control is audit-ready.
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

**Tool Query:** `GET /evidence/RA-7?env=great` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "RA-7", "env": "great", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:10:00Z", "status": "sufficient",
  "data": {
    "open_findings_count": 12,
    "overdue_remediations": 0,
    "critical_findings_open": 0,
    "poam_artifact": "GP-S3/3POA/POAM-2026-Q1.xlsx (ISSO signed 2026-04-05)",
    "avg_remediation_days_critical": 14,
    "avg_remediation_days_high": 30,
    "risk_response_sla": "Critical: 14d, High: 30d, Medium: 90d"
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "12 open findings, 0 overdue, 0 critical open. POA&M is at GP-S3/3POA/POAM-2026-Q1.xlsx
> — signed by me (ISSO M.Chen) on 2026-04-05. Risk response SLAs: Critical 14 days,
> High 30 days, Medium 90 days. Average remediation time for critical findings has been
> 14 days — we've been meeting the SLA. The POA&M updates weekly and feeds into the
> CISO monthly review."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 12 open findings; 0 overdue; 0 critical open; POA&M artifact with ISSO signature; SLA documented and being met

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 0 overdue remediations; 0 critical open; SLA being met; weekly POA&M updates |
| Impact | Low | POA&M signed by ISSO; feeding into CISO review; SLAs enforced with average meeting targets |
| **Residual Risk** | **Low** | All SSP claims verified by Prowler data and POA&M artifact |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 12 open findings with 0 overdue and 0 critical; POA&M ISSO-signed 2026-04-05; SLAs met for RA-7.
CONTROL: RA-7 — Risk Response
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - ISSO interview (finding count, overdue count, critical count, POA&M path, SLA metrics produced)
  - Prowler query (12 open, 0 overdue, 0 critical, POA&M signed 2026-04-05, SLA: 14/30/90 days)
  - POA&M: GP-S3/3POA/POAM-2026-Q1.xlsx (ISSO M.Chen signed 2026-04-05)
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: ISSO (accountability) / CompO (evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Risk response is fully evidenced. POA&M current with ISSO signature, 0 overdue remediations, 0 critical findings, and SLAs being met. This control is audit-ready.
```
