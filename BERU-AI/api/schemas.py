"""Pydantic request/response models for the BERU API.

Schemas are deliberately small — the agent returns rich dicts but most fields
are internal. The HTTP boundary returns the minimum a caller needs.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AuditRequest(BaseModel):
    """POST /audit body."""
    scanner_output_path: str = Field(..., description="Path to scanner output (json/csv/log)")
    system_name: str = "unknown-system"
    client: str = "unknown-client"
    ai_context: bool = False


class GradeSSPRequest(BaseModel):
    """POST /grade-ssp body."""
    ssp_path: Optional[str] = Field(None, description="Path to SSP markdown file")
    ssp_text: Optional[str] = Field(None, description="SSP markdown as a string (alternative to ssp_path)")
    system_name: str = "unknown-system"
    client: str = "unknown-client"
    ai_context: bool = False


class AskRequest(BaseModel):
    """POST /ask body — freeform compliance question."""
    text: str
    system_name: str = "unknown-system"
    client: str = "unknown-client"
    ai_context: bool = False


class AssessRequest(BaseModel):
    """POST /assess body — full GRC assessment: SSP claims + evidence → gaps + POA&M.

    Provide the SSP via ssp_path OR ssp_text. Evidence is optional but is the
    point — scanner output / policy docs / command outputs that confirm or
    contradict the SSP's claims. Each evidence file is auto-parsed as scanner
    output if possible; otherwise treated as a policy/text artifact.
    """
    ssp_path: Optional[str] = Field(None, description="Path to SSP markdown file")
    ssp_text: Optional[str] = Field(None, description="SSP markdown as a string")
    evidence_paths: List[str] = Field(default_factory=list, description="Paths to evidence files (scanner output, policy docs, command outputs)")
    evidence_text: List[str] = Field(default_factory=list, description="Inline evidence blobs (pasted text)")
    system_name: str = "unknown-system"
    client: str = "unknown-client"
    ai_context: bool = False


class CISOBriefRequest(BaseModel):
    """POST /ciso-brief body — synthesize an executive summary over pre-computed findings."""
    findings: List[Dict[str, Any]] = Field(..., description="List of BERU finding dicts")
    system_name: str = "unknown-system"
    client: str = "unknown-client"


class FindingSummary(BaseModel):
    """Per-finding response item."""
    control_id: str
    status: str
    rank: str
    hitl_status: str
    deterministic: bool = False
    evidence_hallucination: bool = False
    rank_bumped_for_hallucination: bool = False
    raw: str = ""  # the full 9-field finding text the model (or Guard 1) produced


class BlockedFindingSummary(BaseModel):
    """B/S-rank finding sent to the HITL queue."""
    control_id: str
    rank: str
    queue_id: Optional[str] = None
    reason: Optional[str] = None
    raw: str = ""  # the finding text that was held for human review


class RunResponse(BaseModel):
    run_id: str
    findings: List[FindingSummary]
    blocked_findings: List[BlockedFindingSummary]
    poam_count: int
    ssp_narrative_count: int
    evidence_archive_path: Optional[str] = None
    errors: List[str] = []


class CISOBriefResponse(BaseModel):
    run_id: str
    ciso_summary: str
    evidence_archive_path: Optional[str] = None
    errors: List[str] = []


# ── HITL ──────────────────────────────────────────────────────────────────────


class HITLPendingItem(BaseModel):
    queue_id: str
    rank: str
    finding_id: str
    queued_at: str
    control_id: Optional[str] = None
    status: str
    control_citation: str
    finding_preview: Optional[str] = None


class HITLApprovalRequest(BaseModel):
    approver: str = "human"
    notes: str = ""


class HITLRejectionRequest(BaseModel):
    reviewer: str = "human"
    reason: str = ""


class HITLApprovalResponse(BaseModel):
    queue_id: str
    status: Literal["approved"] = "approved"
    approved_finding: Dict[str, Any]


class HITLRejectionResponse(BaseModel):
    queue_id: str
    status: Literal["rejected"] = "rejected"
    reason: str


class HITLStats(BaseModel):
    pending: int
    approved: int
    rejected: int


# ── Health / model info ───────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    ollama_reachable: bool
    model_resolved: str
    using_fallback: bool


class ModelInfoResponse(BaseModel):
    model: str
    primary_model: str
    using_fallback: bool
    base_url: str
    available: bool
    gguf_path: Optional[str] = None
