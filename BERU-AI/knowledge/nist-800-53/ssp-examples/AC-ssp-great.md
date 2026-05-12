# System Security Plan — Access Control (AC) Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** This SSP is auditor-ready. Every control names the mechanism, the owner,
> the parameters with real values, and the exact artifact an auditor would request. A 3PAO
> could walk in tomorrow, pull this document, and know exactly what to test and where to find
> the evidence. No TBDs. No vague language. Every enhancement addressed or explicitly justified
> as not applicable.

---

**System Name:** Links-Matrix Platform
**System Owner:** J. Rivera, Platform Engineering Lead (jrivera@links-matrix.io)
**ISSO:** M. Chen, Information System Security Officer (mchen@links-matrix.io)
**Prepared By:** M. Chen, ISSO
**Date:** 2026-05-01
**Review Date:** 2027-05-01 (annual) or upon significant system change
**Status:** Approved — ATO Granted 2026-03-15, expires 2029-03-15
**Authorization Boundary:** The Links-Matrix Platform authorization boundary encompasses:
the AWS EKS production cluster (`lm-prod-eks-us-east-1`), all namespaces within that cluster,
the supporting AWS services (RDS PostgreSQL `lm-prod-db`, S3 buckets `lm-data-*` and
`lm-logs-*`, ECR registry `lm-prod-ecr`, KMS key `lm-cmk-prod`), the Okta tenant
(`links-matrix.okta.com`) managing all human user identities, and the AWS Client VPN endpoint
(`cvpn-endpoint-0a1b2c3d`). Systems outside this boundary are noted as leveraged systems
with a shared responsibility designation.

---

## AC-2 — Account Management

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Moderate and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Account Types

| Account Type | System | Provisioning Method | Approver | Review Cadence |
|---|---|---|---|---|
| Human user (standard) | Okta → Links-Matrix App | HR HRIS → Okta lifecycle rule | Manager via Jira LM-ACCESS | Quarterly |
| Human user (privileged) | AWS IAM Identity Center | Manual — ISSO approval required | ISSO | Quarterly + after each use |
| Kubernetes service account | K8s cluster | GitOps PR to `platform-gitops/` repo | Platform Engineering Lead | Quarterly (automated scan) |
| AWS IAM role (workload identity) | AWS IAM via Terraform | Terraform PR to `infra-iac/` repo | Cloud Security Engineer | Quarterly (IAM Access Analyzer) |
| Temporary/emergency (break-glass) | AWS IAM + K8s | ISSO-signed break-glass runbook (BG-001) | ISSO | After each use + quarterly |
| Guest/anonymous | None | Not supported — no guest access model | N/A | N/A |

### Implementation Description

**Provisioning:** Human accounts are provisioned through an automated integration between
the Workday HRIS and Okta. When a new hire record is marked "active" in Workday, an Okta
user is created within 4 hours via SCIM. Application access (viewer, editor, operator, admin)
is assigned by the manager through a Jira service request (`LM-ACCESS` project). Jira is
configured to require ISSO co-approval for `admin` role assignments. No manual account
creation bypasses the Jira workflow; this is enforced by an Okta API access restriction.

**Modification:** Role changes require a new Jira request. Role expansion (adding permissions)
requires manager + ISSO approval. Role reduction (removing permissions) requires manager
approval only. All modifications generate an audit event in Okta System Log with the
requesting user, approver, change type, and timestamp.

**Disabling:** Upon employment termination, Workday marks the employee inactive. The Okta
SCIM integration suspends (not deletes) the account within 2 hours. Account suspension is
logged and triggers a PagerDuty alert to the IT Operations on-call. The suspended account
retains its attributes for 30 days to support offboarding investigations, then is permanently
deleted. This 2-hour SLA is verified monthly by IT Operations against the HR termination log.

**Inactivity:** Okta lifecycle automation disables accounts with no authentication event in
30 days. Disabled accounts trigger a notification to the account's manager and to the ISSO
distribution list. Re-enablement requires a new Jira access request.

