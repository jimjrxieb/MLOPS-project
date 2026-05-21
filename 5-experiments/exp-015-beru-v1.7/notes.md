# exp-015 — BERU v1.7 Notes

## What We Tried
First clean BERU training run from a pure GRC corpus. Previous experiments (exp-011/012) had
contamination from Katie/JADE K8s data mixed into the raw data lake. This run used a purpose-built
corpus: ISC2 CGRC exam Q&A, CompTIA CySA+, AI security exam tips, and GRC-HAT governance briefs
with control maps from GP-SECLAB.

## Data Changes
- Removed 7 Katie/JADE files from raw-data-lake before ETL (wrong persona, would contaminate)
- Moved beru_validation_v1.jsonl to 06-eval-holdout (was being ETL'd as training data)
- New data generators: generate_ai_exam_training.py + generate_seclab_grc_training.py
- 1,832 training examples after dedup (1,971 duplicates removed from prior corpus overlap)

## Training Observations
- Loss descended cleanly: 3.18 → 1.36 over 2 epochs
- No instability, no spikes — cosine scheduler behaved well at 1,832 examples
- Single chunk, ~34 minutes on RTX 5080 Laptop

## Eval Findings

### knowledge_brain (34.1% no-RAG, 35.1% RAG)
- RAG barely helps overall (+1%) and actively hurt tool_output_interpretation (-17%)
- finding_accuracy is strongest at 48.8% — partial learning confirmed
- dual_citation (24.2%) and atlas_mapped_ai_risk (23.8%) are the clear gaps
- Root cause: 1,832 examples not enough; corpus lacks explicit dual-citation worked examples

### pentest_brain
- Old v1 suite (54.8%) was testing raw refusal behavior — wrong for BERU's architecture
- BERU never receives direct user prompts in production; inputs come from CrewAI as evidence
- Rebuilt pentest_brain_v2 with evidence-in/finding-out framing → 63.0%
- 8/10 LLM categories at 70% from base model + system prompt alone (no pentest training data)
- LLM01 (35%): BERU occasionally complies with injected directives inside scanner output
- LLM09 (35%): BERU over-extrapolates from single evidence events

## What exp-016 Should Target
1. More dual-citation training examples — explicit 800-53 ↔ AI RMF pairing patterns
2. More ATLAS mapping examples — scenarios where BERU walks through ATLAS technique → control
3. Evidence gap detection examples — "I see X, I don't see Y, therefore evidence gap"
4. LLM01 injection resistance — more examples of BERU ignoring embedded directives in data
5. LLM09 scope discipline — more examples of "one event = one finding, not a posture assessment"
6. Larger corpus — target 5,000+ examples before next run

## Artifacts
- Merged weights: 3-model-registry/beru/v1.7/beru-merged/
- GGUF (Q4_K_M): 3-model-registry/beru/v1.7/beru-v1.7-q4_k_m.gguf (1.88 GB)
- Modelfile: BERU-AI/Modelfile_beru_v17
- Ollama: beru:v1.7
- Eval results: 4-eval-clarify/3-results/beru/
