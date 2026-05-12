# System Security Plan — Audit and Accountability (AU) Family

## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** This SSP is auditor-ready. The AU control chain is explicitly
> honored (AU-2 defines scope → AU-3 defines fields → AU-12 generates records →
> AU-6 reviews them → AU-7 reports on them, with AU-9 protecting the whole pipeline).
> Every control names the mechanism, the owner, the exact parameter, and the
> artifact with its location. A 3PAO can walk in tomorrow and start testing.

---

**System Name:** Links-Matrix Platform
**System Owner:** J. Rivera, Platform Engineering Lead (jrivera@links-matrix.io)
**ISSO:** M. Chen, Information System Security Officer (mchen@links-matrix.io)
**Prepared By:** M. Chen, ISSO
**Date:** 2026-05-01
**Review Date:** 2027-05-01 (annual) or upon significant system change
**Status:** Approved — ATO Granted 2026-03-15, expires 2029-03-15

**Control Chain Note:** The AU controls on this system are implemented as an explicit
pipeline. AU-2 defines *what* to log. AU-3 defines *what fields* each record must contain.
AU-12 verifies the system is *actually generating* those records. AU-6 ensures someone
is *reviewing* them. AU-7 provides the *reporting* capability. AU-9 *protects* the entire
pipeline from tampering. A gap in any link breaks the chain.

---

## AU-2 — Event Logging

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Low, Moderate, and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Auditable Event Categories

The following event categories are required to be logged across all Links-Matrix Platform
components. This list was developed by the ISSO in coordination with the Platform Engineer,
Cloud Security Engineer, SOC Lead, and Application Developer. It was last reviewed and
approved on 2026-02-01 and is stored as a formal document in Confluence
(space: `LM-SECURITY`, page: `AU-2 Auditable Event List`, version 4).

| Category | Required Events | Primary Log Source | K8s Audit Level |
| -------- | --------------- | ------------------ | --------------- |
| Authentication — success | User login, MFA challenge pass, session creation, IAM role assumption | Okta System Log, CloudTrail | N/A |
| Authentication — failure | Failed login, failed MFA, locked account, invalid token | Okta System Log, CloudTrail | N/A |
| Privilege use | cluster-admin API calls, IAM admin role assumption, break-glass activation | K8s audit log, CloudTrail | Request |
| Account lifecycle | Account create, modify, disable, delete (human and service) | Okta System Log, CloudTrail | N/A |
| Data access | S3 GetObject/PutObject on `lm-data-*`, RDS query on `pii_*` tables | CloudTrail (data events), RDS audit log | N/A |
| Configuration change | IAM policy change, K8s RBAC change, Kyverno policy change, CloudTrail config change, K8s audit policy change | CloudTrail, K8s audit log | Request |
| Secret access | Kubernetes Secret read/write, AWS Secrets Manager GetSecretValue, KMS Decrypt | K8s audit log, CloudTrail | RequestResponse |
| Security tool events | Kyverno admission denial, Falco alert, GuardDuty finding | K8s events, GuardDuty, Falco JSON | N/A |
| Network | VPC flow REJECT records, security group change, NACl change | VPC Flow Logs, CloudTrail | N/A |
| System health | Container crash (OOMKilled, CrashLoopBackOff), node NotReady, log pipeline drop | CloudWatch Logs, Fluent Bit metrics | Metadata |
| Application | API auth failure, authorization denial (HTTP 403), data export events | Application audit log (`/lm-audit/`) | N/A |

**Kubernetes Audit Policy:**
The K8s audit policy (`k8s-audit-policy.yaml`) is deployed to the EKS control plane via
Terraform (`infra-iac/eks/audit-policy.tf`). It defines per-resource audit levels:
`RequestResponse` for secrets and configmaps, `Request` for RBAC resources and privilege
verbs, `Metadata` for all other resources, and `None` for read-only health check endpoints
(`/healthz`, `/readyz`, `/livez`) to prevent log noise without coverage gaps.

Changes to `k8s-audit-policy.yaml` require a pull request approved by the ISSO. The
Kyverno policy `protect-audit-policy` rejects any direct patch to the audit policy
ConfigMap outside of the ArgoCD service account.

**Event List Review:**
The AU-2 event list is reviewed by the ISSO annually (each February) and within 14 days
of any significant architecture change (new AWS service enabled, new K8s namespace for
sensitive workloads, new application integration). Reviews are documented in Confluence
with the reviewer name, review date, trigger (annual or change-driven), changes made, and
ISSO signature. The review record links to the updated event list version.

**Responsible Role:** ISSO (event list ownership, annual review), Platform Engineer (K8s audit policy deployment), Cloud Security Engineer (CloudTrail and VPC Flow Log configuration)

**Parameters:**
- K8s audit level for secrets: **RequestResponse**
- K8s audit level for RBAC and privilege verbs: **Request**
- K8s audit level for standard resources: **Metadata**
- Event list review frequency: **Annual** (February) + **within 14 days** of significant change
- Coordination scope: ISSO, Platform Engineer, Cloud Security Engineer, SOC Lead, Application Developer

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| AU-2 Auditable Event List (v4) | Confluence: LM-SECURITY / AU-2 Auditable Event List | 2026-02-01 |
| `k8s-audit-policy.yaml` | `platform-gitops/config/k8s-audit-policy.yaml` | Per-commit (git history) |
| CloudTrail trail config (data events enabled) | `infra-iac/cloudtrail/main.tf` + AWS Console | 2026-04-15 |
| Annual event list review record | Confluence: LM-SECURITY / AU-2 Review History | 2026-02-01 |
| Kyverno `protect-audit-policy` rule | `platform-gitops/kyverno/protect-audit-policy.yaml` | Per-commit |

