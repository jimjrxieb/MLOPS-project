# System Security Plan — Audit and Accountability (AU) Family

## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** This SSP would receive "Insufficient" ratings on every AU control
> from a 3PAO. The core problem: it describes intent, not implementation. Logs may or
> may not exist — there is no way to tell from this document.

---

**System Name:** Links-Matrix
**Prepared By:** IT Department
**Date:** TBD
**Status:** Draft

---

## AU-2 — Event Logging

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The organization logs important system events. We have logging enabled across our systems
to capture relevant security events. Our logging configuration captures what is needed
to support security investigations.

We review our logging configuration periodically and update it when needed. The security
team is responsible for ensuring appropriate events are being logged.

**Responsible Role:** IT / Security Team

**Parameters:** Periodically, as needed

**Evidence / Artifacts:** Logging configuration, security policy

**Enhancements Addressed:** None

---

## AU-3 — Content of Audit Records

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

Our audit records contain the information needed to understand what happened. Logs include
relevant details about events including timestamps and user information. We capture enough
information to support incident investigations.

**Responsible Role:** IT

**Parameters:** N/A

**Evidence / Artifacts:** Sample log entries

**Enhancements Addressed:** None

---

## AU-6 — Audit Record Review, Analysis, and Reporting

**Implementation Status:** Partially Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The security team reviews logs when there is a security concern. We have monitoring tools
in place to help identify unusual activity. Findings are reported to management as appropriate.

We are working on improving our log review process and plan to implement more automated
monitoring in the future.

**Responsible Role:** Security Team / Management

**Parameters:** As needed, periodically

**Evidence / Artifacts:** Monitoring tool configuration, incident reports

**Enhancements Addressed:** We use some automated tooling

---

## AU-7 — Audit Record Reduction and Report Generation

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

We can generate reports from our audit logs. The security team has the ability to query
logs and produce reports when needed. Log reduction tools are available to help process
large volumes of log data.

**Responsible Role:** IT / Security Team

**Parameters:** On demand

**Evidence / Artifacts:** Reporting tool, log queries

**Enhancements Addressed:** Automated processing is available

---

## AU-9 — Protection of Audit Information

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

Audit logs are protected from unauthorized access. Access to logs is restricted to
authorized personnel. We have controls in place to prevent log tampering.

Logs are stored securely and backed up regularly.

**Responsible Role:** IT

**Parameters:** N/A

**Evidence / Artifacts:** Access control policy, backup configuration

**Enhancements Addressed:** Some enhancements are implemented

---

## AU-12 — Audit Record Generation

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The system generates audit records for security-relevant events. Audit record generation
is configured across our system components. Records are generated in accordance with
our logging requirements.

**Responsible Role:** IT / Platform Team

**Parameters:** N/A

**Evidence / Artifacts:** System logging configuration

**Enhancements Addressed:** None

---

## What Makes This BAD — Examiner's Red Flags

| Control | Problem |
| ------- | ------- |
| AU-2 | No event list exists. "Important system events" is meaningless. Zero specificity on categories (auth, privilege use, data access, config change). No K8s audit policy mentioned. "Periodically" is not a review schedule. |
| AU-3 | "Relevant details" and "enough information" are circular. No fields named. An auditor cannot verify this without guessing what to look for. |
| AU-6 | "When there is a security concern" means no proactive review. "Plan to implement" with no date is a POA&M item dressed as an SSP statement. No SIEM named. No cadence defined. |
| AU-7 | "Reports are available" with no tool named, no immutability mention, no separation between read and write access to log storage. Can the reporting tool delete logs? Unknown. |
| AU-9 | "Stored securely" is not a control. Logs stored on the same system being audited. No S3 Object Lock, no separate account, no alert on log deletion. "Some enhancements are implemented" is the laziest possible response. |
| AU-12 | No coverage verification. No NTP config. No mention of whether all regions or all cluster nodes are covered. Could have a 40% event gap and this SSP would still read the same. |
| All | The AU control chain (AU-2 → AU-3 → AU-12 → AU-6 → AU-7) is never acknowledged. No control depends on any other in this document. That is architecturally incoherent for a logging program. |
