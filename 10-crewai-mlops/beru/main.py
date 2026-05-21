"""
CrewAI service — FastAPI wrapper + CLI entry point.

REST API (for n8n HTTP Request nodes):
  POST /run/beru-audit      body: {"finding": "..."}
  POST /run/ssp-to-poam     body: {"ssp_text": "...", "system_name": "...", "findings": "..."}
  GET  /health

CLI:
  python main.py audit "finding text here"
  python main.py ssp path/to/ssp.txt [--system "SystemName"] [--findings path/to/findings.txt]
"""

import sys
import asyncio
import argparse
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# Add this crew's directory to sys.path so bare imports (agents, crews.*) resolve
# regardless of where uvicorn or python3 is invoked from.
_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

os.environ.setdefault("CREWAI_STORAGE_DIR", "/tmp/crewai-storage")

app = FastAPI(title="BERU CrewAI Service", version="1.0.0")


class FindingRequest(BaseModel):
    finding: str


class SSPRequest(BaseModel):
    ssp_text: str
    system_name: Optional[str] = "Target System"
    findings: Optional[str] = ""


def _run_crew(crew):
    return crew.kickoff()


def _cli():
    parser = argparse.ArgumentParser(description="BERU CrewAI CLI")
    sub = parser.add_subparsers(dest="command")

    audit_p = sub.add_parser("audit", help="Run BERU audit crew for a finding")
    audit_p.add_argument("finding", nargs="+", help="Finding text to assess")

    ssp_p = sub.add_parser("ssp", help="Run SSP to SAR/POA&M crew")
    ssp_p.add_argument("ssp_path", help="Path to SSP text or markdown")
    ssp_p.add_argument("system_name", nargs="?", default="Target System")
    ssp_p.add_argument("findings_path", nargs="?")

    args = parser.parse_args()

    if args.command == "audit":
        from crews.beru_audit import build_audit_crew

        crew = build_audit_crew(" ".join(args.finding))
        result = crew.kickoff()
        print("\n=== AUDIT RESULT ===\n")
        print(result)
        return

    if args.command == "ssp":
        from crews.ssp_to_poam import build_ssp_to_poam_crew

        ssp_text = Path(args.ssp_path).read_text()
        findings = Path(args.findings_path).read_text() if args.findings_path else ""
        crew = build_ssp_to_poam_crew(ssp_text, args.system_name, findings)
        result = crew.kickoff()
        print("\n=== SSP -> POA&M RESULT ===\n")
        print(result)
        return

    parser.print_help()


@app.get("/health")
def health():
    return {"status": "ok", "service": "crewai"}


@app.post("/run/beru-audit")
async def run_beru_audit(req: FindingRequest):
    if not req.finding.strip():
        raise HTTPException(status_code=400, detail="finding is required")
    try:
        from crews.beru_audit import build_audit_crew
        crew = build_audit_crew(req.finding)
        result = await asyncio.get_event_loop().run_in_executor(None, _run_crew, crew)
        return {"status": "completed", "result": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run/ssp-to-poam")
async def run_ssp_to_poam(req: SSPRequest):
    if not req.ssp_text.strip():
        raise HTTPException(status_code=400, detail="ssp_text is required")
    try:
        from crews.ssp_to_poam import build_ssp_to_poam_crew
        crew = build_ssp_to_poam_crew(
            ssp_text=req.ssp_text,
            system_name=req.system_name,
            findings=req.findings or "",
        )
        result = await asyncio.get_event_loop().run_in_executor(None, _run_crew, crew)
        return {"status": "completed", "system": req.system_name, "result": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    _cli()
