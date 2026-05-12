---
family: SR
family_name: Supply Chain Risk Management
id: SR-3
name: Supply Chain Controls and Processes
---

question: "Do you have controls and processes that manage the supply-chain risk of every component, vendor, and dependency in the system?"

description: >
  The organization establishes a process or processes to identify and address weaknesses
  or deficiencies in the supply-chain elements and processes of the information system.
  The supply chain controls cover acquisition (vetting vendors and components before
  inclusion), provenance (knowing the origin of each artifact), integrity (verifying
  artifacts have not been tampered with between origin and use), and ongoing monitoring
  (catching changes in the supply chain that affect the security posture). For AI
  systems, SR-3 includes the base model provenance, training-data sources, embedding
  models, and any third-party tooling that participates in inference or training.

enhancements:
  - id: SR-3(1)
    name: Diverse Supply Base
    description: >
      The organization employs a diverse supply base for organization-defined system
      components such that no single vendor concentration creates a critical
      single point of failure for supply-chain integrity.
  - id: SR-3(2)
    name: Limitation of Harm
    description: >
      The organization employs controls to limit harm from potential adversaries
      identifying and targeting the organizational supply chain. Includes
      compartmentalization of supply-chain information, redundant sourcing, and
      restricting public visibility of organizational supply-chain dependencies
      where appropriate.
  - id: SR-3(3)
    name: Sub-Tier Flow Down
    description: >
      The organization ensures that the supply-chain controls and processes
      established for primary suppliers also apply to sub-tier suppliers
      that contribute to the system or its components.

evidence_typical:
  - SR-3 vendor risk register with per-vendor classification, scope, and last review date
  - SOC 2 Type 2 reports or equivalent independent assessments for in-scope vendors
  - DPA / BAA / contract terms with data-handling, breach notification, and audit rights
  - Component inventory cross-referencing CM-8 with vendor / origin per component
  - Cosign or equivalent signature verification for downloaded artifacts (model weights,
    container base images, source dependencies)

common_findings:
  - Vendor onboarded without independent assessment (SOC 2 or equivalent) on file
  - Compliance claims accepted from vendor without verification against authoritative
    sources (FedRAMP Marketplace, SOC 2 attestation report contents)
  - Sub-tier processors not enumerated; the organization knows the primary vendor
    but not who that vendor delegates to
  - AI model artifact downloaded from public hub without signature verification
  - Training data assembled from heterogeneous public sources without per-source
    integrity checking

scanner_hints:
  - Manual review of vendor records during procurement and renewal
  - SBOM tooling (Syft, Trivy) to enumerate software components and surface their origins
  - cosign / Sigstore for artifact signature verification at ingest
  - AI-specific tooling for model provenance (model cards, lineage manifests)

remediation_approach: >
  Establish an SR-3 vendor risk register with the per-vendor classification, scope,
  and required evidence (SOC 2, DPA, sub-tier list). Enforce a no-onboarding-without-evidence
  policy at procurement. Apply SR-4 (Provenance) for every artifact pulled into the system
  including base models, embedding models, container base images, and source dependencies.
  Pair SR-3 with CM-8 (Component Inventory) so the inventory and the supply-chain register
  cross-reference each other. For AI systems, capture model-card lineage and verify model
  weights with cosign-style signatures at ingest.
