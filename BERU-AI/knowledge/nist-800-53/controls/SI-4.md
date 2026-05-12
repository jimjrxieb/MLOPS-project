---
family: SI
family_name: System and Information Integrity
id: SI-4
name: System Monitoring
---

question: "Is the system continuously monitored for attacks, anomalies, and policy violations — with active alerting?"

description: >
  The organization monitors the system to detect attacks and indicators of potential attacks,
  unauthorized connections, unauthorized use of system resources, and other anomalous behavior.
  System monitoring is the detection layer — distinct from audit logging (AU), which records
  what happened, and malicious code protection (SI-3), which blocks known-bad code. SI-4
  is about behavioral detection: what is the system doing right now that it should not be
  doing? Monitoring without alerting is observation without response. Both are required.
  In K8s, this spans the control plane (API server audit events), the data plane (pod and
  node behavior), and the network (unexpected connections, exfiltration patterns).

enhancements:
  - id: SI-4(2)
    name: Automated Tools and Mechanisms for Real-Time Analysis
    description: >
      The organization employs automated tools and mechanisms to support near real-time
      analysis of events. Human review of raw logs is not real-time analysis. SIEM rules,
      streaming analytics, and runtime security tools that fire within seconds of a
      detectable event are the expected implementation.
  - id: SI-4(4)
    name: Inbound and Outbound Communications Traffic
    description: >
      The organization monitors inbound and outbound communications traffic for unusual
      or unauthorized activity or conditions. Network monitoring covers both directions —
      inbound attack traffic and outbound exfiltration or C2 communication. VPC Flow Logs
      with anomaly detection and service mesh telemetry both contribute.
  - id: SI-4(5)
    name: System-Generated Alerts
    description: >
      The information system alerts defined personnel when the following indications of
      compromise or potential compromise occur. Alerts must be named, routed to specific
      individuals, and have a defined response. An alert that fires into a queue no one
      watches is not a SI-4(5) control.
  - id: SI-4(11)
    name: Analyze Communications Traffic Anomalies
    description: >
      The organization analyzes outbound communications traffic at selected interior points
      to discover anomalies. East-west traffic between services is analyzed, not just
      north-south traffic at the perimeter. An attacker who has moved laterally inside
      the cluster is only visible through interior traffic analysis.

HITRUST_map:
  - "09.ab — Monitoring System Use"
  - "06.d — Information Security Incident Management"
  - "09.m — Network Controls"

evidence:
  what_to_look_for:
    - Runtime security tool (Falco, Tetragon) deployed on all nodes with active alert routing
    - SIEM or security analytics platform with rules tuned to the environment and active alert queue
    - Network monitoring covering both ingress and egress traffic with anomaly detection
    - Alert routing documentation — who receives which alert type, escalation path, and SLA
    - Evidence that monitoring covers the control plane (K8s API server) and the data plane (workload behavior)
    - Incident tickets or triage records showing alerts were received, investigated, and resolved
  ask_for:
    - "Show me your Falco rules and where alerts are sent — PagerDuty, Slack, SIEM? Show me a recent alert that was triaged."
    - "Show me your SIEM detection rules relevant to K8s and cloud — what TTPs are you detecting and how are they mapped to MITRE ATT&CK?"
    - "Show me your network monitoring — can you detect anomalous east-west traffic between pods that is not in the NetworkPolicy?"
    - "Show me your alert escalation matrix — for a critical SI-4 alert at 2 AM, who gets paged and what is the expected response time?"
  tools:
    generic:
      - Falco (syscall-based runtime detection — shell in container, privilege escalation, unexpected network connection)
      - Tetragon (eBPF runtime enforcement and telemetry)
      - Prometheus + Alertmanager (metrics-based anomaly alerting — resource spike, pod crash loop)
      - Grafana (visualization of monitoring data with alerting rules)
      - MITRE ATT&CK for Containers (TTP framework for detection rule development)
    aws:
      - Amazon GuardDuty (ML-based threat detection on CloudTrail, VPC Flow Logs, DNS — covers K8s audit events for EKS)
      - AWS Security Hub (aggregate findings from GuardDuty, Inspector, Config into prioritized alert view)
      - Amazon CloudWatch (metric alarms and log-based anomaly detection)
      - AWS Detective (graph-based investigation of suspicious activity across accounts)
    microsoft:
      - Microsoft Sentinel (cloud-native SIEM — detection rules, threat hunting, automated response)
      - Microsoft Defender for Containers (K8s runtime threat detection — maps to MITRE ATT&CK)
      - Microsoft Defender XDR (cross-product alert correlation and investigation)
      - Azure Monitor (infrastructure-level metric and log alerting)

failure_to_implement:
  - Runtime security tool installed but alerts route to /dev/null — no one reads the output.
  - SIEM has detection rules but they were never tuned — 95% of alerts are false positives, creating alert fatigue that causes real alerts to be ignored.
  - Only perimeter traffic monitored — lateral movement inside the cluster is completely invisible.
  - No on-call rotation for security alerts — a critical detection at 2 AM sits unacknowledged until the next business day.
  - Monitoring gaps in non-primary regions — an attacker operating in a secondary region generates no alerts.

related:
  - AU-6
  - SI-3
  - IR-4
  - SC-7

chain: null
