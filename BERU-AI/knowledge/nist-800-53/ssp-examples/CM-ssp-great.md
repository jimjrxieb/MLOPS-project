# System Security Plan — Configuration Management (CM) Family

## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** This SSP is auditor-ready. The CM chain is explicitly honored:
> CM-2 defines the approved baseline → CM-3 controls how it changes → CM-6 enforces
> the settings within it → CM-7 scopes what is allowed to run → CM-8 accounts for
> everything that is running. Drift from baseline detected in CM-2/CM-3 feeds CM-6
> policy enforcement; CM-8 inventory reconciles against CM-2 to find unauthorized
> components. Every enhancement addressed. Every policy either in Enforce mode or
> has a dated POA&M entry for the gap.

---

**System Name:** Links-Matrix Platform
**System Owner:** J. Rivera, Platform Engineering Lead (jrivera@links-matrix.io)
**ISSO:** M. Chen, Information System Security Officer (mchen@links-matrix.io)
**Prepared By:** M. Chen, ISSO
**Date:** 2026-05-01
**Review Date:** 2027-05-01 (annual) or upon significant system change
**Status:** Approved — ATO Granted 2026-03-15, expires 2029-03-15

**Control Chain Note:** CM controls on this platform form a closed enforcement loop.
CM-2 declares the approved baseline in git. CM-3 ensures only reviewed, approved changes
alter that baseline. CM-6 enforces the security settings defined in the baseline at
admission and continuously. CM-7 scopes what the baseline permits to run. CM-8 accounts
for everything actually running and reconciles it against the CM-2 baseline — any
component in CM-8 that has no corresponding CM-2 baseline entry is an unauthorized
component finding.

---

## CM-2 — Baseline Configuration

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Low, Moderate, and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Baseline Definition

The Links-Matrix Platform baseline configuration is the `main` branch of two
version-controlled repositories:

| Repository | Contents | Approved Via |
| ---------- | -------- | ------------ |
| `github.com/links-matrix/platform-gitops` | K8s manifests, Helm values, Kyverno policies, ArgoCD app definitions, NetworkPolicies, RBAC | PR with required review + ArgoCD sync approval |
| `github.com/links-matrix/infra-iac` | Terraform modules for all AWS resources (EKS, VPC, IAM, RDS, S3, KMS, CloudTrail) | PR with required review + `terraform apply` via CI only |

Every file in these repositories at `HEAD` of `main` is a component of the approved
baseline. Tagged releases (`platform-gitops@v2.4.1`, `infra-iac@v1.9.0`) mark stable
baseline snapshots used for rollback reference (see CM-2(3)).

### Baseline Reference Standards

| Standard | Version | Scope | Coverage Assessment |
| -------- | ------- | ----- | ------------------- |
| CIS Kubernetes Benchmark | v1.8.0 | EKS control plane + worker nodes | 89% Level 1, 72% Level 2 — assessed by kube-bench weekly; gaps in Baseline Deviation Register |
| CIS AWS Foundations Benchmark | v3.0 | AWS account configuration | 94% — assessed by Prowler weekly; gaps in Baseline Deviation Register |
| NIST SP 800-190 | Rev 1 | Container image security | Applied via Trivy scan policy in CI pipeline |
| NSA/CISA Kubernetes Hardening Guide | v1.2 | K8s cluster hardening | Applied as supplement to CIS K8s; mapped to Kyverno policies |

Deviations from these standards require ISSO written approval with documented business
justification, compensating control, and annual review date. The Baseline Deviation
Register (`platform-gitops/security/baseline-deviations.md` in git, versioned with
the baseline) currently contains 4 active deviations:

| Deviation ID | Component | Standard | Justification | Expiry |
| ------------ | --------- | -------- | ------------- | ------ |
| DEV-001 | `monitoring` namespace NetworkPolicy | CIS K8s 5.3.2 | Prometheus scraping requires broad egress to all namespaces; mitigated by network-level egress filter | 2027-03-01 |
| DEV-002 | ALB port 80 security group | CIS AWS 5.2 | HTTP→HTTPS redirect requires port 80 open at ALB; mitigated by WAF redirect rule | 2027-03-01 |
| DEV-003 | `lm-legacy-api` readOnlyRootFilesystem | CIS K8s 5.7.4 | Legacy application writes runtime config to `/tmp`; refactor scheduled Q4 2026 | 2026-12-31 |
| DEV-004 | RDS parameter group `log_min_duration` | CIS AWS RDS | Full query logging would exceed log storage budget; mitigated by slow-query threshold logging | 2027-03-01 |

### Drift Detection

ArgoCD continuously reconciles live cluster state against `platform-gitops@main`.
Drift from approved state (any manual `kubectl apply` or `kubectl patch` bypassing GitOps)
triggers:
1. ArgoCD UI shows application as `OutOfSync`
2. Slack alert to `#platform-alerts` with diff details
3. If unresolved after 30 minutes, PagerDuty P2 alert to Platform Engineer on-call

