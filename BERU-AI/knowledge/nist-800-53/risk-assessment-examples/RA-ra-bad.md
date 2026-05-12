# Risk Assessment Evidence — RA Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** Evidence collected for all three Risk Assessment controls is incomplete
> and unverifiable. Control owners provided vague verbal assurances with no supporting artifacts.
> Tool queries returned null or error responses indicating risk assessment tooling is not
> deployed or not capturing required data. All three findings are FAIL; all require POA&M items.

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

**Tool Query:** `GET /evidence/RA-3?env=bad` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "RA-3", "env": "bad", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "security_hub_enabled": null,
    "risk_register_artifact": null,
    "last_assessment_date": null,
    "error": "Security Hub not enabled or not accessible"
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "We do risk assessments. The last one was... I'd have to check. Security Hub —
> I think it might be enabled. The risk register is somewhere in Confluence."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Security Hub status unknown; risk register not produced; assessment date not confirmed |
| Impact | High | Without a verified risk assessment, risks are unidentified and unmanaged |
| **Residual Risk** | **Critical** | Risk assessment posture entirely unverifiable |

**Finding:** FAIL
**Evidence Gap:** Security Hub status unknown. Risk register not produced. Last assessment date not confirmed. Approver not named. Next assessment date not confirmed.

**BERU Finding:**
```
FINDING: Security Hub status is unknown and no risk register or assessment date can be produced for RA-3.
CONTROL: RA-3 — Risk Assessment
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - ISSO verbal statement (assessment described, Security Hub uncertain, register location unknown)
  - Prowler query (security_hub_enabled null, risk_register null, last_assessment_date null)
EVIDENCE GAP: Security Hub status unknown, risk register not produced, assessment date not confirmed, approver not named
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: ISSO (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Risk assessment cannot be evidenced. Security Hub is not confirmed, the risk register cannot be located, and the annual assessment date is unknown. Enable Security Hub and produce the risk register before the next assessment.
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

**Tool Query:** `GET /evidence/RA-5?env=bad` — simulates: trivy

**Tool Evidence (API Response):**
```json
{
  "control": "RA-5", "env": "bad", "tool": "trivy",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "images_scanned": 0,
    "cve_critical": null,
    "cve_high": null,
    "scan_schedule": null,
    "error": "Trivy scan not run — no results"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "Trivy is on the roadmap. We check for CVEs manually sometimes. I don't have
> specific counts or a formal patch SLA."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Trivy not run; 0 images scanned; CVE count unknown; no patch SLA |
| Impact | Critical | Unknown CVE exposure in container images means vulnerabilities are undetected and unpatched |
| **Residual Risk** | **Critical** | Vulnerability posture is entirely unverifiable |

**Finding:** FAIL
**Evidence Gap:** Trivy not run. Zero images scanned. CVE counts unknown. No patch SLA. No SBOM. No S3 scan artifact.

**BERU Finding:**
```
FINDING: Trivy has not been run and no vulnerability scan results or patch SLA exist for RA-5.
CONTROL: RA-5 — Vulnerability Monitoring and Scanning
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - SecEng verbal statement (Trivy roadmap, manual checks, no SLA)
  - Trivy query (not run, 0 images scanned, CVE counts null, no results)
EVIDENCE GAP: Trivy not run, 0 images scanned, CVE counts unknown, no patch SLA, no SBOM, no S3 artifact
RISK:
  Likelihood: High
  Impact: Critical
  Residual Risk: Critical
CONTROL OWNER: SecEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Vulnerability scanning is absent. Trivy has not been configured and no CVE counts or patch SLA exist. Container images may have critical vulnerabilities that are completely unknown. Deploy Trivy immediately and establish the SLA framework.
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

**Tool Query:** `GET /evidence/RA-7?env=bad` — simulates: prowler

**Tool Evidence (API Response):**
```json
{
  "control": "RA-7", "env": "bad", "tool": "prowler",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "open_findings_count": null,
    "overdue_remediations": null,
    "risk_response_artifact": null,
    "error": "No risk response tracking data available"
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "We track findings in JIRA. I don't have the POA&M document handy. Risk response
> SLA — it's not formally defined. Overdue items — I'd have to check."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | No risk response tracking data; POA&M not produced; SLA not defined |
| Impact | High | Without POA&M tracking, findings accumulate without remediation accountability |
| **Residual Risk** | **Critical** | Risk response capability is entirely unverifiable |

**Finding:** FAIL
**Evidence Gap:** POA&M document not produced. Open finding count unknown. Overdue remediation count unknown. Risk response SLA not defined.

**BERU Finding:**
```
FINDING: No POA&M tracking data is available and risk response SLAs are not defined for RA-7.
CONTROL: RA-7 — Risk Response
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - ISSO verbal statement (JIRA tracking described, POA&M not available, SLA undefined)
  - Prowler query (no risk response tracking, open_findings null, overdue null, artifact null)
EVIDENCE GAP: POA&M document not produced, open finding count unknown, overdue remediation count unknown, risk response SLA not defined
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: ISSO (accountability) / CompO (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Risk response tracking cannot be evidenced. No POA&M document was produced and risk response SLAs are not defined. Without formal tracking, findings accumulate without remediation accountability. Create and maintain the POA&M and establish SLAs before the next assessment.
```
