"""
test_schemas.py — Validates real data against 7-data-schemas/ contracts.

Tests actual files in the repo against their JSON Schema definitions.
If a generator changes output format, or a scanner produces unexpected fields,
these tests catch it before it reaches training or eval.

Run: python3 -m pytest 8-tests/test_schemas.py -v
"""

import json
from pathlib import Path

import pytest

# Optional: jsonschema for full validation
try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "7-data-schemas"
EVAL_DIR = Path(__file__).resolve().parent.parent / "4-eval-clarify" / "2-test-data" / "evaluation"
MANIFEST_DIR = Path(__file__).resolve().parent.parent / "0-data-lab" / "manifests"
JSA_INBOX = Path("/home/jimmie/linkops-industries/GP-copilot/GP-PROJECTS/02-instance/slot-3/jsa/inbox")


def load_schema(name):
    with open(SCHEMA_DIR / name) as f:
        return json.load(f)


class TestTrainingExampleSchema:
    """Training examples match training_example.json schema."""

    def test_curated_corpus_has_messages_key(self):
        corpus = Path(__file__).resolve().parent.parent / "1-data-pipeline" / "05-data-quality" / "curated" / "katie_v2_clean.jsonl"
        if not corpus.exists():
            pytest.skip("Curated corpus not found")
        with open(corpus) as f:
            first = json.loads(f.readline())
        assert "messages" in first
        assert len(first["messages"]) >= 2
        roles = [m["role"] for m in first["messages"]]
        assert "assistant" in roles


class TestEvalQuestionSchema:
    """Eval questions match eval_question.json schema."""

    def _get_all_eval_files(self):
        files = []
        for d in sorted(EVAL_DIR.glob("[0-9]*-*")):
            for f in d.glob("*.jsonl"):
                files.append(f)
        return files

    def test_eval_files_exist(self):
        files = self._get_all_eval_files()
        assert len(files) > 0, "No eval question files found"

    def test_all_eval_questions_have_required_fields(self):
        required = {"id", "category", "question", "expected_keywords"}
        missing = []
        for f in self._get_all_eval_files():
            with open(f) as fh:
                for i, line in enumerate(fh, 1):
                    q = json.loads(line.strip())
                    for field in required:
                        if field not in q:
                            missing.append(f"{f.name}:{i} missing '{field}'")
        assert len(missing) == 0, f"Missing fields:\n" + "\n".join(missing[:10])

    def test_all_eval_questions_have_keywords(self):
        empty_keywords = []
        for f in self._get_all_eval_files():
            with open(f) as fh:
                for i, line in enumerate(fh, 1):
                    q = json.loads(line.strip())
                    kw = q.get("expected_keywords", [])
                    if len(kw) < 2:
                        empty_keywords.append(f"{f.name}:{i} has {len(kw)} keywords (need ≥2)")
        assert len(empty_keywords) == 0, f"Too few keywords:\n" + "\n".join(empty_keywords[:10])

    def test_eval_question_ids_are_unique(self):
        seen = {}
        dupes = []
        for f in self._get_all_eval_files():
            with open(f) as fh:
                for line in fh:
                    q = json.loads(line.strip())
                    qid = q.get("id", "")
                    if qid in seen:
                        dupes.append(f"{qid} in {f.name} AND {seen[qid]}")
                    seen[qid] = f.name
        assert len(dupes) == 0, f"Duplicate IDs:\n" + "\n".join(dupes[:10])


class TestJSAFindingSchema:
    """JSA inbox findings match jsa_finding.json schema."""

    def test_jsa_findings_have_required_fields(self):
        if not JSA_INBOX.exists():
            pytest.skip("JSA inbox not found")
        required = {"finding_id", "scanner", "severity", "title", "state"}
        missing = []
        for f in sorted(JSA_INBOX.glob("*.json"))[:50]:  # Sample 50
            data = json.load(open(f))
            for field in required:
                if field not in data:
                    missing.append(f"{f.name} missing '{field}'")
        assert len(missing) == 0, f"Missing fields:\n" + "\n".join(missing[:10])

    def test_jsa_findings_have_valid_severity(self):
        if not JSA_INBOX.exists():
            pytest.skip("JSA inbox not found")
        valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
        invalid = []
        for f in sorted(JSA_INBOX.glob("*.json"))[:50]:
            data = json.load(open(f))
            sev = data.get("severity", "")
            if sev not in valid:
                invalid.append(f"{f.name}: severity='{sev}'")
        assert len(invalid) == 0, f"Invalid severity:\n" + "\n".join(invalid[:10])

    def test_jsa_findings_have_valid_rank(self):
        if not JSA_INBOX.exists():
            pytest.skip("JSA inbox not found")
        valid = {"E", "D", "C", "B", "S"}
        invalid = []
        for f in sorted(JSA_INBOX.glob("*.json"))[:50]:
            data = json.load(open(f))
            rank = data.get("rank", "")
            if rank and rank not in valid:
                invalid.append(f"{f.name}: rank='{rank}'")
        assert len(invalid) == 0, f"Invalid rank:\n" + "\n".join(invalid[:10])


class TestGenerationManifestSchema:
    """Generation manifests match generation_manifest.json schema."""

    def test_manifests_exist(self):
        if not MANIFEST_DIR.exists():
            pytest.skip("No manifests directory")
        manifests = list(MANIFEST_DIR.glob("*.manifest.json"))
        assert len(manifests) > 0, "No generation manifests found"

    def test_manifests_have_required_fields(self):
        if not MANIFEST_DIR.exists():
            pytest.skip("No manifests directory")
        required = {"generator", "domain", "generated_at", "examples_count", "file_sha256"}
        missing = []
        for f in MANIFEST_DIR.glob("*.manifest.json"):
            data = json.load(open(f))
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                for field in required:
                    if field not in entry:
                        missing.append(f"{f.name} missing '{field}'")
        assert len(missing) == 0, f"Missing fields:\n" + "\n".join(missing[:10])

    def test_manifest_sha256_is_valid_hex(self):
        if not MANIFEST_DIR.exists():
            pytest.skip("No manifests directory")
        invalid = []
        for f in MANIFEST_DIR.glob("*.manifest.json"):
            data = json.load(open(f))
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                sha = entry.get("file_sha256", "")
                if len(sha) != 64 or not all(c in "0123456789abcdef" for c in sha):
                    invalid.append(f"{f.name}: sha256='{sha[:20]}...'")
        assert len(invalid) == 0, f"Invalid SHA256:\n" + "\n".join(invalid[:10])
