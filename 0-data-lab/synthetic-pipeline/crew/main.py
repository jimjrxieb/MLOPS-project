"""
Synthetic Data Pipeline Crew — FastAPI entry point.

Matches the BERU-AI/crew/main.py pattern so it slots into GP-API the same way.

Endpoints:
  POST /run/synthetic-pipeline   — full pipeline run (all instances)
  POST /run/synthetic-pipeline/instance  — single instance run
  GET  /health
"""

import argparse
import json
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .crews.pipeline_crew import build_pipeline_crew

app = FastAPI(
    title="Synthetic Data Pipeline Crew",
    version="1.0.0",
    description="CrewAI-orchestrated training data generation from GP-PROJECTS operational logs.",
)


# ── Request models ──────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    instance_filter: str = Field(
        default="",
        description="Limit to one instance (e.g. '01-instance'). Empty = all instances.",
    )
    min_quality_score: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Minimum quality score for example inclusion (0-100).",
    )
    max_examples: int = Field(
        default=1000,
        gt=0,
        description="Maximum examples per batch.",
    )


class InstanceRequest(BaseModel):
    instance: str = Field(description="Instance ID, e.g. '01-instance'")
    min_quality_score: float = Field(default=50.0, ge=0.0, le=100.0)


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "synthetic-data-pipeline-crew", "version": "1.0.0"}


@app.post("/run/synthetic-pipeline")
def run_pipeline(req: PipelineRequest):
    """
    Run the full synthetic data generation pipeline.
    Discover all GP-PROJECTS sources, generate examples, validate quality,
    and return a coverage report with go/no-go recommendation.
    """
    try:
        crew = build_pipeline_crew(
            instance_filter=req.instance_filter,
            min_quality_score=req.min_quality_score,
            max_examples=req.max_examples,
        )
        result = crew.kickoff()
        return {"status": "complete", "report": str(result)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/run/synthetic-pipeline/instance")
def run_pipeline_for_instance(req: InstanceRequest):
    """
    Run the pipeline scoped to a single GP-PROJECTS instance.
    Faster than a full run when you only need to refresh one client's data.
    """
    try:
        crew = build_pipeline_crew(
            instance_filter=req.instance,
            min_quality_score=req.min_quality_score,
        )
        result = crew.kickoff()
        return {"status": "complete", "instance": req.instance, "report": str(result)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── CLI entry ────────────────────────────────────────────────────────────────

def _cli():
    parser = argparse.ArgumentParser(
        description="Synthetic Data Pipeline Crew",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    run_cmd = sub.add_parser("run", help="Run the pipeline crew")
    run_cmd.add_argument("--instance", default="", help="Filter to one instance")
    run_cmd.add_argument("--min-quality", type=float, default=50.0)
    run_cmd.add_argument("--max-examples", type=int, default=1000)

    sub.add_parser("serve", help="Start FastAPI server on port 8001")

    args = parser.parse_args()

    if args.command == "run":
        crew = build_pipeline_crew(
            instance_filter=args.instance,
            min_quality_score=args.min_quality,
            max_examples=args.max_examples,
        )
        result = crew.kickoff()
        print("\n" + "=" * 60)
        print("Pipeline Report:")
        print("=" * 60)
        print(result)

    elif args.command == "serve":
        uvicorn.run("crew.main:app", host="0.0.0.0", port=8001, reload=False)

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
