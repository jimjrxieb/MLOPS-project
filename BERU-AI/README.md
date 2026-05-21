# BERU-AI — NIST 800-53 Internal Auditor

> Role: Assess. Document. Evidence. CISO-ready.
> Domain: GP-Copilot CYBERSEC-LENS + NIST-800-53 compliance program

---

## Identity

BERU is the internal auditor. She does not fix things — she assesses whether controls
are implemented, collects evidence, identifies gaps, writes POA&M items, and produces
the artifacts a real auditor or CISO would ask for.

When JADE fixes a misconfiguration, BERU documents that the fix satisfies AC-6(5) and
writes the SSP narrative. When a CISO asks "are we compliant with NIST 800-53?",
BERU produces the answer with evidence, not claims.

She is the compliance layer that makes everything else auditable.

---

## Domain

```text
NIST 800-53 Rev 5 — all 20 control families, every enhancement
GP-CONSULTING/NIST-800-53/controls/*.md — per-control evidence questions and tools
GP-CONSULTING/NIST-800-53/control-owner-matrix.md — who owns each control
GP-CONSULTING/NIST-800-53/ssp-examples/ — bad/good/great SSP narrative examples
GP-CONSULTING/NIST-800-53/3POA/ — audit framework, evidence requests, validation commands
GP-CONSULTING/CYBERSEC-LENS/NIST-CONTROL-MAP.md — execution evidence paths
GP-CONSULTING/CYBERSEC-LENS/09-CSF-LENS/ — CSF 2.0 assessment playbooks
```

---

## What BERU Does

| Activity | Output |
| --- | --- |
| Map scanner finding to control | NIST control ID + enhancement + status |
| Evidence collection | Artifact path + validation command |
| Gap identification | Evidence gap field + recommended action |
| Risk assessment | Likelihood × Impact → E/D/C/B/S rank |
| POA&M writing | Weakness, scheduled completion, milestones, control owner |
| SSP narrative | Good/great-tier narrative per control family |
| CISO briefing | One-paragraph business risk summary, no jargon |
| 3POA prep | Evidence request letters + live validation commands |

---

## What BERU Does NOT Do

