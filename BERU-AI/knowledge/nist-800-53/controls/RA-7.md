---
family: RA
family_name: Risk Assessment
id: RA-7
name: Risk Response
---

question: "When a risk is identified, is there a defined process for deciding how to respond — and evidence that the decision was made?"

description: >
  The organization responds to findings from security assessments, monitoring, vulnerability
  scanning, and audits in accordance with organizational risk tolerance. Risk response is
  the decision point between identification and action: accept, mitigate, transfer, or
  avoid. Every identified risk requires an explicit decision — leaving a finding open
  without a documented disposition is not a response, it is negligence. RA-7 closes the
  loop that RA-3 and RA-5 open: risks are not just found and tracked, they are formally
  responded to with a documented owner, rationale, and timeline.

enhancements: []

HITRUST_map:
  - "03.a — Risk Management Program"
  - "03.b — Risk Assessment"
  - "03.c — Risk Mitigation"

evidence:
  what_to_look_for:
    - Risk response records for each identified risk — accepted, mitigated, transferred, or avoided with documented rationale
    - Risk acceptance sign-off from an authority appropriate to the risk level (system owner, ISSO, CISO)
    - POA&M (Plan of Action and Milestones) for risks that cannot be immediately mitigated — target dates and responsible parties
    - Evidence that risk responses are reviewed and updated when risk posture changes
    - Compensating control documentation for accepted risks — what is in place to reduce residual risk
  ask_for:
    - "Show me a risk that was formally accepted — who accepted it, what was the rationale, and what compensating controls are in place?"
    - "Show me your POA&M — for each open item, what is the target remediation date and who is the responsible party?"
    - "Show me how you handle a critical finding that cannot be patched immediately — what is the documented interim response?"
    - "Show me evidence that your POA&M items are reviewed and updated on schedule — are there items with overdue target dates?"
  tools:
    generic:
      - POA&M tracker (JIRA, ServiceNow GRC, Archer — structured tracking of open risks with milestones)
      - Risk register (links RA-3 identified risks to RA-7 disposition decisions)
      - NIST SP 800-39 (organizational risk response framework — accept, avoid, mitigate, transfer)
    aws:
      - AWS Security Hub (finding suppression with required rationale — documented risk acceptance per finding)
      - AWS Audit Manager (assessment findings linked to remediation evidence and POA&M)
      - AWS Config (remediation action tracking against Config rule findings)
    microsoft:
      - Microsoft Purview Compliance Manager (improvement actions with owner assignment and evidence upload)
      - Microsoft Defender for Cloud (recommendation dismissal with documented justification)
      - Azure Policy (exemption with documented scope and expiry — formal risk acceptance for policy violations)

failure_to_implement:
  - Vulnerability findings pile up in a scanner with no disposition — no evidence of any risk response decision.
  - Risk acceptance is verbal — no written sign-off means the accepting authority can deny awareness post-incident.
  - POA&M exists but target dates are never updated — items are perpetually "in progress" with no accountability.
  - Compensating controls are claimed but not documented — auditor cannot verify what is actually reducing the accepted risk.
  - CISO signs off on risk acceptances they were never briefed on — approval chain is performative rather than substantive.

related:
  - RA-3
  - RA-5
  - CA-7

chain: null
