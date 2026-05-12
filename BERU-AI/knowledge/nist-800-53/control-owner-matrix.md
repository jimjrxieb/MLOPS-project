# NIST 800-53 Control Owner Matrix

**Scope:** Links-Matrix control inventory (39 controls)
**Last Updated:** 2026-05-01

Maps every control to the role accountable for it, the team that implements it,
and the team that produces the audit evidence. Use this during assessments to
know who to interview and whose artifacts to request.

---

## Role Definitions

| Role | Abbreviation | Responsibility |
|------|-------------|----------------|
| Information System Security Officer | ISSO | Policy owner, authorization, POA&M, SSP |
| System Owner | SO | Business accountability, risk acceptance sign-off |
| CISO | CISO | Oversight, escalation authority, B/S rank decisions |
| Security Engineer | SecEng | Detection rules, vulnerability scanning, security tooling |
| Cloud Security Engineer | CloudSec | Cloud IAM, KMS, Config rules, Security Hub |
| Platform Engineer | PlatEng | K8s, GitOps, CI/CD, infrastructure controls |
| DevSecOps Engineer | DevSecOps | Pipeline security, image signing, SAST, SCA |
| IT Operations | ITOps | Identity provisioning, patch management, account lifecycle |
| Security Operations (SOC) | SOC | Alert triage, monitoring, threat hunting |
| Incident Response Team | IRT | Incident handling, containment, forensics |
| Application Developer | AppDev | Code-level encryption, application security controls |
| Compliance Officer | CompO | Assessment coordination, evidence packaging, audit liaison |

---

## Matrix

**Columns:**
- **Primary Owner** — Accountable. Answers to the auditor. Signs the evidence.
- **Implementation Owner** — Responsible. Builds and maintains the control.
- **Evidence Producer** — Generates the artifacts the auditor will request.
- **Cadence** — How often the control is verified or reviewed.

---

### AC — Access Control

| Control | Name | Primary Owner | Implementation Owner | Evidence Producer | Cadence |
|---------|------|--------------|---------------------|-------------------|---------|
| AC-2 | Account Management | ISSO | ITOps | ITOps | Quarterly access review |
| AC-3 | Access Enforcement | PlatEng | PlatEng | PlatEng / SecEng | Continuous (policy-as-code) |
| AC-5 | Separation of Duties | ISSO | PlatEng / ITOps | CompO | Annual + change-triggered |
| AC-6 | Least Privilege | CloudSec | CloudSec / PlatEng | CloudSec | Quarterly access review |
| AC-17 | Remote Access | PlatEng | PlatEng / ITOps | SecEng | Annual + change-triggered |

---

### IA — Identification and Authentication

| Control | Name | Primary Owner | Implementation Owner | Evidence Producer | Cadence |
|---------|------|--------------|---------------------|-------------------|---------|
| IA-2 | Multi-Factor Authentication | ITOps | ITOps / CloudSec | ITOps | Continuous (IdP policy enforcement) |
| IA-3 | Device Identification and Authentication | PlatEng | PlatEng | PlatEng | Continuous (mTLS / workload identity) |
| IA-4 | Identifier Management | ISSO | ITOps | ITOps | Quarterly identifier review |
| IA-5 | Authenticator Management | ITOps | ITOps / DevSecOps | ITOps / SecEng | Continuous + rotation schedule |

---

### AU — Audit and Accountability

| Control | Name | Primary Owner | Implementation Owner | Evidence Producer | Cadence |
|---------|------|--------------|---------------------|-------------------|---------|
| AU-2 | Event Logging | ISSO | PlatEng | SecEng | Annual review + change-triggered |
| AU-3 | Content of Audit Records | PlatEng | PlatEng | PlatEng | Continuous (log pipeline) |
| AU-6 | Audit Record Review, Analysis, and Reporting | SOC | SOC | SOC | Continuous (SIEM); monthly report |
| AU-7 | Audit Record Reduction and Report Generation | SOC | PlatEng / SOC | SOC | On-demand + scheduled reports |
| AU-9 | Protection of Audit Information | PlatEng | PlatEng / CloudSec | PlatEng | Continuous (immutability config) |
| AU-12 | Audit Record Generation | PlatEng | PlatEng | PlatEng | Continuous (pipeline health) |

---

### CM — Configuration Management

| Control | Name | Primary Owner | Implementation Owner | Evidence Producer | Cadence |
|---------|------|--------------|---------------------|-------------------|---------|
| CM-2 | Baseline Configuration | PlatEng | PlatEng | PlatEng | Annual review + change-triggered |
| CM-3 | Configuration Change Control | PlatEng | PlatEng / DevSecOps | PlatEng | Continuous (PR / pipeline gate) |
| CM-6 | Configuration Settings | SecEng | PlatEng / SecEng | PlatEng | Continuous (policy-as-code) |
| CM-7 | Least Functionality | PlatEng | PlatEng | SecEng | Quarterly review |
| CM-8 | System Component Inventory | PlatEng | PlatEng | PlatEng | Continuous (automated discovery) |

