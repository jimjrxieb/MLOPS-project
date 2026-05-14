"""Training Tracker — MLflow-backed experiment tracking and model registry for BERU.

Covers the training half of the MLOps loop (the inference half is inference_tracker.py):

  data validate → train → eval → promote decision → model registry

Control traceability:
  MEASURE-2.6   — Evaluation metrics tracked per run
  MANAGE-2.4    — Model version lineage via registry
  GOVERN-1.7    — Champion/challenger gate enforces authority boundaries
  AU-12         — Every run logged with full params + artifacts
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("beru.mlops.training")

try:
    import mlflow
    from mlflow.tracking import MlflowClient
    MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None
    MlflowClient = None
    MLFLOW_AVAILABLE = False

# ── constants ────────────────────────────────────────────────────────────────

TRAINING_EXPERIMENT = "beru-training"
REGISTRY_MODEL_NAME = "beru-grc-analyst"

_MLRUNS_ROOT = Path(__file__).resolve().parent.parent / "mlruns"
_DEFAULT_TRACKING_URI = f"file://{_MLRUNS_ROOT}"

# Promotion gate thresholds (MANAGE-2.4 / beru-design-decisions.md D-010)
GATE = {
    "knowledge_brain_overall_min": 0.70,
    "knowledge_brain_per_type_min": 0.60,
    "pentest_brain_overall_min": 0.70,
    "zero_hallucinated_ids": True,
}


# ── public API ───────────────────────────────────────────────────────────────

def log_training_run(
    exp_id: str,
    params: Dict[str, Any],
    metrics: Dict[str, Any],
    artifacts: Optional[Dict[str, str]] = None,
    promotion_decision: str = "BLOCKED",
    run_date: str = "",
    tracking_uri: str = _DEFAULT_TRACKING_URI,
) -> str:
    """Log a completed training run to MLflow.

    Returns the MLflow run_id (or empty string if MLflow unavailable).

    params  — hyperparameters (lora_r, lr, corpus_size, etc.)
    metrics — flat numeric metrics (knowledge_brain_overall, etc.)
    artifacts — {label: local_path} files to attach to the run
    """
    if not MLFLOW_AVAILABLE:
        logger.warning("MLflow not available — training run not logged.")
        return ""

    client = MlflowClient(tracking_uri=tracking_uri)
    mlflow.set_tracking_uri(tracking_uri)
    exp = mlflow.set_experiment(TRAINING_EXPERIMENT)

    with mlflow.start_run(run_name=exp_id, experiment_id=exp.experiment_id) as run:
        # params
        safe_params = {k: str(v) for k, v in params.items()}
        mlflow.log_params(safe_params)

        # metrics (must be numeric)
        safe_metrics = {}
        for k, v in metrics.items():
            try:
                safe_metrics[k] = float(v)
            except (TypeError, ValueError):
                pass
        mlflow.log_metrics(safe_metrics)

        # tags
        mlflow.set_tags({
            "promotion_decision": promotion_decision,
            "run_date": run_date or "",
            "model_name": params.get("model", "unknown"),
            "base_model": params.get("base_model", "unknown"),
        })

        # artifacts
        for label, path in (artifacts or {}).items():
            p = Path(path)
            if p.exists():
                mlflow.log_artifact(str(p), artifact_path=label)

        run_id = run.info.run_id
        logger.info(f"Logged training run {exp_id} → run_id={run_id}")
        return run_id


def register_model_version(
    run_id: str,
    model_name: str = REGISTRY_MODEL_NAME,
    transition_to: str = "Staging",
    tracking_uri: str = _DEFAULT_TRACKING_URI,
) -> Optional[int]:
    """Register a trained model version in the MLflow Model Registry.

    transition_to: "Staging" (blocked) | "Production" (promoted)
    Returns the new version number.
    """
    if not MLFLOW_AVAILABLE or not run_id:
        return None

    client = MlflowClient(tracking_uri=tracking_uri)
    mlflow.set_tracking_uri(tracking_uri)

    # ensure the registered model exists
    try:
        client.create_registered_model(
            model_name,
            description="BERU GRC Analyst — NIST 800-53 + AI RMF dual-citation findings",
        )
    except Exception:
        pass  # already exists

    # create the version (artifact URI points to the run)
    run_uri = f"runs:/{run_id}/model"
    try:
        mv = client.create_model_version(
            name=model_name,
            source=run_uri,
            run_id=run_id,
        )
    except Exception:
        # source artifact doesn't exist (no model logged) — register metadata-only
        mv = client.create_model_version(
            name=model_name,
            source=f"runs:/{run_id}",
            run_id=run_id,
        )

    client.transition_model_version_stage(
        name=model_name,
        version=mv.version,
        stage=transition_to,
        archive_existing_versions=(transition_to == "Production"),
    )
    logger.info(
        f"Registered {model_name} v{mv.version} → {transition_to} (run={run_id})"
    )
    return int(mv.version)


def get_champion(
    model_name: str = REGISTRY_MODEL_NAME,
    tracking_uri: str = _DEFAULT_TRACKING_URI,
) -> Optional[Dict[str, Any]]:
    """Return metadata for the current Production champion, or None."""
    if not MLFLOW_AVAILABLE:
        return None
    client = MlflowClient(tracking_uri=tracking_uri)
    try:
        versions = client.get_latest_versions(model_name, stages=["Production"])
        if not versions:
            return None
        mv = versions[0]
        run = client.get_run(mv.run_id)
        return {
            "version": mv.version,
            "run_id": mv.run_id,
            "model_name": run.data.tags.get("model_name", "unknown"),
            "knowledge_brain_overall": run.data.metrics.get("knowledge_brain_overall", 0.0),
            "pentest_brain_overall": run.data.metrics.get("pentest_brain_overall", 0.0),
            "run_date": run.data.tags.get("run_date", "unknown"),
        }
    except Exception as e:
        logger.debug(f"get_champion failed: {e}")
        return None


def evaluate_promotion_gate(
    knowledge_brain: Dict[str, Any],
    pentest_brain: Dict[str, Any],
    champion: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply promotion gate rules and return a structured decision dict.

    Returns:
        {
          "decision": "PROMOTED" | "BLOCKED",
          "gates_passed": [...],
          "gates_failed": [...],
          "reason": "human-readable summary",
        }
    """
    passed = []
    failed = []

    kb_overall = knowledge_brain.get("overall", 0.0)
    pb_overall = pentest_brain.get("overall", 0.0)
    per_type = knowledge_brain.get("per_type", {})

    # gate 1: knowledge brain overall
    if kb_overall >= GATE["knowledge_brain_overall_min"]:
        passed.append(f"knowledge_brain_overall ≥ {GATE['knowledge_brain_overall_min']:.0%}")
    else:
        failed.append(
            f"knowledge_brain_overall {kb_overall:.1%} < {GATE['knowledge_brain_overall_min']:.0%}"
        )

    # gate 2: knowledge brain per-type minimum
    per_type_min = GATE["knowledge_brain_per_type_min"]
    type_fails = [k for k, v in per_type.items() if v < per_type_min]
    if not type_fails:
        passed.append(f"all knowledge types ≥ {per_type_min:.0%}")
    else:
        failed.append(f"knowledge per-type below {per_type_min:.0%}: {type_fails}")

    # gate 3: pentest brain overall
    if pb_overall >= GATE["pentest_brain_overall_min"]:
        passed.append(f"pentest_brain_overall ≥ {GATE['pentest_brain_overall_min']:.0%}")
    else:
        failed.append(
            f"pentest_brain_overall {pb_overall:.1%} < {GATE['pentest_brain_overall_min']:.0%}"
        )

    # gate 4: beats champion (if one exists)
    if champion:
        champ_kb = champion.get("knowledge_brain_overall", 0.0)
        if kb_overall > champ_kb:
            passed.append(f"beats champion knowledge_brain ({champ_kb:.1%})")
        else:
            failed.append(f"does not beat champion knowledge_brain ({champ_kb:.1%})")

    decision = "PROMOTED" if not failed else "BLOCKED"
    reason = (
        f"All {len(passed)} gates passed."
        if decision == "PROMOTED"
        else f"{len(failed)} gate(s) failed: {'; '.join(failed[:2])}"
    )

    return {
        "decision": decision,
        "gates_passed": passed,
        "gates_failed": failed,
        "reason": reason,
        "knowledge_brain_overall": kb_overall,
        "pentest_brain_overall": pb_overall,
    }


def corpus_fingerprint(corpus_path: str) -> str:
    """SHA-256 of the first 1 MB of a corpus file (fast, collision-resistant enough)."""
    p = Path(corpus_path)
    if not p.exists():
        return "unknown"
    h = hashlib.sha256()
    with p.open("rb") as f:
        h.update(f.read(1_048_576))
    return h.hexdigest()[:16]
