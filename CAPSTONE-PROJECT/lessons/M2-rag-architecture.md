# M2 — RAG Architecture

> **Goal:** Understand why RAG exists and build a retrieval pipeline that grounds BERU in real control text.
> **Build:** Populate the `beru-nist-800-53` ChromaDB collection from `GP-CONSULTING/NIST-800-53/controls/`.
> **Gate:** Query "least privilege access" returns AC-6. Query "network boundary" returns SC-7.

---

## The Problem RAG Solves

LLMs know NIST 800-53 from training data — but vaguely, like someone who read a summary once. They might confuse AC-6 and AC-3. They don't know the specific wording in your organization's control implementation guide. They definitely don't know what your last Prowler scan found.

RAG (Retrieval-Augmented Generation) solves this by injecting the exact relevant text into every prompt. Before the model answers, the pipeline looks up the relevant controls and includes them verbatim in the context. The model then cites what it was given, not what it guessed.

**The analogy:** Imagine an open-book exam. Without RAG, the model is doing the exam from memory — plausible answers, possible errors. With RAG, you hand the model the relevant textbook page before it answers. It still writes the answer in its own words, but the facts come from the page you gave it, not its imperfect memory.

**The design decision this connects to:** `beru-design-decisions.md D-002` — "NIST 800-53 control text is in ChromaDB (RAG), not baked into weights via training." The reason: NIST releases revisions. Updating ChromaDB is one ingestion run. Retraining the model takes weeks.

---

## Concept 1 — Embeddings

### What they are
An embedding is a list of numbers (a vector) that represents the *meaning* of a piece of text. Similar texts produce vectors that are close together in this high-dimensional space.

```
"least privilege access controls" → [0.12, -0.45, 0.89, 0.03, ...] (768 numbers)
"AC-6 Least Privilege"            → [0.11, -0.43, 0.91, 0.02, ...] (similar!)
"network firewall rules"          → [-0.78, 0.23, -0.12, 0.67, ...] (far away)
```

The model we use: `nomic-embed-text` via Ollama. It outputs 768-dimensional vectors.

**Why 768 dimensions matters:** ChromaDB stores these vectors. When you create a collection, the dimension is fixed. If you ingest with 768-dim embeddings and then query with 1536-dim embeddings (e.g., OpenAI ada-002), ChromaDB silently fails or errors. This is the #1 RAG debugging issue.

### The analogy
Think of words arranged in physical space by meaning. "King" and "Queen" are close. "King" and "Database" are far. Embeddings are coordinates in that meaning-space. Retrieval is: "find the coordinates closest to my query."

---

## Concept 2 — The Retrieval Pipeline

Five steps, same every time:

```
1. Chunk documents     → split control text into ~500-word chunks
2. Embed each chunk    → convert text to 768-dim vector
3. Store in ChromaDB   → save vector + text + metadata (control_id, family)
4. Embed user query    → convert "least privilege" to vector
5. Similarity search   → find the 5 chunks whose vectors are closest to the query
```

Steps 1-3 run once (ingestion). Steps 4-5 run on every BERU query (retrieval).

```python
# Simplified retrieval in BERU context
import chromadb
from chromadb.utils import embedding_functions

# CRITICAL: must use same embedding function that was used for ingestion
ollama_ef = embedding_functions.OllamaEmbeddingFunction(
    url="http://localhost:11434/api/embeddings",
    model_name="nomic-embed-text",
)

client = chromadb.PersistentClient(path="2-rag-ingestion/05-ragged-data/chroma/")
collection = client.get_collection(
    name="beru-nist-800-53",
    embedding_function=ollama_ef,  # ← NEVER omit this
)

results = collection.query(
    query_texts=["least privilege access controls"],
    n_results=3,
)
# results["documents"][0] → list of 3 matching text chunks
# results["metadatas"][0] → list of 3 metadata dicts (control_id, family, etc.)
```

---

## Concept 3 — Chunking Strategy

### Why chunking matters
Control text can be long — AC-2 has 20+ sub-requirements. If you store the entire control as one chunk, a query about "account termination" might not retrieve it because the account termination content is 80% through the document. If you chunk it, the termination-specific text has its own vector that matches the query.

### What good chunks look like for BERU

| Chunk | Size | Metadata |
|-------|------|----------|
| One control enhancement (e.g., AC-6(5)) | ~200-400 words | `control_id: AC-6`, `enhancement: 5`, `family: AC` |
| One SSP implementation statement | ~100-300 words | `control_id: SI-2`, `system: NovaSec`, `status: PARTIAL` |
| One POA&M item | ~50-150 words | `control_id: AC-2`, `chunk_type: poam_item` |

The `SSPParser` we built (`BERU-AI/tools/ssp_parser.py`) does exactly this — it splits SSPs into per-control chunks with metadata. Each chunk gets its own row in ChromaDB.

### What bad chunking looks like
- Chunks so large they contain 10 different topics → retrieval returns noise
- Chunks so small they have no context → retrieval returns meaningless fragments
- No metadata → you get the text back but can't tell what control it's from

---

## Concept 4 — ChromaDB Collections

ChromaDB organizes vectors into **collections** — one per use case. Think of collections like tables in a database.

This repo's collections (from `2-rag-ingestion/`):
- `jade-general` — 31,094 docs (broad security knowledge for JADE)
- `jade-nist-800-53` — 144 docs (NIST controls for JADE)
- `beru-nist-800-53` — **this is what M2 builds** (NIST controls + SSP examples for BERU)

Why a separate collection for BERU? Different retrieval needs. JADE needs broad security context. BERU needs precise control text with evidence questions and implementation quality examples. Mixing them degrades both.

