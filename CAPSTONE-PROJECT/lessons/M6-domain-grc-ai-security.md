# M6 — Domain: GRC and AI Security

> **Goal:** Know NIST 800-53 well enough to map any finding to the right control family, and understand where AI RMF fits alongside it.
> **Build:** `BERU-COVERAGE.md` — the honest coverage map showing what BERU can and cannot assess.
> **Gate:** Coverage map is complete with honest gaps documented. A 3PAO auditor can read it and know BERU's limits.

---

## Why Domain Knowledge Is the Differentiator

Every AI engineer knows Python, RAG, and LLM APIs. Almost none of them understand NIST 800-53. That gap is where you separate from the field for the roles you're targeting.

PwC, Deloitte, and the defense MLOps role all want AI engineers who can build the system AND explain its compliance posture. "I built a RAG pipeline over NIST controls" is table stakes. "I can tell you which controls BERU can assess autonomously, which require human judgment, and why — and I documented all of it" is what gets you in the room.

This module is the vocabulary. You don't need to memorize 800-53. You need to know the structure well enough to navigate it confidently.

---

## Concept 1 — NIST 800-53 Rev 5 Structure

### The 20 families

Each family is a two-letter code. Know these cold:

| Code | Family | What It Covers |
|------|--------|---------------|
| **AC** | Access Control | Who can access what. Accounts, least privilege, session management. |
| **AT** | Awareness and Training | Security training requirements. |
| **AU** | Audit and Accountability | Logging, log retention, log review. "Who did what when." |
| **CA** | Assessment, Authorization, Monitoring | Security assessments, ATO, POA&M, continuous monitoring. |
| **CM** | Configuration Management | Baselines, change control, software inventory. |
| **CP** | Contingency Planning | Backup, recovery, business continuity. |
| **IA** | Identification and Authentication | Passwords, MFA, credentials. "Prove you are who you say." |
| **IR** | Incident Response | How you respond to breaches. Plan, test, execute. |
| **MA** | Maintenance | System maintenance procedures. |
| **MP** | Media Protection | How you handle physical media (USB, backups). |
| **PE** | Physical and Environmental | Physical access to data centers. |
| **PL** | Planning | Security plans. SSP lives here. |
| **PM** | Program Management | Organization-level risk program. |
| **PS** | Personnel Security | Background checks, termination procedures. |
| **PT** | PII Processing | How you handle personally identifiable information. |
| **RA** | Risk Assessment | Vulnerability scanning, risk assessments. |
| **SA** | System Acquisition | How you buy and develop software securely. |
| **SC** | Communications Protection | Network controls, encryption in transit, TLS, firewalls. |
| **SI** | System Integrity | Patches, malware, monitoring, input validation. |
| **SR** | Supply Chain Risk | Third-party software, open source risk. |

**The 5 C's map directly to these families:**

- **Code** → SA (how you develop it), SI-7 (integrity), SR-3 (dependencies)
- **Container** → CM-6 (configuration), SC-28 (at rest), SI-2 (patching base images)
- **Cluster** → AC-6 (RBAC), CM-6 (benchmarks), SC-7 (network policy), AU-2 (audit logging)
- **Cloud** → AC-2 (IAM), SC-7 (security groups), RA-5 (vulnerability scanning), AU-12 (CloudTrail)
- **Compliance** → CA-2 (assessments), CA-5 (POA&M), CA-7 (continuous monitoring), PL-2 (SSP)

### High-impact controls you see most often

These appear in almost every engagement. Know them by memory:

| Control | What it means in practice |
|---------|--------------------------|
| **AC-2** | Account lifecycle — create, review, disable on offboard. Common FAIL: no quarterly review. |
| **AC-6** | Least privilege — minimum access to do the job. Common FAIL: admin access for everyone. |
| **AU-2** | Audit events — what gets logged. Common FAIL: no logging for authentication failures. |
| **CA-5** | POA&M — every FAIL has a tracked remediation. BERU's core output. |
| **CM-6** | Configuration settings — CIS benchmarks, locked-down defaults. |
| **IA-2** | MFA. Still one of the most common FAILs. |
| **RA-5** | Vulnerability scanning — Trivy, Prowler, Nessus. Monthly minimum. |
| **SC-7** | Network boundary protection — firewalls, NetworkPolicy, security groups. |
| **SC-8** | Encryption in transit — TLS 1.2+ everywhere. |
| **SC-28** | Encryption at rest — KMS, encrypted EBS, encrypted S3. |
| **SI-2** | Patch management — critical CVEs within 15 days. |
| **SI-4** | System monitoring — GuardDuty, Falco, Splunk forwarding. |

