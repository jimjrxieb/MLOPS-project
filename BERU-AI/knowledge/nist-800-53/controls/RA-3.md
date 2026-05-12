---
family: RA
family_name: Risk Assessment
id: RA-3
name: Risk Assessment
---

question: "Has the organization formally assessed its risk — identified threats, likelihoods, and impacts — and documented the results?"

description: >
  The organization conducts an assessment of risk, including the likelihood and magnitude of
  harm from unauthorized access, use, disclosure, disruption, modification, or destruction
  of the system and the information it processes, stores, or transmits; documents risk
  assessment results; reviews risk assessment results at defined frequencies; disseminates
  results to defined personnel; and updates the risk assessment when there are significant
  changes to the system or environment. A risk assessment is the foundation of every other
  security decision — prioritization, resource allocation, and control selection all depend
  on a documented understanding of what is actually at risk and from what. Without it,
  security controls are selected by habit or compliance checkbox rather than threat.

enhancements: []

HITRUST_map:
  - "03.a — Risk Management Program"
  - "03.b — Risk Assessment"
  - "03.c — Risk Mitigation"

evidence:
  what_to_look_for:
    - Formal risk assessment document covering the system's threat sources, vulnerabilities, likelihood ratings, and impact ratings
    - Risk register with each identified risk, owner, current status, and planned or completed treatment
    - Risk assessment review records showing periodic re-evaluation (typically annual or on significant change)
    - Evidence the risk assessment informed control selection — traceability between risk findings and implemented controls
    - Sign-off from system owner or ISSO on the most recent risk assessment
  ask_for:
    - "Show me your current system risk assessment — when was it completed, who approved it, and what were the top-rated risks?"
    - "Show me your risk register — for each open risk, who is the owner and what is the treatment plan and target date?"
    - "Show me how a significant system change (new cloud region, new data type) triggers a risk assessment update."
    - "Show me the traceability between your risk assessment findings and the controls you implemented — how do you know the controls address the actual risks?"
  tools:
    generic:
      - NIST SP 800-30 (risk assessment methodology — threat source, vulnerability, likelihood, impact)
      - OWASP Risk Rating Methodology (likelihood × impact scoring for application risks)
      - Threat modeling tools (STRIDE, PASTA, MITRE ATT&CK Navigator)
      - Risk register (spreadsheet, JIRA, or GRC platform — formalized tracking of identified risks)
    aws:
      - AWS Trusted Advisor (risk-relevant configuration findings across cost, security, fault tolerance)
      - Amazon Inspector (contributes CVE-level risk data to feed into the broader risk assessment)
      - AWS Security Hub (aggregated risk signal across accounts — feeds risk register)
      - AWS Well-Architected Tool (structured risk assessment against AWS WAF pillars)
    microsoft:
      - Microsoft Defender for Cloud (secure score as quantified risk signal)
      - Azure Security Center Regulatory Compliance (maps findings to risk by control family)
      - Microsoft Purview Compliance Manager (risk assessment and compliance score)
      - Microsoft Threat Modeling Tool (formal threat model generation for system components)

failure_to_implement:
  - No formal risk assessment means control selection is arbitrary — gaps in coverage are invisible until an incident reveals them.
  - Risk assessment completed for the initial ATO and never updated — does not reflect current architecture, data types, or threat landscape.
  - Risk register exists but has no owners or treatment plans — identified risks are documented but not managed.
  - Risk assessment results not communicated to system owner or leadership — security team holds risk information that decision-makers never see.
  - Auditor finds risk assessment predates a major system change — authorization basis is invalid.

related:
  - RA-5
  - RA-7
  - CA-2
  - PL-2

chain: null
