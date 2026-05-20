"""Tests for RAG ingestion prep crew — collectors, tools, agents, crew."""
import json
import sys
import tempfile
from pathlib import Path

# Add GP-MODEL-OPS root to path
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

import pytest


class TestCollectors:
    """collectors.py: run_prep_collectors() pre-flight pipeline."""

    def test_run_prep_collectors_creates_state_file(self, tmp_path):
        """run_prep_collectors writes a state.json with expected top-level keys."""
        from crewai_mlops.rag_ingestion.collectors import run_prep_collectors

        state_file = tmp_path / "state.json"
        # Use a non-existent category so discover returns 0 files — fast test
        result = run_prep_collectors(
            state_file=state_file,
            category="__nonexistent_category__",
        )

        assert state_file.exists(), "state file must be written"
        state = json.loads(state_file.read_text())

        for key in ("run_id", "stats", "pass_batch", "repair_batch", "unlabeled_batch", "routing_decisions"):
            assert key in state, f"missing key: {key}"

        assert state["stats"]["discovered"] == 0
        assert isinstance(state["pass_batch"], list)
        assert isinstance(state["repair_batch"], list)
        assert isinstance(state["unlabeled_batch"], list)
        assert isinstance(state["routing_decisions"], list)

    def test_run_prep_collectors_returns_same_data_as_state_file(self, tmp_path):
        """return value matches the state file contents."""
        from crewai_mlops.rag_ingestion.collectors import run_prep_collectors

        state_file = tmp_path / "state.json"
        result = run_prep_collectors(
            state_file=state_file,
            category="__nonexistent_category__",
        )
        state = json.loads(state_file.read_text())
        assert result["run_id"] == state["run_id"]
        assert result["stats"] == state["stats"]


class TestTools:
    """tools.py: each tool reads/writes state correctly."""

    def _make_state(self, tmp_path: Path) -> Path:
        """Write a minimal state fixture to tmp_path/state.json."""
        state = {
            "run_id": "20260520T120000Z",
            "stats": {"discovered": 5, "pass_count": 3, "repair_count": 1, "fail_count": 1,
                      "labeled_count": 2, "unlabeled_count": 1, "total_chunks": 12, "preprocessed": 4},
            "pass_batch": [],
            "repair_batch": [
                {"file": "a.md", "content_hash": "abc123", "category": "compliance",
                 "quality_gate": "REPAIR", "chunks": [{"content": "x", "metadata": {"domain": []}}],
                 "destination": "RAG", "rag_collection": "jade-general", "sql_table": None, "routing_reason": "default"}
            ],
            "unlabeled_batch": [
                {"file": "b.md", "content_hash": "def456", "category": "domain-sme",
                 "quality_gate": "PASS", "chunks": [{"content": "y", "metadata": {"domain": []}}],
                 "destination": "RAG", "rag_collection": "jade-domain-sme", "sql_table": None, "routing_reason": "domain-sme"}
            ],
            "routing_decisions": [
                {"file": "c.md", "content_hash": "ghi789", "category": "opa-policies",
                 "destination": "RAG", "rag_collection": "jade-general", "sql_table": None, "reason": "default fallback"}
            ],
            "quality_overrides": {},
            "label_overrides": {},
            "routing_overrides": {},
        }
        sf = tmp_path / "state.json"
        sf.write_text(json.dumps(state))
        return sf

    def test_get_repair_items_returns_repair_batch(self, tmp_path):
        from crewai_mlops.rag_ingestion import tools
        sf = self._make_state(tmp_path)
        tools.set_state_file(sf)
        result = tools.get_repair_items.func()
        assert "repair_batch" in result
        assert result["repair_batch"][0]["content_hash"] == "abc123"

    def test_override_quality_gate_writes_to_overrides(self, tmp_path):
        from crewai_mlops.rag_ingestion import tools
        sf = self._make_state(tmp_path)
        tools.set_state_file(sf)
        tools.override_quality_gate.func("abc123", "FAIL", "content too short")
        state = json.loads(sf.read_text())
        assert "abc123" in state["quality_overrides"]
        assert state["quality_overrides"]["abc123"]["decision"] == "FAIL"

    def test_get_unlabeled_items_returns_unlabeled_batch(self, tmp_path):
        from crewai_mlops.rag_ingestion import tools
        sf = self._make_state(tmp_path)
        tools.set_state_file(sf)
        result = tools.get_unlabeled_items.func()
        assert result["unlabeled_batch"][0]["content_hash"] == "def456"

    def test_apply_labels_writes_to_label_overrides(self, tmp_path):
        from crewai_mlops.rag_ingestion import tools
        sf = self._make_state(tmp_path)
        tools.set_state_file(sf)
        tools.apply_labels.func("def456", ["kubernetes"], ["documentation"], "intermediate", ["pod", "rbac"])
        state = json.loads(sf.read_text())
        assert "def456" in state["label_overrides"]
        assert state["label_overrides"]["def456"]["domain"] == ["kubernetes"]

    def test_get_routing_decisions_returns_decisions(self, tmp_path):
        from crewai_mlops.rag_ingestion import tools
        sf = self._make_state(tmp_path)
        tools.set_state_file(sf)
        result = tools.get_routing_decisions.func()
        assert any(d["destination"] == "RAG" for d in result["routing_decisions"])

    def test_override_routing_writes_to_routing_overrides(self, tmp_path):
        from crewai_mlops.rag_ingestion import tools
        sf = self._make_state(tmp_path)
        tools.set_state_file(sf)
        tools.override_routing.func("ghi789", "RAG", "jade-policy-as-code", "rego file — belongs in policy collection")
        state = json.loads(sf.read_text())
        assert "ghi789" in state["routing_overrides"]
        assert state["routing_overrides"]["ghi789"]["rag_collection"] == "jade-policy-as-code"

    def test_get_pipeline_stats_returns_stats_dict(self, tmp_path):
        from crewai_mlops.rag_ingestion import tools
        sf = self._make_state(tmp_path)
        tools.set_state_file(sf)
        result = tools.get_pipeline_stats.func()
        assert result["stats"]["discovered"] == 5
        assert "quality_overrides_count" in result
        assert "label_overrides_count" in result
        assert "routing_overrides_count" in result