**Access Review:** The ISSO runs a quarterly access review using the `access-review.sh` script
in `platform-gitops/tools/`. The script pulls current Okta user-role assignments, compares
to the approved access list in Confluence (space: `LM-SECURITY`, page: `Access Register`),
and produces a delta report. Each manager must certify their team's access in Jira within
10 business days. Unresponded reviews escalate to the ISSO for enforcement action.

**Service Accounts:** Every Kubernetes service account and AWS IAM role used by workloads is
defined in the GitOps repository (`platform-gitops/serviceaccounts/` and `infra-iac/iam/`).
Each manifest includes a required `secteam.io/owner` annotation and a `secteam.io/purpose`
annotation. A Kyverno policy (`require-sa-annotation`) rejects service account creation
that omits these annotations. The service account inventory is auto-generated weekly by a
CronJob and posted to Confluence (page: `Service Account Inventory`).

**Responsible Role:** ISSO (primary owner, reviews, escalation), IT Operations (provisioning,
offboarding automation), Platform Engineer (K8s service accounts), Cloud Security Engineer
(AWS IAM roles)

**Parameters:**
- Inactivity period triggering disable: **30 days**
- Temporary account maximum lifetime: **72 hours** (break-glass), auto-expires via Okta rule
- Emergency account maximum lifetime: **8 hours** (Kubernetes), auto-deleted by CronJob
- Access review frequency: **Quarterly** (January, April, July, October — first Monday)
- Offboarding SLA: **2 hours** from Workday termination event to Okta suspension
- Account deletion after suspension: **30 days**

**Evidence / Artifacts:**

| Artifact | Location | Frequency |
|---|---|---|
| Okta System Log (account lifecycle events) | Okta Admin → Reports → System Log | Continuous; exported to S3 `lm-logs-okta/` daily |
| Quarterly access review records | Confluence: LM-SECURITY / Access Reviews | Quarterly — last: 2026-04-07, signed by M. Chen |
| Service account inventory | Confluence: LM-SECURITY / Service Account Inventory | Weekly auto-generated |
| Offboarding SLA compliance report | IT Ops runbook `offboarding-sla-report.sh` | Monthly |
| Break-glass use log | ISSO-maintained `break-glass-log.md` in `platform-gitops/security/` | Per-use |

**Test Procedure:**
1. Select three accounts from the last quarterly access review.
2. Verify each account's current Okta status matches the approved access register.
3. Select one terminated employee from the last 90 days. Verify their Okta account was
   suspended within 2 hours of the Workday termination timestamp.
4. Query Okta System Log for `user.lifecycle.deactivate` events — verify timestamp delta.
5. Inspect the ServiceAccount manifests in `platform-gitops/serviceaccounts/` — verify
   every manifest has `secteam.io/owner` and `secteam.io/purpose` annotations.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
|---|---|---|
| AC-2(1) Automated System Account Management | Implemented | Okta SCIM + lifecycle automation handles provisioning/disabling without manual steps. Kyverno enforces service account annotation requirements. |
| AC-2(2) Automated Temporary/Emergency Account Management | Implemented | Okta rule auto-expires temporary accounts at 72-hour mark. K8s emergency service accounts auto-deleted by `emergency-account-cleanup` CronJob after 8 hours. |
| AC-2(3) Disable Inactive Accounts | Implemented | Okta lifecycle rule disables human accounts after 30 days of inactivity. AWS IAM Access Analyzer flags IAM roles unused for 90+ days; ISSO reviews findings monthly. |
| AC-2(4) Automated Audit Actions | Implemented | All account lifecycle events (creation, modification, disabling, deletion) are written to Okta System Log and AWS CloudTrail. Logs are immutable (S3 Object Lock + CloudTrail log file validation). |

---

## AC-3 — Access Enforcement

**Implementation Status:** Implemented
**Control Origination:** Hybrid (Inherited from AWS IAM; System-Specific for K8s RBAC and app-layer)
**Baseline Allocation:** Low, Moderate, and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Implementation Description

Access enforcement operates at four distinct layers, each with its own policy source of truth,
enforcement point, and audit trail. Enforcement is non-discretionary at the IAM and K8s API
layers — no user-side override exists.

