# System Security Plan — Configuration Management (CM) Family

## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** This SSP would pass a readiness review with 4-6 clarification items.
> GitOps and real tools are named, the chain between controls is implicit, and most
> settings are enforced. Gaps: some Kyverno policies are still in Audit mode, the
> deviation process exists but has no expiry requirement, CM-8 has no SBOM and no
> unauthorized component detection, and CM-7(5) allow-by-exception is not explicit.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Final Draft — Pending ISSO Signature

---

## CM-2 — Baseline Configuration

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

The Links-Matrix Platform baseline configuration is managed as code in the
`platform-gitops` repository (`github.com/links-matrix/platform-gitops`). The baseline
consists of:

- **Kubernetes manifests:** Helm chart values files, Kustomize overlays, and raw manifests
  for all cluster components stored in `platform-gitops/`
- **Infrastructure:** Terraform modules in `infra-iac/` defining all AWS resources
  (EKS cluster, VPCs, IAM, RDS, S3, KMS)
- **Policy-as-code:** Kyverno ClusterPolicies in `platform-gitops/kyverno/` defining
  security enforcement rules
- **ArgoCD Application definitions:** `platform-gitops/argocd/` defining desired state
  for all deployed applications

The CIS Kubernetes Benchmark v1.8 and CIS AWS Foundations Benchmark v3.0 serve as the
baseline reference standards. Deviations from the benchmarks are documented in the
Baseline Deviation Register (Confluence: LM-SECURITY / CM / Baseline Deviations).

ArgoCD provides continuous sync status — any drift between the `main` branch and live
cluster state is visible in the ArgoCD UI and triggers a Slack alert to `#platform-alerts`.
The Platform Engineer resolves drift within 4 hours per the GitOps runbook.

The baseline is reviewed annually by the ISSO and Platform Engineering Lead, and whenever
a significant architecture change occurs. Last review: 2026-03-01.

**Responsible Role:** Platform Engineer (baseline maintenance), ISSO (review and approval)

**Parameters:**
- Baseline repository: `github.com/links-matrix/platform-gitops` (main branch)
- Baseline reference standards: CIS Kubernetes Benchmark v1.8, CIS AWS Foundations Benchmark v3.0
- Baseline review frequency: Annual + significant change
- ArgoCD drift remediation SLA: 4 hours

**Evidence / Artifacts:**
- `platform-gitops` repository (GitHub — main branch as current approved baseline)
- ArgoCD application sync status dashboard
- Baseline Deviation Register (Confluence: LM-SECURITY / CM / Baseline Deviations)
- Annual baseline review record (last: 2026-03-01, signed by ISSO and Platform Lead)

**Enhancements Addressed:**
- **CM-2(1):** Baseline reviewed annually and on significant change. Review records maintained in Confluence.
- **CM-2(2):** ArgoCD provides automated drift detection and sync. The `main` branch is always the authoritative baseline — drift alerts fire within minutes of any deviation.
- **CM-2(3):** Git history retains every prior baseline state. Tagged releases (`v1.0`, `v1.1`, etc.) mark approved baseline versions for rollback reference.

---

## CM-3 — Configuration Change Control

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

All configuration changes to the Links-Matrix Platform follow a GitOps change control
process. Changes must be submitted as pull requests to the `platform-gitops` or `infra-iac`
repositories and pass required checks before merging to `main`.

**Branch protection rules (enforced by GitHub):**
- Minimum 1 approving reviewer required (Platform Engineering Lead or ISSO for security-impacting changes)
- All required status checks must pass before merge
- No direct pushes to `main` permitted — force push is disabled
- Stale approvals are dismissed on new commits

**Required CI pipeline gates (GitHub Actions):**
- Helm lint and template validation
- Kyverno policy dry-run against proposed manifests
- Trivy misconfiguration scan (HIGH/CRITICAL findings block merge)
- Terraform plan with security review (for `infra-iac` changes)
- SAST scan via Semgrep

**Security review requirement:** Changes to Kyverno policies, RBAC manifests, IAM Terraform
modules, or network configuration require explicit approval from the ISSO or a designated
Security Engineer in addition to the Platform Engineering Lead. This is enforced via
GitHub CODEOWNERS file (`platform-gitops/CODEOWNERS`).

