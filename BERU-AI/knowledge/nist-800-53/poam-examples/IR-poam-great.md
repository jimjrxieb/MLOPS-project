# POA&M — Incident Response (IR) Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Auditor-ready POA&M. All deficiencies are numbered within each weakness.
> Remediation owners are split between evidence producer and sign-off authority. Due dates
> follow severity-based priority tiers. Milestones include M1, M2, and M3 with exact dated
> actions. Validation commands include expected output. Residual risk identifies the specific
> remaining gap after remediation. Status history shows full progression from OPEN to CLOSED.

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
  Four deficiencies identified on Links-Matrix (Kubernetes cluster / IRT operations):
  (1) Falco not deployed — DaemonSet does not exist in the monitoring namespace;
      numberReady: 0; no runtime detection rules are active on any node.
  (2) Alert routing not configured — falcosidekick is not deployed; IRT Slack channel
      and PagerDuty integration are both absent; no alert has ever fired from the cluster.
  (3) Escalation path undocumented — no IRT runbook names L1/L2/L3 contacts; verbal
      statement from IRT lead only; no Confluence artifact produced.
  (4) Tabletop exercise artifact not produced — ISSO could not supply a written scenario,
      participant list, or outcome record for any IR exercise conducted in the past 12 months.

SYSTEM AFFECTED:  Links-Matrix (Kubernetes cluster, monitoring namespace, IRT operations)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/IR-4?env=bad → tool: falco, status: insufficient,
                  falco_daemonset_ready: 0, detection_rules_active: 0,
                  alert_routing_configured: false, escalation_path_artifact: null,
                  tabletop_artifact: null.
                  IRT interview: no detection rules, no alert routing, no escalation doc,
                  no tabletop artifact produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/IR-4-2026-05-10/IR-4-finding.json

