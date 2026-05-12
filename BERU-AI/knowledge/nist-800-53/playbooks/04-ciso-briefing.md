# BERU — Produce CISO Briefing

> Input: all completed BERU findings from one or more family playbooks
> Output: one-page executive summary + risk table + recommended actions
> Audience: CISO or executive sponsor — no NIST IDs, no acronyms without explanation
> Save to: `GP-S3/5-consulting-reports/<instance>/<slot>/CISO-BRIEF-YYYY-MM-DD.md`

---

## When to Run This Playbook

- CISO asks "are we compliant with NIST 800-53?"
- End of a 3POA engagement
- Quarterly compliance review
- Before a FedRAMP audit
- After a significant finding is resolved

---

## Step 1 — Aggregate All Findings

```bash
BRIEF_DIR="GP-S3/5-consulting-reports/$(date +%Y-%m-%d)-ciso-brief"
mkdir -p $BRIEF_DIR

# Collect all finding files from this engagement
FINDINGS_DIR="GP-S3/6-seclab-reports/cybersec-evidence/beru-findings"

# Count by status
echo "=== Finding Summary ===" > $BRIEF_DIR/summary.txt
grep -h "^STATUS:" $FINDINGS_DIR/*.md 2>/dev/null | sort | uniq -c >> $BRIEF_DIR/summary.txt

# Count by rank
echo "=== Risk Rank Summary ===" >> $BRIEF_DIR/summary.txt
grep -h "→ Rank:" $FINDINGS_DIR/*.md 2>/dev/null | sort | uniq -c >> $BRIEF_DIR/summary.txt
```

---

## Step 2 — Write the Executive Summary

One paragraph. Business language. Answer these three questions in order:

1. **What did we look at?** (scope — not tool names, but what the tools examined)
2. **What is the overall posture?** (quantified — N controls PASS, N PARTIAL, N FAIL)
3. **What is the most important thing to fix?** (the highest-rank finding in plain language)

Template:
```text
We assessed [N] security controls across [the cluster configuration, cloud access controls,
data protection, runtime monitoring, and/or AI workloads] of [system name] against the
NIST 800-53 Rev 5 standard. Of the controls assessed:

  [N] are fully implemented with documented evidence — no action required.
  [N] are partially implemented — documented gaps with remediation plans attached.
  [N] are not implemented or lack evidence — require action before [audit/go-live/deadline].

The highest-priority finding is [finding in plain language: e.g., "three production
systems have administrator-level access that is broader than what they need — if any of
these systems is compromised, an attacker would have control over the entire environment"].
Remediation requires approximately [N hours/days] of engineering time and is tracked in
the attached remediation plan.
```

---

## Step 3 — Write the Risk Table

One row per PARTIAL or FAIL finding, sorted by rank (S first, then B, C, D, E).

Business language only. No control IDs in this table.

```markdown
| Risk | What It Means in Plain Language | Likelihood | Impact | Rank | Remediation Time |
| --- | --- | --- | --- | --- | --- |
| [Plain-language risk] | [What goes wrong if not fixed] | High/Med/Low | High/Med/Low | S/B/C/D | [N days] |
```

Example rows:
```markdown
| Admin-level access on production systems | If any production service is compromised, attacker controls the entire environment | High | High | B | 14 days |
| Container images not verified before deployment | Malicious or tampered images could run in production without detection | Medium | High | C | 7 days |
| Audit logs not reviewed on schedule | Intrusions may go undetected for weeks | Medium | Medium | C | 3 days |
| Backup recovery not tested | If a ransomware event occurs, recovery time and data loss are unknown | Low | High | C | 30 days |
```

---

## Step 4 — Write the Recommended Actions

Three to five actions, ordered by priority. Each action names who does it and by when.

```text
1. [IMMEDIATE — B-rank] [Action in plain language]
   Owner: [role, not name]
   By: [date]
   Estimated effort: [N hours]

2. [TWO WEEKS — C-rank] [Action]
   Owner: [role]
   By: [date]
   Estimated effort: [N hours]

3. [THIRTY DAYS — C-rank] [Action]
   Owner: [role]
   By: [date]
   Estimated effort: [N hours]
```

