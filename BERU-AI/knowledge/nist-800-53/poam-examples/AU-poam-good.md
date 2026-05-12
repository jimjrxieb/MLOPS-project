# POA&M — Audit and Accountability (AU) Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** POA&M items reflect specific evidence gaps from the BERU assessment.
> Control owners are identified by role. Due dates follow severity-based priority tiers.
> Milestones cover M1 and M2 with actionable steps. Validation commands are real tool queries.
> Residual risk is acknowledged but remains generic. Status history includes opening reason.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** AU-ra-bad.md
**Prepared By:** GRC Engineer
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-006 | AU-2 — Event Logging | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-007 | AU-3 — Content of Audit Records | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-008 | AU-6 — Audit Record Review, Analysis, and Reporting | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-009 | AU-7 — Audit Record Reduction and Report Generation | High | P2 30 Days | 2026-06-09 |
| POAM-2026-05-010 | AU-9 — Protection of Audit Information | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-011 | AU-11 — Audit Record Retention | High | P2 30 Days | 2026-06-09 |
| POAM-2026-05-012 | AU-12 — Audit Record Generation | Critical | P1 Immediate | 2026-05-17 |

---

## POAM-2026-05-006 — AU-2

```text
POAM-ID:          POAM-2026-05-006
CONTROL:          AU-2 — Event Logging

WEAKNESS:
  No event category list produced. CloudTrail trail configuration not retrievable — management
  events, data events, and Insight events are unverified. No alert rules tied to event categories.
  No annual AU-2 event category review artifact — SecEng verbal statement only.

SYSTEM AFFECTED:  AWS CloudTrail / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AU-2?env=bad → cloudtrail, status: insufficient,
                  auditable_event_categories: [], data_events_enabled: false,
                  insight_events_enabled: false. SecEng interview: no artifacts produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AU-2-2026-05-10/

REMEDIATION OWNER: ISSO (accountability) / SecEng (evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Enable CloudTrail management events, S3 data events, and Insight events;
                  confirm trail configuration retrievable and all categories captured.
  M2: 2026-05-15  Produce AU-2 event category list in Confluence; create CloudWatch alert rules
                  for each defined category; obtain ISSO sign-off on the annual review artifact.

REMEDIATION APPROACH:
  Enable CloudTrail management events (Read + Write) and S3 data events in us-east-1.
  Enable CloudTrail Insights to detect unusual API activity. Run a test management event
  (e.g., CreateBucket) and confirm it appears in the trail. Produce an event category list
  in Confluence that maps each required audit event to its CloudTrail source. Create
  CloudWatch metric filters and alarms for each category. ISSO conducts and signs the
  annual AU-2 event category review. Store all artifacts in the evidence path.

VALIDATION COMMAND:
  aws cloudtrail describe-trails --query 'trailList[*].HasCustomEventSelectors'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — CloudTrail configuration not retrievable; no event categories confirmed;
             no alert rules; no annual review artifact.
```

---

## POAM-2026-05-007 — AU-3

```text
POAM-ID:          POAM-2026-05-007
CONTROL:          AU-3 — Content of Audit Records

WEAKNESS:
  CloudTrail audit records missing 4 required fields: eventTime, userIdentity, sourceIPAddress,
  requestParameters. No sample record available — CloudTrail not delivering to accessible S3
  bucket. No platform logging standard document produced.

SYSTEM AFFECTED:  AWS CloudTrail / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AU-3?env=bad → cloudtrail, status: insufficient,
                  required_fields_present: false, missing_fields: [eventTime, userIdentity,
                  sourceIPAddress, requestParameters], sample_record: null.
                  PlatEng interview: no sample record or logging standard produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AU-3-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Configure CloudTrail to deliver logs to an S3 bucket accessible to the
                  grc-engineer IAM group; confirm all 8 required fields appear in a sample record.
  M2: 2026-05-15  Produce the platform logging standard document specifying all required
                  NIST AU-3 fields; store a sample record and the standard in the evidence path.

REMEDIATION APPROACH:
  Configure CloudTrail to deliver event records to an S3 bucket. Verify the IAM policy on the
  bucket grants read access to the grc-engineer group. Run a test API call and retrieve the
  resulting event record. Confirm all required fields are present: eventTime, eventSource,
  eventName, userIdentity, sourceIPAddress, requestParameters, responseElements, awsRegion.
  Produce the platform logging standard document in Confluence listing each required field and
  its source. Export a sample record JSON as the evidence artifact.

VALIDATION COMMAND:
  aws cloudtrail describe-trails --query 'trailList[*].HasCustomEventSelectors'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — 4 required fields missing; sample record not available; logging standard
             not produced.
```

---

## POAM-2026-05-008 — AU-6

