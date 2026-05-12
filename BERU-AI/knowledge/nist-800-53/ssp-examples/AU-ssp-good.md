# System Security Plan — Audit and Accountability (AU) Family

## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** This SSP would pass a readiness review with 4-6 clarification items.
> Real tools are named, cadences are defined, and the AU control chain is respected.
> Gaps: evidence is described not located, two enhancements are silently skipped,
> test procedures are absent, and AU-9 immutability is asserted but not proven.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Final Draft — Pending ISSO Signature
**Authorization Boundary:** AWS EKS production cluster (`lm-prod-eks-us-east-1`),
supporting AWS services (RDS, S3, ECR, KMS), and the Okta tenant managing human
user identities.

---

## AU-2 — Event Logging

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

The Links-Matrix Platform has a documented audit event policy covering the following
event categories:

- **Authentication events:** Successful and failed logins, MFA challenges, session creation
  and termination (captured in Okta System Log and CloudTrail console sign-in events)
- **Privilege use:** IAM role assumption events, Kubernetes cluster-admin API calls,
  break-glass account activation (captured in CloudTrail and K8s audit log)
- **Data access:** S3 object reads and writes on `lm-data-*` buckets, RDS query events
  for sensitive tables (captured via CloudTrail data events and RDS audit log)
- **Configuration changes:** IAM policy modifications, K8s RBAC changes, CloudTrail
  configuration changes, Kyverno policy changes (captured in CloudTrail and K8s audit log)
- **System and application failures:** Application error logs, health check failures,
  container crash events (captured in CloudWatch Logs and OpenSearch)

The Kubernetes audit policy (`k8s-audit-policy.yaml`) is deployed to the EKS control
plane via Terraform and defines event rules at Metadata level for standard operations
and Request level for secrets, configmaps, and RBAC resources.

The event list is reviewed annually by the ISSO and after any significant architecture
change. Last review: 2026-02-01.

**Responsible Role:** ISSO (policy owner), Platform Engineer (K8s audit policy), Cloud Security Engineer (CloudTrail config)

**Parameters:**
- Event list review frequency: Annual + change-triggered
- K8s audit log levels: Metadata (default), Request (secrets/RBAC/configmaps)

**Evidence / Artifacts:**
- Audit event policy document (Security Runbook, Section 5)
- `k8s-audit-policy.yaml` in `platform-gitops/config/`
- CloudTrail trail configuration showing enabled event categories
- Last audit event list review record (2026-02-01, signed by ISSO)

**Enhancements Addressed:**
- **AU-2(3):** Event list reviewed annually and after significant architecture changes.
  Next scheduled review: 2027-02-01.

---

## AU-3 — Content of Audit Records

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

All audit record sources on the Links-Matrix Platform are configured to capture the
following minimum required fields:

| Field | Description | Source |
| ----- | ----------- | ------ |
| Event type | Classification of the event (auth, config-change, data-access, etc.) | All log sources |
| Timestamp | ISO 8601 UTC — all nodes synchronized to AWS Time Sync Service (NTP) | All log sources |
| Source identity | Username, IAM role ARN, or K8s service account name | CloudTrail, K8s audit, Okta |
| Source location | Source IP address and VPC/network context | CloudTrail, K8s audit, VPC Flow Logs |
| Target resource | ARN, K8s resource kind/name/namespace, or application endpoint | CloudTrail, K8s audit |
| Outcome | Success or failure with response code | All log sources |
| Additional context | Request parameters for configuration changes; session ID for auth events | CloudTrail, K8s audit |

**Kubernetes audit records** at Request level include: `user.username`, `user.groups`,
`sourceIPs`, `verb`, `resource`, `namespace`, `name`, `responseStatus.code`.

**CloudTrail records** include: `eventTime`, `userIdentity` (ARN + session context),
`sourceIPAddress`, `eventName`, `requestParameters`, `responseElements`, `errorCode`.

**Application audit records** (Links-Matrix API) are structured JSON including:
`timestamp`, `user_id`, `role`, `action`, `resource_id`, `source_ip`, `http_status`.
Application logs are shipped to OpenSearch via Fluent Bit.

Failed events are captured with the same field set as successful events, including the
specific error code or denial reason.

**Responsible Role:** Platform Engineer (K8s and log pipeline), Application Developer (app audit format)

**Parameters:** N/A (field requirements are enforced by log source configuration)

