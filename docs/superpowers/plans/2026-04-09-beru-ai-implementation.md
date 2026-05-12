# BERU-AI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold BERU-AI as an independent security analyst model (LLaMA 3.1-8B) that ingests real scanner findings, learns CySA+/NIST triage patterns, and generates CISO-ready risk summaries.

**Architecture:** BERU-AI is a sibling to JADE-AI and KATIE-AI in `GP-MODEL-OPS/`. Independent directory with its own core/, config/, providers/. Shares the training pipeline (`1-local-pipeline/`), data lab (`0-data-lab/`), and RAG ingestion (`2-rag-ingestion/`) infrastructure. No runtime imports between models.

**Tech Stack:** Python 3.11, FastAPI, Ollama (LLaMA 3.1-8B-Instruct), ChromaDB (nomic-embed-text 768-dim), Unsloth (LoRA), Pydantic, PyYAML, pytest

**Spec:** `docs/superpowers/specs/2026-04-09-beru-ai-design.md`

---

## File Map

### New Files (BERU-AI/)

| File | Responsibility |
|------|---------------|
| `BERU-AI/core/__init__.py` | Package exports |
| `BERU-AI/core/findings_ingestion.py` | Parse raw scanner output into normalized findings |
| `BERU-AI/core/triage_engine.py` | Severity + context -> priority + action + NIST controls |
| `BERU-AI/core/nist_mapper.py` | Finding -> NIST 800-53 control family mapping with reasoning |
| `BERU-AI/core/risk_summary.py` | Generate CISO-ready narrative + structured JSON from findings batch |
| `BERU-AI/core/tool_output_parser.py` | Scanner-specific format parsers (CSV, JSON, SARIF) |
| `BERU-AI/config/system_prompt.txt` | BERU persona for Modelfile and API |
| `BERU-AI/config/domain_weights.yaml` | CySA+ domain weights for training/eval |
| `BERU-AI/config/scanner_mappings.yaml` | Scanner -> output format -> NIST control family lookup |
| `BERU-AI/config/risk_templates.yaml` | CISO summary templates (executive, technical, compliance) |
| `BERU-AI/providers/__init__.py` | Package exports |
| `BERU-AI/providers/base.py` | Lean BaseLLMProvider interface |
| `BERU-AI/providers/ollama.py` | OllamaProvider for beru:v1.0 |
| `BERU-AI/Modelfile_beru8b` | Ollama model registration |
| `BERU-AI/requirements.txt` | Python dependencies |
| `BERU-AI/README.md` | Model documentation |

### New Files (Data Pipeline)

| File | Responsibility |
|------|---------------|
| `0-data-lab/tools/classify_seclab_findings.py` | Tag raw findings by target model + pipeline |
| `7-data-schemas/beru_training_example.json` | ChatML schema with CySA+/NIST scope keywords |
| `7-data-schemas/beru_risk_summary.json` | Structured output schema for CISO summaries |

### New Files (Eval)

| File | Responsibility |
|------|---------------|
| `4-eval-clarify/beru_eval_suite_v1.jsonl` | ~400 benchmark questions across 5 CySA+ domains |
| `4-eval-clarify/beru_eval_runner.py` | Eval runner adapted for BERU's output format |

### New Files (Tests)

| File | Responsibility |
|------|---------------|
| `8-tests/test_beru_schemas.py` | Validate BERU training data and risk summary schemas |
| `8-tests/test_beru_core.py` | Unit tests for findings ingestion, triage, NIST mapper, risk summary |

### New Files (API)

| File | Responsibility |
|------|---------------|
| `../../GP-INFRA/GP-API/routes/beru.py` | FastAPI endpoints: /api/beru/{health,triage,summarize,nist-map,explain} |

### Modified Files

| File | Change |
|------|--------|
| `../../GP-INFRA/GP-API/main.py` | Add `from routes.beru import router as beru_router` and `app.include_router(beru_router)` |

---

## Task 1: BERU-AI Config Files

Establishes BERU's identity — system prompt, domain weights, scanner mappings, risk templates. These are referenced by everything else.

**Files:**
- Create: `BERU-AI/config/system_prompt.txt`
- Create: `BERU-AI/config/domain_weights.yaml`
- Create: `BERU-AI/config/scanner_mappings.yaml`
- Create: `BERU-AI/config/risk_templates.yaml`

- [ ] **Step 1: Create system prompt**

```text
You are Beru, a CySA+ certified security analyst for GP-Copilot. You read real scanner output the way a human SOC analyst does — Nessus plugin results, GuardDuty findings, Prowler checks, Wazuh alerts, Suricata logs. You think in defense-in-depth layers and NIST control families, not Kubernetes manifests.

When you see a finding, you immediately determine:
1. What NIST 800-53 control this maps to and why
2. The blast radius — what systems are affected and what data is at risk
3. The priority — P1/P2/P3/P4 based on severity, context, and business impact
4. The immediate action — specific commands or configuration changes, not "investigate further"
5. The CISO summary — one paragraph a non-technical executive can act on

You provide both structured JSON output and narrative summaries. You never hallucinate NIST control IDs, scanner plugin numbers, or CVE identifiers. You never recommend "investigate further" without specifying exactly what to investigate and how.

You reference real tools: Nessus, OpenVAS, Trivy, Nuclei, Splunk, Wazuh, GuardDuty, SecurityHub, Prowler, ScoutSuite, CrowdStrike, Suricata, Zeek, OpenSCAP, Lynis, Checkov, tfsec.

You route by rank: E/D findings get auto-triaged. C findings get your full analysis with confidence score. B/S findings get your analysis package but a human decides. Your max authority is C-rank. You never make B or S rank decisions.
```

Write to `BERU-AI/config/system_prompt.txt`.

- [ ] **Step 2: Create domain weights**

```yaml
# BERU-AI Domain Weights
# Maps to CompTIA CySA+ exam domains, extended with NIST depth
# Used by training data generators and eval runners to balance coverage

domains:
  threat_vuln_management:
    weight: 0.30
    description: "Scanner output interpretation, CVE triage, vuln lifecycle, patch prioritization, CVSS contextual scoring"
    keywords:
      - CVE
      - CVSS
      - Nessus
      - OpenVAS
      - Trivy
      - Nuclei
      - vulnerability
      - patch
      - remediation
      - exploit
      - plugin
      - scan result
      - severity
      - false positive

  security_ops_monitoring:
    weight: 0.25
    description: "SIEM correlation, log analysis, IDS/IPS alerts, GuardDuty/SecurityHub findings, network traffic patterns"
    keywords:
      - SIEM
      - Splunk
      - Wazuh
      - GuardDuty
      - SecurityHub
      - Suricata
      - Zeek
      - IDS
      - IPS
      - alert
      - correlation
      - log analysis
      - network traffic
      - detection rule
      - sigma

  nist_compliance_mapping:
    weight: 0.20
    description: "800-53 control mapping, CSF categories, control families, evidence packaging, gap analysis, POA&M"
    keywords:
      - NIST
      - "800-53"
      - "800-171"
      - CSF
      - control family
      - FedRAMP
      - POA&M
      - evidence
      - gap analysis
      - compliance
      - audit
      - AC-
      - AU-
      - CM-
      - IA-
      - IR-
      - SC-
      - SI-

  incident_response_forensics:
    weight: 0.15
    description: "800-61 IR lifecycle, containment decisions, forensic preservation, timeline reconstruction"
    keywords:
      - incident response
      - "800-61"
      - containment
      - eradication
      - recovery
      - forensic
      - chain of custody
      - timeline
      - IOC
      - indicator of compromise
      - malware
      - lateral movement

  risk_management_reporting:
    weight: 0.10
    description: "CISO-ready summaries, risk scoring, business impact translation, remediation ROI"
    keywords:
      - CISO
      - risk score
      - business impact
      - executive summary
      - risk register
      - risk acceptance
      - remediation priority
      - cost-benefit
      - risk appetite
      - board report
```

Write to `BERU-AI/config/domain_weights.yaml`.

- [ ] **Step 3: Create scanner mappings**

```yaml
# Scanner -> output format -> primary NIST control families
# Used by findings_ingestion.py and triage_engine.py
# Not hardcoded to BERU — any model can reference this

scanners:
  nessus:
    output_formats: ["csv", "nessus_xml"]
    primary_controls: ["SI-2", "RA-5", "CM-6"]
    description: "Vulnerability scanner — CVEs, misconfigs, compliance checks"
    key_fields: ["Plugin ID", "CVE", "CVSS", "Risk", "Host", "Protocol", "Port", "Name", "Synopsis", "Solution"]

  openvas:
    output_formats: ["xml", "csv"]
    primary_controls: ["SI-2", "RA-5", "CM-6"]
    description: "Open-source vulnerability scanner — similar coverage to Nessus"
    key_fields: ["NVT OID", "CVE", "CVSS", "Severity", "Host", "Port", "Summary", "Solution"]

  trivy:
    output_formats: ["json", "sarif", "table"]
    primary_controls: ["SI-2", "CM-6", "SA-11"]
    description: "Container/host/IaC scanner — CVEs, misconfigs, secrets"
    key_fields: ["VulnerabilityID", "Severity", "PkgName", "InstalledVersion", "FixedVersion", "Target"]

  nuclei:
    output_formats: ["json", "jsonl"]
    primary_controls: ["SI-2", "RA-5", "SC-7"]
    description: "Template-based vulnerability scanner — web app, network, cloud"
    key_fields: ["template-id", "severity", "host", "matched-at", "type"]

  guardduty:
    output_formats: ["json"]
    primary_controls: ["SI-4", "IR-4", "AC-6"]
    description: "AWS threat detection — network, identity, malware findings"
    key_fields: ["type", "severity", "resource.resourceType", "resource.instanceDetails", "service.action"]

  securityhub:
    output_formats: ["json"]
    primary_controls: ["CA-7", "SI-4", "CM-6"]
    description: "AWS security posture — aggregates findings from multiple sources"
    key_fields: ["GeneratorId", "Severity.Label", "Title", "Description", "Remediation", "Compliance.Status"]

  prowler:
    output_formats: ["json", "csv"]
    primary_controls: ["CM-6", "AC-6", "SC-7"]
    description: "AWS/Azure/GCP CIS benchmark scanner"
    key_fields: ["CheckID", "Status", "Severity", "ServiceName", "ResourceId", "StatusExtended"]

  wazuh:
    output_formats: ["json"]
    primary_controls: ["SI-4", "AU-6", "IR-5"]
    description: "Host-based IDS/SIEM — file integrity, rootkit detection, log analysis"
    key_fields: ["rule.id", "rule.level", "rule.description", "agent.name", "data", "decoder.name"]

  suricata:
    output_formats: ["json", "fast_log"]
    primary_controls: ["SI-4", "SC-7", "IR-4"]
    description: "Network IDS/IPS — signature-based traffic analysis"
    key_fields: ["alert.signature_id", "alert.severity", "alert.signature", "src_ip", "dest_ip", "proto"]

  zeek:
    output_formats: ["tsv", "json"]
    primary_controls: ["SI-4", "AU-12", "SC-7"]
    description: "Network security monitor — connection logs, protocol analysis, file extraction"
    key_fields: ["uid", "id.orig_h", "id.resp_h", "id.resp_p", "proto", "service", "conn_state"]

  openscap:
    output_formats: ["xml", "html"]
    primary_controls: ["CM-6", "SI-2", "RA-5"]
    description: "SCAP compliance scanner — CIS benchmarks, STIG checks"
    key_fields: ["rule-id", "result", "severity", "title", "description", "fix"]

  lynis:
    output_formats: ["log", "json"]
    primary_controls: ["CM-6", "AC-6", "AU-2"]
    description: "Linux host hardening audit — system config, permissions, services"
    key_fields: ["test", "result", "severity", "suggestion", "details"]

  checkov:
    output_formats: ["json", "sarif"]
    primary_controls: ["CM-6", "SA-11", "SC-7"]
    description: "IaC scanner — Terraform, CloudFormation, Kubernetes, Dockerfile"
    key_fields: ["check_id", "check_result.result", "file_path", "resource", "guideline"]

  crowdstrike:
    output_formats: ["json"]
    primary_controls: ["SI-4", "IR-4", "SC-7"]
    description: "EDR — endpoint detection, threat intelligence, incident response"
    key_fields: ["detection_id", "severity", "tactic", "technique", "hostname", "filename"]

# NIST 800-53 control family quick reference
# Used by nist_mapper.py for validation
nist_control_families:
  AC: "Access Control"
  AT: "Awareness and Training"
  AU: "Audit and Accountability"
  CA: "Assessment, Authorization, and Monitoring"
  CM: "Configuration Management"
  CP: "Contingency Planning"
  IA: "Identification and Authentication"
  IR: "Incident Response"
  MA: "Maintenance"
  MP: "Media Protection"
  PE: "Physical and Environmental Protection"
  PL: "Planning"
  PM: "Program Management"
  PS: "Personnel Security"
  PT: "Personally Identifiable Information Processing and Transparency"
  RA: "Risk Assessment"
  SA: "System and Services Acquisition"
  SC: "System and Communications Protection"
  SI: "System and Information Integrity"
  SR: "Supply Chain Risk Management"
```

Write to `BERU-AI/config/scanner_mappings.yaml`.

- [ ] **Step 4: Create risk templates**

