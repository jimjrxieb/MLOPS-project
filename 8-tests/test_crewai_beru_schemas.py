"""Tests for BERU CrewAI structured output contracts."""

from datetime import date

import pytest
from pydantic import ValidationError

from crewai_mlops.beru.schemas import AuditFinding, CrewRunSummary


def _valid_audit_finding() -> dict:
    return {
        "finding": "Service account has cluster-admin binding in production.",
        "control_id": "AC-6",
        "control_name": "Least Privilege",
        "ai_rmf_subcategory": None,
        "status": "FAIL",
        "determination": "Other Than Satisfied",
        "evidence_reviewed": [
            {
                "artifact": "kubescape-results.json",
                "validation_method": "RBAC scan review",
                "supports_claim": "no",
                "gap": "Privileged binding remains active.",
            }
        ],
        "evidence_gap": "No evidence of least-privilege enforcement for the service account.",
        "likelihood": "High",
        "impact": "High",
        "rank": "B",
        "control_owner": "Platform Security",
        "poam_item": {
            "control_id": "AC-6",
            "weakness_name": "Excessive service account privileges",
            "weakness_description": (
                "A production service account has cluster-admin privileges without "
                "documented business justification or compensating controls."
            ),
            "detection_method": "Kubescape RBAC scan",
            "responsible_role": "Platform Security",
            "resources_required": "4 engineering hours",
            "scheduled_completion": "2026-06-30",
            "milestones": ["Remove binding or replace with scoped RoleBinding by 2026-06-15"],
        },
        "ciso_summary": (
            "A production service account has broad administrative access, increasing "
            "the blast radius of credential misuse."
        ),
    }


def test_audit_finding_contract_accepts_valid_output():
    finding = AuditFinding.model_validate(_valid_audit_finding())
    assert finding.control_id == "AC-6"
    assert finding.poam_item.scheduled_completion == date(2026, 6, 30)


def test_audit_finding_contract_rejects_invalid_control_id():
    payload = _valid_audit_finding()
    payload["control_id"] = "ACCESS-6"
    with pytest.raises(ValidationError):
        AuditFinding.model_validate(payload)


def test_crew_run_summary_wraps_findings_for_review():
    summary = CrewRunSummary.model_validate(
        {
            "run_id": "20260521T120000Z",
            "workflow": "beru-audit",
            "status": "completed",
            "findings": [_valid_audit_finding()],
            "human_review_required": True,
            "reviewer_notes": "B-rank finding requires approval before auto-output.",
        }
    )
    assert summary.findings[0].rank == "B"
    assert summary.human_review_required is True
