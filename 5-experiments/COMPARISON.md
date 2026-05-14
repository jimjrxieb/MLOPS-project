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
| exp-013 | BERU: SSP-grading heavy corpus (392 examples) with PASS-rebalance rolled back | exp-012 regressed on PASS-rebalance |

---

## BERU Track (GRC analyst 3B — exp-005 through exp-012)

Promotion gate: **knowledge brain ≥70%, pentest brain ≥70%, zero hallucinated IDs.**  
Knowledge brain is the hard wall — 30-question suite across 6 GRC question types.  
Pentest brain is the security-robustness check — 22 questions across OWASP LLM01-LLM10.

### Summary

| | exp-005 | exp-006 | exp-007 | exp-008 | exp-009 | exp-010 | exp-011 | exp-012 |
|---|---|---|---|---|---|---|---|---|
| **Version** | v1.0 baseline | v1.0 | v1.1 | v1.2 | v1.3 | v1.4 | v1.5 | v1.6 |
| **Type** | RAG baseline | Fine-tune | Fine-tune | Fine-tune | Fine-tune | Fine-tune | Fine-tune | Fine-tune |
| **Corpus** | — | 579 | 579 | 679 | 234 | 835 | 1,031 | 1,227 |
| **Train loss** | — | — | 2.056 | 2.037 | 1.936 | 1.901 | 1.759 | 1.561 |
| **Duration** | — | — | 7.2 min | 8.2 min | 3.1 min | 10.2 min | 13.1 min | 16.3 min |
| **Knowledge brain** | 29.4% | 3.3% | **16.7%** | 3.3% | 13.3% | 10.0% | 10.0% | 13.3% |
| **Pentest brain** | 40.3% | 95.5% | 72.7% | 68.2% | 72.7% | **81.8%** | **81.8%** | **81.8%** |
| **Decision** | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |

Gate thresholds (70% both) shown in **bold** where pentest passes.

### What We Learned

| Experiment | What changed | What happened | Lesson |
|---|---|---|---|
| exp-005 | RAG baseline (no fine-tune) | KB: 29.4%, PB: 40.3% | This is the floor. RAG alone is insufficient. |
| exp-006 | First fine-tune (3 epochs, 579 examples) | KB crashed to 3.3%; PB spiked to 95.5% | Catastrophic forgetting of GRC knowledge when training skewed toward adversarial. |
| exp-007 | max_seq 4096→8192, train_on_responses_only, 2 epochs | KB: 16.7% (best so far), PB: 72.7% | Longer context + response-only training recovered KB from the exp-006 floor. |
| exp-008 | Added 100 analyst examples to corpus (679 total) | KB: 3.3%, PB: 68.2% | Corpus addition alone without quality tuning regressed KB. Variable isolation failed. |
| exp-009 | Isolated 234 analyst-only examples | KB: 13.3%, PB: 72.7% | Smaller, targeted corpus beats larger noisy one for KB. |
| exp-010 | Combined 835 (adversarial + analyst, deduped) | KB: 10.0%, PB: 81.8% | Pentest brain stabilized at 81.8%. KB still regressed. Balance problem surfaced. |
| exp-011 | Expanded to 1,031 examples (added SSP-grading corpus) | KB: 10.0%, PB: 81.8% | More SSP data did not lift KB. Model reached a plateau. |
| exp-012 | 1,227 examples — doubled SSP-grading, PASS-rebalanced | KB: 13.3%, PB: 81.8% | Minor KB recovery but PASS-rebalance did not deliver the expected lift. Rolled back per commit notes. |

### Decision Log (BERU track)

| Date | Decision | Reason |
|------|----------|--------|
| 2026-05-08 | Establish RAG baseline (exp-005) before any fine-tune | D-010 requires beating baseline on KB, not regressions |
| 2026-05-10 | Pivot: train_on_responses_only + seq_len 8192 (exp-007) | exp-006 catastrophic forgetting traced to full-sequence loss on instruction tokens |
| 2026-05-11 | Revert PASS-rebalance after exp-012 | Did not lift KB; pentest held at 81.8% but KB gain insufficient |
| 2026-05-13 | Current champion: none promoted yet | KB 13.3% (need 70%). Next: narrative-first prompt rewrite + heavier SSP corpus (exp-013) |

### Promotion Gate (BERU)

```
Knowledge brain ≥70% overall
  per question type floor: ≥60%
  zero hallucinated control IDs / AI RMF subcategory IDs / ATLAS technique IDs

Pentest brain ≥70% overall
  LLM01, LLM06, LLM08 critical floor: ≥70% each

Fine-tune must beat exp-005 baseline on knowledge brain.
Fine-tune must not regress pentest brain below baseline (40.3%).
```

**Current status:** Pentest brain passes (81.8%). Knowledge brain blocked at 13.3% — 56.7 pp gap to gate.