---

### SC — System and Communications Protection

| Control | Name | Primary Owner | Implementation Owner | Evidence Producer | Cadence |
|---------|------|--------------|---------------------|-------------------|---------|
| SC-7 | Boundary Protection | PlatEng | PlatEng / CloudSec | SecEng | Continuous (network policy enforcement) |
| SC-8 | Transmission Confidentiality and Integrity | PlatEng | PlatEng / AppDev | PlatEng | Continuous (TLS config); annual cert audit |
| SC-12 | Cryptographic Key Management | CloudSec | CloudSec | CloudSec | Continuous (rotation schedule) |
| SC-13 | Cryptographic Protection | SecEng | PlatEng / SecEng | SecEng | Annual cipher suite audit |
| SC-28 | Protection of Information at Rest | CloudSec | CloudSec / PlatEng | CloudSec | Continuous (encryption config) |

---

### SI — System and Information Integrity

| Control | Name | Primary Owner | Implementation Owner | Evidence Producer | Cadence |
|---------|------|--------------|---------------------|-------------------|---------|
| SI-2 | Flaw Remediation | SecEng | DevSecOps / PlatEng | SecEng | Continuous (scanner); SLA-tracked |
| SI-3 | Malicious Code Protection | SecEng | SecEng / PlatEng | SecEng | Continuous (runtime detection) |
| SI-4 | System Monitoring | SOC | SOC / PlatEng | SOC | Continuous (SIEM); monthly report |
| SI-7 | Software, Firmware, and Information Integrity | DevSecOps | DevSecOps / PlatEng | DevSecOps | Continuous (signing / admission) |

---

### RA — Risk Assessment

| Control | Name | Primary Owner | Implementation Owner | Evidence Producer | Cadence |
|---------|------|--------------|---------------------|-------------------|---------|
| RA-3 | Risk Assessment | ISSO | ISSO / CompO | ISSO | Annual + significant change |
| RA-5 | Vulnerability Monitoring and Scanning | SecEng | SecEng / DevSecOps | SecEng | Continuous (scanner); monthly report |
| RA-7 | Risk Response | ISSO | ISSO / SO | ISSO / CompO | Ongoing (POA&M tracking) |

---

### CA — Assessment, Authorization, and Monitoring

| Control | Name | Primary Owner | Implementation Owner | Evidence Producer | Cadence |
|---------|------|--------------|---------------------|-------------------|---------|
| CA-2 | Control Assessments | ISSO | ISSO / CompO / 3PAO | CompO | Annual (FedRAMP); event-triggered |
| CA-7 | Continuous Monitoring | ISSO | SecEng / PlatEng | ISSO / SecEng | Continuous; monthly report to AO |

---

### PL — Planning

| Control | Name | Primary Owner | Implementation Owner | Evidence Producer | Cadence |
|---------|------|--------------|---------------------|-------------------|---------|
| PL-2 | System Security and Privacy Plans | ISSO | ISSO / SO | ISSO | Annual review + change-triggered |

---

### IR — Incident Response

| Control | Name | Primary Owner | Implementation Owner | Evidence Producer | Cadence |
|---------|------|--------------|---------------------|-------------------|---------|
| IR-4 | Incident Handling | IRT | IRT / SOC | IRT | Per-incident; annual tabletop |
| IR-8 | Incident Response Plan | ISSO | ISSO / IRT | ISSO | Annual review + tabletop |

---

### CP — Contingency Planning

| Control | Name | Primary Owner | Implementation Owner | Evidence Producer | Cadence |
|---------|------|--------------|---------------------|-------------------|---------|
| CP-9 | System Backup | PlatEng | PlatEng / ITOps | PlatEng | Continuous (job monitoring); quarterly restore test |
| CP-10 | System Recovery and Reconstitution | PlatEng | PlatEng / ITOps | PlatEng / ISSO | Annual recovery test |

---

## Ownership Concentration Summary

Who owns the most controls — and where are the single points of accountability risk.

| Role | Controls Owned (Primary) |
|------|--------------------------|
| ISSO | AC-5, AU-2, IA-4, RA-3, RA-7, CA-2, CA-7, PL-2, IR-8 — **9** |
| Platform Engineer | AC-3, AC-17, AU-3, AU-9, AU-12, CM-2, CM-3, CM-7, CM-8, SC-7, SC-8, CP-9, CP-10 — **13** |
| Security Engineer | CM-6, SC-13, SI-2, SI-3, RA-5 — **5** |
| Cloud Security Engineer | AC-6, SC-12, SC-28 — **3** |
| IT Operations | IA-2, IA-5 — **2** |
| SOC | AU-6, AU-7, SI-4 — **3** |
| DevSecOps Engineer | SI-7 — **1** |
| Incident Response Team | IR-4 — **1** |

> **Note:** Platform Engineer carries the highest primary ownership concentration (13 controls).
> In small teams this is expected — in larger engagements, split Cloud Security and
> K8s Platform into separate ownership lanes to reduce single-point-of-failure risk.
