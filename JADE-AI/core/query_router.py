"""
Query Router - Intelligent intent classification for multi-retriever RAG

Analyzes user queries and routes to appropriate retriever(s):
- Vector (semantic/conceptual questions)
- SQL (structured data queries)
- Graph (relationship/multi-hop reasoning)

Architecture:
- Rule-based classifier (fast, explainable)
- Can be upgraded to LLM-based routing
- Returns list of retrievers to query
- Supports multi-retriever queries (hybrid)
"""

import re
from typing import List, Dict, Any, Set
from enum import Enum


class RetrieverType(Enum):
    """Available retriever types"""
    VECTOR = "vector"      # Semantic search in ChromaDB
    SQL = "sql"            # Structured queries in findings.db
    GRAPH = "graph"        # Relationship traversal in NetworkX


class QueryIntent(Enum):
    """Query intent categories"""
    SEMANTIC = "semantic"              # "What is SQL injection?"
    STRUCTURED = "structured"          # "Show me HIGH severity findings"
    RELATIONSHIP = "relationship"      # "What fixes CWE-89?"
    HYBRID_SEMANTIC_SQL = "hybrid_semantic_sql"  # "Explain HIGH severity findings"
    HYBRID_ALL = "hybrid_all"          # "What tools detect OWASP A03 and how do I fix it?"


