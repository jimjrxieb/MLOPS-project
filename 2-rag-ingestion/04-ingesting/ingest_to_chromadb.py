#!/usr/bin/env python3
"""
RAG Ingestion Pipeline - Part 2 of 2
=====================================

Ingest approved preprocessed data to ChromaDB + Knowledge Graph.

Flow:
    03-preprocessed/*.jsonl → [ChromaDB + NetworkX Graph] → 4-ingested-data/rag-processed/

Prerequisites:
    1. Run preprocess_pipeline.py first
    2. Review manifest and data in 03-preprocessed/
    3. Then run this script

Usage:
    python3 ingest_to_chromadb.py                    # Ingest all approved data
    python3 ingest_to_chromadb.py --dry-run          # Preview only
    python3 ingest_to_chromadb.py --file processed_20251205_143000.jsonl  # Specific file

Architecture (RAGGraph Hybrid):
    ┌────────────────────────────────────────┐
    │           Query Router                  │
    │    (LangGraph decides: Vector/Graph)   │
    └───────────────┬────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
    ┌────────────┐         ┌────────────┐
    │ ChromaDB   │         │ NetworkX   │
    │ Vector     │         │ Knowledge  │
    │ Search     │         │ Graph      │
    └────────────┘         └────────────┘
        │                       │
        └───────────┬───────────┘
                    ▼
            Combined Context
                    ▼
               LLM Response
"""

import sys
import json
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import argparse
import hashlib

# Setup paths
SCRIPT_DIR = Path(__file__).parent
RAG_ROOT = SCRIPT_DIR.parent  # GP-MODEL-OPS/2-rag-ingestion/
MODEL_OPS_ROOT = RAG_ROOT.parent  # GP-MODEL-OPS/
GP_ROOT = MODEL_OPS_ROOT.parent  # /home/jimmie/linkops-industries/GP-copilot/
GP_S3 = GP_ROOT / "GP-S3"
REPORTS_DIR = GP_S3 / "3-mlops-reports" / "1-rag-staging"

PREPROCESSED_DIR = RAG_ROOT / "03-preprocessed"
# Centralized RAG storage in GP-MODEL-OPS/2-rag-ingestion/05-ragged-data/
INGESTED_DIR = RAG_ROOT / "05-ragged-data" / "rag-processed"
CHROMA_DIR = RAG_ROOT / "05-ragged-data"  # Primary ChromaDB location
GRAPH_DIR = GP_S3 / "knowledge-base"

# Direct ChromaDB import with Ollama embedding function
try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    import requests
    HAS_CHROMADB = True
except ImportError:
    print("Warning: ChromaDB not available")
    HAS_CHROMADB = False

