# System Security Plan — Contingency Planning (CP) Family

## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** This SSP is auditor-ready. CP-9 and CP-10 are explicitly linked —
> CP-9 is validated only by the CP-10 exercise results. RTO/RPO targets are derived from
> a Business Impact Analysis. Backup failures alert immediately. Restore tests are
> quarterly. Post-recovery reconstitution includes an attacker-persistence checklist,
> a clean-state verification scan, and a formal ISSO sign-off before returning to
> production. An auditor can pull every artifact referenced here without asking a
> single clarifying question.

---

**System Name:** Links-Matrix Platform
**System Owner:** J. Rivera, Platform Engineering Lead (jrivera@links-matrix.io)
**ISSO:** M. Chen, Information System Security Officer (mchen@links-matrix.io)
**Prepared By:** M. Chen, ISSO
**Date:** 2026-05-01
**Review Date:** 2027-05-01 (annual) or upon significant system change
**Status:** Approved — ATO Granted 2026-03-15, expires 2029-03-15

**Control Relationship Note:** CP-9 and CP-10 are two halves of the same commitment.
CP-9 creates recovery capability. CP-10 proves that capability works within the
required timeframe and leaves the system in a verified secure state. A CP-9 backup
that has never been tested under CP-10 conditions is a hypothesis. The quarterly
restore test is the only evidence that either control is real.

---

## CP-9 — System Backup

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Moderate and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### RTO and RPO Basis

RTO and RPO targets were established through a Business Impact Analysis (`BIA-LM-2025`,
Confluence: LM-SECURITY / CP / BIA-LM-2025.pdf, approved by System Owner and ISSO,
2025-11-01). The BIA assessed maximum tolerable downtime per component by interviewing
stakeholders and analyzing revenue and compliance impact of outages. Backup schedules
and retention periods are designed to meet or exceed the derived RPO for each tier.

| Tier | Components | Max Tolerable Downtime | Derived RTO | Derived RPO |
| ---- | ---------- | ---------------------- | ----------- | ----------- |
| Tier 1 — Critical data | RDS PostgreSQL (`lm-prod-db`) | 4 hours | **2 hours** | **5 minutes** |
| Tier 2 — Application state | EKS workloads, K8s config (Velero) | 8 hours | **4 hours** | **6 hours** |
| Tier 3 — Object data | S3 `lm-data-*` buckets | 24 hours | **1 hour** | **Near-zero** |
| Tier 4 — Infrastructure | Terraform state, IaC | 24 hours | **8 hours** | **N/A** (stateless) |

### Backup Schedule and Configuration

All backup jobs are managed by AWS Backup (`lm-backup-plan`) and Velero (`lm-velero-schedule`).
AWS Backup configuration is defined in Terraform (`infra-iac/backup/main.tf`).
Velero schedule is defined in `platform-gitops/velero/backup-schedule.yaml`.

| Component | Backup Tool | Frequency | Retention (Primary) | Cross-Region Copy | Retention (DR) |
| --------- | ----------- | --------- | ------------------- | ----------------- | -------------- |
| RDS PostgreSQL `lm-prod-db` | AWS Backup + RDS PITR | Continuous PITR + daily snapshot | 35 days (PITR), 90 days (snapshot) | Yes — us-west-2 (automated) | 35 days |
| EBS volumes (EKS worker nodes) | AWS Backup | Daily 02:00 UTC | 30 days | Yes — us-west-2 | 14 days |
| S3 `lm-data-*` (application data) | S3 Cross-Region Replication | Continuous (object-level, <15 min SLA) | 7 years (Object Lock — Compliance) | Continuous to `lm-data-dr-*` us-west-2 | 7 years |
| K8s cluster state (Velero) | Velero + S3 `lm-backup-us-east-1` | Every 6 hours | 30 days | Daily copy to `lm-backup-us-west-2` | 30 days |
| etcd snapshots | etcd CronJob `etcd-backup` | Every 3 hours | 7 days | Every 6 hours to S3 us-west-2 | 7 days |
| Terraform state | S3 backend (`lm-tf-state`) with versioning | On every `terraform apply` | Indefinite (S3 versioning) | S3 CRR to us-west-2 | Indefinite |
| Application secrets (Secrets Manager) | AWS Backup | Daily | 30 days | Yes — us-west-2 | 30 days |

