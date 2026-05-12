# Risk Assessment Evidence — PL Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Evidence collected fully supports the SSP claim. The control owner produced
> the exact artifact location, version number, review date, approvers, ATO dates, and change-
> trigger process on first request. The tool query returned complete structured data with no
> gaps. The control receives a PASS finding. No POA&M item required. This is the evidence
> standard a 3PAO expects to walk in and find.

**Assessment Date:** 2026-05-10
**Assessor:** GRC Engineer (grc-engineer group — read-only)
**Framework:** NIST 800-53 Rev 5
**Graded Against:** Links-Matrix SSP (see ssp-examples/PL-ssp-great.md)

---

## PL-2 — System Security and Privacy Plan

**Control Owner:** ISSO
**Evidence Producer:** ISSO
**Cadence:** Annual review + change-triggered

### SSP Claim
> The SSP asserts that the System Security Plan (v7.1) is maintained in Confluence and
> was last reviewed 2026-04-15 by the System Owner and ISSO. ATO was granted 2025-11-01
> and expires 2028-11-01. Change-triggered reviews are initiated automatically when
> significant environment changes occur.

### Evidence Request

**Interview — Questions asked of control owner (ISSO):**
1. Show me the SSP — current version, last review date, and approvers.
2. Show me the change-trigger review process.

**Tool Query:** `GET /evidence/PL-2?env=great` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "PL-2", "env": "great", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "sufficient",
  "data": {
    "ssp_artifact": "Confluence: links-matrix-ssp-v7.1 (ATO granted 2025-11-01, expires 2028-11-01)",
    "last_reviewed": "2026-04-15",
    "review_approver": "SO + ISSO",
    "change_trigger_review": true
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "SSP v7.1 is at Confluence: links-matrix-ssp-v7.1. Last reviewed 2026-04-15 by
> System Owner K.Patel and myself (ISSO M.Chen). ATO granted 2025-11-01 by the
> Authorizing Official, expires 2028-11-01 — letter is at
> s3://links-matrix-audit/ato-letter-2025-11-01.pdf. Change-trigger review is
> automated via a Confluence webhook — any pull request tagged 'significant-change'
> triggers an SSP review ticket in JIRA assigned to the ISSO."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — SSP v7.1 in Confluence with 2026-04-15 review; SO and ISSO approvals confirmed; ATO dates confirmed; change-trigger mechanism described

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | SSP v7.1 current with SO and ISSO review; ATO within validity; change-trigger automated |
| Impact | Low | SSP in assessor-accessible Confluence; ATO letter retrievable; change-trigger documented |
| **Residual Risk** | **Low** | All SSP claims verified by Semgrep data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: SSP v7.1 reviewed 2026-04-15 by SO + ISSO; ATO confirmed 2025-11-01 to 2028-11-01; change-trigger automated for PL-2.
CONTROL: PL-2 — System Security and Privacy Plan
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - ISSO interview (SSP Confluence path, review date, approvers, ATO dates, change-trigger mechanism produced)
  - Semgrep query (SSP v7.1 in Confluence, last_reviewed 2026-04-15, SO+ISSO approvers, change_trigger true)
  - SSP: Confluence: links-matrix-ssp-v7.1 (reviewed 2026-04-15, SO K.Patel + ISSO M.Chen)
  - ATO letter: s3://links-matrix-audit/ato-letter-2025-11-01.pdf (granted 2025-11-01, expires 2028-11-01)
  - Change-trigger: Confluence webhook → JIRA ticket for 'significant-change' PRs
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: ISSO (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: The System Security Plan is fully evidenced. SSP v7.1 current with SO and ISSO review, ATO valid through 2028-11-01, and change-trigger process automated. This control is audit-ready.
```
