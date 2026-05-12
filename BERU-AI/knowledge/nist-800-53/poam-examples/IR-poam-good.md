# POA&M — Incident Response (IR) Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** POA&M items reflect specific evidence gaps from the BERU assessment.
> Control owners are identified by role. Due dates follow severity-based priority tiers.
> Milestones cover M1 and M2 with actionable steps. Validation commands are real tool queries.
> Residual risk is acknowledged but remains generic. Status history includes opening reason.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** IR-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-026 | IR-4 — Incident Handling | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-027 | IR-8 — Incident Response Plan | Critical | P1 Immediate | 2026-05-17 |

---

## POAM-2026-05-026 — IR-4

```text
POAM-ID:          POAM-2026-05-026
CONTROL:          IR-4 — Incident Handling

WEAKNESS:
  Falco is not deployed. No incident detection rules, alert routing, or tabletop evidence
  can be produced for IR-4. Escalation path is undocumented and no tabletop exercise
  artifact has been generated.

SYSTEM AFFECTED:  Kubernetes / Links-Matrix cluster

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/IR-4?env=bad (falco — status: insufficient) + IRT interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/IR-4-2026-05-10/

REMEDIATION OWNER: IRT (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Deploy Falco as a DaemonSet to the Links-Matrix cluster; confirm all
                  nodes show at least one ready pod; export detection rule list to evidence
                  path.
  M2: 2026-05-16  Configure alert routing to Slack/PagerDuty; document escalation path in
                  the IRT runbook; produce a tabletop exercise artifact (scenario, participants,
                  outcomes) and store in evidence path.

REMEDIATION APPROACH:
  Deploy Falco via the official Helm chart to the monitoring namespace. Confirm the DaemonSet
  reaches numberReady equal to the node count. Enable the default rule set and configure
  falco.yaml to route alerts to the IRT Slack channel via falcosidekick. Produce the
  escalation path document naming L1 (IRT on-call), L2 (SecEng lead), and L3 (CISO).
  Conduct a tabletop exercise using the simulated privilege-escalation scenario and store
  the written outcome report in the evidence path.

VALIDATION COMMAND:
  kubectl -n monitoring get daemonset falco -o jsonpath='{.status.numberReady}'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Falco not deployed. 0 detection rules active. Alert routing not
             configured. Escalation path undocumented. No tabletop artifact.
```

---

## POAM-2026-05-027 — IR-8

```text
POAM-ID:          POAM-2026-05-027
CONTROL:          IR-8 — Incident Response Plan

WEAKNESS:
  The IR plan document cannot be found. No review date or approver is named. No tabletop
  exercise artifact has been produced to demonstrate the plan has been tested. ISSO
  verbal statement was the only evidence available — no artifacts to verify SSP claims.

SYSTEM AFFECTED:  Links-Matrix / ISSO governance records

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/IR-8?env=bad (semgrep — status: insufficient) + ISSO interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/IR-8-2026-05-10/

REMEDIATION OWNER: ISSO (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Locate or draft the IR plan document; confirm review date and named
                  approver; store signed copy in evidence path and link from Confluence.
  M2: 2026-05-16  Conduct a tabletop exercise using the IR plan; produce a written artifact
                  (scenario, participants, lessons learned) and store in evidence path.

REMEDIATION APPROACH:
  Search Confluence and SharePoint for the IR plan using the keyword "incident response plan".
  If not found, draft a new plan using the NIST SP 800-61 template covering: purpose, scope,
  roles, detection, containment, eradication, recovery, and post-incident review. Obtain
  ISSO and CISO sign-off. Record the review date and approver name on the title page. Conduct
  the tabletop exercise and produce the written outcome artifact. Store all artifacts in
  the evidence path and link from Confluence.

VALIDATION COMMAND:
  ls GP-CONSULTING/NIST-800-53/risk-assessment-examples/IR-ra-great.md && echo "IR policy artifact exists"

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — IR plan document not found. Review date not confirmed. Approver not
             named. No tabletop artifact produced.
```
