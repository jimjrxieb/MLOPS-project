# Risk Assessment Evidence — CP Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Evidence collected fully supports all SSP claims. Control owners provided
> exact artifacts, dates, version numbers, and metrics on first request. Tool queries returned
> complete structured data with no gaps. Every SSP claim is traceable to a specific artifact
> with a retrievable location. Both controls receive PASS findings. No POA&M items required.
> This is the evidence standard a 3PAO expects to walk in and find.

**Assessment Date:** 2026-05-10
**Assessor:** GRC Engineer (grc-engineer group — read-only)
**Framework:** NIST 800-53 Rev 5
**Graded Against:** Links-Matrix SSP (see ssp-examples/CP-ssp-great.md)

---

## CP-9 — System Backup

**Control Owner:** PlatEng
**Evidence Producer:** PlatEng
**Cadence:** Continuous; quarterly restore test

### SSP Claim
> The SSP asserts that AWS Backup is configured with 8 backup jobs covering all critical
> data stores. Backups run nightly and are copied to us-west-2 for cross-region redundancy.
> Retention is 90 days. The backup plan is defined in terraform/backup/backup-plan.tf.
> Quarterly restore tests are conducted and documented.

### Evidence Request

**Interview — Questions asked of control owner (PlatEng):**
1. Show me your backup jobs and last successful backup.
2. Show me cross-region copy configuration.

**Tool Query:** `GET /evidence/CP-9?env=great` — simulates: aws-backup

**Tool Evidence (API Response):**
```json
{
  "control": "CP-9", "env": "great", "tool": "aws-backup",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "sufficient",
  "data": {
    "backup_jobs_configured": 8,
    "last_backup": "2026-05-09T02:00:00Z",
    "backup_success_rate_30d": "100%",
    "offsite_copy": true,
    "offsite_region": "us-west-2",
    "retention_days": 90,
    "backup_plan_artifact": "terraform/backup/backup-plan.tf"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "8 backup jobs configured covering RDS (2 instances), EBS (3 volumes), EFS (1),
> DynamoDB (1), and S3 Glacier archive (1). Last backup: 2026-05-09T02:00:00Z —
> 100% success rate for 30 days. Cross-region copy to us-west-2 is enabled — backup
> vault is links-matrix-backup-west. Retention is 90 days with lifecycle to Glacier
> after 30. Backup plan is in terraform/backup/backup-plan.tf on the main branch."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 8 jobs confirmed; last backup timestamped; 100% success rate; cross-region to us-west-2 confirmed; 90-day retention; Terraform artifact named

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 8 backup jobs; 100% success rate; cross-region redundancy; 90-day retention with Glacier archival |
| Impact | Low | Cross-region copy means a single-region failure cannot cause data loss; Terraform artifact auditable |
| **Residual Risk** | **Low** | All SSP claims verified by AWS Backup data and Terraform artifact |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 8 AWS Backup jobs confirmed with 100% success rate, cross-region us-west-2 copy, and 90-day retention for CP-9.
CONTROL: CP-9 — System Backup
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - PlatEng interview (job count by data store, last backup timestamp, cross-region vault name, Terraform path produced)
  - AWS Backup query (8 jobs, last backup 2026-05-09, 100% success rate, offsite us-west-2, 90-day retention)
  - Backup plan: terraform/backup/backup-plan.tf (main branch)
  - Cross-region vault: links-matrix-backup-west (us-west-2)
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: System backup is fully implemented and evidenced. 8 jobs, 100% success rate, cross-region redundancy, 90-day retention, and Terraform-managed configuration. This control is audit-ready.
```

---

## CP-10 — System Recovery and Reconstitution

**Control Owner:** PlatEng
**Evidence Producer:** PlatEng / ISSO
**Cadence:** Annual recovery test

### SSP Claim
> The SSP asserts that an annual disaster recovery test is conducted. The last test on
> 2026-03-15 achieved RTO of 47 minutes and RPO of 4 hours. The test artifact is at
> s3://links-matrix-audit/cp10-recovery-test-2026-03.pdf. A disaster recovery runbook
> (v3) is maintained in Confluence.

### Evidence Request

**Interview — Questions asked of control owner (PlatEng):**
1. Show me your last recovery test and documented RTO/RPO outcome.

**Tool Query:** `GET /evidence/CP-10?env=great` — simulates: aws-backup

**Tool Evidence (API Response):**
```json
{
  "control": "CP-10", "env": "great", "tool": "aws-backup",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "sufficient",
  "data": {
    "recovery_test_last_date": "2026-03-15",
    "recovery_rto_minutes": 47,
    "recovery_rpo_hours": 4,
    "test_artifact": "s3://links-matrix-audit/cp10-recovery-test-2026-03.pdf",
    "next_test_date": "2026-09-15",
    "runbook": "Confluence: disaster-recovery-runbook-v3.md"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "Annual recovery test was 2026-03-15. RTO: 47 minutes — measured from snapshot
> restore start to application health check passing. RPO: 4 hours — confirmed by
> last backup timestamp before simulated failure. Test artifact is at
> s3://links-matrix-audit/cp10-recovery-test-2026-03.pdf, signed by ISSO and PlatEng
> lead. Next test scheduled 2026-09-15. DR runbook is at Confluence:
> disaster-recovery-runbook-v3.md, last updated 2026-03-10."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 47-minute RTO confirmed; 4-hour RPO confirmed; test artifact in S3; next test scheduled; runbook named and versioned

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | Tested RTO of 47 min; RPO 4 hours; annual test scheduled; runbook current |
| Impact | Low | Recovery capability verified by actual test; next test scheduled; artifact provides audit chain-of-custody |
| **Residual Risk** | **Low** | All SSP claims verified by AWS Backup test data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: Recovery test 2026-03-15 confirms RTO 47 min and RPO 4 hours for CP-10. Test artifact in S3 and DR runbook produced.
CONTROL: CP-10 — System Recovery and Reconstitution
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - PlatEng interview (test date, RTO/RPO measurements, artifact path, next test date, runbook location produced)
  - AWS Backup query (recovery_test_last_date 2026-03-15, rto 47 min, rpo 4 hours, artifact in S3, next test 2026-09-15)
  - Test artifact: s3://links-matrix-audit/cp10-recovery-test-2026-03.pdf (ISSO + PlatEng signed)
  - DR runbook: Confluence: disaster-recovery-runbook-v3.md (updated 2026-03-10)
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: PlatEng (accountability) / ISSO (evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: System recovery capability is fully tested and evidenced. 47-minute RTO and 4-hour RPO confirmed by actual test with signed artifact, and the next test is scheduled. This control is audit-ready.
```
