---
family: AU
family_name: Audit and Accountability
id: AU-9
name: Protection of Audit Information
---

question: "Are audit logs protected so an attacker cannot erase or alter evidence of their activity?"

description: >
  The information system protects audit information and audit tools from unauthorized access,
  modification, and deletion. An attacker who gains system access will attempt to cover their
  tracks by deleting or modifying logs. AU-9 closes that path — audit data must be stored
  in a location and with permissions that the compromised system cannot reach. This means
  log storage must be architecturally separate from the system being audited, with write
  access removed from the system after initial log shipment.

enhancements:
  - id: AU-9(2)
    name: Store on Separate Physical Systems or Components
    description: >
      The information system backs up audit records periodically onto a physically different
      system or component than the system being audited. In cloud-native terms: K8s audit
      logs must be shipped to a separate account, bucket, or log management platform —
      not stored on the cluster nodes being audited.
  - id: AU-9(4)
    name: Access by Subset of Privileged Users
    description: >
      The organization authorizes access to management of audit logging functionality
      to only a defined subset of privileged users. The set of users who can modify
      audit configuration (what gets logged) must be strictly smaller than the set
      of users who can read logs. Developers and operators read logs; only security
      personnel modify audit policy.

HITRUST_map:
  - "09.aa — Audit Logging"
  - "09.ab — Monitoring System Use"
  - "10.f — Policy on the Use of Cryptographic Controls"

evidence:
  what_to_look_for:
    - Log storage location in a separate account, subscription, or system from the audited system
    - Immutability configuration on log storage (S3 Object Lock, Azure Immutable Blob, Vault audit log)
    - Access control policy showing the audited system has write-only or append-only access to log storage (no delete, no modify)
    - Separate access control for audit log management vs. audit log reading
    - Integrity verification mechanism (hash or digital signature) on log files
    - Alert on audit log deletion or gap in log stream
  ask_for:
    - "Show me where K8s audit logs are stored — is it on the cluster itself or shipped to an external system? Who has delete access to that storage?"
    - "Show me the S3 bucket or log storage policy — can the cluster's IAM role delete or overwrite log objects?"
    - "Show me your immutability configuration for audit log storage — is Object Lock or equivalent enforced?"
    - "Show me what alerts fire if audit logging stops or if a log deletion event is detected."
  tools:
    generic:
      - Falco (alert on audit log file modification or deletion on nodes)
      - Fluent Bit / Fluentd (ship audit logs to external system — verify no local buffering that can be cleared)
      - HashiCorp Vault audit log (append-only, separate from application data)
      - Vector (log shipping with integrity checksums)
    aws:
      - S3 Object Lock (WORM — Governance or Compliance mode on CloudTrail bucket)
      - CloudTrail log file validation (SHA-256 hash chain — `aws cloudtrail validate-logs`)
      - S3 bucket policy (deny s3:DeleteObject, s3:PutObject for all except log delivery role)
      - AWS Config (rule: cloud-trail-log-file-validation-enabled)
      - Separate AWS account for log archive (Organizations log archive account pattern)
    microsoft:
      - Azure Immutable Blob Storage (WORM policy on Log Analytics or Storage Account)
      - Azure Monitor Log Analytics (read-only workspace access for analysts — no delete permission)
      - Microsoft Sentinel (immutable log ingestion — Sentinel cannot retroactively delete ingested data)
      - Azure Policy (deny storage account configuration changes that would disable immutability)

failure_to_implement:
  - Audit logs stored on cluster nodes — an attacker with node access deletes logs before detection.
  - Log storage bucket has no Object Lock — a compromised cloud credential can delete all audit history.
  - The same IAM role that runs workloads also has delete access to the CloudTrail bucket.
  - No alerting on log gaps — audit logging silently stops for 12 hours and no one notices.
  - Auditor requests 90-day log history — logs were deleted at 30 days because storage was not sized for retention.

related:
  - AU-2
  - AU-3
  - AU-12

chain: null