# Ollama Embedding Function for ChromaDB (768-dim nomic-embed-text)
class OllamaEmbeddingFunction:
    """ChromaDB-compatible embedding function using Ollama's nomic-embed-text (768-dim)

    Key behaviors:
    - Retries failed embeddings once before skipping
    - NEVER inserts zero-vectors (they poison the vector space)
    - Returns None for failed texts so callers can filter them out
    - Logs failures to a quarantine file for investigation
    """

    QUARANTINE_FILE = RAG_ROOT / "05-ragged-data" / "embedding_quarantine.jsonl"
    MAX_RETRIES = 2
    RETRY_DELAY = 1.0  # seconds

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text:latest"):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.failed_count = 0
        self.success_count = 0

    def __call__(self, input: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Returns embeddings list aligned with input. Failed embeddings are None.
        Callers MUST filter out None entries and their corresponding documents/ids.
        """
        embeddings = []
        for text in input:
            embedding = self._embed_with_retry(text)
            embeddings.append(embedding)
        return embeddings

    def _embed_with_retry(self, text: str) -> Optional[list[float]]:
        """Embed a single text with retry logic. Returns None on failure."""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                    timeout=30
                )
                response.raise_for_status()
                embedding = response.json()["embedding"]
                self.success_count += 1
                return embedding
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    self.failed_count += 1
                    self._quarantine(text, str(e))
                    print(f"  ⚠️ Embedding failed after {self.MAX_RETRIES} attempts, SKIPPING (not inserting zero-vector)")
        return None

    def _quarantine(self, text: str, error: str):
        """Log failed embedding to quarantine file for investigation."""
        try:
            self.QUARANTINE_FILE.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.now().isoformat(),
                "error": error,
                "text_preview": text[:200],
                "text_length": len(text),
                "model": self.model
            }
            with open(self.QUARANTINE_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception:
            pass  # Don't fail the pipeline over quarantine logging

# Import NetworkX for knowledge graph
try:
    import networkx as nx
    HAS_GRAPH = True
except ImportError:
    print("Warning: NetworkX not available - graph features disabled")
    HAS_GRAPH = False

# Import Security Ontology for concept extraction
try:
    from security_ontology import SecurityOntology, enrich_document_with_concepts, extract_security_concepts
    HAS_ONTOLOGY = True
except ImportError:
    HAS_ONTOLOGY = False
    print("Warning: Security ontology not available - basic graph only")


class RAGGraphIngester:
    """
    Hybrid RAG + Graph ingestion system.

    Ingests to:
    1. ChromaDB - Vector embeddings for semantic search
    2. NetworkX - Knowledge graph for entity relationships
    """

    def __init__(self, dry_run: bool = False, verbose: bool = False, skip_graph: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.skip_graph = skip_graph
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Statistics
        self.stats = {
            'files_processed': 0,
            'items_loaded': 0,
            'items_ingested': 0,
            'items_skipped': 0,
            'graph_nodes_added': 0,
            'graph_edges_added': 0,
            'concept_links_added': 0,  # Security concept links
            'by_collection': {},
            'errors': []
        }

        # Initialize ChromaDB directly with Ollama 768-dim embedding function
        if HAS_CHROMADB and not dry_run:
            if not self.dry_run:
                print("🚀 Connecting to ChromaDB (768-dim Ollama nomic-embed-text)...")
            CHROMA_DIR.mkdir(parents=True, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(
                path=str(CHROMA_DIR / "chroma"),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            # Initialize Ollama embedding function for 768-dim embeddings
            self.embedding_function = OllamaEmbeddingFunction()
        else:
            self.chroma_client = None
            self.embedding_function = None

        # Initialize or load knowledge graph (skip if --skip-graph)
        if HAS_GRAPH and not skip_graph:
            self.graph = self._load_or_create_graph()
            # Initialize security ontology if available
            if HAS_ONTOLOGY and self.graph is not None:
                self.ontology = SecurityOntology(self.graph)
                self.ontology.build_base_graph()
                if not dry_run:
                    print(f"🔐 Security ontology loaded: {self.ontology.get_stats()['concept_nodes']} concepts")
            else:
                self.ontology = None
        else:
            self.graph = None
            self.ontology = None
            if skip_graph and not dry_run:
                print("⏭️  Skipping NetworkX graph (ChromaDB only mode)")

    def _load_or_create_graph(self) -> 'nx.DiGraph':
        """Load existing graph or create new one"""
        graph_file = GRAPH_DIR / "security_graph.pkl"

        if graph_file.exists():
            try:
                import pickle
                with open(graph_file, 'rb') as f:
                    graph = pickle.load(f)
                print(f"📊 Loaded existing graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
                return graph
            except Exception as e:
                print(f"⚠️  Could not load graph: {e}, creating new one")

        # Create new directed graph
        graph = nx.DiGraph()
        print("📊 Created new knowledge graph")
        return graph

    def run(self, specific_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the ingestion pipeline.

        Args:
            specific_file: Process only this specific file

        Returns:
            Summary dict with stats
        """
        print("\n" + "="*70)
        print("💾 RAG INGESTION PIPELINE - Part 2 of 2")
        print("="*70)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"ChromaDB: {CHROMA_DIR}")
        print(f"Graph: {GRAPH_DIR}")
        print("="*70 + "\n")

        # Find files to process
        if specific_file:
            files = [PREPROCESSED_DIR / specific_file]
        else:
            files = sorted(PREPROCESSED_DIR.glob("processed_*.jsonl"))

        if not files:
            print("⚠️  No processed JSONL files found in 03-preprocessed/")
            print("   Run preprocess_pipeline.py first")
            return {'status': 'empty', 'stats': self.stats}

        print(f"📂 Found {len(files)} file(s) to ingest\n")

        # Process each file
        for file_path in files:
            if not file_path.exists():
                print(f"⚠️  File not found: {file_path}")
                continue

            self._process_file(file_path)

        # Save graph if modified
        if not self.dry_run and self.graph and self.stats['graph_nodes_added'] > 0:
            self._save_graph()

        # Print summary
        self._print_summary()

        # Write report to GP-S3/3-mlops-reports/1-rag-staging/
        if not self.dry_run:
            self._write_report()

        return {
            'status': 'success',
            'stats': self.stats
        }

    def _process_file(self, file_path: Path):
        """Process a single JSONL file"""
        print(f"📄 Processing: {file_path.name}")
        self.stats['files_processed'] += 1

        # Load JSONL
        items = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        item = json.loads(line)
                        items.append(item)
                    except json.JSONDecodeError as e:
                        self.stats['errors'].append(f"{file_path.name}:{line_num}: {e}")

        self.stats['items_loaded'] += len(items)
        print(f"   Loaded {len(items)} items")

        if not items:
            return

        # Group by collection
        by_collection = {}
        for item in items:
            collection = item.get('metadata', {}).get('rag_collection', 'jade-general')
            if collection not in by_collection:
                by_collection[collection] = []
            by_collection[collection].append(item)

        # Ingest each collection
        for collection, collection_items in by_collection.items():
            self._ingest_collection(collection, collection_items)

        # Move file to ingested
        if not self.dry_run:
            self._move_to_ingested(file_path)

    def _ingest_collection(self, collection: str, items: List[Dict[str, Any]]):
        """Ingest items to a specific ChromaDB collection"""
        if self.verbose:
            print(f"   → {collection}: {len(items)} items")

        self.stats['by_collection'][collection] = self.stats['by_collection'].get(collection, 0) + len(items)

        if self.dry_run:
            self.stats['items_skipped'] += len(items)
            return

        # Prepare documents for ChromaDB
        documents = []
        ids = []
        metadatas = []

        for idx, item in enumerate(items):
            content = item.get('content', '')
            if not content or not content.strip():
                self.stats['items_skipped'] += 1
                continue

            metadata = item.get('metadata', {})

            # Generate DETERMINISTIC ID based on content + source context
            # This ensures: same content = same ID (enables upsert/deduplication)
            source_file = metadata.get('source_file', 'unknown')
            chunk_idx = metadata.get('chunk_index', idx)
            # Include source in hash to differentiate same content from different files
            id_seed = f"{content}|{source_file}|{chunk_idx}"
            content_hash = hashlib.md5(id_seed.encode()).hexdigest()[:16]
            doc_id = f"{collection}_{content_hash}"

            # Flatten metadata for ChromaDB (no nested dicts/lists)
            flat_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, list):
                    flat_metadata[key] = ', '.join(str(v) for v in value)
                elif isinstance(value, dict):
                    flat_metadata[key] = json.dumps(value)
                elif isinstance(value, (str, int, float, bool)):
                    flat_metadata[key] = value

            flat_metadata['ingested_at'] = datetime.now().isoformat()

            # Alias 'file' for JADE chat_handler compatibility (expects metadata.get('file'))
            if 'source_file' in flat_metadata and 'file' not in flat_metadata:
                flat_metadata['file'] = flat_metadata['source_file']

            documents.append(content)
            ids.append(doc_id)
            metadatas.append(flat_metadata)

            # Add to knowledge graph
            if self.graph is not None:
                self._add_to_graph(content, metadata, doc_id)

        if not documents:
            return

        # Deduplicate within batch (ChromaDB requires unique IDs even in upsert)
        seen_ids = {}
        deduped_docs = []
        deduped_ids = []
        deduped_meta = []
        for doc, doc_id, meta in zip(documents, ids, metadatas):
            if doc_id not in seen_ids:
                seen_ids[doc_id] = True
                deduped_docs.append(doc)
                deduped_ids.append(doc_id)
                deduped_meta.append(meta)

        if len(documents) != len(deduped_docs):
            dupes_removed = len(documents) - len(deduped_docs)
            if self.verbose:
                print(f"      ⚠️  Removed {dupes_removed} duplicates within batch")

        documents = deduped_docs
        ids = deduped_ids
        metadatas = deduped_meta

        # Ingest to ChromaDB in batches
        BATCH_SIZE = 50
        try:
            if self.chroma_client:
                # Get or create collection with 768-dim Ollama embedding function
                chroma_collection = self.chroma_client.get_or_create_collection(
                    name=collection,
                    metadata={"description": f"RAG knowledge collection for {collection}"},
                    embedding_function=self.embedding_function
                )

                total_ingested = 0
                total_skipped = 0

                # Process in batches to manage memory and provide progress
                for batch_start in range(0, len(documents), BATCH_SIZE):
                    batch_docs = documents[batch_start:batch_start + BATCH_SIZE]
                    batch_ids = ids[batch_start:batch_start + BATCH_SIZE]
                    batch_meta = metadatas[batch_start:batch_start + BATCH_SIZE]

                    # Pre-compute embeddings so we can filter out failures
                    raw_embeddings = self.embedding_function(batch_docs)

                    # Filter out documents whose embeddings failed (None entries)
                    valid_docs = []
                    valid_ids = []
                    valid_meta = []
                    valid_embeddings = []

                    for doc, doc_id, meta, emb in zip(batch_docs, batch_ids, batch_meta, raw_embeddings):
                        if emb is not None:
                            valid_docs.append(doc)
                            valid_ids.append(doc_id)
                            valid_meta.append(meta)
                            valid_embeddings.append(emb)
                        else:
                            total_skipped += 1

                    if valid_docs:
                        # Upsert with pre-computed embeddings (no zero-vectors possible)
                        chroma_collection.upsert(
                            ids=valid_ids,
                            documents=valid_docs,
                            metadatas=valid_meta,
                            embeddings=valid_embeddings
                        )
                        total_ingested += len(valid_docs)

                if total_skipped > 0:
                    print(f"      ⚠️  Skipped {total_skipped} docs with failed embeddings (NOT inserting zero-vectors)")
                    self.stats['items_skipped'] += total_skipped

                self.stats['items_ingested'] += total_ingested

                if self.verbose:
                    print(f"      ✅ Ingested {total_ingested} to ChromaDB collection '{collection}'")

        except Exception as e:
            self.stats['errors'].append(f"ChromaDB error for {collection}: {e}")
            if self.verbose:
                print(f"      ❌ Error: {e}")

    def _add_to_graph(self, content: str, metadata: Dict[str, Any], doc_id: str):
        """Add item to knowledge graph with security concept linking"""
        if self.graph is None:
            return

        # Extract entities from metadata
        domains = metadata.get('domain', [])
        if isinstance(domains, str):
            domains = [d.strip() for d in domains.split(',')]

        types = metadata.get('type', [])
        if isinstance(types, str):
            types = [t.strip() for t in types.split(',')]

        tags = metadata.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]

        source = metadata.get('source_file', 'unknown')
        collection = metadata.get('rag_collection', 'general')

        # Add document node
        self.graph.add_node(doc_id, type='document', collection=collection, source=source)
        self.stats['graph_nodes_added'] += 1

        # Add domain nodes and edges
        for domain in domains:
            if domain and domain != 'general':
                if not self.graph.has_node(domain):
                    self.graph.add_node(domain, type='domain')
                    self.stats['graph_nodes_added'] += 1
                self.graph.add_edge(doc_id, domain, relation='has_domain')
                self.stats['graph_edges_added'] += 1

        # Add type nodes and edges
        for type_ in types:
            if type_ and type_ != 'general':
                if not self.graph.has_node(type_):
                    self.graph.add_node(type_, type='doc_type')
                    self.stats['graph_nodes_added'] += 1
                self.graph.add_edge(doc_id, type_, relation='has_type')
                self.stats['graph_edges_added'] += 1

        # Add tag nodes and edges
        for tag in tags[:5]:  # Limit tags
            if tag:
                if not self.graph.has_node(tag):
                    self.graph.add_node(tag, type='tag')
                    self.stats['graph_nodes_added'] += 1
                self.graph.add_edge(doc_id, tag, relation='tagged')
                self.stats['graph_edges_added'] += 1

        # NEW: Link document to security concepts via ontology
        if self.ontology is not None:
            concept_links = self.ontology.link_document_to_concepts(doc_id, content, metadata)
            self.stats['concept_links_added'] += concept_links

    def _save_graph(self):
        """Save knowledge graph to disk"""
        GRAPH_DIR.mkdir(parents=True, exist_ok=True)
        graph_file = GRAPH_DIR / "security_graph.pkl"

        import pickle
        with open(graph_file, 'wb') as f:
            pickle.dump(self.graph, f)

        print(f"\n📊 Saved graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")

    def _move_to_ingested(self, file_path: Path):
        """Move processed file to 4-ingested-data/rag-processed/"""
        INGESTED_DIR.mkdir(parents=True, exist_ok=True)

        # Create timestamped subdirectory
        dest_dir = INGESTED_DIR / self.timestamp
        dest_dir.mkdir(exist_ok=True)

        dest_file = dest_dir / file_path.name
        shutil.move(str(file_path), str(dest_file))

        # Also move manifest if exists
        manifest_file = file_path.parent / file_path.name.replace('processed_', 'manifest_').replace('.jsonl', '.json')
        if manifest_file.exists():
            shutil.move(str(manifest_file), str(dest_dir / manifest_file.name))

        if self.verbose:
            print(f"   📁 Moved to: {dest_dir}")

    def _print_summary(self):
        """Print final summary"""
        print("\n" + "="*70)
        print("📊 INGESTION SUMMARY")
        print("="*70)

        print(f"\n  Files processed:     {self.stats['files_processed']}")
        print(f"  Items loaded:        {self.stats['items_loaded']}")
        print(f"  Items ingested:      {self.stats['items_ingested']}")
        print(f"  Items skipped:       {self.stats['items_skipped']}")

        if self.graph:
            print(f"\n  Knowledge Graph:")
            print(f"    Nodes added:       {self.stats['graph_nodes_added']}")
            print(f"    Edges added:       {self.stats['graph_edges_added']}")
            print(f"    Concept links:     {self.stats['concept_links_added']}")
            print(f"    Total nodes:       {self.graph.number_of_nodes()}")
            print(f"    Total edges:       {self.graph.number_of_edges()}")
            if self.ontology:
                print(f"    Security concepts: {self.ontology.get_stats()['concept_nodes']}")

        if self.embedding_function:
            print(f"\n  Embeddings:")
            print(f"    Succeeded:         {self.embedding_function.success_count}")
            print(f"    Failed (skipped):  {self.embedding_function.failed_count}")
            if self.embedding_function.failed_count > 0:
                print(f"    Quarantine log:    {OllamaEmbeddingFunction.QUARANTINE_FILE}")

        if self.stats['by_collection']:
            print(f"\n  By Collection:")
            for coll, count in sorted(self.stats['by_collection'].items()):
                print(f"    {coll}: {count}")

        if self.stats['errors']:
            print(f"\n  ⚠️  Errors ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:5]:
                print(f"    - {error}")

        if not self.dry_run:
            print(f"\n  📁 Data Locations:")
            print(f"    ChromaDB:  {CHROMA_DIR}")
            print(f"    Graph:     {GRAPH_DIR / 'security_graph.pkl'}")
            print(f"    Archive:   {INGESTED_DIR}")

        print("\n" + "="*70)

    def _write_report(self):
        """Write ingestion report to GP-S3/3-mlops-reports/1-rag-staging/"""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_file = REPORTS_DIR / f"rag-ingestion-{self.timestamp}.md"

        # Get ChromaDB collection totals
        collection_totals = {}
        if self.chroma_client:
            try:
                for coll in self.chroma_client.list_collections():
                    collection_totals[coll.name] = coll.count()
            except Exception:
                pass

        total_docs = sum(collection_totals.values())

        lines = [
            f"# RAG Ingestion Report",
            f"",
            f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Status:** {'SUCCESS' if not self.stats['errors'] else 'COMPLETED WITH ERRORS'}",
            f"",
            f"## Pipeline Stats",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Files processed | {self.stats['files_processed']} |",
            f"| Items loaded | {self.stats['items_loaded']} |",
            f"| Items ingested | {self.stats['items_ingested']} |",
            f"| Items skipped | {self.stats['items_skipped']} |",
            f"| Errors | {len(self.stats['errors'])} |",
        ]

        if self.embedding_function:
            lines.extend([
                f"| Embeddings succeeded | {self.embedding_function.success_count} |",
                f"| Embeddings failed | {self.embedding_function.failed_count} |",
            ])

        if self.graph:
            lines.extend([
                f"",
                f"## Knowledge Graph",
                f"",
                f"| Metric | Value |",
                f"|--------|-------|",
                f"| Nodes added | {self.stats['graph_nodes_added']} |",
                f"| Edges added | {self.stats['graph_edges_added']} |",
                f"| Concept links | {self.stats['concept_links_added']} |",
                f"| Total nodes | {self.graph.number_of_nodes()} |",
                f"| Total edges | {self.graph.number_of_edges()} |",
            ])

        if self.stats['by_collection']:
            lines.extend([
                f"",
                f"## Ingested by Collection",
                f"",
                f"| Collection | Added This Run | Total in ChromaDB |",
                f"|------------|---------------|-------------------|",
            ])
            for coll in sorted(self.stats['by_collection'].keys()):
                added = self.stats['by_collection'][coll]
                total = collection_totals.get(coll, '?')
                lines.append(f"| {coll} | {added} | {total} |")

        if collection_totals:
            lines.extend([
                f"",
                f"## Full ChromaDB State",
                f"",
                f"| Collection | Documents |",
                f"|------------|-----------|",
            ])
            for coll in sorted(collection_totals.keys()):
                lines.append(f"| {coll} | {collection_totals[coll]:,} |")
            lines.append(f"| **TOTAL** | **{total_docs:,}** |")

        if self.stats['errors']:
            lines.extend([
                f"",
                f"## Errors",
                f"",
            ])
            for error in self.stats['errors']:
                lines.append(f"- {error}")

        lines.append("")

        with open(report_file, 'w') as f:
            f.write('\n'.join(lines))

        print(f"\n  📝 Report:   {report_file}")


def main():
    parser = argparse.ArgumentParser(description='RAG Ingestion Pipeline')
    parser.add_argument('--dry-run', action='store_true', help='Preview without ingesting')
    parser.add_argument('--file', type=str, help='Process specific file only')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    parser.add_argument('--skip-graph', action='store_true', help='Skip NetworkX graph (use ChromaDB only)')

    args = parser.parse_args()

    if not HAS_CHROMADB and not args.dry_run:
        print("❌ Cannot run: ChromaDB not available")
        print("   Install: pip install chromadb")
        return 1

    ingester = RAGGraphIngester(dry_run=args.dry_run, verbose=args.verbose, skip_graph=args.skip_graph)
    result = ingester.run(specific_file=args.file)

    return 0 if result['status'] == 'success' else 1


if __name__ == "__main__":
    sys.exit(main())
