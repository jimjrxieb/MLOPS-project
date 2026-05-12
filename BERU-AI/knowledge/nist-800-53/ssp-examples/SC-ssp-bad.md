# System Security Plan — System and Communications Protection (SC) Family

## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** The SC family covers four interlocking technical controls — boundary
> protection, encryption in transit, key management, algorithm selection, and encryption
> at rest. Every one of them requires specific technical evidence, not policy statements.
> "We use encryption" is the most common bad answer in this family. It describes the
> intention, not the implementation. Assessors will ask to see cipher suites, key rotation
> records, NetworkPolicy manifests, and etcd configuration — none of which this SSP can
> produce.

---

**System Name:** Links-Matrix
**Prepared By:** IT Department
**Date:** TBD
**Status:** Draft

---

## SC-7 — Boundary Protection

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The Links-Matrix system is protected by network boundary controls including firewalls
and security groups. Traffic into and out of the system is filtered to only allow
authorized communications. The organization uses cloud security controls to protect
the system boundary. Network access is restricted to authorized users and systems.

**Responsible Role:** IT / Network Team

**Parameters:** As configured

**Evidence / Artifacts:** Network diagrams, firewall rules

**Enhancements Addressed:** The number of external connections is minimized. Network
traffic flows through managed interfaces.

---

## SC-8 — Transmission Confidentiality and Integrity

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The Links-Matrix system uses TLS/HTTPS to protect data in transit. All external
communications are encrypted. Certificates are managed and renewed to prevent expiration.

**Responsible Role:** IT / Security Team

**Parameters:** TLS encryption on all external connections

**Evidence / Artifacts:** TLS certificates, HTTPS configuration

**Enhancements Addressed:** Cryptographic protection is implemented on all transmissions.

---

## SC-12 — Cryptographic Key Establishment and Management

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

Cryptographic keys used by the Links-Matrix system are managed according to
organizational policy. Keys are stored securely and rotated on a regular basis.
Access to keys is restricted to authorized personnel.

**Responsible Role:** Security Team

**Parameters:** Keys rotated annually

**Evidence / Artifacts:** Key management policy, key rotation records

---

## SC-13 — Cryptographic Protection

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The Links-Matrix system uses approved cryptographic algorithms to protect
information. Weak or deprecated algorithms are not used in production. Cryptographic
implementations comply with applicable standards.

**Responsible Role:** Security Team

**Parameters:** NIST-approved algorithms

**Evidence / Artifacts:** Cryptographic policy, TLS configuration

---

## SC-28 — Protection of Information at Rest

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

Data stored in the Links-Matrix system is encrypted at rest. Storage encryption
is enabled for databases and file systems. Encryption keys are managed centrally.
Sensitive data is protected from unauthorized access even if physical media is
compromised.

**Responsible Role:** IT / Security Team

**Parameters:** Encryption at rest on all storage

**Evidence / Artifacts:** Encryption configuration documentation, storage settings

**Enhancements Addressed:** Cryptographic mechanisms protect data at rest using
approved algorithms.

---

## What Makes This BAD — Examiner's Red Flags

| Control | Problem |
| ------- | ------- |
| SC-7 | "Firewalls and security groups" — which security groups? What are the rules? Is there default-deny or default-allow? No NetworkPolicy is mentioned. In Kubernetes, security groups protect the node boundary but not pod-to-pod traffic. Without NetworkPolicy, a compromised pod can reach any other pod in the cluster. |
| SC-7 | No mention of VPC architecture, subnets, or DMZ separation. No egress controls described. A pod can call any external internet endpoint and this SSP provides no evidence otherwise. |
| SC-8 | "Uses TLS/HTTPS" — what TLS version? TLS 1.0 is technically TLS. What cipher suites? RC4 is technically encryption. "Certificates are renewed" — by what process, with how much lead time, monitored by whom? |
| SC-8 | No mention of service-to-service traffic inside the cluster. If all external traffic is encrypted but internal service-to-service traffic is plain HTTP, an attacker who compromises one pod sees everything in plaintext. |
| SC-12 | "Keys rotated annually" — which keys? TLS certificates have different rotation needs than encryption keys. API keys have different needs than signing keys. A single "annually" parameter applied to all key types shows no understanding of the key inventory. |
| SC-12 | No KMS or key management service named. "Stored securely" is meaningless without a specific storage mechanism. Keys in a secrets manager are not equivalent to keys in a config file. |
| SC-13 | "Approved cryptographic algorithms" — approved by whom? NIST? Internal policy? What is the list? Without a specific algorithm list, no one knows whether MD5, SHA-1, or RC4 are in use. |
| SC-28 | "Encryption at rest on all storage" — does this include Kubernetes etcd? K8s Secrets are base64-encoded in etcd by default, not encrypted. Without EncryptionConfiguration, every Secret in the cluster is readable to anyone with etcd access. |