```text
POAM-ID:          POAM-2026-05-008
CONTROL:          AU-6 — Audit Record Review, Analysis, and Reporting

WEAKNESS:
  Splunk gp_security index not found or empty. Zero active alert rules for AU-6. Zero log
  review records in 90 days. No monthly audit report artifact produced. SOC verbal statement
  only — no triage records and no report distribution evidence.

SYSTEM AFFECTED:  Splunk / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AU-6?env=bad → splunk, status: insufficient,
                  log_review_records_90d: 0, alert_rules_active: 0, last_review: null,
                  error: "Splunk index gp_security not found or empty".
                  SOC interview: no alert rules, no triage records, no monthly report artifact.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AU-6-2026-05-10/

REMEDIATION OWNER: SOC (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Create the gp_security Splunk index and ingest CloudTrail and Kubernetes
                  audit events; confirm index is non-empty with at least 24 hours of data.
  M2: 2026-05-15  Create and activate a minimum of 3 AU-6 alert rules in Splunk; produce the
                  first monthly audit review report and distribute to ISSO and CISO; store
                  artifact in the evidence path.

REMEDIATION APPROACH:
  Create the gp_security index in Splunk and configure the CloudTrail S3 input to ingest
  log data. Add Kubernetes API server audit log ingestion via the Splunk Kubernetes app.
  Confirm events are appearing in the index. Create correlation rules mapped to AU-6 event
  categories (e.g., unauthorized API call, privilege escalation, account modification).
  Configure a scheduled saved search to generate a monthly report and email it to the ISSO
  and CISO distribution list. Store the first report in the evidence path.

VALIDATION COMMAND:
  curl -sk https://localhost:8089/services/saved/searches -u admin:<pass> | grep -c "AU-6"

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Splunk gp_security index not found; 0 alert rules; 0 review records;
             no monthly report. SOC verbal only.
```

---

## POAM-2026-05-009 — AU-7

```text
POAM-ID:          POAM-2026-05-009
CONTROL:          AU-7 — Audit Record Reduction and Report Generation

WEAKNESS:
  Zero Splunk reports generated in 90 days. No scheduled report artifact found. No recipient
  list configured. Splunk reporting is not operational. SOC verbal statement that reports are
  generated "when needed" — no scheduled artifact, no distribution evidence.

SYSTEM AFFECTED:  Splunk / Links-Matrix

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AU-7?env=bad → splunk, status: insufficient,
                  reports_generated_90d: 0, scheduled_report_artifact: null,
                  error: "No scheduled reports found in Splunk".
                  SOC interview: no reports produced on demand or on schedule.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AU-7-2026-05-10/

REMEDIATION OWNER: SOC (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-06-09

MILESTONES:
  M1: 2026-05-25  Configure at least one scheduled Splunk saved search to produce a monthly
                  audit reduction report; confirm the search runs and produces output.
  M2: 2026-06-02  Configure recipient list and test automated email delivery of the monthly
                  report to ISSO and CISO; store a generated report artifact in the evidence
                  path.

REMEDIATION APPROACH:
  In Splunk, create a saved search that reduces raw audit events into a summary report
  showing event counts by category, alert rule triggers, and anomaly flags. Schedule the
  search to run on the first of each month. Configure the report to be emailed to the ISSO
  and CISO in PDF format with a dashboard link. Confirm the first automated execution
  produces output. Store the first report PDF in the evidence path. Update the SSP AU-7
  implementation statement to reference the Splunk saved search name and schedule.

VALIDATION COMMAND:
  curl -sk https://localhost:8089/services/saved/searches -u admin:<pass> | grep -c "AU-7"

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — 0 Splunk reports in 90 days; no scheduled report configured; no recipient
             list; SOC verbal statement only.
```

---

## POAM-2026-05-010 — AU-9

```text
POAM-ID:          POAM-2026-05-010
CONTROL:          AU-9 — Protection of Audit Information

WEAKNESS:
  Falco not deployed — zero audit log tamper detection rules active. S3 Object Lock status
  unconfirmed — PlatEng could not verify whether the CloudTrail delivery bucket has Object
  Lock enabled. MFA delete status on the log archive bucket is unknown.

SYSTEM AFFECTED:  Falco / AWS S3 / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AU-9?env=bad → falco, status: insufficient,
                  log_tamper_rules_active: 0, immutable_log_config: null,
                  error: "Falco not deployed".
                  PlatEng interview: Object Lock and MFA delete unverified.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AU-9-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Deploy Falco via Helm to the Links-Matrix cluster; confirm the tamper
                  detection rules for log modification and deletion are active.
  M2: 2026-05-15  Confirm S3 Object Lock is enabled on the CloudTrail delivery bucket;
                  confirm MFA delete is enabled on the log archive bucket; export S3
                  configuration as evidence artifact.

REMEDIATION APPROACH:
  Deploy Falco to the Links-Matrix cluster using the official Helm chart. Confirm the Falco
  DaemonSet is running and the tamper detection rules (file modified, log deleted) are active.
  Test by attempting a log modification and confirming Falco generates an alert. In AWS S3,
  navigate to the CloudTrail delivery bucket and confirm Object Lock is enabled in Compliance
  mode. Navigate to the log archive bucket and confirm MFA delete is enabled. Export the
  S3 bucket configuration for both buckets as JSON and store in the evidence path.

VALIDATION COMMAND:
  kubectl -n monitoring get daemonset falco -o jsonpath='{.status.numberReady}'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Falco not deployed; 0 tamper detection rules; S3 Object Lock unconfirmed;
             MFA delete status unknown. PlatEng verbal only.
```

