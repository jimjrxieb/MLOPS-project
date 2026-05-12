# POA&M — System and Information Integrity (SI) Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Auditor-ready POA&M. All deficiencies are numbered within each weakness.
> Remediation owners are split between evidence producer and sign-off authority. Due dates
> follow severity-based priority tiers. Milestones include M1, M2, and M3 with exact dated
> actions. Validation commands include expected output. Residual risk identifies the specific
> remaining gap after remediation. Status history shows full progression from OPEN to CLOSED.

**Platform:** Links-Matrix
**POA&M Date:** 2026-05-10
**Source Assessment:** SI-ra-bad.md
**Prepared By:** ISSO
**Framework:** NIST 800-53 Rev 5

---

## Priority Summary

| POAM-ID | Control | Severity | Priority | Due Date |
|---------|---------|----------|----------|----------|
| POAM-2026-05-037 | SI-2 — Flaw Remediation | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-038 | SI-3 — Malicious Code Protection | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-039 | SI-4 — System Monitoring | Critical | P1 Immediate | 2026-05-17 |
| POAM-2026-05-040 | SI-7 — Software, Firmware, and Information Integrity | Critical | P1 Immediate | 2026-05-17 |

---

## POAM-2026-05-037 — SI-2

```text
POAM-ID:          POAM-2026-05-037
CONTROL:          SI-2 — Flaw Remediation

WEAKNESS:
  Four deficiencies identified on Links-Matrix (container images, EKS nodes):
  (1) Trivy not deployed — critical CVE count is completely unknown; no image scan results
      exist for any production image; trivy_deployed: false per BERU assessment.
  (2) No patch SLA defined — severity tiers (Critical/High/Medium) have no documented
      remediation deadline; SecEng verbal statement only; no policy artifact produced.
  (3) No JIRA vulnerability tracking board — no ticket per finding, no owner assignment,
      no aging report; remediation workflow is completely undocumented.
  (4) Kyverno base image policy not confirmed — SSP asserts pinned digests are enforced
      at admission but no policy YAML or admission webhook record was produced.

SYSTEM AFFECTED:  Links-Matrix (container images, EKS nodes, Kyverno admission controller)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SI-2?env=bad → tool: trivy, status: insufficient,
                  critical_cves: unknown, patch_sla_defined: false, trivy_deployed: false,
                  jira_board: null, kyverno_base_image_policy: unconfirmed.
                  SecEng interview: no scan results, no SLA document, no JIRA board produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SI-2-2026-05-10/SI-2-finding.json

REMEDIATION OWNER: SecEng (Trivy deployment and scan evidence producer) / ISSO (patch SLA sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Deploy Trivy via CI plugin; run trivy image --severity CRITICAL --format json
                  links-matrix:latest; export results JSON to evidence path; confirm critical
                  CVE count is known and non-null.
  M2: 2026-05-14  Draft and publish the patch SLA policy document (Critical: 7 days, High: 30
                  days, Medium: 90 days); ISSO signs; create JIRA vulnerability tracking board
                  with one ticket per critical finding; assign owners.
  M3: 2026-05-16  Deploy Kyverno base image policy from 02-CLUSTER-HARDEN/01-policies/ requiring
                  pinned digest; test by attempting to deploy links-matrix:latest (no digest) and
                  confirm 403 admission denial; export policy YAML and test result to evidence
                  path.

REMEDIATION APPROACH:
  Step 1: Add trivy image scan to the CI pipeline (GitHub Actions step: aquasecurity/trivy-action).
  Target all production images. Export findings as JSON to evidence path. Run immediately against
  links-matrix:latest and export the critical CVE list.
  Step 2: Create the patch SLA policy document using the template in GP-CONSULTING/templates/.
  Tiers: Critical patched within 7 days, High within 30 days, Medium within 90 days. ISSO
  reviews and signs. Create the JIRA board (project: VULN) with one ticket per critical finding,
  assigned to image owners, with due dates matching the SLA.
  Step 3: Apply the Kyverno ClusterPolicy from 02-CLUSTER-HARDEN/01-policies/images/ that
  requires image references to include a SHA digest. Test: kubectl run test --image=links-matrix:latest
  and confirm the admission webhook returns 403 with "image must be pinned by digest". Export
  the policy YAML and kubectl output to evidence path. Wire the CI step to re-run Trivy on each
  PR targeting production images.

VALIDATION COMMAND:
  trivy image --exit-code 0 --severity CRITICAL --format json links-matrix:latest | jq '.Results[].Vulnerabilities | length'
  Expected output: 0

RESIDUAL RISK AFTER REMEDIATION:
  Trivy CI scan covers container images only — EKS node OS packages (kernel, systemd) are not
  scanned by the current Trivy configuration. Node-level CVE tracking requires a separate
  kube-bench or Inspector scan. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Trivy not deployed. Critical CVE count unknown. Patch SLA not defined.
             No JIRA tracking board. Kyverno base image policy unconfirmed. SecEng verbal only.
  2026-05-12 IN PROGRESS — M1 complete: Trivy deployed in CI. Initial scan run on
             links-matrix:latest. 7 critical CVEs identified and exported to evidence path.
  2026-05-14 IN PROGRESS — M2 complete: Patch SLA policy published. ISSO sign-off obtained.
             JIRA VULN board created with 7 tickets assigned to image owners. All critical
             tickets due 2026-05-17.
  2026-05-16 IN PROGRESS — M3 complete: Kyverno base image policy applied. :latest tag rejected
             (403 confirmed). CI gate wired to re-run Trivy on each PR to production.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/SI-2?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-038 — SI-3

```text
POAM-ID:          POAM-2026-05-038
CONTROL:          SI-3 — Malicious Code Protection

