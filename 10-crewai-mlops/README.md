# 10-crewai-mlops

CrewAI workflows for turning AI governance, compliance, and MLOps playbooks into repeatable agentic review flows.

This folder is the orchestration layer for GP-Copilot model operations. The main idea is simple: deterministic Python gathers evidence, then CrewAI agents perform the human-like review work that benefits from language reasoning.

## Why This Exists

Most AI governance work starts as playbooks:

- check these files
- gather this evidence
- compare it to this control
- identify gaps
- write a finding
- route the risk to the right owner

This project turns that kind of playbook into an executable workflow.

The goal is not to replace a human governance engineer. The goal is to give that engineer a repeatable evidence-gathering and first-pass review system that produces structured outputs they can inspect, challenge, and improve.

## Architecture Pattern

Every crew follows the same split:

```text
deterministic collectors
  - read files
  - call APIs
  - run scanners or pipeline stages
  - normalize evidence
  - produce structured JSON state

CrewAI judgment agents
  - review evidence quality
  - classify risk
  - map evidence to controls
  - write reports
  - recommend go/no-go or HITL routing
```

This keeps LLMs out of the parts that should be deterministic. It also makes the workflows easier to test because evidence collection and agent judgment are separate concerns.

State is passed through per-run JSON files instead of stuffing large batches into agent prompts. That keeps context usage controlled and makes the workflow easier to audit after a run.

## Current Crews

### 1. RAG Ingestion Prep Crew

Package: `crewai_mlops.rag_ingestion`

Turns a RAG ingestion playbook into a review workflow.

The collector runs the existing `2-RagIngestion-Pipeline` prep stages:

- discover files by category
- parse supported formats
- sanitize and deduplicate content
- convert to JSONL chunks
- apply Tier 1/Tier 2 labels
- route items to target collections

Then four CrewAI agents review the run:

- `quality_reviewer`: decides whether repairable items should pass or fail
- `semantic_labeler`: fills missing domain/type/tag metadata
- `routing_validator`: checks collection routing decisions
- `pipeline_reporter`: writes the final go/no-go report

Outputs:

```text
2-RagIngestion-Pipeline/03-preprocessed/processed_{run_id}.jsonl
2-RagIngestion-Pipeline/03-preprocessed/crew-report_{run_id}.md
```

Example:

```bash
python3 -m crewai_mlops.rag_ingestion.main run --category compliance
python3 -m crewai_mlops.rag_ingestion.main run --dry-run
```

API:

```bash
curl -X POST http://localhost:8002/run/rag-prep \
  -H 'Content-Type: application/json' \
  -d '{"category": "compliance", "dry_run": false}'
```

### 2. BERU Audit and Governance Crews

Package: `crewai_mlops.beru`

Turns compliance review playbooks into CrewAI workflows for BERU-AI.

Core workflows:

- `beru_audit.py`: triage a finding and produce a structured audit finding
- `ssp_to_poam.py`: review SSP text, assess gaps, draft SAR language, and generate POA&M items

Specialized governance workflows under `beru/crews/`:

| Workflow | Focus |
|---|---|
| `ac-access-control` | NIST 800-53 AC-2, AC-3, AC-6, AC-17 access control review |
| `ai-safety-m23-07` | AI safety review mapped to OMB M-23-07 / EO 14110 style evidence |
| `au-logging-maturity` | Logging maturity and event visibility review |
| `icam-m24-04` | ICAM and phishing-resistant MFA evidence review |
| `zt-zero-trust` | Zero Trust evidence review across major pillars |
| `cmmc-level2` | CMMC Level 2 evidence collection and gap review |

Example:

```bash
python3 -m crewai_mlops.beru.main audit \
  "AC-6 violation: service account has cluster-admin binding"

python3 -m crewai_mlops.beru.main ssp path/to/ssp.txt "System Name" path/to/findings.txt
```

API:

```bash
curl -X POST http://localhost:8089/run/beru-audit \
  -H 'Content-Type: application/json' \
  -d '{"finding": "AC-6 violation: service account has cluster-admin binding"}'
```

### 3. Synthetic Training Data Pipeline Crew

Package: `crewai_mlops.synthetic_pipeline`

Turns operational security findings into reviewable training-data generation runs.

The crew covers:

- source discovery
- example generation
- quality validation
- coverage analysis
- go/no-go recommendation for corpus inclusion

Example:

```bash
python3 -m crewai_mlops.synthetic_pipeline.main run --min-quality 60
```

API:

```bash
curl -X POST http://localhost:8001/run/synthetic-pipeline \
  -H 'Content-Type: application/json' \
  -d '{"min_quality_score": 60, "max_examples": 500}'
```

## Package Layout

```text
10-crewai-mlops/
  pyproject.toml
  requirements.txt
  README.md
  LINKEDIN-NARRATIVE.md
  __init__.py

  rag_ingestion/
    main.py
    collectors.py
    agents.py
    tools.py
    crews/prep_crew.py

  beru/
    main.py
    agents.py
    config_loader.py
    llm-config.yaml
    crews/
      beru_audit.py
      ssp_to_poam.py
      ac-access-control/
      ai-safety-m23-07/
      au-logging-maturity/
      icam-m24-04/
      zt-zero-trust/
      cmmc-level2/

  synthetic_pipeline/
    main.py
    agents.py
    tools.py
    crews/pipeline_crew.py
```

## Install Locally

From this directory:

```bash
python3 -m pip install -e .
```

Then run:

```bash
python3 -m crewai_mlops.rag_ingestion.main run --dry-run
python3 -m crewai_mlops.beru.main audit "test finding"
python3 -m crewai_mlops.synthetic_pipeline.main run --min-quality 60
```

Or use the installed console scripts:

```bash
gp-crewai-rag-prep run --dry-run
gp-crewai-beru audit "AC-6 violation: service account has cluster-admin binding"
gp-crewai-synthetic run --min-quality 60
```

## Output Contracts

BERU audit outputs are expected to match the Pydantic models in
`beru/schemas.py`. The core contract is:

```text
AuditFinding
  finding
  control_id + control_name
  ai_rmf_subcategory
  status + determination
  evidence_reviewed[]
  evidence_gap
  likelihood + impact -> rank
  control_owner
  poam_item
  ciso_summary
```

This is the current review boundary: agents may draft the content, but outputs
should be validated against a schema before they are trusted by downstream GRC
workflows.

## LLM Configuration

All crews read `CREWAI_LLM` from the environment.

Default:

```bash
CREWAI_LLM=ollama/llama3.2
```

Example with a hosted model:

```bash
CREWAI_LLM=claude-3-5-haiku-20241022 python3 -m crewai_mlops.rag_ingestion.main run
```

## Portfolio Positioning

This is an applied AI engineering project, not a toy chatbot.

It demonstrates:

- converting written governance playbooks into runnable workflows
- separating deterministic evidence collection from LLM judgment
- using CrewAI for review, classification, and reporting
- integrating RAG ingestion, model operations, and GRC workflows
- keeping human-in-the-loop review as part of the design

## Current Maturity

This is ready for engineering critique as a working prototype. The pieces worth
reviewing first are the collector/agent split, the BERU output schema, and the
RAG ingestion prep workflow.

Known cleanup areas:

- add schema validation directly to every crew result before returning from APIs
- add golden-output evals for SAR/POA&M quality
- version every run with corpus, model, prompt, and collector commit metadata
- keep package metadata aligned with the CrewAI version used in local/CI runs

The project is still evolving. The next improvements are stronger tests, cleaner packaging for every sub-crew, corpus/run versioning, and more evaluation around agent output quality.
