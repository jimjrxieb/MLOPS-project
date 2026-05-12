# System Security Plan — Planning (PL) Family

## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** PL-2 is a meta-control — the SSP must describe itself accurately.
> This SSP fails at the most fundamental level: it is a draft that no one has signed,
> describes a system that no longer matches what is deployed, and cannot serve as the
> basis for any authorization decision. This is worse than having no SSP because it
> gives auditors a false picture.

---

**System Name:** Links-Matrix
**Prepared By:** IT Department
**Date:** TBD
**Status:** Draft

---

## PL-2 — System Security and Privacy Plans

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The organization has a System Security Plan (SSP) that documents the security controls
in place for the Links-Matrix system. The SSP describes the system and its security
requirements and is updated as needed. The SSP has been reviewed by the security team
and is available to authorized personnel.

The SSP includes a description of the system boundary, the information types processed,
and the controls that are implemented to protect the system. The document is reviewed
periodically and updated when significant changes occur.

**Responsible Role:** Security Team / Management

**Parameters:** Reviewed annually

**Evidence / Artifacts:** System Security Plan document

**Enhancements Addressed:** The SSP coordinates security activities with other teams
as needed.

---

## What Makes This BAD — Examiner's Red Flags

| Control | Problem |
| ------- | ------- |
| PL-2 | "Implemented" status with no AO signature, no approval date, no approver name. A draft SSP is not an approved plan. No authorization can be granted on an unsigned document. |
| PL-2 | "Updated as needed" — by what process? Who decides a change is significant enough to trigger an update? What is the SLA from system change to SSP update? None of these are answered. |
| PL-2 | No version number on the SSP. No version history. There is no way to know if this document reflects the system as it exists today or two years ago. |
| PL-2 | "Reviewed periodically" — when was the last review? By whom? What changed as a result? This statement is true whether the SSP was reviewed last week or three years ago. |
| PL-2 | No boundary diagram reference. A system boundary is a picture and a definition — this SSP contains neither. Assessors will find components not described in this plan. |
| PL-2(3) | "Coordinates security activities with other teams as needed" — which teams? For what activities? Under what advance notice requirement? An informal coordination statement provides zero assurance that a penetration test won't surprise a shared-infrastructure partner. |
| Both | An SSP that does not accurately describe the deployed system is not a compliance artifact — it is a liability. Auditors will compare it against the actual environment and document every discrepancy. |
