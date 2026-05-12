# Risk Assessment Evidence — SI Family
## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** Evidence collected fully supports all SSP claims. Control owners provided
> exact artifacts, dates, version numbers, and metrics on first request. Tool queries returned
> complete structured data with no gaps. Every SSP claim is traceable to a specific artifact
> with a retrievable location. All four controls receive PASS findings. No POA&M items required.
> This is the evidence standard a 3PAO expects to walk in and find.

**Assessment Date:** 2026-05-10
**Assessor:** GRC Engineer (grc-engineer group — read-only)
**Framework:** NIST 800-53 Rev 5
**Graded Against:** Links-Matrix SSP (see ssp-examples/SI-ssp-great.md)

---

## SI-2 — Flaw Remediation

**Control Owner:** SecEng
**Evidence Producer:** SecEng
**Cadence:** Continuous; SLA-tracked

### SSP Claim
> The SSP asserts that Trivy scans all images continuously. 0 critical CVEs are unpatched.
> Patch SLAs are Critical: 7 days, High: 30 days, Medium: 90 days. 23 patches were applied
> in the last 30 days with 100% SLA compliance. A JIRA patch tracking board is maintained
> and a base image policy enforces Kyverno: require-non-root-base and max-image-age-30d.

### Evidence Request

**Interview — Questions asked of control owner (SecEng):**
1. Show me open CVEs above high severity.
2. Show me your patch SLA and compliance rate.

**Tool Query:** `GET /evidence/SI-2?env=great` — simulates: trivy

**Tool Evidence (API Response):**
```json
{
  "control": "SI-2", "env": "great", "tool": "trivy",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "sufficient",
  "data": {
    "patches_applied_30d": 23,
    "critical_unpatched": 0,
    "patch_sla_compliance": "100%",
    "patch_tracking_artifact": "JIRA: SEC-patch-board",
    "base_image_policy": "Kyverno: require-non-root-base + max-image-age-30d"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "23 patches applied in last 30 days — all within SLA. 0 critical CVEs unpatched.
> Patch SLA: Critical 7 days, High 30 days, Medium 90 days — documented in
> Confluence: vuln-sla-policy-v2.md. JIRA patch tracking board is SEC-patch-board
> — 100% SLA compliance for last 30 days. Kyverno base image policies:
> require-non-root-base.yaml and max-image-age-30d.yaml — both in
> platform-gitops/policies/si/."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 23 patches in 30 days; 0 critical unpatched; 100% SLA compliance; JIRA tracking board named; Kyverno policies named and located

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 0 critical CVEs; 23 patches in SLA; 100% compliance rate; JIRA tracking; Kyverno base image policy |
| Impact | Low | Automated scanning with SLA enforcement; JIRA audit trail; base image freshness enforced |
| **Residual Risk** | **Low** | All SSP claims verified by Trivy data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 0 critical CVEs unpatched, 23 patches in 30 days with 100% SLA compliance, JIRA board, and Kyverno policies confirmed for SI-2.
CONTROL: SI-2 — Flaw Remediation
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - SecEng interview (patch count, critical count, SLA compliance rate, JIRA board name, Kyverno policy names and paths produced)
  - Trivy query (23 patches, 0 critical_unpatched, 100% SLA compliance, JIRA SEC-patch-board, Kyverno policies)
  - Patch tracking: JIRA: SEC-patch-board (100% SLA compliance last 30 days)
  - Base image policies: platform-gitops/policies/si/require-non-root-base.yaml + max-image-age-30d.yaml
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: SecEng (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Flaw remediation is fully implemented. Zero critical CVEs, 100% patch SLA compliance, JIRA tracking, and Kyverno base image freshness enforcement. This control is audit-ready.
```

---

## SI-3 — Malicious Code Protection

**Control Owner:** SecEng
**Evidence Producer:** SecEng
**Cadence:** Continuous

### SSP Claim
> The SSP asserts that Semgrep runs 47 malicious code detection rules in CI. The CI gate
> blocks on critical findings. 0 critical findings have passed since last rule update
> (2026-04-20). Rules are in git: semgrep-rules/security/. The last rule update was
> 2026-04-20.

### Evidence Request