The Kyverno policy `block-non-argocd-rbac-apply` (Enforce) prevents direct RBAC
changes. The policy `block-direct-audit-policy-patch` (Enforce) prevents audit policy
changes. All other resource types rely on ArgoCD drift detection + alert.

For AWS resources, Terraform state drift is detected by a weekly `terraform plan` job
in CI (`infra-iac/.github/workflows/drift-check.yaml`). Any plan showing unexpected
changes creates a Jira `INFRA-SEC` ticket for ISSO review.

**Responsible Role:** Platform Engineer (baseline maintenance, ArgoCD, Terraform), ISSO (review and approval, deviation register ownership)

**Parameters:**
- Baseline repository: `github.com/links-matrix/platform-gitops` + `infra-iac` (main branch)
- CIS K8s Benchmark version: **v1.8.0** (Level 1: 89%, Level 2: 72%)
- CIS AWS Benchmark version: **v3.0** (coverage: 94%)
- ArgoCD drift alert: **30 minutes** to PagerDuty P2
- Terraform drift check cadence: **Weekly** (Sunday 01:00 UTC)
- Baseline review frequency: **Annual** (March) + significant change (within 14 days)
- Active deviations: **4** (all with expiry dates and annual review)

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| Baseline repository (`platform-gitops` main) | GitHub: github.com/links-matrix/platform-gitops | Continuous (git HEAD) |
| Baseline repository (`infra-iac` main) | GitHub: github.com/links-matrix/infra-iac | Continuous (git HEAD) |
| Baseline Deviation Register | `platform-gitops/security/baseline-deviations.md` | 2026-04-07 (quarterly review) |
| kube-bench CIS report (weekly) | Confluence: LM-SECURITY / kube-bench / 2026-W17.md | 2026-04-28 |
| Prowler CIS AWS report (weekly) | S3 `lm-audit-reports/prowler/2026-04-26.json` | 2026-04-26 |
| ArgoCD sync status (all apps) | ArgoCD UI: argocd.links-matrix.io | Continuous |
| Terraform drift check results | GitHub Actions run history: `infra-iac` repo | 2026-04-27 (last run) |
| Annual baseline review record | Confluence: LM-SECURITY / CM / Baseline Reviews / 2026-03.md | 2026-03-01 |
| Tagged baseline releases | GitHub releases: `platform-gitops` repo | Current: v2.4.1 (2026-04-15) |

**Test Procedure:**
1. Pull `platform-gitops` main branch — verify the most recent commit has a PR merge
   reference (no direct pushes). Pull one tagged release and verify it corresponds to
   a signed PR merge commit.
2. Check ArgoCD for all applications — verify all show `Synced` and `Healthy`. If any
   show `OutOfSync`, confirm a Jira or PagerDuty ticket exists for the drift.
3. Pull the Baseline Deviation Register from `platform-gitops/security/baseline-deviations.md`
   — verify each deviation has an expiry date, approver, and compensating control.
   Verify no deviation is past its expiry date.
4. Run `kube-bench --benchmark cis-1.8` on a sample node — verify output matches the
   most recent weekly kube-bench report in Confluence. Confirm failures correspond to
   active deviation entries.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| CM-2(1) Reviews and Updates | Implemented | Annual baseline review in March + within 14 days of significant change. Review records in Confluence. kube-bench and Prowler weekly reports surface benchmark gaps. Deviation Register reviewed quarterly. |
| CM-2(2) Automation Support for Accuracy and Currency | Implemented | ArgoCD provides continuous automated reconciliation against `platform-gitops@main`. Drift detected and alerted within 30 minutes. Terraform drift check weekly for cloud resources. The baseline is always the current `main` branch — no manual documentation required to stay current. |
| CM-2(3) Retention of Previous Configurations | Implemented | Git history retains every prior baseline state with full commit authorship and PR reference. Tagged releases (`v2.4.1`, `v2.4.0`, etc.) mark stable baseline snapshots for rollback. Helm release history (`helm history lm-platform`) provides per-service rollback capability. Git history is retained indefinitely; no force-push or history rewrite is permitted (enforced by branch protection). |

---

## CM-3 — Configuration Change Control

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Moderate and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Change Control Pipeline

Every configuration change to the Links-Matrix Platform — whether to K8s manifests,
Kyverno policies, IAM Terraform, or network configuration — must pass through the
following pipeline. No exceptions outside of the documented emergency change procedure.

