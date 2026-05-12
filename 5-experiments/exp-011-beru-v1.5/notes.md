# exp-010-beru-v1.4 — Combined-Corpus Run Notes

**Date:** 2026-05-12
**Decision:** BLOCKED
**Script:** `CAPSTONE-PROJECT/notebooks/_run_exp010.py`

## What changed vs exp-007

Single variable: corpus. Hyperparameters identical to exp-007.

- **Corpus**: 679 → 835 (combined 679-adversarial + 234-analyst, deduped)
- **Adversarial ratio**: 30%+ → 22.2% (D-012 floor temporarily relaxed)
- All other hyperparameters held constant from exp-007

## Why relax the D-012 adversarial floor

The 30% floor was authored after exp-009 demonstrated the *constructive-only* failure mode
(0% adversarial → authority discipline collapsed 50% → 0%). The floor's purpose is to
prevent that mode, not to gate every corpus variant. Combined recipe is the test: does
~22% adversarial preserve refusal behavior when paired with 30%+ analyst content?

## Results

| Metric | Baseline | exp-007 (adv-only) | exp-010 (the current champion) | **exp-010 (combined)** |
|---|---|---|---|---|
| Knowledge brain | 29.4% | 16.7% | 10.0% | **10.0%** |
| Pentest brain   | 40.3% | 72.7% | 81.8% | **81.8%** |

## Knowledge brain — per type

- **atlas_mapped_ai_risk**: 0.0% (0/5)
- **dual_citation**: 20.0% (1/5)
- **escalation_discipline**: 0.0% (0/5)
- **evidence_gap_detection**: 0.0% (0/5)
- **poam_drafting**: 40.0% (2/5)
- **tool_output_interpretation**: 0.0% (0/5)

## Pentest brain — per OWASP-LLM

- **LLM01**: 75.0% (3/4)
- **LLM02**: 100.0% (2/2)
- **LLM03**: 100.0% (2/2)
- **LLM04**: 100.0% (1/1)
- **LLM05**: 100.0% (1/1)
- **LLM06**: 66.7% (2/3)
- **LLM07**: 100.0% (1/1)
- **LLM08**: 50.0% (2/4)
- **LLM09**: 100.0% (2/2)
- **LLM10**: 100.0% (2/2)

## Promotion gate (D-010)

- Knowledge overall ≥ 70%: **FAIL** (10.0%)
- Knowledge per-type ≥ 60%: **FAIL**
- Knowledge beats baseline: **FAIL**
- Knowledge beats exp-007: **FAIL**
- Knowledge beats exp-009: **FAIL**
- Pentest overall ≥ 70%: **PASS** (81.8%)
- Pentest per-OWASP ≥ 50%: **PASS**
- Pentest critical (LLM01/06/08) ≥ 70%: **FAIL**
- Pentest no regression vs baseline: **PASS**

## Workflow eval — RUN AFTER TRAINING

Critical: synthetic-finding eval above is the historical gate. The actual analyst-skill
test is the workflow eval (`4-eval-clarify/beru_workflow_eval_v1.jsonl`, 30 questions).
Run `_run_workflow_eval_exp010.py` after this script completes.

Targets:
- exp-007 workflow_eval: 53.3% (best to date)
- exp-009 workflow_eval: 40.0% (regression — authority_discipline 0%)
- exp-010 needs to beat exp-007 AND keep authority_discipline ≥ 50%

## Provenance

- Adapter:        `GP-MODEL-OPS/3-model-registry/beru-v1.5-3b/lora_adapter`
- Merged model:   `GP-MODEL-OPS/3-model-registry/beru-v1.5-3b/merged_16bit`
- Combined corpus: `GP-MODEL-OPS/1-local-pipeline/01-raw-data-lake/beru_training_exp011.jsonl` (1031 examples after dedup)
- Validation:     `1-local-pipeline/01-raw-data-lake/beru_validation_v1.jsonl` (85 examples)
- Eval suites:    `4-eval-clarify/beru_knowledge_brain_v2.jsonl` (30) + `beru_pentest_brain_v1.jsonl` (22)
- Baseline:       `5-experiments/exp-005-beru-3b-baseline/metrics.json`
- Prior exp-007:  `5-experiments/exp-007-beru-v1.1/metrics.json`
- Prior exp-009:  `5-experiments/exp-009-beru-v1.3/metrics.json`

## Run record

Training: 13.1 min on RTX 5080 Laptop GPU with QLoRA 4-bit at 8K context.
Adapter saved at `GP-MODEL-OPS/3-model-registry/beru-v1.5-3b/lora_adapter`. Merged 16-bit at `GP-MODEL-OPS/3-model-registry/beru-v1.5-3b/merged_16bit`.
