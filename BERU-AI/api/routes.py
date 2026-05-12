"""HTTP route handlers. Each maps an HTTP request to a graph invocation or
HITL queue operation.

Long-running operations (audit, grade-ssp) are synchronous — they take 10-90s
depending on how many controls the brain needs to assess. For the demo and the
mentor handoff this is the right call: curl returns the full result inline. For
production scale, swap to a background-task pattern (FastAPI BackgroundTasks +
a job-status endpoint).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from . import schemas as S

# Make the BERU-AI dir importable (so we get providers/, agent/, tools/).
import sys as _sys
_BERU_AI_ROOT = Path(__file__).resolve().parent.parent
if str(_BERU_AI_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_BERU_AI_ROOT))

from agent.graph import (  # noqa: E402
    run_audit,
    run_ssp_grading,
    run_freeform,
    run_assessment,
    run_ciso_briefing,
)
from tools.hitl_router import HITLRouter  # noqa: E402
from providers.ollama import OllamaProvider  # noqa: E402
from mlops.inference_tracker import get_tracker  # noqa: E402

router = APIRouter()


def _model_name() -> str:
    """Resolve the currently configured model without round-tripping to Ollama."""
    import os
    return os.environ.get("BERU_MODEL") or "beru:v1.4"


# ── helpers ───────────────────────────────────────────────────────────────────

def _run_id(prefix: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{ts}"


def _to_finding_summaries(findings: List[Dict[str, Any]]) -> List[S.FindingSummary]:
    return [
        S.FindingSummary(
            control_id=f.get("control_id", "?"),
            status=f.get("status", "?"),
            rank=f.get("rank", "?"),
            hitl_status=f.get("hitl_status", "?"),
            deterministic=bool(f.get("deterministic", False)),
            evidence_hallucination=bool(f.get("evidence_hallucination", False)),
            rank_bumped_for_hallucination=bool(f.get("rank_bumped_for_hallucination", False)),
            raw=f.get("raw", ""),
        )
        for f in findings
    ]


def _to_blocked_summaries(blocked: List[Dict[str, Any]]) -> List[S.BlockedFindingSummary]:
    return [
        S.BlockedFindingSummary(
            control_id=b.get("control_id", "?"),
            rank=b.get("rank", "?"),
            queue_id=(b.get("hitl_meta") or {}).get("queue_id"),
            reason=(b.get("hitl_meta") or {}).get("message"),
            raw=b.get("raw", ""),
        )
        for b in blocked
    ]


def _shape_run_result(prefix: str, result: Dict[str, Any]) -> S.RunResponse:
    return S.RunResponse(
        run_id=result.get("run_id", prefix),
        findings=_to_finding_summaries(result.get("findings") or []),
        blocked_findings=_to_blocked_summaries(result.get("blocked_findings") or []),
        poam_count=len(result.get("poam_items") or []),
        ssp_narrative_count=len(result.get("ssp_narratives") or []),
        evidence_archive_path=result.get("artifact_archive_path"),
        errors=result.get("errors") or [],
    )


# ── audit / grade / ask / ciso-brief ──────────────────────────────────────────


@router.post("/audit", response_model=S.RunResponse)
def audit(req: S.AuditRequest):
    rid = _run_id("audit")
    if not Path(req.scanner_output_path).exists():
        raise HTTPException(status_code=400, detail=f"scanner_output_path not found: {req.scanner_output_path}")
    tracker = get_tracker()
    with tracker.track(
        "audit",
        model=_model_name(),
        system_name=req.system_name,
        client=req.client,
        ai_context=req.ai_context,
        input_size_chars=Path(req.scanner_output_path).stat().st_size,
        run_id=rid,
    ) as m:
        result = run_audit(
            scanner_output_path=req.scanner_output_path,
            system_name=req.system_name,
            client=req.client,
            ai_context=req.ai_context,
            output_dir=f"/tmp/beru-api/{rid}",
            run_id=rid,
        )
        m.absorb_result(result)
    return _shape_run_result(rid, result)


@router.post("/grade-ssp", response_model=S.RunResponse)
def grade_ssp(req: S.GradeSSPRequest):
    if not req.ssp_path and not req.ssp_text:
        raise HTTPException(status_code=400, detail="provide ssp_path OR ssp_text")
    rid = _run_id("ssp")

    # If ssp_text was provided, persist it to a tmp file so the agent's parser
    # gets a real path to read (matches the rest of the agent's contract).
    ssp_path = req.ssp_path
    if not ssp_path:
        tmp = Path(f"/tmp/beru-api/{rid}/inline-ssp.md")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(req.ssp_text or "")
        ssp_path = str(tmp)
    elif not Path(ssp_path).exists():
        raise HTTPException(status_code=400, detail=f"ssp_path not found: {ssp_path}")

    tracker = get_tracker()
    with tracker.track(
        "grade-ssp",
        model=_model_name(),
        system_name=req.system_name,
        client=req.client,
        ai_context=req.ai_context,
        input_size_chars=Path(ssp_path).stat().st_size,
        run_id=rid,
    ) as m:
        result = run_ssp_grading(
            ssp_path=ssp_path,
            system_name=req.system_name,
            client=req.client,
            ai_context=req.ai_context,
            output_dir=f"/tmp/beru-api/{rid}",
            run_id=rid,
        )
        m.absorb_result(result)
    return _shape_run_result(rid, result)


@router.post("/assess", response_model=S.RunResponse)
def assess(req: S.AssessRequest):
    """Full GRC assessment: SSP claims + evidence → claim-vs-evidence findings,
    EVIDENCE GAPs, and POA&M items. The 'load SSP and evidence, find the gaps,
    prep the POA&M' workflow."""
    if not req.ssp_path and not req.ssp_text:
        raise HTTPException(status_code=400, detail="provide ssp_path OR ssp_text")
    rid = _run_id("assess")

    ssp_path = req.ssp_path
    if ssp_path and not Path(ssp_path).exists():
        raise HTTPException(status_code=400, detail=f"ssp_path not found: {ssp_path}")
    for ep in req.evidence_paths:
        if not Path(ep).exists():
            raise HTTPException(status_code=400, detail=f"evidence path not found: {ep}")

    ssp_size = (Path(ssp_path).stat().st_size if ssp_path else len(req.ssp_text or ""))
    ev_size = sum(len(t) for t in req.evidence_text) + sum(
        (Path(p).stat().st_size if Path(p).exists() else 0) for p in req.evidence_paths
    )
    tracker = get_tracker()
    with tracker.track(
        "assess",
        model=_model_name(),
        system_name=req.system_name,
        client=req.client,
        ai_context=req.ai_context,
        input_size_chars=ssp_size + ev_size,
        run_id=rid,
    ) as m:
        result = run_assessment(
            ssp_path=ssp_path,
            ssp_text=req.ssp_text or "",
            evidence_paths=req.evidence_paths,
            evidence_text=req.evidence_text,
            system_name=req.system_name,
            client=req.client,
            ai_context=req.ai_context,
            output_dir=f"/tmp/beru-api/{rid}",
            run_id=rid,
        )
        m.absorb_result(result)
    return _shape_run_result(rid, result)


