# GP-MODEL-OPS

[![CI](https://github.com/jimjrxieb/MLOPS-project/actions/workflows/ci.yml/badge.svg)](https://github.com/jimjrxieb/MLOPS-project/actions/workflows/ci.yml)

I'm building AI agents tailored to GRC — the unglamorous but necessary work of mapping findings to NIST controls, drafting POA&M items, and producing evidence that holds up in front of a 3PAO. This repo is the training lab. It's where the models get built, evaluated, and promoted to the serving layer.

Fourteen experiments in. Still iterating. The gates are real.

---

## What's Here

A full MLOps pipeline for three AI agents — BERU, JADE, and Katie — plus the CrewAI crews that automate the data work:

```
0-data-lab/          ← Raw data. CI evidence, Claude Code sessions, synthetic generation.
1-local-pipeline/    ← Training engine. ETL → chunk → LoRA fine-tune → merge → GGUF.
2-rag-ingestion/     ← RAG pipeline. 7-stage prep factory → ChromaDB (33k+ docs).
3-model-registry/    ← Artifact store. Weights, GGUFs, Modelfiles per version.
4-eval-clarify/      ← Eval suites. knowledge-brain, pentest-brain, workflow-brain.
5-experiments/       ← 14 tracked experiments. params.yaml + metrics.json + notes.md each.
6-model-cards/       ← Model governance. Champion/challenger docs.
7-data-schemas/      ← Data contracts. JSON Schema for training + eval formats.
8-tests/             ← Quality gates. pytest runs in CI before any build.
10-crewai-mlops/     ← CrewAI crews. 3 production crews, one architectural pattern.
BERU-AI/             ← The running system. FastAPI + Docker + MLflow tracking.
CAPSTONE-PROJECT/    ← Design decisions, NIST AI RMF frameworks, intake templates.
```

---

## Pipeline

```
Raw data (0-data-lab)
    │
    ▼
ETL + chunk (1-local-pipeline)  ──► Data quality gate (8-tests/)
    │
    ▼
LoRA fine-tune on RTX 5080      ──► Hyperparams + metrics → MLflow (5-experiments/)
    │
    ▼
Merge + GGUF (3-model-registry)
    │
    ▼
Eval: knowledge-brain + pentest-brain (4-eval-clarify/)
    │
    ▼
Promotion gate (≥70% KB, ≥70% PB) ──► PASS: ollama create beru:latest
                                   ──► FAIL: notes.md → back to ETL
    │ (on pass)
    ▼
BERU-AI/  ──► FastAPI serving + MLflow inference tracking + drift monitoring
```

RAG path runs in parallel:

```
docs → 2-rag-ingestion/02-preperation-factory/ (7 stages)
     → 10-crewai-mlops/rag_ingestion/ (4 LLM agents: quality, labeling, routing, report)
     → 03-preprocessed/ → 04-ingesting/ingest_to_chromadb.py → ChromaDB
```

---

## The CrewAI Architecture

The `10-crewai-mlops/` package holds three production crews. The pattern across all three is the same: **deterministic Python does the collection, LLM agents do the judgment**.

```
collectors.py   ← pure Python, no LLM, reads files + runs pipeline stages
      ↓
CrewAI agents   ← quality review, semantic labeling, routing decisions, reporting
      ↓
output files    ← processed JSONL + markdown report
```

This keeps token cost low, failures diagnosable, and agents focused on what they're actually good at.

| Crew | Purpose | Port |
|------|---------|------|
| `synthetic_pipeline` | Convert JSA findings to ChatML training examples | 8001 |
| `beru` | NIST 800-53 audit sub-crews (beru_audit, ssp_to_poam, ac-access-control) | 8089 |
| `rag_ingestion` | Quality-review + label + route RAG prep batches | 8002 |

See [`10-crewai-mlops/README.md`](10-crewai-mlops/README.md) for the full architecture.

---

## Models

| Model | Base | Domain | Current Status |
|-------|------|--------|---------------|
| **BERU** | Llama 3.2-3B | NIST 800-53 + AI RMF GRC analyst | exp-014: KB 20% / PB 68.2% — blocked at 70% gate |
| **JADE** | Llama 3.1-8B | DevSecOps — Code + Cluster phases | Checkpoint v1.1, serving via Ollama |
| **Katie** | Llama 3.2-3B | K8s ops — CKS/CKA/CKAD/CNPA/OPS | Deployed |

**BERU promotion gate:** ≥70% knowledge brain + ≥70% pentest brain. Per-type floor: 60%.  
14 experiments completed. Current gap is `dual_citation` (0%) and `tool_output_interpretation` (20%) — the next training corpus targets these specifically.

---

## CI Pipeline

Three jobs on every push to `main`:

| Job | What it checks | OWASP LLM |
|-----|---------------|-----------|
| `secret-scan` | gitleaks — full git history | LLM02 |
| `test` | pip-audit + pytest (89 tests) | LLM03, LLM04, LLM05, LLM06 |
| `build` | docker build + trivy + smoke test | LLM03 |

---

## Key Files

| File | Purpose |
|------|---------|
| `beru_pipeline.py` | E2E orchestrator: validate → train → eval → promote → registry |
| `BERU-AI/mlops/training_tracker.py` | MLflow training run logger + model registry |
| `BERU-AI/mlops/inference_tracker.py` | Per-call inference logging (latency, findings, rank) |
| `5-experiments/COMPARISON.md` | Side-by-side of all 14 experiments |
| `10-crewai-mlops/README.md` | CrewAI crew architecture + entry points |
| `.github/workflows/ci.yml` | CI pipeline with OWASP LLM Top 10 mapping |

---

## Quick Start

```bash
# Validate training data before any run
python3 -m pytest 8-tests/test_beru_data_quality.py -v

# Run the E2E pipeline
python3 beru_pipeline.py --help

# Check experiment history
cat 5-experiments/COMPARISON.md

# RAG ingestion crew
python3 -m crewai_mlops.rag_ingestion.main run --dry-run

# MLflow UI (experiment tracking)
mlflow ui --backend-store-uri file://BERU-AI/mlruns --port 5001
```
