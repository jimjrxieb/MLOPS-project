# System Security Plan — Planning (PL) Family

## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** This SSP would pass a FedRAMP readiness review with zero major
> findings. The SSP is version-controlled in git alongside the infrastructure it describes.
> Significant-change triggers are formally defined with SLAs. The boundary diagram is
> generated from IaC tags and auto-updated on merge. Control statement accuracy is
> verified quarterly by spot-check, not just annually. PL-2(3) coordination has formal
> advance notice requirements, a coordination log, and pre-activity sign-off records.
> OSCAL-compatible formatting is maintained so the SSP can be machine-read by any
> FedRAMP-compatible tool.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Approved — Active Authorization

> **Control chain:** PL-2 is the root document. Every other control family in this SSP
> references PL-2 as the authoritative statement of what is in scope, who is responsible,
> and what the authorization boundary is. Changes to any control implementation statement
> flow back to PL-2 version tracking.

---

## PL-2 — System Security and Privacy Plans

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

### Document Authority and Version Control

The Links-Matrix Platform System Security Plan is maintained as a living document
in two authoritative forms:

1. **Human-readable:** `SSP-LM-v4.0` hosted in Confluence (LM-SECURITY / SSP /
   SSP-LM-v4.0) with full version history. Approved by AO (D. Walsh) and System Owner
   (J. Rivera) on 2026-03-01. ISSO (M. Chen) is the plan custodian.

2. **Version-controlled source:** The SSP control implementation statements are
   maintained as Markdown files in `platform-gitops/ssp/controls/` — one file per
   control family. This repo is the single source of truth. The Confluence page is
   generated from this source via a GitHub Actions workflow on merge to `main`. Any
   manual edit to Confluence that is not reflected in git is treated as unauthorized
   and overwritten on the next build.

Current version: **v4.0** (git tag `ssp-v4.0`, SHA `a1b2c3d`).
Version history: `platform-gitops/ssp/CHANGELOG.md` — every version with date,
approver, and summary of changes.

### Authorization Boundary

The Links-Matrix Platform authorization boundary is formally defined and depicted
in the boundary diagram (`platform-gitops/ssp/diagrams/boundary-v4.0.drawio`,
exported to PNG at build time and embedded in the Confluence SSP). The diagram
is version-controlled alongside the control statements. A GitHub Actions workflow
compares the diagram's last-modified date against the most recent IaC merge — if
the diagram has not been updated within 30 days of a boundary-affecting IaC change,
a Jira ticket is auto-created and assigned to the ISSO.

**Within boundary:**

| Component | Type | Location | Authorization Basis |
| --------- | ---- | -------- | ------------------- |
| `lm-prod-cluster` (EKS) | Platform | us-east-1 | System-specific |
| `lm-dr-cluster` (EKS) | Platform | us-west-2 | System-specific |
| RDS PostgreSQL (`lm-db-prod`) | Data store | us-east-1 | System-specific |
| S3 buckets (`lm-app-data-*`) | Data store | us-east-1/us-west-2 | System-specific |
| AWS Secrets Manager | Credential store | us-east-1/us-west-2 | System-specific |
| CloudTrail, GuardDuty, Config | Monitoring | us-east-1/us-west-2 | System-specific |
| ECR (`lm-ecr-prod`) | Image registry | us-east-1 | System-specific |
| ArgoCD, Falco, OpenSearch | Platform tooling | In-cluster | System-specific |
| cert-manager, Kyverno | Platform tooling | In-cluster | System-specific |

**Inherited (out of boundary — leveraged controls only):**

| Component | Provider | Inherited Controls |
| --------- | -------- | ------------------ |
| Okta | Okta, Inc. | IA-2, IA-4, IA-5 (partially) |
| AWS infrastructure | Amazon Web Services | PE, PS, MA families |
| PagerDuty | PagerDuty, Inc. | IR alerting mechanism |

### Information Types

