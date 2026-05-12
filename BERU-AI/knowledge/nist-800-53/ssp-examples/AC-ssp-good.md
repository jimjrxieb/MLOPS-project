# System Security Plan — Access Control (AC) Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** This SSP would pass an initial readiness review but would receive
> several "Clarify" comments from a 3PAO. It shows real implementation but some controls
> are still too high-level and evidence is described rather than cited. Acceptable for
> a Moderate baseline, needs tightening for High or FedRAMP.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Final Draft — Pending ISSO Signature
**Authorization Boundary:** AWS EKS production cluster, supporting services (RDS, S3, ECR),
and the Okta tenant managing human user identities.

---

## AC-2 — Account Management

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Control Origination:** Organization-defined

**Implementation Description:**

The Links-Matrix Platform manages four account types: human user accounts (via Okta), AWS IAM
service roles (for workload identity), Kubernetes service accounts (per-namespace), and
temporary/emergency accounts provisioned through a documented break-glass procedure.

Human accounts are provisioned through an HR-driven Okta workflow. When a new employee is
hired, IT Operations creates their Okta account within 1 business day of their start date.
Access to the Links-Matrix application roles (viewer, editor, admin) requires a manager
approval ticket in Jira. Accounts are disabled within 24 hours of employment termination
via an automated HR system integration.

Quarterly access reviews are conducted by the ISSO and IT Operations team. Each review
produces a sign-off document listing reviewed accounts, approver, and date. Service accounts
in Kubernetes are inventoried in a ServiceAccount manifest in the platform GitOps repo, with
each annotated with an owning team and creation justification.

Accounts inactive for more than 45 days are automatically disabled by an Okta lifecycle rule.

**Responsible Role:** ISSO (primary), IT Operations (implementation)

**Parameters:**
- Inactivity threshold: 45 days
- Account review frequency: Quarterly
- Offboarding SLA: 24 hours from termination notification

**Evidence / Artifacts:**
- Okta audit logs showing account creation, modification, and disabling events
- Quarterly access review records (last review: 2026-04-01, signed by ISSO)
- ServiceAccount manifests in `platform-gitops/namespaces/` repository
- HR integration runbook documenting offboarding automation

**Enhancements Addressed:**
- **AC-2(1):** Okta lifecycle management automates account provisioning and disabling.
- **AC-2(3):** Okta rule disables accounts after 45-day inactivity period.
- **AC-2(4):** Okta System Log and AWS CloudTrail capture account lifecycle events.

---

## AC-3 — Access Enforcement

**Implementation Status:** Implemented

**Control Inheritance:** Hybrid (Inherited: AWS IAM enforcement; System-Specific: K8s RBAC)

**Control Origination:** Inherited from AWS + System-defined

**Implementation Description:**

Access enforcement in Links-Matrix operates at three layers:

1. **AWS IAM:** Application workloads assume named IAM roles via IRSA (IAM Roles for Service
   Accounts). Human access to the AWS console is governed by IAM Identity Center (SSO) with
   role assignments managed by the Cloud Security team. No direct IAM user credentials are
   issued to application workloads.

2. **Kubernetes RBAC:** Each application namespace defines ClusterRoles with verbs scoped to
   required resources only. Role bindings are maintained in the GitOps repo and changes
   require pull request review by the Platform Engineering Lead. No wildcard verb bindings
   exist in production namespaces outside of the `kube-system` namespace.

3. **Application Layer:** The Links-Matrix API enforces authorization via JWT claims issued by
   Okta. Each API endpoint is annotated with required roles. Unauthorized requests receive
   HTTP 403 responses, which are captured in application audit logs.

**Responsible Role:** Platform Engineer (K8s RBAC, AWS IRSA), Cloud Security Engineer (IAM)

**Parameters:** N/A (enforcement is continuous via policy-as-code)

