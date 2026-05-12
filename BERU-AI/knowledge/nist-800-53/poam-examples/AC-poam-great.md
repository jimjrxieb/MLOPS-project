# POA&M — Access Control (AC) Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Auditor-ready POA&M. All deficiencies are numbered within each weakness.
> Remediation owners are split between evidence producer and sign-off authority. Due dates
> follow severity-based priority tiers. Milestones include M1, M2, and M3 with exact dated
> actions. Validation commands include expected output. Residual risk identifies the specific
> remaining gap after remediation. Status history shows full progression from OPEN to CLOSED.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** AC-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-001 | AC-2 — Account Management | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-002 | AC-3 — Access Enforcement | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-003 | AC-5 — Separation of Duties | High | P2 30 Days | 2026-06-09 |
| POAM-2026-05-004 | AC-6 — Least Privilege | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-005 | AC-17 — Remote Access | Critical | P1 Immediate | 2026-05-17 |

---

## POAM-2026-05-001 — AC-2

```text
POAM-ID:          POAM-2026-05-001
CONTROL:          AC-2 — Account Management

WEAKNESS:
  Four deficiencies identified on Links-Matrix (AWS IAM / Okta SCIM):
  (1) CloudTrail management events not enabled for IAM category — CreateUser and DeleteUser
      events produce 0 results over 90-day lookback window.
  (2) No quarterly access review produced — ITOps verbal statement only; no artifact, no
      reviewer sign-off, no Confluence record.
  (3) No service account inventory — Terraform state not exported; ISSO approval workflow
      not documented.
  (4) No offboarding SLA documentation — no evidence terminated users are disabled within
      4 hours as SSP asserts.

SYSTEM AFFECTED:  Links-Matrix (AWS IAM, Okta SCIM, CloudTrail)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AC-2?env=bad → tool: cloudtrail, status: insufficient,
                  DeleteUser_events_90d: 0, CreateUser_events_90d: 0, last_access_review: null.
                  ITOps interview: no artifacts produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AC-2-2026-05-10/AC-2-finding.json

REMEDIATION OWNER: ITOps (evidence producer) / ISSO (quarterly review owner and sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Enable CloudTrail management events for IAM in us-east-1; run test CreateUser
                  action and confirm event captured in trail within 5 minutes; export event
                  JSON to evidence path.
  M2: 2026-05-14  Complete Q2 2026 access review using IAM credential report; ISSO signs off;
                  artifact stored in Confluence at AC-2-Q2-2026 page and linked from evidence
                  path.
  M3: 2026-05-16  Export service account inventory from Terraform state; import into Okta SCIM
                  dry-run; confirm deprovisioning fires for a test terminated-user principal.

REMEDIATION APPROACH:
  Step 1: In AWS Console → CloudTrail → Trail settings, enable Management events for Write and
  Read categories including IAM. Confirm by running:
    aws cloudtrail get-event-selectors --trail-arn <arn>
  and verifying IncludeManagementEvents is true.
  Step 2: Run aws iam generate-credential-report and export the CSV. ITOps reviews each active
  account against the current employee list and flags any inactive accounts (>90 days) for
  disablement. ISSO reviews and signs the completed report.
  Step 3: Export all IAM service accounts from Terraform: terraform show -json | jq '.values.root_module.resources[] | select(.type=="aws_iam_user")'. Store the inventory JSON in the evidence path.
  Step 4: Verify the offboarding runbook in Confluence (IT-Runbook-Offboarding) specifies
  disablement within 4 hours of HR notification. Update if missing.

VALIDATION COMMAND:
  aws cloudtrail get-event-selectors \
    --trail-arn arn:aws:cloudtrail:us-east-1:<account-id>:trail/management-events \
    | jq '.EventSelectors[0].IncludeManagementEvents'
  Expected output: true

RESIDUAL RISK AFTER REMEDIATION:
  3 legacy SaaS apps (Jira, Confluence, PagerDuty) not integrated with Okta SCIM — manual
  offboarding verification required each cycle. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — CloudTrail IAM events not enabled (0 events in 90 days).
             No access review produced. No service account inventory.
             No offboarding SLA documentation.
  2026-05-12 IN PROGRESS — M1 complete: CloudTrail management events enabled.
             CreateUser/DeleteUser events confirmed in trail within 5 min.
  2026-05-14 IN PROGRESS — M2 complete: Q2 2026 access review completed.
             ISSO sign-off stored in Confluence (link: <confluence-url>/pages/AC-2-Q2-2026).
  2026-05-16 IN PROGRESS — M3 complete: 14 service accounts imported into Terraform.
             Okta SCIM dry-run confirmed deprovisioning for terminated users.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/AC-2?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-002 — AC-3

```text
POAM-ID:          POAM-2026-05-002
CONTROL:          AC-3 — Access Enforcement

