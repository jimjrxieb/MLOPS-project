---
family: CP
family_name: Contingency Planning
id: CP-9
name: System Backup
---

question: "Are system backups taken on schedule, verified for integrity, and confirmed restorable before they are needed?"

description: >
  The organization conducts backups of user-level information, system-level information,
  and system documentation at defined frequencies; protects the confidentiality, integrity,
  and availability of backup information; and tests backup information to verify media
  reliability and information integrity. The critical failure mode for backups is not
  missing the backup — it is assuming the backup works and discovering it does not during
  a recovery. Backup without verified restoration capability is not a backup program;
  it is a false sense of resilience. Every backup must be tested. The recovery must work
  under incident conditions, not just during a planned exercise with time to spare.

enhancements:
  - id: CP-9(1)
    name: Testing for Reliability and Integrity
    description: >
      The organization tests backup information at defined frequencies to verify media
      reliability and information integrity. A successful backup write is not evidence
      of a successful backup — only a successful restore from the backup is evidence.
      Restore tests must be scheduled, documented, and must result in a verified
      functional system state.
  - id: CP-9(3)
    name: Separate Storage for Critical Information
    description: >
      The organization stores backup copies of the operating system and other critical
      system software in a separate facility or fire-rated container. In cloud terms:
      backup storage is in a different region or availability zone from the primary system.
      A disaster that takes down the primary region must not also destroy the backup.
  - id: CP-9(5)
    name: Transfer to Alternate Storage Site
    description: >
      The organization transfers system backup information to the alternate storage site
      at defined frequencies consistent with recovery time and recovery point objectives.
      Cross-region replication on a schedule that matches the RPO — not a manual process
      that only happens when someone remembers.

HITRUST_map:
  - "09.l — Network Monitoring"
  - "09.s — Information Backup"
  - "10.b — Input Data Validation"

evidence:
  what_to_look_for:
    - Backup schedule documentation defining what is backed up, at what frequency, and retained for how long
    - Backup job success/failure logs with timestamps for each scheduled backup
    - Cross-region or off-site backup storage configuration with replication verification
    - Restore test records — date of test, what was restored, time to restore, and pass/fail outcome
    - Backup encryption configuration (backups encrypted at rest using KMS or equivalent)
    - RPO and RTO targets defined and tested against actual backup and restore times
  ask_for:
    - "Show me your backup schedule and the last 30 days of backup job results — are there any failures or gaps?"
    - "Show me your most recent restore test — what was restored, how long did it take, and how was success verified?"
    - "Show me where backups are stored — is it in a different region from primary? Show me the replication configuration."
    - "Show me your backup encryption configuration — are backups encrypted with a CMK, and is key access separate from backup access?"
  tools:
    generic:
      - Velero (K8s cluster and persistent volume backup — schedule, restore, and verification)
      - etcd backup (K8s control plane state — scheduled snapshot with off-cluster storage)
      - pg_dump / mysqldump (database backup with integrity verification)
      - restic (encrypted, deduplicated backup with restore testing support)
    aws:
      - AWS Backup (centralized backup management — schedule, retention, cross-region copy, restore testing)
      - EBS Snapshots (automated snapshot lifecycle with cross-region copy)
      - RDS Automated Backups and Snapshots (point-in-time restore with defined retention)
      - S3 Cross-Region Replication (backup bucket replication to secondary region)
      - AWS Config (rule: rds-automatic-minor-version-upgrade-enabled, db-instance-backup-enabled)
    microsoft:
      - Azure Backup (VM, database, and file backup with restore point management)
      - Azure Site Recovery (replication and failover capability for contingency)
      - Azure Kubernetes Service backup (AKS cluster state and PVC backup)
      - Azure Blob Storage geo-redundant replication (backup storage with cross-region redundancy)

failure_to_implement:
  - Backups are configured but job failures go unmonitored — a silent failure means no backup has been taken for 30 days.
  - Backups stored in the same region as primary — a regional outage destroys both the system and its recovery data.
  - Restore has never been tested — during an actual incident the restore process takes 10x longer than expected and partially fails.
  - Backup retention is 7 days — a ransomware infection that went undetected for 8 days has corrupted all available restore points.
  - Backups are not encrypted — a backup storage breach exposes the full dataset in plaintext.

related:
  - CP-10
  - IR-4
  - SC-28

chain: null
