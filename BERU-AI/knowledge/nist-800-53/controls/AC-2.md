---
family: AC
family_name: Access Control
id: AC-2
name: Account Management
---

question: "Does this account exist legitimately, and is it managed through its lifecycle?"

description: >
  The organization manages information system accounts including user, group, system, application,
  guest/anonymous, and temporary accounts. Management covers account creation, enablement,
  modification, disabling, removal, periodic review, and enforcement of access authorization.
  Accounts must be authorized by a designated approver, assigned to an accountable owner,
  and removed or disabled when no longer needed.

enhancements:
  - id: AC-2(1)
    name: Automated System Account Management
    description: >
      The organization employs automated mechanisms to support management of information system
      accounts. Automation eliminates manual error and enforces consistency across account
      creation, modification, disabling, and removal.
  - id: AC-2(2)
    name: Automated Temporary and Emergency Account Management
    description: >
      The information system automatically removes or disables temporary and emergency accounts
      after an organization-defined time period. Prevents accounts created for incidents or
      short-term needs from persisting indefinitely.
  - id: AC-2(3)
    name: Disable Inactive Accounts
    description: >
      The information system automatically disables accounts after an organization-defined
      inactivity period (typically 30–90 days). Eliminates stale credential attack surface.
  - id: AC-2(4)
    name: Automated Audit Actions
    description: >
      The information system automatically audits account creation, modification, enabling,
      disabling, and removal. Produces an immutable record of the full account lifecycle.

HITRUST_map:
  - "01.a — Access Control Policy"
  - "01.b — User Registration and De-registration"
  - "01.c — Privilege Management"

evidence:
  what_to_look_for:
    - Current user account roster with creation dates and assigned owners
    - Quarterly or semi-annual access review records (signed off by approvers)
    - Offboarding records showing timely account disable/removal after termination
    - Temporary/emergency account log with expiry timestamps
    - Service account inventory with owning team and justification
  ask_for:
    - "Show me the last completed access review — who approved it and when was it run?"
    - "Show me how terminated users are removed from the system. Is it automated or manual?"
    - "Show me the process for creating a service account — what approval and documentation is required?"
    - "Show me accounts inactive for more than 90 days that are still enabled."
  tools:
    generic:
      - kubectl (service accounts — `kubectl get sa -A`)
      - ldapsearch / Active Directory query
      - git log (to verify account change history in IaC)
    aws:
      - IAM Access Analyzer
      - AWS Organizations (SCPs enforcing account lifecycle)
      - CloudTrail (CreateUser, DeleteUser, AttachUserPolicy events)
      - IAM Credential Report (`aws iam generate-credential-report`)
    microsoft:
      - Entra ID (Azure AD) — User Management and Audit Logs
      - Azure AD PIM — Privileged Identity Management reviews
      - Microsoft Defender for Cloud Apps — account activity anomalies

failure_to_implement:
  - Terminated employee credentials remain active, enabling unauthorized access post-separation.
  - Service accounts accumulate without owners, creating unaudited long-lived credentials.
  - No access review means privilege creep goes undetected across role changes and promotions.
  - Emergency accounts created for incidents persist indefinitely with elevated permissions.
  - Inability to produce account lifecycle evidence fails FedRAMP and SOC 2 audit requirements.

related:
  - AC-3
  - AC-6
  - IA-4
  - IA-5

chain: null
