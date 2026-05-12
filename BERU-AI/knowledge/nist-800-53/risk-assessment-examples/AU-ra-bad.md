# Risk Assessment Evidence — AU Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** Evidence collected for all six Audit and Accountability controls is incomplete
> and unverifiable. Control owners provided vague verbal assurances with no supporting artifacts.
> Tool queries returned empty or error responses indicating controls are not deployed or not
> configured to capture required data. All six findings are FAIL; all require POA&M items.

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

**Tool Query:** `GET /evidence/AU-2?env=bad` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "AU-2", "env": "bad", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "management_events_enabled": null,
    "data_events_enabled": false,
    "insight_events_enabled": false,
    "auditable_event_categories": [],
    "error": "Trail configuration not retrievable"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "We log everything. CloudTrail is on. The events are all there somewhere. I don't have
> the specific alert rules in front of me but SOC would know. The annual review happened
> a while back."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Trail configuration not retrievable; no event categories confirmed; no alert rules produced |
| Impact | High | Undefined event logging means security-relevant events may be missed entirely |
| **Residual Risk** | **Critical** | No evidence any required audit events are captured |

**Finding:** FAIL
**Evidence Gap:** CloudTrail configuration not retrievable. No event categories confirmed. No annual review artifact. No alert rules produced.

**BERU Finding:**
```
FINDING: SecEng cannot produce the AU-2 event category list, alert rules, or annual review artifact.
CONTROL: AU-2 — Event Logging
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - SecEng verbal statement (no artifacts provided)
  - CloudTrail query (trail configuration not retrievable, no categories returned)
EVIDENCE GAP: No event category list, no alert rules, no annual review artifact
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: ISSO (accountability) / SecEng (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Auditable event categories are not defined and CloudTrail configuration is not retrievable. Without defined event categories and alert rules, security-relevant events will be missed. This is a foundational audit control and cannot remain unverified.
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

**Tool Query:** `GET /evidence/AU-3?env=bad` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "AU-3", "env": "bad", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "required_fields_present": false,
    "missing_fields": ["eventTime", "userIdentity", "sourceIPAddress", "requestParameters"],
    "sample_record": null,
    "error": "Sample record not available — CloudTrail not delivering to accessible S3 bucket"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "Logs are on our servers. CloudTrail captures what it captures. I'm sure the fields
> are all there. I don't have a sample record to show you right now."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Sample record not available; 4 required fields confirmed missing; no logging standard produced |
| Impact | High | Incomplete audit records cannot support incident investigation or compliance verification |
| **Residual Risk** | **Critical** | Audit record completeness cannot be established |

**Finding:** FAIL
**Evidence Gap:** No sample record produced. Four required fields confirmed missing. Platform logging standard not provided.

**BERU Finding:**
```
FINDING: CloudTrail audit records are missing 4 required fields and no sample record can be produced for AU-3.
CONTROL: AU-3 — Content of Audit Records
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (no artifacts)
  - CloudTrail query (required_fields_present false, 4 fields missing, sample record null)
EVIDENCE GAP: No sample record, 4 missing required fields (eventTime, userIdentity, sourceIPAddress, requestParameters), no logging standard document
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Audit records are missing four required NIST fields. Without complete audit records, incident forensics and audit chain-of-custody cannot be established. This must be remediated before any authorization assessment.
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

**Tool Query:** `GET /evidence/AU-6?env=bad` — simulates: splunk

**Tool Evidence (API Response):**
```json
{
  "control": "AU-6", "env": "bad", "tool": "splunk",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "log_review_records_90d": 0,
    "alert_rules_active": 0,
    "last_review": null,
    "error": "Splunk index gp_security not found or empty"
  }
}
```

**Interview Response (Control Owner — SOC):**
> "SOC reviews alerts. We get paged when something comes in. I don't have the alert
> count or the triage records but the SOC lead would know. Monthly reports go out."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Splunk index not found; 0 alert rules active; no review records; no monthly report artifact |
| Impact | High | Without SIEM review, security events go uninvestigated; incident detection depends on alert infrastructure |
| **Residual Risk** | **Critical** | No evidence SIEM is operational or that any log review is occurring |

**Finding:** FAIL
**Evidence Gap:** Splunk gp_security index not found. Zero alert rules configured. No review records. No monthly report artifact.

