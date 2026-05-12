# NIST 800-53 — Links-Matrix Table of Contents

A GRC/3PAO-oriented reference. Controls organized by the question an auditor is actually trying to answer.

---

## 1. Who can do what?

> Are identities real, scoped, and enforced?

### AC — Access Control

- AC-2: Account Management
- AC-3: Access Enforcement
- AC-5: Separation of Duties
- AC-6: Least Privilege
- AC-17: Remote Access

### IA — Identification and Authentication

- IA-2: Multi-Factor Authentication
- IA-3: Device Identification and Authentication
- IA-4: Identifier Management
- IA-5: Authenticator Management

> K8s tie-in: RBAC, Service Accounts, OIDC

---

## 2. What happened?

> Is there a complete, tamper-evident record of system activity?

### AU — Audit and Accountability

- AU-2: Event Logging
- AU-3: Content of Audit Records
- AU-6: Audit Record Review, Analysis, and Reporting
- AU-7: Audit Record Reduction and Report Generation
- AU-9: Protection of Audit Information
- AU-12: Audit Record Generation

> Chain: AU-2 → AU-3 → AU-12 → AU-6 → AU-7
>
> Distinction: AU = logging | SI = threat detection

---

## 3. Is the system what we said it is?

> Is the configuration baseline documented, enforced, and drift-free?

### CM — Configuration Management and Hardening

- CM-2: Baseline Configuration
- CM-3: Configuration Change Control
- CM-6: Configuration Settings
- CM-7: Least Functionality
- CM-8: System Component Inventory

> K8s tie-in: Kyverno, OPA/Gatekeeper, CIS Benchmarks, Trivy

---

## 4. Is the data protected?

> Is data encrypted in transit and at rest, and are boundaries enforced?

### SC — System and Communications Protection

- SC-7: Boundary Protection
- SC-8: Transmission Confidentiality and Integrity
- SC-12: Cryptographic Key Establishment and Management
- SC-13: Cryptographic Protection
- SC-28: Protection of Information at Rest

> K8s tie-in: NetworkPolicy, TLS, Sealed Secrets, KMS

---

## 5. Are we detecting bad behavior?

> Is the system actively identifying threats, not just logging them?

### SI — System and Information Integrity

- SI-2: Flaw Remediation
- SI-3: Malicious Code Protection
- SI-4: System Monitoring
- SI-7: Software, Firmware, and Information Integrity

> Distinction: AU = logging | SI = threat detection
>
> K8s tie-in: Falco, Trivy, image signing (cosign), admission control

---

## 6. What's weak?

> Have risks been identified, scored, and actively tracked?

### RA — Risk Assessment

- RA-3: Risk Assessment
- RA-5: Vulnerability Monitoring and Scanning
- RA-7: Risk Response

> K8s tie-in: Trivy, kube-bench, DAST/SAST pipelines

---

## 7. Are controls still working over time?

> Is there continuous evidence that security posture is maintained?

### CA — Assessment, Authorization, and Monitoring

- CA-2: Control Assessments
- CA-7: Continuous Monitoring

### PL — Planning

- PL-2: System Security and Privacy Plans

---

## 8. What do we do when it breaks?

> Is there a tested, documented plan for incidents and recovery?

### IR — Incident Response

- IR-4: Incident Handling
- IR-8: Incident Response Plan

### CP — Contingency Planning

- CP-9: System Backup
- CP-10: System Recovery and Reconstitution

---

## Control Count

| # | Question | Families | Controls |
| --- | --- | --- | --- |
| 1 | Who can do what? | AC, IA | 9 |
| 2 | What happened? | AU | 6 |
| 3 | Is the system what we said it is? | CM | 5 |
| 4 | Is the data protected? | SC | 5 |
| 5 | Are we detecting bad behavior? | SI | 4 |
| 6 | What's weak? | RA | 3 |
| 7 | Are controls still working over time? | CA, PL | 3 |
| 8 | What do we do when it breaks? | IR, CP | 4 |
| | **Total** | | **39** |
