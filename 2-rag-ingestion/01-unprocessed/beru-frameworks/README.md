# BERU Source Files — Pointer Index

> **You walked the pipeline tree looking for BERU's source files. They are not in this directory.**
> They live in two version-controlled locations outside the staging tree, by design. This README tells you where, why, and what reads them.

---

## Where BERU's RAG source files actually live

| Source set | Filesystem location | Files | Owner |
|---|---|---|---|
| NIST 800-53 controls | `GP-CONSULTING/NIST-800-53/controls/` | 39 `.md` (AC-2, AC-3, AU-2, CM-6, etc.) | Shared with JADE/Katie playbooks — single source of truth for the org |
| NIST AI RMF subcategories | `GP-MODEL-OPS/CAPSTONE-PROJECT/frameworks/nist-ai-600-1/` | 3 `.md` (govern, map, manage) | BERU capstone work |
| MITRE ATLAS techniques | `GP-MODEL-OPS/CAPSTONE-PROJECT/frameworks/mitre-atlas/` | 6 `.md` (16 techniques) | BERU capstone work |
| 800-53 ↔ AI RMF crosswalk | `GP-MODEL-OPS/CAPSTONE-PROJECT/frameworks/crosswalk/` | 1 `.md` | BERU capstone work |

## Why source files aren't physically staged here

Most content under `01-unprocessed/` arrives messy: scraped HTML, YouTube transcripts, raw session logs, bulk JSONL dumps. Those need the 7-stage prep factory at `02-preperation-factory/stages/` to clean, sanitize, format-convert, and label.

BERU's source is **already curated, structured markdown**, version-controlled in git, with hand-authored YAML frontmatter on the 800-53 control files. Running it through PII redaction, format conversion, or 3-tier labeling adds nothing — those gates are no-ops on this content.

So the source files stay in their authored locations under git, and a BERU-specific ingest script reads them directly. See `CAPSTONE-PROJECT/beru-design-decisions.md` (D-008 + D-011) for the full rationale.

## What reads these source files

```
2-rag-ingestion/04-ingesting/ingest_beru_to_chromadb.py
```

This is BERU's ingest script. Lives in the same `04-ingesting/` directory as JADE's `ingest_to_chromadb.py`, but:
- BERU script handles only the four source sets above (curated reference frameworks)
- JADE script handles bulk content from `01-unprocessed/` via the 7-stage factory

Run it:
```bash
python3 2-rag-ingestion/04-ingesting/ingest_beru_to_chromadb.py --dry-run     # verify parsers
python3 2-rag-ingestion/04-ingesting/ingest_beru_to_chromadb.py               # idempotent ingest
python3 2-rag-ingestion/04-ingesting/ingest_beru_to_chromadb.py --reset       # wipe + rebuild
```

## Where the output lands

| Artifact | Location |
|---|---|
| ChromaDB collection `beru-nist-800-53` | `2-rag-ingestion/05-ragged-data/chroma/` |
| Embedding failures (currently 0) | `2-rag-ingestion/05-ragged-data/embedding_quarantine.jsonl` |
| Audit log per ingest run | `GP-S3/3-mlops-reports/1-rag-staging/rag-ingestion-{ts}-beru.md` |

## Verification

The post-ingest data quality gate lives at:
```
8-tests/test_beru_rag.py
```

Run with `python3 -m pytest 8-tests/test_beru_rag.py -v`. 23 tests covering structure, provenance, integrity, direct-ID lookups, and semantic retrieval. This is the MEASURE 2.1 / GOVERN 1.4 evidence artifact required by `beru-design-decisions.md` D-010.