**Production deployment:** ArgoCD is configured with manual sync for the `production`
app set — changes merged to `main` do not automatically deploy. A Platform Engineer or
ISSO must trigger the ArgoCD sync after reviewing the diff. Sync events are logged in
ArgoCD and CloudTrail.

**Emergency changes:** Emergency hotfixes follow the expedited change procedure (ECP-001,
Confluence: LM-SECURITY / CM / Emergency Change Procedure). The Platform Engineer may
apply the change with verbal ISSO approval, followed by a post-implementation review
within 24 hours and a Jira `PLAT-SEC` ticket documenting the change, rationale, and
approver. Emergency changes are reviewed in the next weekly platform security sync.

**Responsible Role:** Platform Engineering Lead (change review, ArgoCD sync), ISSO (security-impacting change approval), DevSecOps (pipeline security gates)

**Parameters:**
- Required reviewers: 1 (platform changes); 2 including ISSO or Security Engineer (security-impacting changes)
- Emergency change post-review deadline: 24 hours
- Required CI gates: Kyverno dry-run, Trivy, Semgrep (all blocking)

**Evidence / Artifacts:**
- GitHub branch protection configuration (repo settings screenshot)
- CODEOWNERS file (`platform-gitops/CODEOWNERS`)
- GitHub Actions workflow files (`platform-gitops/.github/workflows/`)
- ArgoCD sync history (last 90 days)
- Emergency Change Procedure ECP-001 (Confluence: LM-SECURITY / CM / Emergency Change Procedure)
- Jira `PLAT-SEC` emergency change tickets

**Enhancements Addressed:**
- **CM-3(1):** GitHub branch protection enforces documentation, notification (PR reviewers notified automatically), and prohibition of unapproved changes. ArgoCD requires manual sync — no change auto-deploys to production.
- **CM-3(2):** Required CI gates include Helm lint, Kyverno dry-run, Trivy, and Semgrep — all blocking. Changes cannot merge without passing these tests.
- **CM-3(4):** CODEOWNERS requires ISSO or Security Engineer approval for security-impacting changes. *(Note: a formal change control board with standing security representation is not yet established — security review is per-PR rather than board-based. This is flagged as a process maturity gap for the next annual review.)*

---

## CM-6 — Configuration Settings

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

Security configuration settings for the Links-Matrix Platform are enforced through
policy-as-code at two layers: Kyverno for Kubernetes and AWS Config for cloud resources.

**Kubernetes — Kyverno ClusterPolicies (all in `platform-gitops/kyverno/`):**

| Policy | Enforcement Mode | Setting Enforced |
| ------ | ---------------- | ---------------- |
| `require-run-as-non-root` | Enforce | Pods must set `runAsNonRoot: true` |
| `require-read-only-rootfs` | Enforce | Containers must set `readOnlyRootFilesystem: true` |
| `drop-all-capabilities` | Enforce | All Linux capabilities dropped; explicit adds require ISSO approval |
| `require-resource-limits` | Enforce | CPU and memory limits required on all containers |
| `deny-privileged-containers` | Enforce | `privileged: true` pods rejected |
| `deny-host-namespaces` | Enforce | `hostPID`, `hostIPC`, `hostNetwork` rejected |
| `require-sa-annotation` | Enforce | Service accounts require `secteam.io/owner` annotation |
| `restrict-image-registries` | Enforce | Only `lm-prod-ecr.dkr.ecr.us-east-1.amazonaws.com` and `registry.k8s.io` allowed |
| `require-network-policy` | Audit | Every namespace must have a NetworkPolicy *(moving to Enforce in Q3 2026)* |
| `require-pod-disruption-budget` | Audit | PodDisruptionBudget required for stateful workloads *(operational, not security)* |

**AWS — Config Rules (18 active, mapped to CIS AWS Foundations Benchmark v3.0):**
Non-compliant resources trigger a CloudWatch alarm routed to the SOC on-call and
a Jira `CLOUD-SEC` ticket. Critical rules include:
`s3-bucket-public-read-prohibited`, `restricted-ssh`, `cloud-trail-enabled`,
`iam-no-inline-policy`, `encrypted-volumes`, `rds-storage-encrypted`,
`ec2-security-group-attached-to-eni`, `mfa-enabled-for-iam-console-access`.

