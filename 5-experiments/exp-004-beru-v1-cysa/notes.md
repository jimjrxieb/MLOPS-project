# Experiment 004: BERU v1 — CySA+/NIST Fine-Tune

## Hypothesis

LLaMA 3.1-8B-Instruct can learn scanner output triage patterns and accurate NIST 800-53 control mapping from real seclab findings, producing CISO-ready risk summaries that are structured (JSON) and narrative.

## Status

**Scaffold complete.** Training blocked on real scanner data.

## What's Done

- [x] Directory structure (BERU-AI/)
- [x] Config files (system prompt, domain weights, scanner mappings, risk templates)
- [x] Data schemas (training example, risk summary)
- [x] Core modules (parser, ingestion, NIST mapper, triage engine, risk summary generator)
- [x] Providers (Ollama with fallback)
- [x] GP-API endpoints (/api/beru/*)
- [x] Eval suite (20 seed questions across 5 domains)
- [x] Tests (schema validation, core module unit tests)

## What's Next

1. Populate `0-data-lab/seclab-findings/` with real scanner output
2. Run `classify_seclab_findings.py` to tag data for BERU
3. Build training data generators from real findings
4. Train chunk 1 and evaluate
5. Expand eval suite to ~400 questions

## Observations

(To be filled during training)
