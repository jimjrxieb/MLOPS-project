# BERU Demo Runbook

This is the reviewer-facing path. It shows the project as an implemented
AI/MLOps system without overstating model maturity.

## 1. Inspect The Architecture

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS

sed -n '1,220p' BERU-AI/README.md
sed -n '1,220p' 10-crewai-mlops/README.md
sed -n '1,180p' BERU-AI/BERU-COVERAGE.md
```

## 2. Run The Fast Checks

```bash
python3 -m pytest \
  8-tests/test_evidence_guard.py \
  8-tests/test_beru_tools.py \
  8-tests/test_beru_core.py \
  8-tests/test_rag_ingestion_crew.py \
  8-tests/test_crewai_beru_schemas.py \
  -q
```

## 3. Validate The CrewAI CLIs

```bash
cd 10-crewai-mlops

python3 beru/main.py --help
python3 rag_ingestion/main.py --help
python3 synthetic_pipeline/main.py --help
```

## 4. Start The Full BERU Stack

This requires Docker and the local model artifact path referenced by
`BERU-AI/docker-compose.yml`.

```bash
cd ../BERU-AI
docker compose up --build
```

Expected services:

| Service | URL |
|---|---|
| BERU API | `http://localhost:8088/docs` |
| CrewAI BERU service | `http://localhost:8089/docs` |
| n8n workflow UI | `http://localhost:5678` |
| Ollama | `http://localhost:11434` |

## 5. What To Show In Five Minutes

1. `BERU-AI/agent/graph.py` for the LangGraph control flow.
2. `BERU-AI/BERU-COVERAGE.md` for honest control-family coverage.
3. `5-experiments/COMPARISON.md` for the model promotion gate and blocked runs.
4. `10-crewai-mlops/beru/schemas.py` for structured BERU output contracts.
5. `BERU-AI/docker-compose.yml` for the deployed stack.

## Positioning

The correct claim is:

> BERU is a guarded GRC analyst assistant with real MLOps scaffolding,
> evidence-oriented workflows, and explicit promotion gates. The architecture is
> reviewable today; the model remains below autonomous promotion threshold.

Do not claim BERU is production-approved or 3PAO-equivalent.
