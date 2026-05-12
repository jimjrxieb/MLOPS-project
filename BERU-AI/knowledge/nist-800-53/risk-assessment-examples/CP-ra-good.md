# Risk Assessment Evidence — CP Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** Evidence collected is partially sufficient. Control owners named specific
> tools and processes but could not produce exact artifacts, dates, or complete metrics. Tool
> queries returned partial data — some booleans confirmed but key counts and timestamps absent.
> Both controls receive PARTIAL findings requiring POA&M items to close the evidence gaps
> before the next audit cycle.

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

**Tool Query:** `GET /evidence/CP-9?env=good` — simulates: aws-backup

**Tool Evidence (API Response):**
```json
{
  "control": "CP-9", "env": "good", "tool": "aws-backup",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "partial",
  "data": {
    "backup_jobs_configured": 3,
    "last_backup": "2026-05-08",
    "offsite_copy": false,
    "note": "Backups running but no cross-region copy configured"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "AWS Backup is configured with 3 jobs running. Last backup was 2026-05-08. Cross-region
> copy — that's not set up yet, it's on the backlog. Retention is 30 days, I think,
> but I'd need to confirm the exact policy. The Terraform backup plan exists but
> I don't have the path."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — 3 of 8 backup jobs running; no cross-region copy; retention period unconfirmed; Terraform artifact not produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Backups running but only 3 of 8 jobs; no cross-region copy means single-region failure risk exists |
| Impact | High | Without cross-region redundancy, a regional outage could result in data loss |
| **Residual Risk** | **High** | Partial backup coverage confirmed; cross-region and retention gaps must be closed |

**Finding:** PARTIAL
**Evidence Gap:** Only 3 of 8 claimed backup jobs configured. Cross-region copy not configured. Retention period unconfirmed. Terraform backup plan artifact not produced.

**BERU Finding:**
```
FINDING: 3 of 8 backup jobs are running for CP-9 but cross-region copy is absent and retention period is unconfirmed.
CONTROL: CP-9 — System Backup
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (3 jobs running, cross-region backlog, retention uncertain)
  - AWS Backup query (3 jobs configured, last backup 2026-05-08, offsite_copy false)
EVIDENCE GAP: Only 3 of 8 backup jobs configured, cross-region copy not configured, retention period unconfirmed, Terraform backup plan not produced
RISK:
  Likelihood: Medium
  Impact: High
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Backups are running but coverage is below the SSP claim and cross-region redundancy is absent. Configure all 8 backup jobs, enable cross-region copy to us-west-2, and confirm the 90-day retention policy to close this finding.
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

**Tool Query:** `GET /evidence/CP-10?env=good` — simulates: aws-backup

**Tool Evidence (API Response):**
```json
{
  "control": "CP-10", "env": "good", "tool": "aws-backup",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "partial",
  "data": {
    "recovery_test_last_date": "2025",
    "recovery_rto_minutes": null,
    "test_artifact": null,
    "note": "Recovery test conducted but no documented RTO/RPO outcome"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "We did a recovery test in 2025. It worked — we got things back up. I don't have
> the formal RTO metric documented though. The test artifact — it might be in someone's
> email. The runbook is in Confluence but I'd need to find the link."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — recovery test occurred in 2025; RTO/RPO not measured; no test artifact; runbook location not confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Recovery test conducted; RTO/RPO not measured; test artifact absent; test was in 2025 not 2026 |
| Impact | Medium | Recovery capability demonstrated informally; without RTO/RPO documentation, SLA cannot be confirmed |
| **Residual Risk** | **High** | Recovery test occurred but evidence package is too thin to satisfy an auditor |

**Finding:** PARTIAL
**Evidence Gap:** RTO/RPO not documented. Test artifact not produced. Recovery test date imprecise. Disaster recovery runbook location not confirmed.

**BERU Finding:**
```
FINDING: A recovery test was conducted in 2025 for CP-10 but RTO/RPO were not measured and no test artifact or runbook location was produced.
CONTROL: CP-10 — System Recovery and Reconstitution
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (test occurred in 2025, RTO not measured, artifact in email)
  - AWS Backup query (test date 2025, rto null, test_artifact null)
EVIDENCE GAP: RTO/RPO not documented, test artifact not produced, recovery test date imprecise, DR runbook location not confirmed
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability) / ISSO (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: A recovery test occurred but the evidence is insufficient for audit. Document the RTO/RPO outcome, produce the test artifact, and confirm the disaster recovery runbook location to close this finding.
```
