# GP-MODEL-OPS

[![CI](https://github.com/jimjrxieb/MLOPS-project/actions/workflows/ci.yml/badge.svg)](https://github.com/jimjrxieb/MLOPS-project/actions/workflows/ci.yml)

I'm building AI agents tailored to GRC — the unglamorous but necessary work of mapping findings to NIST controls, drafting POA&M items, and producing evidence that holds up in front of a 3PAO. This repo is the training lab. It's where the models get built, evaluated, and promoted to the serving layer.

Fifteen experiments in. Still iterating. The gates are real.

---

## What's Here

A full MLOps pipeline for three AI agents — BERU, JADE, and Katie — plus the CrewAI crews that automate the data work:

```text
0-data-lab/          ← Raw data. CI evidence, Claude Code sessions, synthetic generation.
1-FineTuning-Pipeline/  ← Training engine. ETL → chunk → LoRA fine-tune → merge → GGUF.
2-RagIngestion-Pipeline/ ← RAG pipeline. 7-stage prep factory → ChromaDB (33k+ docs).
3-model-registry/    ← Artifact store. Weights, GGUFs, Modelfiles per version.
4-eval-clarify/      ← Eval suites. knowledge-brain, pentest-brain, workflow-brain.
5-experiments/       ← 15 tracked experiments. params.yaml + metrics.json + notes.md each.
6-model-cards/       ← Model governance. Champion/challenger docs.
7-data-schemas/      ← Data contracts. JSON Schema for training + eval formats.
8-tests/             ← Quality gates. pytest runs in CI before any build.
10-crewai-mlops/     ← CrewAI crews. 3 production crews, one architectural pattern.
BERU-AI/             ← The running system. FastAPI + LangGraph + Docker + MLflow tracking.
RANK-AI/             ← E/D/C/B/S rank classifier. sklearn model + training data.
CAPSTONE-PROJECT/    ← Design decisions, NIST AI RMF frameworks, intake templates.
```

---

## Pipeline

```text
Raw data (0-data-lab)
    │
    ▼
ETL + chunk (1-FineTuning-Pipeline)  ──► Data quality gate (8-tests/)
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

```text
docs → 2-RagIngestion-Pipeline/02-preperation-factory/ (7 stages)
     → 10-crewai-mlops/rag_ingestion/ (4 LLM agents: quality, labeling, routing, report)
     → 03-preprocessed/ → 04-ingesting/ingest_to_chromadb.py → ChromaDB
```

---

## The CrewAI Architecture

The `10-crewai-mlops/` package holds three production crews. The pattern across all three is the same: **deterministic Python does the collection, LLM agents do the judgment**.

```text
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
| `beru` | 7 NIST 800-53 + federal compliance sub-crews (beru_audit, ssp_to_poam, ac, au, icam, ai-safety, zt) | 8089 |
| `rag_ingestion` | Quality-review + label + route RAG prep batches | 8002 |

See [`10-crewai-mlops/README.md`](10-crewai-mlops/README.md) for the full architecture.

---

## Models

| Model | Role | Champion | Challenger | Gate |
|-------|------|----------|-----------|------|
| **BERU** | NIST 800-53 + AI RMF GRC analyst | v1.6 — KB 20.0% / PB 68.2% | v1.7 (exp-015) — KB 34.1% / PB 63.0% | ≥70% KB + PB, 60% per-type floor |

**15 experiments completed.** v1.7 raised `finding_accuracy` to 48.8% (+8pp) and overall knowledge_brain to 34.1% — a 70% relative gain over v1.6. Remaining gaps: `dual_citation` 24.2% (needs explicit 800-53 ↔ AI RMF pairing examples) and `atlas_mapped_ai_risk` 23.8% (needs MITRE ATLAS technique → control mapping scenarios). exp-016 targets both with dedicated generators and a 5,000+ example corpus.

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
