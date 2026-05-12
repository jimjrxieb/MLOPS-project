"""
RAG (Retrieval-Augmented Generation) Engine for GP-Copilot
Ollama-Powered Knowledge Management for Security Consulting

Uses Ollama for embeddings instead of PyTorch/sentence-transformers:
- No PyTorch dependency
- Native RTX 5080 GPU support
- Optimized embeddings (nomic-embed-text: 768-dim)
- Faster and simpler
"""

import os
import json
import math
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

# Import Ollama embeddings (replaces sentence-transformers)
try:
    from .ollama_embeddings import get_ollama_embeddings
    from .paths import GP_CHROMA_PATH
except ImportError:
    from ollama_embeddings import get_ollama_embeddings
    from paths import GP_CHROMA_PATH

# ============================================================
# SINGLETON PATTERN - Ensures ONE RAG instance everywhere
# ============================================================
_rag_instance: Optional['RAGEngine'] = None

def get_rag_engine(quiet: bool = False) -> 'RAGEngine':
    """
    Get the singleton RAG engine instance.

    This ensures all commands (chat, scan, query, etc.) use the SAME
    RAG instance with consistent embedding model and ChromaDB config.

    Args:
        quiet: Suppress initialization messages (default: False for backward compatibility)

    Returns:
        RAGEngine: Singleton instance
    """
    global _rag_instance
    if _rag_instance is None:
        if not quiet:
            print("🔧 Initializing RAG Engine (singleton)...")
        _rag_instance = RAGEngine(quiet=quiet)
    return _rag_instance

