# 10-crewai-mlops — AI Automation Crews

All CrewAI orchestration for the GP-MODEL-OPS pipeline lives here. Three production crews, one architectural pattern.

---

## The Pattern: Collectors + Judgment Agents

The insight behind every crew in this package is the same: **don't use an LLM for what deterministic code can do**.

Each crew is split into two layers:

```
collectors.py  — pure Python, no LLM
                 reads files, calls APIs, runs pipeline stages
                 produces structured batches
                        ↓
CrewAI agents  — LLM judgment only
                 quality review, semantic classification,
                 routing decisions, coverage reporting
```

Data collection is deterministic and fast. Agent work is where you actually need language understanding. Mixing them wastes tokens and makes failures hard to diagnose. Keep them separate.

State between agents passes through a per-run JSON file on disk — not through CrewAI's context strings. This avoids hitting token limits when batches are large.

---

## Crews

### synthetic_pipeline — Training Data Factory (port 8001)

Converts real JSA security findings and scan outputs into ChatML training examples for JADE/Katie fine-tuning.

```
pipeline.py (5 phases: discover → generate → merge → validate → save)
    ↓
CrewAI crew (3 agents, sequential):
  pipeline_orchestrator  → decides what to generate and at what volume
  quality_auditor        → scores examples, flags garbage, enforces format
  report_generator       → coverage gap analysis, per-domain breakdown
```

**Source pipeline:** `0-data-lab/synthetic-pipeline/`

```bash
python3 -m crewai_mlops.synthetic_pipeline.main run --min-quality 60
curl -X POST http://localhost:8001/run/synthetic-pipeline -H 'Content-Type: application/json' \
  -d '{"min_quality_score": 60, "max_examples": 500}'
```

---

### beru — NIST 800-53 Audit Crews (port 8089)

Three sub-crews sharing one agent pool. BERU reads scanner output and produces structured GRC findings — dual-cited against NIST 800-53 and AI RMF.

```
Agent pool (6 agents):
  beru_auditor   triage_agent   ssp_reviewer
  assessor       sar_writer     poam_writer

Sub-crews:
  beru_audit.py       — 2 agents: triage → audit finding
  ssp_to_poam.py      — 4 agents: review → assess → SAR → POA&M
  ac_access_control/  — 3 agents + pure Python collectors (kubectl/AWS CLI)
```

**Source system:** `BERU-AI/`

```bash
python3 -m crewai_mlops.beru.main run
# or via Docker (port 8089):
docker compose -f BERU-AI/docker-compose.yml up
```

---

### rag_ingestion — RAG Prep Crew (port 8002)

Runs the 7-stage RAG prep factory as pure Python pre-flight, then hands borderline items to 4 LLM agents for quality review, semantic labeling, routing validation, and coverage reporting.

```
collectors.py (no LLM):
  Stage 1: discover files by category
  Stage 2: preprocess (parse formats)
  Stage 3: sanitize (dedup, PII, JSON repair) → PASS / REPAIR / FAIL
  Stage 4: format_convert → JSONL chunks
  Stage 5 Tier 1+2: ontology + regex labeling → labeled / unlabeled
  Stage 6: route → collection assignments
  Outputs: pass_batch, repair_batch, unlabeled_batch, routing_decisions
        ↓
CrewAI crew (4 agents, sequential):
  quality_reviewer   → REPAIR items → promote PASS or demote FAIL
  semantic_labeler   → unlabeled items → domain / type / tags
  routing_validator  → routing decisions → override misroutes / SKIPs
  pipeline_reporter  → stats + overrides → markdown report + go/no-go
        ↓
2-rag-ingestion/03-preprocessed/processed_{timestamp}.jsonl
2-rag-ingestion/03-preprocessed/crew-report_{timestamp}.md
```

**Source pipeline:** `2-rag-ingestion/02-preperation-factory/`

```bash
python3 -m crewai_mlops.rag_ingestion.main run --category compliance
python3 -m crewai_mlops.rag_ingestion.main run --dry-run
curl -X POST http://localhost:8002/run/rag-prep -H 'Content-Type: application/json' \
  -d '{"category": "compliance", "dry_run": false}'
```

---

## Package Structure

```
10-crewai-mlops/
  __init__.py
  synthetic_pipeline/
    __init__.py
    main.py       ← FastAPI + CLI (port 8001)
    agents.py     ← 3 agent definitions
    tools.py      ← tools that read pipeline state
    crews/
      prep_crew.py
  beru/
    __init__.py
    main.py       ← FastAPI + CLI (port 8089)
    agents.py     ← 6 agent pool
    Dockerfile
    crews/
      beru_audit.py
      ssp_to_poam.py
      ac_access_control/
  rag_ingestion/
    __init__.py
    main.py       ← FastAPI + CLI (port 8002)
    agents.py     ← 4 agent definitions
    tools.py      ← tools that read/write run state JSON
    collectors.py ← pure Python pre-flight (wraps stages/ modules)
    crews/
      prep_crew.py
```

---

## Python Import

The directory name has a leading number (`10-crewai-mlops`), which is not a valid Python identifier. `8-tests/conftest.py` registers it as `crewai_mlops` via `importlib` so tests and imports work:

```python
from crewai_mlops.rag_ingestion.collectors import run_preflight
from crewai_mlops.beru.agents import beru_auditor
```

---

## LLM Configuration

All crews read `CREWAI_LLM` from the environment. Default: `ollama/llama3.1` (local, no API cost).

```bash
# Local (default)
CREWAI_LLM=ollama/llama3.1 python3 -m crewai_mlops.rag_ingestion.main run

# Claude (for production quality)
CREWAI_LLM=claude-3-5-haiku-20241022 python3 -m crewai_mlops.rag_ingestion.main run
```
