# Risk Assessment Evidence — IA Family
## Links-Matrix Platform — BAD VERSION

> **Reviewer note:** Evidence collected for all four Identification and Authentication controls
> is incomplete and unverifiable. Control owners provided vague verbal assurances with no
> supporting artifacts. Tool queries returned null or error responses indicating identity
> management tooling is not deployed or not capturing required data. All four findings are
> FAIL; all require POA&M items.

**Assessment Date:** 2026-05-10
**Assessor:** GRC Engineer (grc-engineer group — read-only)
**Framework:** NIST 800-53 Rev 5
**Graded Against:** Links-Matrix SSP (see ssp-examples/IA-ssp-great.md)

---

## IA-2 — Identification and Authentication (Organizational Users)

**Control Owner:** ITOps
**Evidence Producer:** ITOps
**Cadence:** Continuous (IdP policy enforcement)

### SSP Claim
> The SSP asserts that MFA is enforced for all organizational users via SCP p-abc123def456
> at the AWS Organizations level. All console logins require FIDO2/WebAuthn via Okta Verify.
> ConsoleLogin events in CloudTrail confirm 0 MFA bypass attempts in the last 90 days.

### Evidence Request

**Interview — Questions asked of control owner (ITOps):**
1. Show me MFA enforcement — SCP or IdP policy?
2. Show me ConsoleLogin events with any MFA bypass attempts.

**Tool Query:** `GET /evidence/IA-2?env=bad` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "IA-2", "env": "bad", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "mfa_enforced_via_scp": null,
    "console_login_events_90d": 0,
    "mfa_not_used_logins": null,
    "error": "ConsoleLogin events not present in trail"
  }
}
```

**Interview Response (Control Owner — ITOps):**
> "MFA is configured. People need to authenticate. I'm not sure about the SCP —
> it might be in a different account. ConsoleLogin events — CloudTrail should have
> them but I can't pull them right now."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | ConsoleLogin events not in trail; SCP status unknown; MFA configuration unconfirmed |
| Impact | High | Without MFA enforcement evidence, credential-only access is possible |
| **Residual Risk** | **Critical** | MFA enforcement is entirely unverifiable |

**Finding:** FAIL
**Evidence Gap:** ConsoleLogin events not present in CloudTrail. SCP ID not confirmed. MFA type not confirmed. Bypass attempt count unknown.

**BERU Finding:**
```
FINDING: ConsoleLogin events are absent from CloudTrail and SCP MFA enforcement cannot be confirmed for IA-2.
CONTROL: IA-2 — Identification and Authentication (Organizational Users)
ENHANCEMENT: IA-2(1) — Multi-Factor Authentication to Privileged Accounts
STATUS: FAIL
EVIDENCE REVIEWED:
  - ITOps verbal statement (MFA described, SCP uncertain, events unavailable)
  - CloudTrail query (ConsoleLogin events not present, mfa_enforced_via_scp null, 0 events found)
EVIDENCE GAP: ConsoleLogin events not in trail, SCP ID not confirmed, MFA type not confirmed, bypass attempt count unknown
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: ITOps (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: MFA enforcement cannot be evidenced. ConsoleLogin events are absent from CloudTrail and the SCP is not confirmed. Without MFA verification, credential-only access is a critical risk. Enable ConsoleLogin events and confirm SCP enforcement immediately.
```

---

## IA-3 — Device Identification and Authentication

**Control Owner:** PlatEng
**Evidence Producer:** PlatEng
**Cadence:** Continuous (mTLS/workload identity)

### SSP Claim
> The SSP asserts that all Kubernetes workloads use mTLS in STRICT mode via Istio service mesh.
> SPIFFE IDs are assigned to all pods via SPIRE. AWS workloads use EC2 Instance Profiles
> for node identity. Workload identity is managed via AWS IRSA (IAM Roles for Service Accounts).

### Evidence Request

**Interview — Questions asked of control owner (PlatEng):**
1. Show me how workload identity is established for Kubernetes pods.

**Tool Query:** `GET /evidence/IA-3?env=bad` — simulates: kubescape

**Tool Evidence (API Response):**
```json
{
  "control": "IA-3", "env": "bad", "tool": "kubescape",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "mtls_enabled": null,
    "workload_identity": null,
    "error": "Device/workload identity not scanned"
  }
}
```

**Interview Response (Control Owner — PlatEng):**
> "We use Kubernetes service accounts. Istio — it's deployed but I'm not sure if
> STRICT mode is on. SPIFFE IDs — I'd have to check if SPIRE is configured."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | mTLS mode unconfirmed; SPIFFE IDs unconfirmed; workload identity scan not available |
| Impact | Medium | Without mTLS STRICT mode, pod-to-pod communication may proceed without mutual authentication |
| **Residual Risk** | **High** | Workload identity cannot be verified |

**Finding:** FAIL
**Evidence Gap:** Kubescape workload identity scan not available. mTLS STRICT mode not confirmed. SPIFFE IDs not confirmed. IRSA configuration not produced.

**BERU Finding:**
```
FINDING: Workload identity scan is not available and mTLS STRICT mode and SPIFFE IDs cannot be confirmed for IA-3.
CONTROL: IA-3 — Device Identification and Authentication
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - PlatEng verbal statement (Istio deployed, STRICT mode uncertain, SPIFFE unknown)
  - Kubescape query (workload identity not scanned, mtls_enabled null)
EVIDENCE GAP: Kubescape scan not available, mTLS STRICT mode unconfirmed, SPIFFE IDs unconfirmed, IRSA configuration not produced
RISK:
  Likelihood: High
  Impact: Medium
  Residual Risk: High
