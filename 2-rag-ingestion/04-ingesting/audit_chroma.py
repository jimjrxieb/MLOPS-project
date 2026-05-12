#!/usr/bin/env python3
"""
ChromaDB Audit Tool
Deep inspection of vector database health and contents.
"""

import chromadb
from pathlib import Path
import json
from collections import Counter

CHROMA_PATH = "2-rag-ingestion/05-ragged-data/chroma"

def audit_chroma():
    if not Path(CHROMA_PATH).exists():
        print(f"Error: Chroma directory not found at {CHROMA_PATH}")
        return

    print(f"--- Auditing ChromaDB at {CHROMA_PATH} ---")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    collections = client.list_collections()
    print(f"Found {len(collections)} collections.")
    
    total_docs = 0
    
    for coll in collections:
        count = coll.count()
        total_docs += count
        print(f"\nCollection: {coll.name}")
        print(f"  Document Count: {count}")
        
        if count > 0:
            # Sample metadata to see what we have
            try:
                sample = coll.get(limit=100, include=["metadatas"])
                metadatas = sample["metadatas"]
                
                # Analyze metadata fields
                keys = set()
                domains = Counter()
                ranks = Counter()
                
                for m in metadatas:
                    if m:
                        keys.update(m.keys())
                        domains[m.get("domain", "unknown")] += 1
                        ranks[m.get("rank", "unknown")] += 1
                
                print(f"  Metadata Keys: {sorted(list(keys))}")
                print(f"  Domains: {dict(domains)}")
                print(f"  Ranks: {dict(ranks)}")
            except Exception as e:
                print(f"  [ERROR] Could not sample metadata: {e}")

    print(f"\n--- Audit Complete ---")
    print(f"Total Documents across all collections: {total_docs}")

if __name__ == "__main__":
    audit_chroma()