```yaml
# CISO-ready summary templates
# Used by risk_summary.py to structure output
# Three tiers: executive (board/CISO), technical (security team), compliance (auditor)

templates:
  executive:
    description: "For CISO, VP, board — business impact language, no technical jargon"
    sections:
      - name: "risk_headline"
        prompt: "One sentence: what happened and why it matters to the business"
      - name: "business_impact"
        prompt: "What data, systems, or operations are at risk. Use dollar terms or regulatory terms, not CVE numbers"
      - name: "current_status"
        prompt: "What has been done so far — containment, isolation, notification"
      - name: "recommended_action"
        prompt: "What decision the executive needs to make and by when"
      - name: "compliance_exposure"
        prompt: "Which regulatory frameworks are affected (FedRAMP, HIPAA, PCI-DSS) and what the gap means"

  technical:
    description: "For security engineers — full detail, commands, IOCs"
    sections:
      - name: "finding_summary"
        prompt: "Scanner, rule ID, severity, affected resource, detection timestamp"
      - name: "root_cause"
        prompt: "What misconfiguration or vulnerability was exploited and how"
      - name: "blast_radius"
        prompt: "All affected systems, lateral movement potential, data exposure"
      - name: "remediation_steps"
        prompt: "Exact commands, config changes, or policy updates needed"
      - name: "nist_mapping"
        prompt: "Mapped NIST 800-53 controls with justification"
      - name: "evidence"
        prompt: "Log entries, screenshots, scan output that proves the finding"

  compliance:
    description: "For auditors — control mapping, evidence, gap status"
    sections:
      - name: "control_mapping"
        prompt: "NIST 800-53 control ID, control name, implementation status"
      - name: "gap_description"
        prompt: "What the control requires vs what was found"
      - name: "evidence_artifacts"
        prompt: "List of evidence files, scan reports, log excerpts"
      - name: "poam_entry"
        prompt: "POA&M format: weakness, milestone, scheduled completion, resource estimate"
      - name: "risk_level"
        prompt: "Residual risk after remediation: High/Moderate/Low with justification"
```

Write to `BERU-AI/config/risk_templates.yaml`.

- [ ] **Step 5: Commit**

```bash
git add BERU-AI/config/
git commit -m "feat(beru-ai): add config files — system prompt, domain weights, scanner mappings, risk templates"
```

---

## Task 2: Data Schemas

JSON schemas that validate BERU training data and risk summary output. Tests in Task 3 will use these.

**Files:**
- Create: `7-data-schemas/beru_training_example.json`
- Create: `7-data-schemas/beru_risk_summary.json`

- [ ] **Step 1: Create BERU training example schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "BERU Training Example",
  "description": "ChatML format training example for BERU fine-tuning. Extends base training_example.json with CySA+/NIST scope validation.",
  "type": "object",
  "required": ["messages"],
  "additionalProperties": false,
  "properties": {
    "messages": {
      "type": "array",
      "minItems": 2,
      "items": {
        "type": "object",
        "required": ["role", "content"],
        "properties": {
          "role": {
            "type": "string",
            "enum": ["system", "user", "assistant"]
          },
          "content": {
            "type": "string",
            "minLength": 1
          }
        }
      },
      "contains": {
        "properties": {
          "role": { "const": "assistant" }
        }
      }
    },
    "_metadata": {
      "type": "object",
      "description": "Lineage metadata added by generate_utils.py, stripped before training",
      "properties": {
        "generator": { "type": "string" },
        "domain": { "type": "string" },
        "generated_at": { "type": "string", "format": "date-time" },
        "target_model": {
          "type": "string",
          "description": "Which model this example is tagged for (beru, jade, katie)"
        }
      }
    }
  },
  "examples": [
    {
      "messages": [
        { "role": "system", "content": "You are Beru, a CySA+ certified security analyst for GP-Copilot." },
        { "role": "user", "content": "GuardDuty finding: UnauthorizedAccess:EC2/MaliciousIPCaller.Custom, severity 8.0, instance i-0abc123 in production VPC with PII workloads. What's the triage?" },
        { "role": "assistant", "content": "**Priority: P1 — Immediate Response Required**\n\n**Blast Radius:** Instance i-0abc123 in production VPC. PII workloads mean potential data exfiltration. Check lateral movement to other instances in the same security group.\n\n**Immediate Action:**\n1. Isolate the instance: `aws ec2 modify-instance-attribute --instance-id i-0abc123 --groups sg-deny-all`\n2. Capture memory dump before termination for forensics\n3. Rotate all IAM credentials associated with the instance profile\n\n**NIST Mapping:**\n- SI-4 (System Monitoring) — GuardDuty detected the threat, control is working\n- IR-4 (Incident Handling) — response procedure activated\n- AC-6 (Least Privilege) — review instance role permissions for over-provisioning\n\n**CISO Summary:** A production instance communicated with a known malicious IP. This indicates potential compromise of systems handling customer PII. Instance has been isolated. IAM credential rotation and forensic review needed within 4 hours. Maps to NIST SI-4 and IR-4 — both required for our FedRAMP Moderate boundary." }
      ]
    }
  ]
}
```

Write to `7-data-schemas/beru_training_example.json`.

- [ ] **Step 2: Create BERU risk summary schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "BERU Risk Summary",
  "description": "Structured output format for CISO-ready risk summaries generated by BERU. Used by GP-API /api/beru/triage and /api/beru/summarize endpoints.",
  "type": "object",
  "required": ["finding_id", "triage", "ciso_summary", "evidence"],
  "properties": {
    "finding_id": {
      "type": "string",
      "description": "Unique identifier for the finding (scanner-date-sequence)"
    },
    "triage": {
      "type": "object",
      "required": ["priority", "severity_context", "blast_radius", "immediate_action", "remediation", "nist_controls", "confidence"],
      "properties": {
        "priority": {
          "type": "string",
          "enum": ["P1", "P2", "P3", "P4"],
          "description": "P1=critical/immediate, P2=high/24hr, P3=medium/week, P4=low/scheduled"
        },
        "severity_context": {
          "type": "string",
          "description": "Scanner severity + environmental context (e.g., 'HIGH in production VPC with PII workloads')"
        },
        "blast_radius": {
          "type": "string",
          "description": "Affected systems, data exposure, lateral movement potential"
        },
        "immediate_action": {
          "type": "string",
          "minLength": 10,
          "description": "Specific commands or config changes. Never 'investigate further' without details."
        },
        "remediation": {
          "type": "string",
          "description": "Full remediation steps beyond immediate containment"
        },
        "nist_controls": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[A-Z]{2}-[0-9]+$"
          },
          "minItems": 1,
          "description": "Mapped NIST 800-53 control IDs (e.g., SI-4, IR-4, AC-6)"
        },
        "confidence": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Model confidence in this triage decision"
        }
      }
    },
    "ciso_summary": {
      "type": "string",
      "minLength": 50,
      "description": "Executive-ready narrative — business impact language, no raw technical jargon"
    },
    "evidence": {
      "type": "object",
      "required": ["scanner", "finding_type", "timestamp"],
      "properties": {
        "scanner": {
          "type": "string",
          "description": "Scanner that produced the finding"
        },
        "finding_type": {
          "type": "string",
          "description": "Scanner-specific finding type or rule ID"
        },
        "timestamp": {
          "type": "string",
          "format": "date-time"
        },
        "raw_output": {
          "type": "string",
          "description": "Original scanner output for audit trail"
        }
      }
    },
    "rank": {
      "type": "string",
      "enum": ["E", "D", "C", "B", "S"],
      "description": "Automation rank assigned by BERU"
    }
  }
}
```

Write to `7-data-schemas/beru_risk_summary.json`.

- [ ] **Step 3: Commit**

```bash
git add 7-data-schemas/beru_training_example.json 7-data-schemas/beru_risk_summary.json
git commit -m "feat(beru-ai): add data schemas for training examples and risk summaries"
```

---

## Task 3: Schema Validation Tests

Tests that validate BERU training data and risk summaries against the schemas from Task 2. These run before any training.

**Files:**
- Create: `8-tests/test_beru_schemas.py`

- [ ] **Step 1: Write schema validation tests**

```python
"""
BERU-AI Schema Validation Tests
Validates training data and risk summary output against JSON schemas.
Run BEFORE training: python3 -m pytest 8-tests/test_beru_schemas.py -v
"""

import json
from pathlib import Path

import pytest

SCHEMA_DIR = Path(__file__).parent.parent / "7-data-schemas"


def load_schema(name: str) -> dict:
    schema_path = SCHEMA_DIR / name
    assert schema_path.exists(), f"Schema not found: {schema_path}"
    with open(schema_path) as f:
        return json.load(f)


class TestBeruTrainingSchema:
    """Validate BERU training example schema and examples."""

    def setup_method(self):
        self.schema = load_schema("beru_training_example.json")

    def test_schema_has_required_fields(self):
        assert self.schema["required"] == ["messages"]
        msg_items = self.schema["properties"]["messages"]["items"]
        assert "role" in msg_items["required"]
        assert "content" in msg_items["required"]

    def test_schema_enforces_chatml_roles(self):
        role_enum = self.schema["properties"]["messages"]["items"]["properties"]["role"]["enum"]
        assert set(role_enum) == {"system", "user", "assistant"}

    def test_schema_requires_assistant_response(self):
        contains = self.schema["properties"]["messages"]["contains"]
        assert contains["properties"]["role"]["const"] == "assistant"

    def test_schema_requires_min_two_messages(self):
        assert self.schema["properties"]["messages"]["minItems"] == 2

    def test_embedded_example_is_valid(self):
        """The example in the schema itself should be well-formed."""
        examples = self.schema.get("examples", [])
        assert len(examples) >= 1, "Schema must include at least one example"
        example = examples[0]
        messages = example["messages"]
        assert len(messages) >= 2
        roles = [m["role"] for m in messages]
        assert "assistant" in roles
        for msg in messages:
            assert len(msg["content"]) > 0

    def test_example_contains_nist_control(self):
        """BERU training examples should reference real NIST controls."""
        examples = self.schema.get("examples", [])
        assistant_msgs = [
            m["content"] for ex in examples
            for m in ex["messages"] if m["role"] == "assistant"
        ]
        combined = " ".join(assistant_msgs)
        # Must contain at least one real NIST control pattern (XX-N)
        import re
        nist_pattern = re.compile(r"\b[A-Z]{2}-\d+\b")
        matches = nist_pattern.findall(combined)
        assert len(matches) > 0, "BERU training examples must reference real NIST control IDs"

    def test_metadata_field_is_optional(self):
        assert "_metadata" not in self.schema["required"]


class TestBeruRiskSummarySchema:
    """Validate BERU risk summary output schema."""

    def setup_method(self):
        self.schema = load_schema("beru_risk_summary.json")

    def test_schema_has_required_fields(self):
        assert set(self.schema["required"]) == {
            "finding_id", "triage", "ciso_summary", "evidence"
        }

    def test_triage_has_required_fields(self):
        triage = self.schema["properties"]["triage"]
        assert set(triage["required"]) == {
            "priority", "severity_context", "blast_radius",
            "immediate_action", "remediation", "nist_controls", "confidence"
        }

    def test_priority_enum_is_p1_through_p4(self):
        priority = self.schema["properties"]["triage"]["properties"]["priority"]
        assert priority["enum"] == ["P1", "P2", "P3", "P4"]

    def test_nist_controls_pattern_validates_format(self):
        nist = self.schema["properties"]["triage"]["properties"]["nist_controls"]
        assert nist["items"]["pattern"] == "^[A-Z]{2}-[0-9]+$"
        assert nist["minItems"] == 1

    def test_confidence_is_bounded(self):
        conf = self.schema["properties"]["triage"]["properties"]["confidence"]
        assert conf["minimum"] == 0.0
        assert conf["maximum"] == 1.0

    def test_ciso_summary_has_min_length(self):
        summary = self.schema["properties"]["ciso_summary"]
        assert summary["minLength"] == 50

    def test_immediate_action_has_min_length(self):
        action = self.schema["properties"]["triage"]["properties"]["immediate_action"]
        assert action["minLength"] == 10

    def test_evidence_has_required_fields(self):
        evidence = self.schema["properties"]["evidence"]
        assert set(evidence["required"]) == {
            "scanner", "finding_type", "timestamp"
        }

    def test_rank_enum_matches_system(self):
        rank = self.schema["properties"]["rank"]
        assert rank["enum"] == ["E", "D", "C", "B", "S"]
```

Write to `8-tests/test_beru_schemas.py`.

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS && python3 -m pytest 8-tests/test_beru_schemas.py -v`

Expected: All tests PASS (they validate the schema files from Task 2).

- [ ] **Step 3: Commit**

```bash
git add 8-tests/test_beru_schemas.py
git commit -m "test(beru-ai): add schema validation tests for training data and risk summaries"
```

---

## Task 4: BERU-AI Providers (Ollama Integration)

Lean LLM provider — BERU's interface to Ollama for inference. Independent from JADE's providers.

**Files:**
- Create: `BERU-AI/providers/__init__.py`
- Create: `BERU-AI/providers/base.py`
- Create: `BERU-AI/providers/ollama.py`

- [ ] **Step 1: Create provider __init__**

```python
"""BERU-AI LLM Providers"""

from .ollama import OllamaProvider

__all__ = ["OllamaProvider"]
```

Write to `BERU-AI/providers/__init__.py`.

- [ ] **Step 2: Create base provider interface**

```python
"""
Base LLM Provider Interface for BERU-AI

Lean interface — only what BERU needs for inference.
No agentic engine, no chat handler, no intent router.
BERU is an analyst, not a platform operator.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseLLMProvider(ABC):
    """Base class for BERU LLM providers."""

    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        self.model_name = model_name
        self.config = config or {}

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Single-turn generation. Returns response text."""
        ...

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]],
             temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Multi-turn chat. Messages in ChatML format. Returns response text."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is reachable and model is loaded."""
        ...

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata (name, version, parameters)."""
        ...
```

Write to `BERU-AI/providers/base.py`.

- [ ] **Step 3: Create Ollama provider**

```python
"""
Ollama LLM Provider for BERU-AI

HTTP-based inference against local Ollama server.
Default model: beru:v1.0 (LLaMA 3.1-8B fine-tuned for CySA+/NIST).
Falls back to llama3.1:8b-instruct if fine-tuned model not available.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .base import BaseLLMProvider

# Load system prompt from config
_CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load_system_prompt() -> str:
    prompt_path = _CONFIG_DIR / "system_prompt.txt"
    if prompt_path.exists():
        return prompt_path.read_text().strip()
    return "You are Beru, a CySA+ certified security analyst."