```
Author opens PR
    ↓
Automated CI gates (all must pass — any failure blocks merge):
    ├── helm lint + template validation
    ├── Kyverno dry-run against proposed manifests
    ├── Trivy misconfiguration scan (HIGH/CRITICAL = block)
    ├── Semgrep SAST (security rules — HIGH = block)
    ├── terraform validate + plan (infra-iac PRs only)
    └── OPA conftest policy check (custom policy bundle)
    ↓
Human review (CODEOWNERS enforced by GitHub):
    ├── Standard platform changes: 1 Platform Engineering Lead approval
    ├── Security-impacting changes (RBAC, Kyverno, IAM, network): 1 Platform Lead + 1 ISSO or Security Engineer
    └── Break-glass / access control exception: ISSO + System Owner
    ↓
Merge to main (no direct push; no force push; stale approvals dismissed)
    ↓
ArgoCD detects change → Platform Engineer reviews diff in ArgoCD UI → Manual sync approval
    ↓
Post-deployment: ArgoCD shows Synced + Healthy; CI smoke test passes
```

### Change Categories and Approval Requirements

| Change Type | Examples | Required Approvers | Security Gate |
| ----------- | -------- | ------------------ | ------------- |
| Standard platform | Helm values update, resource limits, replica count | 1 Platform Lead | Trivy + Kyverno dry-run |
| Security-impacting | RBAC changes, Kyverno policy changes, IAM policy, NetworkPolicy | Platform Lead + ISSO or SecEng | All CI gates + ISSO review |
| Baseline exception | Adding a deviation to the Baseline Deviation Register | ISSO sign-off in PR + SO for high-risk | All CI gates + ISSO + SO |
| Infrastructure | Terraform changes to VPC, IAM, EKS config | Cloud Security Engineer + Platform Lead | Terraform plan review + Trivy |
| Emergency | Critical security patch, active incident response | Platform Engineer (immediate) + ISSO verbal + post-review within 4 hours | Expedited CI (Trivy required); full CI within 24 hours |

### Emergency Change Procedure

Emergency changes (ECP-001, `platform-gitops/docs/emergency-change-procedure.md`) follow:
1. Platform Engineer assesses urgency — confirms it meets emergency criteria (active incident
   or imminent security risk)
2. ISSO notified via Slack DM to `#isso-approvals` bot (logged automatically) — verbal approval
   sufficient for immediate action
3. Change applied — if via `kubectl`, Platform Engineer documents exact command in the
   `#platform-alerts` Slack thread
4. PR opened within **2 hours** of change application with full description and justification
5. Post-implementation review completed within **4 hours** — ISSO confirms no unintended
   side effects; Jira `PLAT-SEC` ticket created
6. If change was applied via kubectl (not GitOps), a corrective GitOps PR is opened within
   **4 hours** to bring the baseline into sync with the emergency change; ArgoCD then manages
   the resource going forward

Emergency changes are reviewed in the weekly platform security sync and summarized in the
monthly CM report.

**Responsible Role:** Platform Engineering Lead (standard change review, ArgoCD sync), ISSO (security-impacting change approval, emergency post-review), Cloud Security Engineer (infrastructure change review), DevSecOps (CI gate maintenance)

**Parameters:**
- Standard change review: **1 approver** (Platform Lead)
- Security-impacting change review: **2 approvers** (Platform Lead + ISSO or SecEng)
- Emergency PR deadline: **2 hours** after change
- Emergency post-review deadline: **4 hours** after change
- GitOps sync deadline after emergency kubectl: **4 hours**
- Required CI gates: Kyverno dry-run, Trivy (HIGH/CRITICAL blocking), Semgrep, OPA conftest

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| GitHub branch protection config | GitHub repo settings → Branches (screenshot in quarterly CM review) | 2026-04-07 |
| CODEOWNERS file | `platform-gitops/CODEOWNERS` | Per-commit |
| GitHub Actions CI workflow | `platform-gitops/.github/workflows/pr-checks.yaml` | Per-commit |
| ArgoCD sync history (90 days) | ArgoCD UI: argocd.links-matrix.io → App history | Continuous |
| Emergency Change Procedure ECP-001 | `platform-gitops/docs/emergency-change-procedure.md` | 2026-03-01 |
| Emergency change Jira tickets (`PLAT-SEC`) | Jira project PLAT-SEC (label: `emergency-change`) | Per-incident |
| Monthly CM report (includes emergency change summary) | S3 `lm-audit-reports/cm-monthly/` | Monthly |

**Test Procedure:**
1. Select 3 recent merged PRs to `platform-gitops` — verify each has at least 1 approved
   review and all required CI checks passed (no bypassed gates). Verify no direct commits
   to `main` appear in `git log --merges`.
2. Select 1 RBAC or Kyverno policy change PR — verify ISSO or Security Engineer is in
   the approver list.
3. Attempt a direct push to `main` — verify GitHub blocks the push with "protected branch"
   error.
4. Pull Jira `PLAT-SEC` emergency-change tickets — verify each has a PR reference, a
   post-review completion timestamp within 4 hours, and an ISSO sign-off comment.
