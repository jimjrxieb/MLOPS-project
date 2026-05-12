# System Security Plan — Identification and Authentication (IA) Family

## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** This SSP has the most dangerous failure pattern in the IA family —
> controls that are available but not enforced. MFA "available" is not MFA "required."
> Secrets "managed" is not secrets "rotated." The delta between available and enforced
> is where breaches happen.

---

**System Name:** Links-Matrix
**Prepared By:** IT Department
**Date:** TBD
**Status:** Draft

---

## IA-2 — Multi-Factor Authentication

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

We require multi-factor authentication for system access. Users are required to use MFA
when logging into the system. MFA is configured in our identity provider and users
are enrolled during onboarding.

Privileged accounts also use MFA. We have procedures in place to ensure MFA is
maintained for all users.

**Responsible Role:** IT / Security Team

**Parameters:** All users

**Evidence / Artifacts:** MFA configuration, user enrollment records

**Enhancements Addressed:** MFA is enforced for privileged and non-privileged accounts

---

## IA-3 — Device Identification and Authentication

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

Devices and systems are authenticated before connecting to our environment. We use
authentication mechanisms to verify the identity of devices accessing the system.
Service-to-service communication is secured appropriately.

**Responsible Role:** Platform Team

**Parameters:** N/A

**Evidence / Artifacts:** Network configuration, authentication configuration

**Enhancements Addressed:** None

---

## IA-4 — Identifier Management

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

We manage identifiers for all users and systems. Each user has a unique identifier
and shared accounts are not permitted. Identifiers are deactivated when users leave
the organization. Service accounts are named and tracked.

**Responsible Role:** IT

**Parameters:** Identifiers deactivated upon departure

**Evidence / Artifacts:** User account list, offboarding records

**Enhancements Addressed:** None

---

## IA-5 — Authenticator Management

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

We manage credentials securely. Passwords must meet our password policy requirements.
Secrets and API keys are stored securely and not hardcoded in applications. We rotate
credentials periodically.

We have procedures to handle lost or compromised credentials.

**Responsible Role:** IT / Security Team

**Parameters:** Periodically, per policy

**Evidence / Artifacts:** Password policy, credential management procedures

**Enhancements Addressed:** Credentials are protected

---

## What Makes This BAD — Examiner's Red Flags

| Control | Problem |
| ------- | ------- |
| IA-2 | "Required" and "configured" are not "enforced." There is no reference to a Conditional Access policy, an Okta policy, or any mechanism that technically prevents login without a second factor. An auditor cannot tell if this is enforced or merely recommended. No MFA method named — SMS? TOTP? FIDO2? Matters enormously for replay-resistance. |
| IA-3 | "Secured appropriately" describes nothing. No service mesh, no IRSA, no mTLS, no OIDC workload identity mentioned. This could mean static API keys in environment variables — which is exactly what IA-3 is designed to prevent. |
| IA-4 | "Shared accounts are not permitted" is a policy statement, not a technical control. No inactivity period defined. "Deactivated upon departure" has no SLA — how quickly? No mention of identifier reuse prevention. |
| IA-5 | "Rotate credentials periodically" — no rotation schedule, no rotation mechanism, no evidence rotation actually happens. "Not hardcoded" is not enforced by any scanner named here. "Stored securely" could mean an encrypted spreadsheet. No rotation records. |
| All | The IA chain (IA-2 authenticates humans, IA-3 authenticates devices, IA-4 manages the IDs, IA-5 manages the credentials) is never acknowledged. Each control reads as if the others do not exist. |
