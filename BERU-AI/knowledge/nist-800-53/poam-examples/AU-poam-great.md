# POA&M — Audit and Accountability (AU) Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Auditor-ready POA&M. All deficiencies are numbered within each weakness.
> Remediation owners are split between evidence producer and sign-off authority. Due dates
> follow severity-based priority tiers. Milestones include M1, M2, and M3 with exact dated
> actions. Validation commands include expected output. Residual risk identifies the specific
> remaining gap after remediation. Status history shows full progression from OPEN to CLOSED.

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
  Three deficiencies identified on Links-Matrix (AWS CloudTrail):
  (1) CloudTrail trail configuration not retrievable — management_events_enabled: null,
      data_events_enabled: false, insight_events_enabled: false; auditable_event_categories
      returned empty list over 90-day lookback window.
  (2) No alert rules produced tied to defined event categories — SecEng verbal statement
      only; SOC could not confirm any CloudWatch alarms mapped to AU-2 event categories.
  (3) No annual AU-2 event category review artifact — ISSO stated the review "happened a
      while back" but no Confluence page, no reviewer sign-off, no date was produced.

SYSTEM AFFECTED:  Links-Matrix (AWS CloudTrail, CloudWatch, Confluence)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AU-2?env=bad → tool: cloudtrail, status: insufficient,
                  management_events_enabled: null, data_events_enabled: false,
                  insight_events_enabled: false, auditable_event_categories: [],
                  error: "Trail configuration not retrievable".
                  SecEng interview: no event category list, no alert rules, no annual review
                  artifact produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AU-2-2026-05-10/AU-2-finding.json

