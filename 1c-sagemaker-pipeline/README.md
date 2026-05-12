# 1c-SageMaker Pipeline

AWS SageMaker managed training for Katie/JADE LoRA fine-tuning. No K8s, no GPU provisioning, no container management.

## Quick Start

```bash
# 1. Upload data + submit training job (spot, cheapest GPU)
python3 submit_training_job.py --chunk chunk_0005_10k.jsonl --spot --instance ml.g4dn.xlarge -y

# 2. Monitor
aws sagemaker describe-training-job --training-job-name <job-name> --query 'TrainingJobStatus'

# 3. Download model artifacts
aws s3 cp s3://<bucket>/katie-training/output/<job-name>/output/model.tar.gz ./
```

## Cost

| Instance | On-Demand | Spot (~70% off) | Time for 3K examples |
|----------|-----------|-----------------|----------------------|
| `ml.g4dn.xlarge` (T4 16GB) | $0.74/hr | ~$0.25/hr | ~30 min |
| `ml.g5.xlarge` (A10G 24GB) | $1.41/hr | ~$0.50/hr | ~20 min |

**Total cost per chunk: $0.10-0.25 with spot.** Full 5-chunk training: $1-3.

## Files

```
1c-sagemaker-pipeline/
├── submit_training_job.py   ← Uploads data, submits SageMaker job
├── train_sagemaker.py       ← Training script (runs inside SageMaker container)
├── config.yaml              ← Hyperparameters
├── jobs/                    ← Job metadata (auto-created per run)
└── README.md                ← You are here
```

## How It Works

```
Local chunk → S3 upload → SageMaker Training Job (GPU) → S3 model artifacts
                                    │
                              HuggingFace DLC + pip install unsloth
                              Spot instances (auto-recovery on interruption)
                              Per-second billing, no idle cost
```

## Options

```bash
# On-demand (no interruption risk, 3x more expensive)
python3 submit_training_job.py --chunk chunk_0005_10k.jsonl

# Spot training (recommended — 60-90% cheaper)
python3 submit_training_job.py --chunk chunk_0005_10k.jsonl --spot

# Cheapest possible
python3 submit_training_job.py --chunk chunk_0005_10k.jsonl --spot --instance ml.g4dn.xlarge

# Background (don't wait for completion)
python3 submit_training_job.py --chunk chunk_0005_10k.jsonl --spot --background

# Resume from checkpoint
python3 submit_training_job.py --chunk chunk_0005_10k.jsonl --checkpoint s3://bucket/path/to/checkpoint
```

## Prerequisites

- AWS credentials configured (`aws sts get-caller-identity` works)
- SageMaker execution role: `AmazonSageMakerAdminIAMExecutionRole`
- S3 bucket: auto-detected from SageMaker session
- `pip install sagemaker boto3`
