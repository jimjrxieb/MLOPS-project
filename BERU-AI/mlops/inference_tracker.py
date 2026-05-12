"""Inference Tracker — MLflow-backed observability for BERU.

Logs every BERU agent invocation with:
  - Request shape (audit / grade-ssp / ask / ciso-brief)
  - Model + provider + version
  - Latency (total wall-clock)
  - Findings produced: per-status, per-rank, deterministic vs brain-run
  - Guard activity: evidence_hallucination flags, rank-bumps
  - HITL routing: blocked-finding count
  - POA&M and SSP narrative output volume

Design principles (same as JADE's tracker, deliberately):
  - NEVER block the request if MLflow is down — log failure, move on
  - Singleton per process
  - Works for single calls AND for batch sweeps

Control traceability:
  MEASURE-2.7   — Drift monitoring: per-call metrics enable cumulative drift detection
  MANAGE-2.4    — Post-deployment evidence: every call is logged with a run_id
  AU-3          — Audit Record Content: model version + run_id + outputs all tracked
  AU-12         — Audit generation: tracker writes to disk for every call, durable
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("beru.mlops")

try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:  # pragma: no cover
    mlflow = None
    MLFLOW_AVAILABLE = False


@dataclass
class BERUInferenceMetrics:
    """Per-call metrics for a BERU agent invocation."""

    # ── inputs / params ─────────────────────────────────────────────────────
    request_type: str = "unknown"        # audit | grade-ssp | ask | ciso-brief
    model: str = ""
    provider: str = "ollama"
    system_name: str = ""
    client: str = ""
    ai_context: bool = False
    using_fallback: bool = False
    input_size_chars: int = 0

    # ── timing ─────────────────────────────────────────────────────────────
    latency_seconds: float = 0.0

    # ── outputs ────────────────────────────────────────────────────────────
    findings_count: int = 0
    blocked_count: int = 0
    poam_count: int = 0
    ssp_narrative_count: int = 0

    # ── per-status counts (over approved findings) ─────────────────────────
    pass_count: int = 0
    partial_count: int = 0
    fail_count: int = 0

    # ── per-rank counts (over approved findings) ───────────────────────────
    rank_e: int = 0
    rank_d: int = 0
    rank_c: int = 0
    rank_b: int = 0
    rank_s: int = 0

    # ── guard activity ─────────────────────────────────────────────────────
    deterministic_count: int = 0
    brain_run_count: int = 0
    evidence_hallucination_count: int = 0
    rank_bumped_count: int = 0

    # ── outcome ────────────────────────────────────────────────────────────
    success: bool = True
    error: str = ""
    run_id: str = ""
    archive_path: str = ""


_tracker_instance: Optional["InferenceTracker"] = None


def get_tracker() -> "InferenceTracker":
    """Get the singleton tracker (cheap; init runs once)."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = InferenceTracker()
    return _tracker_instance


_DEFAULT_MLRUNS = Path(__file__).resolve().parent.parent / "mlruns"


