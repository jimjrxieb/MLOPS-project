# Risk Assessment Evidence — CM Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Evidence collected fully supports all SSP claims. Control owners provided
> exact artifacts, dates, version numbers, and metrics on first request. Tool queries returned
> complete structured data with no gaps. Every SSP claim is traceable to a specific artifact
> with a retrievable location. All five controls receive PASS findings. No POA&M items required.
> This is the evidence standard a 3PAO expects to walk in and find.

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

**Tool Query:** `GET /evidence/CM-2?env=great` — simulates: kube-bench

**Tool Evidence (API Response):**
```json
{
  "control": "CM-2", "env": "great", "tool": "kube-bench",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "sufficient",
  "data": {
    "cis_benchmark_run": true,
    "cis_benchmark_version": "CIS Kubernetes 1.8",
    "baseline_config_artifact": "git: cluster-baseline/kube-bench-baseline.yaml (main branch)",
    "last_run": "2026-05-01T06:00:00Z",
    "score": "97/101 PASS"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "Last kube-bench run: 2026-05-01T06:00:00Z, score 97/101 PASS. Results are at
> s3://links-matrix-audit/kube-bench/2026-05-01-report.json. The baseline document
> is at git: cluster-baseline/kube-bench-baseline.yaml on the main branch — updated
> any time a check remediation is merged. The 4 informational items are documented
> exceptions in cluster-baseline/exceptions.md."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 97/101 PASS confirmed; baseline in git; last run timestamp and S3 artifact location produced

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 97/101 CIS checks passing; baseline version-controlled; automated runs with S3 results |
| Impact | Low | 4 exceptions documented; baseline in git ensures drift detection via PR reviews |
| **Residual Risk** | **Low** | All SSP claims verified by kube-bench data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: kube-bench run 2026-05-01 confirms 97/101 PASS with baseline in git for CM-2. S3 artifact produced.
CONTROL: CM-2 — Baseline Configuration
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - PlatEng interview (run timestamp, score, S3 artifact path, git baseline reference produced)
  - kube-bench query (CIS 1.8, 97/101 PASS, last_run 2026-05-01, baseline in git)
  - Scan artifact: s3://links-matrix-audit/kube-bench/2026-05-01-report.json
  - Baseline: git: cluster-baseline/kube-bench-baseline.yaml (main branch)
  - Exceptions: cluster-baseline/exceptions.md (4 informational items documented)
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Baseline configuration is fully evidenced. 97/101 CIS Kubernetes 1.8 checks passing, baseline version-controlled in git, and automated runs with S3 archival. This control is audit-ready.
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

**Tool Query:** `GET /evidence/CM-3?env=great` — simulates: kube-bench

**Tool Evidence (API Response):**
```json
{
  "control": "CM-3", "env": "great", "tool": "kube-bench",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "sufficient",
  "data": {
    "pr_gate_config_scan": true,
    "ci_tool": "GitHub Actions — kube-bench-gate.yaml",
    "four_eyes_enforced": true,
    "change_approval_artifact": "GitHub: branch protection + CODEOWNERS",
    "drift_detection": "ArgoCD auto-sync with diff alerts"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "Every configuration change goes through a PR. CI gate runs kube-bench via
> kube-bench-gate.yaml in GitHub Actions — PR blocks if any new failures appear.
> CODEOWNERS requires at least one security team approval. Branch protection enforces
> four-eyes with no bypass. ArgoCD drift detection sends Slack alerts to #platform-alerts
> within 5 minutes of any out-of-band change. Change history is in GitHub PR audit log."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — kube-bench CI gate active; CODEOWNERS four-eyes confirmed; ArgoCD drift detection confirmed; PR audit trail available

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | kube-bench PR gate blocks new failures; CODEOWNERS enforces four-eyes; ArgoCD drift detection active |
| Impact | Low | Unauthorized configuration changes detected within 5 minutes and blocked at PR |
| **Residual Risk** | **Low** | All SSP claims verified by CI configuration and change approval artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: kube-bench CI gate, CODEOWNERS four-eyes, and ArgoCD drift detection all confirmed for CM-3.
CONTROL: CM-3 — Configuration Change Control
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - PlatEng interview (CI tool name, CODEOWNERS policy, ArgoCD alert configuration produced)
  - kube-bench query (pr_gate active, GitHub Actions kube-bench-gate.yaml, four_eyes enforced, drift detection)
  - CI gate: GitHub Actions kube-bench-gate.yaml
  - Four-eyes: GitHub branch protection + CODEOWNERS (security team approval required)
  - Drift detection: ArgoCD auto-sync with diff alerts to #platform-alerts (5 min SLA)
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Configuration change control is fully implemented. kube-bench CI gate, four-eyes CODEOWNERS enforcement, and ArgoCD drift detection provide layered change control. This control is audit-ready.
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

**Tool Query:** `GET /evidence/CM-6?env=great` — simulates: kube-bench

**Tool Evidence (API Response):**
```json
{
  "control": "CM-6", "env": "great", "tool": "kube-bench",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:10:00Z", "status": "sufficient",
  "data": {
    "failed_checks": 0,
    "passed_checks": 101,
    "last_remediation": "2026-04-20",
    "kyverno_policies_enforcing": 15,
    "report_artifact": "s3://links-matrix-audit/kube-bench/2026-05-01-report.json"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "0 failed checks — all 101 CIS Kubernetes 1.8 checks pass as of 2026-05-01. Last
> remediation was 2026-04-20 — we fixed the etcd peer cert issue. Report is at
> s3://links-matrix-audit/kube-bench/2026-05-01-report.json. 15 Kyverno policies
> enforce the configuration at admission — list is in platform-gitops/policies/cm/."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 101/101 CIS checks passing; 15 Kyverno policies confirmed; report artifact in S3; last remediation dated

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 0 failed CIS checks; 15 Kyverno policies enforce at admission; automated runs with S3 results |
| Impact | Low | All benchmark checks pass; admission control prevents regression; S3 audit trail available |
| **Residual Risk** | **Low** | All SSP claims verified by kube-bench data and Kyverno policy count |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 0 failed kube-bench checks and 15 Kyverno policies confirmed for CM-6. S3 artifact produced.
CONTROL: CM-6 — Configuration Settings
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - PlatEng interview (0 failures, last remediation date, Kyverno policy count and location produced)
  - kube-bench query (0 failed, 101 passed, last_remediation 2026-04-20, 15 Kyverno policies)
  - Report artifact: s3://links-matrix-audit/kube-bench/2026-05-01-report.json
  - Kyverno policies: platform-gitops/policies/cm/ (15 policies)
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: SecEng (accountability) / PlatEng (evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Configuration settings are fully compliant. All 101 CIS Kubernetes 1.8 checks pass, 15 Kyverno policies enforce at admission, and S3 audit artifacts are available. This control is audit-ready.
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

**Tool Query:** `GET /evidence/CM-7?env=great` — simulates: kube-bench

**Tool Evidence (API Response):**
```json
{
  "control": "CM-7", "env": "great", "tool": "kube-bench",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:15:00Z", "status": "sufficient",
  "data": {
    "disabled_components": ["dashboard", "alpha-features", "anonymous-auth"],
    "enabled_unnecessary_components": [],
    "admission_plugins_review_date": "2026-03-01",
    "runtime_syscall_policy": "Seccomp RuntimeDefault + Falco"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "Disabled: Kubernetes dashboard, alpha features, anonymous auth — confirmed by
> kube-bench checks 1.2.1 and 1.2.2. 0 enabled unnecessary components. Admission
> plugin review was 2026-03-01 — artifact in platform-gitops/security/admission-review-2026-Q1.md.
> Seccomp RuntimeDefault is enforced via Kyverno policy require-seccomp.yaml and
> Falco provides supplemental syscall monitoring."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — all three components disabled confirmed by kube-bench; admission plugin review artifact dated; Seccomp enforcement policy named

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | All unnecessary components disabled by kube-bench confirmation; 0 unnecessary enabled; Seccomp enforced |
| Impact | Low | Admission plugin review current; Falco supplemental coverage; Kyverno policy enforcement |
| **Residual Risk** | **Low** | All SSP claims verified by kube-bench data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: Dashboard, alpha features, and anonymous auth disabled confirmed by kube-bench for CM-7. Admission plugin review and Seccomp enforcement artifacts produced.
CONTROL: CM-7 — Least Functionality
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - SecEng interview (disabled component list, admission review date and location, Seccomp policy name produced)
  - kube-bench query (3 components disabled, 0 unnecessary enabled, admission review 2026-03-01, Seccomp enforced)
  - Admission review: platform-gitops/security/admission-review-2026-Q1.md (2026-03-01)
  - Seccomp policy: Kyverno require-seccomp.yaml + Falco supplemental syscall monitoring
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: PlatEng (accountability) / SecEng (evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Least functionality is fully implemented and evidenced. All unnecessary components are disabled, admission plugins reviewed, and Seccomp enforced at admission. This control is audit-ready.
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

**Tool Query:** `GET /evidence/CM-8?env=great` — simulates: kubescape

**Tool Evidence (API Response):**
```json
{
  "control": "CM-8", "env": "great", "tool": "kubescape",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:20:00Z", "status": "sufficient",
  "data": {
    "resource_inventory": "complete",
    "untracked_resources": 0,
    "terraform_drift": false,
    "inventory_artifact": "terraform/inventory.tf + kubescape report 2026-05-01"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "0 untracked resources — Kubescape daily reconciliation confirms. Terraform inventory
> is at terraform/inventory.tf — every resource has a corresponding Terraform resource
> block. Terraform drift detection runs via a daily plan check; last run 2026-05-01
> shows no drift. Kubescape report for 2026-05-01 is at
> s3://links-matrix-audit/kubescape/2026-05-01-inventory.json."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 0 untracked resources; Terraform drift false; inventory artifacts in both Terraform and Kubescape; daily reconciliation confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 0 untracked resources; Terraform drift detection daily; Kubescape reconciliation automated |
| Impact | Low | Complete inventory enables patch management and monitoring for all components |
| **Residual Risk** | **Low** | All SSP claims verified by Kubescape data and Terraform artifact |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 0 untracked resources and no Terraform drift confirmed by Kubescape daily reconciliation for CM-8. Inventory artifacts produced.
CONTROL: CM-8 — System Component Inventory
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - PlatEng interview (0 untracked resources, Terraform drift date, inventory artifact locations produced)
  - Kubescape query (resource_inventory complete, 0 untracked, Terraform drift false)
  - Terraform inventory: terraform/inventory.tf (all resources tracked)
  - Kubescape report: s3://links-matrix-audit/kubescape/2026-05-01-inventory.json
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: System component inventory is complete and continuously maintained. Zero untracked resources, daily Kubescape reconciliation, and Terraform drift detection. This control is audit-ready.
```
