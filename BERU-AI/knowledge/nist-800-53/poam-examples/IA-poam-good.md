# POA&M — Identification and Authentication (IA) Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** POA&M items reflect specific evidence gaps from the BERU assessment.
> Control owners are identified by role. Due dates follow severity-based priority tiers.
> Milestones cover M1 and M2 with actionable steps. Validation commands are real tool queries.
> Residual risk is acknowledged but remains generic. Status history includes opening reason.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** IA-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-022 | IA-2 — Identification and Authentication (Organizational Users) | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-023 | IA-3 — Device Identification and Authentication | High | P2 30 Days | 2026-06-09 |
| POAM-2026-05-024 | IA-4 — Identifier Management | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-025 | IA-5 — Authenticator Management | Critical | P1 Immediate | 2026-05-17 |

---

## POAM-2026-05-022 — IA-2

```text
POAM-ID:          POAM-2026-05-022
CONTROL:          IA-2 — Identification and Authentication (Organizational Users)

WEAKNESS:
  ConsoleLogin events are absent from CloudTrail and SCP MFA enforcement cannot be confirmed.
  MFA type is not confirmed, SCP ID is not on record, and bypass attempt count is unknown.
  No MFA device inventory artifact was produced. ITOps verbal statement was the only evidence
  available — no artifacts to verify SSP claims.

SYSTEM AFFECTED:  AWS IAM / Okta / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/IA-2?env=bad (cloudtrail — status: insufficient) + ITOps interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/IA-2-2026-05-10/

REMEDIATION OWNER: ITOps (evidence producer) / ISSO (sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Enable ConsoleLogin events in CloudTrail; confirm events appear in trail
                  within 5 minutes of a test login; export event list to evidence path.
  M2: 2026-05-15  Run aws iam list-virtual-mfa-devices to produce MFA device inventory;
                  confirm SCP ID for MFA enforcement; store artifacts in evidence path with
                  ISSO sign-off.

REMEDIATION APPROACH:
  Enable ConsoleLogin event capture in the CloudTrail trail event selectors. Perform a test
  console login and confirm the event appears in the trail. Export the last 30-day ConsoleLogin
  event log. Run aws iam list-virtual-mfa-devices --assignment-status Assigned to produce
  the MFA device inventory. Retrieve the SCP ID from AWS Organizations that enforces MFA.
  Confirm bypass attempt count via CloudTrail lookup for MFA-skipped login events.

VALIDATION COMMAND:
  aws iam list-virtual-mfa-devices --assignment-status Assigned --query 'VirtualMFADevices | length(@)'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — ConsoleLogin events absent from CloudTrail; MFA enforcement unconfirmed
```

---

## POAM-2026-05-023 — IA-3

```text
POAM-ID:          POAM-2026-05-023
CONTROL:          IA-3 — Device Identification and Authentication

WEAKNESS:
  Workload identity scan is not available and mTLS STRICT mode cannot be confirmed. Kubescape
  is not deployed on the cluster, SPIFFE IDs are unconfirmed, and the IRSA configuration was
  not produced. PlatEng could not supply any scan artifact or identity enforcement evidence.

SYSTEM AFFECTED:  Kubernetes / Istio / Links-Matrix cluster

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/IA-3?env=bad (kubescape — status: insufficient) + PlatEng interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/IA-3-2026-05-10/

REMEDIATION OWNER: PlatEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-06-09

MILESTONES:
  M1: 2026-05-20  Deploy Kubescape and run control C-0035 (workload identity); export results
                  JSON to evidence path; confirm mTLS PeerAuthentication mode is STRICT.
  M2: 2026-06-02  Confirm SPIFFE IDs are assigned to all workloads; produce IRSA configuration
                  artifact for each service account; store artifacts in evidence path.

REMEDIATION APPROACH:
  Deploy Kubescape via Helm to the Links-Matrix cluster and run control C-0035 to assess
  workload identity enforcement. Export scan results to the evidence path. Check Istio
  PeerAuthentication resources in all namespaces and confirm mode is STRICT. Enumerate
  all SPIFFE IDs assigned to workloads and confirm IRSA is configured for each service
  account that calls AWS APIs. Produce and store configuration artifacts for each.

VALIDATION COMMAND:
  kubescape scan control C-0035 --format json | jq '.summaryDetails.controlsSummaries["C-0035"].status.status'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Kubescape not deployed; mTLS STRICT mode unconfirmed; SPIFFE IDs unconfirmed
```

