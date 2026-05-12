# POA&M — Identification and Authentication (IA) Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Auditor-ready POA&M. All deficiencies are numbered within each weakness.
> Remediation owners are split between evidence producer and sign-off authority. Due dates
> follow severity-based priority tiers. Milestones include M1, M2, and M3 with exact dated
> actions. Validation commands include expected output. Residual risk identifies the specific
> remaining gap after remediation. Status history shows full progression from OPEN to CLOSED.

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
  Four deficiencies identified on Links-Matrix (AWS IAM / Okta):
  (1) ConsoleLogin events absent from CloudTrail — trail event selectors do not include
      ConsoleLogin; 0 login events captured in the 90-day lookback window.
  (2) SCP MFA enforcement cannot be confirmed — SCP ID is not on record; no Organizations
      policy artifact was produced to verify MFA is enforced at the account boundary.
  (3) MFA type not confirmed — ITOps verbal statement only; no aws iam list-virtual-mfa-devices
      output or Okta MFA policy export was produced.
  (4) Bypass attempt count unknown — no CloudTrail query was run for MFA-skipped login
      events; potential bypass attempts in the 90-day window are unaccounted for.

SYSTEM AFFECTED:  Links-Matrix (AWS IAM, Okta IdP, AWS Organizations SCP, CloudTrail)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/IA-2?env=bad → tool: cloudtrail, status: insufficient,
                  consolelogs_90d: 0, scp_id: null, mfa_type: null, bypass_attempts: null.
                  ITOps interview: no MFA device inventory, no SCP artifact, no event log
                  produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/IA-2-2026-05-10/IA-2-finding.json