**Layer 1 — AWS IAM (Inherited from AWS):**
The AWS IAM service enforces all authorization decisions for AWS API calls. The Links-Matrix
application workloads use IAM Roles for Service Accounts (IRSA) — each Kubernetes workload
assumes a named IAM role with a trust policy scoped to the specific service account in its
specific namespace. No static IAM user credentials are issued to application workloads.
Policies are written in Terraform (`infra-iac/iam/`) and require a pull request with
Cloud Security Engineer approval before apply. Service Control Policies (SCPs) at the AWS
Organization level enforce an additional deny layer that cannot be overridden by account-level
policies. Key SCPs enforced: deny S3 bucket public-access override, deny CloudTrail
modification, deny KMS key deletion.

**Layer 2 — Kubernetes RBAC:**
The K8s API server enforces RBAC for all kubectl and in-cluster API calls. RBAC policies
are managed exclusively via GitOps (`platform-gitops/rbac/`). Direct kubectl apply of RBAC
resources is blocked by a Kyverno policy (`block-direct-rbac-apply`) that rejects any
ClusterRole or ClusterRoleBinding not originating from the ArgoCD service account. This
prevents ad-hoc privilege escalation bypassing the GitOps review process.

Current production RBAC assignments are verified quarterly via `rbac-audit.sh`. The last audit
(2026-04-07) confirmed zero wildcard-verb bindings on namespaced resources outside of
`kube-system`. Kyverno policy `deny-wildcard-rbac` continuously rejects any new wildcard
ClusterRole that is not in the approved exception list (currently empty).

**Layer 3 — Application Authorization:**
The Links-Matrix API server enforces authorization on every API endpoint using JWT claims
issued by Okta. The `role` claim in the JWT is mapped to one of four application roles:
`viewer`, `editor`, `operator`, `admin`. Each API handler is annotated with required minimum
role. Unauthorized requests return HTTP 403 and generate an application audit log entry
(`/var/log/lm-audit/access-denied.jsonl`) with user ID, role claimed, endpoint requested,
and source IP. Application audit logs are shipped to OpenSearch via Fluent Bit for SIEM
analysis.

**Layer 4 — Network Enforcement (Defense in Depth):**
Kubernetes NetworkPolicy objects in each namespace enforce microsegmentation — pods can
only initiate connections to explicitly allowed destinations. The `default-deny-all` policy
is applied to all namespaces at creation via a Kyverno mutation policy. This means access
enforcement exists even if the application layer were to be bypassed.

**Responsible Role:** Platform Engineer (K8s RBAC, NetworkPolicy), Cloud Security Engineer
(AWS IAM, SCPs), Application Developer (app-layer authorization)

**Parameters:** Not applicable (enforcement is continuous and automated)

**Evidence / Artifacts:**

| Artifact | Location | Frequency |
|---|---|---|
| K8s RBAC audit report | `platform-gitops/security/rbac-audit-YYYY-QQ.md` | Quarterly |
| Kyverno policy evaluation log | K8s events + Fluent Bit → OpenSearch index `lm-kyverno-*` | Continuous |
| CloudTrail AccessDenied events | S3 `lm-logs-cloudtrail/` | Continuous; SIEM alert on patterns |
| Application access-denied log | OpenSearch index `lm-access-denied-*` | Continuous |
| IRSA trust policy documents | `infra-iac/iam/` in Terraform repo | Per-change (git history) |

**Test Procedure:**
1. Attempt to create a wildcard ClusterRole via kubectl directly (not through ArgoCD) —
   verify Kyverno blocks the request and records a policy violation event.
2. Call the Links-Matrix API as a `viewer` role user against an `operator`-only endpoint —
   verify HTTP 403 response and audit log entry.
3. Attempt cross-namespace pod communication blocked by NetworkPolicy — verify connection
   is refused and the NetworkPolicy is applied.
4. Review CloudTrail for any `sts:AssumeRole` calls from unexpected principals — verify
   IRSA trust policy scoping is enforced.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