WEAKNESS:
  Three deficiencies identified on Links-Matrix (Kubernetes cluster):
  (1) Kubescape not deployed — no RBAC scan results exist; current state of bindings is
      completely unverified.
  (2) No Kyverno policy artifact for RBAC enforcement — SSP asserts Kyverno blocks
      ClusterAdmin grants but no policy YAML or admission webhook record was produced.
  (3) No ClusterAdmin binding audit — PlatEng verbal statement only; actual cluster-admin
      RoleBindings are unknown.

SYSTEM AFFECTED:  Links-Matrix (Kubernetes cluster, Kyverno admission controller)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AC-3?env=bad → tool: kubescape, status: insufficient,
                  rbac_scan_run: false, wildcard_roles: null, error: "Kubescape not deployed".
                  PlatEng interview: no policy artifact or binding audit produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AC-3-2026-05-10/AC-3-finding.json

REMEDIATION OWNER: PlatEng (RBAC remediation and Kyverno deployment) / SecEng (evidence sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Deploy Kubescape via Helm to the Links-Matrix cluster; run RBAC category
                  scan; export results JSON to evidence path.
  M2: 2026-05-14  Audit all ClusterRoleBindings for cluster-admin role; remove any
                  non-approved subjects; document remaining approved principals with
                  justification in evidence path.
  M3: 2026-05-16  Apply Kyverno policy from 02-CLUSTER-HARDEN/01-policies/ blocking new
                  cluster-admin grants; confirm admission webhook rejects a test binding;
                  wire CI gate to re-run scan on each PR to production.

REMEDIATION APPROACH:
  Step 1: helm repo add kubescape https://kubescape.github.io/helm-charts/ && helm install
  kubescape kubescape/kubescape --namespace kubescape --create-namespace. Run
  kubectl port-forward -n kubescape svc/kubescape 8080:8080 and trigger an RBAC scan.
  Step 2: Run kubectl get clusterrolebindings -o json | jq '[.items[] | select(.roleRef.name=="cluster-admin")]'
  and enumerate all subjects. For each non-approved subject, remove the binding:
  kubectl delete clusterrolebinding <name>.
  Step 3: Apply the block-cluster-admin Kyverno ClusterPolicy from
  02-CLUSTER-HARDEN/01-policies/rbac/. Test by attempting to create a ClusterRoleBinding
  for cluster-admin and confirming it is blocked with a 403.
  Step 4: Add the Kubescape RBAC scan as a CI step in the deployment pipeline targeting
  the production namespace.

VALIDATION COMMAND:
  kubectl get clusterrolebindings -o json \
    | jq '[.items[] | select(.roleRef.name=="cluster-admin")] | length'
  Expected output: 2

RESIDUAL RISK AFTER REMEDIATION:
  CI gate only runs on PR — drift introduced via direct kubectl apply by cluster operators
  outside of CI is not detected until next scheduled scan. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Kubescape not deployed. No RBAC scan results. No Kyverno policy artifact.
             ClusterAdmin bindings completely unverified.
  2026-05-12 IN PROGRESS — M1 complete: Kubescape deployed and initial RBAC scan run.
             Results exported to evidence path. 3 unexpected ClusterAdmin bindings found.
  2026-05-14 IN PROGRESS — M2 complete: 3 non-approved ClusterAdmin bindings removed.
             2 approved principals documented with justification.
  2026-05-16 IN PROGRESS — M3 complete: Kyverno block-cluster-admin policy applied.
             Test binding rejected (403 confirmed). CI gate wired.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/AC-3?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-003 — AC-5

```text
POAM-ID:          POAM-2026-05-003
CONTROL:          AC-5 — Separation of Duties

WEAKNESS:
  Three deficiencies identified on Links-Matrix (Kubernetes namespaces):
  (1) No SoD matrix produced — ISSO could not provide a Confluence link; no role-to-namespace
      access mapping exists in any auditable artifact.
  (2) No RBAC namespace separation evidence — no scan confirms that developer service accounts
      are blocked from write access to the production namespace.
  (3) No annual SoD review record — verbal claim only; no reviewer sign-off, no date, no
      artifact.

SYSTEM AFFECTED:  Links-Matrix (Kubernetes namespaces: dev, staging, production)

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AC-5?env=bad → tool: kubescape, status: insufficient,
                  sod_violations: null, privileged_ns_count: null, error: "Separation of duties
                  scan not run". ISSO interview: no SoD matrix or review record produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AC-5-2026-05-10/AC-5-finding.json

REMEDIATION OWNER: CompO (SoD matrix and annual review evidence producer) / ISSO (accountability and sign-off)

SCHEDULED COMPLETION: 2026-06-09

MILESTONES:
  M1: 2026-05-20  CompO produces SoD matrix in Confluence mapping all roles (developer,
                  operator, auditor, ISSO) to namespace access (read/write/none) for dev,
                  staging, and production; ISSO reviews and signs.
  M2: 2026-06-02  Run kubectl auth can-i scan for all developer service accounts against
                  the production namespace; remediate any bindings that allow create/update/
                  delete on Deployments, Pods, or Secrets; export scan results to evidence
                  path.
  M3: 2026-06-06  Conduct formal annual SoD review; ISSO signs and stores artifact in
                  Confluence at AC-5-Annual-Review-2026; link from evidence path.

REMEDIATION APPROACH:
  Step 1: CompO to enumerate all Kubernetes service accounts in the dev, staging, and
  production namespaces. Map each account to its bound Roles and ClusterRoles. Produce
  the SoD matrix table in Confluence showing role → namespace → permission level.
  Step 2: For each developer service account (identified by label app.kubernetes.io/role=developer),
  run kubectl auth can-i create deployments --namespace=production --as=<sa-name> -n <sa-ns>.
  If any return "yes", remove the binding or replace with a read-only Role.
  Step 3: ISSO and CompO conduct the annual SoD review using the Confluence matrix as the
  source of truth. Sign the review record and attach to the evidence path.

VALIDATION COMMAND:
  kubectl auth can-i create deployments --namespace=production --as=developer-sa
  Expected output: no

RESIDUAL RISK AFTER REMEDIATION:
  SoD matrix covers Kubernetes namespaces only — AWS IAM role separation between developer
  and production accounts is not yet mapped. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — No SoD matrix. No RBAC namespace scan. No annual review record.
             Verbal claim from ISSO only.
  2026-05-20 IN PROGRESS — M1 complete: SoD matrix published in Confluence.
             ISSO sign-off obtained. 4 roles mapped across 3 namespaces.
  2026-06-02 IN PROGRESS — M2 complete: kubectl auth can-i scan run for all 8 developer
             service accounts. 2 had write access to production — bindings removed.
  2026-06-06 IN PROGRESS — M3 complete: Annual SoD review conducted and signed.
             Artifact stored in Confluence (link: <confluence-url>/pages/AC-5-Annual-Review-2026).
  2026-06-09 CLOSED — BERU re-ran GET /evidence/AC-5?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-004 — AC-6

```text
POAM-ID:          POAM-2026-05-004
CONTROL:          AC-6 — Least Privilege

WEAKNESS:
  Three deficiencies identified on Links-Matrix (AWS IAM):
  (1) Prowler not run — iam_policies_scanned: 0; wildcard action policy count and
      star-resource policy count are unknown; no IAM scan results exist.
  (2) No SCP artifact — CloudSec could not produce the Organizations SCP prohibiting wildcard
      action policies; current enforcement status is unverified.
  (3) No break-glass account inventory — admin user count is unknown; MFA enforcement on
      break-glass accounts cannot be confirmed.

SYSTEM AFFECTED:  Links-Matrix (AWS IAM, AWS Organizations SCP)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AC-6?env=bad → tool: prowler, status: insufficient,
                  iam_policies_scanned: 0, wildcard_action_policies: null, admin_users_count: null,
                  error: "Prowler IAM scan not run — no results available".
                  CloudSec interview: no SCP artifact or break-glass inventory produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AC-6-2026-05-10/AC-6-finding.json

REMEDIATION OWNER: CloudSec (IAM scan and SCP evidence producer) / ISSO (break-glass inventory sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Install Prowler and run iam_no_root_access_key_exists and
                  iam_user_mfa_enabled_console_access checks; export findings JSON to
                  evidence path; remediate any FAIL findings immediately.
  M2: 2026-05-14  Produce SCP artifact from AWS Organizations console; confirm wildcard
                  action policy prohibition is active on all member accounts; store SCP JSON
                  in evidence path.
  M3: 2026-05-16  Produce break-glass account inventory (both accounts); confirm MFA is
                  enabled on each; confirm CloudTrail alert fires on break-glass console login;
                  ISSO signs the inventory.

REMEDIATION APPROACH:
  Step 1: pip install prowler && prowler aws -c iam_no_root_access_key_exists
  iam_user_mfa_enabled_console_access -o json -f evidence-path/. Review FAIL results and
  remediate: disable root access keys, enforce MFA on all console-access IAM users.
  Step 2: In AWS Organizations console, export the SCP attached to the root OU or the
  Links-Matrix member account. Verify it includes a Deny on Action: ["*"] and
  Resource: ["*"] statements. Save the SCP JSON to the evidence path.
  Step 3: List IAM users with AdministratorAccess: aws iam list-users and cross-reference
  against the break-glass account list. Confirm MFA: aws iam list-mfa-devices --user-name <name>.
  Confirm CloudTrail alert: check CloudWatch alarm linked to ConsoleLogin events from the
  break-glass account ARN.

VALIDATION COMMAND:
  prowler aws -c iam_no_root_access_key_exists iam_user_mfa_enabled_console_access \
    -o json | jq '[.[] | select(.status=="FAIL")] | length'
  Expected output: 0

RESIDUAL RISK AFTER REMEDIATION:
  Permission boundaries are not yet enforced on developer-created IAM roles — a developer
  with iam:CreateRole could still create an overprivileged role outside SCP scope. Residual
  risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Prowler not run. iam_policies_scanned: 0. No SCP artifact.
             No break-glass account inventory. CloudSec verbal only.
  2026-05-12 IN PROGRESS — M1 complete: Prowler installed and run. 3 FAIL findings
             (root key exists on 1 account, MFA missing on 2 users). Remediated same day.
  2026-05-14 IN PROGRESS — M2 complete: SCP artifact exported from Organizations.
             Wildcard action policy Deny confirmed active on all 4 member accounts.
  2026-05-16 IN PROGRESS — M3 complete: Break-glass inventory produced (2 accounts).
             MFA confirmed on both. CloudTrail alert tested and confirmed firing.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/AC-6?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-005 — AC-17

```text
POAM-ID:          POAM-2026-05-005
CONTROL:          AC-17 — Remote Access

WEAKNESS:
  Three deficiencies identified on Links-Matrix (VPN / AWS CloudTrail):
  (1) No VPN session logs — CloudTrail scope does not include remote access session events;
      vpn_session_logs: false; ConsoleLogin events not captured in trail.
  (2) No remote access policy document produced — SecEng could not retrieve policy v3.1
      from Confluence; MFA type and session timeout controls are unspecified.
  (3) MFA enforcement unconfirmed — SecEng verbal statement only; no identity provider
      configuration artifact or test result produced.

SYSTEM AFFECTED:  Links-Matrix (VPN, AWS CloudTrail, Okta IdP)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AC-17?env=bad → tool: cloudtrail, status: insufficient,
                  vpn_session_logs: false, remote_access_policy_artifact: null,
                  error: "No remote access session events found in trail scope".
                  SecEng interview: no VPN logs, no policy document, no MFA confirmation.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AC-17-2026-05-10/AC-17-finding.json

REMEDIATION OWNER: SecEng (VPN log evidence and MFA confirmation producer) / PlatEng (accountability and CloudTrail scope owner)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Extend CloudTrail trail to include ConsoleLogin and VPN session events
                  in us-east-1; run test login and confirm event appears in trail within
                  5 minutes; export 30-day event log to evidence path.
  M2: 2026-05-14  Retrieve remote access policy document (v3.1) from Confluence; verify it
                  specifies permitted MFA types (TOTP or hardware key), session timeout
                  (max 8h), and offboarding procedure; store signed copy in evidence path.
  M3: 2026-05-16  Run MFA enforcement test via Okta: attempt VPN login without MFA and
                  confirm access is denied; export Okta MFA policy configuration as JSON
                  to evidence path; ISSO signs the artifact.

REMEDIATION APPROACH:
  Step 1: In AWS CloudTrail console, edit the trail event selectors to add Management Events
  with Read and Write, and ensure ConsoleLogin is captured. Run a test console login and
  confirm with: aws cloudtrail lookup-events --lookup-attributes
  AttributeKey=EventName,AttributeValue=ConsoleLogin --max-results 5. Export the 30-day
  ConsoleLogin event log to the evidence path.
  Step 2: Locate the remote access policy in Confluence (search: "remote access policy v3.1").
  If not found, create a new version using the template in GP-CONSULTING/templates/ and have
  ISSO and PlatEng sign it. Confirm the policy specifies: permitted MFA types, max session
  duration, and the offboarding SLA for revoking VPN access.
  Step 3: In the Okta admin console, navigate to Security → Authentication Policies → VPN
  Access Policy. Confirm MFA is required for all users. Export the policy configuration JSON.
  Conduct a test: attempt VPN authentication without MFA enrolled and confirm denial.

VALIDATION COMMAND:
  aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin \
    --max-results 5 | jq '.Events | length'
  Expected output: 5

RESIDUAL RISK AFTER REMEDIATION:
  VPN session duration enforcement is configured in Okta but not enforced at the network
  layer — a session token could persist beyond the 8-hour policy limit if Okta is bypassed.
  Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — VPN session logs absent from CloudTrail scope. No remote access policy
             artifact. MFA enforcement unconfirmed. SecEng verbal only.
  2026-05-12 IN PROGRESS — M1 complete: CloudTrail extended to ConsoleLogin events.
             Test login confirmed in trail within 3 minutes. 30-day log exported.
  2026-05-14 IN PROGRESS — M2 complete: Remote access policy v3.1 retrieved from Confluence.
             MFA type (TOTP), session timeout (8h), and offboarding SLA (2h) confirmed.
             Signed copy stored in evidence path.
  2026-05-16 IN PROGRESS — M3 complete: Okta MFA policy exported. Test login without MFA
             denied (confirmed). ISSO signed the artifact.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/AC-17?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```
