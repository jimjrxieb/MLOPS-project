# Risk Assessment Evidence — CM Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** Evidence collected for all five Configuration Management controls is
> incomplete and unverifiable. Control owners provided vague verbal assurances with no
> supporting artifacts. Tool queries returned null or error responses indicating configuration
> management tooling is not deployed or not configured. All five findings are FAIL; all
> require POA&M items.

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

**Tool Query:** `GET /evidence/CM-2?env=bad` — simulates: kube-bench

**Tool Evidence (API Response):**
```json
{
  "control": "CM-2", "env": "bad", "tool": "kube-bench",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "cis_benchmark_run": false,
    "baseline_config_artifact": null,
    "error": "kube-bench not deployed"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "We have a baseline. It's the standard Kubernetes setup. kube-bench is on the
> roadmap. I don't have the specific benchmark results but the cluster is configured
> securely."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | kube-bench not deployed; no benchmark results; no baseline configuration document produced |
| Impact | High | Without a verified baseline, configuration drift cannot be detected and security posture is unknown |
| **Residual Risk** | **Critical** | Baseline configuration is entirely undocumented and unverified |

**Finding:** FAIL
**Evidence Gap:** kube-bench not deployed. No CIS benchmark results. No baseline configuration document. No git reference for cluster-baseline.

**BERU Finding:**
```
FINDING: kube-bench is not deployed and no baseline configuration document or benchmark results can be produced for CM-2.
CONTROL: CM-2 — Baseline Configuration
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (baseline described but not documented, kube-bench roadmap)
  - kube-bench query (not deployed, no results, artifact null)
EVIDENCE GAP: No kube-bench deployment, no CIS benchmark results, no baseline configuration document, no git artifact
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Baseline configuration is not documented and CIS benchmarking has not been run. Without a verified baseline, configuration drift is undetectable. Deploy kube-bench, run the CIS Kubernetes benchmark, and store results in git before the next assessment.
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

**Tool Query:** `GET /evidence/CM-3?env=bad` — simulates: kube-bench

**Tool Evidence (API Response):**
```json
{
  "control": "CM-3", "env": "bad", "tool": "kube-bench",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "pr_gate_config_scan": false,
    "change_approval_artifact": null,
    "error": "No config change control evidence"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "We use pull requests. People review before merging. I don't think kube-bench is
> in the PR gate yet. CODEOWNERS — I'd have to check if it's configured."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | PR gate not configured; CODEOWNERS status unknown; no change approval artifact |
| Impact | High | Uncontrolled configuration changes can introduce vulnerabilities or cause service disruptions |
| **Residual Risk** | **Critical** | Configuration change control cannot be verified |

**Finding:** FAIL
**Evidence Gap:** PR CI gate for kube-bench not configured. CODEOWNERS configuration not confirmed. No change approval artifact produced.

**BERU Finding:**
```
FINDING: No configuration change control evidence — kube-bench PR gate not configured and CODEOWNERS status unknown for CM-3.
CONTROL: CM-3 — Configuration Change Control
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (PR process described, CI gate and CODEOWNERS unconfirmed)
  - kube-bench query (pr_gate_config_scan false, change_approval_artifact null)
EVIDENCE GAP: kube-bench PR gate not configured, CODEOWNERS not confirmed, no change approval artifact
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Configuration change control cannot be verified. The CI gate and four-eyes enforcement are not confirmed. Implement the kube-bench PR gate, configure CODEOWNERS, and produce change approval artifacts before the next assessment.
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

**Tool Query:** `GET /evidence/CM-6?env=bad` — simulates: kube-bench

