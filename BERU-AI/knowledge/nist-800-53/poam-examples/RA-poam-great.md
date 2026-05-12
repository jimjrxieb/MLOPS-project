# POA&M — Risk Assessment (RA) Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Auditor-ready POA&M. All deficiencies are numbered within each weakness.
> Remediation owners are split between evidence producer and sign-off authority. Due dates
> follow severity-based priority tiers. Milestones include M1, M2, and M3 with exact dated
> actions. Validation commands include expected output. Residual risk identifies the specific
> remaining gap after remediation. Status history shows full progression from OPEN to CLOSED.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** RA-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-029 | RA-3 — Risk Assessment | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-030 | RA-5 — Vulnerability Monitoring and Scanning | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-031 | RA-7 — Risk Response | Critical | P1 Immediate | 2026-05-17 |

---

## POAM-2026-05-029 — RA-3

```text
POAM-ID:          POAM-2026-05-029
CONTROL:          RA-3 — Risk Assessment

WEAKNESS:
  Four deficiencies identified on Links-Matrix (AWS Security Hub / Confluence GRC):
  (1) Security Hub not confirmed enabled — security_hub_enabled: null; prowler query returned
      null for all three required standards (NIST-800-53-r5, CIS-AWS-1.4, FSBP); current
      activation state is unverifiable.
  (2) Risk register not produced — ISSO could not provide a Confluence link or export;
      v3.2 referenced in SSP cannot be located; no auditable record exists.
  (3) Last assessment date not confirmed — SSP asserts 2026-04-01; no calendar record,
      no meeting notes, no assessor signature artifact supports this claim.
  (4) Approver not named — SSP asserts ISSO approval; ISSO verbal only; no signed artifact
      with approver identity and date produced.

SYSTEM AFFECTED:  Links-Matrix (AWS Security Hub, Confluence, GRC platform)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/RA-3?env=bad → tool: prowler, status: insufficient,
                  security_hub_enabled: null, risk_register_artifact: null,
                  last_assessment_date: null, error: "Security Hub not enabled or not
                  accessible". ISSO interview: Security Hub uncertain, register location
                  unknown, assessment date unconfirmed, approver not named.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/RA-3-2026-05-10/RA-3-finding.json

REMEDIATION OWNER: ISSO (risk register and approval evidence producer) / CloudSec (Security Hub enablement owner)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Enable Security Hub in us-east-1; activate NIST-800-53-r5, CIS-AWS-1.4,
                  and FSBP standards; export enabled standards configuration JSON to evidence
                  path; confirm all three standards show status: ENABLED.
  M2: 2026-05-14  Locate or produce risk register (v3.2) in Confluence GRC space; document
                  last review date (2026-04-01), next assessment date (2027-04-01), and
                  approver name with title; ISSO signs the completed register; store artifact
                  in evidence path.
  M3: 2026-05-16  Produce the risk assessment completion record: assessor name, assessment
                  date, methodology (NIST 800-53A), and ISSO sign-off; store signed artifact
                  in Confluence at RA-3-Assessment-2026 page and link from evidence path.

REMEDIATION APPROACH:
  Step 1: In AWS Console → Security Hub → Enable Security Hub. Select all three required
  standards. Confirm activation: aws securityhub get-enabled-standards | jq '.StandardsSubscriptions[].StandardsArn'.
  Export the enabled standards list as JSON to the evidence path.
  Step 2: Search Confluence GRC space for "risk register v3.2". If located, verify it contains:
  assessment date (2026-04-01), next assessment date (2027-04-01), approver name (ISSO),
  and coverage of 323 FedRAMP Moderate controls. If not found, produce a new version using
  the template in GP-CONSULTING/templates/ and populate all required fields. ISSO reviews
  and signs with date.
  Step 3: Produce the risk assessment completion record documenting the assessor (GRC Engineer),
  assessment date (2026-05-10), methodology (NIST 800-53A Rev 5), and ISSO sign-off. Attach
  the Security Hub standards screenshot as a supporting artifact. Store in Confluence at
  RA-3-Assessment-2026 and link from the evidence path.

VALIDATION COMMAND:
  prowler aws -c ec2_instance_managed_by_ssm --output-formats json \
    | jq '[.[] | select(.status=="FAIL")] | length'
  Expected output: 0

RESIDUAL RISK AFTER REMEDIATION:
  Security Hub aggregates findings but does not replace a manual risk assessment for
  non-automated controls (e.g., physical security, personnel security). Annual manual
  review of non-automated controls remains required outside Security Hub scope. Residual
  risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Security Hub not confirmed enabled. Risk register not produced.
             Last assessment date unconfirmed. Approver not named. ISSO verbal only.
  2026-05-12 IN PROGRESS — M1 complete: Security Hub enabled in us-east-1. All three
             standards activated (NIST-800-53-r5, CIS-AWS-1.4, FSBP confirmed ENABLED).
             Standards configuration JSON exported to evidence path.
  2026-05-14 IN PROGRESS — M2 complete: Risk register (v3.2) located and updated in
             Confluence. Assessment date 2026-04-01 confirmed. Next assessment 2027-04-01
             documented. ISSO signed with date. Artifact stored in evidence path.
  2026-05-16 IN PROGRESS — M3 complete: Risk assessment completion record produced.
             Assessor name, date, methodology, and ISSO sign-off documented. Stored at
             Confluence: RA-3-Assessment-2026 (link: <confluence-url>/pages/RA-3-Assessment-2026).
  2026-05-17 CLOSED — BERU re-ran GET /evidence/RA-3?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-030 — RA-5

```text
POAM-ID:          POAM-2026-05-030
CONTROL:          RA-5 — Vulnerability Monitoring and Scanning