|---|---|---|
| AC-3(4) Discretionary Access Control | Not Applicable | Links-Matrix does not implement a discretionary model. All access is non-discretionary: IAM policies and K8s RBAC are centrally managed and cannot be modified by end users. Documented in Security Architecture Decision Record ADR-012. |
| AC-3(7) Role-Based Access Control | Implemented | RBAC is the enforcement model at K8s (ClusterRole/RoleBinding), AWS IAM (role-based trust policies), and application layer (JWT role claims). All three tiers enforce the same four-role model: viewer, editor, operator, admin. |

---

## AC-5 — Separation of Duties

**Implementation Status:** Implemented
**Control Origination:** System-Specific
**Baseline Allocation:** Moderate and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Separation of Duties Matrix

The following table defines conflicting permission combinations and the control that prevents
any single principal from holding both:

| Conflicting Capability A | Conflicting Capability B | Control Preventing Combination |
|---|---|---|
| Write code / author PR | Approve and merge PR to main | GitHub branch protection: `require_pull_request_reviews`, `dismiss_stale_reviews`, `require_code_owner_reviews`. Authors cannot self-approve. |
| Trigger production deploy | Approve production deploy gate | GitHub Actions environment `production` requires a second approving reviewer from the `platform-leads` team, distinct from the deployer. |
| Create K8s RBAC role | Apply K8s RBAC role binding | GitOps separation: RBAC definitions and bindings are in separate directories with separate CODEOWNERS. The Kyverno `block-direct-rbac-apply` policy prevents bypassing ArgoCD. |
| Create IAM role | Attach IAM policy to role | Separate Terraform modules with separate AWS IAM conditions. The deployment role (`lm-deploy`) cannot call `iam:AttachRolePolicy` — this action is restricted to the `infra-admin` role requiring ISSO approval. |
| Generate break-glass credentials | Approve break-glass use | Break-glass runbook (BG-001) requires ISSO written approval before the `break-glass-activate.sh` script will execute. The script validates an ISSO-signed Jira ticket ID. |

### Implementation Description

Separation of duties is implemented as a layered technical control, not solely a policy
requirement. The controls above cannot be bypassed by a single user because they are enforced
at the GitHub API level (branch protection), the Kubernetes admission control level (Kyverno),
the ArgoCD sync level, and the AWS IAM condition level.

All SoD controls are documented in the Platform Security Runbook, Section 4
(`platform-gitops/docs/security-runbook.md`). Changes to the SoD matrix require a Security
Architecture Review (SAR) documented in an ADR.

The SoD configuration is verified quarterly: the ISSO reviews GitHub branch protection
settings and pulls the CODEOWNERS file, the ArgoCD environment protection rules, and the
IAM condition policies to confirm no single identity holds conflicting capabilities.

**Responsible Role:** ISSO (policy owner, quarterly verification), Platform Engineering Lead
(technical implementation of branch protection and GitOps controls), Cloud Security Engineer
(IAM condition enforcement)

**Parameters:** Not applicable (controls are always-enforced, not parameterized)

**Evidence / Artifacts:**

| Artifact | Location | Frequency |
|---|---|---|
| GitHub branch protection configuration | Repo settings → Branches (screenshot in quarterly SoD review) | Annual review + change-triggered |
| ArgoCD environment protection rules | `platform-gitops/argocd/production-app.yaml` | Per-change (git history) |
| CODEOWNERS file | `platform-gitops/CODEOWNERS` | Per-change (git history) |
| IAM condition policies preventing iam:AttachRolePolicy | `infra-iac/iam/deploy-role.tf` | Per-change (git history) |
| Quarterly SoD verification report | `platform-gitops/security/sod-review-YYYY-QQ.md` | Quarterly |
| Break-glass activation log | `platform-gitops/security/break-glass-log.md` | Per-use |

**Test Procedure:**
1. As an author of an open PR, attempt to approve and merge your own PR — verify GitHub
   blocks self-approval.
2. As a user in the `deployer` role (not `platform-leads`), attempt to approve the
   production environment deployment gate — verify GitHub Actions blocks the approval.
3. Attempt to apply a ClusterRoleBinding directly via kubectl — verify Kyverno blocks and
   records a policy violation.
4. As the `lm-deploy` IAM role, attempt `iam:AttachRolePolicy` — verify AccessDenied from
   IAM condition, captured in CloudTrail.

