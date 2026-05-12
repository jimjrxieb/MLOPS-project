---
family: AU
family_name: Audit and Accountability
id: AU-2
name: Event Logging
---

question: "Have we defined which events must be logged across every system component?"

description: >
  The organization determines which system events are auditable, coordinates with other
  entities requiring audit information, and provides a rationale for why the selected
  event list is sufficient to support after-the-fact investigations of security incidents.
  AU-2 is the planning control — it defines WHAT to log before the system logs anything.
  Without a documented, approved event list, audit logs are arbitrary and fail evidence
  requirements. Every other AU control depends on this foundation.

enhancements:
  - id: AU-2(3)
    name: Reviews and Updates
    description: >
      The organization reviews and updates the list of auditable events annually and
      whenever there is a change to the system, threat environment, or organizational
      risk posture. An event list that was appropriate two years ago may miss attack
      patterns that are now common.

HITRUST_map:
  - "09.aa — Audit Logging"
  - "09.ab — Monitoring System Use"
  - "06.d — Information Security Incident Management"

evidence:
  what_to_look_for:
    - Documented audit event policy listing required event categories (auth, privilege use, data access, config change, failures)
    - Kubernetes audit policy YAML showing event rules, levels (None/Metadata/Request/RequestResponse), and stage coverage
    - Cloud provider logging configuration showing which event categories are enabled (management events, data events, network)
    - Annual or change-triggered review records showing the event list was validated and updated
    - Evidence the event list was coordinated across system components (app, OS, network, cloud)
  ask_for:
    - "Show me your audit event policy document — what specific event categories are required to be logged?"
    - "Show me your Kubernetes audit-policy.yaml in git — what verb/resource combinations are captured and at what level?"
    - "Show me when this event list was last reviewed and what triggered the review."
    - "Are there any system components that are explicitly excluded from audit logging — and what's the documented rationale?"
  tools:
    generic:
      - kubectl audit-policy.yaml (K8s audit policy — verify event coverage and log levels)
      - auditd rules file (`/etc/audit/rules.d/` — OS-level event capture)
      - Falco rules (supplemental event detection layer)
    aws:
      - CloudTrail (verify management events, data events for S3/Lambda, Insights enabled)
      - AWS Config (track configuration change events)
      - VPC Flow Logs (network-level event capture)
      - CloudWatch Logs (application event aggregation)
    microsoft:
      - Azure Monitor Diagnostic Settings (verify all resource types are forwarding logs)
      - Microsoft Defender for Cloud (coverage gaps in audit event collection)
      - Azure Activity Log (management plane event coverage)
      - Entra ID Audit Logs (identity event capture)

failure_to_implement:
  - No documented event list means audit logs are whatever the system happened to capture — not a defensible compliance posture.
  - Event list never reviewed after a major architecture change — critical new components emit no auditable events.
  - K8s audit policy set to None for sensitive verbs (create/delete on secrets) — credential access goes unlogged.
  - Coordination between app, OS, and cloud logging teams never happened — gaps exist at each handoff layer.
  - Auditor requests evidence of auditable event coverage — organization cannot produce a list, fails FedRAMP AU-2 requirement.

related:
  - AU-3
  - AU-12
  - SI-4

chain: "AU-2 → AU-3 → AU-12 → AU-6 → AU-7"