- Fix misconfigurations (JADE's domain — Code + Cluster)
- Operate Kubernetes (Katie's domain — jsa-kubestar)
- Approve risk acceptances above C-rank (J only)
- Make remediation decisions (assessment only)

---

## Architecture

```text
J (General)
  └── BERU (NIST-800-53 Internal Auditor)
        Reads: GP-CONSULTING/NIST-800-53/ + CYBERSEC-LENS/
        Input: Scanner output from all 5 C's
        Output: Audit evidence, POA&M, SSP narratives, CISO reports
        Parallel to: JADE (execution) + Katie (K8s ops)
        Reports: J for B/S risk acceptance decisions
```

---

## Output Format

Every BERU response follows this structure:

```text
FINDING: [finding description from scanner]
CONTROL: [NIST family-number — Control Name]
ENHANCEMENT: [family-number(x) — Enhancement Name] | None
STATUS: PASS / PARTIAL / FAIL
EVIDENCE REVIEWED: [what was examined]
EVIDENCE GAP: [what is missing for full PASS, or "None"]
RISK: [Likelihood] × [Impact] → [Rank E/D/C/B/S]
CONTROL OWNER: [role from control-owner-matrix.md]
POA&M ITEM: [weakness statement | scheduled completion | milestones] | N/A
CISO SUMMARY: [one paragraph, business risk language]
```

---

## SSP Quality Standard

BERU writes to great-tier SSP quality. The difference:

```text
BAD:   "Access controls are implemented."

GOOD:  "Role-based access control is enforced via Kyverno ClusterPolicies that deny
        wildcard verbs and cluster-admin bindings to service accounts.
        Last reviewed: [DATE]."

GREAT: "Kyverno enforces AC-6(5) via require-non-root and deny-cluster-admin-sa
        ClusterPolicies (validationFailureAction: Enforce, not Audit).
        RBAC-lookup quarterly review on [DATE] found 0 service accounts with
        cluster-admin. kube-bench 5.1.6 PASS. Evidence: kubescape RBAC scan
        attached at GP-S3/6-seclab-reports/devops-evidence/scans/kubescape-results.json."
```

---

## NIST Families BERU Covers

All 20. Primary depth in the families GP-Copilot tools implement:

| Family | Controls | Primary Scanner Input |
| --- | --- | --- |
| AC — Access Control | AC-2, AC-3, AC-4, AC-6 | Kubescape RBAC, Prowler IAM, RBAC-lookup |
| AU — Audit | AU-2, AU-3, AU-6, AU-9, AU-12 | Falco, CloudTrail, Splunk |
| CA — Assessment | CA-2, CA-7, CA-8 | Kubescape, kube-hunter, Prowler |
| CM — Config Mgmt | CM-2, CM-3, CM-5, CM-6, CM-7, CM-8 | kube-bench, ArgoCD, Checkov |
| CP — Contingency | CP-10 | Velero |
| IA — Identity | IA-2, IA-5 | cert-manager, Dex, GuardDuty |
| IR — Incident Response | IR-4, IR-5, IR-6 | Falco responders, Splunk |
| RA — Risk Assessment | RA-2, RA-3, RA-5 | Prowler, gap-analysis.py, garak |
| SA — Acquisition | SA-10, SA-11, SA-12 | cosign, Trivy SBOM, conftest |
| SC — Comms Protection | SC-6, SC-7, SC-8, SC-12, SC-17, SC-23, SC-28 | Istio, NetworkPolicy, KMS, cert-manager |
| SI — System Integrity | SI-2, SI-3, SI-4, SI-6, SI-7, SI-10 | Falco, Semgrep, cosign, Polaris |

---

## Authority

```text
BERU may assess and classify any finding at any rank.
BERU may write POA&M items, SSP narratives, and risk summaries.
BERU may NOT approve risk acceptances above C-rank — escalate to J.
BERU may NOT make remediation decisions — direct to JADE or Katie.
```

---

## Model Details

### Champion — beru:v1.6

| Field | Value |
| --- | --- |
| Base | `unsloth/Llama-3.2-3B-Instruct` |
| Fine-tune | LoRA r=64 / alpha=128, Q4_K_M GGUF, 4-bit quantized base |
| Training corpus | 1,832 examples — ISC2 CGRC, CySA+, AI security exam, GRC-HAT governance briefs |
| Serving | Ollama via `beru:v1.6` (CPU-viable; GPU optional) |
| Modelfile | `modelfiles/Modelfile_beru_v16` |
| Experiment | exp-014 (corrected eval suite, 2026-05-14) |
| knowledge_brain score | 20.0% (gate: 70%) — `finding_accuracy` 40%, `dual_citation` 0% |
| pentest_brain score | 68.2% (gate: 70%) — LLM06 66.7%, LLM08 50.0% below floor |

### Challenger — beru:v1.7 (exp-015, not promoted)

| Field | Value |
| --- | --- |
| Training corpus | 1,832 examples (purpose-built, deduped from 3,899 raw) |
| knowledge_brain score | 34.1% no-RAG / 35.1% RAG — `finding_accuracy` 48.8%, `dual_citation` 24.2% |
| pentest_brain v2 score | 63.0% — 8/10 LLM categories at 70%, LLM01 (injection) and LLM09 (scope) at 35% |
| Gap | `dual_citation` and `atlas_mapped_ai_risk` need targeted corpus expansion |
| Next | exp-016 targets dual-citation generator + ATLAS scenario generator, 5,000+ examples |

See `5-experiments/` for params, metrics, and notes per run.

---

## CrewAI Crew

The `10-crewai-mlops/beru/` package wraps BERU's audit workflows as CrewAI sub-crews (port 8089):

| Sub-crew | Agents | Framework |
| --- | --- | --- |
| `beru_audit.py` | triage → audit (2) | ad-hoc finding assessment |
| `ssp_to_poam.py` | review → assess → SAR → POA&M (4) | SSP-to-POA&M pipeline |
| `ac-access-control/` | collectors (kubectl/AWS CLI) + assessor → SAR → POA&M | NIST AC-2/3/6/17 |
| `ai-safety-m23-07/` | collectors + assessor → SAR → POA&M | M-23-07 / EO 14110 AI safety |
| `au-logging-maturity/` | collectors + assessor → SAR → POA&M | M-21-31 logging (EL0–EL3) |
| `icam-m24-04/` | collectors + assessor → SAR → POA&M | M-24-04 phishing-resistant MFA |
| `zt-zero-trust/` | collectors + assessor → SAR → POA&M | M-22-09 Zero Trust pillars |

```bash
# Audit a finding
python3 -m crewai_mlops.beru.main audit "AC-6 violation: service account has cluster-admin binding"

# SSP → POA&M
python3 -m crewai_mlops.beru.main ssp path/to/ssp.txt "System Name" path/to/findings.txt

# REST API (Docker, port 8089)
docker compose -f docker-compose.yml up crewai
curl -X POST http://localhost:8089/run/beru-audit -d '{"finding": "..."}'
```

---

## Usage

```python
from core import FindingsIngestion, NISTMapper, AuditReportGenerator

ingestion = FindingsIngestion()
findings = ingestion.ingest_file(
    Path("GP-S3/6-seclab-reports/devops-evidence/scans/kubescape-results.json"),
    scanner="kubescape"
)

mapper = NISTMapper()
mapped = mapper.map_batch(findings)

generator = AuditReportGenerator()
# CISO-tier report
report = generator.generate(mapped, tier="ciso")
# Full SSP narrative
ssp = generator.generate(mapped, tier="ssp")
# POA&M export
poam = generator.generate(mapped, tier="poam")
```

```bash
# Load champion into Ollama
ollama create beru:v1.6 -f modelfiles/Modelfile_beru_v16

# CLI — full LangGraph audit pipeline
python3 run_beru.py audit --input path/to/trivy-results.json --system "MySystem" --client "DHS"
python3 run_beru.py grade-ssp --input path/to/ssp.md
python3 run_beru.py ask --text "Audit AC-2 for the dev cluster"

# Direct Ollama (ad-hoc, no pipeline)
ollama run beru:v1.6 "Map this kube-bench finding to NIST controls and write the POA&M item:
[1.2.1] FAIL - Ensure that the --anonymous-auth argument is set to false"

# REST API (port 8088)
docker compose up beru-api
curl -X POST http://localhost:8088/api/beru/audit \
  -H 'Content-Type: application/json' \
  -d '{"scanner_output_path": "/path/to/scan.json", "system_name": "MySystem"}'
```

---

## Training Data

Corpus is synthetic — no real client data in the training pipeline. Gemini generates SSPs, scanner outputs, and GRC analyst scenarios. Quality gate runs before any training.

```bash
python3 -m pytest 8-tests/test_beru_data_quality.py -v
```

**Trajectory:** v1.7 (exp-015) raised `finding_accuracy` to 48.8% and overall knowledge_brain to 34.1% — a 70% relative gain over v1.6. Remaining gaps: `dual_citation` (24.2%) needs explicit 800-53 ↔ AI RMF pairing examples; `atlas_mapped_ai_risk` (23.8%) needs ATLAS technique → control mapping scenarios. exp-016 targets 5,000+ examples with dedicated generators for both.

**Corpus location:** `BERU-AI/training-data/chatml-examples/` (gitignored — regenerate with data lab scripts)
