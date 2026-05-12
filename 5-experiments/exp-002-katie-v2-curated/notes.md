# Experiment 002 — Katie v2 Curated Training

## Hypothesis

Quality > quantity. 42,276 curated examples (from 284,844 raw) will outperform the v1 bulk approach by eliminating garbage data that caused catastrophic forgetting.

## Changes from exp-001

| What | exp-001 (v1) | exp-002 (v2) |
|------|-------------|-------------|
| Corpus size | 284,844 | 42,276 |
| Curation | None | 6-gate pipeline |
| Format | Mixed (Alpaca + ChatML) | ChatML only |
| LoRA approach | Stacked (chunk on chunk) | Fresh from base |
| Eval cadence | Periodic | After every chunk |
| Domain tracking | None | CKS 35%, CKA 30%, CKAD 20%, CNPA 10%, OPS 5% |

## Curation Results

Built `curate_corpus.py` to clean the v1 corpus:
- Input: 284,844 examples
- Output: 42,276 examples (85.2% rejected)
- Rejections: wrong format, out-of-scope, garbage, transcripts, duplicates, stubs

## Current Status

- Chunk 1/5 trained (10,000 examples)
- Merged checkpoint at `3-model-registry/v2.0-3b/chunk_0001_10k/merged`
- Eval pending — must pass before continuing to chunk 2

## Expected Outcome

If the hypothesis holds:
- Per-category scores should improve vs v1 best (28.5% overall)
- No catastrophic forgetting between chunks (fresh LoRA + clean data)
- CNPA should improve (was 45.5% in v1 despite minimal targeted data)
- Cloud and hardening should improve from 0% (had almost no clean data in v1)

## Promotion Criteria

- Weighted total ≥ 60% → production
- Each category (CKS, CKA, CNPA, Cloud) ≥ 50%
- Zero hallucinated commands

## Artifacts

- Curated corpus: `1-data-pipeline/05-data-quality/curated/katie_v2_clean.jsonl`
- Checkpoint: `3-model-registry/v2.0-3b/chunk_0001_10k/merged`
- Training state: `3-model-registry/v2.0-3b/training_state.json`
