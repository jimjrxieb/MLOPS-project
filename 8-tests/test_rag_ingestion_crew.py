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
