# GP-MODEL-OPS — BERU MLOps Repository

End-to-end MLOps for **BERU**, a GRC analyst AI agent that audits NIST 800-53 and AI RMF compliance.  
Built as a capstone targeting MLOps Engineer and AI/ML Platform roles.

---

## The Flow (read the folders in order)

```
0-data-lab/          ← Lab notebook. Raw analysis, CI evidence, synthetic data generation.
1-local-pipeline/    ← Training pipeline. ETL → chunk → LoRA fine-tune → merge → GGUF.
2-rag-ingestion/     ← RAG pipeline. Embed + ingest NIST docs into ChromaDB.
3-model-registry/    ← Artifact store. Weights, GGUFs, Modelfiles per version.
4-eval-clarify/      ← Evaluation. Benchmark suites (knowledge-brain, pentest-brain).
5-experiments/       ← Experiment tracking. params.yaml + metrics.json + notes.md per run.
6-model-cards/       ← Model governance. Champion/challenger documentation.
7-data-schemas/      ← Data contracts. JSON Schema for training + eval formats.
8-tests/             ← Quality gates. pytest suites run in CI before any build.
9-mlops-deploy/      ← Client playbook. How to deploy this pattern at other orgs.

BERU-AI/             ← The running system. FastAPI agent + Docker + MLflow tracking.
CAPSTONE-PROJECT/    ← Design decisions, NIST AI RMF frameworks, intake forms.
```

---

## MLOps Pipeline

```
Raw data (0-data-lab)
    │
    ▼
ETL + chunk (1-local-pipeline)  ──► Data quality gate (8-tests/test_beru_data_quality.py)
    │
    ▼
LoRA fine-tune on RTX 5080       ──► Hyperparams logged to MLflow (5-experiments/)
    │
    ▼
Merge + GGUF (3-model-registry)
    │
    ▼
Eval: knowledge-brain + pentest-brain (4-eval-clarify)
    │
    ▼
Promotion gate                   ──► PROMOTED → Production | BLOCKED → Staging (MLflow registry)
    │
    ▼
ollama create beru:latest        ──► Inference tracking per call (BERU-AI/mlops/)
    │
    ▼
Drift monitoring → feedback_loop.py → back to ETL
```

**Entrypoint:** `python3 beru_pipeline.py --help`

---

## CI Pipeline (`.github/workflows/ci.yml`)

Three jobs on every push to `main`:

| Job | Gate | OWASP LLM |
|-----|------|-----------|
| `secret-scan` | gitleaks — full git history | LLM02 |
| `test` | pip-audit + pytest 89 tests | LLM03, LLM04, LLM05, LLM06 |
| `build` | docker build + trivy + smoke test | LLM03 |

---

## BERU at a Glance

**What it is:** A 3B LoRA-fine-tuned GRC analyst. Given scanner output, it produces structured findings with dual citation (NIST 800-53 control + AI RMF subcategory), POA&M items, and CISO briefings.

**What it is not:** A remediator. BERU assesses and documents. It never fixes, never approves B/S-rank risk acceptances, never escalates above its C-rank authority ceiling.

**Current status:** Pentest brain 81.8% (passes gate). Knowledge brain 13.3% (gate needs 70%). Experiment 12 of N — still training.

**MLflow UI:**
```bash
mlflow ui --backend-store-uri file://BERU-AI/mlruns --port 5001
# Open http://localhost:5001 → beru-training experiment → 9 runs with full metrics
```

---

## Key Files

| File | Purpose |
|------|---------|
| `beru_pipeline.py` | E2E orchestrator: data validate → train → eval → promote → registry |
| `BERU-AI/mlops/training_tracker.py` | MLflow training run logger + model registry operations |
| `BERU-AI/mlops/inference_tracker.py` | Per-call inference logging (latency, findings, rank distribution) |
| `BERU-AI/mlops/backfill_experiments.py` | Load historical experiments into MLflow |
| `5-experiments/COMPARISON.md` | Side-by-side experiment results table |
| `.trivyignore` | Documented CVE suppressions (2 false-positives, 2 deferred upgrades) |

---

## Models

| Model | Base | Domain | Status |
|-------|------|--------|--------|
| BERU | Llama 3.2-3B | NIST 800-53 + AI RMF GRC analyst | Training (exp-012) |
| JADE | Llama 3.1-8B | DevSecOps — Code + Cluster phases | Checkpoint v1.1 |
| Katie | Llama 3.2-3B | K8s ops — CKS/CKA/CKAD/CNPA/OPS | Deployed |