CONTROL OWNER: PlatEng (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Workload identity cannot be evidenced. mTLS STRICT mode and SPIFFE ID assignment are unconfirmed. Configure Kubescape to scan workload identity and confirm Istio mTLS mode before the next assessment.
```

---

## IA-4 — Identifier Management

**Control Owner:** ISSO
**Evidence Producer:** ITOps
**Cadence:** Quarterly identifier review

### SSP Claim
> The SSP asserts that user identifiers are reviewed quarterly. The last review was 2026-04-30,
> approved by the ISSO. Zero inactive identifiers (>90 days), zero orphaned identifiers,
> and zero shared identifiers exist. Naming conventions are documented in IAM-NAMING-POLICY-v1.2.pdf.

### Evidence Request

**Interview — Questions asked of control owner (ITOps):**
1. Show me your identifier review — any orphaned or shared identifiers?

**Tool Query:** `GET /evidence/IA-4?env=bad` — simulates: cloudtrail

**Tool Evidence (API Response):**
```json
{
  "control": "IA-4", "env": "bad", "tool": "cloudtrail",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "identifier_review_last_run": null,
    "inactive_identifiers_gt90d": null,
    "orphaned_identifiers": null,
    "error": "IAM credential report not generated"
  }
}
```

**Interview Response (Control Owner — ITOps):**
> "We do identifier reviews. I don't have the last one handy. Orphaned identifiers
> — I'd have to run the report. Naming conventions exist but I don't have the
> policy document location."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | IAM credential report not generated; orphaned identifier count unknown; review date not confirmed |
| Impact | High | Orphaned and shared identifiers are attack vectors; without review evidence, stale credentials persist |
| **Residual Risk** | **Critical** | Identifier management entirely unverified |

**Finding:** FAIL
**Evidence Gap:** IAM credential report not generated. Last review date not confirmed. Orphaned and shared identifier counts unknown. Naming policy document not produced.

**BERU Finding:**
```
FINDING: IAM credential report cannot be generated and no identifier review artifact exists for IA-4.
CONTROL: IA-4 — Identifier Management
ENHANCEMENT: None
STATUS: FAIL
EVIDENCE REVIEWED:
  - ITOps verbal statement (review described, credential report unavailable)
  - CloudTrail query (IAM credential report not generated, review dates null, orphaned null)
EVIDENCE GAP: IAM credential report not generated, last review date not confirmed, orphaned/shared identifier counts unknown, naming policy not produced
RISK:
  Likelihood: High
  Impact: High
  Residual Risk: Critical
CONTROL OWNER: ISSO (accountability) / ITOps (evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Identifier management cannot be evidenced. The IAM credential report has not been generated and no quarterly review artifact was produced. Orphaned identifiers are an unquantified risk. Generate the credential report and produce the Q1 review artifact immediately.
```

---

## IA-5 — Authenticator Management

**Control Owner:** ITOps
**Evidence Producer:** ITOps / SecEng
**Cadence:** Continuous + rotation schedule

### SSP Claim
> The SSP asserts that no secrets exist in git repositories — confirmed by Gitleaks CI gate
> running on every push. Secrets are rotated on a 90-day schedule enforced via AWS Secrets
> Manager. Pre-commit hooks prevent secret commits. The credential report confirms 0 access
> keys older than 90 days.

### Evidence Request

**Interview — Questions asked of control owner (ITOps):**
1. Show me your secret rotation schedule and last rotation.
2. Show me Gitleaks CI gate configuration.

**Tool Query:** `GET /evidence/IA-5?env=bad` — simulates: gitleaks

**Tool Evidence (API Response):**
```json
{
  "control": "IA-5", "env": "bad", "tool": "gitleaks",
  "iam_group": "grc-engineer", "queried_at": null, "status": "insufficient",
  "data": {
    "secrets_found": null,
    "rotation_schedule": null,
    "error": "Gitleaks not configured in CI"
  }
}
```

**Interview Response (Control Owner — ITOps):**
> "We try to keep secrets out of git. Gitleaks — it's on the roadmap. Secret rotation
> — it happens when we remember to do it. AWS Secrets Manager — some secrets are
> there but not all."

### Risk Assessment

**Evidence Quality:** Insufficient
**SSP Claim Verified:** No

| Factor | Rating | Justification |
|--------|--------|---------------|
| Likelihood | High | Gitleaks not configured; rotation not scheduled; secrets in git unknown; CI gate absent |
| Impact | Critical | Secrets in git are permanent — once committed, they must be treated as compromised |
| **Residual Risk** | **Critical** | Secret exposure and rotation posture entirely unverified |

**Finding:** FAIL
**Evidence Gap:** Gitleaks not configured in CI. Secret rotation schedule not enforced. Secret count in git unknown. Credential report access key age not available.

**BERU Finding:**
```
FINDING: Gitleaks is not configured in CI and no secret rotation schedule or pre-commit hook exists for IA-5.
CONTROL: IA-5 — Authenticator Management
ENHANCEMENT: IA-5(1) — Password-Based Authentication
STATUS: FAIL
EVIDENCE REVIEWED:
  - ITOps verbal statement (Gitleaks roadmap, rotation ad hoc, Secrets Manager partial)
  - Gitleaks query (not configured in CI, secrets_found null, rotation_schedule null)
EVIDENCE GAP: Gitleaks not in CI, no rotation schedule, no pre-commit hook, credential report access key age unknown
RISK:
  Likelihood: High
  Impact: Critical
  Residual Risk: Critical
CONTROL OWNER: ITOps (accountability and evidence producer)
POA&M ITEM: Needed
CISO SUMMARY: Authenticator management is critically deficient. Gitleaks is not configured, secrets are not rotated on a schedule, and secret exposure in git cannot be ruled out. Configure Gitleaks immediately and enforce rotation via AWS Secrets Manager.
```
