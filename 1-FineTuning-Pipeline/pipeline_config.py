"""
Pipeline config loader.

Usage in any pipeline script:
    from pipeline_config import cfg, pipeline_dir, gp_model_ops, repo_root

    base_model   = cfg["base_model"]
    model_name   = cfg["run"]["model_name"]
    registry     = gp_model_ops / cfg["output"]["registry"]
"""
import yaml
from pathlib import Path

pipeline_dir  = Path(__file__).resolve().parent          # 1-FineTuning-Pipeline/
gp_model_ops  = pipeline_dir.parent                      # GP-MODEL-OPS/
repo_root     = gp_model_ops.parent                      # GP-copilot/

_manifest = pipeline_dir / "pipeline.yaml"


def _load() -> dict:
    if not _manifest.exists():
        raise FileNotFoundError(
            f"pipeline.yaml not found at {_manifest}\n"
            "Edit pipeline.yaml with your current run details before running any step."
        )
    with open(_manifest) as f:
        return yaml.safe_load(f)


cfg: dict = _load()
