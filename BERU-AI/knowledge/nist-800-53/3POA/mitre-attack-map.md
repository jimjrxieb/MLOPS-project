# MITRE ATT&CK + ATLAS Coverage Map

**Purpose**: Maps every threat technique to the NIST 800-53 control that governs it
and the GP-Copilot tool that detects or prevents it. Use this when asked:
"what threats does your security stack detect?" or "how do you cover ATT&CK?"

An auditor or CISO expects two things: coverage breadth and control traceability.
This document gives both.

---

## MITRE ATT&CK for Enterprise (K8s / Container / Cloud)

Format: `Technique | Tactic | NIST Control | Tool | Detection Method`

### Initial Access

| Technique | ID | NIST Control | Tool | How It Detects / Prevents |
|-----------|----|-------------|------|--------------------------|
| Exploit Public-Facing Application | T1190 | RA-5, SA-10 | Semgrep, nuclei, ZAP | Semgrep catches vulnerable code pre-deploy; nuclei/ZAP test the running surface |
| Supply Chain Compromise | T1195 | SA-12, SI-7 | cosign, Trivy SBOM, Gitleaks | cosign blocks unsigned images; Trivy SBOM tracks component provenance |
| Supply Chain — Software | T1195.002 | SA-12(3), SI-7(1) | cosign | Sigstore transparency log — every image has a verifiable build provenance |
| Valid Accounts | T1078 | AC-2, AC-6 | Falco, GuardDuty, RBAC-lookup | Falco: K8s service account abuse; GuardDuty: AWS console login anomalies |

### Execution

| Technique | ID | NIST Control | Tool | How It Detects / Prevents |
|-----------|----|-------------|------|--------------------------|
| Command and Script Interpreter | T1059 | SI-3, IR-4 | Falco | Rule: `spawned_shell_in_container` — alerts on `/bin/sh`, `/bin/bash` in running containers |
| Container Administration Command | T1609 | SI-4, AC-6 | Falco | Rule: `exec_in_container` — alerts on kubectl exec sessions |
| Deploy Container | T1610 | CM-7, AC-3 | Kyverno, Falco | Kyverno blocks unverified images at admission; Falco detects unexpected image pulls |

### Persistence

| Technique | ID | NIST Control | Tool | How It Detects / Prevents |
|-----------|----|-------------|------|--------------------------|
| Implant Container Image | T1525 | SA-12, CM-7, SI-7 | cosign, Kyverno, Trivy | cosign: unsigned image blocked; Kyverno: image registry allowlist; Trivy: malware scan |
| Account Manipulation | T1098 | AC-2, CM-3 | Falco, CloudTrail | Falco: K8s RBAC modification rule; CloudTrail: IAM policy changes |
| Create or Modify System Process | T1543 | CM-7, SI-4 | Falco, Kyverno | Kyverno: no hostPID/hostIPC; Falco: systemd unit creation in container |
| Modify Authentication Process | T1556 | IA-5, CM-3 | CloudTrail, GuardDuty | CloudTrail: authentication configuration changes; GuardDuty: root account usage |

### Privilege Escalation

| Technique | ID | NIST Control | Tool | How It Detects / Prevents |
|-----------|----|-------------|------|--------------------------|
| Escape to Host | T1611 | AC-6, SI-4 | Falco, Kyverno | Kyverno: deny privileged containers + hostPath mounts; Falco: nsenter/chroot rules |
| Abuse Elevation Control Mechanism | T1548 | AC-6, AU-2 | Falco, GuardDuty | Falco: sudo in container; GuardDuty: role escalation in AWS |
| Process Injection | T1055 | SC-39, SI-4 | Falco, Kyverno | Kyverno: seccomp RuntimeDefault; Falco: ptrace syscall rule |

### Defense Evasion

| Technique | ID | NIST Control | Tool | How It Detects / Prevents |
|-----------|----|-------------|------|--------------------------|
| Masquerading | T1036 | SI-4, SI-7 | Falco | Rule: `read_sensitive_file_untrusted` + image name anomaly detection |
| Indicator Removal | T1070 | AU-9, SI-7 | Falco, CloudTrail | Falco: log file modification rule; CloudTrail S3: object delete events on audit bucket |
| Modify Cloud Compute Infrastructure | T1578 | CM-3, CA-7 | CloudTrail, GuardDuty | CloudTrail: EC2/EKS mutation events; GuardDuty: unusual API calls |
| Unused/Unsupported Cloud Regions | T1535 | CM-7, CA-7 | Prowler | Prowler check: regions without GuardDuty enabled |

