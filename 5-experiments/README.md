# Experiments

Each directory is one experiment — a hypothesis, params, eval results, and notes on what was learned.

## History (14 experiments)

| ID | Name | Model | KB | PB | Outcome |
|----|------|-------|-----|-----|---------|
| 001 | katie-v1-bulk | LLaMA 3.2-3B | — | 28.5%\* | FAILED — 85% garbage data, mixed format |
| 002 | katie-v2-curated | LLaMA 3.2-3B | — | In progress | PENDING — quality > quantity hypothesis |
| 003 | jade-v1-8b | LLaMA 3.1-8B | — | 0%\*\* | Deployed qualitatively — eval mismatch |
| 004 | beru-v1-cysa | LLaMA 3.2-3B | — | — | Corpus design only — no training run |
| 005 | beru-3b-baseline | llama3.2:3b | 29.4% | 40.3% | BLOCKED — baseline established |
| 006 | beru-v1.0 | beru-v1.0-3b | 3.3% | 95.5% | BLOCKED — PB overfit, KB collapsed |
| 007 | beru-v1.1 | beru-v1.1-3b | 16.7% | 72.7% | BLOCKED — seq_len fix recovered KB |
| 008 | beru-v1.2 | beru-v1.2-3b | 3.3% | 68.2% | BLOCKED — KB regression on larger corpus |
| 009 | beru-v1.3 | beru-v1.3-3b | 13.3% | 72.7% | BLOCKED — smaller focused corpus |
| 010 | beru-v1.4 | beru-v1.4-3b | 10.0% | 81.8% | BLOCKED — PB up, KB plateau |
| 011 | beru-v1.5 | beru-v1.5-3b | 10.0% | 81.8% | BLOCKED — plateau confirmed |
| 012 | beru-v1.6 | beru-v1.6-3b | 13.3% | 81.8% | BLOCKED — marginal KB gain |
| 013 | beru-v1.6-live-eval | beru:v1.6 | 20.0% | 68.2% | BLOCKED — first live Ollama serving eval |
| 014 | beru-v1.6-corrected-eval | beru:v1.6 | 20.0% | 68.2% | BLOCKED — corrected eval suite |

\* 466-question bridge eval, not comparable to BERU suite.  
\*\* 10-question strict-keyword eval. Eval mismatch, not model failure.

Gate: ≥70% KB + ≥70% PB. Current champion: none yet.

## Convention

```
exp-NNN-short-name/
├── params.yaml    ← hyperparameters, corpus SHA256, artifact paths
├── metrics.json   ← machine-readable eval output
└── notes.md       ← hypothesis, results, what to try next
```

See `COMPARISON.md` for full breakdown, per-type scores, and lessons learned.

## Rules

- Every training run gets an experiment entry. Not optional.
- `params.yaml` must include `artifacts.corpus_sha256` — results must be reproducible.
- `metrics.json` must link to the eval result file in `4-eval-clarify/3-results/`.
- New model must beat current champion on the same eval suite to promote.
