# Risk Assessment Evidence — SI Family
## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** Evidence collected is partially sufficient. Control owners named specific
> tools and processes but could not produce exact artifacts, dates, or complete metrics. Tool
> queries returned partial data — some booleans confirmed but key counts and timestamps absent.
> All four controls receive PARTIAL findings requiring POA&M items to close the evidence gaps
> before the next audit cycle.

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

**Tool Query:** `GET /evidence/SI-2?env=good` — simulates: trivy

**Tool Evidence (API Response):**
```json
{
  "control": "SI-2", "env": "good", "tool": "trivy",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:00:00Z", "status": "partial",
  "data": {
    "patches_applied_30d": null,
    "critical_unpatched": 3,
    "patch_sla_days": null,
    "note": "Critical CVEs present. No documented patch SLA."
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "Trivy runs. There are 3 critical CVEs open. We're working on them but there's
> no formal SLA written down. Patches applied — I'd have to count in JIRA. Kyverno
> base image policies — I think they're deployed but I'd need to check the names."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — Trivy running; 3 critical CVEs open (SSP claims 0); no patch SLA; patch count not confirmed; Kyverno policies unconfirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Trivy running; 3 critical CVEs open without SLA; patching occurring but not tracked |
| Impact | High | 3 open critical CVEs without SLA mean remediation is undefined and exploitable |
| **Residual Risk** | **High** | Trivy active but critical CVEs open and SLA absent |

**Finding:** PARTIAL
**Evidence Gap:** 3 critical CVEs open without patch SLA. Patch count not confirmed. Kyverno base image policies not confirmed. JIRA patch tracking board not produced.

**BERU Finding:**
```
FINDING: Trivy confirms 3 critical CVEs for SI-2 but no patch SLA is defined and the Kyverno base image policies are not confirmed.
CONTROL: SI-2 — Flaw Remediation
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - SecEng verbal statement (Trivy running, 3 critical CVEs, no SLA, Kyverno uncertain)
  - Trivy query (3 critical_unpatched, patch_sla null, patches_applied null)
EVIDENCE GAP: 3 critical CVEs without SLA, patch count not confirmed, Kyverno base image policies not confirmed, JIRA board not produced
RISK:
  Likelihood: Medium
  Impact: High
  Residual Risk: High
CONTROL OWNER: SecEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: 3 critical CVEs are open without a patch SLA. Define the SLA, produce the JIRA patch tracking board, and confirm Kyverno base image policies to close this finding.
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

**Tool Query:** `GET /evidence/SI-3?env=good` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "SI-3", "env": "good", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:05:00Z", "status": "partial",
  "data": {
    "malicious_pattern_rules": 12,
    "ci_gate_active": true,
    "block_on_critical": false,
    "note": "CI gate warns but does not block"
  }
}
```

**Interview Response (Control Owner — SecEng):**
> "Semgrep runs 12 rules in CI. It's in warn mode — we're not blocking yet because
> there are some false positives we haven't tuned out. Rules are in the repo but
> I don't have the path. Last rule update — I'm not sure of the date."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — Semgrep CI gate active with 12 rules; gate not blocking (warn mode); 35 of 47 rules missing; last rule update date not confirmed

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | CI gate active; warn-only mode means critical findings can pass; only 12 of 47 rules deployed |
| Impact | Medium | Non-blocking gate means malicious patterns can reach production with a warning |
| **Residual Risk** | **High** | Partial malicious code detection; blocking mode and rule count gaps must close |

**Finding:** PARTIAL
**Evidence Gap:** CI gate in warn mode — not blocking on critical findings. Only 12 of 47 claimed rules deployed. Rules repo path not provided. Last rule update date not confirmed.

**BERU Finding:**
```
FINDING: Semgrep CI gate has 12 of 47 claimed rules for SI-3 but is in warn mode, not blocking on critical findings.
CONTROL: SI-3 — Malicious Code Protection
ENHANCEMENT: None
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - SecEng verbal statement (Semgrep running, warn mode, false positives, rules location unknown)
  - Semgrep query (12 rules, ci_gate active, block_on_critical false, warn mode)
EVIDENCE GAP: Gate not blocking, only 12 of 47 rules deployed, rules repo path not provided, last rule update date unknown
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: SecEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: The Semgrep CI gate is running but in warn mode. Enable blocking mode, deploy the remaining 35 rules, and provide the rules repo path to close this finding.
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

