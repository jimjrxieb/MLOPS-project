# System Security Plan — Configuration Management (CM) Family

## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** This SSP describes a configuration management program that exists
> only on paper. The five controls form a chain — baseline, change control, settings,
> least functionality, inventory. Every link here is broken.

---

**System Name:** Links-Matrix
**Prepared By:** IT Department
**Date:** TBD
**Status:** Draft

---

## CM-2 — Baseline Configuration

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

We maintain a documented baseline configuration for our systems. The configuration
is reviewed periodically and updated when changes are made. Our baseline reflects
the current approved state of the system.

The platform team manages the baseline and ensures that systems are configured
according to our security standards.

**Responsible Role:** Platform Team

**Parameters:** Periodically

**Evidence / Artifacts:** System configuration documentation

**Enhancements Addressed:** None

---

## CM-3 — Configuration Change Control

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

Changes to the system configuration go through a review process before being
implemented in production. The team reviews proposed changes for security impact.
Approved changes are documented and tracked.

We have a change management process that ensures changes are properly reviewed
and approved before deployment.

**Responsible Role:** Platform Team / Management

**Parameters:** Before implementation

**Evidence / Artifacts:** Change records, approval documentation

**Enhancements Addressed:** None

---

## CM-6 — Configuration Settings

**Implementation Status:** Partially Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

Security configuration settings are applied to our systems. We follow best practices
for configuring our Kubernetes cluster and cloud environment. Some security policies
are deployed to enforce configuration requirements.

We are working on improving our configuration enforcement capabilities.

**Responsible Role:** Platform Team / Security Team

**Parameters:** As required

**Evidence / Artifacts:** Configuration settings documentation, policy definitions

**Enhancements Addressed:** Some automation is in place

---

## CM-7 — Least Functionality

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

Our systems are configured to run only the services and functions that are needed.
Unnecessary services are disabled. We review our systems periodically to identify
and remove functionality that is no longer required.

**Responsible Role:** Platform Team

**Parameters:** Periodically

**Evidence / Artifacts:** Service configuration, system reviews

**Enhancements Addressed:** None

---

## CM-8 — System Component Inventory

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

We maintain an inventory of system components. The inventory is updated when
components are added or removed. The inventory is reviewed periodically to ensure
accuracy.

**Responsible Role:** IT / Platform Team

**Parameters:** Periodically

**Evidence / Artifacts:** Component inventory document

**Enhancements Addressed:** None

---

## What Makes This BAD — Examiner's Red Flags

| Control | Problem |
| ------- | ------- |
| CM-2 | "Reviewed periodically" — no frequency, no version control mentioned, no CIS Benchmark cited, no review records. "System configuration documentation" is not a baseline — it is an undefined artifact. No ArgoCD, no GitOps, no way to detect drift. |
| CM-3 | "A review process" — which process? Who reviews? What constitutes approval? No pipeline, no branch protection, no required status checks. Changes could be applied by anyone with kubectl access and this SSP would still technically say "changes are reviewed." |
| CM-6 | "Partially Implemented" with "working on improving" is a POA&M entry, not an SSP statement. "Some policies are deployed" — which policies? In Enforce or Audit mode? "As required" is not a parameter. |
| CM-7 | "Reviewed periodically" with no frequency means never. No NetworkPolicy. No image registry restriction. No port scan results. "Unnecessary services are disabled" with zero evidence means this is a hope, not a control. |
| CM-8 | "Component inventory document" — is it a spreadsheet? When was it last updated? No automated discovery. No SBOM. No unauthorized component detection. If a rogue container is running in production, this SSP provides no mechanism to find it. |
| Chain | The CM chain (CM-2 → CM-3 → CM-6 → CM-7 → CM-8) is never acknowledged. There is no connection between the documented baseline (CM-2), the change process that maintains it (CM-3), the settings that enforce it (CM-6), the functionality that scopes it (CM-7), and the inventory that accounts for it (CM-8). These five controls read as unrelated checkboxes. |
