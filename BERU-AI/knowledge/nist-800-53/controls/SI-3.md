---
family: SI
family_name: System and Information Integrity
id: SI-3
name: Malicious Code Protection
---

question: "Are controls in place to detect and block malicious code at entry points and during runtime?"

description: >
  The organization employs malicious code protection mechanisms at information system entry
  points and exit points to detect and eradicate malicious code; updates malicious code
  protection mechanisms whenever new releases are available; configures them to perform
  periodic scans and real-time scans of files from external sources; and addresses the
  receipt of false positives. In cloud-native environments, malicious code protection
  operates across multiple layers: supply chain (scanning images before deployment),
  admission (blocking images with known malware), and runtime (detecting unexpected
  process execution, file writes to read-only filesystems, and network connections
  inconsistent with the workload profile).

enhancements:
  - id: SI-3(1)
    name: Central Management
    description: >
      The organization centrally manages malicious code protection mechanisms. Fragmented
      point solutions on individual nodes or images are insufficient — protection must be
      consistently deployed, centrally configured, and centrally monitored across the
      entire environment.
  - id: SI-3(2)
    name: Automatic Updates
    description: >
      The information system automatically updates malicious code protection mechanisms.
      Signature-based detection is only effective when signatures are current. Automated
      update pipelines with verification ensure protection mechanisms are not silently
      stale.
  - id: SI-3(7)
    name: Nonsignature-Based Detection
    description: >
      The information system implements nonsignature-based malicious code detection
      mechanisms. Behavioral detection (Falco rules, eBPF-based runtime monitoring)
      catches novel threats that have no signature. In containerized environments,
      behavioral anomaly detection is more effective than signature scanning because
      the expected behavior of a container is narrowly defined.

HITRUST_map:
  - "09.ab — Monitoring System Use"
  - "10.l — Control of Technical Vulnerabilities"
  - "10.j — Controls Against Malicious Code"

evidence:
  what_to_look_for:
    - Image scanning in CI/CD pipeline — malware and known-bad binaries blocked before registry push
    - Admission controller policy blocking images with critical CVEs or known malware signatures
    - Runtime security tool deployed to all nodes (Falco, Tetragon, or equivalent) with active rule set
    - Falco/runtime alert history showing detections were investigated and acted upon
    - Evidence of automatic signature/rule updates for scanning and runtime tools
    - Network egress controls preventing malware from phoning home after execution
  ask_for:
    - "Show me your image scanning configuration in CI/CD — at what severity threshold does a scan block a build?"
    - "Show me your Falco or runtime security rules — what behaviors trigger alerts, and show me a recent alert that was investigated."
    - "Show me how your runtime security tool is deployed — is it running as a DaemonSet on all nodes, and what's the update cadence for rules?"
    - "Show me what happens if malware is detected in a running container — is there an automated response (kill pod, isolate node) or only alerting?"
  tools:
    generic:
      - Falco (runtime malicious behavior detection via syscall monitoring and K8s audit)
      - Tetragon (eBPF-based runtime security — process, network, and file access enforcement)
      - Trivy (image scanning for known malware and vulnerabilities before deployment)
      - ClamAV (open source AV scanning for file-level malicious code detection)
      - Kyverno (admission policy blocking images from untrusted registries or with critical findings)
    aws:
      - Amazon GuardDuty Malware Protection (scan EBS volumes and S3 objects for malware on demand and on upload)
      - Amazon Inspector (ECR image scanning — continuous CVE and malware detection)
      - AWS Security Hub (aggregate malware findings into a single tracking view)
      - Amazon Macie (detect malicious scripts or sensitive data indicators in S3)
    microsoft:
      - Microsoft Defender for Containers (runtime threat detection for K8s workloads)
      - Microsoft Defender Antivirus (built-in malware protection for Windows and Linux nodes)
      - Microsoft Defender for Cloud (malware detection recommendations and findings)
      - Microsoft Defender for Storage (malware scanning on blob upload via hash reputation and deep scan)

failure_to_implement:
  - No image scanning in CI/CD — malware embedded in a base image or dependency reaches production undetected.
  - Runtime security tool deployed but default rules only — no tuning for the environment means high false-positive rate leads to alert fatigue and ignored alerts.
  - Admission controller in audit mode — malicious images are logged but not blocked.
  - Read-only filesystem not enforced — malware can write to container filesystem after execution begins.
  - No egress filtering — malware executes successfully and establishes C2 channel without detection.

related:
  - SI-2
  - SI-4
  - CM-7
  - SC-7

chain: null
