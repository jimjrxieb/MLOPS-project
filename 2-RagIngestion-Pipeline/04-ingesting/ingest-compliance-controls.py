#!/usr/bin/env python3
"""
Ingest NIST 800-53 controls + AI RMF frameworks into ChromaDB.
Creates a 'compliance-controls' collection with real control data.
"""

import chromadb
import requests
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import sys

# Configuration
REPO_ROOT = Path("/home/jimmie/linkops-industries/GP-copilot")
CHROMA_PATH = REPO_ROOT / "GP-MODEL-OPS/2-RagIngestion-Pipeline/05-ragged-data/chroma"
NIST_CONTROLS = REPO_ROOT / "GP-CONSULTING/NIST-800-53/controls"
AI_RMF_FRAMEWORKS = REPO_ROOT / "GP-MODEL-OPS/CAPSTONE-PROJECT/frameworks"

COLLECTION_NAME = "compliance-controls"
OLLAMA_API = "http://localhost:11434/api/embed"
EMBEDDING_MODEL = "nomic-embed-text"

def parse_markdown_frontmatter(filepath: Path) -> tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter + markdown content."""
    content = filepath.read_text()

    if content.startswith("---"):
        # Find closing ---
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2].strip()
            return frontmatter or {}, body

    return {}, content

def embed_text(text: str) -> Optional[list[float]]:
    """Get embedding from Ollama."""
    try:
        response = requests.post(
            OLLAMA_API,
            json={"model": EMBEDDING_MODEL, "input": text},
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            embeddings = result.get("embeddings", [])
            return embeddings[0] if embeddings else None
        else:
            print(f"    ⚠️  Embedding failed (status {response.status_code})")
            return None
    except Exception as e:
        print(f"    ⚠️  Embedding error: {e}")
        return None

def prepare_documents():
    """Load and prepare all control documents."""
    documents = []
    metadatas = []
    ids = []
    doc_id = 0

    print("\n📖 Loading NIST 800-53 Controls...")
    for control_file in sorted(NIST_CONTROLS.glob("*.md")):
        frontmatter, body = parse_markdown_frontmatter(control_file)

        control_id = frontmatter.get("id", control_file.stem)
        family = frontmatter.get("family", "")
        name = frontmatter.get("name", control_id)

        # Create searchable content
        doc_content = f"""
Control ID: {control_id}
Family: {family}
Name: {name}
---
{body}
""".strip()

        documents.append(doc_content)
        ids.append(f"nist-{control_id}")
        metadatas.append({
            "source": "NIST-800-53",
            "control_id": control_id,
            "family": family,
            "name": name,
            "type": "control",
            "ingested_at": datetime.utcnow().isoformat()
        })
        doc_id += 1

    print(f"  ✓ Loaded {doc_id} NIST controls")

    print("\n📖 Loading AI RMF Frameworks...")
    ai_rmf_count = 0
    for framework_file in sorted(AI_RMF_FRAMEWORKS.rglob("*.md")):
        # Skip crosswalk for now, do framework files
        if "crosswalk" in str(framework_file):
            continue

        frontmatter, body = parse_markdown_frontmatter(framework_file)

        framework_name = framework_file.stem
        doc_content = f"""
Framework: {framework_name}
Source: NIST AI RMF
---
{body}
""".strip()

        documents.append(doc_content)
        ids.append(f"ai-rmf-{framework_name}")
        metadatas.append({
            "source": "NIST-AI-RMF",
            "framework": framework_name,
            "type": "framework",
            "ingested_at": datetime.utcnow().isoformat()
        })
        ai_rmf_count += 1

    print(f"  ✓ Loaded {ai_rmf_count} AI RMF framework files")

    return documents, metadatas, ids

def ingest_to_chromadb():
    """Main ingestion workflow."""
    print(f"\n{'='*60}")
    print(f"  COMPLIANCE-CONTROLS INGESTION")
    print(f"{'='*60}")

    # Prepare documents
    documents, metadatas, ids = prepare_documents()
    total = len(documents)
    print(f"\n📦 Total documents: {total}")

    # Connect to ChromaDB
    print(f"\n🔌 Connecting to ChromaDB at {CHROMA_PATH}...")
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    # Delete old collection if exists
    try:
        client.delete_collection(name=COLLECTION_NAME)
        print(f"  ✓ Cleared old '{COLLECTION_NAME}' collection")
    except:
        pass

    # Create new collection
    collection = client.create_collection(name=COLLECTION_NAME)
    print(f"  ✓ Created new '{COLLECTION_NAME}' collection")

    # Embed and ingest in batches
    print(f"\n🧠 Embedding with {EMBEDDING_MODEL}...")
    batch_size = 5
    successful = 0
    failed = 0

    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_docs = documents[batch_start:batch_end]
        batch_ids = ids[batch_start:batch_end]
        batch_meta = metadatas[batch_start:batch_end]

        print(f"  Processing batch {batch_start//batch_size + 1}/{(total + batch_size - 1)//batch_size}...", end="")

        # Embed batch
        embeddings = []
        for doc in batch_docs:
            emb = embed_text(doc[:8000])  # Limit to 8k chars per Ollama limits
            if emb:
                embeddings.append(emb)
                successful += 1
            else:
                embeddings.append([0.0] * 768)  # Fallback: zero vector
                failed += 1

        # Ingest batch
        try:
            collection.upsert(
                documents=batch_docs,
                embeddings=embeddings,
                metadatas=batch_meta,
                ids=batch_ids
            )
            print(f" ✓")
        except Exception as e:
            print(f" ✗ ({e})")

    print(f"\n  Embedded: {successful}/{total} successfully")
    if failed > 0:
        print(f"  Failed: {failed} (used fallback embeddings)")

    # Validate
    print(f"\n✅ VALIDATION")
    final_count = collection.count()
    print(f"  Documents in collection: {final_count}")

    # Sample a few
    sample = collection.get(limit=3, include=["documents", "metadatas"])
    print(f"\n  Sample documents:")
    for i, (doc, meta) in enumerate(zip(sample["documents"], sample["metadatas"]), 1):
        source = meta.get("source", meta.get("framework", "unknown"))
        print(f"    [{i}] {source} — {len(doc)} chars")

    print(f"\n{'='*60}")
    print(f"✨ DONE — collection '{COLLECTION_NAME}' ready for RAG")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    try:
        ingest_to_chromadb()
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
