# POA&M — Identification and Authentication (IA) Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** POA&M items were written quickly after the assessment. Fields are incomplete,
> milestones are vague, validation commands are wrong, and scheduled completion dates ignore
> severity-based priority tiers.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** IA-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-022 | IA-2 — Identification and Authentication (Organizational Users) | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-023 | IA-3 — Device Identification and Authentication | High | P2 30 Days | 2026-12-31 |
| POAM-2026-05-024 | IA-4 — Identifier Management | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-025 | IA-5 — Authenticator Management | Critical | P1 Immediate | 2026-12-31 |

> **REVIEWER NOTE:** All due dates set to 2026-12-31 regardless of severity. Critical items
> should be due 2026-05-17. This is a bad POA&M quality indicator.

---

## POAM-2026-05-022 — IA-2

```text
POAM-ID:          POAM-2026-05-022
CONTROL:          IA-2 — Identification and Authentication (Organizational Users)

WEAKNESS:
  MFA is not fully in place.

SYSTEM AFFECTED:  AWS

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Fix MFA settings

REMEDIATION APPROACH:
  Work with IT to fix the authentication process.

VALIDATION COMMAND:
  Check logs to verify

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-023 — IA-3

```text
POAM-ID:          POAM-2026-05-023
CONTROL:          IA-3 — Device Identification and Authentication

WEAKNESS:
  Device identity is not verified.

SYSTEM AFFECTED:  Kubernetes

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: PlatEng team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Set up workload identity scanning

REMEDIATION APPROACH:
  Work with PlatEng to configure mTLS and identity.

VALIDATION COMMAND:
  Check Kubernetes settings

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-024 — IA-4

```text
POAM-ID:          POAM-2026-05-024
CONTROL:          IA-4 — Identifier Management

WEAKNESS:
  Identifier management is not documented.

SYSTEM AFFECTED:  AWS

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Generate IAM credential report

REMEDIATION APPROACH:
  Run IAM report when IT is available.

VALIDATION COMMAND:
  Check IAM users

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-025 — IA-5

```text
POAM-ID:          POAM-2026-05-025
CONTROL:          IA-5 — Authenticator Management

WEAKNESS:
  Secret management is not fully in place.

SYSTEM AFFECTED:  all

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Set up secret scanning

REMEDIATION APPROACH:
  Add secret scanning to CI when ready.

VALIDATION COMMAND:
  Check repo for secrets

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```