**Enhancements Addressed:** No enhancements defined for AC-5 in NIST SP 800-53 Rev 5.

---

## AC-6 — Least Privilege

**Implementation Status:** Implemented
**Control Origination:** Hybrid (Inherited from AWS IAM boundary controls; System-Specific for K8s RBAC scoping and privileged account management)
**Baseline Allocation:** Low, Moderate, and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Implementation Description

Least privilege is applied as a standing constraint across all account types. It is enforced
by automated tooling and verified by a quarterly review. The current state is zero wildcard
`*` action or resource statements in any application-owned IAM policy or K8s ClusterRole.
This claim is verified by automated scans described below.

**AWS IAM — Workload Identity (IRSA):**
Each AWS IAM role used by a Kubernetes workload is defined in `infra-iac/iam/` with explicit
`Allow` statements scoped to specific ARNs and required actions. Example: the
`lm-api-s3-read` role allows only `s3:GetObject` and `s3:ListBucket` on `arn:aws:s3:::lm-data-*`.
A CI pipeline job (`iam-policy-lint.py`) runs on every pull request to the `infra-iac/`
repository. It rejects any policy document containing a `*` action or `*` resource without
an ISSO-approved exception comment in the code. The exception list is empty as of 2026-05-01.

All non-break-glass IAM roles have a permission boundary (`lm-permission-boundary-policy`)
that hard-caps the maximum privilege the role can hold, regardless of what is attached.
This boundary prevents privilege escalation even if a policy error grants excess permissions.

**Kubernetes RBAC — Service Accounts:**
RBAC roles for service accounts are defined at the minimum verb level required by the workload.
This is documented in each workload's threat model (`platform-gitops/threat-models/`).
The `rbac-minimizer.sh` script compares deployed ClusterRoles against API server audit logs
to identify unused verbs. It runs monthly in CI and produces a report; unused verbs are
removed in the following sprint.

**Human Privileged Access:**
Privileged access (cluster-admin K8s, AWS account admin, IAM administrator) is granted only
to named individuals whose role requires it. The current privileged account list is:

| Account | Principal | System | Justification | Last Reviewed |
|---|---|---|---|---|
| cluster-admin | M. Chen (ISSO) | K8s | ISSO incident response requirement | 2026-04-07 |
| cluster-admin | J. Rivera (Platform Lead) | K8s | Platform operations | 2026-04-07 |
| AWS account admin | Cloud Security team (2 members) | AWS | Break-glass only | 2026-04-07 |

Standard engineers do not hold cluster-admin or AWS admin. All privileged operations in
production are performed via time-limited role assumption with CloudTrail logging.

A CloudWatch alarm (`lm-priv-function-alarm`) triggers a PagerDuty alert for any IAM
`AssumeRole` event for admin roles or any K8s API call to `cluster-admin`-gated endpoints.
Alerts are reviewed by the ISSO within 1 business hour during business hours, 4 hours
outside.

**Responsible Role:** Cloud Security Engineer (IAM least privilege, permission boundaries),
Platform Engineer (K8s RBAC), ISSO (privileged account list ownership, quarterly review)

**Parameters:**
- Wildcard permission approval authority: ISSO
- Unused privilege removal target: Within 1 sprint of identification
- Privileged account review cadence: Quarterly
- Privileged function alert response SLA: 1 hour (business hours), 4 hours (off-hours)

**Evidence / Artifacts:**

| Artifact | Location | Frequency |
|---|---|---|
| IAM Access Analyzer findings | AWS Console → Access Analyzer; exported to S3 `lm-logs-access-analyzer/` | Continuous; monthly ISSO review |
| CI policy lint report (no wildcards) | GitHub Actions run history for `infra-iac/` PRs | Per-PR |
| RBAC minimizer report | `platform-gitops/security/rbac-minimizer-YYYY-MM.md` | Monthly |
| Privileged account inventory | Confluence: LM-SECURITY / Privileged Accounts | Quarterly |
| CloudWatch alarm config for privileged use | `infra-iac/monitoring/priv-alerts.tf` | Per-change |
| Quarterly least-privilege review record | `platform-gitops/security/lp-review-YYYY-QQ.md` | Quarterly |

