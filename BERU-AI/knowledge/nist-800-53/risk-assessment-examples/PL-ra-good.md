# Risk Assessment Evidence — PL Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** Evidence collected is partially sufficient. The control owner named a
> specific tool and process but could not produce the exact artifact, current version number,
> or confirmed review date. The tool query returned partial data — SSP exists but review
> currency is unconfirmed. The control receives a PARTIAL finding requiring a POA&M item
> to close the evidence gap before the next audit cycle.

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

**Tool Query:** `GET /evidence/PL-2?env=good` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "PL-2", "env": "good", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "partial",
  "data": {
    "ssp_artifact": "SharePoint — access restricted",
    "last_reviewed": "2025",
    "note": "SSP exists but last review date unconfirmed"
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "The SSP is in SharePoint. I can get you access but it requires a separate request.
> Last review was in 2025 — I don't have the exact month. Version — I think it's
> around v7 but I'd need to pull it. ATO was granted — yes, in late 2025. Change-
> trigger process is documented somewhere in the policies but I don't have the link."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — SSP exists in SharePoint; review date imprecise; version not confirmed; ATO dates not confirmed; change-trigger process not produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | SSP exists but review date imprecise; access restricted; version and ATO dates unconfirmed |
| Impact | Medium | Without confirmed review date and version, SSP currency is unverifiable for audit purposes |
| **Residual Risk** | **High** | SSP exists but evidence package insufficient for auditor review |

**Finding:** PARTIAL
**Evidence Gap:** SSP review date imprecise. Version not confirmed. ATO dates not confirmed. SharePoint access restricted for assessor. Change-trigger process not produced.

**BERU Finding:**
```
FINDING: SSP exists in SharePoint for PL-2 but review date is imprecise, version is unconfirmed, and assessor access is restricted.
CONTROL: PL-2 — System Security and Privacy Plan
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - ISSO verbal statement (SSP in SharePoint, 2025 review, version approximately 7, ATO unconfirmed)
  - Semgrep query (ssp_artifact in SharePoint, access restricted, last_reviewed 2025 imprecise)
EVIDENCE GAP: SSP review date imprecise, version not confirmed, ATO dates not confirmed, assessor access restricted, change-trigger process not produced
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: ISSO (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: The SSP exists but cannot be reviewed by the assessor due to access restrictions. Move the SSP to Confluence, confirm the version and review date, and produce the ATO dates to close this finding.
```