**Evidence / Artifacts:**
- K8s audit log sample entry (produced during quarterly RBAC audit)
- CloudTrail event example for a privileged role assumption
- Application audit log JSON schema in `platform-gitops/docs/audit-log-schema.md`
- OpenSearch index mapping for `lm-audit-*` showing all required fields

**Enhancements Addressed:**
- **AU-3(1):** K8s audit records include extended fields (namespace, requestURI, userAgent,
  sourceIPs). CloudTrail records include requestParameters for all management events.
- **AU-3(2):** Log format and field requirements are centrally managed — Fluent Bit
  configuration in `platform-gitops/logging/` controls enrichment. Individual teams
  cannot remove required fields without a GitOps PR review.

---

## AU-6 — Audit Record Review, Analysis, and Reporting

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

Audit log review and analysis is performed through a combination of automated SIEM
alerting and scheduled human review.

**Automated Review (Continuous):**
OpenSearch with OpenSearch Dashboards serves as the primary SIEM for the Links-Matrix
Platform. Fluent Bit ships logs from all cluster components, application containers,
and CloudTrail to OpenSearch in near-real-time (average latency: <30 seconds). Active
alert rules cover the following event categories from the AU-2 event list:

- Failed authentication (>5 failures in 5 minutes from a single source IP)
- Privileged role assumption outside business hours (18:00–06:00 UTC)
- Kubernetes cluster-admin API calls
- CloudTrail configuration modification (disable, delete, update)
- S3 `DeleteObject` events on audit log buckets
- Kyverno policy violations (admission control denials)

Alerts route to the `#sec-alerts` Slack channel and create PagerDuty incidents for
P1/P2 severity. The SOC on-call acknowledges and triages alerts within 1 hour.

**Scheduled Human Review:**
- **Daily:** SOC on-call reviews the OpenSearch overnight alert summary dashboard
  (saved search: `lm-daily-alert-summary`) each morning.
- **Weekly:** SOC lead reviews the 7-day trend dashboard and closes or escalates open
  alert tickets in Jira.
- **Monthly:** The ISSO reviews the monthly audit summary report generated by the
  `audit-monthly-report.sh` script and distributed to the CISO and System Owner.

**Cross-Source Correlation:**
OpenSearch correlation rules link CloudTrail `AssumeRole` events with K8s API server
access events by correlating on IAM role ARN and timestamp within a 5-minute window.
This detects cloud-to-cluster lateral movement patterns.

**Responsible Role:** SOC (daily/weekly review, alert triage), ISSO (monthly report, escalation authority)

**Parameters:**
- Alert acknowledgment SLA: 1 hour (P1/P2), 4 hours (P3)
- Daily review: Every business day
- Monthly report distribution: First Monday of each month

**Evidence / Artifacts:**
- OpenSearch alert rule definitions (exported from OpenSearch Alerts plugin)
- Jira alert triage ticket history (project: `SEC-ALERTS`, last 90 days)
- Monthly audit summary report for April 2026 (distributed 2026-05-04)
- PagerDuty service configuration for `lm-security-alerts`

**Enhancements Addressed:**
- **AU-6(1):** OpenSearch + PagerDuty automates alert generation. SOC reviews alerts,
  not raw log streams.
- **AU-6(3):** CloudTrail-to-K8s correlation rule in OpenSearch correlates across log
  repositories. *(Note: correlation coverage is limited to cloud-to-cluster paths;
  app-to-cluster cross-source correlation is planned for Q3 2026.)*

---

## AU-7 — Audit Record Reduction and Report Generation

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

The Links-Matrix Platform provides audit record reduction and reporting through two
read-only query interfaces:

**OpenSearch (Primary):** Analysts access OpenSearch Dashboards using role-based access.
The `soc-analyst` role has read-only access to audit indices (`lm-audit-*`,
`lm-cloudtrail-*`, `lm-k8s-audit-*`). The role explicitly does not have `indices:data/write`
or `cluster:admin` permissions — analysts cannot modify or delete index data. Saved searches
and dashboards allow on-demand filtering by user, time range, event type, and source IP
without touching raw log storage.

**Amazon Athena (CloudTrail Archive):** CloudTrail logs stored in S3
(`lm-logs-cloudtrail/`) are queryable via Athena using a Glue catalog table. The Athena
execution role (`lm-athena-query-role`) has `s3:GetObject` and `s3:ListBucket` on the
CloudTrail bucket only — no `s3:DeleteObject` or `s3:PutObject`. Queries return results
without modifying the source objects.