class InferenceTracker:
    """MLflow-backed BERU inference tracker.

    Usage (the route handlers use this):

        tracker = get_tracker()
        with tracker.track("grade-ssp", model="beru:v1.4") as m:
            result = run_ssp_grading(...)
            m.absorb_result(result)
    """

    def __init__(self):
        self.enabled = False
        self.experiment_name = os.environ.get(
            "MLFLOW_BERU_EXPERIMENT", "beru-inference-tracking"
        )
        self.tracking_uri = os.environ.get(
            "MLFLOW_BERU_TRACKING_URI", f"file://{_DEFAULT_MLRUNS}"
        )

        # Cumulative counters survive MLflow outages
        self.total_calls = 0
        self.total_errors = 0
        self.total_latency_seconds = 0.0
        self.total_findings_emitted = 0
        self.total_blocked = 0
        self._call_counts: Dict[str, int] = {}

        self._init_mlflow()

    def _init_mlflow(self) -> None:
        if not MLFLOW_AVAILABLE:
            logger.info("MLflow not installed — tracking disabled.")
            return
        try:
            mlflow.set_tracking_uri(self.tracking_uri)
            mlflow.set_experiment(self.experiment_name)
            self.enabled = True
            logger.info(
                f"BERU MLflow tracking enabled: experiment={self.experiment_name} "
                f"uri={self.tracking_uri}"
            )
        except Exception as e:
            logger.warning(f"MLflow init failed — tracking disabled: {e}")
            self.enabled = False

    @contextmanager
    def track(self, request_type: str, **extra):
        """Time + log a single BERU invocation."""
        m = BERUInferenceMetrics(request_type=request_type)
        for k, v in extra.items():
            if hasattr(m, k):
                setattr(m, k, v)
        start = time.perf_counter()
        try:
            yield _MetricsHandle(m)
        except Exception as e:
            m.success = False
            m.error = str(e)[:300]
            raise
        finally:
            m.latency_seconds = time.perf_counter() - start
            self.log_inference(m)

    def log_inference(self, m: BERUInferenceMetrics) -> None:
        # cumulative counters always update
        self.total_calls += 1
        self.total_latency_seconds += m.latency_seconds
        self.total_findings_emitted += m.findings_count
        self.total_blocked += m.blocked_count
        if not m.success:
            self.total_errors += 1
        key = f"{m.model or 'unknown'}:{m.request_type}"
        self._call_counts[key] = self._call_counts.get(key, 0) + 1

        if not self.enabled:
            return

        try:
            with mlflow.start_run(run_name=f"{m.request_type}-{m.run_id or self.total_calls}"):
                mlflow.log_params({
                    "request_type": m.request_type,
                    "model": m.model or "unknown",
                    "provider": m.provider,
                    "system_name": m.system_name,
                    "client": m.client,
                    "ai_context": m.ai_context,
                    "using_fallback": m.using_fallback,
                })
                mlflow.log_metrics({
                    "latency_seconds": m.latency_seconds,
                    "input_size_chars": m.input_size_chars,
                    "findings_count": m.findings_count,
                    "blocked_count": m.blocked_count,
                    "poam_count": m.poam_count,
                    "ssp_narrative_count": m.ssp_narrative_count,
                    "pass_count": m.pass_count,
                    "partial_count": m.partial_count,
                    "fail_count": m.fail_count,
                    "rank_e": m.rank_e,
                    "rank_d": m.rank_d,
                    "rank_c": m.rank_c,
                    "rank_b": m.rank_b,
                    "rank_s": m.rank_s,
                    "deterministic_count": m.deterministic_count,
                    "brain_run_count": m.brain_run_count,
                    "evidence_hallucination_count": m.evidence_hallucination_count,
                    "rank_bumped_count": m.rank_bumped_count,
                    "success": 1.0 if m.success else 0.0,
                })
                tags = {
                    "call_type": m.request_type,
                    "model_version": m.model or "unknown",
                    "system_name": m.system_name,
                    "client": m.client,
                }
                if m.run_id:
                    tags["beru_run_id"] = m.run_id
                if m.archive_path:
                    tags["evidence_archive"] = m.archive_path
                if m.error:
                    tags["error"] = m.error[:250]
                mlflow.set_tags(tags)
        except Exception as e:
            logger.debug(f"MLflow logging failed (request unaffected): {e}")

    def summary(self) -> Dict[str, Any]:
        avg_latency = (
            self.total_latency_seconds / self.total_calls
            if self.total_calls else 0.0
        )
        return {
            "tracking_enabled": self.enabled,
            "mlflow_available": MLFLOW_AVAILABLE,
            "experiment": self.experiment_name,
            "tracking_uri": self.tracking_uri,
            "total_calls": self.total_calls,
            "total_errors": self.total_errors,
            "error_rate": self.total_errors / max(self.total_calls, 1),
            "avg_latency_seconds": round(avg_latency, 3),
            "total_findings_emitted": self.total_findings_emitted,
            "total_blocked": self.total_blocked,
            "calls_by_model_request": dict(self._call_counts),
        }


class _MetricsHandle:
    """Thin wrapper exposed inside `with tracker.track(...) as m:`.

    Lets route handlers either set fields directly or hand the full agent
    result to `absorb_result()` and have the right counters extracted.
    """

    def __init__(self, m: BERUInferenceMetrics):
        self.m = m

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "m":
            super().__setattr__(name, value)
        elif hasattr(self.m, name):
            setattr(self.m, name, value)
        else:
            super().__setattr__(name, value)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.m, name)

    def absorb_result(self, result: Dict[str, Any]) -> None:
        """Extract per-call metrics from a graph result dict."""
        findings = result.get("findings") or []
        blocked = result.get("blocked_findings") or []
        m = self.m
        m.findings_count = len(findings)
        m.blocked_count = len(blocked)
        m.poam_count = len(result.get("poam_items") or [])
        m.ssp_narrative_count = len(result.get("ssp_narratives") or [])
        m.run_id = result.get("run_id", "") or m.run_id
        m.archive_path = result.get("artifact_archive_path", "") or ""

        for f in findings:
            status = (f.get("status") or "").upper()
            rank = (f.get("rank") or "").upper()
            if status == "PASS": m.pass_count += 1
            elif status == "PARTIAL": m.partial_count += 1
            elif status == "FAIL": m.fail_count += 1
            if rank == "E": m.rank_e += 1
            elif rank == "D": m.rank_d += 1
            elif rank == "C": m.rank_c += 1
            elif rank == "B": m.rank_b += 1
            elif rank == "S": m.rank_s += 1
            if f.get("deterministic"): m.deterministic_count += 1
            else: m.brain_run_count += 1
            if f.get("evidence_hallucination"): m.evidence_hallucination_count += 1
            if f.get("rank_bumped_for_hallucination"): m.rank_bumped_count += 1

        for b in blocked:
            rank = (b.get("rank") or "").upper()
            if rank == "B": m.rank_b += 1
            elif rank == "S": m.rank_s += 1
