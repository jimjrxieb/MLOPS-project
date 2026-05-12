# Playbook 06 — Setup RAG Pipeline

> Deploy the RAG ingestion pipeline: preprocess → embed → ingest → validate.
> **When:** Alongside or after training pipeline (Playbook 05)
> **Time:** 3-4 hours

---

## Prerequisites

- [ ] Ollama running with `nomic-embed-text` model
- [ ] ChromaDB (local or server mode)
- [ ] Python 3.10+ with chromadb, sentence-transformers

---

## Phase 1: Embedding Model Setup

```bash
# Pull embedding model
ollama pull nomic-embed-text:latest

# Verify dimensions (MUST be 768)
curl http://localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "test"
}' | python3 -c "import sys,json; print(len(json.load(sys.stdin)['embedding']))"
# Expected: 768
```

**CRITICAL:** nomic-embed-text produces 768-dimension vectors. Dimension mismatch with ChromaDB = silent failure. Always pass `embedding_function=ollama_ef` to ChromaDB.

---

## Phase 2: Document Preprocessing

```bash
# Drop raw documents into intake directory
ls 2-rag-ingestion/01-unprocessed/

# Run preprocessing stages
cd 2-rag-ingestion/02-preperation-factory/

# Stage 1: Discover files (PDF, MD, YAML, JSONL, TXT)
python3 -m stages.discover

# Stage 2: Parse formats (PDF extraction, markdown splitting)
python3 -m stages.preprocess

# Stage 3: Quality gates + PII redaction
python3 -m stages.sanitize_npc

# Stage 4: Normalize to JSONL with overlap chunking
python3 -m stages.format_conversion_npc

# Stage 5: 3-tier security labeling
python3 -m stages.labeling_npc

# Stage 6: Validate + build _embedding_text field
python3 -m stages.validators
```

---

## Phase 3: Ingest into ChromaDB

```bash
# Embed and ingest
python3 2-rag-ingestion/04-ingesting/ingest_to_chromadb.py
```

**What happens:**
- Reads preprocessed JSONL from staging
- Generates embeddings via Ollama (nomic-embed-text)
- Inserts into ChromaDB collections
- Failed embeddings quarantined to `embedding_quarantine.jsonl` (zero-vector policy)
- Builds knowledge graph (NetworkX DiGraph)
- Writes ingestion report to `GP-S3/3-mlops-reports/1-rag-staging/`

**Collection strategy:**
```
jade-general          → Bulk security knowledge
jade-kubernetes       → K8s-specific docs
jade-consulting       → Playbooks, engagement guides
jade-nist-800-53      → Compliance controls
jade-terraform-iac    → IaC patterns
jade-operational      → Developer scenarios
concept-links         → Ontology relationships
```

---

## Phase 4: Validate Ingestion

```bash
# Check collection counts
python3 -c "
import chromadb
client = chromadb.PersistentClient(path='2-rag-ingestion/05-ragged-data/chroma/')
for col in client.list_collections():
    print(f'{col.name}: {col.count()} docs')
"

# Test retrieval quality
python3 -c "
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
ollama_ef = OllamaEmbeddingFunction(model_name='nomic-embed-text', url='http://localhost:11434/api/embeddings')
client = chromadb.PersistentClient(path='2-rag-ingestion/05-ragged-data/chroma/')
col = client.get_collection('jade-general', embedding_function=ollama_ef)
results = col.query(query_texts=['pod running as root fix'], n_results=3)
for doc in results['documents'][0]:
    print(doc[:200])
    print('---')
"
```

---

## Phase 5: Bridge RAG to Training (Optional)

```bash
# Convert high-quality RAG docs into training examples
python3 2-rag-ingestion/migrate_rag_to_training.py
```

This creates Q&A pairs from RAG documents and outputs them to `1-data-pipeline/01-raw-data-lake/` for the training pipeline.

---

## What Next

| Status | Next Playbook |
|--------|---------------|
| RAG pipeline working | `07-setup-model-eval.md` |
| Need to eval model with RAG | `07-setup-model-eval.md` |
| Ready to serve | `08-deploy-model-serving.md` |
