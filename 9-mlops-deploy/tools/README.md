# 9-MLOPS-DEPLOY Tools

Master orchestration scripts. These call into domain directories — no business logic here.

## Scripts

| Script | What It Does |
|--------|-------------|
| `run-ml-audit.sh` | Assess current ML infrastructure — inventory models, check maturity |
| `deploy-kubeflow.sh` | Deploy KFP standalone on K8s (MySQL + S3) |
| `deploy-kserve.sh` | Deploy KServe + vLLM + KEDA on K8s |
| `train-eval-promote.sh` | Submit KFP training pipeline, wait for completion |
| `validate-training-data.py` | Data quality gates (format, scope, dedup, content) |
| `generate-compliance-report.sh` | Full lifecycle report (lineage, provenance, eval, infra) |
| `deploy-sagemaker-training.py` | Launch SageMaker training job |
| `setup-sagemaker.sh` | Configure SageMaker IAM roles and S3 buckets |
| `sagemaker-lifecycle.py` | SageMaker model lifecycle management |

## Usage

```bash
# Full audit
bash tools/run-ml-audit.sh --target /path/to/ml-project

# Deploy Kubeflow track
bash tools/deploy-kubeflow.sh --namespace mlops
bash tools/deploy-kserve.sh --namespace kserve

# Train cycle (submits to KFP)
bash tools/train-eval-promote.sh --model katie-3b --data s3://bucket/corpus.jsonl

# SageMaker track
bash tools/setup-sagemaker.sh
python3 tools/deploy-sagemaker-training.py --model katie-3b --data s3://bucket/corpus.jsonl
```
