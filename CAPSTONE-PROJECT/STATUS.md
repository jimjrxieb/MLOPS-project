# BERU Capstone Status

> Current operating position: credible working prototype, not a promoted autonomous
> compliance model.

## Executive Summary

BERU is a GRC analyst model and workflow system for evidence-based compliance
review. It combines:

- a local LLaMA 3.2-3B BERU model served through Ollama
- RAG over NIST 800-53, NIST AI RMF, and MITRE ATLAS knowledge
- LangGraph orchestration for BERU runtime assessment paths
- CrewAI workflows for governance review, SSP-to-POA&M, and RAG prep
- FastAPI serving, Docker Compose, MLflow tracking, and CI quality gates
- HITL routing for B/S-rank findings and guard-triggered outputs

The engineering system is real and reviewable. The model is still below the
promotion gate and should be presented as a guarded analyst assistant, not an
autonomous 3PAO replacement.

## Current Model Position

| Area | Status |
|---|---|
| Champion | `beru:v1.6` operating reference in model cards and coverage docs |
| Challenger | `beru:v1.7`, not promoted |
| Promotion gate | >=70% knowledge brain and >=70% pentest brain, 60% per-type floor |
| Current gap | dual citation, ATLAS-mapped AI risk, and evidence-gap accuracy |
| Current use | assisted drafting, review, evidence structuring, HITL-routed findings |

## Implemented Evidence

| Capability | Evidence |
|---|---|
| Agent orchestration | `BERU-AI/agent/graph.py`, `BERU-AI/agent/nodes.py` |
| API serving | `BERU-AI/api/main.py`, `BERU-AI/api/routes.py` |
| Container stack | `BERU-AI/docker-compose.yml`, `BERU-AI/Dockerfile` |
| CrewAI workflows | `10-crewai-mlops/README.md`, `10-crewai-mlops/beru/` |
| RAG and knowledge | `BERU-AI/knowledge/`, `2-RagIngestion-Pipeline/` |
| Eval history | `5-experiments/COMPARISON.md` |
| Coverage map | `BERU-AI/BERU-COVERAGE.md` |
| Training tracking | `BERU-AI/mlops/training_tracker.py` |
| Inference tracking | `BERU-AI/mlops/inference_tracker.py` |
| Quality gates | `8-tests/`, `.github/workflows/ci.yml` |

## Honest Limitations

- The model has not passed the promotion gate.
- Per-family eval evidence is strongest for access-control-style SSP grading.
- Dual-framework citation is partially learned but not reliable enough to promote.
- Some CrewAI workflows are working prototypes and still need schema validation
  on returned agent outputs.
- Full end-to-end model execution depends on Ollama and the registered BERU model
  being available locally.

## Next Engineering Target

exp-016 should focus on:

1. Dual-citation examples that pair NIST 800-53 controls with AI RMF subcategories.
2. MITRE ATLAS scenario coverage for AI-specific adversarial risk.
3. Golden-output evals for SAR and POA&M quality.
4. Schema validation before CrewAI API responses are trusted downstream.