On-demand reports are generated using saved Athena queries or OpenSearch Dashboards
exports (CSV or PDF). Reports generated for compliance or investigation requests are
retained in S3 bucket `lm-audit-reports/` with a 7-year retention policy.

Scheduled automated reports include the daily alert summary (generated at 06:00 UTC by
a CloudWatch Events rule triggering a Lambda) and the monthly audit summary.

**Responsible Role:** SOC (report generation, saved query ownership), Platform Engineer (pipeline and access configuration)

**Parameters:**
- Audit report retention: 7 years (S3 lifecycle policy)
- Automated daily report generation time: 06:00 UTC

**Evidence / Artifacts:**
- OpenSearch role definition for `soc-analyst` (showing no write permissions)
- Athena execution role IAM policy (`infra-iac/iam/athena-query-role.tf`)
- Sample on-demand Athena query output for a recent investigation
- S3 lifecycle configuration for `lm-audit-reports/`

**Enhancements Addressed:**
- **AU-7(1):** CloudWatch Events Lambda generates daily audit summary automatically.
  OpenSearch saved searches surface events of interest without manual scanning.

---

## AU-9 — Protection of Audit Information

**Implementation Status:** Implemented

**Control Origination:** Hybrid (Inherited from AWS S3 Object Lock; System-Specific for access controls and alerting)

**Implementation Description:**

Audit logs are stored in a dedicated AWS account (`lm-log-archive`, account ID
`112233445566`) separate from the production workload account (`lm-prod`). Cross-account
log delivery is the only write path — production workloads can ship logs to the archive
account but cannot read, modify, or delete them.

**S3 Immutability:**
The CloudTrail log bucket (`lm-logs-cloudtrail`) and the OpenSearch snapshot bucket
(`lm-logs-opensearch-snapshots`) in the archive account have S3 Object Lock enabled in
Compliance mode with a 7-year retention period. No IAM principal, including the account
root user, can delete or overwrite objects within the retention period. CloudTrail log
file validation is enabled — SHA-256 hash chains are verified monthly using
`aws cloudtrail validate-logs`.

**Access Control:**
In the archive account, the `log-reader` IAM role (assigned to SOC analysts) has
`s3:GetObject` and `s3:ListBucket` only. No role in the archive account has
`s3:DeleteObject` or `s3:PutObjectAcl`. This is enforced by an SCP at the AWS
Organizations level (`deny-log-deletion` SCP on the archive OU).

**Alerting on Log Gaps:**
A CloudWatch metric filter monitors the CloudTrail log stream delivery. If no new log
objects are written to S3 within a 15-minute window during active hours, a CloudWatch
alarm triggers a PagerDuty P2 alert to the SOC. Separately, an EventBridge rule alerts
on any `DeleteBucket` or `DeleteObject` API call in the archive account regardless of
outcome (even access-denied attempts are alerted).

**Responsible Role:** Cloud Security Engineer (archive account, Object Lock, SCP), ISSO (access policy owner)

**Parameters:**
- Log retention period: 7 years (S3 Object Lock — Compliance mode)
- Log gap alert threshold: 15 minutes without new CloudTrail delivery
- Archive account separation: Enforced at AWS Organizations OU level

**Evidence / Artifacts:**
- S3 Object Lock configuration for `lm-logs-cloudtrail` (AWS console or CLI output)
- SCP `deny-log-deletion` applied to log archive OU (AWS Organizations console)
- CloudTrail log validation report (`aws cloudtrail validate-logs` output — run monthly)
- CloudWatch alarm configuration for log gap detection
- Archive account IAM policy showing no delete permissions for any role

**Enhancements Addressed:**
- **AU-9(2):** Audit logs stored in a physically separate AWS account (`lm-log-archive`)
  from the system being audited (`lm-prod`). Cross-account delivery only — no reverse path.
- **AU-9(4):** Audit logging configuration (CloudTrail settings, K8s audit policy) is
  modifiable only by the Cloud Security Engineer and ISSO roles. SOC analysts have
  read-only access. *(Note: a formal access matrix for audit management functions is
  planned for documentation in Q3 2026.)*

---

## AU-12 — Audit Record Generation

**Implementation Status:** Implemented

**Control Origination:** Hybrid (Inherited from AWS CloudTrail; System-Specific for K8s audit and application logging)

**Implementation Description:**