```python
# Creating a new collection
client.get_or_create_collection(
    name="beru-nist-800-53",
    embedding_function=ollama_ef,
    metadata={"hnsw:space": "cosine"},  # cosine similarity for text
)
```

---

## Concept 5 — The Ingestion Pipeline in This Repo

The existing RAG pipeline lives in `2-rag-ingestion/`. The BERU ingestion will use it.

Source documents for `beru-nist-800-53`:
1. `GP-CONSULTING/NIST-800-53/controls/` — one `.md` file per control, with evidence questions
2. `CAPSTONE-PROJECT/frameworks/nist-ai-600-1/` — AI RMF GOVERN/MAP/MANAGE subcategories
3. `CAPSTONE-PROJECT/frameworks/crosswalk/800-53-to-ai-rmf.md` — the bidirectional mapping
4. Gemini-generated synthetic SSPs (when you generate them) → parsed by `SSPParser`

The ingestion script that already works:
```bash
cd 2-rag-ingestion/04-ingesting/
python3 ingest_to_chromadb.py  # ← you will point this at the BERU source docs
```

Key config it needs:
```python
EMBEDDING_MODEL = "nomic-embed-text"  # 768-dim — never change this mid-collection
COLLECTION_NAME = "beru-nist-800-53"
CHROMA_PATH = "2-rag-ingestion/05-ragged-data/chroma/"
```

---

## Troubleshooting M2

| Symptom | Cause | Fix |
|---------|-------|-----|
| Query returns wrong controls | Embedding model mismatch | Check collection was built with `nomic-embed-text`. Delete and rebuild if wrong. |
| `InvalidDimensionException` | Different embedding dim at query vs ingest | Always pass `embedding_function=ollama_ef` to `get_collection()` |
| Query returns empty results | Ollama not running | `ollama serve` in another terminal; check `curl http://localhost:11434/api/tags` |
| Chunks have no metadata | Parser not attaching metadata | Check `SSPParser._make_chunk()` — `control_id`, `family`, `chunk_type` must all be set |
| Same chunk appears multiple times | No dedup | `SSPParser` uses content-hashed `id` — same content = same ID. ChromaDB `upsert` handles this. |
| Collection doesn't exist error | Wrong path or name | `client.list_collections()` to see what's actually there |
| Retrieval is slow | Too many chunks | Reduce `n_results` from 10 to 3. BERU only needs the top few. |

---

## What You Build

The M2 build is the ingestion run that creates `beru-nist-800-53`.

```bash
# Step 1: Make sure Ollama is running and has nomic-embed-text
ollama pull nomic-embed-text
curl http://localhost:11434/api/tags  # should show nomic-embed-text

# Step 2: Run ingestion pointing at NIST control files
# (we'll write this script — it reads GP-CONSULTING/NIST-800-53/controls/)

# Step 3: Verify retrieval works
python3 -c "
import chromadb
from chromadb.utils import embedding_functions

ollama_ef = embedding_functions.OllamaEmbeddingFunction(
    url='http://localhost:11434/api/embeddings',
    model_name='nomic-embed-text',
)
client = chromadb.PersistentClient(path='2-rag-ingestion/05-ragged-data/chroma/')
col = client.get_collection('beru-nist-800-53', embedding_function=ollama_ef)
results = col.query(query_texts=['least privilege'], n_results=3)
print(results['metadatas'])
"
# Expected: [{'control_id': 'AC-6', ...}] in the results
```

**3PAO question this answers:** "How does BERU know what AC-6 actually says? Is it guessing?"
Your answer: "BERU retrieves the exact control text from ChromaDB before producing every finding. The control text is ingested from the NIST 800-53 control library — same source as the published standard."

---

## Control Traceability

> When an auditor asks "what's in that ChromaDB? Is any client data in there?" — point here.

**NIST 800-53:**

| Control | What it maps to in M2 | Audit answer |
|---------|----------------------|--------------|
| **SC-28** — Protection of Information at Rest | `SSPParser` rejects any SSP without a synthetic marker — real client SSPs cannot enter the ChromaDB corpus | "The RAG corpus only contains synthetic data. `SSPParser._validate_source()` enforces this at ingest time. Real client SSPs raise `ValueError` and are never inserted." |
| **AU-3** — Content of Audit Records | Every ChromaDB chunk retains `source_file`, `ingested_at`, `collection`, and `control_id` — provenance is never stripped | "Every document in ChromaDB has full provenance. We can trace any retrieved chunk back to its source file and ingest timestamp." |
| **SI-12** — Information Management and Retention | Synthetic SSPs in `training-data/raw-ssps/`, processed chunks in `05-ragged-data/chroma/` — data lifecycle is defined and one-way | "Data flows in one direction: raw → preprocessed → ChromaDB. No raw client data enters the pipeline." |

**NIST AI RMF:**

| Subcategory | What it maps to | Audit answer |
|-------------|----------------|--------------|
| **MAP-4.1** — Practices are in place to evaluate AI risks from data collection | Synthetic marker enforcement prevents real PII, PHI, and client confidential data from entering BERU's training corpus | "MAP-4.1 is implemented by the synthetic marker check in `SSPParser`. The design decision is documented in `beru-design-decisions.md D-005`." |
| **GOVERN-1.7** — Processes for AI risk management are in place | The ChromaDB collection structure (`beru-nist-800-53`) is designed so BERU retrieves authoritative NIST text, not internet noise | "BERU's RAG knowledge base is scoped to NIST 800-53 and AI RMF source documents. It cannot retrieve arbitrary web content." |
