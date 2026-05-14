#!/usr/bin/env python3
"""Backfill historical BERU experiments into MLflow.

Reads every 5-experiments/exp-0*/metrics.json and logs each as an MLflow
training run.  Run once to populate the MLflow UI with the full experiment
history before any future runs are tracked live.

Usage:
    python3 -m BERU-AI.mlops.backfill_experiments
    python3 BERU-AI/mlops/backfill_experiments.py
    python3 BERU-AI/mlops/backfill_experiments.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]  # GP-MODEL-OPS/
_BERU_AI_ROOT = Path(__file__).resolve().parents[1]  # BERU-AI/
sys.path.insert(0, str(_BERU_AI_ROOT))

from mlops.training_tracker import (  # noqa: E402
    log_training_run,
    register_model_version,
    REGISTRY_MODEL_NAME,
    _DEFAULT_TRACKING_URI,
)

EXPERIMENTS_DIR = _REPO_ROOT / "5-experiments"

# BERU-specific experiments (skip JADE/Katie)
BERU_PREFIXES = {
    "exp-004-beru-v1-cysa",
    "exp-005-beru-3b-baseline",
    "exp-006-beru-v1.0",
    "exp-007-beru-v1.1",
    "exp-008-beru-v1.2",
    "exp-009-beru-v1.3",
    "exp-010-beru-v1.4",
    "exp-011-beru-v1.5",
    "exp-012-beru-v1.6",
}

# exp-007 is the best knowledge-brain to date (16.7%) — treat it as the de-facto
# champion even though it never cleared the 70% gate (no run has).
BEST_KNOWLEDGE_BRAIN_EXP = "exp-007-beru-v1.1"


def _flatten_metrics(m: dict) -> dict:
    """Extract flat numeric metrics from a metrics.json dict."""
    out: dict = {}

    # top-level numerics
    for key in ("training_corpus_size", "validation_corpus_size",
                "training_duration_minutes", "final_train_loss",
                "adversarial_ratio_actual"):
        if key in m and m[key] is not None:
            try:
                out[key] = float(m[key])
            except (TypeError, ValueError):
                pass

    # nested eval scores
    fine_tuned = m.get("fine_tuned", {})

    kb = fine_tuned.get("knowledge_brain", {})
    out["knowledge_brain_overall"] = float(kb.get("overall", 0.0))
    out["knowledge_brain_passed"] = float(kb.get("passed", 0.0))
    out["knowledge_brain_total"] = float(kb.get("total", 0.0))
    for typ, score in (kb.get("per_type") or {}).items():
        out[f"kb_{typ}"] = float(score)

    pb = fine_tuned.get("pentest_brain", {})
    out["pentest_brain_overall"] = float(pb.get("overall", 0.0))
    out["pentest_brain_passed"] = float(pb.get("passed", 0.0))
    out["pentest_brain_total"] = float(pb.get("total", 0.0))
    for owasp, score in (pb.get("per_owasp_llm") or {}).items():
        out[f"pb_{owasp}"] = float(score)

    # workflow eval (if present)
    we = m.get("workflow_eval") or {}
    if we.get("overall_score") is not None:
        out["workflow_eval_overall"] = float(we["overall_score"])

    # baseline deltas (lift metrics)
    for k, v in (m.get("lift_over_baseline") or {}).items():
        try:
            out[f"lift_baseline_{k}"] = float(v)
        except (TypeError, ValueError):
            pass

    return out


def _flatten_params(m: dict) -> dict:
    """Extract hyperparameters from a metrics.json dict."""
    out: dict = {}

    for key in ("experiment_id", "model", "base_model",
                "training_corpus_size", "validation_corpus_size",
                "corpus_recipe", "adversarial_ratio_actual"):
        if key in m:
            out[key] = str(m[key])

    lora = m.get("lora_config", {})
    for key in ("r", "alpha", "dropout"):
        if key in lora:
            out[f"lora_{key}"] = str(lora[key])

    tr = m.get("training_config", {})
    for key in ("epochs_per_chunk", "batch_size", "gradient_accumulation_steps",
                "learning_rate", "lr_scheduler", "warmup_ratio", "weight_decay"):
        if key in tr:
            out[key] = str(tr[key])

    return out


def backfill(dry_run: bool = False, tracking_uri: str = _DEFAULT_TRACKING_URI) -> None:
    dirs = sorted(
        d for d in EXPERIMENTS_DIR.iterdir()
        if d.is_dir() and d.name in BERU_PREFIXES
    )

    if not dirs:
        print(f"No BERU experiment directories found under {EXPERIMENTS_DIR}")
        return

    print(f"Backfilling {len(dirs)} BERU experiments → MLflow ({tracking_uri})")
    print()

    registered_champion = False

    for exp_dir in dirs:
        metrics_file = exp_dir / "metrics.json"
        if not metrics_file.exists():
            print(f"  SKIP  {exp_dir.name}  (no metrics.json)")
            continue

        with metrics_file.open() as f:
            m = json.load(f)

        exp_id = exp_dir.name
        decision = m.get("promotion_gate", {}).get("decision", "BASELINE")
        run_date = m.get("run_date_utc", "")
        params = _flatten_params(m)
        metrics = _flatten_metrics(m)

        kb = metrics.get("knowledge_brain_overall", 0.0)
        pb = metrics.get("pentest_brain_overall", 0.0)
        print(
            f"  {exp_id:<35}  kb={kb:.1%}  pb={pb:.1%}  → {decision}"
        )

        if dry_run:
            continue

        artifacts = {}
        if metrics_file.exists():
            artifacts["experiment"] = str(metrics_file)
        params_file = exp_dir / "params.yaml"
        if params_file.exists():
            artifacts["experiment"] = str(metrics_file)
            artifacts["params"] = str(params_file)

        run_id = log_training_run(
            exp_id=exp_id,
            params=params,
            metrics=metrics,
            artifacts=artifacts,
            promotion_decision=decision,
            run_date=run_date,
            tracking_uri=tracking_uri,
        )

        # Register the best-knowledge-brain run as de-facto champion (Staging)
        # since no run has cleared the 70% gate yet.
        if run_id and exp_dir.name == BEST_KNOWLEDGE_BRAIN_EXP and not registered_champion:
            ver = register_model_version(
                run_id=run_id,
                model_name=REGISTRY_MODEL_NAME,
                transition_to="Staging",
                tracking_uri=tracking_uri,
            )
            print(f"    ↳ registered as {REGISTRY_MODEL_NAME} v{ver} → Staging (best-to-date)")
            registered_champion = True

    print()
    if dry_run:
        print("Dry run — nothing written to MLflow.")
    else:
        print("Backfill complete.")
        print(f"Open MLflow UI:  mlflow ui --backend-store-uri {tracking_uri} --port 5001")


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill BERU experiments into MLflow.")
    ap.add_argument("--dry-run", action="store_true", help="Preview without writing.")
    ap.add_argument("--tracking-uri", default=_DEFAULT_TRACKING_URI)
    args = ap.parse_args()
    backfill(dry_run=args.dry_run, tracking_uri=args.tracking_uri)


if __name__ == "__main__":
    main()