**Test Procedure:**
1. Pull `k8s-audit-policy.yaml` from `platform-gitops/config/` — verify the `secrets`
   resource rule specifies `level: RequestResponse` and the rule is in effect on the cluster
   via `kubectl get auditpolicy -n kube-system`.
2. Access a Kubernetes Secret (`kubectl get secret lm-test-secret -n lm-prod`) and verify
   the corresponding audit log entry appears in OpenSearch within 60 seconds with
   `verb: get`, `resource: secrets`, and the requesting user's identity.
3. Attempt to directly patch the K8s audit policy ConfigMap as a non-ArgoCD principal —
   verify Kyverno blocks the request and generates a policy violation event.
4. Pull the AU-2 Auditable Event List from Confluence — verify its last-modified date
   is within the past 12 months or within 14 days of the last architecture change.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| AU-2(3) Reviews and Updates | Implemented | Annual review every February + within 14 days of significant change. Review records maintained in Confluence with ISSO signature. Review process is documented in Security Runbook Section 5.1. |

---

## AU-3 — Content of Audit Records

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Low, Moderate, and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Required Audit Record Field Schema

All log sources must produce audit records satisfying the following field requirements.
The field mapping document (`platform-gitops/docs/audit-field-mapping.md`) shows
how each required field is populated per log source and is reviewed quarterly.

| Required Field | NIST Purpose | K8s Audit | CloudTrail | Okta System Log | App Audit Log |
| -------------- | ------------ | --------- | ---------- | --------------- | ------------- |
| Event type | What occurred | `verb` + `resource` | `eventName` | `eventType` | `action` |
| Timestamp (UTC) | When it occurred | `requestReceivedTimestamp` | `eventTime` | `published` | `timestamp` |
| Source identity | Who caused it | `user.username` + `user.groups` | `userIdentity.arn` + session | `actor.id` + `actor.displayName` | `user_id` + `role` |
| Source location | Where from | `sourceIPs[0]` | `sourceIPAddress` | `client` (IP) | `source_ip` |
| Target resource | What was affected | `objectRef.resource` + `objectRef.name` + `objectRef.namespace` | `resources[].ARN` | `target.id` + `target.type` | `resource_id` + `resource_type` |
| Outcome | Success or failure | `responseStatus.code` | `errorCode` (absent = success) | `outcome.result` | `http_status` |
| Request detail | What parameters | `requestObject` (Request level) | `requestParameters` | `debugData` | `request_body_hash` |
| Response detail | What was returned | `responseObject` (RequestResponse level) | `responseElements` | N/A | `response_summary` |

**Field Completeness for Failure Events:**
Failed events are captured with identical field completeness to success events. This is
verified by the `audit-field-completeness-check.sh` test (see Test Procedure below).
Specifically: failed K8s API calls include `responseStatus.code` (4xx/5xx),
`responseStatus.message`, and `user.username` even when the user is unauthenticated
(the `system:anonymous` principal is captured). Failed Okta authentications include the
attempted username and failure reason in `outcome.reason`.

**Centralized Field Enforcement:**
Log format requirements are enforced at the pipeline level. The Fluent Bit configuration
(`platform-gitops/logging/fluent-bit-config.yaml`) includes a Lua filter that validates
required fields are present before forwarding to OpenSearch. Records missing required
fields are rejected and counted in the `fluentbit_output_rejected_records_total` metric,
which triggers a PagerDuty alert if non-zero over a 10-minute window. This ensures
field gaps are detected immediately, not discovered during an audit.

**Responsible Role:** Platform Engineer (Fluent Bit field enforcement, K8s audit format), Application Developer (application audit log schema), Cloud Security Engineer (CloudTrail record configuration)

**Parameters:**
- K8s audit Request level: secrets, configmaps, RBAC resources (RequestObject captured)
- K8s audit RequestResponse level: secrets only (ResponseObject captured)
- Field validation failure alert threshold: >0 rejected records over 10 minutes

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| Audit field mapping document | `platform-gitops/docs/audit-field-mapping.md` | 2026-04-07 (quarterly review) |
| Fluent Bit Lua field validation filter | `platform-gitops/logging/fluent-bit-config.yaml` | Per-commit |
| OpenSearch index mapping for `lm-audit-*` | OpenSearch Dev Tools: `GET lm-audit-*/_mapping` | 2026-04-07 |
| Field completeness test results | `platform-gitops/security/au3-field-test-YYYY-QQ.md` | 2026-04-07 |
| Application audit log JSON schema | `platform-gitops/docs/audit-log-schema.md` | Per-commit (app team owns) |

**Test Procedure:**
1. Run `audit-field-completeness-check.sh` from `platform-gitops/tools/`:
   - The script generates a known test event for each AU-2 category (auth success, auth
     failure, secret access, config change, privilege use)
   - It queries OpenSearch for the corresponding log entry within 120 seconds
   - It validates that all required fields from the field mapping table are populated
   - It produces a pass/fail report saved to `platform-gitops/security/au3-field-test-YYYY-QQ.md`
