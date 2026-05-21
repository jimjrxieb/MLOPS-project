# 4-eval-clarify — Evaluation Engine

This is where models get interrogated before they're allowed to serve. Two eval suites, both required. No model moves to production without passing both.

**Promotion gate:** ≥70% knowledge brain + ≥70% pentest brain. Per-type floor: 60%. Zero hallucinated control IDs.

---

## Active Eval Suites

### Knowledge Brain (`beru_knowledge_brain_v2.jsonl`)

30 questions across 6 types that test BERU's GRC reasoning:

| Type | What it tests | v1.6 | v1.7 |
|------|--------------|------|------|
| `finding_accuracy` | SSP claim + real evidence → PASS / PARTIAL / FAIL | 40% | 48.8% |
| `poam_drafting` | Write a complete POA&M item from a finding | 20% | 39.6% |
| `tool_output_interpretation` | Read scanner output → control ID + status | 20% | 39.3% |
| `evidence_gap_detection` | What's missing for a PASS? | 40% | 29.2% |
| `dual_citation` | 800-53 control + AI RMF subcategory simultaneously | 0% | 24.2% |
| `atlas_mapped_ai_risk` | Map AI system risk to MITRE ATLAS technique | 0% | 23.8% |
| **Overall** | | **20.0%** | **34.1%** |

Gate: 70% overall / 60% per type. Neither version promoted yet.

### Pentest Brain (`beru_pentest_brain_v2.jsonl`)

22 questions mapped to OWASP LLM Top 10, framed as **evidence-in / finding-out** — matching BERU's production context where inputs arrive as scanner output and evidence reports, not direct user prompts.

| Category | v1.6 (PB v1) | v1.7 (PB v2†) |
|----------|-------------|--------------|
| LLM01 Prompt Injection | 75% | 35% |
| LLM02–07, LLM08, LLM10 | varies | 70% each |
| LLM09 Scope Discipline | 100% | 35% |
| **Overall** | **68.2%** | **63.0%** |

†PB v2 uses evidence-in/finding-out framing — scores are not directly comparable to PB v1.

### Workflow Brain (`beru_workflow_eval_v1.jsonl`)

End-to-end scenario tests: given a full scanner output, produce a complete structured finding (all 9 fields). Tests the full BERU workflow, not individual capabilities.

### SSP Grading (`eval_ssp_grading.py`)

Grades SSP narrative quality against bad / good / great rubric. Results tracked per experiment in `3-results/beru/ssp_grading/`.

---

## Running Evals

```bash
# Run knowledge brain (requires Ollama with beru:vX.X loaded)
python3 beru_eval_runner.py --suite knowledge --model beru:v1.7

# Run pentest brain
python3 beru_eval_runner.py --suite pentest --model beru:v1.7

# Run both (full promotion gate check)
python3 beru_eval_runner.py --suite all --model beru:v1.7

# Results written to 3-results/beru/
```

---

## Directory Structure

```text
4-eval-clarify/
  beru_eval_runner.py            ← main eval runner (knowledge + pentest + workflow)
  eval_ssp_grading.py            ← SSP quality grader (bad/good/great tier)
  build_workflow_eval.py         ← workflow eval builder
  workflow_scorer.py             ← workflow eval scorer
  BENCHMARK_FRAMEWORK.md         ← original JADE eval design (historical reference)
  2-test-data/
    evaluation/                  ← domain Q&A benchmarks for JADE/Katie (CKS, CKA, cloud, etc.)
    beru/
      knowledge_brain_v2.jsonl   ← 30-question GRC reasoning suite (current)
      pentest_brain_v2.jsonl     ← 22-question OWASP LLM Top 10 suite (evidence-in framing)
      workflow_eval_v1.jsonl     ← end-to-end 9-field finding scenarios
    training-data/               ← faulty + fixed examples (JADE/Katie training artifacts)
  3-results/
    beru/
      knowledge_brain/           ← per-run KB eval JSON (gitignored)
      pentest_brain/             ← per-run PB eval JSON (gitignored)
      ssp_grading/               ← SSP grading results exp-010 → exp-012 (tracked)
  archive/                       ← superseded suites and old scripts
```

---

## Eval Design Principles

**Test behavior, not knowledge recall.** A model that can recite NIST control names but can't correctly grade a PASS/PARTIAL/FAIL from real evidence is useless for GRC work.

**Question types must match the job.** Early eval suites included `escalation_discipline` questions (would BERU refuse to output a report until a human approved it). Wrong mental model — BERU produces documents. Replaced with `finding_accuracy` in exp-014.

**Suite framing must match production context.** The original pentest brain tested raw refusal behavior. BERU never receives direct user prompts in production — inputs arrive as CrewAI evidence reports. Pentest brain v2 reflects this with evidence-in / finding-out framing.

**Separate the suites.** Knowledge brain tests subject matter expertise. Pentest brain tests adversarial robustness. They measure different things and a model can fail one while passing the other.
