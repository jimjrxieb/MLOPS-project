# Risk Assessment Evidence — AU Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Evidence collected fully supports all SSP claims. Control owners provided
> exact artifacts, dates, version numbers, and metrics on first request. Tool queries returned
> complete structured data with no gaps. Every SSP claim is traceable to a specific artifact
> with a retrievable location. All six controls receive PASS findings. No POA&M items required.
> This is the evidence standard a 3PAO expects to walk in and find.

**Assessment Date:** 2026-05-10
**Assessor:** GRC Engineer (grc-engineer group — read-only)
**Framework:** NIST 800-53 Rev 5
**Graded Against:** Links-Matrix SSP (see ssp-examples/AU-ssp-great.md)

---

## AU-2 — Event Logging

**Control Owner:** ISSO
**Evidence Producer:** SecEng
**Cadence:** Annual + change-triggered

### SSP Claim
> The SSP asserts that auditable event categories are defined, documented in Confluence, and
> reviewed annually. CloudTrail captures management events, S3 data events, Lambda data events,
> and Insight events. Alert rules in CloudWatch map to each event category. The last annual
> event category review was conducted 2026-03-01 and signed by the ISSO.

### Evidence Request

**Interview — Questions asked of control owner (SecEng):**
1. Show me the active alert rules tied to your defined auditable events.
2. Show me the last annual AU-2 event category review artifact.
3. Show me which event categories are currently enabled in CloudTrail.