The Links-Matrix Platform generates audit records for all event categories defined in
AU-2 across the following system components:

| Component | Audit Mechanism | Coverage Scope |
| --------- | --------------- | -------------- |
| AWS API calls (all services) | CloudTrail multi-region trail | All AWS regions where workloads run (us-east-1, us-west-2) |
| Kubernetes API server | K8s audit policy (`k8s-audit-policy.yaml`) | All API server instances in EKS control plane |
| Container workloads | Fluent Bit DaemonSet → OpenSearch | All namespaces; stdout/stderr of all containers |
| Application (Links-Matrix API) | Structured JSON logging → OpenSearch | All API endpoints; auth, data access, errors |
| AWS resource configuration | AWS Config recorder (all resource types) | Both regions; continuous recording |
| Network | VPC Flow Logs → CloudWatch Logs | All VPCs; ACCEPT and REJECT records |

**NTP / Time Synchronization:**
All EKS worker nodes use the AWS Time Sync Service (`169.254.169.123`) as their NTP source.
Node clock synchronization is verified by a daily CronJob (`clock-skew-check`) that runs
`chronyc tracking` on each node and writes results to a ConfigMap. The ISSO reviews
this report weekly. Maximum permitted clock skew: 500 milliseconds.

**Log Pipeline Health:**
Fluent Bit exposes Prometheus metrics for `fluentbit_input_records_total` and
`fluentbit_output_dropped_records_total`. A Prometheus alert rule fires if drop rate
exceeds 0.1% over a 5-minute window. The alert routes to PagerDuty P2.

**Responsible Role:** Platform Engineer (K8s audit, Fluent Bit, NTP), Cloud Security Engineer (CloudTrail, Config, VPC Flow Logs)

**Parameters:**
- Multi-region CloudTrail: us-east-1, us-west-2 (all regions with workloads)
- Maximum permitted NTP clock skew: 500 milliseconds
- Log pipeline drop rate alert threshold: >0.1% over 5 minutes

**Evidence / Artifacts:**
- CloudTrail trail configuration showing multi-region and all event categories enabled
- `k8s-audit-policy.yaml` in `platform-gitops/config/` (git history shows deployment date)
- Fluent Bit DaemonSet manifest in `platform-gitops/logging/`
- Clock skew check CronJob report (weekly — last: 2026-04-28)
- Fluent Bit drop rate alert definition in `platform-gitops/monitoring/`

**Enhancements Addressed:**
- **AU-12(1):** All components synchronized to AWS Time Sync Service. Fluent Bit
  pipeline aggregates records from all components into OpenSearch with a common
  timestamp field enabling cross-component audit trail reconstruction.
- **AU-12(3):** The ISSO can increase K8s audit log verbosity by updating
  `k8s-audit-policy.yaml` via a GitOps PR, which ArgoCD applies within 2 minutes.
  For urgent investigations, the Platform Engineer can patch the audit policy directly
  with ISSO written approval. *(Note: a formal procedure documenting the time threshold
  and approval chain for verbosity changes is planned for the Security Runbook by Q3 2026.)*

---

## What Makes This GOOD (But Not Great) — Examiner's Notes

| Control | Strengths | Gaps |
| ------- | --------- | ---- |
| AU-2 | Event categories named, K8s audit levels specified, annual review documented | Event list is in "Security Runbook Section 5" — not a standalone artifact an auditor can request; no explicit coordination across component owners documented |
| AU-3 | Field table present, three log sources described with specific fields | No test procedure to verify fields actually appear; failure events are mentioned but not proven to have same field completeness |
| AU-6 | Specific alert rules listed, SIEM named, SOC cadence defined, monthly ISSO report | App-to-cluster cross-source correlation is "planned" (gap); no alert triage SLA metric tracked |
| AU-7 | Read-only access mentioned for both OpenSearch and Athena | No explicit test proving write access is blocked; report retention policy exists but immutability of report bucket not stated |
| AU-9 | Separate archive account, Object Lock named, alerting on log gaps | Audit management access matrix "planned" — that's a finding; AU-9(4) partially implemented |
| AU-12 | Component coverage table, NTP config specified, pipeline health monitoring | No coverage test verifying each AU-2 category produces actual log entries; Falco not mentioned as a generation layer |
| All | Real tools, real account IDs, real cadences | Evidence tables describe where artifacts live but don't confirm last-verified date; test procedures absent throughout |
