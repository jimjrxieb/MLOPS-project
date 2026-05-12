# Playbook 14 — SageMaker Training Jobs

> Run LoRA fine-tuning on SageMaker instead of a persistent GPU node.
> **When:** Client wants on-demand GPU without managing infrastructure
> **Time:** 2-3 hours setup, then per-run

---

## Prerequisites

- [ ] SageMaker execution role with S3 access
- [ ] Training data in S3 (or upload during job)
- [ ] Training script (your existing `train_v11.py` works)

---

## Why SageMaker Training Jobs

```
Self-hosted GPU node:
  - Pay 24/7 even when idle ($730/month for g5.xlarge on-demand)
  - You manage the instance, drivers, CUDA, disk

SageMaker Training Job:
  - Pay only during training (~$1/hr for ml.g5.xlarge)
  - Instance spins up, trains, saves checkpoint to S3, shuts down
  - No GPU management
```

For a 3B LoRA fine-tune that takes 2 hours: **$2 per run vs $730/month**.

---

## Phase 1: Package Your Training Script

SageMaker runs your script in a container. Minimal changes needed:

```python
# train_sagemaker.py — wrapper around your existing train_v11.py
import os
import json

# SageMaker passes paths via environment variables
training_data = os.environ.get("SM_CHANNEL_TRAINING", "/opt/ml/input/data/training")
model_output = os.environ.get("SM_MODEL_DIR", "/opt/ml/model")
hyperparams_file = os.environ.get("SM_HPS", "{}")

# Load hyperparameters (SageMaker passes these as a JSON file)
hyperparams = json.loads(os.environ.get("SM_HPS", "{}"))
print(f"Hyperparameters: {hyperparams}")

# Your existing training logic
# Just change the input/output paths to use the SM_ variables
```

---

## Phase 2: Launch Training Job

```python
from sagemaker.huggingface import HuggingFace

estimator = HuggingFace(
    entry_point="train_sagemaker.py",
    source_dir="./src",
    instance_type="ml.g5.xlarge",        # 1x A10G, 24GB VRAM
    instance_count=1,
    role="arn:aws:iam::123456789:role/SageMakerTrainingRole",
    transformers_version="4.37",
    pytorch_version="2.1",
    py_version="py310",
    hyperparameters={
        "model_name": "unsloth/Llama-3.2-3B-Instruct",
        "lora_r": 64,
        "lora_alpha": 128,
        "epochs": 2,
        "batch_size": 4,
        "learning_rate": "2e-5",
    },
    output_path="s3://your-bucket/model-output/",
    max_run=7200,                         # 2 hour timeout
    use_spot_instances=True,              # 60-70% savings
    max_wait=10800,                       # Wait up to 3hr for spot
    checkpoint_s3_uri="s3://your-bucket/checkpoints/",  # Resume on spot interruption
)

# Upload training data and start job
estimator.fit({
    "training": "s3://your-bucket/training-data/katie_v2_clean.jsonl"
})
```

---

## Phase 3: Spot Instance Strategy

```python
# Spot saves 60-70% but can be interrupted
# SageMaker auto-resumes from checkpoint on interruption

use_spot_instances=True,
max_wait=10800,                          # 3hr max wait for spot
checkpoint_s3_uri="s3://your-bucket/checkpoints/",
checkpoint_local_path="/opt/ml/checkpoints",

# In your training script, save checkpoints frequently:
# trainer.save_checkpoint(f"/opt/ml/checkpoints/chunk_{i}")
```

**Cost comparison (3B LoRA, 2 hours):**

| Instance | On-demand | Spot | Savings |
|----------|-----------|------|---------|
| ml.g5.xlarge (A10G 24GB) | $1.41/hr = $2.82 | $0.50/hr = $1.00 | 65% |
| ml.g5.2xlarge (A10G 24GB, more CPU) | $1.69/hr = $3.38 | $0.60/hr = $1.20 | 65% |

---

## Phase 4: Retrieve Model

```bash
# Download trained model from S3
aws s3 sync s3://your-bucket/model-output/model/ ./model-output/

# Convert to GGUF (locally — GGUF conversion doesn't need GPU)
python3 1-data-pipeline/convert_gguf.py --model-path ./model-output/

# Upload to S3 for KServe serving
aws s3 sync ./model-output/ s3://ml-artifacts/models/katie-3b/v2.0/
```

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| Training job works | `15-sagemaker-model-registry.md` |
| Need eval after training | `07-setup-model-eval.md` (same eval, different training backend) |
| Need to optimize cost | `11-optimize-ml-costs.md` |
