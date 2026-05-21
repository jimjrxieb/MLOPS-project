# M8 — Capstone: BERU End-to-End

> **Goal:** Wire everything together. Run the full pipeline from one command. Tell the story in 5 minutes.
> **Build:** The complete BERU demo — API/graph path from scanner or SSP evidence to evidence package.
> **Gate:** `DEMO.md` checks pass and the stack boots through `BERU-AI/docker-compose.yml`.

---

## What This Module Is

M8 is assembly. You built all the parts in M0-M7. Now you connect them, test the seams, and practice telling the story.

The technical work is mostly debugging integration points — the places where two modules connect and something breaks. The non-technical work is writing the interview story so it flows naturally when asked.

---

## The Full Pipeline (What "Connected" Means)

```
Input:  scanner output file (Trivy JSON)
           │
           ▼
   [1] ToolOutputParser          → normalized finding dicts
           │
           ▼
   [2] NISTMapper                → 800-53 controls + AI RMF subcategories
           │
           ▼
   [3] ChromaDB retrieval        → relevant control text injected into context
   (beru-nist-800-53 collection)
           │
           ▼
   [4] BERU model via Ollama     → structured BERU finding (LLM call)
           │
           ▼
   [5] validate_control_id()     → catches hallucinated IDs before they leave
           │
           ▼
   [6] HITLRouter                → E/D/C → continue │ B/S → pending queue
           │                                         │
           ▼                                         ▼
   [7] EvidencePackager          → findings.jsonl, poam.md, ciso-briefing.md, evidence.zip
```

Every box is a module you built:
- Box 1 → M0 (core/tool_output_parser.py)
- Box 2 → M0 (core/nist_mapper.py)
- Box 3 → M2 (ChromaDB beru-nist-800-53)
- Box 4 → M1+M3 (`BERU-AI/modelfiles/Modelfile_beru3b` + model registry)
- Box 5 → M1 (validate_control_id)
- Box 6 → M0 (tools/hitl_router.py — built in Phase 2)
- Box 7 → M0 (tools/evidence_packager.py — built in Phase 2)

The LangGraph agent (`BERU-AI/agent/graph.py` + `BERU-AI/agent/nodes.py`) is the orchestrator that calls each box in sequence.

---

## Integration Checklist

Run through this before the demo. These are the seams that break.

### Seam 1: Scanner parser → NIST mapper
```python
# Verify the normalized finding has the right shape
parser = ToolOutputParser()
findings = parser.parse("trivy", open("sample-trivy.json").read(), format_hint="json")
assert findings[0]["scanner"] == "trivy"
assert "severity" in findings[0]
assert "nist_controls_hint" in findings[0]
```

### Seam 2: NIST mapper → ChromaDB
```python
# Verify controls mapped, then retrievable
mapper = NISTMapper()
result = mapper.map_finding(findings[0])
primary_control = result["primary_control"]  # e.g., "SI-2"

# Now retrieve from ChromaDB
collection = get_beru_collection()
docs = collection.query(query_texts=[primary_control], n_results=2)
assert len(docs["documents"][0]) > 0, f"No docs found for {primary_control}"
```

### Seam 3: Control text → LLM prompt
```python
# Verify the LLM receives the control text in context
rag_context = docs["documents"][0][0]
# This must appear in the user message sent to the BERU model.
# If it's not there, BERU is answering from weights only
```

### Seam 4: LLM output → validation
```python
# Verify control ID in output is real
output_text = llm_response
control_ids_in_output = re.findall(r"\b[A-Z]{2}-\d+\b", output_text)
for cid in control_ids_in_output:
    assert mapper.validate_control_id(cid), f"Hallucinated control ID: {cid}"
```

### Seam 5: Rank → HITL router
```python
# Verify B-rank findings don't make it to output
router = HITLRouter()
for finding in mapped_findings:
    result = router.route(finding)
    if result["rank"] in ("B", "S"):
        assert result["status"] == "pending_human"
        # This finding must NOT appear in the final output artifacts
```

### Seam 6: Outputs → Evidence package
```python
packager = EvidencePackager()
pkg = packager.package(findings=approved_findings, poam_text=poam, ...)
verify = packager.verify(pkg["archive_path"])
assert verify["valid"] is True
```

