"""
Inference Tracker — MLflow-backed observability for JADE/Katie inference.

Logs every inference call with:
- Model version, provider, method (generate/chat/rag_query)
- Latency breakdown (total, LLM, RAG)
- Prompt/response token estimates
- Success/failure status
- Rank classification accuracy (when available)

Design principles:
- NEVER block inference if MLflow is down — log failure, move on
- Singleton pattern — one tracker per process
- Batch-friendly — works for single calls and bulk triage
"""

import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("jade.mlops")

# MLflow is optional — inference works without it
try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None
    MLFLOW_AVAILABLE = False


@dataclass
class InferenceMetrics:
    """Metrics collected per inference call."""
    model: str = ""
    provider: str = "ollama"
    method: str = "generate"           # generate, chat, rag_query, approve
    prompt_chars: int = 0
    response_chars: int = 0
    latency_ms: float = 0.0
    llm_latency_ms: float = 0.0       # LLM-only time (excludes RAG)
    rag_latency_ms: float = 0.0       # RAG retrieval time
    rag_context_used: bool = False
    rag_sources_count: int = 0
    success: bool = True
    error: str = ""
    temperature: float = 0.7
    max_tokens: int = 500
    using_fallback: bool = False
    # Rank-specific (for approve/triage calls)
    rank: str = ""
    decision: str = ""                 # approve/deny/escalate
    confidence: float = 0.0
    ml_prediction_used: bool = False


# Singleton
_tracker_instance: Optional["InferenceTracker"] = None


def get_tracker() -> "InferenceTracker":
    """Get singleton InferenceTracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = InferenceTracker()
    return _tracker_instance


class InferenceTracker:
    """
    MLflow-backed inference tracker for JADE.

    Usage:
        tracker = get_tracker()

        # Simple timing
        with tracker.track("generate", model="jade:v1.0") as metrics:
            response = ollama.generate(prompt)
            metrics.prompt_chars = len(prompt)
            metrics.response_chars = len(response)

        # Or manual
        tracker.log_inference(InferenceMetrics(
            model="jade:v1.0", method="generate", latency_ms=142.5, ...
        ))
    """

    def __init__(self):
        self.enabled = False
        self.experiment_name = os.environ.get(
            "MLFLOW_EXPERIMENT", "jade-inference-tracking"
        )
        self.tracking_uri = os.environ.get(
            "MLFLOW_TRACKING_URI", "file:///home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/JADE-AI/mlruns"
        )

        # Cumulative counters (survive MLflow outages)
        self.total_calls = 0
        self.total_errors = 0
        self.total_latency_ms = 0.0
        self._call_counts: Dict[str, int] = {}

        self._init_mlflow()

    def _init_mlflow(self):
        """Initialize MLflow tracking. Fails silently."""
        if not MLFLOW_AVAILABLE:
            logger.info("MLflow not installed — tracking disabled. pip install mlflow to enable.")
            return

        try:
            mlflow.set_tracking_uri(self.tracking_uri)
            mlflow.set_experiment(self.experiment_name)
            self.enabled = True
            logger.info(
                f"MLflow tracking enabled: experiment={self.experiment_name}, "
                f"uri={self.tracking_uri}"
            )
        except Exception as e:
            logger.warning(f"MLflow init failed — tracking disabled: {e}")
            self.enabled = False

    @contextmanager
    def track(self, method: str, model: str = "", **extra_params):
        """
        Context manager for timing inference calls.

        Usage:
            with tracker.track("generate", model="jade:v1.0") as m:
                response = provider.generate(prompt)
                m.prompt_chars = len(prompt)
                m.response_chars = len(response)
        """
        metrics = InferenceMetrics(
            model=model,
            method=method,
            **{k: v for k, v in extra_params.items() if hasattr(InferenceMetrics, k)}
        )
        start = time.perf_counter()

        try:
            yield metrics
        except Exception as e:
            metrics.success = False
            metrics.error = str(e)[:200]
            raise
        finally:
            metrics.latency_ms = (time.perf_counter() - start) * 1000
            self.log_inference(metrics)

    def log_inference(self, metrics: InferenceMetrics):
        """Log a single inference call to MLflow + internal counters."""
        # Always update internal counters (even if MLflow is down)
        self.total_calls += 1
        self.total_latency_ms += metrics.latency_ms
        if not metrics.success:
            self.total_errors += 1
        method_key = f"{metrics.model}:{metrics.method}"
        self._call_counts[method_key] = self._call_counts.get(method_key, 0) + 1

        if not self.enabled:
            return

        try:
            with mlflow.start_run(run_name=f"{metrics.method}_{self.total_calls}"):
                # Parameters (what was configured)
                mlflow.log_params({
                    "model": metrics.model or "unknown",
                    "provider": metrics.provider,
                    "method": metrics.method,
                    "temperature": metrics.temperature,
                    "max_tokens": metrics.max_tokens,
                    "using_fallback": metrics.using_fallback,
                    "rag_context_used": metrics.rag_context_used,
                })

                # Metrics (what happened)
                log_metrics = {
                    "latency_ms": metrics.latency_ms,
                    "prompt_chars": metrics.prompt_chars,
                    "response_chars": metrics.response_chars,
                    "success": 1.0 if metrics.success else 0.0,
                }

                if metrics.llm_latency_ms > 0:
                    log_metrics["llm_latency_ms"] = metrics.llm_latency_ms
                if metrics.rag_latency_ms > 0:
                    log_metrics["rag_latency_ms"] = metrics.rag_latency_ms
                if metrics.rag_sources_count > 0:
                    log_metrics["rag_sources_count"] = metrics.rag_sources_count
                if metrics.confidence > 0:
                    log_metrics["confidence"] = metrics.confidence

                mlflow.log_metrics(log_metrics)

                # Tags (searchable metadata)
                tags = {
                    "call_type": metrics.method,
                    "model_version": metrics.model or "unknown",
                }
                if metrics.rank:
                    tags["rank"] = metrics.rank
                if metrics.decision:
                    tags["decision"] = metrics.decision
                if metrics.error:
                    tags["error"] = metrics.error[:250]
                if metrics.ml_prediction_used:
                    tags["ml_prediction_used"] = "true"

                mlflow.set_tags(tags)

        except Exception as e:
            # NEVER let tracking failures break inference
            logger.debug(f"MLflow logging failed (inference unaffected): {e}")

    def get_summary(self) -> Dict[str, Any]:
        """Get cumulative tracking summary."""
        avg_latency = (
            self.total_latency_ms / self.total_calls
            if self.total_calls > 0 else 0.0
        )
        return {
            "tracking_enabled": self.enabled,
            "mlflow_available": MLFLOW_AVAILABLE,
            "experiment": self.experiment_name,
            "total_calls": self.total_calls,
            "total_errors": self.total_errors,
            "error_rate": self.total_errors / max(self.total_calls, 1),
            "avg_latency_ms": round(avg_latency, 1),
            "calls_by_model_method": dict(self._call_counts),
        }