**Approved Deviations:**
Settings deviations from the baseline require ISSO written approval and are documented
in the Baseline Deviation Register (Confluence: LM-SECURITY / CM / Baseline Deviations).
Each entry includes: component, setting, deviation description, business justification,
approver, approval date, and review date.

**Responsible Role:** Platform Engineer (Kyverno policies), Cloud Security Engineer (Config rules), ISSO (deviation approval)

**Parameters:**
- Kyverno policy enforcement mode: Enforce (8 of 10 policies); Audit (2 — with Enforce target dates)
- AWS Config rule count: 18 active
- Deviation approval authority: ISSO
- Deviation review cadence: Annual

**Evidence / Artifacts:**
- Kyverno ClusterPolicy manifests in `platform-gitops/kyverno/`
- AWS Config rule list and compliance status (AWS Console → Config → Rules)
- Baseline Deviation Register (Confluence: LM-SECURITY / CM / Baseline Deviations)
- kube-bench CIS Level 1 report (weekly — Confluence: LM-SECURITY / kube-bench Reports)

**Enhancements Addressed:**
- **CM-6(1):** Kyverno enforces settings at admission time (not post-hoc). AWS Config evaluates on resource change. Central management via GitOps — no individual can apply policy changes without PR review.
- **CM-6(2):** Kyverno blocks non-compliant resources at admission. AWS Config triggers automated CloudWatch alarms on non-compliance. ArgoCD detects drift from desired state. *(Note: automated remediation actions for Config rules are partially implemented — 6 of 18 rules have auto-remediation SSM documents; remaining 12 generate alerts only.)*

---

## CM-7 — Least Functionality

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

The Links-Matrix Platform is configured to expose only required services, ports,
protocols, and functions.

**Kubernetes NetworkPolicy:**
A `default-deny-all` NetworkPolicy is applied to all namespaces via a Kyverno mutation
policy (`default-network-policy`) that inserts the deny-all policy at namespace creation.
Explicit allow rules are added per-service in `platform-gitops/network-policies/`.
Currently 12 namespaces have active NetworkPolicies with allow rules; 2 system namespaces
(`monitoring`, `logging`) have broader allow rules with documented justification.

**Container image registry restriction:**
The `restrict-image-registries` Kyverno policy (Enforce mode) rejects any pod spec
referencing an image not from the approved list: ECR `lm-prod-ecr.dkr.ecr.us-east-1.amazonaws.com`
or `registry.k8s.io` (for K8s system components). Attempts to deploy from Docker Hub,
Quay, or any other registry are blocked at admission and logged as Kyverno violations.

**AWS Security Groups:**
All worker node and RDS security groups restrict inbound traffic to required ports
from required CIDRs only. No security group has an inbound rule open to `0.0.0.0/0`
except the ALB on ports 443 (HTTPS) and 80 (redirects to 443). This is enforced by
AWS Config rule `restricted-ssh` and a custom rule `no-unrestricted-ingress-except-alb`.

**Exposed service audit:**
No NodePort or LoadBalancer services exist in production namespaces — all external
traffic enters through the ALB Ingress Controller. This is enforced by Kyverno policy
`deny-nodeport-services` (Enforce mode).

**Quarterly functionality review:**
The ISSO and Platform Engineering Lead conduct a quarterly least-functionality review.
The review examines: K8s services and exposed ports, running DaemonSets and CronJobs,
enabled AWS services and open security group rules, and installed packages in base images.
Last review: 2026-04-07.

**Responsible Role:** Platform Engineer (NetworkPolicy, security groups, Kyverno enforcement), ISSO (quarterly review)

**Parameters:**
- Default NetworkPolicy: deny-all (applied to all namespaces at creation)
- Approved image registries: ECR `lm-prod-ecr`, `registry.k8s.io`
- External ingress: ALB port 443 only (port 80 redirects)
- Quarterly functionality review: January, April, July, October

**Evidence / Artifacts:**
- NetworkPolicy manifests in `platform-gitops/network-policies/`
- Kyverno `restrict-image-registries` policy in `platform-gitops/kyverno/`
- AWS Config custom rule `no-unrestricted-ingress-except-alb` (compliance report)
- Quarterly least-functionality review record (last: 2026-04-07, Confluence: LM-SECURITY / CM / Functionality Reviews)

