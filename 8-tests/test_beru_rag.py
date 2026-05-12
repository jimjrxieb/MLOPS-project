"""
test_beru_rag.py — Data quality gate for BERU's `beru-nist-800-53` ChromaDB collection.

Satisfies NIST 800-53 MEASURE-adjacent controls and AI RMF MEASURE 2.1 / GOVERN 1.4
("test sets, metrics, and details about the tools used during TEVV are documented")
by asserting that the BERU RAG corpus meets minimum structural and content quality
before any model promotion gate.

Skips cleanly if:
  - ChromaDB store does not exist yet (M2 not run)
  - Ollama is not reachable (cannot construct query embedding)

Run: python3 -m pytest 8-tests/test_beru_rag.py -v
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INGEST_DIR = REPO_ROOT / "GP-MODEL-OPS" / "2-rag-ingestion" / "04-ingesting"
sys.path.insert(0, str(INGEST_DIR))

import chromadb
from chromadb.config import Settings

import requests

from ingest_beru_to_chromadb import (
    COLLECTION_NAME,
    CHROMA_PATH,
    EMBED_DIM,
    EMBED_MODEL,
    OLLAMA_URL,
    STUB_PATTERNS,
    OllamaEmbeddingFunction,
)


REQUIRED_METADATA_KEYS = {"framework", "source_file", "source_path", "ingested_at"}
EXPECTED_FRAMEWORKS = {"nist-800-53-rev5", "nist-ai-rmf-1.0", "mitre-atlas-v4.7", "crosswalk"}
MIN_TOTAL_DOCS = 70
MIN_CONTROL_DOCS = 30
MIN_AI_RMF_DOCS = 20
MIN_ATLAS_TECHNIQUES = 10


def _ollama_reachable() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        if r.status_code != 200:
            return False
        models = [m.get("name", "") for m in r.json().get("models", [])]
        return any(EMBED_MODEL in n or "nomic-embed" in n for n in models)
    except Exception:
        return False


@pytest.fixture(scope="module")
def collection():
    if not CHROMA_PATH.exists():
        pytest.skip(f"ChromaDB store not present at {CHROMA_PATH} — run BERU-AI/ingest_rag.py first")
    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=Settings(anonymized_telemetry=False),
    )
    if COLLECTION_NAME not in [c.name for c in client.list_collections()]:
        pytest.skip(f"collection {COLLECTION_NAME!r} not found — run BERU-AI/ingest_rag.py first")
    ef = OllamaEmbeddingFunction()
    return client.get_collection(COLLECTION_NAME, embedding_function=ef)


@pytest.fixture(scope="module")
def all_docs(collection):
    return collection.get(include=["metadatas", "documents"])


class TestCollectionStructure:
    """Structural checks — no Ollama needed."""

    def test_collection_meets_minimum_size(self, collection):
        n = collection.count()
        assert n >= MIN_TOTAL_DOCS, (
            f"BERU RAG collection has {n} docs, below floor of {MIN_TOTAL_DOCS}"
        )

    def test_framework_breakdown_complete(self, all_docs):
        seen = {(m or {}).get("framework") for m in all_docs["metadatas"]}
        missing = EXPECTED_FRAMEWORKS - seen
        assert not missing, f"missing framework partitions: {missing}; saw: {seen}"

    def test_minimum_nist_800_53_controls(self, all_docs):
        controls = {
            (m or {}).get("control_id")
            for m in all_docs["metadatas"]
            if (m or {}).get("framework") == "nist-800-53-rev5"
        }
        controls.discard(None)
        controls.discard("")
        assert len(controls) >= MIN_CONTROL_DOCS, (
            f"only {len(controls)} unique 800-53 control_ids; floor is {MIN_CONTROL_DOCS}"
        )

    def test_minimum_ai_rmf_subcategories(self, all_docs):
        subs = {
            (m or {}).get("subcategory_id")
            for m in all_docs["metadatas"]
            if (m or {}).get("framework") == "nist-ai-rmf-1.0"
        }
        subs.discard(None)
        subs.discard("")
        assert len(subs) >= MIN_AI_RMF_DOCS, (
            f"only {len(subs)} unique AI RMF subcategories; floor is {MIN_AI_RMF_DOCS}"
        )

    def test_all_three_ai_rmf_functions_present(self, all_docs):
        funcs = {
            (m or {}).get("function")
            for m in all_docs["metadatas"]
            if (m or {}).get("framework") == "nist-ai-rmf-1.0"
        }
        funcs.discard(None)
        for required in {"GOVERN", "MAP", "MANAGE"}:
            assert required in funcs, f"AI RMF function {required} missing; saw {funcs}"

    def test_minimum_atlas_techniques(self, all_docs):
        techs = {
            (m or {}).get("technique_id")
            for m in all_docs["metadatas"]
            if (m or {}).get("framework") == "mitre-atlas-v4.7"
        }
        techs.discard(None)
        techs.discard("")
        assert len(techs) >= MIN_ATLAS_TECHNIQUES, (
            f"only {len(techs)} unique ATLAS techniques; floor is {MIN_ATLAS_TECHNIQUES}"
        )

    def test_atlas_covers_critical_owasp_llm_techniques(self, all_docs):
        """Every BERU-relevant OWASP LLM Top 10 entry must have at least one ATLAS technique mapping."""
        techs = {
            (m or {}).get("technique_id")
            for m in all_docs["metadatas"]
            if (m or {}).get("framework") == "mitre-atlas-v4.7"
        }
        techs.discard(None)
        critical = {
            "AML.T0051",  # Prompt Injection (LLM01)
            "AML.T0024",  # Exfiltration via Inference (LLM06)
            "AML.T0020",  # Poison Training Data (LLM03)
            "AML.T0050",  # Command Interpreter (LLM07)
            "AML.T0029",  # Denial of ML Service (LLM04)
            "AML.T0044",  # Full Model Access (LLM10)
        }
        missing = critical - techs
        assert not missing, f"critical ATLAS techniques missing from corpus: {missing}"


class TestProvenanceMetadata:
    """SR-4 / MAP 4.1 — every chunk traceable to a source file."""

    def test_every_chunk_has_required_metadata(self, all_docs):
        missing_keys: list[tuple[str, set]] = []
        for cid, m in zip(all_docs["ids"], all_docs["metadatas"]):
            present = set((m or {}).keys())
            absent = REQUIRED_METADATA_KEYS - present
            if absent:
                missing_keys.append((cid, absent))
        assert not missing_keys, f"chunks missing metadata keys: {missing_keys[:5]}"

    def test_source_paths_resolve_to_real_files(self, all_docs):
        seen_paths = {(m or {}).get("source_path") for m in all_docs["metadatas"]}
        seen_paths.discard(None)
        for sp in seen_paths:
            full = REPO_ROOT / sp
            assert full.exists(), f"source_path {sp!r} does not resolve to a real file"

    def test_no_unknown_framework_values(self, all_docs):
        for m in all_docs["metadatas"]:
            fw = (m or {}).get("framework")
            assert fw in EXPECTED_FRAMEWORKS, f"unexpected framework value: {fw!r}"


class TestContentIntegrity:
    """SI-7 — stored documents must not contain known synthetic-stub patterns."""

    def test_no_stub_patterns_in_stored_docs(self, all_docs):
        offenders: list[tuple[str, str]] = []
        for cid, doc in zip(all_docs["ids"], all_docs["documents"]):
            for pat in STUB_PATTERNS:
                if pat.search(doc):
                    offenders.append((cid, pat.pattern))
                    break
        assert not offenders, f"stub patterns detected in stored docs: {offenders[:5]}"

    def test_stable_id_format(self, all_docs):
        valid = re.compile(
            r"^("
            r"800-53::[A-Z]{2}-\d+(\(\d+\))?|"
            r"ai-rmf::(GOVERN|MAP|MANAGE)-\d+\.\d+|"
            r"atlas::AML-T\d+|"
            r"crosswalk::[\w-]+"
            r")$"
        )
        bad = [cid for cid in all_docs["ids"] if not valid.match(cid)]
        assert not bad, f"invalid id formats: {bad[:5]}"

    def test_no_empty_documents(self, all_docs):
        empties = [cid for cid, doc in zip(all_docs["ids"], all_docs["documents"]) if not (doc or "").strip()]
        assert not empties, f"empty documents: {empties[:5]}"


class TestDirectIDLookup:
    """Sanity — known IDs must resolve to real content."""

    @pytest.mark.parametrize("doc_id,expected_substring", [
        ("800-53::AC-2", "Account Management"),
        ("800-53::SI-2", "Flaw"),
        ("ai-rmf::GOVERN-1.1", "Policies, processes, procedures"),
        ("atlas::AML-T0051", "Prompt Injection"),
        ("atlas::AML-T0024", "Exfiltration"),
        ("crosswalk::800-53-to-ai-rmf", "AI RMF"),
    ])
    def test_known_id_returns_expected_content(self, collection, doc_id, expected_substring):
        result = collection.get(ids=[doc_id], include=["documents"])
        assert result["ids"], f"id {doc_id!r} not in collection"
        assert expected_substring in result["documents"][0], (
            f"id {doc_id!r} stored but content does not contain {expected_substring!r}"
        )


@pytest.mark.skipif(not _ollama_reachable(), reason="Ollama nomic-embed-text not reachable")
class TestSemanticRetrieval:
    """End-to-end sanity — does the embedding round-trip work for a known query?"""

    def test_semantic_query_for_ac2_returns_ac2_in_top_results(self, collection):
        q = collection.query(query_texts=["AC-2 account management lifecycle"], n_results=3)
        ids = q["ids"][0]
        assert "800-53::AC-2" in ids, f"AC-2 not in top-3 for AC-2 query; got {ids}"

    def test_semantic_query_for_si2_returns_si2_in_top_results(self, collection):
        q = collection.query(query_texts=["SI-2 flaw remediation patching"], n_results=3)
        ids = q["ids"][0]
        assert "800-53::SI-2" in ids, f"SI-2 not in top-3 for SI-2 query; got {ids}"

    def test_semantic_query_for_prompt_injection_returns_atlas(self, collection):
        q = collection.query(
            query_texts=["prompt injection attack against LLM system prompt"],
            n_results=5,
        )
        ids = q["ids"][0]
        atlas_hits = [i for i in ids if i.startswith("atlas::")]
        assert atlas_hits, f"no ATLAS techniques in top-5 for prompt-injection query; got {ids}"

    def test_query_embedding_dim_matches_collection(self, collection):
        ef = OllamaEmbeddingFunction()
        v = ef(["dimension probe"])[0]
        assert len(v) == EMBED_DIM, f"query embedding produced {len(v)} dims, collection expects {EMBED_DIM}"
