# POA&M — System and Information Integrity (SI) Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** POA&M items reflect specific evidence gaps from the BERU assessment.
> Control owners are identified by role. Due dates follow severity-based priority tiers.
> Milestones cover M1 and M2 with actionable steps. Validation commands are real tool queries.
> Residual risk is acknowledged but remains generic. Status history includes opening reason.

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
  Trivy is not deployed and no patch SLA, CVE counts, or remediation tracking exist.
  Critical CVE count is unknown. No JIRA tracking board for patch management. Kyverno
  base image policies not confirmed. No evidence of a defined patch SLA for any severity
  tier.

SYSTEM AFFECTED:  Links-Matrix (container images, EKS nodes)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SI-2?env=bad → tool: trivy, status: insufficient,
                  critical_cves: unknown, patch_sla_defined: false, trivy_deployed: false.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SI-2-2026-05-10/

REMEDIATION OWNER: SecEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Deploy Trivy to CI pipeline and run initial image scan against
                  links-matrix:latest; export critical CVE findings JSON to evidence path.
  M2: 2026-05-15  Define and document patch SLA (Critical: 7 days, High: 30 days);
                  create JIRA tracking board and link from evidence path; confirm Kyverno
                  base image policy is deployed and blocking :latest tags.

REMEDIATION APPROACH:
  Install Trivy via Helm or CI plugin and run against all production images. Export critical
  CVE count and CVSS scores to the evidence path. Define the patch SLA policy document with
  severity tiers and owner assignments. Create the JIRA vulnerability tracking board and import
  Trivy findings. Deploy the Kyverno policy from 02-CLUSTER-HARDEN/01-policies/ that requires
  pinned base image digests and blocks :latest. Confirm the policy is enforced by attempting to
  deploy an image with :latest tag and verifying admission denial.

VALIDATION COMMAND:
  trivy image --exit-code 0 --severity CRITICAL --format json links-matrix:latest | jq '.Results[].Vulnerabilities | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Trivy not deployed. Critical CVE count unknown. Patch SLA not defined.
             No JIRA tracking board. Kyverno base image policy not confirmed.
```

---

## POAM-2026-05-038 — SI-3

```text
POAM-ID:          POAM-2026-05-038
CONTROL:          SI-3 — Malicious Code Protection

WEAKNESS:
  Semgrep malicious code protection is not configured and the CI gate does not block for
  SI-3. Zero Semgrep rules are deployed for malicious code patterns. The rules repository
  is not available. CI pipeline passes with no malicious code scan results.

SYSTEM AFFECTED:  Links-Matrix (CI/CD pipeline, source repositories)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SI-3?env=bad → tool: semgrep, status: insufficient,
                  malware_rules_deployed: 0, ci_gate_blocking: false,
                  rules_repo: null.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SI-3-2026-05-10/

