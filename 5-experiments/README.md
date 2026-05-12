# Experiments

Each directory is one experiment — a hypothesis tested, with params, results, and notes.

## History

| ID | Name | Model | Corpus | Result | Outcome |
|----|------|-------|--------|--------|---------|
| 001 | katie-v1-bulk | LLaMA 3.2-3B | 284,844 raw | 28.5% overall, 27.8% CKS | Failed — garbage data |
| 002 | katie-v2-curated | LLaMA 3.2-3B | 42,276 curated | In progress | Hypothesis: quality > quantity |
| 003 | jade-v1-8b | LLaMA 3.1-8B | 284,844 raw | 0% benchmark | Eval framework mismatch |

## Convention

```
exp-NNN-short-name/
├── params.yaml       ← exact hyperparameters + data SHA256 + artifact paths
├── metrics.json      ← eval results (machine-readable)
└── notes.md          ← why we tried this, what we learned
```

See `COMPARISON.md` for side-by-side view of all experiments.

## Rules

- Every training run gets an experiment entry. Not optional.
- `params.yaml` must include `artifacts.corpus_sha256` so results are reproducible.
- `metrics.json` must link to the eval result directory in `4-eval-clarify/3-results/`.
- New model must beat current champion on the same eval suite to promote.
