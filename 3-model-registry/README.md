# 3-model-registry — Artifact Store

Version-controlled store for model weights, GGUFs, and training state. Every version that reaches Ollama is registered here first. Weights are gitignored (too large for GitHub) — the metadata files are the source of truth.

---

## Current State

| Version | Naming | Has GGUF | Ollama Tag | Status |
|---------|--------|----------|------------|--------|
| v1.4 | `beru-v1.4-3b/` | Yes | `beru:v1.4` | Superseded |
| v1.5 | `beru-v1.5-3b/` | Yes | `beru:v1.5` | Superseded |
| v1.6 | `beru-v1.6-3b/` | Yes | `beru:v1.6` | **Champion** (serving) |
| v1.7 | `beru/v1.7/` | Yes | `beru:v1.7` | Challenger (exp-015, not promoted) |

Versions v1.0–v1.3 were deleted — no GGUFs, never served, all blocked at eval gate.

---

## Directory Layout

```text
3-model-registry/
├── beru-v1.4-3b/          ← old naming convention (version + base size)
│   ├── _checkpoints/      ← LoRA training checkpoints (gitignored)
│   ├── lora_adapter/      ← final LoRA weights (gitignored)
│   ├── merged_16bit/      ← base + LoRA merged, full precision (gitignored)
│   └── gguf/              ← Q4_K_M / Q8_0 quantized (gitignored)
│
├── beru-v1.5-3b/          ← same layout
├── beru-v1.6-3b/          ← same layout — CHAMPION
│
└── beru/                  ← new naming convention (pipeline.yaml drives path)
    └── v1.7/              ← challenger from exp-015
        ├── beru-merged/   ← 16-bit merged weights (gitignored)
        ├── beru-v1.7-q4_k_m.gguf  ← 1.88 GB quantized (gitignored)
        └── training_state.json    ← tracked — corpus hash, eval scores, promotion decision
```

**Naming convention changed at v1.7.** Prior versions embed the base model size in the directory name (`beru-v1.6-3b`). From v1.7 onward, `pipeline.yaml` controls the output path (`3-model-registry/beru/vX.X`) and the base model is recorded in `training_state.json` — not the directory name.

---

## What's Tracked vs Gitignored

Gitignored (large binary, regenerable from training):
- `*.safetensors`, `*.bin`, `*.pt`, `*.pth`, `*.ckpt` — LoRA adapters, checkpoints
- `*.gguf` — quantized models
- `merged_16bit/`, `beru-merged/` — full-precision merged weights

Tracked (small, hand-authored or machine-generated metadata):
- `training_state.json` — corpus SHA, experiment ID, eval scores, promotion decision
- `README.md` — this file

---

## Loading a Version into Ollama

```bash
# Champion (v1.6)
ollama create beru:v1.6 -f BERU-AI/modelfiles/Modelfile_beru_v16

# Challenger (v1.7)
ollama create beru:v1.7 -f BERU-AI/modelfiles/Modelfile_beru_v17

# List registered tags
ollama list | grep beru
```

---

## Promotion Gate

A version is promoted to champion only when it clears both eval suites on the same run:

- `knowledge_brain` ≥ 70% overall, ≥ 60% per question type
- `pentest_brain` ≥ 70% overall

Eval results live in `5-experiments/exp-NNN-beru-vX.X/metrics.json`. See `5-experiments/COMPARISON.md` for the full history.
