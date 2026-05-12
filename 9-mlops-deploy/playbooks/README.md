# 9-MLOPS-DEPLOY Playbooks

Two tracks: **Kubeflow** (KFP + KServe on K8s) and **AWS SageMaker** (managed services). Pick one or mix.

## Execution Order

```
ASSESS
  01-assess-ml-maturity              → Baseline current state, score maturity (L0-L4)

FOUNDATION (pick a track)
  Kubeflow:                            AWS SageMaker:
  02a-kubeflow-docker-desktop-setup    (skip if EKS — Docker Desktop + WSL2 only)
  02-deploy-kubeflow (KFP)             13-sagemaker-experiment-tracking
  03-setup-model-registry              15-sagemaker-model-registry
  04-setup-data-quality-gates          04-setup-data-quality-gates (same)

PIPELINE
  05-setup-kfp-pipeline                14-sagemaker-training-jobs
  06-setup-rag-pipeline                06-setup-rag-pipeline (same — RAG is always K8s)
  07-setup-model-eval                  07-setup-model-eval (same)

SERVING
  08-deploy-kserve                     16-sagemaker-endpoints

AUTOMATE
  09-deploy-model-cicd                 09-deploy-model-cicd (same — GHA triggers either)
  10-setup-drift-detection             17-sagemaker-model-monitor

REPORT
  11-optimize-ml-costs                 11-optimize-ml-costs (same)
  12-mlops-compliance-report           12-mlops-compliance-report (same)
```

## Kubeflow Track (01-12)

| Playbook | What |
|----------|------|
| 01 | Assess ML maturity |
| 02 | KFP standalone (pipeline orchestration + experiment tracking) |
| 03 | Model registry (S3-based + promotion workflow) |
| 04 | Data quality gates |
| 05 | KFP training pipeline (7-step: validate → promote) |
| 06 | RAG pipeline (ChromaDB) |
| 07 | Model eval (benchmarks + promotion gates) |
| 08 | KServe + vLLM serving (KEDA autoscaling) |
| 09 | Model CI/CD (GitHub Actions → KFP) |
| 10 | Drift detection (vLLM Prometheus metrics + scheduled eval) |
| 11 | Cost optimization |
| 12 | Compliance report |

## AWS SageMaker Track (13-17)

| Playbook | What | Replaces |
|----------|------|----------|
| 13 | SageMaker Experiments | 02 |
| 14 | SageMaker Training Jobs (on-demand GPU) | 05 |
| 15 | SageMaker Model Registry (approval workflow) | 03 |
| 16 | SageMaker Endpoints (autoscaling inference) | 08 |
| 17 | SageMaker Model Monitor (drift detection) | 10 |

## When to Use Which

| Client situation | Track |
|-----------------|-------|
| K8s-native team, multi-cloud, portability | Kubeflow |
| AWS shop, compliance-required (FedRAMP) | SageMaker |
| Want managed training, K8s serving | Hybrid: 14 (training) + 08 (serving) |
| Small team, cost-sensitive | Kubeflow (no per-use charges) |
