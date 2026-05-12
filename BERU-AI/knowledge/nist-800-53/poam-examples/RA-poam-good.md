# POA&M — Risk Assessment (RA) Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** POA&M items reflect specific evidence gaps from the BERU assessment.
> Control owners are identified by role. Due dates follow severity-based priority tiers.
> Milestones cover M1 and M2 with actionable steps. Validation commands are real tool queries.
> Residual risk is acknowledged but remains generic. Status history includes opening reason.

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
  Security Hub status is unknown and no risk register or assessment date can be produced for
  RA-3. ISSO could not confirm whether Security Hub is enabled. Risk register location in
  Confluence is unknown. Last assessment date and approver are not documented.

SYSTEM AFFECTED:  AWS Security Hub / Links-Matrix (Confluence, GRC platform)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/RA-3?env=bad → tool: prowler, status: insufficient,
                  security_hub_enabled: null, risk_register_artifact: null,
                  last_assessment_date: null. ISSO interview: no artifacts produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/RA-3-2026-05-10/

REMEDIATION OWNER: ISSO (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Enable Security Hub with NIST-800-53-r5, CIS-AWS-1.4, and FSBP standards;
                  confirm activation via AWS console; export enabled standards list to evidence
                  path.
  M2: 2026-05-16  Locate or produce the risk register (v3.2) in Confluence; confirm last
                  review date (2026-04-01) and approver name; store artifact in evidence path
                  and link from Confluence GRC space.

REMEDIATION APPROACH:
  Enable Security Hub in us-east-1 via AWS Console → Security Hub → Enable Security Hub.
  Activate the three required standards: NIST 800-53 Rev 5, CIS AWS Foundations 1.4, and
  AWS Foundational Security Best Practices. Export the enabled standards configuration as
  evidence. Locate the risk register (v3.2) in Confluence under the GRC space. If not found,
  produce a new risk register document covering the 323 FedRAMP Moderate controls, documenting
  the last assessment date (2026-04-01), approver name, and next assessment date (2027-04-01).
  Store the artifact in the evidence path and obtain ISSO sign-off.

VALIDATION COMMAND:
  prowler aws -c ec2_instance_managed_by_ssm --output-formats json | jq '[.[] | select(.status=="FAIL")] | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment. Security Hub status unknown.
             Risk register not produced. Assessment date not confirmed. Approver not named.
```

---

## POAM-2026-05-030 — RA-5

```text
POAM-ID:          POAM-2026-05-030
CONTROL:          RA-5 — Vulnerability Monitoring and Scanning

WEAKNESS:
  Trivy has not been run and no vulnerability scan results or patch SLA exist for RA-5.
  SecEng confirmed Trivy is on the roadmap but has not been configured. Zero images have
  been scanned. CVE counts are unknown. No SBOM has been generated. No S3 scan artifact
  exists. Patch SLA is not formally defined.

SYSTEM AFFECTED:  Links-Matrix (container images, CI/CD pipeline, S3 artifact store)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/RA-5?env=bad → tool: trivy, status: insufficient,
                  images_scanned: 0, cve_critical: null, cve_high: null, scan_schedule: null,
                  error: "Trivy scan not run — no results". SecEng interview: Trivy on roadmap,
                  no scan results, no SLA.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/RA-5-2026-05-10/

REMEDIATION OWNER: SecEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Install Trivy and run an initial scan against all 47 container images;
                  export scan results JSON to evidence path; identify open critical and high
                  CVEs.
  M2: 2026-05-16  Configure Trivy in CI pipeline to run on every push and daily schedule;
                  generate SBOM for all images; produce patch SLA document (Critical: 7 days,
                  High: 30 days, Medium: 90 days) and store in evidence path.

REMEDIATION APPROACH:
  Install Trivy: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh.
  Run initial scan against all container images in the registry. Export results as JSON to
  the evidence path. Identify all CRITICAL and HIGH CVEs and begin remediation per the SLA.
  Configure Trivy in the CI pipeline using the Trivy GitHub Action or equivalent step,
  setting --exit-code 1 for CRITICAL findings to block merges. Enable SBOM generation with
  --format cyclonedx. Produce the patch SLA document and obtain SecEng and ISSO sign-off.
  Upload scan artifacts to S3 at the path documented in the SSP.

VALIDATION COMMAND:
  trivy image --exit-code 0 --severity CRITICAL,HIGH --format json links-matrix:latest | jq '.Results[].Vulnerabilities | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment. Trivy not deployed.
             0 images scanned. CVE counts unknown. No patch SLA. No SBOM. No S3 artifact.
```

---

## POAM-2026-05-031 — RA-7

```text
POAM-ID:          POAM-2026-05-031
CONTROL:          RA-7 — Risk Response

WEAKNESS:
  No POA&M tracking data is available and risk response SLAs are not defined for RA-7.
  ISSO stated findings are tracked in JIRA but could not produce the POA&M document.
  Open finding count is unknown. Overdue remediation count is unknown. No formal risk
  response SLA has been defined or documented.

SYSTEM AFFECTED:  Links-Matrix (GRC platform, POA&M tracker, Confluence)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/RA-7?env=bad → tool: prowler, status: insufficient,
                  open_findings_count: null, overdue_remediations: null,
                  risk_response_artifact: null, error: "No risk response tracking data
                  available". ISSO interview: JIRA tracking described, POA&M not available,
                  SLA undefined.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/RA-7-2026-05-10/

REMEDIATION OWNER: ISSO (accountability) / CompO (evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Produce the POA&M document (GP-S3/3POA/POAM-2026-Q2.xlsx) with all open
                  findings enumerated, overdue count documented, and ISSO sign-off obtained;
                  store artifact in evidence path.
  M2: 2026-05-16  Define and document risk response SLAs (Critical: 14 days, High: 30 days,
                  Medium: 90 days) in a formal policy document; obtain ISSO and CISO approval;
                  store signed document in evidence path.

REMEDIATION APPROACH:
  CompO to produce the POA&M document in Excel or the GRC tool, populating all open findings
  with POAM-ID, control, severity, scheduled completion date, and current status. Cross-reference
  with JIRA to enumerate all open findings and identify overdue items. ISSO reviews and signs
  the completed POA&M. Produce the risk response SLA policy document defining remediation
  timelines per severity tier. Obtain ISSO and CISO approval. Store both artifacts in the
  evidence path and link from the Confluence GRC space.

VALIDATION COMMAND:
  prowler aws -c accessanalyzer_enabled --output-formats json | jq '[.[] | select(.status=="FAIL")] | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Evidence gap identified during GRC assessment. POA&M document not produced.
             Open finding count unknown. Overdue remediation count unknown. SLA not defined.
```