2. Manually pull a CloudTrail entry for a recent `sts:AssumeRole` event and verify
   `userIdentity.arn`, `sourceIPAddress`, `requestParameters`, and `responseElements`
   are all present and non-null.
3. Attempt a failed authentication in the Links-Matrix app (wrong password) and verify
   the Okta System Log entry contains `actor.id`, `client` IP, and `outcome.reason`.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| AU-3(1) Additional Audit Information | Implemented | K8s audit records include `requestURI`, `userAgent`, `sourceIPs` (array for proxy chains), `objectRef.subresource`, and `annotations` (Kyverno decision). CloudTrail includes `requestParameters`, `responseElements`, `vpcEndpointId`, and `sessionContext` for assumed roles. |
| AU-3(2) Centralized Management of Planned Audit Record Content | Implemented | Fluent Bit configuration centrally managed via GitOps. Lua field validation filter enforces required fields at pipeline ingestion. Individual teams cannot reduce field coverage without a PR reviewed by Platform Engineer + ISSO. Field validation failures alert immediately. |

---

## AU-6 — Audit Record Review, Analysis, and Reporting

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Moderate and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### SIEM Alert Rules

OpenSearch Alerting covers the following rules derived from the AU-2 event list. All rules
are defined in `platform-gitops/monitoring/opensearch-alerts/` and deployed via ArgoCD.

| Alert Rule | Trigger Condition | Severity | Notification |
| ---------- | ----------------- | -------- | ------------ |
| `auth-brute-force` | >5 Okta auth failures from same IP in 5 minutes | P2 | Slack `#sec-alerts` + PagerDuty |
| `priv-role-outside-hours` | CloudTrail `AssumeRole` for admin roles 18:00–06:00 UTC | P1 | PagerDuty + ISSO email |
| `cluster-admin-use` | K8s audit `verb:*` with `clusterrolebinding:cluster-admin` group | P1 | PagerDuty + ISSO email |
| `cloudtrail-disabled` | CloudTrail `StopLogging` or `DeleteTrail` event | P0 | PagerDuty (immediate) + CISO email |
| `log-bucket-delete-attempt` | S3 `DeleteObject` or `DeleteBucket` on `lm-logs-*` buckets (any outcome) | P1 | PagerDuty + ISSO email |
| `kyverno-violation-spike` | >10 Kyverno admission denials in 10 minutes | P2 | Slack `#sec-alerts` |
| `secret-access-unusual-principal` | K8s audit `verb:get` on `resource:secrets` by non-allowlisted service account | P2 | Slack `#sec-alerts` + PagerDuty |
| `guardduty-high` | GuardDuty finding severity ≥7.0 | P1 | PagerDuty + ISSO email |
| `falco-critical` | Falco priority `CRITICAL` or `ERROR` output | P1 | PagerDuty + ISSO email |
| `log-pipeline-gap` | No Fluent Bit records ingested for >15 minutes | P2 | PagerDuty |

### Review Cadence

| Cadence | Activity | Owner | Output |
| ------- | -------- | ----- | ------ |
| Continuous | SIEM alert triage — acknowledge P1/P2 within 1 hour, P3 within 4 hours | SOC on-call | Jira ticket `SEC-ALERTS` closed with disposition |
| Daily (06:00 UTC) | Review overnight alert dashboard (saved search `lm-daily-alert-summary`) | SOC on-call | Morning standup note in `#sec-ops` Slack |
| Weekly (Monday) | 7-day alert trend review, close stale Jira tickets, identify recurring false positives | SOC Lead | Weekly summary posted to `#sec-ops` |
| Monthly (first Monday) | Full audit log review report — alert volume, top sources, open items, trend analysis | ISSO | Report distributed to CISO and System Owner via email; archived in S3 `lm-audit-reports/monthly/` |
| Quarterly | SIEM alert rule review — add/remove/tune rules based on threat intel and false positive rate | ISSO + SOC Lead | Updated alert rule set merged via GitOps PR; review record in Confluence |

### Cross-Source Correlation

Four correlation rules are active in OpenSearch:

1. **Cloud-to-cluster lateral movement:** Correlates CloudTrail `AssumeRole` for a given
   IAM role ARN with K8s API server calls using that role's identity within 5 minutes.
   Flags: IAM assume-role from an unusual IP followed by K8s `secrets:get` or
   `clusterrolebinding:create`.

2. **Auth bypass attempt:** Correlates Okta authentication failure with a successful
   CloudTrail console login for the same `userPrincipalName` within 10 minutes.
   Flags: credential compromise after brute-force.

3. **Log evasion attempt:** Correlates Kyverno denial of a `patch:audit-policy` attempt
   with any CloudTrail `UpdateTrail` event within 15 minutes by the same principal.
   Flags: attacker attempting to reduce audit coverage.

4. **Privilege escalation chain:** Correlates K8s audit `rolebindings:create` with
   subsequent `secrets:get` by the newly bound principal within 30 minutes.
   Flags: RBAC privilege escalation followed by credential harvesting.

Correlation rules are defined in
`platform-gitops/monitoring/opensearch-correlations/` and reviewed quarterly by the ISSO
and SOC Lead.

