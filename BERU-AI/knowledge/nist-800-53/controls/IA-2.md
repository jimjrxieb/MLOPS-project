---
family: IA
family_name: Identification and Authentication
id: IA-2
name: Multi-Factor Authentication
---

question: "Is every privileged login backed by more than one factor?"

description: >
  The information system uniquely identifies and authenticates organizational users (or processes
  acting on behalf of users). At moderate baseline, MFA is required for all network access to
  privileged accounts and all network access to non-privileged accounts. A password alone is
  not sufficient authentication for any system-level access. This control applies to human
  users; IA-3 covers device-to-device authentication.

enhancements:
  - id: IA-2(1)
    name: Multi-Factor Authentication to Privileged Accounts
    description: >
      The information system implements multi-factor authentication for network access to
      privileged accounts. Privileged accounts (admin, root, cluster-admin, break-glass)
      must always require a second factor regardless of network location.
  - id: IA-2(2)
    name: Multi-Factor Authentication to Non-Privileged Accounts
    description: >
      The information system implements multi-factor authentication for network access to
      non-privileged accounts. MFA is not optional for standard users accessing the system
      remotely — phishing-resistant MFA preferred (FIDO2/WebAuthn over SMS/TOTP).
  - id: IA-2(8)
    name: Access to Accounts — Replay Resistant
    description: >
      The information system implements replay-resistant authentication mechanisms for
      network access to privileged accounts. Hardware tokens or FIDO2 satisfy this;
      static OTPs shared over SMS do not.
  - id: IA-2(12)
    name: Acceptance of PIV Credentials
    description: >
      The information system accepts and electronically verifies Personal Identity Verification
      (PIV) credentials. Required for federal environments; satisfies the phishing-resistant
      MFA mandate under OMB M-22-09.

HITRUST_map:
  - "01.d — User Access Management"
  - "01.f — Password Policy"
  - "01.r — Password Management System"
  - "09.ab — Monitoring System Use"

evidence:
  what_to_look_for:
    - MFA enrollment records showing 100% coverage for privileged accounts
    - MFA enforcement policy (Conditional Access, SCP, or IdP policy) — not just availability, enforcement
    - Authentication logs showing second-factor challenges on every login
    - Policy documentation listing approved MFA methods and prohibited methods (e.g., SMS discouraged)
    - Break-glass account configuration — MFA still enforced, usage alerted
  ask_for:
    - "Show me the Conditional Access or IdP policy that enforces MFA — is there any bypass condition or exclusion?"
    - "Show me an authentication log entry for a privileged account login — does it show second-factor challenge?"
    - "Show me how cluster API server access is authenticated — can a user authenticate with a static kubeconfig token alone?"
    - "Show me your break-glass account procedure — does MFA still apply, and how is use alerted?"
  tools:
    generic:
      - OIDC provider configuration (Dex, Keycloak, Okta — verify MFA policy applied)
      - kubectl config view (check if static token auth is in use — should not be)
      - auditd / kube-apiserver audit log (Authentication events)
    aws:
      - IAM MFA enforcement (aws iam list-virtual-mfa-devices, check users without MFA)
      - AWS Config (rule: mfa-enabled-for-iam-console-access, root-account-mfa-enabled)
      - CloudTrail (ConsoleLogin events — verify mfaAuthenticated field is true)
      - AWS SSO / Identity Center (enforce MFA at IdP level)
    microsoft:
      - Entra ID Conditional Access (require MFA policy — verify no exclusions for privileged roles)
      - Entra ID Sign-in Logs (filter by MFA status)
      - Microsoft Authenticator / FIDO2 security key registration report
      - Azure AD Identity Protection (risky sign-in detections)

failure_to_implement:
  - Password-only authentication means a single phished or breached credential grants full system access.
  - MFA available but not enforced — users opt out, privileged accounts remain single-factor.
  - SMS-based OTP is trivially bypassable via SIM swap — fails phishing-resistant MFA requirements.
  - Static kubeconfig tokens shared among team members cannot be individually revoked or attributed.
  - Federal systems without PIV acceptance fail OMB M-22-09 and FedRAMP High MFA requirements.

related:
  - IA-3
  - IA-4
  - IA-5
  - AC-17

chain: null