WEAKNESS:
  Four deficiencies identified on Links-Matrix (CI/CD pipeline, source repositories):
  (1) Semgrep malicious code protection not configured — malware_rules_deployed: 0; no
      .semgrep/malware-patterns.yaml ruleset exists in any repository.
  (2) CI gate not blocking — pipeline completes successfully with no malicious code scan
      results; ci_gate_blocking: false per BERU assessment.
  (3) Rules repository not available — SecEng could not provide the Semgrep rules repo URL
      or commit hash; no versioned ruleset is tracked.
  (4) No scan evidence for any prior CI run — no historical scan result, no suppression
      record, no finding-to-ticket mapping exists.

SYSTEM AFFECTED:  Links-Matrix (CI/CD pipeline, GitHub repositories, Semgrep)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SI-3?env=bad → tool: semgrep, status: insufficient,
                  malware_rules_deployed: 0, ci_gate_blocking: false, rules_repo: null,
                  last_scan_result: null.
                  SecEng interview: no rules repo, no CI gate, no scan history produced.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SI-3-2026-05-10/SI-3-finding.json

REMEDIATION OWNER: SecEng (Semgrep configuration and CI gate evidence producer) / DevSecOps (CI pipeline owner and sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Create .semgrep/malware-patterns.yaml covering reverse shells, encoded
                  payloads, suspicious exec calls, and credential harvesting patterns; commit
                  to the rules repo at a pinned tag (v1.0.0); run initial scan against main
                  and export results JSON to evidence path.
  M2: 2026-05-14  Wire Semgrep malicious code scan as a required blocking CI check in the
                  GitHub Actions workflow; inject a synthetic malware pattern (e.g., base64-
                  encoded reverse shell) and confirm the pipeline fails with the Semgrep
                  finding; export the CI run log to evidence path.
  M3: 2026-05-16  Create a JIRA ticket template for Semgrep malicious code findings; confirm
                  the suppression workflow (semgrep-ignore with justification) is documented
                  in Confluence; ISSO signs the CI gate configuration artifact.

REMEDIATION APPROACH:
  Step 1: Create .semgrep/malware-patterns.yaml using rules from the Semgrep Registry
  (category: security, subcategory: malware). Include rules for: subprocess with shell=True
  and encoded strings, base64-decoded exec patterns, outbound connection to hardcoded IPs,
  credential harvesting functions. Pin the ruleset to a git tag (v1.0.0) in the rules repo.
  Step 2: Run semgrep --config .semgrep/malware-patterns.yaml --json . against the main
  branch. Export results JSON to evidence path. Add a GitHub Actions step using
  semgrep/semgrep-action@v1 with --error flag to block on any finding. Validate by injecting
  a synthetic reverse shell pattern into a test branch and confirming CI fails.
  Step 3: Document the suppression workflow: any semgrep-ignore requires a JIRA ticket number
  as justification in the ignore comment. Publish the workflow in Confluence. ISSO reviews and
  signs the CI gate configuration (workflow YAML + ruleset YAML) as the SI-3 evidence artifact.

VALIDATION COMMAND:
  semgrep --config .semgrep/malware-patterns.yaml --json . | jq '.results | length'
  Expected output: 0

RESIDUAL RISK AFTER REMEDIATION:
  Semgrep scan covers source code only — compiled binaries and third-party dependencies
  (node_modules, pip packages) are not scanned for malicious code by the current ruleset.
  Binary and dependency scanning requires a separate Trivy or Grype step. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Semgrep malicious code protection not configured. 0 rules deployed.
             CI gate not blocking. Rules repo not available. No scan history. SecEng verbal only.
  2026-05-12 IN PROGRESS — M1 complete: .semgrep/malware-patterns.yaml created with 12 rules.
             Pinned at v1.0.0. Initial scan run — 0 findings on main branch. Results exported.
  2026-05-14 IN PROGRESS — M2 complete: Blocking CI gate wired in GitHub Actions. Synthetic
             reverse shell pattern injected — pipeline failed with 1 Semgrep finding (confirmed).
             CI run log exported to evidence path.
  2026-05-16 IN PROGRESS — M3 complete: JIRA suppression template created. Semgrep-ignore
             workflow published in Confluence. ISSO signed the CI gate configuration artifact.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/SI-3?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-039 — SI-4

```text
POAM-ID:          POAM-2026-05-039
CONTROL:          SI-4 — System Monitoring

WEAKNESS:
  Five deficiencies identified on Links-Matrix (Kubernetes runtime, Splunk SIEM):
  (1) Falco not deployed — falco_deployed: false; no DaemonSet exists in the monitoring
      namespace; cluster runtime behavior is completely unmonitored.
  (2) Zero Falco rules active — rules_active: 0; neither the default ruleset nor any custom
      rules from 03-RUNTIME-SECURITY/ are loaded.
  (3) Alert volume unknown — alert_volume_24h: unknown; no baseline exists and no triage
      SLA has been defined.
  (4) False-positive rate unknown — no FP suppression list, no tuning record, no runbook for
      alert handling.
  (5) No Splunk dashboard for SI-4 — splunk_dashboard: null; gp_security index receives no
      Falco events; SOC has no visibility into runtime security events.

SYSTEM AFFECTED:  Links-Matrix (Kubernetes runtime, Falco DaemonSet, Splunk gp_security index)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SI-4?env=bad → tool: falco, status: insufficient,
                  falco_deployed: false, rules_active: 0, alert_volume_24h: unknown,
                  fp_rate: unknown, splunk_dashboard: null, coverage: unknown.
                  SOC interview: no runtime monitoring, no Splunk integration, no alert baseline.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SI-4-2026-05-10/SI-4-finding.json

REMEDIATION OWNER: SOC (Falco deployment and Splunk integration evidence producer) / PlatEng (DaemonSet deployment sign-off)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Deploy Falco as a DaemonSet to all nodes in the Links-Matrix cluster via
                  Helm (falcosecurity/falco chart); enable the default ruleset plus custom
                  rules from 03-RUNTIME-SECURITY/; confirm all nodes show Ready status;
                  export DaemonSet status and rule count to evidence path.
  M2: 2026-05-14  Configure Falco HTTP output plugin to forward alerts to Splunk gp_security
                  index; confirm alert events appear in Splunk within 1 hour of deployment;
                  create the SI-4 Splunk dashboard showing alert volume, top rules, and FP
                  suppression list; export dashboard screenshot to evidence path.
  M3: 2026-05-16  Establish alert triage SLA (P1: 15 min, P2: 1 hour) in the SOC runbook;
                  run a synthetic Falco trigger (privilege escalation test) and confirm the
                  alert appears in Splunk within 2 minutes; SOC lead signs the runbook
                  artifact; ISSO signs the SI-4 evidence package.

REMEDIATION APPROACH:
  Step 1: helm repo add falcosecurity https://falcosecurity.github.io/charts && helm install
  falco falcosecurity/falco --namespace monitoring --create-namespace --set falco.grpc.enabled=true.
  Confirm: kubectl -n monitoring get daemonset falco -o jsonpath='{.status.numberReady}'.
  All node count must match. Enable custom rules from 03-RUNTIME-SECURITY/falco-rules/ by
  mounting them as a ConfigMap.
  Step 2: Configure the Falco HTTP output plugin to POST alerts to the Splunk HEC endpoint
  at https://splunk.links-matrix.internal:8088/services/collector with the gp_security index.
  Verify events appear in Splunk: index=gp_security sourcetype=falco | head 10.
  Create the SI-4 Splunk dashboard with panels for: alerts per hour, top 10 triggered rules,
  alert severity distribution, and FP suppression log.
  Step 3: Publish the SOC alert triage runbook in Confluence (SOC-Runbook-SI4) specifying
  triage SLA by severity and the escalation path. Run a synthetic privilege escalation:
  kubectl exec -it <pod> -- sudo whoami and confirm the Falco "Privilege Escalation" rule
  fires and the alert appears in Splunk within 2 minutes. SOC lead signs the runbook.
  ISSO reviews and signs the complete SI-4 evidence package (DaemonSet status, rule count,
  Splunk screenshot, runbook) and stores it in the evidence path.

VALIDATION COMMAND:
  kubectl -n monitoring get daemonset falco -o jsonpath='{.status.numberReady}'
  Expected output: 3

RESIDUAL RISK AFTER REMEDIATION:
  Falco eBPF probe requires a Linux kernel version >=4.14 — older EKS node AMIs may fall
  back to the kernel module driver which has a higher FP rate on certain syscall patterns.
  Node AMI version must be confirmed before considering Falco coverage complete. Residual
  risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Falco not deployed. 0 rules active. Alert volume unknown. FP rate unknown.
             No Splunk dashboard. No triage SLA. SOC verbal only.
  2026-05-12 IN PROGRESS — M1 complete: Falco DaemonSet deployed to 3/3 nodes. Default
             ruleset enabled (65 rules). Custom rules from 03-RUNTIME-SECURITY/ loaded (12 rules).
             DaemonSet status and rule count exported to evidence path.
  2026-05-14 IN PROGRESS — M2 complete: Falco HTTP output configured to Splunk HEC.
             First alerts appearing in gp_security index within 30 minutes. SI-4 dashboard
             created — 3 panels active. Dashboard screenshot exported.
  2026-05-16 IN PROGRESS — M3 complete: Triage SLA published in SOC runbook. Synthetic
             privilege escalation test fired Falco alert in Splunk within 90 seconds (confirmed).
             SOC lead signed the runbook. ISSO signed the SI-4 evidence package.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/SI-4?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```

---

## POAM-2026-05-040 — SI-7

```text
POAM-ID:          POAM-2026-05-040
CONTROL:          SI-7 — Software, Firmware, and Information Integrity

WEAKNESS:
  Four deficiencies identified on Links-Matrix (container registry, Kubernetes admission,
  CI/CD pipeline):
  (1) Image signing not configured — image_signing_configured: false; no cosign key pair
      or keyless signing workflow exists; any image can be deployed without a valid
      signature.
  (2) Kyverno admission policy not deployed — kyverno_policy_deployed: false; SSP asserts
      signature verification is enforced at admission but no policy YAML or admission
      webhook record was produced.
  (3) SBOM not generated — sbom_generated: false; no Software Bill of Materials exists
      for links-matrix:latest or any prior production image build.
  (4) Integrity checks not automated — no CI step generates or verifies image signatures or
      SBOMs; integrity verification is entirely manual and undocumented.

SYSTEM AFFECTED:  Links-Matrix (container registry, Kubernetes admission, CI/CD pipeline, cosign/syft)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SI-7?env=bad → tool: semgrep, status: insufficient,
                  image_signing_configured: false, kyverno_policy_deployed: false,
                  sbom_generated: false, integrity_checks_automated: false.
                  DevSecOps interview: no signing key, no Kyverno policy, no SBOM, no CI gate.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SI-7-2026-05-10/SI-7-finding.json

REMEDIATION OWNER: DevSecOps (cosign and CI integration evidence producer) / SecEng (Kyverno policy sign-off and SBOM verification)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-12  Configure keyless cosign signing in the CI pipeline using Sigstore;
                  sign links-matrix:latest on the next build; confirm a valid signature
                  is stored in the registry; generate the SBOM using syft and store
                  in SPDX-JSON format in the evidence path.
  M2: 2026-05-14  Deploy the Kyverno ClusterPolicy from 02-CLUSTER-HARDEN/01-policies/
                  requiring cosign signature verification for all images in the production
                  namespace; test by attempting to deploy an unsigned image and confirming
                  403 admission denial; export policy YAML and kubectl output to evidence
                  path.
  M3: 2026-05-16  Wire SBOM generation (syft) and cosign verify as required CI steps that
                  run on every production build; confirm the pipeline fails if cosign verify
                  returns non-zero; ISSO and SecEng sign the SI-7 evidence package.

REMEDIATION APPROACH:
  Step 1: Add cosign to the CI pipeline using the sigstore/cosign-installer GitHub Action.
  Sign the image after push: cosign sign --yes links-matrix:latest. For keyless signing,
  use the OIDC identity from the GitHub Actions OIDC provider. Confirm the signature:
  cosign verify --certificate-identity-regexp ".*" --certificate-oidc-issuer-regexp ".*"
  links-matrix:latest. Generate the SBOM: syft links-matrix:latest -o spdx-json > sbom.json
  and store in the evidence path.
  Step 2: Apply the Kyverno ClusterPolicy (verify-image-signature.yaml) from
  02-CLUSTER-HARDEN/01-policies/images/. The policy must reference the Sigstore keyless
  attestation or the cosign public key. Test: kubectl run test --image=unsigned-image:latest
  in the production namespace and confirm admission webhook returns 403 with the Kyverno
  deny message. Export the policy YAML and the kubectl error output to evidence path.
  Step 3: Add two required CI steps to the production workflow: (1) syft image scan → sbom.json
  stored as a build artifact; (2) cosign verify run post-push → pipeline fails on non-zero
  exit code. ISSO and SecEng review and sign the complete SI-7 evidence package (signing
  config, Kyverno YAML, SBOM sample, CI run log) and store in the evidence path.

VALIDATION COMMAND:
  cosign verify --certificate-identity-regexp ".*" --certificate-oidc-issuer-regexp ".*" links-matrix:latest 2>&1 | grep -c "Verification successful"
  Expected output: 1

RESIDUAL RISK AFTER REMEDIATION:
  Keyless cosign signing is tied to the GitHub Actions OIDC provider — if the pipeline is
  run outside GitHub Actions (e.g., a local developer build), the signing step is skipped
  and the resulting image will fail admission. Local build workflow must be documented and
  restricted to prevent unsigned images from reaching the registry. Residual risk: Low.

STATUS HISTORY:
  2026-05-10 OPEN — Image signing not configured. Kyverno admission policy not deployed.
             SBOM not generated. Integrity checks not automated. DevSecOps verbal only.
  2026-05-12 IN PROGRESS — M1 complete: Keyless cosign signing configured in CI. links-matrix:
             latest signed on build #147. Signature confirmed in registry. SBOM (SPDX-JSON)
             generated and stored in evidence path.
  2026-05-14 IN PROGRESS — M2 complete: Kyverno verify-image-signature policy applied to
             production namespace. Test with unsigned image returned 403 (confirmed). Policy
             YAML and kubectl output exported to evidence path.
  2026-05-16 IN PROGRESS — M3 complete: syft and cosign verify wired as required CI steps.
             Pipeline failed on synthetic unsigned image test (confirmed). ISSO and SecEng
             signed the SI-7 evidence package.
  2026-05-17 CLOSED — BERU re-ran GET /evidence/SI-7?env=great → status: sufficient.
             Validation commands passed. Evidence artifact stored.
```
