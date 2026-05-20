# BERU Training Corpus Audit — 2026-05-14

## What triggered this audit

exp-014 knowledge brain eval (corrected suite) surfaced three failure patterns:
1. Three responses generated bash/Python scripts instead of GRC findings
2. Dual citation (800-53 + AI RMF + ATLAS in one response) scored 0% across 5 questions
3. Format drift — correct content, missing specific keywords like "AC-6" or "AU-3"

## Corpus audited

| File | Examples | Code contamination | Format issues | AI RMF present | ATLAS present |
|---|---|---|---|---|---|
| `beru_training_exp012.jsonl` | 1,227 | 0 (0.0%) | 1 (0.1%) | 204 (16.6%) | 44 (3.6%) |
| `beru_training_combined_v1.jsonl` | 835 | 0 (0.0%) | 1 (0.1%) | 204 (24.4%) | 44 (5.3%) |
| `beru-training-examples.jsonl` | 679 | 0 (0.0%) | 1 (0.1%) | 204 (30.0%) | 44 (6.5%) |

## Root cause findings

### 1. Code generation is a base model behavior, not corpus contamination

The training corpus has **zero code-contaminated examples**. The bash/Python script responses
during eval are the LLaMA 3.2-3B base model pattern-matching to certain prompt structures
(e.g., "Produce the BERU finding" gets misread as "produce output" and the base model
defaults to code-generation mode).

**Fix:** More GRC-format examples increase the signal-to-noise ratio and override the base
model's code-generation prior. Target: 300+ additional examples in the 10-field BERU format.

### 2. Dual citation is undertrained

The 1,227-example corpus has only:
- **204 examples with any AI RMF content (16.6%)** — but these are scattered across individual
  subcategory citations, not the full triple (800-53 + AI RMF + ATLAS) pattern
- **44 examples with ATLAS technique IDs (3.6%)** — the model sees AML.T0xxx rarely enough
  that it doesn't recognize the trigger for citing them

The eval failure pattern confirms this: on every dual-citation question, BERU cites ONE
framework but not all three. The retrieval is working (ATLAS chunks are in the RAG collection),
but the model hasn't learned that "AI system in scope" is the trigger for producing all three
citations simultaneously.

**Fix:** 50 new dual-citation examples covering all major ATLAS technique clusters with
explicit 800-53 + AI RMF + ATLAS in every response.

### 3. Format drift is a keyword coverage gap, not a comprehension failure

POA&M questions show BERU writing the correct content but omitting specific keywords:
- Writes "least privilege" but not "AC-6"
- Writes "log rotation" but not "AU-3"  
- Writes "restrict SSH" but not "bastion"

The model understands the concept but hasn't seen enough examples pairing the concept
with the control ID in a POA&M context specifically.

**Fix:** 30 new `finding_accuracy` examples (SSP grading format) that pair evidence
descriptions with explicit control IDs and PASS/PARTIAL/FAIL determinations.

### 4. RAG top_k is already at 4

Default `DEFAULT_RAG_TOP_K = 4` in `beru_eval_runner.py`. The training-time evals
(exp-006 through exp-012) used `top_k=2` (set in the experiment-specific config as a
fix for context length). The live eval runner uses 4. No change needed.

## Data gaps by eval question type

| Question type | Current training examples (est.) | Pass rate (exp-014) | Gap |
|---|---|---|---|
| `tool_output_interpretation` | ~150 | 20% (1/5) | More scanner-output → finding examples |
| `evidence_gap_detection` | ~80 | 40% (2/5) | Adequate, minor format drift |
| `dual_citation` | ~44 | 0% (0/5) | Critical — need 50 new triple-cite examples |
| `poam_drafting` | ~200 | 20% (1/5) | Format drift — need keyword-explicit examples |
| `atlas_mapped_ai_risk` | ~44 | 0% (0/5) | Critical — same gap as dual_citation |
| `finding_accuracy` | ~0 | 40% (2/5) | New type — need 30 new examples |

## Output produced by this audit

```
0-data-lab/mlops-loop-training/new-data/
├── dual-citation-50.jsonl       ← 50 ChatML examples: 800-53 + AI RMF + ATLAS in every response
├── finding-accuracy-30.jsonl    ← 30 ChatML examples: SSP claim + evidence → PASS/PARTIAL/FAIL
└── lineage.json                 ← Provenance record for the new examples
```

## Recommended next experiment (exp-015)

Combine `beru_training_exp012.jsonl` (1,227 examples) with:
- `dual-citation-50.jsonl` (+50)
- `finding-accuracy-30.jsonl` (+30)

Total: ~1,307 examples. Run 2 epochs. Target: dual_citation ≥ 40%, finding_accuracy ≥ 60%.
