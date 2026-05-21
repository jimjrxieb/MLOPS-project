"""CrewAI BERU audit template.

Copy-paste use case:
    raw security finding -> triage -> GRC assessment -> POA&M/CISO summary

This is based on the real BERU crew in:
    10-crewai-mlops/beru/agents.py
    10-crewai-mlops/beru/crews/beru_audit.py

Run:
    export CREWAI_LLM=ollama/llama3.2
    export OLLAMA_BASE_URL=http://localhost:11434
    export BERU_API_URL=http://localhost:8088
    python3 crewai_beru_audit_template.py "AC-6 violation: service account has cluster-admin"
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import httpx

os.environ.setdefault("CREWAI_STORAGE_DIR", "/tmp/crewai-storage")

from crewai import Agent, Crew, Process, Task
from crewai.tools import tool

BERU_API_URL = os.getenv("BERU_API_URL", "http://localhost:8088")


def make_llm() -> str:
    """Return a CrewAI-compatible model string.

    CrewAI accepts provider-prefixed strings such as:
        ollama/llama3.2
        ollama/beru:v1.6
        gpt-4o-mini
    """
    return os.getenv("CREWAI_LLM", "ollama/llama3.2")


@tool("beru_assess")
def beru_assess(finding: str) -> str:
    """Submit a finding to BERU API for assessment context."""
    try:
        response = httpx.post(
            f"{BERU_API_URL}/api/beru/ask",
            json={"text": finding},
            timeout=60,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        findings = data.get("findings", [])
        if findings:
            return "\n".join(str(f.get("raw", f)) for f in findings)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return (
            f"BERU API unavailable: {exc}. Continue using the finding text, "
            "NIST 800-53 reasoning, and the required output schema."
        )


@tool("format_poam_item")
def format_poam_item(
    control_id: str,
    weakness_name: str,
    weakness_description: str,
    detection_method: str,
    responsible_role: str,
    scheduled_completion: str,
    milestone: str,
) -> str:
    """Format one POA&M item as JSON."""
    return json.dumps(
        {
            "control_id": control_id,
            "weakness_name": weakness_name,
            "weakness_description": weakness_description,
            "detection_method": detection_method,
            "status": "Ongoing",
            "responsible_role": responsible_role,
            "scheduled_completion": scheduled_completion,
            "milestones": [milestone],
        },
        indent=2,
    )


def triage_agent() -> Agent:
    return Agent(
        role="Security Finding Triage Analyst",
        goal=(
            "Classify a raw security finding by severity and E/D/C/B/S rank, "
            "then define the audit scope."
        ),
        backstory=(
            "You are a security analyst who reads scanner output and quickly "
            "separates noise from findings that need GRC review."
        ),
        tools=[],
        llm=make_llm(),
        verbose=True,
        allow_delegation=False,
    )


def grc_auditor() -> Agent:
    return Agent(
        role="NIST 800-53 GRC Auditor",
        goal=(
            "Map the finding to NIST 800-53, identify evidence gaps, draft a "
            "POA&M item, and produce a concise CISO summary."
        ),
        backstory=(
            "You are a GRC analyst. You do not fix systems. You assess, cite, "
            "document evidence, and route risk to human owners."
        ),
        tools=[beru_assess, format_poam_item],
        llm=make_llm(),
        verbose=True,
        allow_delegation=False,
    )


def build_audit_crew(finding: str) -> Crew:
    triager = triage_agent()
    auditor = grc_auditor()

    triage_task = Task(
        description=(
            "Triage this finding. Classify severity as Critical/High/Medium/Low, "
            "assign an E/D/C/B/S rank, identify affected component, and write a "
            f"one-sentence audit scope.\n\nFinding:\n{finding}"
        ),
        expected_output=(
            "A triage report with severity, E/D/C/B/S rank, affected component, "
            "and one-sentence audit scope."
        ),
        agent=triager,
    )

    audit_task = Task(
        description=(
            "Use the triage report to produce a structured GRC assessment. "
            "Call beru_assess for BERU context when useful. Call format_poam_item "
            "for any FAIL or PARTIAL finding. Do not claim evidence you were not given."
        ),
        expected_output=(
            "JSON with fields: finding, control_id, control_name, status "
            "(PASS/PARTIAL/FAIL), evidence_reviewed, evidence_gap, likelihood, "
            "impact, rank, control_owner, poam_item, ciso_summary."
        ),
        agent=auditor,
        context=[triage_task],
    )

    return Crew(
        agents=[triager, auditor],
        tasks=[triage_task, audit_task],
        process=Process.sequential,
        verbose=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BERU audit CrewAI template.")
    parser.add_argument("finding", nargs="+", help="Raw finding text")
    args = parser.parse_args()

    crew = build_audit_crew(" ".join(args.finding))
    result = crew.kickoff()
    print("\n=== CREW RESULT ===\n")
    print(result)


if __name__ == "__main__":
    main()
