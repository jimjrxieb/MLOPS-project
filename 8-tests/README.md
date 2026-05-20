# 8-tests — Quality Gates

pytest suites that run in CI before any build. A training run that hasn't passed data quality validation doesn't happen. A Docker build that hasn't passed schema and behavior tests doesn't ship.

**CI triggers:** every push to `main` via `.github/workflows/ci.yml`

---

## Test Suites

| File | What it guards | When to run |
|------|---------------|------------|
| `test_beru_data_quality.py` | Training corpus format, scope, no garbage | Before every training run |
| `test_data_quality.py` | General data contract (format, dedup, min size) | Before ingestion |
| `test_beru_core.py` | NIST mapper, triage engine, output parser | On BERU-AI/ changes |
| `test_beru_tools.py` | SSP parser, HITL router, evidence packager | On BERU-AI/tools/ changes |
| `test_beru_rag.py` | ChromaDB retrieval, embedding dimensions (768) | On RAG changes |
| `test_beru_evals.py` | Eval runner, scoring logic, result format | On 4-eval-clarify/ changes |
| `test_beru_schemas.py` | JSON Schema validation for BERU findings | On schema changes |
| `test_beru_training_data.py` | BERU-specific ChatML corpus checks | Before BERU training |
| `test_rag_ingestion_crew.py` | CrewAI rag_ingestion crew (collectors, tools, agents) | On 10-crewai-mlops/ changes |
| `test_rank_classifier.py` | E/D/C/B/S rank classifier accuracy | On rank model changes |
| `test_schemas.py` | Training example JSON Schema | On 7-data-schemas/ changes |
| `test_model_behavior.py` | Smoke tests against live Ollama (requires model loaded) | Pre-promotion |
| `test_serving.py` | BERU-AI FastAPI health + endpoint contract | On API changes |
| `test_evidence_guard.py` | Audit trail completeness, no orphaned findings | On compliance changes |

---

## Running Tests

```bash
# Full suite (CI equivalent)
python3 -m pytest 8-tests/ -v

# Data quality gate only (run before every training run)
python3 -m pytest 8-tests/test_beru_data_quality.py -v

# Crew tests (requires 10-crewai-mlops/ importable via conftest.py)
python3 -m pytest 8-tests/test_rag_ingestion_crew.py -v

# Live model tests (requires Ollama running with beru:vX.X loaded)
python3 -m pytest 8-tests/test_model_behavior.py -v
python3 -m pytest 8-tests/test_serving.py -v
```

---

## Import Setup

`conftest.py` registers `10-crewai-mlops/` as the `crewai_mlops` Python package via `importlib`. This is what makes `from crewai_mlops.rag_ingestion.collectors import ...` work in tests despite the directory name starting with a number.

---

## Data Quality Rules (enforced by test_beru_data_quality.py)

1. **Format:** ChatML only. Alpaca rejected.
2. **Scope:** Must match CKS/CKA/CKAD/CNPA/OPS/GRC keywords.
3. **No garbage:** Placeholders, raw JSON logs, nested JSON inception — REJECTED.
4. **No transcripts:** YouTube captions, exam cram dumps — REJECTED.
5. **No filler:** Stubs under 50 chars, definitions without real commands — REJECTED.
6. **Dedup:** Exact duplicates kept to 1. Same response, different phrasing — max 3 variants.
7. **Min size:** Never train on fewer than 500 examples.
8. **Response quality:** Must contain real commands or real YAML, not vague advice.
