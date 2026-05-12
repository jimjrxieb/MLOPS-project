# Risk Assessment Evidence — CM Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** Evidence collected is partially sufficient. Control owners named specific
> tools and processes but could not produce exact artifacts, dates, or complete metrics. Tool
> queries returned partial data — some booleans confirmed but key counts and timestamps absent.
> All five controls receive PARTIAL findings requiring POA&M items to close the evidence gaps
> before the next audit cycle.

**Assessment Date:** 2026-05-10
**Assessor:** GRC Engineer (grc-engineer group — read-only)
**Framework:** NIST 800-53 Rev 5
**Graded Against:** Links-Matrix SSP (see ssp-examples/CM-ssp-great.md)

---

## CM-2 — Baseline Configuration

**Control Owner:** PlatEng
**Evidence Producer:** PlatEng
**Cadence:** Annual + change-triggered

### SSP Claim
> The SSP asserts that a baseline configuration document is maintained for the Kubernetes
> cluster and mapped to CIS Kubernetes 1.8 benchmarks. kube-bench runs automatically and
> results are stored in S3. The last kube-bench run achieved a score of 97/101 PASS.
> The baseline is stored in git: cluster-baseline/kube-bench-baseline.yaml.

### Evidence Request

**Interview — Questions asked of control owner (PlatEng):**
1. Show me your baseline configuration document.
2. Show me your last CIS benchmark run results.

**Tool Query:** `GET /evidence/CM-2?env=good` — simulates: kube-bench

**Tool Evidence (API Response):**
```json
{
  "control": "CM-2", "env": "good", "tool": "kube-bench",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "partial",
  "data": {
    "cis_benchmark_run": true,
    "cis_benchmark_version": "CIS Kubernetes 1.8",
    "baseline_config_artifact": "exists — not versioned in git",
    "last_run": null
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "kube-bench runs — it's the CIS Kubernetes 1.8 benchmark. The baseline config doc
> exists but it's not in git yet — it's a local file. I don't have the exact date
> of the last run but I know it completed. The score was somewhere in the 90s."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — kube-bench runs confirmed with CIS 1.8 benchmark; baseline not versioned in git; last run date and score not confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | kube-bench runs confirmed; baseline not in git means configuration drift may not be tracked |
| Impact | Medium | Unversioned baseline means changes cannot be audited; last run score unconfirmed |
| **Residual Risk** | **High** | Benchmark running but baseline documentation and run history gaps must be closed |

**Finding:** PARTIAL
**Evidence Gap:** Baseline configuration not versioned in git. Last run date not available. Score not confirmed. S3 artifact for results not produced.

**BERU Finding:**
```
FINDING: kube-bench runs with CIS Kubernetes 1.8 for CM-2 but the baseline is not versioned in git and the last run date and score were not produced.
CONTROL: CM-2 — Baseline Configuration
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (kube-bench running, baseline exists but unversioned)
  - kube-bench query (benchmark run true, CIS 1.8 version, baseline not in git, last run null)