| Information Type | NIST SP 800-60 Category | Confidentiality | Integrity | Availability |
| ---------------- | ----------------------- | --------------- | --------- | ------------ |
| Application operational data | C.2.8.12 | Moderate | Moderate | Moderate |
| Platform audit logs | C.2.8.8 | Low | High | Moderate |
| Customer configuration data | C.2.8.12 | Moderate | High | Moderate |
| Encryption keys / credentials | C.2.8.2 | High | High | Moderate |

System categorization (overall): **Moderate (M-M-M)** — per FIPS 199 high-water mark.

### SSP Maintenance and Significant-Change Triggers

The SSP is maintained on a defined cadence with formal significant-change triggers.
"ISSO discretion" is not a trigger — a change either meets the criteria below or it does not.

**Annual review:**
Conducted each February. ISSO reviews all control implementation statements against
currently deployed configuration. Any statement that no longer matches deployed state
is flagged as a discrepancy. Discrepancies are corrected before the AO re-approval
meeting in March. The annual review produces a written findings report
(`platform-gitops/ssp/reviews/annual-review-YYYY.md`) documenting: statements reviewed,
discrepancies found, corrections made, and AO re-approval date.

**Significant-change triggers (SSP update required within 30 days):**

| Change Type | Trigger Condition | SLA | Approver |
| ----------- | ----------------- | --- | -------- |
| New AWS service added to boundary | Terraform merge adding new service to `infra-iac/boundary-services.tf` | 30 days | ISSO review, AO approval for impact level change |
| New EKS cluster | `cluster-provision` workflow completion | 30 days | ISSO review, AO approval |
| New information type | Data classification change in DLP policy | 15 days | ISSO review, AO approval |
| New external interconnection | ISA/MOU signed | 15 days | ISSO review, AO approval |
| Control implementation change (major) | Control statement in `platform-gitops/ssp/controls/` marked `status: changed` | 30 days | ISSO review |
| Authorization boundary reduction | Component decommissioned | 30 days | ISSO review |

A GitHub Actions workflow (`ssp-freshness-check.yaml`) runs nightly and compares:
- AWS Config resource inventory against the boundary component table above
- ArgoCD application list against the platform tooling table above

Any component present in AWS Config or ArgoCD but not in the SSP boundary table
creates a Jira ticket (`SEC-SSP` project, priority: High) assigned to the ISSO
with a 30-day SLA. This is the machine-readable enforcement of the significant-change
trigger process.

### Control Statement Accuracy Verification

Control statement accuracy is verified on two cadences:

**Quarterly spot-check:** The ISSO selects 3 controls per quarter from the SSP and
verifies the implementation statement against the actual deployment. Verification
method: read the control statement, then run the verification query in the `Evidence`
section of each control file. If the statement does not match, it is corrected immediately
and logged in the annual review record. Quarterly spot-check history:

| Quarter | Controls Spot-Checked | Discrepancies Found | Corrected |
| ------- | -------------------- | ------------------- | --------- |
| 2025-Q3 | AU-9, CM-2, IA-2 | 1 (AU-9 S3 bucket name updated) | 2025-09-12 |
| 2025-Q4 | AC-3, IR-4, IA-5 | 0 | — |
| 2026-Q1 | CA-7, SC-7, SI-4 | 1 (CA-7 tool added: AWS Config) | 2026-03-05 |
| 2026-Q2 | Scheduled | — | — |

**Annual comprehensive review:** Covers all control families before AO re-approval.

### OSCAL Compatibility

The control implementation statements in `platform-gitops/ssp/controls/` follow
a structured frontmatter schema that is OSCAL-compatible. A conversion script
(`platform-gitops/ssp/tools/to-oscal.py`) produces a valid OSCAL SSP JSON file
on every PR merge, stored at `platform-gitops/ssp/output/ssp-oscal-v4.0.json`.
This allows FedRAMP-compatible tools (e.g., NIST OSCAL tools, Trestle) to ingest
the SSP programmatically.