WEAKNESS:
  Five deficiencies identified on Links-Matrix (container images / CI/CD pipeline):
  (1) Trivy not deployed — images_scanned: 0; scan_schedule: null; no CI gate configured;
      Trivy confirmed on roadmap but not installed on any build runner.
  (2) CVE counts unknown — cve_critical: null, cve_high: null; current vulnerability
      exposure for all 47 production container images is completely unverifiable.
  (3) No patch SLA defined — SecEng verbal statement only; no document specifying remediation
      timelines per severity tier exists in any auditable artifact.
  (4) No SBOM generated — SSP asserts SBOM for all images; no SBOM artifact exists in S3
      or any other store; software composition is unverifiable.
  (5) No S3 scan artifact — SSP asserts scan results uploaded to S3 after each run;
      S3 bucket contains 0 scan result files matching Trivy output format.

SYSTEM AFFECTED:  Links-Matrix (container images, CI/CD pipeline, S3 artifact store)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/RA-5?env=bad → tool: trivy, status: insufficient,
                  images_scanned: 0, cve_critical: null, cve_high: null, scan_schedule: null,
                  error: "Trivy scan not run — no results". SecEng interview: Trivy on roadmap,
                  manual checks only, no SLA, no SBOM, no S3 artifact.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/RA-5-2026-05-10/RA-5-finding.json