---

## The Demo Script (5 Minutes)

Practice this until it's automatic. This is what you run in an interview when they ask "show me."

```bash
# Terminal 1: start Ollama (should already be running in prod)
ollama serve

# Terminal 2: run the reviewer path
cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS
sed -n '1,220p' CAPSTONE-PROJECT/DEMO.md
python3 -m pytest 8-tests/test_rag_ingestion_crew.py 8-tests/test_crewai_beru_schemas.py -q
cd BERU-AI && docker compose up --build
```

---

## The Interview Story

When they ask "tell me about a project you're proud of," this is the answer. Say it out loud until it takes 90 seconds or less:

> "I built BERU — a guarded GRC analyst model and workflow system for NIST 800-53 and NIST AI RMF. It ingests scanner output and SSP evidence, maps findings to controls through RAG over bundled governance knowledge, and produces structured findings, POA&M drafts, and CISO summaries. The runtime path uses LangGraph, governance workflows use CrewAI, serving is through FastAPI and Ollama, and MLflow tracks eval and inference runs. I baseline-tested before fine-tuning so model lift is measured, not assumed.
>
> What makes it interesting is that it follows two frameworks simultaneously — NIST 800-53 for IT infrastructure findings and NIST AI RMF for findings about AI systems themselves. So when BERU assesses a Kubernetes cluster running Ollama, it can produce both an infrastructure finding about RBAC configuration and an AI governance finding about whether the model has a registered inventory entry. B-rank and S-rank findings are architecturally blocked from auto-output — they go to a human review queue enforced by the HITL router.
>
> The model has not passed my autonomous promotion gate yet. That is part of the project: the gate blocks promotion while I improve dual citation, evidence-gap detection, and ATLAS-mapped AI risk coverage."

---

## Connecting to the Job Requirements

| Requirement | Module | What you say |
|-------------|--------|-------------|
| "Production Python backend" | M0 | "gap-to-poam.py — typed, tested, validated, CLI interface" |
| "LLM integrations" | M1 | "Ollama local, Anthropic API for B/S decisions, same message format" |
| "RAG systems, embeddings" | M2 | "ChromaDB beru-nist-800-53, nomic-embed-text, semantic retrieval over 50+ controls" |
| "Fine-tuning" | M3 | "LLaMA 3.2-3B, LoRA r=32, Unsloth, 200+ synthetic GRC examples, brain baseline before/after" |
| "Agents / agentic architecture" | M4 | "LangGraph StateGraph, 6 nodes, playbook-as-brain, no improvisation" |
| "MLOps + CI/CD" | M5 | "MLflow eval tracking, GitHub Actions gate, Ollama versioned models" |
| "Docker + Kubernetes" | M5 | "K8s deployment manifests, non-root, resource limits, health probes" |
| "Domain expertise" | M6 | "BERU-COVERAGE.md — honest 80/20 coverage map" |
| "AI governance" | M6+M7 | "AI RMF dual-citation, AI inventory register, risk assessment completed for BERU itself" |
| "Executive communication" | M7 | "CISO briefing template — no NIST IDs, three questions, one page" |

---

## Troubleshooting the Full Pipeline

| Symptom | Module | Fix |
|---------|--------|-----|
| `ModuleNotFoundError` when importing BERU modules | Path setup | Run from `GP-MODEL-OPS/` or use the FastAPI service path |
| ChromaDB returns empty results | M2 ingestion not run | Run the ingestion script against NIST control files first |
| LLM output missing fields | M1 system prompt not loaded | Check Modelfile TEMPLATE — system prompt must be in the conversation history |
| B-rank findings in output files | M4 HITL not wired | Check `route_by_rank` node calls `HITLRouter` before `produce_outputs` |
| Evidence package verify fails | M5 packaging order | Write all artifacts before calling `packager.package()` — don't package partial results |
| `ollama: model not found` | M5 model not registered | Check `BERU-AI/docker-compose.yml` and the mounted model registry path |
| Demo runs but output is empty | M4 state not flowing | Print state at each node boundary to find where data stops |
| MLflow run not showing up | M5 tracking URI | Check `mlflow.set_tracking_uri()` matches the path where the runs are stored |

