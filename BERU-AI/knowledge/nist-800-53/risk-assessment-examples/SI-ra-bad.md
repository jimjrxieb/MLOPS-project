# Risk Assessment Evidence — SI Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** Evidence collected for all four System and Information Integrity controls
> is incomplete and unverifiable. Control owners provided vague verbal assurances with no
> supporting artifacts. Tool queries returned null or error responses indicating integrity
> tooling is not deployed or not configured. All four findings are FAIL; all require POA&M items.

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

**Tool Query:** `GET /evidence/SI-2?env=bad` — simulates: trivy

**Tool Evidence (API Response):**
```json
{
  "control": "SI-2", "env": "bad", "tool": "trivy",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "patches_applied_30d": null,
    "critical_unpatched": null,
    "patch_sla_days": null,
    "error": "No patch remediation records"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "We patch things when we can. Trivy hasn't been set up yet. I don't have a
> formal patch SLA. Critical CVEs — I'm not sure what the current count is."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Trivy not deployed; critical CVE count unknown; no patch SLA; no tracking artifact |
| Impact | Critical | Unknown critical CVEs in production are exploitable without any defined remediation timeline |
| **Residual Risk** | **Critical** | Flaw remediation posture entirely unverifiable |

**Finding:** FAIL
**Evidence Gap:** Trivy not deployed. Critical CVE count unknown. Patch SLA not defined. No patch tracking artifact. Kyverno base image policies not confirmed.

**BERU Finding:**
```
FINDING: Trivy is not deployed and no patch SLA, CVE counts, or remediation tracking exist for SI-2.
CONTROL: SI-2 — Flaw Remediation
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - SecEng verbal statement (patching described ad hoc, Trivy not set up, SLA not defined)
  - Trivy query (no patch records, critical_unpatched null, patch_sla null)
EVIDENCE GAP: Trivy not deployed, critical CVE count unknown, patch SLA not defined, no JIRA tracking board, Kyverno base image policies not confirmed
RISK:
  Likelihood: High
  Impact: Critical
  Residual Risk: Critical
CONTROL OWNER: SecEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Flaw remediation cannot be evidenced. Trivy is not deployed and no patch SLA exists. Critical CVEs may be present in production without any remediation timeline. Deploy Trivy and establish the patch SLA immediately.
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

**Tool Query:** `GET /evidence/SI-3?env=bad` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "SI-3", "env": "bad", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "malicious_pattern_rules": 0,
    "ci_gate_active": false,
    "error": "No malicious code protection scan configured"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "We have some SAST scanning. Semgrep for malicious code — it's not configured
> specifically for that. CI gate — it runs but I don't think it blocks on anything
> yet."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Semgrep malicious code protection not configured; 0 rules; CI gate not blocking |
| Impact | High | Without blocking CI gate, malicious code patterns can reach production |
| **Residual Risk** | **Critical** | Malicious code protection entirely absent |

**Finding:** FAIL
**Evidence Gap:** Semgrep malicious code protection not configured. Zero detection rules. CI gate not blocking. Rules repo not available.

**BERU Finding:**
```
FINDING: Semgrep malicious code protection is not configured and the CI gate does not block for SI-3.
CONTROL: SI-3 — Malicious Code Protection
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - SecEng verbal statement (SAST running, malicious code rules not configured, no block)
  - Semgrep query (0 malicious pattern rules, ci_gate_active false)
EVIDENCE GAP: Semgrep malicious code protection not configured, 0 rules, CI gate not blocking, rules repo not available
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: SecEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Malicious code protection is absent from the CI pipeline. Semgrep is not configured for malicious code detection and the CI gate does not block. Configure 47 detection rules and enable blocking mode before the next assessment.
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

**Tool Query:** `GET /evidence/SI-4?env=bad` — simulates: falco

**Tool Evidence (API Response):**
```json
{
  "control": "SI-4", "env": "bad", "tool": "falco",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "monitoring_rules_active": 0,
    "alert_volume_30d": null,
    "error": "Falco not deployed"
  }
}
```

**Interview Response (Control Owner — SOC):**
> "System monitoring — we get alerts from various places. Falco is on the roadmap.
> Alert volume and false positive rate — I don't have those metrics."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Falco not deployed; 0 monitoring rules; alert volume and FP rate unknown |
| Impact | High | Without continuous system monitoring, threats go undetected until they cause visible impact |
| **Residual Risk** | **Critical** | System monitoring entirely absent |

**Finding:** FAIL
**Evidence Gap:** Falco not deployed. Zero monitoring rules. Alert volume unknown. False positive rate unknown. No Splunk dashboard. Coverage score unknown.

**BERU Finding:**
```
FINDING: Falco is not deployed and no system monitoring rules, alert volume, or Splunk dashboard exist for SI-4.
CONTROL: SI-4 — System Monitoring
ENHANCEMENT: SI-4(2) — Automated Tools and Mechanisms for Real-Time Analysis
STATUS: FAIL
EVIDENCE REVIEWED:
  - SOC verbal statement (alerts from various sources, Falco roadmap, metrics unknown)
  - Falco query (not deployed, 0 monitoring rules, alert volume null)
EVIDENCE GAP: Falco not deployed, 0 rules, alert volume unknown, FP rate unknown, no Splunk dashboard, coverage unknown
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: SOC (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: System monitoring cannot be evidenced. Falco is not deployed and no alert metrics exist. Without continuous monitoring, threats go undetected. Deploy Falco, configure the Splunk dashboard, and establish alert volume tracking immediately.
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

**Tool Query:** `GET /evidence/SI-7?env=bad` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "SI-7", "env": "bad", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "signing_enabled": false,
    "integrity_checks": null,
    "error": "Software signing not configured"
  }
}
```

**Interview Response (Control Owner — DevSecOps):**
> "Image signing — we haven't set that up yet. Kyverno admission for signatures
> is on the backlog. SBOM — not configured. We verify images manually sometimes."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Signing not configured; admission enforcement absent; SBOM not generated |
| Impact | High | Unsigned images could be tampered with between build and deployment without detection |
| **Residual Risk** | **Critical** | Software integrity is entirely unverifiable |

**Finding:** FAIL
**Evidence Gap:** Image signing not configured. Kyverno admission policy not deployed. SBOM not generated. Integrity checks not automated.

**BERU Finding:**
```
FINDING: Container image signing is not configured and Kyverno admission enforcement and SBOM generation are absent for SI-7.
CONTROL: SI-7 — Software, Firmware, and Information Integrity
ENHANCEMENT: SI-7(1) — Integrity Checks
STATUS: FAIL
EVIDENCE REVIEWED:
  - DevSecOps verbal statement (signing not set up, Kyverno backlog, SBOM not configured)
  - Semgrep query (signing_enabled false, integrity_checks null)
EVIDENCE GAP: Image signing not configured, Kyverno admission policy not deployed, SBOM not generated, integrity checks not automated
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: DevSecOps (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Software integrity controls are absent. Image signing, Kyverno admission enforcement, and SBOM generation are all unconfigured. Without these controls, tampered images can reach production undetected. Implement cosign signing and Kyverno admission policy before the next assessment.
```
