# System Security Plan — Assessment, Authorization, and Monitoring (CA) Family

## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** This SSP would halt a FedRAMP authorization in its tracks.
> CA-2 with no independent assessor and CA-7 with no monitoring strategy are
> not missing details — they are missing the controls entirely.

---

**System Name:** Links-Matrix
**Prepared By:** IT Department
**Date:** TBD
**Status:** Draft

---

## CA-2 — Control Assessments

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

We perform security assessments of our system. The security team reviews controls
periodically to make sure they are working correctly. Assessment results are reviewed
by management and any issues are addressed. We maintain documentation of our
security posture.

We conduct assessments according to our security policy and update the documentation
as needed.

**Responsible Role:** Security Team / Management

**Parameters:** Periodically

**Evidence / Artifacts:** Assessment records, security documentation

**Enhancements Addressed:** None

---

## CA-7 — Continuous Monitoring

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

We continuously monitor our systems for security issues. Our monitoring tools alert
the security team when something unusual is detected. We use cloud security tools
to track the health of our environment.

The security team reviews monitoring results and takes action when needed. We are
working on improving our continuous monitoring capabilities.

**Responsible Role:** Security Team

**Parameters:** Ongoing

**Evidence / Artifacts:** Monitoring tool dashboards, alert logs

**Enhancements Addressed:** Some monitoring is automated

---

## What Makes This BAD — Examiner's Red Flags

| Control | Problem |
| ------- | ------- |
| CA-2 | "The security team reviews controls" — this is self-assessment, not independent assessment. FedRAMP requires a 3PAO. No assessor named. No assessment plan referenced. No report produced. No POA&M mentioned. "Periodically" is not a frequency. |
| CA-2 | No penetration testing mentioned. No assessment scope defined. No evidence the full control baseline was covered. This would fail a FedRAMP readiness review before the first question is asked. |
| CA-7 | "Working on improving" is a POA&M entry, not an SSP statement. No continuous monitoring strategy document. No metrics defined. No reporting cadence. No link to POA&M or risk register. |
| CA-7 | "Cloud security tools" — which tools? What rules? What thresholds? "Alert the security team" — via what mechanism? Reviewed how often? This describes a wish, not an implementation. |
| Both | No connection between the two controls. CA-2 assessments should feed CA-7 metrics. CA-7 findings should feed the POA&M that CA-2 tracks. Neither is connected to anything. |