**Backup encryption:**
All AWS Backup jobs use the `lm-cmk-backup` KMS Customer Managed Key
(`arn:aws:kms:us-east-1:998877665544:key/mrk-abc123...`). The CMK is a multi-region
key with a replica in us-west-2 (`arn:aws:kms:us-west-2:998877665544:key/mrk-abc123...`)
to support DR restores. Key policy restricts decrypt access to the `lm-backup-restore`
IAM role and the ISSO — workload IAM roles cannot decrypt backup data directly.
Velero S3 buckets have S3-SSE-KMS encryption using the same CMK.

**Immutable backup copy:**
In addition to the standard backup schedule, a monthly immutable snapshot is taken of
the RDS database and written to S3 `lm-backup-immutable-us-west-2` with S3 Object Lock
in Compliance mode (1-year retention). This protects against ransomware that goes
undetected within the 35-day PITR window — there is always a clean copy no older than
31 days that cannot be overwritten or deleted.

### Backup Monitoring and Alerting

Backup job results are monitored automatically — manual console review is not the
primary detection mechanism.

| Alert Condition | Detection | Severity | Notification |
| --------------- | --------- | -------- | ------------ |
| AWS Backup job failure | EventBridge rule on `BACKUP_JOB_FAILED` | P2 | PagerDuty + ISSO email within 15 minutes |
| AWS Backup job not started (missed schedule) | EventBridge rule on `BACKUP_JOB_EXPIRED` | P2 | PagerDuty + Platform Engineer |
| Velero backup failure | Velero metrics `velero_backup_failure_total` > 0 via Prometheus alert | P2 | PagerDuty + Slack `#platform-alerts` |
| etcd backup CronJob failure | K8s CronJob failure event → Prometheus alert | P1 | PagerDuty + Platform Engineer on-call |
| S3 CRR replication lag >30 minutes | CloudWatch metric `ReplicationLatency` alarm | P2 | Slack `#platform-alerts` |
| Cross-region copy not received (24h) | Lambda daily check of us-west-2 backup vault job history | P2 | PagerDuty + ISSO |

All backup alerts route to PagerDuty service `lm-backup-integrity` (separate from the
general security service). Alerts are acknowledged within 1 hour and investigated before
the next scheduled backup window.

**Responsible Role:** Platform Engineer (Velero, etcd CronJob, backup monitoring), Cloud Security Engineer (AWS Backup, KMS CMK, S3 CRR, cross-region copy alerting)

**Parameters:**
- RDS PITR retention: **35 days**; snapshot retention: **90 days**
- Immutable monthly snapshot retention: **12 months** (S3 Object Lock Compliance)
- Velero backup interval: **Every 6 hours**; retention: **30 days**
- etcd snapshot interval: **Every 3 hours**; retention: **7 days**
- S3 CRR replication lag alert: **>30 minutes**
- Backup failure alert SLA: **15 minutes** to PagerDuty
- Backup CMK: `lm-cmk-backup` (multi-region, restricted to `lm-backup-restore` role + ISSO)

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| AWS Backup plan `lm-backup-plan` | `infra-iac/backup/main.tf` + AWS Console → Backup → Backup plans | 2026-04-15 |
| Velero backup schedule | `platform-gitops/velero/backup-schedule.yaml` | Per-commit |
| etcd CronJob manifest | `platform-gitops/etcd/etcd-backup-cronjob.yaml` | Per-commit |
| Backup CMK policy | `infra-iac/kms/backup-cmk.tf` | Per-commit |
| S3 CRR configuration for `lm-data-*` | `infra-iac/s3/data-buckets.tf` | Per-commit |
| S3 Object Lock config for `lm-backup-immutable-us-west-2` | `infra-iac/s3/immutable-backup.tf` + AWS CLI: `aws s3api get-object-lock-configuration` | 2026-04-15 |
| AWS Backup vault job history (last 90 days) | AWS Console → Backup → Backup vaults → `lm-backup-vault` | Continuous |
| Backup failure PagerDuty alert config | `infra-iac/monitoring/backup-alerts.tf` | Per-commit |
| BIA `BIA-LM-2025` | Confluence: LM-SECURITY / CP / BIA-LM-2025.pdf | 2025-11-01 |
| Quarterly restore test results | Confluence: LM-SECURITY / CP / Recovery Tests | Quarterly |

**Test Procedure:**
1. Pull AWS Backup vault job history for the last 30 days — verify no failed or expired
   backup jobs. If any exist, verify a corresponding PagerDuty ticket was created within
   15 minutes.
2. Pull Velero backup list: `velero backup get` — verify backups exist for each 6-hour
   window in the last 48 hours with `STATUS: Completed`.
3. Pull etcd backup objects from S3 us-west-2: `aws s3 ls s3://lm-backup-us-west-2/etcd/`
   — verify objects exist for each 6-hour window in the last 24 hours.
