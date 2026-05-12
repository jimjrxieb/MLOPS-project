# Risk Assessment Evidence — PL Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** Evidence collected for the Planning control is incomplete and unverifiable.
> The control owner provided a vague verbal assurance with no supporting artifact. The tool
> query returned a null response indicating the SSP document is not accessible or does not
> exist in a retrievable form. The finding is FAIL; a POA&M item is required.

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

**Tool Query:** `GET /evidence/PL-2?env=bad` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "PL-2", "env": "bad", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "ssp_artifact": null,
    "last_reviewed": null,
    "error": "SSP document not accessible"
  }
}
```

**Interview Response (Control Owner — ISSO):**
> "We have an SSP. I'd have to find where it's stored — it might be in SharePoint
> or Confluence. The last review was some time ago. ATO — yes, we have one.
> I don't have the exact dates."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | SSP document not accessible; version not confirmed; review date and approvers not produced |
| Impact | High | Without an accessible SSP, the authorization basis for the system cannot be confirmed |
| **Residual Risk** | **Critical** | The system security plan cannot be evidenced |

**Finding:** FAIL
**Evidence Gap:** SSP document not accessible. Version not confirmed. Review date not confirmed. Approvers not named. ATO dates not confirmed. Change-trigger process not described.

**BERU Finding:**
```
FINDING: The SSP document is not accessible and no version, review date, or approver can be confirmed for PL-2.
CONTROL: PL-2 — System Security and Privacy Plan
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - ISSO verbal statement (SSP described, location unknown, dates unknown)
  - Semgrep query (ssp_artifact null, last_reviewed null)
EVIDENCE GAP: SSP document not accessible, version not confirmed, review date and approvers not named, ATO dates not confirmed, change-trigger process not described
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: ISSO (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: The System Security Plan cannot be produced. Without an accessible, versioned SSP with confirmed review dates and ATO information, the system's authorization basis is unverifiable. Locate the SSP, confirm its location in Confluence, and produce the review artifact before the next assessment.
```