**Interview — Questions asked of control owner (SecEng):**
1. Show me your malicious code detection rules in CI.
2. Does it block or warn on critical findings?

**Tool Query:** `GET /evidence/SI-3?env=great` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "SI-3", "env": "great", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "sufficient",
  "data": {
    "malicious_pattern_rules": 47,
    "ci_gate_active": true,
    "block_on_critical": true,
    "last_rule_update": "2026-04-20",
    "rule_repo": "git: semgrep-rules/security/",
    "zero_critical_findings": true
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "47 Semgrep rules in CI — blocking mode on critical findings. 0 critical findings
> have passed the gate since the last rule update on 2026-04-20. Rules are in
> git: semgrep-rules/security/ on the main branch. The gate runs on every push
> and PR — GitHub Actions: semgrep-gate.yaml. CI results are logged to Splunk
> gp_vulnerability index."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 47 rules; blocking on critical; 0 critical findings passing; rule repo named; last update date confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 47 rules; blocking on critical; 0 critical findings passing; rules version-controlled |
| Impact | Low | Blocking mode prevents malicious code from reaching production; Splunk audit trail |
| **Residual Risk** | **Low** | All SSP claims verified by Semgrep data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 47 Semgrep rules in blocking mode with 0 critical findings passing and rules in git confirmed for SI-3.
CONTROL: SI-3 — Malicious Code Protection
ENHANCEMENT: None
STATUS: PASS
EVIDENCE REVIEWED:
  - SecEng interview (47 rules, blocking mode, 0 critical findings, rule repo path, last update date produced)
  - Semgrep query (47 malicious pattern rules, ci_gate blocking, 0 critical findings, last_rule_update 2026-04-20)
  - Rule repo: git: semgrep-rules/security/ (main branch)
  - CI gate: GitHub Actions semgrep-gate.yaml + Splunk gp_vulnerability logging
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: SecEng (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Malicious code protection is fully implemented. 47 Semgrep rules in blocking mode, 0 critical findings passing, rules version-controlled, and CI gate integrated with Splunk. This control is audit-ready.
```

---

## SI-4 — System Monitoring

**Control Owner:** SOC
**Evidence Producer:** SOC
**Cadence:** Continuous; monthly report

### SSP Claim
> The SSP asserts that Falco provides continuous monitoring with 65 rules. Alert volume
> is 1,847 per 30 days with a 3% false positive rate. 12 rules have been tuned. A Splunk
> dashboard (gp_security/falco-monitoring) provides real-time visibility. Coverage score
> is 92%.

### Evidence Request

**Interview — Questions asked of control owner (SOC):**
1. Show me your monitoring rule count and alert volume.
2. Show me your false positive rate.

**Tool Query:** `GET /evidence/SI-4?env=great` — simulates: falco

**Tool Evidence (API Response):**
```json
{
  "control": "SI-4", "env": "great", "tool": "falco",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:10:00Z", "status": "sufficient",
  "data": {
    "monitoring_rules_active": 65,
    "alert_volume_30d": 1847,
    "false_positive_rate": 0.03,
    "tuned_rules": 12,
    "splunk_dashboard": "gp_security/falco-monitoring",
    "coverage_score": "92%"
  }
}
```

**Interview Response (Control Owner — SOC):**
> "65 Falco rules active. 1,847 alerts in last 30 days, 3% false positive rate —
> we've tuned 12 rules to get there. Splunk dashboard is gp_security/falco-monitoring
> — real-time visibility for SOC. Coverage score is 92% based on MITRE ATT&CK
> mapping of our Falco rule set. Monthly report is at
> s3://links-matrix-audit/si4-monthly-2026-04.pdf."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — 65 rules; 1,847 alert volume; 3% FP rate; 12 tuned rules; Splunk dashboard named; 92% coverage

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | 65 rules; FP rate tracked and managed to 3%; coverage score 92%; Splunk dashboard active |
| Impact | Low | Monthly report with S3 artifact; MITRE ATT&CK coverage scoring; real-time SOC visibility |
| **Residual Risk** | **Low** | All SSP claims verified by Falco data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: 65 Falco rules, 1,847 alerts/30d, 3% FP rate, 12 tuned rules, Splunk dashboard, and 92% coverage confirmed for SI-4.
CONTROL: SI-4 — System Monitoring
ENHANCEMENT: SI-4(2) — Automated Tools and Mechanisms for Real-Time Analysis
STATUS: PASS
EVIDENCE REVIEWED:
  - SOC interview (rule count, alert volume, FP rate, tuned rules, Splunk dashboard, coverage score, monthly report produced)
  - Falco query (65 rules, 1847 alerts, 0.03 FP rate, 12 tuned, splunk_dashboard, 92% coverage)
  - Splunk dashboard: gp_security/falco-monitoring (real-time SOC visibility)
  - Monthly report: s3://links-matrix-audit/si4-monthly-2026-04.pdf
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: SOC (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: System monitoring is fully implemented. 65 Falco rules, 3% false positive rate, 92% MITRE ATT&CK coverage, real-time Splunk dashboard, and monthly reports. This control is audit-ready.
```

---

## SI-7 — Software, Firmware, and Information Integrity

**Control Owner:** DevSecOps
**Evidence Producer:** DevSecOps
**Cadence:** Continuous

### SSP Claim
> The SSP asserts that all container images are signed with cosign and sigstore. Admission
> is enforced via Kyverno policy require-image-signature.yaml. SBOMs are generated for all
> images. Integrity checks run on every push and daily scheduled scan.

### Evidence Request

**Interview — Questions asked of control owner (DevSecOps):**
1. Show me how container images are signed and how signing is enforced at admission.

**Tool Query:** `GET /evidence/SI-7?env=great` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "SI-7", "env": "great", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:15:00Z", "status": "sufficient",
  "data": {
    "signing_enabled": true,
    "signing_tool": "cosign + sigstore",
    "admission_enforced": true,
    "kyverno_policy": "require-image-signature.yaml",
    "sbom_generated": true,
    "integrity_check_cadence": "every push + daily scheduled"
  }
}
```

**Interview Response (Control Owner — DevSecOps):**
> "All images signed with cosign and sigstore during the CI pipeline — signature
> is pushed to the same registry as the image. Kyverno policy require-image-signature.yaml
> enforces at admission — unsigned images are rejected. SBOM is generated by Trivy
> during the scan step and attached to the image manifest. Integrity checks run
> on every push via GitHub Actions and daily at 02:00 via scheduled workflow."

### Risk Assessment

**Evidence Quality:** Sufficient
**SSP Claim Verified:** Yes — cosign + sigstore signing; Kyverno admission enforcement; SBOM generated; push + daily cadence all confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Low | Image signing enforced at admission; unsigned images blocked by Kyverno; SBOM attached to manifest |
| Impact | Low | Admission enforcement means tampered images cannot be deployed even if signing is bypassed |
| **Residual Risk** | **Low** | All SSP claims verified by Semgrep data and produced artifacts |

**Finding:** PASS
**Evidence Gap:** None

**BERU Finding:**
```
FINDING: cosign + sigstore signing, Kyverno admission enforcement, SBOM generation, and push + daily integrity checks confirmed for SI-7.
CONTROL: SI-7 — Software, Firmware, and Information Integrity
ENHANCEMENT: SI-7(1) — Integrity Checks
STATUS: PASS
EVIDENCE REVIEWED:
  - DevSecOps interview (signing tool, signature registry, Kyverno policy name, SBOM method, integrity cadence produced)
  - Semgrep query (signing_enabled true, cosign+sigstore, admission_enforced true, require-image-signature.yaml, SBOM true)
  - Kyverno admission policy: require-image-signature.yaml (platform-gitops/policies/si/)
  - SBOM: Trivy SBOM attached to image manifest during CI scan step
  - Integrity cadence: every push + daily 02:00 UTC scheduled scan
EVIDENCE GAP: None
RISK:
  Likelihood: Low
  Impact: Low
  Residual Risk: Low
CONTROL OWNER: DevSecOps (accountability and evidence producer)
POA&M ITEM: N/A
CISO SUMMARY: Software integrity is fully implemented. cosign signing enforced at admission via Kyverno, SBOM generated for all images, and integrity checks run on every push and daily schedule. This control is audit-ready.
```