**Responsible Role:** SOC (alert triage, daily/weekly review), ISSO (monthly report, rule governance, escalation authority), SOC Lead (weekly trend analysis, rule tuning)

**Parameters:**
- P1 alert acknowledgment SLA: **1 hour** (enforced; PagerDuty escalates if unacknowledged)
- P2 alert acknowledgment SLA: **4 hours**
- P3 alert acknowledgment SLA: **next business day**
- Monthly report distribution: **First Monday of each month**
- Alert rule review cadence: **Quarterly**

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| OpenSearch alert rule definitions | `platform-gitops/monitoring/opensearch-alerts/` | Per-commit (ArgoCD deployed) |
| Jira `SEC-ALERTS` ticket history (90 days) | Jira project SEC-ALERTS | Continuous |
| Monthly audit report (April 2026) | S3 `lm-audit-reports/monthly/2026-04.pdf` | 2026-05-04 |
| Cross-source correlation rule definitions | `platform-gitops/monitoring/opensearch-correlations/` | 2026-04-07 (quarterly review) |
| Quarterly alert rule review record | Confluence: LM-SECURITY / Alert Rule Reviews | 2026-04-07 |
| PagerDuty SLA compliance report | PagerDuty Analytics → Service `lm-security-alerts` | Monthly |

**Test Procedure:**
1. Simulate a brute-force authentication event (generate 6 Okta auth failures from a
   test account within 5 minutes) — verify `auth-brute-force` alert fires in OpenSearch
   within 60 seconds and a PagerDuty incident is created.
2. Pull the Jira `SEC-ALERTS` project — verify every P1 ticket from the last 90 days
   was acknowledged within 1 hour of creation (compare Jira `created` vs. first comment
   timestamp).
3. Pull the monthly audit report for the most recent month from S3 — verify it is
   present, not empty, and was distributed before the 5th of the following month.
4. Verify the cloud-to-cluster lateral movement correlation rule is active: run
   `GET /_plugins/_alerting/rules` in OpenSearch Dev Tools and confirm the rule
   `cloud-to-cluster-lateral-movement` is enabled with the correct trigger conditions.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| AU-6(1) Automated Process Integration | Implemented | OpenSearch Alerting + PagerDuty automate detection and escalation. SOC reviews alert tickets and dashboards, not raw log streams. Ten active alert rules covering all AU-2 event categories. False positive rate tracked quarterly; rule tuning is a standing agenda item. |
| AU-6(3) Correlate Audit Repositories | Implemented | Four cross-source correlation rules active in OpenSearch covering cloud-to-cluster movement, auth bypass, log evasion, and privilege escalation chains. Rules reviewed quarterly. Coverage gap analysis completed 2026-04-07 — no unaddressed cross-source attack patterns identified for current threat model. |

---

## AU-7 — Audit Record Reduction and Report Generation

**Implementation Status:** Implemented
**Control Origination:** Hybrid (Inherited from AWS Athena read-only access model; System-Specific for OpenSearch role separation and report retention)
**Baseline Allocation:** Moderate and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Implementation Description

**Separation of Read and Write Access to Log Storage:**
Log storage and log querying are architecturally separated. The log archive account
(`lm-log-archive`) holds the authoritative log store. The OpenSearch cluster and Athena
query engine have read-only access via cross-account IAM roles with explicit deny on all
write and delete operations. This is enforced at three layers:

1. **S3 bucket policy** on `lm-logs-cloudtrail` and `lm-logs-opensearch-snapshots`:
   explicit `Deny` on `s3:DeleteObject`, `s3:PutObject`, `s3:DeleteBucket` for all
   principals except the log delivery role.
2. **IAM role policy** for `lm-opensearch-reader` and `lm-athena-query-role`:
   `s3:GetObject` and `s3:ListBucket` only — no write actions present.
3. **SCP** on the log archive OU: denies `s3:DeleteObject` and `s3:DeleteBucket`
   for all principals on log buckets, overriding any account-level policy that might
   be added in the future.

**OpenSearch (SIEM Query and Dashboards):**
SOC analysts access OpenSearch Dashboards using the `soc-analyst` OpenSearch role.
This role has `indices:data/read/*` on `lm-audit-*` indices and explicitly omits
`indices:data/write/*`, `indices:admin/delete`, and `cluster:admin/*`. Role assignment
is managed in `platform-gitops/opensearch/roles/soc-analyst-role.yaml`. An automated
weekly check (`opensearch-role-audit.sh`) queries the OpenSearch Security API and
verifies no write permissions are present on the analyst role. Discrepancies trigger
a PagerDuty P1 alert.

**Amazon Athena (CloudTrail Archive Queries):**
CloudTrail logs in S3 are queryable via Athena using a Glue catalog table
(`lm_cloudtrail_logs`). Saved queries for common investigation patterns
(user activity timeline, resource change history, cross-account access review) are
stored in `platform-gitops/athena/saved-queries/`. The Athena execution role
(`lm-athena-query-role`) is scoped as described above.

**Report Generation and Retention:**
All audit reports (generated from OpenSearch exports or Athena query outputs) are written
to S3 `lm-audit-reports/` with:
- 7-year retention via S3 lifecycle policy
- S3 Object Lock in Governance mode (reports cannot be deleted by non-root principals
  before 7 years — separate from the Compliance mode on raw logs)
- Read access for ISSO, CISO, and Compliance Officer only