**Test Procedure:**
1. Pull all IAM policies from `infra-iac/iam/` and verify zero `*` actions or resources
   without approved exception comment.
2. Run `kubectl get clusterroles -A -o json | jq '.items[].rules[].verbs'` — verify no
   wildcard verbs in non-system ClusterRoles.
3. Pull the K8s audit log for the last 30 days and verify that every cluster-admin API call
   maps to a named principal on the privileged account list.
4. Verify permission boundary `lm-permission-boundary-policy` is attached to all
   non-break-glass IAM roles via AWS CLI:
   `aws iam list-roles --query 'Roles[?PermissionsBoundary==null]'` — expect zero results
   outside of break-glass roles.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
|---|---|---|
| AC-6(1) Authorize Access to Security Functions | Implemented | IAM policies governing security functions (KMS key management, CloudTrail config, Security Hub, GuardDuty) are restricted to the `cloud-security-admin` role. K8s admission control configuration (Kyverno policies) is modifiable only via ArgoCD with Cloud Security or ISSO approval. |
| AC-6(2) Non-Privileged Access for Nonsecurity Functions | Implemented | Engineers with cluster-admin have a separate standard-user account for daily work (coding, PR review, Slack). The privileged account is used only for operations requiring elevated access and is documented in the acceptable use policy (AUP-003). |
| AC-6(5) Privileged Accounts | Implemented | See Privileged Account table above. All privileged accounts are named, justified, and reviewed quarterly by the ISSO. Shared privileged accounts are not permitted. |
| AC-6(9) Log Use of Privileged Functions | Implemented | CloudWatch alarm `lm-priv-function-alarm` triggers on all admin role assumption and cluster-admin API calls. CloudTrail logs are immutable (S3 Object Lock — compliance mode, 7-year retention). K8s audit logs are forwarded to OpenSearch and retained for 1 year. |
| AC-6(10) Prohibit Non-Privileged Users from Executing Privileged Functions | Implemented | IAM deny conditions and K8s RBAC prevent standard user accounts from executing privileged functions. Kyverno `deny-privileged-sa` policy prevents non-admin service accounts from requesting privileged pod security contexts. Enforcement is technical, not policy-only. |

---

## AC-17 — Remote Access

**Implementation Status:** Implemented
**Control Origination:** Hybrid (Inherited from AWS Systems Manager; System-Specific for kubectl OIDC policy, VPN config, session monitoring)
**Baseline Allocation:** Low, Moderate, and High
**Last Reviewed:** 2026-05-01 by M. Chen (ISSO)

### Approved Remote Access Methods

| Access Type | Mechanism | Authentication | MFA Required | Session Logging |
|---|---|---|---|---|
| Kubernetes API (kubectl) | OIDC via Okta + AWS Client VPN | Okta OIDC token + VPN cert | Yes — Okta MFA (FIDO2 for privileged) | K8s audit log → OpenSearch |
| AWS console (standard) | Okta SSO → AWS IAM Identity Center | Okta SAML + Okta Push MFA | Yes | CloudTrail |
| AWS console (privileged) | Okta SSO → AWS IAM Identity Center | Okta SAML + FIDO2 hardware key | Yes (FIDO2 required) | CloudTrail + ISSO notification |
| EC2/node access | AWS Systems Manager Session Manager | IAM role + Session Manager policy | Inherited from AWS console auth | Session Manager log → S3 `lm-ssm-sessions/` + CloudWatch |
| CI/CD pipeline | GitHub Actions OIDC → AWS STS | GitHub Actions OIDC token | N/A (machine identity) | CloudTrail + GitHub Actions audit log |

### Prohibited Remote Access Methods

The following are explicitly prohibited and blocked by technical controls:

