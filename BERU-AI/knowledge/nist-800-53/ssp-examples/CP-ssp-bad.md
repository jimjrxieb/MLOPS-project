# System Security Plan — Contingency Planning (CP) Family

## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** This SSP represents one of the most dangerous failure modes
> in security compliance — controls that look implemented on paper but have never
> been verified to work. A backup that has never been restored is not a backup.
> An RTO that has never been tested is a guess.

---

**System Name:** Links-Matrix
**Prepared By:** IT Department
**Date:** TBD
**Status:** Draft

---

## CP-9 — System Backup

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

We perform regular backups of our system data. Backups are stored securely and
retained according to our backup policy. The platform team manages backup
configuration and ensures that data is protected.

Backups are encrypted and stored off-site. We have procedures in place to restore
data if needed.

**Responsible Role:** Platform Team / IT

**Parameters:** Regular, as required

**Evidence / Artifacts:** Backup configuration, backup logs

**Enhancements Addressed:** None

---

## CP-10 — System Recovery and Reconstitution

**Implementation Status:** Implemented

**Control Inheritance:** System-Specific

**Implementation Description:**

The system can be recovered in the event of a disruption. We have recovery procedures
documented and the team is familiar with the steps required to restore the system.
Recovery time and recovery point objectives are defined in our contingency plan.

We test our recovery capabilities periodically to ensure we can restore the system
when needed.

**Responsible Role:** Platform Team / Management

**Parameters:** Periodically

**Evidence / Artifacts:** Contingency plan, recovery procedures

**Enhancements Addressed:** None

---

## What Makes This BAD — Examiner's Red Flags

| Control | Problem |
| ------- | ------- |
| CP-9 | "Regular backups" — no frequency, no retention period, no list of what is backed up. "Stored off-site" — which region? What service? "Encrypted" — with what key, managed by whom? |
| CP-9 | No restore test records. "Procedures in place to restore" is not a restore test — it is a claim that a procedure document exists. Until a restore is executed and timed, there is zero evidence the backup is usable. |
| CP-10 | "Periodically" as a recovery test cadence means never. No RTO or RPO values are stated. "The team is familiar with the steps" is not a recovery runbook — it is institutional knowledge that disappears when someone leaves. |
| CP-10 | No post-recovery integrity verification. A system restored from backup after a compromise without a reconstitution checklist may restore the attacker's persistence along with the data. This SSP would not catch that. |
| Both | The direct dependency between CP-9 and CP-10 is never acknowledged. CP-9 without CP-10 testing is a backup hypothesis. The only evidence that CP-9 works is a successful CP-10 test. Neither references the other. |
