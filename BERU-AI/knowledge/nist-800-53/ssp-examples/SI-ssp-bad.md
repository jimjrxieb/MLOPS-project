# System Security Plan — System and Information Integrity (SI) Family

## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** SI is where security programs die quietly. An organization can have
> every upstream control — RA-5 scanning, SC-7 boundaries, CM-2 baselines — and still
> fail at the SI layer because findings pile up unpatched, runtime alerts go to /dev/null,
> and modified code runs undetected. This SSP provides comfort language for all four
> controls without demonstrating that any of them produce results an auditor can examine.
> The most dangerous sentence in SI is "the system is monitored for security events" —
> it is true of every system that has logging enabled, whether or not anyone reads it.

---

**System Name:** Links-Matrix
**Prepared By:** IT Department
**Date:** TBD
**Status:** Draft

---

## SI-2 — Flaw Remediation

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The organization identifies and remediates software and firmware vulnerabilities
in a timely manner. Critical vulnerabilities are given priority and remediated as
quickly as possible. Software updates and patches are applied following testing
to ensure they do not negatively impact system functionality. Lessons learned from
flaw remediation are incorporated into future processes.

**Responsible Role:** IT / Security Team

**Parameters:** Critical vulnerabilities remediated within 30 days

**Evidence / Artifacts:** Patch records, vulnerability scan reports

**Enhancements Addressed:** Automated tools are used to identify flaws and track
remediation status.

---

## SI-3 — Malicious Code Protection

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The Links-Matrix system employs malicious code protection mechanisms to detect and
prevent malware from entering the system. Antivirus and security scanning tools are
deployed and kept up to date. Malicious code detected by these mechanisms is contained
and removed. Security scans are performed regularly.

**Responsible Role:** Security Team

**Parameters:** Scans performed regularly; signatures updated automatically

**Evidence / Artifacts:** Security scan logs, AV configuration

**Enhancements Addressed:** Centralized management of malicious code protection.
Automatic signature updates are configured.

---

## SI-4 — System Monitoring

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The Links-Matrix system is monitored for security events and anomalous activity.
Security monitoring tools are deployed to detect unauthorized access, configuration
changes, and unusual system behavior. Alerts are generated when suspicious activity
is detected and the security team is notified. Monitoring logs are retained for
review and analysis.

**Responsible Role:** Security Team / SOC

**Parameters:** Continuous monitoring; alerts reviewed by security team

**Evidence / Artifacts:** Monitoring logs, alert configurations, SIEM records

**Enhancements Addressed:** Automated tools support real-time analysis. Inbound and
outbound traffic is monitored. Alerts are generated for potential compromises.

---

## SI-7 — Software, Firmware, and Information Integrity

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The organization employs integrity verification mechanisms to detect unauthorized
changes to software and information. Software deployed to the Links-Matrix system
is verified before installation. Unauthorized modifications to critical system files
are detected and reported. Configuration management processes ensure only authorized
software is installed.

**Responsible Role:** IT / Security Team

**Parameters:** Integrity checks performed on critical software components

**Evidence / Artifacts:** Integrity check logs, software inventory

**Enhancements Addressed:** Cryptographic protection is used to detect unauthorized
changes. Detection is integrated with the incident response process.

---

## What Makes This BAD — Examiner's Red Flags

| Control | Problem |
| ------- | ------- |
| SI-2 | "Critical vulnerabilities remediated within 30 days" — from which discovery date? Scan date? Report date? Without a tracking system with timestamps, this SLA cannot be verified. "Lessons learned are incorporated" — from which remediations? When? What changed? |
| SI-2 | Patching a base image does not remediate running containers. If the patched image is built but live pods are not restarted, the vulnerability remains active in production. This SSP has no statement about container restart practices. |
| SI-3 | "Antivirus and security scanning tools" — which tools? ClamAV? Defender? Falco? In a Kubernetes environment, traditional antivirus is largely irrelevant — container-native behavioral detection is required. "Tools are deployed" tells an assessor nothing about whether they're monitoring the right things. |
| SI-3 | "Scans performed regularly" — how regularly? Is this on every image push or quarterly? Container images ship new vulnerabilities on every build. A quarterly scan misses the entire CI/CD window. |
| SI-4 | "The security team is notified" — by what mechanism? Email? PagerDuty? Slack? A 2 AM critical alert delivered to an email inbox is not a monitoring control. Without an on-call rotation and defined acknowledgment SLA, alerts are observations, not controls. |
| SI-4 | "Monitoring logs are retained for review" — review by whom, on what schedule, at what depth? Manual log review is not real-time analysis. An attacker who moves laterally inside the cluster on a Friday afternoon is not detected until Monday's log review. |
| SI-7 | "Software deployed to the system is verified before installation" — by what mechanism? Hash check? Signed certificate? If a compromised image is pushed to ECR, what stops it from being deployed? Without cryptographic signature verification at admission, "verified" is undefined. |
| SI-7 | No mention of readOnlyRootFilesystem, image digest pinning, or runtime file integrity detection. A container with a writable filesystem can be modified after deployment — SI-7's question is whether that modification would be detected. |
