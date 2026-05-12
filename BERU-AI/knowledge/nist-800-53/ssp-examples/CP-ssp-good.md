# System Security Plan — Contingency Planning (CP) Family

## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** This SSP would pass a readiness review with 3-4 clarification items.
> Tools are named, RTO/RPO are defined, and restore tests are documented.
> Gaps: no backup job failure alerting, restore tests are annual not quarterly,
> post-recovery integrity verification is described but not proceduralized,
> and CP-10(2) transaction recovery is mentioned but not evidenced at the
> transaction level.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Final Draft — Pending ISSO Signature

---

## CP-9 — System Backup

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

The Links-Matrix Platform uses AWS Backup to manage centralized backup schedules
for all critical data components. Backups are cross-region replicated to us-west-2
as the alternate storage site. All backups are encrypted using the platform KMS CMK
(`lm-cmk-backup`, managed by the Cloud Security Engineer).

**Backup Schedule:**

| Component | Tool | Frequency | Retention | Cross-Region |
| --------- | ---- | --------- | --------- | ------------ |
| RDS PostgreSQL (`lm-prod-db`) | AWS Backup + RDS automated backups | Daily snapshot + continuous PITR | 35 days | Yes — us-west-2 |
| EBS volumes (EKS node groups) | AWS Backup | Daily snapshot | 14 days | Yes — us-west-2 |
| S3 `lm-data-*` buckets | S3 Cross-Region Replication | Continuous (object-level) | 7 years (Object Lock) | Yes — us-west-2 |
| K8s cluster state (Velero) | Velero + S3 | Daily (scheduled backup) | 30 days | Yes — `lm-backup-us-west-2` bucket |
| etcd snapshots | etcd snapshot CronJob | Every 6 hours | 7 days | Yes — S3 us-west-2 |
| Terraform state | S3 backend with versioning | On every `terraform apply` | Indefinite (S3 versioning) | Yes — S3 CRR to us-west-2 |

Backup job success and failure are logged in AWS Backup vault job history. The Platform
Engineer reviews the AWS Backup console weekly for any failed jobs.

**Restore Testing:**
Backup restoration is tested annually as part of the CP-10 annual recovery exercise.
The most recent restore test was conducted on 2026-02-15 covering RDS point-in-time
recovery and Velero K8s namespace restore. Both tests were successful with results
documented in the recovery test report (Confluence: LM-SECURITY / CP / Recovery Tests / 2026).

**Responsible Role:** Platform Engineer (backup schedules, Velero), Cloud Security Engineer (AWS Backup, KMS CMK, cross-region replication)

**Parameters:**
- RDS PITR retention: 35 days
- K8s Velero backup retention: 30 days
- etcd snapshot interval: 6 hours
- Cross-region backup location: us-west-2
- Backup encryption CMK: `lm-cmk-backup` (Cloud Security Engineer managed)
- Restore test cadence: Annual (February)

**Evidence / Artifacts:**
- AWS Backup vault job history (`lm-backup-vault`)
- Velero backup schedule manifest (`platform-gitops/velero/backup-schedule.yaml`)
- RDS automated backup configuration (AWS Console → RDS → `lm-prod-db` → Maintenance & backups)
- S3 Cross-Region Replication configuration for `lm-data-*` buckets
- Annual restore test report (Confluence: LM-SECURITY / CP / Recovery Tests / 2026)

**Enhancements Addressed:**
- **CP-9(1):** Annual restore test conducted as part of the CP-10 recovery exercise.
  Most recent test: 2026-02-15 — RDS PITR and Velero restore both passed.
- **CP-9(3):** All backups cross-region replicated to us-west-2. Primary workloads in
  us-east-1. A regional failure in us-east-1 does not affect backup availability.
- **CP-9(5):** S3 Cross-Region Replication provides continuous transfer for S3 data.
  RDS and Velero backups are copied to us-west-2 on the daily backup schedule.
  RPO for RDS is 5 minutes (PITR). RPO for K8s state is 24 hours (daily Velero backup).

---

## CP-10 — System Recovery and Reconstitution

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

**RTO and RPO Targets:**

