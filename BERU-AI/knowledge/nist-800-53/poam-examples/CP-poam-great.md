# POA&M — Contingency Planning (CP) Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Auditor-ready POA&M. All deficiencies are numbered within each weakness.
> Remediation owners are split between evidence producer and sign-off authority. Due dates
> follow severity-based priority tiers. Milestones include M1, M2, and M3 with exact dated
> actions. Validation commands include expected output. Residual risk identifies the specific
> remaining gap after remediation. Status history shows full progression from OPEN to CLOSED.

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
  Five deficiencies identified on Links-Matrix (AWS Backup):
  (1) AWS Backup not configured — backup_jobs_configured: 0; no active backup plan exists
      in the AWS account; the SSP-asserted plan in terraform/backup/backup-plan.tf was not
      deployed.
  (2) No last backup timestamp — last_backup: null; no evidence any data store has ever
      been backed up via AWS Backup.
  (3) No cross-region copy configuration — us-west-2 copy rule asserted in SSP does not
      exist; cross-region redundancy is entirely unverified.
  (4) No Terraform backup plan artifact produced — PlatEng verbal statement only; no
      terraform show output or plan JSON was provided.
  (5) No quarterly restore test record — SSP asserts quarterly tests; no test artifact,
      date, or RTO/RPO outcome was produced for any quarter.

SYSTEM AFFECTED:  Links-Matrix (AWS Backup, RDS, S3, EFS)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/CP-9?env=bad → tool: aws-backup, status: insufficient,
                  backup_jobs_configured: 0, last_backup: null,
                  error: "AWS Backup not configured".
                  PlatEng interview: no backup plan, no cross-region config, no restore test
                  artifact produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/CP-9-2026-05-10/CP-9-finding.json

