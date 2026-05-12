# Example: JADE RAG Pipeline

> Real RAG ingestion for JADE's knowledge base — 33,000+ documents across 7 ChromaDB collections.

---

## Architecture

```
Raw docs (PDF, MD, YAML, JSONL)
  → 7-stage NPC factory (discover → preprocess → sanitize → format → label → validate)
  → nomic-embed-text (768-dim via Ollama)
  → ChromaDB (persistent, 7 collections)
  → Knowledge graph (NetworkX DiGraph)
```

---

## Collections (Mar 2026)

| Collection | Documents | Purpose |
|------------|-----------|---------|
| jade-general | 31,094 | Bulk security knowledge |
| jade-consulting | 2,247 | Playbooks, engagement guides |
| jade-nist-800-53 | 144 | Compliance controls |
| jade-terraform-iac | 136 | IaC patterns |
| jade-operational | 31 | Developer scenario training |
| concept-links | 18 | Ontology relationships |
| jade-ccsp | 6 | Cloud security domains |
| **Total** | **33,676** | |

---

## Embedding Details

- **Model:** nomic-embed-text:latest via Ollama
- **Dimensions:** 768 (MUST match ChromaDB config)
- **Zero-vector policy:** Failed embeddings quarantined to `embedding_quarantine.jsonl`, never inserted
- **CRITICAL:** Always pass `embedding_function=ollama_ef` to ChromaDB — dimension mismatch = silent failure

---

## Quality Controls

1. **PII redaction** during sanitize stage
2. **Minimum chunk length** (50 chars) — prevents meaningless fragments
3. **Maximum chunk length** (2000 chars) — prevents context dilution
4. **Overlap chunking** — 200 char overlap between chunks for continuity
5. **3-tier security labeling** — public / internal / sensitive

---

## Knowledge Graph

- **Format:** NetworkX DiGraph serialized as pickle
- **Location:** `GP-S3/knowledge-base/security_graph.pkl`
- **Purpose:** Concept relationships (e.g., "NetworkPolicy" → "pod isolation" → "zero trust")
- **Used by:** `JADE-AI/core/raggraph_engine.py` for graph-augmented retrieval

---

## Key Lessons

1. **Embedding model consistency:** Changing embedding models requires re-indexing everything
2. **Collection strategy matters:** Separate collections for different domains improve retrieval quality
3. **Quarantine, don't skip:** Zero-vector documents indicate preprocessing bugs — fix the pipeline, don't ignore them
4. **Reports after every run:** `GP-S3/3-mlops-reports/1-rag-staging/` tracks exactly what was ingested
