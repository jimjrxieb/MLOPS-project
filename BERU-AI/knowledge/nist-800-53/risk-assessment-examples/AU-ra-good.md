# Risk Assessment Evidence — AU Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** Evidence collected is partially sufficient. Control owners named specific
> tools and processes but could not produce exact artifacts, dates, or complete metrics. Tool
> queries returned partial data — some booleans confirmed but key counts and timestamps absent.
> All six controls receive PARTIAL findings requiring POA&M items to close the evidence gaps
> before the next audit cycle.

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

**Tool Query:** `GET /evidence/AU-2?env=good` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "AU-2", "env": "good", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "partial",
  "data": {
    "management_events_enabled": true,
    "data_events_enabled": false,
    "insight_events_enabled": false,
    "auditable_event_categories": ["Management"],
    "note": "S3 data events and Lambda data events not captured"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "CloudTrail is enabled and we capture management events. S3 data events and Insight
> events are on the backlog — we know they're not on yet. The alert rules exist in
> CloudWatch but I don't have the full list here. The annual review happened around
> March but I'd need to pull the artifact from Confluence."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — management events confirmed; S3 data events and Insight events absent; alert rules and review artifact not produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Management events captured; data and insight events missing; alert rules not produced |
| Impact | Medium | Partial event coverage means S3 and Lambda activity goes unlogged; review artifact gap means control intent is unverifiable |
| **Residual Risk** | **High** | Partial event logging confirmed but coverage gaps and missing review artifact require remediation |

**Finding:** PARTIAL
**Evidence Gap:** S3 data events and Insight events not enabled. Alert rules not produced. Annual review artifact not retrieved.

**BERU Finding:**
```
FINDING: CloudTrail captures management events for AU-2 but S3 data events and Insight events are absent; alert rules and annual review artifact not produced.
CONTROL: AU-2 — Event Logging
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - SecEng verbal statement (event categories described, artifact location referenced)
  - CloudTrail query (management events enabled, data events false, insight events false)
EVIDENCE GAP: S3 data events not enabled, Insight events not enabled, alert rules not produced, annual review artifact not retrieved
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: ISSO (accountability) / SecEng (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Audit event logging is partial — management events are captured but S3 and Lambda data events are not configured. Enable remaining event categories and produce the annual review artifact to close this finding.
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

**Tool Query:** `GET /evidence/AU-3?env=good` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "AU-3", "env": "good", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "partial",
  "data": {
    "required_fields_present": true,
    "missing_fields": ["requestParameters"],
    "sample_record": "present but requestParameters truncated in some events"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "Most fields are there. We know requestParameters gets truncated on some large API calls
> — it's a CloudTrail behavior we're working around. The logging standard is documented
> somewhere in the platform runbooks but I don't have the exact link."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — most required fields present; requestParameters truncated in some events; logging standard not produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Most fields present; requestParameters truncation is a known gap; logging standard not linked |
| Impact | Medium | Truncated requestParameters may impede forensic investigation of specific API calls |
| **Residual Risk** | **High** | Partial field coverage confirmed but truncation gap and missing logging standard must close |

**Finding:** PARTIAL
**Evidence Gap:** requestParameters field truncated in some events. Platform logging standard document not produced. Sample record S3 path not provided.

**BERU Finding:**
```
FINDING: AU-3 audit records are mostly complete but requestParameters is truncated in some events and the logging standard was not produced.
CONTROL: AU-3 — Content of Audit Records
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (truncation issue acknowledged, logging standard location unconfirmed)
  - CloudTrail query (required_fields_present true, requestParameters truncated, sample record partial)
EVIDENCE GAP: requestParameters truncation unresolved, platform logging standard not produced, sample record S3 path not provided
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Audit records are mostly complete but the requestParameters truncation gap must be addressed and the logging standard produced before this control can be fully evidenced.
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

**Tool Query:** `GET /evidence/AU-6?env=good` — simulates: splunk

**Tool Evidence (API Response):**
```json
{
  "control": "AU-6", "env": "good", "tool": "splunk",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:10:00Z", "status": "partial",
  "data": {
    "log_review_records_90d": 1,
    "alert_rules_active": 4,
    "last_review": "2026-04-28",
    "reviewer": null,
    "escalation_path": null,
    "note": "One review record found. Reviewer identity not logged. No escalation path documented."
  }
}
```

**Interview Response (Control Owner — SOC):**
> "Splunk is configured. We have 4 alert rules active. The last review was April 28.
> Monthly reports go out but I'd have to pull the artifact. The escalation path is
> word-of-mouth for now — it's not formally documented."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — Splunk configured with 4 rules; reviewer identity not logged; escalation path not documented; monthly report artifact not produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | SIEM active with 4 rules; 3 fewer than SSP claim; reviewer identity gap means accountability is unverifiable |
| Impact | Medium | Alert coverage partial; undocumented escalation path means incident response may be delayed |
| **Residual Risk** | **High** | SIEM operational but alert count, reviewer logging, and escalation documentation gaps require closure |

**Finding:** PARTIAL
**Evidence Gap:** Only 4 of 7 claimed alert rules active. Reviewer identity not logged. Escalation path not documented. Monthly report artifact not produced.

**BERU Finding:**
```
FINDING: Splunk is configured with 4 alert rules for AU-6 but reviewer identity, escalation path, and monthly report artifact were not produced.
CONTROL: AU-6 — Audit Record Review, Analysis, and Reporting
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - SOC verbal statement (Splunk described, monthly reports mentioned but not produced)
  - Splunk query (4 alert rules active, 1 review record, reviewer null, escalation null)
EVIDENCE GAP: Only 4 of 7 claimed alert rules active, reviewer identity not logged, escalation path not documented, monthly report artifact not produced
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: SOC (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: SIEM is operational but alert coverage is below the SSP claim and the review process lacks accountability logging. Document the escalation path, enable remaining alert rules, and produce the monthly report artifact to close this finding.
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

**Tool Query:** `GET /evidence/AU-7?env=good` — simulates: splunk

**Tool Evidence (API Response):**
```json
{
  "control": "AU-7", "env": "good", "tool": "splunk",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:15:00Z", "status": "partial",
  "data": {
    "reports_generated_90d": 3,
    "scheduled_report_artifact": "Splunk saved search — not distributed",
    "recipients": null,
    "note": "Reports exist but not sent to ISSO/CISO"
  }
}
```

**Interview Response (Control Owner — SOC):**
> "We have 3 reports in Splunk from the last 90 days. They're saved searches. We
> haven't set up distribution to ISSO and CISO yet — that's on the roadmap. The SOC
> lead reviews them internally."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — Splunk reports exist; distribution to ISSO/CISO not configured; no S3 artifact produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Reports exist in Splunk; distribution gap means ISSO/CISO oversight is not occurring |
| Impact | Medium | ISSO and CISO cannot exercise audit oversight without receiving reports |
| **Residual Risk** | **High** | Report generation partially confirmed but distribution and archival not evidenced |

**Finding:** PARTIAL
**Evidence Gap:** Reports not distributed to ISSO or CISO. No S3 artifact for report archival. Recipients list not configured.

**BERU Finding:**
```
FINDING: Splunk has generated 3 reports in 90 days for AU-7 but distribution to ISSO/CISO is not configured and no S3 artifact was produced.
CONTROL: AU-7 — Audit Record Reduction and Report Generation
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - SOC verbal statement (Splunk reports described, distribution gap acknowledged)
  - Splunk query (3 reports generated, not distributed, recipients null)
EVIDENCE GAP: Reports not distributed to ISSO/CISO, no S3 archive artifact, recipient list not configured
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: SOC (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Splunk reports exist but are not being distributed to oversight personnel. Configure report distribution to ISSO and CISO and store artifacts in S3 to close this finding.
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

**Tool Query:** `GET /evidence/AU-9?env=good` — simulates: falco

**Tool Evidence (API Response):**
```json
{
  "control": "AU-9", "env": "good", "tool": "falco",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:20:00Z", "status": "partial",
  "data": {
    "log_tamper_rules_active": 3,
    "immutable_log_config": null,
    "note": "Basic tamper rules active. S3 immutability not confirmed via Falco."
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "Falco has some tamper detection rules — 3 of them. S3 Object Lock — I believe it's
> on but I'd need to verify. MFA delete is something we discussed but I'm not sure
> if it was implemented."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — 3 of 8 claimed Falco tamper rules active; S3 Object Lock and MFA delete not confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Partial tamper detection active; S3 immutability unconfirmed; MFA delete status unknown |
| Impact | High | Without full tamper protection, logs remain vulnerable to deletion if S3 protections are not enabled |
| **Residual Risk** | **High** | Partial Falco coverage confirmed but S3 protection gaps must be verified |

**Finding:** PARTIAL
**Evidence Gap:** Only 3 of 8 claimed Falco tamper rules active. S3 Object Lock not confirmed. MFA delete not confirmed.

**BERU Finding:**
```
FINDING: Falco has 3 of 8 claimed tamper detection rules for AU-9; S3 Object Lock and MFA delete status not confirmed.
CONTROL: AU-9 — Protection of Audit Information
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (Falco rules described, S3 protections uncertain)
  - Falco query (3 tamper rules active, S3 immutability not confirmed)
EVIDENCE GAP: 5 of 8 claimed tamper rules not deployed, S3 Object Lock unconfirmed, MFA delete status unknown
RISK:
  Likelihood: Medium
  Impact: High
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Falco tamper detection is partially deployed but below the SSP claim. Confirm S3 Object Lock and MFA delete, and deploy remaining Falco rules to fully evidence log integrity protection.
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

**Tool Query:** `GET /evidence/AU-12?env=good` — simulates: falco

**Tool Evidence (API Response):**
```json
{
  "control": "AU-12", "env": "good", "tool": "falco",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:25:00Z", "status": "partial",
  "data": {
    "event_generation_rules": 22,
    "k8s_audit_log_enabled": true,
    "coverage_gaps": ["network syscalls", "file integrity"],
    "note": "Partial coverage — 22 rules active; network syscalls and file integrity not covered"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "Falco runs with 22 rules. Kubernetes audit logging is on. We know network syscalls
> and file integrity aren't covered yet — those are in the backlog. The rules are
> in git but the repo isn't linked from the SSP."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — Falco deployed with 22 rules and K8s audit logging enabled; coverage gaps in network syscalls and file integrity

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Falco deployed and K8s audit logging enabled; 43 of 65 claimed rules not deployed; coverage gaps confirmed |
| Impact | Medium | Network syscall and file integrity gaps mean container escape and file tampering events may not be recorded |
| **Residual Risk** | **High** | Partial runtime audit generation confirmed but coverage gaps require remediation |

**Finding:** PARTIAL
**Evidence Gap:** Only 22 of 65 claimed Falco rules active. Network syscall and file integrity coverage absent. Rules repo not linked from SSP.

**BERU Finding:**
```
FINDING: Falco is deployed with 22 of 65 claimed rules for AU-12; Kubernetes audit logging is enabled but network syscall and file integrity coverage gaps exist.
CONTROL: AU-12 — Audit Record Generation
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (Falco running, coverage gaps acknowledged)
  - Falco query (22 rules active, K8s audit log enabled, network syscalls and file integrity gaps)
EVIDENCE GAP: 43 Falco rules not deployed, network syscall coverage absent, file integrity coverage absent, rules repo not linked from SSP
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Runtime audit record generation is partially implemented. Deploy the remaining 43 Falco rules and close the network syscall and file integrity coverage gaps to fully implement AU-12.
```
