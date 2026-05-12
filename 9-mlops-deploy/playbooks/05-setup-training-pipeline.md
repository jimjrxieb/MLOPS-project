# Playbook 05 — Setup KFP Training Pipeline

> Build the KFP v2 training pipeline: validate → ETL → chunk → train → merge → convert → eval → promote.
> Each step runs in its own container. Artifacts flow automatically. KFP handles caching, lineage, and retry.
> **When:** After data quality gates are in place (Playbook 04)
> **Time:** 4-6 hours

---

## Prerequisites

- [ ] KFP deployed (Playbook 02)
- [ ] Data quality gates passing (Playbook 04)
- [ ] GPU available (Docker Desktop WSL2 with `default-runtime: nvidia`, or EKS with Karpenter)
- [ ] S3 bucket for artifacts and model storage
- [ ] Base model accessible (HuggingFace or S3)

---

## Phase 1: Understand the Pipeline

```
validate_data ──► etl_and_chunk ──► train_lora ──► merge_lora ──► convert_gguf ──► evaluate ──► register
    │                  │                │               │              │              │            │
  FAIL→stop     splits data     GPU pod (LoRA)    CPU pod       CPU pod        FAIL→issue   S3 upload
                 + holdout       via Unsloth     merge weights   to GGUF        PASS→next    + registry
```

Each box is a `@dsl.component` — runs in its own container with its own dependencies. No dependency conflicts between steps.

---

## Phase 2: Review Pipeline Code

The full pipeline is at `02-training-pipeline/kfp/training_pipeline.py`.

**Key parameters (all configurable per run):**

| Parameter | Default | What |
|-----------|---------|------|
| `data_path` | `s3://ml-artifacts/training-data/corpus.jsonl` | Training data location |
| `base_model` | `unsloth/Llama-3.2-3B-Instruct` | Base model for LoRA |
| `lora_r` | 64 | LoRA rank |
| `lora_alpha` | 128 | LoRA alpha |
| `learning_rate` | 2e-4 | Training LR |
| `epochs` | 2 | Epochs per chunk |
| `batch_size` | 4 | Per-device batch size |
| `chunk_size` | 10000 | Examples per chunk |
| `promotion_threshold` | 60.0 | Minimum eval score to promote |

---

## Phase 3: Compile and Upload Pipeline

```bash
cd 02-training-pipeline/kfp/

# Compile pipeline to YAML (can be uploaded via KFP UI)
python3 training_pipeline.py --compile
# → training_pipeline.yaml

# Or submit directly to KFP server
python3 training_pipeline.py --submit \
  --endpoint http://kfp.mlops.svc:8888 \
  --model katie-3b \
  --data s3://ml-artifacts/training-data/katie_v2_clean.jsonl
```

---

## Phase 4: Configure GPU Access

The `train_lora` component needs a GPU. Setup depends on environment.

### Docker Desktop + WSL2 (local dev)

GPU is available to all pods automatically — no resource requests needed.

**Prerequisites (one-time setup):**
1. NVIDIA driver installed on Windows
2. NVIDIA Container Toolkit installed in WSL2:
   ```bash
   sudo apt-get install -y nvidia-container-toolkit
   ```
3. Docker Desktop → Settings → Docker Engine → add to the JSON:
   ```json
   "default-runtime": "nvidia",
   "runtimes": {
     "nvidia": {
       "path": "nvidia-container-runtime",
       "runtimeArgs": []
     }
   }
   ```
4. Apply & Restart Docker Desktop

**Verify:** `docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi`

**Note:** WSL2 uses `/dev/dxg` not `/dev/nvidia*`, so the NVIDIA K8s device plugin won't enumerate GPUs. That's OK — `default-runtime: nvidia` gives every pod GPU access without needing `nvidia.com/gpu` resource requests. Don't bother with the device plugin on WSL2.

### EKS + Karpenter (production)

```yaml
# Karpenter NodePool for training jobs
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-training
spec:
  template:
    spec:
      requirements:
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["g5.xlarge", "g5.2xlarge"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]  # Prefer spot (60-70% savings)
      taints:
        - key: nvidia.com/gpu
          effect: NoSchedule
  limits:
    cpu: 32
    memory: 128Gi
    nvidia.com/gpu: 4
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 5m  # Scale down 5min after training completes
```

Uncomment GPU requests in `training_pipeline.py`:
```python
train_task.set_accelerator_type("nvidia.com/gpu")
train_task.set_accelerator_limit(1)
```

---

## Phase 5: Run Training Pipeline

### Docker Desktop WSL2

```bash
# Port-forward KFP API
kubectl port-forward svc/ml-pipeline -n kubeflow 8887:8888 &
kubectl port-forward svc/ml-pipeline-ui -n kubeflow 8888:80 &

# Upload training data to SeaweedFS
kubectl port-forward svc/seaweedfs -n kubeflow 8333:8333 &
python3 -c "
import boto3
s3 = boto3.client('s3', endpoint_url='http://localhost:8333',
    aws_access_key_id='minio', aws_secret_access_key='minio123', region_name='us-east-1')
s3.upload_file('path/to/chunk.jsonl', 'ml-artifacts', 'training-data/chunk.jsonl')
"

# Submit pipeline
python3 02-training-pipeline/kfp/train_chunk5_kfp.py
# → View at http://localhost:8888/#/runs/details/<run-id>
```

### EKS

```bash
# Submit directly (KFP accessible via cluster DNS)
python3 02-training-pipeline/kfp/training_pipeline.py --submit \
  --endpoint http://kfp.kubeflow.svc:8888 \
  --model katie-3b \
  --data s3://ml-artifacts/training-data/corpus.jsonl
```

**Monitor in KFP UI:**
- Pipeline DAG shows step-by-step progress (download → validate → ETL → train)
- Click any step to see logs, artifacts, metrics
- Validation step shows domain distribution and pass rate
- Training step shows loss, training time, examples trained
- Failed steps show error details with full stack trace

---

## Phase 6: Set Up Recurring Training

```python
# Schedule weekly retraining (e.g., after new data lands in S3)
client.create_recurring_run(
    experiment_id=experiment.experiment_id,
    job_name="katie-weekly-retrain",
    pipeline_id=pipeline.pipeline_id,
    cron_expression="0 2 * * 0",  # Sunday 2am UTC
    parameters={
        "data_path": "s3://ml-artifacts/training-data/latest.jsonl",
        "model_name": "katie-3b",
    },
)
```

---

## Decision Tree

```
Pipeline submitted
  ├── validate_data FAILS → Pipeline stops. Fix data quality.
  ├── train_lora OOM → Reduce batch_size or max_seq_length. Retry.
  ├── train_lora spot interrupted → KFP retries from checkpoint.
  ├── evaluate PASSES (≥60%) → Model promoted to S3, registry updated.
  ├── evaluate 40-60% → Feedback loop: generate targeted data, retrain.
  └── evaluate <40% → Review data quality. Manual inspection.
```

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| Pipeline running | `06-setup-rag-pipeline.md` (if RAG needed) |
| Model promoted | `08-deploy-kserve.md` (serve it) |
| Eval scores low | `feedback_loop.py` → generate data → re-run pipeline |
| Want SageMaker training | `14-sagemaker-training-jobs.md` |
