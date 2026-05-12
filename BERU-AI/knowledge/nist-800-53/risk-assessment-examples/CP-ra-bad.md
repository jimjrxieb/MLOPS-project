# Risk Assessment Evidence — CP Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** Evidence collected for both Contingency Planning controls is incomplete
> and unverifiable. Control owners provided vague verbal assurances with no supporting artifacts.
> Tool queries returned null or error responses indicating backup and recovery infrastructure
> is not configured. Both findings are FAIL; both require POA&M items.

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

**Tool Query:** `GET /evidence/CP-9?env=bad` — simulates: aws-backup

**Tool Evidence (API Response):**
```json
{
  "control": "CP-9", "env": "bad", "tool": "aws-backup",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "backup_jobs_configured": 0,
    "last_backup": null,
    "error": "AWS Backup not configured"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "We have backups. The data is somewhere. I'd need to check what AWS Backup has
> configured — it might be in a different account. Cross-region I'm not sure about."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | AWS Backup not configured; 0 backup jobs; last backup unknown; no cross-region evidence |
| Impact | Critical | Without verified backups, data loss from any incident cannot be recovered |
| **Residual Risk** | **Critical** | No evidence backups exist or are running |

**Finding:** FAIL
**Evidence Gap:** AWS Backup not configured. Zero backup jobs. No last backup timestamp. No cross-region copy evidence. No Terraform backup plan artifact.

**BERU Finding:**
```
FINDING: AWS Backup is not configured and no backup jobs are running for CP-9.
CONTROL: CP-9 — System Backup
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (backups described, no artifacts produced)
  - AWS Backup query (not configured, 0 backup jobs, last_backup null)
EVIDENCE GAP: AWS Backup not configured, 0 jobs, no last backup timestamp, no cross-region evidence, no Terraform artifact
RISK:
  Likelihood: High
  Impact: Critical
  Residual Risk: Critical
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: System backup cannot be evidenced. AWS Backup is not configured and no backup jobs are running. A data loss event would be unrecoverable. Configure AWS Backup immediately and produce the Terraform backup plan artifact before the next assessment.
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

**Tool Query:** `GET /evidence/CP-10?env=bad` — simulates: aws-backup

**Tool Evidence (API Response):**
```json
{
  "control": "CP-10", "env": "bad", "tool": "aws-backup",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "recovery_test_last_date": null,
    "recovery_rto_minutes": null,
    "error": "No recovery test records found"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "We haven't done a formal recovery test yet. It's on the plan for this year.
> RTO — I'm not sure what it actually is, we haven't measured it. There's
> a recovery runbook somewhere."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | No recovery test conducted; RTO/RPO not measured; test artifact absent; runbook location unknown |
| Impact | Critical | Without a verified recovery test, actual recovery capability is unknown; data loss and extended downtime possible |
| **Residual Risk** | **Critical** | Recovery capability entirely unverified |

**Finding:** FAIL
**Evidence Gap:** No recovery test conducted. No RTO/RPO measurements. No test artifact. No disaster recovery runbook produced.

**BERU Finding:**
```
FINDING: No recovery test has been conducted and RTO/RPO are unmeasured for CP-10.
CONTROL: CP-10 — System Recovery and Reconstitution
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (test planned, not conducted, runbook location unknown)
  - AWS Backup query (no recovery test records, recovery_test_last_date null, rto null)
EVIDENCE GAP: No recovery test, no RTO/RPO measurements, no test artifact, disaster recovery runbook not produced
RISK:
  Likelihood: High
  Impact: Critical
  Residual Risk: Critical
CONTROL OWNER: PlatEng (accountability) / ISSO (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: System recovery capability has never been tested. RTO and RPO are undefined. Without a verified recovery test, the organization cannot confirm it can recover from a disaster event. Conduct the annual recovery test and document the RTO/RPO outcome before the next assessment.
```