REMEDIATION OWNER: IRT (Falco deployment and alert routing evidence producer) / SecEng (escalation path sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Deploy Falco DaemonSet via Helm to the monitoring namespace; confirm
                  numberReady equals node count; export the active detection rule list
                  (kubectl describe cm falco-rules -n monitoring) to evidence path.
  M2: 2026-05-14  Deploy falcosidekick and configure alert routing to IRT Slack channel
                  and PagerDuty; trigger a test alert using the falco_event_generator and
                  confirm receipt in both destinations; store test receipt screenshots in
                  evidence path.
  M3: 2026-05-16  Publish IRT escalation runbook in Confluence naming L1 (IRT on-call),
                  L2 (SecEng lead), and L3 (CISO) with contact details and SLA; conduct
                  a tabletop exercise using the privilege-escalation scenario; produce
                  written outcome artifact (participants, scenario, findings, action items)
                  and store in evidence path; SecEng signs.

REMEDIATION APPROACH:
  Step 1: helm repo add falcosecurity https://falcosecurity.github.io/charts && helm install
  falco falcosecurity/falco --namespace monitoring --create-namespace
  --set falcosidekick.enabled=true --set falcosidekick.config.slack.webhookurl=<url>
  --set falcosidekick.config.pagerduty.routingkey=<key>. Confirm with:
    kubectl -n monitoring get daemonset falco -o jsonpath='{.status.numberReady}'
  and verify output equals the node count (e.g. 3).
  Step 2: Run the falco_event_generator in the cluster to trigger a test alert:
    kubectl run event-generator --image=falcosecurity/event-generator --restart=Never \
      -- run syscall --loop --sleep 500ms
  Confirm alert appears in IRT Slack channel and PagerDuty within 60 seconds.
  Step 3: Draft the IRT escalation runbook in Confluence under the IR family page tree.
  Include: L1 (IRT on-call, 15-min SLA), L2 (SecEng lead, 1-hr SLA), L3 (CISO, 4-hr SLA).
  Step 4: Schedule and conduct the tabletop exercise. Scenario: attacker achieves container
  escape and attempts lateral movement to the production namespace. Record participants,
  timeline, decisions made, and three action items. ISSO and SecEng sign the artifact.

VALIDATION COMMAND:
  kubectl -n monitoring get daemonset falco -o jsonpath='{.status.numberReady}'
  Expected output: non-zero integer (e.g. `3`)

RESIDUAL RISK AFTER REMEDIATION:
  Falco rules cover kernel syscall events only — eBPF-based detection for host-level
  persistence (e.g., systemd unit modification) requires Tetragon, which is not yet
  deployed on the Links-Matrix cluster. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Falco DaemonSet not deployed (numberReady: 0). 0 detection rules active.
             Alert routing absent. Escalation path undocumented. No tabletop artifact.
             IRT verbal statement only.
  2026-05-12 IN PROGRESS — M1 complete: Falco deployed via Helm. DaemonSet numberReady: 3
             (all nodes). 65 default detection rules active. Rule list exported to evidence
             path.
  2026-05-14 IN PROGRESS — M2 complete: falcosidekick deployed. Slack and PagerDuty
             integrations confirmed via event-generator test. Alert receipt screenshots
             stored in evidence path.
  2026-05-16 IN PROGRESS — M3 complete: IRT escalation runbook published in Confluence.
             Tabletop exercise conducted (6 participants, privilege-escalation scenario).
             Written outcome artifact produced and signed by SecEng.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/IR-4?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-027 — IR-8

```text
POAM-ID:          POAM-2026-05-027
CONTROL:          IR-8 — Incident Response Plan

WEAKNESS:
  Four deficiencies identified on Links-Matrix (ISSO governance / IR documentation):
  (1) IR plan document not found — Confluence and SharePoint searches returned no result;
      no PDF, DOCX, or Markdown IR plan artifact exists in any auditable location.
  (2) Review date not confirmed — ISSO verbal claim of "annually reviewed" cannot be
      substantiated; no dated version history, no last-reviewed field, no calendar entry
      produced.
  (3) Approver not named — no CISO or authorizing official signature on any version
      of the IR plan; SSP assertion of named approver is unverified.
  (4) Tabletop exercise artifact not produced — no written scenario, participant list,
      or outcome record for any exercise conducted in the past 12 months.

SYSTEM AFFECTED:  Links-Matrix (ISSO governance records, Confluence, SharePoint)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/IR-8?env=bad → tool: semgrep, status: insufficient,
                  ir_plan_artifact: null, review_date_confirmed: false,
                  approver_named: false, tabletop_artifact: null.
                  ISSO interview: no IR plan document, no review date, no approver, no
                  tabletop artifact produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/IR-8-2026-05-10/IR-8-finding.json

REMEDIATION OWNER: ISSO (IR plan author and tabletop artifact evidence producer) / CISO (approver and sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Locate or draft the IR plan document using the NIST SP 800-61 template;
                  obtain CISO signature; record review date on title page; store signed
                  PDF in evidence path and link from Confluence IR family page.
  M2: 2026-05-14  Conduct a tabletop exercise using the IR plan; cover at minimum one
                  detection scenario (ransomware or privilege escalation); produce written
                  outcome artifact (participants, scenario, timeline, action items) signed
                  by ISSO and SecEng; store in evidence path.
  M3: 2026-05-16  Confirm IR plan is scheduled for annual review in the GRC calendar;
                  set a calendar entry for 2027-05-10 review; update SSP Section 3.6 to
                  reference the evidence path for the signed plan and tabletop artifact.

REMEDIATION APPROACH:
  Step 1: Search Confluence (search: "incident response plan" site:confluence.links-matrix.internal)
  and SharePoint. If found, update it to include: named approver, review date, and NIST
  SP 800-61 section headings. If not found, draft using the template at
  GP-CONSULTING/templates/IR-plan-template.md. Sections required: purpose, scope, roles
  (IRT lead, SecEng, CISO, Legal), detection criteria, containment playbooks (ransomware,
  data exfiltration, privilege escalation), eradication steps, recovery SLA, and
  post-incident review process.
  Step 2: Schedule the tabletop exercise with IRT, SecEng, and CISO. Use the
  privilege-escalation scenario: attacker compromises a developer credential and attempts
  to access the production database. Run through detection, containment, escalation, and
  recovery phases. Record participant names, roles, scenario details, timeline of decisions,
  and three action items with owners and due dates.
  Step 3: File the signed IR plan PDF and tabletop outcome artifact in the evidence path.
  Update the SSP Section 3.6 IR-8 row to include the evidence path reference. Set the
  annual review calendar entry. CISO reviews and confirms the SSP update.

VALIDATION COMMAND:
  ls GP-CONSULTING/NIST-800-53/risk-assessment-examples/IR-ra-great.md && echo "IR policy artifact exists"
  Expected output: GP-CONSULTING/NIST-800-53/risk-assessment-examples/IR-ra-great.md
                   IR policy artifact exists

RESIDUAL RISK AFTER REMEDIATION:
  IR plan covers in-scope Kubernetes and AWS assets only — third-party SaaS integrations
  (Slack, PagerDuty, Confluence) do not have their own IR runbooks and are not yet
  incorporated into the tabletop exercise scenarios. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — IR plan document not found in Confluence or SharePoint. Review date
             unconfirmed. Approver not named. No tabletop artifact for past 12 months.
             ISSO verbal statement only.
  2026-05-12 IN PROGRESS — M1 complete: IR plan drafted using NIST SP 800-61 template.
             CISO signed. Review date 2026-05-12 recorded on title page. Signed PDF
             stored in evidence path and linked from Confluence (IR-Plan-v1.0).
  2026-05-14 IN PROGRESS — M2 complete: Tabletop exercise conducted (7 participants).
             Privilege-escalation scenario run end-to-end. Written outcome artifact
             (3 action items) signed by ISSO and SecEng. Stored in evidence path.
  2026-05-16 IN PROGRESS — M3 complete: Annual review calendar entry set for 2027-05-10.
             SSP Section 3.6 updated with evidence path reference. CISO confirmed.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/IR-8?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```
