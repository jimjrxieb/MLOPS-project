#!/usr/bin/env python3
"""
Ingest NIST 800-53 controls + AI RMF frameworks into ChromaDB.
Creates the `compliance-controls` collection with real control data.

This script is retained as a generic compliance collection builder. BERU's
canonical curated ingest is `ingest_beru_to_chromadb.py`.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json
import sys

import chromadb
import requests
import yaml


REPO_ROOT = Path("/home/jimmie/linkops-industries/GP-copilot")
RAG_ROOT = REPO_ROOT / "GP-MODEL-OPS" / "2-RagIngestion-Pipeline"
CHROMA_PATH = RAG_ROOT / "05-ragged-data" / "chroma"
QUARANTINE = RAG_ROOT / "05-ragged-data" / "embedding_quarantine.jsonl"
NIST_CONTROLS = REPO_ROOT / "GP-CONSULTING" / "NIST-800-53" / "controls"
AI_RMF_FRAMEWORKS = REPO_ROOT / "GP-MODEL-OPS" / "CAPSTONE-PROJECT" / "frameworks"

COLLECTION_NAME = "compliance-controls"
OLLAMA_API = "http://localhost:11434/api/embed"
EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_DIM = 768


def parse_markdown_frontmatter(filepath: Path) -> tuple[Dict[str, Any], str]:
    content = filepath.read_text(encoding="utf-8")
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2].strip()
            return frontmatter or {}, body
    return {}, content


def quarantine_embedding_failure(doc_id: str, text: str, error: str) -> None:
    QUARANTINE.parent.mkdir(parents=True, exist_ok=True)
    with QUARANTINE.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "timestamp": datetime.now().isoformat(),
                    "source": "ingest-compliance-controls",
                    "doc_id": doc_id,
                    "error": error,
                    "text_preview": text[:200],
                    "text_length": len(text),
                    "model": EMBEDDING_MODEL,
                }
            )
            + "\n"
        )


def embed_text(text: str) -> Optional[list[float]]:
    try:
        response = requests.post(
            OLLAMA_API,
            json={"model": EMBEDDING_MODEL, "input": text},
            timeout=30,
        )
        response.raise_for_status()
        embeddings = response.json().get("embeddings", [])
        if not embeddings:
            return None
        embedding = embeddings[0]
        if len(embedding) != EMBEDDING_DIM:
            raise RuntimeError(f"expected {EMBEDDING_DIM} dims, got {len(embedding)}")
        return embedding
    except Exception as e:
        print(f"    WARNING: Embedding failed: {e}")
        return None


def prepare_documents():
    documents = []
    metadatas = []
    ids = []

    print("\nLoading NIST 800-53 Controls...")
    for control_file in sorted(NIST_CONTROLS.glob("*.md")):
        frontmatter, body = parse_markdown_frontmatter(control_file)
        control_id = frontmatter.get("id", control_file.stem)
        family = frontmatter.get("family", "")
        name = frontmatter.get("name", control_id)

        doc_content = f"""Control ID: {control_id}
Family: {family}
Name: {name}
---
{body}
""".strip()

        documents.append(doc_content)
        ids.append(f"nist-{control_id}")
        metadatas.append(
            {
                "source": "NIST-800-53",
                "control_id": control_id,
                "family": family,
                "name": name,
                "type": "control",
                "ingested_at": datetime.utcnow().isoformat(),
            }
        )

    print(f"  Loaded {len(ids)} NIST controls")

    print("\nLoading AI RMF Frameworks...")
    ai_rmf_count = 0
    for framework_file in sorted(AI_RMF_FRAMEWORKS.rglob("*.md")):
        if "crosswalk" in str(framework_file):
            continue

        _, body = parse_markdown_frontmatter(framework_file)
        framework_name = framework_file.stem
        doc_content = f"""Framework: {framework_name}
Source: NIST AI RMF
---
{body}
""".strip()

        documents.append(doc_content)
        ids.append(f"ai-rmf-{framework_name}")
        metadatas.append(
            {
                "source": "NIST-AI-RMF",
                "framework": framework_name,
                "type": "framework",
                "ingested_at": datetime.utcnow().isoformat(),
            }
        )
        ai_rmf_count += 1

    print(f"  Loaded {ai_rmf_count} AI RMF framework files")
    return documents, metadatas, ids


def ingest_to_chromadb():
    print(f"\n{'=' * 60}")
    print("  COMPLIANCE-CONTROLS INGESTION")
    print(f"{'=' * 60}")

    documents, metadatas, ids = prepare_documents()
    total = len(documents)
    print(f"\nTotal documents: {total}")

    print(f"\nConnecting to ChromaDB at {CHROMA_PATH}...")
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    try:
        client.delete_collection(name=COLLECTION_NAME)
        print(f"  Cleared old '{COLLECTION_NAME}' collection")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={
            "embed_model": EMBEDDING_MODEL,
            "embed_dim": EMBEDDING_DIM,
            "zero_vector_fallback": False,
        },
    )
    print(f"  Created new '{COLLECTION_NAME}' collection")

    print(f"\nEmbedding with {EMBEDDING_MODEL}...")
    batch_size = 5
    successful = 0
    failed = 0

    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_docs = documents[batch_start:batch_end]
        batch_ids = ids[batch_start:batch_end]
        batch_meta = metadatas[batch_start:batch_end]

        print(f"  Processing batch {batch_start // batch_size + 1}/{(total + batch_size - 1) // batch_size}...", end="")

        valid_docs = []
        valid_ids = []
        valid_meta = []
        valid_embeddings = []

        for doc_id, doc, meta in zip(batch_ids, batch_docs, batch_meta):
            embedding = embed_text(doc[:8000])
            if embedding is None:
                failed += 1
                quarantine_embedding_failure(doc_id, doc, "embedding returned no vector")
                continue
            valid_docs.append(doc)
            valid_ids.append(doc_id)
            valid_meta.append(meta)
            valid_embeddings.append(embedding)
            successful += 1

        if valid_docs:
            collection.upsert(
                documents=valid_docs,
                embeddings=valid_embeddings,
                metadatas=valid_meta,
                ids=valid_ids,
            )
        print(" OK")

    print(f"\n  Embedded: {successful}/{total} successfully")
    if failed > 0:
        print(f"  Failed: {failed} skipped and quarantined at {QUARANTINE}")

    final_count = collection.count()
    print("\nVALIDATION")
    print(f"  Documents in collection: {final_count}")

    sample = collection.get(limit=3, include=["documents", "metadatas"])
    print("\n  Sample documents:")
    for i, (doc, meta) in enumerate(zip(sample["documents"], sample["metadatas"]), 1):
        source = meta.get("source", meta.get("framework", "unknown"))
        print(f"    [{i}] {source} - {len(doc)} chars")

    print(f"\n{'=' * 60}")
    print(f"DONE - collection '{COLLECTION_NAME}' ready for RAG")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    try:
        ingest_to_chromadb()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