| Prohibited Method | Blocking Control |
|---|---|
| Direct SSH to worker nodes (port 22) | Security group `lm-worker-sg` has no inbound rule for port 22 (verified by AWS Config rule `lm-no-ssh-0.0.0.0`) |
| Telnet | No open port 23 in any security group; blocked by VPC NACL |
| Unencrypted HTTP to management endpoints | ALB listener redirects port 80 to 443; no HTTP management endpoints exist |
| kubectl with static long-lived kubeconfig tokens | Cluster configured for OIDC only; static token authentication is disabled at the API server (`--token-auth-file` not set) |
| RDP without MFA | Not applicable — no Windows instances in boundary |

### Implementation Description

**Kubernetes API Access:** Engineers access the cluster via kubectl configured with an Okta
OIDC token. The EKS cluster authenticates against the Okta OIDC endpoint
(`https://links-matrix.okta.com/oauth2/default`). Token lifetime is 1 hour; engineers
re-authenticate via `okta-aws-cli` or the `kubelogin` plugin. The kubeconfig distributed
to engineers does not contain credentials — it references the OIDC endpoint only. Access
to the cluster API server is restricted at the network level to the VPN CIDR
(`10.128.0.0/14`) via EKS security group `lm-eks-api-sg`.

**Node Access:** Direct SSH to worker nodes is technically impossible — no SSH daemon runs
on nodes (validated by the `node-no-ssh` Falco rule which alerts if sshd starts on any node)
and the security group permits no inbound traffic on port 22. When node-level access is
required for incident response, the Security Operations runbook (IR-RUNBOOK-002, Section 3)
specifies using AWS Systems Manager Session Manager. All Session Manager sessions are
automatically logged to S3 bucket `lm-ssm-sessions-prod` (versioning + Object Lock enabled)
and mirrored to CloudWatch log group `/aws/ssm/lm-prod-sessions`.

**Remote Access Policy:** The Remote Access Policy (RAP-001, last reviewed 2026-02-01,
approved by ISSO and System Owner) governs all remote access. It specifies: approved
protocols and tools, MFA requirements, session duration limits (kubectl OIDC token: 1 hour;
Session Manager session: 4-hour auto-termination), prohibited protocols, logging requirements,
and violation reporting procedures. RAP-001 is incorporated into the annual security awareness
training delivered to all engineers.

**Session Monitoring:** An EventBridge rule triggers a Lambda function on all
`AWS API Call via CloudTrail` events matching `sts:AssumeRole` for privileged IAM roles
from source IPs outside the corporate IP range (`52.x.x.x/29`). The Lambda sends a real-time
alert to the ISSO Slack channel (`#sec-alerts`) and creates a PagerDuty incident. Similarly,
Falco rule `unexpected-kubectl-source-ip` alerts on kubectl API calls originating from IPs
not in the VPN CIDR.

**Responsible Role:** Platform Engineer (kubectl OIDC configuration, VPN integration),
Cloud Security Engineer (Session Manager, VPN endpoint, security groups),
ISSO (policy ownership, anomalous access review)

**Parameters:**
- Approved VPN CIDR: 10.128.0.0/14
- kubectl OIDC token lifetime: 1 hour
- Session Manager session auto-termination: 4 hours
- Session log retention: 365 days (S3 + CloudWatch)
- Anomalous remote access alert response SLA: 30 minutes
- Remote Access Policy review cycle: Annual (next: 2027-02-01)

**Evidence / Artifacts:**

| Artifact | Location | Frequency |
|---|---|---|
| EKS API server security group config | `infra-iac/eks/cluster.tf` + AWS Console (sg `lm-eks-api-sg`) | Per-change |
| Worker node security group (no SSH) | `infra-iac/eks/nodegroup.tf` + AWS Config rule `lm-no-ssh-0.0.0.0` | Continuous (Config) |
| kubectl OIDC integration config | AWS Console → EKS → Authentication (OIDC provider ARN) | Per-change |
| Session Manager session logs | S3 `lm-ssm-sessions-prod/` + CW log group `/aws/ssm/lm-prod-sessions` | Per-session |
| CloudTrail remote access events | S3 `lm-logs-cloudtrail/` | Continuous |
| EventBridge rule for anomalous assume-role | `infra-iac/monitoring/remote-access-alerts.tf` | Per-change |
| Remote Access Policy RAP-001 | Confluence: LM-SECURITY / Policies / RAP-001 | Annual review |
| VPN endpoint config and MFA settings | `infra-iac/vpn/client-vpn.tf` | Per-change |