5. Check ArgoCD sync history — verify every production sync event was performed by an
   authorized principal (Platform Engineer or ISSO) and not by an automated process
   without a corresponding PR merge.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| CM-3(1) Automated Documentation, Notification, Prohibition | Implemented | GitHub branch protection prohibits unapproved merges. PR creation auto-notifies CODEOWNERS. CI gates auto-document test results in the PR. ArgoCD requires manual sync — changes cannot reach production automatically. Emergency changes are logged automatically by the `#isso-approvals` Slack bot. |
| CM-3(2) Testing, Validation, Documentation | Implemented | Required CI gates: Kyverno dry-run (policy validation), Trivy (misconfiguration — HIGH/CRITICAL blocking), Semgrep (SAST), OPA conftest, Helm lint. All results are recorded in the PR check history. No change can merge without all gates passing. Emergency changes require Trivy immediately; full CI within 24 hours. |
| CM-3(4) Security Representative | Implemented | CODEOWNERS enforces ISSO or Security Engineer approval on all security-impacting changes (RBAC, Kyverno, IAM, NetworkPolicy). The ISSO attends the weekly platform security sync where all changes from the prior week are reviewed. Emergency changes require ISSO verbal approval before application. *(A formal standing change control board is not established — security review is CODEOWNERS-enforced per-PR. This is documented as a process maturity goal for the 2027 ATO cycle.)* |

---

## CM-6 — Configuration Settings

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Moderate and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Kubernetes — Kyverno Policy Enforcement

All Kyverno policies are in `platform-gitops/kyverno/`, deployed via ArgoCD, and
protected from direct modification by the Kyverno `protect-kyverno-policies` policy
(Enforce — only ArgoCD service account can modify Kyverno resources).

| Policy Name | Mode | CIS K8s Ref | Setting Enforced | Violation Action |
| ----------- | ---- | ----------- | ---------------- | ---------------- |
| `require-run-as-non-root` | **Enforce** | 5.7.1 | `runAsNonRoot: true` on all pods | Admission denied; Kyverno violation event → OpenSearch |
| `require-read-only-rootfs` | **Enforce** | 5.7.4 | `readOnlyRootFilesystem: true` | Admission denied (DEV-003 exempts `lm-legacy-api`) |
| `drop-all-capabilities` | **Enforce** | 5.7.3 | `capabilities.drop: [ALL]`; adds require ISSO approval | Admission denied |
| `require-resource-limits` | **Enforce** | 5.6.4 | CPU + memory limits required | Admission denied |
| `deny-privileged-containers` | **Enforce** | 5.7.2 | `privileged: false` | Admission denied |
| `deny-host-namespaces` | **Enforce** | 5.7.2 | `hostPID/IPC/Network: false` | Admission denied |
| `deny-nodeport-services` | **Enforce** | 5.3.1 | Service type NodePort blocked | Admission denied |
| `restrict-image-registries` | **Enforce** | 5.5.1 | Only ECR `lm-prod-ecr` + `registry.k8s.io` | Admission denied; see CM-7 |
| `require-network-policy` | **Enforce** | 5.3.2 | Each namespace must have a NetworkPolicy | Admission denied (DEV-001 exempts `monitoring`) |
| `require-sa-annotation` | **Enforce** | N/A | ServiceAccounts need `secteam.io/owner` annotation | Admission denied |
| `protect-kyverno-policies` | **Enforce** | N/A | Only ArgoCD SA can modify Kyverno resources | Admission denied; alert P1 |
| `protect-audit-policy` | **Enforce** | N/A | K8s audit policy ConfigMap protected | Admission denied; alert P1 |

**Current Kyverno violation rate:** 0 policy violations in production namespaces for the
past 30 days (last violation: 2026-03-22, remediated within 2 hours). Violation metrics
in OpenSearch index `lm-kyverno-*`.

### AWS — Config Rules

All 18 AWS Config rules are active with continuous evaluation and automated remediation
where applicable.

| Rule Name | CIS AWS Ref | Compliant | Auto-Remediation |
| --------- | ----------- | --------- | ---------------- |
| `s3-bucket-public-read-prohibited` | 2.1.1 | ✅ | SSM document `s3-block-public-access` |
| `s3-bucket-public-write-prohibited` | 2.1.2 | ✅ | SSM document `s3-block-public-access` |
| `restricted-ssh` | 5.2 | ✅ | SSM document `revoke-open-ssh-sg` |
| `no-unrestricted-ingress-except-alb` | 5.2 (custom) | ✅ | Alert only (manual review required) |
| `cloud-trail-enabled` | 3.1 | ✅ | SSM document `enable-cloudtrail` |
| `cloud-trail-log-file-validation-enabled` | 3.2 | ✅ | Alert only |
| `encrypted-volumes` | 2.2.1 | ✅ | Alert only (encryption requires recreation) |
| `rds-storage-encrypted` | 2.3.1 | ✅ | Alert only |
| `iam-no-inline-policy` | 1.16 | ✅ | Alert only |
| `iam-password-policy-ensure-expires` | 1.9 | ✅ | SSM document `enforce-iam-password-policy` |
| `mfa-enabled-for-iam-console-access` | 1.10 | ✅ | Alert only |
| `access-keys-rotated` (90-day) | 1.14 | ✅ | Alert to key owner + ISSO |
| `kms-cmk-backing-key-rotation-enabled` | 3.7 | ✅ | Alert only |
| `vpc-flow-logs-enabled` | 3.9 | ✅ | SSM document `enable-vpc-flow-logs` |
| `ec2-instance-managed-by-ssm` | N/A (custom) | ✅ | Alert to Cloud Security Engineer |
| `detect-unmanaged-ec2` | N/A (custom) | ✅ | Alert + Jira `INFRA-SEC` ticket auto-created |
| `guardduty-enabled-centralized` | N/A | ✅ | Alert only |
| `securityhub-enabled` | N/A | ✅ | Alert only |