REMEDIATION OWNER: SecEng (event category list and alert rules producer) / ISSO (annual review sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Enable CloudTrail management events (Read + Write), S3 data events, and
                  Insight events in us-east-1; run a test CreateBucket API call and confirm
                  the event appears in the trail within 5 minutes; export trail configuration
                  JSON to evidence path.
  M2: 2026-05-14  Produce the AU-2 event category list in Confluence mapping each required
                  audit event to its CloudTrail source; create CloudWatch metric filters and
                  alarms for each defined category; confirm all alarms transition to OK state
                  with a test event.
  M3: 2026-05-16  Conduct ISSO-signed annual AU-2 event category review; store artifact in
                  Confluence at AU-2-Annual-Review-2026 page; link from evidence path.

REMEDIATION APPROACH:
  Step 1: In AWS CloudTrail console, edit the trail event selectors. Enable Management Events
  (Read and Write), S3 Data Events (All buckets), and CloudTrail Insights. Confirm with:
    aws cloudtrail describe-trails --query 'trailList[*].HasCustomEventSelectors'
  Step 2: In Confluence, produce the AU-2 event category list table mapping each NIST-required
  event category to the specific CloudTrail event names that satisfy it (e.g., IAM changes →
  CreateUser, DeleteUser, AttachUserPolicy). For each category, create a CloudWatch metric
  filter on the CloudTrail log group and attach an SNS alarm.
  Step 3: ISSO reviews the event category list and the 90-day CloudTrail coverage and signs
  the annual review record. Store the signed PDF in the evidence path.

VALIDATION COMMAND:
  aws cloudtrail describe-trails --query 'trailList[*].HasCustomEventSelectors'
  Expected output: [true]

RESIDUAL RISK AFTER REMEDIATION:
  CloudTrail does not capture Kubernetes API server events natively — runtime-layer events
  (container exec, pod deletion) depend on AU-12 Falco deployment. Residual risk: Low pending
  AU-12 closure.

STATUS HISTORY:
  2026-05-10 OPEN — Trail configuration not retrievable. management_events_enabled: null.
             data_events_enabled: false. insight_events_enabled: false.
             No event category list. No alert rules. No annual review artifact.
  2026-05-12 IN PROGRESS — M1 complete: CloudTrail management, S3 data, and Insight events
             enabled. Test CreateBucket event confirmed in trail within 3 minutes.
             Trail configuration JSON exported to evidence path.
  2026-05-14 IN PROGRESS — M2 complete: AU-2 event category list published in Confluence.
             12 CloudWatch alarms created — all transitioned to OK on test events.
  2026-05-16 IN PROGRESS — M3 complete: ISSO-signed annual review stored in Confluence
             (link: <confluence-url>/pages/AU-2-Annual-Review-2026).
  2026-05-17 CLOSED — BERU re-ran GET /evidence/AU-2?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-007 — AU-3

```text
POAM-ID:          POAM-2026-05-007
CONTROL:          AU-3 — Content of Audit Records

WEAKNESS:
  Three deficiencies identified on Links-Matrix (AWS CloudTrail):
  (1) Four required NIST AU-3 fields confirmed missing from CloudTrail records:
      eventTime, userIdentity, sourceIPAddress, requestParameters —
      required_fields_present: false per tool query.
  (2) No sample record available — CloudTrail not delivering to an S3 bucket accessible
      to the grc-engineer IAM group; sample_record: null.
  (3) No platform logging standard document produced — PlatEng could not provide a
      Confluence link or any artifact specifying which fields are required and why.

SYSTEM AFFECTED:  Links-Matrix (AWS CloudTrail, S3 log delivery bucket)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AU-3?env=bad → tool: cloudtrail, status: insufficient,
                  required_fields_present: false, missing_fields: [eventTime, userIdentity,
                  sourceIPAddress, requestParameters], sample_record: null,
                  error: "Sample record not available — CloudTrail not delivering to
                  accessible S3 bucket". PlatEng interview: no sample record or logging
                  standard produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AU-3-2026-05-10/AU-3-finding.json

REMEDIATION OWNER: PlatEng (CloudTrail delivery and logging standard producer) / SecEng (evidence sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Configure CloudTrail to deliver logs to an S3 bucket with a bucket policy
                  granting read access to the grc-engineer IAM group; run a test API call
                  and confirm the resulting event record appears in the bucket within 15
                  minutes with all 8 required fields populated.
  M2: 2026-05-14  Produce the platform logging standard document in Confluence specifying
                  all 8 required NIST AU-3 fields, their source (CloudTrail attribute name),
                  and the validation method; store the document link in the evidence path.
  M3: 2026-05-16  Export a sample CloudTrail event record (JSON) from the delivery bucket
                  that demonstrates all 8 required fields; SecEng signs off that the record
                  meets the logging standard; store in evidence path.

REMEDIATION APPROACH:
  Step 1: In AWS CloudTrail, confirm the trail has an S3 destination. If the delivery bucket
  lacks grc-engineer read access, add the following bucket policy statement:
    {"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::<acct>:group/grc-engineer"},
     "Action":"s3:GetObject","Resource":"arn:aws:s3:::<bucket>/AWSLogs/*"}
  Step 2: Run a test API call (e.g., aws s3 ls) and wait 15 minutes. Retrieve the event
  record and confirm all 8 fields are present: eventVersion, userIdentity, eventTime,
  eventSource, eventName, awsRegion, sourceIPAddress, requestParameters.
  Step 3: Produce the platform logging standard in Confluence. For each required field,
  document: field name, NIST requirement it satisfies, CloudTrail attribute name, and
  example value. Have PlatEng and SecEng review and sign.

VALIDATION COMMAND:
  aws cloudtrail describe-trails --query 'trailList[*].HasCustomEventSelectors'
  Expected output: [true]

RESIDUAL RISK AFTER REMEDIATION:
  CloudTrail captures AWS API events only — host-level and container-level audit record
  fields (process name, container ID) are not available without Falco (AU-12). Residual
  risk: Low pending AU-12 closure.

STATUS HISTORY:
  2026-05-10 OPEN — required_fields_present: false. 4 fields missing (eventTime,
             userIdentity, sourceIPAddress, requestParameters). sample_record: null.
             No logging standard document. PlatEng verbal only.
  2026-05-12 IN PROGRESS — M1 complete: CloudTrail delivery bucket reconfigured with
             grc-engineer read policy. Test event retrieved — all 8 fields confirmed present.
  2026-05-14 IN PROGRESS — M2 complete: Platform logging standard published in Confluence.
             8 fields documented with NIST mapping and example values.
  2026-05-16 IN PROGRESS — M3 complete: Sample record (JSON) exported and signed by SecEng.
             Stored in evidence path.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/AU-3?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-008 — AU-6

```text
POAM-ID:          POAM-2026-05-008
CONTROL:          AU-6 — Audit Record Review, Analysis, and Reporting

WEAKNESS:
  Four deficiencies identified on Links-Matrix (Splunk):
  (1) Splunk gp_security index not found or empty — log_review_records_90d: 0; no CloudTrail
      or Kubernetes events are being ingested.
  (2) Zero active alert rules for AU-6 — no correlation rules, no triggered alerts, no
      escalation path documented.
  (3) Zero log review or triage records in 90 days — SOC verbal claim only; no triage ticket,
      no review log, no evidence of any human review activity.
  (4) No monthly audit report artifact produced — no PDF, no dashboard link, no distribution
      list; ISSO and CISO have not received an audit review report in the assessment period.

SYSTEM AFFECTED:  Links-Matrix (Splunk, gp_security index)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AU-6?env=bad → tool: splunk, status: insufficient,
                  log_review_records_90d: 0, alert_rules_active: 0, last_review: null,
                  error: "Splunk index gp_security not found or empty".
                  SOC interview: no alert rules, no triage records, no monthly report
                  artifact produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AU-6-2026-05-10/AU-6-finding.json

REMEDIATION OWNER: SOC (index creation, alert rules, and triage record producer) / ISSO (monthly report sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Create the gp_security Splunk index; configure the CloudTrail S3 input
                  and the Kubernetes audit log input; confirm the index contains at least
                  24 hours of events; export index stats to evidence path.
  M2: 2026-05-14  Create and activate a minimum of 3 AU-6 correlation rules (unauthorized
                  API call, privilege escalation attempt, account modification); test each
                  rule by generating the triggering event and confirming an alert fires;
                  document the escalation path in Confluence.
  M3: 2026-05-16  Produce the first monthly audit review report from the gp_security index;
                  distribute to ISSO and CISO via scheduled saved search email; store PDF
                  artifact in evidence path; ISSO signs as reviewer.

REMEDIATION APPROACH:
  Step 1: In Splunk, create the gp_security index (Settings → Indexes → New Index, name:
  gp_security, max size: 100GB). Add a Splunk S3 input pointing to the CloudTrail delivery
  bucket. Add the Kubernetes Audit Events Splunk add-on to ingest K8s API server audit logs.
  Confirm events appear: index=gp_security | head 10.
  Step 2: Create three saved searches as alert rules:
    - AU-6-Unauthorized-API: index=gp_security errorCode="AccessDenied" | alert on >5 in 5m
    - AU-6-Privilege-Escalation: index=gp_security eventName IN (CreatePolicy,AttachUserPolicy) | alert on any
    - AU-6-Account-Modification: index=gp_security eventName IN (CreateUser,DeleteUser) | alert on any
  Set each alert to trigger a webhook to the SOC ticketing system. Document the escalation
  path: SOC analyst → SOC lead → ISSO (P1 findings).
  Step 3: Create a scheduled saved search that summarizes the past 30 days of gp_security
  events by category, alert count, and disposition. Schedule to run on the 1st of each month
  and email a PDF to the ISSO and CISO distribution list.

VALIDATION COMMAND:
  curl -sk https://localhost:8089/services/saved/searches -u admin:<pass> | grep -c "AU-6"
  Expected output: 1

RESIDUAL RISK AFTER REMEDIATION:
  gp_security index currently covers CloudTrail and Kubernetes API events only — Falco
  runtime events are not ingested until AU-12 Falco deployment is complete. Monthly
  report coverage will be partial until then. Residual risk: Low pending AU-12 closure.

STATUS HISTORY:
  2026-05-10 OPEN — gp_security index not found. alert_rules_active: 0.
             log_review_records_90d: 0. No monthly report. SOC verbal only.
  2026-05-12 IN PROGRESS — M1 complete: gp_security index created. CloudTrail and K8s
             inputs configured. Index confirmed non-empty (48h of events).
  2026-05-14 IN PROGRESS — M2 complete: 3 AU-6 alert rules active. All 3 test events
             triggered alerts successfully. Escalation path documented in Confluence.
  2026-05-16 IN PROGRESS — M3 complete: First monthly report generated (30-day coverage).
             Distributed to ISSO and CISO. ISSO signed as reviewer. PDF stored in evidence
             path.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/AU-6?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-009 — AU-7

```text
POAM-ID:          POAM-2026-05-009
CONTROL:          AU-7 — Audit Record Reduction and Report Generation

WEAKNESS:
  Three deficiencies identified on Links-Matrix (Splunk):
  (1) Zero Splunk reports generated in 90 days — reports_generated_90d: 0; no on-demand
      or scheduled report has been produced in the assessment window.
  (2) No scheduled report artifact — scheduled_report_artifact: null; no saved search
      is configured to produce a recurring report; Splunk reporting is not operational.
  (3) No recipient list configured — no evidence that ISSO, CISO, or SOC Lead receive
      any scheduled audit reduction output; SOC verbal claim that reports are produced
      "when needed" is unverifiable.

SYSTEM AFFECTED:  Links-Matrix (Splunk)

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AU-7?env=bad → tool: splunk, status: insufficient,
                  reports_generated_90d: 0, scheduled_report_artifact: null,
                  error: "No scheduled reports found in Splunk".
                  SOC interview: no report produced on demand or on schedule.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AU-7-2026-05-10/AU-7-finding.json

REMEDIATION OWNER: SOC (scheduled report configuration and producer) / ISSO (report recipient and sign-off)

SCHEDULED COMPLETION: 2026-06-09

MILESTONES:
  M1: 2026-05-25  Configure an AU-7 Splunk saved search that reduces raw gp_security events
                  into a monthly summary report (event count by category, top 10 source IPs,
                  alert rule triggers, anomaly flags); confirm the search runs on demand and
                  produces non-empty output.
  M2: 2026-06-02  Schedule the saved search to run on the 1st of each month; configure the
                  Splunk email action to deliver a PDF report to the ISSO, CISO, and SOC Lead
                  distribution list; execute the first scheduled run and confirm email delivery.
  M3: 2026-06-06  Store the first generated report PDF in the evidence path; ISSO signs as
                  the authorized reviewer; update the SSP AU-7 implementation statement to
                  reference the Splunk saved search name, schedule, and recipient list.

REMEDIATION APPROACH:
  Step 1: In Splunk, create a new saved search named "AU-7-Monthly-Audit-Report":
    index=gp_security earliest=-30d@d latest=@d
    | stats count by eventName, sourceIPAddress, alert_rule
    | sort -count
  Run the search on demand and confirm it returns results from the gp_security index.
  Step 2: Edit the saved search schedule: run every month on the 1st at 06:00 UTC.
  Enable the email action: send PDF to isso@links-matrix.com, ciso@links-matrix.com,
  soc-lead@links-matrix.com. Subject: "AU-7 Monthly Audit Reduction Report — {date}".
  Step 3: Wait for the first scheduled run (or trigger manually). Download the generated PDF.
  ISSO reviews the report content and confirms it satisfies the AU-7 requirement for audit
  record reduction and report generation. ISSO signs the artifact and stores it in the
  evidence path. Update the SSP AU-7 section.

VALIDATION COMMAND:
  curl -sk https://localhost:8089/services/saved/searches -u admin:<pass> | grep -c "AU-7"
  Expected output: 1

RESIDUAL RISK AFTER REMEDIATION:
  Splunk report covers events from the gp_security index only — Falco runtime events are
  excluded until AU-12 is closed. The monthly cadence also means intra-month anomalies are
  not summarized until the next scheduled run. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — reports_generated_90d: 0. scheduled_report_artifact: null.
             No recipient list. SOC verbal claim only.
  2026-05-25 IN PROGRESS — M1 complete: AU-7-Monthly-Audit-Report saved search created.
             On-demand run produced 847 events across 12 categories. Output confirmed.
  2026-06-02 IN PROGRESS — M2 complete: Report scheduled for 1st of each month at 06:00 UTC.
             Email action confirmed: delivery to ISSO, CISO, SOC Lead tested and received.
  2026-06-06 IN PROGRESS — M3 complete: First report PDF stored in evidence path. ISSO signed
             as reviewer. SSP AU-7 statement updated with saved search name and schedule.
  2026-06-09 CLOSED — BERU re-ran GET /evidence/AU-7?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-010 — AU-9

```text
POAM-ID:          POAM-2026-05-010
CONTROL:          AU-9 — Protection of Audit Information

WEAKNESS:
  Three deficiencies identified on Links-Matrix (Falco / AWS S3):
  (1) Falco not deployed — log_tamper_rules_active: 0; zero runtime tamper detection rules
      are active; no alert fires if audit logs are modified or deleted.
  (2) S3 Object Lock status unconfirmed — immutable_log_config: null; PlatEng could not
      verify whether the CloudTrail delivery bucket has Object Lock enabled in Compliance
      mode; SSP claim is unverified.
  (3) MFA delete status on log archive bucket unknown — PlatEng verbal "I'd have to check";
      no aws s3api output or S3 console screenshot produced.

SYSTEM AFFECTED:  Links-Matrix (Falco DaemonSet, AWS S3 CloudTrail delivery bucket, S3 log archive bucket)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AU-9?env=bad → tool: falco, status: insufficient,
                  log_tamper_rules_active: 0, immutable_log_config: null,
                  error: "Falco not deployed".
                  PlatEng interview: Object Lock and MFA delete status unverified;
                  no S3 configuration artifact produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AU-9-2026-05-10/AU-9-finding.json

REMEDIATION OWNER: PlatEng (Falco deployment and S3 configuration producer) / SecEng (evidence sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Deploy Falco via Helm to the Links-Matrix cluster in the monitoring
                  namespace; confirm the DaemonSet is running on all nodes; verify the
                  tamper detection rules (write_below_root, modify_shell_config_file,
                  delete_audit_logs) are active and generating events.
  M2: 2026-05-14  Confirm S3 Object Lock is enabled in Compliance mode on the CloudTrail
                  delivery bucket; confirm MFA delete is enabled on the log archive bucket;
                  export both bucket configurations as JSON to the evidence path.
  M3: 2026-05-16  Test Falco tamper detection: attempt to modify a log file inside the
                  Falco container and confirm an alert fires; export the Falco alert JSON
                  as a test artifact; SecEng signs off on all AU-9 evidence.

REMEDIATION APPROACH:
  Step 1: helm repo add falcosecurity https://falcosecurity.github.io/charts && helm install
  falco falcosecurity/falco --namespace monitoring --create-namespace \
  --set falco.grpc.enabled=true --set falcosidekick.enabled=true. Confirm:
    kubectl -n monitoring get daemonset falco
  Verify log tamper rules are loaded:
    kubectl -n monitoring exec ds/falco -- falco --list | grep -i "log\|audit\|tamper"
  Step 2: In AWS S3, navigate to the CloudTrail delivery bucket → Properties → Object Lock.
  Confirm it is enabled in Compliance mode with a 3-year retention period. Navigate to the
  log archive bucket → Properties → Versioning → confirm MFA delete is enabled. Export:
    aws s3api get-object-lock-configuration --bucket <cloudtrail-bucket>
    aws s3api get-bucket-versioning --bucket <archive-bucket>
  Store both JSON outputs in the evidence path.
  Step 3: Simulate a tamper event: exec into a pod and attempt to write to /var/log. Confirm
  Falco generates an alert with rule name in the output. Export the alert JSON.

VALIDATION COMMAND:
  kubectl -n monitoring get daemonset falco -o jsonpath='{.status.numberReady}'
  Expected output: 3

RESIDUAL RISK AFTER REMEDIATION:
  Falco tamper detection covers the Kubernetes runtime layer — audit logs stored in S3 after
  delivery are protected by Object Lock, but direct AWS API calls that bypass the S3 bucket
  policy (e.g., by a root user) are not blocked by Falco. CloudTrail alerts cover this
  gap partially. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Falco not deployed. log_tamper_rules_active: 0. S3 Object Lock
             status: unconfirmed. MFA delete status: unknown. PlatEng verbal only.
  2026-05-12 IN PROGRESS — M1 complete: Falco deployed to monitoring namespace.
             DaemonSet running on 3 nodes. Tamper detection rules confirmed active
             (write_below_root, modify_shell_config_file loaded).
  2026-05-14 IN PROGRESS — M2 complete: S3 Object Lock confirmed (Compliance mode, 3yr).
             MFA delete confirmed enabled on log archive bucket. Both configs exported.
  2026-05-16 IN PROGRESS — M3 complete: Tamper simulation run — Falco alert fired in < 1s.
             Alert JSON exported. SecEng signed off on all AU-9 evidence artifacts.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/AU-9?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-011 — AU-11

```text
POAM-ID:          POAM-2026-05-011
CONTROL:          AU-11 — Audit Record Retention

WEAKNESS:
  Three deficiencies identified on Links-Matrix (AWS S3 / CloudTrail):
  (1) No S3 lifecycle policy on the CloudTrail delivery bucket — retention_policy_days: null;
      no lifecycle configuration is applied; logs may be deleted or expire without meeting
      the 3-year FedRAMP Moderate retention requirement.
  (2) No audit record retention policy document — no Confluence page specifies the required
      retention period, storage tiers, or exception handling for legal hold scenarios.
  (3) No evidence that logs older than 90 days are still accessible — PlatEng could not
      confirm logs from the assessment start window (February 2026) are still in the bucket.

SYSTEM AFFECTED:  Links-Matrix (AWS S3 CloudTrail delivery bucket, S3 log archive bucket)

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AU-11?env=bad → tool: cloudtrail, status: insufficient,
                  retention_policy_days: null, lifecycle_policy_artifact: null,
                  error: "Retention configuration not documented". PlatEng interview: no
                  S3 lifecycle policy, no retention policy document produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AU-11-2026-05-10/AU-11-finding.json

REMEDIATION OWNER: PlatEng (S3 lifecycle policy and retention configuration producer) / ISSO (retention policy sign-off)

SCHEDULED COMPLETION: 2026-06-09

MILESTONES:
  M1: 2026-05-25  Apply an S3 lifecycle policy to the CloudTrail delivery bucket: transition
                  objects to S3 Glacier Instant Retrieval at 90 days, transition to S3 Glacier
                  Deep Archive at 365 days, expire at 1,095 days (3 years); export the lifecycle
                  configuration JSON to the evidence path.
  M2: 2026-06-02  Produce the AU-11 audit record retention policy document in Confluence
                  specifying the 3-year requirement, storage tiers, legal hold exception
                  procedure, and annual review cadence; ISSO reviews and signs.
  M3: 2026-06-06  Verify that a log object from February 2026 (90+ days ago) is retrievable
                  from the delivery bucket or Glacier tier; document the retrieval command and
                  result in the evidence path as proof of accessibility.

REMEDIATION APPROACH:
  Step 1: Apply the S3 lifecycle policy to the CloudTrail delivery bucket:
    aws s3api put-bucket-lifecycle-configuration --bucket <cloudtrail-bucket> \
    --lifecycle-configuration file://au11-lifecycle-policy.json
  The policy JSON should define:
    - Rule 1: Transition to GLACIER_IR after 90 days
    - Rule 2: Transition to DEEP_ARCHIVE after 365 days
    - Rule 3: Expire after 1095 days
  Apply the same policy to the log archive bucket. Export the applied configuration:
    aws s3api get-bucket-lifecycle-configuration --bucket <cloudtrail-bucket>
  Step 2: In Confluence, produce the AU-11 retention policy document with sections: scope
  (which buckets), retention period (3 years / 1,095 days for FedRAMP Moderate), storage
  tiers and retrieval times, legal hold procedure (contact ISSO to apply S3 Object Lock hold),
  annual review schedule (January each year). ISSO signs the document.
  Step 3: Retrieve a test object from February 2026:
    aws s3 cp s3://<cloudtrail-bucket>/AWSLogs/<account>/CloudTrail/us-east-1/2026/02/01/ \
    /tmp/au11-test-retrieve/ --recursive --include "*.json.gz"
  Confirm at least one file is retrieved. Document the command and result in the evidence path.

VALIDATION COMMAND:
  aws cloudtrail describe-trails --query 'trailList[*].HasCustomEventSelectors'
  Expected output: [true]

RESIDUAL RISK AFTER REMEDIATION:
  S3 lifecycle policies are applied at bucket level — objects created before the policy was
  applied are not retroactively governed until their object-level age matches the rule. Logs
  created before 2026-05-25 will follow the old (no) retention policy until they age into
  the transition thresholds. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — retention_policy_days: null. No S3 lifecycle policy. No retention policy
             document. Log accessibility for 90+ day-old objects unconfirmed. PlatEng verbal.
  2026-05-25 IN PROGRESS — M1 complete: S3 lifecycle policy applied to CloudTrail delivery
             and log archive buckets. Lifecycle configuration JSON exported to evidence path.
  2026-06-02 IN PROGRESS — M2 complete: AU-11 retention policy published in Confluence.
             3-year requirement documented. ISSO signed and dated.
  2026-06-06 IN PROGRESS — M3 complete: February 2026 log object retrieved from delivery
             bucket (48 files downloaded). Retrieval command and result stored in evidence
             path.
  2026-06-09 CLOSED — BERU re-ran GET /evidence/AU-11?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-012 — AU-12

```text
POAM-ID:          POAM-2026-05-012
CONTROL:          AU-12 — Audit Record Generation

WEAKNESS:
  Three deficiencies identified on Links-Matrix (Falco / Kubernetes):
  (1) Falco not deployed — event_generation_rules: 0; zero runtime event generation rules
      are active; syscall, container, and file-level events are not being generated.
  (2) Kubernetes audit logging status unconfirmed — k8s_audit_log_enabled: null; PlatEng
      verbal claim that "CloudTrail covers it" cannot substitute for K8s API server audit
      log confirmation.
  (3) No coverage evidence for AU-2 event categories at the runtime layer — no Falco rule
      list, no K8s audit policy YAML, no coverage mapping produced by PlatEng.

SYSTEM AFFECTED:  Links-Matrix (Falco DaemonSet, Kubernetes API server, monitoring namespace)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AU-12?env=bad → tool: falco, status: insufficient,
                  event_generation_rules: 0, k8s_audit_log_enabled: null,
                  error: "Falco not deployed". PlatEng interview: no rule count, no K8s
                  audit log artifact, no AU-2 coverage mapping produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AU-12-2026-05-10/AU-12-finding.json

REMEDIATION OWNER: PlatEng (Falco deployment and K8s audit log enablement producer) / SecEng (coverage mapping sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Deploy Falco via Helm to the monitoring namespace; confirm the DaemonSet
                  is running on all nodes; export the active rule list showing coverage of
                  syscall, Kubernetes API, network, file integrity, and process event
                  categories to the evidence path.
  M2: 2026-05-14  Enable Kubernetes API server audit logging by applying an audit policy
                  YAML to the kube-apiserver; confirm audit log events appear in the
                  /var/log/audit/ path on control plane nodes; verify events are forwarded
                  to the Splunk gp_security index.
  M3: 2026-05-16  Produce an AU-2 coverage mapping document showing each event category
                  defined in AU-2 mapped to the Falco rule or K8s audit policy section that
                  generates the corresponding audit record; SecEng reviews and signs the
                  coverage mapping.

REMEDIATION APPROACH:
  Step 1: helm install falco falcosecurity/falco --namespace monitoring --create-namespace \
  --set falco.grpc.enabled=true --set falcosidekick.enabled=true. Confirm DaemonSet:
    kubectl -n monitoring get daemonset falco -o wide
  Export the active rule list:
    kubectl -n monitoring exec ds/falco -- falco --list > /tmp/falco-rules.txt
  Review the rule list for coverage of the 5 AU-2 event categories. Store the rule list
  in the evidence path.
  Step 2: Apply a Kubernetes audit policy to the API server. Create audit-policy.yaml:
    apiVersion: audit.k8s.io/v1
    kind: Policy
    rules:
      - level: RequestResponse
        resources: [{group: "", resources: ["pods", "secrets", "configmaps"]}]
      - level: Metadata
        resources: [{group: "apps", resources: ["deployments"]}]
  Add --audit-log-path=/var/log/audit/kube-apiserver-audit.log and
  --audit-policy-file=/etc/kubernetes/audit-policy.yaml to the API server manifest.
  Confirm audit events appear in the log file. Configure the Splunk Kubernetes Audit Events
  input to ingest from this path into the gp_security index.
  Step 3: SecEng produces the AU-2 coverage mapping in Confluence. For each of the 5
  categories (syscall, K8s API, network, file integrity, process), list the specific Falco
  rule name or K8s audit policy section that generates the audit record, and confirm
  alignment with the AU-2 event category list.

VALIDATION COMMAND:
  kubectl -n monitoring logs ds/falco --tail=5 | grep -c "rule="
  Expected output: 5

RESIDUAL RISK AFTER REMEDIATION:
  Falco rules cover the monitoring namespace and default node syscalls — workloads running
  in namespaces with restricted PodSecurityAdmission may suppress some syscall-level events.
  Namespace-level Falco tuning is required for complete coverage. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Falco not deployed. event_generation_rules: 0.
             k8s_audit_log_enabled: null. No AU-2 coverage mapping. PlatEng verbal only.
  2026-05-12 IN PROGRESS — M1 complete: Falco deployed to monitoring namespace.
             DaemonSet running on 3 nodes. 65 rules loaded — rule list exported to evidence
             path. Coverage confirmed for all 5 AU-2 event categories.
  2026-05-14 IN PROGRESS — M2 complete: K8s API server audit logging enabled. Audit events
             confirmed in /var/log/audit/ on control plane. Events forwarded to Splunk
             gp_security index (confirmed: index=gp_security source=k8s-audit | head 5).
  2026-05-16 IN PROGRESS — M3 complete: AU-2 coverage mapping produced in Confluence.
             All 5 categories mapped to Falco rules and K8s audit policy sections.
             SecEng signed the mapping artifact.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/AU-12?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```
