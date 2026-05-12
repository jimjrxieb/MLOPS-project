# 02-Training Pipeline

Training configuration templates and KFP v2 pipeline definitions for LoRA fine-tuning.

## Contents

```
02-training-pipeline/
├── configs/
│   └── default.yaml             ← Default training config (3B model, LoRA r=64)
├── kfp/
│   ├── training_pipeline.py     ← KFP v2 full pipeline (validate → ETL → train → eval → promote)
│   ├── training_pipeline.yaml   ← Compiled pipeline (upload to KFP UI or submit via API)
│   └── validate_etl_test.py     ← CPU-only test pipeline (validate + ETL, no GPU)
└── sagemaker/
    └── train_sagemaker.py       ← SageMaker training job wrapper
```

## How Training Works

Two paths — same data, same model, same result:

### Path 1: KFP Pipeline (full automation)

All 7 steps run as K8s pods orchestrated by KFP. Artifacts flow between steps automatically.

```
SeaweedFS (S3) → download → validate → ETL+chunk → train_lora (GPU) → merge → convert → eval → promote
```

```bash
# Submit to KFP
python3 kfp/training_pipeline.py --submit --endpoint http://localhost:8887

# Or compile and upload via KFP UI
python3 kfp/training_pipeline.py --compile
# → Upload training_pipeline.yaml at http://localhost:8888
```

### Path 2: Local training + KFP tracking (hybrid)

Train locally with `1-data-pipeline/train_llama3b.py`, use KFP for validation, ETL, and eval.

```
KFP: validate → ETL → chunk (in K8s)
Local: train_llama3b.py (your GPU directly)
KFP: eval → promote (in K8s)
```

```bash
# Local training (picks up next untrained chunk automatically)
python3 1-data-pipeline/train_llama3b.py --version v2.0-3b --skip-eval
```

### Which path to use?

| Environment | Path | Why |
|-------------|------|-----|
| Docker Desktop + WSL2 | Either works | GPU available via `default-runtime: nvidia` |
| EKS + Karpenter | Path 1 (KFP) | Spot GPU on demand, scale to zero |
| No GPU on cluster | Path 2 (hybrid) | Train locally, orchestrate in K8s |

## KFP Pipeline Steps

Each step runs in its own container with artifact tracking and caching:

1. **download_data** — Pull training data from SeaweedFS/S3
2. **validate_data** — Data quality gates (format, dedup, content check)
3. **etl_and_chunk** — Normalize to ChatML, deduplicate, split into chunks + eval holdout
4. **train_lora** — LoRA fine-tuning via Unsloth (GPU, 4-bit quantized)
5. **merge_lora** — Merge LoRA adapters into base model
6. **convert_gguf** — Convert to GGUF for Ollama/vLLM serving
7. **evaluate_model** — Benchmark against eval suite, check promotion gate
8. **register_model** — Upload promoted model to S3, update registry.json

## GPU Access

- **Docker Desktop WSL2:** GPU available to all pods automatically (`default-runtime: nvidia` in daemon.json). No `nvidia.com/gpu` resource requests needed.
- **EKS:** Uncomment `set_accelerator_type` / `set_accelerator_limit` in `training_pipeline.py`. Karpenter provisions spot `g5.xlarge` on demand.

See `01-kubeflow-platform/README.md` for full GPU setup instructions.

## Training Data

Training data lives in `1-data-pipeline/03-chunked-untrained/` (local) and `ml-artifacts` bucket on SeaweedFS (in-cluster S3). The `validate_etl_test.py` pipeline demonstrates the full flow: download from S3 → validate → ETL + chunk.

## Related

- Playbook `05-setup-training-pipeline.md`
- Actual training scripts: `GP-MODEL-OPS/1-data-pipeline/` (`train_llama3b.py`, `train_v11.py`)
- Training config: `configs/default.yaml`
- SageMaker alternative: Playbook `14-sagemaker-training-jobs.md`