Automated scheduled reports:
- **Daily alert summary:** Lambda at 06:00 UTC queries OpenSearch, generates PDF,
  uploads to `lm-audit-reports/daily/YYYY-MM-DD.pdf`
- **Monthly audit report:** Lambda on first Monday queries Athena and OpenSearch,
  generates PDF, uploads to `lm-audit-reports/monthly/YYYY-MM.pdf`, emails CISO and SO
- **Quarterly compliance export:** ISSO-triggered Athena query producing a structured
  CSV for FedRAMP evidence packaging

**Responsible Role:** SOC (report generation, saved query ownership), Platform Engineer (OpenSearch role configuration, Lambda report jobs), ISSO (report distribution, retention policy ownership)

**Parameters:**
- Analyst log access: **read-only** (enforced at S3 + IAM + SCP + OpenSearch role)
- Audit report retention: **7 years** (S3 Object Lock — Governance mode)
- Daily report generation time: **06:00 UTC**
- OpenSearch role write-permission check: **Weekly** (automated)

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| OpenSearch `soc-analyst` role definition | `platform-gitops/opensearch/roles/soc-analyst-role.yaml` | Per-commit |
| Weekly OpenSearch role audit report | `platform-gitops/security/opensearch-role-audit-YYYY-WW.md` | 2026-04-28 |
| Athena query role IAM policy | `infra-iac/iam/athena-query-role.tf` | Per-commit |
| S3 bucket policy for `lm-logs-cloudtrail` | `infra-iac/s3/log-archive-policy.tf` | Per-commit |
| S3 Object Lock config for `lm-audit-reports` | `infra-iac/s3/audit-reports-bucket.tf` | Per-commit |
| SCP `deny-log-write` on archive OU | AWS Organizations console | 2026-04-15 |
| Sample daily audit report | S3 `lm-audit-reports/daily/2026-05-03.pdf` | 2026-05-04 |

**Test Procedure:**
1. As the `soc-analyst` OpenSearch user, attempt to delete a document from the
   `lm-audit-2026-04` index — verify `403 Forbidden` response and no document is deleted.
2. As the `lm-athena-query-role` IAM role, attempt `aws s3 rm s3://lm-logs-cloudtrail/test`
   — verify `AccessDenied` from the S3 bucket policy.
3. Pull `lm-audit-reports/daily/` from S3 — verify a report exists for each of the
   last 7 calendar days with non-zero file size.
4. Run `opensearch-role-audit.sh` manually — verify output shows zero write permissions
   on the `soc-analyst` role and the result matches the last weekly report.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| AU-7(1) Automatic Processing | Implemented | Lambda-driven daily and monthly report generation runs automatically on schedule. OpenSearch saved searches and Athena saved queries surface events of interest for the SOC without manual scanning. Scheduled Lambda generates compliance-ready CSV exports for FedRAMP evidence packages on demand. |

---

## AU-9 — Protection of Audit Information

**Implementation Status:** Implemented
**Control Origination:** Hybrid (Inherited from AWS S3 Object Lock and Organizations SCP; System-Specific for alerting, access management, and audit management authorization)
**Baseline Allocation:** Moderate and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Log Storage Architecture

Audit logs are stored in a dedicated AWS log archive account (`lm-log-archive`,
account ID `112233445566`) that is organizationally and technically isolated from the
production workload account (`lm-prod`, account ID `998877665544`). The log delivery
trust relationship is one-way: production workloads can write to the archive account;
no principal in the archive account has any access to the production account.

```
lm-prod (998877665544)
  ├── CloudTrail → cross-account delivery → lm-log-archive S3
  ├── Fluent Bit → cross-account OpenSearch ingestion role → lm-log-archive OpenSearch
  └── VPC Flow Logs → cross-account delivery → lm-log-archive S3

lm-log-archive (112233445566)
  ├── S3 lm-logs-cloudtrail/         [Object Lock: Compliance, 7yr]
  ├── S3 lm-logs-vpc-flow/           [Object Lock: Compliance, 7yr]
  ├── S3 lm-logs-opensearch-snaps/   [Object Lock: Compliance, 7yr]
  └── OpenSearch cluster             [read-only to soc-analyst role]
```

### Immutability Configuration

| Storage | Immutability Mechanism | Retention | Enforcement Level |
| ------- | ---------------------- | --------- | ----------------- |
| `lm-logs-cloudtrail` | S3 Object Lock — **Compliance mode** | 7 years | Cannot be removed by any IAM principal including root; only AWS support can override with AWS account closure |
| `lm-logs-vpc-flow` | S3 Object Lock — **Compliance mode** | 7 years | Same as above |
| `lm-logs-opensearch-snaps` | S3 Object Lock — **Compliance mode** | 7 years | Same as above |
| `lm-audit-reports` | S3 Object Lock — **Governance mode** | 7 years | ISSO can remove with `s3:BypassGovernanceRetention` for legitimate correction — requires CISO approval |
| CloudTrail log file integrity | SHA-256 hash chain (`--enable-log-file-validation`) | 7 years | `aws cloudtrail validate-logs` run monthly; failures trigger P1 alert |

### Access Control for Audit Management Functions

The ability to modify *what gets logged* (audit management) is separate from the ability
to *read* logs. This separation is documented in the Audit Management Access Matrix:

| Function | Authorized Roles | Mechanism |
| -------- | ---------------- | --------- |
| Modify K8s audit policy | ISSO (approval), Platform Engineer (PR author) | GitOps PR + Kyverno `protect-audit-policy` enforcement |
| Modify CloudTrail configuration | ISSO + Cloud Security Engineer (both required) | IAM condition requiring MFA + session tag `approved-by-isso` |
| Modify OpenSearch alert rules | ISSO + SOC Lead (PR review required) | GitOps PR with CODEOWNERS requiring both approvers |
| Read audit logs | SOC analysts, ISSO, CISO, Compliance Officer | OpenSearch `soc-analyst` role + S3 `log-reader` role |
| Delete audit logs | No principal permitted during retention period | S3 Object Lock Compliance mode + SCP |

### Alerting on Audit Integrity Events

The following events trigger immediate P1 alerts to PagerDuty and ISSO email:

| Event | Detection Mechanism | Trigger |
| ----- | ------------------- | ------- |
| CloudTrail stopped or deleted | EventBridge rule on `StopLogging`, `DeleteTrail` | Any outcome, any principal |
| CloudTrail log file validation failure | Monthly `validate-logs` Lambda + ad-hoc check | Any hash mismatch |
| S3 delete attempt on any `lm-logs-*` bucket | EventBridge rule on `DeleteObject`, `DeleteBucket` | Any outcome, any principal |
| K8s audit policy patch attempt (blocked) | Kyverno violation event → OpenSearch alert | Any attempt outside ArgoCD SA |
| Fluent Bit log pipeline gap | CloudWatch metric alarm on `fluentbit_input_records_total` | 0 records for 15 minutes |
| OpenSearch index deletion | OpenSearch audit log → alert rule | Any `DELETE /{index}` on `lm-audit-*` |

All alerts route to PagerDuty service `lm-audit-integrity` (separate from the general
security service) to ensure audit integrity events are never de-prioritized during
an alert storm.

**Responsible Role:** Cloud Security Engineer (S3 Object Lock, SCP, archive account), ISSO (audit management access matrix, alert policy owner), Platform Engineer (Fluent Bit pipeline, K8s audit policy protection)

**Parameters:**
- Log retention: **7 years** (S3 Object Lock — Compliance mode for raw logs)
- Log gap alert threshold: **15 minutes** without Fluent Bit records
- CloudTrail hash validation: **Monthly** (automated Lambda + ad-hoc on investigation)
- Archive account isolation: **AWS Organizations OU-level SCP**

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| S3 Object Lock configuration (`lm-logs-cloudtrail`) | `infra-iac/s3/log-archive-cloudtrail.tf` + AWS CLI: `aws s3api get-object-lock-configuration` | 2026-04-15 |
| SCP `deny-log-deletion` on log archive OU | AWS Organizations console / `infra-iac/organizations/scp-log-archive.tf` | 2026-04-15 |
| CloudTrail log file validation report | S3 `lm-audit-reports/cloudtrail-validation/2026-04.json` | 2026-04-01 |
| Audit Management Access Matrix | Confluence: LM-SECURITY / Audit Management Access Matrix | 2026-04-07 |
| EventBridge rule for log deletion attempts | `infra-iac/monitoring/audit-integrity-alerts.tf` | Per-commit |
| Kyverno `protect-audit-policy` policy | `platform-gitops/kyverno/protect-audit-policy.yaml` | Per-commit |
| PagerDuty service `lm-audit-integrity` config | PagerDuty console | 2026-04-07 |

**Test Procedure:**
1. Verify S3 Object Lock on `lm-logs-cloudtrail`:
   `aws s3api get-object-lock-configuration --bucket lm-logs-cloudtrail`
   — expect `ObjectLockEnabled: Enabled`, `Mode: COMPLIANCE`, `Days >= 2555`.
2. Attempt `aws s3 rm s3://lm-logs-cloudtrail/<object>` using the `lm-athena-query-role`
   — verify `AccessDenied` and confirm an EventBridge alert fires within 60 seconds.
3. Run `aws cloudtrail validate-logs --trail-arn <arn> --start-time <30-days-ago>` —
   verify output contains `"valid": true` for all log files, zero failures.
4. Attempt to patch the K8s audit policy ConfigMap directly as a non-ArgoCD principal —
   verify Kyverno denies the request and a Kyverno violation event appears in OpenSearch.
5. Stop Fluent Bit on one node (`kubectl delete pod <fluent-bit-pod>`) — verify the
   CloudWatch metric alarm fires within 15 minutes and a PagerDuty P2 incident is created.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| AU-9(2) Store on Separate Physical Systems | Implemented | All audit logs delivered to dedicated `lm-log-archive` AWS account (`112233445566`) via cross-account trust. Production workload account (`lm-prod`) has no read, modify, or delete access to the archive account. Separation enforced at AWS Organizations level. |
| AU-9(4) Access by Subset of Privileged Users | Implemented | Audit management functions (modifying what gets logged) are restricted to ISSO + Cloud Security Engineer + Platform Engineer with dual-approval requirements. SOC analysts have read-only access. Audit Management Access Matrix in Confluence documents every management function and its authorized principals. Reviewed quarterly. |

---

## AU-12 — Audit Record Generation

