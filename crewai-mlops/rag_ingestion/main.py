"""
RAG Ingestion Prep Crew — FastAPI entry point + CLI.

Endpoints:
  POST /run/rag-prep   — run pre-flight + crew, write processed JSONL + report
  GET  /health

CLI:
  python3 -m crewai_mlops.rag_ingestion.main run
  python3 -m crewai_mlops.rag_ingestion.main run --category compliance
  python3 -m crewai_mlops.rag_ingestion.main run --dry-run
  python3 -m crewai_mlops.rag_ingestion.main run --min-quality 70
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import tools as _tools
from .collectors import run_prep_collectors
from .crews.prep_crew import build_prep_crew

# Output goes here (same as existing preprocess_pipeline.py)
_PREPROCESSED_DIR = (
    Path(__file__).parent.parent.parent
    / "2-rag-ingestion"
    / "03-preprocessed"
)

app = FastAPI(
    title="RAG Ingestion Prep Crew",
    version="1.0.0",
    description="CrewAI-orchestrated RAG prep: quality review, semantic labeling, routing validation.",
)


class PrepRequest(BaseModel):
    category: Optional[str] = None
    dry_run: bool = False
    min_quality: int = 50


@app.get("/health")
def health():
    return {"status": "ok", "crew": "rag-ingestion", "port": 8002}


@app.post("/run/rag-prep")
async def run_rag_prep(req: PrepRequest):
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, _run_pipeline, req.category, req.dry_run, req.min_quality
        )
        return {"status": "completed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _run_pipeline(
    category: Optional[str] = None,
    dry_run: bool = False,
    min_quality: int = 50,
) -> dict:
    """Orchestrate pre-flight + crew. Returns summary dict."""
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    state_file = Path(f"/tmp/rag-prep-{run_id}/state.json")

    print(f"[rag-prep] run_id={run_id} category={category} dry_run={dry_run}")

    # Step 1: Pre-flight — pure Python, no LLM
    print("[rag-prep] running pre-flight collectors (stages 1-4 + Tier1/2 labeling)...")
    state = run_prep_collectors(
        state_file=state_file,
        category=category,
        dry_run=dry_run,
        min_quality=min_quality,
    )
    stats = state["stats"]
    print(
        f"[rag-prep] pre-flight done: "
        f"{stats['pass_count']} PASS, {stats['repair_count']} REPAIR, "
        f"{stats['fail_count']} FAIL, {stats['total_chunks']} chunks"
    )

    # Step 2: Wire tools to this run's state file
    _tools.set_state_file(state_file)

    # Step 3: Crew kickoff — agents handle judgment
    print("[rag-prep] starting crew (quality review → labeling → routing → report)...")
    crew = build_prep_crew()
    crew_result = crew.kickoff()
    crew_report = str(crew_result)

    # Step 4: Apply overrides + assemble final JSONL
    if not dry_run:
        processed_file, report_file = _write_outputs(run_id, state_file, crew_report)
        print(f"[rag-prep] wrote {processed_file}")
        print(f"[rag-prep] wrote {report_file}")
    else:
        processed_file = report_file = None
        print("[rag-prep] dry-run: no files written")

    return {
        "run_id": run_id,
        "stats": stats,
        "processed_file": str(processed_file) if processed_file else None,
        "report_file": str(report_file) if report_file else None,
        "crew_report": crew_report,
    }


def _write_outputs(run_id: str, state_file: Path, crew_report: str):
    """Apply agent overrides and write processed JSONL + markdown report."""
    state = json.loads(state_file.read_text())
    quality_overrides = state["quality_overrides"]
    label_overrides = state["label_overrides"]
    routing_overrides = state["routing_overrides"]

    _PREPROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    processed_file = _PREPROCESSED_DIR / f"processed_{run_id}.jsonl"
    report_file = _PREPROCESSED_DIR / f"crew-report_{run_id}.md"

    # Collect all items: pass_batch + unlabeled_batch + repair_batch promoted to PASS
    all_items = list(state["pass_batch"]) + list(state["unlabeled_batch"])
    for item in state["repair_batch"]:
        override = quality_overrides.get(item.get("content_hash", ""))
        if override and override["decision"] == "PASS":
            all_items.append(item)

    # Apply label + routing overrides, write JSONL
    with processed_file.open("w") as f:
        for item in all_items:
            h = item.get("content_hash", "")
            chunks = item.get("chunks", [])
            dest = routing_overrides.get(h, {}).get("destination") or item.get("destination")
            collection = routing_overrides.get(h, {}).get("rag_collection") or item.get("rag_collection")
            lab = label_overrides.get(h, {})
            for chunk in chunks:
                if lab:
                    chunk.setdefault("metadata", {}).update({
                        "domain": lab.get("domain", []),
                        "type": lab.get("type", []),
                        "difficulty": lab.get("difficulty", "intermediate"),
                        "tags": lab.get("tags", []),
                    })
                chunk.setdefault("metadata", {}).update({
                    "rag_collection": collection,
                    "destination": dest,
                    "run_id": run_id,
                })
                f.write(json.dumps(chunk) + "\n")

    report_file.write_text(crew_report)
    return processed_file, report_file


def _cli():
    parser = argparse.ArgumentParser(description="RAG Ingestion Prep Crew CLI")
    sub = parser.add_subparsers(dest="command")
    run_p = sub.add_parser("run", help="Run the prep crew")
    run_p.add_argument("--category", default=None, help="Process one category only")
    run_p.add_argument("--dry-run", action="store_true", help="Skip writing output files")
    run_p.add_argument("--min-quality", type=int, default=50, help="Min quality score (0-100)")
    args = parser.parse_args()

    if args.command == "run":
        result = _run_pipeline(
            category=args.category,
            dry_run=args.dry_run,
            min_quality=args.min_quality,
        )
        print(json.dumps(result, indent=2, default=str))
    else:
        parser.print_help()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "serve":
        _cli()
    else:
        uvicorn.run("crewai_mlops.rag_ingestion.main:app", host="0.0.0.0", port=8002, reload=True)
