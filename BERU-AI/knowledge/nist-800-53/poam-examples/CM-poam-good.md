# POA&M — Configuration Management (CM) Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** POA&M items reflect specific evidence gaps from the BERU assessment.
> Control owners are identified by role. Due dates follow severity-based priority tiers.
> Milestones cover M1 and M2 with actionable steps. Validation commands are real tool queries.
> Residual risk is acknowledged but remains generic. Status history includes opening reason.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** CM-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-015 | CM-2 — Baseline Configuration | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-016 | CM-3 — Configuration Change Control | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-017 | CM-6 — Configuration Settings | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-018 | CM-7 — Least Functionality | High | P2 30 Days | 2026-06-09 |
| POAM-2026-05-019 | CM-8 — System Component Inventory | High | P2 30 Days | 2026-06-09 |

---

## POAM-2026-05-015 — CM-2

```text
POAM-ID:          POAM-2026-05-015
CONTROL:          CM-2 — Baseline Configuration

WEAKNESS:
  kube-bench is not deployed and no baseline configuration document or benchmark results
  can be produced for CM-2. No CIS benchmark results, no baseline configuration document,
  and no git artifact exist. PlatEng could not confirm the current hardened state of any
  node configuration.

SYSTEM AFFECTED:  Links-Matrix (Kubernetes nodes, control plane)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/CM-2?env=bad (kube-bench — status: insufficient) + PlatEng interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/CM-2-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Deploy kube-bench to the Links-Matrix cluster; run master and node targets;
                  export JSON results to evidence path.
  M2: 2026-05-15  Produce baseline configuration document pinning CIS benchmark version and
                  approved configuration state; commit document to git and link from evidence
                  path.

REMEDIATION APPROACH:
  Deploy kube-bench as a Job to the cluster targeting master and node components. Run
  kube-bench run --targets master,node --json and export the output to the evidence path.
  Identify all FAIL findings and remediate each to PASS. Produce a baseline configuration
  document in git (docs/baseline-config.md) that pins the CIS Kubernetes Benchmark version
  and records the approved hardened state. Link the document from the evidence path. Configure
  kube-bench to run on a nightly schedule and alert on new FAIL findings.

VALIDATION COMMAND:
  kube-bench run --targets master,node --json | jq '[.Controls[] | .tests[] | .results[] | select(.status=="FAIL")] | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment: kube-bench not deployed,
             no CIS benchmark results, no baseline configuration document
```

---

## POAM-2026-05-016 — CM-3

```text
POAM-ID:          POAM-2026-05-016
CONTROL:          CM-3 — Configuration Change Control

WEAKNESS:
  No configuration change control evidence exists. kube-bench PR gate is not configured
  and CODEOWNERS status is unknown. No change approval artifact was produced. PlatEng
  could not confirm that configuration changes to the cluster are gated by automated
  scanning or peer review.

SYSTEM AFFECTED:  Links-Matrix (Kubernetes, CI/CD pipeline, git repository)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/CM-3?env=bad (kube-bench — status: insufficient) + PlatEng interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/CM-3-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Add kube-bench scan as a required CI gate on all PRs touching cluster
                  configuration; confirm the gate blocks merge on any new FAIL finding.
  M2: 2026-05-15  Create CODEOWNERS file assigning PlatEng and SecEng as required reviewers
                  for all cluster configuration paths; confirm review is enforced on a test PR.

REMEDIATION APPROACH:
  Add a kube-bench CI step to the cluster configuration pipeline using the kube-bench GitHub
  Action or a custom job. Configure the gate to fail the pipeline if any new FAIL findings
  are introduced. Create a CODEOWNERS file at the repository root assigning PlatEng and SecEng
  as required reviewers for paths matching .kube/, charts/, and manifests/. Confirm branch
  protection rules require the kube-bench gate and CODEOWNERS review before merge. Export
  a sample approved PR with passing gate output as the change approval artifact.

VALIDATION COMMAND:
  kube-bench run --targets master,node --json | jq '[.Controls[] | .tests[] | .results[] | select(.status=="FAIL")] | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment: kube-bench PR gate not
             configured, CODEOWNERS not confirmed, no change approval artifact
```

---

## POAM-2026-05-017 — CM-6