**Implementation Status:** Implemented
**Control Origination:** Hybrid (Inherited from AWS CloudTrail multi-region trail; System-Specific for K8s audit, application logging, NTP, and coverage verification)
**Baseline Allocation:** Low, Moderate, and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Audit Record Generation Coverage

Every event category in the AU-2 Auditable Event List has a verified log source and
generation mechanism. Coverage is verified quarterly by the `audit-coverage-test.sh`
script in `platform-gitops/tools/`, which generates a representative event in each
category and confirms the corresponding log entry appears in OpenSearch within 120 seconds.

| AU-2 Category | Log Source | Generation Mechanism | Region / Scope Coverage |
| ------------- | ---------- | -------------------- | ----------------------- |
| Authentication success/failure | Okta System Log | Okta SCIM integration; automatic for all authentications | Global (Okta SaaS) |
| Privilege use | CloudTrail + K8s audit | CloudTrail: all management events; K8s: `Request` level for privilege verbs | us-east-1, us-west-2 (all active regions) |
| Account lifecycle | Okta System Log + CloudTrail | Okta: SCIM-driven lifecycle events; CloudTrail: IAM CreateUser/DeleteUser/AttachPolicy | Global + both regions |
| Data access | CloudTrail data events | S3 data events enabled for `lm-data-*` buckets; RDS audit log via CloudWatch | us-east-1 (data region only) |
| Configuration change | CloudTrail + K8s audit | All CloudTrail management events; K8s `Request` level for RBAC, Kyverno, ConfigMaps | Both regions; all cluster namespaces |
| Secret access | K8s audit + CloudTrail | K8s `RequestResponse` for secrets; CloudTrail: Secrets Manager `GetSecretValue`, KMS `Decrypt` | Both regions; all namespaces |
| Security tool events | GuardDuty + Falco + K8s events | GuardDuty findings via EventBridge → OpenSearch; Falco via Fluent Bit → OpenSearch | Both regions; all nodes (Falco DaemonSet) |
| Network | VPC Flow Logs | ACCEPT + REJECT; all VPCs in both regions | us-east-1, us-west-2 |
| System health | CloudWatch + Fluent Bit | Container events via kubelet → CloudWatch; node metrics via CloudWatch Agent | All nodes, both regions |
| Application | Links-Matrix API structured log | Application writes to `/lm-audit/access.jsonl`; Fluent Bit tails and ships to OpenSearch | All pod replicas |

### NTP / Time Synchronization

All EKS worker nodes (managed node groups in us-east-1 and us-west-2) use the
AWS Time Sync Service (`169.254.169.123`) as their chrony NTP source. This is
configured in the EKS launch template (`infra-iac/eks/launch-template.tf`) via
a cloud-init script that writes `/etc/chrony.conf` with `server 169.254.169.123 prefer`.

**Clock skew monitoring:** A DaemonSet CronJob (`clock-skew-monitor`, schedule: `0 * * * *`)
runs `chronyc tracking` on every node and writes the `System time offset` value to a
Prometheus gauge `node_clock_skew_seconds`. A Prometheus alert rule fires if any node's
skew exceeds **100 milliseconds** for more than 2 minutes. The alert routes to PagerDuty
P2 and the ISSO Slack DM.

Maximum permitted clock skew: **100 milliseconds** (well within the 500ms threshold
that would cause log sequencing ambiguity across components).

### Log Pipeline Health

Fluent Bit metrics are scraped by Prometheus every 30 seconds:

| Metric | Alert Threshold | Severity | Action |
| ------ | --------------- | -------- | ------ |
| `fluentbit_output_dropped_records_total` | Rate > 0.1% over 5 minutes | P2 | PagerDuty + Platform Engineer on-call |
| `fluentbit_input_records_total` | 0 records for >15 minutes | P2 | PagerDuty (AU-9 gap alert) |
| `fluentbit_output_rejected_records_total` (field validation) | >0 over 10 minutes | P1 | PagerDuty + ISSO — potential AU-3 field completeness breach |

CloudTrail delivery to S3 is monitored by an EventBridge rule that fires if no new
objects are written to `lm-logs-cloudtrail/AWSLogs/` within 20 minutes during
active hours (07:00–22:00 UTC).

### Authorized Verbosity Changes

The ISSO can increase K8s audit log verbosity for investigation purposes by updating
`k8s-audit-policy.yaml` via a GitOps PR (standard path, ~2 minutes for ArgoCD to apply).
For urgent investigations requiring immediate verbosity increase, the Platform Engineer
may apply a temporary patch with ISSO written approval (Slack DM to `#isso-approvals`
channel logged by a Slack workflow bot). Temporary verbosity increases are automatically
reverted after **4 hours** by a cleanup CronJob (`audit-policy-revert`, triggered on
manual activation). Verbosity changes are logged as a Confluence entry in
`LM-SECURITY / Audit Policy Change Log` within 1 hour of activation.

**Responsible Role:** Platform Engineer (K8s audit policy, Fluent Bit, NTP config, coverage testing), Cloud Security Engineer (CloudTrail multi-region, Config, VPC Flow Logs), ISSO (coverage verification ownership, verbosity change approvals)

