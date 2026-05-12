---
family: AC
family_name: Access Control
id: AC-6
name: Least Privilege
---

question: "Does each account have only the permissions it needs — nothing more?"

description: >
  The organization employs the principle of least privilege, allowing only authorized accesses
  for users and processes acting on behalf of users which are necessary to accomplish assigned
  tasks. Least privilege is not a one-time configuration — it is an ongoing constraint that
  must be enforced at account creation, reviewed periodically, and tightened after incidents.
  In cloud-native environments, this applies equally to human accounts, service accounts,
  and IAM roles assumed by workloads.

enhancements:
  - id: AC-6(1)
    name: Authorize Access to Security Functions
    description: >
      The organization explicitly authorizes access to security functions and security-relevant
      information. Prevents general users from accessing configuration that controls the
      security posture of the system.
  - id: AC-6(2)
    name: Non-Privileged Access for Nonsecurity Functions
    description: >
      The organization requires users of information system accounts with access to security
      functions to use non-privileged accounts for nonsecurity functions. Enforces privilege
      separation for day-to-day work vs. administrative actions.
  - id: AC-6(5)
    name: Privileged Accounts
    description: >
      The organization restricts privileged accounts to organization-defined roles or personnel.
      Privileged access (admin, root, cluster-admin) is named, documented, and limited to those
      who operationally require it.
  - id: AC-6(9)
    name: Log Use of Privileged Functions
    description: >
      The information system audits the execution of privileged functions. Ensures that when
      elevated permissions are exercised, there is an immutable record of who did what and when.
  - id: AC-6(10)
    name: Prohibit Non-Privileged Users from Executing Privileged Functions
    description: >
      The information system prevents non-privileged users from executing privileged functions
      and captures execution in audit logs. Provides a hard technical enforcement boundary
      (not just policy) against unauthorized privilege escalation.

HITRUST_map:
  - "01.a — Access Control Policy"
  - "01.c — Privilege Management"
  - "01.e — Review of User Access Rights"
  - "01.f — Password Policy"

evidence:
  what_to_look_for:
    - IAM roles and policies scoped to specific resources — not wildcard (*) on actions or resources
    - K8s service account RBAC limited to the verbs and resources the workload actually uses
    - Permission boundary policies applied to IAM roles to cap maximum privilege
    - Privileged account inventory (named individuals, not shared accounts)
    - Evidence that wildcard or admin permissions are break-glass only, with alerting on use
  ask_for:
    - "Show me any IAM roles with '*' actions or resources not scoped to break-glass — how are they justified?"
    - "Show me the RBAC roles bound to service accounts in production — what verbs and resources are allowed?"
    - "Show me how you detect and alert when a privileged account is used in production."
    - "Show me the last access review that identified and remediated over-permissive roles."
  tools:
    generic:
      - kubectl (`kubectl get clusterroles,roles -A -o yaml` — scan for wildcards)
      - rbac-lookup (map principals to effective permissions)
      - kube-score (flag over-privileged service accounts)
    aws:
      - IAM Access Analyzer (external and unused access findings)
      - AWS Config (rule: iam-no-inline-policy, iam-policy-no-statements-with-admin-access)
      - CloudTrail (privileged function execution events)
      - IAM Credential Report (last used, key age)
    microsoft:
      - Entra ID PIM (time-bound privilege activation, approval workflows)
      - Azure Policy (deny assignments for over-privileged operations)
      - Microsoft Defender for Cloud (IAM recommendations)
      - Azure AD Access Reviews

failure_to_implement:
  - Compromised service account credential grants an attacker blast radius equivalent to cluster-admin.
  - Wildcard IAM policies allow data exfiltration across all S3 buckets from a single role compromise.
  - Developers have read access to production secrets because permissions were never scoped after initial setup.
  - No alerting on privileged function use means admin actions are invisible until post-incident forensics.
  - FedRAMP audit finds no documented justification for elevated permissions — fails AC-6(5) evidence requirement.

related:
  - AC-2
  - AC-3
  - AC-5
  - IA-5

chain: null