**All 18 rules: 18/18 compliant** as of 2026-05-01. Last non-compliance event: 2026-03-14
(IAM access key age exceeded 90 days; remediated 2026-03-15 by key rotation).

### Deviation Process

Deviations from CM-6 settings require:
1. ISSO written approval (PR comment in `platform-gitops` with explicit ISSO sign-off)
2. Business justification documented in `platform-gitops/security/baseline-deviations.md`
3. Compensating control specified
4. Annual expiry date — deviation auto-expires and requires re-approval

A GitHub Actions job (`deviation-expiry-check.yaml`) runs weekly and creates a Jira
`SEC` ticket 30 days before any deviation's expiry date. The ISSO must re-approve or
close the deviation before expiry.

**Responsible Role:** Platform Engineer (Kyverno policies), Cloud Security Engineer (Config rules), ISSO (deviation approval, policy governance)

**Parameters:**
- Kyverno policies: **12 active, all in Enforce mode**
- AWS Config rules: **18 active, 18/18 compliant**
- Deviation approval authority: **ISSO**
- Deviation expiry check: **Weekly automated** with 30-day pre-expiry Jira ticket
- Violation response for admission denial: **Immediate** (Kyverno blocks at API server)

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| Kyverno ClusterPolicy manifests | `platform-gitops/kyverno/*.yaml` | Per-commit |
| Kyverno violation history | OpenSearch index `lm-kyverno-*` | Continuous |
| AWS Config rule compliance report | AWS Console → Config → Rules; also S3 `lm-audit-reports/config/2026-04.json` | 2026-05-01 |
| Baseline Deviation Register | `platform-gitops/security/baseline-deviations.md` | 2026-04-07 |
| Deviation expiry check workflow | `platform-gitops/.github/workflows/deviation-expiry-check.yaml` | Per-run (weekly) |

**Test Procedure:**
1. Attempt to deploy a pod with `runAsNonRoot: false` to any production namespace —
   verify Kyverno denies admission and an event appears in OpenSearch `lm-kyverno-*`
   within 60 seconds.
2. Pull `kubectl get clusterpolicies -o yaml` — verify all 12 policies show
   `validationFailureAction: Enforce` (not `audit`).
3. Pull AWS Config compliance report — verify all 18 rules show `COMPLIANT`.
   For any non-compliant finding, verify a Jira ticket exists and is assigned.
4. Pull the Baseline Deviation Register — verify each deviation has an expiry date,
   ISSO approver, and compensating control. Verify no deviation is past its expiry.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| CM-6(1) Automated Central Management | Implemented | Kyverno enforces settings at K8s admission time — no workload can run in a non-compliant configuration. All Kyverno policies managed via GitOps (ArgoCD). AWS Config evaluates cloud resources on every change. No manual configuration inspection required — enforcement is continuous and automated. |
| CM-6(2) Respond to Unauthorized Changes | Implemented | Kyverno Enforce mode blocks non-compliant resources at admission — they never reach running state. AWS Config auto-remediation SSM documents correct 8 of 18 rules automatically. ArgoCD drift detection blocks unauthorized K8s changes from persisting. All violation events route to OpenSearch and PagerDuty. No detected violation goes without a ticket and response. |

---

## CM-7 — Least Functionality

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Moderate and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Implementation Description

**Kubernetes NetworkPolicy — Default Deny:**
All namespaces receive a `default-deny-ingress-egress` NetworkPolicy at creation via
a Kyverno mutation policy (`inject-default-network-policy`). This policy is in Enforce
mode — namespaces without a NetworkPolicy cannot be created. Explicit allow rules are
added in `platform-gitops/network-policies/<namespace>/` for each required
communication path and require PR review with Platform Lead + ISSO approval (CODEOWNERS).

Current network-policy coverage: 14 production namespaces with default-deny + explicit
allows. DEV-001 exempts the `monitoring` namespace from egress restriction (Prometheus
scraping); a compensating NACL rule limits `monitoring` namespace egress to cluster CIDR.

