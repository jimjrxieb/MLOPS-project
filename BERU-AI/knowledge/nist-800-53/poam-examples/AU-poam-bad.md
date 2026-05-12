# POA&M — Audit and Accountability (AU) Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** POA&M items were written quickly after the assessment. Fields are incomplete,
> milestones are vague, validation commands are wrong, and scheduled completion dates ignore
> severity-based priority tiers.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** AU-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-006 | AU-2 — Event Logging | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-007 | AU-3 — Content of Audit Records | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-008 | AU-6 — Audit Record Review, Analysis, and Reporting | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-009 | AU-7 — Audit Record Reduction and Report Generation | High | P2 30 Days | 2026-12-31 |
| POAM-2026-05-010 | AU-9 — Protection of Audit Information | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-011 | AU-11 — Audit Record Retention | High | P2 30 Days | 2026-12-31 |
| POAM-2026-05-012 | AU-12 — Audit Record Generation | Critical | P1 Immediate | 2026-12-31 |

> **REVIEWER NOTE:** All due dates set to 2026-12-31 regardless of severity. Critical items
> should be due 2026-05-17. This is a bad POA&M quality indicator.

---

## POAM-2026-05-006 — AU-2

```text
POAM-ID:          POAM-2026-05-006
CONTROL:          AU-2 — Event Logging

WEAKNESS:
  Audit event logging is not set up properly.

SYSTEM AFFECTED:  AWS

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Set up CloudTrail

REMEDIATION APPROACH:
  Work with IT to fix CloudTrail logging.

VALIDATION COMMAND:
  Check CloudTrail settings

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-007 — AU-3

```text
POAM-ID:          POAM-2026-05-007
CONTROL:          AU-3 — Content of Audit Records

WEAKNESS:
  Audit records are not complete.

SYSTEM AFFECTED:  AWS

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Fix CloudTrail fields

REMEDIATION APPROACH:
  Make sure CloudTrail records have all the fields.

VALIDATION COMMAND:
  Look at CloudTrail logs

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-008 — AU-6

```text
POAM-ID:          POAM-2026-05-008
CONTROL:          AU-6 — Audit Record Review, Analysis, and Reporting

WEAKNESS:
  Audit log review is not happening.

SYSTEM AFFECTED:  all

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: SOC team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Set up Splunk

REMEDIATION APPROACH:
  Set up Splunk and start reviewing logs.

VALIDATION COMMAND:
  Check Splunk for alerts

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-009 — AU-7

```text
POAM-ID:          POAM-2026-05-009
CONTROL:          AU-7 — Audit Record Reduction and Report Generation

WEAKNESS:
  Reports are not being generated.

SYSTEM AFFECTED:  all

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: SOC team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Configure Splunk reports

REMEDIATION APPROACH:
  Set up scheduled reports in Splunk.

VALIDATION COMMAND:
  Check Splunk reports

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-010 — AU-9

```text
POAM-ID:          POAM-2026-05-010
CONTROL:          AU-9 — Protection of Audit Information

WEAKNESS:
  Audit logs are not protected.

SYSTEM AFFECTED:  all

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Deploy Falco

REMEDIATION APPROACH:
  Deploy Falco and enable S3 Object Lock.

VALIDATION COMMAND:
  Check Falco status

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-011 — AU-11

```text
POAM-ID:          POAM-2026-05-011
CONTROL:          AU-11 — Audit Record Retention

WEAKNESS:
  Audit record retention is not documented.

SYSTEM AFFECTED:  AWS

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Configure S3 retention

REMEDIATION APPROACH:
  Set up S3 lifecycle policy for log retention.

VALIDATION COMMAND:
  Check S3 bucket settings

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-012 — AU-12

```text
POAM-ID:          POAM-2026-05-012
CONTROL:          AU-12 — Audit Record Generation

WEAKNESS:
  Audit record generation is not working.

SYSTEM AFFECTED:  all

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Deploy Falco

REMEDIATION APPROACH:
  Deploy Falco to generate audit records.

VALIDATION COMMAND:
  Check Falco logs

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```
