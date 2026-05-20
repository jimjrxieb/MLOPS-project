# 4-eval-clarify — Evaluation Engine

This is where models get interrogated before they're allowed to serve. Two eval suites, both required. No model moves to production without passing both.

**Promotion gate:** ≥70% knowledge brain + ≥70% pentest brain. Per-type floor: 60%. Zero hallucinated control IDs.

---

## Eval Suites

### Knowledge Brain (`beru_knowledge_brain_v2.jsonl`)

30 questions across 6 types that test BERU's GRC reasoning:

| Type | What it tests | Count |
|------|--------------|-------|
| `finding_accuracy` | Given SSP claim + real evidence → PASS / PARTIAL / FAIL | 5 |
| `evidence_gap_detection` | What's missing for a PASS? | 5 |
| `poam_drafting` | Write a complete POA&M item from a finding | 5 |
| `tool_output_interpretation` | Read scanner output → control ID + status | 5 |
| `dual_citation` | 800-53 control + AI RMF subcategory simultaneously | 5 |
| `atlas_mapped_ai_risk` | Map AI system risk to MITRE ATLAS technique | 5 |

Current gap: `dual_citation` 0%, `tool_output_interpretation` 20%. These are the targets for the next corpus generation.

### Pentest Brain (`beru_pentest_brain_v1.jsonl`)

22 questions mapped to OWASP LLM Top 10. Tests whether BERU correctly handles adversarial prompts, data poisoning scenarios, and LLM-specific attack surfaces.

| Category | Weight | Current (exp-014) |
|----------|--------|-------------------|
| LLM01 Prompt Injection | — | 75% |
| LLM04 Data/Model Poisoning | — | 100% |
| LLM07 System Prompt Leakage | — | 100% |
| LLM09 Misinformation | — | 100% |
| LLM10 Unbounded Consumption | — | 100% |
| LLM06 Excessive Agency | — | 67% |
| LLM08 Vector/Embedding Weakness | — | 50% ← needs work |
| LLM02 Sensitive Info Disclosure | — | 50% |
| LLM03 Supply Chain | — | 50% |
| LLM05 Improper Output Handling | — | 0% |

### Workflow Brain (`beru_workflow_eval_v1.jsonl`)

End-to-end scenario tests: given a full scanner output, produce a complete structured finding (all 9 fields). Tests the full BERU workflow, not individual capabilities.

---

## Running Evals

```bash
# Run knowledge brain eval (requires Ollama with beru:vX.X loaded)
python3 beru_eval_runner.py --suite knowledge --model beru:v1.6

# Run pentest brain
python3 beru_eval_runner.py --suite pentest --model beru:v1.6

# Run both (full gate check)
python3 beru_eval_runner.py --suite all --model beru:v1.6

# Results go to 3-results/beru/
```

---

## Directory Structure

```text
4-eval-clarify/
  beru_eval_runner.py          ← main eval runner
  beru_knowledge_brain_v2.jsonl ← 30 KB questions (current)
  beru_pentest_brain_v1.jsonl  ← 22 PB questions
  beru_workflow_eval_v1.jsonl  ← end-to-end workflow scenarios
  eval_ssp_grading.py          ← SSP quality grader (good/great tier)
  workflow_scorer.py           ← workflow eval scorer
  BENCHMARK_FRAMEWORK.md       ← original JADE eval design (historical)
  1-model-registry/            ← model manifest per eval run
  2-test-data/
    evaluation/                ← domain Q&A benchmarks (CKS, CKA, cloud, etc.)
    beru/                      ← BERU-specific test fixtures
    training-data/             ← faulty + fixed examples for eval testing
  3-results/                   ← raw eval output per run (gitignored)
```

---

## Eval Design Principles

**Test behavior, not knowledge recall.** A model that can recite NIST control names but can't correctly grade a PASS/PARTIAL/FAIL from real evidence is useless for GRC work.

**Question types must match the job.** Early eval suites included `escalation_discipline` questions (would BERU refuse to output a report until a human approved it). Wrong mental model — BERU produces documents. It doesn't gate on approvals. Replaced with `finding_accuracy` in exp-014.

**Separate the suites.** Knowledge brain tests subject matter expertise. Pentest brain tests adversarial robustness. They measure different things and a model can fail one while passing the other.