EVIDENCE GAP: Baseline not versioned in git, last run date unavailable, score not confirmed, S3 artifact not produced
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: kube-bench is running but the baseline is not version-controlled and the last run results are not retrievable. Commit the baseline to git and produce the S3 scan artifact to close this finding.
```

---

## CM-3 — Configuration Change Control

**Control Owner:** PlatEng
**Evidence Producer:** PlatEng
**Cadence:** Continuous (PR gate)

### SSP Claim
> The SSP asserts that all configuration changes are gated by a PR review process with
> four-eyes enforcement via GitHub CODEOWNERS. kube-bench runs as a CI gate on every
> PR. ArgoCD drift detection alerts on unauthorized changes. Change approval records
> are stored in GitHub PR history.

### Evidence Request

**Interview — Questions asked of control owner (PlatEng):**
1. Show me how configuration changes are approved before deployment.

**Tool Query:** `GET /evidence/CM-3?env=good` — simulates: kube-bench

**Tool Evidence (API Response):**
```json
{
  "control": "CM-3", "env": "good", "tool": "kube-bench",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "partial",
  "data": {
    "pr_gate_config_scan": true,
    "change_approval_artifact": "JIRA tickets exist",
    "four_eyes_enforced": null
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "kube-bench runs in the CI gate on PRs. Change records are in JIRA. Four-eyes
> enforcement — I believe CODEOWNERS is configured but I'd need to check the exact
> state. ArgoCD drift detection is on but I don't have the alert configuration."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — kube-bench PR gate active; JIRA change records exist; four-eyes enforcement and ArgoCD drift detection not confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | CI gate active; JIRA records exist; four-eyes enforcement unconfirmed; drift detection unconfirmed |
| Impact | Medium | Without confirmed four-eyes enforcement, single-developer configuration changes are possible |
| **Residual Risk** | **High** | CI gate partially confirmed but four-eyes and drift detection gaps must be closed |

**Finding:** PARTIAL
**Evidence Gap:** Four-eyes enforcement (CODEOWNERS) not confirmed. ArgoCD drift detection alert configuration not produced. CODEOWNERS file not reviewed.

**BERU Finding:**
```
FINDING: kube-bench CI gate is active for CM-3 but four-eyes enforcement and ArgoCD drift detection configuration were not confirmed.
CONTROL: CM-3 — Configuration Change Control
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (CI gate described, CODEOWNERS uncertain, drift detection mentioned)
  - kube-bench query (pr_gate active, JIRA records exist, four_eyes_enforced null)
EVIDENCE GAP: Four-eyes enforcement (CODEOWNERS) not confirmed, ArgoCD drift detection configuration not produced
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: The kube-bench CI gate is running but four-eyes enforcement is unconfirmed. Verify CODEOWNERS configuration and produce the ArgoCD drift alert configuration to close this finding.
```

---

## CM-6 — Configuration Settings

**Control Owner:** SecEng
**Evidence Producer:** PlatEng
**Cadence:** Continuous (policy-as-code)

### SSP Claim
> The SSP asserts that all 101 CIS Kubernetes benchmark checks pass. 15 Kyverno policies
> enforce configuration settings at admission. The last kube-bench run on 2026-05-01 shows
> 0 failed checks. Results are stored at s3://links-matrix-audit/kube-bench/2026-05-01-report.json.

### Evidence Request

**Interview — Questions asked of control owner (PlatEng):**
1. Show me your current kube-bench failed checks and remediation plan.

**Tool Query:** `GET /evidence/CM-6?env=good` — simulates: kube-bench

**Tool Evidence (API Response):**
```json
{
  "control": "CM-6", "env": "good", "tool": "kube-bench",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:10:00Z", "status": "partial",
  "data": {
    "failed_checks": 14,
    "passed_checks": 87,
    "remediation_plan": null,
    "note": "14 failed checks not remediated"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "There are 14 failed kube-bench checks. We know about them but we don't have a
> formal remediation plan documented yet. Kyverno has some policies but I don't
> have the exact count. The failed checks are logged but I don't have the S3
> artifact path."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — kube-bench scan data exists; 14 failed checks conflict with SSP claim of 0 failures; remediation plan absent; Kyverno count unconfirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | 14 failed CIS checks confirmed; Kyverno count below SSP claim; no remediation plan |
| Impact | High | 14 open CIS failures represent known configuration weaknesses without remediation timeline |
| **Residual Risk** | **High** | Configuration settings posture partially known but 14 open failures without remediation plan is a material gap |

**Finding:** PARTIAL
**Evidence Gap:** 14 failed kube-bench checks with no remediation plan. Kyverno policy count not confirmed. S3 scan artifact path not provided.

**BERU Finding:**
```
FINDING: kube-bench scan shows 14 failed checks for CM-6; remediation plan absent and Kyverno policy count unconfirmed.
CONTROL: CM-6 — Configuration Settings
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (failed checks acknowledged, remediation plan absent)
  - kube-bench query (14 failed checks, 87 passed, remediation_plan null)
EVIDENCE GAP: 14 failed checks without remediation plan, Kyverno policy count unconfirmed, S3 artifact path not provided
RISK:
  Likelihood: Medium
  Impact: High
  Residual Risk: High
CONTROL OWNER: SecEng (accountability) / PlatEng (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: 14 CIS benchmark checks are failing and there is no remediation plan. Produce a remediation plan with target dates for each failed check and confirm the Kyverno policy count to close this finding.
```

---

## CM-7 — Least Functionality

**Control Owner:** PlatEng
**Evidence Producer:** SecEng
**Cadence:** Quarterly review

### SSP Claim
> The SSP asserts that unnecessary components are disabled: Kubernetes dashboard, alpha features,
> and anonymous auth. Enabled components are reviewed quarterly. Admission plugins are reviewed
> annually. The runtime syscall policy enforces Seccomp RuntimeDefault.

### Evidence Request

**Interview — Questions asked of control owner (SecEng):**
1. Show me the list of disabled components and justification for what remains enabled.

**Tool Query:** `GET /evidence/CM-7?env=good` — simulates: kube-bench

**Tool Evidence (API Response):**
```json
{
  "control": "CM-7", "env": "good", "tool": "kube-bench",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:15:00Z", "status": "partial",
  "data": {
    "disabled_components": ["dashboard"],
    "enabled_unnecessary_components": null,
    "note": "Partial inventory — not all components reviewed"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "The dashboard is disabled. Alpha features — I believe those are off but I'd
> need to confirm. Anonymous auth was disabled during initial setup. Admission
> plugin review was done once but I don't have the date or artifact. Seccomp
> is configured on most workloads."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — dashboard confirmed disabled; alpha features and anonymous auth not confirmed; admission plugin review date missing; Seccomp coverage not confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Dashboard disabled confirmed; alpha features and anonymous auth status unverified; component inventory partial |
| Impact | Medium | Unconfirmed component states mean potential attack surface remains |
| **Residual Risk** | **High** | Partial component inventory; alpha features and anonymous auth gaps must be confirmed |

**Finding:** PARTIAL
**Evidence Gap:** Alpha features and anonymous auth disable status not confirmed. Admission plugin review artifact not produced. Seccomp coverage on all workloads not confirmed.

**BERU Finding:**
```
FINDING: Dashboard disable confirmed for CM-7 but alpha features, anonymous auth, admission plugin review, and Seccomp coverage are not confirmed.
CONTROL: CM-7 — Least Functionality
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - SecEng verbal statement (dashboard disabled, other components uncertain)
  - kube-bench query (dashboard in disabled list, enabled_unnecessary_components null, partial inventory)
EVIDENCE GAP: Alpha features and anonymous auth disable not confirmed, admission plugin review artifact missing, Seccomp coverage not confirmed
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability) / SecEng (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Component disabling is partially evidenced. Confirm the status of alpha features and anonymous auth, produce the admission plugin review artifact, and verify Seccomp coverage to fully evidence CM-7.
```

---

## CM-8 — System Component Inventory

**Control Owner:** PlatEng
**Evidence Producer:** PlatEng
**Cadence:** Continuous

### SSP Claim
> The SSP asserts that a complete component inventory is maintained via Terraform and
> Kubescape. No untracked resources exist. Terraform drift detection is enabled. The
> inventory artifact is at terraform/inventory.tf with Kubescape generating a daily
> reconciliation report.

### Evidence Request

**Interview — Questions asked of control owner (PlatEng):**
1. Show me your component inventory and how it stays current.

**Tool Query:** `GET /evidence/CM-8?env=good` — simulates: kubescape

**Tool Evidence (API Response):**
```json
{
  "control": "CM-8", "env": "good", "tool": "kubescape",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:20:00Z", "status": "partial",
  "data": {
    "resource_inventory": "partial",
    "untracked_resources": null,
    "note": "Terraform drift not confirmed"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "We have Terraform for most resources. Kubescape runs but I'm not sure if inventory
> mode is configured. Drift detection — I believe it's on in ArgoCD but I haven't
> confirmed it catches everything. Untracked resources — I can't give you a count
> right now."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — Terraform and Kubescape described; inventory is partial; drift detection unconfirmed; untracked resource count unavailable

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Partial inventory confirmed; untracked resource count unknown; drift detection unconfirmed |
| Impact | Medium | Untracked resources could be running without patch management or monitoring |
| **Residual Risk** | **High** | Inventory exists but completeness and drift detection cannot be confirmed |

**Finding:** PARTIAL
**Evidence Gap:** Inventory is partial — completeness not confirmed. Untracked resource count unavailable. Terraform drift detection not confirmed. Kubescape inventory mode configuration not verified.

**BERU Finding:**
```
FINDING: Kubescape shows a partial inventory for CM-8; Terraform drift detection is unconfirmed and untracked resource count is unavailable.
CONTROL: CM-8 — System Component Inventory
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (Terraform and Kubescape described, drift detection uncertain)
  - Kubescape query (resource_inventory partial, untracked_resources null, drift not confirmed)
EVIDENCE GAP: Inventory completeness not confirmed, untracked resource count unavailable, Terraform drift detection not confirmed
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Component inventory is partially evidenced. Complete the Kubescape inventory scan, confirm Terraform drift detection, and produce a count of untracked resources to close this finding.
```
