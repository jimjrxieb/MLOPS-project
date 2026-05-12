---
family: PL
family_name: Planning
id: PL-2
name: System Security and Privacy Plans
---

question: "Is there a current, approved security plan that accurately describes the system and its controls?"

description: >
  The organization develops a security and privacy plan for the system that is consistent
  with the enterprise architecture; explicitly defines the authorization boundary; describes
  the operational context and information types; characterizes the security and privacy
  requirements; identifies the controls in place or planned; and is reviewed and approved
  by the authorizing official. The System Security Plan (SSP) is the authoritative document
  that ties everything together — it describes what the system is, what it processes, what
  controls protect it, and who is responsible. An SSP that does not match the system as it
  actually operates is worse than no SSP: it gives auditors a false picture and assessors
  a misleading baseline.

enhancements:
  - id: PL-2(3)
    name: Plan and Coordinate with Other Organizations
    description: >
      The organization plans and coordinates security and privacy activities affecting
      the system with other organizations before conducting such activities to reduce the
      impact on other entities. For shared infrastructure or multi-tenant systems, security
      activities (penetration tests, configuration changes, incident response) must be
      coordinated so that actions affecting shared components are understood across tenants.

HITRUST_map:
  - "06.a — Information Security Policy Document"
  - "06.b — Review of the Information Security Policy"
  - "03.a — Risk Management Program"

evidence:
  what_to_look_for:
    - Current SSP document with approval signature from the Authorizing Official (AO)
    - SSP accurately describing the system boundary, components, data flows, and information types
    - Control implementation statements in the SSP that match what is actually deployed
    - SSP review and update records showing the plan is kept current with system changes
    - Evidence that the SSP was the basis for the most recent authorization decision
    - Interconnection agreements (ISAs, MOUs) for system connections referenced in the SSP
  ask_for:
    - "Show me your SSP — when was it last approved, by whom, and when was it last updated?"
    - "Show me a section of the SSP describing a specific control — does the implementation statement match what is actually deployed?"
    - "Show me how a significant system change (new component, new data type, new interconnection) triggers an SSP update."
    - "Show me your system boundary diagram in the SSP — does it accurately reflect the current architecture?"
  tools:
    generic:
      - NIST SP 800-18 (SSP development guidance)
      - FedRAMP SSP template (for FedRAMP authorizations — standardized SSP structure)
      - Docusaurus / Confluence (SSP hosted as living document with version history)
      - draw.io / Lucidchart (system boundary and data flow diagrams embedded in SSP)
    aws:
      - AWS Artifact (compliance reports and agreements referenced in SSP)
      - AWS Audit Manager (automated evidence collection that feeds SSP control implementation statements)
      - AWS Config (current resource inventory that should match SSP system description)
    microsoft:
      - Microsoft Purview Compliance Manager (assessment templates that generate SSP-equivalent documentation)
      - Azure Resource Graph (inventory that should match SSP system component list)
      - Azure Blueprints (policy-as-code that implements what the SSP documents)

failure_to_implement:
  - SSP describes the system as it was two years ago — current architecture differs materially from what is documented.
  - Control implementation statements are copy-pasted boilerplate — do not describe how the control is actually implemented in this environment.
  - No AO signature — the SSP exists but was never formally approved, making the authorization basis invalid.
  - System boundary in the SSP excludes components that are clearly within the authorization boundary — assessors find undocumented components.
  - SSP is a static document in a shared drive — no version history, no review cadence, no process for updates on system change.

related:
  - CA-2
  - CA-7
  - RA-3

chain: null