```text
POAM-ID:          POAM-2026-05-017
CONTROL:          CM-6 — Configuration Settings

WEAKNESS:
  kube-bench scan results are not available and Kyverno policy count is unconfirmed for
  CM-6. No kube-bench results exist, the count of failed checks is unknown, and the
  Kyverno policy list has not been produced. SecEng could not confirm that configuration
  settings comply with organizational security policy.

SYSTEM AFFECTED:  Links-Matrix (Kubernetes nodes, Kyverno admission controller)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/CM-6?env=bad (kube-bench — status: insufficient) + SecEng interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/CM-6-2026-05-10/

REMEDIATION OWNER: SecEng (accountability) / PlatEng (evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Run kube-bench scan and export results; produce count of FAIL findings
                  per CIS section; store JSON output in evidence path.
  M2: 2026-05-15  Produce Kyverno policy list showing all active policies; confirm each
                  policy enforces an organizational security setting; store artifact in
                  evidence path.

REMEDIATION APPROACH:
  Run kube-bench run --targets master,node --json and export results to evidence path.
  Identify all FAIL findings and remediate: kubelet configuration, API server flags, and
  etcd encryption settings. Run kubectl get clusterpolicies -o json to enumerate all
  Kyverno policies and export the list. Cross-reference each policy against the
  organizational security settings baseline in docs/baseline-config.md. Confirm that
  all required settings (e.g. pod security, image policy, resource limits) have a
  corresponding Kyverno policy in enforce mode.

VALIDATION COMMAND:
  kube-bench run --targets master,node --json | jq '[.Controls[] | .tests[] | .results[] | select(.status=="FAIL")] | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment: no kube-bench results,
             failed check count unknown, Kyverno policy list not produced
```

---

## POAM-2026-05-018 — CM-7

```text
POAM-ID:          POAM-2026-05-018
CONTROL:          CM-7 — Least Functionality

WEAKNESS:
  Component inventory scan has not been run and no disabled component list or formal
  inventory exists for CM-7. No component inventory scan output, no disabled component
  list, and no formal inventory document were produced. The admission plugin review has
  not been run. PlatEng could not confirm which cluster components are active or which
  have been explicitly disabled.

SYSTEM AFFECTED:  Links-Matrix (Kubernetes cluster components, admission plugins)

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/CM-7?env=bad (kube-bench — status: insufficient) + PlatEng interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/CM-7-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability) / SecEng (evidence producer)

SCHEDULED COMPLETION: 2026-06-09

MILESTONES:
  M1: 2026-05-20  Run kube-bench and export the admission plugin and component configuration
                  sections; identify any enabled components not required for production workloads.
  M2: 2026-06-02  Disable all non-required components and admission plugins; produce a formal
                  disabled component list and store it in git; export as evidence artifact.

REMEDIATION APPROACH:
  Run kube-bench run --targets master,node --json and filter results to the admission plugins
  and component sections. Review the API server --enable-admission-plugins flag and confirm
  only required plugins are active (e.g. NodeRestriction, PodSecurity). Enumerate all running
  control plane components and identify any that are not required for production operations.
  Disable non-required components by removing them from the kube-apiserver manifest. Produce
  a formal inventory document listing each component, its status (enabled/disabled), and the
  justification. Commit the document to git and link from the evidence path.

VALIDATION COMMAND:
  kube-bench run --targets master,node --json | jq '[.Controls[] | .tests[] | .results[] | select(.status=="FAIL")] | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment: no component inventory
             scan, disabled component list empty, admission plugin review not produced
```

---

## POAM-2026-05-019 — CM-8

```text
POAM-ID:          POAM-2026-05-019
CONTROL:          CM-8 — System Component Inventory

WEAKNESS:
  Kubescape inventory scan is not configured and no Terraform inventory artifact exists
  for CM-8. The count of untracked resources is unknown. PlatEng could not confirm that
  the system component inventory is complete or current for any environment.

SYSTEM AFFECTED:  Links-Matrix (Kubernetes cluster, Terraform-managed infrastructure)

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/CM-8?env=bad (kubescape — status: insufficient) + PlatEng interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/CM-8-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-06-09

MILESTONES:
  M1: 2026-05-20  Deploy Kubescape and run an NSA framework inventory scan; export results
                  JSON to evidence path; identify the count of untracked or failed controls.
  M2: 2026-06-02  Export Terraform state inventory for all Links-Matrix resources; reconcile
                  against Kubescape scan results; store reconciled inventory artifact in
                  evidence path.

REMEDIATION APPROACH:
  Deploy Kubescape via Helm to the Links-Matrix cluster. Run kubescape scan framework nsa
  --format json and export results to evidence path. Identify all controls with a failed
  status and remediate each. Export the Terraform resource inventory using terraform show
  -json and produce a list of all managed resources by type and environment. Reconcile the
  Kubescape scan results against the Terraform inventory to identify any untracked resources.
  Produce a reconciled component inventory artifact and store it in the evidence path.
  Configure Kubescape to run on a weekly schedule and alert on new failed controls.

VALIDATION COMMAND:
  kubescape scan framework nsa --format json | jq '.summaryDetails.controlsSummaries | to_entries | map(select(.value.status.status=="failed")) | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment: Kubescape inventory not
             configured, no Terraform inventory artifact, untracked resource count unknown
```