**Approved Container Image Registries (CM-7(5)):**
The approved software list for container images is defined in the Kyverno policy
`restrict-image-registries` (`platform-gitops/kyverno/restrict-image-registries.yaml`)
and is the authoritative artifact for CM-7(5). Currently two registries are approved:

| Registry | Purpose | Owner | Approved Since |
| -------- | ------- | ----- | -------------- |
| `lm-prod-ecr.dkr.ecr.us-east-1.amazonaws.com` | All Links-Matrix application images | DevSecOps | 2025-09-01 |
| `registry.k8s.io` | Kubernetes system component images | Platform Engineer | 2025-09-01 |

Any deployment referencing an image from any other registry is rejected at admission
by Kyverno. This includes Docker Hub, Quay, GHCR, and any other public or private
registry not on the approved list. Rejection events are logged in OpenSearch
`lm-kyverno-*` and trigger a Slack alert to `#sec-alerts`.

Addition of a new approved registry requires: ISSO approval, documented justification,
and image signing verification capability for the new registry (Cosign signature
verification enforced by Kyverno `verify-image-signatures` policy).

**AWS Exposed Service Audit:**
No public-facing services exist in the Links-Matrix Platform other than the Application
Load Balancer on port 443 (HTTP/2, TLS 1.2 minimum). This is enforced by:
- Kyverno `deny-nodeport-services` (Enforce): No NodePort or ExternalIP services in K8s
- AWS Config `no-unrestricted-ingress-except-alb`: All security group inbound rules except ALB 443 are flagged
- AWS Inspector Network Reachability: Weekly scan confirms only ALB port 443 is reachable from the internet

**Quarterly Least-Functionality Review:**
The ISSO and Platform Lead conduct a quarterly review covering:
1. All running K8s services and their exposure type (ClusterIP only in production namespaces)
2. All DaemonSets and CronJobs — each must have a documented operational purpose
3. All open security group inbound rules — verified against the approved port/protocol list
4. All enabled AWS services in the account — unexpected services flagged for review
5. Base image package lists — Trivy SBOMs reviewed for unnecessary packages

Review results are recorded in `platform-gitops/security/functionality-review-YYYY-QQ.md`.
Last review: 2026-04-07. 0 unauthorized services or ports found. 2 CronJobs flagged for
documentation updates (resolved in `PLAT-SEC-1842`).

**Responsible Role:** Platform Engineer (NetworkPolicy, Kyverno, security groups), Cloud Security Engineer (AWS Inspector, Config rules), ISSO (quarterly review, approved registry approval)

**Parameters:**
- Default NetworkPolicy: **deny-all ingress and egress** (all namespaces)
- Approved image registries: **2** (ECR + registry.k8s.io — deny-all, permit-by-exception)
- External ingress: **ALB port 443 only**
- Quarterly review cadence: **January, April, July, October** (first Monday)

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| `inject-default-network-policy` Kyverno mutation policy | `platform-gitops/kyverno/inject-default-network-policy.yaml` | Per-commit |
| NetworkPolicy manifests (all namespaces) | `platform-gitops/network-policies/` | Per-commit |
| `restrict-image-registries` Kyverno policy (approved registry list) | `platform-gitops/kyverno/restrict-image-registries.yaml` | Per-commit |
| `verify-image-signatures` Kyverno policy | `platform-gitops/kyverno/verify-image-signatures.yaml` | Per-commit |
| AWS Inspector network reachability report | S3 `lm-audit-reports/inspector/network-2026-04-28.json` | 2026-04-28 |
| Quarterly functionality review | `platform-gitops/security/functionality-review-2026-Q2.md` | 2026-04-07 |

**Test Procedure:**
1. Attempt to deploy a pod from Docker Hub (`image: nginx:latest`) to any production
   namespace — verify Kyverno blocks admission and an event appears in `lm-kyverno-*`.
2. Create a test namespace without a NetworkPolicy — verify Kyverno blocks namespace
   creation or immediately injects the default-deny policy.
3. Pull AWS Inspector network reachability findings — verify only ALB port 443 shows
   as reachable from the internet. Any other port flagged is a finding.
4. Pull `kubectl get services -A -o wide` — verify no service of type `NodePort` or
   `LoadBalancer` (other than the ALB Ingress Controller service) exists in production
   namespaces.
5. Pull the quarterly functionality review document — verify it was completed in the
   current quarter, signed by ISSO and Platform Lead, and shows 0 unauthorized services.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| CM-7(1) Periodic Review | Implemented | Quarterly least-functionality review covering K8s services, DaemonSets/CronJobs, security group rules, enabled AWS services, and base image packages. Results documented in versioned markdown in `platform-gitops/security/`. Last review: 2026-04-07. |