4. Verify S3 CRR for `lm-data-prod` is replicating: `aws s3api get-bucket-replication`
   — confirm destination bucket is `lm-data-dr-us-west-2` and rule is `Enabled`.
5. Verify immutable backup: `aws s3api get-object-lock-configuration --bucket lm-backup-immutable-us-west-2`
   — confirm `ObjectLockEnabled: Enabled`, `Mode: COMPLIANCE`, retention ≥365 days.
6. Verify backup CMK access restriction: As a non-authorized IAM role, attempt
   `aws kms decrypt` using `lm-cmk-backup` — verify `AccessDenied`.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| CP-9(1) Testing for Reliability and Integrity | Implemented | Quarterly restore tests (February, May, August, November) covering RDS PITR and Velero namespace restore. Each test produces a restore test report documenting actual restore time vs. RTO target, data integrity verification, and ISSO sign-off. See CP-10 for full test detail. |
| CP-9(3) Separate Storage for Critical Information | Implemented | All backups cross-region replicated to us-west-2. Primary workloads in us-east-1. A complete regional failure in us-east-1 does not affect backup availability. Cross-region copies monitored for delivery within 24 hours; missed delivery triggers P2 alert. Immutable monthly snapshot stored in us-west-2 with Object Lock Compliance — survives any compromise of the primary account. |
| CP-9(5) Transfer to Alternate Storage Site | Implemented | RDS and EBS cross-region copies run on the daily AWS Backup schedule. S3 CRR provides continuous object-level replication with <15-minute SLA. etcd snapshots copy to us-west-2 every 6 hours. Velero backups copy daily. All transfers are automated — no manual intervention required to maintain DR currency. |

---

## CP-10 — System Recovery and Reconstitution

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Moderate and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### RTO/RPO Targets (derived from BIA-LM-2025)

| Tier | Component | RTO Target | RPO Target | Last Tested RTO | Last Tested RPO | Test Date |
| ---- | --------- | ---------- | ---------- | --------------- | --------------- | --------- |
| 1 | RDS PostgreSQL | 2 hours | 5 minutes | 47 minutes ✅ | ~3 minutes ✅ | 2026-02-15 |
| 2 | EKS workloads (Velero) | 4 hours | 6 hours | 1 hr 24 min ✅ | ~4 hours ✅ | 2026-02-15 |
| 3 | S3 data (`lm-data-*`) | 1 hour | Near-zero | 18 minutes ✅ | <15 min ✅ | 2026-02-15 |
| 4 | Infrastructure (Terraform) | 8 hours | N/A | 3 hours 12 min ✅ | N/A | 2026-02-15 |

All four tiers met their RTO and RPO targets in the most recent annual exercise.
Quarterly restore tests cover Tier 1 and Tier 2 only (most critical); Tier 3 and 4
are tested annually. The next quarterly restore test (Tier 1 + 2) is scheduled for
2026-05-19.

### Recovery Runbook

The Links-Matrix Recovery Runbook (`platform-gitops/docs/recovery-runbook.md`,
currently at version `v1.4`, last updated 2026-02-16 after the annual exercise)
contains step-by-step recovery procedures for each tier. The runbook is maintained
in the `platform-gitops` repository so it is version-controlled and updated alongside
architecture changes. Any PR that modifies EKS cluster configuration, RDS configuration,
or Terraform VPC/IAM modules requires the ISSO to verify the runbook remains accurate
(enforced by CODEOWNERS — ISSO is a required reviewer for runbook file changes).

Runbook sections:
- `Section 1` — Pre-recovery assessment (determine scope, declare incident, notify ISSO)
- `Section 2` — Tier 1 recovery: RDS PITR step-by-step, connection string update procedure
- `Section 3` — Tier 2 recovery: Velero restore commands, ArgoCD sync sequence, health check verification
- `Section 4` — Tier 3 recovery: S3 replica promotion, DNS cutover procedure
- `Section 5` — Tier 4 recovery: Terraform apply sequence in us-west-2, dependency order
- `Section 6` — Post-recovery reconstitution checklist (see below)
- `Section 7` — Return-to-production authorization (ISSO sign-off required)

### Quarterly Restore Tests

Restore tests are conducted quarterly (February, May, August, November) using the
`lm-staging` environment as the restore target. Production data is not used in tests —
a Velero backup taken from `lm-prod` 24 hours before the test is restored into
`lm-staging`. The test environment matches production configuration exactly
(same EKS version, same K8s node type, same RDS instance class) to ensure timing
results are representative.