**Tool Query:** `GET /evidence/AU-2?env=great` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "AU-2", "env": "great", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "sufficient",
  "data": {
    "management_events_enabled": true,
    "data_events_enabled": true,
    "insight_events_enabled": true,
    "auditable_event_categories": ["Management", "S3DataEvents", "LambdaDataEvents", "InsightEvents"],
    "last_review_date": "2026-03-01",
    "review_artifact": "Confluence: au2-event-categories-v2.md"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "All four event categories are enabled: Management, S3DataEvents, LambdaDataEvents, and
> InsightEvents. The annual review was 2026-03-01 — artifact is in Confluence at
> au2-event-categories-v2.md, signed by ISSO M.Chen. Alert rules tied to these categories
> are in CloudWatch: priv-escalation, failed-logins-5min, after-hours-access, data-exfil-volume,
> lateral-movement, policy-violation, admin-action — 7 rules total."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — all four event categories enabled; annual review artifact produced; 7 alert rules named

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | All four event categories enabled; annual review current; alert rules named and active |
| Impact | Low | Complete event coverage with documented review and mapped alert rules |
| **Residual Risk** | **Low** | All SSP claims verified by CloudTrail data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: All four AU-2 event categories are enabled; annual review artifact produced; 7 alert rules confirmed active.
CONTROL: AU-2 — Event Logging
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - SecEng interview (categories named, review artifact location and date produced, 7 alert rules named)
  - CloudTrail query (Management, S3DataEvents, LambdaDataEvents, InsightEvents all enabled)
  - Annual review: Confluence: au2-event-categories-v2.md (reviewed 2026-03-01, ISSO M.Chen)
  - Alert rules: priv-escalation, failed-logins-5min, after-hours-access, data-exfil-volume, lateral-movement, policy-violation, admin-action
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: ISSO (accountability) / SecEng (evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Audit event logging is fully implemented and documented. All four required event categories are enabled in CloudTrail, the annual review is current, and 7 alert rules are active. This control is audit-ready.
```

---

## AU-3 — Content of Audit Records

**Control Owner:** PlatEng
**Evidence Producer:** PlatEng
**Cadence:** Continuous

### SSP Claim
> The SSP asserts that all audit records contain the required fields: event time, event source,
> event name, user identity, source IP, request parameters, response elements, and AWS region.
> A sample record is stored in S3 for assessor review. Field requirements are documented in
> the platform logging standard.

### Evidence Request

**Interview — Questions asked of control owner (PlatEng):**
1. Show me a sample audit record with all required fields populated.
2. Show me which fields are required and where that requirement is documented.

**Tool Query:** `GET /evidence/AU-3?env=great` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "AU-3", "env": "great", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "sufficient",
  "data": {
    "required_fields_present": true,
    "missing_fields": [],
    "fields_verified": [
      "eventTime", "eventSource", "eventName", "userIdentity",
      "sourceIPAddress", "requestParameters", "responseElements", "awsRegion"
    ],
    "sample_record": "s3://links-matrix-audit/cloudtrail/sample-2026-04-30.json"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "All 8 required fields are present in every record: eventTime, eventSource, eventName,
> userIdentity, sourceIPAddress, requestParameters, responseElements, awsRegion. Sample
> record is at s3://links-matrix-audit/cloudtrail/sample-2026-04-30.json. Field requirements
> are documented in Confluence: platform-logging-standard-v1.3.md."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — all 8 required fields confirmed present; sample record location provided; logging standard named

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | All required fields present in every record; sample record retrievable; standard documented |
| Impact | Low | Complete audit records support forensic investigation and chain-of-custody |
| **Residual Risk** | **Low** | All SSP claims verified by CloudTrail field validation and sample record |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: All 8 required AU-3 fields confirmed present in CloudTrail records; sample record and logging standard produced.
CONTROL: AU-3 — Content of Audit Records
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - PlatEng interview (all fields named, sample record path and logging standard produced)
  - CloudTrail query (required_fields_present true, 0 missing fields, all 8 fields verified)
  - Sample record: s3://links-matrix-audit/cloudtrail/sample-2026-04-30.json
  - Logging standard: Confluence: platform-logging-standard-v1.3.md
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Audit record content is fully evidenced. All 8 required fields are present, a sample record is retrievable, and the logging standard is documented. This control is audit-ready.
```

---

## AU-6 — Audit Record Review, Analysis, and Reporting

**Control Owner:** SOC
**Evidence Producer:** SOC
**Cadence:** Continuous; monthly report

### SSP Claim
> The SSP asserts that Splunk ingests all CloudTrail, Falco, and Kubernetes audit events
> into the gp_security index. SOC reviews alerts continuously with 7 active correlation rules.
> A monthly report is generated and sent to the ISSO and CISO. Review records are retained
> for 12 months.

### Evidence Request

**Interview — Questions asked of control owner (SOC):**
1. Show me your active SIEM alert rules — which audit events trigger alerts, and what is the escalation path?
2. Show me alert triage records for the last 30 days — how many alerts fired and what was the outcome?

**Tool Query:** `GET /evidence/AU-6?env=great` — simulates: splunk

**Tool Evidence (API Response):**
```json
{
  "control": "AU-6", "env": "great", "tool": "splunk",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:10:00Z", "status": "sufficient",
  "data": {
    "log_review_records_90d": 12,
    "alert_rules_active": 7,
    "alert_names": [
      "priv-escalation", "failed-logins-5min", "after-hours-access",
      "data-exfil-volume", "lateral-movement", "policy-violation", "admin-action"
    ],
    "last_review": "2026-04-28T09:00:00Z",
    "reviewer": "SOC-L2",
    "splunk_index": "gp_security",
    "retention_days": 365,
    "correlation_rules": 3,
    "monthly_report_artifact": "s3://links-matrix-audit/au6-monthly-2026-04.pdf"
  }
}
```

**Interview Response (Control Owner — SOC):**
> "12 review records in the last 90 days, last review 2026-04-28 by SOC-L2. All 7 alert
> rules are active: priv-escalation, failed-logins-5min, after-hours-access, data-exfil-volume,
> lateral-movement, policy-violation, admin-action. Monthly report is at
> s3://links-matrix-audit/au6-monthly-2026-04.pdf — recipients are ISSO, CISO, and SOC-Lead.
> gp_security index retains 365 days. Escalation: SOC-L1 triages, SOC-L2 reviews, IRT
> escalates P1/P2."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 12 review records, 7 alert rules named, reviewer identified, monthly report artifact in S3, escalation path documented

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 7 alert rules active; 12 review records; reviewer logged; escalation path documented |
| Impact | Low | Monthly reports to ISSO and CISO; 365-day retention; complete SOC triage chain |
| **Residual Risk** | **Low** | All SSP claims verified by Splunk data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: Splunk confirms 7 active alert rules, 12 review records in 90 days, and monthly report artifact for AU-6. All SSP claims verified.
CONTROL: AU-6 — Audit Record Review, Analysis, and Reporting
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - SOC interview (alert rule names, reviewer, escalation path, monthly report artifact produced)
  - Splunk query (7 alert rules, 12 review records, last review 2026-04-28 by SOC-L2, 365-day retention)
  - Monthly report: s3://links-matrix-audit/au6-monthly-2026-04.pdf (ISSO, CISO, SOC-Lead recipients)
  - Alert rules: priv-escalation, failed-logins-5min, after-hours-access, data-exfil-volume, lateral-movement, policy-violation, admin-action
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: SOC (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Audit record review is fully implemented. 7 alert rules active, 12 review records in 90 days, monthly reports distributed to ISSO and CISO with S3 artifact, and a documented SOC escalation path. This control is audit-ready.
```

---

## AU-7 — Audit Record Reduction and Report Generation

**Control Owner:** SOC
**Evidence Producer:** SOC
**Cadence:** On-demand + scheduled

### SSP Claim
> The SSP asserts that Splunk provides on-demand query capability and scheduled monthly reports.
> Reports are distributed to the ISSO, CISO, and SOC Lead in PDF format with a Splunk dashboard
> link. Report artifacts are stored in S3 for 12 months.

### Evidence Request

**Interview — Questions asked of control owner (SOC):**
1. Show me how audit findings are reported — who receives the report, how often, and what format?

**Tool Query:** `GET /evidence/AU-7?env=great` — simulates: splunk

**Tool Evidence (API Response):**
```json
{
  "control": "AU-7", "env": "great", "tool": "splunk",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:15:00Z", "status": "sufficient",
  "data": {
    "reports_generated_90d": 12,
    "scheduled_report": "Monthly — 1st of month 08:00 ET",
    "recipients": ["ISSO", "CISO", "SOC-Lead"],
    "format": "PDF + Splunk dashboard link",
    "report_artifact": "s3://links-matrix-audit/au7-report-2026-04.pdf",
    "on_demand_capability": true
  }
}
```

**Interview Response (Control Owner — SOC):**
> "12 reports generated in the last 90 days — monthly scheduled on the 1st at 08:00 ET.
> Recipients: ISSO, CISO, SOC-Lead. Format is PDF with Splunk dashboard link. April
> report is at s3://links-matrix-audit/au7-report-2026-04.pdf. On-demand queries are
> available in Splunk for any assessor with read access."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 12 reports, scheduled cadence confirmed, recipients listed, S3 artifact produced, on-demand capability confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | Monthly scheduled reports with named recipients; 12 reports in 90 days; on-demand available |
| Impact | Low | ISSO and CISO receive monthly reports; S3 artifact provides archival chain-of-custody |
| **Residual Risk** | **Low** | All SSP claims verified by Splunk data and S3 artifact |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: Splunk generates monthly reports distributed to ISSO, CISO, and SOC-Lead for AU-7. 12 reports in 90 days; S3 artifact produced.
CONTROL: AU-7 — Audit Record Reduction and Report Generation
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - SOC interview (schedule, recipients, format, S3 artifact path produced)
  - Splunk query (12 reports in 90d, monthly scheduled, ISSO/CISO/SOC-Lead recipients, on-demand confirmed)
  - Report artifact: s3://links-matrix-audit/au7-report-2026-04.pdf
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: SOC (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Audit reporting is fully implemented. Monthly scheduled reports distributed to ISSO, CISO, and SOC-Lead with S3 archival and on-demand query capability. This control is audit-ready.
```

---

## AU-9 — Protection of Audit Information

**Control Owner:** PlatEng
**Evidence Producer:** PlatEng
**Cadence:** Continuous

### SSP Claim
> The SSP asserts that Falco detects log tampering attempts via 8 active rules. CloudTrail
> logs are delivered to an S3 bucket with Object Lock enabled. Splunk gp_security index is
> immutable. Log archive bucket is protected by MFA delete.

### Evidence Request

**Interview — Questions asked of control owner (PlatEng):**
1. Show me how audit logs are protected from tampering or deletion.

**Tool Query:** `GET /evidence/AU-9?env=great` — simulates: falco

**Tool Evidence (API Response):**
```json
{
  "control": "AU-9", "env": "great", "tool": "falco",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:20:00Z", "status": "sufficient",
  "data": {
    "log_tamper_rules_active": 8,
    "rule_names": [
      "detect_log_rotate", "write_below_var_log",
      "clear_log_activities", "remove_bulk_data_from_disk"
    ],
    "s3_object_lock_validated": true,
    "falco_output_integrity": "Splunk gp_security index — immutable"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "8 Falco tamper detection rules active — detect_log_rotate, write_below_var_log,
> clear_log_activities, remove_bulk_data_from_disk, plus 4 additional custom rules.
> S3 Object Lock is enabled on links-matrix-cloudtrail-logs-archive — validated via
> Terraform: terraform/s3/audit-bucket.tf. MFA delete is enabled. Falco output goes
> to the Splunk gp_security index which is immutable by index policy."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 8 Falco tamper rules active; S3 Object Lock validated; MFA delete enabled; Splunk index immutable

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 8 tamper detection rules active; S3 Object Lock and MFA delete confirmed; Splunk index immutable |
| Impact | Low | Multi-layer log protection via runtime detection, S3 Object Lock, and immutable SIEM index |
| **Residual Risk** | **Low** | All SSP claims verified by Falco data and S3 configuration |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 8 Falco tamper detection rules active; S3 Object Lock validated; MFA delete enabled; Splunk index immutable for AU-9.
CONTROL: AU-9 — Protection of Audit Information
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - PlatEng interview (rule names, S3 Terraform reference, MFA delete confirmation produced)
  - Falco query (8 tamper rules active, S3 Object Lock validated, Splunk index immutable)
  - Tamper rules: detect_log_rotate, write_below_var_log, clear_log_activities, remove_bulk_data_from_disk + 4 custom
  - S3 config: terraform/s3/audit-bucket.tf (Object Lock + MFA delete)
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Audit log protection is fully implemented. 8 Falco tamper detection rules, S3 Object Lock with MFA delete, and an immutable Splunk index provide layered protection. This control is audit-ready.
```

---

## AU-12 — Audit Record Generation

**Control Owner:** PlatEng
**Evidence Producer:** PlatEng
**Cadence:** Continuous

### SSP Claim
> The SSP asserts that Falco generates audit records for all event categories defined in AU-2.
> 65 rules cover syscalls, Kubernetes API events, network activity, file integrity, and process
> activity. Kubernetes audit logging is enabled. Rules are stored in git for version control.

### Evidence Request

**Interview — Questions asked of control owner (PlatEng):**
1. Show me evidence that all required events from AU-2 are being generated.

**Tool Query:** `GET /evidence/AU-12?env=great` — simulates: falco

**Tool Evidence (API Response):**
```json
{
  "control": "AU-12", "env": "great", "tool": "falco",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:25:00Z", "status": "sufficient",
  "data": {
    "event_generation_rules": 65,
    "k8s_audit_log_enabled": true,
    "coverage": ["syscalls", "k8s-api", "network", "file-integrity", "process"],
    "last_rule_review": "2026-04-01",
    "rule_repo": "git: falco-rules/custom-rules.yaml"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "65 Falco rules active covering all 5 categories: syscalls, Kubernetes API events,
> network activity, file integrity, and process activity. Kubernetes audit logging is
> enabled and feeding into Falco. Last rule review was 2026-04-01 — rules are in
> git at falco-rules/custom-rules.yaml on the main branch. Coverage maps directly
> to the event categories in the AU-2 review artifact."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 65 Falco rules active; all 5 coverage categories confirmed; K8s audit logging enabled; rule repo named

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 65 rules covering all required event categories; Kubernetes audit logging enabled; rules version-controlled |
| Impact | Low | Complete runtime event generation with direct mapping to AU-2 categories |
| **Residual Risk** | **Low** | All SSP claims verified by Falco rule data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 65 Falco rules confirmed active covering all 5 AU-2 event categories; Kubernetes audit logging enabled; rule repo produced for AU-12.
CONTROL: AU-12 — Audit Record Generation
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - PlatEng interview (rule count, coverage categories, K8s audit log, rule repo path produced)
  - Falco query (65 rules, K8s audit log enabled, coverage: syscalls/k8s-api/network/file-integrity/process)
  - Rule repo: git: falco-rules/custom-rules.yaml (last review 2026-04-01)
  - Coverage maps to AU-2 event categories: Confluence: au2-event-categories-v2.md
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Audit record generation is fully implemented. 65 Falco rules covering all required event categories, Kubernetes audit logging enabled, and rules version-controlled in git. This control is audit-ready.
```
