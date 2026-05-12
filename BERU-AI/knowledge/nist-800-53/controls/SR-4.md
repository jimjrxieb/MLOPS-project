---
family: SR
family_name: Supply Chain Risk Management
id: SR-4
name: Provenance
---

question: "Can you trace every component, artifact, and dataset in the system back to its origin with documented evidence at each handoff?"

description: >
  The organization establishes and maintains provenance for the information system,
  system components, and associated data. Provenance is the documented chain that
  links every artifact in production to its origin — for traditional IT systems this
  covers software components, container images, libraries, and configuration sources;
  for AI systems it additionally covers base models, embedding models, training
  datasets, fine-tuning artifacts, and the lineage records that demonstrate which
  inputs produced which outputs at each stage. SR-4 evidence is what enables the
  organization to answer "did this artifact come from where we expected" rather than
  "the artifact looks correct so we'll assume it is."

enhancements:
  - id: SR-4(1)
    name: Identity
    description: >
      The organization establishes a unique identification capability for every
      supply-chain artifact (component, module, dataset, model). Identification is
      sufficient to distinguish authentic artifacts from look-alikes and to detect
      substitution attempts.
  - id: SR-4(2)
    name: Track and Trace
    description: >
      The organization establishes processes to track changes to organization-defined
      system components throughout their lifecycle. Includes recording who changed
      what, when, and on what authority — for AI systems this includes which dataset
      contributed to which fine-tune and which fine-tune is in which deployment.
  - id: SR-4(3)
    name: Validate as Genuine and Not Altered
    description: >
      The organization employs controls to validate that the system or system
      component received is genuine and has not been altered. Validation typically
      relies on cryptographic signatures (cosign, SLSA attestations) or independent
      hash verification against the publisher's authoritative record.
  - id: SR-4(4)
    name: Supply Chain Integrity / Pedigree
    description: >
      The organization employs organization-defined controls and conducts assessments
      to ensure the integrity of the system component supply chain by establishing
      the authoritative source of supply for components and ensuring components
      received are sourced through the authorized supply chain.

evidence_typical:
  - SBOM (Software Bill of Materials) per release artifact, generated via Syft or
    equivalent at build time, attached to the release record
  - cosign signatures (or equivalent) on container images, model weights, and
    datasets, with public-key trust store under organizational control
  - Lineage manifest (JSON or equivalent structured record) for AI artifacts that
    documents source datasets, training configuration, and resulting weights with
    SHA-256 hashes per artifact
  - Vendor attestations (SOC 2 Type 2, FedRAMP authorization, SLSA level statements)
    cross-referenced to the SR-3 vendor risk register
  - Drift detection: periodic re-verification of artifact hashes vs the recorded
    lineage to catch tampering between handoff and use

common_findings:
  - Container images deployed without cosign signature verification at admission
  - Model artifacts ingested without integrity attestation
  - Training datasets assembled from heterogeneous public sources without per-source
    integrity check
  - Lineage manifest absent or stale (recorded at training time, never re-verified)
  - SBOM generated but not attached to the release record or not consumed by any
    downstream tooling
  - Vendor compliance claims accepted without verification against the authoritative
    source (FedRAMP Marketplace, vendor SOC 2 attestation report contents)

scanner_hints:
  - cosign verify against the organizational trust store for every artifact pulled
  - SBOM-driven dependency monitoring (Trivy SBOM scan, Snyk SBOM analysis) for
    detecting newly-introduced supply-chain components
  - Lineage-manifest verification scripts that re-hash artifacts at deploy time and
    compare to the recorded value
  - For AI artifacts, model-card-completeness checking against the organizational
    SR-3 evidence standard

remediation_approach: >
  Establish identity for every artifact (cosign signature for container images and
  model weights, SHA-256 for datasets) and require admission-time verification before
  the artifact is permitted in production. Maintain a lineage manifest (machine-
  readable) that documents every artifact's source, authorized handoff path, and
  current hash. Cross-reference SR-4 evidence with SR-3 vendor records, CM-8
  component inventory, and SI-7 information-integrity controls. For AI systems
  specifically, treat training datasets and fine-tuned weights as first-class
  supply-chain artifacts with full lineage from source data through the deployed
  model. Verify pedigree through the organization's authorized supply chain rather
  than by accepting vendor claims.
