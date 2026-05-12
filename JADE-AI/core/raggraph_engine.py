#!/usr/bin/env python3
"""
RAGGraph Hybrid Query Engine
=============================

Combines ChromaDB vector search with NetworkX graph traversal
for intelligent, context-aware retrieval.

Architecture:
    ┌─────────────────────────────────────────┐
    │            Query Router                  │
    │   (Decides: Vector / Graph / Hybrid)    │
    └──────────────────┬──────────────────────┘
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
    ┌──────────────┐        ┌──────────────┐
    │   ChromaDB   │        │   NetworkX   │
    │   Vector     │        │   Knowledge  │
    │   Search     │        │   Graph      │
    └──────────────┘        └──────────────┘
           │                       │
           │  Semantic Match       │  Entity Relations
           │  "SQL injection       │  CVE-2023-XXX →
           │   patterns"           │  CWE-89 → SQLi
           │                       │
           └───────────┬───────────┘
                       ▼
               ┌──────────────┐
               │   Reranker   │
               │  (Combine &  │
               │   Dedupe)    │
               └──────────────┘
                       │
                       ▼
               Combined Context

Usage:
    from core.raggraph_engine import get_raggraph_engine

    engine = get_raggraph_engine()

    # Hybrid search (default)
    results = engine.query("How to fix SQL injection in Kubernetes?")

    # Vector-only search
    results = engine.query("pod security policy", mode="vector")

    # Graph-only traversal
    results = engine.query("CVE-2023-12345", mode="graph")

    # Get related entities
    related = engine.get_related("kubernetes", depth=2)
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass
import re

# Import RAG engine and paths
try:
    from .rag_engine import get_rag_engine
    from .paths import GP_ROOT
except ImportError:
    from rag_engine import get_rag_engine
    from paths import GP_ROOT

# Import NetworkX
try:
    import networkx as nx
    HAS_GRAPH = True
except ImportError:
    HAS_GRAPH = False

# Import Security Ontology for query expansion
try:
    import sys
    sys.path.insert(0, str(GP_ROOT / "GP-OPENSEARCH" / "04-ingesting"))
    from security_ontology import SecurityOntology, extract_security_concepts, get_related_concepts
    HAS_ONTOLOGY = True
except ImportError:
    HAS_ONTOLOGY = False

# Paths - Graph is stored in GP-S3/knowledge-base (created by ingest_to_chromadb.py)
GRAPH_FILE = GP_ROOT / "GP-S3" / "knowledge-base" / "security_graph.pkl"


@dataclass
class QueryResult:
    """Single query result — supports both attribute and dict-style access"""
    content: str
    score: float
    source: str  # 'vector' or 'graph' or 'both'
    collection: str
    metadata: Dict[str, Any]
    related_entities: List[str] = None

    def __post_init__(self):
        if self.related_entities is None:
            self.related_entities = []

    def get(self, key: str, default=None):
        """Dict-style access for API compatibility"""
        return getattr(self, key, default)


# Singleton
_raggraph_instance: Optional['RAGGraphEngine'] = None


def get_raggraph_engine(quiet: bool = False) -> 'RAGGraphEngine':
    """Get singleton RAGGraph engine instance"""
    global _raggraph_instance
    if _raggraph_instance is None:
        _raggraph_instance = RAGGraphEngine(quiet=quiet)
    return _raggraph_instance


class RAGGraphEngine:
    """
    Hybrid RAG + Graph query engine.

    Combines:
    - ChromaDB semantic search (vector similarity)
    - NetworkX graph traversal (entity relationships)
    """

    def __init__(self, quiet: bool = False):
        self.quiet = quiet

        # Initialize RAG engine (ChromaDB + Ollama embeddings)
        if not quiet:
            print("🔧 Initializing RAGGraph Engine...")

        self.rag = get_rag_engine(quiet=True)

        # Load knowledge graph
        self.graph = self._load_graph()

        # Initialize security ontology for query expansion
        self.ontology = None
        if HAS_ONTOLOGY and self.graph is not None:
            try:
                self.ontology = SecurityOntology(self.graph)
                if not quiet:
                    print("🔐 Security ontology loaded for query expansion")
            except Exception as e:
                if not quiet:
                    print(f"   Warning: Could not load ontology: {e}")

        if not quiet:
            stats = self.get_stats()
            print(f"✅ RAGGraph ready: {stats['total_vectors']} vectors, {stats['graph_nodes']} graph nodes")

    def _load_graph(self) -> Optional['nx.DiGraph']:
        """Load knowledge graph from disk"""
        if not HAS_GRAPH:
            return None

        if not GRAPH_FILE.exists():
            if not self.quiet:
                print("   (No existing graph - will use vector-only mode)")
            return nx.DiGraph()

        try:
            import pickle
            with open(GRAPH_FILE, 'rb') as f:
                data = json.load(f)

            # Handle both formats: raw NetworkX graph or dict with 'graph' key
            if isinstance(data, dict):
                # Format from rag_graph_engine.py: {'graph': nx.Graph, 'node_types': {...}}
                graph = data.get('graph', nx.DiGraph())
                if not self.quiet:
                    print(f"   Loaded graph (dict format): {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
            else:
                # Format from ingest_to_chromadb.py: raw NetworkX graph
                graph = data
                if not self.quiet:
                    print(f"   Loaded graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
            return graph
        except Exception as e:
            if not self.quiet:
                print(f"   Warning: Could not load graph: {e}")
            return nx.DiGraph()

    def query(self,
              query: str,
              mode: Literal["hybrid", "vector", "graph"] = "hybrid",
              top_k: int = 5,
              collections: Optional[List[str]] = None,
              expand_concepts: bool = True) -> List[QueryResult]:
        """
        Query the hybrid RAG + Graph system.

        Args:
            query: Search query
            mode: Search mode
                - "hybrid": Combine vector + graph (default)
                - "vector": Vector search only
                - "graph": Graph traversal only
            top_k: Number of results to return
            collections: Specific collections to search (None = all)
            expand_concepts: Whether to expand query with related security concepts

        Returns:
            List of QueryResult objects sorted by relevance
        """
        results = []

        # Expand query with related security concepts
        expanded_query = query
        if expand_concepts and self.ontology:
            related_concepts = self.ontology.expand_query_concepts(query, depth=1)
            if related_concepts:
                # Add top 5 related concepts to query
                concept_terms = ' '.join(related_concepts[:5])
                expanded_query = f"{query} {concept_terms}"
                if not self.quiet:
                    print(f"   🔗 Query expanded with: {related_concepts[:5]}")

        # Vector search (with expanded query)
        if mode in ("hybrid", "vector"):
            vector_results = self._vector_search(expanded_query, top_k * 2, collections)
            results.extend(vector_results)

        # Graph search
        if mode in ("hybrid", "graph") and self.graph and self.graph.number_of_nodes() > 0:
            graph_results = self._graph_search(query, top_k)
            results.extend(graph_results)

        # Deduplicate and rerank
        results = self._rerank(results, top_k)

        return results

    def _vector_search(self,
                       query: str,
                       top_k: int,
                       collections: Optional[List[str]] = None) -> List[QueryResult]:
        """Perform vector search via ChromaDB"""
        try:
            raw_results = self.rag.vector_search(query, top_k=top_k)

            results = []
            for r in raw_results:
                # Filter by collection if specified
                if collections and r.get('collection') not in collections:
                    continue

                result = QueryResult(
                    content=r['content'],
                    score=r['score'],
                    source='vector',
                    collection=r.get('collection', 'unknown'),
                    metadata=r.get('metadata', {})
                )
                results.append(result)

            return results

        except Exception as e:
            if not self.quiet:
                print(f"⚠️  Vector search error: {e}")
            return []

    def _graph_search(self, query: str, top_k: int) -> List[QueryResult]:
        """Perform graph traversal search.

        Finds document nodes via graph entity matching, then retrieves
        the actual document content from ChromaDB (not placeholder text).
        """
        if not self.graph or self.graph.number_of_nodes() == 0:
            return []

        results = []

        # Extract potential entities from query
        entities = self._extract_entities(query)

        for entity in entities:
            # Find matching nodes
            matching_nodes = [n for n in self.graph.nodes()
                            if entity.lower() in str(n).lower()]

            for node in matching_nodes[:3]:  # Limit per entity
                # Get related documents
                related_docs = self._get_documents_for_entity(node)

                for doc_id, doc_data in related_docs:
                    # Get all related entities for context
                    related = list(self.graph.neighbors(doc_id))[:5]

                    # Retrieve actual content from ChromaDB using doc_id
                    collection_name = doc_data.get('collection', 'graph')
                    content = self._fetch_document_content(doc_id, collection_name)

                    if not content:
                        continue  # Skip if we can't retrieve the actual content

                    result = QueryResult(
                        content=content,
                        score=0.5,  # Base score for graph results
                        source='graph',
                        collection=collection_name,
                        metadata={
                            'graph_node': node,
                            'doc_id': doc_id,
                            'graph_entity': entity,
                            **doc_data
                        },
                        related_entities=related
                    )
                    results.append(result)

        return results[:top_k]

    def _fetch_document_content(self, doc_id: str, collection_name: str) -> Optional[str]:
        """Fetch actual document content from ChromaDB by ID.

        Tries the specified collection first, then falls back to searching
        all collections if the doc_id format includes a collection prefix.
        """
        if not self.rag or not self.rag.client:
            return None

        # Try the specific collection first
        collections_to_try = [collection_name]

        # doc_ids from ingestion have format: "{collection}_{hash}"
        # Extract the collection prefix if present
        if '_' in doc_id:
            prefix = doc_id.rsplit('_', 1)[0]
            if prefix != collection_name:
                collections_to_try.append(prefix)

        for coll_name in collections_to_try:
            try:
                collection = self.rag.client.get_collection(coll_name)
                result = collection.get(ids=[doc_id], include=["documents"])
                if result and result.get("documents") and result["documents"][0]:
                    return result["documents"][0]
            except Exception:
                continue

        return None

    def _extract_entities(self, query: str) -> List[str]:
        """Extract potential entity names from query"""
        entities = []

        # CVE patterns
        cves = re.findall(r'CVE-\d{4}-\d+', query, re.IGNORECASE)
        entities.extend(cves)

        # CWE patterns
        cwes = re.findall(r'CWE-\d+', query, re.IGNORECASE)
        entities.extend(cwes)

        # Known domains
        domains = ['kubernetes', 'docker', 'terraform', 'opa', 'aws', 'azure', 'gcp',
                   'sql injection', 'xss', 'rbac', 'network policy', 'pod security']
        for domain in domains:
            if domain.lower() in query.lower():
                entities.append(domain)

        # Capitalized words (potential named entities)
        caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        entities.extend(caps[:3])

        return list(set(entities))

    def _get_documents_for_entity(self, entity: str) -> List[tuple]:
        """Get documents connected to an entity in the graph"""
        if not self.graph or entity not in self.graph:
            return []

        docs = []

        # Get neighbors (documents connected to this entity)
        for neighbor in self.graph.neighbors(entity):
            node_data = self.graph.nodes.get(neighbor, {})
            if node_data.get('type') == 'document':
                docs.append((neighbor, node_data))

        # Also check predecessors (entities connected TO documents)
        for pred in self.graph.predecessors(entity):
            node_data = self.graph.nodes.get(pred, {})
            if node_data.get('type') == 'document':
                docs.append((pred, node_data))

        return docs[:10]

    def _rerank(self, results: List[QueryResult], top_k: int) -> List[QueryResult]:
        """Deduplicate and rerank results"""
        seen_content = set()
        unique_results = []

        for result in results:
            # Simple deduplication by content hash
            content_hash = hash(result.content[:200])
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)

            # Boost score for results that appear in both vector and graph
            if result.source == 'both':
                result.score *= 1.2

            unique_results.append(result)

        # Sort by score
        unique_results.sort(key=lambda x: x.score, reverse=True)

        return unique_results[:top_k]

    def get_related(self, entity: str, depth: int = 2) -> Dict[str, Any]:
        """
        Get entities related to a given entity via graph traversal.

        Args:
            entity: Starting entity
            depth: How many hops to traverse

        Returns:
            Dict with related entities grouped by type
        """
        if not self.graph:
            return {'error': 'Graph not available'}

        # Find matching node
        matching = [n for n in self.graph.nodes() if entity.lower() in str(n).lower()]
        if not matching:
            return {'entity': entity, 'found': False, 'related': {}}

        node = matching[0]
        related = {'domains': [], 'types': [], 'tags': [], 'documents': []}

        # BFS traversal
        visited = set()
        queue = [(node, 0)]

        while queue:
            current, current_depth = queue.pop(0)
            if current in visited or current_depth > depth:
                continue
            visited.add(current)

            node_data = self.graph.nodes.get(current, {})
            node_type = node_data.get('type', 'unknown')

            # Categorize
            if node_type == 'domain':
                related['domains'].append(current)
            elif node_type == 'doc_type':
                related['types'].append(current)
            elif node_type == 'tag':
                related['tags'].append(current)
            elif node_type == 'document':
                related['documents'].append(current)

            # Add neighbors to queue
            for neighbor in list(self.graph.neighbors(current)) + list(self.graph.predecessors(current)):
                if neighbor not in visited:
                    queue.append((neighbor, current_depth + 1))

        return {
            'entity': entity,
            'found': True,
            'matched_node': node,
            'related': related
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        rag_stats = self.rag.get_stats() if self.rag else {}

        return {
            'total_vectors': rag_stats.get('total_documents', 0),
            'collections': rag_stats.get('collections', {}),
            'embedding_model': rag_stats.get('embedding_model', 'unknown'),
            'embedding_dim': rag_stats.get('embedding_dimension', 0),
            'graph_nodes': self.graph.number_of_nodes() if self.graph else 0,
            'graph_edges': self.graph.number_of_edges() if self.graph else 0
        }


if __name__ == "__main__":
    print("🧪 Testing RAGGraph Engine...\n")

    engine = get_raggraph_engine()

    # Show stats
    stats = engine.get_stats()
    print(f"📊 Stats:")
    print(f"   Vectors: {stats['total_vectors']}")
    print(f"   Graph nodes: {stats['graph_nodes']}")
    print(f"   Graph edges: {stats['graph_edges']}")

    # Test queries
    test_queries = [
        "How to fix SQL injection?",
        "Kubernetes pod security best practices",
        "CVE remediation strategies"
    ]

    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        results = engine.query(query, top_k=3)

        if results:
            for i, r in enumerate(results, 1):
                print(f"   {i}. [{r.source}] {r.collection} (score: {r.score:.2f})")
                print(f"      {r.content[:100]}...")
        else:
            print("   (no results)")

    print("\n✅ RAGGraph Engine test complete!")
