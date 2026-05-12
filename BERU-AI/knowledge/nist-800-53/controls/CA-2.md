---
family: CA
family_name: Assessment, Authorization, and Monitoring
id: CA-2
name: Control Assessments
---

question: "Are security controls independently assessed on a defined schedule — and do the results drive action?"

description: >
  The organization develops a control assessment plan; assesses controls at defined
  frequencies to determine whether the controls are implemented correctly, operating as
  intended, and producing the desired outcome; produces an assessment report; provides
  the results to defined individuals and organizations; and develops a POA&M. A control
  assessment is not a self-attestation — it is an independent evaluation of whether
  what is documented actually matches what is deployed and operating. The assessment
  produces evidence, the evidence is reviewed, and gaps feed directly into remediation
  or accepted risk.

enhancements:
  - id: CA-2(1)
    name: Independent Assessors
    description: >
      The organization employs assessors with defined independence to conduct control
      assessments. For FedRAMP, this means a 3PAO (Third Party Assessment Organization)
      accredited by the FedRAMP PMO. Independence means the assessors are not part of
      the team that implemented and operates the controls being assessed.
  - id: CA-2(2)
    name: Specialized Assessments
    description: >
      The organization includes specialized assessments in control assessment plans —
      including penetration testing, red team exercises, and announced or unannounced
      assessments. Automated scanning and documentation review do not substitute for
      adversarial testing.
  - id: CA-2(3)
    name: Leveraging Results from External Organizations
    description: >
      The organization leverages the results of control assessments performed by other
      organizations when the assessment meets defined requirements. Shared assessment
      results (SOC 2 Type II, FedRAMP assessment reuse) reduce duplication without
      sacrificing evidence quality.

HITRUST_map:
  - "06.a — Information Security Policy Document"
  - "06.d — Information Security Incident Management"
  - "03.b — Risk Assessment"

evidence:
  what_to_look_for:
    - Control assessment plan documenting scope, methodology, frequency, and assessor independence
    - Most recent assessment report (internal audit, 3PAO report, or equivalent)
    - POA&M generated from assessment findings with owners and target remediation dates
    - Evidence of periodic assessment cadence (annual for FedRAMP, more frequent for high-impact systems)
    - Penetration test results and remediation records
    - Evidence the assessment covered the full control baseline, not a sampled subset
  ask_for:
    - "Show me your most recent control assessment report — who conducted it, when, and what was the scope?"
    - "Show me the POA&M generated from the last assessment — how many open items remain and what are their target dates?"
    - "Show me your penetration test results from the last 12 months — what was the scope, what was found, and what was remediated?"
    - "For FedRAMP: show me your 3PAO authorization package and the date of the last annual assessment."
  tools:
    generic:
      - NIST SP 800-53A (assessment procedures for each control — the companion to 800-53)
      - OpenSCAP (automated SCAP-based control assessment for RHEL and related OS)
      - Prowler (AWS and Azure security best practice assessment — maps to NIST controls)
      - ScoutSuite (multi-cloud security audit — assessment evidence generation)
    aws:
      - AWS Audit Manager (automated evidence collection for frameworks including NIST 800-53, FedRAMP)
      - AWS Config Conformance Packs (NIST 800-53 conformance pack — automated assessment against control set)
      - AWS Security Hub (continuous compliance monitoring — supplemental to periodic formal assessment)
    microsoft:
      - Microsoft Purview Compliance Manager (assessment templates for NIST 800-53, FedRAMP, HIPAA)
      - Microsoft Defender for Cloud Regulatory Compliance (continuous assessment against selected standards)
      - Azure Policy Compliance (resource-level control assessment evidence)

failure_to_implement:
  - No independent assessment — self-attestation accepted as evidence of control effectiveness.
  - Assessment conducted but report not produced or not retained — auditor cannot review findings.
  - POA&M from the last assessment shows no progress on findings that are now two years old.
  - Assessment scope intentionally narrow — core production systems excluded from assessment boundary.
  - No penetration testing — configuration review passes but adversarial exploitation paths go unexamined.

related:
  - CA-7
  - RA-3
  - RA-5

chain: null
