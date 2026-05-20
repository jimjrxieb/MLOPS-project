#!/usr/bin/env python3
"""
Elite RAG Schema Enforcement
Ensures all data meets high-quality security engineering standards.
"""

from typing import List, Dict, Optional, Literal, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
import json

class RAGMetadata(BaseModel):
    source_type: Literal["documentation", "session", "policy", "benchmark", "log", "youtube"]
    security_domain: Literal["kubernetes", "cloud", "devsecops", "compliance", "iam", "network", "general"]
    expert_rank: Literal["S", "A", "B", "C", "D", "E"] = "C"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0"
    tags: List[str] = []
    original_source: str
    
    @validator("timestamp")
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            return datetime.now().isoformat()

class RAGChunk(BaseModel):
    content: str
    metadata: RAGMetadata
    entity_extraction: Optional[Dict[str, List[str]]] = None # To be filled by NLP NPC later

SOURCE_TYPE_MAP = {
    "policy-generation": "policy",
    "fix, configuration": "policy",
    "general": "documentation",
    "consultant": "documentation",
    "etl": "documentation",
    "session": "session",
    "log": "log",
    "youtube": "youtube",
    "benchmark": "benchmark"
}

DOMAIN_MAP = {
    "opa-rego": "devsecops",
    "kubernetes-opa": "kubernetes",
    "terraform-iac": "devsecops",
    "aws": "cloud",
    "azure": "cloud",
    "gcp": "cloud"
}

def validate_rag_item(item: Dict) -> Dict:
    """
    Validates a single RAG item against the strict schema.
    If fields are missing, it attempts to infer them or uses defaults.
    """
    try:
        # Check if item is already in standard format
        if "messages" in item:
            # Handle ChatML format if needed
            content = json.dumps(item["messages"])
        else:
            content = item.get("content", str(item))
            
        raw_meta = item.get("metadata", {})
        
        # Mapping Logic
        raw_type = raw_meta.get("type", "documentation")
        source_type = SOURCE_TYPE_MAP.get(raw_type, "documentation")
        
        raw_domain = raw_meta.get("domain", "general")
        if isinstance(raw_domain, list):
            raw_domain = raw_domain[0]
        
        # Inference Logic
        domain = DOMAIN_MAP.get(raw_domain, "general")
        if "k8s" in content.lower() or "kubernetes" in content.lower():
            domain = "kubernetes"
        elif "aws" in content.lower() or "azure" in content.lower():
            domain = "cloud"
            
        # Standardize metadata
        clean_meta = RAGMetadata(
            source_type=source_type,
            security_domain=domain,
            expert_rank=raw_meta.get("rank", raw_meta.get("skill_level", "C"))[0].upper() if raw_meta.get("rank") or raw_meta.get("skill_level") else "C",
            original_source=str(raw_meta.get("source", "unknown")),
            tags=raw_meta.get("tags", "").split(", ") if isinstance(raw_meta.get("tags"), str) else []
        )
        
        chunk = RAGChunk(content=content, metadata=clean_meta)
        return {"valid": True, "data": chunk.dict(), "error": None}
        
    except Exception as e:
        return {"valid": False, "data": item, "error": str(e)}

if __name__ == "__main__":
    test_item = {
        "content": "How to secure a Kubernetes pod using NetworkPolicies",
        "metadata": {"source": "k8s-docs.md", "domain": "kubernetes"}
    }
    result = validate_rag_item(test_item)
    print(json.dumps(result, indent=2))
