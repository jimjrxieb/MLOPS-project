"""Structured output contracts for BERU CrewAI workflows."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Rank(str, Enum):
    E = "E"
    D = "D"
    C = "C"
    B = "B"
    S = "S"


class Status(str, Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Determination(str, Enum):
    SATISFIED = "Satisfied"
    OTHER_THAN_SATISFIED = "Other Than Satisfied"
    NOT_APPLICABLE = "Not Applicable"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact: str = Field(..., min_length=1)
    validation_method: str = Field(..., min_length=1)
    supports_claim: Literal["yes", "partial", "no"]
    gap: str = Field(..., min_length=1)


class POAMItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    control_id: str = Field(..., pattern=r"^[A-Z]{2}-\d+(\(\d+\))?$")
    weakness_name: str = Field(..., min_length=3)
    weakness_description: str = Field(..., min_length=10)
    detection_method: str = Field(..., min_length=3)
    responsible_role: str = Field(..., min_length=2)
    resources_required: str = Field(..., min_length=2)
    scheduled_completion: date
    milestones: list[str] = Field(..., min_length=1)


class AuditFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding: str = Field(..., min_length=5)
    control_id: str = Field(..., pattern=r"^[A-Z]{2}-\d+(\(\d+\))?$")
    control_name: str = Field(..., min_length=3)
    ai_rmf_subcategory: str | None = None
    status: Status
    determination: Determination
    evidence_reviewed: list[EvidenceItem] = Field(..., min_length=1)
    evidence_gap: str = Field(..., min_length=1)
    likelihood: Literal["Low", "Medium", "High"]
    impact: Literal["Low", "Medium", "High"]
    rank: Rank
    control_owner: str = Field(..., min_length=2)
    poam_item: POAMItem | None = None
    ciso_summary: str = Field(..., min_length=20)


class CrewRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., min_length=1)
    workflow: str = Field(..., min_length=1)
    status: Literal["completed", "failed", "dry_run"]
    findings: list[AuditFinding] = Field(default_factory=list)
    human_review_required: bool
    reviewer_notes: str = ""
