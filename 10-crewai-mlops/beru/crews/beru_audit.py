from crewai import Crew, Task, Process
from agents import beru_auditor, triage_agent


def build_audit_crew(finding: str) -> Crew:
    triager = triage_agent()
    auditor = beru_auditor()

    triage_task = Task(
        description=(
            f"Triage the following security finding. Classify severity (Critical/High/Medium/Low), "
            f"assign a rank (E/D/C/B/S), and summarize what needs auditing:\n\n{finding}"
        ),
        expected_output=(
            "A triage report with: severity classification, rank assignment, "
            "affected system/component, and a one-sentence audit scope statement."
        ),
        agent=triager,
    )

    audit_task = Task(
        description=(
            "Using the triage report, perform a full NIST 800-53 assessment. "
            "Identify the applicable control family and control ID. "
            "Call BERU to generate a POA&M item. "
            "Produce a CISO-ready summary with control citation and remediation timeline."
        ),
        expected_output=(
            "A JSON object compatible with crewai_mlops.beru.schemas.AuditFinding. "
            "It must include: finding, control_id, control_name, ai_rmf_subcategory "
            "(null if not applicable), status, determination, evidence_reviewed, "
            "evidence_gap, likelihood, impact, rank, control_owner, poam_item, "
            "and ciso_summary. POA&M dates must use YYYY-MM-DD."
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
