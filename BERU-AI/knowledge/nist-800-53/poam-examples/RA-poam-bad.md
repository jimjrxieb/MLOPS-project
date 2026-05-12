# POA&M — Risk Assessment (RA) Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** POA&M items were written quickly after the assessment. Fields are incomplete,
> milestones are vague, validation commands are wrong, and scheduled completion dates ignore
> severity-based priority tiers.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** RA-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-029 | RA-3 — Risk Assessment | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-030 | RA-5 — Vulnerability Monitoring and Scanning | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-031 | RA-7 — Risk Response | Critical | P1 Immediate | 2026-12-31 |

> **REVIEWER NOTE:** All due dates set to 2026-12-31 regardless of severity. Critical items
> should be due 2026-05-17. This is a bad POA&M quality indicator.

---

## POAM-2026-05-029 — RA-3

```text
POAM-ID:          POAM-2026-05-029
CONTROL:          RA-3 — Risk Assessment

WEAKNESS:
  Risk assessment is not fully in place.

SYSTEM AFFECTED:  AWS

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Enable Security Hub

REMEDIATION APPROACH:
  Work with IT to fix the risk assessment process.

VALIDATION COMMAND:
  Check Security Hub settings

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-030 — RA-5

```text
POAM-ID:          POAM-2026-05-030
CONTROL:          RA-5 — Vulnerability Monitoring and Scanning

WEAKNESS:
  Vulnerability scanning is not configured.

SYSTEM AFFECTED:  Containers

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: SecEng team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Deploy Trivy

REMEDIATION APPROACH:
  Work with SecEng to set up Trivy scanning.

VALIDATION COMMAND:
  Check container scan results

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-031 — RA-7

```text
POAM-ID:          POAM-2026-05-031
CONTROL:          RA-7 — Risk Response

WEAKNESS:
  Risk response tracking is not in place.

SYSTEM AFFECTED:  all

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: ISSO

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Create POA&M document

REMEDIATION APPROACH:
  Document risk response SLAs and produce a POA&M.

VALIDATION COMMAND:
  Check JIRA for open findings

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```
