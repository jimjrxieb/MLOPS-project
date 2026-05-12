---
family: AC
family_name: Access Control
id: AC-3
name: Access Enforcement
---

question: "Is access actually restricted to what's authorized — at the system level?"

description: >
  The information system enforces approved authorizations for logical access to information
  and system resources in accordance with applicable access control policies. This is the
  enforcement layer — where policy becomes a technical control that cannot be bypassed
  by users. It covers both human and non-human (service, application) access subjects.

enhancements:
  - id: AC-3(4)
    name: Discretionary Access Control
    description: >
      The information system implements a discretionary access control policy that allows
      users to specify and control sharing of information and system resources, and includes
      or excludes access to specific resources based on user identity or group membership.
  - id: AC-3(7)
    name: Role-Based Access Control
    description: >
      The information system enforces a role-based access control policy over defined subjects
      and objects and controls access based on organization-defined roles and users authorized
      to assume such roles. RBAC is the dominant implementation pattern in Kubernetes and
      cloud-native environments.

HITRUST_map:
  - "01.a — Access Control Policy"
  - "01.d — User Access Management"
  - "01.e — Review of User Access Rights"

evidence:
  what_to_look_for:
    - RBAC role definitions and bindings (ClusterRole, Role, ClusterRoleBinding in K8s)
    - IAM policies and permission boundaries scoped to least privilege
    - Access control matrix mapping roles to allowed actions on resources
    - Policy enforcement point configuration (OPA, Kyverno, SCPs)
    - Evidence that unapproved access attempts are denied and logged
  ask_for:
    - "Show me the RBAC ClusterRoleBindings for production — who has cluster-admin and why?"
    - "Show me how your authorization policy is defined and where enforcement happens — is it at the API gateway, service mesh, or K8s API server?"
    - "Show me a denied access attempt in your audit logs to verify enforcement is working."
    - "Show me the IAM policy attached to your application's service account/role — is it scoped to specific resources?"
  tools:
    generic:
      - kubectl (`kubectl get clusterrolebindings,rolebindings -A`)
      - rbac-lookup (Kubernetes RBAC visualizer)
      - OPA / Gatekeeper policy bundles
      - Kyverno ClusterPolicies
    aws:
      - IAM policy simulator
      - AWS Config (managed rules for IAM policy compliance)
      - CloudTrail (AccessDenied events)
      - Service Control Policies (SCPs) via AWS Organizations
    microsoft:
      - Azure RBAC role assignments
      - Entra ID Conditional Access policies
      - Azure Policy (deny effects)
      - Microsoft Defender for Cloud (policy compliance)

failure_to_implement:
  - Access control exists only in the UI layer — direct API calls bypass all enforcement.
  - Over-permissive wildcard roles allow lateral movement across namespaces or accounts.
  - Policy drift: roles are defined but bindings are modified ad hoc without review.
  - Service accounts carry cluster-admin or equivalent due to copy-paste manifests.
  - Privilege escalation paths exist where a lower-privilege user can assume a higher-privilege role.

related:
  - AC-2
  - AC-5
  - AC-6
  - IA-2

chain: null