| CM-7(2) Prevent Program Execution | Implemented | `restrict-image-registries` Kyverno policy (Enforce) blocks images from unapproved registries at admission. `verify-image-signatures` policy requires Cosign signature from the DevSecOps signing key on all application images — unsigned images are rejected regardless of registry. Falco rule `unexpected-spawned-process` detects runtime process execution anomalies. |
| CM-7(5) Authorized Software — Allow-by-Exception | Implemented | Kyverno `restrict-image-registries` implements deny-all, permit-by-exception for container images. The approved registry list is the Kyverno policy file itself (`platform-gitops/kyverno/restrict-image-registries.yaml`) — versioned, reviewed, and auditable. Adding a registry requires ISSO approval + image signing capability. Current approved registries: 2 (ECR `lm-prod-ecr`, `registry.k8s.io`). |

---

## CM-8 — System Component Inventory

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Low, Moderate, and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Component Inventory Sources

The Links-Matrix Platform component inventory is maintained through four automated
sources that together provide a complete, continuously updated view of all system components.

| Source | Scope | Cadence | Storage |
| ------ | ----- | ------- | ------- |
| K8s API export (CronJob `inventory-export`) | All K8s resources across all namespaces | Weekly (Sun 04:00 UTC) | S3 `lm-audit-reports/inventory/k8s-YYYY-MM-DD.json` |
| AWS Config resource inventory | All AWS resource types, both regions (us-east-1, us-west-2) | Continuous (on change) | AWS Config console + S3 `lm-logs-config/` |
| ECR image inventory | All container images in `lm-prod-ecr` with SBOM | On every image push + weekly full scan | S3 `lm-audit-reports/sbom/` (CycloneDX format) |
| ArgoCD application inventory | All applications managed by ArgoCD (desired state) | Continuous (ArgoCD sync) | ArgoCD API + `platform-gitops/argocd/` |

### Software Bill of Materials (SBOM)

Every container image pushed to ECR `lm-prod-ecr` triggers a CI pipeline job
(`generate-sbom`) that runs `trivy image --format cyclonedx` and uploads the SBOM to
S3 `lm-audit-reports/sbom/<image-name>/<tag>/sbom-cyclonedx.json`. This provides
a complete package-level inventory for every production image.

SBOMs are used for:
- **Vulnerability matching:** When a new CVE is published, `kev-check.sh` and Trivy
  compare against all SBOMs to identify affected images within minutes
- **License compliance:** A weekly scan checks SBOM packages against the approved
  license list
- **FedRAMP evidence:** SBOMs are requested artifacts for RA-5 (vulnerability scanning)
  and SI-2 (flaw remediation) evidence packages

Current SBOM coverage: **100%** of images in `lm-prod-ecr` (12 application images,
7 supporting images). SBOM index maintained at
S3 `lm-audit-reports/sbom/index.json` (updated on every image push).

### Inventory Reconciliation with Baseline (CM-2 Link)

A weekly reconciliation job (`inventory-reconcile.sh`, `platform-gitops/tools/`) compares
the K8s inventory export against the ArgoCD application inventory (the CM-2 baseline):

- **Components in ArgoCD but not in K8s inventory:** ArgoCD app not yet deployed or
  deployment failed — flagged for Platform Engineer review
- **Components in K8s inventory but not in ArgoCD:** Unauthorized component — resource
  deployed outside GitOps pipeline — flagged as CM-8(3) finding, Jira `SEC` ticket created,
  ISSO notified within 1 hour

Last reconciliation run: 2026-04-27. Result: 0 unauthorized components. All K8s workloads
traced to an ArgoCD application.

### Unauthorized Component Detection

Three mechanisms detect components outside the authorized baseline:

1. **ArgoCD orphan detection:** `inventory-reconcile.sh` (weekly) identifies K8s resources
   not managed by any ArgoCD application
2. **AWS Config `detect-unmanaged-ec2`:** Flags EC2 instances not tagged `managed-by: terraform`
   and not registered with Systems Manager — auto-creates Jira `INFRA-SEC` ticket
3. **Falco rule `unexpected-container-start`:** Alerts in real-time on any container
   starting from an image not in the ECR approved registry (runtime enforcement,
   complements Kyverno admission enforcement)

When an unauthorized component is detected, the response procedure (UCD-001,
`platform-gitops/docs/unauthorized-component-procedure.md`) is initiated:
- ISSO notified within 1 hour
- Component isolated (NetworkPolicy applied to deny all egress) within 4 hours
- Root cause investigation within 24 hours
- Component removed or authorized via CM-3 change process within 48 hours

**Responsible Role:** Platform Engineer (K8s inventory, ArgoCD reconciliation, SBOM pipeline), Cloud Security Engineer (AWS Config inventory, unmanaged EC2 detection), DevSecOps (SBOM generation in CI)