**Responsible Role:** ISSO (plan custodian, quarterly spot-check, annual review), AO (approval authority), System Owner (co-approval, boundary decisions), Platform Engineer (IaC change triggers, boundary diagram maintenance), DevSecOps (ssp-freshness-check workflow)

**Parameters:**
- SSP version: v4.0 (git tag `ssp-v4.0`)
- Last AO approval: 2026-03-01
- Annual review month: February (review) / March (AO re-approval)
- Quarterly spot-check: 3 controls per quarter, ISSO-selected
- Significant-change SLA: 15–30 days depending on change type (see trigger table)
- Component gap detection: Nightly automated check (ssp-freshness-check.yaml)
- OSCAL output: Generated on every merge to main

**Evidence / Artifacts:**
- `SSP-LM-v4.0` source (git: `platform-gitops/ssp/controls/`, tag `ssp-v4.0`)
- `SSP-LM-v4.0` human-readable (Confluence: LM-SECURITY / SSP / SSP-LM-v4.0)
- Boundary diagram source (`platform-gitops/ssp/diagrams/boundary-v4.0.drawio`)
- OSCAL SSP output (`platform-gitops/ssp/output/ssp-oscal-v4.0.json`)
- Annual review 2026 (`platform-gitops/ssp/reviews/annual-review-2026.md`)
- Quarterly spot-check records (`platform-gitops/ssp/reviews/spot-checks/`)
- AO approval record (Confluence: LM-SECURITY / SSP / Approvals / AO-Approval-2026-03-01.msg)
- `ssp-freshness-check.yaml` workflow (GitHub Actions: `platform-gitops/.github/workflows/`)
- SSP CHANGELOG (`platform-gitops/ssp/CHANGELOG.md` — v1.0 through v4.0)

**Enhancements Addressed:**
- **PL-2(3) — Plan and Coordinate with Other Organizations:** Security activities that
  affect shared infrastructure are coordinated under a formal process with documented
  advance notice requirements and sign-off records. See section below.

---

## PL-2(3) — Plan and Coordinate with Other Organizations

**Implementation Status:** Implemented

**Implementation Description:**

Security activities on the Links-Matrix Platform that could affect shared infrastructure
or external parties are coordinated before the activity begins. A "security activity"
for this purpose includes: penetration tests, red team exercises, major configuration
changes to shared components, major incident response actions affecting multiple teams,
and DR/failover tests.

**Coordination register:**
All coordination activities are logged in `platform-gitops/ssp/coordination-log.md`.
Each entry records: activity type, affected parties, advance notice provided, acknowledgment
received, and actual execution date.

**Advance notice requirements:**

| Activity | Affected Parties | Advance Notice Required | Acknowledgment Required |
| -------- | --------------- | ----------------------- | ----------------------- |
| Annual penetration test (Coalfire) | Platform Engineering, AWS Account Owner, Legal | 15 business days | Written (email) from Platform Engineering Lead and AO |
| Major Kubernetes version upgrade | All application teams | 10 business days | Slack acknowledgment in `#platform-changes` (logged) |
| DR failover test (us-east-1 → us-west-2) | All application teams, On-call SREs | 10 business days | Written from each affected team lead |
| Emergency IR action affecting shared VPC | AWS Account Owner, adjacent system owners | Best effort — notify during or within 1 hour | Not required for emergency; documented in PIR |
| Major IaC change (VPC/subnet/SG) | Adjacent application teams | 5 business days | Slack acknowledgment in `#infra-changes` |

**Coordination log excerpt (last 12 months):**

| Date | Activity | Parties Notified | Advance Notice | Acknowledgment |
| ---- | -------- | ---------------- | -------------- | -------------- |
| 2026-04-15 | Coalfire annual pentest | Platform Eng, AWS Owner, Legal | 15 BD (2026-03-25) | Written — all parties |
| 2026-03-20 | DR failover test | All app teams, On-call SREs | 10 BD (2026-03-06) | Written — all team leads |
| 2026-02-10 | EKS 1.28→1.29 upgrade | All application teams | 10 BD (2026-01-27) | Slack `#platform-changes` — all teams |
| 2025-11-05 | VPC flow log config change | Adjacent system owner (HR-System) | 5 BD (2025-10-29) | Slack `#infra-changes` |

