# GP-Copilot 3POA Audit Framework

**Version**: 1.0 | **Framework**: NIST 800-53 Rev 5 + NIST AI 600-1
**Audience**: Third-party assessors, internal CISO audits, FedRAMP 3PAO prep

A 3POA (Third-Party Organization Assessment) is an independent audit of a system's
security controls. This framework tells you exactly how to assess GP-Copilot — what
to ask, who to interview, what evidence to collect, and how to validate it.

The controls are implemented across three lenses. You assess all three to get complete
coverage. Each lens has a separate evidence request template.

---

## Assessment Model

Three activities per control:

1. **Interview** — ask the control owner to explain the implementation
2. **Evidence review** — review the artifacts they provide
3. **Live validation** — run validation commands in front of the assessor

A control passes only when all three are satisfied. Evidence without a live
validation is hearsay. A working system with no documentation fails the audit.

---

## Who to Interview

Use `control-owner-matrix.md` to identify the right person per control.
Do not accept evidence from the wrong role — the Primary Owner must answer to the auditor.

| Control Family | Primary Interview Target | Secondary |
|---------------|------------------------|-----------|
| AC — Access Control | ISSO (policy) + PlatEng (K8s RBAC) + CloudSec (IAM) | DevSecOps |
| AU — Audit/Logging | SOC + SecEng | PlatEng |
| CA — Assessment | CompO (compliance officer) | ISSO |
| CM — Config Management | PlatEng (K8s) + CloudSec (cloud) | DevSecOps (CI/CD) |
| CP — Contingency | ITOps + PlatEng | SOC |
| IA — Identity and Auth | ITOps + CloudSec | PlatEng |
| IR — Incident Response | IRT (IR team) + SOC | SecEng |
| RA — Risk Assessment | CompO + SecEng | CISO |
| SA — Acquisition/Dev | DevSecOps + PlatEng | ISSO |
| SC — System/Comms | PlatEng (K8s) + CloudSec (cloud) + AppDev (app layer) | SecEng |
| SI — System Integrity | SecEng + DevSecOps | SOC |

---

## Assessment Flow

```
Phase 1 — Pre-Assessment (1 week before)
  Send evidence request templates (one per lens)
  Request SSP excerpt for each control in scope
  Set live validation schedule (2-hour blocks per lens)

Phase 2 — Evidence Review (before live sessions)
  Review returned evidence for completeness
  Flag missing artifacts
  Identify controls for deeper testing

Phase 3 — DEVOPS-LENS Live Session (2 hours)
  Interview: PlatEng + DevSecOps
  Validate: CI pipeline, Kyverno policies, kube-bench, cosign, RBAC
  Scope: Code (01-APP-SEC) + Cluster (02-CLUSTER-HARDEN)

Phase 4 — CYBERSEC-LENS Live Session (2 hours)
  Interview: SOC + SecEng + CloudSec
  Validate: Falco rules, Prowler scan, GuardDuty findings, Splunk dashboards
  Scope: Container (03-RUNTIME) + Cloud (04-CLOUD) + Compliance (05-COMPLIANCE-READY)

Phase 5 — AI-SEC-LENS Live Session (1 hour, if AI workloads in scope)
  Interview: AI security engineer
  Validate: cosign model signatures, garak scan, Presidio PII check, MLflow logs
  Scope: Model supply chain + training data + inference security

Phase 6 — Report
  Finding: Control ID + status (PASS/PARTIAL/FAIL) + evidence + gap
  Risk: Likelihood × Impact using table below
  POA&M: Remediation item for every PARTIAL or FAIL
```

---

## Scoring

### Control Status

| Status | Criteria |
|--------|----------|
| **PASS** | Documented + implemented + evidence provided + live validation succeeds |
| **PARTIAL** | Implemented but incomplete documentation, or gaps in coverage |
| **FAIL** | Not implemented, or implemented without evidence |
| **N/A** | Control is not applicable to this system boundary |

### Risk Scoring (Likelihood × Impact)

| | Low Impact | Medium Impact | High Impact |
|-|-----------|--------------|-------------|
| **Low Likelihood** | Low | Low | Medium |
| **Medium Likelihood** | Low | Medium | High |
| **High Likelihood** | Medium | High | Critical |

Map to GP-Copilot rank system:

| Risk | GP-Copilot Rank | Who Decides |
|------|----------------|-------------|
| Low | E/D | Auto-remediate |
| Medium | C | JADE proposes, human approves |
| High | B | Human decides, JADE provides intel |
| Critical | S | Human only, JADE provides dashboard |

---

## Document Index for This Package

```
NIST-800-53/3POA/
├── AUDIT-FRAMEWORK.md               ← this file
├── tool-justification-matrix.md     ← every tool → control → why (not shiny object)
├── mitre-attack-map.md              ← ATT&CK + ATLAS → control → tool
├── evidence-requests/
│   ├── DEVOPS-LENS.md               ← what to ask PlatEng/DevSecOps
│   ├── CYBERSEC-LENS.md             ← what to ask SOC/SecEng/CloudSec
│   └── AI-SEC-LENS.md              ← what to ask AI security engineer
```

Related documents:

- `../control-owner-matrix.md` — who is accountable for each control
- `../controls/*.md` — per-control evidence questions and tool list
- `../ssp-examples/` — bad/good/great SSP narrative examples per family
- `../../DEVOPS-LENS/NIST-CONTROL-MAP.md` — DEVOPS execution and evidence paths
- `../../CYBERSEC-LENS/NIST-CONTROL-MAP.md` — CYBERSEC execution and evidence paths
- `../../AI-SEC-LENS/NIST-CONTROL-MAP.md` — AI-SEC execution and evidence paths

---

## Honest System Boundary

GP-Copilot covers 45 of the NIST 800-53 controls the tools can automate.
Controls it does **not** cover — and why:

| Gap | Why It's a Gap | What to Do |
|-----|---------------|-----------|
| AT-1 through AT-4 (Training) | LMS/HR workflow — not infrastructure | Client CISO provides |
| PL-1 through PL-9 (Planning) | SSP narrative — no tool generates policy prose | GRC analyst writes |
| PS-1 through PS-9 (Personnel) | HR background checks — out of scope | Client HR provides |
| PE-* (Physical/Environmental) | Data center controls — cloud-native engagements don't touch this | Cloud provider's responsibility |
| IR-1, IR-2, IR-3 | Policy documents + tabletop exercises | GRC analyst writes, tests manually |
| IA-3, IA-6–IA-12 | Enterprise IdP (Okta, AD, Keycloak) | Client provides IdP |
| CA-3, CA-5 | Interconnection agreements + POA&M narrative | Human signs, JADE drafts |

These gaps are documented here so you are never surprised in an audit. A senior
engineer does not hide gaps — they document them and show the remediation path.
