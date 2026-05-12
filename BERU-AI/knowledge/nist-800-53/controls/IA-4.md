---
family: IA
family_name: Identification and Authentication
id: IA-4
name: Identifier Management
---

question: "Is every identity unique, attributed to a real owner, and revoked when no longer needed?"

description: >
  The organization manages information system identifiers for users and devices — covering
  authorization from an appropriate authority, selection of identifiers that distinguish
  one user from all others, assignment of identifiers to intended parties, prevention of
  identifier reuse for a defined period, and disabling of identifiers after a defined
  inactivity period. The core principle: every action in the system must be traceable to
  a specific, accountable identity. Shared accounts and recycled identifiers break this chain.

enhancements:
  - id: IA-4(4)
    name: Identify User Status
    description: >
      The organization manages individual identifiers by uniquely identifying each individual
      as a contractor, foreign national, or other status category. Identifiers reflect the
      type of user — allowing access policy and audit to distinguish workforce categories
      without manual cross-referencing of HR systems.

HITRUST_map:
  - "01.a — Access Control Policy"
  - "01.b — User Registration and De-registration"
  - "01.d — User Access Management"

evidence:
  what_to_look_for:
    - Policy prohibiting shared accounts and defining identifier uniqueness requirements
    - User provisioning records linking each identifier to a named individual and approver
    - Identifier reuse prevention policy (e.g., former employee username not reused for 2 years)
    - Inactive identifier disable records (accounts disabled after 30–90 days without login)
    - Service account and system identifier inventory with owning team per identifier
  ask_for:
    - "Show me your user provisioning workflow — how is each new identifier linked to a specific named individual and approved?"
    - "Show me your policy on shared accounts — are there any systems where multiple people share a single login?"
    - "Show me identifiers disabled in the last 90 days due to inactivity — how is inactivity tracked and enforced?"
    - "Show me how service account identifiers are named and inventoried — can you trace each one to an owning team?"
  tools:
    generic:
      - LDAP / Active Directory query (enumerate all user objects, check for shared/generic accounts)
      - kubectl (`kubectl get sa -A` — inventory service account identifiers across namespaces)
      - git log (verify commit authors are individual named identities, not shared accounts)
    aws:
      - IAM Credential Report (last used, creation date, key age — detect stale/shared identifiers)
      - AWS Config (iam-no-inline-policy, detect generic/shared role patterns)
      - CloudTrail (correlate actions to specific IAM identity ARNs)
      - AWS SSO / Identity Center (centralized identifier lifecycle management)
    microsoft:
      - Entra ID User Management (review for generic/shared accounts, guest identities)
      - Entra ID Audit Logs (user creation, modification, deletion events)
      - Microsoft 365 Admin Center (identifier provisioning and deprovisioning records)
      - Azure AD Access Reviews (periodic identifier review workflows)

failure_to_implement:
  - Shared accounts make attribution impossible — an audit finding cannot be traced to a specific person.
  - Recycled usernames assign historical audit records from a former employee to a new hire.
  - Inactive identifiers left enabled become persistent footholds for compromised credentials.
  - Generic service account names (e.g., "app-service", "test-user") have no accountable owner and are never reviewed.
  - Inability to enumerate all active identifiers means you cannot answer "who has access?" — a FedRAMP audit blocker.

related:
  - AC-2
  - IA-2
  - IA-5

chain: null
