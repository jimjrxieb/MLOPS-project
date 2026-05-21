# 9-mlops-deploy — MLOps Operational Toolkit

Deployment scripts, GitHub Actions workflows, and monitoring setup for production MLOps pipelines. Battle-tested on BERU (3B GRC analyst), JADE (8B DevSecOps), and Katie (3B K8s engineer) trained on this repo's pipeline.

Covers the operational half of the model lifecycle: submit training runs, enforce data quality gates, detect drift, and roll out new model versions with promotion gates.

---

## What's Here

```
9-mlops-deploy/
├── tools/                         ← Deployment and orchestration scripts
│   ├── run-ml-audit.sh            ← Assess current ML infrastructure maturity
│   ├── deploy-kubeflow.sh         ← KFP standalone on K8s (MySQL + S3)
│   ├── deploy-kserve.sh           ← KServe + vLLM + KEDA on K8s
│   ├── train-eval-promote.sh      ← Submit KFP pipeline, wait, check gate
│   ├── validate-training-data.py  ← Data quality gates (format, scope, dedup)
│   ├── generate-compliance-report.sh  ← Lineage + provenance + eval history
│   ├── deploy-sagemaker-training.py   ← SageMaker training job launcher
│   ├── setup-sagemaker.sh         ← SageMaker IAM roles + S3 buckets
│   └── sagemaker-lifecycle.py     ← SageMaker model lifecycle management
├── 06-model-cicd/
│   └── github-actions/
│       ├── validate-training-data.yml  ← Gate on data pushes
│       ├── train-eval-promote.yml      ← Full training cycle (chained from validate)
│       └── weekly-eval.yml             ← Scheduled eval against production model
├── 07-monitoring/
│   └── drift-detection/
│       ├── servicemonitor.yaml    ← Prometheus ServiceMonitor for ML metrics
│       └── compare-eval.py        ← Compare current eval scores against baseline
├── examples/
│   ├── katie-training-cycle.md    ← Complete Katie v2 training lifecycle (reference)
│   └── jade-rag-ingestion.md      ← JADE RAG pipeline: 33k+ docs, 7 collections
├── outputs/                       ← Where audit results land (gitignored in client repos)
├── ENGAGEMENT-GUIDE.md            ← 6-phase engagement playbook
└── README.md                      ← You are here
```

---

## Two Infrastructure Tracks

| | Kubeflow (K8s-native) | SageMaker (AWS-managed) |
|---|---|---|
| **Pipeline orchestration** | KFP v2 | SageMaker Pipelines |
| **Experiment tracking** | KFP experiments + artifacts | SageMaker Experiments |
| **Model registry** | S3-based + `registry.json` | SageMaker Model Registry |
| **Model serving** | KServe + vLLM | SageMaker Endpoints |
| **Autoscaling** | KEDA (custom vLLM metrics) | Built-in |
| **Monitoring** | Prometheus + vLLM metrics | SageMaker Model Monitor |
| **Best for** | K8s-native teams, multi-cloud | AWS-native, compliance-required |

---

## MLOps Maturity Model

| Level | Description | How to get there |
|-------|-------------|-----------------|
| **L0 — Manual** | Models trained on laptops, no versioning, manual deployment | `run-ml-audit.sh` to baseline |
| **L1 — Tracked** | Experiment tracking, model registry, manual promotion | `deploy-kubeflow.sh` |
| **L2 — Automated** | KFP pipelines, data quality gates, automated eval | `train-eval-promote.sh` |
| **L3 — CI/CD** | Model CI/CD, automated promotion, canary serving | `06-model-cicd/github-actions/` |
| **L4 — Full Loop** | Drift detection, feedback loops, scheduled retraining | `07-monitoring/drift-detection/` |

---

## Quick Start

```bash
# 1. Assess current ML maturity
bash tools/run-ml-audit.sh --target /path/to/ml-project

# 2. Validate training data before any run
python3 tools/validate-training-data.py --input corpus.jsonl --check all --strict

# 3. Deploy Kubeflow (experiment tracking + pipeline orchestration)
bash tools/deploy-kubeflow.sh --namespace kubeflow

# 4. Submit a training pipeline
bash tools/train-eval-promote.sh \
  --model beru \
  --data s3://bucket/beru-corpus.jsonl \
  --threshold 70

# 5. Deploy KServe + vLLM (model serving)
bash tools/deploy-kserve.sh --namespace kserve
```

---

## Model CI/CD

The GitHub Actions workflows wire data validation into training automatically:

```
Push to data branch
  → validate-training-data.yml (quality gates)
  → IF pass: train-eval-promote.yml submits KFP pipeline
    → IF eval ≥ threshold: model promoted, KServe InferenceService patched
    → IF eval < threshold: GitHub issue opened with per-category breakdown
  → weekly-eval.yml: scheduled eval against production model (drift signal)
```

```bash
# Copy workflows to your repo
cp 06-model-cicd/github-actions/*.yml .github/workflows/
```

---

## Drift Detection

`07-monitoring/drift-detection/` uses Prometheus metrics from vLLM to detect performance degradation:

| Metric | What it signals |
|--------|----------------|
| `ml_eval_score` (Gauge) | Eval benchmark trending down → retrain trigger |
| `ml_data_drift_score` (Gauge) | Input distribution shifted → data collection needed |
| `ml_inference_latency_seconds` | Serving degradation |
| `ml_prompt_category` | Domain shift in production traffic |

```bash
# Compare current eval scores against saved baseline
python3 07-monitoring/drift-detection/compare-eval.py \
  --baseline 5-experiments/exp-015-beru-v1.7/metrics.json \
  --current 4-eval-clarify/3-results/beru/knowledge_brain/latest.json
```

---

## Related

| Directory | What it feeds |
|-----------|--------------|
| `0-data-lab/` | Raw training data — input to `validate-training-data.py` |
| `1-FineTuning-Pipeline/` | ETL → train → merge → GGUF — what KFP wraps |
| `4-eval-clarify/` | Eval suites — what promotion gates run |
| `5-experiments/` | Per-run metrics — baseline for `compare-eval.py` |
| `BERU-AI/` | FastAPI runtime — what KServe/Ollama serves |