**Enhancements Addressed:**
- **CM-7(1):** Quarterly functionality review conducted by ISSO and Platform Lead. Review records maintained in Confluence.
- **CM-7(2):** `deny-nodeport-services` Kyverno policy prevents unauthorized service exposure. Falco rule `unexpected-process-in-container` detects unexpected process execution at runtime.
- **CM-7(5):** Kyverno `restrict-image-registries` implements deny-all, permit-by-exception for container images. *(Note: the approved registry list is enforced but not formally documented as a standalone "authorized software list" artifact — the Kyverno policy serves as the authoritative list.)*

---

## CM-8 — System Component Inventory

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

The Links-Matrix Platform component inventory is maintained through a combination of
live Kubernetes API queries, AWS Config, and a weekly automated inventory export.

**Kubernetes inventory:**
All K8s workloads are inventoried via a weekly CronJob (`inventory-export`) that runs
`kubectl get all,serviceaccounts,configmaps,secrets,networkpolicies,ingresses -A -o json`
and uploads the output to S3 `lm-audit-reports/inventory/k8s-YYYY-MM-DD.json`.
The inventory covers: Deployments, StatefulSets, DaemonSets, CronJobs, Services,
Ingresses, ConfigMaps (metadata only), Secrets (metadata only), ServiceAccounts,
and NetworkPolicies.

**AWS resource inventory:**
AWS Config records the configuration state of all resource types in both us-east-1 and
us-west-2. The Config configuration recorder is enabled for all resource types with
continuous recording. Resource inventory is queryable via the AWS Config console or
AWS CLI (`aws configservice list-discovered-resources`).

**Inventory update on deployment:**
The CI/CD pipeline adds a deployment record to Confluence (LM-SECURITY / CM / Deployment Log)
on every production deployment, capturing: component name, image tag, deployment timestamp,
deploying principal, and ArgoCD application name.

**Responsible Role:** Platform Engineer (inventory CronJob, ArgoCD), Cloud Security Engineer (AWS Config recorder)

**Parameters:**
- K8s inventory export cadence: Weekly (Sunday 04:00 UTC)
- AWS Config recording: Continuous, all resource types, both regions

**Evidence / Artifacts:**
- S3 `lm-audit-reports/inventory/` (weekly K8s inventory exports)
- AWS Config resource inventory (AWS Console → Config → Resource Inventory)
- Confluence deployment log (LM-SECURITY / CM / Deployment Log)

**Enhancements Addressed:**
- **CM-8(1):** Deployment pipeline records new components in the Confluence deployment log on every production deploy.
- **CM-8(2):** AWS Config continuous recording provides automated cloud resource inventory. Weekly K8s CronJob exports cluster state automatically.
- **CM-8(3):** AWS Config custom rule `detect-unmanaged-ec2` flags EC2 instances not tagged with `managed-by: terraform`. *(Note: unauthorized container detection within the K8s cluster — a pod deployed outside ArgoCD — is not currently automated. This is an open gap targeted for Q3 2026.)*

---

## What Makes This GOOD (But Not Great) — Examiner's Notes

| Control | Strengths | Gaps |
| ------- | --------- | ---- |
| CM-2 | GitOps repo named, ArgoCD sync, CIS Benchmarks cited, drift SLA defined | No specific CIS coverage percentage; baseline review record location is Confluence but no version number or page ID |
| CM-3 | Full pipeline with named gates, CODEOWNERS, emergency procedure | CM-3(4) security representative is "per-PR not board-based" — flagged as maturity gap, but still a gap; no change board meeting cadence |
| CM-6 | Policy table with enforcement modes, deviation register | 2 of 10 Kyverno policies still in Audit mode with "Q3 2026" target but no POA&M entry; only 6 of 18 Config rules have auto-remediation |
| CM-7 | Deny-all NetworkPolicy, registry restriction, quarterly review | CM-7(5) approved software list is the Kyverno policy itself — not a standalone artifact an auditor can request separately |
| CM-8 | AWS Config + weekly K8s export, deployment log | No SBOM for production images; no unauthorized container detection inside K8s; inventory is weekly snapshot, not real-time |
| Chain | Implicitly connected through GitOps references | CM-2 baseline ↔ CM-8 inventory reconciliation is not described — auditor cannot verify the inventory matches the baseline |
