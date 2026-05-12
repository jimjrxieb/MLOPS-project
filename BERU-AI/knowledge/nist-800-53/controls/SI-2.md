---
family: SI
family_name: System and Information Integrity
id: SI-2
name: Flaw Remediation
---

question: "Are vulnerabilities identified, prioritized, and patched within defined timeframes — with proof?"

description: >
  The organization identifies, reports, and corrects information system flaws; tests software
  and firmware updates related to flaw remediation for effectiveness and potential side effects;
  installs security-relevant updates within organization-defined timeframes; and incorporates
  flaw remediation into the configuration management process. Flaw remediation closes the
  loop between vulnerability discovery (RA-5) and verified fix. The key failure mode is
  not missing the vulnerability — it is finding it and failing to remediate it within the
  required window. FedRAMP defines: Critical — 30 days, High — 30 days, Moderate — 90 days,
  Low — 180 days. Evidence means timestamps on both discovery and remediation.

enhancements:
  - id: SI-2(2)
    name: Automated Flaw Remediation Status
    description: >
      The organization employs automated mechanisms to determine the state of flaw remediation
      for defined system components. Continuous scanning with tracked findings and SLA
      enforcement — not a point-in-time scan with results emailed to a team that may or
      may not act. Findings must be in a system where age and status are visible and
      reportable on demand.
  - id: SI-2(3)
    name: Time to Remediate Flaws and Benchmarks for Corrective Action
    description: >
      The organization measures the time between flaw identification and remediation and
      establishes benchmarks for taking corrective actions. SLA tracking — every finding
      has a discovery timestamp, a severity, and a target remediation date. Overdue
      findings are escalated automatically.

HITRUST_map:
  - "10.l — Control of Technical Vulnerabilities"
  - "10.m — Control of Technical Vulnerabilities"
  - "06.d — Information Security Incident Management"

evidence:
  what_to_look_for:
    - Vulnerability scan results with discovery timestamps and severity ratings
    - Remediation records linking each finding to a patch, configuration change, or accepted risk with sign-off
    - SLA tracking report showing time-to-remediate against defined thresholds per severity
    - Patch management process documentation showing update testing and deployment pipeline
    - Evidence that critical/high findings are not open beyond defined SLA windows
    - Accepted risk register for findings that cannot be patched — compensating controls documented
  ask_for:
    - "Show me your open critical and high vulnerabilities — when were they discovered and what is the current remediation status?"
    - "Show me a closed vulnerability — the scan finding, the fix, and the timestamp proving remediation happened within SLA."
    - "Show me how patch updates are tested before production deployment — is there a staging validation step?"
    - "Show me your accepted risk register — which findings are open beyond SLA and who approved the risk acceptance?"
  tools:
    generic:
      - Trivy (container image and filesystem vulnerability scanning with CVE tracking)
      - Grype (vulnerability scanner for container images and SBOMs)
      - Dependabot / Renovate (automated dependency update PRs with CVE context)
      - kube-bench (K8s component version and patch compliance)
      - OSV Scanner (open source vulnerability scanning against OSV database)
    aws:
      - Amazon Inspector (EC2 and ECR image vulnerability scanning — continuous, not point-in-time)
      - AWS Security Hub (aggregate Inspector, GuardDuty, Config findings into SLA-trackable view)
      - AWS Systems Manager Patch Manager (automated patch deployment with compliance reporting)
      - ECR Enhanced Scanning (continuous CVE scanning of container images on push and on new CVE publication)
    microsoft:
      - Microsoft Defender for Containers (continuous vulnerability assessment for registry images and running containers)
      - Microsoft Defender for Servers (VM vulnerability assessment with remediation tracking)
      - Microsoft Defender for Cloud (secure score and time-to-remediate metrics)
      - Azure Update Manager (patch compliance reporting and automated patching)

failure_to_implement:
  - Vulnerability scan runs monthly — a critical CVE published between scans goes undetected for weeks.
  - Findings are emailed to a distribution list with no tracking system — remediation status is unknown.
  - Patch is applied to the base image but running containers are not restarted — live workloads remain vulnerable.
  - Accepted risk register does not exist — open findings beyond SLA have no documented rationale or compensating control.
  - FedRAMP assessment finds critical findings open for 60+ days — triggers a POA&M and potential authorization impact.

related:
  - RA-5
  - CM-8
  - SI-3
  - SI-7

chain: null