REMEDIATION OWNER: SecEng (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Configure Semgrep with the .semgrep/malware-patterns.yaml ruleset targeting
                  known malicious code patterns; run initial scan against the main branch;
                  export results JSON to evidence path.
  M2: 2026-05-15  Wire the Semgrep malicious code scan as a blocking CI gate; confirm the
                  pipeline fails on a synthetic malware-pattern test case; document the
                  rules repo location and gate configuration in evidence path.

REMEDIATION APPROACH:
  Create or obtain the .semgrep/malware-patterns.yaml ruleset covering known malicious code
  patterns (e.g., reverse shells, encoded payloads, suspicious exec calls). Run an initial
  Semgrep scan against the full repository and export findings as JSON. Wire the scan as a
  required CI check in the GitHub Actions workflow, configured to block merge on any findings.
  Validate the gate by injecting a synthetic malware pattern and confirming the pipeline fails.
  Store the rules file path and CI configuration in the evidence path.

VALIDATION COMMAND:
  semgrep --config .semgrep/malware-patterns.yaml --json . | jq '.results | length'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Semgrep malicious code protection not configured. 0 rules deployed.
             CI gate not blocking. Rules repo not available.
```

---

## POAM-2026-05-039 — SI-4

```text
POAM-ID:          POAM-2026-05-039
CONTROL:          SI-4 — System Monitoring

WEAKNESS:
  Falco is not deployed and no system monitoring rules, alert volume, or Splunk dashboard
  exist. Zero Falco rules are active. Alert volume and false-positive rate are unknown.
  No Splunk dashboard for runtime security events. Coverage of monitored system behaviors
  is completely unknown.

SYSTEM AFFECTED:  Links-Matrix (Kubernetes runtime, Splunk SIEM)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SI-4?env=bad → tool: falco, status: insufficient,
                  falco_deployed: false, rules_active: 0, alert_volume_24h: unknown,
                  splunk_dashboard: null.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SI-4-2026-05-10/

REMEDIATION OWNER: SOC (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Deploy Falco as a DaemonSet to the Links-Matrix cluster using the Helm chart;
                  confirm Falco is running on all nodes; enable the default ruleset and export
                  rule count to evidence path.
  M2: 2026-05-15  Configure Falco output to ship alerts to Splunk (gp_security index); create
                  the Splunk SI-4 monitoring dashboard; confirm alert volume appears within
                  24 hours of deployment; export dashboard screenshot to evidence path.

REMEDIATION APPROACH:
  Deploy Falco via Helm (helm install falco falcosecurity/falco --namespace monitoring) and
  confirm the DaemonSet is running on all nodes. Enable the default Falco ruleset and any
  custom rules from 03-RUNTIME-SECURITY/. Configure Falco's output to forward alerts to
  Splunk using the HTTP output plugin or Fluent Bit forwarder. Create the SI-4 Splunk
  dashboard in the gp_security index showing alert volume, rule match rate, and top triggered
  rules. Monitor for 24 hours and export the dashboard screenshot and alert count to the
  evidence path.

VALIDATION COMMAND:
  kubectl -n monitoring get daemonset falco -o jsonpath='{.status.numberReady}'

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Falco not deployed. 0 rules active. Alert volume unknown.
             FP rate unknown. No Splunk dashboard. Coverage unknown.
```

---

## POAM-2026-05-040 — SI-7

```text
POAM-ID:          POAM-2026-05-040
CONTROL:          SI-7 — Software, Firmware, and Information Integrity

WEAKNESS:
  Container image signing is not configured and Kyverno admission enforcement and SBOM
  generation are absent. Image signing has not been set up. No Kyverno admission policy
  enforces signature verification at deploy time. No SBOM has been generated for any
  production image. Integrity checks are not automated in CI or at admission.

SYSTEM AFFECTED:  Links-Matrix (container registry, Kubernetes admission, CI/CD)

SEVERITY:         Critical

DETECTION DATE:   2026-05-10
DETECTION METHOD: GET /evidence/SI-7?env=bad → tool: semgrep, status: insufficient,
                  image_signing_configured: false, kyverno_policy_deployed: false,
                  sbom_generated: false, integrity_checks_automated: false.

EVIDENCE PATH:    GP-S3/6-seclab-reports/cybersec-evidence/poam/SI-7-2026-05-10/

REMEDIATION OWNER: DevSecOps (accountability and evidence producer)

SCHEDULED COMPLETION: 2026-05-17

MILESTONES:
  M1: 2026-05-13  Configure cosign to sign the links-matrix:latest image in the CI pipeline;
                  confirm a valid signature exists in the registry; generate an SBOM using
                  syft and store it in the evidence path.
  M2: 2026-05-15  Deploy the Kyverno policy from 02-CLUSTER-HARDEN/01-policies/ that requires
                  cosign signature verification at admission; confirm unsigned image deployment
                  is rejected; export the policy YAML and admission test result to evidence
                  path.

REMEDIATION APPROACH:
  Install cosign and configure the CI pipeline to sign the links-matrix image on every build
  using a keyless signature (Sigstore). Run cosign sign links-matrix:latest and confirm the
  signature appears in the registry. Generate an SBOM using syft: syft links-matrix:latest -o
  spdx-json > sbom.json and store in the evidence path. Deploy the Kyverno ClusterPolicy
  requiring cosign verification for all images in production namespaces. Test by attempting to
  deploy an unsigned image and confirming admission denial. Wire SBOM generation as a CI step
  that runs on every build.

VALIDATION COMMAND:
  cosign verify --certificate-identity-regexp ".*" --certificate-oidc-issuer-regexp ".*" links-matrix:latest 2>&1 | grep -c "Verification successful"

RESIDUAL RISK AFTER REMEDIATION: Low after remediation

STATUS HISTORY:
  2026-05-10 OPEN — Image signing not configured. Kyverno admission policy not deployed.
             SBOM not generated. Integrity checks not automated.
```
