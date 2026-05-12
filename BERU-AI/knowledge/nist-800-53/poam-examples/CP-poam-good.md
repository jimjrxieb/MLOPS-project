# POA&M — Contingency Planning (CP) Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** POA&M items reflect specific evidence gaps from the BERU assessment.
> Control owners are identified by role. Due dates follow severity-based priority tiers.
> Milestones cover M1 and M2 with actionable steps. Validation commands are real tool queries.
> Residual risk is acknowledged but remains generic. Status history includes opening reason.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** CP-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-020 | CP-9 — System Backup | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-021 | CP-10 — System Recovery and Reconstitution | Critical | P1 Immediate | 2026-05-17 |

---

## POAM-2026-05-020 — CP-9

```text
POAM-ID:          POAM-2026-05-020
CONTROL:          CP-9 — System Backup

WEAKNESS:
  AWS Backup is not configured. Zero backup jobs exist. No last backup timestamp is available.
  No cross-region copy configuration is in place. No Terraform backup plan artifact was
  produced to verify SSP claims. PlatEng verbal statement was the only evidence available.

SYSTEM AFFECTED:  AWS Backup / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/CP-9?env=bad (aws-backup — status: insufficient) + PlatEng interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/CP-9-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Configure AWS Backup plan in Terraform (backup-plan.tf); deploy to AWS;
                  confirm at least one backup job is active and last_backup is non-null.
  M2: 2026-05-16  Configure cross-region copy rule to us-west-2; set 90-day retention;
                  export backup plan configuration to evidence path.

REMEDIATION APPROACH:
  Create the AWS Backup plan in terraform/backup/backup-plan.tf covering all critical data
  stores (RDS, S3, EFS). Apply the Terraform configuration and confirm the plan appears in
  the AWS Backup console. Run a manual backup job and verify the last_backup timestamp is
  populated. Add a cross-region copy rule targeting us-west-2 with 90-day retention. Export
  the backup plan JSON artifact and store it in the evidence path.

VALIDATION COMMAND:
  aws backup list-backup-plans --query 'BackupPlansList[*].BackupPlanName'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment
```

---

## POAM-2026-05-021 — CP-10

```text
POAM-ID:          POAM-2026-05-021
CONTROL:          CP-10 — System Recovery and Reconstitution

WEAKNESS:
  No recovery test has been conducted. RTO and RPO are unmeasured. No recovery test artifact
  or S3 report exists. A disaster recovery runbook location was unknown to the control owner.
  PlatEng verbal statement confirmed the test is planned but not yet executed.

SYSTEM AFFECTED:  AWS Backup / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/CP-10?env=bad (aws-backup — status: insufficient) + PlatEng interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/CP-10-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability) / ISSO (evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Locate or create disaster recovery runbook (v3) in Confluence; confirm
                  RTO and RPO targets are documented; store link in evidence path.
  M2: 2026-05-16  Conduct the annual recovery test using AWS Backup restore; document
                  actual RTO and RPO; store test artifact in S3 and evidence path.

REMEDIATION APPROACH:
  Locate the disaster recovery runbook in Confluence (search: "DR runbook v3"). If not found,
  create a new version documenting the recovery procedure, RTO target (47 minutes), and RPO
  target (4 hours). Schedule and conduct the annual recovery test using AWS Backup restore
  to a test environment. Record actual RTO and RPO achieved. Export the test artifact as a PDF
  and store at s3://links-matrix-audit/cp10-recovery-test-2026-05.pdf. Link from evidence path.

VALIDATION COMMAND:
  aws backup list-recovery-points-by-backup-vault --backup-vault-name links-matrix-vault --query 'RecoveryPoints | length(@)'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment
```
