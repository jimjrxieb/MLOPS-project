---
family: IR
family_name: Incident Response
id: IR-8
name: Incident Response Plan
---

question: "Is there a current, approved incident response plan — and does the team know how to execute it?"

description: >
  The organization develops an incident response plan that provides the organization with
  a roadmap for implementing its incident response capability; describes the structure and
  organization of the incident response capability; provides a high-level approach for how
  the capability fits into the overall organization; meets the unique requirements of the
  organization; defines reportable incidents; provides metrics for measuring the incident
  response capability; defines the resources and management support needed; is reviewed and
  approved by designated officials; and is distributed to defined personnel. IR-8 is the
  document; IR-4 is the execution. Both must exist and align. A plan no one has read and
  a plan that does not match how the team actually responds are equivalent failures.

enhancements:
  - id: IR-8(1)
    name: Breaches
    description: >
      The organization incorporates the handling of breaches — specifically including
      notification procedures for affected individuals, regulatory bodies, and oversight
      organizations — into the incident response plan. Breach notification timelines
      (72 hours under GDPR, defined windows under HIPAA, state breach notification laws)
      must be embedded in the plan, not improvised during an active incident.

HITRUST_map:
  - "06.d — Information Security Incident Management"
  - "06.e — Responsibilities and Procedures"
  - "06.f — Learning from Information Security Incidents"

evidence:
  what_to_look_for:
    - Current IR plan document with approval signature and version date
    - IR plan distributed to all personnel with incident response roles — distribution records
    - Annual IR plan review records showing the plan is kept current
    - IR tabletop exercise or drill records from the last 12 months
    - Breach notification procedure embedded in the IR plan with specific timelines and notification authorities
    - Metrics defined in the plan (MTTD, MTTR, incidents by severity) and evidence they are being measured
  ask_for:
    - "Show me your IR plan — when was it last approved, by whom, and when was it last tested?"
    - "Show me your distribution records — who has received the current IR plan and confirmed they have read it?"
    - "Show me your most recent tabletop exercise — what scenario was tested and what gaps were identified?"
    - "Show me your breach notification procedure — within what timeframe must you notify regulators and affected parties, and who initiates that process?"
  tools:
    generic:
      - NIST SP 800-61 (Computer Security Incident Handling Guide — IR plan development reference)
      - Confluence / SharePoint (IR plan hosted as a live document with version history and distribution tracking)
      - Tabletop exercise platforms (Cybersecurity tabletop simulation tools for plan testing)
      - PagerDuty (on-call schedule and escalation path — should align with IR plan roles)
    aws:
      - AWS Incident Manager (IR plan execution — runbooks, contacts, escalation plans embedded in AWS)
      - AWS Systems Manager (runbook-as-code for automated IR steps referenced in the plan)
      - AWS Artifact (compliance documents that may inform IR regulatory notification requirements)
    microsoft:
      - Microsoft Sentinel Playbooks (automated IR plan execution steps)
      - Microsoft 365 Defender (IR plan integration with automated response capabilities)
      - Azure Business Continuity Center (IR plan coordination with CP plans)

failure_to_implement:
  - IR plan exists as a draft from two years ago — never approved, never distributed, never tested.
  - Plan does not include breach notification procedures — during an actual breach, the team improvises notification timelines and misses regulatory windows.
  - IR roles in the plan reference individuals who have since left the organization — on-call contacts are incorrect.
  - No tabletop exercise in the last 12 months — team has never rehearsed the plan and does not know their roles.
  - Plan metrics are defined but not measured — MTTD and MTTR are listed as goals with no actual tracking data.

related:
  - IR-4
  - CP-9
  - CP-10

chain: null
