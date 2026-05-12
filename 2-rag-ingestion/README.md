# 2-rag-ingestion: RAG Pipeline

Retrieval-Augmented Generation pipeline for the JSA AI fleet (JADE, Katie, BERU). Ingests security knowledge into ChromaDB vector embeddings + NetworkX knowledge graph for contextual responses.

**Two ingest paths live here:**
- `04-ingesting/ingest_to_chromadb.py` — JADE's bulk ingest. Runs the 7-stage prep factory at `02-preperation-factory/stages/` (discover → preprocess → sanitize → format-conversion → labeling → validators → ingest). Used for messy bulk content (Claude Code sessions, scraped docs, YouTube transcripts, JSA logs).
- `04-ingesting/ingest_beru_to_chromadb.py` — BERU's curated-corpus ingest. Reads hand-authored markdown directly from `GP-CONSULTING/NIST-800-53/controls/` and `CAPSTONE-PROJECT/frameworks/` — the JADE prep stages don't fit curated content. See `2-rag-ingestion/01-unprocessed/beru-frameworks/README.md` for the source-file pointer index. Rationale documented in `CAPSTONE-PROJECT/beru-design-decisions.md` D-008 + D-011.

Both write to the same ChromaDB store at `05-ragged-data/chroma/` but to different collections (`jade-*` vs `beru-nist-800-53`).

## Architecture

```
01-unprocessed/            Raw files drop here
       |
02-preperation-factory/    NPC assembly line (7 stages)
       |
03-preprocessed/           Quality-reviewed JSONL
       |
04-ingesting/              Embed + store
       |
05-ragged-data/            ChromaDB vectors + knowledge graph
       |
JADE-AI/core/              Query-time retrieval (hybrid RAG+Graph)
```

## Directory Structure

```
GP-OPENSEARCH/
├── 01-unprocessed/                  # Raw ingestion sources
│   ├── claudecode-sessions/         # Claude Code session transcripts
│   ├── consulting-knowledge/        # Client consulting knowledge
│   ├── jsa-logs/                    # JSA agent operational logs
│   ├── npc-templates/               # NPC template definitions
│   ├── opa-policies/                # OPA/Rego policy files
│   ├── operational-training-data/   # JSA operational training data
│   ├── webscraper/                  # Scraped security documentation
│   ├── windows-sync/                # Windows-synced content
│   └── yt-transcripts/              # YouTube transcript data
│
├── 02-preperation-factory/          # NPC assembly line
│   └── stages/
│       ├── discover.py              # File discovery (22 categories)
│       ├── preprocess.py            # Format-specific parsers
│       ├── sanitize_npc.py          # Quality gates (PASS/REPAIR/FAIL)
│       ├── format_conversion_npc.py # Normalize to JSONL + overlap chunking
│       ├── labeling_npc.py          # 3-tier labeling (ontology/pattern/Claude)
│       ├── validators.py            # Format validation + token estimation
│       ├── route.py                 # Collection routing (RAG/SQL/BOTH)
│       └── cleanup.py               # Post-processing cleanup
│
├── 03-preprocessed/                 # Quality-reviewed output (JSONL)
│
├── 04-ingesting/                    # Embedding + storage
│   ├── ingest_to_chromadb.py        # ChromaDB + NetworkX ingestion
│   └── rag_cleanup.py               # Concept linking + cleanup
│
├── 05-ragged-data/                  # Final storage
│   ├── chroma/                      # ChromaDB persistent store
│   ├── rag-processed/               # Ingested file archive
│   ├── jsa-docs/                    # JSA documentation
│   └── raw-data/                    # Additional raw data
│
├── manifest.json                    # Pipeline metadata + collection stats
├── migrate_rag_to_training.py       # RAG-to-training data migration
└── README.md                        # This file
```

## Pipeline Stages

### Stage 1: Discovery (`discover.py`)
Scans `01-unprocessed/` recursively for `.jsonl`, `.json`, `.md`, `.txt`, `.rego`, `.yaml` across 22 source categories.

### Stage 2: Preprocessing (`preprocess.py`)
Format-specific parsers:
- **JSONL**: Line-by-line JSON parsing
- **JSON**: Structure-aware parsing
- **Markdown**: Header-aware splitting
- **Rego**: Package/rule/comment extraction with policy type detection
- **YAML**: K8s manifest and config parsing

### Stage 3: Sanitization (`sanitize_npc.py`)
Quality gates with three outcomes: **PASS**, **REPAIR**, **FAIL**
- SHA256 content deduplication
- PII redaction (emails, API keys, passwords, filesystem paths)
- Control character removal and whitespace normalization
- JSON repair for malformed LLM output (Qwen double-escaping, trailing commas)