REMEDIATION OWNER: SecEng (Trivy deployment and scan evidence producer) / ISSO (patch SLA sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Install Trivy on the CI build runner; run initial scan against all 47
                  container images; export scan results JSON to evidence path; identify
                  all open CRITICAL and HIGH CVEs and begin remediation.
  M2: 2026-05-14  Configure Trivy in CI pipeline (on push + daily schedule); generate SBOM
                  in CycloneDX format for all images; upload scan results and SBOMs to S3
                  at path documented in SSP; confirm S3 artifacts exist.
  M3: 2026-05-16  Produce patch SLA policy document (Critical: 7 days, High: 30 days,
                  Medium: 90 days); obtain SecEng and ISSO sign-off; store signed document
                  in Confluence and link from evidence path.

REMEDIATION APPROACH:
  Step 1: Install Trivy on the CI build runner:
  curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh.
  Run initial scan: trivy image --severity CRITICAL,HIGH --format json links-matrix:latest
  > evidence-path/RA-5-initial-scan.json. Review all CRITICAL findings and remediate within
  7 days per the draft SLA.
  Step 2: Add Trivy to the CI pipeline using the aquasecurity/trivy-action GitHub Action
  with inputs: image-ref, format: json, exit-code: 1, severity: CRITICAL. Configure a
  daily scheduled scan via cron. Enable SBOM generation: trivy image --format cyclonedx
  links-matrix:latest > sbom.json. Upload scan JSON and SBOM to S3:
  aws s3 cp evidence-path/ s3://links-matrix-evidence/trivy-scans/ --recursive.
  Step 3: Draft the patch SLA policy document using the template in GP-CONSULTING/templates/.
  Define remediation timelines: Critical — 7 days from detection, High — 30 days, Medium —
  90 days, Low — next quarterly cycle. SecEng reviews technical feasibility. ISSO reviews
  and signs. Store signed policy in Confluence at RA-5-Patch-SLA-2026.

VALIDATION COMMAND:
  trivy image --exit-code 0 --severity CRITICAL,HIGH --format json links-matrix:latest \
    | jq '.Results[].Vulnerabilities | length'
  Expected output: 0

RESIDUAL RISK AFTER REMEDIATION:
  Trivy CI gate runs on push and daily schedule but does not scan images already deployed
  in production — a zero-day CVE published between scan cycles could affect running
  containers without immediate detection. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Trivy not deployed. images_scanned: 0. CVE counts unknown.
             No patch SLA. No SBOM. No S3 artifact. SecEng verbal only.
  2026-05-12 IN PROGRESS — M1 complete: Trivy installed and initial scan run against all
             47 images. 3 CRITICAL and 8 HIGH CVEs identified. Remediation begun on all
             CRITICAL findings. Scan JSON exported to evidence path.
  2026-05-14 IN PROGRESS — M2 complete: Trivy CI gate configured (on push + daily cron).
             SBOM generated in CycloneDX format for all 47 images. Scan results and SBOMs
             uploaded to S3 (47 files confirmed in bucket).
  2026-05-16 IN PROGRESS — M3 complete: Patch SLA policy document produced. SecEng and
             ISSO signed. Stored in Confluence at RA-5-Patch-SLA-2026 (link: <confluence-url>/pages/RA-5-Patch-SLA-2026).
  2026-05-17 CLOSED — BERU re-ran GET /evidence/RA-5?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-031 — RA-7

```text
POAM-ID:          POAM-2026-05-031
CONTROL:          RA-7 — Risk Response

WEAKNESS:
  Four deficiencies identified on Links-Matrix (GRC platform / POA&M tracker):
  (1) POA&M document not produced — ISSO referenced JIRA tracking but could not produce
      the POA&M document (GP-S3/3POA/POAM-2026-Q1.xlsx); open_findings_count: null;
      SSP claim of 12 open findings with 0 overdue cannot be verified.
  (2) Open finding count unknown — prowler query returned open_findings_count: null;
      no enumeration of open findings across all 5 C's exists in any auditable artifact.
  (3) Overdue remediation count unknown — overdue_remediations: null; no tracking shows
      which findings have exceeded their SLA; accountability for overdue items is absent.
  (4) Risk response SLA not defined — no formal document specifying remediation timelines
      per severity tier exists; SSP asserts Critical: 14 days, High: 30 days, Medium: 90
      days, but no signed policy artifact supports this claim.

SYSTEM AFFECTED:  Links-Matrix (GRC platform, POA&M tracker, Confluence)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/RA-7?env=bad → tool: prowler, status: insufficient,
                  open_findings_count: null, overdue_remediations: null,
                  risk_response_artifact: null, error: "No risk response tracking data
                  available". ISSO interview: JIRA tracking described, POA&M not available,
                  SLA undefined, overdue count unknown.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/RA-7-2026-05-10/RA-7-finding.json

REMEDIATION OWNER: CompO (POA&M document and SLA evidence producer) / ISSO (accountability and sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  CompO produces the POA&M document (GP-S3/3POA/POAM-2026-Q2.xlsx) with
                  all open findings enumerated by POAM-ID, control, severity, scheduled
                  completion, and current status; ISSO reviews and signs; artifact stored
                  in evidence path.
  M2: 2026-05-14  Identify all overdue remediations (findings past their SLA date) in the
                  POA&M; produce an overdue tracking report with finding count and elapsed
                  days past SLA; escalate to CISO for acknowledgment; store report in
                  evidence path.
  M3: 2026-05-16  Produce the risk response SLA policy document formalizing remediation
                  timelines (Critical: 14 days, High: 30 days, Medium: 90 days); obtain
                  ISSO and CISO sign-off; store signed document in Confluence at
                  RA-7-RiskResponse-SLA-2026 and link from evidence path.

REMEDIATION APPROACH:
  Step 1: CompO to export all open findings from JIRA and cross-reference with assessment
  reports across all 5 C's (Code, Container, Cluster, Cloud, Compliance). Produce the POA&M
  in Excel or the GRC tool, populating POAM-ID, control ID, finding description, severity,
  detection date, scheduled completion date, and current status for each finding. Flag any
  finding past its scheduled completion date as overdue. ISSO reviews, signs with date, and
  stores the signed document in GP-S3/3POA/POAM-2026-Q2.xlsx.
  Step 2: Extract the overdue subset from the POA&M (any finding where scheduled completion
  < 2026-05-10 and status != CLOSED). Document the count, the elapsed days past SLA for each,
  and the assigned remediation owner. Produce a one-page overdue tracking report and escalate
  to CISO for acknowledgment signature. Store the signed report in the evidence path.
  Step 3: Draft the risk response SLA policy using the template in GP-CONSULTING/templates/.
  Define: Critical — 14 calendar days from detection, High — 30 calendar days, Medium — 90
  calendar days, Low — next quarterly POA&M review cycle. Define the escalation path for
  overdue items (owner → ISSO → CISO). Obtain ISSO and CISO signatures. Store in Confluence
  at RA-7-RiskResponse-SLA-2026 and link from the evidence path.

VALIDATION COMMAND:
  prowler aws -c accessanalyzer_enabled --output-formats json \
    | jq '[.[] | select(.status=="FAIL")] | length'
  Expected output: 0

RESIDUAL RISK AFTER REMEDIATION:
  POA&M covers findings identified through automated scanning — manual assessment findings
  from penetration tests and third-party audits require a separate ingestion workflow not
  yet implemented. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — POA&M document not produced. open_findings_count: null.
             overdue_remediations: null. Risk response SLA not defined. ISSO verbal only.
  2026-05-12 IN PROGRESS — M1 complete: POA&M document produced (POAM-2026-Q2.xlsx).
             28 open findings enumerated across 5 C's. ISSO signed with date.
             Artifact stored in GP-S3/3POA/ and linked from evidence path.
  2026-05-14 IN PROGRESS — M2 complete: Overdue tracking report produced. 4 findings
             identified as overdue (2–14 days past SLA). CISO acknowledgment obtained.
             Report stored in evidence path.
  2026-05-16 IN PROGRESS — M3 complete: Risk response SLA policy produced and signed
             by ISSO and CISO. Stored in Confluence at RA-7-RiskResponse-SLA-2026
             (link: <confluence-url>/pages/RA-7-RiskResponse-SLA-2026).
  2026-05-17 CLOSED — BERU re-ran GET /evidence/RA-7?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```
