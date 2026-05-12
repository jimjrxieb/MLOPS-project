# POA&M — Contingency Planning (CP) Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** POA&M items were written quickly after the assessment. Fields are incomplete,
> milestones are vague, validation commands are wrong, and scheduled completion dates ignore
> severity-based priority tiers.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** CP-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-020 | CP-9 — System Backup | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-021 | CP-10 — System Recovery and Reconstitution | Critical | P1 Immediate | 2026-12-31 |

> **REVIEWER NOTE:** All due dates set to 2026-12-31 regardless of severity. Critical items
> should be due 2026-05-17. This is a bad POA&M quality indicator.

---

## POAM-2026-05-020 — CP-9

```text
POAM-ID:          POAM-2026-05-020
CONTROL:          CP-9 — System Backup

WEAKNESS:
  Backups are not configured properly.

SYSTEM AFFECTED:  AWS

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Set up backups

REMEDIATION APPROACH:
  Work with IT to configure backup jobs.

VALIDATION COMMAND:
  Check AWS console to verify

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-021 — CP-10

```text
POAM-ID:          POAM-2026-05-021
CONTROL:          CP-10 — System Recovery and Reconstitution

WEAKNESS:
  Recovery testing has not been done.

SYSTEM AFFECTED:  all

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: PlatEng team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Schedule recovery test

REMEDIATION APPROACH:
  Plan and conduct a recovery test when resources are available.

VALIDATION COMMAND:
  Check recovery logs

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```