### Credential Access

| Technique | ID | NIST Control | Tool | How It Detects / Prevents |
|-----------|----|-------------|------|--------------------------|
| OS Credential Dumping | T1003 | AC-6, SC-28 | Falco, Kyverno | Kyverno: read-only filesystem; Falco: `/etc/shadow` access rule |
| Unsecured Credentials | T1552 | SC-12, AC-6 | Gitleaks, Falco | Gitleaks: scans git history for secrets; Falco: environment variable secrets rule |
| Credentials in Files | T1552.001 | SC-12 | Gitleaks | Git history scan catches secrets "deleted" in subsequent commits |
| Forge Web Credentials | T1606 | IA-5, SC-23 | cert-manager, Dex | cert-manager: short-lived certs; Dex: OIDC token validation |

### Discovery

| Technique | ID | NIST Control | Tool | How It Detects / Prevents |
|-----------|----|-------------|------|--------------------------|
| Network Service Discovery | T1046 | AC-4, SI-4 | Falco, NetworkPolicy | Falco: unexpected network connections; Kyverno: deny hostNetwork |
| Cloud Service Discovery | T1526 | CA-7, RA-5 | Prowler, GuardDuty | Prowler: identifies overly permissive service exposure; GuardDuty: API enumeration |
| Account Discovery | T1087 | AC-2, AU-2 | Falco, CloudTrail | Falco: IAM enumeration commands; CloudTrail: ListUsers/ListRoles calls |

### Lateral Movement

| Technique | ID | NIST Control | Tool | How It Detects / Prevents |
|-----------|----|-------------|------|--------------------------|
| Internal Spear Phishing | T1534 | SI-4, IR-4 | Falco | Unusual inter-pod communication pattern rules |
| Remote Service Session Hijacking | T1563 | SC-8, IA-5 | Falco, cert-manager | Falco: unexpected SSH; mTLS via Istio prevents session hijack |
| Use Alternate Authentication Material | T1550 | IA-5, SC-23 | GuardDuty | GuardDuty: credential use from unexpected location |

### Collection

| Technique | ID | NIST Control | Tool | How It Detects / Prevents |
|-----------|----|-------------|------|--------------------------|
| Data from Cloud Storage | T1530 | AC-3, SC-28 | Prowler, GuardDuty | Prowler: public S3 buckets; GuardDuty: unusual S3 GetObject patterns |
| Data from Information Repositories | T1213 | AC-3, AU-2 | Falco, RBAC-lookup | Falco: sensitive file access; RBAC: scoped service account permissions |
| Screen Capture (K8s secrets) | T1113 | SC-28, AC-6 | Falco, ExternalSecrets | Falco: secrets access in container; ExternalSecrets: no secrets in manifests |

### Exfiltration

| Technique | ID | NIST Control | Tool | How It Detects / Prevents |
|-----------|----|-------------|------|--------------------------|
| Exfiltration Over Alternative Protocol | T1048 | AC-4, SI-4, SC-7 | Falco, NetworkPolicy | Falco: unexpected outbound connection rules; NetworkPolicy: egress allowlist |
| Transfer Data to Cloud Account | T1537 | SC-7, AU-2 | GuardDuty, CloudTrail | GuardDuty: cross-account data movement; CloudTrail: S3 cross-account copy |

### Impact

| Technique | ID | NIST Control | Tool | How It Detects / Prevents |
|-----------|----|-------------|------|--------------------------|
| Resource Hijacking (cryptomining) | T1496 | SC-6, SI-4 | Falco | Falco: `crypto_miners_using_the_container` rule; ResourceQuota caps CPU |
| Data Destruction | T1485 | CP-10, SI-7 | Falco, Velero | Falco: file deletion + rm -rf rules; Velero: automated backup restoration |
| Defacement | T1491 | SI-7, AU-2 | Falco | Falco: write to web-served directories in container |
| Service Stop | T1489 | SI-4, CP-10 | Falco, Prometheus | Falco: process kill in container; Prometheus: service availability alerts |

---

## MITRE ATLAS (AI / ML Threat Techniques)

ATLAS is the adversarial ML equivalent of ATT&CK. Relevant techniques for GP-Copilot AI workloads:

