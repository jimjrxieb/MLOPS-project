---
family: CM
family_name: Configuration Management
id: CM-6
name: Configuration Settings
---

question: "Are security configuration settings documented, enforced, and drift-free across every component?"

description: >
  The organization establishes and documents configuration settings for technology products
  employed within the system that reflect the most restrictive mode consistent with operational
  requirements; implements them; identifies, documents, and approves deviations; and monitors
  and controls changes to settings. CM-6 is where the baseline from CM-2 becomes enforceable
  reality — every security-relevant configuration setting is explicitly defined, the most
  restrictive value that operations allows is selected, and deviations require documented
  approval. In K8s, this is Kyverno or OPA policies enforcing pod security standards, network
  policies, and resource constraints. In cloud, this is AWS Config rules and Azure Policy
  deny effects.

enhancements:
  - id: CM-6(1)
    name: Automated Central Management
    description: >
      The organization employs automated mechanisms to centrally manage, apply, and verify
      configuration settings. Policy-as-code (Kyverno, OPA/Gatekeeper, AWS Config, Azure Policy)
      is the expected implementation — configuration is enforced at admission time, not
      checked periodically after the fact.
  - id: CM-6(2)
    name: Respond to Unauthorized Changes
    description: >
      The organization employs automated mechanisms to respond to unauthorized changes to
      configuration settings. Responses include alerting, blocking admission of non-compliant
      resources, and triggering remediation pipelines. Detection without response is audit
      theater.

HITRUST_map:
  - "09.ab — Monitoring System Use"
  - "10.l — Control of Technical Vulnerabilities"
  - "10.m — Control of Technical Vulnerabilities"

evidence:
  what_to_look_for:
    - Policy-as-code definitions (Kyverno ClusterPolicies, OPA rego bundles, AWS Config rules, Azure Policy definitions)
    - Enforcement mode configuration — policies set to Enforce/Deny, not just Audit/Warn
    - Documented deviation records for approved exceptions to the security baseline
    - Drift detection output showing current configuration matches approved settings
    - CIS Benchmark mapping showing which benchmark controls are enforced by which policies
  ask_for:
    - "Show me your Kyverno or OPA policies in production — are they in Enforce mode or Audit mode? If Audit, why?"
    - "Show me your AWS Config rules or Azure Policy assignments — what's the compliance percentage and how are non-compliant resources handled?"
    - "Show me your approved deviation list — which components are explicitly exempted from baseline settings and why?"
    - "Show me a drift detection report — has any component drifted from approved settings in the last 30 days and what was the response?"
  tools:
    generic:
      - Kyverno (`kubectl get clusterpolicies` — verify enforce mode, check violation events)
      - OPA / Gatekeeper (`kubectl get constrainttemplate,constraint` — check enforcement action)
      - kube-bench (CIS K8s Benchmark — verify configuration settings against benchmark)
      - kube-score (flag missing security contexts, resource limits, network policies)
      - Trivy (misconfiguration scanning — Dockerfile, K8s manifests, Terraform)
    aws:
      - AWS Config rules (managed and custom — verify Enforce mode via remediation actions)
      - AWS Config Conformance Packs (CIS AWS Foundations, NIST 800-53 packs)
      - AWS Security Hub (aggregated Config findings by control)
      - AWS Systems Manager (enforce configuration via State Manager associations)
    microsoft:
      - Azure Policy (deny effect assignments — verify compliance percentage)
      - Microsoft Defender for Cloud (secure score recommendations mapped to CM-6 settings)
      - Azure Arc (extend Azure Policy enforcement to hybrid and on-prem systems)
      - Azure Resource Graph (query current configuration settings at scale)

failure_to_implement:
  - Security policies deployed in Audit mode only — violations are logged but non-compliant workloads run unimpeded.
  - CIS Benchmark referenced in documentation but no technical controls enforce the benchmark settings.
  - Deviation process does not exist — ad-hoc exceptions are granted verbally with no documentation or expiry.
  - AWS Config rules configured but no remediation actions — findings accumulate without correction.
  - Pod security contexts missing on production workloads — containers run as root with no capability drops.

related:
  - CM-2
  - CM-3
  - CM-7
  - SI-7

chain: null