---

## Concept 2 — POA&M Structure

POA&M = Plan of Action and Milestones. It's the remediation tracking document. Every control that's FAIL or PARTIAL needs a POA&M item.

**The fields every POA&M item must have:**

```markdown
## POA&M Item F-001

**Control:** AC-6 Least Privilege
**Weakness:** All developers have cluster-admin in the production Kubernetes cluster.
**Likelihood:** High — 12 accounts, no justification documented
**Impact:** High — full cluster takeover by any compromised developer credential
**Risk Rank:** B (Likelihood × Impact = 4 × 5 = 20)
**Responsible Officer:** Platform Engineering Lead
**Scheduled Completion:** 2026-06-30
**Milestones:**
  - 2026-05-15: Audit all cluster-admin bindings and identify minimum required access
  - 2026-06-01: Implement namespace-scoped roles for developer accounts
  - 2026-06-30: Remove cluster-admin from all non-break-glass accounts
**Resources Required:** 2 engineer days
**Status:** Open
```

**The 3PAO test:** Can the Authorizing Official (AO) read this and understand: what is broken, who owns fixing it, when it will be fixed, and what the interim risk is? If yes, it's a good POA&M item.

**What BERU produces:** The `POA&M ITEM` field in every BERU finding maps directly to this structure.

---

## Concept 3 — SSP Narrative Quality

The SSP (System Security Plan) is the core authorization document. It describes how each control is implemented. Control implementation statements range from terrible to excellent.

Look at `GP-CONSULTING/NIST-800-53/ssp-examples/` for the bad/good/great examples. The pattern:

| Quality | What it looks like |
|---------|-------------------|
| **Bad** | "We implement AC-6 per NIST guidelines." (Restates the control name. Tells the auditor nothing.) |
| **Good** | "Developers have read-only access to production namespaces. Only the Platform SRE team holds cluster-admin, which requires Change Advisory Board approval per change control procedure CM-3." |
| **Great** | Above, plus: "Access reviews are conducted quarterly via ServiceNow ticket PR-4521, last completed 2026-04-01. Results are documented in `AC-2-quarterly-review-2026-Q1.xlsx`. 3 accounts were removed following the last review." |

The difference: **Great** answers the auditor's follow-up questions before they ask. Dates, tool names, file names, specific numbers.

BERU's `EVIDENCE REVIEWED` and `EVIDENCE GAP` fields in the finding format are designed to capture exactly this — what did we see, what's missing, with specifics.

---

## Concept 4 — NIST AI RMF and How It Layers on 800-53

From `CAPSTONE-PROJECT/frameworks/crosswalk/800-53-to-ai-rmf.md`:

> **IT infrastructure finding** (Trivy, kube-bench, Prowler result) → Use 800-53 controls
> **AI system behavior finding** (garak, promptfoo, mlflow-audit) → Use AI RMF subcategories + corresponding 800-53

The four AI RMF functions:
- **GOVERN** — policies, accountability, risk tolerance (is there even a policy for AI risk?)
- **MAP** — understand the AI system before deploying it (what does it do? what can go wrong?)
- **MEASURE** — test it (is it accurate? biased? vulnerable to prompt injection?)
- **MANAGE** — respond when it goes wrong (incident response for AI errors, model updates)

**The 6 risks that 800-53 doesn't cover (AI 600-1 specific):**

| Risk | What it means for BERU |
|------|----------------------|
| Hallucination (MEASURE 2.5) | BERU citing a control that doesn't exist |
| Prompt injection (MEASURE 2.11) | Malicious scanner output manipulating BERU's output |
| Data poisoning (MAP 4.1) | Corrupt training data producing wrong control mappings |
| Output bias (MEASURE 2.9) | BERU consistently underrating risk for certain system types |
| Model supply chain (MAP 4.1) | Base model weights from an unverified source |
| Privacy (MEASURE 2.10) | PII in scanner output ending up in training data |

BERU assesses all of these when the finding involves an AI system (JADE, Katie, BERU itself).

---

## Concept 5 — FedRAMP Moderate Context

FedRAMP Moderate is what most federal cloud systems must achieve. It applies NIST 800-53 at Moderate impact level.

Key facts for interviews:
- **325 controls** at Moderate (vs 125 at Low, 421 at High)
- **Three impact levels**: Confidentiality, Integrity, Availability — each rated Low/Moderate/High
- **Annual assessments** by a 3PAO (Third Party Assessment Organization)
- **Continuous monitoring**: monthly scans (Prowler, Nessus), annual pen test, POA&M reviews
- **The ATO**: Authorization To Operate — the document that says "this system is authorized to handle federal data"