| Technique | ID | NIST AI 600-1 | Tool | How It Detects / Prevents |
|-----------|----|--------------|------|--------------------------|
| Direct Prompt Injection | AML.T0048 | MANAGE 2.4–2.6 | garak | Automated probe: injection payloads across 40+ categories |
| LLM Jailbreak | AML.T0054 | MANAGE 2.4–2.6 | garak, promptfoo | Jailbreak probes: DAN, roleplay, encoding, token manipulation |
| Adversarial Input — Image | AML.T0056 | MEASURE 2.1–2.3 | counterfit, ART | FGSM + PGD attacks against image classifiers |
| Poison Training Data | AML.T0020 | MAP 2.1–2.3 | Great Expectations, Presidio | Schema validation + PII detection before ingestion |
| Backdoor ML Model | AML.T0011 | MAP 2.1, SI-7 | cosign (model), SHA256 chain | Model signature verification; checkpoint hash chain |
| ML Supply Chain Compromise | AML.T0010 | SA-12, SI-7 | cosign, MLflow | cosign signs every GGUF artifact; MLflow ties checkpoint to training run |
| Erode ML Model Integrity | AML.T0031 | MEASURE 2.1–2.3 | counterfit, ART | Adversarial robustness testing pre-deployment |
| Steal ML Model | AML.T0035 | AC-3, AC-6 | OPA model API policy | API rate limiting + authentication required for all inference endpoints |
| Craft Adversarial Data | AML.T0043 | MEASURE 2.1 | counterfit, ART | Black-box and white-box adversarial example generation |
| Exploit Public-Facing ML API | AML.T0046 | RA-5, AC-3 | garak, nuclei | garak probes external-facing LLM endpoints; nuclei scans API surface |
| Training Data Extraction | AML.T0047 | SC-28, AU-2 | Presidio, ChromaDB auth | PII scrubbed before training; ChromaDB requires auth for embedding queries |
| Membership Inference | AML.T0049 | SC-28, RA-3 | ART | ART membership inference attack simulation |
| Model Inversion | AML.T0053 | SC-28, AC-3 | ART, API rate limiting | ART inversion simulation; API returns minimal output to reduce inversion surface |

---

## ATT&CK Coverage Summary by Control Family

| Control Family | ATT&CK Tactics Covered | Primary Detection Tool |
|---------------|----------------------|----------------------|
| AC — Access Control | Initial Access (Valid Accounts), Privilege Escalation, Persistence | Falco + RBAC-lookup + GuardDuty |
| AU — Audit | Defense Evasion (Indicator Removal), all tactics via logs | Falco → Splunk + CloudTrail |
| CA — Monitoring | All tactics via continuous posture | Kubescape + GuardDuty + Prowler |
| CM — Config Mgmt | Execution (Deploy Container), Persistence (Implant Image) | Kyverno + cosign + Checkov |
| CP — Contingency | Impact (Data Destruction, Service Stop) | Velero + Falco |
| IA — Identity | Credential Access, Lateral Movement | cert-manager + GuardDuty + Dex |
| IR — Incident Response | All tactics — response side | Falco responders + Splunk |
| RA — Risk Assessment | Initial Access (Exploit), all vulnerability classes | Semgrep + Trivy + Prowler + garak |
| SA — Acquisition | Supply Chain (T1195, T1525) | cosign + Trivy SBOM + Gitleaks |
| SC — Comms Protection | Credential Access, Exfiltration, Collection | Istio mTLS + NetworkPolicy + ExternalSecrets |
| SI — System Integrity | Execution, Defense Evasion, Impact | Falco + Polaris + cosign |

---

## Gap: What ATT&CK Techniques GP-Copilot Does Not Cover

Document these honestly. An auditor who finds an uncovered technique you didn't mention
loses confidence. One you documented loses nothing.

| Technique | ID | Why Not Covered | Recommended Tool |
|-----------|-----|----------------|-----------------|
| Phishing (human) | T1566 | Human vector, not infrastructure | Security awareness training (AT-2) |
| Hardware Additions | T1200 | Physical access — cloud-native scope | Data center provider covers |
| Firmware modification | T1495 | Below hypervisor layer | Cloud provider responsibility |
| Adversarial ML — Real-time monitoring | AML.T0046 (streaming) | Sub-10ms latency constraint for stream processing | Fiddler, Arize, WhyLabs (enterprise) |
| Behavioral analysis at scale | T1078 (long-term) | Requires ML baseline over weeks | Darktrace, Vectra (enterprise) |
| Kernel exploit (0-day) | T1068 | eBPF rules catch known patterns; 0-days bypass | CrowdStrike Falcon (enterprise EDR) |