class RAGEngine:
    """High-performance RAG system for security knowledge"""

    def __init__(self, custom_db_path: Optional[Path] = None, quiet: bool = False):
        # Allow custom Chroma DB path for specialized collections
        if custom_db_path:
            self.db_path = custom_db_path
        else:
            # Use centralized path config (deployable via GP_CHROMA_PATH env var)
            self.db_path = GP_CHROMA_PATH

        self.db_path.mkdir(parents=True, exist_ok=True)
        self.quiet = quiet  # Store for use in other methods

        # Initialize ChromaDB with persistent storage
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Initialize Ollama embeddings (replaces sentence-transformers + PyTorch)
        if not quiet:
            print(f"🚀 Initializing Ollama embeddings (GPU-accelerated on RTX 5080)")

        self.embedding_model = get_ollama_embeddings()

        # Initialize collections
        self.init_collections()

    def _get_or_create(self, name: str, description: str):
        """Create a collection with the correct Ollama embedding function.

        CRITICAL: Always pass embedding_function to avoid ChromaDB defaulting
        to all-MiniLM-L6-v2 (384-dim) which is incompatible with our
        nomic-embed-text (768-dim) vectors.
        """
        return self.client.get_or_create_collection(
            name=name,
            metadata={"description": description},
            embedding_function=self.embedding_model,
        )

    def init_collections(self):
        """Initialize ChromaDB collections for different knowledge types"""

        self.security_patterns = self._get_or_create(
            "security_patterns", "Security best practices and vulnerability patterns")
        self.client_knowledge = self._get_or_create(
            "client_knowledge", "Client-specific documentation and context")
        self.compliance_frameworks = self._get_or_create(
            "compliance_frameworks", "SOC2, CIS, PCI-DSS compliance requirements")
        self.cks_knowledge = self._get_or_create(
            "cks_knowledge", "Kubernetes security and CKS exam content")
        self.scan_findings = self._get_or_create(
            "scan_findings", "Latest security scan results and findings")
        self.documentation = self._get_or_create(
            "documentation", "Project documentation, reports, and guides")
        self.project_context = self._get_or_create(
            "project_context", "Project-specific context and metadata")

        if not self.quiet:
            print(f"✅ Initialized {len(self.client.list_collections())} knowledge collections")

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """Generate embeddings for documents using Ollama"""
        # Ollama embeddings return numpy array, convert to list for ChromaDB
        embeddings = self.embedding_model.embed_documents(
            documents,
            show_progress=True
        )
        return embeddings.tolist()

    def add_security_knowledge(self, knowledge_type: str, documents: List[Dict[str, Any]]):
        """Add security knowledge to appropriate collection"""

        collection_map = {
            "patterns": self.security_patterns,
            "client": self.client_knowledge,
            "compliance": self.compliance_frameworks,
            "cks": self.cks_knowledge,
            "scans": self.scan_findings,
            "docs": self.documentation,
            "projects": self.project_context
        }

        # Try to get existing collection, or create new one dynamically
        collection = collection_map.get(knowledge_type)
        if not collection:
            # Create new collection dynamically for specialized ingesters
            print(f"📚 Creating new collection: {knowledge_type}")
            collection = self._get_or_create(
                knowledge_type, f"Specialized collection: {knowledge_type}"
            )

        # Prepare documents for embedding (filter out empty content)
        valid_documents = [doc for doc in documents if doc.get("content", "").strip()]

        if not valid_documents:
            print("⚠️  All documents have empty content - nothing to ingest")
            return

        texts = [doc["content"] for doc in valid_documents]
        metadatas = [doc.get("metadata", {}) for doc in valid_documents]
        ids = [doc.get("id", f"{knowledge_type}_{i}") for i, doc in enumerate(valid_documents)]

        # Generate embeddings
        print(f"📝 Embedding {len(texts)} documents (filtered from {len(documents)})...")
        embeddings = self.embed_documents(texts)

        # Add to collection
        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

        print(f"✅ Added {len(documents)} documents to {knowledge_type} collection")

    def query_knowledge(self, query: str, knowledge_type: str = "all", n_results: int = 5) -> List[Dict[str, Any]]:
        """Query knowledge base for relevant information"""

        # Generate query embedding with Ollama
        query_embedding = [self.embedding_model.embed_query(query)]

        results = []

        if knowledge_type == "all":
            # Query ALL collections including dynamically created ones
            collections = self.client.list_collections()
        else:
            collection_map = {
                "patterns": self.security_patterns,
                "client": self.client_knowledge,
                "compliance": self.compliance_frameworks,
                "cks": self.cks_knowledge
            }
            collections = [collection_map.get(knowledge_type, self.security_patterns)]

        # Query each collection
        for collection in collections:
            try:
                # If collections is a list of collection metadata (from list_collections)
                # we need to get the actual collection
                if hasattr(collection, 'name') and not hasattr(collection, 'query'):
                    collection = self.client.get_collection(collection.name)

                result = collection.query(
                    query_embeddings=query_embedding,
                    n_results=n_results
                )

                # Format results with similarity score
                for i in range(len(result["documents"][0])):
                    distance = result["distances"][0][i] if result["distances"] else 0
                    # ChromaDB returns squared L2 distance.
                    # 1/(1+d) gives proper spread: d=0→1.0, d=100→0.01, d=10000→0.0001
                    # Much better differentiation than exp(-d/50000) which was nearly flat.
                    similarity = 1.0 / (1.0 + distance)

                    results.append({
                        "content": result["documents"][0][i],
                        "metadata": result["metadatas"][0][i] if result["metadatas"] else {},
                        "distance": distance,
                        "score": similarity,
                        "collection": collection.name
                    })
            except Exception as e:
                print(f"Error querying {collection.name}: {e}")

        # Sort by relevance (higher score is better)
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:n_results]

    def ingest_client_project(self, project_path: str, client_name: str):
        """Ingest client project documentation for context"""
        project_path = Path(project_path)

        if not project_path.exists():
            print(f"❌ Project path not found: {project_path}")
            return

        # Clear existing client data first
        try:
            # Get existing documents for this client
            existing = self.client_knowledge.get(where={"client": client_name})
            if existing and existing["ids"]:
                self.client_knowledge.delete(ids=existing["ids"])
                print(f"🧹 Cleared {len(existing['ids'])} existing documents for {client_name}")
        except Exception as e:
            print(f"Note: Could not clear existing data: {e}")

        documents = []

        # Scan for documentation files
        for ext in ["*.md", "*.txt", "*.yaml", "*.yml", "README*"]:
            for file_path in project_path.rglob(ext):
                try:
                    # Try multiple encodings
                    content = None
                    for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                        try:
                            content = file_path.read_text(encoding=encoding)
                            break
                        except UnicodeDecodeError:
                            continue

                    if content is None:
                        print(f"⚠️  Could not decode {file_path}")
                        continue

                    # Skip empty or very small files
                    if len(content) < 50:
                        continue

                    documents.append({
                        "content": content[:5000],  # Limit content size
                        "metadata": {
                            "client": client_name,
                            "file": str(file_path.relative_to(project_path)),
                            "type": file_path.suffix
                        },
                        "id": f"{client_name}_{file_path.relative_to(project_path).as_posix().replace('/', '_')}_{hash(content)}"
                    })
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

        if documents:
            self.add_security_knowledge("client", documents)
            print(f"✅ Ingested {len(documents)} documents for client: {client_name}")
        else:
            print(f"⚠️  No documents found for client: {client_name}")

    def load_cks_knowledge(self):
        """Load CKS best practices into knowledge base"""
        cks_knowledge = [
            {
                "content": "Pod Security Standards: Enforce restricted policy to prevent privileged containers, require non-root users, and block privilege escalation. Use Pod Security Admission controller or OPA Gatekeeper.",
                "metadata": {"topic": "Pod Security Standards", "framework": "CKS"},
                "id": "cks_pss_001"
            },
            {
                "content": "Network Policies: Implement default-deny NetworkPolicy for all namespaces. Allow only required ingress/egress traffic. Use Calico or Cilium for advanced network policies.",
                "metadata": {"topic": "Network Policies", "framework": "CKS"},
                "id": "cks_network_001"
            },
            {
                "content": "RBAC Best Practices: Follow least privilege principle. Avoid cluster-admin bindings. Use RoleBindings over ClusterRoleBindings when possible. Audit RBAC regularly.",
                "metadata": {"topic": "RBAC", "framework": "CKS"},
                "id": "cks_rbac_001"
            },
            {
                "content": "Secret Management: Never hardcode secrets. Use external secret operators (Sealed Secrets, External Secrets Operator). Enable encryption at rest for etcd.",
                "metadata": {"topic": "Secrets", "framework": "CKS"},
                "id": "cks_secrets_001"
            },
            {
                "content": "Image Security: Scan images with Trivy or Snyk. Use image signing with Cosign. Implement admission controllers to block vulnerable images. Use distroless or minimal base images.",
                "metadata": {"topic": "Image Security", "framework": "CKS"},
                "id": "cks_images_001"
            }
        ]

        self.add_security_knowledge("cks", cks_knowledge)
        print("✅ Loaded CKS knowledge base")

    def load_compliance_frameworks(self):
        """Load compliance framework requirements"""
        compliance_docs = [
            {
                "content": "SOC2 Type II: Requires continuous monitoring, access controls, encryption at rest and in transit, incident response procedures, and regular security assessments.",
                "metadata": {"framework": "SOC2", "type": "overview"},
                "id": "soc2_001"
            },
            {
                "content": "CIS Kubernetes Benchmark: Control plane security, worker node security, RBAC policies, network policies, pod security policies, logging and monitoring.",
                "metadata": {"framework": "CIS", "type": "kubernetes"},
                "id": "cis_k8s_001"
            },
            {
                "content": "PCI-DSS: Cardholder data protection, network segmentation, access control measures, regular security testing, encryption requirements.",
                "metadata": {"framework": "PCI-DSS", "type": "overview"},
                "id": "pci_001"
            }
        ]

        self.add_security_knowledge("compliance", compliance_docs)
        print("✅ Loaded compliance frameworks")

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        stats = {
            "collections": {},
            "total_documents": 0,
            "embedding_model": self.embedding_model.model,
            "embedding_dimension": self.embedding_model.get_dimension()
        }

        for collection in self.client.list_collections():
            count = collection.count()
            stats["collections"][collection.name] = count
            stats["total_documents"] += count

        return stats

    def vector_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Vector search across all collections with confidence scoring.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of results with content, score, collection, metadata
        """
        all_results = []

        # Get ALL collections dynamically (includes jade-domain-sme and any other specialized collections)
        collections_metadata = self.client.list_collections()

        # Generate query embedding once (reuse for all collections)
        query_embedding = self.embedding_model.embed_query(query)

        # Search each collection
        for collection_meta in collections_metadata:
            try:
                # Get the actual collection object from metadata
                collection = self.client.get_collection(collection_meta.name)

                result = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k
                )

                # Format results with similarity score
                if result['documents'] and result['documents'][0]:
                    for i in range(len(result['documents'][0])):
                        distance = result['distances'][0][i] if result['distances'] else 1.0
                        # ChromaDB returns squared L2 distance.
                        # 1/(1+d) gives proper spread: d=0→1.0, d=100→0.01, d=10000→0.0001
                        similarity = 1.0 / (1.0 + distance)

                        all_results.append({
                            'content': result['documents'][0][i],
                            'score': similarity,
                            'distance': distance,
                            'collection': collection.name,
                            'metadata': result['metadatas'][0][i] if result['metadatas'] else {}
                        })
            except Exception as e:
                print(f"⚠️  Search failed for {collection_meta.name}: {e}")

        # Sort by similarity score (highest first)
        all_results.sort(key=lambda x: x['score'], reverse=True)

        return all_results[:top_k]

if __name__ == "__main__":
    print("🧪 Testing RAG Engine...")

    # Use singleton
    rag = get_rag_engine()

    # Load knowledge bases
    rag.load_cks_knowledge()
    rag.load_compliance_frameworks()

    # Test query
    test_query = "What are Kubernetes pod security best practices?"
    results = rag.query_knowledge(test_query, knowledge_type="cks", n_results=3)

    print(f"\n🔍 Query: {test_query}")
    print(f"📚 Found {len(results)} relevant documents:")

    for i, result in enumerate(results, 1):
        print(f"\n{i}. Collection: {result['collection']}")
        print(f"   Relevance: {1 - result['distance']:.2%}")
        print(f"   Content: {result['content'][:200]}...")

    # Display stats
    stats = rag.get_stats()
    print(f"\n📊 RAG System Stats:")
    print(f"Device: {stats['device']}")
    print(f"Total Documents: {stats['total_documents']}")
    for collection, count in stats['collections'].items():
        print(f"  {collection}: {count} documents")