**Evidence / Artifacts:**
- `kubectl get clusterrolebindings,rolebindings -A -o yaml` output (quarterly snapshot)
- IRSA role trust policy documents in Terraform repository
- CloudTrail AccessDenied event sample from last 30 days
- Application audit log showing 403 responses for unauthorized access attempts

**Enhancements Addressed:**
- **AC-3(7):** RBAC is the enforcement model for both K8s and AWS IAM.

---

## AC-5 — Separation of Duties

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Control Origination:** Organization-defined

**Implementation Description:**

The Links-Matrix Platform enforces separation of duties through the following controls:

- **Code deployment:** All changes to production require a pull request with at least one
  approving review from a team member who did not author the change. Branch protection rules
  in GitHub prevent the author from self-approving. The CI/CD pipeline (GitHub Actions) will
  not deploy to production without a passing review and all required status checks.

- **Administrative access:** The role that can create Kubernetes RBAC role bindings
  (`cluster-admin`) is separate from the role that deploys application workloads
  (`deployer`). No single service account holds both permissions.

- **Cloud IAM:** The AWS account admin role and the application deployment role are separate
  IAM roles. The deployment pipeline assumes the `links-matrix-deploy` role, which cannot
  modify IAM policies.

The separation of duties matrix is documented in the Platform Security Runbook (Section 4).

**Responsible Role:** ISSO (policy), Platform Engineer (implementation)

**Parameters:** N/A

**Evidence / Artifacts:**
- GitHub branch protection configuration screenshot (repo settings)
- GitHub Actions workflow YAML showing required approvals for production deployment
- `kubectl get clusterrolebindings -A` showing separation of `cluster-admin` and `deployer` bindings
- Platform Security Runbook, Section 4 — Separation of Duties Matrix

**Enhancements Addressed:** No formal enhancements for AC-5 in NIST 800-53 Rev 5.

---

## AC-6 — Least Privilege

**Implementation Status:** Implemented

**Control Inheritance:** Hybrid (Inherited: AWS IAM boundary controls; System-Specific: K8s RBAC scoping)

**Control Origination:** Inherited from AWS + System-defined

**Implementation Description:**

The principle of least privilege is applied to all account types on the Links-Matrix Platform:

**AWS IAM Roles:** Application workloads use IRSA roles scoped to specific S3 bucket ARNs,
specific RDS instances, and required ECR actions only. IAM permission boundaries are applied
to all non-admin roles to cap maximum privilege. Wildcard (`*`) action or resource statements
require ISSO approval and documented justification. Currently zero wildcard roles exist in
the application account outside of the break-glass admin role.

**Kubernetes RBAC:** Service accounts are scoped to the minimum verbs required by the
workload. The `links-matrix-api` service account has `get`, `list` on ConfigMaps in its
namespace only. No service account has `create` or `delete` on cluster-scoped resources
unless explicitly required and documented.

**Human Access:** Privileged access (AWS Admin, cluster-admin) is restricted to named
individuals. A list of privileged account holders is reviewed quarterly by the ISSO.
Privileged actions trigger alerts via AWS CloudTrail → CloudWatch → PagerDuty.

**Responsible Role:** Cloud Security Engineer (AWS IAM), Platform Engineer (K8s RBAC)

**Parameters:**
- Privileged account review cadence: Quarterly
- Wildcard permission approval authority: ISSO
- Break-glass account review: After each use

**Evidence / Artifacts:**
- IAM Access Analyzer findings report (last run: 2026-04-15, zero external access findings)
- `kubectl get clusterroles -A -o yaml` showing no wildcard verbs on namespaced resources
- Privileged account inventory (maintained in Confluence, last updated 2026-04-01)
- CloudWatch alert configuration for privileged function use (alert ID: `lm-priv-use-alert`)

**Enhancements Addressed:**
- **AC-6(1):** Security functions (KMS, IAM management, CloudTrail config) restricted to named Cloud Security roles.
- **AC-6(5):** Privileged accounts are named and inventoried, reviewed quarterly.
- **AC-6(9):** CloudTrail captures privileged function execution with immutable log storage in S3.

