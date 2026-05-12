# Experiment Comparison

Side-by-side comparison of all training experiments. Updated after each experiment completes.

## Summary

| | exp-001 | exp-002 | exp-003 |
|---|---|---|---|
| **Name** | Katie v1 Bulk | Katie v2 Curated | JADE v1 8B |
| **Model** | LLaMA 3.2-3B | LLaMA 3.2-3B | LLaMA 3.1-8B |
| **Corpus** | 284,844 (raw) | 42,276 (curated) | 284,844 (raw) |
| **Format** | Mixed | ChatML only | Mixed |
| **Curation** | None | 6-gate pipeline | None |
| **LoRA approach** | Stacked (36 chunks) | Fresh from base | Stacked |
| **Overall accuracy** | 28.5% | In progress | 0% (eval mismatch) |
| **Status** | Failed | In progress | Deployed (jade:v1.0) |
| **Promoted?** | No | Pending | Yes (qualitative) |

## Category Comparison

| Category | exp-001 (v1 3B) | exp-002 (v2 3B) | exp-003 (8B) |
|----------|-----------------|-----------------|--------------|
| CKS | 27.8% (100/360) | — | 0% (0/3)* |
| Kubernetes | 60.0% (6/10) | — | — |
| CNPA | 45.5% (10/22) | — | — |
| DevSecOps | 40.0% (4/10) | — | — |
| CKA | 31.6% (6/19) | — | — |
| Compliance | 30.0% (3/10) | — | — |
| Incident Response | 20.0% (2/10) | — | — |
| Threat Modeling | 20.0% (2/10) | — | — |
| Hardening | 0.0% (0/5) | — | — |
| Cloud | 0.0% (0/10) | — | 0% (0/3)* |

*exp-003 used a 10-question eval suite with strict keyword matching. Not directly comparable to exp-001's 466-question bridge eval.

## What We Learned

### exp-001 → exp-002 (the v1 to v2 pivot)

| What failed in v1 | What v2 changes |
|---|---|
| 85% of data was garbage | curate_corpus.py rejects garbage |
| Mixed format (Alpaca + ChatML) | ChatML enforced, Alpaca rejected |
| Stacked LoRA caused forgetting | Fresh LoRA from base each time |
| No eval between chunks | Eval after every chunk |
| No domain tracking | CKS 35%, CKA 30%, CKAD 20%, CNPA 10%, OPS 5% |
| No quality gates | 6-gate validation pipeline |

### exp-003 (JADE 8B)

| Finding | Implication |
|---|---|
| 0% on 10-question benchmark | Eval suite was too narrow, not model failure |
| Model serves useful answers with RAG | RAG compensates for weak fine-tuning |
| Deployed without promotion gate | Gap — next version must pass gate |
| Same garbage corpus as exp-001 | Needs curated corpus (same fix as Katie) |

## Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-03-15 | Abandon v1 corpus | 85% garbage, catastrophic forgetting after chunk 36 |
| 2026-03-15 | Build curate_corpus.py | Need quality gates before any more training |
| 2026-03-17 | Start exp-002 with curated data | Quality > quantity hypothesis |
| 2026-03-17 | Keep jade:v1.0 in production | Works with RAG despite bad benchmark. Replace after v2 curated training. |

## Promotion Gate (must pass to deploy)

```
Weighted total ≥ 60%
  CKS  (40% weight) ≥ 50%
  CKA  (25% weight) ≥ 50%
  CNPA (25% weight) ≥ 50%
  Cloud (10% weight) ≥ 50%

Zero hallucinated commands
New model must beat current champion on same eval suite
```

## Next Experiments

| ID | Hypothesis | Blocked by |
|----|-----------|------------|
| exp-004 | Katie v2 chunk 2-5 training | exp-002 chunk 1 eval |
| exp-005 | JADE v2 with curated corpus (8B) | exp-002 proving curation works on 3B first |
| exp-006 | Katie with platform eng data (Python, Bash, GHA, Terraform) | New training data from generators |