**Parameters:**
- Multi-region CloudTrail scope: **us-east-1, us-west-2** (all regions with active workloads)
- Maximum permitted NTP clock skew: **100 milliseconds** (alert threshold)
- Log pipeline drop rate alert: **>0.1% over 5 minutes**
- Log stream gap alert: **15 minutes** without records (Fluent Bit); **20 minutes** (CloudTrail)
- Audit coverage test cadence: **Quarterly**
- Temporary verbosity increase auto-revert: **4 hours**

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| CloudTrail multi-region trail config | `infra-iac/cloudtrail/main.tf` + `aws cloudtrail describe-trails` | 2026-04-15 |
| CloudTrail data events config (S3, Secrets Manager, KMS) | `infra-iac/cloudtrail/data-events.tf` | 2026-04-15 |
| K8s audit policy (`k8s-audit-policy.yaml`) | `platform-gitops/config/k8s-audit-policy.yaml` | Per-commit |
| Falco DaemonSet deployment (all nodes) | `platform-gitops/falco/daemonset.yaml` | Per-commit |
| NTP launch template cloud-init config | `infra-iac/eks/launch-template.tf` | Per-commit |
| Clock skew Prometheus alert rule | `platform-gitops/monitoring/prometheus-rules/clock-skew.yaml` | Per-commit |
| Quarterly audit coverage test results | `platform-gitops/security/au12-coverage-YYYY-QQ.md` | 2026-04-07 |
| Fluent Bit drop rate Prometheus alert rule | `platform-gitops/monitoring/prometheus-rules/fluent-bit.yaml` | Per-commit |
| Audit Policy Change Log | Confluence: LM-SECURITY / Audit Policy Change Log | Per-change |

**Test Procedure:**
1. Run `audit-coverage-test.sh` — for each AU-2 event category, generate a test event
   and confirm a corresponding OpenSearch log entry appears within 120 seconds.
   Pass criterion: 100% category coverage. Last passing run: 2026-04-07.
2. Verify multi-region CloudTrail:
   `aws cloudtrail describe-trails --include-shadow-trails`
   — confirm `IsMultiRegionTrail: true` and `IncludeManagementEvents: true` and
   `DataResources` includes `lm-data-*` S3 buckets.
3. Verify NTP sync on a sample of 3 nodes:
   `kubectl exec -n kube-system <clock-skew-monitor-pod> -- chronyc tracking`
   — confirm `System time offset` <100ms on all sampled nodes.
4. Verify Fluent Bit is running on all nodes:
   `kubectl get daemonset fluent-bit -n logging -o jsonpath='{.status.numberReady}'`
   — confirm value equals `{.status.desiredNumberScheduled}`.
5. Verify Falco is running on all nodes:
   `kubectl get daemonset falco -n falco -o jsonpath='{.status.numberReady}'`
   — confirm value equals `{.status.desiredNumberScheduled}`.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| AU-12(1) System-Wide and Time-Correlated Audit Trail | Implemented | All components synchronized to AWS Time Sync Service via chrony. Clock skew monitored continuously with Prometheus; alert fires at >100ms. Fluent Bit aggregates all component logs into OpenSearch with a unified `@timestamp` field (UTC ISO 8601) enabling cross-component timeline reconstruction. |
| AU-12(3) Changes by Authorized Individuals | Implemented | ISSO can increase K8s audit verbosity via GitOps PR (standard, ~2 min) or via Platform Engineer emergency patch with ISSO Slack approval (immediate). Temporary increases auto-revert after 4 hours. All changes logged in Confluence `Audit Policy Change Log` within 1 hour. |

---

## What Makes This GREAT — Full Side-by-Side

| Dimension | Bad | Good | Great |
| --------- | --- | ---- | ----- |
| **AU-2 event list** | "Important system events" (no list) | 5 categories described in prose | 11-row table with category, required events, log source, and K8s audit level |
| **AU-3 field requirements** | "Relevant details" | Field list described per source | Structured field schema table mapping each required field across 4 log sources; Fluent Bit enforces fields at pipeline — rejections alert immediately |
| **AU-6 review** | "When there is a concern" | SOC cadence defined, 7 alert rules | 10 named alert rules in a table with severity and notification path; 4 cross-source correlation rules named and tested; monthly ISSO report with distribution and archive location |
| **AU-7 immutability** | Not mentioned | Read-only access mentioned | Three-layer write protection (S3 policy + IAM + SCP); automated weekly OpenSearch role audit; test procedure proves write is blocked |
| **AU-9 log protection** | "Stored securely" | Separate account + Object Lock named | Architecture diagram, immutability table per bucket with mode and retention, Audit Management Access Matrix, 6-rule integrity alerting table on separate PagerDuty service |
| **AU-12 coverage** | "Records are generated" | Component coverage table, NTP mentioned | Quarterly automated coverage test script; per-metric Fluent Bit health table; NTP clock skew Prometheus alert at 100ms; Falco DaemonSet coverage verified |
| **Control chain** | Never acknowledged | Acknowledged in intro | Explicitly documented in SSP header — AU-2→AU-3→AU-12→AU-6→AU-7 with AU-9 as the protection wrapper |
| **Test procedures** | None | None | Every control has a numbered test procedure with expected result — a 3PAO can run them without clarification |
| **Enhancement coverage** | None or "some are implemented" | Partial — 2 gaps with "planned" notes | Every enhancement: implemented with specifics OR explicitly N/A with ADR reference |
| **Evidence tables** | "Policy document" | Artifact described by name | Every artifact: what it is, exact location (S3 path, Confluence page, Terraform file), and last verified date |
