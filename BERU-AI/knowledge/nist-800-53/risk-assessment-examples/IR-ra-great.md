# Risk Assessment Evidence — IR Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Evidence collected fully supports all SSP claims. Control owners provided
> exact artifacts, dates, version numbers, and metrics on first request. Tool queries returned
> complete structured data with no gaps. Every SSP claim is traceable to a specific artifact
> with a retrievable location. Both controls receive PASS findings. No POA&M items required.
> This is the evidence standard a 3PAO expects to walk in and find.

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

**Tool Query:** `GET /evidence/IR-4?env=great` — simulates: falco

**Tool Evidence (API Response):**
```json
{
  "control": "IR-4", "env": "great", "tool": "falco",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "sufficient",
  "data": {
    "incident_detection_rules": 65,
    "alert_routing": "PagerDuty P1/P2 + Slack #soc-alerts",
    "escalation_path": "SOC-L1 → SOC-L2 → IRT",
    "mean_time_to_detect_minutes": 4,
    "tabletop_last_date": "2026-02-15"
  }
}
```

**Interview Response (Control Owner — IRT):**
> "65 Falco rules active. P1/P2 alerts route to PagerDuty — P1 wakes someone up
> in 2 minutes, P2 in 15 minutes. Also routed to Slack #soc-alerts. Escalation:
> SOC-L1 triages, SOC-L2 investigates, IRT leads response — documented in
> Confluence: incident-escalation-policy-v2.md. MTTD is 4 minutes — measured
> from Falco alert to PagerDuty acknowledgment. Tabletop was 2026-02-15 —
> artifact is at s3://links-matrix-audit/ir-tabletop-2026-02.pdf."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 65 Falco rules; PagerDuty + Slack routing; escalation path documented; MTTD 4 minutes measured; tabletop artifact in S3

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 65 detection rules; PagerDuty P1/P2 routing; MTTD 4 minutes measured; documented escalation path |
| Impact | Low | Automated detection with documented escalation and annual tabletop validation |
| **Residual Risk** | **Low** | All SSP claims verified by Falco data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 65 Falco rules, PagerDuty + Slack routing, MTTD 4 minutes, documented escalation, and tabletop artifact confirmed for IR-4.
CONTROL: IR-4 — Incident Handling
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - IRT interview (Falco rule count, routing targets, escalation policy location, MTTD measurement, tabletop artifact path produced)
  - Falco query (65 detection rules, PagerDuty P1/P2 + Slack #soc-alerts, SOC-L1→L2→IRT, MTTD 4 min, tabletop 2026-02-15)
  - Escalation policy: Confluence: incident-escalation-policy-v2.md
  - Tabletop artifact: s3://links-matrix-audit/ir-tabletop-2026-02.pdf
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: IRT (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Incident handling is fully implemented. 65 Falco rules with PagerDuty routing, 4-minute MTTD, documented escalation path, and annual tabletop artifact. This control is audit-ready.
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

**Tool Query:** `GET /evidence/IR-8?env=great` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "IR-8", "env": "great", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "sufficient",
  "data": {
    "ir_plan_artifact": "Confluence: ir-plan-v4.2 (ISSO reviewed 2026-03-01)",
    "last_review_date": "2026-03-01",
    "tabletop_conducted": "2026-02-15",
    "tabletop_artifact": "s3://links-matrix-audit/ir-tabletop-2026-02.pdf",
    "irt_contacts_current": true
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "IR plan is at Confluence: ir-plan-v4.2, reviewed 2026-03-01 by me (ISSO M.Chen).
> The plan includes roles, escalation paths, communication templates, and recovery
> procedures. Tabletop was 2026-02-15 — artifact at
> s3://links-matrix-audit/ir-tabletop-2026-02.pdf, which includes the scenario,
> participant list, findings, and action items. IRT contacts were validated
> 2026-03-01 during the annual review."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — IR plan v4.2 in Confluence with 2026-03-01 ISSO review; tabletop artifact in S3; IRT contacts confirmed current

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | IR plan current with ISSO review; tabletop documented with outcome artifact; IRT contacts validated |
| Impact | Low | Structured plan with roles, escalation, and communication templates; annual tabletop validation |
| **Residual Risk** | **Low** | All SSP claims verified by Semgrep data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: IR plan v4.2 reviewed 2026-03-01 by ISSO; tabletop artifact and IRT contacts confirmed for IR-8.
CONTROL: IR-8 — Incident Response Plan
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - ISSO interview (plan version, review date, tabletop artifact path, IRT contact validation produced)
  - Semgrep query (ir-plan-v4.2 in Confluence, ISSO reviewed 2026-03-01, tabletop 2026-02-15, contacts current)
  - IR plan: Confluence: ir-plan-v4.2 (reviewed 2026-03-01, ISSO M.Chen)
  - Tabletop artifact: s3://links-matrix-audit/ir-tabletop-2026-02.pdf
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: ISSO (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Incident Response Plan is fully evidenced. IR plan v4.2 current with ISSO review, tabletop artifact with documented outcomes, and IRT contacts validated. This control is audit-ready.
```
