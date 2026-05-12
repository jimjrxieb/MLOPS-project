---
family: AU
family_name: Audit and Accountability
id: AU-6
name: Audit Record Review, Analysis, and Reporting
---

question: "Is someone actually reviewing audit logs — regularly, with a defined process, and acting on findings?"

description: >
  The organization reviews and analyzes system audit records periodically for indications of
  inappropriate or unusual activity, reports findings to defined personnel, and adjusts the
  level of audit review, analysis, and reporting based on risk. Logs that are generated but
  never reviewed provide zero security value — they create storage costs without detection
  capability. AU-6 is where audit data becomes security intelligence. The key question is
  not whether logs exist, but whether a human or automated system is reading them and
  acting on what they find.

enhancements:
  - id: AU-6(1)
    name: Automated Process Integration
    description: >
      The organization employs automated mechanisms to integrate audit review, analysis,
      and reporting. Manual log review is insufficient at cloud-native scale — SIEM, log
      analytics, and alerting pipelines are the expected implementation. Automated does
      not mean no human review; it means humans review alerts, not raw log streams.
  - id: AU-6(3)
    name: Correlate Audit Repositories
    description: >
      The organization analyzes and correlates audit records across different repositories
      to gain organization-wide situational awareness. Correlating K8s API server logs
      with cloud provider logs and application logs reveals attack chains invisible in
      any single source — lateral movement that looks normal per-system is anomalous
      when viewed across systems.

HITRUST_map:
  - "09.ab — Monitoring System Use"
  - "06.d — Information Security Incident Management"
  - "09.aa — Audit Logging"

evidence:
  what_to_look_for:
    - SIEM or log analytics platform with active alert rules targeting the defined auditable events from AU-2
    - Records showing alerts were reviewed, triaged, and either closed with rationale or escalated
    - Scheduled review cadence documentation (daily automated, weekly human triage, monthly trend report)
    - Cross-source correlation rules (e.g., correlating failed auth in IdP with lateral movement in K8s audit log)
    - Reporting artifacts showing findings were communicated to defined personnel (security team, ISSO, CISO)
  ask_for:
    - "Show me your active SIEM alert rules — which audit events trigger alerts, and what's the escalation path?"
    - "Show me your alert triage records for the last 30 days — how many alerts fired, how many were investigated, and what was the outcome?"
    - "Show me a cross-source correlation example — can you detect an attacker who fails auth externally then succeeds internally via a different path?"
    - "Show me how audit findings are reported — who receives the report, how often, and what format?"
  tools:
    generic:
      - Elasticsearch / OpenSearch + Kibana (SIEM log ingestion and alerting)
      - Grafana Loki (log aggregation with alert rules)
      - Falco (real-time K8s audit event analysis and alerting)
      - Splunk (enterprise SIEM with correlation rules)
    aws:
      - Amazon Security Hub (aggregates GuardDuty, Config, Inspector findings — one review pane)
      - CloudWatch Alarms (metric filters on CloudTrail logs trigger alerts)
      - Amazon GuardDuty (ML-based anomaly detection on CloudTrail, VPC Flow, DNS logs)
      - AWS Detective (investigation and correlation across audit sources)
    microsoft:
      - Microsoft Sentinel (SIEM + SOAR — correlation rules across Entra ID, Defender, Azure logs)
      - Microsoft Defender XDR (cross-product alert correlation)
      - Azure Monitor Alerts (metric and log-based alerting)
      - Microsoft Purview Audit (unified audit log review across Microsoft 365 workloads)

failure_to_implement:
  - Logs are collected and stored but no alert rules exist — an active intrusion generates no notification.
  - Alerts exist but are acknowledged without investigation — alert fatigue has made the SIEM functionally silent.
  - Each system's logs are reviewed in isolation — a multi-stage attack that spans K8s and cloud is never correlated.
  - No reporting mechanism — the ISSO and CISO have no visibility into audit findings.
  - Incident post-mortem reveals that logs showing attacker activity existed for weeks before detection.

related:
  - AU-2
  - AU-3
  - AU-7
  - AU-9
  - SI-4

chain: "AU-2 → AU-3 → AU-12 → AU-6 → AU-7"