---

## Step 5 — Attach the Evidence Package

Reference the evidence paths at the bottom of the briefing — the CISO does not need to read them, but they must exist for auditor use.

```text
## Evidence Package

All findings are documented with supporting evidence at:
  GP-S3/6-seclab-reports/cybersec-evidence/beru-findings/[DATE]-[FAMILY]/

POA&M items: GP-S3/6-seclab-reports/cybersec-evidence/poam/POAM-[YYYY-MM].md

SSP narratives: GP-S3/6-seclab-reports/cybersec-evidence/ssp-narratives/[DATE]-SSP-*.md

This assessment was conducted on [DATE] by [BERU / assessor name].
Evidence is valid for 90 days from collection date.
Next assessment recommended: [DATE + 90 days or 12 months depending on scope].
```

---

## Step 6 — CISO Briefing Quality Check

Before delivering:

- [ ] No NIST control IDs in the executive summary or risk table (spell out what the control means)
- [ ] No tool names without plain-language context ("Kyverno policy enforcement" → "automated rules that prevent misconfigured systems from being deployed")
- [ ] Every risk has a plain-language consequence (not "AC-6(5) violation" → "an attacker who compromises X gains access to everything")
- [ ] Every recommended action names a specific owner role and date
- [ ] Evidence package paths are all reachable (spot-check two files)
- [ ] The executive summary answers: what did we look at, what did we find, what matters most

---

## CISO Briefing Hard Stops

```text
NEVER use NIST control IDs as the primary language in the executive summary.
NEVER present a FAIL finding without a remediation timeline.
NEVER claim the environment is "compliant" — compliance is a point-in-time assessment.
  Use: "As of [DATE], [N of N] assessed controls are fully implemented."
NEVER omit the evidence package reference — claims without evidence are claims, not findings.
NEVER make remediation decisions in the briefing — present options and costs, J decides.
```

---

## Sample CISO Briefing (Condensed)

```text
# Security Control Assessment — Executive Summary
Date: 2026-05-06 | Assessed By: BERU (GP-Copilot NIST-800-53 Auditor)
System: jsa-staging cluster + AWS account 123456789

## What We Looked At
We assessed 28 security controls across cluster configuration, identity and access
management, data encryption, runtime monitoring, and incident response for the
jsa-staging environment.

## What We Found
  19 controls: fully implemented with evidence — no action required.
   6 controls: partially implemented — gaps documented with remediation plans.
   3 controls: not yet implemented — require action before FedRAMP assessment.

The most urgent finding: three production systems have administrator-level Kubernetes
access beyond what they require. If any of those systems is compromised, an attacker
gains full control of all 12 services in the environment. Remediation takes approximately
8 hours of engineering time.

## Risk Table
| Risk | Consequence | Rank | By When |
|------|-------------|------|---------|
| Overly broad admin access on 3 production services | Full cluster compromise from single breach | B | May 20 |
| Container images not signed before deployment | Tampered image could run in production undetected | C | May 13 |
| Backups not tested for recovery | Unknown recovery time in a ransomware event | C | Jun 5 |

## Recommended Actions
1. [B-rank] Scope down the three over-privileged services to minimum required access.
   Owner: Platform Engineering. By: May 20. Effort: ~8 hours.

2. [C-rank] Enable image signature enforcement in production Kubernetes.
   Owner: DevSecOps. By: May 13. Effort: ~3 hours.

3. [C-rank] Run a full backup restore test and document recovery time.
   Owner: IT Operations. By: June 5. Effort: ~4 hours.

Evidence: GP-S3/6-seclab-reports/cybersec-evidence/beru-findings/2026-05-06-*/
POA&M: GP-S3/6-seclab-reports/cybersec-evidence/poam/POAM-2026-05.md
Next assessment: August 2026
```
