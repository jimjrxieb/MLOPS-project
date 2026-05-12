# Experiment 001 — Katie v1 Bulk Training

## Hypothesis

Train Katie (3B) on the full 284,844-example corpus. More data = better model.

## What Happened

Trained 36 chunks (294,998 examples) over multiple sessions from Jan-Mar 2026. Peak accuracy reached 28.5% overall at chunk 36, with CKS at 27.8% and kubernetes general at 60%.

Then continued training chunks 37-46. Accuracy **dropped to 8.3%** — catastrophic forgetting.

## Root Cause Analysis

1. **~85% of the data was garbage.** Raw JSON logs, YouTube transcripts, wrong format (Alpaca instead of ChatML), placeholder text like `[NEEDS CORRECTION]`, duplicate examples.
2. **Stacked LoRA weights on noisy data.** Each chunk added noise on top of noise. By chunk 46, the model had memorized garbage patterns.
3. **No data quality gates.** Nothing prevented bad data from entering the pipeline.
4. **No per-chunk eval.** We didn't catch the regression at chunk 37 because we only evaluated periodically.

## Key Findings

- Kubernetes general scored 60% — the cleanest subset of training data
- CKS scored 27.8% — reasonable given the noise, but far from 50% threshold
- Cloud scored 0% — almost no clean cloud training data
- Hardening scored 0% — same problem
- Zero hallucinations across all evals — model doesn't fabricate, it just gives weak answers

## Decision

**Abandon v1 corpus. Build curate_corpus.py. Start fresh from base model.**

See: `exp-002-katie-v2-curated`

## Artifacts

- Checkpoint: `3-model-registry/v1.1-3b/chunk_0036_10k/merged` (best v1)
- Eval results: `4-eval-clarify/3-results/bridge_20260315_134833/`
- Curation report: `1-data-pipeline/curation_report.txt`
