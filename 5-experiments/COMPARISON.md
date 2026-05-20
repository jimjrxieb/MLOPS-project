# Experiment Comparison

Side-by-side of all training experiments. Updated after each run completes.

Promotion gate: **≥70% knowledge brain + ≥70% pentest brain**, per-type floor 60%, zero hallucinated control IDs.

---

## History

| Exp | Model | Corpus | KB | PB | Gate | Key Learning |
|-----|-------|--------|-----|-----|------|-------------|
| 001 | LLaMA 3.2-3B (raw) | 284,844 | — | 28.5%\* | FAILED | 85% of data was garbage — mixed format, no curation |
| 002 | LLaMA 3.2-3B (curated) | 42,276 | — | In progress | PENDING | Hypothesis: quality > quantity |
| 003 | LLaMA 3.1-8B (raw) | 284,844 | — | 0%\*\* | Deployed | Eval framework mismatch; model serves well with RAG |
| 004 | LLaMA 3.2-3B | CySA corpus | — | — | DATA | Corpus design run — no training |
| 005 | llama3.2:3b (baseline) | — | 29.4% | 40.3% | BLOCKED | Pre-fine-tune baseline established |
| 006 | beru-v1.0-3b | 579 | 3.3% | 95.5% | BLOCKED | KB collapsed; PB overfit to refusal behavior |
| 007 | beru-v1.1-3b | 579 | 16.7% | 72.7% | BLOCKED | max_seq_length 4096→8192 fixed truncation; KB recovering |
| 008 | beru-v1.2-3b | 679 | 3.3% | 68.2% | BLOCKED | KB regression on expanded corpus |
| 009 | beru-v1.3-3b | 234 | 13.3% | 72.7% | BLOCKED | Smaller focused corpus; PB stable |
| 010 | beru-v1.4-3b | — | 10.0% | 81.8% | BLOCKED | PB improving; KB plateau |
| 011 | beru-v1.5-3b | — | 10.0% | 81.8% | BLOCKED | Plateau confirmed — corpus change needed |
| 012 | beru-v1.6-3b | — | 13.3% | 81.8% | BLOCKED | KB marginal improvement; PB stable |
| 013 | beru:v1.6 (live) | — | 20.0% | 68.2% | BLOCKED | Live Ollama serving eval; PB dip vs static |
| 014 | beru:v1.6 (corrected) | — | 20.0% | 68.2% | BLOCKED | Corrected eval suite — see below |

\* exp-001 used a 466-question bridge eval. Not comparable to BERU eval suite.  
\*\* exp-003 used a 10-question strict-keyword eval. Eval mismatch, not model failure.

---

## Per-Type Breakdown (BERU knowledge brain, exp-014)

| Question Type | Score | Notes |
|---------------|-------|-------|
| `finding_accuracy` | 40% | SSP claim vs real evidence — correct question type |
| `evidence_gap_detection` | 40% | Identifying what's missing for a PASS |
| `poam_drafting` | 20% | Temperature variance — was 60% in exp-012 |
| `tool_output_interpretation` | 20% | Scanner output → control mapping |
| `dual_citation` | 0% | 800-53 + AI RMF simultaneously — hardest capability |
| `atlas_mapped_ai_risk` | 0% | MITRE ATLAS technique mapping |

---

## What We Learned

### The garbage data problem (exp-001 → exp-002)

| What failed | What changes |
|-------------|-------------|
| 85% of examples were garbage | 6-gate curation pipeline |
| Mixed Alpaca + ChatML format | ChatML enforced, Alpaca rejected |
| Stacked LoRA caused forgetting | Fresh LoRA from base each run |
| No domain tracking | CKS 35% / CKA 30% / CKAD 20% / CNPA 10% / OPS 5% |

### The truncation problem (exp-006 → exp-007)

max_seq_length of 4096 was truncating 50-80% of every eval prompt. Increasing to 8192 recovered 13pp on KB in one run. Always validate that eval prompts fit the context window before attributing results to the model.

### The dual-citation gap (persistent across all runs)

`dual_citation` scores 0% across every experiment. The training corpus describes the format (cite both 800-53 + AI RMF) but doesn't give enough examples of the *trigger pattern* — recognizing that an AI system is in scope and switching into dual-citation mode. exp-015 targets this with realistic garak/promptfoo/MLflow audit inputs.

### The eval design problem (exp-013 → exp-014)

The original suite included `escalation_discipline` questions that tested whether BERU would refuse to output a report until a human "approved" it. Wrong mental model. BERU is a document-producing GRC analyst, not an action-taking agent. A GRC analyst doesn't hold their report — they write the finding, assign a rank, and send it. Human decisions happen in the recipient's inbox, not in the tool. Replaced with `finding_accuracy` questions (SSP claim vs actual evidence → PASS/PARTIAL/FAIL), which is BERU's actual job.

---

## Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-05-08 | Rebaseline to 3B from 8B | 8B fine-tune takes 9+ hours on RTX 5080; 3B trains in ~45 min per chunk with comparable GRC output quality |
| 2026-05-14 | Remove escalation_discipline questions | Wrong mental model — BERU produces documents, not actions |
| 2026-05-14 | Add finding_accuracy questions | SSP claim vs real evidence grading is BERU's actual job |
