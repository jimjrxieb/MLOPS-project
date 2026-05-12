# Risk Assessment Evidence — IR Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** Evidence collected for both Incident Response controls is incomplete
> and unverifiable. Control owners provided vague verbal assurances with no supporting artifacts.
> Tool queries returned null or error responses indicating incident response infrastructure
> is not deployed or not documented. Both findings are FAIL; both require POA&M items.

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

**Tool Query:** `GET /evidence/IR-4?env=bad` — simulates: falco

**Tool Evidence (API Response):**
```json
{
  "control": "IR-4", "env": "bad", "tool": "falco",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "incident_detection_rules": 0,
    "alert_routing": null,
    "error": "Falco not deployed"
  }
}
```

**Interview Response (Control Owner — IRT):**
> "We handle incidents when they come up. The SOC gets paged. I don't have
> the specific detection rules — Falco is on the roadmap. The escalation
> path exists but it's not written down formally. Tabletop — we did one
> maybe last year."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Falco not deployed; 0 detection rules; escalation path undocumented; tabletop date unconfirmed |
| Impact | High | Without automated detection, incidents will be discovered late or not at all |
| **Residual Risk** | **Critical** | Incident detection and handling capability is entirely unverifiable |

**Finding:** FAIL
**Evidence Gap:** Falco not deployed — zero detection rules. Alert routing not configured. Escalation path not documented. Tabletop exercise artifact not produced.

**BERU Finding:**
```
FINDING: Falco is not deployed and no incident detection rules, alert routing, or tabletop evidence can be produced for IR-4.
CONTROL: IR-4 — Incident Handling
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - IRT verbal statement (incident handling described, Falco roadmap, escalation undocumented)
  - Falco query (not deployed, 0 detection rules, alert_routing null)
EVIDENCE GAP: Falco not deployed, 0 detection rules, alert routing not configured, escalation path undocumented, tabletop artifact not produced
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: IRT (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Incident handling cannot be evidenced. Falco is not deployed, the escalation path is undocumented, and no tabletop exercise record was produced. Without automated detection, mean time to detect is undefined and incidents will be missed. Deploy Falco and document the escalation path immediately.
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

**Tool Query:** `GET /evidence/IR-8?env=bad` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "IR-8", "env": "bad", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "ir_plan_artifact": null,
    "last_review_date": null,
    "error": "IR plan document not found"
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "We have an IR plan. I'd have to find the link — it's in Confluence somewhere.
> Review date — I think it was reviewed recently but I don't have the exact date.
> The tabletop happened but the documentation is light."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | IR plan document not found; review date not confirmed; tabletop documentation not produced |
| Impact | High | Without an IR plan, incident response will be ad hoc and ineffective |
| **Residual Risk** | **Critical** | Incident response capability is entirely undocumented |

**Finding:** FAIL
**Evidence Gap:** IR plan document not found. Review date not confirmed. Approver not named. Tabletop artifact not produced.

**BERU Finding:**
```
FINDING: The IR plan document cannot be found and no review date or tabletop artifact can be produced for IR-8.
CONTROL: IR-8 — Incident Response Plan
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - ISSO verbal statement (IR plan described but location unknown, tabletop documentation light)
  - Semgrep query (ir_plan_artifact null, last_review_date null)
EVIDENCE GAP: IR plan document not found, review date not confirmed, approver not named, tabletop artifact not produced
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: ISSO (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: The Incident Response Plan cannot be located and the annual review cannot be confirmed. Without a documented IR plan and tabletop exercise, the organization cannot demonstrate a repeatable response capability. Locate the plan, confirm the review date, and produce the tabletop artifact before the next assessment.
```
