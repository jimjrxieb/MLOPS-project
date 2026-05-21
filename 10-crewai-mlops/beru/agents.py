import os
import json
import httpx
from crewai import Agent
from crewai.tools import tool

from config_loader import make_llm  # noqa: F401 -- re-exported for backwards compat

BERU_API_URL = os.getenv("BERU_API_URL", "http://beru-api:8088")


@tool("beru_assess")
def beru_assess(finding: str) -> str:
    """Submit a security finding to BERU for NIST 800-53 assessment and POA&M generation."""
    try:
        resp = httpx.post(
            f"{BERU_API_URL}/api/beru/ask",
            json={"text": finding},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        findings = data.get("findings", [])
        if findings:
            return "\n".join(f.get("raw", "") for f in findings)
        return data.get("errors", [str(data)])[0] if data.get("errors") else str(data)
    except Exception as e:
        return f"BERU assess error: {e}"


@tool("beru_poam")
def beru_poam(control_id: str, finding: str) -> str:
    """Ask BERU to generate a POA&M item for a specific NIST control and finding."""
    try:
        resp = httpx.post(
            f"{BERU_API_URL}/api/beru/ask",
            json={"text": f"Generate a FedRAMP-compliant POA&M item for {control_id}: {finding}"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        findings = data.get("findings", [])
        if findings:
            return "\n".join(f.get("raw", "") for f in findings)
        return str(data)
    except Exception as e:
        return f"BERU POA&M error: {e}"


@tool("beru_health")
def beru_health() -> str:
    """Check BERU API health status."""
    try:
        resp = httpx.get(f"{BERU_API_URL}/api/beru/health", timeout=10)
        return resp.json()
    except Exception as e:
        return f"BERU health error: {e}"


@tool("assess_control")
def assess_control(control_id: str, narrative: str, evidence_summary: str) -> str:
    """
    Submit a control narrative + evidence to BERU for Satisfied / Other Than Satisfied /
    Not Applicable determination with justification.
    """
    try:
        resp = httpx.post(
            f"{BERU_API_URL}/api/beru/assess",
            json={
                "ssp_text": f"Control {control_id}:\n{narrative}",
                "evidence_text": [evidence_summary],
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        findings = data.get("findings", [])
        if findings:
            return "\n".join(f.get("raw", "") for f in findings)
        return str(data)
    except Exception as e:
        # Degrade gracefully — agent still has LLM reasoning to fall back on
        return (
            f"BERU API unavailable ({e}). Assess based on narrative and evidence "
            f"provided: control={control_id}"
        )


@tool("format_poam_item")
def format_poam_item(
    control_id: str,
    weakness_name: str,
    weakness_description: str,
    detection_method: str,
    responsible_role: str,
    resources_required: str,
    scheduled_completion: str,
    milestones: str,
) -> str:
    """
    Format a FedRAMP-compliant POA&M item as structured JSON.
    All fields are required. scheduled_completion should be YYYY-MM-DD.
    """
    item = {
        "control_id": control_id,
        "weakness_name": weakness_name,
        "weakness_description": weakness_description,
        "detection_method": detection_method,
        "status": "Ongoing",
        "responsible_role": responsible_role,
        "resources_required": resources_required,
        "scheduled_completion": scheduled_completion,
        "milestones": milestones,
    }
    return json.dumps(item, indent=2)


def beru_auditor() -> Agent:
    return Agent(
        role="NIST 800-53 Internal Auditor",
        goal=(
            "Assess security findings against NIST 800-53 Rev 5 controls, "
            "produce POA&M items with dual citations (800-53 + AI RMF where applicable), "
            "and generate CISO-ready evidence summaries."
        ),
        backstory=(
            "You are BERU, a GRC analyst with deep expertise in NIST 800-53 Rev 5 and "
            "the NIST AI Risk Management Framework. You do not fix findings — you assess, "
            "document, and produce auditor-ready artifacts."
        ),
        tools=[beru_assess, beru_poam, beru_health],
        llm=make_llm(),
        verbose=True,
    )


def ssp_reviewer() -> Agent:
    return Agent(
        role="SSP Control Narrative Reviewer",
        goal=(
            "Read each NIST 800-53 control narrative in the SSP and determine whether "
            "the implementation claim is supported by evidence. Flag every unsupported, "
            "vague, or missing claim. Be skeptical — if a control says 'MFA is enforced' "
            "but no evidence artifact is cited, that is a gap."
        ),
        backstory=(
            "You are a 3PAO-trained SSP reviewer who has read hundreds of system security plans. "
            "You know the difference between a control that is genuinely implemented and one that "
            "is copy-pasted boilerplate. Your job is to produce a precise list of claims that "
            "cannot be verified from the evidence provided — no opinions, just gaps."
        ),
        tools=[beru_health],
        llm=make_llm(),
        verbose=True,
    )


def assessor() -> Agent:
    return Agent(
        role="NIST 800-53 Control Assessor",
        goal=(
            "For each control reviewed, assign a determination: "
            "Satisfied (S), Other Than Satisfied (OTS), or Not Applicable (NA). "
            "Every OTS determination must include the specific gap, the control enhancement "
            "affected, and the impact if left unremediated."
        ),
        backstory=(
            "You are a federal security assessor who has conducted ATO assessments for "
            "FedRAMP Moderate and High systems. You know that 'Other Than Satisfied' is not "
            "a failure — it is an honest finding that protects the AO. You never mark a control "
            "Satisfied unless the evidence actually supports it."
        ),
        tools=[assess_control],
        llm=make_llm(),
        verbose=True,
    )


def sar_writer() -> Agent:
    return Agent(
        role="Security Assessment Report Writer",
        goal=(
            "Synthesize the control assessments into a structured Security Assessment Report. "
            "The SAR must list every control assessed, its determination, the evidence reviewed, "
            "and the gap description for every OTS finding. Format must be auditor-ready."
        ),
        backstory=(
            "You are a technical writer embedded in a GRC team. You have turned raw assessment "
            "notes into SAR sections that passed 3PAO review and satisfied FedRAMP PMO comments. "
            "You write clearly, use exact control IDs, and never editorialize — just facts and findings."
        ),
        tools=[],
        llm=make_llm(),
        verbose=True,
    )


def poam_writer() -> Agent:
    return Agent(
        role="POA&M Item Author",
        goal=(
            "Convert every OTS finding from the SAR into a properly formatted POA&M item. "
            "Each item must include: control ID, weakness name, weakness description, "
            "detection method, responsible role, resources required, scheduled completion date, "
            "and at least one milestone. No OTS finding leaves without a POA&M item."
        ),
        backstory=(
            "You have managed POA&M registries for FedRAMP Moderate authorizations. "
            "You know that a well-written POA&M item is what gets a system its ATO — "
            "a vague one gets a comment from the 3PAO and delays the package by a month. "
            "You write tight, specific, traceable items that an AO can sign off on."
        ),
        tools=[format_poam_item, beru_poam],
        llm=make_llm(),
        verbose=True,
    )


def triage_agent() -> Agent:
    return Agent(
        role="Security Finding Triage Analyst",
        goal=(
            "Receive raw scanner output or incident descriptions, classify severity "
            "and rank (E/D/C/B/S), and route to the appropriate downstream agent."
        ),
        backstory=(
            "You are a senior security analyst who reads scanner output cold and "
            "immediately knows whether something is noise, a quick fix, or a boardroom issue. "
            "Your rank decisions are grounded in impact and exploitability, not CVSS alone."
        ),
        tools=[],
        llm=make_llm(),
        verbose=True,
    )
