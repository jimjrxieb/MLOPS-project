---
family: IA
family_name: Identification and Authentication
id: IA-5
name: Authenticator Management
---

question: "Are credentials created, distributed, stored, and rotated securely — and are weak ones prohibited?"

description: >
  The organization manages information system authenticators (passwords, tokens, PKI certificates,
  biometrics, key cards) by verifying identity before issuance, establishing content and
  complexity requirements, establishing administrative procedures for initial distribution and
  lost/compromised authenticators, changing default authenticators, changing/refreshing
  authenticators on a defined schedule, and protecting authenticator content from unauthorized
  disclosure. Authenticator management is where most credential-based breaches originate —
  default passwords, hardcoded secrets, and unrotated API keys are all IA-5 failures.

enhancements:
  - id: IA-5(1)
    name: Password-Based Authentication
    description: >
      The information system enforces minimum password complexity and change requirements;
      prohibits password reuse; stores and transmits only cryptographically protected passwords;
      and enforces defined restrictions on the number of password changes per time period.
      At minimum: 15 characters, no complexity-only requirements, breach corpus checking.
  - id: IA-5(2)
    name: Public Key Infrastructure Certificates
    description: >
      The organization manages PKI certificates by issuing them from an approved trust anchor,
      including only approved trust anchors in trust stores, verifying the identity of
      certificate holders before issuance, and ensuring access to private keys is restricted
      to authorized individuals.
  - id: IA-5(6)
    name: Protection of Authenticators
    description: >
      The organization protects authenticators commensurate with the security category of
      the information to which the authenticator provides access. High-value credentials
      (prod SSH keys, signing certificates, break-glass tokens) must be stored in secrets
      management systems — not in files, environment variables, or source code.
  - id: IA-5(7)
    name: No Embedded Unencrypted Static Authenticators
    description: >
      The organization ensures unencrypted static authenticators are not embedded in
      applications or stored on function-specific information technology devices.
      Hardcoded credentials in source code or container images are an IA-5(7) violation.
  - id: IA-5(11)
    name: Hardware-Based Authentication
    description: >
      The information system uses hardware-based mechanisms for authenticating to systems
      handling high-value data. FIDO2 hardware security keys (YubiKey) satisfy this
      for privileged access scenarios.

HITRUST_map:
  - "01.a — Access Control Policy"
  - "01.f — Password Policy"
  - "01.r — Password Management System"
  - "09.ab — Monitoring System Use"
  - "10.f — Policy on the Use of Cryptographic Controls"

evidence:
  what_to_look_for:
    - Password policy configuration enforcing length, breach corpus checking, no reuse
    - Secrets management system in use (Vault, AWS Secrets Manager, Azure Key Vault) — not plaintext files
    - Rotation schedule and records for all long-lived credentials (API keys, certificates, service account tokens)
    - Secret scanning configuration in CI/CD — blocking commits with embedded credentials
    - Certificate expiry monitoring and alerting (no expired certs in production)
    - Default credential change records for all new systems and service deployments
  ask_for:
    - "Show me your secret scanning configuration in CI/CD — what happens when a credential is detected in a commit?"
    - "Show me the rotation schedule for your production API keys and service account tokens — when was each last rotated?"
    - "Show me how application secrets are delivered to pods — are they mounted from a secrets manager or baked into the image?"
    - "Show me your certificate expiry monitoring — what alerts fire before a cert expires, and what's the lead time?"
    - "Show me that default credentials have been changed on all new service deployments — is this enforced or checked manually?"
  tools:
    generic:
      - truffleHog / gitleaks (scan git history for embedded credentials)
      - detect-secrets (pre-commit hook for credential detection)
      - HashiCorp Vault (secrets management and dynamic credential generation)
      - cert-manager (K8s certificate lifecycle automation — expiry alerting)
      - kubesec / kube-score (flag secrets mounted as environment variables)
    aws:
      - AWS Secrets Manager (rotation configuration — verify automatic rotation enabled)
      - AWS Config (rule: secretsmanager-rotation-enabled-check)
      - AWS Macie (detect credentials in S3 objects)
      - CloudTrail (GetSecretValue events — detect broad secret access)
      - ACM (Certificate Manager — expiry alerting, automated renewal)
    microsoft:
      - Azure Key Vault (secrets, keys, certificates — rotation policy configuration)
      - Microsoft Defender for DevOps (secret scanning in repos and pipelines)
      - Entra ID Application Registration (client secret expiry monitoring)
      - Azure Monitor (Key Vault diagnostic logs — alert on secret access patterns)

failure_to_implement:
  - Hardcoded API key in a public GitHub repository is discovered by automated scanners within minutes of commit.
  - Unrotated service account token from a departed employee remains valid indefinitely.
  - Secrets delivered via environment variables are visible in pod specs, CI logs, and crash dumps.
  - Expired certificate causes production outage — no monitoring existed to catch the approaching expiry.
  - Default admin password never changed on a newly deployed service — trivially exploited by automated scanners.

related:
  - IA-2
  - IA-3
  - IA-4
  - SC-12
  - SC-13

chain: null
