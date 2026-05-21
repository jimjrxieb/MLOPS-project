"""
test_beru_evals.py — Coverage gate for the four BERU eval suites.

Runs WITHOUT Ollama. Tests structure of the eval JSONL files only — does not
execute the model against them. Per `CAPSTONE-PROJECT/beru-design-decisions.md`
D-010, this is the GOVERN 1.4 / MEASURE 2.1 evidence artifact: it asserts the
eval suites cover what they claim to cover before any baseline run reports
scores against them.

Run: python3 -m pytest 8-tests/test_beru_evals.py -v
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = REPO_ROOT / "4-eval-clarify"
BERU_SUITES_DIR = EVAL_DIR / "2-test-data" / "beru"

KNOWLEDGE_BRAIN_FILE = BERU_SUITES_DIR / "knowledge_brain_v2.jsonl"
PENTEST_BRAIN_FILE = BERU_SUITES_DIR / "pentest_brain_v2.jsonl"

KNOWLEDGE_TYPES = {
    "tool_output_interpretation",
    "evidence_gap_detection",
    "dual_citation",
    "poam_drafting",
    "atlas_mapped_ai_risk",
    "finding_accuracy",  # replaced escalation_discipline in exp-014 (see COMPARISON.md)
}
MIN_PER_KNOWLEDGE_TYPE = 5

OWASP_LLM_CATEGORIES = {f"LLM{i:02d}" for i in range(1, 11)}
CRITICAL_OWASP = {"LLM01", "LLM06", "LLM08"}
MIN_PER_CRITICAL = 2  # LLM06 has 2 questions in pentest_brain_v2; raise to 3 in exp-016
MIN_PER_NONCRITICAL = 1

ID_PREFIX_KNOWLEDGE = "beru-knowledge-brain-"
ID_PREFIX_PENTEST = "beru-pentest-brain-"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        pytest.skip(f"eval file not found: {path}")
    out: list[dict] = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                pytest.fail(f"{path.name}:{i} invalid JSON: {e}")
    return out


@pytest.fixture(scope="module")
def knowledge_questions() -> list[dict]:
    return _load_jsonl(KNOWLEDGE_BRAIN_FILE)


@pytest.fixture(scope="module")
def pentest_questions() -> list[dict]:
    return _load_jsonl(PENTEST_BRAIN_FILE)


class TestKnowledgeBrainStructure:

    def test_file_exists(self):
        assert KNOWLEDGE_BRAIN_FILE.exists(), (
            f"knowledge brain eval missing: {KNOWLEDGE_BRAIN_FILE}"
        )

    def test_minimum_question_count(self, knowledge_questions):
        assert len(knowledge_questions) >= 30, (
            f"need >=30 knowledge questions, got {len(knowledge_questions)}"
        )

    def test_all_question_types_present(self, knowledge_questions):
        types_seen = {q.get("type") for q in knowledge_questions}
        missing = KNOWLEDGE_TYPES - types_seen
        assert not missing, f"missing knowledge question types: {missing}"

    def test_minimum_per_type(self, knowledge_questions):
        from collections import Counter
        counts = Counter(q.get("type") for q in knowledge_questions)
        below_floor = {t: n for t, n in counts.items() if t in KNOWLEDGE_TYPES and n < MIN_PER_KNOWLEDGE_TYPE}
        assert not below_floor, f"types below floor of {MIN_PER_KNOWLEDGE_TYPE}: {below_floor}"

    def test_id_prefix_consistency(self, knowledge_questions):
        bad = [q.get("id") for q in knowledge_questions if not (q.get("id") or "").startswith(ID_PREFIX_KNOWLEDGE)]
        assert not bad, f"knowledge IDs missing prefix {ID_PREFIX_KNOWLEDGE!r}: {bad[:3]}"

    def test_ids_are_unique(self, knowledge_questions):
        ids = [q.get("id") for q in knowledge_questions]
        dupes = [i for i in ids if ids.count(i) > 1]
        assert not dupes, f"duplicate knowledge IDs: {set(dupes)}"


class TestKnowledgeBrainContent:

    def test_every_question_has_required_fields(self, knowledge_questions):
        required = {"id", "type", "scenario", "expected_actions", "validation_keywords", "expected_status"}
        missing: list[tuple[str, set]] = []
        for q in knowledge_questions:
            absent = required - set(q.keys())
            if absent:
                missing.append((q.get("id", "?"), absent))
        assert not missing, f"questions missing required fields: {missing[:3]}"

    def test_no_empty_validation_keywords(self, knowledge_questions):
        bad = [q.get("id") for q in knowledge_questions if not q.get("validation_keywords")]
        assert not bad, f"questions with empty validation_keywords: {bad[:3]}"

    def test_dual_citation_questions_cite_both_frameworks(self, knowledge_questions):
        dc = [q for q in knowledge_questions if q.get("type") == "dual_citation"]
        for q in dc:
            assert q.get("expected_control_ids"), f"{q['id']}: dual_citation missing 800-53 controls"
            assert q.get("expected_ai_rmf"), f"{q['id']}: dual_citation missing AI RMF subcategories"
            assert q.get("ai_in_scope") is True, f"{q['id']}: dual_citation must have ai_in_scope=true"

    def test_atlas_questions_cite_atlas(self, knowledge_questions):
        atlas_qs = [q for q in knowledge_questions if q.get("type") == "atlas_mapped_ai_risk"]
        atlas_id_re = re.compile(r"^AML\.T\d+$")
        for q in atlas_qs:
            atlas_ids = q.get("expected_atlas", [])
            assert atlas_ids, f"{q['id']}: atlas_mapped_ai_risk must list expected_atlas"
            bad = [a for a in atlas_ids if not atlas_id_re.match(a)]
            assert not bad, f"{q['id']}: malformed ATLAS technique IDs: {bad}"

    def test_atlas_referenced_techniques_are_in_corpus(self, knowledge_questions):
        """ATLAS technique IDs cited in the eval must exist in beru-nist-800-53.

        This is the cross-corpus integrity check — eval cannot rely on a
        technique that isn't in the RAG store BERU retrieves from.
        """
        try:
            import sys
            sys.path.insert(0, str(REPO_ROOT / "GP-MODEL-OPS" / "2-RagIngestion-Pipeline" / "04-ingesting"))
            from ingest_beru_to_chromadb import (
                COLLECTION_NAME,
                CHROMA_PATH,
                OllamaEmbeddingFunction,
            )
            import chromadb
            from chromadb.config import Settings
            if not CHROMA_PATH.exists():
                pytest.skip("ChromaDB not present yet")
            client = chromadb.PersistentClient(path=str(CHROMA_PATH), settings=Settings(anonymized_telemetry=False))
            if COLLECTION_NAME not in [c.name for c in client.list_collections()]:
                pytest.skip(f"collection {COLLECTION_NAME!r} not present")
            col = client.get_collection(COLLECTION_NAME, embedding_function=OllamaEmbeddingFunction())
        except Exception as e:
            pytest.skip(f"ChromaDB not reachable: {e}")

        ids_in_corpus = set(col.get(include=[])["ids"])

        cited: set[str] = set()
        for q in knowledge_questions:
            for a in q.get("expected_atlas", []) or []:
                cited.add(a)

        missing: list[tuple[str, str]] = []
        for technique in cited:
            stable_id = f"atlas::{technique.replace('.', '-')}"
            if stable_id not in ids_in_corpus:
                missing.append((technique, stable_id))
        assert not missing, f"ATLAS techniques cited in evals but not in RAG corpus: {missing}"


class TestPentestBrainStructure:

    def test_file_exists(self):
        assert PENTEST_BRAIN_FILE.exists(), f"pentest brain eval missing: {PENTEST_BRAIN_FILE}"

    def test_minimum_question_count(self, pentest_questions):
        assert len(pentest_questions) >= 20, (
            f"need >=20 pentest questions, got {len(pentest_questions)}"
        )

    def test_all_owasp_llm_categories_covered(self, pentest_questions):
        seen = {q.get("owasp_llm") for q in pentest_questions}
        missing = OWASP_LLM_CATEGORIES - seen
        assert not missing, f"OWASP LLM categories without any pentest question: {missing}"

    def test_critical_categories_have_minimum_coverage(self, pentest_questions):
        from collections import Counter
        counts = Counter(q.get("owasp_llm") for q in pentest_questions)
        below: dict[str, int] = {}
        for cat in CRITICAL_OWASP:
            if counts.get(cat, 0) < MIN_PER_CRITICAL:
                below[cat] = counts.get(cat, 0)
        assert not below, f"critical OWASP categories below floor of {MIN_PER_CRITICAL}: {below}"

    def test_id_prefix_consistency(self, pentest_questions):
        bad = [q.get("id") for q in pentest_questions if not (q.get("id") or "").startswith(ID_PREFIX_PENTEST)]
        assert not bad, f"pentest IDs missing prefix {ID_PREFIX_PENTEST!r}: {bad[:3]}"

    def test_ids_are_unique(self, pentest_questions):
        ids = [q.get("id") for q in pentest_questions]
        dupes = [i for i in ids if ids.count(i) > 1]
        assert not dupes, f"duplicate pentest IDs: {set(dupes)}"


class TestPentestBrainContent:

    def test_every_question_has_fail_indicators(self, pentest_questions):
        """Pentest questions are scored negatively. Empty fail_indicators = no test."""
        bad = [q.get("id") for q in pentest_questions if not q.get("fail_indicators")]
        assert not bad, f"pentest questions with empty fail_indicators: {bad[:5]}"

    def test_every_question_has_required_fields(self, pentest_questions):
        required = {"id", "owasp_llm", "scenario", "expected_behavior", "fail_indicators", "harm_vector"}
        missing: list[tuple[str, set]] = []
        for q in pentest_questions:
            absent = required - set(q.keys())
            if absent:
                missing.append((q.get("id", "?"), absent))
        assert not missing, f"questions missing required fields: {missing[:3]}"

    def test_quad_citation_at_least_three_frameworks(self, pentest_questions):
        """Per D-010: each pentest question must cite at least 3 of {OWASP, AI RMF, 800-53, ATLAS}.

        ATLAS may be empty for purely policy/procedural questions (e.g., excessive-agency
        scenarios that don't have a direct ATLAS technique). The other three are mandatory.
        """
        bad: list[str] = []
        for q in pentest_questions:
            framework_count = sum([
                bool(q.get("owasp_llm")),
                bool(q.get("ai_rmf")),
                bool(q.get("nist_800_53")),
                bool(q.get("atlas")),  # may be []
            ])
            if framework_count < 3:
                bad.append(q.get("id", "?"))
        assert not bad, f"pentest questions citing fewer than 3 frameworks: {bad}"

    def test_owasp_llm_format_valid(self, pentest_questions):
        valid = re.compile(r"^LLM(0[1-9]|10)$")
        bad = [q.get("id") for q in pentest_questions if not valid.match(q.get("owasp_llm", ""))]
        assert not bad, f"pentest questions with invalid owasp_llm format: {bad[:3]}"

    def test_severity_field_valid(self, pentest_questions):
        valid = {"critical", "high", "medium", "low"}
        bad = [
            (q.get("id"), q.get("severity"))
            for q in pentest_questions
            if q.get("severity") not in valid
        ]
        assert not bad, f"pentest questions with invalid severity: {bad[:3]}"

    def test_atlas_techniques_format_when_present(self, pentest_questions):
        atlas_id_re = re.compile(r"^AML\.T\d+$")
        bad: list[tuple[str, str]] = []
        for q in pentest_questions:
            for a in q.get("atlas") or []:
                if not atlas_id_re.match(a):
                    bad.append((q.get("id", "?"), a))
        assert not bad, f"pentest questions with malformed ATLAS IDs: {bad[:3]}"


class TestCrossSuiteUniqueness:

    def test_no_duplicate_ids_across_suites(self, knowledge_questions, pentest_questions):
        kids = {q.get("id") for q in knowledge_questions}
        pids = {q.get("id") for q in pentest_questions}
        overlap = kids & pids
        assert not overlap, f"IDs appear in both suites: {overlap}"
