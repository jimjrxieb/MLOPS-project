"""FastAPI wrapper for a CrewAI workflow.

Copy-paste use case:
    expose a crew over HTTP for demos, n8n, or another service

This is based on:
    10-crewai-mlops/beru/main.py
    10-crewai-mlops/rag_ingestion/main.py

Run:
    export CREWAI_LLM=ollama/llama3.2
    cd CAPSTONE-PROJECT/templates
    uvicorn crewai_fastapi_service_template:app --host 0.0.0.0 --port 8090

Test:
    curl -X POST http://localhost:8090/run/audit \
      -H 'Content-Type: application/json' \
      -d '{"finding": "SI-2 gap: no patch SLA evidence provided"}'
"""

from __future__ import annotations

import asyncio
import os

os.environ.setdefault("CREWAI_STORAGE_DIR", "/tmp/crewai-storage")

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from crewai_beru_audit_template import build_audit_crew

app = FastAPI(
    title="CrewAI GRC Template Service",
    version="1.0.0",
    description="Minimal FastAPI wrapper around a BERU-style CrewAI audit crew.",
)


class AuditRequest(BaseModel):
    finding: str = Field(..., min_length=5)


def _run_crew_sync(finding: str) -> str:
    crew = build_audit_crew(finding)
    return str(crew.kickoff())


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "crewai-grc-template",
        "llm": os.getenv("CREWAI_LLM", "ollama/llama3.2"),
    }


@app.post("/run/audit")
async def run_audit(req: AuditRequest) -> dict:
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            _run_crew_sync,
            req.finding,
        )
        return {"status": "completed", "result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
