"""BERU graph state — typed shape passed between nodes.

LangGraph applies node returns as partial state updates. List fields use a
reducer so node updates append rather than overwrite.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict


InputType = Literal["scanner_output", "ssp_grading", "freeform_request", "ciso_briefing"]


class BERUState(TypedDict, total=False):
    # --- inputs ---
    input_type: InputType
    input_path: Optional[str]
    raw_input: str
    system_name: str
    client: str
    ai_context: bool

    # --- routing ---
    pending_controls: List[str]
    current_control: Optional[str]
    family_playbook_path: Optional[str]

    # --- per-control working memory ---
    control_definition: str
    evidence: List[Dict[str, Any]]
    validated_control_ids: List[str]
    validated_ai_rmf_ids: List[str]
    rag_context: str

    # --- model output (current control) ---
    raw_finding_text: str
    validation_errors: List[str]
    finding: Dict[str, Any]
    rank: str
    deterministic_finding: bool   # narrative_check set raw_finding_text → skip brain
    evidence_hallucination: bool  # groundedness check flagged unsourced evidence

    # --- accumulated outputs ---
    findings: Annotated[List[Dict[str, Any]], operator.add]
    blocked_findings: Annotated[List[Dict[str, Any]], operator.add]
    poam_items: Annotated[List[str], operator.add]
    ssp_narratives: Annotated[List[str], operator.add]
    ciso_summary: str

    # --- bookkeeping ---
    errors: Annotated[List[str], operator.add]
    run_id: str
    output_dir: str
    artifact_archive_path: Optional[str]


def new_state(
    input_type: InputType,
    *,
    raw_input: str = "",
    input_path: Optional[str] = None,
    system_name: str = "unknown-system",
    client: str = "unknown-client",
    ai_context: bool = False,
    run_id: str = "",
    output_dir: str = "/tmp/beru-out",
) -> BERUState:
    """Build a fresh state with required fields populated."""
    from datetime import datetime, timezone

    return BERUState(
        input_type=input_type,
        input_path=input_path,
        raw_input=raw_input,
        system_name=system_name,
        client=client,
        ai_context=ai_context,
        pending_controls=[],
        current_control=None,
        family_playbook_path=None,
        control_definition="",
        evidence=[],
        validated_control_ids=[],
        validated_ai_rmf_ids=[],
        rag_context="",
        raw_finding_text="",
        validation_errors=[],
        finding={},
        rank="",
        deterministic_finding=False,
        evidence_hallucination=False,
        findings=[],
        blocked_findings=[],
        poam_items=[],
        ssp_narratives=[],
        ciso_summary="",
        errors=[],
        run_id=run_id or f"beru-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        output_dir=output_dir,
        artifact_archive_path=None,
    )