Each test produces a Restore Test Report (`CP-RESTORE-YYYY-QQ`) stored in Confluence
(LM-SECURITY / CP / Recovery Tests) and signed by the Platform Engineer (test executor)
and ISSO (independent verifier). The report includes:

- Test date, executor, and ISSO verifier
- Components restored and restore method used
- Actual restore time per component vs. RTO target (pass/fail)
- Actual recovery point achieved vs. RPO target (pass/fail)
- Issues encountered and resolution
- Post-recovery integrity verification results (see below)
- ISSO sign-off for return to production
- Action items for runbook updates

| Test | Date | Tier 1 RTO | Tier 2 RTO | Issues | Report |
| ---- | ---- | ---------- | ---------- | ------ | ------ |
| Q1 2026 (Annual) | 2026-02-15 | 47 min ✅ | 1h 24m ✅ | Velero restore of `lm-secrets` namespace required manual namespace pre-creation — runbook updated | `CP-RESTORE-2026-Q1` |
| Q4 2025 | 2025-11-17 | 52 min ✅ | 1h 31m ✅ | None | `CP-RESTORE-2025-Q4` |
| Q3 2025 | 2025-08-18 | 1h 03m ✅ | 1h 45m ✅ | RDS restore to new endpoint — app config update required extra 18 min; runbook updated | `CP-RESTORE-2025-Q3` |

### Post-Recovery Reconstitution Checklist

Before any recovered system component is returned to production, the following
reconstitution checklist (`platform-gitops/docs/reconstitution-checklist.md`)
must be completed and signed off by the ISSO. The checklist exists specifically
to prevent restoring attacker persistence along with legitimate data.

**Step 1 — Configuration integrity:**
- [ ] ArgoCD sync confirms all namespaces match `platform-gitops@main` baseline (no drift)
- [ ] `kubectl get clusterpolicies` confirms all Kyverno policies are active in Enforce mode
- [ ] `kubectl get daemonset falco -n falco` confirms Falco is running on all nodes
- [ ] kube-bench CIS Level 1 scan — 0 new failures vs. pre-incident baseline
- [ ] AWS Config compliance report — all 18 rules COMPLIANT

**Step 2 — Credential rotation (required after any compromise or suspected compromise):**
- [ ] All Kubernetes ServiceAccount tokens rotated (`kubectl delete secret <sa-token>`)
- [ ] AWS IAM role session tokens invalidated (update role trust policy to force re-assumption)
- [ ] Okta admin sessions invalidated and MFA re-enrolled for privileged accounts
- [ ] Database credentials rotated in Secrets Manager and application redeployed
- [ ] KMS key usage reviewed — if `lm-cmk-prod` was accessible to compromised principal, key rotation initiated

**Step 3 — Audit log review:**
- [ ] K8s audit logs from 30 days prior to incident reviewed for unauthorized access patterns
- [ ] CloudTrail logs reviewed for IAM role assumption, data access, and configuration changes
- [ ] No evidence of attacker persistence in K8s workloads (no unexpected containers, CronJobs, or RBAC bindings)
- [ ] Velero and AWS Backup audit logs confirm no unauthorized restore operations

**Step 4 — Security scan:**
- [ ] Trivy image scan on all restored container images — 0 Critical CVEs in deployed images
- [ ] Prowler AWS CIS scan — no new HIGH findings post-recovery
- [ ] IAM Access Analyzer — no external access findings post-recovery

**Step 5 — ISSO return-to-production authorization:**
- [ ] All checklist steps above completed with evidence
- [ ] ISSO signs the Restore Test Report or Incident Recovery Report
- [ ] System Owner notified of recovery completion and return to production

No recovered component enters production without ISSO sign-off on the reconstitution
checklist. This is enforced by procedure — the Platform Engineer does not flip production
DNS or remove staging routing until the signed report is in Confluence.

**Responsible Role:** Platform Engineer (recovery execution, reconstitution steps 1–4),
ISSO (checklist sign-off, return-to-production authorization, exercise oversight),
Cloud Security Engineer (AWS-layer recovery, Tier 4 Terraform apply)