---

## AC-17 — Remote Access

**Implementation Status:** Implemented

**Control Inheritance:** Hybrid (Inherited: AWS Session Manager; System-Specific: kubectl policy)

**Control Origination:** Inherited from AWS + System-defined

**Implementation Description:**

Remote access to the Links-Matrix Platform is controlled through two primary paths:

**Kubernetes API Server access:** Engineers access the cluster via `kubectl` authenticated
through OIDC (Okta as the IdP). Kubeconfigs reference the Okta OIDC endpoint and require
a valid Okta MFA session. Long-lived kubeconfig tokens are not distributed. The cluster API
server is not publicly exposed — it is accessible only within the VPC or via the corporate
VPN (AWS Client VPN with certificate + Okta MFA).

**EC2/Node access:** Direct SSH to worker nodes is disabled. Node access, when required for
incident response, is performed exclusively through AWS Systems Manager Session Manager.
All Session Manager sessions are logged to an S3 bucket with versioning enabled and
a CloudWatch log stream. No inbound port 22 is allowed in any worker node security group.

**Management console:** AWS console access requires SSO through Okta with FIDO2 hardware key
for privileged roles and Okta push for standard roles.

Remote access is documented in the Remote Access Policy (RAP-001, last reviewed 2026-02-01).
The policy lists approved protocols (OIDC kubectl, Session Manager, Client VPN), prohibited
protocols (plaintext SSH to nodes, Telnet, unencrypted HTTP), and session monitoring
requirements.

**Responsible Role:** Platform Engineer (kubectl/cluster access), Cloud Security Engineer (VPN, Session Manager)

**Parameters:**
- Approved remote access methods: OIDC kubectl via VPN, AWS Session Manager
- Prohibited protocols: Direct SSH to nodes, Telnet, RDP without MFA
- Session log retention: 365 days (S3 + CloudWatch Logs)

**Evidence / Artifacts:**
- Okta OIDC integration configuration for EKS cluster (AWS console screenshot)
- Security group rules showing no inbound port 22 on worker nodes (`aws ec2 describe-security-groups`)
- Session Manager session log sample from S3 bucket `lm-ssm-session-logs`
- AWS Client VPN configuration showing MFA requirement (Okta SAML integration)
- Remote Access Policy document RAP-001

**Enhancements Addressed:**
- **AC-17(1):** CloudWatch monitors remote access sessions; PagerDuty alerts on anomalous source IPs.
- **AC-17(2):** All remote sessions use TLS (OIDC/HTTPS, Session Manager HTTPS). No plaintext protocols allowed.
- **AC-17(3):** All remote access routes through VPN or Session Manager (managed access control points).

---

## What Makes This GOOD (But Not Great) — Examiner's Notes

| Control | Strengths | Gaps |
|---------|-----------|------|
| AC-2 | Named tool (Okta), defined intervals, specific offboarding SLA, enhancement coverage | Missing: account type table with all types; no mention of guest/anonymous accounts; AC-2(2) for temp/emergency accounts not explicitly addressed |
| AC-3 | Three enforcement layers named, IRSA specifically called out | Missing: Kyverno/OPA policy enforcement layer; no mention of what happens to AccessDenied events — are they reviewed? |
| AC-5 | Specific pipeline controls named, matrix document referenced | Missing: "who can't do what" is implied but not stated explicitly in the SSP; no test procedure to verify self-approval is blocked |
| AC-6 | IRSA, permission boundaries, zero wildcards claim documented | Missing: AC-6(2) non-privileged accounts for non-security functions; AC-6(10) not addressed; no automated scan verifying zero wildcards on schedule |
| AC-17 | Session Manager, OIDC, MFA all named specifically | Missing: AC-17(4) privileged commands via remote access not addressed; no anomalous access detection thresholds defined |
| All | Real technology names, real parameters, actual evidence described | Evidence is *described*, not *linked*. No OSCAL implementation-status tagging. No test procedures with expected results. |
