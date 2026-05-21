#!/usr/bin/env python3
"""
ChromaDB Audit Tool
Deep inspection of vector database health and contents.
"""

from pathlib import Path
from collections import Counter

import chromadb


SCRIPT_DIR = Path(__file__).resolve().parent
RAG_ROOT = SCRIPT_DIR.parent
CHROMA_PATH = RAG_ROOT / "05-ragged-data" / "chroma"


def audit_chroma():
    if not CHROMA_PATH.exists():
        print(f"Error: Chroma directory not found at {CHROMA_PATH}")
        return 1

    print(f"--- Auditing ChromaDB at {CHROMA_PATH} ---")
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    collections = client.list_collections()
    print(f"Found {len(collections)} collections.")

    total_docs = 0

    for coll in sorted(collections, key=lambda c: c.name):
        count = coll.count()
        total_docs += count
        print(f"\nCollection: {coll.name}")
        print(f"  Document Count: {count}")

        if count > 0:
            try:
                sample = coll.get(limit=100, include=["metadatas"])
                metadatas = sample["metadatas"]

                keys = set()
                domains = Counter()
                ranks = Counter()
                frameworks = Counter()

                for metadata in metadatas:
                    if metadata:
                        keys.update(metadata.keys())
                        domains[metadata.get("domain", "unknown")] += 1
                        ranks[metadata.get("rank", "unknown")] += 1
                        frameworks[metadata.get("framework", "unknown")] += 1

                print(f"  Metadata Keys: {sorted(keys)}")
                print(f"  Domains: {dict(domains)}")
                print(f"  Ranks: {dict(ranks)}")
                print(f"  Frameworks: {dict(frameworks)}")
            except Exception as e:
                print(f"  [ERROR] Could not sample metadata: {e}")

    print("\n--- Audit Complete ---")
    print(f"Total Documents across all collections: {total_docs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(audit_chroma())