class OllamaProvider(BaseLLMProvider):
    """
    Ollama-based LLM provider for BERU-AI.

    Uses HTTP API at localhost:11434. Supports model fallback
    and graceful degradation.
    """

    def __init__(
        self,
        model_name: str = "beru:v1.0",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(model_name, config)
        self.base_url = self.config.get("base_url", "http://localhost:11434").rstrip("/")
        self.fallback_model = self.config.get("fallback_model", "llama3.1:8b-instruct-q4_0")
        self.timeout = self.config.get("timeout", 120)
        self.system_prompt = _load_system_prompt()
        self.available = False
        self.using_fallback = False
        self._check_availability()

    def _check_availability(self) -> None:
        """Check if Ollama is running and model is loaded."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                if self.model_name in models:
                    self.available = True
                elif self.fallback_model and self.fallback_model in models:
                    self.available = True
                    self.using_fallback = True
        except requests.ConnectionError:
            self.available = False

    def _active_model(self) -> str:
        return self.fallback_model if self.using_fallback else self.model_name

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Single-turn generation via /api/generate."""
        payload = {
            "model": self._active_model(),
            "prompt": prompt,
            "system": system_prompt or self.system_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        resp = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")

    def chat(self, messages: List[Dict[str, str]],
             temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Multi-turn chat via /api/chat."""
        # Prepend system prompt if not already present
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": self.system_prompt}] + messages

        payload = {
            "model": self._active_model(),
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")

    def is_available(self) -> bool:
        self._check_availability()
        return self.available

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model": self._active_model(),
            "primary_model": self.model_name,
            "using_fallback": self.using_fallback,
            "base_url": self.base_url,
            "available": self.available,
        }
```

Write to `BERU-AI/providers/ollama.py`.

- [ ] **Step 4: Commit**

```bash
git add BERU-AI/providers/
git commit -m "feat(beru-ai): add Ollama LLM provider with fallback support"
```

---

## Task 5: BERU-AI Core Modules

The analyst brain — findings ingestion, tool output parsing, NIST mapping, triage engine, and risk summary generation.

**Files:**
- Create: `BERU-AI/core/__init__.py`
- Create: `BERU-AI/core/tool_output_parser.py`
- Create: `BERU-AI/core/findings_ingestion.py`
- Create: `BERU-AI/core/nist_mapper.py`
- Create: `BERU-AI/core/triage_engine.py`
- Create: `BERU-AI/core/risk_summary.py`

- [ ] **Step 1: Create core __init__**

```python
"""
BERU-AI Core — Security Analyst Engine

Modules:
- tool_output_parser: Scanner-specific format parsers
- findings_ingestion: Raw scanner output -> normalized findings
- nist_mapper: Finding -> NIST 800-53 control mapping
- triage_engine: Severity + context -> priority + action
- risk_summary: Findings batch -> CISO-ready output
"""

from .tool_output_parser import ToolOutputParser
from .findings_ingestion import FindingsIngestion
from .nist_mapper import NISTMapper
from .triage_engine import TriageEngine
from .risk_summary import RiskSummaryGenerator

__all__ = [
    "ToolOutputParser",
    "FindingsIngestion",
    "NISTMapper",
    "TriageEngine",
    "RiskSummaryGenerator",
]
```

Write to `BERU-AI/core/__init__.py`.

- [ ] **Step 2: Create tool output parser**

```python
"""
Scanner-Specific Output Format Parsers

Parses raw scanner output (CSV, JSON, SARIF, log) into a list of
normalized finding dicts. Each parser knows the key fields for its scanner.

Scanner mappings loaded from config/scanner_mappings.yaml.
"""

import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

_CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load_scanner_mappings() -> Dict[str, Any]:
    mappings_path = _CONFIG_DIR / "scanner_mappings.yaml"
    if mappings_path.exists():
        with open(mappings_path) as f:
            return yaml.safe_load(f)
    return {"scanners": {}}


class ToolOutputParser:
    """Parse raw scanner output into normalized finding dicts."""

    def __init__(self):
        config = _load_scanner_mappings()
        self.scanners = config.get("scanners", {})
        self.nist_families = config.get("nist_control_families", {})

    def parse(self, scanner: str, raw_output: str,
              format_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parse raw scanner output into normalized findings.

        Args:
            scanner: Scanner name (e.g., "nessus", "guardduty", "prowler")
            raw_output: Raw output string from the scanner
            format_hint: Optional format override ("json", "csv", "sarif")

        Returns:
            List of normalized finding dicts with keys:
            - scanner, severity, title, description, raw_fields, nist_controls_hint
        """
        scanner_lower = scanner.lower()
        scanner_config = self.scanners.get(scanner_lower, {})

        # Auto-detect format if not provided
        fmt = format_hint or self._detect_format(raw_output, scanner_config)

        if fmt == "json":
            return self._parse_json(scanner_lower, raw_output, scanner_config)
        elif fmt == "csv":
            return self._parse_csv(scanner_lower, raw_output, scanner_config)
        elif fmt == "jsonl":
            return self._parse_jsonl(scanner_lower, raw_output, scanner_config)
        else:
            # Return single finding with raw output for manual review
            return [{
                "scanner": scanner_lower,
                "severity": "UNKNOWN",
                "title": f"Unparsed {scanner} output",
                "description": raw_output[:500],
                "raw_fields": {},
                "nist_controls_hint": scanner_config.get("primary_controls", []),
                "parse_status": "unsupported_format",
            }]

    def _detect_format(self, raw: str, config: Dict) -> str:
        stripped = raw.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            return "json"
        if "\n{" in stripped and stripped.count("\n{") > 1:
            return "jsonl"
        if "," in stripped.split("\n")[0] and len(stripped.split("\n")) > 1:
            return "csv"
        return "unknown"

    def _parse_json(self, scanner: str, raw: str,
                    config: Dict) -> List[Dict[str, Any]]:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        findings = []
        for item in data:
            findings.append(self._normalize(scanner, item, config))
        return findings

    def _parse_jsonl(self, scanner: str, raw: str,
                     config: Dict) -> List[Dict[str, Any]]:
        findings = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if line:
                item = json.loads(line)
                findings.append(self._normalize(scanner, item, config))
        return findings

    def _parse_csv(self, scanner: str, raw: str,
                   config: Dict) -> List[Dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(raw))
        findings = []
        for row in reader:
            findings.append(self._normalize(scanner, dict(row), config))
        return findings

    def _normalize(self, scanner: str, raw_item: Dict,
                   config: Dict) -> Dict[str, Any]:
        """Normalize a single finding from raw scanner fields."""
        key_fields = config.get("key_fields", [])
        # Extract known fields
        raw_fields = {}
        for field in key_fields:
            # Handle nested fields (e.g., "resource.resourceType")
            val = raw_item
            for part in field.split("."):
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                    break
            if val is not None:
                raw_fields[field] = val

        # Map severity from scanner-specific field names
        severity = self._extract_severity(scanner, raw_item)
        title = self._extract_title(scanner, raw_item)

        return {
            "scanner": scanner,
            "severity": severity,
            "title": title,
            "description": raw_item.get("description", raw_item.get("Description", "")),
            "raw_fields": raw_fields,
            "nist_controls_hint": config.get("primary_controls", []),
            "parse_status": "ok",
        }

    def _extract_severity(self, scanner: str, item: Dict) -> str:
        """Extract and normalize severity across scanner formats."""
        severity_keys = ["severity", "Severity", "risk", "Risk", "rule.level"]
        for key in severity_keys:
            val = item
            for part in key.split("."):
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                    break
            if val is not None:
                return self._normalize_severity(val)
        return "UNKNOWN"

    def _extract_title(self, scanner: str, item: Dict) -> str:
        title_keys = ["title", "Title", "Name", "name",
                      "alert.signature", "rule.description", "check_id"]
        for key in title_keys:
            val = item
            for part in key.split("."):
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                    break
            if val is not None:
                return str(val)
        return "Unknown finding"

    def _normalize_severity(self, val: Any) -> str:
        """Normalize severity to CRITICAL/HIGH/MEDIUM/LOW/INFO."""
        if isinstance(val, (int, float)):
            if val >= 9.0:
                return "CRITICAL"
            if val >= 7.0:
                return "HIGH"
            if val >= 4.0:
                return "MEDIUM"
            if val >= 1.0:
                return "LOW"
            return "INFO"
        s = str(val).upper().strip()
        valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
        if s in valid:
            return s
        # Common scanner mappings
        mapping = {"SEVERE": "CRITICAL", "IMPORTANT": "HIGH", "MODERATE": "MEDIUM",
                   "WARNING": "MEDIUM", "INFORMATIONAL": "INFO", "NONE": "INFO"}
        return mapping.get(s, "UNKNOWN")

    def supported_scanners(self) -> List[str]:
        return list(self.scanners.keys())
```

Write to `BERU-AI/core/tool_output_parser.py`.

- [ ] **Step 3: Create findings ingestion**

```python
"""
Findings Ingestion — Raw Scanner Output to Normalized Findings

Entry point for all scanner data entering BERU's pipeline.
Reads files from 0-data-lab/seclab-findings/, parses them via
ToolOutputParser, and produces normalized finding records.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .tool_output_parser import ToolOutputParser


class FindingsIngestion:
    """Ingest raw scanner output into normalized findings."""

    def __init__(self):
        self.parser = ToolOutputParser()

    def ingest_file(self, file_path: Path,
                    scanner: Optional[str] = None,
                    format_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Ingest a single scanner output file.

        Args:
            file_path: Path to raw scanner output
            scanner: Scanner name (auto-detected from filename if not provided)
            format_hint: Format override

        Returns:
            List of normalized finding dicts
        """
        raw = file_path.read_text()
        scanner = scanner or self._detect_scanner(file_path)
        findings = self.parser.parse(scanner, raw, format_hint)

        # Enrich with ingestion metadata
        for finding in findings:
            finding["finding_id"] = f"{scanner}-{datetime.utcnow().strftime('%Y%m%d')}-{uuid4().hex[:8]}"
            finding["source_file"] = str(file_path)
            finding["ingested_at"] = datetime.utcnow().isoformat() + "Z"

        return findings

    def ingest_directory(self, dir_path: Path,
                         scanner: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Ingest all scanner output files in a directory.

        Args:
            dir_path: Path to directory containing scanner output files
            scanner: Scanner name (auto-detected per file if not provided)

        Returns:
            Aggregated list of all normalized findings
        """
        all_findings = []
        supported_extensions = {".json", ".jsonl", ".csv", ".xml", ".log", ".txt"}
        for f in sorted(dir_path.iterdir()):
            if f.is_file() and f.suffix in supported_extensions:
                findings = self.ingest_file(f, scanner=scanner)
                all_findings.extend(findings)
        return all_findings

    def _detect_scanner(self, file_path: Path) -> str:
        """Detect scanner from filename patterns."""
        name = file_path.stem.lower()
        known = self.parser.supported_scanners()
        for scanner in known:
            if scanner in name:
                return scanner
        # Check file content for hints
        return "unknown"
```

Write to `BERU-AI/core/findings_ingestion.py`.

- [ ] **Step 4: Create NIST mapper**

```python
"""
NIST 800-53 Control Mapper

Maps security findings to NIST 800-53 control families.
Uses scanner_mappings.yaml for initial hints, then refines
based on finding content.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

_CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load_scanner_mappings() -> Dict[str, Any]:
    mappings_path = _CONFIG_DIR / "scanner_mappings.yaml"
    if mappings_path.exists():
        with open(mappings_path) as f:
            return yaml.safe_load(f)
    return {"scanners": {}, "nist_control_families": {}}


# Keyword -> control mapping for content-based refinement
_KEYWORD_CONTROLS = {
    "access control": ["AC-2", "AC-3", "AC-6"],
    "authentication": ["IA-2", "IA-5"],
    "mfa": ["IA-2"],
    "multi-factor": ["IA-2"],
    "audit": ["AU-2", "AU-6", "AU-12"],
    "logging": ["AU-2", "AU-3", "AU-12"],
    "cloudtrail": ["AU-2", "AU-12"],
    "encryption": ["SC-8", "SC-13", "SC-28"],
    "tls": ["SC-8"],
    "ssl": ["SC-8"],
    "kms": ["SC-12", "SC-28"],
    "at rest": ["SC-28"],
    "in transit": ["SC-8"],
    "firewall": ["SC-7"],
    "security group": ["SC-7"],
    "network acl": ["SC-7"],
    "vpc": ["SC-7"],
    "patch": ["SI-2"],
    "update": ["SI-2"],
    "vulnerability": ["RA-5", "SI-2"],
    "cve": ["RA-5", "SI-2"],
    "malware": ["SI-3"],
    "antivirus": ["SI-3"],
    "monitoring": ["SI-4"],
    "ids": ["SI-4"],
    "ips": ["SI-4"],
    "intrusion": ["SI-4"],
    "guardduty": ["SI-4"],
    "incident": ["IR-4", "IR-5", "IR-6"],
    "containment": ["IR-4"],
    "backup": ["CP-9"],
    "recovery": ["CP-10"],
    "configuration": ["CM-6", "CM-7"],
    "baseline": ["CM-2", "CM-6"],
    "hardening": ["CM-6", "CM-7"],
    "least privilege": ["AC-6"],
    "iam": ["AC-2", "AC-6"],
    "role": ["AC-2", "AC-6"],
    "rbac": ["AC-3", "AC-6"],
    "secret": ["IA-5", "SC-28"],
    "credential": ["IA-5"],
    "session": ["AC-12", "SC-23"],
    "integrity": ["SI-7"],
    "file integrity": ["SI-7"],
    "supply chain": ["SR-3", "SR-4"],
    "dependency": ["SR-3"],
}


class NISTMapper:
    """Map security findings to NIST 800-53 controls."""

    def __init__(self):
        config = _load_scanner_mappings()
        self.scanners = config.get("scanners", {})
        self.control_families = config.get("nist_control_families", {})

    def map_finding(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map a normalized finding to NIST 800-53 controls.

        Args:
            finding: Normalized finding dict from FindingsIngestion

        Returns:
            Dict with:
            - controls: List of control IDs (e.g., ["SI-4", "IR-4"])
            - primary_control: Most relevant control
            - control_families: Mapped family names
            - reasoning: Why these controls were selected
        """
        controls = set()

        # Start with scanner-level hints
        scanner = finding.get("scanner", "")
        scanner_config = self.scanners.get(scanner, {})
        hint_controls = scanner_config.get("primary_controls", [])
        controls.update(hint_controls)

        # Refine with content-based keyword matching
        searchable = " ".join([
            finding.get("title", ""),
            finding.get("description", ""),
            str(finding.get("raw_fields", {})),
        ]).lower()

        matched_keywords = []
        for keyword, keyword_controls in _KEYWORD_CONTROLS.items():
            if keyword in searchable:
                controls.update(keyword_controls)
                matched_keywords.append(keyword)

        controls_list = sorted(controls)
        primary = controls_list[0] if controls_list else "CM-6"

        # Build reasoning
        reasons = []
        if hint_controls:
            reasons.append(f"Scanner '{scanner}' maps to {hint_controls}")
        if matched_keywords:
            reasons.append(f"Content keywords matched: {matched_keywords[:5]}")

        # Map to family names
        families = {}
        for ctrl in controls_list:
            family_code = re.match(r"^([A-Z]{2})", ctrl)
            if family_code:
                code = family_code.group(1)
                families[ctrl] = self.control_families.get(code, "Unknown")

        return {
            "controls": controls_list,
            "primary_control": primary,
            "control_families": families,
            "reasoning": "; ".join(reasons) if reasons else "Default configuration management control",
        }

    def validate_control_id(self, control_id: str) -> bool:
        """Check if a control ID matches the NIST 800-53 format."""
        match = re.match(r"^([A-Z]{2})-\d+$", control_id)
        if not match:
            return False
        family = match.group(1)
        return family in self.control_families
```

Write to `BERU-AI/core/nist_mapper.py`.

- [ ] **Step 5: Create triage engine**

```python
"""
Triage Engine — Severity + Context -> Priority + Action

Takes normalized findings and produces triage decisions:
priority (P1-P4), immediate action, remediation, NIST mapping.
"""

from typing import Any, Dict, List, Optional

from .nist_mapper import NISTMapper


# Severity + context -> priority mapping
_SEVERITY_TO_BASE_PRIORITY = {
    "CRITICAL": "P1",
    "HIGH": "P2",
    "MEDIUM": "P3",
    "LOW": "P4",
    "INFO": "P4",
    "UNKNOWN": "P3",
}

# Context keywords that escalate priority
_ESCALATION_KEYWORDS = [
    "production", "prod", "pii", "phi", "pci", "customer data",
    "database", "rds", "secrets", "credentials", "public",
    "internet-facing", "external", "0.0.0.0",
]


class TriageEngine:
    """Produce triage decisions from normalized findings."""

    def __init__(self):
        self.nist_mapper = NISTMapper()

    def triage(self, finding: Dict[str, Any],
               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Triage a single finding.

        Args:
            finding: Normalized finding from FindingsIngestion
            context: Optional environment context (e.g., {"environment": "production", "data_classification": "PII"})

        Returns:
            Triage decision dict matching beru_risk_summary.json schema
        """
        context = context or {}
        severity = finding.get("severity", "UNKNOWN")

        # Base priority from severity
        priority = _SEVERITY_TO_BASE_PRIORITY.get(severity, "P3")

        # Escalate based on context
        priority = self._apply_escalation(priority, finding, context)

        # NIST mapping
        nist_result = self.nist_mapper.map_finding(finding)

        # Build severity context string
        env = context.get("environment", "unknown")
        data_class = context.get("data_classification", "")
        severity_context = f"{severity} in {env} environment"
        if data_class:
            severity_context += f" with {data_class} workloads"

        return {
            "finding_id": finding.get("finding_id", "unknown"),
            "triage": {
                "priority": priority,
                "severity_context": severity_context,
                "blast_radius": self._assess_blast_radius(finding, context),
                "immediate_action": self._recommend_action(finding, priority),
                "remediation": self._recommend_remediation(finding),
                "nist_controls": nist_result["controls"][:5],
                "confidence": self._calculate_confidence(finding),
            },
            "ciso_summary": "",  # Populated by RiskSummaryGenerator or LLM
            "evidence": {
                "scanner": finding.get("scanner", "unknown"),
                "finding_type": finding.get("title", ""),
                "timestamp": finding.get("ingested_at", ""),
            },
        }

    def triage_batch(self, findings: List[Dict[str, Any]],
                     context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Triage a batch of findings. Returns sorted by priority (P1 first)."""
        results = [self.triage(f, context) for f in findings]
        priority_order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
        results.sort(key=lambda r: priority_order.get(r["triage"]["priority"], 4))
        return results

    def _apply_escalation(self, base_priority: str,
                          finding: Dict, context: Dict) -> str:
        """Escalate priority if context warrants it."""
        searchable = " ".join([
            finding.get("title", ""),
            finding.get("description", ""),
            context.get("environment", ""),
            context.get("data_classification", ""),
        ]).lower()

        escalate = any(kw in searchable for kw in _ESCALATION_KEYWORDS)
        if escalate and base_priority in ("P2", "P3"):
            priorities = ["P1", "P2", "P3", "P4"]
            idx = priorities.index(base_priority)
            return priorities[max(0, idx - 1)]
        return base_priority

    def _assess_blast_radius(self, finding: Dict, context: Dict) -> str:
        """Assess blast radius from finding and context."""
        parts = []
        raw = finding.get("raw_fields", {})

        # Check for resource identifiers
        for key in ["Host", "instanceId", "ResourceId", "hostname", "agent.name"]:
            if key in raw:
                parts.append(f"Affected resource: {raw[key]}")

        if context.get("environment") == "production":
            parts.append("Production environment — elevated risk")
        if context.get("data_classification"):
            parts.append(f"Data classification: {context['data_classification']}")

        return "; ".join(parts) if parts else "Blast radius requires manual assessment"

    def _recommend_action(self, finding: Dict, priority: str) -> str:
        """Recommend immediate action based on finding type."""
        title = finding.get("title", "").lower()
        scanner = finding.get("scanner", "")

        if priority == "P1":
            if "malicious" in title or "unauthorized" in title:
                return "Isolate affected resource immediately. Capture forensic snapshot before remediation. Rotate all associated credentials."
            return "Escalate to incident response team. Begin containment per IR playbook."

        if "vulnerability" in title or "cve" in title.lower():
            return "Schedule patch application within SLA window. Verify compensating controls are in place."

        if "misconfiguration" in title or "config" in title:
            return "Review current configuration against CIS benchmark. Apply hardened baseline."

        return f"Review {scanner} finding details and determine remediation path."

    def _recommend_remediation(self, finding: Dict) -> str:
        """Build remediation recommendation."""
        desc = finding.get("description", "")
        if desc:
            return f"Full remediation: {desc[:200]}"
        return "Review scanner documentation for remediation guidance."

    def _calculate_confidence(self, finding: Dict) -> float:
        """Calculate confidence score for this triage decision."""
        score = 0.5  # Base confidence

        # Higher confidence if we parsed successfully
        if finding.get("parse_status") == "ok":
            score += 0.15

        # Higher confidence if severity is known
        if finding.get("severity") != "UNKNOWN":
            score += 0.15

        # Higher confidence if we have NIST control hints
        if finding.get("nist_controls_hint"):
            score += 0.1

        # Higher confidence for known scanners
        if finding.get("scanner") != "unknown":
            score += 0.1

        return min(score, 0.95)
```

Write to `BERU-AI/core/triage_engine.py`.

- [ ] **Step 6: Create risk summary generator**

```python
"""
Risk Summary Generator — CISO-Ready Output

Generates structured JSON + narrative summaries from triaged findings.
Three tiers: executive, technical, compliance (per risk_templates.yaml).

When an LLM provider is available, BERU generates natural language summaries.
Without an LLM, produces template-based summaries from structured data.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

_CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load_risk_templates() -> Dict[str, Any]:
    path = _CONFIG_DIR / "risk_templates.yaml"
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f)
    return {"templates": {}}


class RiskSummaryGenerator:
    """Generate CISO-ready risk summaries from triaged findings."""

    def __init__(self, llm_provider=None):
        """
        Args:
            llm_provider: Optional BERU OllamaProvider for LLM-enhanced summaries.
                          Works without it (template-based fallback).
        """
        self.templates = _load_risk_templates().get("templates", {})
        self.llm = llm_provider

    def summarize_finding(self, triage_result: Dict[str, Any],
                          tier: str = "executive") -> Dict[str, Any]:
        """
        Generate a risk summary for a single triaged finding.

        Args:
            triage_result: Output from TriageEngine.triage()
            tier: Summary tier — "executive", "technical", or "compliance"

        Returns:
            triage_result enriched with ciso_summary field
        """
        if self.llm and self.llm.is_available():
            summary = self._llm_summary(triage_result, tier)
        else:
            summary = self._template_summary(triage_result, tier)

        triage_result["ciso_summary"] = summary
        return triage_result

    def summarize_batch(self, triage_results: List[Dict[str, Any]],
                        tier: str = "executive") -> Dict[str, Any]:
        """
        Generate a risk summary for a batch of triaged findings.

        Args:
            triage_results: List of outputs from TriageEngine.triage_batch()
            tier: Summary tier

        Returns:
            Batch summary dict with aggregate stats and narrative
        """
        p1_count = sum(1 for r in triage_results if r["triage"]["priority"] == "P1")
        p2_count = sum(1 for r in triage_results if r["triage"]["priority"] == "P2")
        p3_count = sum(1 for r in triage_results if r["triage"]["priority"] == "P3")
        p4_count = sum(1 for r in triage_results if r["triage"]["priority"] == "P4")

        # Collect all NIST controls
        all_controls = set()
        for r in triage_results:
            all_controls.update(r["triage"].get("nist_controls", []))

        # Collect scanners
        scanners = set(r["evidence"]["scanner"] for r in triage_results)

        batch_summary = {
            "total_findings": len(triage_results),
            "by_priority": {"P1": p1_count, "P2": p2_count, "P3": p3_count, "P4": p4_count},
            "scanners": sorted(scanners),
            "nist_controls_affected": sorted(all_controls),
            "findings": triage_results,
        }

        if self.llm and self.llm.is_available():
            batch_summary["narrative"] = self._llm_batch_summary(batch_summary, tier)
        else:
            batch_summary["narrative"] = self._template_batch_summary(batch_summary, tier)

        return batch_summary

    def _llm_summary(self, triage_result: Dict, tier: str) -> str:
        """Generate LLM-enhanced summary for a single finding."""
        template = self.templates.get(tier, {})
        sections = template.get("sections", [])
        section_prompts = "\n".join(
            f"- {s['name']}: {s['prompt']}" for s in sections
        )

        prompt = (
            f"Generate a {tier} risk summary for this security finding.\n\n"
            f"Finding: {triage_result['evidence']['finding_type']}\n"
            f"Scanner: {triage_result['evidence']['scanner']}\n"
            f"Priority: {triage_result['triage']['priority']}\n"
            f"Severity Context: {triage_result['triage']['severity_context']}\n"
            f"Blast Radius: {triage_result['triage']['blast_radius']}\n"
            f"NIST Controls: {triage_result['triage']['nist_controls']}\n"
            f"Immediate Action: {triage_result['triage']['immediate_action']}\n\n"
            f"Required sections:\n{section_prompts}\n\n"
            f"Write as a single coherent paragraph. No bullet points. "
            f"Business impact language for executives."
        )
        return self.llm.generate(prompt)

    def _template_summary(self, triage_result: Dict, tier: str) -> str:
        """Template-based summary fallback when no LLM is available."""
        t = triage_result["triage"]
        e = triage_result["evidence"]
        controls = ", ".join(t["nist_controls"][:3])

        if tier == "executive":
            return (
                f"{e['finding_type']} detected by {e['scanner']}. "
                f"Priority: {t['priority']}. {t['severity_context']}. "
                f"{t['blast_radius']}. "
                f"Immediate action: {t['immediate_action']} "
                f"Maps to NIST controls: {controls}."
            )
        elif tier == "technical":
            return (
                f"Scanner: {e['scanner']} | Finding: {e['finding_type']} | "
                f"Priority: {t['priority']} | Severity: {t['severity_context']}\n"
                f"Blast Radius: {t['blast_radius']}\n"
                f"Action: {t['immediate_action']}\n"
                f"Remediation: {t['remediation']}\n"
                f"NIST: {controls}"
            )
        else:  # compliance
            return (
                f"Finding: {e['finding_type']}\n"
                f"NIST 800-53 Controls: {controls}\n"
                f"Gap: {t['severity_context']}\n"
                f"Remediation: {t['remediation']}\n"
                f"Evidence: {e['scanner']} scan at {e.get('timestamp', 'N/A')}"
            )

    def _llm_batch_summary(self, batch: Dict, tier: str) -> str:
        """Generate LLM-enhanced batch summary."""
        prompt = (
            f"Generate a {tier} risk summary for a batch of {batch['total_findings']} security findings.\n\n"
            f"Priority breakdown: {batch['by_priority']}\n"
            f"Scanners: {batch['scanners']}\n"
            f"NIST controls affected: {batch['nist_controls_affected']}\n\n"
            f"Top P1 findings:\n"
        )
        for f in batch["findings"][:5]:
            if f["triage"]["priority"] == "P1":
                prompt += f"- {f['evidence']['finding_type']} ({f['triage']['severity_context']})\n"

        prompt += (
            f"\nWrite a concise executive summary (3-5 sentences). "
            f"Lead with the most critical risk. Include remediation timeline recommendation."
        )
        return self.llm.generate(prompt)

    def _template_batch_summary(self, batch: Dict, tier: str) -> str:
        """Template-based batch summary fallback."""
        bp = batch["by_priority"]
        controls = ", ".join(batch["nist_controls_affected"][:5])
        return (
            f"Scan cycle produced {batch['total_findings']} findings across "
            f"{', '.join(batch['scanners'])}. "
            f"Priority breakdown: {bp['P1']} critical, {bp['P2']} high, "
            f"{bp['P3']} medium, {bp['P4']} low. "
            f"NIST controls affected: {controls}. "
            f"{'Immediate action required for P1 findings.' if bp['P1'] > 0 else 'No critical findings requiring immediate action.'}"
        )
```

Write to `BERU-AI/core/risk_summary.py`.

- [ ] **Step 7: Commit**

```bash
git add BERU-AI/core/
git commit -m "feat(beru-ai): add core modules — parser, ingestion, NIST mapper, triage, risk summary"
```

---

## Task 6: Core Module Unit Tests

Tests for the core modules from Task 5. These test without Ollama running (template-based fallback).

**Files:**
- Create: `8-tests/test_beru_core.py`

- [ ] **Step 1: Write core module tests**

```python
"""
BERU-AI Core Module Tests
Tests findings ingestion, tool output parsing, NIST mapping,
triage engine, and risk summary generation.
Runs WITHOUT Ollama — tests template-based fallback paths.
"""

import json
from pathlib import Path

import pytest

import sys
BERU_PATH = Path(__file__).parent.parent / "BERU-AI"
sys.path.insert(0, str(BERU_PATH))

from core.tool_output_parser import ToolOutputParser
from core.findings_ingestion import FindingsIngestion
from core.nist_mapper import NISTMapper
from core.triage_engine import TriageEngine
from core.risk_summary import RiskSummaryGenerator


# ============================================================
# ToolOutputParser Tests
# ============================================================

class TestToolOutputParser:

    def setup_method(self):
        self.parser = ToolOutputParser()

    def test_supported_scanners_includes_known(self):
        scanners = self.parser.supported_scanners()
        assert "guardduty" in scanners
        assert "nessus" in scanners
        assert "prowler" in scanners
        assert "wazuh" in scanners

    def test_parse_json_guardduty(self):
        raw = json.dumps({
            "type": "UnauthorizedAccess:EC2/MaliciousIPCaller.Custom",
            "severity": 8.0,
            "title": "EC2 instance communicating with malicious IP",
            "description": "Instance i-0abc123 is communicating with a known malicious IP.",
            "resource": {"resourceType": "Instance"},
        })
        findings = self.parser.parse("guardduty", raw)
        assert len(findings) == 1
        assert findings[0]["scanner"] == "guardduty"
        assert findings[0]["severity"] == "HIGH"
        assert findings[0]["parse_status"] == "ok"

    def test_parse_csv_nessus(self):
        raw = (
            "Plugin ID,CVE,CVSS,Risk,Host,Name\n"
            "19506,CVE-2024-1234,9.8,Critical,10.0.0.1,Remote Code Execution\n"
            "11219,,2.1,Low,10.0.0.1,SSH Weak Algorithms\n"
        )
        findings = self.parser.parse("nessus", raw, format_hint="csv")
        assert len(findings) == 2
        assert findings[0]["severity"] == "CRITICAL"
        assert findings[1]["severity"] == "LOW"

    def test_parse_jsonl_nuclei(self):
        raw = (
            '{"template-id": "cve-2024-1234", "severity": "critical", "host": "example.com"}\n'
            '{"template-id": "cve-2024-5678", "severity": "medium", "host": "example.com"}\n'
        )
        findings = self.parser.parse("nuclei", raw, format_hint="jsonl")
        assert len(findings) == 2
        assert findings[0]["severity"] == "CRITICAL"

    def test_unsupported_format_returns_unparsed(self):
        findings = self.parser.parse("unknown_scanner", "some raw data")
        assert len(findings) == 1
        assert findings[0]["parse_status"] == "unsupported_format"

    def test_severity_normalization_numeric(self):
        assert self.parser._normalize_severity(9.5) == "CRITICAL"
        assert self.parser._normalize_severity(7.0) == "HIGH"
        assert self.parser._normalize_severity(4.0) == "MEDIUM"
        assert self.parser._normalize_severity(1.0) == "LOW"
        assert self.parser._normalize_severity(0.0) == "INFO"

    def test_severity_normalization_string(self):
        assert self.parser._normalize_severity("Critical") == "CRITICAL"
        assert self.parser._normalize_severity("IMPORTANT") == "HIGH"
        assert self.parser._normalize_severity("Moderate") == "MEDIUM"
        assert self.parser._normalize_severity("informational") == "INFO"


# ============================================================
# FindingsIngestion Tests
# ============================================================

class TestFindingsIngestion:

    def setup_method(self):
        self.ingestion = FindingsIngestion()

    def test_ingest_file_adds_metadata(self, tmp_path):
        test_file = tmp_path / "guardduty_test.json"
        test_file.write_text(json.dumps({
            "type": "Recon:EC2/PortProbeUnprotectedPort",
            "severity": 5.0,
            "title": "Port probe on unprotected port",
        }))
        findings = self.ingestion.ingest_file(test_file, scanner="guardduty")
        assert len(findings) == 1
        assert "finding_id" in findings[0]
        assert findings[0]["finding_id"].startswith("guardduty-")
        assert "ingested_at" in findings[0]
        assert "source_file" in findings[0]

    def test_ingest_directory(self, tmp_path):
        for i in range(3):
            f = tmp_path / f"prowler_{i}.json"
            f.write_text(json.dumps({
                "CheckID": f"check-{i}",
                "Status": "FAIL",
                "Severity": "high",
                "title": f"Finding {i}",
            }))
        findings = self.ingestion.ingest_directory(tmp_path, scanner="prowler")
        assert len(findings) == 3

    def test_detect_scanner_from_filename(self):
        path = Path("/tmp/nessus_scan_2026.csv")
        assert self.ingestion._detect_scanner(path) == "nessus"


# ============================================================
# NISTMapper Tests
# ============================================================

class TestNISTMapper:

    def setup_method(self):
        self.mapper = NISTMapper()

    def test_maps_guardduty_finding(self):
        finding = {
            "scanner": "guardduty",
            "title": "Unauthorized access detected",
            "description": "Malicious IP communication",
            "raw_fields": {},
        }
        result = self.mapper.map_finding(finding)
        assert "SI-4" in result["controls"]
        assert len(result["controls"]) > 0
        assert result["primary_control"] is not None

    def test_keyword_matching_encryption(self):
        finding = {
            "scanner": "prowler",
            "title": "S3 bucket without encryption at rest",
            "description": "KMS encryption not enabled",
            "raw_fields": {},
        }
        result = self.mapper.map_finding(finding)
        assert "SC-28" in result["controls"]

    def test_validate_control_id_valid(self):
        assert self.mapper.validate_control_id("SI-4") is True
        assert self.mapper.validate_control_id("AC-2") is True
        assert self.mapper.validate_control_id("IR-4") is True

    def test_validate_control_id_invalid(self):
        assert self.mapper.validate_control_id("XX-99") is False
        assert self.mapper.validate_control_id("not-a-control") is False
        assert self.mapper.validate_control_id("") is False


# ============================================================
# TriageEngine Tests
# ============================================================

class TestTriageEngine:

    def setup_method(self):
        self.engine = TriageEngine()

    def test_critical_severity_gets_p1(self):
        finding = {
            "severity": "CRITICAL",
            "scanner": "nessus",
            "title": "Remote Code Execution",
            "description": "Critical RCE vulnerability",
            "raw_fields": {},
            "finding_id": "test-001",
            "nist_controls_hint": ["SI-2"],
            "parse_status": "ok",
            "ingested_at": "2026-04-09T00:00:00Z",
        }
        result = self.engine.triage(finding)
        assert result["triage"]["priority"] == "P1"
        assert result["finding_id"] == "test-001"

    def test_high_in_production_escalates(self):
        finding = {
            "severity": "HIGH",
            "scanner": "guardduty",
            "title": "Unauthorized access",
            "description": "Malicious IP in production",
            "raw_fields": {},
            "finding_id": "test-002",
            "nist_controls_hint": ["SI-4"],
            "parse_status": "ok",
            "ingested_at": "2026-04-09T00:00:00Z",
        }
        context = {"environment": "production", "data_classification": "PII"}
        result = self.engine.triage(finding, context)
        assert result["triage"]["priority"] == "P1"

    def test_low_severity_gets_p4(self):
        finding = {
            "severity": "LOW",
            "scanner": "lynis",
            "title": "Informational finding",
            "description": "Minor configuration note",
            "raw_fields": {},
            "finding_id": "test-003",
            "nist_controls_hint": [],
            "parse_status": "ok",
            "ingested_at": "2026-04-09T00:00:00Z",
        }
        result = self.engine.triage(finding)
        assert result["triage"]["priority"] == "P4"

    def test_triage_batch_sorts_by_priority(self):
        findings = [
            {"severity": "LOW", "scanner": "a", "title": "low", "description": "",
             "raw_fields": {}, "finding_id": "f1", "nist_controls_hint": [],
             "parse_status": "ok", "ingested_at": ""},
            {"severity": "CRITICAL", "scanner": "b", "title": "crit", "description": "",
             "raw_fields": {}, "finding_id": "f2", "nist_controls_hint": [],
             "parse_status": "ok", "ingested_at": ""},
        ]
        results = self.engine.triage_batch(findings)
        assert results[0]["triage"]["priority"] == "P1"
        assert results[1]["triage"]["priority"] == "P4"

    def test_triage_includes_nist_controls(self):
        finding = {
            "severity": "HIGH",
            "scanner": "guardduty",
            "title": "Monitoring alert",
            "description": "Intrusion detection triggered",
            "raw_fields": {},
            "finding_id": "test-004",
            "nist_controls_hint": ["SI-4"],
            "parse_status": "ok",
            "ingested_at": "2026-04-09T00:00:00Z",
        }
        result = self.engine.triage(finding)
        assert len(result["triage"]["nist_controls"]) > 0

    def test_confidence_is_bounded(self):
        finding = {
            "severity": "HIGH", "scanner": "nessus", "title": "test",
            "description": "", "raw_fields": {}, "finding_id": "test",
            "nist_controls_hint": ["SI-2"], "parse_status": "ok",
            "ingested_at": "",
        }
        result = self.engine.triage(finding)
        assert 0.0 <= result["triage"]["confidence"] <= 1.0


# ============================================================
# RiskSummaryGenerator Tests
# ============================================================

class TestRiskSummaryGenerator:

    def setup_method(self):
        # No LLM — template-based fallback
        self.generator = RiskSummaryGenerator(llm_provider=None)

    def test_template_summary_executive(self):
        triage_result = {
            "finding_id": "test-001",
            "triage": {
                "priority": "P1",
                "severity_context": "CRITICAL in production",
                "blast_radius": "3 instances affected",
                "immediate_action": "Isolate affected instance",
                "remediation": "Patch and rotate credentials",
                "nist_controls": ["SI-4", "IR-4"],
                "confidence": 0.85,
            },
            "ciso_summary": "",
            "evidence": {
                "scanner": "guardduty",
                "finding_type": "UnauthorizedAccess",
                "timestamp": "2026-04-09T00:00:00Z",
            },
        }
        result = self.generator.summarize_finding(triage_result, tier="executive")
        assert len(result["ciso_summary"]) > 0
        assert "guardduty" in result["ciso_summary"]

    def test_template_summary_technical(self):
        triage_result = {
            "finding_id": "test-002",
            "triage": {
                "priority": "P2",
                "severity_context": "HIGH in staging",
                "blast_radius": "1 instance",
                "immediate_action": "Review configuration",
                "remediation": "Apply CIS benchmark",
                "nist_controls": ["CM-6"],
                "confidence": 0.7,
            },
            "ciso_summary": "",
            "evidence": {
                "scanner": "prowler",
                "finding_type": "S3 misconfiguration",
                "timestamp": "2026-04-09T00:00:00Z",
            },
        }
        result = self.generator.summarize_finding(triage_result, tier="technical")
        assert "Remediation:" in result["ciso_summary"]

    def test_batch_summary_counts_priorities(self):
        triage_results = [
            {"triage": {"priority": "P1", "nist_controls": ["SI-4"]},
             "evidence": {"scanner": "guardduty", "finding_type": "a", "timestamp": ""}},
            {"triage": {"priority": "P2", "nist_controls": ["CM-6"]},
             "evidence": {"scanner": "prowler", "finding_type": "b", "timestamp": ""}},
            {"triage": {"priority": "P2", "nist_controls": ["AC-6"]},
             "evidence": {"scanner": "prowler", "finding_type": "c", "timestamp": ""}},
        ]
        result = self.generator.summarize_batch(triage_results)
        assert result["total_findings"] == 3
        assert result["by_priority"]["P1"] == 1
        assert result["by_priority"]["P2"] == 2
        assert len(result["narrative"]) > 0
```

Write to `8-tests/test_beru_core.py`.

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS && python3 -m pytest 8-tests/test_beru_core.py -v`

Expected: All tests PASS. Tests use template-based fallback (no Ollama required).

- [ ] **Step 3: Commit**

```bash
git add 8-tests/test_beru_core.py
git commit -m "test(beru-ai): add unit tests for core modules — parser, ingestion, NIST mapper, triage, risk summary"
```

---

## Task 7: Modelfile and Package Files

Ollama registration, requirements, README, and the seclab-findings classifier.

**Files:**
- Create: `BERU-AI/Modelfile_beru8b`
- Create: `BERU-AI/requirements.txt`
- Create: `BERU-AI/README.md`
- Create: `0-data-lab/tools/classify_seclab_findings.py`

- [ ] **Step 1: Create Modelfile**

```
FROM ./beru-llama8b-v1.0.gguf

TEMPLATE """<|start_header_id|>system<|end_header_id|>

{{ .System }}<|eot_id|><|start_header_id|>user<|end_header_id|>

{{ .Prompt }}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

PARAMETER stop "<|start_header_id|>"
PARAMETER stop "<|end_header_id|>"
PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|reserved_special_token"

SYSTEM """You are Beru, a CySA+ certified security analyst for GP-Copilot. You read real scanner output — Nessus, GuardDuty, Prowler, Wazuh, Suricata, SecurityHub — the way a human SOC analyst does. You think in defense-in-depth layers and NIST 800-53 control families. When you see a finding, you determine the NIST control mapping, blast radius, priority (P1-P4), immediate action with specific commands, and a CISO-ready summary in business impact language. You never hallucinate NIST control IDs, scanner plugin numbers, or CVE identifiers. You never recommend 'investigate further' without specifying exactly what to investigate and how. Your max authority is C-rank."""
```

Write to `BERU-AI/Modelfile_beru8b`.

- [ ] **Step 2: Create requirements.txt**

```
requests>=2.31.0,<3.0
pyyaml>=6.0,<7.0
```

Write to `BERU-AI/requirements.txt`.

- [ ] **Step 3: Create README**

```markdown
# BERU-AI

Shadow-rank security analyst model for GP-Copilot.

- **Base model**: LLaMA 3.1-8B-Instruct
- **Training**: LoRA fine-tune (r=64, alpha=128, 4-bit quant, Unsloth)
- **Serving**: Ollama GGUF (beru:v1.0)
- **Domain**: CompTIA CySA+ / NIST 800-53

## What BERU Does

Reads real scanner output (Nessus, GuardDuty, Prowler, Wazuh, Suricata, etc.) and produces:

1. Triage decisions (P1-P4 priority with specific actions)
2. NIST 800-53 control mappings with reasoning
3. CISO-ready risk summaries (executive, technical, compliance tiers)

## Architecture

```
core/           - Analyst engine (parser, ingestion, NIST mapper, triage, risk summary)
config/         - System prompt, domain weights, scanner mappings, risk templates
providers/      - Ollama LLM provider (independent from JADE)
```

## Usage

```python
from core import FindingsIngestion, TriageEngine, RiskSummaryGenerator

ingestion = FindingsIngestion()
findings = ingestion.ingest_file(Path("scan_output.json"), scanner="guardduty")

engine = TriageEngine()
triaged = engine.triage_batch(findings, context={"environment": "production"})

generator = RiskSummaryGenerator()
summary = generator.summarize_batch(triaged, tier="executive")
```

## Design Spec

See `docs/superpowers/specs/2026-04-09-beru-ai-design.md`
```

Write to `BERU-AI/README.md`.

- [ ] **Step 4: Create seclab findings classifier**

```python
#!/usr/bin/env python3
"""
Classify SecLab Findings — Tag by Target Model and Pipeline

Reads raw scanner output from 0-data-lab/seclab-findings/ and classifies
each file by:
1. Target model (beru, jade, katie) — based on content domain
2. Pipeline (training, rag) — based on content type

Not hardcoded to any model — tagging rules are keyword-based and extensible.

Usage:
    python3 classify_seclab_findings.py [--dry-run]

Output:
    Prints classification for each file. With --dry-run, no files are moved.
    Without --dry-run, copies files to appropriate pipeline directories.
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Paths
SECLAB_DIR = Path(__file__).parent.parent / "seclab-findings"
TRAINING_DIR = Path(__file__).parent.parent.parent / "1-local-pipeline" / "01-raw-data-lake"
RAG_DIR = Path(__file__).parent.parent.parent / "2-rag-ingestion" / "01-unprocessed"

# Model tagging rules — keyword-based, not hardcoded
# Add new models by extending this dict
MODEL_TAGS = {
    "beru": {
        "description": "Security analyst — CySA+, NIST, vulnerability management, risk reporting",
        "keywords": [
            "nist", "800-53", "800-61", "cve", "cvss", "vulnerability",
            "nessus", "openvas", "guardduty", "securityhub", "prowler",
            "wazuh", "suricata", "zeek", "crowdstrike", "siem",
            "incident response", "forensic", "triage", "risk score",
            "compliance", "fedramp", "hipaa", "pci", "ciso",
            "ids", "ips", "firewall", "network security",
            "openscap", "lynis", "scap", "cis benchmark",
        ],
    },
    "jade": {
        "description": "Platform security — DevSecOps, K8s, containers, CI/CD",
        "keywords": [
            "kubernetes", "k8s", "pod", "deployment", "namespace",
            "helm", "argocd", "kyverno", "gatekeeper", "falco",
            "trivy", "kubescape", "semgrep", "bandit", "gitleaks",
            "dockerfile", "container", "rbac", "serviceaccount",
            "admission control", "securitycontext", "networkpolicy",
            "ci/cd", "github actions", "pipeline",
        ],
    },
    "katie": {
        "description": "Platform operations — K8s ops, health, diagnostics",
        "keywords": [
            "kubectl", "k8sgpt", "popeye", "node", "drain",
            "cordon", "etcd", "kubelet", "scheduler",
            "resource quota", "limitrange", "hpa", "pdb",
            "crashloopbackoff", "oomkilled", "pending pod",
        ],
    },
}

# Pipeline classification rules
PIPELINE_RULES = {
    "training": {
        "description": "Structured Q&A, triage decisions, tool walkthroughs",
        "extensions": [".jsonl", ".json"],
        "content_hints": ["messages", "question", "answer", "scenario"],
    },
    "rag": {
        "description": "Reference docs, scan reports, compliance docs, templates",
        "extensions": [".md", ".txt", ".pdf", ".csv", ".xml", ".html", ".log"],
        "content_hints": ["report", "template", "procedure", "policy", "standard"],
    },
}


def classify_file(file_path: Path) -> dict:
    """Classify a single file by target model and pipeline."""
    try:
        content = file_path.read_text(errors="replace").lower()
    except Exception:
        content = ""

    filename = file_path.name.lower()

    # Score each model
    model_scores = {}
    for model, config in MODEL_TAGS.items():
        score = sum(1 for kw in config["keywords"] if kw in content or kw in filename)
        model_scores[model] = score

    # Pick highest scoring model (ties go to first match)
    best_model = max(model_scores, key=model_scores.get)
    best_score = model_scores[best_model]

    # If no keywords matched, mark as unclassified
    if best_score == 0:
        best_model = "unclassified"

    # Determine pipeline
    ext = file_path.suffix.lower()
    pipeline = "rag"  # Default to RAG
    for pipe, rules in PIPELINE_RULES.items():
        if ext in rules["extensions"]:
            if any(hint in content for hint in rules["content_hints"]):
                pipeline = pipe
                break

    return {
        "file": str(file_path),
        "target_model": best_model,
        "pipeline": pipeline,
        "model_scores": model_scores,
        "classified_at": datetime.utcnow().isoformat() + "Z",
    }


def main():
    dry_run = "--dry-run" in sys.argv

    if not SECLAB_DIR.exists():
        print(f"seclab-findings directory not found: {SECLAB_DIR}")
        sys.exit(1)

    files = [f for f in SECLAB_DIR.iterdir() if f.is_file()]
    if not files:
        print("No files found in seclab-findings/")
        sys.exit(0)

    print(f"Classifying {len(files)} files from {SECLAB_DIR}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()

    results = []
    for f in sorted(files):
        result = classify_file(f)
        results.append(result)
        print(f"  {f.name}")
        print(f"    Model: {result['target_model']} (scores: {result['model_scores']})")
        print(f"    Pipeline: {result['pipeline']}")

        if not dry_run and result["target_model"] != "unclassified":
            dest_dir = TRAINING_DIR if result["pipeline"] == "training" else RAG_DIR
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f.name
            shutil.copy2(f, dest)
            print(f"    -> Copied to {dest}")

        print()

    # Summary
    print("--- Summary ---")
    for model in list(MODEL_TAGS.keys()) + ["unclassified"]:
        count = sum(1 for r in results if r["target_model"] == model)
        if count:
            print(f"  {model}: {count} files")

    # Write manifest
    manifest_path = SECLAB_DIR / ".classification_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nManifest written to {manifest_path}")


if __name__ == "__main__":
    main()
```

Write to `0-data-lab/tools/classify_seclab_findings.py`.

- [ ] **Step 5: Commit**

```bash
git add BERU-AI/Modelfile_beru8b BERU-AI/requirements.txt BERU-AI/README.md 0-data-lab/tools/classify_seclab_findings.py
git commit -m "feat(beru-ai): add Modelfile, requirements, README, and seclab findings classifier"
```

---

## Task 8: GP-API BERU Route

FastAPI endpoint exposing BERU's triage, summarize, NIST mapping, and explain capabilities.

**Files:**
- Create: `../../GP-INFRA/GP-API/routes/beru.py`
- Modify: `../../GP-INFRA/GP-API/main.py`

- [ ] **Step 1: Create BERU API route**

```python
"""
BERU API Routes
===============
Security analyst endpoints — triage findings, generate risk summaries,
map NIST controls, explain scanner output.

Endpoints:
- GET  /api/beru/health     - Health check
- POST /api/beru/triage     - Triage a single finding
- POST /api/beru/summarize  - Batch risk summary
- POST /api/beru/nist-map   - NIST 800-53 control mapping
- POST /api/beru/explain    - Scanner output walkthrough
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/beru", tags=["beru"])

# Add BERU-AI to path
GP_ROOT = Path(__file__).parent.parent.parent.parent
BERU_AI_PATH = GP_ROOT / "GP-MODEL-OPS" / "BERU-AI"
sys.path.insert(0, str(BERU_AI_PATH))

# Lazy-load BERU modules (avoid import errors if deps missing)
_triage_engine = None
_risk_generator = None
_nist_mapper = None
_ingestion = None
_provider = None


def _get_triage_engine():
    global _triage_engine
    if _triage_engine is None:
        from core.triage_engine import TriageEngine
        _triage_engine = TriageEngine()
    return _triage_engine


def _get_risk_generator():
    global _risk_generator
    if _risk_generator is None:
        from core.risk_summary import RiskSummaryGenerator
        _risk_generator = RiskSummaryGenerator(llm_provider=_get_provider())
    return _risk_generator


def _get_nist_mapper():
    global _nist_mapper
    if _nist_mapper is None:
        from core.nist_mapper import NISTMapper
        _nist_mapper = NISTMapper()
    return _nist_mapper


def _get_ingestion():
    global _ingestion
    if _ingestion is None:
        from core.findings_ingestion import FindingsIngestion
        _ingestion = FindingsIngestion()
    return _ingestion


def _get_provider():
    global _provider
    if _provider is None:
        try:
            from providers.ollama import OllamaProvider
            _provider = OllamaProvider()
        except Exception:
            _provider = None
    return _provider


# ============================================================================
# Request/Response Models
# ============================================================================

class FindingInput(BaseModel):
    """Raw scanner finding for triage."""
    scanner: str = Field(..., description="Scanner name (nessus, guardduty, prowler, etc.)")
    raw_output: str = Field(..., description="Raw scanner output (JSON, CSV, or text)")
    format_hint: Optional[str] = Field(default=None, description="Format override (json, csv, jsonl)")
    context: Optional[Dict] = Field(default=None, description="Environment context (environment, data_classification)")


class BatchInput(BaseModel):
    """Batch of findings for summarization."""
    findings: List[FindingInput]
    tier: str = Field(default="executive", description="Summary tier: executive, technical, compliance")


class NISTMapInput(BaseModel):
    """Single finding for NIST mapping."""
    scanner: str
    title: str
    description: str = ""
    severity: str = "UNKNOWN"


class ExplainInput(BaseModel):
    """Scanner output for analyst walkthrough."""
    scanner: str
    raw_output: str
    format_hint: Optional[str] = None


class TriageResponse(BaseModel):
    """Triage result."""
    model_config = {"protected_namespaces": ()}

    finding_id: str
    triage: Dict
    ciso_summary: str
    evidence: Dict
    response_time_ms: int


class HealthResponse(BaseModel):
    """Health check response."""
    model_config = {"protected_namespaces": ()}

    status: str
    ollama_available: bool
    model_name: str
    using_fallback: bool
    supported_scanners: List[str]


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health():
    """Check BERU health — Ollama reachable, model loaded, scanners configured."""
    provider = _get_provider()
    ingestion = _get_ingestion()

    ollama_ok = provider.is_available() if provider else False
    model_info = provider.get_model_info() if provider else {}

    return HealthResponse(
        status="ok" if ollama_ok else "degraded",
        ollama_available=ollama_ok,
        model_name=model_info.get("model", "none"),
        using_fallback=model_info.get("using_fallback", False),
        supported_scanners=ingestion.parser.supported_scanners(),
    )


@router.post("/triage", response_model=TriageResponse)
async def triage(finding: FindingInput):
    """Triage a single scanner finding."""
    start = time.time()

    ingestion = _get_ingestion()
    engine = _get_triage_engine()
    generator = _get_risk_generator()

    # Parse raw output
    parsed = ingestion.parser.parse(finding.scanner, finding.raw_output, finding.format_hint)
    if not parsed:
        raise HTTPException(status_code=422, detail="Could not parse scanner output")

    # Triage first finding
    triaged = engine.triage(parsed[0], context=finding.context)

    # Generate summary
    result = generator.summarize_finding(triaged, tier="executive")

    elapsed_ms = int((time.time() - start) * 1000)

    return TriageResponse(
        finding_id=result["finding_id"],
        triage=result["triage"],
        ciso_summary=result["ciso_summary"],
        evidence=result["evidence"],
        response_time_ms=elapsed_ms,
    )


@router.post("/summarize")
async def summarize(batch: BatchInput):
    """Generate CISO-ready risk summary for a batch of findings."""
    start = time.time()

    ingestion = _get_ingestion()
    engine = _get_triage_engine()
    generator = _get_risk_generator()

    all_triaged = []
    for f in batch.findings:
        parsed = ingestion.parser.parse(f.scanner, f.raw_output, f.format_hint)
        for p in parsed:
            triaged = engine.triage(p, context=f.context)
            all_triaged.append(triaged)

    result = generator.summarize_batch(all_triaged, tier=batch.tier)
    result["response_time_ms"] = int((time.time() - start) * 1000)

    return result


@router.post("/nist-map")
async def nist_map(finding: NISTMapInput):
    """Map a finding to NIST 800-53 controls."""
    mapper = _get_nist_mapper()

    normalized = {
        "scanner": finding.scanner,
        "title": finding.title,
        "description": finding.description,
        "severity": finding.severity,
        "raw_fields": {},
    }

    result = mapper.map_finding(normalized)
    return result


@router.post("/explain")
async def explain(input_data: ExplainInput):
    """Walk through scanner output like an analyst."""
    provider = _get_provider()
    ingestion = _get_ingestion()

    # Parse the output first
    parsed = ingestion.parser.parse(input_data.scanner, input_data.raw_output, input_data.format_hint)

    if provider and provider.is_available():
        prompt = (
            f"Walk me through this {input_data.scanner} output like I'm a junior analyst.\n"
            f"Explain each field, what's normal vs concerning, and what action to take.\n\n"
            f"Raw output:\n{input_data.raw_output[:2000]}"
        )
        explanation = provider.generate(prompt)
    else:
        # Structured fallback
        explanation = f"Parsed {len(parsed)} findings from {input_data.scanner}.\n\n"
        for i, f in enumerate(parsed[:10], 1):
            explanation += (
                f"{i}. [{f['severity']}] {f['title']}\n"
                f"   NIST hint: {f.get('nist_controls_hint', [])}\n\n"
            )

    return {
        "scanner": input_data.scanner,
        "findings_parsed": len(parsed),
        "explanation": explanation,
        "parsed_findings": parsed[:10],
    }
```

Write to the GP-API routes directory. The exact path is `../../GP-INFRA/GP-API/routes/beru.py` relative to BERU-AI, which is `/home/jimmie/linkops-industries/GP-copilot/GP-INFRA/GP-API/routes/beru.py`.

- [ ] **Step 2: Add BERU router to main.py**

Read `GP-INFRA/GP-API/main.py` first, then add the import and router inclusion following the same pattern as the JADE router. Add these lines:

```python
from routes.beru import router as beru_router
```

(in the imports section)

```python
app.include_router(beru_router)
```

(next to the existing `app.include_router(jade_router)` line)

- [ ] **Step 3: Commit**

```bash
git add ../../GP-INFRA/GP-API/routes/beru.py ../../GP-INFRA/GP-API/main.py
git commit -m "feat(beru-ai): add GP-API endpoints — /api/beru/{health,triage,summarize,nist-map,explain}"
```

---

## Task 9: Eval Scaffold

Benchmark questions and eval runner for BERU. Starts with a seed set — expands as training data grows.

**Files:**
- Create: `4-eval-clarify/beru_eval_suite_v1.jsonl`
- Create: `4-eval-clarify/beru_eval_runner.py`
- Create: `4-eval-clarify/2-test-data/beru/` (directory)
- Create: `4-eval-clarify/3-results/beru/` (directory)

- [ ] **Step 1: Create seed eval suite (20 questions across 5 domains)**

Write 20 eval questions (4 per domain) as JSONL. Each line follows the JADE eval format with BERU-specific domains.

```jsonl
{"id": "beru-tvm-001", "domain": "threat_vuln_management", "difficulty": "C", "scenario": "A Nessus scan shows CVE-2024-3094 (xz-utils backdoor, CVSS 10.0) on 3 production servers running Ubuntu 22.04. The affected package version is 5.6.0. What is your triage and remediation?", "expected_actions": ["Identify P1 priority", "Recommend immediate patching to 5.6.1+", "Map to NIST SI-2 and RA-5"], "expected_resources": ["Patch advisory", "NIST mapping"], "validation_keywords": ["SI-2", "P1", "5.6.1", "backdoor", "supply chain"], "objective": "Triage critical CVE with NIST mapping"}
{"id": "beru-tvm-002", "domain": "threat_vuln_management", "difficulty": "D", "scenario": "OpenVAS reports 47 LOW severity findings across your development environment. 40 are informational SSL certificate warnings. How do you handle this batch?", "expected_actions": ["Classify as P4", "Recommend bulk suppression of informational SSL warnings", "Flag remaining 7 for review"], "expected_resources": ["Scan report summary"], "validation_keywords": ["P4", "false positive", "suppress", "development"], "objective": "Efficient handling of low-severity scan noise"}
{"id": "beru-tvm-003", "domain": "threat_vuln_management", "difficulty": "B", "scenario": "Trivy host scan shows a CRITICAL vulnerability in libcurl (CVE-2023-38545) but the affected binary is not in the execution path of any running service. CVSS 9.8 but actual exploitability is low. How do you triage?", "expected_actions": ["Assess contextual risk vs CVSS score", "Recommend P3 with compensating controls", "Document risk acceptance rationale"], "expected_resources": ["Risk assessment"], "validation_keywords": ["contextual", "compensating", "risk acceptance", "execution path"], "objective": "CVSS vs contextual risk assessment"}
{"id": "beru-tvm-004", "domain": "threat_vuln_management", "difficulty": "C", "scenario": "Nuclei scan found an exposed .env file at https://api.example.com/.env containing AWS_SECRET_ACCESS_KEY. What immediate actions do you take?", "expected_actions": ["P1 — rotate AWS credentials immediately", "Block public access to .env", "Search CloudTrail for unauthorized API calls using the exposed key", "Map to NIST IA-5 and SC-28"], "expected_resources": ["AWS credential rotation procedure", "CloudTrail query"], "validation_keywords": ["rotate", "IA-5", "CloudTrail", "P1", "block"], "objective": "Exposed secrets incident response"}
{"id": "beru-som-001", "domain": "security_ops_monitoring", "difficulty": "C", "scenario": "GuardDuty finding: UnauthorizedAccess:EC2/MaliciousIPCaller.Custom, severity 8.0. Instance i-0abc123 in production VPC. The instance runs a customer-facing API handling PII.", "expected_actions": ["P1 triage", "Isolate instance via security group", "Capture memory dump", "Rotate IAM credentials", "Map to SI-4 and IR-4"], "expected_resources": ["Isolation procedure", "Forensic capture steps"], "validation_keywords": ["SI-4", "IR-4", "isolate", "security group", "PII", "P1"], "objective": "GuardDuty finding triage in production"}
{"id": "beru-som-002", "domain": "security_ops_monitoring", "difficulty": "D", "scenario": "Wazuh rule 5710 (sshd authentication failure) is firing 200+ times per hour from IP 203.0.113.50 against your jumpbox. What do you do?", "expected_actions": ["Identify brute force pattern", "Block source IP at firewall/security group", "Check if any logins succeeded", "Map to AC-7 and SI-4"], "expected_resources": ["Firewall rule", "Auth log review"], "validation_keywords": ["brute force", "block", "AC-7", "succeeded", "firewall"], "objective": "Detect and respond to brute force attack"}
{"id": "beru-som-003", "domain": "security_ops_monitoring", "difficulty": "C", "scenario": "Suricata alert: ET MALWARE Win32/Emotet Activity (signature ID 2024792), severity 1. Source: internal host 10.0.1.50, destination: known C2 server 198.51.100.25. What is your response?", "expected_actions": ["P1 — malware C2 communication", "Isolate host 10.0.1.50", "Block C2 IP at network boundary", "Begin forensic investigation", "Map to SI-3 and IR-4"], "expected_resources": ["Network isolation", "IOC list"], "validation_keywords": ["C2", "isolate", "SI-3", "IR-4", "Emotet", "forensic"], "objective": "Network IDS malware detection response"}
{"id": "beru-som-004", "domain": "security_ops_monitoring", "difficulty": "B", "scenario": "SecurityHub shows 15 CRITICAL findings from CIS AWS Foundations Benchmark. Your team has a FedRAMP Moderate audit in 30 days. Which findings do you prioritize and why?", "expected_actions": ["Map each finding to NIST 800-53 controls", "Prioritize findings that map to FedRAMP Moderate required controls", "Create POA&M for findings that cannot be remediated in 30 days"], "expected_resources": ["FedRAMP control mapping", "POA&M template"], "validation_keywords": ["FedRAMP", "POA&M", "prioritize", "800-53", "30 days"], "objective": "Audit-driven prioritization"}
{"id": "beru-ncm-001", "domain": "nist_compliance_mapping", "difficulty": "C", "scenario": "Prowler found that S3 bucket 'customer-data-prod' has no server-side encryption enabled. The bucket contains PII subject to HIPAA. Map this to NIST controls and provide remediation.", "expected_actions": ["Map to SC-28 (Protection of Information at Rest)", "Map to SC-13 (Cryptographic Protection)", "Recommend enabling SSE-KMS with customer-managed key", "Note HIPAA 164.312(a)(2)(iv) alignment"], "expected_resources": ["AWS CLI command for SSE-KMS", "NIST-HIPAA crosswalk"], "validation_keywords": ["SC-28", "SC-13", "SSE-KMS", "HIPAA", "encryption at rest"], "objective": "S3 encryption gap to NIST control mapping"}
{"id": "beru-ncm-002", "domain": "nist_compliance_mapping", "difficulty": "D", "scenario": "CloudTrail is not enabled in us-west-2 region. Map this gap to NIST controls.", "expected_actions": ["Map to AU-2 (Event Logging)", "Map to AU-12 (Audit Record Generation)", "Recommend enabling CloudTrail in all regions"], "expected_resources": ["CloudTrail enable command"], "validation_keywords": ["AU-2", "AU-12", "CloudTrail", "all regions"], "objective": "Audit logging gap mapping"}
{"id": "beru-ncm-003", "domain": "nist_compliance_mapping", "difficulty": "B", "scenario": "An auditor asks for evidence that your organization implements AC-2 (Account Management). What artifacts do you provide from your AWS environment?", "expected_actions": ["IAM user list with last activity dates", "IAM policies showing least privilege", "CloudTrail logs showing account creation/deletion events", "SSO/IdP configuration evidence"], "expected_resources": ["AWS CLI commands for evidence collection", "AC-2 control description"], "validation_keywords": ["AC-2", "IAM", "CloudTrail", "least privilege", "last activity"], "objective": "Evidence collection for AC-2 audit"}
{"id": "beru-ncm-004", "domain": "nist_compliance_mapping", "difficulty": "C", "scenario": "Lynis audit shows that password aging is not configured (PASS_MAX_DAYS = 99999) on 12 production Linux hosts. Map and remediate.", "expected_actions": ["Map to IA-5 (Authenticator Management)", "Recommend setting PASS_MAX_DAYS to 90 in /etc/login.defs", "Note compensating control if SSO is primary auth"], "expected_resources": ["login.defs configuration", "NIST IA-5 guidance"], "validation_keywords": ["IA-5", "PASS_MAX_DAYS", "90", "login.defs"], "objective": "Password policy gap remediation"}
{"id": "beru-irf-001", "domain": "incident_response_forensics", "difficulty": "C", "scenario": "GuardDuty detected CryptoCurrency:EC2/BitcoinTool.B!DNS on instance i-0abc123. The instance is a c5.4xlarge launched 6 hours ago by an IAM user that normally launches t3.micro instances. Walk through your IR process.", "expected_actions": ["Containment: isolate instance", "Evidence: capture AMI snapshot and memory dump", "Investigation: review CloudTrail for IAM user activity", "Eradication: terminate instance, rotate credentials", "Map to IR-4 and IR-5"], "expected_resources": ["IR procedure", "CloudTrail query", "AMI snapshot command"], "validation_keywords": ["IR-4", "IR-5", "snapshot", "CloudTrail", "containment", "cryptomining"], "objective": "Cryptomining incident response"}
{"id": "beru-irf-002", "domain": "incident_response_forensics", "difficulty": "B", "scenario": "Wazuh file integrity monitoring detected changes to /etc/passwd on a production web server. The change added a new user 'svc_backup' with UID 0. No change request exists.", "expected_actions": ["P1 — unauthorized root-level account creation", "Isolate the server", "Preserve /etc/passwd and auth logs", "Search for persistence mechanisms", "Map to SI-7 and IR-4"], "expected_resources": ["Forensic preservation checklist", "IOC search commands"], "validation_keywords": ["SI-7", "UID 0", "persistence", "isolate", "unauthorized"], "objective": "Unauthorized account creation response"}
{"id": "beru-irf-003", "domain": "incident_response_forensics", "difficulty": "D", "scenario": "A phishing email was reported by an employee. The email contains a link to a credential harvesting page mimicking your SSO portal. 3 employees may have clicked it. What are your first 4 actions?", "expected_actions": ["Force password reset for 3 affected users", "Block harvesting domain at DNS/proxy", "Review SSO logs for unauthorized access", "Send org-wide phishing alert"], "expected_resources": ["Password reset procedure", "DNS block command"], "validation_keywords": ["password reset", "block domain", "SSO logs", "phishing"], "objective": "Phishing incident initial response"}
{"id": "beru-irf-004", "domain": "incident_response_forensics", "difficulty": "C", "scenario": "CrowdStrike detected Cobalt Strike beacon activity on endpoint WORKSTATION-42. The beacon is communicating with C2 at 192.0.2.100 every 60 seconds. What is your containment and investigation plan?", "expected_actions": ["Network isolate WORKSTATION-42", "Block C2 IP at all boundaries", "Capture memory for beacon analysis", "Search for lateral movement indicators", "Map to IR-4, SI-4, SC-7"], "expected_resources": ["CrowdStrike isolation command", "Network block rule", "Memory capture tool"], "validation_keywords": ["Cobalt Strike", "beacon", "isolate", "C2", "lateral movement", "IR-4"], "objective": "Advanced threat containment"}
{"id": "beru-rmr-001", "domain": "risk_management_reporting", "difficulty": "C", "scenario": "Monthly scan produced 156 findings: 3 CRITICAL, 12 HIGH, 47 MEDIUM, 94 LOW. Write the executive summary paragraph for the CISO.", "expected_actions": ["Lead with the 3 critical findings", "Quantify business risk", "Recommend remediation timeline", "Reference NIST controls affected"], "expected_resources": ["Executive summary template"], "validation_keywords": ["critical", "business impact", "timeline", "remediation", "CISO"], "objective": "Monthly scan executive summary"}
{"id": "beru-rmr-002", "domain": "risk_management_reporting", "difficulty": "B", "scenario": "The CISO asks: 'We spent $200K on security tools this year. What's our risk reduction?' How do you answer this with data?", "expected_actions": ["Compare finding trends over time", "Calculate mean time to remediation improvement", "Map tool coverage to NIST control families", "Show before/after compliance gap percentages"], "expected_resources": ["Risk metrics dashboard", "Trend analysis"], "validation_keywords": ["ROI", "trend", "MTTR", "coverage", "before/after"], "objective": "Security ROI quantification"}
{"id": "beru-rmr-003", "domain": "risk_management_reporting", "difficulty": "D", "scenario": "A P3 vulnerability has been open for 90 days. The application team says they need 60 more days to patch because of a code freeze. Write the risk acceptance memo.", "expected_actions": ["Document the vulnerability and current severity", "State compensating controls in place", "Define the acceptance period (60 days)", "Require re-evaluation at expiry", "Get application owner signature"], "expected_resources": ["Risk acceptance template"], "validation_keywords": ["risk acceptance", "compensating controls", "60 days", "re-evaluation", "signature"], "objective": "Risk acceptance documentation"}
{"id": "beru-rmr-004", "domain": "risk_management_reporting", "difficulty": "C", "scenario": "Your organization failed 8 of 323 FedRAMP Moderate controls in the latest assessment. The auditor wants a POA&M within 30 days. What goes into each entry?", "expected_actions": ["Control ID and description", "Weakness description", "Remediation milestone with dates", "Scheduled completion date", "Resource estimate and responsible party"], "expected_resources": ["POA&M template", "FedRAMP guidance"], "validation_keywords": ["POA&M", "milestone", "completion date", "resource", "weakness"], "objective": "FedRAMP POA&M generation"}
```

Write to `4-eval-clarify/beru_eval_suite_v1.jsonl`.

- [ ] **Step 2: Create eval runner**

```python
#!/usr/bin/env python3
"""
BERU Eval Runner
================
Runs benchmark evaluation against BERU model (Ollama or local).
Scores responses by keyword matching and domain coverage.

Usage:
    python3 beru_eval_runner.py [--model beru:v1.0] [--domain threat_vuln_management]
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

EVAL_DIR = Path(__file__).parent
EVAL_SUITE = EVAL_DIR / "beru_eval_suite_v1.jsonl"
RESULTS_DIR = EVAL_DIR / "3-results" / "beru"

# Domain weights from spec
DOMAIN_WEIGHTS = {
    "threat_vuln_management": 0.30,
    "security_ops_monitoring": 0.25,
    "nist_compliance_mapping": 0.20,
    "incident_response_forensics": 0.15,
    "risk_management_reporting": 0.10,
}


def load_eval_suite(domain_filter: Optional[str] = None) -> List[Dict]:
    """Load eval questions, optionally filtered by domain."""
    questions = []
    with open(EVAL_SUITE) as f:
        for line in f:
            line = line.strip()
            if line:
                q = json.loads(line)
                if domain_filter is None or q["domain"] == domain_filter:
                    questions.append(q)
    return questions


def score_response(question: Dict, response: str) -> Dict[str, Any]:
    """Score a model response against expected keywords and actions."""
    response_lower = response.lower()

    # Keyword matching
    keywords = question.get("validation_keywords", [])
    matched_keywords = [kw for kw in keywords if kw.lower() in response_lower]
    keyword_score = len(matched_keywords) / len(keywords) if keywords else 0.0

    # Action coverage
    actions = question.get("expected_actions", [])
    matched_actions = []
    for action in actions:
        # Check if key terms from the action appear in the response
        action_terms = [t for t in action.lower().split() if len(t) > 3]
        if action_terms:
            match_ratio = sum(1 for t in action_terms if t in response_lower) / len(action_terms)
            if match_ratio >= 0.5:
                matched_actions.append(action)
    action_score = len(matched_actions) / len(actions) if actions else 0.0

    # Combined score
    combined = (keyword_score * 0.6) + (action_score * 0.4)

    return {
        "question_id": question["id"],
        "domain": question["domain"],
        "difficulty": question["difficulty"],
        "keyword_score": round(keyword_score, 3),
        "action_score": round(action_score, 3),
        "combined_score": round(combined, 3),
        "matched_keywords": matched_keywords,
        "missed_keywords": [kw for kw in keywords if kw not in matched_keywords],
        "matched_actions": matched_actions,
        "passed": combined >= 0.5,
    }


def run_eval(model_name: str = "beru:v1.0",
             domain_filter: Optional[str] = None,
             ollama_url: str = "http://localhost:11434") -> Dict[str, Any]:
    """Run full eval suite against model."""
    import requests

    questions = load_eval_suite(domain_filter)
    print(f"Running {len(questions)} eval questions against {model_name}")

    results = []
    for i, q in enumerate(questions, 1):
        print(f"  [{i}/{len(questions)}] {q['id']}...", end=" ", flush=True)

        start = time.time()
        try:
            resp = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": q["scenario"],
                    "system": "You are Beru, a CySA+ certified security analyst. Provide specific, actionable analysis with NIST control mappings.",
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 1000},
                },
                timeout=120,
            )
            resp.raise_for_status()
            response_text = resp.json().get("response", "")
        except Exception as e:
            response_text = f"ERROR: {e}"

        elapsed = time.time() - start
        scored = score_response(q, response_text)
        scored["response_time_s"] = round(elapsed, 2)
        scored["response_length"] = len(response_text)
        results.append(scored)

        status = "PASS" if scored["passed"] else "FAIL"
        print(f"{status} ({scored['combined_score']:.2f}, {elapsed:.1f}s)")

    # Aggregate by domain
    domain_scores = {}
    for domain, weight in DOMAIN_WEIGHTS.items():
        domain_results = [r for r in results if r["domain"] == domain]
        if domain_results:
            avg = sum(r["combined_score"] for r in domain_results) / len(domain_results)
            passed = sum(1 for r in domain_results if r["passed"])
            domain_scores[domain] = {
                "average_score": round(avg, 3),
                "passed": passed,
                "total": len(domain_results),
                "pass_rate": round(passed / len(domain_results), 3),
                "weight": weight,
                "weighted_score": round(avg * weight, 3),
            }

    # Overall weighted score
    weighted_total = sum(d["weighted_score"] for d in domain_scores.values())
    total_weight = sum(d["weight"] for d in domain_scores.values())
    overall = weighted_total / total_weight if total_weight > 0 else 0.0

    # Check promotion gates
    all_domains_pass = all(
        d["average_score"] >= 0.5 for d in domain_scores.values()
    )
    promotion_eligible = overall >= 0.6 and all_domains_pass

    summary = {
        "model": model_name,
        "eval_suite": str(EVAL_SUITE),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "questions_total": len(results),
        "questions_passed": sum(1 for r in results if r["passed"]),
        "overall_weighted_score": round(overall, 3),
        "promotion_eligible": promotion_eligible,
        "domain_scores": domain_scores,
        "results": results,
    }

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    result_path = RESULTS_DIR / f"eval-{model_name.replace(':', '-')}-{ts}.json"
    with open(result_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to {result_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"BERU Eval Summary — {model_name}")
    print(f"{'='*60}")
    print(f"Overall weighted score: {overall:.1%}")
    print(f"Promotion eligible: {'YES' if promotion_eligible else 'NO'}")
    print()
    for domain, scores in domain_scores.items():
        gate = "PASS" if scores["average_score"] >= 0.5 else "FAIL"
        print(f"  {domain}: {scores['average_score']:.1%} ({scores['passed']}/{scores['total']}) [{gate}]")

    return summary


if __name__ == "__main__":
    model = "beru:v1.0"
    domain = None

    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--model" and i < len(sys.argv) - 1:
            model = sys.argv[i + 1]
        if arg == "--domain" and i < len(sys.argv) - 1:
            domain = sys.argv[i + 1]

    run_eval(model_name=model, domain_filter=domain)
```

Write to `4-eval-clarify/beru_eval_runner.py`.

- [ ] **Step 3: Create result directories**

```bash
mkdir -p 4-eval-clarify/2-test-data/beru
mkdir -p 4-eval-clarify/3-results/beru
touch 4-eval-clarify/2-test-data/beru/.gitkeep
touch 4-eval-clarify/3-results/beru/.gitkeep
```

- [ ] **Step 4: Commit**

```bash
git add 4-eval-clarify/beru_eval_suite_v1.jsonl 4-eval-clarify/beru_eval_runner.py 4-eval-clarify/2-test-data/beru/.gitkeep 4-eval-clarify/3-results/beru/.gitkeep
git commit -m "feat(beru-ai): add eval suite (20 seed questions, 5 domains) and eval runner"
```

---

## Task 10: Model Card and Experiment Scaffold

Documentation for BERU as a challenger model and experiment tracking.

**Files:**
- Create: `6-model-cards/challenger/beru-v1.md`
- Create: `5-experiments/exp-004-beru-v1-cysa/params.yaml`
- Create: `5-experiments/exp-004-beru-v1-cysa/notes.md`

- [ ] **Step 1: Create challenger model card**

```markdown
# BERU v1.0 — Model Card

**Status**: Challenger (not yet trained)
**Base model**: LLaMA 3.1-8B-Instruct (meta-llama/Llama-3.1-8B-Instruct)
**Training method**: LoRA (r=64, alpha=128, 4-bit quantized, Unsloth)
**Domain**: CompTIA CySA+ / NIST 800-53
**Role**: Security analyst — scanner triage, NIST mapping, CISO-ready summaries

## Intended Use

Reads real scanner output (Nessus, GuardDuty, Prowler, Wazuh, Suricata, etc.) and produces:
- Triage decisions (P1-P4 with specific actions)
- NIST 800-53 control mappings with reasoning
- CISO-ready risk summaries (executive, technical, compliance tiers)

## Limitations

- Not yet trained — this card tracks the challenger model through its lifecycle
- Max authority: C-rank (hardcoded, same as JADE/Katie)
- NIST mapping is keyword-based until LLM fine-tuning improves accuracy
- No real scanner training data yet — training blocked on seclab data collection

## Training Data

- Source: `0-data-lab/seclab-findings/` (real scanner output from seclab)
- Format: ChatML (messages array with system/user/assistant)
- Quality gate: Schema validation + BERU-specific checks (real output, NIST accuracy, no vendor marketing)
- Target corpus: TBD (depends on seclab data volume)

## Eval Benchmark

- Suite: `4-eval-clarify/beru_eval_suite_v1.jsonl` (20 seed questions, expanding)
- Domains: Threat/Vuln (30%), SecOps (25%), NIST/Compliance (20%), IR/Forensics (15%), Risk/Reporting (10%)
- Promotion gate: Weighted >= 60%, each domain >= 50%
- Zero tolerance: Hallucinated NIST control IDs, made-up plugin numbers

## Metrics

Not yet evaluated. First eval after training chunk 1.

## Version History

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| v1.0 | 2026-04-09 | Challenger (scaffold) | Directory structure, config, core modules, eval suite created |
```

Write to `6-model-cards/challenger/beru-v1.md`.

- [ ] **Step 2: Create experiment params**

```yaml
# Experiment: BERU v1 — CySA+/NIST Fine-Tune
# Hypothesis: LLaMA 3.1-8B can learn scanner triage patterns and NIST mapping
# from real seclab findings via LoRA fine-tuning

experiment_id: "exp-004-beru-v1-cysa"
model: "beru"
base_model: "unsloth/Llama-3.1-8B-Instruct"

lora:
  r: 64
  alpha: 128
  dropout: 0
  target_modules: ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

training:
  epochs_per_chunk: 2
  batch_size: 4
  gradient_accumulation_steps: 8
  learning_rate: 2e-5
  warmup_ratio: 0.03
  lr_scheduler: "cosine"
  weight_decay: 0.01
  max_seq_length: 2048
  load_in_4bit: true

domain_weights:
  threat_vuln_management: 0.30
  security_ops_monitoring: 0.25
  nist_compliance_mapping: 0.20
  incident_response_forensics: 0.15
  risk_management_reporting: 0.10

data:
  source: "0-data-lab/seclab-findings/"
  corpus_version: "TBD — pending seclab data collection"
  quality_gate: "8-tests/test_beru_schemas.py"

eval:
  suite: "4-eval-clarify/beru_eval_suite_v1.jsonl"
  promotion_threshold: 0.60
  domain_minimum: 0.50
```

Write to `5-experiments/exp-004-beru-v1-cysa/params.yaml`.

- [ ] **Step 3: Create experiment notes**

```markdown
# Experiment 004: BERU v1 — CySA+/NIST Fine-Tune

## Hypothesis

LLaMA 3.1-8B-Instruct can learn scanner output triage patterns and accurate NIST 800-53 control mapping from real seclab findings, producing CISO-ready risk summaries that are structured (JSON) and narrative.

## Status

**Scaffold complete.** Training blocked on real scanner data.

## What's Done

- [x] Directory structure (BERU-AI/)
- [x] Config files (system prompt, domain weights, scanner mappings, risk templates)
- [x] Data schemas (training example, risk summary)
- [x] Core modules (parser, ingestion, NIST mapper, triage engine, risk summary generator)
- [x] Providers (Ollama with fallback)
- [x] GP-API endpoints (/api/beru/*)
- [x] Eval suite (20 seed questions across 5 domains)
- [x] Tests (schema validation, core module unit tests)

## What's Next

1. Populate `0-data-lab/seclab-findings/` with real scanner output
2. Run `classify_seclab_findings.py` to tag data for BERU
3. Build training data generators from real findings
4. Train chunk 1 and evaluate
5. Expand eval suite to ~400 questions

## Observations

(To be filled during training)
```

Write to `5-experiments/exp-004-beru-v1-cysa/notes.md`.

- [ ] **Step 4: Commit**

```bash
git add 6-model-cards/challenger/beru-v1.md 5-experiments/exp-004-beru-v1-cysa/
git commit -m "feat(beru-ai): add challenger model card and experiment scaffold"
```

---

## Task 11: Update CLAUDE.md and Memory

Update GP-MODEL-OPS CLAUDE.md to include BERU-AI in the model registry and update memory for future conversations.

**Files:**
- Modify: `CLAUDE.md` (GP-MODEL-OPS root)
- Create/Update: Memory files

- [ ] **Step 1: Update CLAUDE.md**

Add BERU-AI to the "Two model tracks" section (now three), add to the repository structure diagram, and add BERU to common commands. Read the file first to find the exact locations.

- [ ] **Step 2: Update MEMORY.md**

Add BERU-AI entry to the memory index for future conversations.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add BERU-AI to GP-MODEL-OPS CLAUDE.md model registry"
```

---

## Summary

| Task | What It Builds | Tests |
|------|---------------|-------|
| 1 | Config files (system prompt, weights, scanner mappings, templates) | - |
| 2 | Data schemas (training + risk summary) | - |
| 3 | Schema validation tests | 14 tests |
| 4 | Ollama provider (independent from JADE) | - |
| 5 | Core modules (parser, ingestion, NIST mapper, triage, risk summary) | - |
| 6 | Core module unit tests | ~25 tests |
| 7 | Modelfile, requirements, README, seclab classifier | - |
| 8 | GP-API BERU endpoints | - |
| 9 | Eval suite (20 seed questions) + eval runner | - |
| 10 | Model card + experiment scaffold | - |
| 11 | CLAUDE.md + memory updates | - |

**Total estimated tests**: ~39
**Total new files**: ~25
**Modified files**: 2 (GP-API main.py, CLAUDE.md)
