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
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# Add this crew's directory to sys.path so bare imports (agents, crews.*) resolve
# regardless of where uvicorn or python3 is invoked from.
_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

app = FastAPI(title="BERU CrewAI Service", version="1.0.0")


class FindingRequest(BaseModel):
    finding: str


class SSPRequest(BaseModel):
    ssp_text: str
    system_name: Optional[str] = "Target System"
    findings: Optional[str] = ""


def _run_crew(crew):
    return crew.kickoff()


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
    if len(sys.argv) < 3:
        print("Usage:")
        print('  python main.py audit "finding text"')
        print('  python main.py ssp path/to/ssp.txt [SystemName] [path/to/findings.txt]')
        sys.exit(1)

    command = sys.argv[1]

    if command == "audit":
        finding = " ".join(sys.argv[2:])
        from crews.beru_audit import build_audit_crew
        crew = build_audit_crew(finding)
        result = crew.kickoff()
        print("\n=== AUDIT RESULT ===\n")
        print(result)

    elif command == "ssp":
        ssp_path = sys.argv[2]
        system_name = sys.argv[3] if len(sys.argv) > 3 else "Target System"
        findings_path = sys.argv[4] if len(sys.argv) > 4 else None

        with open(ssp_path) as f:
            ssp_text = f.read()

        findings = ""
        if findings_path:
            with open(findings_path) as f:
                findings = f.read()

        from crews.ssp_to_poam import build_ssp_to_poam_crew
        crew = build_ssp_to_poam_crew(ssp_text, system_name, findings)
        result = crew.kickoff()
        print("\n=== SSP → POA&M RESULT ===\n")
        print(result)

    else:
        print(f"Unknown command: {command}. Use 'audit' or 'ssp'.")
        sys.exit(1)