---

## Capstone Completion Checklist

When every row is checked, you're done.

| Item | Module | How to verify |
|------|--------|--------------|
| `gap-to-poam.py` — mypy clean, ≥80% coverage | M0 | `mypy` + `pytest --cov` |
| System prompt produces 10-field output consistently | M1 | 10 API calls, check format |
| `beru-nist-800-53` collection populated | M2 | Query "least privilege" → AC-6 |
| 200+ training examples pass quality gates | M3 | `pytest test_data_quality.py` |
| Fine-tuned BERU beats base model on 30-question eval | M3 | MLflow before/after scores |
| BERU graph/API path runs end-to-end | M4 | Demo script runs clean |
| `/api/beru` endpoint responds | M5 | `curl /api/beru/health` → 200 |
| MLflow `beru-eval` experiment has at least one run | M5 | MLflow UI |
| GitHub Actions workflow passes | M5 | Green checkmark on latest commit |
| `BERU-COVERAGE.md` — 5+ families with honest gaps | M6 | File exists, gaps documented |
| CISO briefing template — zero NIST IDs | M7 | Ctrl+F for "AC-", "SI-", etc. |
| One-command demo produces all 4 artifacts | M8 | `ls /tmp/beru-demo/` |

**Start applying at M5. Apply hard at M8 completion.**

---

## Control Traceability

> The capstone is the evidence package. Every control below is something you can point to in the ZIP.

**NIST 800-53:**

| Control | What it maps to in M8 | Artifact in evidence package |
|---------|----------------------|------------------------------|
| **CA-7** — Continuous Monitoring | The full BERU pipeline running end-to-end IS the continuous monitoring system | `findings.jsonl` — every scan, every finding, every run |
| **CA-5** — Plan of Action and Milestones | POA&M generation from BERU output → `gap-to-poam.py` → ServiceNow CSV | `poam.md` + `poam-<system>-<date>.csv` |
| **AU-3** — Content of Audit Records | `EvidencePackager` manifest contains sha256, timestamp, assessor, and artifact list | `manifest.json` inside `evidence.zip` |
| **AU-6** — Audit Record Review, Analysis, and Reporting | CISO briefing is the executive summary of findings — business language, no NIST IDs | `ciso-briefing.md` |
| **SI-7** — Software, Firmware, and Information Integrity | Detached `.sha256` checksum file alongside every evidence ZIP | `beru-evidence-<system>-<ts>.sha256` |

**NIST AI RMF:**

| Subcategory | What it maps to | Artifact in evidence package |
|-------------|----------------|------------------------------|
| **MANAGE-2.2** — Human oversight mechanisms | `approved.jsonl` from HITLRouter — proof that B/S findings were human-reviewed before inclusion | `hitl/approved.jsonl` inside `evidence.zip` |
| **MANAGE-2.4** — Mechanisms to sustain deployed AI systems | MLflow run ID in the manifest links the assessment to the specific BERU version that produced it | `manifest.json` → `run_id` → MLflow |
| **MEASURE-2.13** — TEVV metrics are tracked | Eval scores in `5-experiments/` show BERU's accuracy on GRC benchmarks over time | `5-experiments/exp-NNN/metrics.json` |

**The 3PAO moment:**
An auditor opens `evidence.zip`. They see `manifest.json`. They check the sha256. They open `hitl/approved.jsonl` and see every B-rank finding was approved by a human before it went into the report. They look at `findings.jsonl` and see every finding has a control ID, a risk rank, and an evidence gap. They ask "how do I know this model version is the one you evaluated?" — you hand them the MLflow run ID from the manifest.

That's the answer to every question in one ZIP file.


# BERU Capstone Master Checklist

## 1. Governance System (AI Governance / GRC Layer)

Purpose:

> “Are controls, approvals, evidence, and risk managed correctly?”

### Core Features

