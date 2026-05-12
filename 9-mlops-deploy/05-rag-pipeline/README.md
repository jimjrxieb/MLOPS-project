# 05-RAG Pipeline

Configuration and templates for RAG (Retrieval-Augmented Generation) ingestion.

## Contents

- `configs/chromadb.yaml` — ChromaDB collection config and embedding settings
- `templates/collection-schema.json` — Collection metadata schema

## Pipeline Stages

1. **Discover** — Find files (PDF, MD, YAML, JSONL, TXT)
2. **Preprocess** — Parse formats (PDF extraction, markdown splitting)
3. **Sanitize** — Quality gates + PII redaction
4. **Format** — Normalize to JSONL with overlap chunking
5. **Label** — 3-tier security labeling
6. **Validate** — Build `_embedding_text` field
7. **Ingest** — Embed via nomic-embed-text (768-dim) → ChromaDB

## Critical Details

- **Embedding model:** nomic-embed-text via Ollama, 768 dimensions
- **MUST pass** `embedding_function=ollama_ef` to ChromaDB — dimension mismatch = silent failure
- **Zero-vector policy:** Failed embeddings quarantined, never inserted

## Related

- Playbook `06-setup-rag-pipeline.md`
- Actual pipeline: `GP-MODEL-OPS/2-rag-ingestion/`
