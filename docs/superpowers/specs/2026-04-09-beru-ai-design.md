# BERU-AI Design Spec

> Shadow-rank security analyst model. LLaMA 3.1-8B, LoRA fine-tuned on CompTIA CySA+ domains and NIST frameworks. Ingests real scanner findings, learns triage patterns, generates CISO-ready risk summaries.

**Name origin**: Beru — a high-ranking loyal shadow from Solo Leveling.

**Approved**: 2026-04-09

---

## 1. Identity & Persona

BERU is a CySA+ certified security analyst. Not a DevOps engineer (JADE), not a K8s operator (Katie), not a classifier (RANK-AI). BERU reads the same screens a SOC analyst reads at 8 AM and makes the same decisions.

BERU doesn't just know what Nessus is — BERU reads Nessus plugin output the way a human analyst does. Sees a GuardDuty finding and immediately thinks: what NIST control does this map to, what's the blast radius, what do I tell the CISO, and what's the fix.

**Base model**: LLaMA 3.1-8B-Instruct (same base as JADE)
**Training method**: LoRA fine-tune via `1-FineTuning-Pipeline/` (r=64, alpha=128, 4-bit quant, Unsloth)
**Serving**: Ollama GGUF (`beru:v1.0`)

### What BERU Is NOT

- Not a DevOps engineer (that's JADE)
- Not a K8s operator (that's Katie)
- Not a rank classifier (that's RANK-AI)
- Not a scanner — BERU reads scanner output, doesn't generate it

---

## 2. Domain Weights

Maps to CompTIA CySA+ exam domains, extended with NIST depth.

| Domain | Weight | What It Covers |
|--------|--------|----------------|
| **Threat & Vuln Management** | 30% | Scanner output interpretation, CVE triage, vuln lifecycle, patch prioritization, CVSS contextual scoring |
| **Security Operations & Monitoring** | 25% | SIEM correlation, log analysis, IDS/IPS alerts (Suricata, Wazuh), GuardDuty/SecurityHub findings, network traffic patterns |
| **NIST & Compliance Mapping** | 20% | 800-53 control mapping, CSF categories, control families, evidence packaging, gap analysis, POA&M generation |
| **Incident Response & Forensics** | 15% | 800-61 IR lifecycle, containment decisions, forensic preservation, timeline reconstruction, communication templates |
| **Risk Management & Reporting** | 10% | CISO-ready summaries, risk scoring, business impact translation, remediation ROI, executive dashboards |

### OSI Model Perspective

BERU thinks in defense-in-depth layers, not in K8s manifests. The same tools that JADE uses (Trivy, Prowler, GuardDuty) are viewed through a different lens: what framework is this tool associated with, why is it there, how does the tool block the threat, what NIST control does it cover, how to spot bad configurations, and how to fix them.

---

## 3. Directory Structure

```
BERU-AI/
├── core/
│   ├── __init__.py
│   ├── findings_ingestion.py    — Parse raw scanner output (Nessus, GuardDuty, Prowler, Wazuh, etc.)
│   ├── triage_engine.py         — Learned triage patterns: severity + context -> priority + action
│   ├── nist_mapper.py           — Finding -> NIST 800-53 control family mapping
│   ├── risk_summary.py          — Generate CISO-ready narrative + structured JSON
│   └── tool_output_parser.py    — Scanner-specific output format parsers (CSV, JSON, SARIF, etc.)
├── config/
│   ├── system_prompt.txt        — BERU's persona and instruction set
│   ├── domain_weights.yaml      — CySA+ domain weights for training/eval
│   ├── scanner_mappings.yaml    — Scanner -> output format -> NIST control family lookup
│   └── risk_templates.yaml      — CISO summary templates (executive, technical, compliance)
├── providers/
│   ├── __init__.py
│   ├── base.py                  — BaseLLMProvider (lean copy, no JADE coupling)
│   └── ollama.py                — OllamaProvider for beru:v1.0
├── Modelfile_beru8b             — Ollama registration (FROM beru-llama8b-v1.0.gguf)
├── requirements.txt
└── README.md
```

Independent from JADE-AI. No shared runtime imports. Sibling models, not parent-child.

---

## 4. Training Data Pipeline

### Data Readiness (as of 2026-04-09)

**seclab-findings/ is empty.** No real scanner output exists in the training pipeline yet.
`GP-S3/6-seclab-reports/` has directory structure only (dashboards/, evidence/, governance/, poam/) — all empty.
The findings DBs in `GP-S3/4-sql/` are empty shells. One synthetic GuardDuty log exists in eval test data.

Training cannot start until real scanner output lands in `0-data-lab/seclab-findings/`.
This is Phase 0 of implementation.

### Data Flow

```
GP-S3/6-seclab-reports/          <- Raw scanner exports from seclab
        |
        v  (manual copy)
0-data-lab/seclab-findings/      <- Shared landing zone for ALL models (not BERU-specific)
        |                           Raw Nessus CSV, GuardDuty JSON, Prowler output,
        |                           Wazuh alerts, Suricata logs, etc.
        |
        v  (clean + classify + tag)
0-data-lab/tools/
   classify_seclab_findings.py      - Tag findings by target model (beru, jade, katie)
                                      and pipeline (training vs rag). Not hardcoded —
                                      tagging rules determine which model gets what.
   generate_triage_training.py      - Scanner output -> "what would the analyst do?"
   generate_nist_mapping.py         - Finding -> NIST control mapping with reasoning
   generate_risk_summaries.py       - Findings batch -> CISO-ready summary
   generate_tool_navigation.py      - "Here's a Nessus scan, walk me through it"
        |
        |-->  1-FineTuning-Pipeline/01-raw-data-lake/  (training JSONL -> LoRA pipeline)
        |
        '-->  2-RagIngestion-Pipeline/01-unprocessed/     (reference docs -> ChromaDB)
```

### Training Data Categories

Training examples are grounded in real tool output, not abstract Q&A.

| Category | Example Training Pair |
|----------|----------------------|
| **Scanner reading** | User: "Here's a Nessus plugin 19506 output: [raw output]. What am I looking at?" -> BERU walks through it like an analyst |
| **Triage decision** | User: "GuardDuty shows UnauthorizedAccess:EC2/MaliciousIPCaller.Custom. CVSS 7.2. Production VPC." -> BERU: priority, blast radius, immediate action, NIST control |
| **NIST mapping** | User: "Prowler found S3 bucket without encryption. Map this." -> BERU: SC-28 (Protection of Information at Rest), evidence needed, remediation |
| **Config fix** | User: "Wazuh rule 550 keeps firing false positives on our jumpbox." -> BERU: here's the rule, here's why it fires, here's the tuned config |
| **CISO summary** | User: "I have 47 HIGH findings from this month's scan cycle. Summarize for the CISO." -> BERU: executive narrative, top 5 risks, business impact, remediation timeline, NIST gaps |
| **Tool navigation** | User: "Walk me through interpreting a Suricata fast.log." -> BERU: field-by-field breakdown with real examples |

### Scanners in Scope

All scanner families — BERU's diet is broad:

- **Vulnerability scanners**: Nessus, OpenVAS, Trivy (host-mode), Nuclei
- **SIEM/log analysis**: Splunk, Elastic SIEM, Wazuh
- **Cloud security**: GuardDuty, SecurityHub, Prowler, ScoutSuite
- **Endpoint/network**: CrowdStrike, Suricata, Zeek
- **Compliance**: OpenSCAP, SCAP benchmarks, Lynis
- **IaC/DevSec overlap**: Checkov, tfsec, Trivy (config-mode)

### Quality Gate (extends existing pattern)

Same mandatory gate as Katie/JADE (ChatML format, no garbage, no transcripts, dedup, min chunk size), plus additional gates for analyst-grade training data:

1. **Real output check**: Training examples must contain actual scanner output format, not paraphrased descriptions
2. **NIST accuracy**: Every control mapping must reference a real 800-53 control ID (not fabricated)
3. **No vendor marketing**: Scanner descriptions must be operational, not sales copy
4. **Triage grounding**: Every triage recommendation must include specific next steps, not "investigate further"
5. **Risk language check**: CISO summaries must use business impact language, not just technical severity

---

## 5. ChromaDB Collections

BERU gets its own collections. `beru-nist-800-53` re-ingests from JADE's existing `jade-nist-800-53` to save research tokens, then expands with CySA+-mapped controls.

| Collection | What Goes In |
|-----------|-------------|
| `beru-nist-800-53` | Source documents from JADE's NIST collection re-ingested through BERU's own pipeline (not vector copy — BERU may chunk differently), then expanded with CySA+ mapped controls |
| `beru-scanner-knowledge` | Scanner documentation, output format specs, plugin databases |
| `beru-triage-patterns` | Historical triage decisions from seclab (finding -> action taken -> outcome) |
| `beru-risk-templates` | CISO report templates, executive summary patterns, compliance language |
| `beru-incident-response` | 800-61 procedures, IR playbooks, containment checklists |

All collections use the same embedding model: `nomic-embed-text` (768-dim) via Ollama.

---

## 6. Eval Framework

Lives in `4-eval-clarify/` alongside JADE's eval suite.

```
4-eval-clarify/
├── beru_eval_suite_v1.jsonl        — BERU benchmark questions
├── beru_eval_runner.py             — Runner adapted for BERU's output format
├── 2-test-data/
│   └── beru/                       — Sample scanner outputs for eval
└── 3-results/
    └── beru/                       — BERU eval results per experiment
```

### Eval Domains

| Domain | Questions | Weight | Pass Gate |
|--------|-----------|--------|-----------|
| Threat & Vuln Management | ~120 | 30% | >=50% |
| Security Ops & Monitoring | ~100 | 25% | >=50% |
| NIST & Compliance Mapping | ~80 | 20% | >=50% |
| Incident Response & Forensics | ~60 | 15% | >=50% |
| Risk Management & Reporting | ~40 | 10% | >=50% |
| **Total** | **~400** | **100%** | **Weighted >=60%** |

### Eval Types (Knowledge + Task Performance)

| Type | What It Tests | Example |
|------|---------------|---------|
| **Knowledge** | Does BERU know the domain? | "What NIST control family covers audit logging?" |
| **Scanner reading** | Can BERU parse real output? | Given raw Nessus CSV -> extract top 5 critical findings |
| **Triage task** | Can BERU make the right call? | Given GuardDuty finding + context -> correct priority + action |
| **NIST mapping task** | Can BERU map accurately? | Given finding -> correct 800-53 control ID + justification |
| **Summary generation** | Can BERU write for a CISO? | Given 20 findings -> executive risk summary (graded on structure, accuracy, business language) |

### Zero Tolerance

- Hallucinated NIST control IDs
- Made-up scanner plugin numbers
- "Investigate further" as a triage recommendation without specific steps

### Promotion Gates

Same pattern as Katie/JADE:
- Each domain >=50%
- Weighted total >=60% -> production
- 40-60% -> targeted data generation
- <40% -> review training data quality
- New BERU must beat current champion on same eval suite

---

## 7. GP-API Integration

New route file in the existing FastAPI app.

```
GP-INFRA/GP-API/
├── main.py                  — Add beru router import
└── routes/
    ├── jade.py              — Existing JADE endpoints
    └── beru.py              — New BERU endpoints
```

### Endpoints

| Endpoint | Method | What It Does |
|----------|--------|-------------|
| `/api/beru/health` | GET | Model loaded? Ollama reachable? ChromaDB collections present? |
| `/api/beru/triage` | POST | Accepts raw scanner findings -> returns triage priority, NIST mapping, recommended action |
| `/api/beru/summarize` | POST | Accepts batch of findings -> returns CISO-ready risk summary (JSON + narrative) |
| `/api/beru/nist-map` | POST | Accepts single finding -> returns mapped NIST 800-53 controls with reasoning |
| `/api/beru/explain` | POST | Accepts scanner output blob -> returns analyst walkthrough |

### Output Format (Both Structured + Narrative)

```json
{
  "finding_id": "guardduty-2026-04-09-001",
  "triage": {
    "priority": "P1",
    "severity_context": "HIGH in production VPC with PII workloads",
    "blast_radius": "3 EC2 instances, 1 RDS, reachable from public subnet",
    "immediate_action": "Isolate instance i-0abc123 via security group deny-all",
    "remediation": "Rotate IAM keys, review CloudTrail for lateral movement",
    "nist_controls": ["SI-4", "IR-4", "AC-6"],
    "confidence": 0.87
  },
  "ciso_summary": "A production EC2 instance communicated with a known malicious IP. This indicates potential compromise of workloads handling customer PII. Immediate network isolation applied. IAM credential rotation and forensic review recommended within 4 hours. Maps to NIST SI-4 (monitoring) and IR-4 (incident handling) -- both required for our FedRAMP Moderate boundary.",
  "evidence": {
    "scanner": "guardduty",
    "finding_type": "UnauthorizedAccess:EC2/MaliciousIPCaller.Custom",
    "timestamp": "2026-04-09T14:23:00Z"
  }
}
```

---

## 8. Rank Authority

BERU follows the same rank system. Same ceiling as JADE and Katie.

| Rank | BERU's Role |
|------|------------|
| **E/D** | Auto-triage: known CVEs with patches, standard misconfigs, routine scan noise |
| **C** | BERU proposes triage + NIST mapping + summary. Confidence-scored. Logged. May need approval. |
| **B** | BERU provides full analysis package. Human decides. |
| **S** | BERU provides dashboards and risk context. Human only. |

**BERU max authority: C-rank. Hardcoded. Never change.**

### Updated Authority Chain

```
Constant (President) -> J (General) -> JADE (Fleet Cmdr -- platform security)
                                     -> BERU (Shadow -- risk analysis & compliance)
                                       -> Katie (Fast triage -- routing & classification)
                                         -> JSA Agents -> Iron Legion
```

BERU sits alongside JADE, not under JADE. They are peers with different specializations:
- JADE calls BERU when a finding needs NIST mapping or a risk summary
- BERU calls JADE when a finding needs platform-level remediation

---

## 9. Experiment Tracking

Follows existing pattern in `5-experiments/`.

```
5-experiments/
└── exp-NNN-beru-v1-cysa/
    ├── params.yaml       — LoRA config, domain weights, training data version
    ├── metrics.json      — Eval results per domain
    └── notes.md          — Hypothesis, observations, decision
```

Model card goes to `6-model-cards/challenger/beru-v1.md` until promoted to `6-model-cards/champion/`.

---

## 10. Data Schema

New schema at `7-data-schemas/beru_training_example.json` extending the base ChatML format with BERU-specific scope keywords (CySA+ domains, NIST control families, scanner names).

New schema at `7-data-schemas/beru_risk_summary.json` defining the structured output format for CISO summaries.
