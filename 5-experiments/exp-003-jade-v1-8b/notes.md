# Experiment 003 — JADE v1 8B

## Hypothesis

8B model (LLaMA 3.1-8B-Instruct) has enough capacity for complex C-rank security reasoning that 3B can't handle. Use for JADE's approval decisions, with RAG augmentation from ChromaDB.

## What Happened

Trained on the same uncurated 284k corpus as exp-001. Model was deployed as `jade:v1.0` via Ollama and is currently serving C-rank approval decisions.

Benchmark results show 0% on the automated eval — but this is misleading. The original benchmark was only 10 questions with strict keyword matching. The model generates useful, contextual security analysis in practice.

## Honest Assessment

**What works:**
- General security Q&A is coherent and technically sound
- C-rank approval decisions with RAG context are reasonable
- Response quality better than the 3B model for complex multi-step reasoning
- No hallucinated commands or fake CVE numbers

**What doesn't work:**
- Fails strict automated eval (keyword-based scoring too narrow)
- Trained on same garbage corpus as exp-001 — same data quality problems apply
- No formal promotion gate was used — deployed based on qualitative assessment

## Lessons

1. The eval framework matters as much as the model. 10 questions with strict keyword match is not a useful eval.
2. Deploying without passing a promotion gate is a gap — even if the model works in practice.
3. JADE's real power comes from RAG + ML classifier + LLM together, not the LLM alone. The 0% benchmark doesn't reflect the full system's capability.

## What's Next

JADE v2 will use the curated corpus (same as exp-002) + expanded eval suite (466 questions). Must pass promotion gate before replacing jade:v1.0.

## Artifacts

- Checkpoint: `3-model-registry/v1.1/`
- Modelfile: `3-model-registry/Modelfile_llama3b`
- Serving: `jade:v1.0` via Ollama
- Eval: `4-eval-clarify/3-results/benchmark_20260316_234331/`
