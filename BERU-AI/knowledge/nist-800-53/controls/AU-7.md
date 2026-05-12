---
family: AU
family_name: Audit and Accountability
id: AU-7
name: Audit Record Reduction and Report Generation
---

question: "Can we query and report on audit logs on demand — without altering the originals?"

description: >
  The information system provides an audit record reduction and report generation capability
  that supports on-demand analysis and reporting requirements, and does not alter the original
  content of audit records or the time ordering of audit records. Reduction means filtering
  and aggregating large log volumes into actionable signals. Report generation means producing
  structured output for investigators, auditors, and leadership without modifying the source
  of truth. The separation between raw log storage and reporting tooling is essential —
  the reporting layer must never be able to mutate what it reads.

enhancements:
  - id: AU-7(1)
    name: Automatic Processing
    description: >
      The information system provides the capability to process audit records for events
      of interest based on organization-defined criteria. Automated log processing pipelines
      (scheduled queries, streaming analytics) replace manual grep — events of interest
      surface without a human scanning raw logs.

HITRUST_map:
  - "09.aa — Audit Logging"
  - "09.ab — Monitoring System Use"

evidence:
  what_to_look_for:
    - Query and reporting capability (SIEM dashboards, log analytics queries, saved searches) operating on read-only log data
    - Evidence that audit log storage is immutable or write-once — reporting tools have read-only access
    - On-demand report generation capability demonstrated for a specific event or time range
    - Automated report generation (scheduled queries for daily/weekly/monthly audit summaries)
    - Documentation separating log storage access controls from reporting access controls
  ask_for:
    - "Show me how an investigator queries audit logs for a specific user's activity over a time range — walk me through the tool and the query."
    - "Show me that your reporting or SIEM tooling has read-only access to log storage — can the SIEM delete or modify log entries?"
    - "Show me an example on-demand audit report generated for a recent investigation or compliance request."
    - "Show me your scheduled audit reports — what runs automatically, how often, and where are the outputs retained?"
  tools:
    generic:
      - Elasticsearch / OpenSearch (Kibana dashboards and saved queries — verify index access is read-only for analysts)
      - Grafana Loki (LogQL queries with read-only datasource permissions)
      - Splunk (saved searches, scheduled reports, role-based access to search only)
      - kubectl logs (read-only — cannot modify K8s audit log)
    aws:
      - CloudWatch Logs Insights (ad-hoc query against log groups — read-only by nature)
      - Amazon Athena (SQL queries against S3-stored CloudTrail logs — S3 bucket policy restricts writes)
      - AWS Security Hub (report generation from aggregated findings)
      - S3 Object Lock (WORM configuration on CloudTrail log bucket — immutability evidence)
    microsoft:
      - Log Analytics Workspace (KQL queries — verify analyst role has read-only permissions)
      - Microsoft Sentinel Workbooks (dashboard and report generation from immutable log store)
      - Azure Monitor Logs (read-only query access separated from log ingestion permissions)
      - Microsoft Purview Audit (search and export without modification)

failure_to_implement:
  - No query capability — investigators must request raw log exports and process them manually, adding hours to incident response.
  - Reporting tools have write access to log storage — a compromised SIEM account can delete evidence of the compromise.
  - Log volume is so high that on-demand queries time out — effectively no audit report generation capability under load.
  - Reports are generated but not retained — auditor requests a report from six months ago and it no longer exists.
  - Log reduction is destructive — summarization discards raw events before the retention period expires.

related:
  - AU-2
  - AU-3
  - AU-6
  - AU-9

chain: "AU-2 → AU-3 → AU-12 → AU-6 → AU-7"