**Parameters:**
- Quarterly restore test cadence: **February, May, August, November**
- Tier 1+2 quarterly; Tier 3+4 annual
- Recovery runbook version: **v1.4** (updated after Q1 2026 exercise)
- Return-to-production authorization: **ISSO sign-off required** (no exceptions)
- Credential rotation: **Required after any compromise or suspected compromise**

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| Recovery Runbook v1.4 | `platform-gitops/docs/recovery-runbook.md` | 2026-02-16 (post-Q1-exercise update) |
| Reconstitution Checklist | `platform-gitops/docs/reconstitution-checklist.md` | 2026-02-15 (used in Q1 exercise) |
| Quarterly restore test reports (last 4) | Confluence: LM-SECURITY / CP / Recovery Tests | Q1 2026: 2026-02-15 |
| BIA `BIA-LM-2025` (RTO/RPO basis) | Confluence: LM-SECURITY / CP / BIA-LM-2025.pdf | 2025-11-01 |
| Q1 2026 Restore Test Report `CP-RESTORE-2026-Q1` | Confluence: LM-SECURITY / CP / Recovery Tests / CP-RESTORE-2026-Q1.pdf | 2026-02-15 (signed) |
| Contingency Plan | Confluence: LM-SECURITY / CP / Contingency-Plan-v2.pdf | 2026-03-01 (last reviewed) |

**Test Procedure:**
1. Pull the most recent Restore Test Report from Confluence — verify it has both the
   Platform Engineer and ISSO signatures, and that actual RTO and RPO results are
   documented for each tested tier.
2. Verify the Recovery Runbook in `platform-gitops/docs/recovery-runbook.md` matches
   the current architecture — pull the git blame and verify the last modification
   date is within 90 days of the last architectural change.
3. Verify the reconstitution checklist was completed in the most recent exercise —
   pull `CP-RESTORE-2026-Q1` and confirm all checklist steps are checked with evidence
   references.
4. Verify the quarterly schedule is being maintained — confirm test reports exist for
   each of the last 4 scheduled quarters (Q1 2026, Q4 2025, Q3 2025, Q2 2025).
5. Verify RTO targets are BIA-derived: pull `BIA-LM-2025` and confirm the RTO/RPO
   values in the SSP match the BIA-derived maximum tolerable downtime figures.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| CP-10(2) Transaction Recovery | Implemented | RDS PostgreSQL PITR provides transaction-level recovery with a 5-minute RPO. The database engine writes continuous transaction logs to S3; any point within the retention window (35 days) can be selected as a restore target. Q1 2026 exercise confirmed actual RPO of ~3 minutes. Application-level transaction state (in-flight requests at time of failure) is handled by the EKS application's idempotency design — requests are retried by clients, not replayed from logs. |
| CP-10(4) Restore Within Time Period | Implemented | Quarterly restore tests validate RTO for all tiers. RTO targets are BIA-derived (documented in `BIA-LM-2025`). Q1 2026 results: Tier 1 (RDS) 47 min vs. 2-hour target ✅; Tier 2 (EKS) 1h 24m vs. 4-hour target ✅; Tier 3 (S3) 18 min vs. 1-hour target ✅; Tier 4 (Terraform infra) 3h 12m vs. 8-hour target ✅. All targets met. Next test: 2026-05-19 (Tier 1+2). |

---

## What Makes This GREAT — Side-by-Side

| Dimension | Bad | Good | Great |
| --------- | --- | ---- | ----- |
| **RTO/RPO basis** | Not defined | Values stated ("2 hours") | BIA document cited with derivation; max tolerable downtime per tier; stakeholder approval documented |
| **Backup schedule** | "Regular backups" | 6-row table with frequencies and retention | 7-row table adding Secrets Manager; immutable monthly snapshot with Object Lock Compliance for ransomware protection beyond PITR window |
| **Backup failure alerting** | Manual console review "weekly" | Manual weekly review | 6-condition alert table with separate PagerDuty service; 15-minute failure notification SLA; automated missed-schedule detection |
| **Restore test cadence** | "Periodically" | Annual | Quarterly (February/May/August/November); separate cadence for Tier 1+2 vs Tier 3+4; test history table with 3 prior results |
| **Post-recovery integrity** | Not mentioned | Bulleted list (4 items) | 5-step numbered checklist with 18 discrete checkboxes; credential rotation required after compromise; Trivy + Prowler + IAM Analyzer scans; ISSO sign-off required before return to production |
| **Attacker persistence** | Not mentioned | Not mentioned | Explicit audit log review for 30 days prior to incident; check for unauthorized containers/CronJobs/RBAC bindings; credential rotation procedure for every principal class |
| **Runbook currency** | "Procedures documented" | Annual review | Version-controlled in `platform-gitops`; CODEOWNERS requires ISSO review on any PR touching runbook; issue log from prior tests drives updates; runbook section map provided |
| **CP-9 ↔ CP-10 link** | None | Both reference each other | Explicit in SSP header: CP-9 validity is proven only by CP-10 test results; quarterly tests are the evidence that CP-9 is working |
