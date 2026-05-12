# POA&M — System and Communications Protection (SC) Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** POA&M items were written quickly after the assessment. Fields are incomplete,
> milestones are vague, validation commands are wrong, and scheduled completion dates ignore
> severity-based priority tiers.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** SC-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-032 | SC-7 — Boundary Protection | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-033 | SC-8 — Transmission Confidentiality and Integrity | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-034 | SC-12 — Cryptographic Key Establishment and Management | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-035 | SC-13 — Cryptographic Protection | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-036 | SC-28 — Protection of Information at Rest | Critical | P1 Immediate | 2026-12-31 |

> **REVIEWER NOTE:** All due dates set to 2026-12-31 regardless of severity. Critical items
> should be due 2026-05-17. This is a bad POA&M quality indicator.

---

## POAM-2026-05-032 — SC-7

```text
POAM-ID:          POAM-2026-05-032
CONTROL:          SC-7 — Boundary Protection

WEAKNESS:
  Boundary protection controls are not fully in place.

SYSTEM AFFECTED:  AWS

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Fix boundary protection

REMEDIATION APPROACH:
  Work with the network team to fix boundary controls.

VALIDATION COMMAND:
  Check VPC settings

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-033 — SC-8

```text
POAM-ID:          POAM-2026-05-033
CONTROL:          SC-8 — Transmission Confidentiality and Integrity

WEAKNESS:
  TLS is not fully configured.

SYSTEM AFFECTED:  AWS

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: PlatEng team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Enable TLS on load balancers

REMEDIATION APPROACH:
  Work with PlatEng to configure TLS.

VALIDATION COMMAND:
  Check load balancer settings

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-034 — SC-12

```text
POAM-ID:          POAM-2026-05-034
CONTROL:          SC-12 — Cryptographic Key Establishment and Management

WEAKNESS:
  Key management is not configured.

SYSTEM AFFECTED:  AWS

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: Cloud team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Set up KMS

REMEDIATION APPROACH:
  Work with CloudSec to set up KMS key management.

VALIDATION COMMAND:
  Check KMS settings

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-035 — SC-13

```text
POAM-ID:          POAM-2026-05-035
CONTROL:          SC-13 — Cryptographic Protection

WEAKNESS:
  Cryptographic protection is not verified.

SYSTEM AFFECTED:  all

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: SecEng

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Review cipher settings

REMEDIATION APPROACH:
  Review and update cryptographic settings.

VALIDATION COMMAND:
  Check cipher configuration

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-036 — SC-28

```text
POAM-ID:          POAM-2026-05-036
CONTROL:          SC-28 — Protection of Information at Rest

WEAKNESS:
  Encryption at rest is not confirmed.

SYSTEM AFFECTED:  AWS

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: Cloud team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Enable encryption at rest

REMEDIATION APPROACH:
  Work with CloudSec to enable encryption on storage services.

VALIDATION COMMAND:
  Check S3 and RDS settings

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```