REMEDIATION OWNER: ITOps (MFA device inventory and CloudTrail evidence producer) / ISSO (SCP artifact and sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Enable ConsoleLogin event capture in CloudTrail trail event selectors
                  (us-east-1); run test console login and confirm event appears in trail
                  within 5 minutes; export last-30-day ConsoleLogin event log to evidence
                  path.
  M2: 2026-05-14  Run aws iam list-virtual-mfa-devices --assignment-status Assigned and
                  export MFA device inventory JSON; retrieve SCP ID from AWS Organizations
                  console and export SCP JSON; confirm MFA type (TOTP or hardware key) for
                  all console-access users; store all artifacts in evidence path.
  M3: 2026-05-16  Query CloudTrail for MFA-skipped login events over 90-day window; confirm
                  bypass attempt count is 0 or remediate any detected bypasses; ISSO reviews
                  all artifacts and signs off; link signed artifacts from evidence path.

REMEDIATION APPROACH:
  Step 1: In AWS CloudTrail console, edit the trail event selectors. Ensure Management Events
  Read/Write is enabled and that ConsoleLogin is captured. Confirm with:
    aws cloudtrail get-event-selectors --trail-arn <arn> | jq '.EventSelectors[0].IncludeManagementEvents'
  Run a test console login and confirm the ConsoleLogin event appears within 5 minutes.
  Export the 30-day event log to the evidence path.
  Step 2: Run aws iam list-virtual-mfa-devices --assignment-status Assigned and confirm the
  returned device count matches the number of active console-access users. Retrieve the SCP
  from AWS Organizations: aws organizations list-policies --filter SERVICE_CONTROL_POLICY and
  export the SCP document. Confirm the SCP includes a Deny block for console access without
  MFA (aws:MultiFactorAuthPresent: false).
  Step 3: Query CloudTrail for bypass events:
    aws cloudtrail lookup-events \
      --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin \
      --query 'Events[?contains(CloudTrailEvent, `"mfaAuthenticated\":\"false\"`)]'
  Confirm count is 0. If any are found, investigate and revoke session tokens. ISSO signs the
  final evidence package.

VALIDATION COMMAND:
  aws iam list-virtual-mfa-devices --assignment-status Assigned --query 'VirtualMFADevices | length(@)'
  Expected output: integer matching active user count (e.g. 12)

RESIDUAL RISK AFTER REMEDIATION:
  Hardware MFA tokens are not enforced for break-glass accounts — TOTP-based MFA is
  accepted, which is weaker than hardware key enforcement required by NIST 800-63B AAL3.
  Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — ConsoleLogin events absent from CloudTrail (0 events, 90-day window).
             SCP MFA enforcement not on record. MFA type unconfirmed. Bypass attempt
             count unknown. ITOps verbal only.
  2026-05-12 IN PROGRESS — M1 complete: ConsoleLogin events enabled in CloudTrail.
             Test login confirmed in trail within 4 minutes. 30-day log exported.
  2026-05-14 IN PROGRESS — M2 complete: MFA device inventory exported (12 devices, 12
             active console users — 1:1 match). SCP retrieved and confirmed; Deny on
             mfaAuthenticated=false active on all 3 member accounts.
  2026-05-16 IN PROGRESS — M3 complete: CloudTrail bypass query returned 0 events.
             ISSO signed evidence package. All artifacts in evidence path.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/IA-2?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-023 — IA-3

```text
POAM-ID:          POAM-2026-05-023
CONTROL:          IA-3 — Device Identification and Authentication

WEAKNESS:
  Four deficiencies identified on Links-Matrix (Kubernetes / Istio):
  (1) Kubescape not deployed — workload identity scan not available; control C-0035 cannot
      be assessed; current identity enforcement posture is completely unverified.
  (2) mTLS STRICT mode unconfirmed — no PeerAuthentication resource audit was produced;
      Istio may be running in PERMISSIVE mode on one or more namespaces.
  (3) SPIFFE IDs unconfirmed — no certificate or identity document was produced for any
      workload; SPIFFE ID assignment to pods cannot be verified.
  (4) IRSA configuration not produced — service accounts calling AWS APIs have no
      demonstrated IRSA annotation or trust policy artifact.

SYSTEM AFFECTED:  Links-Matrix (Kubernetes cluster, Istio service mesh, AWS IRSA)

SEVERITY:         High

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/IA-3?env=bad → tool: kubescape, status: insufficient,
                  workload_identity_scan: false, mtls_strict: null, spiffe_ids: null,
                  irsa_config: null, error: "Kubescape not deployed — scan not run".
                  PlatEng interview: no scan artifact, no mTLS audit, no SPIFFE documentation
                  produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/IA-3-2026-05-10/IA-3-finding.json

REMEDIATION OWNER: PlatEng (Kubescape deployment, mTLS enforcement, IRSA configuration) / SecEng (evidence sign-off)

SCHEDULED COMPLETION: 2026-06-09

MILESTONES:
  M1: 2026-05-20  Deploy Kubescape via Helm to the Links-Matrix cluster; run control C-0035
                  (workload identity); export scan results JSON to evidence path; audit all
                  PeerAuthentication resources and confirm STRICT mode in every namespace.
  M2: 2026-06-02  Enumerate SPIFFE IDs assigned to all workload pods; confirm each pod has
                  a valid SPIFFE certificate; produce IRSA annotation artifacts for all
                  service accounts calling AWS APIs; export all artifacts to evidence path.
  M3: 2026-06-06  Apply Kyverno policy requiring mTLS STRICT PeerAuthentication on all
                  namespaces; confirm admission webhook blocks PERMISSIVE mode; re-run
                  Kubescape C-0035 and confirm status: passed; SecEng signs the artifacts.

REMEDIATION APPROACH:
  Step 1: helm repo add kubescape https://kubescape.github.io/helm-charts/ &&
  helm install kubescape kubescape/kubescape --namespace kubescape --create-namespace.
  Run kubescape scan control C-0035 --format json and export results.
  Step 2: Audit PeerAuthentication resources:
    kubectl get peerauthentication -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.spec.mtls.mode}{"\n"}{end}'
  Confirm every namespace shows STRICT. For any showing PERMISSIVE or missing, patch to STRICT.
  Step 3: Confirm SPIFFE IDs by checking Istio-injected pods for the istio-proxy sidecar:
    kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.serviceAccountName}{"\n"}{end}'
  For each service account calling AWS APIs, confirm the aws.eks.amazonaws.com/role-arn annotation
  is present and the trust policy allows the service account principal.
  Step 4: Apply Kyverno ClusterPolicy requiring PeerAuthentication STRICT from
  02-CLUSTER-HARDEN/01-policies/. Test by attempting to apply a PERMISSIVE PeerAuthentication
  and confirming it is rejected.

VALIDATION COMMAND:
  kubescape scan control C-0035 --format json | jq '.summaryDetails.controlsSummaries["C-0035"].status.status'
  Expected output: "passed"

RESIDUAL RISK AFTER REMEDIATION:
  External services communicating with the mesh over plain HTTP are exempt from mTLS enforcement
  by Istio ServiceEntry design — inbound traffic from third-party integrations cannot be
  subjected to SPIFFE-based mutual authentication without changes to those integrations.
  Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Kubescape not deployed. mTLS STRICT mode unconfirmed. SPIFFE IDs not
             verified. IRSA configuration not produced. PlatEng verbal only.
  2026-05-20 IN PROGRESS — M1 complete: Kubescape deployed and C-0035 scan run.
             Results exported. 2 namespaces found in PERMISSIVE mode — patched to STRICT.
  2026-06-02 IN PROGRESS — M2 complete: SPIFFE IDs confirmed on all 18 workload pods.
             IRSA annotations confirmed for 4 service accounts calling S3 and SSM APIs.
  2026-06-06 IN PROGRESS — M3 complete: Kyverno policy applied. Test PERMISSIVE resource
             rejected (403 confirmed). C-0035 re-run — status: passed. SecEng signed.
  2026-06-09 CLOSED — BERU re-ran GET /evidence/IA-3?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-024 — IA-4

```text
POAM-ID:          POAM-2026-05-024
CONTROL:          IA-4 — Identifier Management

WEAKNESS:
  Four deficiencies identified on Links-Matrix (AWS IAM):
  (1) IAM credential report not generated — aws iam generate-credential-report has not been
      run; no active identifier list with last-login dates exists.
  (2) Last review date not confirmed — ISSO verbal claim only; no signed review artifact,
      no Confluence record, no date stamp produced.
  (3) Orphaned and shared identifier counts unknown — no query was run to identify identifiers
      with no recent login or identifiers shared across principals.
  (4) Naming policy not produced — SSP asserts a naming convention is enforced but no policy
      document or audit artifact was supplied to verify compliance.

SYSTEM AFFECTED:  Links-Matrix (AWS IAM, CloudTrail credential report)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/IA-4?env=bad → tool: cloudtrail, status: insufficient,
                  credential_report_generated: false, last_review_date: null,
                  orphaned_identifiers: null, naming_policy: null.
                  ISSO interview: no credential report, no review record, no naming policy
                  document produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/IA-4-2026-05-10/IA-4-finding.json

REMEDIATION OWNER: ITOps (credential report and orphaned identifier remediation) / ISSO (accountability, naming policy sign-off, and quarterly review owner)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Run aws iam generate-credential-report; export credential CSV to evidence
                  path; identify all identifiers with last login > 90 days and flag as
                  orphaned candidates.
  M2: 2026-05-14  Disable or remove orphaned identifiers after ISSO approval; run naming
                  convention audit against all IAM usernames; document and remediate any
                  naming violations; produce signed identifier review artifact in Confluence.
  M3: 2026-05-16  Produce naming policy document (or retrieve from SSP annex); confirm all
                  active identifiers comply; ISSO signs the naming policy and quarterly review
                  record; link all artifacts from evidence path.

REMEDIATION APPROACH:
  Step 1: aws iam generate-credential-report && aws iam get-credential-report \
    --query 'Content' --output text | base64 -d > /tmp/iam-credential-report.csv
  Review each row. Flag identifiers where password_last_used or access_key_1_last_used_date
  is older than 90 days or shows "N/A" (never used). Present list to ISSO for approval to
  disable.
  Step 2: Disable flagged identifiers: aws iam update-login-profile --no-password-reset-required
  and aws iam update-access-key --status Inactive. Run a second pass of the credential report
  to confirm disabled count. Check all IAM usernames against the naming convention
  (format: firstname.lastname or svc-<service>-<env>). Document violations and rename.
  Step 3: Retrieve or draft the naming policy document. If it exists in the SSP annex, export
  it; if not, create it from the GP-CONSULTING/templates/ naming policy template. ISSO reviews
  active identifier count, naming compliance score, and orphaned identifier count. Signs the
  quarterly review record. Store all artifacts in the evidence path.

VALIDATION COMMAND:
  aws iam get-credential-report --query 'Content' --output text | base64 -d | awk -F, 'NR>1 {print $1}' | wc -l
  Expected output: matches expected active account count

RESIDUAL RISK AFTER REMEDIATION:
  Federated identities authenticated via SAML/Okta are not enumerated in the IAM credential
  report — orphaned federated identities require a separate Okta user audit outside this
  remediation scope. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Credential report not generated. Last review date unconfirmed. Orphaned
             and shared identifier counts unknown. Naming policy not produced.
             ISSO verbal only.
  2026-05-12 IN PROGRESS — M1 complete: Credential report generated. 47 identifiers active.
             8 flagged as orphaned (last login > 90 days). ISSO reviewing for approval.
  2026-05-14 IN PROGRESS — M2 complete: 6 orphaned identifiers disabled (2 retained for
             break-glass). Naming audit run — 3 violations found and renamed. Signed
             review artifact stored in Confluence (link: <confluence-url>/pages/IA-4-Q2-2026).
  2026-05-16 IN PROGRESS — M3 complete: Naming policy document exported from SSP annex and
             stored in evidence path. All 41 active identifiers confirmed compliant.
             ISSO signed quarterly review record.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/IA-4?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-025 — IA-5

```text
POAM-ID:          POAM-2026-05-025
CONTROL:          IA-5 — Authenticator Management

WEAKNESS:
  Four deficiencies identified on Links-Matrix (GitHub CI / AWS IAM):
  (1) Gitleaks not in CI — no secret scanning step exists in the GitHub Actions pipeline;
      secrets committed to the repository since the last manual scan are undetected.
  (2) No rotation schedule — no policy document specifying IAM access key rotation interval
      (SSP asserts 90 days) was produced; rotation compliance cannot be verified.
  (3) No pre-commit hook — developers can commit secrets locally without any detection prior
      to push; the last line of defense is absent.
  (4) Credential report access key age unknown — aws iam get-credential-report has not been
      run; access key ages for all IAM users are unverified.

SYSTEM AFFECTED:  Links-Matrix (GitHub CI pipeline, AWS IAM, developer workstations)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/IA-5?env=bad → tool: gitleaks, status: insufficient,
                  ci_scan_configured: false, rotation_schedule: null, precommit_hook: null,
                  access_key_age_verified: false.
                  ITOps interview: no CI scan, no rotation schedule, no pre-commit hook
                  artifact produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/IA-5-2026-05-10/IA-5-finding.json

REMEDIATION OWNER: ITOps (CI pipeline integration and access key rotation) / ISSO (rotation policy sign-off and evidence owner)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Add gitleaks step to GitHub Actions CI pipeline targeting the main branch;
                  run initial full-history scan (gitleaks detect --source .); export JSON
                  report to evidence path; rotate any detected secrets immediately and revoke
                  old credentials.
  M2: 2026-05-14  Install gitleaks pre-commit hook for all developer workstations (or enforce
                  via .pre-commit-config.yaml in repo root); run aws iam get-credential-report
                  to produce access key age inventory; rotate any keys older than 90 days.
  M3: 2026-05-16  Produce rotation schedule policy document specifying 90-day IAM access key
                  rotation interval; ISSO reviews final gitleaks scan report (0 findings
                  required), access key age inventory, and rotation policy; ISSO signs and
                  stores all artifacts in evidence path.

REMEDIATION APPROACH:
  Step 1: In the repository's .github/workflows/ directory, add a gitleaks job:
    - name: Gitleaks secret scan
      uses: gitleaks/gitleaks-action@v2
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  Run the action on the main branch. Additionally run gitleaks detect --source . \
  --report-format json --report-path /tmp/gl-report.json locally and on the CI runner
  to produce the initial evidence artifact.
  Step 2: Add a .pre-commit-config.yaml to the repo root with the gitleaks hook:
    repos:
      - repo: https://github.com/gitleaks/gitleaks
        rev: v8.18.4
        hooks:
          - id: gitleaks
  Distribute the pre-commit install instruction to all developers.
  Step 3: Run aws iam generate-credential-report && aws iam get-credential-report \
    --query 'Content' --output text | base64 -d > /tmp/key-age-report.csv.
  For each access key where access_key_1_last_rotated is older than 90 days:
    aws iam create-access-key --user-name <name>
    # Update applications with new key, then:
    aws iam delete-access-key --access-key-id <old-key-id> --user-name <name>
  Produce a rotation schedule policy document and have ISSO sign it.

VALIDATION COMMAND:
  gitleaks detect --source . --report-format json --report-path /tmp/gl-report.json; jq '. | length' /tmp/gl-report.json
  Expected output: 0

RESIDUAL RISK AFTER REMEDIATION:
  Gitleaks detects secrets matching known patterns but cannot detect custom secret formats
  (e.g., internally-generated API tokens without a recognizable prefix) — a bespoke token
  committed without a pattern match would not be flagged. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Gitleaks not in CI. No rotation schedule. No pre-commit hook.
             Access key ages unverified. ITOps verbal only.
  2026-05-12 IN PROGRESS — M1 complete: Gitleaks CI step added and run. Initial scan
             detected 1 legacy AWS access key committed 8 months ago — rotated and revoked
             same day. JSON report exported to evidence path.
  2026-05-14 IN PROGRESS — M2 complete: Pre-commit hook deployed via .pre-commit-config.yaml.
             Credential report run — 2 keys older than 90 days identified and rotated.
             All 14 active keys now within 90-day rotation window.
  2026-05-16 IN PROGRESS — M3 complete: Rotation schedule policy document produced and
             signed by ISSO. Final gitleaks scan returned 0 findings. All artifacts stored.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/IA-5?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```
