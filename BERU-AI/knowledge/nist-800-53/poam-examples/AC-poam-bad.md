# POA&M — Access Control (AC) Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** POA&M items were written quickly after the assessment. Fields are incomplete,
> milestones are vague, validation commands are wrong, and scheduled completion dates ignore
> severity-based priority tiers.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** AC-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-001 | AC-2 — Account Management | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-002 | AC-3 — Access Enforcement | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-003 | AC-5 — Separation of Duties | High | P2 30 Days | 2026-12-31 |
| POAM-2026-05-004 | AC-6 — Least Privilege | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-005 | AC-17 — Remote Access | Critical | P1 Immediate | 2026-12-31 |

> **REVIEWER NOTE:** All due dates set to 2026-12-31 regardless of severity. Critical items
> should be due 2026-05-17. This is a bad POA&M quality indicator.

---

## POAM-2026-05-001 — AC-2

```text
POAM-ID:          POAM-2026-05-001
CONTROL:          AC-2 — Account Management

WEAKNESS:
  Access management is not fully in place.

SYSTEM AFFECTED:  AWS

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Fix access reviews

REMEDIATION APPROACH:
  Work with IT to fix the access management process.

VALIDATION COMMAND:
  Check logs to verify

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-002 — AC-3

```text
POAM-ID:          POAM-2026-05-002
CONTROL:          AC-3 — Access Enforcement

WEAKNESS:
  RBAC is not verified.

SYSTEM AFFECTED:  Kubernetes

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: PlatEng team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Deploy RBAC scanning tool

REMEDIATION APPROACH:
  Work with PlatEng to set up RBAC enforcement.

VALIDATION COMMAND:
  Check Kubernetes settings

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-003 — AC-5

```text
POAM-ID:          POAM-2026-05-003
CONTROL:          AC-5 — Separation of Duties

WEAKNESS:
  Separation of duties is not fully documented.

SYSTEM AFFECTED:  all

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: ISSO

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Create SoD matrix

REMEDIATION APPROACH:
  Document separation of duties.

VALIDATION COMMAND:
  Review namespace access

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-004 — AC-6

```text
POAM-ID:          POAM-2026-05-004
CONTROL:          AC-6 — Least Privilege

WEAKNESS:
  Least privilege is not enforced.

SYSTEM AFFECTED:  AWS

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: Cloud team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Run IAM scan

REMEDIATION APPROACH:
  Run Prowler when it is set up.

VALIDATION COMMAND:
  Check IAM policies

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-005 — AC-17

```text
POAM-ID:          POAM-2026-05-005
CONTROL:          AC-17 — Remote Access

WEAKNESS:
  Remote access controls are not verified.

SYSTEM AFFECTED:  all

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: SecEng

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Review VPN configuration

REMEDIATION APPROACH:
  Review VPN and MFA settings.

VALIDATION COMMAND:
  Check VPN logs

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```
