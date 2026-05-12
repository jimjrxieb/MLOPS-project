# System Security Plan — Incident Response (IR) Family

## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** The two most dangerous words in incident response are "we have
> a plan." Having a plan document and being able to execute incident response are
> completely different capabilities. This SSP demonstrates the former while providing
> zero evidence of the latter.

---

**System Name:** Links-Matrix
**Prepared By:** IT Department
**Date:** TBD
**Status:** Draft

---

## IR-4 — Incident Handling

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The organization has incident handling procedures in place. When an incident is
detected, the security team is notified and responds according to our incident
response procedures. Incidents are contained, investigated, and resolved. Lessons
learned are incorporated into future procedures.

We have tools in place to detect and respond to incidents and our team is trained
on incident response procedures.

**Responsible Role:** Security Team / Management

**Parameters:** As incidents occur

**Evidence / Artifacts:** Incident response procedures, incident logs

**Enhancements Addressed:** None

---

## IR-8 — Incident Response Plan

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

We have a documented incident response plan. The plan describes our approach to
incident response and the roles and responsibilities of the team. The plan is reviewed
periodically and updated as needed. Personnel with incident response responsibilities
are familiar with the plan.

**Responsible Role:** Security Team / Management

**Parameters:** Annually

**Evidence / Artifacts:** Incident response plan document

**Enhancements Addressed:** Breach notification is addressed in the plan

---

## What Makes This BAD — Examiner's Red Flags

| Control | Problem |
| ------- | ------- |
| IR-4 | "The security team is notified" — by what mechanism? PagerDuty? Email? Phone tree? "Responds according to procedures" — which procedures? Where are they? This statement is true whether or not an incident has ever been handled successfully. |
| IR-4 | No containment runbook. No automated containment capability. No incident ticket history. "Lessons learned are incorporated" — from which incidents, when, resulting in what specific changes? |
| IR-8 | "Reviewed periodically" and "personnel are familiar" are both unverifiable claims. No approval date, no approver name, no distribution records. A plan that no one has signed, distributed, or tested is a draft, not a program. |
| IR-8 | "Breach notification is addressed in the plan" — what are the timelines? Who initiates? Which regulators are notified? Without specifics, this statement provides zero assurance that a regulatory notification deadline would be met during an actual breach. |
| Both | IR-4 (execution) and IR-8 (plan) never reference each other. A response team that cannot point to their plan, and a plan that has no evidence of execution, are individually meaningless. |