* [ ] NIST 800-53 control mappings
* [ ] NIST AI RMF mappings
* [ ] AI inventory/risk register
* [ ] HITL approval workflow
* [ ] POA&M generation
* [ ] SSP review/parsing
* [ ] Evidence packaging
* [ ] SHA256 evidence manifests
* [ ] Audit logging
* [ ] Severity classification
* [ ] Risk scoring
* [ ] Remediation recommendations
* [ ] JSON findings export
* [ ] Governance reports

### Governance Policies

* [ ] Dangerous actions require approval
* [ ] Audit logs cannot be disabled
* [ ] Only approved models allowed
* [ ] Sensitive documents blocked
* [ ] Data retention policy enforced

### Framework Mapping

* [ ] OWASP LLM mappings
* [ ] NIST AI RMF mappings
* [ ] NIST 800-53 mappings
* [ ] FedRAMP alignment
* [ ] CIS Benchmarks references

---

# 2. Evaluation System (AI Behavior / Quality Layer)

Purpose:

> “Does the AI behave correctly and consistently?”

### RAG Evaluations

* [ ] Correct document retrieval
* [ ] Citation accuracy
* [ ] Hallucination detection
* [ ] Retrieval relevance scoring
* [ ] Similarity threshold testing
* [ ] Source grounding validation

### Model Behavior Evals

* [ ] Correct control mapping
* [ ] Correct severity classification
* [ ] Consistent outputs
* [ ] Structured reasoning checks
* [ ] Refusal behavior validation
* [ ] Benchmark dataset support

### Eval Infrastructure

* [ ] pytest evaluation suite
* [ ] JSONL dataset support
* [ ] Scoring/rubric engine
* [ ] Pass/fail thresholds
* [ ] Evidence output
* [ ] CI/CD integration

### Evaluation Datasets

* [ ] Malicious prompt dataset
* [ ] SSP test dataset
* [ ] Control mapping dataset
* [ ] Vulnerability classification dataset
* [ ] AI abuse-case dataset

---

# 3. Security System (AI Pentest / Red Team Layer)

Purpose:

> “Can the AI system be abused, manipulated, or bypassed?”

### Prompt Injection Testing

* [ ] Direct prompt injection
* [ ] Indirect prompt injection
* [ ] System prompt extraction
* [ ] Instruction override testing
* [ ] Jailbreak testing

### RAG Security Testing

* [ ] RAG poisoning
* [ ] Malicious document injection
* [ ] Context manipulation
* [ ] Retrieval leakage testing
* [ ] Sensitive data exposure testing

### Agent Security Testing

* [ ] Excessive agency testing
* [ ] Tool abuse testing
* [ ] Privilege escalation scenarios
* [ ] Unsafe command execution
* [ ] HITL bypass attempts

### Infrastructure Security

* [ ] Kubernetes RBAC validation
* [ ] Secret exposure checks
* [ ] Container scanning
* [ ] Network policy validation
* [ ] API authentication testing

### Security Framework Alignment

* [ ] OWASP LLM Top 10 mappings
* [ ] MITRE ATLAS references
* [ ] AI threat modeling
* [ ] CVSS scoring support
* [ ] EPSS awareness

---

# CI/CD Pipeline Checklist

## Static Policy Checks

* [ ] Conftest/OPA policies
* [ ] Kubernetes policy validation
* [ ] AI governance policy validation
* [ ] Terraform/IaC scanning

## Runtime Evaluations

* [ ] pytest AI evals
* [ ] Security attack simulations
* [ ] RAG validation tests
* [ ] Regression testing

## Evidence Generation

* [ ] Findings JSON export
* [ ] Markdown reports
* [ ] SHA256 manifests
* [ ] Pipeline artifacts upload

---

# “Recruiter Demo” Features

These are the flashy/high-value items.

* [ ] Dashboard showing eval pass/fail
* [ ] OWASP LLM mapping output
* [ ] NIST mapping output
* [ ] Automated evidence package
* [ ] Prompt injection demo
* [ ] HITL approval demo
* [ ] RAG poisoning demo
* [ ] Audit log viewer
* [ ] AI risk register

---

# The Core Story Your Project Tells

> “This platform evaluates AI systems for governance compliance, behavioral reliability, and security resilience using policy-as-code, adversarial testing, and structured AI evaluation pipelines.”

That is an EXTREMELY modern capstone direction.
