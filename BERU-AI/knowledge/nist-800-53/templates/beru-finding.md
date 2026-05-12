# BERU Finding — Output Template

> Fill one copy of this template per finding. Do not combine multiple findings into one entry.
> Save completed findings to: `GP-S3/6-seclab-reports/cybersec-evidence/beru-findings/`

---

```text
FINDING: [one sentence — what is the observed condition, from scanner output or evidence review]

CONTROL: [NIST family-number — Control Name]
  Example: AC-6 — Least Privilege

ENHANCEMENT: [family-number(x) — Enhancement Name] | None
  Example: AC-6(5) — Privileged Accounts

STATUS: PASS | PARTIAL | FAIL
  PASS    = documented + implemented + evidence provided + live validation succeeds
  PARTIAL = implemented but gaps in documentation or coverage
  FAIL    = not implemented, or implemented without evidence

EVIDENCE REVIEWED:
  [bullet list of what was examined]
  - [artifact name, path, or command output reviewed]
  - [policy document / config / scan result]
  - [date of evidence]

EVIDENCE GAP:
  [what is missing for a full PASS — be specific, never write "investigate further"]
  None | [specific artifact, command, or documentation missing]

RISK:
  Likelihood: Low | Medium | High
  Impact:     Low | Medium | High
  → Rank: E | D | C | B | S
  Justification: [one sentence on why this likelihood × impact]

CONTROL OWNER:
  [role from control-owner-matrix.md]
  Example: PlatEng (K8s RBAC) | SOC | CloudSec | DevSecOps | ISSO

POA&M ITEM: N/A | [use template: templates/poam-item.md]
  Weakness:             [what is not implemented or not documented]
  Scheduled Completion: [YYYY-MM-DD]
  Milestones:
    M1: [YYYY-MM-DD] [action]
    M2: [YYYY-MM-DD] [action]
  Remediation Owner:    [role]

CISO SUMMARY:
  [one paragraph, business risk language, no NIST jargon, no acronym soup]
  [Answer: what could go wrong, how likely, what it costs the business]
```

---

## Quick Reference — Rank Criteria

| Rank | Meaning | Example |
| --- | --- | --- |
| E | Auto-fix, no approval needed | Missing security context on a dev pod |
| D | Auto-fix + log | Unpinned image tag in a non-prod deployment |
| C | Propose + wait for approval | Wildcard RBAC on a production service account |
| B | Human decides, JADE provides intel | cluster-admin binding in production |
| S | Human only, JADE provides dashboard | Compromise of a signing key or IAM root account |

## Quick Reference — CISO Summary Pattern

Do not write: "AC-6(5) is violated because cluster-admin service accounts exist."

Write: "Three production service accounts have administrator-level access to the entire cluster.
If any application using those accounts is compromised, an attacker gains full control of every
workload, secret, and configuration in the environment. Estimated remediation: 4 hours to scope
down to needed permissions. Risk of not fixing: data breach blast radius extends to all 12 services
in the cluster."
