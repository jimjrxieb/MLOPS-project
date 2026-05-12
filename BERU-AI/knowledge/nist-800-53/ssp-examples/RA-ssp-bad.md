# System Security Plan — Risk Assessment (RA) Family

## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** Risk Assessment is the foundation all other security decisions build
> on. Without a credible RA-3 risk assessment, control selection is arbitrary. Without
> RA-5 scanning, vulnerabilities are invisible. Without RA-7 risk response, identified
> findings sit unresolved forever. This SSP provides evidence of none of these things —
> it documents the existence of processes without demonstrating that any of them produce
> results an auditor can examine.

---

**System Name:** Links-Matrix
**Prepared By:** IT Department
**Date:** TBD
**Status:** Draft

---

## RA-3 — Risk Assessment

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The organization conducts periodic risk assessments to identify threats and
vulnerabilities to the Links-Matrix system. Risk assessment results are documented
and used to guide security decisions. The risk assessment is reviewed and updated
as needed when significant changes occur to the system or threat environment.

**Responsible Role:** Security Team / Management

**Parameters:** Annually

**Evidence / Artifacts:** Risk assessment document

---

## RA-5 — Vulnerability Monitoring and Scanning

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The organization scans for vulnerabilities in the Links-Matrix system on a regular
basis. Vulnerability scan results are reviewed and vulnerabilities are remediated
according to their severity. Critical and high vulnerabilities are addressed in a
timely manner. Scanning tools are kept up to date.

**Responsible Role:** Security Team

**Parameters:** Quarterly scans; critical vulnerabilities remediated promptly

**Evidence / Artifacts:** Vulnerability scan reports, remediation tickets

**Enhancements Addressed:** Scans cover all system components. Authenticated scanning
is used where possible.

---

## RA-7 — Risk Response

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

When risks or vulnerabilities are identified, the security team evaluates the
findings and determines the appropriate response. Findings may be remediated,
accepted with compensating controls, or tracked for future remediation. The
organization maintains a plan of action and milestones (POA&M) to track open
items.

**Responsible Role:** Security Team / Management

**Parameters:** As findings are identified

**Evidence / Artifacts:** POA&M document, risk acceptance records

---

## What Makes This BAD — Examiner's Red Flags

| Control | Problem |
| ------- | ------- |
| RA-3 | "Conducts periodic risk assessments" — when was the last one? What methodology was used? What are the identified threats and their likelihood ratings? Without specifics, this statement describes a process that may have been performed once five years ago and never since. |
| RA-3 | No risk register reference. A risk assessment without a risk register produces a report that no one can act on. Findings are not tracked, not owned, and not treated. |
| RA-5 | "Quarterly scans" is a quarterly point-in-time posture. A CVE published the day after a scan goes undetected for up to 90 days. No mention of continuous scanning, ECR image scanning, or IaC scanning. |
| RA-5 | "Remediates according to severity" and "addressed in a timely manner" are unverifiable. What are the SLAs? 15 days? 90 days? Never? Without a defined SLA and evidence of compliance, this statement means nothing. |
| RA-5 | "Authenticated scanning is used where possible" — where is it not used? What is excluded? An unauthenticated scan of a Kubernetes cluster finds a fraction of the vulnerabilities an authenticated scan would find. |
| RA-7 | "Findings may be remediated, accepted, or tracked" — by whom, at what authority level, with what sign-off? Verbal risk acceptance is not risk acceptance. After an incident, every executive will deny knowing the risk was accepted. |
| RA-7 | POA&M is listed as an artifact but no version, date, or content is described. A POA&M with perpetually "in progress" items and no updated target dates is a compliance checkbox, not a risk management tool. |