---

## POAM-2026-05-024 — IA-4

```text
POAM-ID:          POAM-2026-05-024
CONTROL:          IA-4 — Identifier Management

WEAKNESS:
  IAM credential report cannot be generated and no identifier review artifact exists. Last
  review date is not confirmed, orphaned and shared identifier counts are unknown, and no
  naming policy document was produced. ISSO verbal statement only — no artifacts to verify
  SSP claims.

SYSTEM AFFECTED:  AWS IAM / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/IA-4?env=bad (cloudtrail — status: insufficient) + ISSO interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/IA-4-2026-05-10/

REMEDIATION OWNER: ISSO (accountability) / ITOps (evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Generate IAM credential report via aws iam generate-credential-report;
                  export CSV to evidence path; identify orphaned and shared identifiers.
  M2: 2026-05-15  Produce identifier naming policy document; confirm last review date;
                  disable or remove orphaned identifiers; store all artifacts with ISSO
                  sign-off in evidence path.

REMEDIATION APPROACH:
  Run aws iam generate-credential-report and then aws iam get-credential-report to export
  the credential CSV. Review each identifier for last login date, shared status, and naming
  convention compliance. Produce the naming policy document from the SSP template. Disable
  any identifiers inactive for more than 90 days. Confirm the last identifier review date
  and produce a signed artifact. Store all outputs in the evidence path.

VALIDATION COMMAND:
  aws iam get-credential-report --query 'Content' --output text | base64 -d | awk -F, 'NR>1 {print $1}' | wc -l

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — IAM credential report not generated; identifier review artifact absent
```

---

## POAM-2026-05-025 — IA-5

```text
POAM-ID:          POAM-2026-05-025
CONTROL:          IA-5 — Authenticator Management

WEAKNESS:
  Gitleaks is not configured in CI and no secret rotation schedule or pre-commit hook exists.
  Credential report access key age is unknown. No evidence was produced showing that secrets
  in the codebase have been scanned or that rotation is automated. ITOps verbal statement
  was the only evidence available.

SYSTEM AFFECTED:  GitHub CI / AWS IAM / Links-Matrix

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/IA-5?env=bad (gitleaks — status: insufficient) + ITOps interview

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/IA-5-2026-05-10/

REMEDIATION OWNER: ITOps (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Add gitleaks to CI pipeline; run initial scan against full repo history;
                  export report JSON to evidence path; remediate any detected secrets.
  M2: 2026-05-15  Add pre-commit hook for gitleaks; confirm rotation schedule for IAM access
                  keys (target: 90 days); store rotation policy artifact with ISSO sign-off.

REMEDIATION APPROACH:
  Add a gitleaks step to the GitHub Actions CI pipeline targeting the default branch. Run
  an initial full-history scan using gitleaks detect --source . and export the JSON report.
  Remediate any detected secrets by rotating them and revoking the old credentials. Install
  the gitleaks pre-commit hook to block future secret commits. Confirm IAM access key age
  for all users via the credential report and rotate any keys older than 90 days. Document
  the rotation schedule and store the policy artifact in the evidence path.

VALIDATION COMMAND:
  gitleaks detect --source . --report-format json --report-path /tmp/gl-report.json; jq '. | length' /tmp/gl-report.json

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Gitleaks not in CI; no rotation schedule; no pre-commit hook configured
```