**Evidence / Artifacts:**
- Coordination log (`platform-gitops/ssp/coordination-log.md` — full history)
- Coalfire pentest coordination email (Confluence: LM-SECURITY / CA / Pentest-2026-Coordination)
- DR failover test notification record (Confluence: LM-SECURITY / CP / DR-Test-2026-Notifications)

---

## Test Procedures

### PL-2 Test Procedure

**Objective:** Verify that the SSP accurately describes the system as currently deployed
and that the version control and significant-change processes function as documented.

**Step 1 — Confirm SSP approval:**
```bash
# Verify git tag and approver commit
git -C platform-gitops log --oneline ssp-v4.0 -1
# Expected: commit with message containing "AO approval 2026-03-01"

# Verify Confluence page last-approved date matches
# (Manual: check Confluence page history for approval notation)
```

**Step 2 — Spot-check boundary accuracy:**
```bash
# Compare AWS Config resource list against SSP boundary table
aws configservice list-discovered-resources \
  --resource-type AWS::EKS::Cluster \
  --query 'resourceIdentifiers[*].resourceName'
# Expected: only lm-prod-cluster and lm-dr-cluster appear
# Any other cluster = boundary discrepancy

# Compare ArgoCD apps against SSP platform tooling table
kubectl get applications -n argocd \
  -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n' | sort
# Expected: matches SSP platform tooling table exactly
```

**Step 3 — Verify OSCAL output is current:**
```bash
# Confirm OSCAL file was generated on last merge
git -C platform-gitops log --oneline \
  ssp/output/ssp-oscal-v4.0.json -1
# Expected: commit date within 30 days (or on last SSP-affecting merge)
```

**Step 4 — Verify freshness check workflow:**
```bash
# Check last workflow run result
gh run list --workflow=ssp-freshness-check.yaml \
  --repo platform-gitops --limit 1 --json conclusion,createdAt
# Expected: conclusion: "success", createdAt: yesterday or today
```

**Step 5 — Verify coordination log is current:**
```bash
# Confirm coordination log has entry for most recent security activity
git -C platform-gitops log --oneline \
  ssp/coordination-log.md -3
# Expected: most recent entry within 6 months (or since last scheduled security activity)
```

**Pass criteria:** AO signature present, boundary matches deployed state, OSCAL output
current, freshness workflow passing, coordination log entry for most recent security activity.

---

## What Makes This GREAT — Examiner's Notes

| Control | What Elevates It |
| ------- | ---------------- |
| PL-2 | SSP source is version-controlled in git alongside the infrastructure it describes — diagram, control statements, and CHANGELOG all in one repo. Confluence is a rendered artifact, not the authoritative source. |
| PL-2 | Significant-change triggers are formally defined by change type with explicit SLAs (15–30 days). "ISSO discretion" is replaced by a table. Machine enforcement via nightly `ssp-freshness-check.yaml` creating Jira tickets for undocumented components. |
| PL-2 | Quarterly spot-check history with documented discrepancies — evidence that control statements are verified against reality between annual reviews. Most SSPs verify accuracy only once per year. |
| PL-2 | OSCAL JSON output on every merge — SSP is machine-readable without any conversion work. FedRAMP tools, compliance platforms, and JADE can ingest it directly. |
| PL-2(3) | Coordination is not informal — advance notice requirements are specified by activity type, acknowledgment is required in writing or traceable channel, and every coordination event is logged. Emergency carve-out is documented with PIR requirement. |
| PL-2(3) | Coordination log shows a 12-month history of actual coordination events — assessors can verify the process is followed, not just documented. |
| Both | Boundary table distinguishes system-specific components from inherited external services with explicit inherited control citations — auditors immediately understand what is in scope and what is leveraged. |
