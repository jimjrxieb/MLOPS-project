# Risk Assessment Evidence — IR Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** Evidence collected is partially sufficient. Control owners named specific
> tools and processes but could not produce exact artifacts, dates, or complete metrics. Tool
> queries returned partial data — some booleans confirmed but key counts and timestamps absent.
> Both controls receive PARTIAL findings requiring POA&M items to close the evidence gaps
> before the next audit cycle.

**Assessment Date:** 2026-05-10
**Assessor:** GRC Engineer (grc-engineer group — read-only)
**Framework:** NIST 800-53 Rev 5
**Graded Against:** Links-Matrix SSP (see ssp-examples/IR-ssp-great.md)

---

## IR-4 — Incident Handling

**Control Owner:** IRT
**Evidence Producer:** IRT
**Cadence:** Per-incident; annual tabletop

### SSP Claim
> The SSP asserts that Falco provides automated incident detection with 65 rules routed
> to PagerDuty P1/P2 and Slack #soc-alerts. The escalation path is SOC-L1 to SOC-L2 to IRT.
> Mean time to detect is 4 minutes. An annual tabletop exercise was conducted 2026-02-15
> with documented outcomes.

### Evidence Request

**Interview — Questions asked of control owner (IRT):**
1. Show me how incidents are detected.
2. Show me your escalation path from alert to IRT.
3. Show me your last tabletop exercise record.

**Tool Query:** `GET /evidence/IR-4?env=good` — simulates: falco

**Tool Evidence (API Response):**
```json
{
  "control": "IR-4", "env": "good", "tool": "falco",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "partial",
  "data": {
    "incident_detection_rules": 15,
    "alert_routing": "Slack #security-alerts",
    "escalation_path": null,
    "note": "Alerts route to Slack but escalation SLA not defined"
  }
}
```

**Interview Response (Control Owner — IRT):**
> "Falco is deployed with 15 rules. Alerts go to Slack #security-alerts. The escalation
> is SOC-L1 then SOC-L2 then IRT — but it's not written down formally. Mean time to
> detect — I don't have that metric. The tabletop happened in February but I don't
> have a formal artifact."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — Falco deployed with 15 rules; alerts routing to Slack; escalation path described but undocumented; MTTD and tabletop artifact not produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Falco deployed with 15 rules; Slack routing active; escalation SLA undocumented; PagerDuty not confirmed |
| Impact | Medium | Detection is occurring but 50 of 65 claimed rules missing; escalation SLA gap means response times are unverifiable |
| **Residual Risk** | **High** | Partial incident detection confirmed; escalation documentation and tabletop artifact gaps must close |

**Finding:** PARTIAL
**Evidence Gap:** Only 15 of 65 claimed Falco rules deployed. PagerDuty routing not confirmed. Escalation SLA not documented. Mean time to detect not measured. Tabletop artifact not produced.

**BERU Finding:**
```
FINDING: Falco is deployed with 15 of 65 claimed rules for IR-4; escalation SLA is undocumented and tabletop artifact not produced.
CONTROL: IR-4 — Incident Handling
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - IRT verbal statement (Falco running, Slack routing, escalation described verbally)
  - Falco query (15 detection rules, Slack routing, escalation_path null)
EVIDENCE GAP: 50 of 65 claimed rules missing, PagerDuty not confirmed, escalation SLA undocumented, MTTD not measured, tabletop artifact not produced
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: IRT (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Incident detection is partially deployed but below the SSP claim. Deploy the remaining Falco rules, document the escalation SLA, and produce the tabletop exercise artifact to close this finding.
```

---

## IR-8 — Incident Response Plan

**Control Owner:** ISSO
**Evidence Producer:** ISSO
**Cadence:** Annual review + tabletop

### SSP Claim
> The SSP asserts that an Incident Response Plan (v4.2) is maintained in Confluence and
> reviewed annually by the ISSO. The last review was 2026-03-01. An annual tabletop exercise
> was conducted 2026-02-15 with the artifact at
> s3://links-matrix-audit/ir-tabletop-2026-02.pdf. IRT contacts are current.

### Evidence Request

**Interview — Questions asked of control owner (ISSO):**
1. Show me your IR plan — last review date and approver.
2. Show me the last tabletop outcome.

**Tool Query:** `GET /evidence/IR-8?env=good` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "IR-8", "env": "good", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "partial",
  "data": {
    "ir_plan_artifact": "Confluence page — not version-controlled",
    "last_review_date": "2025",
    "tabletop_conducted": null
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "The IR plan is in Confluence — I can find the link. It was reviewed in 2025
> but I don't have the exact date. Version 4.2 — I'm not sure if that's current.
> The tabletop was conducted but I don't have a formal artifact — it was
> documented in meeting notes."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — IR plan exists in Confluence; review date imprecise; version not confirmed; tabletop artifact not produced; IRT contacts currency not confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | IR plan exists and was reviewed; date imprecise; tabletop not formally documented |
| Impact | Medium | IR plan currency unconfirmed; without version and review date, plan may be stale |
| **Residual Risk** | **High** | IR plan partially evidenced; version, review date, and tabletop artifact gaps must close |

**Finding:** PARTIAL
**Evidence Gap:** IR plan review date imprecise. Plan version not confirmed. Tabletop artifact not produced. IRT contacts currency not confirmed.

**BERU Finding:**
```
FINDING: IR plan exists in Confluence for IR-8 but the review date is imprecise and no tabletop artifact was produced.
CONTROL: IR-8 — Incident Response Plan
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - ISSO verbal statement (plan in Confluence, review in 2025, tabletop meeting notes only)
  - Semgrep query (ir_plan in Confluence, not version-controlled, review 2025 imprecise, tabletop null)
EVIDENCE GAP: Review date imprecise, plan version not confirmed, tabletop artifact not produced, IRT contacts currency not confirmed
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: ISSO (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: The IR plan exists but the evidence package is insufficient for audit. Confirm the plan version and review date, version-control the plan in Confluence, and produce the tabletop artifact to close this finding.
```