**Parameters:**
- K8s inventory export: **Weekly** (Sunday 04:00 UTC)
- AWS Config recording: **Continuous**, all resource types, both regions
- SBOM generation: **On every image push** to ECR + weekly full scan
- Unauthorized component detection: **Real-time** (Falco) + **Weekly** (reconciliation)
- Unauthorized component ISSO notification SLA: **1 hour**
- Unauthorized component isolation SLA: **4 hours**

**Evidence / Artifacts:**

| Artifact | Location | Last Verified |
| -------- | -------- | ------------- |
| K8s inventory exports (weekly) | S3 `lm-audit-reports/inventory/` | 2026-04-27 |
| AWS Config resource inventory | AWS Console → Config → Resource Inventory | Continuous |
| SBOM index | S3 `lm-audit-reports/sbom/index.json` | Per image push |
| SBOM per image (CycloneDX) | S3 `lm-audit-reports/sbom/<image>/<tag>/sbom-cyclonedx.json` | Per image push |
| Inventory reconciliation report | `platform-gitops/security/inventory-reconcile-YYYY-WW.md` | 2026-04-27 |
| Unauthorized Component Detection Procedure UCD-001 | `platform-gitops/docs/unauthorized-component-procedure.md` | 2026-03-01 |
| Falco `unexpected-container-start` rule | `platform-gitops/falco/rules/cm8-rules.yaml` | Per-commit |

**Test Procedure:**
1. Pull S3 `lm-audit-reports/inventory/` — verify a K8s inventory export exists for
   each Sunday in the last 30 days with non-zero file size.
2. Pull SBOM index at S3 `lm-audit-reports/sbom/index.json` — verify all 19 production
   ECR images have a corresponding SBOM entry with a timestamp within 7 days of their
   last push.
3. Pull the most recent inventory reconciliation report — verify 0 unauthorized components
   and that the report date is within 7 days.
4. Deploy a test pod directly via kubectl (not ArgoCD) to a non-production namespace —
   verify the next weekly reconciliation run (or trigger `inventory-reconcile.sh` manually)
   identifies it as an unauthorized component and creates a Jira `SEC` ticket.
5. Push a test image to ECR — verify an SBOM is generated in S3 within 10 minutes of push.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
| ----------- | ------ | -------------- |
| CM-8(1) Updates During Installations and Removals | Implemented | Every ArgoCD sync (deployment) is recorded in ArgoCD history. The CI pipeline generates an SBOM on every image push. AWS Config records every cloud resource change in real time. The inventory is a live reflection of the system state, not a periodic manual update. |
| CM-8(2) Automated Maintenance | Implemented | Four automated inventory sources (K8s API CronJob, AWS Config continuous recording, ECR SBOM pipeline, ArgoCD application list) maintain the inventory without manual effort. Inventory reconciliation runs weekly automatically. |
| CM-8(3) Automated Unauthorized Component Detection | Implemented | Three detection mechanisms: ArgoCD orphan detection (weekly reconciliation), AWS Config `detect-unmanaged-ec2` rule (continuous), and Falco `unexpected-container-start` rule (real-time). Unauthorized component response procedure (UCD-001) defines 1-hour ISSO notification, 4-hour isolation, 48-hour resolution SLAs. Last 30 days: 0 unauthorized components detected. |

---

## What Makes This GREAT — Side-by-Side

| Dimension | Bad | Good | Great |
| --------- | --- | ---- | ----- |
| **CM-2 baseline definition** | "System configuration documentation" | GitOps repo named | Two repos named with path, contents, and approval mechanism; CIS Benchmark version + coverage percentage; 4-deviation register in git with expiry dates |
| **Drift detection** | Not mentioned | ArgoCD + 4-hour SLA | ArgoCD + 30-min PagerDuty P2 + weekly Terraform drift check; drift cannot persist silently |
| **CM-3 pipeline** | "Review process" | Pipeline gates named | Full pipeline diagram with named gates, change category table with approval matrix, emergency procedure with 2-hour PR and 4-hour post-review SLA |
| **CM-6 policy enforcement** | "Some policies deployed" | 8/10 Enforce; 2 Audit with future target | 12/12 Enforce; deviation process with auto-expiry check; 18/18 Config rules compliant with auto-remediation count |
| **CM-7 approved software** | Not mentioned | Kyverno policy noted as "approximate" list | Approved registry table with owner and approval date; image signing required for any new registry; Falco runtime enforcement as second layer |
| **CM-8 inventory** | "Spreadsheet" implied | AWS Config + weekly K8s export | 4 automated sources; SBOM for every image (100% coverage); weekly reconciliation against CM-2 baseline with unauthorized component finding procedure and SLAs |
| **CM-2 ↔ CM-8 link** | None | Not described | Explicitly documented: CM-8 inventory reconciled against ArgoCD (CM-2 baseline) weekly; gap = unauthorized component finding |
| **Control chain** | 5 unrelated checkboxes | Implicitly GitOps-connected | Explicitly documented in header; each control references its dependency on the previous |