| Component | RTO | RPO | Recovery Method |
| --------- | --- | --- | --------------- |
| RDS PostgreSQL | 2 hours | 5 minutes | AWS RDS PITR |
| EKS cluster (applications) | 4 hours | 24 hours | Velero restore + ArgoCD sync |
| S3 data buckets | 1 hour | Near-zero (CRR continuous) | S3 CRR failover (promote replica) |
| Terraform infrastructure | 8 hours | N/A (IaC — no data loss) | `terraform apply` in us-west-2 |

**Recovery Runbook:**
The Links-Matrix recovery runbook (`platform-gitops/docs/recovery-runbook.md`) documents
step-by-step recovery procedures for each component including RDS PITR, Velero K8s
restore, S3 replica promotion, and full infrastructure reconstitution from Terraform in
us-west-2. The runbook is reviewed annually and after any significant architecture change.
Last review: 2026-02-01.

**Recovery Exercise:**
An annual recovery exercise is conducted in February, using the `lm-staging` environment
as the recovery target (production data is not used — a recent backup of production is
restored into staging). The 2026 exercise (2026-02-15) tested:
- RDS PITR restore to a point 2 hours before the exercise — completed in 47 minutes (RTO: 2 hours ✅)
- Velero namespace restore for 3 production namespaces — completed in 1 hour 12 minutes (RTO: 4 hours ✅)
- ArgoCD application sync post-restore — completed in 22 minutes
- Application smoke tests post-restore — passed

**Post-Recovery Integrity Verification:**
After recovery, the Platform Engineer verifies:
- ArgoCD shows all applications Synced and Healthy (configuration matches baseline)
- kube-bench run confirms no CIS Benchmark regressions
- Application health checks pass
- Security controls (Kyverno, Falco) are running

**Responsible Role:** Platform Engineer (recovery execution, Velero, ArgoCD), Cloud Security Engineer (RDS restore, Terraform apply), ISSO (exercise oversight, integrity sign-off)

**Parameters:**
- RTO (RDS): **2 hours**; RTO (EKS applications): **4 hours**; RTO (S3): **1 hour**
- RPO (RDS): **5 minutes** (PITR); RPO (K8s): **24 hours** (daily backup)
- Annual recovery exercise: **February**
- Recovery runbook review cadence: **Annual** + significant change

**Evidence / Artifacts:**
- Recovery runbook (`platform-gitops/docs/recovery-runbook.md`)
- Annual recovery exercise report 2026 (Confluence: LM-SECURITY / CP / Recovery Tests / 2026)
- RDS PITR configuration (AWS Console → RDS → `lm-prod-db`)
- Velero restore test log (retained in `lm-backup-us-east-1` S3 bucket)

**Enhancements Addressed:**
- **CP-10(2):** RDS PostgreSQL automated backups with PITR provide transaction-level
  recovery. RPO of 5 minutes means at most one 5-minute transaction window is lost.
  *(Note: application-level transaction logs are not separately managed — database-level
  PITR is the only transaction recovery mechanism.)*
- **CP-10(4):** Annual recovery exercise validates RTO targets. 2026 exercise confirmed
  RDS RTO (47 min vs. 2-hour target) and EKS RTO (1h12m vs. 4-hour target) were met.
  Both targets documented in the contingency plan (Confluence: LM-SECURITY / CP / Contingency Plan).

---

## What Makes This GOOD (But Not Great) — Examiner's Notes

| Control | Strengths | Gaps |
| ------- | --------- | ---- |
| CP-9 | Backup schedule table complete, cross-region named, CMK encryption, Velero + AWS Backup + etcd all covered | Restore test is annual — a quarterly rotate would catch issues sooner; no automated backup failure alerting (weekly manual review only) |
| CP-9 | PITR retention 35 days | If ransomware goes undetected >35 days, all backups are compromised — no immutable "clean" backup copy beyond that window |
| CP-10 | RTO/RPO table with specific values, recovery exercise with actual timing results | Post-recovery integrity check is a bulleted list, not a formal checklist with sign-off; no attacker persistence check procedure |
| CP-10 | Recovery runbook exists and is reviewed | Runbook review cadence is annual — if architecture changes mid-year and runbook is not updated, it may be wrong during an actual incident |
| Both | CP-9 and CP-10 reference each other | No formal RPO/RTO derivation — where did the 2-hour and 4-hour targets come from? No business impact analysis or risk acceptance for the current targets |
