#!/usr/bin/env python3
"""BERU MLOps Pipeline — end-to-end orchestrator.

Demonstrates the full ML lifecycle for the BERU GRC analyst model:

  Step 1  DATA VALIDATION    — corpus quality gates (test_data_quality.py)
  Step 2  TRAINING           — LoRA fine-tune via Unsloth (or dry-run)
  Step 3  EVALUATION         — knowledge-brain + pentest-brain benchmarks
  Step 4  PROMOTION GATE     — automated pass/fail vs champion baseline
  Step 5  MODEL REGISTRY     — MLflow champion/challenger transition

Every step is logged to MLflow under the "beru-training" experiment.
This is the artifact that proves MLOps discipline, not just ML code.

Usage:
    # Full pipeline (training requires GPU + Unsloth)
    python3 beru_pipeline.py --exp-id exp-013 --corpus-path path/to/corpus.jsonl

    # Skip training, evaluate an already-merged model
    python3 beru_pipeline.py --exp-id exp-013 --skip-training \\
        --merged-model-path 3-model-registry/beru-v1.6-3b/merged_16bit

    # Show what would happen without touching MLflow or weights
    python3 beru_pipeline.py --exp-id exp-013 --dry-run

    # Backfill historical experiments into MLflow and exit
    python3 beru_pipeline.py --backfill

    # Launch MLflow UI to inspect results
    python3 beru_pipeline.py --ui

Control traceability:
    GOVERN-1.7   — Promotion gate enforces C-rank authority ceiling
    MANAGE-2.4   — Model version lineage tracked in registry
    MEASURE-2.6  — Eval metrics logged per run
    AU-12        — Full params + artifacts attached to every run
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# ── repo paths ───────────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parent  # GP-MODEL-OPS/
_BERU_AI_ROOT = _REPO_ROOT / "BERU-AI"
sys.path.insert(0, str(_BERU_AI_ROOT))
sys.path.insert(0, str(_REPO_ROOT))

PIPELINE_DIR = _REPO_ROOT / "1-FineTuning-Pipeline"
EVAL_DIR = _REPO_ROOT / "4-eval-clarify"
EXPERIMENTS_DIR = _REPO_ROOT / "5-experiments"
REGISTRY_DIR = _REPO_ROOT / "3-model-registry"
TESTS_DIR = _REPO_ROOT / "8-tests"

KNOWLEDGE_BRAIN_EVAL = EVAL_DIR / "beru_knowledge_brain_v2.jsonl"
PENTEST_BRAIN_EVAL = EVAL_DIR / "beru_pentest_brain_v1.jsonl"


# ── helpers ──────────────────────────────────────────────────────────────────

def _hdr(title: str) -> None:
    width = 65
    print()
    print("─" * width)
    print(f"  {title}")
    print("─" * width)


def _ok(msg: str) -> None:
    print(f"  ✓  {msg}")


def _fail(msg: str) -> None:
    print(f"  ✗  {msg}")


def _info(msg: str) -> None:
    print(f"     {msg}")


def _warn(msg: str) -> None:
    print(f"  ⚠  {msg}")


def _run_inline_quality_gates(corpus: Path) -> bool:
    """BERU-specific data quality gates (mirrors 8-tests/test_data_quality.py logic)."""
    import json as _json

    gates_passed = []
    gates_failed = []

    examples = []
    parse_errors = 0
    for line in corpus.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            examples.append(_json.loads(line))
        except _json.JSONDecodeError:
            parse_errors += 1

    _info(f"Examples loaded: {len(examples)}  parse errors: {parse_errors}")

    # gate: minimum corpus size
    if len(examples) >= 500:
        gates_passed.append(f"corpus size {len(examples)} ≥ 500")
    else:
        gates_failed.append(f"corpus size {len(examples)} < 500 (min)")

    # gate: ChatML format — must have 'messages' (OpenAI) or 'conversations' key
    chatml = sum(1 for e in examples if "messages" in e or "conversations" in e)
    if chatml == len(examples):
        gates_passed.append(f"ChatML format 100% ({chatml}/{len(examples)})")
    else:
        gates_failed.append(f"ChatML format {chatml}/{len(examples)} — rest lack messages/conversations key")

    # gate: no exact duplicates
    seen: set = set()
    dupes = 0
    for e in examples:
        key = str(e)
        if key in seen:
            dupes += 1
        seen.add(key)
    if dupes == 0:
        gates_passed.append("no exact duplicates")
    else:
        gates_failed.append(f"{dupes} exact duplicates found")

    # gate: no garbage/stub responses (< 50 chars in assistant turn)
    stubs = 0
    for e in examples:
        turns = e.get("messages") or e.get("conversations") or []
        for turn in turns:
            role = turn.get("role") or turn.get("from") or ""
            content = str(turn.get("content") or turn.get("value") or "")
            if role in ("assistant", "gpt") and len(content) < 50:
                stubs += 1
    if stubs == 0:
        gates_passed.append("no stub responses (< 50 chars)")
    else:
        gates_failed.append(f"{stubs} stub responses (assistant turn < 50 chars)")

    for g in gates_passed:
        _ok(g)
    for g in gates_failed:
        _fail(g)

    if gates_failed:
        _warn("Fix data quality issues before training.")
        return False
    return True


# ── step 1: data validation ──────────────────────────────────────────────────

def step_data_validation(corpus_path: str, dry_run: bool = False) -> bool:
    _hdr("STEP 1 / 5 — DATA VALIDATION")

    corpus = Path(corpus_path)
    if not corpus.exists():
        _fail(f"Corpus not found: {corpus_path}")
        return False

    _info(f"Corpus: {corpus_path}")

    if dry_run:
        lines = [l for l in corpus.read_text(errors="replace").splitlines() if l.strip()]
        _info(f"Examples: {len(lines)}")
        _ok("Dry run — skipping quality gates")
        return True

    return _run_inline_quality_gates(corpus)


# ── step 2: training ─────────────────────────────────────────────────────────

def step_training(
    exp_id: str,
    corpus_path: str,
    merged_model_path: Optional[str],
    dry_run: bool = False,
    skip_training: bool = False,
) -> Optional[str]:
    _hdr("STEP 2 / 5 — TRAINING")

    if skip_training:
        _info("--skip-training set — using pre-merged model")
        if merged_model_path:
            _ok(f"Merged model: {merged_model_path}")
            return merged_model_path
        # look for latest in registry
        latest = sorted(REGISTRY_DIR.glob("beru-*/merged_16bit"), reverse=True)
        if latest:
            _ok(f"Auto-detected merged model: {latest[0]}")
            return str(latest[0])
        _fail("No merged model path provided and none found in registry.")
        return None

    config_file = PIPELINE_DIR / "config_beru.yaml"
    train_script = PIPELINE_DIR / "train_v11.py"

    _info(f"Config: {config_file}")
    _info(f"Script: {train_script}")
    _info(f"Corpus: {corpus_path}")
    _info(f"Exp ID: {exp_id}")

    if dry_run:
        _ok("Dry run — skipping GPU training (takes ~16 min on RTX 5080)")
        _info("Would run: python3 train_v11.py --config config_beru.yaml \\")
        _info(f"           --corpus {corpus_path} --exp-id {exp_id}")
        return None

    if not train_script.exists():
        _fail(f"Training script not found: {train_script}")
        return None

    t0 = time.time()
    result = subprocess.run(
        [sys.executable, str(train_script),
         "--corpus-path", corpus_path,
         "--exp-id", exp_id],
        cwd=str(PIPELINE_DIR),
    )
    elapsed = time.time() - t0

    if result.returncode != 0:
        _fail(f"Training failed after {elapsed/60:.1f} min")
        return None

    _ok(f"Training complete — {elapsed/60:.1f} min")

    # locate the merged model written by train_v11.py
    merged = REGISTRY_DIR / f"{exp_id}" / "merged_16bit"
    if merged.exists():
        _ok(f"Merged model: {merged}")
        return str(merged)

    _warn("Merged model path not found at expected location — check 3-model-registry/")
    return None


# ── step 3: evaluation ───────────────────────────────────────────────────────

def step_evaluation(
    merged_model_path: Optional[str],
    exp_id: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    _hdr("STEP 3 / 5 — EVALUATION")

    # Try to load results from the experiment directory first
    exp_dir = EXPERIMENTS_DIR / exp_id
    metrics_file = exp_dir / "metrics.json"

    if metrics_file.exists():
        _info(f"Loading existing eval results from {metrics_file}")
        with metrics_file.open() as f:
            m = json.load(f)
        kb = m.get("fine_tuned", {}).get("knowledge_brain", {})
        pb = m.get("fine_tuned", {}).get("pentest_brain", {})
        _ok(f"Knowledge brain: {kb.get('overall', 0):.1%}  ({kb.get('passed', '?')}/{kb.get('total', '?')})")
        _ok(f"Pentest brain:   {pb.get('overall', 0):.1%}  ({pb.get('passed', '?')}/{pb.get('total', '?')})")
        return m

    if dry_run or not merged_model_path:
        _info("Dry run / no model path — returning placeholder eval results")
        _info(f"Would eval against: {KNOWLEDGE_BRAIN_EVAL.name} ({_count_lines(KNOWLEDGE_BRAIN_EVAL)} Q)")
        _info(f"                    {PENTEST_BRAIN_EVAL.name} ({_count_lines(PENTEST_BRAIN_EVAL)} Q)")
        return _placeholder_metrics(exp_id)

    eval_script = PIPELINE_DIR / "eval_bridge.py"
    if not eval_script.exists():
        _warn("eval_bridge.py not found — returning placeholder metrics")
        return _placeholder_metrics(exp_id)

    _info(f"Model: {merged_model_path}")
    _info(f"Running knowledge-brain eval ({_count_lines(KNOWLEDGE_BRAIN_EVAL)} questions)...")
    result = subprocess.run(
        [sys.executable, str(eval_script), "--model-path", merged_model_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        _fail("Eval failed — check eval_bridge.py output")
        _info(result.stderr[-500:])
        return {}

    # eval_bridge writes results to 4-eval-clarify/3-results/
    results_dir = EVAL_DIR / "3-results"
    latest = sorted(results_dir.glob("bridge_*.json"), reverse=True)
    if latest:
        with latest[0].open() as f:
            return json.load(f)

    return {}


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for l in path.read_text().splitlines() if l.strip())


def _placeholder_metrics(exp_id: str) -> Dict[str, Any]:
    return {
        "experiment_id": exp_id,
        "fine_tuned": {
            "knowledge_brain": {"overall": 0.0, "passed": 0, "total": 30, "per_type": {}},
            "pentest_brain": {"overall": 0.0, "passed": 0, "total": 22, "per_owasp_llm": {}},
        },
    }


# ── step 4: promotion gate ───────────────────────────────────────────────────

def step_promotion_gate(
    eval_results: Dict[str, Any],
) -> Dict[str, Any]:
    _hdr("STEP 4 / 5 — PROMOTION GATE")

    from mlops.training_tracker import evaluate_promotion_gate, get_champion

    ft = eval_results.get("fine_tuned", {})
    kb = ft.get("knowledge_brain", {})
    pb = ft.get("pentest_brain", {})

    champion = get_champion()
    if champion:
        _info(f"Champion: {champion['model_name']} v{champion['version']}  "
              f"kb={champion['knowledge_brain_overall']:.1%}  "
              f"pb={champion['pentest_brain_overall']:.1%}")
    else:
        _info("No champion in registry yet.")

    gate = evaluate_promotion_gate(kb, pb, champion)

    for g in gate["gates_passed"]:
        _ok(g)
    for g in gate["gates_failed"]:
        _fail(g)

    print()
    decision = gate["decision"]
    if decision == "PROMOTED":
        print(f"  ══  DECISION: PROMOTED  ══")
    else:
        print(f"  ══  DECISION: BLOCKED — {gate['reason']}  ══")

    return gate


# ── step 5: model registry ───────────────────────────────────────────────────

def step_model_registry(
    gate: Dict[str, Any],
    exp_id: str,
    eval_results: Dict[str, Any],
    merged_model_path: Optional[str],
    dry_run: bool = False,
) -> None:
    _hdr("STEP 5 / 5 — MODEL REGISTRY")

    from mlops.training_tracker import (
        log_training_run, register_model_version, corpus_fingerprint,
        REGISTRY_MODEL_NAME, _DEFAULT_TRACKING_URI,
    )

    decision = gate.get("decision", "BLOCKED")
    stage = "Production" if decision == "PROMOTED" else "Staging"

    ft = eval_results.get("fine_tuned", {})
    kb = ft.get("knowledge_brain", {})
    pb = ft.get("pentest_brain", {})

    params = {
        "experiment_id": exp_id,
        "model": eval_results.get("model", exp_id),
        "base_model": eval_results.get("base_model", "unsloth/Llama-3.2-3B-Instruct"),
        "training_corpus_size": eval_results.get("training_corpus_size", "unknown"),
        "lora_r": eval_results.get("lora_config", {}).get("r", "32"),
        "lora_alpha": eval_results.get("lora_config", {}).get("alpha", "64"),
        "learning_rate": eval_results.get("training_config", {}).get("learning_rate", "2e-5"),
        "epochs_per_chunk": eval_results.get("training_config", {}).get("epochs_per_chunk", "2"),
    }
    metrics = {
        "knowledge_brain_overall": kb.get("overall", 0.0),
        "pentest_brain_overall": pb.get("overall", 0.0),
        "training_duration_minutes": eval_results.get("training_duration_minutes", 0.0),
        "final_train_loss": eval_results.get("final_train_loss", 0.0),
        "gates_passed": float(len(gate.get("gates_passed", []))),
        "gates_failed": float(len(gate.get("gates_failed", []))),
    }
    for typ, score in (kb.get("per_type") or {}).items():
        metrics[f"kb_{typ}"] = float(score)

    exp_metrics_path = str(EXPERIMENTS_DIR / exp_id / "metrics.json")
    artifacts = {"experiment": exp_metrics_path} if Path(exp_metrics_path).exists() else {}

    _info(f"Logging run to MLflow experiment 'beru-training'...")
    if dry_run:
        _info(f"Dry run — would log: {len(params)} params, {len(metrics)} metrics")
        _info(f"Would register {REGISTRY_MODEL_NAME} → {stage}")
        _ok("Dry run complete — no MLflow writes performed")
        return

    run_id = log_training_run(
        exp_id=exp_id,
        params=params,
        metrics=metrics,
        artifacts=artifacts,
        promotion_decision=decision,
        run_date=eval_results.get("run_date_utc", ""),
    )
    _ok(f"MLflow run logged: {run_id}")

    if run_id:
        ver = register_model_version(
            run_id=run_id,
            model_name=REGISTRY_MODEL_NAME,
            transition_to=stage,
        )
        if ver:
            _ok(f"Registered {REGISTRY_MODEL_NAME} v{ver} → {stage}")

    if decision == "PROMOTED":
        print()
        print(f"  ══  {exp_id} is now the PRODUCTION champion  ══")
        _info("Serving: ollama create beru:latest -f BERU-AI/Modelfile_beru_v16")
        _info("Monitor: mlflow ui --backend-store-uri file://BERU-AI/mlruns --port 5001")
    else:
        print()
        _info(f"Model registered as Staging (challenger). Champion unchanged.")
        _info("Fix the failing gates and re-run to attempt promotion.")


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="BERU MLOps Pipeline — train → eval → promote → registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--exp-id", default="exp-013-beru-v1.7",
                    help="Experiment identifier (e.g. exp-013-beru-v1.7)")
    ap.add_argument("--corpus-path",
                    default="1-FineTuning-Pipeline/01-raw-data-lake/beru_training_exp012.jsonl",
                    help="Path to training corpus JSONL")
    ap.add_argument("--merged-model-path", default=None,
                    help="Path to already-merged HuggingFace model (skips training)")
    ap.add_argument("--skip-training", action="store_true",
                    help="Skip Step 2 (training); use --merged-model-path or auto-detect")
    ap.add_argument("--skip-eval", action="store_true",
                    help="Skip Step 3 (eval); load from 5-experiments/<exp-id>/metrics.json")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would happen without writing to MLflow or GPU")
    ap.add_argument("--backfill", action="store_true",
                    help="Backfill historical BERU experiments into MLflow and exit")
    ap.add_argument("--ui", action="store_true",
                    help="Launch MLflow UI and exit")
    args = ap.parse_args()

    # ── special modes ────────────────────────────────────────────────────────

    if args.ui:
        from mlops.training_tracker import _DEFAULT_TRACKING_URI
        subprocess.run([
            "mlflow", "ui",
            "--backend-store-uri", _DEFAULT_TRACKING_URI,
            "--port", "5001",
        ])
        return

    if args.backfill:
        from mlops.backfill_experiments import backfill
        backfill(dry_run=args.dry_run)
        return

    # ── banner ────────────────────────────────────────────────────────────────

    print()
    print("═" * 65)
    print("  BERU MLOps Pipeline")
    print(f"  Experiment: {args.exp_id}")
    print(f"  Corpus:     {args.corpus_path}")
    if args.dry_run:
        print("  Mode:       DRY RUN (no GPU, no MLflow writes)")
    print("═" * 65)

    # ── step 1: data validation ───────────────────────────────────────────────

    corpus_ok = step_data_validation(
        corpus_path=args.corpus_path,
        dry_run=args.dry_run,
    )
    if not corpus_ok and not args.dry_run:
        sys.exit("Corpus failed quality gate. Fix data before training.")

    # ── step 2: training ──────────────────────────────────────────────────────

    merged_path = step_training(
        exp_id=args.exp_id,
        corpus_path=args.corpus_path,
        merged_model_path=args.merged_model_path,
        dry_run=args.dry_run,
        skip_training=args.skip_training,
    )

    # ── step 3: evaluation ────────────────────────────────────────────────────

    if args.skip_eval:
        _hdr("STEP 3 / 5 — EVALUATION")
        _info(f"--skip-eval set — loading from 5-experiments/{args.exp_id}/metrics.json")
        mf = EXPERIMENTS_DIR / args.exp_id / "metrics.json"
        eval_results = json.loads(mf.read_text()) if mf.exists() else _placeholder_metrics(args.exp_id)
    else:
        eval_results = step_evaluation(
            merged_model_path=merged_path,
            exp_id=args.exp_id,
            dry_run=args.dry_run,
        )

    if not eval_results:
        sys.exit("Evaluation produced no results — cannot run promotion gate.")

    # ── step 4: promotion gate ────────────────────────────────────────────────

    gate = step_promotion_gate(eval_results)

    # ── step 5: model registry ────────────────────────────────────────────────

    step_model_registry(
        gate=gate,
        exp_id=args.exp_id,
        eval_results=eval_results,
        merged_model_path=merged_path,
        dry_run=args.dry_run,
    )

    # ── summary ───────────────────────────────────────────────────────────────

    _hdr("PIPELINE COMPLETE")
    ft = eval_results.get("fine_tuned", {})
    kb_score = ft.get("knowledge_brain", {}).get("overall", 0.0)
    pb_score = ft.get("pentest_brain", {}).get("overall", 0.0)
    decision = gate.get("decision", "BLOCKED")

    print(f"  Experiment:      {args.exp_id}")
    print(f"  Knowledge brain: {kb_score:.1%}")
    print(f"  Pentest brain:   {pb_score:.1%}")
    print(f"  Decision:        {decision}")
    print()
    if not args.dry_run:
        from mlops.training_tracker import _DEFAULT_TRACKING_URI
        print(f"  MLflow UI:  mlflow ui --backend-store-uri {_DEFAULT_TRACKING_URI} --port 5001")
    print()


if __name__ == "__main__":
    main()