REMEDIATION OWNER: PlatEng (backup plan deployment and evidence producer) / ISSO (quarterly restore test sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Create terraform/backup/backup-plan.tf covering all critical data stores
                  (RDS, S3, EFS); apply via terraform apply; confirm backup plan appears in
                  AWS Backup console; export plan JSON artifact to evidence path.
  M2: 2026-05-14  Add cross-region copy rule to us-west-2 with 90-day retention; trigger
                  a manual backup job; confirm last_backup is non-null within 30 minutes;
                  export copy rule configuration to evidence path.
  M3: 2026-05-16  Run the quarterly restore test by restoring the most recent RDS snapshot
                  to a test instance; document RTO achieved; ISSO signs the test artifact;
                  store at s3://links-matrix-audit/cp9-restore-test-2026-05.pdf.

REMEDIATION APPROACH:
  Step 1: Create terraform/backup/backup-plan.tf with an aws_backup_plan resource targeting
  the links-matrix-vault. Include rules covering daily backup of all critical resources:
  aws_db_instance (RDS), aws_s3_bucket (application data), and aws_efs_file_system. Set
  start_window to 60 minutes and completion_window to 120 minutes. Run terraform plan to
  review, then terraform apply to deploy. Verify in the AWS Backup console that the plan
  appears and all 8 jobs are listed as COMPLETED within the first backup window.
  Step 2: Add a copy_action block to the backup rule specifying destination_vault_arn in
  us-west-2. Set lifecycle delete_after_days to 90. Apply the Terraform change and confirm
  the copy rule is visible in the AWS Backup console. Manually trigger a backup job via:
  aws backup start-backup-job --backup-vault-name links-matrix-vault \
    --resource-arn <rds-arn> --iam-role-arn <role-arn>
  Wait for completion and confirm last_backup is populated.
  Step 3: Initiate a restore test from the most recent recovery point in the
  links-matrix-vault to a test RDS instance. Record the time from restore initiation to
  database availability as the actual RTO. Compare against the SSP target (47 minutes).
  ISSO reviews and signs the test record. Upload the signed PDF to the evidence path and S3.

VALIDATION COMMAND:
  aws backup list-backup-plans --query 'BackupPlansList[*].BackupPlanName'
  Expected output: ["links-matrix-daily-backup"]

RESIDUAL RISK AFTER REMEDIATION:
  Cross-region backup copy replication lag is up to 15 minutes — a failure occurring within
  that window could result in up to 15 minutes of additional data loss beyond the RPO target.
  Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — AWS Backup not configured. backup_jobs_configured: 0. last_backup null.
             No cross-region copy rule. No Terraform artifact. No restore test record.
             PlatEng verbal only.
  2026-05-12 IN PROGRESS — M1 complete: backup-plan.tf created and applied. Backup plan
             links-matrix-daily-backup confirmed in AWS console. 8 jobs active.
             Plan JSON artifact exported to evidence path.
  2026-05-14 IN PROGRESS — M2 complete: Cross-region copy rule to us-west-2 deployed.
             Manual backup triggered — last_backup populated within 22 minutes.
             Copy rule configuration exported to evidence path.
  2026-05-16 IN PROGRESS — M3 complete: Restore test conducted — RDS snapshot restored to
             test instance in 41 minutes (within 47-minute RTO target). ISSO signed.
             Artifact stored at s3://links-matrix-audit/cp9-restore-test-2026-05.pdf.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/CP-9?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-021 — CP-10

```text
POAM-ID:          POAM-2026-05-021
CONTROL:          CP-10 — System Recovery and Reconstitution

WEAKNESS:
  Four deficiencies identified on Links-Matrix (AWS Backup / DR process):
  (1) No recovery test conducted — recovery_test_last_date: null; the SSP-asserted annual
      test (2026-03-15) was not performed; PlatEng confirmed the test is only planned.
  (2) RTO and RPO unmeasured — recovery_rto_minutes: null; no actual measurement exists;
      SSP-asserted targets (RTO 47 min, RPO 4h) are aspirational, not verified.
  (3) No recovery test artifact — S3 report path s3://links-matrix-audit/cp10-recovery-test-
      2026-03.pdf does not exist; no evidence of any past test.
  (4) Disaster recovery runbook location unknown — PlatEng stated "a recovery runbook exists
      somewhere"; no Confluence link or document version was produced.

SYSTEM AFFECTED:  Links-Matrix (AWS Backup, RDS, EFS, disaster recovery process)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/CP-10?env=bad → tool: aws-backup, status: insufficient,
                  recovery_test_last_date: null, recovery_rto_minutes: null,
                  error: "No recovery test records found".
                  PlatEng interview: no test conducted, RTO unmeasured, runbook location unknown.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/CP-10-2026-05-10/CP-10-finding.json

REMEDIATION OWNER: PlatEng (recovery test execution and runbook owner) / ISSO (evidence producer and sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Locate or create disaster recovery runbook (v3) in Confluence; confirm
                  it documents RTO target (47 min), RPO target (4h), recovery procedure
                  steps, and escalation contacts; ISSO reviews and links from evidence path.
  M2: 2026-05-14  Conduct the annual recovery test by restoring the RDS primary instance
                  from the most recent AWS Backup recovery point to a test environment;
                  record actual RTO and RPO from start to full application availability.
  M3: 2026-05-16  Produce the signed recovery test artifact (PDF) documenting start time,
                  RTO achieved, RPO achieved, outcome (PASS/FAIL), and corrective actions
                  if any; ISSO signs; store at s3://links-matrix-audit/cp10-recovery-test-
                  2026-05.pdf and link from evidence path.

REMEDIATION APPROACH:
  Step 1: Search Confluence for "DR runbook" or "disaster recovery v3". If found, confirm it
  includes: system inventory, recovery step sequence, RTO/RPO targets, responsible roles, and
  escalation contacts. If not found, create Confluence page CP-10-DR-Runbook-v3 from the
  GP-CONSULTING/templates/ DR template. Have PlatEng and ISSO review and approve.
  Step 2: Select the most recent recovery point in the links-matrix-vault:
  aws backup list-recovery-points-by-backup-vault --backup-vault-name links-matrix-vault \
    --query 'RecoveryPoints[0].RecoveryPointArn'
  Initiate a restore to a test RDS instance:
  aws backup start-restore-job --recovery-point-arn <arn> --metadata '{"DBInstanceIdentifier":"cp10-test"}' \
    --iam-role-arn <role-arn> --resource-type RDS
  Record the exact start time. Monitor until the test instance is in AVAILABLE state. Record
  elapsed time as actual RTO. Confirm data consistency using a row count query against a
  known table. Record RPO by checking the timestamp of the restored recovery point.
  Step 3: Produce the test report document (PDF) with fields: test date, start time, end time,
  actual RTO, actual RPO, SSP targets, outcome (PASS if RTO ≤ 47 min and RPO ≤ 4h), and
  corrective actions for any gap. ISSO signs the report. Upload to S3 and the evidence path.
  Terminate the test instance after completion to avoid ongoing cost.

VALIDATION COMMAND:
  aws backup list-recovery-points-by-backup-vault --backup-vault-name links-matrix-vault \
    --query 'RecoveryPoints | length(@)'
  Expected output: non-zero integer (e.g. 14)

RESIDUAL RISK AFTER REMEDIATION:
  Recovery test covers RDS primary only — EFS and S3 restore procedures are not tested in
  this cycle. A failure of the EFS or S3 restore path would be detected only during an actual
  incident. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — No recovery test conducted. recovery_test_last_date null. RTO/RPO
             unmeasured. No test artifact. DR runbook location unknown. PlatEng verbal only.
  2026-05-12 IN PROGRESS — M1 complete: DR runbook v3 located in Confluence (search:
             "disaster recovery runbook"). RTO target (47 min) and RPO target (4h) confirmed
             documented. ISSO reviewed and linked from evidence path.
  2026-05-14 IN PROGRESS — M2 complete: Recovery test conducted. RDS restore from
             links-matrix-vault completed in 44 minutes (within 47-min target). RPO: 3h 52m.
             Data consistency confirmed via row count match.
  2026-05-16 IN PROGRESS — M3 complete: Test artifact PDF produced. ISSO signed.
             Uploaded to s3://links-matrix-audit/cp10-recovery-test-2026-05.pdf.
             Linked from evidence path.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/CP-10?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```
