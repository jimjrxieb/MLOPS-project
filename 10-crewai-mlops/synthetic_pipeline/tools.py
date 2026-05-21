"""
CrewAI tools wrapping the synthetic data pipeline.

Each tool is a thin adapter over existing pipeline code — no logic lives here.
The pipeline modules (pipeline.py, generator.py, quality_validator.py) are unchanged.
"""

import json
import sys
from pathlib import Path
from typing import Optional

from crewai.tools import tool

# The synthetic-pipeline dir uses relative imports internally, so we register
# it as a package under an importable alias before importing its modules.
import importlib.util as _ilu

# After move to crewai-mlops/synthetic_pipeline/, parent.parent is crewai-mlops/.
# The actual pipeline code lives at ../../0-data-lab/synthetic-pipeline/.
_PIPELINE_DIR = Path(__file__).parent.parent.parent / "0-data-lab" / "synthetic-pipeline"
_PARENT_DIR = _PIPELINE_DIR.parent             # …/0-data-lab/

if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

# Register the old pipeline code under a private alias to avoid colliding with
# crewai-mlops/synthetic_pipeline (this crew's own package name).
_PKG_NAME = "_gp_synthetic_pipeline"
if _PKG_NAME not in sys.modules:
    _spec = _ilu.spec_from_file_location(
        _PKG_NAME,
        _PIPELINE_DIR / "__init__.py",
        submodule_search_locations=[str(_PIPELINE_DIR)],
    )
    _pkg = _ilu.module_from_spec(_spec)
    sys.modules[_PKG_NAME] = _pkg
    _spec.loader.exec_module(_pkg)

# Also register submodules under the private alias so relative imports inside
# the pipeline code resolve correctly.
import importlib as _importlib
for _sub in ("models", "generator", "pipeline", "quality_validator"):
    _sub_key = f"{_PKG_NAME}.{_sub}"
    if _sub_key not in sys.modules:
        _sub_spec = _ilu.spec_from_file_location(
            _sub_key,
            _PIPELINE_DIR / f"{_sub}.py",
        )
        _sub_mod = _ilu.module_from_spec(_sub_spec)
        sys.modules[_sub_key] = _sub_mod
        _sub_spec.loader.exec_module(_sub_mod)

from _gp_synthetic_pipeline.models import GenerationConfig  # noqa: E402
from _gp_synthetic_pipeline.generator import TrainingGenerator  # noqa: E402
from _gp_synthetic_pipeline.pipeline import TrainingPipeline  # noqa: E402
from _gp_synthetic_pipeline.quality_validator import validate_training_file, QualityValidator  # noqa: E402


@tool("discover_sources")
def discover_sources(instance_filter: str = "") -> str:
    """
    Discover all GP-PROJECTS instances and slots that have operational data
    (JSA inbox findings or workflow state) available for training generation.
    Returns a JSON summary of sources found with finding counts per slot.
    """
    pipeline = TrainingPipeline()
    sources = pipeline._discover_sources(
        instance_filter=instance_filter if instance_filter else None
    )
    return json.dumps({
        "sources_found": len(sources),
        "sources": sources
    }, indent=2)


@tool("run_full_pipeline")
def run_full_pipeline(min_quality_score: float = 50.0, max_examples: int = 1000) -> str:
    """
    Run the complete training data generation pipeline across all discovered sources.
    Phases: discover → generate → merge → validate → save.
    Returns JSON with total examples, output file path, and quality stats.
    """
    config = GenerationConfig(
        min_quality_score=min_quality_score,
        max_examples_per_batch=max_examples
    )
    pipeline = TrainingPipeline(config=config)
    result = pipeline.run_full_pipeline()
    return json.dumps(result, indent=2, default=str)


@tool("run_pipeline_for_instance")
def run_pipeline_for_instance(instance: str, min_quality_score: float = 50.0) -> str:
    """
    Run training data generation for a single GP-PROJECTS instance (e.g. '01-instance').
    Use when you need to regenerate data for one client environment without touching others.
    Returns JSON with examples generated and output file path.
    """
    config = GenerationConfig(min_quality_score=min_quality_score)
    pipeline = TrainingPipeline(config=config)
    result = pipeline.run_for_instance(instance)
    return json.dumps(result, indent=2, default=str)


@tool("validate_output_file")
def validate_output_file(file_path: str, min_quality_score: float = 50.0) -> str:
    """
    Validate quality of training examples in a JSONL output file.
    Checks instruction clarity, input completeness, output quality, and metadata.
    Returns pass rate, average score, tier breakdown (excellent/good/acceptable/poor),
    and whether the file meets the minimum quality threshold for corpus inclusion.
    """
    try:
        result = validate_training_file(file_path, min_quality_score)
    except FileNotFoundError:
        return json.dumps({"error": f"File not found: {file_path}"})

    summary = {
        "file": file_path,
        "total_examples": result["total"],
        "passed": len(result["passed"]),
        "failed": len(result["failed"]),
        "pass_rate_pct": round(result["stats"]["pass_rate"], 1),
        "avg_score": round(result["stats"]["avg_score"], 1),
        "excellent_rate_pct": round(result["stats"]["excellent_rate"], 1),
        "by_quality": {k: len(v) for k, v in result["by_quality"].items()},
        "meets_threshold": result["stats"]["pass_rate"] >= min_quality_score,
    }
    # Surface top issues from failed examples for the quality auditor
    top_issues: list[str] = []
    for item in result["failed"][:5]:
        top_issues.extend(item.get("issues", []))
    if top_issues:
        summary["sample_issues"] = list(dict.fromkeys(top_issues))[:8]

    return json.dumps(summary, indent=2)


@tool("get_batch_stats")
def get_batch_stats(file_path: str) -> str:
    """
    Return domain, task_type, and skill_level distribution for a JSONL training file.
    Use after a pipeline run to check coverage across security domains and rank levels.
    """
    import json as _json
    from pathlib import Path as _Path

    fpath = _Path(file_path)
    if not fpath.exists():
        return _json.dumps({"error": f"File not found: {file_path}"})

    by_domain: dict = {}
    by_task_type: dict = {}
    by_skill_level: dict = {}
    total = 0

    with open(fpath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = _json.loads(line)
                meta = data.get("metadata", {})
                domain = meta.get("domain", "unknown")
                task_type = meta.get("task_type", "unknown")
                skill_level = meta.get("skill_level", "unknown")
                by_domain[domain] = by_domain.get(domain, 0) + 1
                by_task_type[task_type] = by_task_type.get(task_type, 0) + 1
                by_skill_level[skill_level] = by_skill_level.get(skill_level, 0) + 1
                total += 1
            except _json.JSONDecodeError:
                continue

    return _json.dumps({
        "file": file_path,
        "total_examples": total,
        "by_domain": dict(sorted(by_domain.items(), key=lambda x: x[1], reverse=True)),
        "by_task_type": dict(sorted(by_task_type.items(), key=lambda x: x[1], reverse=True)),
        "by_skill_level": dict(sorted(by_skill_level.items(), key=lambda x: x[1], reverse=True)),
    }, indent=2)