**Test Procedure:**
1. Attempt to SSH to a worker node IP — verify connection refused (no open port 22) and
   confirm AWS Config rule `lm-no-ssh-0.0.0.0` shows compliant for all worker node SGs.
2. Attempt kubectl access without VPN connection — verify connection timeout to EKS API
   endpoint (API server not reachable outside VPN CIDR).
3. Attempt kubectl with an expired OIDC token (>1 hour old) — verify 401 Unauthorized and
   prompt to re-authenticate.
4. Start an AWS Systems Manager Session Manager session on a worker node — verify session
   appears in CloudWatch log group `/aws/ssm/lm-prod-sessions` and S3 within 60 seconds.
5. Simulate an assume-role event from an IP outside the corporate range in a test account —
   verify PagerDuty incident and Slack `#sec-alerts` message are generated within 5 minutes.

**Enhancements Addressed:**

| Enhancement | Status | Implementation |
|---|---|---|
| AC-17(1) Monitoring and Control | Implemented | EventBridge + Lambda monitors all remote IAM role assumption for anomalous source IPs. Falco monitors kubectl API calls for unexpected source IPs. PagerDuty alerts generate within 5 minutes. |
| AC-17(2) Protection of Confidentiality and Integrity Using Encryption | Implemented | All remote access paths use TLS 1.2 minimum (kubectl OIDC/HTTPS, Session Manager over HTTPS, VPN using TLS 1.2 cipher suites). Cipher suite configuration is documented in `infra-iac/vpn/client-vpn.tf`. No plaintext protocols exist for any management path. |
| AC-17(3) Managed Access Control Points | Implemented | All remote access must transit either the Client VPN endpoint or AWS Session Manager. Direct internet-facing access to the K8s API server or EC2 nodes is technically blocked by security group configuration. There is no other ingress path. |
| AC-17(4) Privileged Commands and Access | Implemented | Use of cluster-admin and AWS admin roles via remote access requires a documented change request or incident ticket. Undocumented privileged remote access triggers PagerDuty alert. The break-glass procedure (BG-001) documents the approval chain for emergency privileged remote access. |

---

## What Makes This GREAT — Side-by-Side Comparison

| Dimension | Bad | Good | Great |
|---|---|---|---|
| **Parameters** | "Periodically", "TBD", "As needed" | Named values (e.g., "45 days", "Quarterly") | Specific org-defined values with justification and contractual SLA where required |
| **Technology named** | None | Tool names (Okta, IRSA, Session Manager) | Tool + specific resource IDs, config file paths, and Terraform module locations |
| **Evidence** | "Policy document" (unspecified) | Evidence described by type | Evidence table: artifact, location, frequency, and last verified date |
| **Enhancements** | Not addressed | Partial — some missing or "not applicable" without justification | Every enhancement: implemented with specifics OR not-applicable with documented justification (ADR number) |
| **Test procedure** | None | None | Step-by-step test with expected result — a 3PAO can run it without asking for clarification |
| **Ownership** | "IT Department" | Role title | Named role + name + email + escalation path |
| **Scope** | Implicit | Authorization boundary stated | Full boundary table with system IDs, ARNs, and third-party leveraged services identified |
| **Vague language** | "We strive to", "We try to", "As appropriate" | Rare but present | Zero — every statement is verifiable or cited |
| **Account types** | "Users" | Four types mentioned | Complete account type table with provisioning, approver, and review cadence per type |
| **SoD** | "We separate duties" | Pipeline controls named | Matrix of conflicting capabilities with the specific technical control preventing each conflict |
| **Least privilege** | "We follow least privilege" | Tools named, wildcard claim made | Automated scan enforcing zero wildcards in CI; RBAC minimizer eliminating unused verbs monthly |
| **Remote access** | "We use VPN" | VPN + Session Manager + OIDC named | Approved/prohibited method table, blocking controls named, session termination timers, alert SLAs |
| **Auditor readiness** | Would fail readiness review | Would pass with 5-10 clarification items | 3PAO could start testing tomorrow with no additional questions |