**BERU Finding:**
```
FINDING: Splunk gp_security index is empty or not found; 0 alert rules active for AU-6.
CONTROL: AU-6 — Audit Record Review, Analysis, and Reporting
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - SOC verbal statement (no artifacts provided)
  - Splunk query (gp_security index not found, 0 alert rules, 0 review records)
EVIDENCE GAP: No Splunk index, no alert rules, no triage records, no monthly report artifact
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: SOC (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: The SIEM is not operational for security event review. Zero alert rules and zero review records mean security events are not being analyzed. This is a critical gap in continuous monitoring and must be remediated immediately.
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

**Tool Query:** `GET /evidence/AU-7?env=bad` — simulates: splunk

**Tool Evidence (API Response):**
```json
{
  "control": "AU-7", "env": "bad", "tool": "splunk",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "reports_generated_90d": 0,
    "scheduled_report_artifact": null,
    "error": "No scheduled reports found in Splunk"
  }
}
```

**Interview Response (Control Owner — SOC):**
> "We generate reports when needed. The SOC lead handles that. I don't have a report
> to show you right now."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Zero reports generated; no scheduled report artifact; Splunk reporting not configured |
| Impact | Medium | Without regular reporting, ISSO and CISO cannot exercise oversight of security posture |
| **Residual Risk** | **High** | No evidence report generation capability exists or is used |

**Finding:** FAIL
**Evidence Gap:** Zero reports generated in 90 days. No scheduled report configured. No artifact produced.

**BERU Finding:**
```
FINDING: No Splunk reports have been generated in 90 days and no scheduled reporting is configured for AU-7.
CONTROL: AU-7 — Audit Record Reduction and Report Generation
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - SOC verbal statement (no artifacts)
  - Splunk query (0 reports generated, no scheduled report found)
EVIDENCE GAP: No reports generated, no scheduled report artifact, no recipient list
RISK:
  Likelihood: High
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: SOC (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Audit report generation is not configured. Zero reports have been produced in the last 90 days. The ISSO and CISO cannot perform oversight without regular audit reporting. Configure scheduled reports and produce the first artifact before the next assessment.
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

**Tool Query:** `GET /evidence/AU-9?env=bad` — simulates: falco

**Tool Evidence (API Response):**
```json
{
  "control": "AU-9", "env": "bad", "tool": "falco",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "log_tamper_rules_active": 0,
    "immutable_log_config": null,
    "error": "Falco not deployed"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "Logs are protected. We have S3. Falco is on the roadmap. I'd have to check if
> Object Lock is on."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Falco not deployed; S3 Object Lock status unknown; no tamper detection rules active |
| Impact | High | Without tamper protection, audit logs can be modified or deleted to cover unauthorized activity |
| **Residual Risk** | **Critical** | Log integrity cannot be verified; audit trail is not trustworthy |

**Finding:** FAIL
**Evidence Gap:** Falco not deployed — zero tamper detection rules. S3 Object Lock status not confirmed. MFA delete status unknown.

**BERU Finding:**
```
FINDING: Falco is not deployed and no audit log tamper detection is active for AU-9.
CONTROL: AU-9 — Protection of Audit Information
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (no artifacts)
  - Falco query (not deployed, 0 tamper rules active)
EVIDENCE GAP: No Falco tamper detection rules, S3 Object Lock status unconfirmed, MFA delete status unknown
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Audit log integrity cannot be verified. Falco is not deployed and S3 Object Lock has not been confirmed. Unprotected audit logs can be tampered with or deleted, invalidating the entire audit trail. This is a critical control gap.
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

**Tool Query:** `GET /evidence/AU-12?env=bad` — simulates: falco

**Tool Evidence (API Response):**
```json
{
  "control": "AU-12", "env": "bad", "tool": "falco",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "event_generation_rules": 0,
    "k8s_audit_log_enabled": null,
    "error": "Falco not deployed"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "We generate audit records. Falco is being set up. In the meantime CloudTrail covers it.
> I don't have the specific rule count."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Falco not deployed; 0 event generation rules; Kubernetes audit logging status unknown |
| Impact | High | Without runtime event generation, container and kernel-level activity goes unrecorded |
| **Residual Risk** | **Critical** | Runtime audit record generation is entirely absent |

**Finding:** FAIL
**Evidence Gap:** Falco not deployed — zero event generation rules. Kubernetes audit logging status not confirmed.

**BERU Finding:**
```
FINDING: Falco is not deployed and audit record generation rules are absent for AU-12.
CONTROL: AU-12 — Audit Record Generation
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (no artifacts)
  - Falco query (not deployed, 0 rules, K8s audit log status unknown)
EVIDENCE GAP: No Falco rules, no K8s audit log confirmation, no coverage evidence for AU-2 event categories
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Runtime audit record generation is absent. Falco is not deployed and the Kubernetes audit log status is unconfirmed. Without AU-12 implementation, the event categories defined in AU-2 are not being generated at the runtime layer. Deploy Falco and confirm Kubernetes audit logging before the next assessment.
```