BERU's entire design is FedRAMP-aligned: local model (SC-28), synthetic training data (no PII in training = MEASURE 2.10), HITL for B/S decisions (CA-6 — AO makes authorization decisions, not AI).

---

## Troubleshooting M6

| Symptom | Cause | Fix |
|---------|-------|-----|
| Wrong control family for a finding | Pattern-matched on the wrong keyword | Check `nist_mapper.py` `_KEYWORD_CONTROLS` — the keyword might map to the wrong family |
| POA&M missing milestones | BERU output truncated | Check `EVIDENCE GAP` field — if BERU couldn't find completion dates, the POA&M item won't have them. Human must fill. |
| AI RMF subcategory on an IT-only finding | `ai_context: true` set incorrectly | Check `scanner_mappings.yaml` — only AI scanners (garak, promptfoo, etc.) should have `ai_context: true` |
| Control ID formatted wrong (AC6 instead of AC-6) | Input parsing | `validate_control_id()` catches this — add a regex normalization step |
| "What about the 20% BERU can't assess?" | Coverage gap not documented | This is what `BERU-COVERAGE.md` is for — the M6 build artifact |

---

## What You Build

`GP-CONSULTING/NIST-800-53/BERU-COVERAGE.md` — one row per control family:

```markdown
| Family | Controls BERU Can Assess | Evidence Tool | Cannot Assess Autonomously |
|--------|--------------------------|---------------|---------------------------|
| AC | AC-2, AC-3, AC-6, AC-17 | kubectl get rolebindings, Prowler | AC-2(j) — physical access review |
| AU | AU-2, AU-3, AU-12 | CloudTrail, Falco logs | AU-6 — log review quality (requires human judgment) |
| CM | CM-2, CM-6, CM-7 | kube-bench, kyverno-policyreport | CM-3 — change control board documentation |
| SC | SC-7, SC-8, SC-28 | Prowler, Trivy | SC-13 — cryptographic standards review (algorithm selection) |
| SI | SI-2, SI-3, SI-4 | Trivy CVEs, GuardDuty | SI-5 — security alert timeliness review |
```

Document at least 5 families with honest gaps. The gaps are as important as the coverage — they show you understand what automated assessment can and can't do.

**3PAO question this answers:** "What can't BERU assess? How do you know your coverage is complete?"
Your answer: "BERU-COVERAGE.md documents 80% coverage across 12 control families with the specific tools used as evidence. The 20% gap — physical access, change board documentation, cryptographic standards review — requires human judgment and is explicitly not automated."

---

## Control Traceability

> M6 is different — BERU's knowledge base IS the control implementation. Point here when asked "what does BERU actually do?"

**NIST 800-53:**

| Control | What BERU implements | Audit answer |
|---------|---------------------|--------------|
| **CA-2** — Control Assessments | BERU's primary function — reads scanner output, maps to 800-53, produces structured findings | "BERU is the CA-2 tool. It takes scanner output as input and produces control assessment findings as output. That's the definition of a CA-2 process." |
| **CA-5** — Plan of Action and Milestones | Every PARTIAL/FAIL finding BERU produces includes a POA&M item with weakness, milestone, and scheduled completion | "BERU outputs a POA&M item for every non-passing finding. The POA&M is the CA-5 artifact. It feeds directly into `gap-to-poam.py` for ServiceNow import." |
| **PL-2** — System Security Plan | `SSPParser` processes SSPs and `ssp-examples/` defines the Bad/Good/Great quality standard in the system prompt | "BERU evaluates SSP narrative quality against a defined standard (bad/good/great). The standard is in the system prompt. A bad SSP gets a finding." |
| **AU-6** — Audit Record Review, Analysis, and Reporting | CISO SUMMARY field is the AU-6 deliverable — business-language risk reporting without NIST IDs | "The CISO summary in every BERU finding is designed for executive reporting. It translates technical findings into business risk language." |

**NIST AI RMF:**

| Subcategory | What it maps to | Audit answer |
|-------------|----------------|--------------|
| **GOVERN-1.1** — Policies for AI trustworthiness are in place | BERU's knowledge of GOVERN 1.1 lets it assess whether an org has documented AI policies at all — the absence is a finding | "If an AI system has no governance documentation, BERU flags GOVERN-1.1 FAIL. That's the first question in every AI assessment." |
| **MAP-1.6** — AI risk and impact are assessed | BERU applies the RISK field (Likelihood × Impact → rank) on every finding — this IS the MAP-1.6 output | "Every BERU finding includes a ranked risk assessment. The rank determines the remediation path. That output is the MAP-1.6 artifact." |
