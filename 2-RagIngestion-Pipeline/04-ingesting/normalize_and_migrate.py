#!/usr/bin/env python3
"""
ChromaDB Metadata Migration & Normalization
Fixes fragmented metadata and populates empty collections.
"""

import chromadb
from pathlib import Path
import sys
import os
from collections import Counter

# Add pipeline root to path so we can import stages
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../02-preperation-factory')))
from stages.schema_enforcement import validate_rag_item

# Import the correct embedding function (768-dim nomic-embed-text via Ollama)
from ingest_to_chromadb import OllamaEmbeddingFunction

CHROMA_PATH = "2-RagIngestion-Pipeline/05-ragged-data/chroma"

# CRITICAL: Always use OllamaEmbeddingFunction (768-dim nomic-embed-text).
# Without this, ChromaDB defaults to all-MiniLM-L6-v2 (384-dim) which is
# incompatible with the rest of the system.
ollama_ef = OllamaEmbeddingFunction()

# Source -> Target Mapping
COLLECTION_MAP = {
    "jade-general": "jsa_knowledge",
    "jade-ccsp": "cloud_knowledge",
    "jade-nist-800-53": "compliance_frameworks",
    "jade-terraform-iac": "infrastructure_knowledge"
}

def migrate():
    print(f"--- Starting Migration and Normalization ---")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    for src_name, target_name in COLLECTION_MAP.items():
        try:
            src_coll = client.get_collection(name=src_name)
            target_coll = client.get_or_create_collection(
                name=target_name,
                embedding_function=ollama_ef
            )
            
            count = src_coll.count()
            if count == 0:
                print(f"Skipping {src_name} (empty)")
                continue
                
            print(f"Migrating {count} docs from {src_name} to {target_name}...")
            
            invalid_reasons = Counter()
            
            # Process in batches of 100
            batch_size = 100
            for i in range(0, count, batch_size):
                batch = src_coll.get(
                    limit=batch_size, 
                    offset=i, 
                    include=["metadatas", "documents"]
                )
                
                new_metadatas = []
                new_documents = []
                new_ids = []
                
                for idx in range(len(batch["ids"])):
                    raw_item = {
                        "content": batch["documents"][idx],
                        "metadata": batch["metadatas"][idx] or {}
                    }
                    
                    # Normalize using our new Schema Enforcement
                    norm_result = validate_rag_item(raw_item)
                    
                    if norm_result["valid"]:
                        clean_meta = norm_result["data"]["metadata"]
                        flat_meta = {
                            "security_domain": clean_meta["security_domain"],
                            "expert_rank": clean_meta["expert_rank"],
                            "source_type": clean_meta["source_type"],
                            "original_source": str(clean_meta["original_source"]),
                            "version": clean_meta["version"],
                            "timestamp": clean_meta["timestamp"]
                        }
                        
                        new_metadatas.append(flat_meta)
                        new_documents.append(batch["documents"][idx])
                        # Use a source-specific unique prefix to avoid ID collisions
                        new_ids.append(f"mig_{src_name}_{batch['ids'][idx]}")
                    else:
                        invalid_reasons[norm_result["error"][:100]] += 1
                
                if new_ids:
                    # Use upsert to handle re-runs gracefully
                    target_coll.upsert(
                        ids=new_ids,
                        metadatas=new_metadatas,
                        documents=new_documents
                    )
                
                print(f"  Processed {i + len(batch['ids'])}/{count} (Validated: {len(new_ids)})", end="\r")
            
            print(f"\n[OK] Completed migration for {src_name}")
            if invalid_reasons:
                print(f"  Invalid items skipped: {sum(invalid_reasons.values())}")
                for reason, c in invalid_reasons.most_common(3):
                    print(f"    - {c} failed due to: {reason}")
            
        except Exception as e:
            print(f"\n[ERROR] Failed to migrate {src_name}: {e}")

    print("\n--- Migration Complete ---")

if __name__ == "__main__":
    migrate()