### Stage 4: Format Conversion (`format_conversion_npc.py`)
Normalizes all formats to JSONL with overlap chunking:
- **Target chunk size**: 512 tokens (~2048 chars)
- **Overlap**: 64 tokens (~256 chars) — 12.5% between consecutive chunks
- **Boundary detection**: Splits on sentence boundaries (`. ` / `! ` / `? `) when possible
- **Markdown**: Split by headers first, then sub-split long sections with overlap
- **Text**: Token-aware overlap chunking (replaces naive paragraph splitting)
- **JSON repair**: Handles LLM output artifacts (markdown blocks, double-escaping)

### Stage 5: Labeling (`labeling_npc.py`)
3-tier intelligent labeling:
- **Tier 1**: SecurityOntology — fast regex (CVE, CWE, scanner codes)
- **Tier 2**: Pattern matching — filename and content regex (domain, type, difficulty)
- **Tier 3**: Claude API — semantic classification fallback (optional)

Produces: `domain`, `type`, `difficulty`, `tags` metadata per document.

### Stage 6: Validation (`validators.py`)
- Format-specific validation (Rego package declarations, JSON structure)
- Token estimation (1 token ~ 4 chars, truncates at ~7000 tokens)
- Constructs `_embedding_text` field combining metadata + content for richer embeddings

### Stage 7: Routing (`route.py`)
Routes items to destination collections based on category:
- `jade-general` — Default security knowledge
- `jade-domain-sme` — Domain-specific expert knowledge
- `jade-projects` — Project documentation
- `jade-kubernetes` — K8s-specific content
- Plus specialized collections per source type

## Ingestion

### ChromaDB + Knowledge Graph (`ingest_to_chromadb.py`)

```bash
# Ingest all preprocessed data
python3 04-ingesting/ingest_to_chromadb.py

# Preview without ingesting
python3 04-ingesting/ingest_to_chromadb.py --dry-run

# Specific file only
python3 04-ingesting/ingest_to_chromadb.py --file processed_20260127.jsonl

# ChromaDB only (skip graph)
python3 04-ingesting/ingest_to_chromadb.py --skip-graph
```

Key behaviors:
- **Deterministic IDs**: `md5(content|source_file|chunk_idx)[:16]` — enables upsert deduplication
- **Embedding retry**: Retries failed embeddings 2x with 1s delay, skips on final failure
- **No zero-vectors**: Failed embeddings are quarantined to `05-ragged-data/embedding_quarantine.jsonl`, never inserted as zero-vectors
- **Flat metadata**: Nested dicts/lists flattened for ChromaDB compatibility
- **Knowledge graph**: Document nodes linked to domain/type/tag entities via NetworkX
- **Security ontology**: Concept linking via SecurityOntology when available

### Concept Linking (`rag_cleanup.py`)
- Removes generic definitions (30+ regex patterns)
- Builds error-to-fix and scanner-to-agent concept links
- Ingests links to `concept-links` ChromaDB collection

## Query-Time Retrieval

JADE queries via `JADE-AI/core/raggraph_engine.py` (hybrid RAG+Graph):

```python
from core.raggraph_engine import get_raggraph_engine

engine = get_raggraph_engine()

# Hybrid search (vector + graph, default)
results = engine.query("How to fix SQL injection in Kubernetes?")

# Vector-only
results = engine.query("pod security policy", mode="vector")

# Graph-only
results = engine.query("CVE-2023-12345", mode="graph")
```

**Hybrid query flow:**
1. Query expansion via SecurityOntology (adds related security concepts)
2. ChromaDB vector search (semantic similarity)
3. NetworkX graph traversal (entity relationships → actual document content from ChromaDB)
4. Reranker: deduplicate by content hash, 1.2x boost for dual-source results
5. Similarity scoring: `1/(1+distance)` for proper relevance differentiation

## Embedding Model

| Property | Value |
|----------|-------|
| Model | `nomic-embed-text:latest` (via Ollama) |
| Dimensions | 768 |
| Distance metric | Squared L2 |
| Similarity formula | `1 / (1 + distance)` |
| GPU | RTX 5080 (via Ollama) |

## Supported Formats

| Extension | Parser | Use Case |
|-----------|--------|----------|
| `.jsonl` | `parse_jsonl` | Training data, knowledge bases |
| `.json` | `parse_json` | Scan results, configs |
| `.md` | `parse_text` | Documentation, guides |
| `.txt` | `parse_text` | Plain text documentation |
| `.rego` | `parse_rego` | OPA/Gatekeeper/Conftest policies |
| `.yaml`/`.yml` | `parse_yaml` | K8s manifests, Helm charts |

## Data Categories

| Category | Description |
|----------|-------------|
| `domain-SME` | Domain expert knowledge (K8s, cloud, IaC) |
| `projects-docs` | GP-Copilot project documentation |
| `sessions` | Claude Code session transcripts |
| `troubleshooting` | Debugging and issue resolution |
| `jsa-logs` | JSA agent operational logs |
| `opa-policies` | OPA/Rego policy files |
| `webscraper` | Scraped security documentation |
| `night-learning` | Overnight autonomous learning sessions |
| `operational-training-data` | JSA training data |
| `sync` | Cross-platform sync data |