class TestAgents:
    """agents.py: each agent has correct role, max 2 tools, distinct goals."""

    def test_four_agents_defined(self):
        from crewai_mlops.rag_ingestion.agents import (
            quality_reviewer, semantic_labeler, routing_validator, pipeline_reporter
        )
        agents = [quality_reviewer(), semantic_labeler(), routing_validator(), pipeline_reporter()]
        assert len(agents) == 4

    def test_each_agent_has_at_most_two_tools(self):
        from crewai_mlops.rag_ingestion.agents import (
            quality_reviewer, semantic_labeler, routing_validator, pipeline_reporter
        )
        for agent_factory in [quality_reviewer, semantic_labeler, routing_validator, pipeline_reporter]:
            agent = agent_factory()
            assert len(agent.tools) <= 2, f"{agent.role} has {len(agent.tools)} tools — max is 2"

    def test_agent_roles_are_unique(self):
        from crewai_mlops.rag_ingestion.agents import (
            quality_reviewer, semantic_labeler, routing_validator, pipeline_reporter
        )
        roles = [a().role for a in [quality_reviewer, semantic_labeler, routing_validator, pipeline_reporter]]
        assert len(roles) == len(set(roles)), "duplicate agent role detected"


class TestCrew:
    """prep_crew.py: crew has 4 tasks in correct dependency order."""

    def test_build_prep_crew_returns_crew_with_four_tasks(self):
        from crewai_mlops.rag_ingestion.crews.prep_crew import build_prep_crew
        crew = build_prep_crew()
        assert len(crew.tasks) == 4

    def test_tasks_have_correct_agent_assignments(self):
        from crewai_mlops.rag_ingestion.crews.prep_crew import build_prep_crew
        crew = build_prep_crew()
        roles = [task.agent.role for task in crew.tasks]
        assert roles[0] == "RAG Quality Gatekeeper"
        assert roles[1] == "Semantic Domain Classifier"
        assert roles[2] == "Collection Routing Auditor"
        assert roles[3] == "RAG Coverage Analyst"

    def test_report_task_has_context_from_all_prior_tasks(self):
        from crewai_mlops.rag_ingestion.crews.prep_crew import build_prep_crew
        crew = build_prep_crew()
        report_task = crew.tasks[3]
        assert report_task.context is not None
        assert len(report_task.context) == 3


class TestMain:
    """main.py: FastAPI app has correct routes and health check works."""

    def test_app_has_required_routes(self):
        from crewai_mlops.rag_ingestion.main import app
        paths = [r.path for r in app.routes]
        assert "/health" in paths
        assert "/run/rag-prep" in paths

    def test_health_returns_ok(self):
        from fastapi.testclient import TestClient
        from crewai_mlops.rag_ingestion.main import app
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["crew"] == "rag-ingestion"
