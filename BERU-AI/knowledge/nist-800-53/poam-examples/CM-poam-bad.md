# POA&M — Configuration Management (CM) Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** POA&M items were written quickly after the assessment. Fields are incomplete,
> milestones are vague, validation commands are wrong, and scheduled completion dates ignore
> severity-based priority tiers.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** CM-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-015 | CM-2 — Baseline Configuration | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-016 | CM-3 — Configuration Change Control | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-017 | CM-6 — Configuration Settings | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-018 | CM-7 — Least Functionality | High | P2 30 Days | 2026-12-31 |
| POAM-2026-05-019 | CM-8 — System Component Inventory | High | P2 30 Days | 2026-12-31 |

> **REVIEWER NOTE:** All due dates set to 2026-12-31 regardless of severity. Critical items
> should be due 2026-05-17. This is a bad POA&M quality indicator.

---

## POAM-2026-05-015 — CM-2

```text
POAM-ID:          POAM-2026-05-015
CONTROL:          CM-2 — Baseline Configuration

WEAKNESS:
  Baseline configuration is not documented.

SYSTEM AFFECTED:  Kubernetes

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Document baseline configuration

REMEDIATION APPROACH:
  Work with IT to document the baseline configuration.

VALIDATION COMMAND:
  Check cluster settings

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-016 — CM-3

```text
POAM-ID:          POAM-2026-05-016
CONTROL:          CM-3 — Configuration Change Control

WEAKNESS:
  Change control process is not fully in place.

SYSTEM AFFECTED:  all

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: PlatEng team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Set up change control process

REMEDIATION APPROACH:
  Work with PlatEng to set up a change control process.

VALIDATION COMMAND:
  Check CI/CD pipeline

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-017 — CM-6

```text
POAM-ID:          POAM-2026-05-017
CONTROL:          CM-6 — Configuration Settings

WEAKNESS:
  Configuration settings are not verified.

SYSTEM AFFECTED:  Kubernetes

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: SecEng team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Run configuration scan

REMEDIATION APPROACH:
  Run a configuration scan when tools are available.

VALIDATION COMMAND:
  Check configuration settings

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-018 — CM-7

```text
POAM-ID:          POAM-2026-05-018
CONTROL:          CM-7 — Least Functionality

WEAKNESS:
  Least functionality is not enforced.

SYSTEM AFFECTED:  Kubernetes

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: PlatEng team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Disable unnecessary components

REMEDIATION APPROACH:
  Review and disable unnecessary components.

VALIDATION COMMAND:
  Check enabled components

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-019 — CM-8

```text
POAM-ID:          POAM-2026-05-019
CONTROL:          CM-8 — System Component Inventory

WEAKNESS:
  System inventory is not complete.

SYSTEM AFFECTED:  all

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Create system inventory

REMEDIATION APPROACH:
  Work with IT to create a system inventory.

VALIDATION COMMAND:
  Check inventory records

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```
