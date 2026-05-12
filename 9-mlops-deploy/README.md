# 9-MLOPS-DEPLOY

> End-to-end MLOps pipeline deployment — from training data to production model serving.

---

## What This Package Does

Deploys a production-grade MLOps platform. Two tracks: **Kubeflow** (K8s-native, portable) and **SageMaker** (AWS-managed). Covers the full model lifecycle: data quality gates, KFP training pipelines, model registry, KServe serving, evaluation benchmarks, and model CI/CD. Battle-tested on JADE (8B) and Katie (3B) — two LLaMA models serving autonomous security remediation in production.

| Metric | Impact |
|--------|--------|
| Training pipeline automation | 7-step KFP pipeline — validate to promote in one command |
| Data quality enforcement | 300k examples curated to 44k (85% garbage removed) |
| Model promotion gates | Zero untested models reach production |
| RAG knowledge base | 33k+ documents across 7 collections |
| Model serving | Sub-second inference via KServe + vLLM on K8s |
| Experiment reproducibility | Every run tracked — KFP artifacts, metrics, lineage |

---

## What's Included

```
9-MLOPS-DEPLOY/
├── README.md                      ← You are here
├── ENGAGEMENT-GUIDE.md            ← Agent brain — phases, timelines, decisions
├── playbooks/                     ← 17 numbered playbooks (Kubeflow + SageMaker tracks)
│   └── README.md
├── tools/                         ← Deployment and orchestration scripts
│   └── README.md
├── 01-kubeflow-platform/          ← KFP + KServe deployment manifests
│   ├── manifests/                 ← Helm values (KFP standalone, KServe standalone)
│   └── kfp-components/            ← Reusable pipeline components
├── 02-training-pipeline/          ← Training configs + KFP pipeline definitions
│   ├── configs/
│   ├── kfp/                       ← KFP v2 training pipeline Python code
│   └── sagemaker/
├── 03-model-registry/             ← Model versioning + Modelfile templates
│   └── templates/
├── 04-model-serving/              ← KServe + vLLM serving configs
│   ├── kserve/                    ← InferenceService, ServingRuntime, KEDA
│   └── vllm/
├── 05-rag-pipeline/               ← ChromaDB + embedding configs
│   └── configs/
├── 06-model-cicd/                 ← GitHub Actions for model lifecycle
│   └── github-actions/
├── 07-monitoring/                 ← Drift detection + dashboards
│   └── drift-detection/
├── examples/                      ← Battle-tested references (Katie, JADE)
└── outputs/                       ← Where audit results land
```

---

## Two Tracks

| | Kubeflow Track (K8s-native) | SageMaker Track (AWS-managed) |
|---|---|---|
| **Pipeline orchestration** | KFP (Kubeflow Pipelines) | SageMaker Pipelines |
| **Experiment tracking** | KFP experiments + artifacts | SageMaker Experiments |
| **Model registry** | S3-based + registry.json | SageMaker Model Registry |
| **Model serving** | KServe + vLLM | SageMaker Endpoints |
| **Autoscaling** | KEDA (custom vLLM metrics) | Built-in |
| **Monitoring** | Prometheus + vLLM metrics | SageMaker Model Monitor |
| **Cost** | Infra-only (self-managed) | Pay per use (managed) |
| **Portability** | Any K8s cluster | AWS only |
| **Best for** | K8s-native teams, multi-cloud | AWS-native, compliance-required |

---

## MLOps Maturity Model

| Level | Description | Playbooks |
|-------|-------------|-----------|
| **L0 — Manual** | Models trained on laptops, no versioning, manual deployment | 01 (assess) |
| **L1 — Tracked** | Experiment tracking, model registry, manual promotion | 02, 03, 05 |
| **L2 — Automated** | KFP pipelines, data quality gates, automated eval | 03, 04, 07 |
| **L3 — CI/CD** | Model CI/CD, automated promotion, canary serving | 09, 10 |
| **L4 — Full Loop** | Drift detection, feedback loops, self-healing retraining | 10, 11, 12 |

---

## Quick Start (Docker Desktop + WSL2)

```bash
# 1. Deploy KFP (experiment tracking + pipeline orchestration)
bash tools/deploy-kubeflow.sh --namespace kubeflow

# 2. Verify KFP
kubectl port-forward svc/ml-pipeline-ui -n kubeflow 8888:80
# → http://localhost:8888

# 3. GPU setup (one-time — see 01-kubeflow-platform/README.md)
#    - Install nvidia-container-toolkit in WSL2
#    - Set default-runtime: nvidia in Docker Desktop → Settings → Docker Engine
#    - Apply & Restart

# 4. Submit training pipeline
kubectl port-forward svc/ml-pipeline -n kubeflow 8887:8888
python3 02-training-pipeline/kfp/training_pipeline.py --submit \
  --endpoint http://localhost:8887

# 5. Or train locally (hybrid — local GPU, KFP for tracking)
python3 1-data-pipeline/train_llama3b.py --version v2.0-3b --skip-eval
```

## Quick Start (EKS + Karpenter)

```bash
# 1. Deploy KFP
bash tools/deploy-kubeflow.sh --namespace kubeflow

# 2. Deploy NVIDIA device plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.17.0/deployments/static/nvidia-device-plugin.yml

# 3. Deploy KServe + vLLM (model serving)
bash tools/deploy-kserve.sh --namespace kserve

# 4. Submit training pipeline (Karpenter provisions spot GPU on demand)
python3 02-training-pipeline/kfp/training_pipeline.py --submit \
  --endpoint http://kfp.kubeflow.svc:8888 \
  --model katie-3b
```

---

## Current Deployment (Mar 2026)

Deployed on Docker Desktop K8s (v1.34.1) + WSL2 + RTX 5080 (16GB).

| Component | Status | Namespace |
|-----------|--------|-----------|
| KFP v2.16.0 (14 pods) | Running | `kubeflow` |
| SeaweedFS (S3-compatible) | Running | `kubeflow` |
| Model registry (registry.json) | Deployed | `ml-artifacts` bucket |
| Training pipeline | Compiled + tested | KFP experiment `katie-3b-training` |
| Data quality gates | Validated (33k examples) | `validate-training-data.py` |
| GPU passthrough | Working | `default-runtime: nvidia` |
| Katie v2.0-3b | 2/5 chunks trained (20k examples) | `3-model-registry/v2.0-3b/` |

---

## Related Packages

| Package | When to Use |
|---------|-------------|
| 00-PLATFORM-SETUP | Cluster + ArgoCD must exist before deploying MLOps infra |
| 02-CLUSTER-HARDEN | Harden the cluster before serving models |
| 04-OPTIMIZE | Right-size GPU nodes, Karpenter for ML workloads |
| 06-JADE-INTELLIGENCE | JADE AI system that this pipeline trains and serves |

---

*Ghost Protocol — MLOps / Model Lifecycle Management*
