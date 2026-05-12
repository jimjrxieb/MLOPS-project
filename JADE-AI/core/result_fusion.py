"""
Result Fusion - Reciprocal Rank Fusion (RRF) algorithm

Combines results from multiple retrievers (vector, SQL, graph) using RRF.

Algorithm:
    RRF_score(d) = Σ 1 / (k + rank_i(d))

Where:
- d is a document
- rank_i(d) is the rank of document d in result set i
- k is a constant (typically 60)

Benefits:
- No need to normalize scores across retrievers
- Documents appearing in multiple result sets are boosted
- Robust to differences in scoring functions
- Industry standard (ElasticSearch, Vespa, etc.)

Reference: "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods"
https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
"""

from typing import List, Dict, Any, Tuple
from collections import defaultdict
import hashlib


class ResultFusion:
    """
    Combine results from multiple retrievers using Reciprocal Rank Fusion

    Handles:
    - Results from vector, SQL, graph retrievers
    - Deduplication by content similarity
    - Score normalization
    - Metadata preservation
    """

    def __init__(self, k: int = 60):
        """
        Initialize result fusion

        Args:
            k: RRF constant (default: 60, as per research paper)
        """
        self.k = k

    def _get_doc_id(self, document: Dict[str, Any]) -> str:
        """
        Generate unique ID for document

        Uses content hash for deduplication across retrievers
        """
        # Try to use existing ID fields
        if 'id' in document:
            return str(document['id'])

        # Check for finding_id in metadata (SQL results)
        metadata = document.get('metadata')
        if metadata and isinstance(metadata, dict) and 'finding_id' in metadata:
            return f"finding_{metadata['finding_id']}"

        # Fallback: hash of content
        content = document.get('content', '')
        content_hash = hashlib.md5(content[:500].encode()).hexdigest()
        return f"doc_{content_hash}"

    def _calculate_rrf_scores(
        self,
        result_sets: List[Tuple[str, List[Dict[str, Any]]]]
    ) -> Dict[str, float]:
        """
        Calculate RRF scores for all documents

        Args:
            result_sets: List of (source_name, results) tuples

        Returns:
            Dict mapping doc_id to RRF score
        """
        rrf_scores = defaultdict(float)

        for source_name, results in result_sets:
            for rank, document in enumerate(results, start=1):
                doc_id = self._get_doc_id(document)
                # RRF formula: 1 / (k + rank)
                rrf_scores[doc_id] += 1.0 / (self.k + rank)

        return dict(rrf_scores)

    def fuse(
        self,
        vector_results: List[Dict[str, Any]] = None,
        sql_results: List[Dict[str, Any]] = None,
        graph_results: List[Dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fuse results from multiple retrievers using RRF

        Args:
            vector_results: Results from vector search
            sql_results: Results from SQL queries
            graph_results: Results from graph traversal
            top_k: Number of results to return

        Returns:
            Fused and ranked results
        """
        # Collect all result sets
        result_sets = []

        if vector_results:
            result_sets.append(('vector', vector_results))

        if sql_results:
            result_sets.append(('sql', sql_results))

        if graph_results:
            result_sets.append(('graph', graph_results))

        # Handle empty case
        if not result_sets:
            return []

        # Calculate RRF scores
        rrf_scores = self._calculate_rrf_scores(result_sets)

        # Build document registry (deduplicated)
        doc_registry = {}

        for source_name, results in result_sets:
            for document in results:
                doc_id = self._get_doc_id(document)

                # Keep first occurrence (or merge metadata)
                if doc_id not in doc_registry:
                    doc_registry[doc_id] = document.copy()
                    # Track which retrievers returned this document
                    doc_registry[doc_id]['sources'] = [source_name]
                else:
                    # Document seen before - add source
                    if 'sources' not in doc_registry[doc_id]:
                        doc_registry[doc_id]['sources'] = []
                    if source_name not in doc_registry[doc_id]['sources']:
                        doc_registry[doc_id]['sources'].append(source_name)

        # Add RRF scores to documents
        for doc_id, document in doc_registry.items():
            document['rrf_score'] = rrf_scores.get(doc_id, 0.0)
            document['doc_id'] = doc_id

        # Sort by RRF score (descending)
        fused_results = sorted(
            doc_registry.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )

        return fused_results[:top_k]

    def explain_fusion(
        self,
        vector_results: List[Dict[str, Any]] = None,
        sql_results: List[Dict[str, Any]] = None,
        graph_results: List[Dict[str, Any]] = None
    ) -> str:
        """
        Generate human-readable explanation of fusion process

        Args:
            vector_results: Results from vector search
            sql_results: Results from SQL queries
            graph_results: Results from graph traversal

        Returns:
            Explanation string
        """
        lines = ["Result Fusion Analysis:", "=" * 50]

        # Count results from each source
        counts = []
        if vector_results:
            counts.append(f"Vector: {len(vector_results)} results")
        if sql_results:
            counts.append(f"SQL: {len(sql_results)} results")
        if graph_results:
            counts.append(f"Graph: {len(graph_results)} results")

        lines.append(f"Input: {', '.join(counts)}")

        # Perform fusion
        fused = self.fuse(vector_results, sql_results, graph_results, top_k=10)

        lines.append(f"Fused: {len(fused)} unique documents")
        lines.append("")
        lines.append("Top 5 by RRF score:")

        for i, doc in enumerate(fused[:5], 1):
            sources = doc.get('sources', ['unknown'])
            rrf_score = doc.get('rrf_score', 0)
            content_preview = doc.get('content', '')[:80]

            lines.append(f"{i}. [RRF: {rrf_score:.4f}] Sources: {', '.join(sources)}")
            lines.append(f"   {content_preview}...")
            lines.append("")

        return "\n".join(lines)


# Singleton instance
_result_fusion: ResultFusion = None

def get_result_fusion(k: int = 60) -> ResultFusion:
    """Get singleton result fusion instance"""
    global _result_fusion
    if _result_fusion is None:
        _result_fusion = ResultFusion(k=k)
    return _result_fusion


if __name__ == "__main__":
    """Test result fusion"""
    print("🧪 Testing Result Fusion (RRF Algorithm)\n")

    fusion = get_result_fusion()

    # Mock results from different retrievers
    vector_results = [
        {'content': 'SQL injection is a code injection technique...', 'score': 0.85, 'collection': 'jade-general'},
        {'content': 'Parameterized queries prevent SQL injection...', 'score': 0.78, 'collection': 'jade-general'},
        {'content': 'Use prepared statements to avoid SQL injection...', 'score': 0.72, 'collection': 'jade-domain-sme'},
    ]

    sql_results = [
        {'content': 'Finding #1: SQL injection in app/routes/login.py:42', 'score': 0.90, 'metadata': {'finding_id': 1}},
        {'content': 'Finding #5: SQL injection in app/api/users.py:128', 'score': 0.90, 'metadata': {'finding_id': 5}},
    ]

    graph_results = [
        {'content': 'CWE-89 (SQL Injection) is detected by Bandit and Semgrep', 'score': 0.80},
        {'content': 'CWE-89 is fixed by parameterized queries', 'score': 0.75},
    ]

    # Perform fusion
    print("Input Results:")
    print(f"  Vector: {len(vector_results)} semantic results")
    print(f"  SQL: {len(sql_results)} structured findings")
    print(f"  Graph: {len(graph_results)} relationship results")
    print()

    fused_results = fusion.fuse(
        vector_results=vector_results,
        sql_results=sql_results,
        graph_results=graph_results,
        top_k=10
    )

    print(f"Fused: {len(fused_results)} unique documents")
    print()
    print("Top 5 Results (by RRF score):")
    print("=" * 70)

    for i, result in enumerate(fused_results[:5], 1):
        rrf_score = result['rrf_score']
        sources = result.get('sources', ['unknown'])
        content = result['content'][:100]

        print(f"\n{i}. [RRF Score: {rrf_score:.4f}]")
        print(f"   Sources: {', '.join(sources)}")
        print(f"   {content}...")

    # Detailed explanation
    print("\n" + "=" * 70)
    print("\nDetailed Fusion Analysis:")
    print(fusion.explain_fusion(vector_results, sql_results, graph_results))
