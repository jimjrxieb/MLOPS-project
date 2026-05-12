# POA&M — System and Information Integrity (SI) Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** POA&M items were written quickly after the assessment. Fields are incomplete,
> milestones are vague, validation commands are wrong, and scheduled completion dates ignore
> severity-based priority tiers.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** SI-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-037 | SI-2 — Flaw Remediation | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-038 | SI-3 — Malicious Code Protection | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-039 | SI-4 — System Monitoring | Critical | P1 Immediate | 2026-12-31 |
| POAM-2026-05-040 | SI-7 — Software, Firmware, and Information Integrity | Critical | P1 Immediate | 2026-12-31 |

> **REVIEWER NOTE:** All due dates set to 2026-12-31 regardless of severity. Critical items
> should be due 2026-05-17. This is a bad POA&M quality indicator.

---

## POAM-2026-05-037 — SI-2

```text
POAM-ID:          POAM-2026-05-037
CONTROL:          SI-2 — Flaw Remediation

WEAKNESS:
  Vulnerability scanning is not fully in place.

SYSTEM AFFECTED:  all

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: IT team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Set up vulnerability scanning tool

REMEDIATION APPROACH:
  Work with IT to fix the vulnerability management process.

VALIDATION COMMAND:
  Check scan logs to verify

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-038 — SI-3

```text
POAM-ID:          POAM-2026-05-038
CONTROL:          SI-3 — Malicious Code Protection

WEAKNESS:
  Malicious code protection is not configured.

SYSTEM AFFECTED:  CI/CD

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: DevOps team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Set up Semgrep scanning

REMEDIATION APPROACH:
  Work with DevOps to configure malicious code detection.

VALIDATION COMMAND:
  Check CI pipeline logs

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-039 — SI-4

```text
POAM-ID:          POAM-2026-05-039
CONTROL:          SI-4 — System Monitoring

WEAKNESS:
  System monitoring is not fully deployed.

SYSTEM AFFECTED:  Kubernetes

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: SOC team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Deploy monitoring tool

REMEDIATION APPROACH:
  Work with SOC to deploy a runtime monitoring solution.

VALIDATION COMMAND:
  Check cluster for monitoring pods

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```

---

## POAM-2026-05-040 — SI-7

```text
POAM-ID:          POAM-2026-05-040
CONTROL:          SI-7 — Software, Firmware, and Information Integrity

WEAKNESS:
  Software integrity checks are not in place.

SYSTEM AFFECTED:  all

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: Interview

EVIDENCE PATH:    N/A

REMEDIATION OWNER: DevOps team

SCHEDULED COMPLETION: 2026-12-31

MILESTONES:
  M1: 2026-12-01  Set up image signing

REMEDIATION APPROACH:
  Work with DevOps to set up image signing and integrity checks.

VALIDATION COMMAND:
  Check image signing status

RESIDUAL RISK AFTER REMEDIATION: N/A

STATUS HISTORY:
  2026-05-10 OPEN
```
