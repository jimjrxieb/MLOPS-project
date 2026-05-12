---
family: IR
family_name: Incident Response
id: IR-4
name: Incident Handling
---

question: "When an incident occurs, is there a defined process to contain it, eradicate it, and recover from it — with evidence at every step?"

description: >
  The organization implements an incident handling capability that includes preparation,
  detection, analysis, containment, eradication, and recovery; coordinates incident
  handling activities with contingency planning; and incorporates lessons learned from
  ongoing incident handling into incident response procedures, training, and testing.
  Incident handling is the operational process — IR-8 is the plan on paper. Both are
  required, and they must align. The most common failure is a well-written IR plan that
  the response team has never rehearsed and cannot execute under pressure. Evidence of
  incident handling means timestamps, decisions, actions, and outcomes recorded throughout
  the incident lifecycle.

enhancements:
  - id: IR-4(1)
    name: Automated Incident Handling Processes
    description: >
      The organization employs automated mechanisms to support the incident handling process.
      Automation in incident response means runbooks that execute, not just runbooks that
      are read. Automated containment (isolate a compromised pod, revoke a credential,
      block an IP) reduces mean time to contain and removes human error from time-critical steps.
  - id: IR-4(4)
    name: Information Correlation
    description: >
      The organization correlates incident information and individual incident responses
      to achieve an organization-wide awareness of incident activity. A single compromised
      service may be the visible tip of a broader campaign — correlation across incidents
      surfaces patterns that individual incident handling would miss.

HITRUST_map:
  - "06.d — Information Security Incident Management"
  - "06.e — Responsibilities and Procedures"
  - "09.ab — Monitoring System Use"

evidence:
  what_to_look_for:
    - Incident response plan with defined phases (preparation, detection, analysis, containment, eradication, recovery, post-incident)
    - Incident log or ticket history showing the handling process was followed for past incidents
    - Containment runbooks for the system's most likely incident types (container compromise, credential breach, data exfiltration)
    - Automated containment capabilities (pod isolation policy, credential revocation script, network policy application)
    - Post-incident review records showing lessons learned and process improvements
    - Communication plan identifying who is notified at each escalation level
  ask_for:
    - "Show me an incident ticket from the last 12 months — walk me through detection, analysis, containment, and recovery with timestamps."
    - "Show me your containment runbook for a compromised container — what are the steps and which are automated?"
    - "Show me how you isolate a compromised pod without taking down the entire node or namespace."
    - "Show me your post-incident review process — what changed as a result of your last significant incident?"
  tools:
    generic:
      - PagerDuty (incident alerting and escalation — automated on-call routing)
      - JIRA / ServiceNow (incident ticket tracking with timestamps and activity log)
      - Falco (detection trigger that initiates incident handling)
      - kubectl (containment — `kubectl delete pod`, `kubectl cordon node`, apply NetworkPolicy to isolate)
      - Velero (snapshot for forensic preservation before eradication)
    aws:
      - AWS Systems Manager Automation (runbook execution — automated containment steps)
      - Amazon GuardDuty (detection source that triggers incident)
      - AWS Security Hub (incident aggregation and tracking)
      - AWS IAM (credential revocation — `aws iam delete-access-key`, disable user)
      - VPC Security Groups (network isolation — automated rule update to quarantine instance)
    microsoft:
      - Microsoft Sentinel SOAR (playbook automation for containment and notification)
      - Microsoft Defender XDR (automated investigation and remediation)
      - Azure Logic Apps (automated response workflows triggered by Defender alerts)
      - Entra ID (credential disable — immediate account suspension during incident)

failure_to_implement:
  - Incident response plan exists but has never been tested — team does not know their roles or how to execute containment steps under pressure.
  - No containment runbook — each incident is handled ad hoc, with varying quality and no audit trail.
  - Compromised pod remains running for hours because the on-call engineer is waiting for management approval to isolate it.
  - No post-incident review — the same attack vector is successfully exploited a second time.
  - Incident log is incomplete — timestamps and decisions are not recorded during the incident, making root cause analysis impossible.

related:
  - IR-8
  - SI-4
  - AU-6
  - CP-9

chain: null