class QueryRouter:
    """
    Route queries to appropriate retriever(s) based on intent

    Routing logic:
    1. Structured data queries → SQL
    2. Semantic/conceptual queries → Vector
    3. Relationship queries → Graph
    4. Complex queries → Multiple retrievers (hybrid)
    """

    def __init__(self):
        """Initialize query router with pattern matchers"""

        # SQL patterns (structured data queries)
        self.sql_patterns = {
            'imperative': r'\b(show|list|display|get|find|fetch)\b',
            'quantifiers': r'\b(how many|count|total|number of)\b',
            'specificity': r'\b(severity|scanner|project|cwe|owasp|status)\b',
            'comparison': r'\b(highest|lowest|most|least|top|bottom)\b',
            'filters': r'\b(high|critical|medium|low|open|fixed|resolved)\b',
        }

        # Vector patterns (semantic/conceptual queries)
        self.vector_patterns = {
            'conceptual': r'\b(what is|explain|describe|tell me about|how does)\b',
            'procedural': r'\b(how to|how do i|best practice|guide|tutorial)\b',
            'general': r'\b(kubernetes|docker|python|aws|terraform|security)\b',
        }

        # Graph patterns (relationship queries)
        self.graph_patterns = {
            'relationships': r'\b(related to|connected to|maps to|associated with|linked to)\b',
            'causation': r'\b(caused by|fixed by|detected by|remediated by)\b',
            'navigation': r'\b(path|route|chain|sequence|workflow)\b',
        }

        # Entities that suggest specific retrievers
        self.sql_entities = {
            'findings', 'projects', 'scans', 'vulnerabilities', 'issues',
            'bandit', 'semgrep', 'trivy', 'checkov', 'gitleaks',
            'high', 'critical', 'medium', 'low',
            'cwe-', 'owasp', 'open', 'fixed'
        }

        self.vector_entities = {
            'kubernetes', 'docker', 'terraform', 'aws', 'azure', 'gcp',
            'python', 'javascript', 'golang', 'java',
            'best practice', 'tutorial', 'guide', 'documentation'
        }

        self.graph_entities = {
            'cve', 'cwe', 'owasp', 'fix', 'remediation', 'tool', 'scanner'
        }

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query and extract features for routing

        Returns:
            {
                'query': original query,
                'tokens': list of words,
                'sql_score': confidence for SQL retriever,
                'vector_score': confidence for vector retriever,
                'graph_score': confidence for graph retriever,
                'entities': detected entities,
                'patterns': matched patterns
            }
        """
        query_lower = query.lower()
        tokens = re.findall(r'\b\w+\b', query_lower)

        analysis = {
            'query': query,
            'tokens': tokens,
            'sql_score': 0.0,
            'vector_score': 0.0,
            'graph_score': 0.0,
            'entities': set(),
            'patterns': []
        }

        # Score SQL patterns
        for pattern_name, pattern in self.sql_patterns.items():
            if re.search(pattern, query_lower):
                analysis['sql_score'] += 0.2
                analysis['patterns'].append(f'sql:{pattern_name}')

        # Score vector patterns
        for pattern_name, pattern in self.vector_patterns.items():
            if re.search(pattern, query_lower):
                analysis['vector_score'] += 0.2
                analysis['patterns'].append(f'vector:{pattern_name}')

        # Score graph patterns
        for pattern_name, pattern in self.graph_patterns.items():
            if re.search(pattern, query_lower):
                analysis['graph_score'] += 0.3  # Higher weight for explicit relationships
                analysis['patterns'].append(f'graph:{pattern_name}')

        # Detect SQL entities
        for entity in self.sql_entities:
            if entity in query_lower:
                analysis['sql_score'] += 0.15
                analysis['entities'].add(f'sql:{entity}')

        # Detect vector entities
        for entity in self.vector_entities:
            if entity in query_lower:
                analysis['vector_score'] += 0.15
                analysis['entities'].add(f'vector:{entity}')

        # Detect graph entities
        for entity in self.graph_entities:
            if entity in query_lower:
                analysis['graph_score'] += 0.2
                analysis['entities'].add(f'graph:{entity}')

        # Special cases
        # CWE/CVE mentions suggest both SQL (to get findings) and graph (to get relationships)
        if re.search(r'\b(cwe|cve)-?\d+', query_lower):
            analysis['sql_score'] += 0.2
            analysis['graph_score'] += 0.2

        # "and" suggests multi-part query
        if ' and ' in query_lower or ' also ' in query_lower:
            # Boost all scores slightly (hybrid query likely)
            analysis['sql_score'] += 0.1
            analysis['vector_score'] += 0.1
            analysis['graph_score'] += 0.1

        return analysis

    def route(self, query: str, threshold: float = 0.3) -> List[RetrieverType]:
        """
        Route query to appropriate retriever(s)

        Args:
            query: User query
            threshold: Minimum score to include retriever (default: 0.3)

        Returns:
            List of RetrieverType enums indicating which retrievers to use
        """
        analysis = self.analyze_query(query)

        retrievers = []

        # Add retrievers that exceed threshold
        if analysis['sql_score'] >= threshold:
            retrievers.append(RetrieverType.SQL)

        if analysis['vector_score'] >= threshold:
            retrievers.append(RetrieverType.VECTOR)

        if analysis['graph_score'] >= threshold:
            retrievers.append(RetrieverType.GRAPH)

        # Default fallback: if no retriever scored high enough, use vector
        if not retrievers:
            retrievers.append(RetrieverType.VECTOR)

        return retrievers

    def classify_intent(self, query: str) -> QueryIntent:
        """
        Classify overall query intent

        Args:
            query: User query

        Returns:
            QueryIntent enum
        """
        analysis = self.analyze_query(query)

        scores = {
            'sql': analysis['sql_score'],
            'vector': analysis['vector_score'],
            'graph': analysis['graph_score']
        }

        # Count how many retrievers are needed
        active_retrievers = sum(1 for score in scores.values() if score >= 0.3)

        if active_retrievers >= 3:
            return QueryIntent.HYBRID_ALL

        if active_retrievers == 2:
            if scores['sql'] >= 0.3 and scores['vector'] >= 0.3:
                return QueryIntent.HYBRID_SEMANTIC_SQL
            else:
                return QueryIntent.HYBRID_ALL

        # Single retriever
        if scores['sql'] > max(scores['vector'], scores['graph']):
            return QueryIntent.STRUCTURED

        if scores['graph'] > max(scores['sql'], scores['vector']):
            return QueryIntent.RELATIONSHIP

        return QueryIntent.SEMANTIC

    def explain_routing(self, query: str) -> str:
        """
        Human-readable explanation of routing decision

        Args:
            query: User query

        Returns:
            Explanation string for debugging/transparency
        """
        analysis = self.analyze_query(query)
        retrievers = self.route(query)
        intent = self.classify_intent(query)

        explanation = [
            f"Query: \"{query}\"",
            f"\nIntent: {intent.value}",
            f"\nScores:",
            f"  SQL: {analysis['sql_score']:.2f}",
            f"  Vector: {analysis['vector_score']:.2f}",
            f"  Graph: {analysis['graph_score']:.2f}",
            f"\nRetrievers to use: {[r.value for r in retrievers]}",
        ]

        if analysis['patterns']:
            explanation.append(f"\nMatched patterns: {', '.join(analysis['patterns'])}")

        if analysis['entities']:
            explanation.append(f"Detected entities: {', '.join(sorted(analysis['entities']))}")

        return "\n".join(explanation)


# Singleton instance
_query_router: QueryRouter = None

def get_query_router() -> QueryRouter:
    """Get singleton query router instance"""
    global _query_router
    if _query_router is None:
        _query_router = QueryRouter()
    return _query_router


if __name__ == "__main__":
    """Test query router"""
    print("🧪 Testing Query Router\n")

    router = get_query_router()

    test_queries = [
        # SQL queries
        "Show me HIGH severity findings",
        "List all CWE-89 issues",
        "How many critical vulnerabilities do we have?",
        "What did bandit find?",

        # Vector queries
        "What is SQL injection?",
        "How to fix hardcoded secrets in Python?",
        "Explain Kubernetes pod security",
        "Best practices for AWS IAM",

        # Graph queries
        "What tools detect CWE-798?",
        "Show me the path from OWASP A03 to remediation",
        "What CWEs are related to SQL injection?",

        # Hybrid queries
        "Show me HIGH severity findings and explain how to fix them",
        "List CWE-89 issues and tell me what causes them",
        "What tools detect OWASP A03 and how do they work?"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}")
        print('='*70)
        print(router.explain_routing(query))
        print()
