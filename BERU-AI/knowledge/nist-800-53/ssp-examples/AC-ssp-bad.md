# System Security Plan — Access Control (AC) Family

## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** This SSP would fail a FedRAMP readiness review and likely generate
> 15+ "Insufficient" ratings from a 3PAO. It reads like someone filled it out to check a box.

---

**System Name:** Links-Matrix
**Prepared By:** IT Department
**Date:** TBD
**Status:** Draft

---

## AC-2 — Account Management

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

We have an account management policy. Users are given access to the system when they need it and
access is removed when they leave the company. We try to review accounts periodically to make sure
they are still valid. Service accounts are created when applications need them.

The IT team manages all accounts and ensures that users have the appropriate level of access.
We follow least privilege principles and make sure accounts are managed properly throughout
their lifecycle.

**Responsible Role:** IT

**Parameters:** As needed, periodically

**Evidence / Artifacts:** Access control policy document, account list

**Enhancements Addressed:** None

---

## AC-3 — Access Enforcement

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The system enforces access control. Users can only access what they are allowed to access.
We use role-based access control to manage permissions. The system will deny access to
unauthorized users.

Access is configured in the system and enforced by the application. We have policies in place
to ensure that only authorized users can access sensitive information.

**Responsible Role:** IT / Development Team

**Parameters:** N/A

**Evidence / Artifacts:** System configuration, access control settings

**Enhancements Addressed:** None

---

## AC-5 — Separation of Duties

**Implementation Status:** Partially Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

We try to separate duties where possible. Not one person should be able to do everything.
We have different roles for different people. The development team and operations team have
different responsibilities.

We are working on improving our separation of duties practices and plan to implement additional
controls in the future.

**Responsible Role:** Management

**Parameters:** As appropriate

**Evidence / Artifacts:** Org chart

**Enhancements Addressed:** N/A

---

## AC-6 — Least Privilege

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

We follow least privilege. Users and systems are only given the access they need to do their
jobs. We review permissions regularly and remove access that is no longer needed.

Our cloud environment uses IAM and we make sure that permissions are appropriate. Kubernetes
RBAC is configured to limit access.

**Responsible Role:** IT / Cloud Team

**Parameters:** Regular review

**Evidence / Artifacts:** IAM policies, RBAC configuration

**Enhancements Addressed:** Some enhancements are implemented as applicable

---

## AC-17 — Remote Access

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

Remote access to the system is controlled. Employees use a VPN to connect to corporate
resources remotely. We require authentication before allowing access. Remote sessions are
monitored.

We have policies about remote access and employees are expected to follow them. Encryption
is used to protect data in transit.

**Responsible Role:** IT

**Parameters:** TBD

**Evidence / Artifacts:** VPN logs, remote access policy

**Enhancements Addressed:** Encryption is used

---

## What Makes This BAD — Examiner's Red Flags

| Control | Problem |
| ------- | ------- |
| AC-2 | "Periodically" — no defined interval. No mention of quarterly reviews, automation, or offboarding SLA. Service accounts described in one sentence with no inventory or owner requirement. |
| AC-3 | "Users can only access what they are allowed to" — restates the control requirement, says nothing about HOW enforcement is implemented. No technology named. |
| AC-5 | "We try to separate duties" — this is not an implementation statement. "Plan to implement" with no date or POA&M is a finding. Org chart does not prove SoD. |
| AC-6 | "Regular review" as a parameter value fails — NIST requires a defined period. "Some enhancements are implemented as applicable" would get a 3PAO laughing at you. |
| AC-17 | "TBD" parameters in an SSP means the control is not implemented. No MFA mentioned. No session logging specifics. "VPN" named but no technology, no config reference. |
| All | No evidence artifacts that an auditor could actually request and verify. No test procedures. No control origination documented properly. Missing OSCAL-required fields throughout. |
