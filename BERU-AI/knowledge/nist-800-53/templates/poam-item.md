# POA&M Item Template

> Plan of Action and Milestones — one item per NIST control finding.
> BERU writes these. JADE/DevSecOps execute them. J approves B/S-rank closures.
> Save to: `GP-S3/6-seclab-reports/cybersec-evidence/poam/POAM-[YYYY-MM].md`

---

## POA&M Item [Sequential Number]

```text
POAM-ID:          POAM-[YYYY-MM]-[NNN]
  Example:        POAM-2026-05-001

CONTROL:          [NIST ID + Name]
  Example:        AC-6(5) — Privileged Accounts

WEAKNESS:
  [Describe what is not implemented or not documented. One to three sentences.
   Be specific — name the resource, policy, or artifact that is missing.]

SYSTEM AFFECTED:  [cluster name / AWS account / application / all]

SEVERITY:         Low | Medium | High | Critical
GP-RANK:          E | D | C | B | S

DETECTION DATE:   [YYYY-MM-DD]
DETECTION METHOD: [scanner name + command, or manual review]
  Example:        kubectl get clusterrolebindings -o yaml | grep cluster-admin

EVIDENCE PATH:
  [path where evidence artifact is saved]
  Example: GP-S3/6-seclab-reports/cybersec-evidence/scans/rbac-audit-2026-05-01.txt

REMEDIATION OWNER: [role — PlatEng | CloudSec | DevSecOps | SOC]

SCHEDULED COMPLETION: [YYYY-MM-DD]

MILESTONES:
  M1: [YYYY-MM-DD] [specific action — e.g., "Scope service account X to verbs: get, list"]
  M2: [YYYY-MM-DD] [specific action — e.g., "Re-run rbac-lookup and attach output as evidence"]
  M3: [YYYY-MM-DD] [specific action — e.g., "BERU re-assesses, updates status to PASS"]

REMEDIATION APPROACH:
  [One paragraph. What specifically gets changed, what tool implements it,
   how it will be validated. Reference the fixer script if one exists.]
  Fixer: GP-CONSULTING/DEVOPS-LENS/02-CLUSTER-HARDEN/02-fixers/[category]/[script].sh

VALIDATION COMMAND:
  [Exact command to verify the fix is implemented]
  Expected output: [what a clean result looks like]

RESIDUAL RISK AFTER REMEDIATION: [if any — what the fix does NOT cover]

STATUS HISTORY:
  [YYYY-MM-DD] OPEN — [brief reason]
  [YYYY-MM-DD] IN PROGRESS — [milestone reached]
  [YYYY-MM-DD] CLOSED — [validation confirmed by BERU]
```

---

## POAM Status Definitions

| Status | Meaning |
| --- | --- |
| OPEN | Finding documented, remediation not started |
| IN PROGRESS | Remediation started, milestone 1+ complete |
| RISK ACCEPTED | J approved risk acceptance (B/S rank only) |
| CLOSED | Validation passed, BERU confirmed |

## Closure Criteria

A POA&M item is only CLOSED when:
1. The remediation action was applied.
2. The validation command returns the expected output.
3. BERU re-runs the original detection and gets a clean result.
4. Evidence path is updated with the post-fix scan artifact.

BERU writes the closure note. JADE or DevSecOps does not self-certify closure.
