# Model Card: JADE v1.0 (8B)

## Model Details

| Field | Value |
|-------|-------|
| **Name** | jade:v1.0 |
| **Base model** | meta-llama/Llama-3.1-8B-Instruct |
| **Fine-tuning** | LoRA (r=64, alpha=128, 4-bit quantized) |
| **Parameters** | 8 billion |
| **Serving format** | GGUF (Q4_K_M) via Ollama |
| **Serving name** | `jade:v1.0` on `localhost:11434` |
| **Checkpoint** | `3-model-registry/v1.1/` |
| **Modelfile** | `3-model-registry/Modelfile_llama3b` |
| **Experiment** | `5-experiments/exp-003-jade-v1-8b/` |
| **License** | Meta LLaMA Community License |

## Intended Use

JADE is the C-rank approval engine. It's NOT just an LLM — it's the full system:

```
Finding → RAG (ChromaDB, 33k docs) → ML classifier (rank verification)
  → LangGraph (multi-step reasoning) → LLM (jade:v1.0, final decision)
```

- Makes approve/deny/escalate decisions on C-rank security findings
- Answers security questions with RAG-augmented context
- Generates fix suggestions for vulnerabilities
- Provides security analysis for Terraform, Kubernetes, and Python code

**Out of scope:** B/S rank decisions (always escalated), E/D rank fixes (Katie handles those).

## Authority

- **Maximum rank:** C (hardcoded, never change)
- **B/S rank findings:** Always escalated to human
- **Red flag patterns:** Always denied (`rm -rf`, `chmod 777`, `curl | bash`, `kubectl delete namespace`, etc.)

## Factors

| Factor | Impact | Detail |
|--------|--------|--------|
| **RAG availability** | Critical | Without RAG, accuracy drops significantly — model depends on retrieval context |
| **Domain** | High | Better at K8s security than cloud/compliance (training data gap) |
| **Fix complexity** | Medium | Simple fixes good, architectural decisions should escalate |
| **Context length** | Medium | 4096 token limit — long findings get truncated |

## Metrics

| Metric | How measured | Target | Current |
|--------|-------------|--------|---------|
| Benchmark score | `run_benchmarks.py` (10q strict) | ≥85% | 0% (eval too narrow) |
| C-rank approval accuracy | Manual review of decisions | No false approves | Not measured yet |
| Hallucination rate | Fake commands/CVEs | 0% | 0% (passing) |
| Inference latency | `JADE-AI/mlops/inference_tracker.py` | <10s | ~3-5s with RAG |
| RAG retrieval relevance | Manual sampling | Top-3 relevant | Not measured |

## Training Data

- **Corpus:** 284,844 examples (uncurated v1 corpus)
- **Known issue:** ~85% was low quality — same corpus as Katie v1
- **Domains:** kubernetes (38.5%), general (23.0%), devsecops (16.1%), cloud (12.1%), compliance (3.8%), secrets (3.3%), terraform (3.3%)
- **No corpus SHA256** — v1 raw data lake had 100+ files, no single hash recorded

## Evaluation

| Metric | Score |
|--------|-------|
| Benchmark (10-question strict keyword) | 0.0% |
| Hallucinations | 0 |

**Context:** The 0% reflects a 10-question eval with strict keyword matching. The model generates useful, contextual security analysis in practice — especially with RAG. The eval framework was too narrow, not the model.

**Not formally evaluated with:** 466-question bridge eval, platform engineering domains, RAG-augmented eval.

## Limitations

- Trained on same uncurated corpus as Katie v1 — same data quality issues
- No formal promotion gate was passed — deployed based on qualitative assessment
- Depends heavily on RAG context (without it, answers are generic)
- C-rank approval accuracy has never been measured quantitatively
- 0% on formal benchmark (eval mismatch, not model failure — but still a gap)

## Ethical Considerations

- Model approves fixes that agents auto-apply — wrong approval = production impact
- C-rank authority ceiling is hardcoded, not learned — model could hallucinate permission to act on B/S rank
- FedRAMP: LLaMA is US-based, local inference, no data leaves network
- Red flag patterns are a hardcoded blocklist, not model behavior — model could suggest dangerous commands that aren't on the list

## Risks

| Risk | Mitigation |
|------|-----------|
| False approval on C-rank fix | Authority ceiling in code, not model weights |
| Generic advice without RAG | RAG is required dependency, not optional |
| Knowledge gaps (cloud, hardening) | Known — curated training planned (exp-005) |

## Next Steps

JADE v2 planned using curated corpus (exp-002 methodology applied to 8B). Blocked by:
- [ ] exp-002 proving curation works on Katie 3B first
- [ ] Expanded eval suite (466+ questions including platform eng)
- [ ] Must pass promotion gate before replacing jade:v1.0
