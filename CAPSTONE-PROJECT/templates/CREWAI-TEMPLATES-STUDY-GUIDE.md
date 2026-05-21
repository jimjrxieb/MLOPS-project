# CrewAI Templates Study Guide

These templates are based on the CrewAI workflows actually built in
`10-crewai-mlops/`.

The pattern is:

```text
deterministic Python gathers state
        |
        v
CrewAI agents make review/judgment calls
        |
        v
structured output or state-file overrides
```

Use these when you need to build a new crew without starting from scratch.

## Template 1 — BERU Audit Crew

File: `crewai_beru_audit_template.py`

Use this when the workflow is:

```text
raw finding -> triage -> GRC assessment -> POA&M/CISO summary
```

This mirrors:

- `10-crewai-mlops/beru/agents.py`
- `10-crewai-mlops/beru/crews/beru_audit.py`

Best for:

- scanner finding review
- NIST 800-53 mapping
- POA&M drafting
- CISO summary drafting
- using BERU API as a tool

Run:

```bash
export CREWAI_LLM=ollama/llama3.2
export OLLAMA_BASE_URL=http://localhost:11434
export BERU_API_URL=http://localhost:8088

python3 CAPSTONE-PROJECT/templates/crewai_beru_audit_template.py \
  "AC-6 violation: service account has cluster-admin binding"
```

## Template 2 — State File Review Crew

File: `crewai_statefile_review_template.py`

Use this when deterministic Python already wrote a JSON state file and agents
need to review it.

This mirrors:

- `10-crewai-mlops/rag_ingestion/tools.py`
- `10-crewai-mlops/rag_ingestion/crews/prep_crew.py`

Best for:

- RAG ingestion review
- data-quality review
- semantic labeling
- routing validation
- go/no-go reporting

Run:

```bash
export CREWAI_LLM=ollama/llama3.2
python3 CAPSTONE-PROJECT/templates/crewai_statefile_review_template.py --make-sample
python3 CAPSTONE-PROJECT/templates/crewai_statefile_review_template.py \
  --state-file /tmp/crewai-state-template/state.json
```

## Template 3 — FastAPI Crew Service

File: `crewai_fastapi_service_template.py`

Use this when you want to wrap a crew in an HTTP service.

This mirrors:

- `10-crewai-mlops/beru/main.py`
- `10-crewai-mlops/rag_ingestion/main.py`

Best for:

- n8n integration
- API-triggered agent workflows
- demo services
- repeatable local endpoints

Run:

```bash
export CREWAI_LLM=ollama/llama3.2
cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/CAPSTONE-PROJECT/templates
uvicorn crewai_fastapi_service_template:app \
  --host 0.0.0.0 \
  --port 8090
```

Then:

```bash
curl -X POST http://localhost:8090/run/audit \
  -H 'Content-Type: application/json' \
  -d '{"finding": "SI-2 gap: no patch SLA evidence provided"}'
```

## Design Rules

1. Keep deterministic collection outside the LLM.
2. Give each agent one job.
3. Keep each agent to one or two tools unless there is a good reason.
4. Pass large batches through files, not prompt context.
5. Make the expected output schema explicit.
6. Route high-risk or low-confidence outputs to human review.
7. Add a dry-run or sample-state path so the crew can be tested without real data.

## Quick Dependency Install

From `10-crewai-mlops/`:

```bash
python3 -m pip install -e .
```

Or standalone:

```bash
python3 -m pip install 'crewai[tools]==0.186.1' fastapi uvicorn httpx pydantic
```
