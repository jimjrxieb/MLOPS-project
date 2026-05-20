# 3-model-registry — Artifact Store

Version-controlled store for model weights, GGUFs, Modelfiles, and training state. Every promoted version lives here. Nothing goes to Ollama that isn't registered here first.

## Models

| Model | Track | Base | Status |
|-------|-------|------|--------|
| BERU | `beru/` | Llama 3.2-3B | Training — exp-014 (KB 20% / PB 68.2%) |
| JADE | `jade/` | Llama 3.1-8B | Checkpoint v1.1 |
| Katie | `katie/` | Llama 3.2-3B | Deployed |

## Structure

```text
3-model-registry/
├── beru/
│   └── vX.X/
│       ├── Modelfile          ← Ollama model definition
│       ├── training_state.json ← corpus SHA, chunk count, eval scores
│       └── (weights gitignored — stored locally or in GP-S3)
├── jade/
│   └── v1.1/
│       ├── Modelfile
│       └── training_state.json
└── katie/
    └── v1.0/
        ├── Modelfile
        └── training_state.json
```

## Model Versions

| Version | Base Model | Examples | Status |
|---------|------------|----------|--------|
| v0.1 | Qwen2.5-7B-Instruct | 10k | Complete |
| v0.2 | Qwen2.5-7B-Instruct | 372k | Complete |
| v0.3 | Qwen2.5-Coder-7B-Instruct | 491k | Training |

## Current Training (v0.3)

```bash
# Check progress
tail -20 v0.3-coder/logs/v03_chunk_5.log

# Resume training
python3 train_v03_coder.py --resume --chunk 6

# After all chunks complete:
python3 scripts/merge_v03.py
ollama create jade:v0.3 -f Modelfile-jade-v0.3
```
