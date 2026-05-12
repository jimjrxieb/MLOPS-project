# POA&M — Access Control (AC) Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** POA&M items reflect specific evidence gaps from the BERU assessment.
> Control owners are identified by role. Due dates follow severity-based priority tiers.
> Milestones cover M1 and M2 with actionable steps. Validation commands are real tool queries.
> Residual risk is acknowledged but remains generic. Status history includes opening reason.

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
  No access review records produced. CloudTrail IAM events not enabled. No service account
  inventory. No offboarding SLA documentation. ITOps verbal statement was the only evidence
  available — no artifacts to verify SSP claims.

SYSTEM AFFECTED:  AWS IAM / Okta SCIM / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AC-2?env=bad (cloudtrail — status: insufficient) + ITOps interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AC-2-2026-05-10/

REMEDIATION OWNER: ITOps (evidence producer) / ISSO (sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Enable CloudTrail management events for IAM category; confirm CreateUser and
                  DeleteUser events appear in trail within 5 minutes of test action.
  M2: 2026-05-15  Complete Q2 2026 access review; obtain ISSO sign-off; store artifact in
                  Confluence and link from evidence path above.

REMEDIATION APPROACH:
  Enable CloudTrail management events for the IAM service category in us-east-1. Verify events
  are captured by running a test CreateUser action and checking the trail. Export the IAM
  credential report and produce a quarterly access review showing active accounts, last login,
  and reviewer sign-off. Document the offboarding SLA (target: disable within 4 hours of
  termination) and produce the service account inventory from Terraform state.

VALIDATION COMMAND:
  aws cloudtrail get-event-selectors --trail-arn <arn> | jq '.EventSelectors[0].IncludeManagementEvents'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment
```

---

## POAM-2026-05-002 — AC-3

```text
POAM-ID:          POAM-2026-05-002
CONTROL:          AC-3 — Access Enforcement

WEAKNESS:
  No RBAC scan results, no Kyverno policy artifact, no ClusterAdmin binding audit. Kubescape
  is not deployed on the cluster. PlatEng could not confirm the current state of ClusterAdmin
  bindings or provide any policy-as-code artifact for RBAC enforcement.

SYSTEM AFFECTED:  Kubernetes / Links-Matrix cluster

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AC-3?env=bad (kubescape — status: insufficient) + PlatEng interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AC-3-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Deploy Kubescape to the cluster and run initial RBAC scan; export results
                  to evidence path.
  M2: 2026-05-15  Audit ClusterAdmin bindings and remove any non-approved principals; apply
                  Kyverno policy blocking new ClusterAdmin grants.

REMEDIATION APPROACH:
  Deploy Kubescape via Helm to the Links-Matrix cluster. Run the RBAC category scan and export
  results as JSON to the evidence path. Manually audit all ClusterRoleBindings for cluster-admin
  role and remove bindings for non-approved subjects. Apply the Kyverno policy from
  02-CLUSTER-HARDEN/01-policies/ that blocks ClusterAdmin grants. Confirm CI gate is wired to
  re-run the scan on each pull request to production namespaces.

VALIDATION COMMAND:
  kubectl get clusterrolebindings -o json | jq '[.items[] | select(.roleRef.name=="cluster-admin")] | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment
```

---

## POAM-2026-05-003 — AC-5

```text
POAM-ID:          POAM-2026-05-003
CONTROL:          AC-5 — Separation of Duties

WEAKNESS:
  No SoD matrix, no RBAC namespace separation evidence, no annual review record. ISSO could
  not produce a Confluence link for the SoD matrix. No tool scan confirmed that developer
  service accounts are blocked from writing to production namespaces.

SYSTEM AFFECTED:  Kubernetes namespaces / Links-Matrix

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AC-5?env=bad (kubescape — status: insufficient) + ISSO interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AC-5-2026-05-10/

REMEDIATION OWNER: ISSO (accountability) / CompO (evidence producer)

SCHEDULED COMPLETION: 2026-06-09

MILESTONES:
  M1: 2026-05-20  Produce SoD matrix documenting which roles have write access to which
                  namespaces; store in Confluence and link from evidence path.
  M2: 2026-06-02  Run kubectl auth can-i scan for developer service accounts against production
                  namespace; remediate any bindings that allow write access.

REMEDIATION APPROACH:
  CompO to produce the SoD matrix in Confluence showing each role (developer, operator,
  auditor) mapped to namespace access (read/write/none) for dev, staging, and production.
  Run kubectl auth can-i for all developer service accounts against the production namespace
  and export results. Remediate any bindings that grant write access. Conduct the annual SoD
  review, obtain ISSO sign-off, and store the signed artifact in Confluence.

VALIDATION COMMAND:
  kubectl auth can-i create deployments --namespace=production --as=developer-sa

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment
```

---

## POAM-2026-05-004 — AC-6

```text
POAM-ID:          POAM-2026-05-004
CONTROL:          AC-6 — Least Privilege

WEAKNESS:
  No Prowler scan results, no SCP enforcement artifact, no break-glass account inventory.
  CloudSec confirmed Prowler is on the roadmap but has not been run. Wildcard IAM policy
  count and admin user count are unknown. No evidence that MFA is enforced on break-glass
  accounts.

SYSTEM AFFECTED:  AWS IAM / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AC-6?env=bad (prowler — status: insufficient) + CloudSec interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AC-6-2026-05-10/

REMEDIATION OWNER: CloudSec (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Install Prowler and run IAM checks iam_no_root_access_key_exists and
                  iam_user_mfa_enabled_console_access; export results to evidence path.
  M2: 2026-05-15  Produce break-glass account inventory; confirm MFA is enabled on each;
                  produce SCP artifact blocking wildcard action policies.

REMEDIATION APPROACH:
  Install Prowler (pip install prowler) and run the IAM check suite against the AWS account.
  Export findings as JSON to the evidence path. Produce an inventory of all IAM users with
  AdministratorAccess or wildcard action policies and remediate each. Confirm MFA is enabled
  on both break-glass accounts. Produce the SCP document from AWS Organizations that prohibits
  wildcard action policies on member accounts.

VALIDATION COMMAND:
  prowler aws -c iam_no_root_access_key_exists iam_user_mfa_enabled_console_access

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment
```

---

## POAM-2026-05-005 — AC-17

```text
POAM-ID:          POAM-2026-05-005
CONTROL:          AC-17 — Remote Access

WEAKNESS:
  No VPN session logs, no remote access policy document, no MFA enforcement confirmation.
  CloudTrail scope does not include remote access session events. SecEng could not confirm
  MFA type or session controls. No offboarding procedure for remote access termination was
  produced.

SYSTEM AFFECTED:  VPN / AWS CloudTrail / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/AC-17?env=bad (cloudtrail — status: insufficient) + SecEng interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/AC-17-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability) / SecEng (evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Extend CloudTrail scope to capture ConsoleLogin and VPN session events;
                  confirm events appear in trail within 5 minutes of test login.
  M2: 2026-05-15  Produce remote access policy document (v3.1) from Confluence; confirm MFA
                  type and session timeout settings; store artifact in evidence path.

REMEDIATION APPROACH:
  Extend the CloudTrail trail to include ConsoleLogin and VPN session events. Run a test
  login and confirm the event appears in the trail. Export the last 30 days of ConsoleLogin
  events as the session log evidence. Retrieve the remote access policy document (v3.1) from
  Confluence and verify it specifies allowed MFA types, session timeout controls, and
  offboarding procedure. Store a signed copy in the evidence path. Confirm MFA is enforced
  via Okta or the identity provider for all remote access methods.

VALIDATION COMMAND:
  aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin --max-results 5 | jq '.Events | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment
```
