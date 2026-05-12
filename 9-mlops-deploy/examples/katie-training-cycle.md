# Example: Katie v2 Training Cycle

> Real training lifecycle for Katie (LLaMA 3.2-3B-Instruct), a CKA/CKS/CKAD/CNPA autonomous Kubernetes engineer.

---

## Context

Katie is a 3B parameter model fine-tuned to handle production Kubernetes incidents autonomously. She executes E/D-rank findings without human intervention and proposes C-rank fixes for JADE approval.

---

## Data Curation

**Problem:** v1 corpus was 300,000 examples but ~85% garbage — raw JSON logs, duplicates, wrong format, YouTube transcripts.

**Solution:** Built `curate_corpus.py` with 6 quality gates:
1. Format validation (ChatML only)
2. Scope check (must match CKS/CKA/CKAD/CNPA/OPS keywords)
3. Garbage rejection (placeholders, nested JSON, stubs)
4. Transcript rejection
5. Deduplication (exact + near-duplicate)
6. Response quality (must contain real commands/YAML)

**Result:** 300,000 → 44,030 clean examples

---

## Training Configuration

```yaml
model:
  base: "unsloth/Llama-3.2-3B-Instruct"
  quantization: "4bit"
lora:
  r: 64
  alpha: 128
  dropout: 0.05
training:
  epochs: 2
  batch_size: 4
  gradient_accumulation: 4
  learning_rate: 2e-4
  lr_scheduler: "cosine"
  max_seq_length: 4096
```

---

## Domain Distribution

| Domain | Target | Actual | Status |
|--------|--------|--------|--------|
| CKS | 35% | 35.2% | On target |
| CKA | 30% | 29.8% | On target |
| CKAD | 20% | 19.1% | On target |
| CNPA | 10% | 10.8% | On target |
| OPS | 5% | 5.1% | On target |

---

## Pipeline Execution

```
Step 1: ETL           — 44,030 examples normalized to ChatML
Step 2: Chunk         — 5 chunks of 10k (last chunk: 4,030)
Step 3: Train         — 2 epochs per chunk, ~45 min/chunk on RTX 4090
Step 4: Merge         — LoRA adapters merged into base
Step 5: Convert       — GGUF Q4_K_M (2.1 GB)
Step 6: Eval          — 466 questions across 9 categories
Step 7: Feedback      — Identified CNPA/service-mesh as weak category
```

---

## Key Lessons

1. **Quality > Quantity:** 44k clean examples outperform 300k noisy ones
2. **Minimum chunk size matters:** Sub-500 chunks caused catastrophic forgetting in v1
3. **Fresh LoRA > Stacked LoRAs:** Starting from base model each time is more stable
4. **Eval after every chunk:** Catches degradation before it compounds
5. **Domain distribution tracking:** Without it, CKS dominates and CNPA starves
