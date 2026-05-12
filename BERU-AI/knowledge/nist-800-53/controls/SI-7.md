---
family: SI
family_name: System and Information Integrity
id: SI-7
name: Software, Firmware, and Information Integrity
---

question: "Can we detect unauthorized changes to software, firmware, or critical system files?"

description: >
  The organization employs integrity verification tools to detect unauthorized changes to
  software, firmware, and information. SI-7 answers the question: is the system running
  what we deployed, or has something changed it? In a container environment this means
  verifying that running images match their signed digests, that no files have been written
  to read-only filesystems, and that no unauthorized binaries have been introduced at
  runtime. In CI/CD it means signing artifacts at build time and verifying signatures
  at deployment. An attacker who can modify what runs without detection has effectively
  bypassed every upstream security control.

enhancements:
  - id: SI-7(1)
    name: Integrity Checks
    description: >
      The information system performs an integrity check of defined software, firmware,
      and information at defined intervals and in response to defined events. Scheduled
      and event-triggered verification — not only at initial deployment. A file that
      passes integrity check on deploy but is modified two hours later must be detected.
  - id: SI-7(6)
    name: Cryptographic Protection
    description: >
      The information system implements cryptographic mechanisms to detect unauthorized
      changes to software, firmware, and information. Cryptographic signatures on artifacts
      (Cosign for container images, in-toto attestations for build provenance) provide
      tamper-evidence that is computationally infeasible to forge.
  - id: SI-7(7)
    name: Integration of Detection and Response
    description: >
      The organization incorporates the detection of unauthorized changes into the
      organizational incident response capability. A detected integrity violation
      automatically triggers an incident — alert, quarantine, or pod termination —
      not just a log entry. Detection without automated response allows an attacker
      to maintain persistence while the detection sits in a queue.
  - id: SI-7(15)
    name: Code Authentication
    description: >
      The information system implements cryptographic mechanisms to authenticate software
      or firmware components prior to installation. Image signature verification at
      admission (Cosign + Kyverno or Sigstore policy controller) blocks unsigned or
      tampered images before they run.

HITRUST_map:
  - "10.l — Control of Technical Vulnerabilities"
  - "10.k — Change Control Procedures"
  - "09.ab — Monitoring System Use"

evidence:
  what_to_look_for:
    - Container image signing configuration (Cosign, Notary v2, or Docker Content Trust) applied to all production images
    - Admission policy verifying image signatures before allowing pods to run
    - Read-only root filesystem enforced on all production containers (securityContext.readOnlyRootFilesystem: true)
    - Runtime detection of filesystem writes outside of explicitly defined writable mounts
    - Build provenance attestations (SLSA provenance, in-toto) for supply chain integrity
    - File integrity monitoring (FIM) on critical host and node paths
  ask_for:
    - "Show me your image signing process — are all production images signed at build time, and show me the Cosign signature verification policy at admission."
    - "Show me your securityContext configuration — do production pods enforce readOnlyRootFilesystem?"
    - "Show me how you detect a runtime modification to a container filesystem — what fires and what is the response?"
    - "Show me your SLSA provenance or build attestation — can you prove that the image running in production was built from the expected source commit?"
  tools:
    generic:
      - Cosign (container image signing and verification — Sigstore ecosystem)
      - Kyverno (admission policy enforcing signature verification before pod admission)
      - Sigstore Policy Controller (cluster-wide image signature enforcement)
      - Falco (runtime detection of unexpected file writes, binary execution in containers)
      - in-toto (supply chain integrity attestation framework)
      - AIDE / Tripwire (host-level file integrity monitoring for node OS files)
    aws:
      - Amazon ECR Image Signing (Notary v2 / Sigstore integration for ECR-hosted images)
      - AWS Signer (code signing service for Lambda functions and IoT device firmware)
      - Amazon Inspector (continuous image integrity and vulnerability assessment)
      - AWS Config (detect changes to configuration outside of approved IaC pipeline)
      - CloudTrail (detect unauthorized API calls that modify running infrastructure)
    microsoft:
      - Azure Container Registry (content trust and image signing with Notary v2)
      - Microsoft Defender for Containers (detect runtime anomalies and unauthorized process execution)
      - Azure Policy (enforce container security contexts including readOnlyRootFilesystem)
      - Microsoft Defender for Cloud (file integrity monitoring for VMs and nodes)
      - GitHub Advanced Security (dependency review and SBOM attestation in pipeline)

failure_to_implement:
  - No image signing — an attacker who compromises the registry can substitute a malicious image that runs without detection.
  - readOnlyRootFilesystem not enforced — malware can write itself to the container filesystem and persist across the container process lifecycle.
  - Image digest not pinned in deployment manifests — a mutable tag (`:latest`) can silently change to a different image between deployments.
  - Build attestations not generated — cannot prove post-incident that the running image came from the expected source, complicating forensics.
  - File integrity violation detected but only logged — attacker maintains persistence for hours while alert sits in queue.

related:
  - SI-2
  - SI-3
  - CM-3
  - CM-6

chain: null
