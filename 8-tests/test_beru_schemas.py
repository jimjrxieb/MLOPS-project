"""
BERU-AI Schema Validation Tests
Validates training data and risk summary output against JSON schemas.
Run BEFORE training: python3 -m pytest 8-tests/test_beru_schemas.py -v
"""

import json
import re
from pathlib import Path

import pytest

SCHEMA_DIR = Path(__file__).parent.parent / "7-data-schemas"


def load_schema(name: str) -> dict:
    schema_path = SCHEMA_DIR / name
    assert schema_path.exists(), f"Schema not found: {schema_path}"
    with open(schema_path) as f:
        return json.load(f)


class TestBeruTrainingSchema:
    """Validate BERU training example schema and examples."""

    def setup_method(self):
        self.schema = load_schema("beru_training_example.json")

    def test_schema_has_required_fields(self):
        assert self.schema["required"] == ["messages"]
        msg_items = self.schema["properties"]["messages"]["items"]
        assert "role" in msg_items["required"]
        assert "content" in msg_items["required"]

    def test_schema_enforces_chatml_roles(self):
        role_enum = self.schema["properties"]["messages"]["items"]["properties"]["role"]["enum"]
        assert set(role_enum) == {"system", "user", "assistant"}

    def test_schema_requires_assistant_response(self):
        contains = self.schema["properties"]["messages"]["contains"]
        assert contains["properties"]["role"]["const"] == "assistant"

    def test_schema_requires_min_two_messages(self):
        assert self.schema["properties"]["messages"]["minItems"] == 2

    def test_embedded_example_is_valid(self):
        """The example in the schema itself should be well-formed."""
        examples = self.schema.get("examples", [])
        assert len(examples) >= 1, "Schema must include at least one example"
        example = examples[0]
        messages = example["messages"]
        assert len(messages) >= 2
        roles = [m["role"] for m in messages]
        assert "assistant" in roles
        for msg in messages:
            assert len(msg["content"]) > 0

    def test_example_contains_nist_control(self):
        """BERU training examples should reference real NIST controls."""
        examples = self.schema.get("examples", [])
        assistant_msgs = [
            m["content"] for ex in examples
            for m in ex["messages"] if m["role"] == "assistant"
        ]
        combined = " ".join(assistant_msgs)
        nist_pattern = re.compile(r"\b[A-Z]{2}-\d+\b")
        matches = nist_pattern.findall(combined)
        assert len(matches) > 0, "BERU training examples must reference real NIST control IDs"

    def test_metadata_field_is_optional(self):
        assert "_metadata" not in self.schema["required"]


class TestBeruRiskSummarySchema:
    """Validate BERU risk summary output schema."""

    def setup_method(self):
        self.schema = load_schema("beru_risk_summary.json")

    def test_schema_has_required_fields(self):
        assert set(self.schema["required"]) == {
            "finding_id", "triage", "ciso_summary", "evidence"
        }

    def test_triage_has_required_fields(self):
        triage = self.schema["properties"]["triage"]
        assert set(triage["required"]) == {
            "priority", "severity_context", "blast_radius",
            "immediate_action", "remediation", "nist_controls", "confidence"
        }

    def test_priority_enum_is_p1_through_p4(self):
        priority = self.schema["properties"]["triage"]["properties"]["priority"]
        assert priority["enum"] == ["P1", "P2", "P3", "P4"]

    def test_nist_controls_pattern_validates_format(self):
        nist = self.schema["properties"]["triage"]["properties"]["nist_controls"]
        assert nist["items"]["pattern"] == "^[A-Z]{2}-[0-9]+$"
        assert nist["minItems"] == 1

    def test_confidence_is_bounded(self):
        conf = self.schema["properties"]["triage"]["properties"]["confidence"]
        assert conf["minimum"] == 0.0
        assert conf["maximum"] == 1.0

    def test_ciso_summary_has_min_length(self):
        summary = self.schema["properties"]["ciso_summary"]
        assert summary["minLength"] == 50

    def test_immediate_action_has_min_length(self):
        action = self.schema["properties"]["triage"]["properties"]["immediate_action"]
        assert action["minLength"] == 10

    def test_evidence_has_required_fields(self):
        evidence = self.schema["properties"]["evidence"]
        assert set(evidence["required"]) == {
            "scanner", "finding_type", "timestamp"
        }

    def test_rank_enum_matches_system(self):
        rank = self.schema["properties"]["rank"]
        assert rank["enum"] == ["E", "D", "C", "B", "S"]