**Tool Query:** `GET /evidence/SI-4?env=good` — simulates: falco

**Tool Evidence (API Response):**
```json
{
  "control": "SI-4", "env": "good", "tool": "falco",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:10:00Z", "status": "partial",
  "data": {
    "monitoring_rules_active": 22,
    "alert_volume_30d": null,
    "false_positive_rate": null,
    "note": "Rules active but alert volume and tuning not tracked"
  }
}
```

**Interview Response (Control Owner — SOC):**
> "Falco is deployed with 22 rules. Alert volume — we don't have that metric
> tracked right now. False positive rate — we haven't measured it. The Splunk
> dashboard exists but it's basic. Coverage score — I don't know."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — Falco deployed with 22 rules; alert volume and FP rate not tracked; 43 of 65 claimed rules missing; coverage score not measured

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Falco deployed; alert volume and FP rate not tracked; 22 of 65 rules below SSP claim |
| Impact | Medium | Without FP rate tracking, alert fatigue cannot be managed; 43 missing rules reduce coverage |
| **Residual Risk** | **High** | Monitoring active but metric tracking and rule count gaps must close |

**Finding:** PARTIAL
**Evidence Gap:** Only 22 of 65 claimed Falco rules active. Alert volume not tracked. False positive rate not measured. Coverage score unknown. Splunk dashboard is basic.

**BERU Finding:**
```
FINDING: Falco is deployed with 22 of 65 claimed rules for SI-4; alert volume, FP rate, and coverage score are not tracked.
CONTROL: SI-4 — System Monitoring
ENHANCEMENT: SI-4(2) — Automated Tools and Mechanisms for Real-Time Analysis
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - SOC verbal statement (22 rules running, metrics not tracked, basic Splunk dashboard)
  - Falco query (22 rules, alert_volume null, false_positive_rate null)
EVIDENCE GAP: Only 22 of 65 rules active, alert volume not tracked, FP rate not measured, coverage score unknown
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: SOC (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Falco monitoring is running but below the SSP claim. Deploy the remaining 43 rules and implement alert volume and false positive rate tracking to close this finding.
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

**Tool Query:** `GET /evidence/SI-7?env=good` — simulates: semgrep

**Tool Evidence (API Response):**
```json
{
  "control": "SI-7", "env": "good", "tool": "semgrep",
  "iam_group": "grc-engineer", "queried_at": "2026-05-10T09:15:00Z", "status": "partial",
  "data": {
    "signing_enabled": true,
    "integrity_checks": "cosign — not enforced via admission",
    "note": "Signing configured but admission control not enforcing"
  }
}
```

**Interview Response (Control Owner — DevSecOps):**
> "Images are signed with cosign. The Kyverno admission policy — it's on the
> todo list. We sign but don't enforce at admission yet. SBOM — cosign can
> generate it but I haven't confirmed it's wired up. Daily scan — not configured."

### Risk Assessment

**Evidence Quality:** Partial
**SSP Claim Verified:** Partially — cosign signing configured; Kyverno admission enforcement not deployed; SBOM not confirmed; daily scan not configured

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | Medium | Signing configured; admission enforcement absent means unsigned images could be deployed |
| Impact | Medium | Without admission enforcement, image signing is not a true security control |
| **Residual Risk** | **High** | Signing exists but without admission enforcement it does not prevent tampered image deployment |

**Finding:** PARTIAL
**Evidence Gap:** Kyverno admission enforcement not deployed. SBOM generation not confirmed. Daily scheduled scan not configured.

**BERU Finding:**
```
FINDING: Cosign signing is configured for SI-7 but Kyverno admission enforcement is not deployed and SBOM generation is not confirmed.
CONTROL: SI-7 — Software, Firmware, and Information Integrity
ENHANCEMENT: SI-7(1) — Integrity Checks
STATUS: PARTIAL
EVIDENCE REVIEWED:
  - DevSecOps verbal statement (cosign configured, Kyverno todo, SBOM not confirmed, daily scan not configured)
  - Semgrep query (signing_enabled true, integrity_checks cosign but not admission-enforced)
EVIDENCE GAP: Kyverno admission enforcement not deployed, SBOM generation not confirmed, daily scan not configured
RISK:
  Likelihood: Medium
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: DevSecOps (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Image signing is configured but not enforced at admission. Deploy the Kyverno require-image-signature.yaml policy, confirm SBOM generation, and configure daily integrity scans to close this finding.
```