**Tool Evidence (API Response):**
```json
{
  "control": "CM-6", "env": "bad", "tool": "kube-bench",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "failed_checks": null,
    "passed_checks": null,
    "error": "kube-bench scan results not available"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "The cluster is configured securely. I don't have the kube-bench results right now.
> Kyverno has some policies but I'd need to look up the count."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | No kube-bench results; failed check count unknown; Kyverno policy count unconfirmed |
| Impact | High | Unknown configuration settings mean CIS benchmark compliance is entirely unverifiable |
| **Residual Risk** | **Critical** | Configuration settings posture is undocumented and unverified |

**Finding:** FAIL
**Evidence Gap:** No kube-bench scan results. Failed check count unknown. Kyverno policy count and names not produced.

**BERU Finding:**
```
FINDING: kube-bench scan results are not available and Kyverno policy count is unconfirmed for CM-6.
CONTROL: CM-6 — Configuration Settings
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (security described, kube-bench results unavailable)
  - kube-bench query (scan results not available, failed_checks null, passed_checks null)
EVIDENCE GAP: No kube-bench results, failed check count unknown, Kyverno policy list not produced
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: SecEng (accountability) / PlatEng (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Configuration settings compliance cannot be verified. No kube-bench results and no Kyverno policy list were produced. Run kube-bench and produce the scan artifact before the next assessment.
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

**Tool Query:** `GET /evidence/CM-7?env=bad` — simulates: kube-bench

**Tool Evidence (API Response):**
```json
{
  "control": "CM-7", "env": "bad", "tool": "kube-bench",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "disabled_components": [],
    "enabled_unnecessary_components": null,
    "error": "Component inventory scan not run"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "We've disabled what we don't use. The dashboard might be off — I'd have to check.
> I don't have a formal component inventory document."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Component inventory scan not run; disabled component list empty; formal inventory not available |
| Impact | Medium | Enabled unnecessary components increase attack surface; without inventory, risk is unquantifiable |
| **Residual Risk** | **High** | Component functionality state entirely unverified |

**Finding:** FAIL
**Evidence Gap:** Component inventory scan not run. Disabled component list is empty. No formal component inventory document. Admission plugin review not produced.

**BERU Finding:**
```
FINDING: Component inventory scan has not been run and no disabled component list or formal inventory exists for CM-7.
CONTROL: CM-7 — Least Functionality
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - SecEng verbal statement (component disabling described, inventory not available)
  - kube-bench query (component inventory scan not run, disabled_components empty)
EVIDENCE GAP: No component inventory scan, disabled component list empty, no formal inventory document, admission plugin review not produced
RISK:
  Likelihood: High
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability) / SecEng (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Least functionality cannot be verified. No component inventory scan has been run and no formal inventory of disabled components exists. Run the kube-bench component check and document what is disabled and why before the next assessment.
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

**Tool Query:** `GET /evidence/CM-8?env=bad` — simulates: kubescape

**Tool Evidence (API Response):**
```json
{
  "control": "CM-8", "env": "bad", "tool": "kubescape",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "resource_inventory": null,
    "untracked_resources": null,
    "error": "Component inventory scan not available"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "We have Terraform for most things. Kubescape might be able to show the components
> but it's not set up for inventory tracking right now. I don't have a Terraform
> inventory file to point to."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Kubescape inventory not configured; no Terraform inventory artifact; untracked resources unknown |
| Impact | Medium | Without a component inventory, unmanaged resources go unmonitored and unpatchable |
| **Residual Risk** | **High** | Component inventory is entirely absent |

**Finding:** FAIL
**Evidence Gap:** Kubescape inventory not configured. No Terraform inventory artifact. Untracked resource count unknown.

**BERU Finding:**
```
FINDING: Kubescape inventory scan is not configured and no Terraform inventory artifact exists for CM-8.
CONTROL: CM-8 — System Component Inventory
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (Terraform described, Kubescape inventory not configured)
  - Kubescape query (inventory scan not available, resource_inventory null)
EVIDENCE GAP: Kubescape inventory not configured, no Terraform inventory artifact, untracked resource count unknown
RISK:
  Likelihood: High
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: System component inventory cannot be evidenced. Kubescape is not configured for inventory tracking and no Terraform inventory artifact was produced. Configure automated inventory and reconciliation before the next assessment.
```