---

## POAM-2026-05-011 — AU-11

```text
POAM-ID:          POAM-2026-05-011
CONTROL:          AU-11 — Audit Record Retention

WEAKNESS:
  No S3 lifecycle policy artifact produced for CloudTrail log retention. Retention period is
  undocumented — no Confluence policy states the required 3-year retention for FedRAMP Moderate.
  No evidence that logs older than 90 days are still accessible or stored in the trail bucket.

SYSTEM AFFECTED:  AWS S3 / AWS CloudTrail / Links-Matrix

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AU-11?env=bad → cloudtrail, status: insufficient,
                  retention_policy_days: null, lifecycle_policy_artifact: null,
                  error: "Retention configuration not documented". PlatEng interview: no
                  S3 lifecycle policy or retention policy document produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AU-11-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-06-09

MILESTONES:
  M1: 2026-05-25  Apply an S3 lifecycle policy to the CloudTrail delivery bucket setting
                  transition to Glacier at 90 days and expiration at 1,095 days (3 years);
                  export the lifecycle configuration JSON to the evidence path.
  M2: 2026-06-02  Produce the audit record retention policy document in Confluence specifying
                  the 3-year retention requirement; obtain ISSO sign-off; link from evidence
                  path.

REMEDIATION APPROACH:
  In AWS S3, navigate to the CloudTrail delivery bucket. Add a lifecycle policy that
  transitions objects to Glacier after 90 days and permanently expires them after 1,095 days.
  Apply the same policy to the log archive bucket. Export the lifecycle configuration JSON
  using aws s3api get-bucket-lifecycle-configuration. Produce the AU-11 retention policy
  document in Confluence specifying the 3-year retention period, storage tiers, and
  exception handling for legal hold scenarios. ISSO reviews and signs. Store all artifacts
  in the evidence path.

VALIDATION COMMAND:
  aws cloudtrail describe-trails --query 'trailList[*].HasCustomEventSelectors'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — No S3 lifecycle policy; retention period undocumented; no Confluence
             retention policy. PlatEng verbal only.
```

---

## POAM-2026-05-012 — AU-12

```text
POAM-ID:          POAM-2026-05-012
CONTROL:          AU-12 — Audit Record Generation

WEAKNESS:
  Falco not deployed — zero event generation rules active. Kubernetes audit logging status
  unconfirmed. No evidence that AU-2 defined event categories are being generated at the
  runtime layer. PlatEng verbal claim that CloudTrail covers it — no rule count or K8s
  audit log confirmation produced.

SYSTEM AFFECTED:  Falco / Kubernetes / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AU-12?env=bad → falco, status: insufficient,
                  event_generation_rules: 0, k8s_audit_log_enabled: null,
                  error: "Falco not deployed". PlatEng interview: no rule count or K8s
                  audit log artifact produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AU-12-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Deploy Falco via Helm; confirm event generation rules are active and
                  generating records for at least the syscall and Kubernetes API event
                  categories defined in AU-2.
  M2: 2026-05-15  Enable Kubernetes audit logging on the Links-Matrix cluster API server;
                  confirm audit log events are captured and forwarded to Splunk gp_security
                  index; export rule list as evidence artifact.

REMEDIATION APPROACH:
  Deploy Falco to the Links-Matrix cluster via Helm. Confirm the DaemonSet is running on
  all nodes. Verify the active rule list covers the event categories defined in AU-2:
  syscalls, Kubernetes API events, network activity, file integrity, and process activity.
  Enable Kubernetes API server audit logging by adding the --audit-log-path and
  --audit-policy-file flags to the kube-apiserver configuration. Forward the audit log to
  Splunk via the Kubernetes Audit Events input. Export the Falco rule list and K8s audit
  policy YAML as evidence artifacts and store in the evidence path.

VALIDATION COMMAND:
  kubectl -n monitoring logs ds/falco --tail=5 | grep -c "rule="

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Falco not deployed; 0 event generation rules; K8s audit log status
             unconfirmed; no coverage evidence for AU-2 event categories.
```