@router.post("/ask", response_model=S.RunResponse)
def ask(req: S.AskRequest):
    rid = _run_id("ask")
    tracker = get_tracker()
    with tracker.track(
        "ask",
        model=_model_name(),
        system_name=req.system_name,
        client=req.client,
        ai_context=req.ai_context,
        input_size_chars=len(req.text or ""),
        run_id=rid,
    ) as m:
        result = run_freeform(
            text=req.text,
            system_name=req.system_name,
            client=req.client,
            ai_context=req.ai_context,
            output_dir=f"/tmp/beru-api/{rid}",
            run_id=rid,
        )
        m.absorb_result(result)
    return _shape_run_result(rid, result)


@router.post("/ciso-brief", response_model=S.CISOBriefResponse)
def ciso_brief(req: S.CISOBriefRequest):
    rid = _run_id("ciso")
    tracker = get_tracker()
    with tracker.track(
        "ciso-brief",
        model=_model_name(),
        system_name=req.system_name,
        client=req.client,
        input_size_chars=sum(len(str(f)) for f in req.findings),
        run_id=rid,
    ) as m:
        result = run_ciso_briefing(
            findings=req.findings,
            system_name=req.system_name,
            client=req.client,
            output_dir=f"/tmp/beru-api/{rid}",
            run_id=rid,
        )
        m.absorb_result(result)
    return S.CISOBriefResponse(
        run_id=rid,
        ciso_summary=result.get("ciso_summary", ""),
        evidence_archive_path=result.get("artifact_archive_path"),
        errors=result.get("errors") or [],
    )


# ── HITL queue management ─────────────────────────────────────────────────────


@router.get("/hitl/pending", response_model=List[S.HITLPendingItem])
def hitl_pending():
    items = HITLRouter().list_pending()
    out: List[S.HITLPendingItem] = []
    for it in items:
        finding = it.get("finding") or {}
        preview = (finding.get("raw") or "")[:400]
        out.append(S.HITLPendingItem(
            queue_id=it["queue_id"],
            rank=it["rank"],
            finding_id=it.get("finding_id", "unknown"),
            queued_at=it["queued_at"],
            control_id=finding.get("control_id"),
            status=it.get("status", "pending"),
            control_citation=it.get("control_citation", "MANAGE-2.2"),
            finding_preview=preview,
        ))
    return out


@router.get("/hitl/stats", response_model=S.HITLStats)
def hitl_stats():
    return S.HITLStats(**HITLRouter().stats())


@router.post("/hitl/{queue_id}/approve", response_model=S.HITLApprovalResponse)
def hitl_approve(queue_id: str, body: S.HITLApprovalRequest):
    try:
        approved = HITLRouter().approve(queue_id, approver=body.approver, notes=body.notes)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return S.HITLApprovalResponse(queue_id=queue_id, approved_finding=approved)


@router.post("/hitl/{queue_id}/reject", response_model=S.HITLRejectionResponse)
def hitl_reject(queue_id: str, body: S.HITLRejectionRequest):
    try:
        HITLRouter().reject(queue_id, reviewer=body.reviewer, reason=body.reason)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return S.HITLRejectionResponse(queue_id=queue_id, reason=body.reason)


# ── health / model info ───────────────────────────────────────────────────────


@router.get("/tracking")
def tracking_summary():
    """Cumulative MLflow tracking summary across this process's lifetime.

    The full per-call detail lives in MLflow at the tracking_uri shown below.
    Open it with: `mlflow ui --backend-store-uri file://<path>`
    """
    return get_tracker().summary()


@router.get("/health", response_model=S.HealthResponse)
def health():
    p = OllamaProvider()
    reachable = p.is_available()
    status: str = "ok" if reachable else "degraded"
    return S.HealthResponse(
        status=status,
        ollama_reachable=reachable,
        model_resolved=p.model_name,
        using_fallback=p.using_fallback,
    )


@router.get("/model-info", response_model=S.ModelInfoResponse)
def model_info():
    p = OllamaProvider()
    info = p.get_model_info()
    gguf = _BERU_AI_ROOT.parent / "3-model-registry" / "beru-v1.4-3b" / "gguf" / "beru-v1.4-q8_0.gguf"
    info["gguf_path"] = str(gguf) if gguf.exists() else None
    return S.ModelInfoResponse(**info)
