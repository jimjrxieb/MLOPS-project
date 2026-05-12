# KFP Reusable Components

Pipeline components used across multiple pipelines. Each component runs in its own container.

## Available Components

| Component | What It Does |
|-----------|-------------|
| `validate_data` | Data quality gates (format, dedup, content check) |
| `etl_and_chunk` | Normalize to ChatML, deduplicate, split into chunks |
| `train_lora` | LoRA fine-tuning via Unsloth (GPU required) |
| `merge_lora` | Merge LoRA adapters into base model |
| `convert_gguf` | Convert to GGUF for vLLM serving |
| `evaluate_model` | Run eval benchmark, check promotion gates |
| `register_model` | Upload promoted model to S3 for KServe |

## Writing New Components

```python
from kfp import dsl
from kfp.dsl import Input, Output, Dataset, Model, Metrics

@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["your-package==1.2.3"],
)
def my_component(
    input_data: Input[Dataset],
    output_model: Output[Model],
    some_param: str,
) -> bool:
    # Each component runs in its own container
    # Input/Output artifacts are automatically passed between steps
    ...
```

## Deployed by

- Pipeline: `02-training-pipeline/kfp/training_pipeline.py`
- Playbook: `playbooks/05-setup-kfp-pipeline.md`
