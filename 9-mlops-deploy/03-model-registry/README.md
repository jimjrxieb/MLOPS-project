# 03-Model Registry

Model versioning templates and promotion workflow patterns.

## Contents

- `templates/Modelfile.template` — Ollama Modelfile template (for local dev serving)

## S3 Registry Structure

Production models are stored in S3 with a version manifest:

```
s3://ml-artifacts/models/
├── katie-3b/
│   ├── v2.0/
│   │   ├── model.gguf           ← GGUF for vLLM serving
│   │   ├── config.yaml          ← Training config snapshot
│   │   ├── eval_results.json    ← Benchmark scores at promotion time
│   │   └── training_state.json  ← What data was used
│   └── v1.1/
├── jade-8b/
│   └── v1.1/
└── registry.json                 ← Version manifest (production/staging/archived)
```

## Local Registry Structure

For development, models are versioned as directories:

```
3-model-registry/
├── v2.0-3b/
│   ├── merged/              ← Merged LoRA weights
│   ├── model.gguf           ← GGUF checkpoint
│   ├── config.yaml
│   ├── eval_results.json
│   └── training_state.json
└── Modelfile_llama3b        ← Ollama Modelfile (local dev only)
```

## Related

- Playbook `03-setup-model-registry.md`
- SageMaker alternative: `15-sagemaker-model-registry.md`
- Actual registry: `GP-MODEL-OPS/3-model-registry/`
